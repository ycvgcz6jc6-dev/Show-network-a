"""Read-only ETC Sensor3/CEM3 web monitor.

The CEM3 user manual documents a basic HTTP web interface whose System page
shows rack software/power information and active errors, and whose Dimmers page
shows the current status of circuits. This client performs fixed GETs
and three fixed read-only POST queries observed on real CEM3 hardware.

No private command endpoint is assumed and no CEM3 configuration is changed.
"""
from __future__ import annotations

import asyncio
import html
import logging
import socket
import aiohttp
import xml.etree.ElementTree as ET
from copy import deepcopy
import ipaddress
import re
from dataclasses import dataclass, field, asdict
from html.parser import HTMLParser
from time import monotonic, time
from urllib.parse import urljoin, urlparse

MAX_BODY = 2 * 1024 * 1024
DEFAULT_TIMEOUT = 2.5


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._anchor: list[str] = []
        self._ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style"}:
            self._ignored += 1
        if self._ignored:
            return
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._anchor = []
        if tag.lower() in {"br", "p", "div", "tr", "li", "td", "th", "h1", "h2", "h3"}:
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style"}:
            self._ignored = max(0, self._ignored - 1)
        if self._ignored:
            return
        if tag.lower() == "a" and self._href:
            label = " ".join("".join(self._anchor).split())
            self.links.append((label, self._href))
            self._href = None
            self._anchor = []
        if tag.lower() in {"p", "div", "tr", "li", "td", "th", "h1", "h2", "h3"}:
            self.text.append("\n")

    def handle_data(self, data):
        if self._ignored:
            return
        self.text.append(data)
        if self._href is not None:
            self._anchor.append(data)

    def plain_text(self) -> str:
        raw = html.unescape("".join(self.text)).replace("\xa0", " ")
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)


def _num(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, flags=re.I | re.M)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except (ValueError, IndexError):
        return None


def _str(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.I | re.M)
    return " ".join(match.group(1).strip().split()) if match else None


def parse_cem3_system_html(body: str) -> dict:
    """Parse only values visibly present on a CEM3 web System page."""
    parser = _HTMLTextParser()
    parser.feed(body)
    text = parser.plain_text()

    # Support both the face-panel wording documented by ETC and common web
    # labels.  Values remain None unless a label/value pair is actually found.
    cpu = _num(r"CPU\s*Temp(?:erature)?\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\s*°?\s*([CF])?", text)
    cpu_unit_match = re.search(r"CPU\s*Temp(?:erature)?\s*[:=]?\s*-?\d+(?:[.,]\d+)?\s*°?\s*([CF])", text, re.I)
    cpu_unit = cpu_unit_match.group(1).upper() if cpu_unit_match else None
    if cpu is not None and cpu_unit == "F":
        cpu = round((cpu - 32.0) * 5.0 / 9.0, 2)

    volt_match = re.search(
        r"(?:X|Phase\s*A)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\D+"
        r"(?:Y|Phase\s*B)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\D+"
        r"(?:Z|Phase\s*C)\s*[:=]?\s*(\d+(?:[.,]\d+)?)",
        text, re.I | re.S,
    )
    phase = [None, None, None]
    if volt_match:
        try:
            phase = [float(volt_match.group(i).replace(",", ".")) for i in (1, 2, 3)]
        except ValueError:
            logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)

    rack_name = _str(r"(?:Rack\s*Name|Name)\s*[:=]\s*([^\n]+)", text)
    rack_number = _num(r"Rack\s*(?:#|Number)\s*[:=]?\s*(\d+)", text)
    match = re.search(r"Rack\s*#\s*(\d+)\s*[-–]\s*([^\n]+)", text, re.I)
    if match:
        if rack_number is None:
            rack_number = float(match.group(1))
        rack_name = rack_name or " ".join(match.group(2).split())

    web_name = _str(r"CEM3[ \t]*([^\n]+?)\s*\(Rack\s*#\s*\d+\)", text)
    rack_name = rack_name or web_name

    software = _str(r"(?:SW\s*Ver(?:sion)?|Software\s*Version|CEM3\s+v)\s*[:=]?\s*([0-9][^\n ]*)", text)
    frequency = _num(r"Frequency\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*Hz", text)
    rack_type = _str(r"Rack\s*Type\s*[:=]\s*([^\n]+)", text)
    panic = _str(r"Panic\s*State\s*[:=]\s*([^\n]+)", text)

    # Errors: prefer an explicit Errors section or status wording. Do not infer
    # a fault from unrelated occurrences of words such as "Error" in scripts.
    errors: list[str] = []
    for line in text.splitlines():
        # "AF Card <N>" on its own is the Software Versions table's row label
        # (e.g. "AF Card 1" followed on a separate line by its version
        # number) -- confirmed against a real captured CEM3 System page,
        # where these four lines sit in the version table, not the page's
        # own Errors section. Only a genuine AF-prefixed fault line (with
        # wording beyond just the card number) should still be caught.
        if re.fullmatch(r"AF Card [1-4]", line.strip(), re.I):
            continue
        if re.match(r"^(?:CPU Temp (?:High|Low)|DMX Error Port [AB]|No Data DMX port [AB]|No DMX Port [AB]|Frequency Error|Phase [ABC] Error|Fan Fail|AF .+|Dim Overtemp|Ambient Overtemp)\b", line, re.I):
            if line not in errors:
                errors.append(line[:256])
    status = _str(r"(?:System\s*Status|Status)\s*[:=]\s*([^\n]+)", text)
    if status is None:
        status = _str(r"\b(System\s+OK|Errors\s+Exist)\b", text)

    return {
        "rack_name": rack_name,
        "rack_number": int(rack_number) if rack_number is not None else None,
        "rack_type": rack_type,
        "software_version": software,
        "cpu_temperature_c": cpu,
        "line_frequency_hz": frequency,
        "phase_x_voltage_v": phase[0],
        "phase_y_voltage_v": phase[1],
        "phase_z_voltage_v": phase[2],
        "panic_state": panic,
        "status": status,
        "errors": errors,
        "links": parser.links,
        "text_evidence": text[:4096],
    }


def parse_cem3_circuit_setup_html(body: str) -> dict:
    """Extract per-circuit patch configuration from the CEM3 web UI's
    "Circuit Setup" page (setup.html: Space / Circuit / Lug / Module /
    Firing Mode / Control Mode / Curve), verified directly against a real
    CEM3 rack's own captured page (72 real circuits, module part numbers
    ETD15AFR/ETD25AFR/ED15N, control modes Dimmable/Switched, curves
    Custom1/ModSquare -- all four real values confirmed present).

    This is patch/configuration data, distinct from parse_cem3_dimmers_html
    (live circuit levels on a different page, dimmers.html) -- no overlap,
    no assumption that one page's schema applies to the other.

    Deliberately conservative like the rest of this module: matches only
    the documented column order and the HTML <select> "selected" option's
    own value attribute for Control Mode/Curve (i.e. reads exactly what
    the web UI itself currently shows as selected, never a private JSON
    endpoint). A row missing any of the seven columns in this exact shape
    is skipped rather than guessed at.
    """
    if len(body.encode("utf-8")) > MAX_BODY:
        raise ValueError("Unsafe or oversized CEM3 HTML")
    circuits = []
    row_re = re.compile(
        r"<tr><td>(\d{1,4})</td><td>(\d{1,4})</td><td>(\d{1,4})</td>"
        r"<td>([^<]*)</td><td>([^<]*)</td>"
        r"<td><select[^>]*>.*?<option\s+selected=\"selected\"\s+value=\"([^\"]*)\"[^>]*>.*?</select></td>"
        r"<td><select[^>]*>.*?<option\s+selected=\"selected\"\s+value=\"([^\"]*)\"[^>]*>.*?</select></td></tr>",
        re.S,
    )
    for m in row_re.finditer(body):
        circuits.append({
            "space": int(m.group(1)),
            "circuit": int(m.group(2)),
            "lug": int(m.group(3)),
            "module": m.group(4).strip() or None,
            "firing_mode": m.group(5).strip() or None,
            "control_mode": m.group(6) or None,
            "curve": m.group(7) or None,
        })
        if len(circuits) >= MAX_CIRCUITS:
            break
    modules = sorted({c["module"] for c in circuits if c["module"]})
    return {
        "circuit_setup_total": len(circuits),
        "circuit_setup_modules": modules,
        "circuits": circuits,
    }


def parse_cem3_dimmers_html(body: str) -> dict:
    """Extract conservative circuit statistics from visible HTML text."""
    parser = _HTMLTextParser()
    parser.feed(body)
    text = parser.plain_text()
    lines = text.splitlines()
    # The official web page is documented as a circuit status table.  Rather
    # than assuming a private JSON schema, count only rows that visibly begin
    # with a circuit number and contain a percentage level.
    circuits = []
    # HTML table cells are deliberately separated by newlines by the parser.
    # Match the documented Circuit / ... / Level ordering without assuming
    # vendor-private element IDs or JSON endpoints.
    for m in re.finditer(r"(?:^|\n)(\d{1,4})\n([^\n]+)\n(\d{1,3})%(?=\n|$)", text):
        level = max(0, min(100, int(m.group(3))))
        circuits.append({"circuit": int(m.group(1)), "level_percent": level, "raw": " ".join(m.groups())[:256]})
        if len(circuits) >= 1024:
            break
    return {
        "circuits_total": len(circuits),
        "circuits_active": sum(1 for row in circuits if row["level_percent"] > 0),
        "circuits": circuits[:128],
        "text_evidence": text[:4096],
    }


# Only these exact requests can leave this module. No caller-supplied XML/URL.
READ_QUERIES = {
    "levels": '<setlevels><get udn="all"/></setlevels>',
    "properties": '<get_prop udn="all" />',
    "spaces": '<setlevels><get_space_info /></setlevels>',
}
MAX_RACKS = 32
MAX_CIRCUITS = 1024
_LOGGER = logging.getLogger(__name__)


def _xml_rows(body: str, tag: str, fields: tuple[str, ...], integers: tuple[str, ...], key: str) -> list[dict]:
    if len(body.encode('utf-8')) > MAX_BODY or re.search(r'<!\s*(DOCTYPE|ENTITY)', body, re.I):
        raise ValueError('Unsafe or oversized CEM3 XML')
    root = ET.fromstring(body)
    rows, seen = [], set()
    for node in root.iter(tag):
        if not all(field in node.attrib for field in fields):
            raise ValueError(f'Incomplete CEM3 {tag}')
        row = {field: node.attrib[field] for field in fields}
        if any(len(value) > 256 for value in row.values()):
            raise ValueError('Oversized CEM3 attribute')
        for field in integers:
            if not re.fullmatch(r'\d{1,7}', row[field]):
                raise ValueError(f'Invalid CEM3 {field}')
            row[field] = int(row[field])
        if row[key] in seen:
            raise ValueError(f'Duplicate CEM3 {key}')
        seen.add(row[key])
        rows.append(row)
        if len(rows) > MAX_CIRCUITS:
            raise ValueError('Too many CEM3 rows')
    if not rows:
        raise ValueError(f'No CEM3 {tag} records')
    return rows


def parse_cem3_levels(body: str) -> list[dict]:
    rows = _xml_rows(body, 'info', ('udn', 'circuit', 'space', 'side', 'wsource', 'level'),
                     ('udn', 'circuit', 'space', 'level'), 'udn')
    if any(row['level'] > 100 for row in rows):
        raise ValueError('CEM3 level outside 0–100')
    # Preserve the observed raw level, including 99; do not rescale it to 100.
    return [dict(row, level_percent=row['level']) for row in rows]


def parse_cem3_properties(body: str) -> list[dict]:
    return _xml_rows(body, 'prop_info', ('udn', 'space', 'circuit', 'control_mode',
        'firing_mode', 'curve', 'threshold', 'module_type', 'controllable_module'),
        ('udn', 'space', 'circuit', 'threshold', 'controllable_module'), 'udn')


def parse_cem3_spaces(body: str) -> list[dict]:
    return _xml_rows(body, 'info', ('space', 'name', 'active_preset', 'active_sequence'),
                     ('space', 'active_preset', 'active_sequence'), 'space')


def validate_cem3_identity(body: str) -> bool:
    parser = _HTMLTextParser()
    parser.feed(body)
    text = parser.plain_text()
    # Generic rack/dimmers pages and a lone vendor/model string are insufficient.
    return bool(re.search(r'\bCEM3\b', text, re.I)
        and re.search(r'\bETC\b|Electronic Theatre Controls', text, re.I)
        and re.search(r'get_cem3_rack\.gif|\bSensor3\b', body, re.I)
        and re.search(r'CPU\s*Temp|Software\s*Version|SW\s*Ver|Rack\s*(?:#|Number|Type)', text, re.I))


def _ipv4(value: str) -> str:
    address = ipaddress.IPv4Address(value.strip())
    if address.is_unspecified or address.is_multicast or int(address) == 0xffffffff:
        raise ValueError('CEM3 requires a unicast IPv4 address')
    return str(address)


def selected_networks(source_ips: tuple[str, ...]) -> list[dict]:
    """Inventory only explicitly selected, up NIC addresses; no route guessing."""
    import psutil
    stats = psutil.net_if_stats()
    rows = []
    for name, addresses in psutil.net_if_addrs().items():
        if not stats.get(name) or not stats[name].isup:
            continue
        for addr in addresses:
            if addr.family == socket.AF_INET and addr.address in source_ips and addr.netmask:
                rows.append({'interface': name, 'address': addr.address,
                    'network': str(ipaddress.ip_network(f'{addr.address}/{addr.netmask}', strict=False))})
    return rows


def discovery_candidates(networks: list[dict], neighbors: list[dict] = ()) -> list[tuple[str, str]]:
    """Small subnets only; on larger subnets probe complete observed neighbors."""
    groups = []
    local = {row['address'] for row in networks}
    for row in networks:
        net = ipaddress.IPv4Network(row['network'])
        if net.prefixlen < 24:
            hosts = [ipaddress.IPv4Address(n['ip']) for n in neighbors
                     if n.get('complete') and n.get('interface') == row['interface']
                     and ipaddress.IPv4Address(n['ip']) in net]
        else:
            hosts = list(net.hosts())
        groups.append([(str(host), row['address']) for host in hosts
                       if str(host) not in local and host not in (net.network_address, net.broadcast_address)
                       and not host.is_multicast and not host.is_loopback][:254])
    # Interleave NICs so a busy first subnet cannot starve the other selected NICs.
    result = []
    for index in range(max((len(g) for g in groups), default=0)):
        for group in groups:
            if index < len(group) and group[index] not in result:
                result.append(group[index])
    return result


@dataclass
class CEM3RackState:
    host: str
    source_ip: str | None = None
    discovered: bool = False
    online: bool = False
    last_seen_epoch: float | None = None
    last_error: str | None = None
    response_ms: float | None = None
    system_url: str | None = None
    dimmers_url: str | None = None
    data: dict = field(default_factory=dict)
    dimmers: dict = field(default_factory=dict)
    spaces: list = field(default_factory=list)
    properties: list = field(default_factory=list)
    updated: dict = field(default_factory=dict)
    section_errors: dict = field(default_factory=dict)

    def snapshot(self) -> dict:
        row = asdict(self)
        row.pop('properties', None)  # Already merged into circuits.
        row['errors_count'] = len(self.data.get('errors') or [])
        row['age_seconds'] = round(max(0, time() - self.last_seen_epoch), 1) if self.last_seen_epoch else None
        row['freshness'] = {key: bool(self.online and key not in self.section_errors and time() - self.updated.get(key, 0) <= age)
                            for key, age in (('system', 15), ('levels', 15), ('properties', 180), ('spaces', 15))}
        row['fresh'] = row['freshness']['system'] and row['freshness']['levels']
        return row


class CEM3WebMonitor:
    """Bounded read-only polling, selected-NIC discovery and explicit IP support."""

    def __init__(self, hosts: list[str], *, source_ip: str | None = None,
                 source_ips: list[str] | None = None, discovery: bool = False,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        self.hosts = tuple(dict.fromkeys(_ipv4(h) for h in hosts if h.strip()))
        if len(self.hosts) > MAX_RACKS:
            raise ValueError('At most 32 CEM3 racks')
        self.source_ips = tuple(dict.fromkeys(_ipv4(s) for s in (source_ips or [source_ip]) if s and s != '0.0.0.0'))
        self.source_ip = self.source_ips[0] if len(self.source_ips) == 1 else None
        self.discovery = bool(discovery)
        self.timeout = max(.5, min(10., float(timeout)))
        self.racks = {host: CEM3RackState(host) for host in self.hosts}
        self._sessions = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(4)
        self._stopped = False
        self._last_poll = float('-inf')
        self._next_scan = 0.
        self._candidates = []
        self._networks = []
        self._tasks = set()
        self.discovery_status = 'disabled' if not discovery else 'waiting for selected interfaces'

    async def _request(self, host: str, kind: str, source: str | None) -> str:
        if kind not in ('system', 'system_front', *READ_QUERIES):
            raise ValueError('Non-read-only CEM3 request refused')
        if self._stopped:
            raise asyncio.CancelledError
        host = _ipv4(host)
        session = self._sessions.get(source)
        if session is None or session.closed:
            connector = aiohttp.TCPConnector(local_addr=(source, 0) if source else None, limit=4)
            session = aiohttp.ClientSession(connector=connector, trust_env=False,
                timeout=aiohttp.ClientTimeout(total=self.timeout))
            self._sessions[source] = session
        path = {'system': '/index.asp', 'system_front': '/front.asp'}.get(kind, '/dimmerlist')
        method = 'GET' if kind.startswith('system') else 'POST'
        async with self._semaphore:
            async with session.request(method, f'http://{host}{path}',
                data=READ_QUERIES.get(kind), allow_redirects=False,
                headers={'User-Agent': 'Show-Network/CEM3-readonly', 'Connection': 'close',
                         'Content-Type': 'text/xml; charset=utf-8'}) as response:
                if response.status != 200:
                    raise OSError(f'CEM3 HTTP {response.status}')
                body = bytearray()
                async for chunk in response.content.iter_chunked(16384):
                    body.extend(chunk)
                    if len(body) > MAX_BODY:
                        raise ValueError('CEM3 body exceeds 2 MiB')
                try:
                    return body.decode(response.charset or 'utf-8', errors='replace')
                except LookupError:
                    return body.decode('utf-8', errors='replace')

    def _routes(self, host: str) -> list[str | None]:
        if not self.source_ips:
            return [None]  # Manual IP keeps system routing when no NIC selected.
        address = ipaddress.IPv4Address(host)
        matching = [r['address'] for r in self._networks if address in ipaddress.ip_network(r['network'])]
        if matching:
            previous = self.racks.get(host)
            if previous and previous.source_ip in matching:
                matching.insert(0, previous.source_ip)
            return list(dict.fromkeys(matching))
        # Explicit single NIC may reach a routed rack. Multiple NICs require an
        # on-link match so a rack cannot accidentally be polled over another NIC.
        return list(self.source_ips) if len(self.source_ips) == 1 else []

    async def _poll(self, host: str, source: str | None, discovered: bool = False) -> CEM3RackState:
        previous = self.racks.get(host)
        state = deepcopy(previous) if previous else CEM3RackState(host, discovered=discovered)
        state.source_ip = source
        state.online = False
        state.last_error = None
        started = monotonic()
        try:
            body = await self._request(host, 'system', source)
            if re.search(r'<(?:frame|iframe)\b[^>]*src=[\"\']/?front\.asp[\"\']', body, re.I):
                body += '\n' + await self._request(host, 'system_front', source)
            if not validate_cem3_identity(body):
                raise ValueError('ETC CEM3 identity not strongly validated')
            state.data = parse_cem3_system_html(body)
            state.data.pop('text_evidence', None)
            state.data.pop('links', None)
            state.updated['system'] = time()
            levels = parse_cem3_levels(await self._request(host, 'levels', source))
            state.updated['levels'] = time()
            for kind, parser in (('properties', parse_cem3_properties), ('spaces', parse_cem3_spaces)):
                if kind == 'properties' and time() - state.updated.get(kind, 0) < 60:
                    identity = {(r['udn'], r['space'], r['circuit']) for r in levels}
                    if {(r['udn'], r['space'], r['circuit']) for r in state.properties} == identity:
                        continue
                try:
                    rows = parser(await self._request(host, kind, source))
                    if kind == 'properties':
                        identity = {(r['udn'], r['space'], r['circuit']) for r in levels}
                        if {(r['udn'], r['space'], r['circuit']) for r in rows} != identity:
                            raise ValueError('CEM3 levels/properties identity mismatch')
                    elif not {r['space'] for r in levels}.issubset({r['space'] for r in rows}):
                        raise ValueError('CEM3 levels/spaces identity mismatch')
                    setattr(state, kind, rows)
                    state.updated[kind] = time()
                    state.section_errors.pop(kind, None)
                except (OSError, ValueError, ET.ParseError, aiohttp.ClientError, asyncio.TimeoutError) as err:
                    state.section_errors[kind] = f'{type(err).__name__}: {err}'[:256]
            props = {(r['udn'], r['space'], r['circuit']): r for r in state.properties}
            circuits = [dict(props.get((r['udn'], r['space'], r['circuit']), {}), **r) for r in levels]
            state.dimmers = {'circuits_total': len(circuits),
                'circuits_active': sum(r['level'] > 0 for r in circuits), 'circuits': circuits}
            state.online = True
            state.last_seen_epoch = time()
            state.response_ms = round((monotonic() - started) * 1000, 1)
            state.system_url = f'http://{host}/index.asp'
            state.dimmers_url = f'http://{host}/dimmerlist'
        except (OSError, ValueError, ET.ParseError, aiohttp.ClientError, asyncio.TimeoutError) as err:
            state.last_error = f'{type(err).__name__}: {err}'[:512]
        return state

    async def _poll_routes(self, host, routes, discovered=False):
        result = None
        for source in routes:
            result = await self._poll(host, source, discovered)
            if result.online:
                break
        if result is None:
            result = deepcopy(self.racks.get(host)) or CEM3RackState(host)
            result.online = False
            result.last_error = 'No matching selected CEM3 interface'
        return result

    async def _update(self):
        try:
            self._networks = await asyncio.to_thread(selected_networks, self.source_ips)
        except (OSError, ImportError):
            self._networks = []
            _LOGGER.debug('CEM3 NIC inventory unavailable', exc_info=True)
        known = await asyncio.gather(*(self._poll_routes(h, self._routes(h)) for h in self.hosts))
        for state in known:
            self.racks[state.host] = state
        if self.discovery and self.source_ips:
            if not self._candidates and monotonic() >= self._next_scan:
                from .network_discovery import arp_neighbors
                neighbors = await asyncio.to_thread(arp_neighbors)
                self._candidates = discovery_candidates(self._networks, neighbors)
                self._next_scan = monotonic() + 300
            # A maximum of eight candidates per coordinator cycle; four requests
            # at a time. Discovery never adds unverified or partially read racks.
            batch, self._candidates = self._candidates[:8], self._candidates[8:]
            results = await asyncio.gather(*(self._poll_routes(h, [s], True) for h, s in batch if h not in self.racks))
            for state in results:
                if state.online and not state.section_errors and len(self.racks) < MAX_RACKS:
                    self.racks[state.host] = state
            self.hosts = tuple(self.racks)
            self.discovery_status = f'{len(self._candidates)} candidates pending; limit {MAX_RACKS} racks'
        elif self.discovery:
            self.discovery_status = 'Select explicit CEM3 IPv4 interfaces to enable discovery'

    async def async_update(self) -> None:
        async with self._lock:
            if self._stopped or monotonic() - self._last_poll < 5:
                return
            self._last_poll = monotonic()
            task = asyncio.create_task(self._update(), name='show-network-cem3-poll')
            self._tasks.add(task)
            try:
                await task
            finally:
                self._tasks.discard(task)

    async def stop(self) -> None:
        self._stopped = True
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()
        self._candidates.clear()

    def snapshot(self, *, detail: bool = True) -> dict:
        rows = [self.racks[h].snapshot() for h in self.hosts]
        if not detail:
            for row in rows:
                row['dimmers'].pop('circuits', None)
                row['spaces'] = []
        temperatures = [r['data'].get('cpu_temperature_c') for r in rows
                        if r['fresh'] and r['data'].get('cpu_temperature_c') is not None]
        return {'enabled': True, 'read_only': True, 'transport': 'CEM3 HTTP fixed read-only queries',
            'source_ip': self.source_ip, 'source_ips': list(self.source_ips),
            'discovery': self.discovery, 'discovery_status': self.discovery_status,
            'total': len(rows), 'online': sum(r['online'] and r['fresh'] for r in rows),
            'errors_total': sum(r['errors_count'] for r in rows if r['fresh']),
            'temperature_max_c': max(temperatures) if temperatures else None, 'racks': rows}

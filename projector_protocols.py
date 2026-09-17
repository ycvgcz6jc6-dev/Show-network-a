"""Projector protocol adapters used by Show Network.

The adapters are intentionally conservative:
- polling only sends documented read/query operations;
- write operations are exposed separately and must still pass Show Network's
  security/control gate in ``services/projector.py``;
- unsupported fields remain absent instead of being synthesized.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import hashlib
import json
import os
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPBasicAuthHandler,
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
)


class ProjectorProtocolError(RuntimeError):
    pass


class ProjectorAuthError(PermissionError):
    pass


def _recv_until(sock: socket.socket, terminator: bytes = b"\r", *, limit: int = 65536) -> bytes:
    """Read until a protocol terminator, handling fragmented TCP frames."""
    buf = bytearray()
    while len(buf) < limit:
        chunk = sock.recv(min(4096, limit - len(buf)))
        if not chunk:
            break
        buf.extend(chunk)
        if terminator in buf:
            return bytes(buf[: buf.index(terminator) + len(terminator)])
    if terminator not in buf:
        raise ConnectionError("incomplete projector response")
    return bytes(buf)


def _clean_text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").strip("\r\n\x00 ")


@dataclass
class ProjectorTelemetry:
    source: str
    manufacturer: str | None = None
    model: str | None = None
    name: str | None = None
    serial_number: str | None = None
    software_version: str | None = None
    power: str | None = None
    input_source: str | None = None
    input_name: str | None = None
    available_inputs: list[str] = field(default_factory=list)
    av_mute: str | None = None
    errors: str | None = None
    error_detail: dict[str, Any] = field(default_factory=dict)
    lamp_hours: int | None = None
    source_hours: dict[str, float] = field(default_factory=dict)
    temperatures_c: dict[str, float] = field(default_factory=dict)
    fans_rpm: dict[str, float] = field(default_factory=dict)
    signal: str | None = None
    authenticated: bool | None = None
    auth_method: str | None = None
    capabilities: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class PJLinkClient:
    """PJLink v1/v2 client with legacy MD5 and PJLink 2.10 SHA256 support."""

    def __init__(self, host: str, port: int = 4352, *, password: str | None = None, timeout: float = 2.0):
        self.host = host
        self.port = int(port)
        self.password = password or ""
        self.timeout = float(timeout)
        self.sock: socket.socket | None = None
        self.auth_prefix = ""
        self.authenticated = False
        self.auth_method = "none"

    @staticmethod
    def legacy_digest(random_hex: str, password: str) -> str:
        return hashlib.md5((random_hex + password).encode("ascii")).hexdigest()

    @staticmethod
    def sha256_digest(projector_random_hex: str, controller_random_hex: str, password: str) -> str:
        p = bytes.fromhex(projector_random_hex)
        c = bytes.fromhex(controller_random_hex)
        if len(p) != 16 or len(c) != 16:
            raise ValueError("PJLink SHA256 random must be 16 bytes")
        x = bytes(a ^ b for a, b in zip(p, c))
        return hashlib.sha256(x.hex().encode("ascii") + password.encode("ascii")).hexdigest()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def connect(self) -> None:
        self.close()
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        s.settimeout(self.timeout)
        banner = _clean_text(_recv_until(s))
        if banner == "PJLINK 0":
            self.sock = s
            self.auth_prefix = ""
            self.authenticated = True
            self.auth_method = "none"
            return
        m = re.fullmatch(r"PJLINK 1 ([0-9A-Fa-f]{8})", banner)
        if not m:
            s.close()
            raise ConnectionError(f"invalid PJLink greeting: {banner!r}")
        if not self.password:
            s.close()
            raise ProjectorAuthError("PJLink authentication required but no password configured")

        legacy_random = m.group(1).lower()
        # PJLink 2.10 security negotiation. A modern projector answers
        # ``PJLINK 2 <32 hex>``; old projectors reject/ignore it and are retried
        # with the legacy MD5 procedure on a fresh TCP session.
        try:
            s.sendall(b"PJLINK 2\r")
            modern = _clean_text(_recv_until(s))
        except Exception:
            modern = ""
        mm = re.fullmatch(r"PJLINK 2 ([0-9A-Fa-f]{32})", modern)
        if mm:
            controller_random = os.urandom(16).hex()
            digest = self.sha256_digest(mm.group(1).lower(), controller_random, self.password)
            self.sock = s
            self.auth_prefix = controller_random + digest
            self.authenticated = True
            self.auth_method = "sha256"
            return

        # Legacy fallback requires a fresh session because the negotiation probe
        # may have invalidated the old connection.
        try:
            s.close()
        except Exception:
            pass
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        s.settimeout(self.timeout)
        banner2 = _clean_text(_recv_until(s))
        m2 = re.fullmatch(r"PJLINK 1 ([0-9A-Fa-f]{8})", banner2)
        if not m2:
            s.close()
            raise ConnectionError("PJLink authentication fallback failed")
        self.sock = s
        self.auth_prefix = self.legacy_digest(m2.group(1).lower(), self.password)
        self.authenticated = True
        self.auth_method = "md5"

    def command(self, command: str) -> str:
        if self.sock is None:
            raise ConnectionError("PJLink client is not connected")
        payload = (self.auth_prefix + command + "\r").encode("ascii")
        self.sock.sendall(payload)
        text = _clean_text(_recv_until(self.sock))
        if text == "PJLINK ERRA":
            raise ProjectorAuthError("PJLink authentication failed")
        return text

    @staticmethod
    def value(response: str) -> str | None:
        if "=" not in response:
            return None
        value = response.split("=", 1)[1].strip()
        if value in {"ERR1", "ERR2", "ERR3", "ERR4", "ERRA"}:
            return None
        return value

    def poll(self) -> ProjectorTelemetry:
        out = ProjectorTelemetry(source="pjlink")
        with self:
            out.authenticated = self.authenticated
            out.auth_method = self.auth_method
            class1 = {
                "power": "%1POWR ?", "input_source": "%1INPT ?", "av_mute": "%1AVMT ?",
                "errors": "%1ERST ?", "lamp": "%1LAMP ?", "available_inputs": "%1INST ?",
                "name": "%1NAME ?", "manufacturer": "%1INF1 ?", "model": "%1INF2 ?",
                "other": "%1INFO ?", "pjlink_class": "%1CLSS ?",
            }
            values: dict[str, str] = {}
            for key, cmd in class1.items():
                try:
                    values[key] = self.command(cmd)
                except ProjectorAuthError:
                    raise
                except Exception:
                    continue
            if not values:
                raise ProjectorProtocolError("no PJLink query returned a response")

            p = self.value(values.get("power", ""))
            out.power = {"0": "off", "1": "on", "2": "cooling", "3": "warming"}.get(p, p)
            out.input_source = self.value(values.get("input_source", ""))
            a = self.value(values.get("av_mute", ""))
            out.av_mute = {"30": "off", "31": "on", "10": "video", "20": "audio"}.get(a, a)
            out.errors = self.value(values.get("errors", ""))
            out.name = self.value(values.get("name", ""))
            out.manufacturer = self.value(values.get("manufacturer", ""))
            out.model = self.value(values.get("model", ""))
            inputs = self.value(values.get("available_inputs", ""))
            if inputs:
                out.available_inputs = inputs.split()
            lamp = self.value(values.get("lamp", ""))
            if lamp:
                parts = lamp.split()
                if parts:
                    try:
                        out.lamp_hours = int(parts[0])
                    except ValueError:
                        pass
            cls = self.value(values.get("pjlink_class", ""))
            if cls:
                out.raw["pjlink_class"] = cls
            out.raw["other_info"] = self.value(values.get("other", ""))
            out.capabilities.extend(["power", "input", "av_mute", "errors", "identity"])

            if cls and cls.startswith("2"):
                class2 = {
                    "serial_number": "%2SNUM ?", "software_version": "%2SVER ?",
                    "input_resolution": "%2IRES ?", "recommended_resolution": "%2RRES ?",
                    "filter_hours": "%2FILT ?", "lamp_replacement": "%2RLMP ?",
                    "filter_replacement": "%2RFIL ?",
                }
                for key, cmd in class2.items():
                    try:
                        value = self.value(self.command(cmd))
                    except Exception:
                        value = None
                    if value is not None:
                        if key == "serial_number": out.serial_number = value
                        elif key == "software_version": out.software_version = value
                        else: out.raw[key] = value
                if out.input_source:
                    try:
                        out.input_name = self.value(self.command(f"%2INNM ?{out.input_source}"))
                    except Exception:
                        pass
                out.capabilities.append("class2")
        return out

    def write(self, name: str, value: str | None = None) -> str:
        commands = {
            "power_on": "%1POWR 1", "standby": "%1POWR 0",
            "av_mute_on": "%1AVMT 31", "av_mute_off": "%1AVMT 30",
        }
        if name == "input":
            if not value:
                raise ValueError("input value required")
            command = f"%1INPT {value}"
        else:
            command = commands.get(name)
            if not command:
                raise ValueError(f"unsupported PJLink command: {name}")
        with self:
            return self.command(command)


class PanasonicWebAPI:
    """Panasonic Projector & Display Web API v1 (Digest auth)."""

    def __init__(self, host: str, *, username: str | None = None, password: str | None = None,
                 scheme: str = "http", port: int | None = None, timeout: float = 3.0):
        self.host = host
        self.username = username or ""
        self.password = password or ""
        self.scheme = scheme
        self.port = port
        self.timeout = timeout
        authority = host if port is None else f"{host}:{int(port)}"
        self.base = f"{scheme}://{authority}/api/v1"

    def _opener(self):
        mgr = HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, self.base, self.username, self.password)
        return build_opener(HTTPDigestAuthHandler(mgr), HTTPBasicAuthHandler(mgr))

    def _request(self, path: str, *, method: str = "GET", body: Any | None = None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(self.base + "/" + path.lstrip("/"), data=data, method=method,
                      headers={"Accept": "application/json", "Content-Type": "application/json"})
        try:
            with self._opener().open(req, timeout=self.timeout) as response:
                payload = response.read(1_048_576)
        except HTTPError as exc:
            if exc.code == 401:
                raise ProjectorAuthError("Panasonic Web API authentication failed") from exc
            raise ProjectorProtocolError(f"Panasonic Web API HTTP {exc.code}") from exc
        except URLError as exc:
            raise ProjectorProtocolError(f"Panasonic Web API unavailable: {exc.reason}") from exc
        if not payload:
            return {}
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise ProjectorProtocolError("Panasonic Web API returned invalid JSON") from exc

    @staticmethod
    def _num(value: Any) -> float | None:
        if value is None:
            return None
        m = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
        return float(m.group(0)) if m else None

    def poll(self) -> ProjectorTelemetry:
        out = ProjectorTelemetry(source="panasonic_webapi", manufacturer="Panasonic", authenticated=True, auth_method="digest")
        endpoints = ["device-information", "version", "power", "input", "error", "temperatures", "signal", "lights", "fans"]
        values: dict[str, Any] = {}
        for ep in endpoints:
            try:
                values[ep] = self._request(ep)
            except ProjectorAuthError:
                raise
            except Exception as exc:
                values[ep] = {"_error": str(exc)}
        info = values.get("device-information") if isinstance(values.get("device-information"), dict) else {}
        out.model = info.get("model-name")
        out.serial_number = info.get("serial-no")
        out.name = info.get("projector-name")
        out.raw["mac_address"] = info.get("mac-address")
        out.raw["device_runtime"] = info.get("device-runtime")
        out.raw["power_on_times"] = info.get("power-on-times")
        ver = values.get("version") if isinstance(values.get("version"), dict) else {}
        out.software_version = ver.get("main-version")
        pwr = values.get("power") if isinstance(values.get("power"), dict) else {}
        out.power = pwr.get("power-state")
        inp = values.get("input") if isinstance(values.get("input"), dict) else {}
        out.input_source = inp.get("input-state")
        err = values.get("error") if isinstance(values.get("error"), dict) else {}
        if err:
            out.error_detail = {k: v for k, v in err.items() if not k.startswith("_")}
            out.errors = "ok" if all(str(v).lower() in {"0", "ok", "normal", "none", "false"} for v in out.error_detail.values()) else "reported"
        temp = values.get("temperatures") if isinstance(values.get("temperatures"), dict) else {}
        for item in temp.get("temperatures", []) or []:
            if not isinstance(item, dict):
                continue
            v = self._num(item.get("temperature-celsius"))
            if v is not None:
                out.temperatures_c[str(item.get("temperature-name") or item.get("temperature-id") or len(out.temperatures_c)+1)] = v
        sig = values.get("signal") if isinstance(values.get("signal"), dict) else {}
        out.signal = sig.get("signal-information")
        lights = values.get("lights") if isinstance(values.get("lights"), dict) else {}
        for item in lights.get("lights", []) or []:
            if isinstance(item, dict):
                runtime = self._num(item.get("light-runtime"))
                if runtime is not None:
                    out.source_hours[str(item.get("light-name") or item.get("light-id") or len(out.source_hours)+1)] = runtime
        fans = values.get("fans") if isinstance(values.get("fans"), dict) else {}
        for item in fans.get("fans", []) or []:
            if isinstance(item, dict):
                rpm = self._num(item.get("fan-rotation-speed"))
                if rpm is not None:
                    out.fans_rpm[str(item.get("fan-name") or item.get("fan-id") or len(out.fans_rpm)+1)] = rpm
        out.raw["endpoint_errors"] = {k: v.get("_error") for k, v in values.items() if isinstance(v, dict) and v.get("_error")}
        out.capabilities.extend(["power", "input", "errors", "identity", "temperature", "signal", "light_hours", "fans"])
        return out

    def write(self, name: str, value: str | None = None) -> Any:
        if name == "power_on": return self._request("power", method="PUT", body={"power-state": "on"})
        if name == "standby": return self._request("power", method="PUT", body={"power-state": "standby"})
        if name == "input":
            if value is None: raise ValueError("input value required")
            return self._request("input", method="PUT", body={"input-state": value})
        raise ValueError(f"unsupported Panasonic command: {name}")


class DigitalProjectionASCII:
    """Digital Projection ASCII protocol family (documented Rev A/F/H style)."""
    def __init__(self, host: str, port: int = 7000, *, timeout: float = 2.0):
        self.host, self.port, self.timeout = host, int(port), float(timeout)

    def _query(self, command: str, operator: str = "?") -> str:
        text = f"*{command}{(' ' + operator) if operator else ''}\r"
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.settimeout(self.timeout)
            s.sendall(text.encode("ascii"))
            raw = _clean_text(_recv_until(s))
        low = raw.lower()
        if low.startswith("nak") or low.startswith("nack"):
            raise ProjectorProtocolError(raw)
        # Common responses include "ACK command = value", "ack value" or
        # simply the value. Keep only the payload when safely identifiable.
        cleaned = re.sub(r"^(?:ack|ACK)\s*", "", raw).strip()
        if "=" in cleaned:
            cleaned = cleaned.split("=", 1)[1].strip()
        return cleaned

    @staticmethod
    def _int(value: str | None) -> int | None:
        if value is None: return None
        m = re.search(r"\d+", value)
        return int(m.group(0)) if m else None

    def poll(self) -> ProjectorTelemetry:
        out = ProjectorTelemetry(source="digital_projection_ascii", manufacturer="Digital Projection")
        queries = ["model.name", "serial", "ser.number", "sw.version", "soft.version", "power", "act.source", "signal", "shutter", "laser.hours", "lamp.hours", "lamp1.hours", "lamp2.hours", "total.hours", "errcode", "ti", "tc", "fans", "ac.voltage", "status.check"]
        vals: dict[str, str] = {}
        for q in queries:
            try: vals[q] = self._query(q)
            except Exception: continue
        if not vals:
            raise ProjectorProtocolError("no Digital Projection ASCII response")
        out.model = vals.get("model.name")
        out.serial_number = vals.get("serial") or vals.get("ser.number")
        out.software_version = vals.get("sw.version") or vals.get("soft.version")
        p = vals.get("power")
        if p is not None:
            out.power = {"0":"off","1":"on","off":"off","on":"on","standby":"standby"}.get(p.strip().lower(), p)
        out.input_source = vals.get("act.source")
        out.signal = vals.get("signal")
        if "shutter" in vals:
            out.av_mute = {"0":"off","1":"on","open":"off","close":"on","closed":"on"}.get(vals["shutter"].lower(), vals["shutter"])
        for key in ("laser.hours", "lamp.hours", "lamp1.hours", "lamp2.hours", "total.hours"):
            n = self._int(vals.get(key))
            if n is not None: out.source_hours[key] = float(n)
        if out.source_hours:
            out.lamp_hours = int(max(out.source_hours.values()))
        for key in ("ti", "tc"):
            if key in vals:
                m = re.search(r"[-+]?\d+(?:\.\d+)?", vals[key])
                if m: out.temperatures_c[key] = float(m.group(0))
        if vals.get("errcode") is not None:
            out.errors = vals["errcode"]
        out.raw.update({k:v for k,v in vals.items() if k not in {"model.name","serial","ser.number","sw.version","soft.version","power","act.source","signal","shutter"}})
        out.capabilities.extend(["power", "input", "shutter", "identity", "hours", "signal"])
        return out

    def write(self, name: str, value: str | None = None) -> str:
        if name == "power_on": cmd = "*power = on\r"
        elif name == "standby": cmd = "*power = off\r"
        elif name == "input":
            if value is None: raise ValueError("input value required")
            cmd = f"*input = {value}\r"
        elif name == "av_mute_on": cmd = "*shutter = 1\r"
        elif name == "av_mute_off": cmd = "*shutter = 0\r"
        else: raise ValueError(f"unsupported Digital Projection command: {name}")
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.settimeout(self.timeout); s.sendall(cmd.encode("ascii")); return _clean_text(_recv_until(s))


class ChristieHSSerialAPI:
    """Christie HS Series serial API over TCP (default port 3002)."""
    def __init__(self, host: str, port: int = 3002, *, timeout: float = 2.0):
        self.host, self.port, self.timeout = host, int(port), float(timeout)

    def _command(self, command: str) -> str:
        wire = f"({command})\r".encode("ascii")
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.settimeout(self.timeout); s.sendall(wire); return _clean_text(_recv_until(s))

    @staticmethod
    def _payload(response: str) -> str:
        return response.strip().strip("()").strip()

    def poll(self) -> ProjectorTelemetry:
        out = ProjectorTelemetry(source="christie_hs", manufacturer="Christie")
        commands = ["PWR?", "SST?", "PIF+MDLN?", "PIF+SNUM?", "PIF+FWVS?", "LIF+LPHS", "LIF+LSHS", "LCE?", "ERR?"]
        vals: dict[str,str] = {}
        for cmd in commands:
            try: vals[cmd] = self._payload(self._command(cmd))
            except Exception: continue
        if not vals:
            raise ProjectorProtocolError("no Christie HS response")
        p = vals.get("PWR?")
        if p:
            m = re.search(r"(?:PWR[^01]*)?([01])\b", p)
            if m: out.power = "on" if m.group(1) == "1" else "off"
        for key, attr in (("PIF+MDLN?","model"),("PIF+SNUM?","serial_number"),("PIF+FWVS?","software_version")):
            v=vals.get(key)
            if v:
                payload = re.sub(r"^[A-Z+?]+\s*", "", v).strip()
                setattr(out, attr, payload or v)
        for key in ("LIF+LPHS","LIF+LSHS"):
            v = vals.get(key)
            if v:
                m = re.search(r"\d+(?:\.\d+)?", v)
                if m: out.source_hours[key] = float(m.group(0))
        if out.source_hours: out.lamp_hours = int(max(out.source_hours.values()))
        out.errors = vals.get("LCE?") or vals.get("ERR?")
        out.raw["projector_status"] = vals.get("SST?")
        out.capabilities.extend(["power", "identity", "hours", "status", "errors"])
        return out

    def write(self, name: str, value: str | None = None) -> str:
        if name == "power_on": cmd="PWR 1"
        elif name == "standby": cmd="PWR 0"
        elif name == "input":
            if value is None: raise ValueError("input value required")
            cmd=f"SIN {value}"
        elif name == "av_mute_on": cmd="SHU 1"
        elif name == "av_mute_off": cmd="SHU 0"
        else: raise ValueError(f"unsupported Christie HS command: {name}")
        return self._command(cmd)


class BarcoPulseJSONRPC:
    """Barco Pulse JSON-RPC 2.0 transport over persistent TCP port 9090."""
    def __init__(self, host: str, port: int = 9090, *, timeout: float = 2.0, passcode: int | None = None):
        self.host, self.port, self.timeout, self.passcode = host, int(port), float(timeout), passcode
        self._id = 0

    def _call_on(self, s: socket.socket, method: str, params: Any | None = None) -> Any:
        self._id += 1
        req: dict[str,Any] = {"jsonrpc":"2.0", "method":method, "id":self._id}
        if params is not None: req["params"] = params
        s.sendall((json.dumps(req, separators=(",", ":")) + "\r\n").encode("utf-8"))
        decoder = json.JSONDecoder(); buf=""
        while len(buf) < 1_048_576:
            chunk = s.recv(4096)
            if not chunk: break
            buf += chunk.decode("utf-8", "replace")
            stripped = buf.lstrip()
            try:
                obj, _ = decoder.raw_decode(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("id") == self._id:
                if obj.get("error"):
                    raise ProjectorProtocolError(f"Barco JSON-RPC error: {obj['error']}")
                return obj.get("result")
        raise ConnectionError("incomplete Barco JSON-RPC response")

    def _session(self):
        s=socket.create_connection((self.host,self.port),timeout=self.timeout); s.settimeout(self.timeout); return s

    def poll(self) -> ProjectorTelemetry:
        out=ProjectorTelemetry(source="barco_pulse",manufacturer="Barco",auth_method="passcode" if self.passcode is not None else "none")
        vals: dict[str,Any]={}
        with self._session() as s:
            if self.passcode is not None:
                try:
                    vals["authenticate"] = self._call_on(s,"authenticate",{"code":int(self.passcode)})
                    out.authenticated=True
                except Exception:
                    out.authenticated=False
            else: out.authenticated=True
            for prop in ("system.state","image.window.main.source","environment.alarmstate","optics.shutter.position"):
                try: vals[prop]=self._call_on(s,"property.get",{"property":prop})
                except Exception: continue
            for vtype in ("Temperature","Speed"):
                try: vals[f"environment:{vtype}"]=self._call_on(s,"environment.getcontrolblocks",{"type":"Sensor","valuetype":vtype})
                except Exception: continue
            for method in ("image.source.list","firmware.listcomponentversionstatus","environment.getalarminfo"):
                try: vals[method]=self._call_on(s,method)
                except Exception: continue
        if len(vals) <= (1 if "authenticate" in vals else 0):
            raise ProjectorProtocolError("no Barco Pulse telemetry response")
        state=vals.get("system.state")
        if state is not None: out.power=str(state)
        src=vals.get("image.window.main.source")
        if src is not None: out.input_source=str(src)
        if isinstance(vals.get("image.source.list"),list): out.available_inputs=[str(x) for x in vals["image.source.list"]]
        sh=vals.get("optics.shutter.position")
        if sh is not None: out.av_mute="off" if str(sh).lower()=="open" else "on" if str(sh).lower() in {"closed","close"} else str(sh)
        temp=vals.get("environment:Temperature")
        if isinstance(temp,dict):
            for k,v in temp.items():
                try: out.temperatures_c[str(k)]=float(v)
                except (TypeError,ValueError): pass
        speed=vals.get("environment:Speed")
        if isinstance(speed,dict):
            for k,v in speed.items():
                try: out.fans_rpm[str(k)]=float(v)
                except (TypeError,ValueError): pass
        alarms=vals.get("environment.getalarminfo")
        if alarms:
            out.error_detail={"alarms":alarms}; out.errors="reported"
        else:
            alarmstate=vals.get("environment.alarmstate")
            if alarmstate is not None:
                out.errors=str(alarmstate)
        fw=vals.get("firmware.listcomponentversionstatus")
        if fw is not None: out.raw["firmware_components"]=fw
        out.capabilities.extend(["power","input","shutter","temperature","fans","alarms","dynamic_api"])
        return out

    def write(self,name:str,value:str|None=None)->Any:
        with self._session() as s:
            if self.passcode is not None:
                self._call_on(s,"authenticate",{"code":int(self.passcode)})
            if name=="power_on": return self._call_on(s,"system.poweron")
            if name=="standby": return self._call_on(s,"system.poweroff")
            if name=="input":
                if value is None: raise ValueError("input value required")
                return self._call_on(s,"property.set",{"property":"image.window.main.source","value":value})
            if name in {"av_mute_on","av_mute_off"}:
                return self._call_on(s,"property.set",{"property":"optics.shutter.position","value":"Closed" if name=="av_mute_on" else "Open"})
            raise ValueError(f"unsupported Barco Pulse command: {name}")

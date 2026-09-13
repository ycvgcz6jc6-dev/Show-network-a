"""Receive-only sACN and Art-Net observation.

This module intentionally parses only the packet envelope required for
monitoring. It does not transmit, respond, merge, or alter DMX data.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct
from time import monotonic
from collections import deque
import asyncio
import logging


_LOGGER = logging.getLogger(__name__)


@dataclass
class UniverseObservation:
    protocol: str
    universe: int
    source: str
    priority: int | None
    sequence: int | None
    packet_rate: float
    active_channels: int
    values: bytes
    last_change: float | None
    interface: str | None = None
    inter_arrival_ms: float = 0.0
    jitter_ms: float = 0.0
    sequence_loss_pct: float = 0.0

class UniverseTracker:
    def __init__(self, max_items: int = 2048, history_seconds: float = 2.0):
        self.max_items = max(64, int(max_items))
        self.history_seconds = max(0.5, float(history_seconds))
        self._items={}
        self._times={}
        self._previous={}
        self._last_time={}
        self._last_sequence={}
        self._seq_expected={}
        self._seq_received={}
        self._order=deque()

    def observe(self, protocol, universe, source, values, priority=None, sequence=None, interface=None):
        key=(protocol,universe,source)
        now=monotonic()
        times=self._times.setdefault(key, deque())
        times.append(now)
        cutoff=now-self.history_seconds
        while times and times[0] < cutoff:
            times.popleft()
        previous=self._previous.get(key)
        changed=previous is not None and previous != values
        current=bytes(values[:512])
        self._previous[key]=current
        last_time = self._last_time.get(key)
        inter = (now-last_time)*1000.0 if last_time is not None else 0.0
        self._last_time[key]=now
        prev_inter = getattr(self._items.get(key), "inter_arrival_ms", 0.0)
        jitter = abs(inter-prev_inter) if last_time is not None else 0.0
        if sequence is not None and protocol.upper() == "SACN":
            prev = self._last_sequence.get(key)
            if prev is not None:
                gap = (int(sequence)-int(prev)) & 0xFF
                if 1 < gap < 128: self._seq_expected[key] = self._seq_expected.get(key, 0) + gap - 1
            self._last_sequence[key]=int(sequence)
            self._seq_received[key]=self._seq_received.get(key, 0)+1
        rate=len(times)/self.history_seconds
        received=self._seq_received.get(key, 0); lost=self._seq_expected.get(key, 0)
        loss=(lost/max(1, lost+received))*100.0
        item=UniverseObservation(
            protocol,universe,source,priority,sequence,rate,
            sum(1 for x in current if x),current,
            now if changed else self._items.get(key,UniverseObservation(
                protocol,universe,source,priority,sequence,rate,0,bytes(values),None,interface
            )).last_change,interface,round(inter,2),round(jitter,2),round(loss,2)
        )
        self._items[key]=item
        if key not in self._order:
            self._order.append(key)
        # O(1) bounded eviction: never sort the complete tracker during a burst.
        while len(self._items) > self.max_items and self._order:
            stale_key = self._order.popleft()
            if stale_key not in self._items:
                continue
            self._items.pop(stale_key, None)
            self._times.pop(stale_key, None)
            self._previous.pop(stale_key, None)
            self._last_time.pop(stale_key, None)
            self._last_sequence.pop(stale_key, None)
            self._seq_expected.pop(stale_key, None)
            self._seq_received.pop(stale_key, None)
        return item

    def all(self):
        return list(self._items.values())

def parse_artnet_dmx(data: bytes):
    if len(data)<18 or data[:8] != b"Art-Net\0":
        return None
    opcode=struct.unpack("<H",data[8:10])[0]
    if opcode != 0x5000:
        return None
    universe=struct.unpack("<H",data[14:16])[0]
    length=struct.unpack(">H",data[16:18])[0]
    return universe,data[18:18+length]

def parse_sacn_dmp(data: bytes):
    # Minimal envelope validation: ACN preamble/vector and DMP property data.
    if len(data)<126 or data[:2] != b"\x00\x10":
        return None
    if b"ASC-E1.17" not in data[:64]:
        return None
    universe=struct.unpack(">H",data[113:115])[0]
    priority=data[108]
    sequence=data[111]
    property_count=struct.unpack(">H",data[123:125])[0]
    start=126
    return universe,priority,sequence,data[start:start+property_count-1]

class DmxNetworkReceiver:
    """Passive Art-Net/sACN receiver with bounded queues and restart supervision.

    Socket reads stay non-blocking on asyncio. Packet parsing/dispatch is isolated
    behind one bounded latest-oriented queue per protocol so a burst cannot spend
    unbounded CPU inside the HA event loop. No listener thread is created.
    """

    def __init__(self, interface: str, on_frame, on_timecode=None, multicast_universes=None,
                 queue_size: int = 1024):
        self.interface = interface or "0.0.0.0"
        self.on_frame = on_frame
        self.on_timecode = on_timecode
        self.multicast_universes = tuple(sorted({int(u) for u in (multicast_universes or ()) if 1 <= int(u) <= 63999}))
        self.queue_size = max(64, int(queue_size))
        self._tasks: list[asyncio.Task] = []
        self._sockets = []
        # Per-protocol latest packet slots keep parser work bounded during bursts.
        self._latest = {"ARTNET": {}, "SACN": {}}
        self._latest_keys = {"ARTNET": asyncio.Queue(maxsize=self.queue_size), "SACN": asyncio.Queue(maxsize=self.queue_size)}
        self._stopping = False
        self._restart_count = {"ARTNET": 0, "SACN": 0}
        self._errors = {"ARTNET": 0, "SACN": 0}
        self._queue_drops = {"ARTNET": 0, "SACN": 0}
        self._packets_received = {"ARTNET": 0, "SACN": 0}
        self._packets_parsed = {"ARTNET": 0, "SACN": 0}
        self._last_error: dict[str, str | None] = {"ARTNET": None, "SACN": None}
        self._last_packet = {"ARTNET": None, "SACN": None}

    async def start(self):
        self._stopping = False
        for protocol, port, group in (("ARTNET", 6454, None), ("SACN", 5568, "239.255.0.0")):
            self._tasks.append(asyncio.create_task(
                self._supervise(protocol, port, group),
                name=f"show-network-{protocol.lower()}-supervisor",
            ))
        await asyncio.sleep(0)

    def _join_groups(self, sock, protocol, group):
        import socket
        if not group:
            return
        if hasattr(socket, "IP_MULTICAST_ALL"):
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_ALL, 1)
            except OSError:
                pass
        groups = self.multicast_universes or (1,)
        for universe in groups:
            octets = ((int(universe) - 1) // 256, (int(universe) - 1) % 256)
            target = f"239.255.{octets[0]}.{octets[1]}"
            mreq = socket.inet_aton(target) + socket.inet_aton(self.interface if self.interface != "0.0.0.0" else "0.0.0.0")
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except OSError:
                if target == "239.255.0.1" and not hasattr(socket, "IP_MULTICAST_ALL"):
                    raise

    async def _open_socket(self, protocol, port, group):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.interface, port))
            self._join_groups(sock, protocol, group)
            sock.setblocking(False)
            self._sockets.append((sock, group))
            return sock
        except Exception:
            sock.close()
            raise

    async def _supervise(self, protocol, port, group):
        backoff = 1.0
        # Minimum uptime (seconds) below which a connection is considered a
        # failed/flapping attempt: the backoff only resets to 1.0 once the
        # receive loop has actually stayed up longer than this, so a listener
        # that connects then immediately errors out keeps backing off instead
        # of retrying every second forever.
        MIN_STABLE_UPTIME_S = 5.0
        while not self._stopping:
            sock = None
            parser_task = None
            started_at = None
            try:
                sock = await self._open_socket(protocol, port, group)
                started_at = asyncio.get_running_loop().time()
                parser_task = asyncio.create_task(self._parser_worker(protocol), name=f"show-network-{protocol.lower()}-parser")
                await self._receive(sock, protocol)
            except asyncio.CancelledError:
                return
            except Exception as err:
                self._restart_count[protocol] += 1
                self._errors[protocol] += 1
                self._last_error[protocol] = f"{type(err).__name__}: {err}"
                _LOGGER.warning("%s listener restarted after error: %s", protocol, err)
            finally:
                if parser_task:
                    parser_task.cancel()
                    await asyncio.gather(parser_task, return_exceptions=True)
                if sock is not None:
                    try:
                        self._sockets.remove((sock, group))
                    except ValueError:
                        pass
                    try:
                        sock.close()
                    except OSError:
                        pass
            if started_at is not None and (asyncio.get_running_loop().time() - started_at) > MIN_STABLE_UPTIME_S:
                backoff = 1.0
            if not self._stopping:
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 2.0)

    async def _receive(self, sock, protocol):
        loop = asyncio.get_running_loop()
        while not self._stopping:
            try:
                data, addr = await loop.sock_recvfrom(sock, 2048)
            except asyncio.CancelledError:
                return
            except OSError as err:
                self._last_error[protocol] = f"{type(err).__name__}: {err}"
                return
            self._packets_received[protocol] += 1
            self._last_packet[protocol] = monotonic()
            # The packet is keyed by its source/universe after a minimal envelope
            # extraction.  Existing keys are overwritten instead of queued again.
            # This bounds parser work while retaining latest-state semantics.
            packet = (bytes(data), addr)
            key = (addr[0], self._packet_universe(protocol, data))
            latest = self._latest[protocol]
            if key in latest:
                latest[key] = packet
                self._queue_drops[protocol] += 1
                continue
            if self._latest_keys[protocol].full():
                self._queue_drops[protocol] += 1
                continue
            latest[key] = packet
            self._latest_keys[protocol].put_nowait(key)

    @staticmethod
    def _packet_universe(protocol, data):
        try:
            if protocol == "ARTNET":
                parsed = parse_artnet_dmx(data)
                return parsed[0] if parsed else -1
            parsed = parse_sacn_dmp(data)
            return parsed[0] if parsed else -1
        except (IndexError, struct.error, ValueError):
            return -1

    async def _parser_worker(self, protocol):
        key_queue = self._latest_keys[protocol]
        latest = self._latest[protocol]
        while not self._stopping:
            key = await key_queue.get()
            packet = latest.pop(key, None)
            if packet is None:
                key_queue.task_done()
                continue
            data, addr = packet
            try:
                if protocol == "ARTNET":
                    if self.on_timecode:
                        try:
                            self.on_timecode(data, addr[0])
                        except Exception:
                            pass
                    parsed = parse_artnet_dmx(data)
                    if not parsed:
                        continue
                    universe, values = parsed
                    self.on_frame("Art-Net", universe + 1, addr[0], values, None, None, self.interface)
                else:
                    parsed = parse_sacn_dmp(data)
                    if not parsed:
                        continue
                    universe, priority, sequence, values = parsed
                    self.on_frame("sACN", universe, addr[0], values, priority, sequence, self.interface)
                self._packets_parsed[protocol] += 1
            except Exception as err:
                self._errors[protocol] += 1
                self._last_error[protocol] = f"packet: {type(err).__name__}: {err}"
            finally:
                key_queue.task_done()

    async def stop(self):
        self._stopping = True
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        for sock, _group in self._sockets:
            try:
                sock.close()
            except OSError:
                pass
        self._tasks.clear()
        self._sockets.clear()
        for protocol in self._latest:
            self._latest[protocol].clear()
            q = self._latest_keys[protocol]
            while True:
                try:
                    q.get_nowait()
                    q.task_done()
                except asyncio.QueueEmpty:
                    break

    def snapshot(self) -> dict:
        return {
            "artnet_restarts": self._restart_count["ARTNET"],
            "sacn_restarts": self._restart_count["SACN"],
            "artnet_errors": self._errors["ARTNET"],
            "sacn_errors": self._errors["SACN"],
            "artnet_queue_depth": self._latest_keys["ARTNET"].qsize(),
            "sacn_queue_depth": self._latest_keys["SACN"].qsize(),
            "artnet_queue_drops": self._queue_drops["ARTNET"],
            "sacn_queue_drops": self._queue_drops["SACN"],
            "artnet_packets_received": self._packets_received["ARTNET"],
            "sacn_packets_received": self._packets_received["SACN"],
            "artnet_packets_parsed": self._packets_parsed["ARTNET"],
            "sacn_packets_parsed": self._packets_parsed["SACN"],
            "artnet_last_error": self._last_error["ARTNET"],
            "sacn_last_error": self._last_error["SACN"],
            "artnet_last_packet": self._last_packet["ARTNET"],
            "sacn_last_packet": self._last_packet["SACN"],
            "queue_size": self.queue_size,
            "running": bool(self._tasks) and not self._stopping,
        }

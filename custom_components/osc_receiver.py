"""Receive-only OSC input with bounded message/bundle parsing and Learn mode."""
from __future__ import annotations
import asyncio
import struct
from .security import ip_allowed, normalize_ip_allowlist

MAX_OSC_PACKET = 65535
MAX_BUNDLE_DEPTH = 8
MAX_BUNDLE_ELEMENTS = 256


class OSCMessage:
    def __init__(self, address, values, source, timetag=None):
        self.address = address
        self.values = values
        self.source = source
        self.timetag = timetag


def _align4(n: int) -> int:
    return (n + 3) & ~3


def _read_string(data: bytes, offset: int) -> tuple[str, int]:
    if offset < 0 or offset >= len(data):
        raise ValueError("OSC string offset out of bounds")
    end = data.find(b"\0", offset)
    if end < 0:
        raise ValueError("unterminated OSC string")
    raw = data[offset:end].decode("utf-8")
    nxt = _align4(end + 1)
    if nxt > len(data):
        raise ValueError("truncated OSC string padding")
    return raw, nxt


def parse_basic_message(data: bytes):
    if not data or len(data) > MAX_OSC_PACKET:
        raise ValueError("invalid OSC packet size")
    address, off = _read_string(data, 0)
    if not address.startswith("/"):
        raise ValueError("invalid OSC address")
    tags, off = _read_string(data, off)
    if not tags.startswith(","):
        raise ValueError("invalid OSC type tag")
    values = []
    for tag in tags[1:]:
        if tag == "f":
            if off + 4 > len(data): raise ValueError("truncated OSC float")
            values.append(struct.unpack(">f", data[off:off+4])[0]); off += 4
        elif tag == "i":
            if off + 4 > len(data): raise ValueError("truncated OSC int")
            values.append(struct.unpack(">i", data[off:off+4])[0]); off += 4
        elif tag == "h":
            if off + 8 > len(data): raise ValueError("truncated OSC int64")
            values.append(struct.unpack(">q", data[off:off+8])[0]); off += 8
        elif tag == "d":
            if off + 8 > len(data): raise ValueError("truncated OSC double")
            values.append(struct.unpack(">d", data[off:off+8])[0]); off += 8
        elif tag == "t":
            if off + 8 > len(data): raise ValueError("truncated OSC timetag")
            values.append(struct.unpack(">Q", data[off:off+8])[0]); off += 8
        elif tag == "s":
            value, off = _read_string(data, off); values.append(value)
        elif tag == "b":
            if off + 4 > len(data): raise ValueError("truncated OSC blob length")
            size = struct.unpack(">I", data[off:off+4])[0]; off += 4
            if size > MAX_OSC_PACKET or off + size > len(data): raise ValueError("truncated OSC blob")
            values.append(bytes(data[off:off+size])); off = _align4(off + size)
            if off > len(data): raise ValueError("truncated OSC blob padding")
        elif tag in ("T", "F", "N", "I"):
            values.append({"T": True, "F": False, "N": None, "I": float("inf")}[tag])
        else:
            raise ValueError(f"unsupported OSC type: {tag}")
    return address, tuple(values)


def parse_osc_packet(data: bytes, *, _depth: int = 0, _timetag=None) -> list[tuple[str, tuple, int | None]]:
    """Parse one OSC message or recursively flatten an OSC bundle."""
    if not data or len(data) > MAX_OSC_PACKET:
        raise ValueError("invalid OSC packet size")
    if data.startswith(b"#bundle\0"):
        if _depth >= MAX_BUNDLE_DEPTH:
            raise ValueError("OSC bundle nesting too deep")
        if len(data) < 16:
            raise ValueError("truncated OSC bundle")
        timetag = struct.unpack(">Q", data[8:16])[0]
        off = 16
        out = []
        elements = 0
        while off < len(data):
            if off + 4 > len(data): raise ValueError("truncated OSC bundle element size")
            size = struct.unpack(">I", data[off:off+4])[0]; off += 4
            if size <= 0 or off + size > len(data): raise ValueError("invalid OSC bundle element")
            elements += 1
            if elements > MAX_BUNDLE_ELEMENTS: raise ValueError("too many OSC bundle elements")
            out.extend(parse_osc_packet(data[off:off+size], _depth=_depth+1, _timetag=timetag))
            off += size
        return out
    address, values = parse_basic_message(data)
    return [(address, values, _timetag)]


class OSCReceiver:
    def __init__(self, host="0.0.0.0", port=8000, learn=None, callback=None, allowed_sources=None):
        self.host = host; self.port = port; self.transport = None; self.messages = 0
        self.learn = learn; self.callback = callback
        self.allowed_sources = normalize_ip_allowlist(allowed_sources)
        self.rejected_messages = 0; self.parse_errors = 0
        self._bg_tasks: set[asyncio.Task] = set()

    async def start(self):
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(lambda: _OSCProtocol(self), local_addr=(self.host, self.port))

    async def stop(self):
        if self.transport: self.transport.close(); self.transport = None
        for task in list(self._bg_tasks): task.cancel()
        if self._bg_tasks: await asyncio.gather(*self._bg_tasks, return_exceptions=True)
        self._bg_tasks.clear()

    def handle(self, data, addr):
        if not ip_allowed(addr[0], self.allowed_sources):
            self.rejected_messages += 1; return None
        try:
            parsed = parse_osc_packet(data)
        except Exception:
            self.parse_errors += 1
            raise
        result_messages = []
        for address, values, timetag in parsed:
            self.messages += 1
            message = OSCMessage(address, values, addr, timetag)
            result_messages.append(message)
            if self.learn:
                for value in values: self.learn.observe(address, value, addr[0])
            if self.callback:
                result = self.callback(message)
                if asyncio.iscoroutine(result):
                    task = asyncio.create_task(result, name="show-network-osc-callback")
                    self._bg_tasks.add(task); task.add_done_callback(self._bg_tasks.discard)
        if len(result_messages) == 1:
            return result_messages[0]
        return result_messages


class _OSCProtocol(asyncio.DatagramProtocol):
    def __init__(self, owner): self.owner = owner
    def datagram_received(self, data, addr):
        try: self.owner.handle(data, addr)
        except Exception: pass

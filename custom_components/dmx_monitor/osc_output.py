"""Safe OSC output for Show Network.

OSC output is opt-in and disabled by default. No lighting/network protocol
output is generated unless the user explicitly arms OSC output.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import socket
import struct
from typing import Any

@dataclass
class OSCTarget:
    target_id: str
    name: str
    host: str
    port: int = 8000
    enabled: bool = True

class OSCTargetStore:
    def __init__(self, path: str): self.path = Path(path)
    def load(self) -> list[OSCTarget]:
        if not self.path.exists(): return []
        try:
            return [OSCTarget(**x) for x in json.loads(self.path.read_text(encoding="utf-8"))]
        except (OSError, ValueError, TypeError): return []
    def save(self, targets):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(x) for x in targets], indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

def _pad_string(value: str) -> bytes:
    raw = value.encode("utf-8") + b"\0"
    return raw + b"\0" * ((4 - len(raw) % 4) % 4)

def encode_osc(address: str, args: list[Any] | tuple[Any, ...] = ()) -> bytes:
    if not address.startswith("/"):
        raise ValueError("OSC address must start with '/'")
    tags = [","]
    payload = bytearray()
    for value in args:
        if isinstance(value, bool): tags.append("T" if value else "F")
        elif isinstance(value, int): tags.append("i"); payload.extend(struct.pack(">i", value))
        elif isinstance(value, float): tags.append("f"); payload.extend(struct.pack(">f", value))
        elif isinstance(value, str): tags.append("s"); payload.extend(_pad_string(value))
        else: raise ValueError(f"Unsupported OSC argument type: {type(value).__name__}")
    return _pad_string(address) + _pad_string("".join(tags)) + bytes(payload)

class OSCOutput:
    def __init__(self):
        self.enabled = False
        self.sent = 0
        self.errors = 0
        self.last_target = None
        self.last_address = None
        self.last_error = None
    def send(self, target: OSCTarget, address: str, args=()):
        if not self.enabled: raise RuntimeError("OSC output safety gate is disabled")
        if not target.enabled: raise RuntimeError("OSC target is disabled")
        packet = encode_osc(address, args)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(packet, (target.host, int(target.port)))
            self.sent += 1; self.last_target = target.target_id; self.last_address = address; self.last_error = None
        except OSError as err:
            self.errors += 1; self.last_error = str(err); raise
        finally: sock.close()

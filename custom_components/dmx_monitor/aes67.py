"""Passive AES67/RTP discovery observer.

Only SAP announcements on the standard multicast address/port are observed.
No RTP stream is subscribed to automatically and no audio/control packets are
sent by this module.
"""
from __future__ import annotations
import asyncio, socket, struct, time
from dataclasses import dataclass

SAP_GROUP = "239.255.255.255"
SAP_PORT = 9875

@dataclass(frozen=True)
class SAPObservation:
    source: str
    length: int
    timestamp: float
    payload_hint: str

class AES67Monitor:
    def __init__(self, interface: str = "0.0.0.0") -> None:
        self.interface = interface
        self.packets = 0
        self.sources: set[str] = set()
        self.last: SAPObservation | None = None
        self.sessions: dict[str, dict] = {}
        self._sock: socket.socket | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", SAP_PORT))
            iface = socket.inet_aton(self.interface) if self.interface != "0.0.0.0" else socket.inet_aton("0.0.0.0")
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack("4s4s", socket.inet_aton(SAP_GROUP), iface))
            sock.setblocking(False)
            self._sock = sock
            self._task = asyncio.create_task(self._receive(), name="show-network-aes67")
        except Exception:
            sock.close()
            self._sock = None
            self._task = None
            raise

    async def _receive(self) -> None:
        loop = asyncio.get_running_loop()
        assert self._sock is not None
        while True:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 8192)
            except asyncio.CancelledError:
                return
            except OSError:
                return
            if not data:
                continue
            self.packets += 1
            self.sources.add(addr[0])
            # Keep only a tiny classification hint; never archive SDP/audio payload.
            text = data.decode("utf-8", errors="ignore")
            hint = "sdp" if "application/sdp" in text.lower() or "m=audio" in text.lower() else "sap"
            if hint == "sdp":
                lines=[x.strip() for x in text.replace("\r","\n").split("\n") if x.strip()]
                name=next((x[2:] for x in lines if x.startswith("s=")), None)
                conn=next((x[2:] for x in lines if x.startswith("c=")), None)
                media=next((x[2:] for x in lines if x.startswith("m=audio")), None)
                clock=next((x for x in lines if "ts-refclk:" in x or "mediaclk:" in x), None)
                key=f"{addr[0]}:{name or conn or 'sdp'}"
                self.sessions[key]={"source":addr[0],"name":name,"connection":conn,"media":media,"clock":clock,"last_seen":time.time()}
            self.last = SAPObservation(addr[0], len(data), time.time(), hint)

    def snapshot(self) -> dict:
        return {
            "aes67_sap_packets": self.packets,
            "aes67_sap_sources": len(self.sources),
            "aes67_last_source": self.last.source if self.last else None,
            "aes67_last_length": self.last.length if self.last else None,
            "aes67_last_hint": self.last.payload_hint if self.last else None,
            "aes67_last_seen": self.last.timestamp if self.last else None,
            "aes67_sessions": list(self.sessions.values()),
            "aes67_session_count": len(self.sessions),
        }

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None
        if self._sock:
            self._sock.close()
        self._sock = None

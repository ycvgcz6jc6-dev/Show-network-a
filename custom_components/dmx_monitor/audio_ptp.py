"""Passive PTP observer for Dante/PTPv1, AES67/PTPv2 and related profiles.

Receive-only. No PTP packets are transmitted and the host never participates in
clock election. UDP/319 and UDP/320 are observed on the Dante multicast groups.
"""
from __future__ import annotations
from dataclasses import dataclass
import asyncio, socket, time

PTP_EVENT_PORT = 319
PTP_GENERAL_PORT = 320
PTP_GROUPS = ("224.0.1.129", "224.0.1.130", "224.0.1.131", "224.0.1.132")

@dataclass(frozen=True)
class PTPObservation:
    source: str; port: int; message_type: int | None; version: int | None
    domain: int | None; length: int; timestamp: float

class PTPMonitor:
    def __init__(self, interface: str = "0.0.0.0") -> None:
        self.interface=interface; self.packets=0; self.sources=set(); self.ports=set(); self.groups=set()
        self.last=None; self.event_packets=0; self.general_packets=0; self._last_time=None
        self.inter_arrival_ms=0.0; self.jitter_ms=0.0; self.announce_packets=0; self.sync_packets=0
        self.follow_up_packets=0; self.delay_packets=0; self.version_counts={}; self.domain_counts={}
        self.last_source_identity=None; self.last_grandmaster_identity=None; self.grandmaster_priority1=None
        self.grandmaster_clock_class=None; self.grandmaster_accuracy=None; self.grandmaster_priority2=None
        self._tasks=[]; self._sockets=[]

    async def start(self):
        if self._tasks: return
        try:
            for port in (PTP_EVENT_PORT, PTP_GENERAL_PORT):
                sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); sock.bind(("0.0.0.0",port))
                iface=socket.inet_aton(self.interface if self.interface!="0.0.0.0" else "0.0.0.0")
                for group in PTP_GROUPS:
                    try:
                        sock.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,socket.inet_aton(group)+iface)
                        self.groups.add(group)
                    except OSError:
                        # A single unavailable pull-up/down group must not disable
                        # monitoring of the default PTP group.
                        if group == PTP_GROUPS[0]: raise
                sock.setblocking(False); self._sockets.append(sock)
                self._tasks.append(asyncio.create_task(self._receive(sock,port),name=f"show-network-ptp-{port}"))
        except Exception:
            await self.stop(); raise

    @staticmethod
    def _decode_header(data: bytes):
        if len(data) < 2: return None, None, None
        # PTPv2: transportSpecific/messageType in byte 0 and versionPTP in byte 1.
        v2 = data[1] & 0x0F
        if v2 == 2:
            return data[0] & 0x0F, 2, (data[4] if len(data) >= 5 else None)
        # Dante commonly uses IEEE1588-2002/PTPv1. The complete v1 message
        # layout differs, so only version/presence is asserted here; identities
        # are not fabricated from v2 offsets.
        if v2 == 1:
            return None, 1, None
        return data[0] & 0x0F, (v2 or None), (data[4] if len(data) >= 5 and v2 == 2 else None)

    async def _receive(self,sock,port):
        loop=asyncio.get_running_loop()
        while True:
            try: data,addr=await loop.sock_recvfrom(sock,4096)
            except asyncio.CancelledError: return
            except OSError: return
            if not data: continue
            now=time.time(); msg_type,version,domain=self._decode_header(data)
            if self._last_time is not None:
                inter=(now-self._last_time)*1000.0; previous=self.inter_arrival_ms; self.inter_arrival_ms=inter; self.jitter_ms=abs(inter-previous) if previous else 0.0
            self._last_time=now
            if version is not None: self.version_counts[version]=self.version_counts.get(version,0)+1
            if domain is not None: self.domain_counts[domain]=self.domain_counts.get(domain,0)+1
            if version == 2:
                if msg_type==0: self.sync_packets+=1
                elif msg_type==8: self.follow_up_packets+=1
                elif msg_type in (1,9): self.delay_packets+=1
                elif msg_type==11:
                    self.announce_packets+=1
                    if len(data)>=64:
                        self.last_source_identity=data[20:28].hex(); self.grandmaster_priority1=data[47]
                        self.grandmaster_clock_class=data[48]; self.grandmaster_accuracy=data[49]
                        self.grandmaster_priority2=data[52]; self.last_grandmaster_identity=data[53:61].hex()
            self.packets+=1; self.event_packets += int(port==PTP_EVENT_PORT); self.general_packets += int(port==PTP_GENERAL_PORT)
            self.sources.add(addr[0]); self.ports.add(port); self.last=PTPObservation(addr[0],port,msg_type,version,domain,len(data),now)

    def snapshot(self):
        last=self.last; age=(time.time()-self._last_time) if self._last_time else None
        versions=sorted(self.version_counts)
        return {
            "ptp_packets":self.packets,"ptp_sources":len(self.sources),"ptp_event_packets":self.event_packets,"ptp_general_packets":self.general_packets,
            "ptp_ports":sorted(self.ports),"ptp_last_source":last.source if last else None,"ptp_last_message_type":last.message_type if last else None,
            "ptp_last_version":last.version if last else None,"ptp_versions_observed":versions,"ptp_dante_v1_observed":1 in versions,"ptp_v2_observed":2 in versions,
            "ptp_last_domain":last.domain if last else None,"ptp_domains_observed":sorted(self.domain_counts),"ptp_last_length":last.length if last else None,
            "ptp_last_seen":last.timestamp if last else None,"ptp_inter_arrival_ms":round(self.inter_arrival_ms,3),"ptp_jitter_ms":round(self.jitter_ms,3),
            "ptp_announce_packets":self.announce_packets,"ptp_sync_packets":self.sync_packets,"ptp_follow_up_packets":self.follow_up_packets,"ptp_delay_packets":self.delay_packets,
            "ptp_last_source_identity":self.last_source_identity,"ptp_grandmaster_identity":self.last_grandmaster_identity,"ptp_grandmaster_priority1":self.grandmaster_priority1,
            "ptp_grandmaster_clock_class":self.grandmaster_clock_class,"ptp_grandmaster_accuracy":self.grandmaster_accuracy,"ptp_grandmaster_priority2":self.grandmaster_priority2,
            "ptp_clock_present":bool(self.packets and age is not None and age < 5.0),"ptp_clock_age_s":round(age,3) if age is not None else None,
            "ptp_multicast_groups":list(PTP_GROUPS),"ptp_interface":self.interface,
        }

    async def stop(self):
        for t in self._tasks:t.cancel()
        if self._tasks: await asyncio.gather(*self._tasks,return_exceptions=True)
        self._tasks.clear()
        for s in self._sockets:
            try:s.close()
            except OSError:pass
        self._sockets.clear()

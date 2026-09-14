"""Passive AES67 SAP/SDP discovery observer."""
from __future__ import annotations
import asyncio, socket, struct, time, re
from dataclasses import dataclass

SAP_GROUP="239.255.255.255"; SAP_PORT=9875

@dataclass(frozen=True)
class SAPObservation:
    source:str; length:int; timestamp:float; payload_hint:str

class AES67Monitor:
    def __init__(self,interface="0.0.0.0"):
        self.interface=interface; self.packets=0; self.sources=set(); self.last=None; self.sessions={}; self._sock=None; self._task=None

    async def start(self):
        if self._task:return
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); sock.bind(("",SAP_PORT))
            iface=socket.inet_aton(self.interface if self.interface!="0.0.0.0" else "0.0.0.0")
            sock.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,struct.pack("4s4s",socket.inet_aton(SAP_GROUP),iface)); sock.setblocking(False)
            self._sock=sock; self._task=asyncio.create_task(self._receive(),name="show-network-aes67")
        except Exception:
            sock.close(); self._sock=None; self._task=None; raise

    @staticmethod
    def _parse_sdp(data:bytes, source:str, now:float):
        text=data.decode("utf-8",errors="ignore")
        pos=text.find("v=0")
        if pos<0:return None
        lines=[x.strip() for x in text[pos:].replace("\r","\n").split("\n") if x.strip()]
        fields={}
        for line in lines:
            if len(line)>2 and line[1]=='=': fields.setdefault(line[0],[]).append(line[2:])
        name=(fields.get('s') or [None])[0]; conn=(fields.get('c') or [None])[0]; media=(fields.get('m') or [None])[0]
        origin=(fields.get('o') or [None])[0]
        dest=None
        if conn:
            m=re.search(r"IN IP4 ([0-9.]+)",conn); dest=m.group(1) if m else None
        port=None; payload_type=None
        if media:
            parts=media.split();
            if len(parts)>=2:
                try:port=int(parts[1])
                except ValueError:pass
            if len(parts)>=4: payload_type=parts[3]
        rtpmap=None; clock=None; ptime=None; sync_time=None
        for a in fields.get('a',[]):
            if a.startswith('rtpmap:'):rtpmap=a
            elif a.startswith('ptime:'):ptime=a.split(':',1)[1]
            elif a.startswith('ts-refclk:') or a.startswith('mediaclk:'): clock=(clock+' | ' if clock else '')+a
            elif a.startswith('sync-time:'):sync_time=a.split(':',1)[1]
        encoding=None;sample_rate=None;channels=None
        if rtpmap:
            parts=rtpmap.split(None,1); codec=parts[1] if len(parts)>1 else ''
            bits=codec.split('/')
            encoding=bits[0] if bits else None
            try:sample_rate=int(bits[1]) if len(bits)>1 else None
            except ValueError:sample_rate=None
            try:channels=int(bits[2]) if len(bits)>2 else None
            except ValueError:channels=None
        key=f"{source}|{origin or name or dest or port}"
        return key,{"source":source,"name":name,"origin":origin,"destination":dest,"port":port,"payload_type":payload_type,"rtpmap":rtpmap,"encoding":encoding,"sample_rate":sample_rate,"channels":channels,"ptime_ms":ptime,"clock":clock,"sync_time":sync_time,"last_seen":now}

    async def _receive(self):
        loop=asyncio.get_running_loop(); assert self._sock is not None
        while True:
            try:data,addr=await loop.sock_recvfrom(self._sock,8192)
            except asyncio.CancelledError:return
            except OSError:return
            if not data:continue
            now=time.time(); self.packets+=1; self.sources.add(addr[0])
            parsed=self._parse_sdp(data,addr[0],now); hint="sap"
            if parsed:
                hint="sdp"; key,row=parsed; self.sessions[key]=row
            self.last=SAPObservation(addr[0],len(data),now,hint)

    def snapshot(self):
        now=time.time(); rows=[]
        for row in self.sessions.values():
            r=dict(row); r['age_s']=round(max(0.0,now-r['last_seen']),3); r['fresh']=r['age_s']<30; rows.append(r)
        rows.sort(key=lambda r:(r.get('name') or '',r.get('source') or ''))
        return {"aes67_sap_packets":self.packets,"aes67_sap_sources":len(self.sources),"aes67_last_source":self.last.source if self.last else None,
                "aes67_last_length":self.last.length if self.last else None,"aes67_last_hint":self.last.payload_hint if self.last else None,
                "aes67_last_seen":self.last.timestamp if self.last else None,"aes67_sessions":rows,"aes67_session_count":len(rows),
                "aes67_fresh_sessions":sum(1 for r in rows if r['fresh']),"aes67_sap_group":SAP_GROUP,"aes67_sap_port":SAP_PORT}

    async def stop(self):
        if self._task:self._task.cancel(); await asyncio.gather(self._task,return_exceptions=True)
        self._task=None
        if self._sock:self._sock.close()
        self._sock=None

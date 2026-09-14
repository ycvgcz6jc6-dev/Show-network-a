"""Conservative passive Dante endpoint inventory from observed mDNS/DNS-SD."""
from __future__ import annotations
from dataclasses import dataclass, field
import re,time

@dataclass
class DanteEndpoint:
    source:str; first_seen:float; last_seen:float; packets:int=0
    services:set[str]=field(default_factory=set); markers:set[str]=field(default_factory=set); names:set[str]=field(default_factory=set)

class DanteInventory:
    def __init__(self)->None:self.endpoints={}

    @staticmethod
    def _printable_hints(payload:bytes)->set[str]:
        # DNS names are label-encoded; this conservative extraction is only a
        # display hint. It never asserts authenticated identity.
        hints=set()
        for raw in re.findall(rb'[A-Za-z0-9][A-Za-z0-9_.&() +\-]{2,80}',payload):
            text=raw.decode('utf-8','ignore').strip('. ')
            if text and not text.isdigit():hints.add(text)
        return hints

    def observe(self,source,payload):
        now=time.time();item=self.endpoints.get(source)
        if item is None:item=DanteEndpoint(source,now,now);self.endpoints[source]=item
        item.last_seen=now;item.packets+=1;lower=payload.lower()
        for marker in (b'_dante',b'_netaudio',b'audinate',b'dante'):
            if marker in lower:item.markers.add(marker.decode())
        for service in (b'_http._tcp',b'_https._tcp',b'_netaudio-arc._udp',b'_netaudio-dante._udp'):
            if service in lower:item.services.add(service.decode())
        for hint in self._printable_hints(payload):
            low=hint.lower()
            if any(x in low for x in ('dante','netaudio','audinate','._udp','._tcp')) or ('.local' in low and len(hint)<80):item.names.add(hint)

    def snapshot(self):
        now=time.time();rows=[]
        for e in sorted(self.endpoints.values(),key=lambda x:x.source):
            if not e.markers and not any('netaudio' in svc for svc in e.services):continue
            age=max(0,now-e.last_seen)
            rows.append({'source':e.source,'packets':e.packets,'services':sorted(e.services),'markers':sorted(e.markers),'names':sorted(e.names)[:20],'last_seen':e.last_seen,'age_s':round(age,3),'fresh':age<20})
        return {'dante_endpoints':len(rows),'dante_fresh_endpoints':sum(1 for r in rows if r['fresh']),'dante_inventory':rows}

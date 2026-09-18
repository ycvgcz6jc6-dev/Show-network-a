"""Persistent receive-only DMX circuit feedback groups.

This is intentionally distinct from Signal Watchdogs (signal presence) and
Power Manager (active DMX output). It observes selected DMX slots and reports
OFF/ON/PARTIAL/SIGNAL_LOST without transmitting anything.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
import json
from pathlib import Path
import time
import uuid

@dataclass(slots=True)
class Circuit:
    channel: int
    name: str = ""
    on_threshold: int = 128
    off_threshold: int = 10

@dataclass(slots=True)
class CircuitGroup:
    group_id: str
    name: str
    protocol: str = "sACN"
    universe: int = 1
    source: str | None = None
    circuits: list[Circuit] = field(default_factory=list)
    enabled: bool = True

class DmxCircuitMonitor:
    def __init__(self, storage_path: str | Path, stale_s: float = 3.0) -> None:
        self.path=Path(storage_path); self.stale_s=float(stale_s); self.groups:dict[str,CircuitGroup]={}; self._observed={}
        # NOTE (audit fix): self.load() used to run here (blocking file I/O
        # directly on Home Assistant's event loop at every startup,
        # confirmed in production logs). Deferred to runtime/setup.py's
        # hass.async_add_executor_job(coordinator.dmx_circuit_monitor.load).

    def load(self):
        try: raw=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else []
        except (OSError,ValueError,TypeError): raw=[]
        for item in raw if isinstance(raw,list) else []:
            try:self.upsert(item,persist=False)
            except (ValueError,TypeError,KeyError):pass

    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps([self._public_config(g) for g in self.groups.values()],indent=2,ensure_ascii=False),encoding='utf-8'); tmp.replace(self.path)

    @staticmethod
    def _public_config(g):
        return {"group_id":g.group_id,"name":g.name,"protocol":g.protocol,"universe":g.universe,"source":g.source,"enabled":g.enabled,"circuits":[asdict(c) for c in g.circuits]}

    def upsert(self,data,persist=True):
        gid=str(data.get('group_id') or f"circuit_{uuid.uuid4().hex[:10]}"); name=str(data.get('name') or 'DMX circuits').strip()
        universe=int(data.get('universe',1));
        if universe<1 or universe>63999:raise ValueError('universe must be 1..63999')
        circuits=[]
        for row in data.get('circuits') or []:
            c=Circuit(int(row['channel']),str(row.get('name','')),int(row.get('on_threshold',128)),int(row.get('off_threshold',10)))
            if not 1<=c.channel<=512:raise ValueError('channel must be 1..512')
            if not 0<=c.off_threshold<=c.on_threshold<=255:raise ValueError('thresholds must satisfy 0 <= off <= on <= 255')
            circuits.append(c)
        if len({c.channel for c in circuits})!=len(circuits):raise ValueError('duplicate DMX channel')
        self.groups[gid]=CircuitGroup(gid,name,str(data.get('protocol') or 'sACN'),universe,str(data.get('source') or '').strip() or None,circuits,bool(data.get('enabled',True)))
        if persist:self.save()
        return self.groups[gid]

    def remove(self,gid):self.groups.pop(str(gid),None);self.save()

    def observe(self,protocol,universe,source,values):
        now=time.time(); frame=bytes(values[:512]).ljust(512,b'\0')
        for g in self.groups.values():
            if not g.enabled or g.protocol.lower()!=str(protocol).lower() or g.universe!=int(universe):continue
            if g.source and g.source!=source:continue
            self._observed[g.group_id]=(now,source,frame)

    def snapshot(self):
        now=time.time(); rows=[]
        for g in self.groups.values():
            obs=self._observed.get(g.group_id); age=(now-obs[0]) if obs else None; fresh=age is not None and age<=self.stale_s; frame=obs[2] if obs else bytes(512)
            circuits=[]; on_count=0; off_count=0
            for c in g.circuits:
                value=frame[c.channel-1]
                state='signal_lost' if not fresh else ('on' if value>=c.on_threshold else 'off' if value<=c.off_threshold else 'transition')
                on_count+=state=='on';off_count+=state=='off';circuits.append({**asdict(c),'value':value if fresh else None,'state':state})
            if not g.enabled:state='disabled'
            elif not fresh:state='signal_lost'
            elif circuits and on_count==len(circuits):state='on'
            elif circuits and off_count==len(circuits):state='off'
            elif circuits:state='partial'
            else:state='empty'
            rows.append({**self._public_config(g),'state':state,'age_s':round(age,3) if age is not None else None,'last_source':obs[1] if obs else None,'circuits':circuits})
        return {'dmx_circuit_groups':rows,'dmx_circuit_group_count':len(rows),'dmx_circuit_groups_alert':sum(1 for r in rows if r['state'] in {'partial','signal_lost'})}

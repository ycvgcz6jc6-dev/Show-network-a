"""Reference snapshots for pre-show comparison.

Stores compact, observed facts only. Comparison never guesses equivalence:
devices are matched by the stable key emitted by DeviceModel and DMX sources
by protocol/universe/source/CID.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

class ShowSnapshotManager:
    def __init__(self, config_dir: str) -> None:
        self.path = Path(config_dir) / ".storage" / "show_network_show_snapshots.json"
        self._data: dict[str, Any] = {"active": None, "snapshots": {}}
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("snapshots"), dict): self._data = raw
        except (OSError, ValueError, TypeError):
            pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _capture(data: dict) -> dict:
        devices=[]
        for d in data.get("device_model", {}).get("devices", []):
            devices.append({k:d.get(k) for k in ("id","name","ip","mac","manufacturer","model","firmware","interface","vlan","switch_name","switch_port","link_speed_mbps","protocols") if d.get(k) not in (None,"",[])})
        dmx=[]
        for row in data.get("dmx_universe_matrix", []):
            for s in row.get("sources", []):
                if s.get("active"):
                    dmx.append({"protocol":row.get("protocol"),"universe":row.get("universe"),"source":s.get("source"),"source_name":s.get("source_name"),"cid":s.get("cid"),"priority":s.get("priority"),"interface":s.get("interface")})
        ptp=data.get("protocol_rx_diagnostics",{}).get("ptp",{})
        switches=[]
        for sw in data.get("switch_telemetry", []) or []:
            ports=[]
            for port in sw.get("ports", []) or []:
                ports.append({k:port.get(k) for k in ("index","name","alias","oper_status","speed_mbps","rx_errors","tx_errors","lldp_remote_system","lldp_remote_port") if port.get(k) is not None})
            switches.append({"name":sw.get("name"),"ip":sw.get("ip"),"manufacturer":sw.get("manufacturer"),"model":sw.get("model"),"firmware":sw.get("firmware"),"ports":ports})
        managed=data.get("dante_managed",{}) or data.get("audio_network_health",{}).get("dante_managed",{}) or {}
        subscriptions=[]
        if managed.get("available"):
            for row in managed.get("subscriptions",[]) or []:
                subscriptions.append({k:row.get(k) for k in ("receiver_device","rx_channel","source_device","source_channel","status") if row.get(k) is not None})
        return {"devices":devices,"dmx_sources":dmx,"ptp":{k:ptp.get(k) for k in ("state","grandmaster_id","domain","version") if ptp.get(k) is not None},"switches":switches,"dante_subscriptions":subscriptions}

    def create(self, name: str, data: dict) -> dict:
        name=" ".join(str(name).split())[:80] or "Show"
        snap={"name":name,"created_at":datetime.now(timezone.utc).isoformat(),"reference":self._capture(data)}
        self._data["snapshots"][name]=snap; self._data["active"]=name; self._save(); return snap

    def activate(self, name: str) -> None:
        if name not in self._data["snapshots"]: raise ValueError("Unknown show snapshot")
        self._data["active"]=name; self._save()

    def delete(self, name: str) -> None:
        self._data["snapshots"].pop(name, None)
        if self._data.get("active")==name: self._data["active"]=None
        self._save()

    @staticmethod
    def _dmx_key(x): return (str(x.get("protocol")), int(x.get("universe") or 0), str(x.get("source") or ""), str(x.get("cid") or ""))
    @staticmethod
    def _device_key(x): return str(x.get("id") or x.get("mac") or x.get("ip") or "")

    def compare(self, data: dict) -> dict:
        active=self._data.get("active"); snap=self._data.get("snapshots",{}).get(active) if active else None
        if not snap: return {"state":"no_reference","active":None,"snapshots":list(self._data.get("snapshots",{})),"differences":[]}
        ref=snap["reference"]; cur=self._capture(data); diffs=[]
        rd={self._device_key(x):x for x in ref.get("devices",[]) if self._device_key(x)}; cd={self._device_key(x):x for x in cur.get("devices",[]) if self._device_key(x)}
        for k in sorted(rd.keys()-cd.keys()): diffs.append({"severity":"warning","kind":"device_missing","label":rd[k].get("name") or rd[k].get("ip") or k,"reference":rd[k]})
        for k in sorted(cd.keys()-rd.keys()): diffs.append({"severity":"info","kind":"device_new","label":cd[k].get("name") or cd[k].get("ip") or k,"current":cd[k]})
        rs={self._dmx_key(x):x for x in ref.get("dmx_sources",[])}; cs={self._dmx_key(x):x for x in cur.get("dmx_sources",[])}
        for k in sorted(rs.keys()-cs.keys()): diffs.append({"severity":"warning","kind":"dmx_source_missing","label":f"{k[0]} U{k[1]} {k[2]}","reference":rs[k]})
        for k in sorted(cs.keys()-rs.keys()): diffs.append({"severity":"info","kind":"dmx_source_new","label":f"{k[0]} U{k[1]} {k[2]}","current":cs[k]})
        rptp=ref.get("ptp") or {}; cptp=cur.get("ptp") or {}
        for field in ("grandmaster_id","domain","version"):
            if rptp.get(field) is not None and cptp.get(field) is not None and rptp[field]!=cptp[field]: diffs.append({"severity":"warning","kind":"ptp_changed","label":field,"reference":rptp[field],"current":cptp[field]})
        # Compare stable device facts only when both snapshots actually measured them.
        for k in sorted(rd.keys() & cd.keys()):
            r, c = rd[k], cd[k]
            for field in ("ip","mac","firmware","interface","vlan","switch_name","switch_port","link_speed_mbps"):
                if r.get(field) not in (None,"") and c.get(field) not in (None,"") and r.get(field) != c.get(field):
                    sev = "warning" if field in {"mac","firmware","vlan","switch_name","switch_port","link_speed_mbps"} else "info"
                    diffs.append({"severity":sev,"kind":"device_fact_changed","field":field,"label":r.get("name") or c.get("name") or k,"reference":r.get(field),"current":c.get(field)})
        def swkey(x): return str(x.get("ip") or x.get("name") or "")
        def pkey(x): return str(x.get("index") if x.get("index") is not None else x.get("name") or "")
        rsw={swkey(x):x for x in ref.get("switches",[]) if swkey(x)}; csw={swkey(x):x for x in cur.get("switches",[]) if swkey(x)}
        for sk in sorted(rsw.keys() & csw.keys()):
            rp={pkey(x):x for x in rsw[sk].get("ports",[]) if pkey(x)}; cp={pkey(x):x for x in csw[sk].get("ports",[]) if pkey(x)}
            for pk in sorted(rp.keys() & cp.keys()):
                for field in ("oper_status","speed_mbps","lldp_remote_system","lldp_remote_port"):
                    if rp[pk].get(field) is not None and cp[pk].get(field) is not None and rp[pk].get(field)!=cp[pk].get(field):
                        diffs.append({"severity":"warning","kind":"switch_port_changed","field":field,"label":f"{rsw[sk].get('name') or sk} / {rp[pk].get('name') or pk}","reference":rp[pk].get(field),"current":cp[pk].get(field)})
        def subkey(x): return (str(x.get("receiver_device") or ""),str(x.get("rx_channel") or ""),str(x.get("source_device") or ""),str(x.get("source_channel") or ""))
        rsub={subkey(x):x for x in ref.get("dante_subscriptions",[]) if any(subkey(x))}; csub={subkey(x):x for x in cur.get("dante_subscriptions",[]) if any(subkey(x))}
        # Subscription diffs are valid only if the official API was available in both captures.
        if ref.get("dante_subscriptions") and cur.get("dante_subscriptions"):
            for k in sorted(rsub.keys()-csub.keys()): diffs.append({"severity":"warning","kind":"dante_subscription_missing","label":f"{k[2]}/{k[3]} → {k[0]}/{k[1]}","reference":rsub[k]})
            for k in sorted(csub.keys()-rsub.keys()): diffs.append({"severity":"info","kind":"dante_subscription_new","label":f"{k[2]}/{k[3]} → {k[0]}/{k[1]}","current":csub[k]})
        warnings=sum(1 for x in diffs if x["severity"]=="warning")
        return {"state":"warning" if warnings else "match","active":active,"created_at":snap.get("created_at"),"snapshots":list(self._data.get("snapshots",{})),"reference_counts":{"devices":len(rd),"dmx_sources":len(rs),"switches":len(ref.get("switches",[])),"dante_subscriptions":len(ref.get("dante_subscriptions",[]))},"current_counts":{"devices":len(cd),"dmx_sources":len(cs),"switches":len(cur.get("switches",[])),"dante_subscriptions":len(cur.get("dante_subscriptions",[]))},"difference_count":len(diffs),"warning_count":warnings,"differences":diffs[:100]}

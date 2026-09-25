"""Evidence-only incident lifecycle for Show Network.

Incidents are correlations, never inferred root causes. Lifecycle state is persisted:
ACTIVE -> ACKNOWLEDGED -> RESOLVED. Auto-resolution is conservative and only
occurs when a later recovery event exists for the same evidence family.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha1
import json
from pathlib import Path


def _now(): return datetime.now(timezone.utc).isoformat()
def _epoch(ts):
    try: return datetime.fromisoformat(str(ts).replace("Z","+00:00")).timestamp()
    except Exception: return None

def _incident_id(raw):
    devs=sorted(set(raw.get("related_device_ids",[]) or []))
    basis="|".join([str(raw.get("kind") or "general"),str(raw.get("event") or "unknown"),",".join(devs)])
    return sha1(basis.encode("utf-8")).hexdigest()[:16]

class IncidentCenter:
    def __init__(self, config_dir: str | None = None):
        self.path = Path(config_dir) / ".storage" / "show_network_incidents.json" if config_dir else None
        self.state={}
        # NOTE (audit fix): this used to call self._load() right here, a
        # synchronous file read on the event loop every startup. Loading
        # now happens explicitly, off the event loop, from
        # runtime/setup.py alongside the coordinator's other
        # persisted-state loaders -- state stays empty until then.
        self.dirty = False
    def _load(self):
        if not self.path or not self.path.exists(): return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8")); self.state=raw if isinstance(raw,dict) else {}
        except Exception: self.state={}
    def _save(self):
        if not self.path: return
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(self.state,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(self.path)
    def acknowledge(self, incident_id: str, by: str | None = None):
        row=self.state.get(str(incident_id))
        if not row: raise ValueError("Unknown incident_id")
        if row.get("status") != "RESOLVED":
            row["status"]="ACKNOWLEDGED"; row["acknowledged_at"]=_now(); row["acknowledged_by"]=(by or "operator")[:100]; self._save()
        return dict(row)
    def build(self, recorder: dict, devices: dict | None = None) -> dict:
        timeline=(recorder or {}).get("timeline",[]) or []
        recoveries=[e for e in timeline if str(e.get("severity"))=="recovery"]
        # Phase C10 (rapport maître S100): "Les favoris deviennent le
        # périmètre privilégié de Doctor/Incident/History." `devices` (the
        # device_model dict) was already accepted here but never actually
        # read -- this is the first real use of it: tag which incidents
        # touch a favorited (monitor_mode='monitor') device, so a
        # dashboard/notification can surface those first without hiding
        # or dropping anything else (every incident is still built and
        # returned exactly as before).
        favorite_ids={d.get("id") for d in ((devices or {}).get("devices") or []) if d.get("monitor_mode")=="monitor"}
        incidents=[]; seen=set(); changed=False
        for raw in (recorder or {}).get("incidents", [])[-12:]:
            iid=_incident_id(raw); seen.add(iid); evs=raw.get("related_events",[]) or []
            kinds=sorted({str(e.get("kind") or "general") for e in evs}); devs=sorted(set(raw.get("related_device_ids",[]) or []))
            symptoms=[]
            for e in evs:
                label=f"{e.get('kind','general')} / {e.get('event','unknown')}"
                if label not in symptoms: symptoms.append(label)
            row=self.state.get(iid)
            if row is None:
                row={"status":"ACTIVE","first_seen":raw.get("ts") or _now(),"last_seen":raw.get("ts") or _now(),"occurrences":1,"acknowledged_at":None,"acknowledged_by":None,"resolved_at":None}
                self.state[iid]=row; changed=True
            else:
                ts=raw.get("ts")
                if ts and ts != row.get("last_seen"):
                    row["last_seen"]=ts; row["occurrences"]=int(row.get("occurrences",1))+1
                    if row.get("status")=="RESOLVED": row.update(status="ACTIVE",resolved_at=None,acknowledged_at=None,acknowledged_by=None)
                    changed=True
            # Conservative resolution: a later explicit recovery in the same family.
            at=_epoch(raw.get("ts")); candidates=[e for e in recoveries if e.get("kind") in kinds and _epoch(e.get("ts")) is not None and (at is None or _epoch(e.get("ts"))>at)]
            if candidates and row.get("status") != "RESOLVED":
                latest=max(candidates,key=lambda e:_epoch(e.get("ts")) or 0)
                row["status"]="RESOLVED"; row["resolved_at"]=latest.get("ts") or _now(); changed=True
            end=_epoch(row.get("resolved_at")) or datetime.now(timezone.utc).timestamp(); start=_epoch(row.get("first_seen"))
            duration=round(max(0,end-start),1) if start else None
            incidents.append({"id":iid,"ts":raw.get("ts"),"severity":raw.get("severity","info"),"anchor":{"kind":raw.get("kind"),"event":raw.get("event")},"symptom_count":len(evs),"families":kinds,"device_ids":devs,"favorite_related":bool(favorite_ids.intersection(devs)),"symptoms":symptoms[:12],"statement":"Événements observés dans la même fenêtre temporelle; aucune cause racine n'est déduite.",**row,"duration_s":duration})
        if changed:
            # NOTE (audit fix): build() runs synchronously inside the
            # coordinator's periodic _async_update_data() (on the event
            # loop, not in an executor) -- self._save() here used to write
            # the incidents file directly on every state change, a
            # confirmed blocking-call warning (6 occurrences in one
            # session). Just mark dirty; the coordinator saves it off the
            # event loop right after calling build().
            self.dirty = True
        counts=Counter(x["severity"] for x in incidents if x.get("status")!="RESOLVED")
        status_counts=Counter(x.get("status","ACTIVE") for x in incidents)
        favorite_active_count=sum(1 for x in incidents if x.get("favorite_related") and x.get("status")=="ACTIVE")
        return {"state":"error" if counts.get("error") else "warning" if counts.get("warning") else "ok","incident_count":len(incidents),"active_count":status_counts.get("ACTIVE",0),"acknowledged_count":status_counts.get("ACKNOWLEDGED",0),"resolved_count":status_counts.get("RESOLVED",0),"counts":dict(counts),"status_counts":dict(status_counts),"favorite_active_count":favorite_active_count,"incidents":incidents,"evidence_only":True,"root_cause_inferred":False}

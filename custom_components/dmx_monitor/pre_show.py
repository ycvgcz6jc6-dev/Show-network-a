"""Read-only pre-show readiness checks from already observed facts.

An optional operator profile can add expectations.  It never gates or blocks any
Show Network feature: it only changes the diagnostic verdict shown by Pre-Show.
"""
from __future__ import annotations
import json, os
from time import time
from .health_engine import find_high_utilization_switch_ports, SWITCH_UTIL_ERROR_PCT

class PreShowCheck:
    def __init__(self, config_dir: str | None = None):
        self.path=os.path.join(config_dir,"show_network_pre_show.json") if config_dir else None
        self.profile={"enabled":False,"name":"","expected_dmx_universes":[],"require_timecode":False,"require_dante":False,"require_ptp":False,"require_switches":False,"require_amplifiers":False,"require_projectors":False,"expected_devices":[]}
        # NOTE (audit fix, pre_show.py:18): this used to call self._load()
        # right here, a synchronous open() on the event loop every time
        # Show Network starts up (confirmed in production logs as a
        # blocking-call warning at this exact line). Loading now happens
        # explicitly, off the event loop, from runtime/setup.py alongside
        # the coordinator's other persisted-state loaders -- profile stays
        # at these defaults until then.
    def _load(self):
        if not self.path: return
        try:
            with open(self.path,"r",encoding="utf-8") as f: self.profile.update(json.load(f) or {})
        except (OSError,ValueError,TypeError): pass
    def _save(self):
        if not self.path: return
        tmp=self.path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f: json.dump(self.profile,f,ensure_ascii=False,indent=2)
        os.replace(tmp,self.path)
    def configure(self, **values):
        allowed=set(self.profile)
        for k,v in values.items():
            if k in allowed and v is not None: self.profile[k]=v
        self.profile["expected_dmx_universes"]=[int(x) for x in (self.profile.get("expected_dmx_universes") or []) if str(x).strip().isdigit()]
        self.profile["expected_devices"]=[str(x).strip() for x in (self.profile.get("expected_devices") or []) if str(x).strip()]
        self._save(); return dict(self.profile)
    def disable(self): self.profile["enabled"]=False; self._save()
    def run(self, data: dict) -> dict:
        checks=[]; prof=dict(self.profile); enabled=bool(prof.get("enabled"))
        def add(cid,title,status,detail,evidence=None,profile=False): checks.append({"id":cid,"title":title,"status":status,"detail":detail,"evidence":evidence or {},"profile_check":profile})
        snap=data.get("show_snapshot",{}) or {}
        if snap.get("state")=="no_reference": add("reference","Référence spectacle","unknown","Aucune référence active; comparaison de configuration impossible.")
        elif snap.get("warning_count",0): add("reference","Référence spectacle","fail",f"{snap.get('warning_count')} écart(s) important(s) avec la référence.",{"differences":snap.get("differences",[])[:20]})
        else: add("reference","Référence spectacle","pass","Configuration observée conforme à la référence active.")
        dmx=data.get("dmx_universes",[]) or []; active=[x for x in dmx if x.get("active") is not False]
        add("dmx","DMX / sACN / Art-Net","pass" if active else "unknown",f"{len(active)} univers/source(s) actuellement observé(s)." if active else "Aucun flux DMX actif observé; aucune attente n'est configurée ici.")
        tc=data.get("timecode",{}) or {}
        if tc.get("status")=="locked": add("timecode","Timecode","pass",f"{tc.get('transport') or 'Timecode'} verrouillé · {tc.get('text') or '—'} · {tc.get('fps') or '—'} fps.")
        elif tc.get("status")=="lost": add("timecode","Timecode","fail",f"Signal timecode précédemment observé mais perdu depuis {tc.get('age_s')} s.")
        else: add("timecode","Timecode","unknown","Aucun timecode observé; Show Network ne sait pas si un timecode est attendu pour ce spectacle.")
        dante=int(data.get("dante_sources") or 0); ptp=bool(data.get("ptp_clock_present"))
        if dante and not ptp: add("clock","Dante / PTP","fail","Dante est observé mais aucune horloge PTP fraîche n'est présente.")
        elif dante and ptp: add("clock","Dante / PTP","pass",f"{dante} source(s) Dante · horloge PTP observée.")
        else: add("clock","Dante / PTP","unknown","Aucune source Dante observée; ce contrôle ne peut pas conclure.")
        switches=data.get("switch_telemetry",[]) or []
        bad=[p for p in find_high_utilization_switch_ports(switches) if p["severity"]=="error"]
        add("network","Réseau / switches","fail" if bad else "pass" if switches else "unknown",f"{len(bad)} port(s) >={SWITCH_UTIL_ERROR_PCT:.0f} %." if bad else f"{len(switches)} switch(es) supervisé(s), aucun port critique." if switches else "Aucune télémétrie switch disponible.")
        amps=data.get("audio_amplifiers",[]) or []
        def amp_fault(a):
            # AudioAmplifierInventory exposes explicit online/error fields. Do not
            # rely on legacy health/state keys or turn an unknown field into OK.
            if a.get("online") is False:
                return True
            err=str(a.get("error") or "").strip().lower()
            return bool(err and err not in {"ok","normal","none","0","false"})
        amp_bad=[a for a in amps if amp_fault(a)]
        add("amps","Amplificateurs","fail" if amp_bad else "pass" if amps else "unknown",f"{len(amp_bad)} ampli(s) hors ligne/en défaut explicite." if amp_bad else f"{len(amps)} ampli(s) observé(s), aucun défaut explicite." if amps else "Aucun ampli supervisé.",{"faults":[{"key":a.get("key"),"host":a.get("host"),"online":a.get("online"),"error":a.get("error")} for a in amp_bad[:20]]})
        projs=data.get("projectors",[]) or []; proj_bad=[p for p in projs if str(p.get("health") or p.get("state") or "").lower() in {"error","fault","offline"}]
        add("video","Projecteurs","fail" if proj_bad else "pass" if projs else "unknown",f"{len(proj_bad)} projecteur(s) en défaut." if proj_bad else f"{len(projs)} projecteur(s) observé(s), aucun défaut explicite." if projs else "Aucun projecteur supervisé.")
        # Optional profile expectations. They add diagnostics only; never gates/actions.
        if enabled:
            observed_u={int(x.get("universe")) for x in active if str(x.get("universe","")).isdigit()}
            exp_u=set(prof.get("expected_dmx_universes") or []); missing=sorted(exp_u-observed_u)
            if exp_u: add("profile_dmx","Profil · Univers attendus","fail" if missing else "pass",f"Univers manquants: {', '.join(map(str,missing))}" if missing else f"{len(exp_u)} univers attendu(s) présent(s).",{"expected":sorted(exp_u),"observed":sorted(observed_u)},True)
            requirements=(("require_timecode","profile_timecode","Profil · Timecode",tc.get("status")=="locked"),("require_dante","profile_dante","Profil · Dante",dante>0),("require_ptp","profile_ptp","Profil · PTP",ptp),("require_switches","profile_switches","Profil · Switches",bool(switches)),("require_amplifiers","profile_amps","Profil · Amplificateurs",bool(amps)),("require_projectors","profile_video","Profil · Projecteurs",bool(projs)))
            for key,cid,title,ok in requirements:
                if prof.get(key): add(cid,title,"pass" if ok else "fail","Attente du profil satisfaite." if ok else "Attente du profil non observée.",profile=True)
            expected=[x.lower() for x in prof.get("expected_devices",[])]; model=(data.get("device_model",{}) or {}).get("devices",[]) or []
            hay=[]
            for d in model:
                hay.append(" ".join(str(d.get(k) or "") for k in ("name","ip","mac","serial","manufacturer","model")).lower())
            miss=[x for x in expected if not any(x in h for h in hay)]
            if expected: add("profile_devices","Profil · Équipements attendus","fail" if miss else "pass",f"Absent(s): {', '.join(miss)}" if miss else f"{len(expected)} équipement(s) attendu(s) observé(s).",{"expected":expected},True)
        statuses=[c["status"] for c in checks]; state="NOT_READY" if "fail" in statuses else "READY" if "unknown" not in statuses else "CHECK"
        return {"generated_at":round(time(),3),"state":state,"counts":{s:statuses.count(s) for s in ("pass","fail","unknown")},"checks":checks,"read_only":True,"unknown_is_not_pass":True,"profile":prof,"profile_enabled":enabled,"profile_optional":True,"blocking":False}

"""On-demand/read-only Show Network Doctor.

Checks only facts present in the current coordinator snapshot. No probing and
no control command is performed here.
"""
from __future__ import annotations
from time import time
from .health_engine import find_high_utilization_switch_ports, SWITCH_UTIL_WARNING_PCT, SWITCH_UTIL_ERROR_PCT

class ShowNetworkDoctor:
    def run(self, data: dict) -> dict:
        checks=[]
        def add(cid, title, status, detail, evidence=None):
            checks.append({"id":cid,"title":title,"status":status,"detail":detail,"evidence":evidence or {}})
        interfaces=data.get("network_interfaces", []) or []
        up=sum(1 for x in interfaces if x.get("is_up") is True or x.get("up") is True)
        add("interfaces","Interfaces réseau","ok" if up else "warning", f"{up}/{len(interfaces)} interface(s) explicitement active(s)", {"total":len(interfaces),"up":up})
        dmx=data.get("dmx_universes", []) or []
        groups={}
        for x in dmx: groups.setdefault((x.get("protocol"),x.get("universe")),set()).add(x.get("source"))
        multi=[{"protocol":k[0],"universe":k[1],"sources":sorted(s for s in v if s)} for k,v in groups.items() if len({s for s in v if s})>1]
        add("dmx_sources","Sources DMX","warning" if multi else "ok", f"{len(multi)} univers avec plusieurs sources" if multi else f"{len(groups)} univers observé(s), aucune multi-source détectée", {"multi_source":multi})
        loss=[{"universe":x.get("universe"),"source":x.get("source"),"loss_pct":x.get("sequence_loss_pct")} for x in dmx if isinstance(x.get("sequence_loss_pct"),(int,float)) and x.get("sequence_loss_pct")>1]
        add("dmx_sequence","Séquences DMX","warning" if loss else "ok", f"{len(loss)} flux avec >1% de perte de séquence" if loss else "Aucune perte >1% observée", {"streams":loss})
        topo=data.get("topology",{}) or {}; stale=[n for n in topo.get("nodes",[]) if n.get("health")=="stale"]
        add("topology","Topologie","warning" if stale else "ok", f"{len(stale)} nœud(s) stale" if stale else f"{len(topo.get('nodes',[]))} nœud(s), aucun stale", {"stale":[n.get("id") for n in stale]})
        model=data.get("device_model",{}) or {}; conflicts=model.get("conflicts",[]) or []
        add("identity","Identités équipements","warning" if conflicts else "ok", f"{len(conflicts)} conflit(s) d'identité" if conflicts else f"{model.get('count',0)} équipement(s) consolidé(s), aucun conflit stable", {"conflicts":conflicts})
        # Phase C10 (rapport maître S100): "Les favoris deviennent le
        # périmètre privilégié de Doctor/Incident/History, sans limiter
        # la découverte globale." monitor_mode ('monitor' = star/favorite,
        # set via the inventory's own ☆/★ toggle) used to be stored and
        # displayed but never actually read anywhere -- this is the first
        # place that gives it real effect: a dedicated check surfacing
        # favorited-equipment health specifically, on top of (not instead
        # of) every other check here, which still covers the whole
        # inventory exactly as before.
        favorites=[d for d in (model.get("devices") or []) if d.get("monitor_mode")=="monitor"]
        if favorites:
            routes_by_ip={r.get("target"):r for r in (data.get("network_routes") or [])}
            now_ts=time()
            stale=[{"id":d.get("id"),"name":d.get("name"),"age_s":round(now_ts-d["last_seen"],1)}
                   for d in favorites if isinstance(d.get("last_seen"),(int,float)) and (now_ts-d["last_seen"])>300]
            unreachable=[{"id":d.get("id"),"name":d.get("name"),"ip":d.get("ip")}
                        for d in favorites if d.get("ip") and routes_by_ip.get(d["ip"]) and not routes_by_ip[d["ip"]].get("reachable")]
            status="error" if unreachable else "warning" if stale else "ok"
            detail=(f"{len(favorites)} favori(s) · {len(stale)} silencieux depuis >5min · {len(unreachable)} sans route réseau"
                    if stale or unreachable else f"{len(favorites)} favori(s), tous à jour et joignables")
            related_ids=sorted({x["id"] for x in stale+unreachable if x.get("id")})
            add("favorites","Équipements favoris (★)",status,detail,
                {"favorites_total":len(favorites),"stale":stale,"unreachable":unreachable,"related_device_ids":related_ids})
        else:
            add("favorites","Équipements favoris (★)","info","Aucun équipement marqué favori — Doctor couvre tout le périmètre de façon égale",{"favorites_total":0})
        switches=data.get("switch_telemetry",[]) or []
        port_errors=[]
        for sw in switches:
            for port in sw.get("ports",[]) or []:
                rx=port.get("rx_errors"); tx=port.get("tx_errors")
                if (isinstance(rx,(int,float)) and rx>0) or (isinstance(tx,(int,float)) and tx>0):
                    port_errors.append({"switch":sw.get("name") or sw.get("ip"),"ip":sw.get("ip"),"port_index":port.get("index"),"port_name":port.get("name"),"rx_errors":rx,"tx_errors":tx})
        add("switch_ports","Ports réseau","warning" if port_errors else "ok", f"{len(port_errors)} port(s) avec compteur d'erreurs non nul" if port_errors else f"{sum(len(sw.get('ports',[]) or []) for sw in switches)} port(s) supervisé(s), aucun compteur d'erreurs non nul", {"ports":port_errors[:50]})
        high_util=find_high_utilization_switch_ports(switches)
        add("audio_bandwidth","Bande passante audio/réseau","error" if any(x["severity"]=="error" for x in high_util) else "warning" if high_util else "ok", f"{len(high_util)} port(s) >={SWITCH_UTIL_WARNING_PCT:.0f}%" if high_util else f"Aucun port mesuré >={SWITCH_UTIL_WARNING_PCT:.0f}%", {"ports":high_util[:50],"warning_pct":SWITCH_UTIL_WARNING_PCT,"critical_pct":SWITCH_UTIL_ERROR_PCT})
        ptp=data.get("protocol_rx_diagnostics",{}).get("ptp",{}) or {}; ptp_state=str(ptp.get("state","")).lower()
        dante_sources=int(data.get("dante_fresh_sources") or 0)
        dante_sources_seen=int(data.get("dante_sources") or 0)
        ptp_present=bool(data.get("ptp_clock_present"))
        ptp_status="error" if dante_sources and not ptp_present else "warning" if ptp_state in {"error","fault","degraded","stale"} else "ok" if ptp_present or ptp_state not in {"","disabled_or_unavailable"} else "info"
        add("ptp","PTP / Clock","%s" % ptp_status, "Dante observé mais aucune horloge PTP fraîche" if dante_sources and not ptp_present else f"État observé: {ptp.get('state','indisponible')} · clock {'présente' if ptp_present else 'non observée'}", {"state":ptp.get("state"),"clock_present":ptp_present,"dante_fresh_sources":dante_sources,"dante_sources_seen":dante_sources_seen,"grandmaster":data.get("ptp_active_grandmaster_identity"),"last_grandmaster_seen":data.get("ptp_grandmaster_identity")})
        host=data.get("host_metrics",{}) or {}; cpu=host.get("cpu_percent"); mem=host.get("memory_percent")
        overloaded=(isinstance(cpu,(int,float)) and cpu>=90) or (isinstance(mem,(int,float)) and mem>=90)
        add("host","Hôte Home Assistant","warning" if overloaded else "ok", f"CPU {cpu if cpu is not None else '?'}% · RAM {mem if mem is not None else '?'}%", {"cpu_percent":cpu,"memory_percent":mem})
        health=data.get("show_network_health",{}) or {}; add("health_engine","Health Engine", "warning" if health.get("overall") in {"warning","error"} else "ok", f"État global: {health.get('overall','unknown')}", {"summary":health.get("summary")})
        fr=(data.get("archive",{}) or {}).get("flight_recorder",{}) or {}; incident=fr.get("last_incident")
        if incident:
            related=incident.get("related_device_ids",[]) or []
            add("flight_recorder","Flight Recorder", incident.get("severity") if incident.get("severity") in {"warning","error"} else "info",
                f"Dernier incident: {incident.get('kind','general')} / {incident.get('event','unknown')} · {len(related)} équipement(s) relié(s) par preuve",
                {"ts":incident.get("ts"),"kind":incident.get("kind"),"event":incident.get("event"),"related_device_ids":related,"related_kinds":incident.get("related_kinds",[])})
        else:
            add("flight_recorder","Flight Recorder","ok","Aucun incident warning/error présent dans la fenêtre mémoire", {"events_total":fr.get("events_total",0)})
        counts={s:sum(1 for c in checks if c["status"]==s) for s in ("ok","info","warning","error")}
        overall="error" if counts["error"] else "warning" if counts["warning"] else "ok"
        return {"generated_at":round(time(),3),"overall":overall,"counts":counts,"checks":checks,"read_only":True}

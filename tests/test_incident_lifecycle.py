from custom_components.dmx_monitor.incident_center import IncidentCenter

def test_incident_ack_recovery_and_recurrence(tmp_path):
    c=IncidentCenter(str(tmp_path))
    raw={"ts":"2026-09-18T20:00:00+00:00","severity":"error","kind":"ptp","event":"clock_lost","related_events":[{"ts":"2026-09-18T20:00:00+00:00","kind":"ptp","event":"clock_lost","severity":"error","data":{}}]}
    rec={"incidents":[raw],"timeline":raw["related_events"]}
    out=c.build(rec,{})
    i=out["incidents"][0]; assert i["status"]=="ACTIVE"
    c.acknowledge(i["id"],"regie")
    assert c.build(rec,{})["incidents"][0]["status"]=="ACKNOWLEDGED"
    rec["timeline"].append({"ts":"2026-09-18T20:01:00+00:00","kind":"ptp","event":"clock_recovered","severity":"recovery","data":{}})
    assert c.build(rec,{})["incidents"][0]["status"]=="RESOLVED"
    raw2=dict(raw); raw2["ts"]="2026-09-18T20:02:00+00:00"; rec["incidents"]=[raw2]
    i2=c.build(rec,{})["incidents"][0]
    assert i2["status"]=="ACTIVE" and i2["occurrences"]>=2

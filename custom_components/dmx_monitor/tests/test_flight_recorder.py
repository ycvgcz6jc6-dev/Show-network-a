from custom_components.dmx_monitor.flight_recorder import analyze, classify


def test_classification_and_correlation():
    events = [
        {"ts":"2026-09-18T18:00:00+00:00","kind":"ptp","event":"activity_change","data":{"value":1}},
        {"ts":"2026-09-18T18:00:05+00:00","kind":"dmx","event":"source_lost","data":{"universe":10}},
        {"ts":"2026-09-18T18:00:09+00:00","kind":"dmx","event":"source_recovered","data":{"universe":10}},
    ]
    out = analyze(events, window_s=10)
    assert classify(events[1]) == "error"
    assert out["last_incident"]["event"] == "source_lost"
    assert out["last_incident"]["related_count"] == 3
    assert set(out["last_incident"]["related_kinds"]) == {"ptp", "dmx"}


def test_does_not_claim_root_cause():
    out = analyze([{"ts":"2026-09-18T18:00:00+00:00","kind":"dmx","event":"cid_change","data":{}}])
    assert "cause" in out["explanation"].lower()
    assert out["incidents"][0]["severity"] == "warning"

# Show Network — test suite

## Running

```bash
pip install -r tests/requirements_test.txt
pytest tests/ -v
```

## What's covered, and honestly, what isn't yet

Every test file below was written against the **real, current** source in
`custom_components/dmx_monitor/`, and every individual test's assertions
were manually executed (bypassing the package import, since this project
was developed in a sandbox with no network access to install `pytest` or
`homeassistant`) and confirmed passing before being committed to these
files. They have **not** been run through an actual `pytest` invocation —
do that before trusting them blindly, the same way any new test suite
should be verified once before being relied on.

| File | Needs Home Assistant installed? | Covers |
|---|---|---|
| `test_security.py` | No (import-only) | Password gate: never auto-unlocks on restart, brute-force lockout, IP allowlist, redaction, archive-limit clamping |
| `test_archive.py` | No | Global archive quota (not just per-file), ZIP export cap, rotation filename collisions, dropped-event/error counters |
| `test_attribute_bounds.py` | No | Entity attributes never exceed HA Recorder's 16384-byte limit (500-device scenario, matching the audit's own acceptance criterion) |
| `test_services_common.py` | No | `entry_id` resolution never silently guesses when multiple config entries exist |
| `test_artnet_discovery.py` | No | ArtPoll/ArtPollReply parsing against real packet bytes, multi-manufacturer identification, console/node classification |
| `test_ma3_web_remote_proxy.py` | No | RFC 6455 frame encode/decode, `Sec-WebSocket-Accept` against the official RFC test vector, HTML/JS content rewriting (the actual mixed-content fix) |
| `test_video_ip_preview.py` | No | Preview stream max-duration cap and idle-timeout, including the exact stalled/infinite-source scenarios |
| `test_config_flow_osc_port.py` | No (imports config_flow.py's pure functions directly) | OSC port pre-flight check, including the "re-saving unchanged options must not false-positive against the entry's own listener" case |
| `test_ma3_web_remote_view_ssrf.py` | No | The SSRF fix: `station_ip` must be a real, already-observed MA-Net3 station, not an arbitrary caller-supplied address |

**Not yet written**, and genuinely needing `pytest-homeassistant-custom-component`'s
full fixtures (`hass`, `MockConfigEntry`, `enable_custom_integrations`) to
do properly rather than a hand-rolled fake:

- Full config flow / options flow round-trip (`async_step_user`, `async_step_init`) through Home Assistant's real flow manager
- All ~80 registered services actually registering and being callable
- `async_setup_entry` / `async_unload_entry` lifecycle (does everything start and stop cleanly, including with hardware/network dependencies absent)
- Entity registration counts and unique_id stability across a reload

These are exactly the audit's own list (Z-10) beyond what's covered above.
They were left for a follow-up pass rather than written blind against a
testing framework this sandbox couldn't install and therefore couldn't
validate even once — a test that was never run is not meaningfully safer
than no test at all, and the honest thing is to say so rather than ship
a plausible-looking file with unknown correctness.

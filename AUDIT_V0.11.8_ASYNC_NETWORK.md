# AUDIT v0.11.8 — Async flow / network-load optimization

## Scope

This release optimizes high-rate asynchronous network paths and persistence, and prepares the same bounded-flow discipline for the dormant Power Manager. No live Home Assistant, physical DMX, Dante, AES70 or ENTTEC hardware test was performed in this environment.

## 🟢 Implemented and connected

- `LatestValuePipeline`: bounded pending/latest state, one asyncio worker, coalescing metrics, bounded completed-key memory.
- sACN/Art-Net receiver: latest packet slots keyed by source/universe prevent stale-frame queue growth during bursts. Packet counters and watchdog observation remain separate from the coalesced state path.
- Dante: monitor groups share one socket per UDP monitor port instead of one socket/task per group+port.
- MA-Net3: multicast groups share one UDP socket/async transport.
- AES70: bounded concurrent polling via `AsyncGate`; optional validated IP/CIDR source filtering.
- OSC receiver: optional validated IP/CIDR source filtering.
- Rule and DMX→HA mapping stores: identical payloads are not rewritten; writes remain atomic via temporary file replacement.
- Power Manager: isolated `PowerOutputPipeline` coalesces latest 512-byte frame and uses one worker. It remains disabled and opens no network/serial resource.

## 🟡 Intentionally not claimed as live validation

- Actual HA event-loop latency under sustained production-rate traffic.
- Actual multicast reception on the user's VLANs.
- Actual Dante/AES70 device responses.
- Actual ENTTEC hardware output.
- Actual sACN/Art-Net transmission by Power Manager.

## Validation

- `python -m compileall -q custom_components tests` → PASS
- `pytest -q` → **44 passed**
- Manifest/const version → **0.11.8**
- Power Manager remains `ENABLED = False`.
- No venue-specific IP/VLAN/device data added.

## Notes

The IP allowlist helpers are deliberately additive and backward-compatible when no allowlist is configured. They are not presented as a substitute for HA authentication or network segmentation.

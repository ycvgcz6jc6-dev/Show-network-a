# Show Network v0.11.2 — Phase 5

## Scope
Reliability, bounded-memory hardening, security hardening and runtime observability, while preserving the Node-RED lessons and existing functional scope.

## 🟢 Implemented and connected
- `LatestValuePipeline` now bounds both pending keys **and completed/latest-value keys**; long-running discovery or protocol streams cannot grow `_last` without limit.
- `RuntimeStateStore` now has a configurable key bound in addition to its bounded history.
- Added HA-independent `RuntimeMetrics` for received/processed/dropped/coalesced/error counters and uptime snapshots.
- Security password storage path handling is deterministic for both a directory and an explicit `.json` file.
- Security verification now tolerates malformed persisted salt/digest data without crashing.
- Added a 5-failure / 30-second temporary lockout to the secondary active-control password gate.
- Password reset clears temporary lockout state.
- Existing active-control gate remains intact; Home Assistant remains the primary access-control layer.

## 🟢 Validation
- Full pytest suite: **33 passed**.
- `python -m compileall`: PASS.
- ZIP integrity: PASS.
- No Home Assistant runtime, live network, DMX, Dante, MIDI, OSC or hardware test is claimed.

## 🟡 Catalogue/documentation
- `RuntimeMetrics` is an internal observability primitive; it does not claim that physical equipment is present.
- Existing manufacturer/vendor data remains descriptive unless backed by live evidence.

## 🔴 Removed
- Nothing functional removed in Phase 5.

## Node-RED principles retained
1. Packet reception stays cheap.
2. Latest-value coalescing remains bounded.
3. High-rate sources do not spawn one downstream task per packet.
4. Backpressure/drop behaviour remains explicit.
5. Blocking I/O stays outside the HA event loop.
6. State and telemetry memory now have explicit bounds.

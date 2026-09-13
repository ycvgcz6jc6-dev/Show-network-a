# Show Network v0.11.1 — Phase 3 + Phase 4

## Baseline

Derived from the corrected v0.11.0 modularized release. Existing useful work was preserved, including the Node-RED-inspired bounded flow model, receive-only protocol posture, security gates, zones, mappings, rules, backups and passive vendor discovery.

## Phase 3 — protocol/runtime isolation

### 🟢 Implemented and connected
- Added a canonical `protocols/catalog.py` adapter registry for DMX network, ENTTEC, MA-Net3, OSC, MIDI, Dante, AES67, PTP, ST2110, AVB and PunchLight.
- Runtime composition now resolves protocol constructors through that registry.
- Adapter metadata explicitly records category, receive-only policy and blocking policy.
- Blocking operations remain off the HA event loop: mDNS scans and MIDI opening use `asyncio.to_thread`; PJLink polling uses an executor; the existing SNMP worker boundary is retained.
- No venue-specific IPs, VLANs, names, devices or credentials were introduced.

### 🟡 Catalogue/documentation
- The adapter catalogue is an architectural registry; it does not imply that any protocol is physically present or reachable.
- Live hardware capability remains evidence-driven.

### 🔴 Removed
- No functional protocol was removed in Phase 3.

## Phase 4 — Home Assistant boundary

### 🟢 Implemented and connected
- Added HA-independent `ProtocolObservation` and `ServiceAction` contracts.
- Added bounded `RuntimeStateStore`.
- Extracted the HA action queue/worker from the coordinator into `HAActionDispatcher`.
- DMX mappings, DMX zones, control mappings and rule actions now feed the same bounded dispatcher.
- Zone coalescing and optional 10 Hz pacing are preserved.
- Coordinator no longer owns a raw HA action queue or action worker implementation.
- Package import is now HA-lazy, making isolated unit/static testing possible without a Home Assistant installation.
- Added architecture regression tests.

### Compatibility fixes caught by full test execution
- `AudioHealth.snapshot()` accepts the historical positional form as well as keyword arguments.
- Rule hysteresis now uses a strict OFF boundary when an explicit `threshold_off` is configured, matching the intended transition semantics.
- Zone tests/documentation reflect the deliberate one-service-call-per-zone batching model.

### 🟡 Catalogue/documentation
- Runtime state store is the normalized boundary for future entity/API consumers; existing coordinator data remains compatible.

### 🔴 Removed
- Direct coordinator-owned HA action queue and worker implementation. The behavior was moved, not discarded.

## Node-RED lessons retained

1. Receive every packet cheaply.
2. Keep watchdog observation at packet rate.
3. Coalesce high-rate state before slower consumers.
4. Bound queues.
5. Apply backpressure/drop policy explicitly.
6. Pace expensive downstream HA actions.
7. Keep blocking I/O out of the event loop.

## Validation

- `python -m compileall` — PASS.
- Full pytest suite — **28 passed**.
- Architecture regression tests — included and passing.
- Service YAML/registration audit remains 43/43 from Phase 1.
- No real Home Assistant instance was available in this environment.
- No live DMX, sACN, Art-Net, Dante, MIDI, OSC, Green-GO, ELC, PunchLight, projector or switch hardware test is claimed.

## Final classification

- 🟢 Phase 3/4 architecture and runtime boundaries implemented.
- 🟡 Hardware/vendor catalogues remain descriptive unless backed by live evidence.
- 🔴 Only duplicate ownership of HA action execution was removed; no useful protocol feature was removed.

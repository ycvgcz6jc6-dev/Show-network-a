# Show Network v0.11.0 — Phase 1 + Phase 2 audit

## Baseline

This release is derived from the corrected v0.10.92 baseline. It keeps the
useful runtime and Node-RED-inspired flow work already present and changes the
architecture around it rather than replacing it wholesale.

## Phase 1 — runtime modularisation

### 🟢 Implemented and connected

- HA entry point reduced to lifecycle/orchestration (`__init__.py`).
- Runtime composition moved to `runtime/setup.py`.
- Protocol implementations exposed through a stable `protocols/` adapter
  boundary without changing their established implementation modules.
- Service handlers split into 12 responsibility-focused modules under
  `services/`.
- Shared multi-entry coordinator resolution centralized in `services/common.py`.
- Existing `ResourceRegistry` remains the owner of protocol lifecycle and
  shutdown.
- Existing bounded latest-value DMX flow, rate limiting and bounded HA action
  queue are preserved.
- Existing executor/thread isolation for blocking operations is preserved.
- A Python 3.13 dataclass compatibility defect in `DmxAction` was corrected
  (`service` is now a required field before optional `entity_id`).

### 🟡 Catalogue/documentation only

- `ARCHITECTURE.md` documents the runtime contract and the preserved design
  choices.
- Existing protocol modules are not all physically moved into new directories;
  the adapter package provides the boundary first, reducing migration risk.

### 🔴 Removed

- The old monolithic service-registration module was removed after its handlers
  were split into responsibility modules.
- No protocol implementation was removed as part of Phase 1 merely for size.

## Phase 2 — data/profile modularisation

### 🟢 Implemented and connected

Static catalogues are now YAML-backed and validated at load time:

- `data/switches.yaml`
- `data/fixtures.yaml`
- `data/spectacle_profiles.yaml`
- `data/osc_profiles.yaml`
- `data/midi_profiles.yaml`
- `data/manufacturers.yaml`

Typed Python dataclasses remain as the runtime API, so existing consumers do
not have to be rewritten just because the data moved out of Python source.

### 🟡 Catalogue/documentation only

The catalogues describe capabilities and setup hints; they do not imply live
control or vendor probing. Evidence level remains part of the design.

### 🔴 Removed

- Repeated version-specific changelog files were consolidated into one root
  `CHANGELOG.md`.
- No SQL/database layer was introduced: static catalogue data does not need a
  database.

## Validation performed

- `python -m compileall` — **PASS**.
- Service YAML ↔ registrations — **43/43 match**.
- Independent catalogue/architecture tests — **7 passed**.
- ZIP integrity — to be verified on the final release archive.

## What was not claimed

- No real Home Assistant instance was executed here because the validation
  environment does not contain the `homeassistant` Python package.
- No live DMX, sACN, Art-Net, Dante, MIDI, OSC, Green-GO, ELC, PunchLight or
  projector hardware test was claimed.
- The user's own network, VLANs, IP addresses, equipment names and devices were
  not embedded in the generic integration.

## Preserved lessons from earlier iterations

The architecture explicitly retains the useful patterns learned from the
Node-RED-oriented pass: bounded queues, latest-value coalescing, deadband,
backpressure, event-loop-safe worker tasks, and separation between high-rate
reception and slower Home Assistant actions.

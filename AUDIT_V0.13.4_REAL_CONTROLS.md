# Audit v0.13.4 — Real controls and visible data paths

## Scope

This release follows the real HA tests of v0.13.3. It targets UI controls that were inert/decorative and one confirmed DMX data-path gap. It does **not** claim hardware validation.

## 🟢 Implemented and connected

- DMX channel payload: `UniverseObservation.values` is published as base64 in `dmx_universes`; the existing DMX panel already decodes `values_b64`. This closes the backend → HA sensor → frontend value path.
- Module gates: a single `dmx_monitor.set_module_enabled` service updates only allow-listed boolean ConfigEntry options. Existing OptionsFlow reload applies the change.
- Quick gates exposed for Art-Net, sACN, MA-Net3, OSC, MIDI, PunchLight, watchdog, HA Builder, PJLink monitoring and diagnostic tests.
- OSC Learn: the pre-existing `OSCLearnSession` is now attached to `OSCReceiver`; Start/Stop/Clear services are registered and the panel renders observed suggestions.
- OSC mapping panel: removed fixed `/show/lobby/...` examples and displays stored mappings. Create/remove buttons call the real mapping services.
- Fixed `services/control.py` imports that incorrectly targeted modules inside the `services` package.
- Journal module now mounts a real panel. EventArchive keeps a bounded in-memory preview of the latest 100 recorded events and exposes them through the journal sensor. Timeline and Journal render those events.
- Diagnostic simulation buttons show action/error feedback and are disabled behind an explicit `chaos_enabled` gate until the user enables diagnostic tests.
- PJLink monitoring can be enabled/disabled separately from the security-protected projector command gate.

## 🟡 Still diagnostic / not claimed complete

- MA-Net3 station/raw-source reception remains passive. Session index/name decoding is **not** claimed implemented in this release because the current listener does not have a validated MA session-metadata decoder. A node that emits no packet on the listened MA-Net3 groups may still be absent.
- OSC output remains protected by Show Network security and its explicit output gate; this release does not bypass either.
- Archive export still creates a server-side ZIP; this release improves visible journal events but does not add an HTTP download endpoint.

## 🔴 Removed / no longer presented as live

- Decorative OSC mapping examples are removed from the operational mapping panel.
- Diagnostic buttons are no longer presented as silently usable when diagnostic tests are disabled.

## Validation

- `python -m compileall -q custom_components`: OK
- `node --check custom_components/dmx_monitor/static/show-network.js`: OK
- `pytest -q`: 108 passed

No real Home Assistant, MA hardware, sACN source, OSC device or projector was available to this build environment.

# Audit v0.13.2 — Protocol RX diagnostics

## Scope

This release is intentionally limited to passive receive diagnostics for Art-Net, sACN, MA-Net3 and mDNS visibility. It does not add control/transmit behavior and it does not claim end-to-end hardware validation.

## Implemented

- Art-Net listener: enabled/state/interface/UDP 6454 bind, packet counters, parsed counters, last source, last universe, last packet timestamp, restarts and last error.
- sACN listener: same diagnostics plus requested multicast universe groups, successfully joined groups and join errors.
- MA-Net3 listener: state/interface/UDP 30020 bind, configured/joined multicast groups, join errors, packet count, last source and last packet timestamp.
- Coordinator publishes a single `protocol_rx_diagnostics` data tree.
- HA sensor exposes that tree in attributes with a scalar state.
- MA sensor attributes now expose `ma_remote`; this repairs a real frontend/backend wiring gap that could leave the MA page empty even if backend observations existed.
- Discovery status now reports mDNS scan state and explanatory detail for zero-result scans.
- DMX, MA and Discovery panels show these diagnostics directly.

## Validation performed

- `python -m compileall -q custom_components`: PASS
- `node --check custom_components/dmx_monitor/static/show-network.js`: PASS
- `pytest -q`: 96 passed

These are static/unit validations only. No real Home Assistant, multicast network, grandMA3 station, sACN source or Art-Net source was available in this build environment. The next real test must inspect the new counters/states on the user's Home Assistant.

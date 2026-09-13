# Show Network v0.11.6 — pre-test audit

## Power Manager

The future Power Manager is isolated from the monitoring runtime and remains disabled.

Supported future output contracts:
- sACN network output
- Art-Net network output
- ENTTEC USB/serial output

The current release sends no DMX from this feature, opens no network/serial output, registers no Power Manager HA service, and exposes no Power Manager dashboard control.

The model supports a dedicated universe, per-channel ON/OFF values, independent ON/OFF delays, and sequenced presets. The output transport is explicitly separate from the receive-only DMX monitoring path.

## Dashboard / route audit

- All custom card types referenced by the supplied dashboards resolve to an element defined by `show-network.js`.
- Corrected stale aliases `topology-panel` and `rule-builder` to their actual custom element names.
- The versioned frontend resource points to `show-network.js?v=0.11.6`.

## Service audit

- 43 service definitions in `services.yaml`.
- 43 corresponding runtime registrations found.
- No unlisted runtime registrations.

## Automated validation

- pytest: **39 passed**
- Python compilation: checked during release build
- Power Manager output choices: sACN / Art-Net / ENTTEC
- No venue-specific network addresses, VLANs or credentials added.

## Scope boundary

This is a code/static validation only. No live Home Assistant instance, DMX gateway, ENTTEC interface, sACN receiver, Art-Net receiver, or electrical power hardware was exercised in this environment.

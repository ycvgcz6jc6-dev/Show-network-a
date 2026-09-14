# Show Network v0.13.0 — Data truth repair

This release is based on the real Home Assistant audit of 2026-09-14.

## Green — implemented/connected
- Sensor constructor accepts `(key, name, unit)` catalogue tuples.
- Missing topology, mappings and archive attributes are exported.
- Network capacity branch ordering corrected.
- Synthetic DMX live component removed.
- DMX monitor lists configured universes even without traffic and distinguishes configured/silent/live.
- Observed DMX selection is keyed by protocol + universe + source instead of universe number alone.
- Network configuration shows unavailable rather than inventing disabled states when the config sensor is absent.

## Yellow — not certified by this package build
- Real Art-Net/sACN packet reception, MA-Net3, Dante/PTP and physical hardware paths require Home Assistant/hardware retest.
- Security, OSC learn/mapping, HA Builder, detailed archives download and other modules still require the later audit steps.

## Red — removed
- `dmx-live-view` synthetic demonstration values and its misleading LIVE RECEIVE presentation.

## Validation
Static/unit/syntax validation only. Real HA validation must be performed after installing v0.13.0.

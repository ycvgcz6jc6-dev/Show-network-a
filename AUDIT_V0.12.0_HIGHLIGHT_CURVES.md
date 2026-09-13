# Show Network v0.12.0 — DMX→HA Highlight & Dimmer Curves Audit

## Implemented
- DMX→Home Assistant mappings expose selectable dimmer curves: linear, gamma 1.8/2.0/2.2/2.4, logarithmic, DALI-like logarithmic approximation, S-curve.
- Curve processing is local to the mapping/zone conversion path; it does not alter received DMX data.
- Mapping panel exposes HIGHLIGHT and RESTORE controls.
- Highlight snapshots the current HA light state/attributes, temporarily turns the mapped light on at full brightness (and white when RGB-capable), and restores the previous state when disabled.
- Highlight is an explicit HA action and remains subject to the existing light-sync safety gate at the DMX mapping execution boundary.
- Mapping sensor now exposes mapping definitions to the frontend panel.

## Validation
- Pytest: 48 passed.
- Python compilation: OK.
- JSON/YAML parsing: OK.
- Service YAML ↔ registered services: exact match (44 services).
- Dashboard custom-card references: all 16 used custom cards are defined; no missing card reference.
- Static dead-marker scan: TODO / FIXME / NotImplemented / IMPLEMENT_ME = 0.
- No live Home Assistant, Hue Bridge, DALI gateway, or physical-light test was performed in this environment.

## Note on DALI
`dali_log` is explicitly a DALI-like logarithmic brightness approximation for DMX→HA brightness conversion. It is not a claim of implementing the DALI bus protocol or a vendor-specific DALI ballast transfer curve. A later device-specific calibration can replace/parameterize this curve when measured characteristics are available.

## Security / behavior
- Highlight does not open a network socket and does not generate DMX/sACN/Art-Net output.
- Restoration is best-effort based on the HA state attributes captured at highlight start. Unsupported attributes are not fabricated.

# Show Network v0.12.4 — Real Home Assistant fixes

Corrections driven by real Home Assistant 2026.9 runtime logs:

- `config_flow.py`: OptionsFlow no longer assigns the read-only `config_entry` property.
- `vendor_discovery.py`: uses Home Assistant shared Zeroconf instance and never closes it.
- `punchlight_network.py`: uses Home Assistant shared Zeroconf instance and cancels only its browser.
- `runtime/setup.py` and `services/punchlight.py`: pass `hass` into shared-Zeroconf discovery helpers.
- `__init__.py`: registers the existing frontend bundle as a real `Show Network` sidebar panel. Previous builds served the JavaScript but did not expose a panel automatically.
- `manifest.json` / `const.py`: version 0.12.4; declares Home Assistant component dependencies used by the integration.

The optional interface argument for PunchLight discovery is retained for API compatibility, but discovery now follows the adapters enabled in Home Assistant's shared Zeroconf service. This avoids creating a second mDNS socket, as required by current Home Assistant.

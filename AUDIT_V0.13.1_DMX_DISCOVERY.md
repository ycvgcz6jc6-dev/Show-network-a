# Show Network v0.13.1 — DMX selection + sensor state + discovery

## 🟢 Implemented and connected

- DMX module is no longer destroyed/recreated on every Home Assistant state refresh while the user is inside a module. The selected `protocol + universe + source` can therefore remain selected instead of being reset by the parent dashboard.
- The DMX selector continues to expose configured universes even with no traffic and observed sources as distinct entries.
- Generic collection-valued sensors no longer return Python lists/dicts as their HA state. Their state is a scalar count; detailed payloads live in attributes. ETC documented sensors are explicitly exposed in the `sensors` attribute.
- Added `discovery_status` sensor with state plus counts/errors.
- mDNS discovery now records all observed DNS-SD services, not only Green-GO/ELC vendor markers. Vendor identification remains conservative when a marker is actually present.
- Passive Linux ARP cache entries are merged into the common device inventory when available. No packet is emitted by this ARP step.
- Passive DMX and MA-Net3 source IPs are promoted into the same device inventory with evidence/source tags.
- Discovery UI shows inventory total, discovery state, mDNS count, ARP count and explicit errors instead of silently showing only `0`.
- Inventory sensor attributes now include hostname, IPv6 and evidence-source labels needed by the UI.

## 🟡 Deliberately limited

- `SCAN NETWORK` is still conservative/read-only: mDNS + local ARP cache + protocol observations. It is not a blind subnet port scanner and therefore cannot guarantee discovery of a completely silent device that advertises nothing and has never entered the ARP cache.
- Real discovery on the user's Home Assistant/network is not certified by this package build. It must be checked after installation.

## 🔴 Removed / avoided

- No synthetic device or synthetic discovery result was added.
- No assumption that a configured IP belongs to a `/24` subnet was introduced.
- No active port sweep is performed automatically every 60 seconds.

## Validation performed

- `python -m compileall -q custom_components` — OK
- `node --check custom_components/dmx_monitor/static/show-network.js` — OK
- `pytest -q` — **90 passed**

These are static/unit/syntax checks only. They do not prove live DMX selection or real network discovery on Home Assistant hardware.

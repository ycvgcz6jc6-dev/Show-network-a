# Audit v0.13.5 — Cockpit + DMX data path

## Confirmed code defect fixed

`ShowNetworkCoordinator.observe_dmx()` queued the DMX HA publication rate limiter with `None`. `RateLimiter` uses `None` to mean “no pending value”, so its worker exited without calling `_publish_dmx_snapshot()`. This directly explains a valid receive/tracker path with no updated 512-channel values in HA. v0.13.5 queues the DMX observation key instead.

## UI wiring

- PRO dashboard includes live summaries for DMX, ENTTEC DMX IN, MA-Net3, Dante/PTP, discovery, manufacturer/profile evidence, topology and journal.
- Module activation is shown in the relevant module page. The Modules page is navigation/status only.
- PJLink activation no longer implies a projector exists; empty configuration is explicit.
- Dante page is a bounded protocol summary, avoiding uncontrolled entity dumps.
- PunchLight scan shows progress/error feedback and calls the existing `discover_punchlight` service.
- Rule Builder decodes `values_b64`, matching the compact DMX sensor representation.

## Discovery/vendor truth

ARP discovery is real. Luminex/generic-switch/Green-GO/ELC/ETC qualification remains evidence-driven: catalogue/profile presence is not presented as a confirmed live device. No IP/subnet is hard-coded.

## Validation scope

Static/unit validation only. No claim of live Home Assistant, multicast, MA-Net3 session, PunchLight hardware, Dante, PJLink, SNMP, Green-GO, ELC or ETC end-to-end validation is made.

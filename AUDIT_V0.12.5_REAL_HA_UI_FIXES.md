# v0.12.5 — Real Home Assistant UI/service fixes

Observed in real HA testing:

- `services.yaml` failed to parse `projector_power.fields[True]` because YAML 1.1 interprets unquoted `on` as boolean. Fixed by quoting the key as `"on"`.
- OSC output and Projector Control correctly require Show Network security unlock. The panel now exposes security status plus configure/unlock/lock actions instead of failing opaquely.
- ENTTEC listen is receive-only. Its switch does not call `require_unlocked()` and remains outside the active-control security gate.
- The PRO panel was visible but its navigation buttons were decorative/unwired. Classic, Timeline metadata and Journal/Backups now navigate to real in-panel views.
- The PRO panel previously assumed fixed entity IDs such as `sensor.dmx_monitor_network_capacity_utilization`. It now resolves `dmx_monitor` entities by integration platform + unique_id from the HA entity registry, with the old IDs only as fallbacks.

Validation performed here is static/unit validation only; no claim of live HA/network/hardware validation is made.

# Show Network OLA RDM bridge

This helper keeps native OLA outside Home Assistant Core. It uses the documented
`ola_rdm_discover`, `ola_rdm_get` and, only when explicitly enabled,
`ola_rdm_set` tools. Default mode is read-only.

Environment: `RDM_UNIVERSES=1,2,10`, `RDM_PORT=8098`, `RDM_ALLOW_SET=0`.
When writes are enabled, only `dmx_start_address`, `dmx_personality`,
`device_label` and `identify_device` are accepted by the bridge.

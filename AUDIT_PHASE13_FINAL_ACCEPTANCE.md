# Show Network — Phase 13 final acceptance

## Release candidate

Version reconciled to **0.15.0 EXPERIMENTAL**. Phase 13 is a cumulative acceptance pass over the Phase 12 + Tally tree; it does not claim hardware certification.

## Checks completed

- Full automated suite: **220 passed / 220**.
- `python -m compileall -q custom_components helpers`: OK.
- `node --check custom_components/dmx_monitor/static/show-network.js`: OK.
- `services.yaml`: **80** documented services.
- Literal Home Assistant service registrations: **80**; no documented service missing and no undocumented literal registration found.
- Frontend `_call()` service references checked against `services.yaml`: no unknown service.
- AST empty-function scan: no function consisting only of `pass` remains. The two Zeroconf listener callbacks that intentionally ignore update/remove events were made explicit no-op returns.
- Frontend cache/version references, manifest and `const.VERSION` reconciled to **0.15.0**.
- README rewritten **French first, English second**, with a prominent EXPERIMENTAL warning, feature overview, manual installation, update, multi-NIC network guidance, safety and hardware-validation limitations.

## Cumulative functional scope retained

The final tree retains the previously implemented DMX/sACN/Art-Net receive path, multi-NIC discovery, SNMP/LLDP, Dante/AES67/PTP/MA-Net3 monitoring, amplifier/projector adapters, GDTF fixture control, RDM/RDMnet bridge integration, the 19-scene HA→DMX bank with external-source arbitration, OSC/MIDI/Show Control, IP-video supervision/optional preview, persistence/backup/diagnostics, ETC Sensor3/CEM3 monitoring and passive TSL UMD IP Tally.

## Important limitations

- **Experimental software**: automated tests do not validate a real venue network or every manufacturer firmware.
- Native ETCLabs RDMnet helper binary remains outside the validated runtime; Show Network provides the HA-side bridge contract/integration but does not claim a locally compiled native RDMnet implementation.
- RDM/OLA, amplifier vendor paths, projector vendor paths, CEM3 pages, ENTTEC output, MIDI hardware, TSL UMD and network multicast behavior require site/hardware validation.
- IP-video preview depends on a real usable stream URI and local media/runtime capability; NDI is not synthesized into a fake stream URI.
- Active outputs remain safety-gated and must be validated before production use.

## Packaging

`Show_Network_0.15.0_EXPERIMENTAL.zip` is the release package. It contains the integration plus project helper/configuration material needed by this source tree, but excludes historical phase archives, pytest caches and Python bytecode.

## dev36 physical-topology regression
- Python compile: PASS
- Frontend JavaScript syntax: PASS
- YAML parse: PASS
- Static frontend audit: PASS (27 modules, 20 literal services, 18 cards, 53 custom elements)
- Executable tests in this environment: 67 passed
- Known HA-runtime-dependent tests excluded from this container recipe: test_config_flow_osc_port.py, test_ma3_web_remote_view_ssrf.py, test_services_common.py, test_video_ip_preview.py
- No project function/module removed in dev36.

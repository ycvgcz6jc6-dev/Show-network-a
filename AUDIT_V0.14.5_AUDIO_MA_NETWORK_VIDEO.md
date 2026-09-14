# Show Network v0.14.5 — MA / Audio / Network / Video

## Policy

- Generic integration: no venue IP, VLAN, host name, credentials or model instance is hard-coded.
- Passive/read-only unless an existing explicit protected control service is invoked.
- No claim of hardware/real-HA validation in this audit. Validation below is static/unit only.

## 🟢 Implemented and connected

### MA-Net3
- UDP 30020 receive-only listener.
- Default multicast base `236.4.1.x` and MA alternative base `239.4.1.x`.
- Session index is inferred only from the multicast session block that actually carries packets.
- Session member list is correlated by source IP and observed session index.
- Session name, location, master role, station model and showfile stay unknown unless future payload evidence proves them.
- No MA session join, no Web Remote probing, no MA command output.

### Dante / PTP
- UDP 319/320 listener joins `224.0.1.129` through `224.0.1.132` on the configured interface.
- PTP packet presence, freshness, sources and observed protocol version are exposed.
- PTPv1 and PTPv2 are distinguished; PTPv2 Grandmaster offsets are not reused on PTPv1 payloads.
- Audio UI now exposes PTP presence/age and PTPv1-vs-v2 observation state.

### AES67
- SAP `239.255.255.255:9875` remains receive-only.
- SDP metadata is parsed conservatively: session name, origin/source, multicast destination, RTP port/payload, RTPMAP and clock attributes.
- Session freshness/age is exposed. Audio payload is not subscribed to or stored.

### Network discovery
- ARP cache remains passive evidence.
- SNMP probing is read-only GET only and bounded.
- Per-host SNMP scan diagnostics are exposed (responded/timeout-or-no-SNMP, sysName, sysDescr, sysObjectID).
- Explicit manufacturer markers currently cover Luminex, ELC Lighting, Green-GO, Cisco, HPE Aruba, NETGEAR, Ubiquiti, MikroTik, TP-Link, Allied Telesis and Juniper.
- A generic SNMP responder is no longer automatically called a switch unless sysDescr/name or manufacturer evidence supports it.

### Amplifiers
- Dedicated UI page for observed amplifiers and telemetry.
- Catalogue/identification hints include L-Acoustics, d&b audiotechnik, Lab Gruppen/Lake, Adamson, Powersoft, QSC, Crown, Yamaha and Meyer Sound.
- Temperature, level, load, limiter and fault fields remain empty until an observer provides real telemetry.

### Video
- Projector page now groups PJLink entities into an exploitation view and surfaces power, input, lamp hours, temperature, errors and online state when available.

## 🟡 Catalogue/documentation only

- Vendor-specific amplifier APIs not already backed by a real redistributable protocol implementation remain catalogue capabilities only.
- L-Acoustics vendor API control is not guessed or embedded.
- Physical switch topology links are not invented from ARP/SNMP identity alone.
- MA session names/roles/master status are not decoded yet because current code has no proven payload parser for those fields.

## 🔴 Not claimed / not performed

- No real Home Assistant install test of v0.14.5 by this environment.
- No live grandMA3 session validation.
- No live Dante/AES67 amplifier validation.
- No live Luminex/other-switch SNMP validation.
- No projector hardware test.

## Validation performed

- `python -m compileall -q custom_components tests` — OK
- `node --check custom_components/dmx_monitor/static/show-network.js` — OK
- `pytest -q --disable-warnings` — **125 passed**

## Regression stance

The DMX receive/value path that passed the user's real v0.14.3 test was not rewritten for this release.

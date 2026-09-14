# Show Network v0.14.4 — Audio / MA / Switch

## 🟢 Implemented and connected
- Dante source freshness inventory from actually received monitor/mDNS packets.
- PTP clock presence/age, Grandmaster identity and domain remain based on received PTP packets.
- AES67 SAP SDP metadata is parsed conservatively into observed session rows.
- SNMP OBJECT IDENTIFIER response decoding fixed: `sysObjectID.0` is no longer silently discarded.
- MA-Net3 raw printable diagnostics are retained per source in a bounded buffer.
- MA session/name/version enrichment accepts only explicitly labelled printable evidence; otherwise remains unknown.

## 🟡 Evidence-dependent
- Dante endpoint names require observed Dante mDNS evidence.
- MA session discovery remains proprietary-protocol evidence-dependent; this release does not guess binary fields or join a session.
- Switch vendor/model qualification depends on read-only SNMP response and evidence.

## 🔴 Not implemented
- No Dante routing/control.
- No SNMP SET.
- No MA-Net3 session join or MA command transmission.

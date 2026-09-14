# Show Network v0.14.8 — Discovery / UI / Security audit

## 🟢 Implemented and connected
- Module live refresh no longer rebuilds the parent dashboard for Audio, Amplifiers, Video, Security, Network or ETC. Child panels receive HA state updates directly; this is intended to preserve open `<details>`, filters and scroll state.
- Manual `scan_network` now performs a bounded inventory sweep on every active non-loopback IPv4 interface, maximum 254 hosts/interface. Periodic discovery remains passive. Protocol listeners (DMX, Dante, MA-Net3, AES67, OSC) are unchanged and remain on their configured interfaces.
- Discovery status exposes interfaces, network/CIDR, ARP counts by interface and active-scan target/skipped diagnostics. UI adds an interface filter.
- Module enable/disable and DMX universe changes now reload the ConfigEntry after changing options. This fixes buttons that updated options but appeared to do nothing at runtime (notably Diagnostics).
- Luminex read-only SNMP telemetry adds documented scalar CPU temperature, CPU 60 s utilisation, free-memory percentage and VLAN count in addition to standard MIB-II interface data.
- Home Assistant inline brand assets added under `custom_components/dmx_monitor/brand/` (icon/logo 1x/2x) for current HA brand proxy support.

## 🟡 Implemented but dependent on equipment/configuration
- Luminex SNMP requires SNMP enabled on the switch. Default read-only community `Public` is used only as the documented Luminex fallback. Timeout means unknown, never “not a switch”.
- Aruba/Cisco/other switch identification uses standard SNMP identity (`sysDescr`, `sysName`, `sysObjectID`) and explicit vendor/switch evidence. Vendor-specific temperature/PoE/VLAN tables are not claimed unless implemented.
- ETC Sensor3/CEM3 load monitoring is documented by ETC, but this release still has no documented live transport adapter for those values; catalogue remains catalogue only.
- Security backend PBKDF2 gate was reviewed. No password bypass/reset was added. Frontend errors from `unlock_security` remain visible; real HA verification is required for the user's reported unlock failure.

## 🔴 Not claimed
- No real switch, amplifier, Green-GO, Dante, AES67, ETC rack or projector was available in the build container.
- No real Home Assistant UI/hardware test was performed by this build.
- No vendor telemetry is fabricated from an IP address.

## Video review (user real HA)
- Diagnostics “Activer les tests diagnostic” could appear ineffective because `set_module_enabled` updated ConfigEntry options without reloading runtime. Fixed in this release.
- Inventory showed many ARP candidates but little/no manufacturer qualification. v0.14.8 broadens inventory coverage to all local IPv4 interfaces during explicit scan and keeps per-interface diagnostics.
- MA-Net3 session visibility is materially improved in the user's real HA video; device classification remains evidence-only.
- ETC page correctly showed `transport live actuel : NON IMPLÉMENTÉ`; this is honest and retained until a supported transport is implemented.

# Show Network v0.14.1 — runtime RX/discovery correction

## 🟢 Implemented and connected
- DMX binary-sensor dynamic creation deduplicated by protocol+universe; multiple sources no longer request duplicate HA unique IDs.
- DMX listen universes can be changed directly from DMX View through `set_dmx_universes`; ConfigEntry reload applies multicast memberships.
- MA passive sources are labelled `station non classifiée` until evidence exists; no console/node guess from IP/source presence.
- OSC input reports `port_in_use` and retries once after reload before giving up.
- Network discovery read-only SNMP identity probe uses configured community, or Luminex documented read-only default `Public` when absent.
- Discovery cadence reduced from 60s to 180s and SNMP concurrency reduced to lower HA load; manual scan remains available.
- Dante shared-Zeroconf scan directly browses known `_netaudio-arc` and `_netaudio-dante` service types in addition to DNS-SD enumeration.
- Dante endpoint inventory excludes unrelated mDNS sources.
- Main panel HA update rendering throttled to 250 ms, including module child propagation, to reduce UI churn.

## 🟡 Catalogue/documentation / needs real hardware validation
- Luminex SNMP identity depends on SNMP being enabled on the actual switch and reachable from HA.
- Dante detection depends on Dante DNS-SD/multicast traffic reaching the selected HA interface/VLAN.
- MA session/member role decoding remains passive/raw; no proprietary metadata is invented.
- DMX socket/parser instrumentation is exposed; real reception still requires validation on the user's HA network.

## 🔴 Removed / no longer claimed
- MA source presence is no longer treated as evidence that a device is a console.

Validation in build environment is static/unit only; no claim of real HA/network/hardware validation.

# Changelog

## 0.15.17 — Pro audio console/mixer brand recognition

Found the manufacturer catalog had zero console/mixer brands at all --
only amplifiers and loudspeakers. Added the major pro audio console
manufacturers, following the exact same conservative pattern already
used for QSC/Yamaha/etc: literal brand-name text matching against
already-collected evidence (mDNS, hostnames, HTTP banners), never an
invented protocol.

- New manufacturer catalog entries: Midas, Soundcraft, DiGiCo, Allen &
  Heath, Avid, Solid State Logic -- each with their real, current product
  lines.
- New mDNS brand-name markers for the same six brands in
  `vendor_discovery.py`.
- Tested: `match_manufacturer()` correctly identifies all three sample
  brands from realistic evidence text.
- These appear directly in the existing generic Auto Discovery table once
  identified -- no new dedicated module needed, consistent with how
  amplifiers/switches already work.

## 0.15.16 — Full audit of every gated/active-output panel and service

Requested comprehensive check of everything security-gated, following two
real refresh bugs found in a row (DMX→HA mappings, then zones).

- Found and fixed a third instance of the same bug class, missed by the
  first sweep because it used `sync()` rather than `render()`: the Rule
  Builder's `call()` waited only 50ms (shorter than the already-fragile
  150ms pattern fixed in 0.15.13) before resyncing, with no retry. Now
  matches the same 400ms+1500ms double-attempt pattern used everywhere
  else.
- Systematically re-checked every custom element with a service-call
  method (16 across the whole panel) for a missing refresh -- all other
  15 confirmed correct.
- Separately and more importantly: checked the actual security gate
  itself (not just the UI refresh) on every service that genuinely emits
  real output -- DMX scene recall, OSC send (both generic and
  profile-based), MIDI send, RDM writes, Power Manager run, QLC+ (widget
  value/cue list/frame/function), Show Control fire, GDTF attribute set,
  and projector power/input/mute. All 15 confirmed to call
  `security.require_unlocked()` (projector control additionally checks
  its own `control_enabled` flag first, in a shared helper all three of
  its services delegate to). No security bypass found anywhere -- every
  bug found in this project has been about the interface not reliably
  showing success, never about an unlocked action slipping through.

## 0.15.15 — DMX → HA Zones: real bug found (no refresh at all) + mobile multi-select fix

- Fixed: "AJOUTER LA ZONE" appeared to do nothing. Root cause: unlike
  every other panel, `DmxHaZonesPanel._call()` never re-rendered after
  any action at all -- not even the fragile single 150ms timeout fixed
  elsewhere, nothing. The backend service was already correct (verified);
  the zone was very likely being created successfully but the screen
  never reflected it. Same double-refresh pattern (400ms + 1500ms) now
  applied here, plus an actual error/success message, which this panel
  never had either.
- Fixed: the "Lampes HA" field was a native HTML multi-select, which
  cannot be used to select multiple items with touch alone (no
  ctrl/cmd+click equivalent on a phone) -- replaced with checkboxes,
  directly addressing the request to be able to add several lights per
  zone.

## 0.15.14 — Root cause found: non-GigaCore switches were never contacted at all

Based on a real network inventory shared by the user (Cisco/Netgear/HPE
switches alongside a Luminex GigaCore, all on 10.4.1.0/24).

- Confirmed `arp_neighbors()` reads the OS's global ARP table
  (`/proc/net/arp`), not scoped to any particular configured interface --
  explaining why discovered devices span multiple subnets regardless of
  the DMX/MA-Net3/etc interface selection.
- Found the real reason a real Cisco switch never appeared anywhere,
  including Auto Discovery: `GenericSwitchMonitor` was only ever fed
  GigaCore's host list, so a switch that isn't a Luminex GigaCore was
  never contacted by anything in Show Network at all -- and an ARP entry
  only exists for a host the OS has actually exchanged packets with, so
  "never contacted" also means "never appears in discovery," independent
  of interface configuration.
- New: `CONF_GENERIC_SWITCH_HOSTS` config field, letting an operator list
  non-GigaCore switches (Cisco, Netgear, HPE, etc.) explicitly. These are
  now actively SNMP-polled alongside GigaCore hosts, which should also
  make them appear in Auto Discovery as a side effect of that traffic.
  Tested the host-list merge against the user's real switch inventory.

## 0.15.13 — Interface filter bug + manual amplifier registration

Based on real screenshots and network inventory shared by the user.

- Fixed: the topology page's "Vue interface" filter always showed only
  "Toutes" -- confirmed root cause: it searched for an `evidence` entry
  with `field==='interface'`, but the backend only ever populates
  `add_evidence()` from one single generic call site that nothing in the
  real ARP/mDNS/SNMP discovery pipeline actually feeds an "interface"
  field into. The interface is really stored as a plain `device.interface`
  attribute, already serialized to the frontend -- the filter was just
  reading the wrong place. Confirmed the field genuinely exists and is
  already sent before fixing.
- New: manual amplifier registration by IP address
  (`manual_register_amplifier`/`manual_remove_amplifier`), a direct
  alternative to automatic Dante/mDNS-based brand detection -- which the
  user found unreliable in practice for a real amplifier that only ever
  showed as "seen via Dante, brand unidentified". Added a `remove()`
  method to `AudioAmplifierInventory` (didn't exist) and a form in the
  Amplifiers panel.
- Noted (not a code fix): Cisco switch not appearing and Luminex having
  no LLDP-derived topology links may be a network-topology issue rather
  than a Show Network bug -- ARP is link-local, and the shared screenshots
  show every currently-visible device coming from different subnets than
  the switches' 10.4.1.0/24, suggesting Show Network's configured
  interface may not have direct L2 visibility into that segment. The
  interface-filter fix above should help confirm this once tested.

## 0.15.12 — Defense in depth around the 0.15.11 deferred loads

Following a report that DMX reception was still not working, re-examined
the 5 deferred loads added in 0.15.11. Each store's own `load()` method
already handles file-read/parse errors internally, but the awaits calling
them in `runtime/setup.py` were unguarded and run in series, before DMX
receiver startup later in the same function -- meaning an exception type
any one loader's own except clause doesn't happen to catch (e.g. a stored
item that isn't a dict, raising AttributeError instead of the caught
ValueError/TypeError/KeyError) would silently abort the rest of setup,
DMX included. Each of the 5 is now individually wrapped so a failure in
any one is logged and setup continues regardless -- this was not
confirmed as the actual cause of the reported DMX issue, but closes a
real gap either way and is the honest, testable next step pending the
specific error message the DMX card now shows.

## 0.15.11 — Blocking I/O in the coordinator constructor (confirmed in production)

A shared production log showed 4 distinct blocking-I/O warnings at every
single startup, all originating from `ShowNetworkCoordinator.__init__`.
Investigating found the true scope was larger than the log alone showed:
5 separate blocking file reads ran synchronously during coordinator
construction, all directly on Home Assistant's event loop.

- `PowerManager.__init__` called `self.load()` directly.
- `DmxCircuitMonitor.__init__` called `self.load()` directly.
- The coordinator's own `_load_dmx_ha_zones()`, `control_mapping_store.
  load()`, and `dmx_ha_mapping_store.load()` all ran inline in `__init__`.

One of these (rules, via `RuleStore`) had already been correctly fixed at
some point, with a comment explaining why -- that same fix was never
applied to its four siblings. All five now defer to
`hass.async_add_executor_job(...)` in `runtime/setup.py`, matching the
pattern already correctly used for `fixture_control`/`dmx_scene_bank`.
Tested directly: constructing `PowerManager`/`DmxCircuitMonitor` no
longer touches disk, and an explicit `.load()` call afterwards still
correctly recovers real persisted data.

A full sweep for any other constructor still doing blocking I/O found
none remaining.

## 0.15.10 — Fresh audit pass

Requested full re-audit of everything built this session. Checked version
consistency, residual TODOs, orphaned modules, duplicate sensor keys,
security-gate coverage on new active-output services, and duplicate/
missing custom-element registrations.

- Fixed: `audiofocus.py` (the honest NotImplementedError scaffold for the
  two Audiofocus commands still awaiting a real packet capture) was never
  imported anywhere -- dead code only discoverable by reading the source.
  Now instantiated in the coordinator and its status note surfaced
  alongside the amplifiers sensor, so "not yet implemented, capture
  needed" is visible in the interface rather than silently absent.
- Everything else checked came back clean; several apparent issues
  turned out to be false positives from the audit script's own regexes
  (quote-style differences, a tuple membership check that looked like a
  duplicate sensor definition) rather than real problems -- noted here
  for the record rather than silently discarded.

## 0.15.9 — Topology root cause + Araneo-style health check

- **Diagnosed the "30 nodes, 0 links" topology issue** confirmed in a live
  audit: LLDP-based link discovery only runs for switches that first
  respond successfully to SNMP identification -- meaning the SNMP
  executor-pool starvation fixed in 0.15.6 was very likely the actual
  root cause of both "topology shows zero links" and the earlier
  "switch/amp monitoring doesn't work" reports, not two separate bugs.
  Confirmed the frontend topology panel already renders links correctly
  when present -- no display-side fix was needed, only the underlying
  SNMP reliability fix already shipped.
- **New: cross-switch health check**, inspired by Luminex Araneo's
  consistency checking -- flags VLAN count or model/firmware string
  mismatches between switches sharing the same identified manufacturer,
  and switches reporting zero UP interfaces despite having some. Computed
  entirely from telemetry this project already collects; nothing new is
  probed or invented, and a single switch of a given manufacturer never
  triggers a false comparison.

## 0.15.8 — Ontime and QLC+ integrations

New, real, verified-against-source integrations, added following this
project's standing rule: only build against confirmed real protocol
behavior, never guessed formats.

- **New: Ontime supervision.** Passive HTTP polling of Ontime's real,
  documented `/api/poll` endpoint (every field verified against
  docs.getontime.no/api/data/runtime-data/). Dashboard card shows
  playback state, time remaining, and schedule offset (running ahead or
  behind). Deliberately supervision-only -- Ontime's separate control API
  is not touched here, the same way DMX emission is kept apart from DMX
  supervision elsewhere in this project.
- **New: QLC+ Virtual Console bridge and panel.** WebSocket connection to
  QLC+'s real API (`ws://<host>:9999/qlcplusWS`). Every command/response
  format was verified against the QLC+ maintainer's own
  `Test_Web_API.html` source file, not community forum posts -- two of
  which were found to actively disagree with each other and with the
  authoritative source on the write-command format. A real indexing bug
  (`getWidgetStatus`'s value is at index 3, not 2) was caught by testing
  against the exact documented response shape before shipping. Supports
  passive widget/function discovery plus gated control (set widget value,
  cue list PLAY/NEXT/PREV/STEP, frame paging, function start/stop).

## 0.15.7 — Closing the remaining service/interface gaps

Completed the audit started in 0.15.6: cross-referenced every backend
service against the frontend again with a corrected extraction (catching
direct `callService('dmx_monitor', 'x', ...)` calls the previous pass
missed) and closed every genuine remaining gap.

- **New: DMX → HA mapping create/remove**, plus a visible Light Sync gate
  toggle (state was tracked but never shown or controllable).
- **New: rule history clearing** button in the Rule Builder.
- **New: archive destination**, editable from the Archive panel (was
  read-only).
- **New: device inventory reset-to-auto** button next to "Modifier".
- **New: HA Builder per-item state control** (switch/sensor/number/binary
  sensor entities Show Network created could not be driven from the UI).
- **New: notification configuration** section (enabled/target/mode).
- **New: RDM observation recording** per DMX→HA zone with RDM listening
  enabled.
- **New: OSC output master gate toggle** -- the send buttons existed but
  the arm/disarm switch for OSC output itself was never added; send
  buttons now also respect this gate, matching every other active-output
  panel in the project.
- Confirmed (not re-implemented) that `set_device_override` and
  `set_dmx_ha_mapping_highlight` were already wired via direct
  `callService()` calls that an earlier automated audit's regex had
  missed -- rechecked against the real file before adding anything, to
  avoid duplicating working code.

## 0.15.6 — Interface functionality audit and repair

Large pass making the panel's active-output modules actually functional,
following a systematic audit that cross-referenced every frontend service
call against every real backend service (found and fixed two extraction
mistakes along the way; final result: all 33 then-existing frontend calls
matched a real service, and ~40 real services had no UI at all).

- **New: DMX Scene Bank UI.** This whole feature (save/recall/delete up to
  19 full DMX scenes, configure output transport) had no interface at all.
- **New: GDTF panel**, plus a genuine backend fix: `FixtureControlEngine.
  set_control_enabled()` existed but no service ever called it, so GDTF
  fixture output could never be armed at all, not even via Developer
  Tools. Added `set_fixture_control_enabled`.
- **New: Show Control cue editor.** Cues could be viewed and fired but not
  created except by calling a service manually; added a form supporting
  all four real action types (ha_service/osc/midi/dmx_scene).
- **New: OSC command library, for real this time.** The panel was static
  decorative HTML with no data binding; rewritten to read the real
  profile catalog and configured targets, manage targets, and send real
  commands via `send_osc_profile_action`. Fixed a companion bug in the
  OSC output status panel, which looked for its data directly on
  `hass.states` instead of on the sensor attributes where it actually
  lives. Added a generic (non-profile) OSC send section, and a Medialon
  Show Control catalog entry (no fixed addresses -- its OSC address space
  is defined per-installation, so this points to Learn instead of
  guessing addresses that would only be right for one specific show).
- **New: MIDI target management and raw send** in the same panel
  (`create_midi_target`, `remove_midi_target`, `send_midi` had no UI).
- **New: projector control** (power/mute/input) added to the previously
  read-only video/projector module, gated by the existing
  `set_projector_control_enabled` service.
- **New: RDM write controls** (identify, set start address, set
  personality, link to a GDTF patch) added to the previously read-only
  RDM module, respecting the existing two-gate design (config-level
  `rdm_allow_writes` plus runtime security unlock).
- Fixed: amplifiers/devices identified only by protocol evidence (e.g. a
  Dante-connected amplifier whose brand isn't in the manufacturer list)
  showed the bare protocol name where a brand would normally appear,
  reading like a (wrong) manufacturer identification; now says so
  explicitly.
- Fixed: DMX receiver errors and restart counts were computed by the
  backend but never shown anywhere -- a flapping Art-Net/sACN listener
  gave no visible reason why. Added to the main DMX overview card.
- Fixed: the adaptive performance manager (refresh interval, discovery
  throttling under CPU/RAM load) was fully functional but completely
  invisible in the interface; added a status card.
- Reorganized the module grid into three labeled sections (Supervision /
  Commande-Émission / Système) instead of one undifferentiated grid, so
  passive monitoring and active-output controls are never presented
  side-by-side without distinction.
- Isolated all SNMP blocking socket I/O onto a dedicated thread pool
  instead of Home Assistant's shared default executor -- a plausible
  contributor to reports of WebSocket ping/pong timeouts and DMX
  reception instability when several configured switches/amplifiers are
  unreachable at once.

## 0.15.5 — Configuration flow repair

- Restored the missing `_choices_for_hass()` helper used when opening the
  configuration and options forms. This fixes the HTTP 500 caused by its
  `NameError`.
- Kept interface, ENTTEC and MIDI discovery in executor jobs so opening the
  form does not block Home Assistant's event loop.

## 0.15.4 — Safe asynchronous catalogue loading

- Fixed config-entry setup when a catalogue is already materialized as a
  tuple by an older loaded module (`AttributeError: 'tuple' object has no
  attribute 'warm'`).
- Kept YAML catalogue reads deferred and warmed them from Home Assistant's
  executor, avoiding blocking `open()` calls on the event loop.

## 0.15.3 — CEM3 real read-only, security hardening, multi-vendor node discovery

- **Versioning fix**: previous packages shipped with `manifest.json` reporting `0.15.0` while other artifacts referenced `0.15.2`, with no changelog entry for the latter and no single source of truth. This release consolidates everything into one consistent version.
- **Security fix (SSRF)**: the grandMA3 Web Remote proxy (`ma3_web_remote_view.py`) previously accepted any `station_ip` from the request URL with no validation, allowing an authenticated Home Assistant user to make Home Assistant issue outbound requests to arbitrary hosts (including internal/cloud-metadata addresses). It now only proxies to an IP already present in that config entry's own passively-observed MA-Net3 station inventory, requires an explicit `entry_id` when more than one Show Network entry exists, and caps the upstream response size.
- **ETC Sensor3/CEM3**: real read-only XML client (`etc_cem3.py`, `cem3_websocket.py`) replacing the earlier catalogue-only status page — queries the rack's System/Dimmers/Spaces pages directly, with XXE/entity-expansion hardening and duplicate/size limits.
- **New: grandMA3 device classification**: MA-Net3 stations are now classified into `console` / `processing_unit` / `node` / `software` categories with accurate grandMA3 product names (previous classification lumped everything under a handful of loosely-matched labels, including a non-existent "RPU" product).
- **New: grandMA3 Web Remote HTTPS/WSS proxy**: fixes the mixed-content issue that broke the console's own Web Remote when Home Assistant is reached over HTTPS (e.g. Nabu Casa) — the console's page hardcodes a plain `ws://` WebSocket URL, which browsers refuse under HTTPS. Not yet verified against real console hardware; validate on-site before relying on it for a show.
- **New: manufacturer-agnostic Art-Net node discovery** (`artnet_discovery.py`) via standard ArtPoll/ArtPollReply — identifies ELC, Luminex, ETC, or any other Art-Net-compliant node regardless of brand, complementing the existing mDNS-only vendor discovery.
- **New: generic SNMP switch telemetry** (`switch_monitor.py`) for switches with no vendor-private OID support in this codebase (e.g. ELC, Green-GO-hosting switches) — identity/uptime/interface-count via standard SNMPv2-MIB/IF-MIB, PoE via POWER-ETHERNET-MIB if answered; no vendor-private OIDs are guessed at.
- Fixed: Aruba switch profile key mismatch (`aruba` vs `hpe_aruba`) between `switches.yaml` and `spectacle_profiles.yaml`/`manufacturers.yaml`, which silently broke manufacturer matching and profile selection for HPE Aruba switches.
- Fixed: Dante-observed amplifier manufacturer detection referenced a `markers` field that dante_inventory rows never populate, making the match effectively always fail; now scans services/instances/hostnames/display_name.
- Fixed: six switch vendors present in `switches.yaml` (Netgear, Ubiquiti, MikroTik, TP-Link, Allied Telesis, Juniper) had no matching entry in `spectacle_profiles.yaml`, so `match_manufacturer()` could never identify them from network evidence.
- Fixed: `manifest.json`'s `documentation`/`issue_tracker` pointed at the project's old repository name.
- Corrected repository links to the current repository name.

## 0.15.0 — Experimental cumulative release

- Cumulative reconciliation of development phases 1–12.
- Added GDTF fixture control, RDM/RDMnet bridge integration, 19-scene HA→DMX bank with external-source arbitration, OSC/MIDI/Show Control, IP-video supervision, backup/restore/diagnostics, ETC Sensor3/CEM3 monitoring and passive TSL UMD IP Tally.
- Final UI/service/runtime consistency audit.
- README rewritten in French then English with experimental warning and manual installation/update instructions.
- Active output features remain independently gated; hardware/vendor validation is still required.

## 0.14.7 — UI state, discovery repair, Power Manager
- Fixed SNMP BER request encoding and response value parsing (including sysObjectID).
- Added Luminex MAC-prefix evidence, bounded HTTP read-only fingerprints and standard IF-MIB switch telemetry.
- Added persistent Auto / Surveiller / Ignorer device monitoring mode.
- Added persistent multi-button Power Manager with custom names/icons and staged sACN/Art-Net/ENTTEC output behind Show Network security.
- Split Rule Builder, Signal Watchdogs, DMX Circuit Monitor and Power Manager into distinct pages with explanations.
- Added receive-only DMX Circuit Monitor groups.
- Expanded Dante/PTP Geek diagnostics and AES67 SDP detail/freshness.
- Added conservative MA station type hints from explicit payload markers only.
- Restored ETC Sensor3/CEM3 catalogue page with clear catalogue-vs-live status.
- Preserved expanded menus/details and protected active forms from live refresh rebuilds.
- Replaced browser prompt() security flow with an in-panel password form.
- Integrated cleaned transparent Show Network logo/icon assets.

# v0.14.5

- MA-Net3: passive session-index observation from official multicast group mapping on UDP 30020, default 236.4.1.x and alternate 239.4.1.x bases; no session join/control.
- MA UI: session indexes/members displayed only when multicast evidence exists; session name/location/master remain unknown without payload evidence.
- PTP/Dante: listener now joins 224.0.1.129-132; exposes PTP presence/age/version and distinguishes observed PTPv1 vs PTPv2 without applying PTPv2 field offsets to PTPv1.
- AES67: SAP listener now extracts safe SDP metadata (session name, source, destination, RTP port/payload, clock attributes) and freshness without storing audio.
- Audio UI: richer Dante/PTP/AES67 page plus a dedicated amplifier telemetry page.
- Amplifier catalogue: L-Acoustics, d&b, Lab Gruppen/Lake, Adamson, Powersoft, QSC, Crown, Yamaha and Meyer Sound identification hints; telemetry remains unknown until observed.
- Network discovery: bounded read-only SNMP diagnostics per ARP host, manufacturer identification for Luminex, ELC, Green-GO, Cisco, Aruba, NETGEAR, Ubiquiti, MikroTik, TP-Link, Allied Telesis and Juniper; generic responders are not automatically labelled as switches without evidence.
- Video UI: projector exploitation view for online/power/input/lamp/temperature/errors when PJLink entities provide them.
- DMX receive/value path intentionally unchanged from the validated v0.14.3 baseline.

## 0.13.5 — Cockpit, DMX live publication, local module controls, Dante cleanup

- Fixed the DMX live publication path: the rate limiter was queued with `None`, which is also its internal “no pending value” sentinel; DMX tracker updates could therefore never be published to HA. It now queues the actual source/universe key.
- Main PRO dashboard now summarizes DMX network RX, ENTTEC DMX IN, MA-Net3, Dante/PTP, discovery, manufacturer/profile evidence, topology and journal.
- Module enable/disable controls moved into the relevant module pages; Modules remains a summary/navigation page.
- Video/PJLink page now explicitly distinguishes “monitor enabled” from “no projector configured/discovered”.
- Dante/audio page replaced the loose entity dump with a bounded protocol summary.
- PunchLight discovery button now reports progress/errors and uses the configured DMX/control interface when available.
- Rule Builder can decode compact `values_b64` DMX frames.
- No site-specific IP/subnet is hard-coded; the user-provided MA subnet is not embedded.

## 0.13.5 — Real module controls, DMX values, OSC Learn, Journal & Diagnostics

- DMX live payload is now exposed to the frontend as `values_b64`; the 512-channel view can show the values actually received instead of staying at zero while packet counters increase.
- Added a generic `set_module_enabled` service and quick ON/OFF controls in the Modules page for Art-Net, sACN, MA-Net3, OSC input, MIDI input, PunchLight, watchdogs, HA Builder, PJLink monitoring and diagnostic/chaos tests. Changes are stored in ConfigEntry options and applied through the existing reload listener.
- Added an independent OSC input interface selector.
- Wired the existing `OSCLearnSession` into the real OSC receiver. START/STOP/CLEAR Learn now call real services and learned addresses are exposed through HA sensor attributes.
- Replaced the decorative OSC mapping examples with the mappings actually stored by the integration plus a minimal real mapping editor. Fixed bad relative imports in the control-mapping service path.
- Journal/archive now keeps the last 100 event previews in memory and exposes them to Journal and Timeline views; no disk read is needed to display them.
- Journal / Backups is now mounted from the Modules page instead of opening an empty module.
- Reliability buttons now show explicit execution/error feedback. Fault-injection controls require the new diagnostic-tests opt-in gate.
- Added PJLink monitor enable gate without weakening the separate protected projector-control gate.
- Frontend cache/version bumped to 0.13.5.

Validation: static/unit/syntax only; no claim of real HA/network/hardware validation.

## 0.13.3 — Raw RX visibility

- Fixed E1.31/sACN multicast universe mapping (U1 -> 239.255.0.1).
- sACN now binds UDP 5568 on wildcard and joins configured groups on the selected DMX interface.
- Added configured/joined multicast group and membership-interface diagnostics.
- Added raw MA-Net3 per-source packet diagnostics before classification.
- Moved fixture catalogue disk loading off the HA event loop during runtime setup.
- Frontend cache/version bumped to 0.13.3.

## 0.13.2 — Protocol RX diagnostics

- Added explicit receive diagnostics for Art-Net and sACN: listener state, bound interface/endpoint, packets received/parsed, last source, last universe, restart/error counters.
- sACN now exposes the exact multicast groups successfully joined and any join error instead of silently looking idle.
- Added MA-Net3 listener diagnostics: bind endpoint, configured/joined multicast groups, join errors, last source, last packet time and listener state.
- Fixed MA inspector data wiring: the frontend previously searched for a `ma_remote` attribute that no sensor exposed, so the MA page could stay empty even when backend data existed. MA sensor attributes now expose both `ma_remote` and RX diagnostics.
- Added a dedicated `protocol_rx_diagnostics` sensor with detailed attributes while keeping the HA state scalar.
- mDNS discovery now distinguishes `scanning`, `observed`, `no_services_observed` and `error`, and explains that a zero result means no service was observed during the passive scan window rather than claiming the network has no mDNS devices.
- DMX and MA panels now display low-level receive/bind/multicast diagnostics. Discovery view shows mDNS state/detail.
- Frontend cache/version bumped to 0.13.2.
- No transmit/control behavior was added. Receive-only posture preserved.

## 0.13.1 — DMX selection / sensor state / discovery

- Preserve module instances during HA state refreshes so the DMX `protocol + universe + source` selector stays usable.
- Prevent list/dict payloads from becoming invalid HA states; expose collection details through attributes.
- Add discovery status telemetry with mDNS/ARP counts and errors.
- Expand conservative mDNS discovery from vendor-only markers to all observed DNS-SD services.
- Merge passive ARP cache, DMX source and MA-Net3 source evidence into the unified inventory.
- Improve discovery/inventory UI diagnostics without inventing devices.
- Version/cache bumped to 0.13.1.
- Validation: compileall OK, JavaScript syntax OK, 90 tests passed.

## 0.13.0 — data truth / DMX monitor repair

- Fixes the sensor tuple contract and preserves declared units.
- Exposes missing topology, DMX→HA mapping and archive attributes used by the frontend.
- Fixes `network_capacity_*` sensors being shadowed by the generic `network_*` branch.
- DMX universe sensor now exposes configured universe/interface/protocol metadata.
- Removes the synthetic `dmx-live-view` that displayed generated values as live DMX.
- DMX monitor now selects an observed stream by protocol + universe + source and also lists configured universes with an explicit no-traffic state.
- LIVE badge is shown only when an observed stream has packet rate > 0.
- Network configuration no longer reports protocols as disabled when the configuration sensor is unavailable.
- Frontend cache/version bumped to 0.13.0.

# Changelog

## 0.12.8
- Fix Home Assistant sensor platform startup: `ShowNetworkSensor` now accepts the `(key, name, unit)` sensor catalogue contract.
- Stop registering Show Network as the integration config panel. The sidebar remains available, while Home Assistant Settings/Configure can open the real OptionsFlow again.
- Frontend cache/version bumped to 0.12.8.

## 0.12.7 — Runtime startup + full module navigation

- Long-lived HA action dispatcher now uses Home Assistant background-task tracking so it no longer blocks completion of the startup phase.
- Initial vendor discovery also uses a background task.
- Show Network sidebar panel now exposes the existing functional modules instead of only PRO/Timeline/Archive.
- Added module navigation for DMX/Art-Net/sACN, DMX→HA zones/mappings, ENTTEC, OSC/MIDI/PunchLight, Rule Builder, network/topology, audio/Dante-family diagnostics, video/projector entities, inventory/discovery, HA Builder, manufacturers, reliability/watchdogs and security.
- Security password/unlock/lock actions now update the panel immediately after a successful service call and surface errors in the panel.
- Keeps v0.12.5 `services.yaml` projector `"on"` fix and all prior HA/Zeroconf/OptionsFlow fixes.

## 0.12.5 — Real HA UI/service fixes

- Fix `services.yaml` parsing for `projector_power.fields["on"]`.
- Show Network PRO panel resolves entity IDs through the Home Assistant entity registry instead of assuming hard-coded IDs.
- PRO buttons now open working Classic, Timeline metadata, and Journal/Backups views.
- Added security status and password/unlock/lock actions to the panel so protected OSC/Light Sync/Projector controls are understandable and usable.
- ENTTEC DMX input remains receive-only and is not security-gated.
- Frontend asset cache version bumped to 0.12.5.

# Changelog — Show Network

## 0.12.3

- **Correctif critique Home Assistant** : `projector_platform` n'est pas une plateforme d'entité Home Assistant valide à transmettre à `async_forward_entry_setups`. Les entités projecteur sont maintenant rattachées aux vraies plateformes `sensor` et `binary_sensor`.
- **Correctif critique capteurs** : `journal_archive`, `network_capacity_utilization` et `chaos_status` retournaient un `dict` comme état natif à cause de branches dupliquées placées avant les branches scalaires. Home Assistant n'accepte pas ce type comme état de capteur. Les états sont désormais scalaires et les détails restent dans les attributs.
- **Correctif robustesse PunchLight** : les callbacks asynchrones conservent maintenant une référence forte jusqu'à leur fin et sont annulés proprement à l'arrêt.
- Ajout de tests statiques de régression pour ces erreurs de plateforme et d'état.

## 0.12.2

- **Correctif critique** : `lighting_receiver.py` référençait `self._queues`, un attribut qui n'a jamais existé (le vrai nom est `self._latest_keys`). La réception Art-Net/sACN plantait donc à chaque tentative, avant de recevoir le moindre paquet. Ligne supprimée (variable morte, jamais utilisée ensuite).
- **Correctif critique** : la logique de "backoff" du superviseur ARTNET/sACN remettait le délai d'attente à 1 seconde dès l'ouverture du socket, avant même de savoir si la réception fonctionnait — l'exponentielle (1s → 30s) ne s'appliquait donc jamais en pratique. Le délai n'est désormais remis à zéro qu'après une réception stable d'au moins 5 secondes.
- **Correctif** : `enabled_profiles()` dans `switch_profiles.py` attendait un dict de réglages mais recevait toujours une liste depuis `coordinator.py` (`AttributeError: 'list' object has no attribute 'get'`). La fonction accepte maintenant directement la liste de fabricants.
- **Correctif** : le premier scan de découverte mDNS (`runtime/setup.py`) était attendu de façon synchrone en plein `async_setup_entry`, ajoutant au moins 2 secondes garanties au démarrage de l'intégration. Il est maintenant lancé en tâche de fond.
- **Correctif** : `DeviceInventory` et `HABuilder` étaient construits directement sur la boucle d'événements alors que leurs constructeurs lisent un fichier JSON sur disque — construction déplacée dans l'executor (`hass.async_add_executor_job`).
- **Correctif** : une tâche asyncio créée pour les callbacks OSC (`osc_receiver.py`) n'était référencée nulle part, ce qui l'exposait à un ramasse-miettes prématuré ; une référence forte est désormais conservée jusqu'à la fin de la tâche.
- **Non corrigé volontairement** : plusieurs chargements de fichiers JSON restent synchrones dans `ShowNetworkCoordinator.__init__` (règles, mappings DMX→HA, zones, cibles OSC, sécurité). Le correctif propre nécessite de sortir la construction de `self.data` du constructeur pour la rendre asynchrone — un changement plus large qui mérite ses propres tests avant d'être appliqué en production. Voir `AUDIT_Show_Network_2026-09-13.md`, section 4.

## 0.12.1

- Ajout du gestionnaire de performance adaptatif CPU/RAM.
- Nouveau profil `Auto` recommandé par défaut.
- Définition documentée du profil `Minimal` pour les hôtes Home Assistant modestes.
- Protection progressive des tâches non critiques sous forte charge.
- Maintien de la réception protocolaire et des watchdogs hors de la réduction de charge.
- README réécrit pour refléter la version et les fonctions actuelles.

## 0.12.1

- Adaptive CPU/RAM performance policy with `Auto` as the recommended default.
- `Minimal` defined as the baseline for modest Home Assistant hosts.
- Automatic reduction of non-critical refresh/discovery work under host pressure.
- Protocol reception and watchdog paths remain independent of adaptive UI/polling cadence.
- CPU/RAM and current performance level are exposed to the HA entity layer.

## 0.14.0
- DMX View: navigation univers précédent/suivant en plus du sélecteur; conservation de la réception réelle uniquement.
- Découverte: enrichissement SNMP v1 strictement read-only et borné des voisins ARP quand une communauté est explicitement configurée; lecture sysDescr/sysName/sysObjectID; qualification Luminex/GigaCore, ELC et Green-GO uniquement sur preuve explicite.
- Dante: reconnaissance mDNS conservative des services netaudio/Dante/Audinate et alimentation de l'inventaire; page Audio conserve une synthèse propre et ajoute un volet repliable Geek Diagnostics.
- Inventaire: édition manuelle plus pratique avec catalogue constructeurs et rafraîchissement après sauvegarde.
- Constructeurs: modal d'ajout remontée dans le composant pour corriger positionnement/styles.
- Aucun plan IP utilisateur n'est codé en dur.

## 0.14.1
- Fix duplicate DMX universe binary sensor IDs when several sources feed one universe.
- Add direct DMX listen-universe update control.
- Remove speculative MA console classification.
- Improve OSC reload/port-conflict state.
- Improve read-only Luminex/SNMP and Dante DNS-SD discovery.
- Reduce discovery frequency/concurrency and throttle frontend updates for HA performance.

## 0.14.3
- Stabilise l'UI temps réel: rafraîchissement du cockpit réduit et contrôles DMX non reconstruits pendant leur utilisation.
- Corrige la déduplication des binary_sensors DMX par protocole/univers normalisé.
- PTP: écoute multicast explicite 224.0.1.129 sur l'interface configurée, présence d'horloge, âge, domaine et Grandmaster exposés.
- Dante/PTP: synthèse horloge ajoutée tout en conservant les diagnostics geek.
- sACN: validation de régression du parseur E1.31 sur 512 slots et maintien réception multicast/unicast sur UDP 5568.

## Phase 12 — ETC Sensor3 / CEM3 live supervision
- Added a dedicated read-only CEM3 HTTP monitor based on the documented CEM3 web interface.
- Added explicit ETC interface binding and configured CEM3 host list.
- Added live rack metrics: CPU temperature, line frequency, X/Y/Z phase voltage, rack status, active errors, software version, panic state, and visible circuit statistics when present in the Dimmers page.
- Added one rack status entity and metric sensors per configured CEM3 rack, plus aggregate ETC CEM3 sensors.
- Reworked the ETC panel from capability-only catalogue to live Sensor3/CEM3 supervision while retaining documented-but-not-yet-live capabilities.
- ETC monitor uses HTTP GET only; no rack configuration, level, preset, test, or power-control command is sent.

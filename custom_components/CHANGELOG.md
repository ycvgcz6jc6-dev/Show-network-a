# 0.15.2 EXPERIMENTAL — 2026-09-15

- Base cumulative : archive FULL 0.15.0 fournie, tous ses fichiers conservés.
- CEM3 : requêtes réelles fixes de lecture, parsers des 72 circuits, propriétés et espaces, validation forte avant POST.
- Découverte progressive limitée aux NIC choisies, ajout manuel conservé, plafond 32 racks, quatre connexions simultanées.
- Circuits détaillés par WebSocket authentifié dans le panneau ; agrégats HA préservés et attributs Recorder allégés.
- États offline/freshness distincts, propriétés en cache, annulation et fermeture des sessions au déchargement.
- Durcissement réappliqué : 44 exceptions silencieuses journalisées, DOMAIN centralisé, locks State Store/DMX tracker, publication DMX à 5 Hz (mappings inchangés à 20 Hz).
- Si HA refuse de décharger les plateformes, les ressources restent actives pour éviter une intégration partiellement arrêtée.
- Tests historiques retrouvés et adaptés aux 80 services, cinq plateformes et version courante ; nouveaux tests CEM3/HTTP/concurrence/cycle de vie.
- README français puis anglais, provenance et limites de validation explicites.

---

# Changelog

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

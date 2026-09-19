# Changelog

## 0.15.25
- Hardened the generic device Web proxy against SSRF: operator-only/manual IP entries no longer authorize a fetch by themselves.
- HTTP redirects are now followed manually (maximum 5) and every redirect must remain HTTP(S) on the exact authorized IP literal; hostname/DNS redirects and cross-IP redirects are rejected.
- Proxy port validation now enforces 1..65535 and forwarded query parameters use proper URL encoding.
- Added pure security regression tests for manual inventory targets, observed targets, special IPs, redirects and ports.
- Added UPS-MIB regression tests for RFC1628 enums/conversions, partial replies, loss of reachability/freshness, low battery/on-battery counters and invalid values.
- Audited remaining `pass` statements: the inspected occurrences are exception/fallback handling or exception class bodies, not empty advertised features; nothing was deleted.

## 0.15.24 — Remote device web-page access + UPS supervision

- **New: generic device web-page proxy.** Lets an operator open any
  already-discovered device's own web management page from inside the
  Show Network panel, including remotely (e.g. via Nabu Casa). Solves two
  real problems the user raised: mixed content (the browser only ever
  loads from Home Assistant's own HTTPS origin, since HA does the actual
  fetch from the local network and relays the bytes back) and local-IP
  unreachability (a device's own IP, e.g. 10.4.1.3, is not reachable at
  all from outside the venue's network -- HA fetches it locally on the
  operator's behalf). Gated behind the security unlock as requested.
  SSRF prevention follows the exact same pattern as the MA3 Web Remote
  proxy: the target IP must already be present in this entry's own
  discovered device inventory, never an arbitrary caller-supplied
  address -- tested against 5 real scenarios (known device, unknown IP,
  loopback, malformed input, multicast).
- **New: UPS (uninterruptible power supply) supervision**, using the
  real, standard UPS-MIB (RFC 1628), a vendor-neutral IETF standard
  supported by virtually every networked UPS (APC, Eaton, CyberPower,
  Vertiv, Tripp Lite). Every OID and enum value verified directly
  against the RFC text, including an official published erratum
  (eid4831) correcting a genuine typo in the RFC's own compliance
  statement for upsOutputSource. Deliberately scoped to the Ident and
  Battery groups (simple scalar OIDs) -- the Input/Output/Bypass groups
  are SNMP tables indexed by line number, and guessing an index without
  a real UPS to verify against risks silently reading the wrong line.
  Read-only by design. Tested against the confirmed enum mappings and a
  real unreachable-IP scenario.
- Added translation labels for the new `ups_hosts` config field to all 6
  languages immediately, avoiding the same gap fixed earlier this
  session.

## 0.15.23 — Node manufacturer coverage + zone form clarity


- **New: three missing Art-Net/sACN node manufacturers.** Artistic
  Licence (the original creators of Art-Net itself) was entirely absent
  from the catalog, along with Pathport and DMXking, two other widely
  used node brands. Added following the exact same conservative pattern
  as every other manufacturer entry: brand-name text matching, real
  product lines, no invented protocol behavior. Tested against realistic
  detection strings.
- Investigated the reported "new zone doesn't work" issue thoroughly:
  re-verified the 0.15.19 render fix is intact, traced the full backend
  chain (service handler, zone engine, channel parsing, sensor wiring)
  and found no rejection or mismatch anywhere in the current code.
  Channel parsing tested directly against the form's own default value.
  Root cause not identified this round -- needs the specific symptom
  (error shown vs. nothing happens vs. zone appears wrong) to go further.
- Added inline explanations for the zone creation form's more confusing
  fields (Fixture vs. Hue model, Source, per-lamp JSON override), which
  had no explanation in the interface at all.

## 0.15.22 — Translation completeness

Closed a gap flagged early in this project's audits but never fixed: 4 of
6 languages (German, Spanish, Italian, Dutch) were each missing 12 config
field labels, some predating this session (chaos_enabled, the three
dante_managed_* fields, projector_monitor_enabled) and some from this
session's new features (Ontime, QLC+, generic_switch_hosts). Without a
label, Home Assistant's config form falls back to showing the raw
snake_case key name.

- Added the missing labels to all 4 languages (best-effort technical
  translation, not professionally reviewed) plus the 7 newest keys to
  French and English.
- All 6 languages now have zero missing keys relative to the English
  reference, verified by direct comparison, not assumed.

## 0.15.21 — Deep verification of ~30 previously-unreviewed modules

Systematically reviewed every module not yet examined (audio_health,
audio_ptp, avb, device_model, discovery_pipeline, doctor, etc, flight_recorder,
green_go, health_engine, incident_center, korg, midi, network_health,
network_interfaces, projector_protocols, punchlight, rules, st2110, tally_ip,
timecode, and the new ha/protocols/core subpackages), verifying specific
technical claims against real sources rather than trusting docstrings alone.

- Verified against real sources: TSL UMD v5 packet framing (PBC field, 2048-byte
  max -- matches tslumd's own protocol documentation and the official TSL
  PDF), Green-GO BPX channel counts and model codes, PunchLight's
  MIDI-note-based design (correctly delegates RTP-MIDI transport to the
  host OS rather than reimplementing it).
- **Fixed a real typo**: the Green-GO wireless beltpack model code was
  written as `GGO-WPBX`; the real, confirmed model code (per Green-GO's
  own documentation) is `GGO-WBPX`. As written, this entry could never
  have matched a real device.
- Every module's docstring consistently follows this project's established
  conservative pattern (receive-only, no invented identity, no proprietary
  control) -- confirmed in the actual code, not just claimed in prose.

## 0.15.20 — Performance/network verification pass

Re-verified every prior performance fix actually survived in this
expanded base (nothing assumed): the dedicated SNMP thread pool, the 5
deferred blocking loads with their defense-in-depth wrapper, and the
generic switch hosts config field are all confirmed intact.

- Found one new instance of the same class of issue already fixed for
  SNMP: `projector_monitor.py`'s discovery/polling ran on Home
  Assistant's shared default executor, not an isolated pool. With
  several slow or unreachable projectors, this carried the same
  starvation risk already identified and fixed for SNMP. Added a
  dedicated `_PROJECTOR_EXECUTOR` (8 workers) and moved both call sites
  to it.
- Swept the entire codebase for any other module still using the shared
  default executor for real network I/O: none found.

## 0.15.19 — Audit of the dev36 base + two real UI bugs fixed

Adopted this expanded tree (225 files, 95 backend services, 52 custom
elements -- up from the 85/30 baseline) as the new working base after a
full audit rather than assuming it was correct.

- Fixed a version mismatch: `const.py` said 0.15.18, `manifest.json` said
  0.15.19. Reconciled everywhere (including the three User-Agent strings
  and the frontend cache-busting query string).
- Removed `.pytest_cache` and `__pycache__` artifacts that had been
  included in the source tree (should never ship).
- Full service-call audit (frontend ↔ backend): confirmed zero dead
  service calls and zero backend services unreachable from any UI, across
  all 95 real services. Re-confirmed the 6 known dynamic/ternary
  construction cases are genuine, not new gaps.
- Custom element registration audit: 52 defined, 32 referenced in the
  mount map, zero missing, zero duplicates.
- Verified the three newest service files (`pre_show`, `incidents`,
  `show_snapshot`) are correctly ungated: all three are pure bookkeeping
  (acknowledge a log entry, save/activate/delete a named config
  reference) with no real network emission, consistent with this
  project's established pattern.
- **Fixed a real bug**: typing a password into the security unlock/set
  dialog and then leaving the field (e.g. to click "Valider") could
  appear to wipe the typed value or swallow the click. Root cause: a
  `focusout`-triggered deferred re-render rebuilt the entire dialog's
  DOM (including the very button being clicked) at exactly the wrong
  moment. Fixed by suppressing that re-render entirely while a security
  dialog is open, in both places that could trigger it.
- **Fixed a real bug**: some module/section titles could render
  invisible (confirmed against a light-background screenshot). Root
  cause: none of the 52 custom elements use Shadow DOM, so every CSS
  class name is in one shared global namespace across the whole app --
  several `.title`/`.name` rules had no explicit color of their own and
  depended on inheriting a color from elsewhere, which isn't reliable
  when 52 unrelated components' styles can all cascade into the same
  selectors. Gave the module grid's title its own uniquely-named,
  explicitly-colored class, and added an explicit color to three other
  color-less `.title` rules found in the same audit.

## 0.15.19-dev36
- Topologie physique multi-NIC durcie sans suppression de module: identité switch des transitions basée sur interface + IP afin d’éviter les collisions entre réseaux isolés.
- LLDP enrichit le chemin physique d’un équipement uniquement après correspondance hostname exacte et unique; switch, port et vitesse de lien proviennent du poll LLDP/IF-MIB frais. Aucun VLAN n’est déduit du seul LLDP.
- Détection de déplacement étendue entre switches: un même `remote_system` LLDP unique peut produire `device_moved` avec ancien/nouveau switch, interface et port; les noms LLDP dupliqués restent ambigus et ne déclenchent pas cette conclusion.
- Topologie conserve maintenant l’interface réseau sur les nœuds d’inventaire et ne signale plus de faux conflit d’identité pour la même IP utilisée sur deux NIC distinctes.
- Santé des liaisons dans la Topologie Live associée au couple switch+n°/nom de port, et non plus au seul numéro de port qui pouvait colorer le mauvais lien sur plusieurs switches.
- Les ★ favoris remontent en tête de la liste Équipements de Topologie Live sans masquer les autres appareils.
- Tests de non-régression ajoutés pour IP identique sur NIC différentes, conflit réel sur une même NIC, conservation de l’interface et chemin LLDP sans VLAN inventé.
- Cache frontend incrémenté en dev36.

## 0.15.19-dev35
- Inventaire multi-NIC durci : une IP observée sur une interface explicite ne peut plus fusionner avec la même IP d’une autre interface.
- Une entrée mDNS sans interface peut encore être promue par une MAC stable lorsqu’ARP apporte ensuite l’interface réelle.
- Pipeline mDNS + enrichissement constructeur réutilisent désormais le même enregistrement : suppression du risque de doublon `candidate:IP` / `mdns:IP` sans supprimer de fonction.
- Un hostname DNS-SD sans adresse A/AAAA n’est plus stocké à tort dans le champ IP.
- Corrélation LLDP conservatrice : fusion automatique uniquement sur hostname explicite exact et unique; custom_name/display/model ne suffisent plus.
- Apple/Bonjour : un modèle Mac n’est renseigné que depuis un identifiant matériel explicite dans les propriétés TXT; constructeur/service seul ne déduit jamais le modèle.
- Cache frontend incrémenté en dev35.

## 0.15.19-dev34
- Audit temps réel Dante/PTP/AES67, MA-Net3, OSC/MIDI/PunchLight et Timecode, sans suppression de module.
- Doctor utilise désormais `dante_fresh_sources` plutôt que le nombre historique de sources Dante; une ancienne observation Dante ne peut plus provoquer à elle seule une alerte PTP actuelle.
- PTP sépare le dernier Grandmaster observé de `ptp_active_grandmaster_identity`; un Announce ancien reste une preuve historique mais n'est plus présenté comme leader courant.
- Audio Network Health et l'UI utilisent uniquement le Grandmaster PTP frais pour le Clock Master, tout en conservant le dernier leader comme historique.
- MA-Net3 distingue sessions/membres historiques et actifs (`active_session_count`, `live_member_count`, `state`), sans inventer nom/master de session.
- PunchLight expose santé et âge du dernier message; en erreur de lecture MIDI, les binary sensors deviennent indisponibles et la carte On Air affiche INDISPONIBLE au lieu de conserver un ancien état comme fiable.
- MTC conserve le durcissement dev30: publication seulement après huit quarter-frames frais et cohérents; ArtTimeCode/MTC restent receive-only.
- Tests de non-régression ajoutés pour GM PTP périmé, session MA historique et PunchLight en erreur.
- Cache frontend incrémenté en dev34.

## 0.15.19-dev33
- Audit profond amplificateurs / QLC+ / GDTF / Power Manager / switches, sans suppression de module.
- QLC+: `setFunctionStatus` ne peut plus réussir silencieusement sans réponse; timeout = erreur réelle et `last_command` distingue `confirmed_response` de `sent_unconfirmed`.
- QLC+: les commandes Virtual Console haute fréquence sans accusé protocolaire sont explicitement marquées envoyées mais non confirmées, jamais présentées comme un retour d’état.
- Power Manager: l’état ON/OFF est explicitement qualifié `commanded_dmx_output_not_physical_feedback`; une émission DMX n’est pas assimilée à un retour physique de relais.
- Inventaire: texte d’aide aligné sur dev30 — Auto/Surveiller/Ignorer filtre et priorise l’opérateur sans couper la découverte générale.
- Tests de non-régression ajoutés pour vérité des commandes QLC+ et preuve d’état Power Manager.
- Cache frontend incrémenté en dev33.

## 0.15.19-dev32
- Audit protocolaire projecteurs / ETC / RDM-RDMnet sans suppression de module.
- RDM/RDMnet: correction de fraîcheur critique. La relecture du cache du helper bridge ne rafraîchit plus artificiellement `last_seen`; seul `last_success` d’un poll réellement réussi sert de preuve temporelle.
- `rdm_refresh` réinjecte immédiatement l’inventaire issu du poll réussi avant publication.
- ETC/CEM3: provenance clarifiée dans le catalogue et l’UI. Les pages GET documentées et les requêtes de lecture fixes observées sur CEM3 sont distinguées; aucune écriture CEM3 n’est revendiquée.
- Projecteurs: audit de la chaîne multi-protocole existante (PJLink, Panasonic Web API, Digital Projection ASCII, Christie HS, Barco Pulse) et maintien des gates de contrôle sécurité + activation explicite.
- Test de non-régression RDM ajouté pour empêcher qu’un cache vieux maintienne un responder ONLINE.
- Cache frontend incrémenté en dev32.

## 0.15.19-dev31
- Audit fonctionnel renforcé: les services appelés littéralement par l’UI doivent désormais être déclarés dans `services.yaml` ET posséder un `hass.services.async_register(DOMAIN, ...)` backend réel.
- Cohérence globale vérifiée: 95 services déclarés / 95 services backend enregistrés, zéro écart dans les deux sens.
- Pre-Show amplificateurs corrigé: utilise les champs réels `online` et `error` de l’inventaire ampli; un ampli explicitement hors ligne ou en défaut ne peut plus passer silencieusement comme sain.
- Pre-Show conserve la preuve des amplis fautifs (clé/hôte/online/error) sans inventer de diagnostic constructeur.
- Aucun module/fonction existant supprimé pendant cette passe.
- Cache frontend incrémenté en dev31.

## 0.15.19-dev30
- Audit fonctionnel profond sans suppression de fonction/module existant.
- Découverte large restaurée: Auto/★ Favori/Ignoré sont des choix opérateur de filtrage/priorité et ne coupent plus les sondes d’identification HTTP/SNMP du scan général.
- Ajout manuel réel d’une IP au périmètre régie: UI `＋ IP ★` → service HA `register_manual_device` → validation IP backend → inventaire + override persistant `monitor`. La provenance reste explicitement `operator`, jamais présentée comme une découverte.
- Formulaire Pre-Show protégé contre les rerenders live pendant la saisie, sur le même principe que le correctif P1 Sécurité.
- MTC quarter-frame durci: huit pièces fraîches exigées, pièces >1 s rejetées et jeu consommé après publication afin de ne pas mélanger des cycles anciens/nouveaux.
- Audit frontend: 20 services littéraux, 18 cartes, 53 custom elements, zéro référence morte détectée.
- 47 tests exécutables passés; quatre tests Home Assistant restent exclus faute des dépendances HA complètes dans l’environnement de recette.

## 0.15.19-dev29
- P1 Sécurité: saisie du mot de passe conservée pendant les rerenders live; effacement uniquement sur Annuler ou succès.
- ★ Favoris de régie persistants via le vrai service `set_device_override` et `monitor_mode=monitor`; découverte générale inchangée.
- Filtres Tous/Favoris/Non favoris/Ignorés + recherche nom/IP/MAC/type/interface dans Inventaire et Auto Discovery; favoris triés en tête.
- Correction carte HA équipements: `monitor` remplace l'ancien test erroné `watch`.
- Audit profond: suppression du scaffold AUDIOFOCUS SCiO non fonctionnel/NotImplemented; aucune télémétrie propriétaire inventée.
- Cache frontend dev29 et tests de non-régression sécurité/favoris.

## 0.15.19-dev28
- Incident Center: cycle de vie persistant ACTIVE → ACKNOWLEDGED → RESOLVED avec identifiant stable.
- Acquittement réel via service backend `incident_acknowledge`; aucun état navigateur décoratif.
- Résolution automatique conservatrice uniquement sur événement explicite de récupération de la même famille.
- Durée, horodatage d’acquittement/résolution et compteur de récurrence exposés dans la vue.
- Un incident résolu qui réapparaît repasse ACTIVE et incrémente sa récurrence.

## 0.15.19-dev25
- Timecode relié au Flight Recorder: perte/récupération du signal, changement de source, transport et FPS journalisés sans qualifier un repositionnement de panne.
- Incident Center corrèle désormais naturellement les événements `timecode` avec réseau/PTP/DMX dans sa fenêtre temporelle, sans inférer de cause racine.
- Pre-Show Check ajoute Timecode: LOCK=PASS, signal précédemment vu puis perdu=FAIL, jamais observé=UNKNOWN car l'attente spectacle n'est pas connue.
- MIDI Time Code (MTC) quarter-frame reçu via le MIDI IN existant: publication uniquement après reconstruction des 8 pièces; aucun second port MIDI n'est ouvert.
- LTC reste explicitement non mesuré sans entrée/décodeur LTC réel.
- Cache frontend incrémenté en dev25.

## 0.15.19-dev20
- Historique par équipement dans Device Model et Inventaire : first/last seen, chemin physique actuel et événements corrélés.
- Corrélation étendue aux preuves LLDP `remote_system`, MAC et serial, toujours sans fuzzy matching.
- Historique basé sur une lecture bornée des 300 derniers événements persistés de `show_timeline.jsonl`, donc conservé à travers les redémarrages dans la limite de rétention/rotation.
- Événements lifecycle/LLDP, Dante/PTP, switch, amplificateur et projecteur rattachés uniquement sur identité explicite.
- Cache frontend incrémenté en dev20.

## 0.15.19-dev19
- Dante passif enrichi par endpoint: octets, paquets monitoring/mDNS, débit observé calculé après intervalle réel, fraîcheur et ports UDP observés.
- Page Dante existante affiche cette activité par endpoint sans la présenter comme débit audio ni comme télémétrie propriétaire Dante.
- Flight Recorder LLDP: événements explicites device_appeared, device_disappeared et device_moved avec ancien/nouveau port.
- Corrélation physique strictement basée sur identité LLDP explicite; aucun fuzzy matching.
- Cache frontend incrémenté en dev19.

## 0.15.19-dev19
- Page Dante/Audio existante restructurée en véritable centre Audio Network Health; aucune seconde page Dante parallèle.
- Clock Status: présence/fraîcheur PTP, Grandmaster PTPv2 décodé et séparation explicite entre jitter d’arrivée et offset/stabilité Dante non mesurés.
- Bandwidth/Layer 1: RX/TX par port, pourcentage de charge calculé sur vitesse réelle, warning Show Network à 70% et critique à 85%.
- Packet Health: compteurs d’erreurs IF-MIB affichés sans les assimiler abusivement à des pertes Dante.
- Sections Routing/Subscriptions, Redundancy Primary/Secondary, Unicast/Multicast/IGMP et Audio Peak/RMS présentes avec état NON MESURÉ quand aucune télémétrie fiable n’existe.
- Doctor alerte si Dante est observé sans PTP frais et sur ports >=70/85%.
- Flight Recorder journalise les franchissements de bandes de charge réseau.
- Politique backend audio_network_health: measured/observed/unavailable, jamais de métrique Dante simulée.
- Cache frontend incrémenté en dev18.

## 0.15.19-dev17
- Switch telemetry: compteurs IF-MIB/ifXTable RX/TX et erreurs RX/TX par port en lecture seule.
- Débits RX/TX calculés uniquement après deux mesures Counter64 réelles; reset/wrap => débit indisponible, jamais négatif inventé.
- Topologie: tuiles et détails de ports affichent trafic et compteurs d'erreurs lorsqu'ils sont disponibles.
- Flight Recorder journalise les hausses réelles des compteurs d'erreurs et les changements LLDP avec port local explicite.
- Doctor ajoute un contrôle des compteurs d'erreurs des ports supervisés.
- Recette frontend renforcée: navigation, boutons/actions, services et cartes Lovelace audités statiquement avant packaging.
- Cache frontend incrémenté en dev17.

## 0.15.19-dev16
- Topologie régie interactive : vue switch → ports → voisin LLDP/équipement.
- Filtres par interface réseau et VLAN dans la vue Topologie.
- Détail cliquable des ports : état, vitesse, alias, voisin LLDP et port distant.
- Détail équipement conservant les preuves et liaisons physiques explicites.
- Aucun lien physique n’est inventé lorsque LLDP/inventaire ne fournit pas de preuve.
- Cache frontend incrémenté en dev16.

## 0.15.19-dev13
- Nouvelle carte Lovelace `custom:show-network-regie-card`: dashboard Régie responsive prêt à l’emploi.
- Vue synthèse: Timecode, PunchLight/On Air, Show Snapshot, grandMA3, Dante, PTP, Doctor, projecteurs et Power Manager.
- Univers DMX optionnels explicitement choisis via `dmx_entities`; aucun univers n’est deviné.
- Les sous-cartes continuent d’afficher INCONNU si l’entité réelle manque; aucune donnée de démonstration.
- Correction du cache frontend: l’URL du module JS porte maintenant la version dev13.

## 0.15.19-dev12
- Réorganisation UX du menu Modules/Configuration par parcours métier : Réseau, Protocoles, Équipements, Contrôles, Home Assistant, Sécurité/Diagnostic, Maintenance.
- Ajout d’un parcours conseillé en 6 étapes et d’explications fonctionnelles dans les pages modules.
- Distinction plus claire entre observation passive, automatisations HA et commandes actives protégées.
- Aucun changement de backend ou de gate de sécurité pour cette réorganisation : la navigation n’active aucune fonction implicitement.

## 0.15.19-dev9
- Flight Recorder relié au Device Model par preuves explicites (IP/source/host/id), sans fuzzy matching.
- Doctor expose le dernier incident et les équipements corrélés.
- UI Flight Recorder affiche les identifiants équipements reliés.
- Audit statique des boutons/actions: les actions littérales UI sont présentes dans services.yaml; boutons dynamiques vérifiés séparément.


### 0.15.19-dev8 — Home Assistant asyncio I/O fix
- Fixed blocking configuration-backup I/O triggered by DMX→HA zone/mapping and OSC target service actions.
- Runtime service handlers now persist stores and run ConfigBackupManager backup/prune work through `hass.async_add_executor_job`.
- Keeps synchronous compatibility wrappers only for non-HA callers/tests; Home Assistant service paths use async variants.
- Prevents `open`, `write_text`, `scandir`, `glob` and `shutil.rmtree` from the backup workflow running on HA's event loop.
### 0.15.19-dev7 — Flight Recorder infrastructure corrélée
- Le Flight Recorder journalise désormais les changements de Grandmaster/présence PTP déjà observés.
- Ajout des transitions Dante device lost/recovered à partir de la fraîcheur réellement mesurée.
- Ajout des changements switch port up/down et voisins LLDP lorsque la télémétrie SNMP/LLDP est disponible.
- Ajout des pertes/récupérations et changements d’erreur des amplificateurs supervisés.
- Ajout des pertes/récupérations et télémétrie stale/recovered des projecteurs supervisés.
- Aucun polling supplémentaire : ces événements réutilisent exclusivement les données déjà collectées.
- Vérification de compilation Python et syntaxe JavaScript effectuée.


### 0.15.19-dev6 — Flight Recorder avancé
- Analyse bornée des 100 derniers événements du journal, avec classification info/warning/error/recovery.
- Corrélation temporelle ±20 s autour des incidents, sans déduction de cause.
- Panneau « Que s’est-il passé ? » : dernier incident, événements voisins, familles de protocoles et timeline récente.
- Les données restent issues du journal existant : aucune capture brute de paquets ni trafic réseau supplémentaire.

## 0.15.19-dev5
- Show Snapshot / Référence spectacle persistante.
- Comparaison appareils, sources DMX et identité PTP observée.
- Services create/activate/delete et panneau UI dédié.
- Aucun état réseau n’est inventé : correspondances par identités stables uniquement.


## 0.15.19-dev4 — DMX Universe Matrix + Flight Recorder
- Ajout d’une matrice passive par protocole/univers/source avec FPS, priorité, canaux actifs, jitter, pertes de séquence et âge de dernière réception.
- Parsing passif sACN étendu au CID E1.31 et au Source Name; aucune émission ni réponse réseau ajoutée.
- Flight Recorder: événements `source_seen`, `source_lost`, `source_recovered`, `cid_change` et `priority_change`.
- Détection `LIVE/LOST` après 3 s sans trame, sans supprimer l’ancienne source de la matrice.
- Interface DMX View enrichie avec tableau multi-source et avertissement visuel.
## 0.15.19-dev — Health Engine foundation

- Added an evidence-based cross-protocol `ShowNetworkHealthEngine`.
- Correlates network-interface freshness, DMX multiple sources and sACN sequence loss, topology staleness, explicit PTP health, archive/flight-recorder health and HA host capacity.
- Adds `sensor.show_network_health` with bounded diagnostic attributes.
- The engine never invents a root cause: warnings are emitted only from observed or explicitly published evidence.
- Added unit coverage for multiple DMX sources/loss and the no-invented-PTP-fault rule.

# Changelog

## 0.15.18 — Dante accessory product names

Enriched the generic Audinate catalog entry (previously just "Dante-
enabled devices") with the real, well-known dedicated Dante accessory
product lines: AVIO adapters, Dante-MY16, Domain Manager, Via, Controller.

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

## 0.15.19-dev — Device Model + Show Network Doctor
- Added a central, evidence-based cross-protocol Device Model consolidating inventory/topology facts without guessing identity.
- Stable identity conflicts (e.g. multiple MAC/serial identities observed on one IP) are surfaced explicitly.
- Added read-only Show Network Doctor with checks for NIC state, DMX multi-source, sACN/DMX sequence loss, stale topology, identity conflicts, PTP state, host load and Health Engine status.
- Added `show_network_devices` and `show_network_doctor` sensors with bounded diagnostic attributes.

## 0.15.19-dev3 — Doctor UI + enriched live topology
- Added a dedicated Show Network Doctor cockpit panel with OK/info/warning/error summaries, expandable evidence, and conservative device correlation.
- Added Doctor to the supervision modules and dashboard state summary.
- Reworked Topology Live to show consolidated device identity, health, IP, manufacturer/model, protocols and clickable device details.
- Topology device details expose interface/VLAN, switch/port, evidence sources and observed links when these facts are available.
- No active network probe or inferred fault cause was added; the UI explicitly avoids attaching a device when evidence is insufficient.

## 0.15.19-dev10 — Apple / Timecode / Home Assistant dashboard
- Apple/macOS: extension de la découverte Bonjour via le Zeroconf partagé de Home Assistant (`_ssh`, `_rfb`, `_airplay`, `_raop`, `_companion-link`, `_device-info`).
- Identification Apple volontairement conservatrice : Apple n'est confirmé que si les données Bonjour/TXT/nom contiennent une preuve Apple/Mac explicite; SSH/AirPlay seuls ne suffisent pas.
- Les Mac confirmés sont fusionnés dans l'inventaire/Device Model avec leurs services observés (Bonjour, SSH, Screen Sharing, AirPlay).
- Timecode Art-Net enrichi : WAITING/LOCKED/LOST, âge, FPS, drop/non-drop, source et transport.
- Ajout d'une vraie vue Timecode Live au module DMX.
- Ajout de deux cartes Lovelace natives au bundle Show Network : `custom:show-network-timecode-card` et `custom:show-network-onair-card`.
- Carte On Air basée uniquement sur les états PunchLight réels disponibles : gris OFF, vert READY, rouge ON AIR. Aucun état orange n'est simulé.

## 0.15.19-dev11 — Lovelace régie status tiles
- Added Lovelace status cards for grandMA3/MA-Net3, PTP, Dante, Show Network Doctor, Show Snapshot, PJLink projectors, Power Manager and individual DMX universes.
- Cards consume existing Home Assistant entities; missing data is shown as UNKNOWN rather than inferred as healthy.
- Power card is intentionally status-only: active power commands remain in the existing secured Power Manager instead of exposing an ambiguous generic power button.
- DMX card requires an explicit universe binary_sensor entity, preventing accidental selection of the wrong universe.
- All status cards open Home Assistant more-info for the underlying entity on tap; no decorative service buttons were added.

## 0.15.19-dev15
- Dashboard Régie enrichi avec infrastructure : interfaces réseau, switches/ports, amplificateurs, Apple/Mac et inventaire consolidé.
- Nouvelle carte `show-network-interfaces-card` basée sur l'inventaire NIC réel du serveur Home Assistant.
- Nouvelle carte `show-network-switches-card` basée sur `switch_telemetry` et l'état réel des ports observés.
- Nouvelle carte `show-network-amplifiers-card` basée sur l'inventaire/télémétrie amplificateurs existants.
- Nouvelle carte `show-network-apple-card` : ne compte que les appareils Apple confirmés par le Device Model; aucun raccourci SSH/AirPlay => Mac.
- Nouvelle carte `show-network-devices-card` pour l'inventaire consolidé et les conflits d'identité.
- Les capteurs réseau exposent maintenant en attributs la liste des interfaces locales et le résumé network_health pour les dashboards.
- Cache-buster frontend mis à jour vers dev14.

## 0.15.19-dev21
- Refonte visuelle de la page Dante/Audio existante vers une console Audio Réseau plus lisible, inspirée de la maquette validée.
- Bandeau Dante/PTP, Clock Master, bande passante et événements regroupés en KPIs opérationnels.
- Ajout d'une banque de vumètres Peak/RMS réellement câblée aux entités de niveaux audio lorsqu'elles existent; aucun niveau n'est animé ou inventé sans télémétrie.
- Tableau appareils Dante conservé et intégré à la nouvelle hiérarchie visuelle.
- Les blocs avancés Clock, Layer 1, latency, subscriptions, redundancy, multicast/IGMP et journal restent disponibles sous la synthèse.
- Cache frontend incrémenté en dev21.

## 0.15.19-dev22
- Dante Managed API: ajout d'une intégration GraphQL **lecture seule** optionnelle pour Dante Director / Dante Domain Manager (DDM >= 1.5), basée sur les requêtes documentées par Audinate.
- La page Audio existante affiche désormais les statuts de domaine, appareils, subscriptions RX et anomalies de subscription quand cette source officielle est configurée.
- Signal Presence est distingué des vrais niveaux Peak/RMS : jamais converti artificiellement en dBFS. Les vumètres restent alimentés uniquement par de vraies valeurs de niveau.
- La matrice de capacités Audio Health documente désormais la voie officielle Managed API au lieu de classer les subscriptions comme définitivement indisponibles.
- Cache frontend incrémenté en dev22.

## 0.15.19-dev23
- Ajout Incident Center: corrélation factuelle des symptômes du Flight Recorder, familles et équipements reliés par preuve, sans inférence de cause racine.
- Ajout Pre-Show Check read-only: READY / NOT_READY / CHECK avec PASS / FAIL / UNKNOWN; UNKNOWN n'est jamais assimilé à PASS.
- Pre-Show contrôle référence spectacle, DMX observé, Dante/PTP, switches, amplificateurs et projecteurs selon les données réellement disponibles.
- Topologie Live: coloration des ports selon état, erreurs et charge mesurée (normal / >=70% / >=85%).
- Correction importante du calcul de charge: les seuils utilisent désormais les compteurs dérivés rx_mbps/tx_mbps réellement produits par la télémétrie SNMP, et non des champs rx_bps/tx_bps inexistants.
- Cache frontend incrémenté en dev23.

## 0.15.19-dev24
- Show Snapshot/Compare enrichi : IP/MAC, firmware, interface, VLAN, switch/port et vitesse de lien par appareil lorsque mesurés dans les deux captures.
- Comparaison read-only des ports switch : état, vitesse et voisin LLDP explicite.
- Comparaison des subscriptions Dante uniquement lorsque Dante Managed API était disponible dans les deux snapshots.
- Vue Snapshot affiche les compteurs référence → actuel pour appareils, DMX, switches et subscriptions Dante.
- Timecode devient un module de navigation dédié tout en restant disponible avec DMX ; affichage du compteur de paquets, intervalle du dernier paquet et fraîcheur.
- Aucun saut de timecode n'est classé automatiquement comme panne : un cue peut légitimement repositionner le TC.
- Cache frontend incrémenté en dev24.

## 0.15.19-dev26
- Pre-Show: profil spectacle persistant entièrement optionnel; aucun profil n'est requis pour utiliser Show Network.
- Les attentes du profil ajoutent uniquement des diagnostics PASS/FAIL; elles ne bloquent aucune fonction ni commande.
- Attentes configurables: univers DMX, équipements explicites, Timecode, Dante, PTP, switches, amplificateurs et projecteurs.
- Désactivation immédiate du profil pour revenir au diagnostic général.
- UI Pre-Show: édition rapide nom/univers/appareils et indication explicite « diagnostic uniquement · jamais bloquant ».

## 0.15.19-dev28
- Dashboard HA : nouvelles cartes Incident Center et Pre-Show intégrées à la carte Régie, sans rendre le Pre-Show obligatoire.
- Incident Center : tri par gravité, compteurs et symptômes détaillés; corrélation seulement, aucune cause racine inventée.
- Topologie Live : résumé des ports en avertissement/critique et coloration des liaisons lorsque leur port local possède une preuve de santé correspondante.
- Recette frontend/cache incrémentée en dev27.

## 0.15.19-dev29
- P1 Sécurité: la saisie du mot de passe survit désormais aux rerenders live du panneau; elle n'est effacée que sur annulation ou succès.
- Favoris de régie réels: l'étoile ★ écrit le mode persistant `monitor` via `set_device_override`; retirer l'étoile revient à `auto` sans réduire la découverte générale.
- Inventaire et découverte IP: favoris triés en tête, filtres Tous/Favoris/Non favoris/Ignorés et recherche nom/IP/MAC/type/interface.
- Correction carte HA équipements: le compteur utilisait `watch` alors que l'enum backend réel est `monitor`.
- Cache frontend incrémenté dev29.
- Audit fonctions: suppression du scaffold AUDIOFOCUS SCiO non câblé/NotImplemented; l’identification Audiofocus par preuves réseau et l’ajout manuel d’ampli restent disponibles.

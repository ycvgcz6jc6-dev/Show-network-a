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

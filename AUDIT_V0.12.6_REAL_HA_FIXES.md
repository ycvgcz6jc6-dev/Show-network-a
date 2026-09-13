# Show Network v0.12.6 — corrections issues des tests Home Assistant réels

## Corrections intégrées

- `ha/action_dispatcher.py`: le worker permanent `show-network-ha-actions` utilise désormais `hass.async_create_background_task(...)`. Il n'est donc plus compté parmi les tâches que Home Assistant attend pour terminer son démarrage.
- `runtime/setup.py`: le premier scan mDNS constructeur est également lancé en background task.
- `config_flow.py`: l'OptionsFlow n'instancie plus manuellement un `DmxMonitorConfigFlow` sans contexte HA. Les choix réseau/USB/MIDI et le schéma sont maintenant partagés via des helpers qui utilisent directement `self.hass`. Le parsing JSON de la liste des projecteurs est aussi appliqué aux options.
- `static/show-network.js`: ajout d'une navigation vers les modules déjà présents et câblés : DMX/Art-Net/sACN, ENTTEC, zones et mappings DMX→HA, OSC/MIDI/PunchLight, Rule Builder/watchdogs, réseau/topologie/découverte, audio réseau, vidéo/projecteurs, MA-Net3, inventaire, HA Builder, constructeurs, reliability, sécurité et archive.
- `static/show-network.js`: ajout d'un accès vers la page Home Assistant de configuration générale de l'intégration pour les interfaces réseau, univers, Dante/PTP/audio, ENTTEC, OSC/MIDI, watchdogs, capacité réseau et projecteurs.
- `static/show-network.js`: le statut de sécurité accepte les chaînes d'état HA `True/False` aussi bien que `true/false/on/off`, et les actions mot de passe/déverrouillage/verrouillage affichent immédiatement un retour visuel après succès. Les erreurs de service restent affichées dans le panneau.
- Version et cache frontend portés à `0.12.6`.
- Le correctif v0.12.5 de `services.yaml` pour `projector_power.fields["on"]` est conservé.

## Validation effectuée hors Home Assistant réel

- `python -m compileall -q custom_components`: OK
- `node --check custom_components/dmx_monitor/static/show-network.js`: OK
- `pytest -q`: **69 tests passés**

Ces validations sont statiques/unitaires. Elles ne remplacent pas le test dans une vraie instance Home Assistant. Le prochain test réel doit notamment confirmer : fin de démarrage sans `show-network-ha-actions` bloquant, navigation des modules, OptionsFlow, et mise à jour visuelle de la sécurité.

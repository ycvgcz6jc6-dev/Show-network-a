# Show Network v0.12.9 — étapes 3 et 4

## 🟢 Étape 3 — DMX réellement configurable
- Interface réseau DMX sélectionnable via OptionsFlow HA.
- Art-Net activable/désactivable.
- sACN activable/désactivable.
- Univers DMX `1,2,10-12` transmis au receiver et utilisés pour les groupes multicast sACN.
- Filtre IP source DMX optionnel; vide = toutes les sources.
- Le panneau Réseau affiche l'état Art-Net/sACN, le filtre source et les univers.

## 🟢 Étape 4 — MA-Net3 configurable
- Interface MA-Net3 indépendante sélectionnable.
- Écoute MA-Net3 activable/désactivable.
- L'interface effective et l'état sont publiés dans `show_network_config`.

## 🟢 Application des réglages
- Une modification OptionsFlow provoque maintenant le reload de l'entrée Show Network afin de redémarrer les listeners avec les nouveaux réglages.

## Validation statique
- `python -m compileall -q custom_components`: OK
- `node --check custom_components/dmx_monitor/static/show-network.js`: OK
- `pytest -q`: 79 tests réussis

Pas de validation réelle sur Home Assistant / réseau physique dans cet environnement.

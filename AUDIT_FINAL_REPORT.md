# Show Network v0.10.92 — rapport d'audit statique final

## Source auditée
`show_network_v0.10.90_final.zip` — reprise directe de l'arbre réel, puis comparaison avec la passe v0.10.91 disponible dans la bibliothèque.

## Résultat

### 🟢 Implémenté et raccordé
- Config Flow / Reconfigure / Options Flow → runtime.
- `entry.runtime_data` renseigné.
- 43 services présents dans `services.yaml` et 43 handlers enregistrés.
- DMX/sACN/Art-Net : réception réelle via `lighting_receiver.py` et `DmxNetworkReceiver`.
- MA-Net3, PTP, Dante, AES67, ST2110/AVB passifs, ENTTEC, PunchLight, OSC, MIDI, Rule Builder, mappings/zones DMX→HA, projecteurs PJLink et archives/backups : conservés uniquement lorsqu'un chemin runtime réel existe.
- Multi-NIC : interfaces distinctes pour DMX, MA, PTP, Dante et audio lorsque configurées.
- Nettoyage du double backup `startup`.
- Nettoyage du compteur Green-GO `green_go_switches`, qui ne pouvait pas être alimenté par la découverte conservative actuelle.
- Catalogue ELC mis à jour avec des caractéristiques vérifiées sur les pages constructeur.

### 🟡 Catalogue / documentation uniquement
- Profils fabricants, profils spectacle/switches, tables de capacités et autres références descriptives restent présents lorsqu'ils ont une valeur documentaire explicite.
- Ils ne sont pas présentés comme des sondes live et ne sont pas utilisés pour fabriquer une identité réseau à partir d'un simple nom/IP.

### 🔴 Supprimé car mort, décoratif, doublon ou non raccordable honnêtement
- `protocols.py` : duplicate des parseurs/UDP non utilisé ; le chemin réel est `lighting_receiver.py`.
- `auto_discovery.py` : scanner TCP générique non raccordé.
- `diagnostics.py` : helper non raccordé au mécanisme HA diagnostics.
- `dmx_mapping.py` : second moteur de mapping DMX non consommé.
- `dmx_view.py`, `dmx_view_model.py` : modèles Python non utilisés par le frontend livré.
- `entities_model.py`, `ha_adapter.py`, `ha_discovery_sources.py`, `ha_targets.py` : abstractions non raccordées aux plateformes runtime.
- `health_model.py`, `network_identity.py`, `network_inspector.py`, `network_protocols.py`, `osc_trace.py` : helpers diagnostics sans consommateur runtime.
- `rve.py`, `show_diagnostics.py`, `show_network.py` : modèles isolés sans alimentation runtime.
- `korg.describe_nanokontrol2()` : helper documentaire non appelé ; l'identification KORG réellement utilisée reste conservée.

## Contrôles effectués
1. `compileall` sur `custom_components` et `tests` : **OK**.
2. Vérification AST des imports relatifs après suppression : **aucun import cassé détecté**.
3. Croisement `services.yaml` ↔ `async_register`: **43/43, aucun manque, aucun extra**.
4. Intégrité de l'archive finale avec `unzip -t`: **OK**.
5. Recherche des chemins morts ciblés et fonctions documentaires non consommées : effectuée.

## Ce qui n'est PAS affirmé
- Aucun test Home Assistant réel : l'environnement d'audit n'embarque pas `homeassistant`, et `pytest` s'arrête sur `ModuleNotFoundError` lors de l'import du package.
- Aucun test réseau live, aucun test avec MA3, Luminex, Green-GO, ELC, KORG, PunchLight, projecteur ou matériel DMX réel.
- Aucune commande constructeur n'a été exécutée pendant l'audit.

## Sources constructeur vérifiées pour ELC
- ELC dmXLAN Node 1S : https://elclighting.com/products/node1s
- ELC dmXLAN NodeGBx 8 : https://www.elclighting.com/products/nodegbx8
- ELC dmXLAN NodeHD 24 : https://www.elclighting.com/products/nodehd24
- ELC catalogue produits : https://www.elclighting.com/products
- ELC Buddy : https://www.elclighting.com/products/buddy

## Version livrée
**Show Network v0.10.92**

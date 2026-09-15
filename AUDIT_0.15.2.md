# Audit 0.15.2 EXPERIMENTAL — 15 septembre 2026

## Base et portée

Base effective : FULL 0.15.0 fourni par l'utilisateur, SHA-256 `ce44da58a326696b67f83ef943e6e3d8e15f9a9835aee5226286bc8bbb8755ec`. L'archive 0.15.1 Hardening n'était pas disponible. Ses corrections décrites dans la conversation ont été réappliquées à cette base, puis les évolutions CEM3 ont été intégrées. Aucune identité binaire avec 0.15.1 n'est revendiquée.

Les 171 chemins de fichiers de la source sont conservés. Aucune phase précédente n'a été retirée ; helpers, dashboards, catalogues, ressources visuelles et 80 services sont conservés. Le comparatif exact est dans `SOURCE_COMPARISON.json`. L'audit Phase 13 inclus est un document historique fourni avec la source ; ses anciens résultats ne remplacent pas `TEST_RESULTS.md` pour cette livraison.

## Modifications principales

- `etc_cem3.py` : ancien poller heuristique remplacé par un client asynchrone à requêtes fixes ; identité forte, trois parsers XML, jointure par UDN/space/circuit, gestion du cache, fraîcheur, arrêt, multi-NIC et découverte bornée. Les anciens parsers HTML publics sont conservés.
- `cem3_websocket.py`, frontend et coordinator : transfert des circuits depuis le cache au panneau authentifié, hors attributs Recorder ; états et capteurs agrégés conservés. Pas de commande CEM3 ni d'entité par circuit.
- Configuration : ajout optionnel de la découverte et d'une sélection multiple de NIC, compatibilité de l'ancien choix d'interface et des IP manuelles.
- System : reconnaissance des libellés visibles sur la capture utilisateur, dont le nom « grada salle A2 (Rack #2) » et « No Data DMX port A ». Les températures/charges absentes restent inconnues.
- Durcissement : 44 blocs d'exception auparavant silencieux journalisés au niveau DEBUG ; aucune exception `CancelledError` n'est absorbée par ces handlers sous Python 3.12. DOMAIN centralisé, RLock sur le State Store et le tracker, copies isolées, publication DMX 5 Hz (pipeline règles/mappings inchangé à 20 Hz).
- Unload : si HA refuse de décharger les plateformes, le runtime est conservé. Sinon les ressources réseau et tâches sont arrêtées.

## Limites connues

Découverte IPv4/HTTP port 80, désactivée par défaut et sans balayage sur `0.0.0.0`. Maximum 32 racks ; quatre requêtes simultanées ; huit candidats par cycle. Les grands sous-réseaux nécessitent des voisins ARP connus ou un ajout manuel. Les racks découverts sont mémorisés seulement jusqu'au reload. Les réseaux différents réutilisant la même IP ne sont pas distingués. Les valeurs de propriétés anciennes sont visibles avec leur indication de fraîcheur ; aucune commande de correction n'est proposée.

La page System brute du firmware n'a pas été récupérée. La validation d'identité est volontairement stricte et peut refuser un firmware présentant un HTML différent. Voir les limites de test dans `TEST_RESULTS.md`. Aucun téléchargement/upload de configuration, firmware, ni activation de preset n'a été effectué.

## Résultat

191 tests Python réussis ; compilation Python et syntaxe JS valides ; test de rendu de 144 circuits et du cache WebSocket réussi. Tous les tests et fixtures utilisés sont inclus dans FULL ; UPDATE_ONLY contient tout le composant d'intégration.

## Exceptions silencieuses instrumentées par fichier

- `dmx_circuit_monitor.py` : 1
- `backup.py` : 2
- `network_discovery.py` : 2
- `dmx_ha_mapping_storage.py` : 1
- `dmx_scene_bank.py` : 1
- `aes70_monitor.py` : 3
- `etc_cem3.py` : 1
- `diagnostics_export.py` : 2
- `lighting_receiver.py` : 5
- `vendor_discovery.py` : 3
- `dante.py` : 1
- `security.py` : 2
- `osc_receiver.py` : 1
- `audio_ptp.py` : 1
- `projector_monitor.py` : 2
- `projector_protocols.py` : 5
- `archive.py` : 3
- `network_interfaces.py` : 1
- `signal_watchdog.py` : 2
- `enttec.py` : 1
- `punchlight_network.py` : 1
- `power_manager.py` : 1
- `runtime/setup.py` : 2

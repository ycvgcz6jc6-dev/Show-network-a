# Audit v0.14.7 — UI / Discovery / Power / Audio

## Statut de validation

Validation effectuée ici : analyse statique, tests unitaires, compilation Python et syntaxe JavaScript. **Aucun test Home Assistant réel, aucun switch/ampli/projecteur réel et aucune sortie DMX physique n'ont été exécutés par l'assistant.** Le DMX receive-only v0.14.3+ n'a pas été réécrit.

## 🟢 Implémenté et connecté

- État des `<details>` conservé lors des rerenders; les composants en cours d'édition (`:focus-within`) ne sont plus reconstruits par le refresh live.
- Séparation UI : Rule Builder / Signal Watchdogs / DMX Circuit Monitor / Power Manager.
- DMX Circuit Monitor persistant, receive-only : groupes nommés, circuits, seuils, état ON/OFF/PARTIAL/SIGNAL_LOST.
- Power Manager persistant : plusieurs boutons, nom et icône libres, circuits, valeurs ON/OFF, délais individuels, OFF en ordre inverse, maintien de trame, sACN multicast/unicast, Art-Net, ENTTEC USB Pro. Exécution bloquée si le verrou Show Network n'est pas déverrouillé.
- Security UI : suppression de `prompt()`; formulaire mot de passe intégré.
- Device Inventory : mode persistant `auto / monitor / ignore`. `ignore` évite les sondes HTTP/SNMP actives; le trafic broadcast déjà reçu peut toujours être observé passivement.
- Découverte : correction de deux défauts BER SNMP qui empêchaient des réponses réelles d'être interprétées : INTEGER zéro mal encodé et parser lisant l'OID de la varbind au lieu de sa valeur. `sysObjectID` est maintenant décodé.
- Luminex : preuve MAC enregistrée (`D0:69:9E` et IAB `00:50:C2:9C:9`), marqueurs HTTP/mDNS, SNMP sysObjectID/texte. Pas de classification par IP.
- Switches : identité SNMP read-only multi-marques + télémétrie MIB-II/IF-MIB bornée (uptime, nombre d'interfaces, nom, operStatus, vitesse) après preuve de switch; température Luminex seulement si l'OID répond.
- Découverte HTTP read-only bornée sur les voisins ARP, avec marqueurs explicites Luminex et grandes marques réseau/audio.
- Dante Geek : `protocol_rx_diagnostics` contient maintenant réellement les snapshots Dante/PTP/audio; sources, ports, types de paquets, âge/fraîcheur, endpoints mDNS, versions/domaines PTP et compteurs Sync/FollowUp/Announce/Delay sont affichables.
- AES67 : enrichissement SDP avec encoding, sample rate, channels, ptime, clock/sync-time lorsque présents.
- MA-Net3 : classification uniquement depuis des marqueurs texte explicitement observés dans le payload (onPC, xPort Node, Processing Unit, NPU/RPU, Node, Console). Les IP du site ne servent jamais à classifier.
- ETC Sensor3/CEM3 : page remise dans les modules; les capacités documentées restent clairement `CATALOGUE` tant qu'aucun transport live n'est raccordé.
- Branding : logo complet + icône transparents intégrés au bundle statique; header PRO utilise le logo.

## 🟡 Catalogue / partiel / à valider sur matériel

- L-Acoustics, d&b, Powersoft, Lab Gruppen/Lake, QSC, Yamaha : détection candidate/confirmée uniquement si marqueur mDNS/HTTP/Dante explicite. Les API propriétaires de télémétrie ne sont pas inventées.
- Luminex : l'identité peut maintenant fonctionner sans SNMP grâce au MAC/HTTP; les ports/température exigent encore une réponse SNMP réelle. Certains GigaCore ont SNMP désactivé tant qu'il n'est pas activé côté switch.
- Dante : la vue Geek est enrichie mais Show Network n'implémente pas Dante Controller; noms de canaux/subscriptions ne sont pas fabriqués sans protocole observé/documenté.
- AES67 : SAP/SDP + PTPv2 sont raccordés; absence de SAP reste affichée comme « non observé ».
- MA : une station sans marqueur de type reste « non classifiée » même si l'utilisateur sait physiquement que c'est un node/une console.
- ETC Sensor3/CEM3 : catalogue seulement pour les températures/tensions/load monitoring tant qu'un transport live documenté n'est pas implémenté.

## 🔴 Retiré / évité

- Aucun `prompt()` navigateur pour la sécurité.
- Aucun classement MA basé sur sous-réseau/IP.
- Aucun switch déclaré Luminex uniquement parce qu'il répond à ARP.
- Aucune température d'ampli/ETC/projecteur inventée.
- Aucun mélange Power Manager ↔ Watchdog ↔ Circuit Monitor.

## Validation locale

- `python -m compileall -q custom_components` : OK
- `node --check custom_components/dmx_monitor/static/show-network.js` : OK
- `pytest -q` : **135 passed**

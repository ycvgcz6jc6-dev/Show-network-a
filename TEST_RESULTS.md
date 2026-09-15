# Résultats des tests — Show Network 0.15.2 EXPERIMENTAL

## Résultat final

**191 tests Python réussis, 0 échec** (Python 3.12.14, macOS ARM64, dernière exécution : 2,53 s).
Compilation de tous les fichiers Python du FULL : OK. Syntaxe du frontend JavaScript : OK.
Test JavaScript du panneau : 144 circuits répartis sur deux racks, deux NIC, état hors ligne et échappement HTML : OK.
Validation JSON de la distribution : OK. 80 services déclarés et enregistrés, identiques à la source : OK.

## Ce qui a réellement été testé

- Parsers : réponse réelle de 72 circuits et fichier original des propriétés ; espaces ; XML malformé, doublons, attributs manquants, valeurs invalides, taille excessive et déclarations d'entités refusées.
- System : fixture synthétique et structure HTML reconstruite à partir des libellés visibles sur la capture réelle (nom, version, tensions, fréquence, erreur DMX). Aucune fixture HTML brute de System n'était disponible.
- HTTP : vrai serveur local et vrais sockets ; GET/POST exacts, liaison source localhost, interdiction des commandes non autorisées et des redirections, réponse trop volumineuse, timeout, fermeture puis création d'un nouveau client. Port éphémère de test, aucun rack physique contacté.
- Découverte : plusieurs sous-réseaux simulés, interfaces sélectionnées, voisins ARP filtrés, lots de huit, temporisation des scans, identité forte avant POST, refus d'un rack incomplet, plafond de racks, absence de scan sans NIC explicite.
- État : multi-rack, cache 60 s des propriétés, invalidation après changement d'identité des circuits, fraîcheur par section, erreur partielle, panne avec conservation de la dernière lecture, snapshots isolés.
- Cycle de vie : annulation d'une lecture en cours, arrêt/recréation du client, fermeture des ressources ; exécution de la fonction unload HA avec doubles minimaux, y compris refus de déchargement des plateformes.
- DMX : concurrence de huit lecteurs/rédacteurs sur le State Store et le tracker ; éviction bornée ; publication à 5 Hz ; libération/réouverture de sockets UDP locaux via les chemins Art-Net et sACN (ports éphémères, sans toucher aux ports de production).
- Accès panneau : contrat WebSocket cache uniquement, multi-entrée, déchargement d'entrée et enregistrement unique ; rendu JavaScript avec adaptateur DOM minimal, sans serveur HA complet.
- Régression : 140 tests historiques récupérés localement (règles, sécurité, audio, mapping/zones DMX, réseau, projecteurs, Power Manager, persistance, UI, architecture).

## Provenance des tests historiques

L'archive source 0.15.0 ne contenait pas de tests. La suite locale 0.14.8 a d'abord été exécutée sans modification contre 0.15.0 : **130 réussites, 10 échecs**. Les 10 échecs correspondaient à huit attentes de version/cache 0.14.8, une attente de 55 services alors que la source en possède 80, et une liste de trois plateformes alors que la source en possède cinq. Ces assertions ont été adaptées à 0.15.2/80 services/cinq plateformes ; aucun test n'a été supprimé ou ignoré. Les 51 cas supplémentaires couvrent CEM3 et le durcissement.

## Limites

Pas de test sur CEM3 physique ni sur installation Home Assistant complète. Le multi-NIC utilise des adresses simulées pour les décisions de routage ; la liaison d'une connexion HTTP réelle est vérifiée sur localhost. Le test de panneau utilise un adaptateur DOM, pas une session navigateur HA. Le helper C/C++ RDMnet n'a pas été compilé. Les résultats ne certifient pas toutes les combinaisons de firmware, matériel ou protocoles tiers.

## Reproduire

Dans le FULL décompressé avec Python 3.12 et Node :

```sh
python -m pip install -r tests/requirements.txt
python -m pytest tests -q
python -m compileall -q custom_components helpers
node --check custom_components/dmx_monitor/static/show-network.js
node tests/test_cem3_frontend.cjs
```

## Conservation de la source

Source : `Show_Network_0.15.0_FULL.zip`
SHA-256 : `ce44da58a326696b67f83ef943e6e3d8e15f9a9835aee5226286bc8bbb8755ec`
171 fichiers source présents dans la livraison : 130 identiques, 41 modifiés, **0 supprimé**. Le détail des empreintes est dans `SOURCE_COMPARISON.json`.

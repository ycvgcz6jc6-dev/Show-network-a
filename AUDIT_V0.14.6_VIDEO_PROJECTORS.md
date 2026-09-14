# Show Network v0.14.6 — Vidéo / projecteurs

## 🟢 Implémenté et connecté
- PJLink Class 2: découverte réseau standard par UDP/4352 avec `%2SRCH` et lecture des réponses `%2ACKN=<MAC>`.
- Recherche read-only bornée, sans scan de ports ni commande de contrôle.
- Monitoring PJLink Class 1 corrigé: POWR, INPT, AVMT, ERST, LAMP, INST, NAME, INF1, INF2, INFO, CLSS.
- Monitoring Class 2 lorsque le projecteur l'annonce: SNUM, SVER, IRES, RRES, FILT, RLMP, RFIL, INNM.
- Distinction correcte NAME (nom de l'équipement) / INF1 (constructeur) / INF2 (produit/modèle).
- Décodage ERST en fan / lamp / temperature / cover / filter / other, avec niveaux OK / warning / error.
- Inventaire projecteurs agrégé exposé dans les attributs des sensors `projectors_*`, afin que les appareils découverts après le démarrage soient visibles dans le panneau sans créer de faux devices HA.
- Page Vidéo enrichie: online/power, identité, Class PJLink, série, firmware, source, entrées disponibles, résolutions, lampe, filtre, erreurs et fraîcheur.
- Les contrôles actifs restent séparés dans `projector.py` derrière le verrou Show Network.

## 🟡 Limites honnêtes
- La température absolue n'est pas une commande PJLink standard. `ERST` expose uniquement un état d'erreur température; aucune valeur °C n'est inventée.
- Un endpoint avec authentification PJLink n'est pas contourné: l'état indique que l'authentification est requise.
- Les projecteurs non-PJLink nécessiteront un adaptateur constructeur séparé et documenté.
- Les entités HA individuelles restent créées pour les projecteurs configurés au démarrage; les projecteurs découverts dynamiquement sont visibles immédiatement dans le panneau via le sensor agrégé.

## Validation
- Validation statique/unitaire uniquement dans l'environnement de développement.
- Aucun projecteur physique ni Home Assistant réel n'a été testé par l'assistant pour cette version.

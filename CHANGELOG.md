# Changelog

## 0.15.27 (suite 36) — Observabilité : UI/UX, deux pistes vérifiées et écartées

Dernier chantier du dernier bloc du rapport maître.

**Piste 1 — cohérence des classes CSS de statut entre composants.**
Écrit un script pour vérifier, composant par composant (chacun avec son
propre Shadow DOM isolé), que les classes CSS utilisées dynamiquement
en JS (`ok`/`warn`/`error`/`bad`...) sont bien définies dans le
`<style>` propre à CE composant — sinon un indicateur de statut
s'afficherait sans couleur, silencieusement. Le script a d'abord
signalé 5 composants avec des classes "manquantes". En vérifiant à la
main par recherche directe dans le texte brut (pas via le script),
confirmé que c'étaient des **faux positifs de mon propre outil** — une
regex d'extraction de bloc `<style>` par composant qui échouait sur
l'échappement des guillemets dans les template literals JS, pas un
vrai défaut du code. Les classes étaient bien définies partout où
vérifié à la main (`DmxMonitorPanel`, `MaInspectorPanel`). Piste
retirée honnêtement plutôt que de la présenter comme un correctif.

**Piste 2 — mélange terminologie française/anglaise.** Recherché des
paires de libellés équivalents (Enregistrer/Save, Fermer/Close, etc.)
utilisés tous les deux dans l'interface. Une seule occurrence
suspecte trouvée ("Save" au milieu de 8 "Enregistrer") — vérifiée : un
commentaire de code interne ("next Save"), pas un libellé affiché à
l'utilisateur. Pas un vrai problème non plus.

**Aucun bug UI/UX supplémentaire confirmé dans cette passe.** Les deux
pistes explorées se sont révélées être des fausses alertes, correctement
écartées après vérification plutôt que présentées comme des correctifs.

361/361 tests sur toute la suite, aucune régression.

---

**Les 8 blocs du rapport maître sont maintenant tous traités** (avec
leurs points explicitement laissés en attente, documentés ci-dessus :
PDU sans marque précisée, spin2dante `report_dante_subscriber`,
Reolink API poussée — Millumin `/ping` a depuis été ajouté, voir plus
haut).

## 0.15.27 (suite 35) — Observabilité : traductions complétées (5 langues)

Comparaison structurelle complète des 6 fichiers de traduction plutôt
que de supposer qu'ils étaient synchronisés. Le français (230 clés)
était la référence complète ; l'anglais en manquait 12, l'allemand
l'espagnol l'italien et le néerlandais 16 chacun.

**Vraies clés manquantes, pas de la décoration** : les champs de
configuration `dmx_artnet_enabled`, `dmx_sacn_enabled`, `dmx_source`,
`ma_enabled` — chacun aux trois endroits où ils apparaissent
(configuration initiale, reconfiguration, options) — plus deux messages
d'erreur (`invalid_json`, `port_in_use`), absents entièrement des
quatre langues non-anglaises. Un utilisateur configurant ou
reconfigurant l'intégration dans l'une de ces langues aurait vu ces
champs précis retomber sur la clé brute ou l'anglais, pas sa propre
langue.

Traductions rédigées en respectant le style déjà établi dans chaque
fichier (vérifié sur des chaînes existantes avant d'écrire quoi que ce
soit : allemand en "X aktivieren" verbe final, espagnol en "Activar X"
verbe initial, italien en "Abilita X" impératif, néerlandais en
"X inschakelen" verbe final), pas une simple traduction automatique
générique. Les 6 fichiers sont maintenant à 230 clés chacun, structure
JSON revalidée.

5 nouveaux tests de non-régression : validité JSON de chaque fichier,
ensemble de clés identique entre toutes les langues, les champs DMX
précis de l'audit épinglés individuellement (pour qu'un futur correctif
partiel — par exemple seulement l'étape initiale, en oubliant
reconfiguration/options — soit détecté précisément), messages d'erreur
présents partout, aucune valeur vide (une traduction présente mais
vide serait pire qu'une absente — elle a l'air intentionnelle mais
affiche un champ blanc).

361/361 tests sur toute la suite. Reste du bloc Observabilité : UI/UX.

## 0.15.27 (suite 34) — Observabilité : code mort nettoyé, précalcul d'attributs étendu (performance)

**Code mort.** Installé `vulture` (analyse statique dédiée) plutôt que
de deviner. À confiance élevée (80%+) : `export_zip()` acceptait un
paramètre `include_all` qui **n'avait aucun effet** dans le corps de la
méthode — vérifié qu'il n'était appelé nulle part (pas par le service
`archive_export`, pas documenté dans `services.yaml`, pas exposé côté
frontend) avant de le retirer, plutôt que de simplement masquer
l'avertissement. Trois imports morts retirés (`UpdateFailed`,
`dataclasses`, `Iterable`), chacun vérifié individuellement absent du
reste de son fichier avant suppression. Le reste des signalements à
confiance plus basse (60%) est du bruit attendu — hooks de cycle de vie
Home Assistant appelés par le framework, invisibles pour un outil
d'analyse statique.

**Performance : précalcul d'attributs étendu à 6 capteurs
supplémentaires.** La docstring de `attribute_bounds.py` documentait
déjà un vrai correctif antérieur : un capteur mesuré à ~0,6s par mise à
jour parce que son `extra_state_attributes` relançait un `json.dumps()`
complet à **chaque lecture** plutôt qu'une fois par cycle. Ce correctif
n'avait été câblé que pour cette seule clé mesurée
(`protocol_rx_diagnostics`) — 6 autres capteurs exposant le même genre
de structure volumineuse (`show_network_health`, `device_model`,
`show_network_doctor`, `show_snapshot`, `incident_center`, `pre_show`)
plus `etc_cem3` faisaient encore le calcul coûteux à chaque lecture,
sans qu'aucun n'ait encore été individuellement signalé comme lent.
Étendu le même précalcul à ces 7 clés — **regroupées en un seul
aller-retour vers l'exécuteur** plutôt que 7 séparés, pour limiter le
changement de contexte thread à chaque cycle plutôt que de simplement
copier-coller le pattern existant.

5 nouveaux tests confirmant que chaque capteur lit bien sa valeur
précalculée plutôt que de la recalculer, avec repli défensif si elle
n'existe pas encore (premier cycle).

356/356 tests sur toute la suite. Reste du bloc Observabilité : UI/UX,
traductions.

## 0.15.27 (suite 33) — Observabilité : santé commune Pre-Show/Doctor/Health Engine unifiée

Premier chantier du dernier bloc. Comparé les trois moteurs de
diagnostic (`doctor.py`, `pre_show.py`, `health_engine.py`) plutôt que
de supposer qu'ils étaient déjà cohérents entre eux.

**Vraie divergence trouvée** : Doctor et Pre-Show calculaient chacun
indépendamment l'utilisation des ports switch, et avaient
silencieusement divergé. Doctor signalait un avertissement dès 70%
d'utilisation (escalade en erreur à 85%) ; Pre-Show ne vérifiait QUE le
seuil de 85%, sans palier intermédiaire. Un port à 75% était visible
dans Doctor, complètement invisible dans la vérification de disponibilité
de Pre-Show — le même fait, deux réponses différentes selon le panneau
consulté.

**Absence complète, pas juste divergence** : `health_engine.py`, malgré
son rôle affiché de "corrélation de santé inter-protocoles", ne
vérifiait pas du tout l'utilisation des ports switch — un vrai trou de
couverture, pas seulement une incohérence de seuil.

**Corrigé en extrayant un calcul unique** (`find_high_utilization_switch_ports`,
avec les constantes nommées `SWITCH_UTIL_WARNING_PCT`/`SWITCH_UTIL_ERROR_PCT`)
que les trois moteurs appellent maintenant, plutôt que de choisir un
seuil "gagnant" et de le recopier dans les deux autres fichiers — recopier
aurait juste recréé le même risque de dérive la prochaine fois que
quelqu'un ajuste un chiffre à un seul endroit. Chaque moteur garde sa
propre logique de présentation (Doctor affiche les deux paliers,
Pre-Show ne bloque que sur le palier critique, cohérent avec son rôle de
porte binaire de disponibilité) — seul le calcul sous-jacent est
maintenant partagé et ne peut plus diverger silencieusement.

11 nouveaux tests, dont deux qui reproduisent exactement le scénario de
l'audit (un port à 75% : Doctor avertit, Pre-Show ne bloque pas — les
deux d'accord sur le fait sous-jacent) et un qui vérifie explicitement
que les constantes de seuil restent les mêmes partout.

351/351 tests sur toute la suite. Reste du bloc Observabilité
(performance, code mort, UI/UX, traductions) : pas encore commencé.

## 0.15.27 (suite 32) — DMX Monitor enrichi : un vrai bug de gigue trouvé et corrigé

`lighting_receiver.py` — le cœur même du monitoring DMX (réception
sACN/Art-Net) — n'avait **aucun test**, malgré son rôle central.
D'abord vérifié les décalages d'octets du parseur sACN à la main
contre la vraie spec ANSI E1.31 (priorité à l'octet 108, séquence à
111, univers à 113-114, nombre de propriétés à 123-124) : tous
corrects. Construit de vrais paquets sACN et Art-Net conformes au
format binaire réel (`tests/_dmx_packet_builders.py`) plutôt que du
HTML/JSON de substitution, et vérifié qu'ils s'analysent correctement
avant de les figer en tests.

**Vrai bug trouvé en testant la gigue (jitter)**, exactement la donnée
"enrichie" que ce bloc visait : sur une source DMX parfaitement
régulière (25ms d'intervalle constant, typique d'une console sACN),
le **deuxième** paquet jamais reçu rapportait une gigue de 25ms au
lieu de 0 — parce qu'il n'existe pas encore de vrai intervalle
précédent auquel se comparer, et le code comparait contre un
"intervalle précédent" placeholder à 0.0. Résultat concret :
à chaque nouvelle source qui apparaît sur le réseau, un pic de gigue
fantôme s'affichait immédiatement, même sur une source parfaitement
stable — trompeur pour un opérateur qui regarderait la colonne
"jitter" au moment où une console se connecte.

Corrigé en suivant explicitement si un intervalle précédent est
**réel** (pas juste un espace réservé) avant de calculer la gigue —
vérifié que ça ne supprime pas la détection d'une vraie variation
(testé : un retard de 5ms puis une avance de 10ms sont toujours
détectés correctement à partir du 3e paquet).

22 tests au total, couvrant aussi : rejet des paquets malformés (trop
courts, mauvais préambule, mauvais identifiant ACN, mauvais opcode
Art-Net), calcul de perte de séquence (normal, avec un vrai trou,
rollover 255→0 correctement non compté comme perte), `last_change` mis
à jour seulement quand les valeurs changent réellement, éviction
bornée du tracker (la source la plus ancienne part en premier),
comptage des canaux actifs.

340/340 tests sur toute la suite. **Bloc DMX & automatisation
maintenant complet** (zones, Rule Builder, DMX Monitor).

## 0.15.27 (suite 31) — Bloc DMX & automatisation : écriture atomique corrigée, Rule Builder audité

**Écriture atomique des zones — vrai bug trouvé et corrigé.**
`coordinator.py` écrivait directement sur le fichier live
(`path.write_text()`) pour sauvegarder les zones DMX→HA — une
interruption en cours d'écriture (crash HA, coupure) pouvait laisser un
JSON tronqué, que le chargement suivant avalait **silencieusement**
(`except: return`), effaçant toutes les zones configurées sans la
moindre trace. Découvert en comparant avec `rule_storage.py` et
`dmx_ha_mapping_storage.py`, qui utilisaient déjà correctement le
pattern fichier temporaire + renommage atomique — une vraie
incohérence dans le code, pas un principe absent du projet. Corrigé en
alignant `save_dmx_ha_zones()`/`async_save_dmx_ha_zones()` sur ce même
pattern déjà établi. Côté lecture, l'échec silencieux devient
maintenant un avertissement dans le journal plutôt qu'une perte muette.
8 nouveaux tests, dont une vérification sur 20 sauvegardes successives
qu'aucun état partiel n'apparaît jamais.

**Rule Builder (`rules.py`) — audité, code correct, mais jamais
testé.** Vérifié à la main avant d'écrire les tests (comme pour GDTF) :
hystérésis seuil ON/seuil OFF, modes any/all/x_of_y, délais
d'activation/désactivation indépendants — tout se comporte exactement
comme attendu. 29 tests ajoutés (zéro avant), dont un piège trouvé dans
**mon propre test** (mauvais calcul de l'origine du délai — le délai
compte depuis le premier changement d'état détecté, pas depuis le début
du scénario) corrigé avant validation finale.

**DMX Monitor enrichi : pas encore exploré.** Reste à faire pour une
prochaine session.

318/318 tests sur toute la suite.

## 0.15.27 (suite 30) — RDM/GDTF audité : solide, mais jamais testé

Fin du bloc Éclairage & scène pour cette session. Audit de
`rdm_inventory.py`, `rdm_bridge.py` et `gdtf.py`.

**Contrairement à CEM3, ce code s'est révélé correct dès le premier
essai.** Séparation fraîcheur découverte/télémétrie déjà bien faite
dans l'inventaire RDM. Le pont RDM (OLA/RDMnet) est déjà read-only par
défaut, écritures gatées par une méthode explicite — cohérent avec la
validation d'URL déjà corrigée en C13 pour ces mêmes ponts. Le parseur
GDTF 1.2 gère correctement les cas les plus piégeux (mise à l'échelle
DMX sur largeur variable 8/16 bits, construction de plages physiques à
partir de plusieurs ChannelFunctions, repli sur la plage la plus proche
pour une valeur hors bornes) — vérifié avec une fixture GDTF minimale
mais conforme à la vraie structure du schéma (GDTF/FixtureType/
DMXModes/.../ChannelFunction), tous les calculs corrects du premier
coup.

**Mais aucun test n'existait** pour `rdm_bridge.py` et `gdtf.py`, et
seulement 2 pour `rdm_inventory.py` — exactement la situation qui avait
caché les deux bugs CEM3. Comblé :

- 15 tests pour `gdtf.py` : identité de fixture, canal simple 8 bits,
  canal 16 bits avec deux fonctions physiques (Pan -270°/+270° divisé
  en deux plages), valeur par défaut déjà à la bonne largeur non
  re-mise à l'échelle, repli sur plage la plus proche hors bornes,
  bornes physiques inversées, archive sans description.xml, fixture
  sans mode DMX exploitable.
- 9 tests pour `rdm_bridge.py`, avec un **vrai serveur HTTP local**
  (pas de simulation d'`urlopen`) : récupération réelle des appareils,
  lignes sans UID filtrées, serveur injoignable géré proprement,
  pont non configuré n'effectue aucun appel réseau, écriture (`async_set`)
  envoie bien une vraie requête POST avec le bon corps JSON, refusée si
  le pont n'est pas configuré, réponse surdimensionnée rejetée.

**PDU reste en attente** d'une marque précise de ta part (aucun MIB
universel, vérifié en C11/C14).

## 0.15.27 (suite 29) — MA Web Remote : vraie poignée de main WebSocket au lieu d'un simple port ouvert

Suite à un nouveau fichier réel fourni par l'utilisateur
(`MA_Webremote.webarchive`, capture de `http://10.2.1.1:8080/`). Deux
apports directs :

**Port confirmé** : 8080, exactement ce que `MA_WEB_REMOTE_PORT`
supposait déjà — bonne nouvelle, rien à corriger là.

**Découverte qui change la sonde C23** : le Web Remote MA3 est en
réalité une appli de bureau à distance (flux vidéo compressé LZ4 décodé
dans un `<canvas>`), pas une API REST classique. Son vrai protocole,
lu directement dans `interface.js` (le code client réel de la page) :
connexion WebSocket vers `ws://host:8080/?ma=1`, et le serveur répond
**immédiatement à l'ouverture du socket**, avant tout login et avant
toute vraie requête de session (`remoteState`, `requestVideo`), avec
`{"status": "server ready"}`.

Le simple test de connexion TCP de la suite précédente (23) confirmait
seulement qu'*un* service écoutait sur ce port — pas que c'était
vraiment un Web Remote MA3 vivant. Remplacé par une vraie poignée de
main WebSocket RFC 6455, implémentée à la main (pas de dépendance
externe, cohérent avec le style du projet) : requête HTTP Upgrade,
vérification du calcul `Sec-WebSocket-Accept` (SHA1 + GUID RFC 6455),
lecture d'**une seule** trame texte, vérification du statut. Jamais de
`remoteState` ni `requestVideo` envoyés — vérifié par un test dédié qui
inspecte le code source à la recherche de tout appel `write()`
contenant ces mots.

Testé contre un **vrai serveur WebSocket** implémenté à la main dans
les tests (poignée de main RFC 6455 complète, pas de bibliothèque) :
accepté avec le bon statut, rejeté si statut différent, rejeté si ce
n'est pas un vrai pair WebSocket (mauvais `Sec-WebSocket-Accept` —
exactement le cas qu'un simple test TCP ne peut pas distinguer), rejeté
si trame binaire au lieu de texte (le protocole utilise aussi des
trames binaires pour la vidéo — confusion à éviter), rejeté si la
connexion se ferme avant la trame. 15 tests au total sur les deux
fichiers de test (bas niveau + intégration), dont 2 anciens tests
adaptés pour refléter le nouveau comportement plus strict (un simple
port TCP ouvert n'est plus jugé "disponible" — c'est justement le but
de la mise à niveau).

## 0.15.27 (suite 28) — ETC CEM3 : deux vrais bugs trouvés grâce à de vraies données

Bloc Éclairage & scène. Recherche préalable dans le rapport d'origine :
"Power Manager" y désigne déjà exactement la fonctionnalité de
séquençage DMX existante (honnête, jamais déclenchée) — rien à
corriger là. "PDU" n'apparaît nulle part dans ce document — reste en
attente d'une marque précise (pas de MIB universel, vérifié : chaque
fabricant a le sien, même situation que les consoles audio).

**Fait marquant de cette session** : l'utilisateur a fourni deux vraies
pages capturées (.webarchive Safari) de son propre rack CEM3 en
production (`grada salle A 2`, Rack #2, 10.2.2.3) — `index.asp` et
`setup.html`. Extraites via `plistlib` (format plist binaire Apple),
copiées comme fixtures de test permanentes
(`tests/fixtures/cem3_index_real.html`,
`tests/fixtures/cem3_setup_real.html`).

**Aucun test n'existait pour `etc_cem3.py`** (527 lignes) avant
aujourd'hui, malgré son ancienneté dans le projet. En exécutant le
parseur réel contre la vraie page, **deux bugs confirmés** :

1. **`rack_name` toujours `None`** : la regex exigeait un espace après
   "CEM3", mais le vrai HTML n'en a aucun
   (`<span class="header_title">ETC CEM3</span>grada salle A 2 (Rack #2)`
   — l'espacement visuel vient uniquement du CSS). Corrigé
   (`[ \t]+` → `[ \t]*`). Résultat réel maintenant : `"grada salle A 2"`.

2. **Quatre fausses erreurs matérielles à chaque sondage** : le motif
   `AF .+` destiné à capter une panne de carte AF captait aussi "AF
   Card 1" à "AF Card 4" — qui sont en réalité les libellés du tableau
   "Software Versions", pas des pannes. Sur la vraie page, ça aurait
   fait remonter 4 pannes matérielles inexistantes à Doctor/santé
   système, en plus de la seule vraie erreur active
   ("No Data DMX port A"). Corrigé en excluant précisément la forme
   prouvée par la vraie page (`AF Card [1-4]` seul, rien d'autre) tout
   en continuant à capter une vraie panne AF si elle a du texte
   supplémentaire (testé explicitement dans les deux sens).

**Piste explorée puis écartée honnêtement** : `setup.html` contient un
tableau "Circuit Setup" très riche (72 circuits réels, modules ETC
réels ETD15AFR/ETD25AFR/ED15N, mode de contrôle et courbe par circuit).
Un nouveau parseur `parse_cem3_circuit_setup_html()` a été écrit et
testé contre les 72 lignes réelles — mais en vérifiant, `parse_cem3_
properties()` (déjà câblée, via l'API XML structurée du CEM3, plus
robuste qu'un grattage HTML) capture déjà exactement les mêmes champs
(control_mode, firing_mode, curve, module_type) plus d'autres
(threshold, controllable_module) que le parseur HTML n'a même pas.
Fonction gardée dans le code (testée, correcte) mais **non câblée**
dans le cycle de sondage réel — pas de raison de dupliquer un chemin
XML déjà plus complet et déjà en production.

13 tests au total pour `etc_cem3.py`, tous basés sur les vraies pages
capturées plutôt que du HTML synthétique.

## 0.15.27 (suite 27) — Reolink : construction d'URL RTSP candidates (partage de flux)

Sur demande explicite : pas une intégration API Reolink poussée, juste
le côté "protocole de partage de flux" pour pouvoir les intégrer.

**Vrai trou trouvé** dans `video_ip_supervision.py` : l'URI RTSP
n'était construite qu'à partir du chemin donné par l'annonce mDNS
elle-même (`path` dans les TXT records). Beaucoup d'annonces RTSP
n'incluent pas ce chemin — dans ce cas, l'URI obtenue était juste
`rtsp://ip:port`, sans le segment de flux, donc non fonctionnelle pour
la plupart des caméras IP réelles.

**Vérifié contre le support officiel Reolink**
(support.reolink.com/articles/900000630706-Introduction-to-RTSP/) :
format `rtsp://<user>:<pass>@<ip>/Preview_<canal>_<type>`, port 554 par
défaut. Recoupé avec le segment de chemin concret réellement utilisé
(`h264Preview_01_main` / `h265Preview_01_main`), confirmé par plusieurs
sources indépendantes (réponse du support Reolink sur son propre forum
communautaire, guides d'intégration SDK, documentation Frigate NVR).

**Ambiguïté réelle trouvée et traitée honnêtement** : un ticket GitHub
réel de l'intégration Home Assistant officielle Reolink
(home-assistant/core#85659, caméra RLC-820A) montre que le préfixe
h264 renvoie une erreur 404 sur certains modèles récents, qui exigent
h265 à la place — dépend du modèle de caméra, une information que la
découverte mDNS passive n'a aucun moyen de connaître à l'avance.
Plutôt que de deviner un seul candidat qui serait silencieusement faux
pour une partie des caméras réelles, les **deux** variantes sont
proposées, explicitement marquées "URLs candidates non vérifiées" côté
interface (même principe déjà appliqué au Web Remote MA avant que sa
vraie sonde TCP existe). Aucune socket n'est jamais ouverte pour tester
ces URLs — cohérent avec le principe déjà affirmé par ce module
("no sockets are opened to media endpoints").

Nouvelle fonction `_reolink_candidate_stream_urls()`, câblée dans
`observe_mdns()` : seulement quand le fabricant est identifié comme
Reolink ET qu'aucun chemin explicite n'a été donné par l'annonce ; une
observation ultérieure avec un vrai chemin efface les candidats
devenus obsolètes plutôt que de laisser une supposition à côté d'une
URI confirmée. Frontend mis à jour pour afficher ces candidats
clairement signalés comme non vérifiés.

6 tests : deux candidats générés, appareil non-Reolink n'en reçoit
aucun (pas de format deviné pour une marque non documentée ici), chemin
explicite efface les candidats, port non standard inclus, aucune
socket ouverte même avec une adresse non routable, détection
insensible à la casse.

## 0.15.27 (suite 26) — C22 complet : Millumin (écoute passive documentée)

Dernière pièce du bloc C22. Recherche de la documentation officielle
Millumin (github.com/anome/millumin-dev-kit/wiki/OSC-documentation,
Millumin V5) — récupérée en entier cette fois, pas juste des extraits.

**Décision de conception importante trouvée en lisant le texte complet** :
le message `/ping` existe bien et "renvoie plusieurs messages OSC qui
décrivent l'état de toutes les couches" — mais leur format exact
(adresses, arguments) n'est **pas** énuméré dans la documentation. En
revanche, le mécanisme de "feedback" de Millumin (activé manuellement
par l'utilisateur via "API feedback" dans son gestionnaire de
périphériques) **est** documenté au format précis : chaque message
préfixé `/millumin/...` avec une adresse et des arguments exacts
(`/millumin/board/launchedColumn [index,"nom"]`,
`/millumin/layer:X/mediaStarted [index,"nom",durée]`, etc.).

Plutôt que deviner le format de réponse à `/ping`, `millumin_monitor.py`
est un **auditeur purement passif** — il n'envoie jamais rien, pas même
`/ping` — qui écoute les messages de feedback documentés. Cohérent avec
tous les autres observateurs passifs déjà dans ce projet
(`audio_ptp.py`, `dante.py`, `greengo_monitor.py`) : écouter ce que
l'appareil annonce déjà plutôt que l'interroger. Réutilise
`OSCReceiver`, déjà existant et testé, plutôt que réécrire un
récepteur UDP maison. Nécessite une configuration ponctuelle côté
Millumin (ajouter Show Network comme périphérique OSC avec "API
feedback" coché) — même principe déjà accepté pour le groupe multicast
Green-GO.

Testé avec de **vrais paquets OSC encodés** envoyés sur un vrai socket
UDP loopback vers un vrai `OSCReceiver` : lancement/arrêt de colonne,
début/pause/arrêt de média par couche (adressée par nom ou par index),
plusieurs couches suivies indépendamment, message non préfixé
`/millumin` correctement ignoré. 7 tests.

Câblé : nouvelle option `millumin_listen_port` (0 = désactivé),
enregistré comme ressource arrêtable (cycle de vie start/stop réel,
contrairement aux moniteurs à sondage), capteur dédié `millumin_status`.

**C22 (rapport maître §112) est maintenant complet : QLab, Resolume et
Millumin tous implémentés et testés.**

## 0.15.27 (suite 25) — C22 : Resolume implémenté et testé, Millumin confirmé viable

Suite de la suite 24.

**Resolume — implémenté et testé.** API REST officiellement documentée
(spec OpenAPI 3.0 complète, resolume.com/docs/restapi/), vérifiée et
recoupée sur plusieurs sources indépendantes et cohérentes (pages
support officielles Resolume, plugin grandMA3, module Bitfocus
Companion, fils du forum officiel) : port par défaut 8080, chemin
`/api/v1/composition` donnant l'état complet de lecture en un seul
appel — confirmé explicitement par le support Resolume lui-même
("you can GET /composition data, and the currently playing clip with
that"). Détail important trouvé en creusant : les valeurs de paramètres
sont enveloppées (`{id, valuetype, value}`), pas des valeurs JSON
brutes — géré avec une fonction de déballage défensive.

Nouveau `resolume_monitor.py`, HTTP (pas OSC, donc son propre module) —
suit exactement le pattern déjà établi dans `avdecc_bridge.py`
(`urlopen` déporté via `asyncio.to_thread`, taille de réponse plafonnée).
Volontairement restreint au monitoring : une seule requête GET jamais
autre chose, vérifié par un test dédié qui inspecte chaque chemin
réellement appelé.

Testé avec un **vrai serveur HTTP local** (thread `http.server`, pas de
simulation d'`urlopen`) : couche avec un clip actif détectée
correctement, couche sans clip connecté correctement signalée inactive,
hôte injoignable géré proprement. 7 tests.

Câblé : nouvelle option `resolume_hosts`, coordinateur, capteur dédié
`resolume_status`.

**Millumin — confirmé viable, pas encore implémenté.** Documentation
OSC officielle trouvée (help.millumin.com/docs/connect/osc-api/) : un
message `/ping` fait remonter l'état de toutes les couches en retour —
exactement le type de requête de monitoring pur recherché. Mais
contrairement à QLab (schéma JSON exact documenté) ou Resolume (schéma
confirmé par des captures réelles), le format précis des messages de
réponse à `/ping` n'a pas encore été récupéré — une passe de recherche
supplémentaire serait nécessaire avant d'implémenter, pour ne pas
deviner sur une base incomplète.

**C22 (rapport maître §112) : QLab et Resolume faits, Millumin
identifié et prêt à reprendre.**

## 0.15.27 (suite 24) — C22 : QLab (monitoring officiel OSC) fait, Resolume confirmé viable

Suite du bloc Vidéo & médias. Recherche protocolaire pour les trois media
servers nommés (QLab, Resolume, Millumin) avant d'écrire quoi que ce
soit — même rigueur que pour Yamaha/Green-GO.

**QLab — implémenté et testé.** Figure 53 (l'éditeur de QLab lui-même)
publie un dictionnaire OSC officiel complet
(qlab.app/docs/v5/scripting/osc-dictionary-v5/), récupéré et vérifié
directement — contrairement à DiGiCo/Soundcraft, un vrai protocole
constructeur documenté. Nouveau `qlab_monitor.py`, volontairement
restreint au monitoring pur, conformément à "Monitoring/read-only
d'abord... GO/Panic/etc. protégés" : seules trois requêtes explicitement
documentées comme acceptées même sans mot de passe sont envoyées —
`/version`, `/workspaces`, `/thump` par espace de travail. Aucune
action de contrôle de cue n'est jamais envoyée, vérifié par un test
dédié qui inspecte chaque requête réellement transmise. Réutilise les
encodeur/décodeur OSC déjà éprouvés du projet (comme pour Yamaha).

Testé avec de **vrais sockets UDP en boucle locale** : un serveur
factice répond exactement dans le format documenté
(`/reply/{adresse} {json}`), y compris un cas de réponse non-JSON géré
proprement (dégradation, pas de crash). 7 tests.

Câblé : nouvelle option `qlab_hosts`, coordinateur, capteur dédié
`qlab_status`.

**Resolume — confirmé viable, pas encore implémenté.** API REST
officielle avec spécification OpenAPI 3.0 complète
(resolume.com/docs/restapi/) — encore mieux documentée que l'OSC de
QLab. Protocole HTTP, pas OSC : un chantier d'implémentation distinct
(requêtes GET plutôt qu'échange UDP), nécessitant de récupérer les
chemins d'endpoints exacts avant d'écrire le code, comme d'habitude.

**Millumin — pas encore vérifié.**

## 0.15.27 (suite 23) — Bloc Vidéo & médias (C20/C21/C22/C23) : C20 déjà fait, C23 complétée

**C20 (projecteurs) — audit, rien à corriger.** Panasonic Web API
(Digest auth), Digital Projection ASCII (familles Rev A/F/H), Christie
HS Serial API, Barco Pulse JSON-RPC 2.0 : les 4 marques nommées par le
rapport ont déjà de vrais adaptateurs protocolaires fonctionnels, pas du
PJLink générique étiqueté. Tous les champs demandés (power/input/mute/
hours/temperature/warning/model/serial/**signal**) déjà présents, avec
une liste `capabilities` honnête par marque ("uniquement si réellement
fournies").

**C21 (Video IP/Reolink) — mis en pause à la demande.**

**C23 (MA-Net3) — vrai trou trouvé et comblé.** Tout le reste (station,
IP, interface, session, rôle, version, dernier paquet, fraîcheur) était
déjà bien fait. Mais `station.web_remote` était figé à la constante
`"not_probed"` — jamais mis à jour, un placeholder honnête plutôt
qu'une fausse donnée, correspondant exactement au constat de l'audit
d'origine ("Web Remote affichés mais disponibilité non prouvée"),
qu'un correctif précédent de cette session avait déjà signalé comme
"⚠ non vérifié" côté UI sans jamais implémenter la vraie vérification.

Nouveau `MARemoteInventory.async_probe_web_remote()` : test de
connexion TCP léger vers le port Web Remote (8080) — **pas** une action
protocolaire MA-Net3 (pas de rejoindre une session, pas de commande MA
envoyée), cohérent avec la philosophie "receive-only" déjà affirmée par
le module ("Aucun join implicite"). Rapporte `unknown` / `available` /
`unavailable`, exactement le vocabulaire du rapport. Piège trouvé et
corrigé en cours de route : `observe()` se déclenche à **chaque**
paquet MA-Net3 reçu (donc en continu pour une station active) —
laisser cette méthode réinitialiser `web_remote` aurait effacé le
résultat de la sonde presque immédiatement après chaque sondage.
Sondage cadencé à 30s dans le coordinateur (pas à chaque cycle de 5s —
un test de connexion reste du vrai trafic réseau).

Frontend mis à jour : le lien affiche maintenant "✓ disponible" /
"✗ injoignable" / "⚠ non vérifié" selon le vrai résultat, plutôt que le
message générique précédent.

13 tests, dont 6 avec de **vrais serveurs/sockets TCP en boucle
locale** (port qui répond, port fermé — vrai refus de connexion — pas
de simulation). Un piège de test trouvé et corrigé en cours de route :
un serveur factice qui ne fermait jamais sa propre connexion bloquait
`wait_closed()` indéfiniment — ce n'était pas le code de production qui
avait un défaut, seulement le nettoyage du test.

**C22 (media servers QLab/Resolume/Millumin) : non commencée.**

## 0.15.27 (suite 22) — Green-GO Niveau 1 (Passive Discovery) réel

Bloc Green-GO (C15). Recherche protocolaire d'abord, avec l'aide de
l'accès direct à l'installation réelle (add-on serveur MCP), qui a
d'ailleurs révélé au passage que **Show Network est déjà déployé et
actif** sur cette instance (198+ entités confirmées via
`integration_entities('dmx_monitor')`) — une ancienne version,
antérieure à toutes les corrections de cette session.

**État constaté sur l'installation réelle** : `sensor.sources_green_go`
à 0. La découverte Green-GO existante (`green_go.py`,
`GreenGOInventory`) est un modèle de données complet mais n'était
alimenté que par une correspondance de texte "green-go"/"greengo" dans
les annonces mDNS génériques — pas par le protocole Green-GO lui-même.

**Vérifié contre la documentation officielle**
(manual.greengoconnect.com) : communication sur port UDP 5810 fixe,
**mais l'adresse multicast est générée par le fichier de configuration,
propre à chaque installation** — contrairement à Dante/PTP qui utilisent
des groupes multicast fixes et connus à l'avance. Aucun canal de
découverte par broadcast séparé n'est documenté. Conséquence directe :
impossible d'écouter "à l'aveugle" comme pour Dante — le port est
connu, le groupe ne l'est pas et ne peut pas être deviné.

**Nouveau `greengo_monitor.py`** : écoute multicast passive sur le
groupe **explicitement fourni par l'utilisateur** (nouveau champ
`greengo_multicast_group`, validé comme adresse multicast IPv4
valide), port 5810. Ne décode **jamais** le contenu des messages
(Talk/Call/Cue/niveaux) — seulement la présence (un test dédié vérifie
qu'aucun contenu de paquet n'apparaît nulle part dans l'instantané) :
les notes de recherche d'origine du projet elles-mêmes avaient étudié
un seul script public et prévenaient explicitement que ce n'était pas
une preuve du format général du protocole. Alimente maintenant
`GreenGOInventory.observe()` en complément (pas en remplacement) de la
détection mDNS existante, avec une preuve plus forte (`source="udp_5810"`
vs `"mdns"`).

10 tests, dont 6 avec de **vrais sockets multicast en boucle locale**
(pas de simulation) : réception réelle, non-décodage du contenu prouvé
explicitement, accumulation multi-paquets, `start()` idempotent,
`stop()` propre.

**Toujours hors de portée** : Niveau 2 (télémétrie OSC) et Niveau 3
(contrôle), qui nécessiteraient de décoder le contenu des messages —
pas fait, faute de spécification vérifiée du format exact.

## 0.15.27 (suite 39) — Trois points repris : PDU (APC/Raritan), Reolink (intégration officielle), spin2dante (préparé), plus une correction sur Nexus Audio

**PDU** — OID récupérés directement depuis le code source réel de
Network UPS Tools (open source, testé sur du vrai matériel), pas
devinés depuis un navigateur de MIB. Deux marques, chacune avec son
propre mapping d'état (**APC** : `outletOn(1)`/`outletOff(2)` ;
**Raritan PX2** : `on(7)`/`off(8)`, un enum partagé différent — vérifié
explicitement, pas supposé identique à APC). Marque choisie
explicitement par hôte, jamais de détection automatique. Lecture seule.
8 tests.

**Reolink** — pas de client API maison : lecture des entités que
l'intégration Reolink **officielle** de Home Assistant crée déjà
(`camera.*`, `binary_sensor.*_motion/_person/_vehicle/_pet/_animal/
_visitor/_package`), confirmées par la documentation officielle HA.
Caméras trouvées par plateforme dans le registre d'entités, pas par
correspondance de texte fragile. 6 tests.

**spin2dante** — nouveau champ candidat `dante_subscriber_status` :
lit l'attribut `source` et le remonte seulement s'il correspond
exactement à "Synchronized" ou "ExternalSource" (les termes exacts de
la doc spin2dante), marqué explicitement `_verified: False` tant que
pas confirmé en direct avec `report_dante_subscriber` réellement activé.

**Correction sur Nexus Audio, suite à une remarque légitime** :
l'utilisateur a demandé une simple visibilité "comme spin2dante", et
j'avais construit un client HTTP actif interrogeant l'API de gestion —
plus lourd que nécessaire. Ajouté `nexus_audio_zones.py`, la version
légère équivalente : lecture des entités `media_player` que Nexus Audio
crée déjà dans Music Assistant pour chacune de ses sources (confirmé
par sa propre doc : "expose them as Sendspin Live Inputs to Music
Assistant"), aucun appel réseau — exactement le même mécanisme que pour
spin2dante. Le client HTTP direct reste disponible en parallèle,
maintenant clairement documenté comme l'option plus complète mais plus
lourde. 7 tests.

Traductions des 3 nouveaux champs de configuration (`pdu_hosts`,
`reolink_ha_enabled`, `nexus_audio_players`) ajoutées immédiatement
dans les 6 langues, pour ne pas répéter l'oubli trouvé plus tôt cette
session.

398/398 tests sur toute la suite.

## 0.15.27 (suite 38) — Un trou introduit par cette session même, trouvé et corrigé : traductions des nouvelles options

Vérification mécanique (pas de données live nécessaires) : est-ce que
les onze nouvelles options de configuration ajoutées tout au long de
cette session (Yamaha OSC, QLab, Resolume, Nexus Audio, Millumin,
Green-GO, Sendspin/spin2dante) avaient bien leur traduction ?

**Zéro occurrence dans les 6 langues, pour les 11 champs.** Chaque
nouveau `vol.Optional(const.CONF_X, ...)` ajouté au schéma partagé
(config initial + reconfiguration + options) s'affichait donc comme
nom de champ brut plutôt qu'un libellé traduit — un trou introduit par
le travail de cette session elle-même, pas hérité de l'audit d'origine.

En creusant, trouvé **en plus** un petit trou pré-existant, sans
rapport avec mes ajouts : `aes70_hosts`/`aes70_port` manquaient
spécifiquement dans `options.step.init.data` (présents seulement dans
la configuration initiale et la reconfiguration) — vérifié que ce
n'était pas un trou plus large en comparant les 74 champs de
`config.step.user.data` contre les 72 de `options.step.init.data` :
seulement ces deux-là, corrigés au passage.

Traductions rédigées en respectant le style déjà établi (vérifié sur
un champ "hosts" existant, `aes70_hosts`, avant d'écrire quoi que ce
soit : "Hôtes X" / "X hosts" / "X-Hosts" / "Hosts X" / "Host X" /
"X-hosts" selon la langue). 13 champs × 3 emplacements × 6 langues =
234 entrées ajoutées ou complétées. Les 6 fichiers sont maintenant à
265 clés chacun.

2 nouveaux tests de non-régression : chaque champ épinglé
individuellement dans les 3 emplacements, pour qu'un futur ajout de
champ sans traduction soit détecté immédiatement plutôt que découvert
des sessions plus tard.

373/373 tests sur toute la suite.

## 0.15.27 (suite 37) — Nexus Audio intégré (monitoring seul), Millumin /ping ajouté

**Nexus Audio** (github.com/ycvgcz6jc6-dev/Nexus-audio), sur demande.
Avant d'intégrer quoi que ce soit, le dépôt a été cloné dans un dossier
d'inspection isolé, séparé du livrable, pour être lu — pas fusionné à
l'aveugle. C'est un vrai add-on Home Assistant OS, complémentaire à
spin2dante : là où spin2dante fait Music Assistant → Dante (sortie),
Nexus Audio fait AirPlay/Spotify Connect/Dante RX/AES67 → Music
Assistant (entrée). Licences réelles (librespot MIT, aiosendspin
Apache-2.0, inferno, GPL-3.0), avertissement de sécurité honnête dans
sa propre doc ("le port de gestion 8099 n'a pas d'authentification
propre, ne pas l'exposer à Internet") — rien qui ressemble à du code
malveillant.

**Routes vérifiées directement dans le vrai code source**
(`app/main.py`, routage `do_GET`/`do_POST`), pas devinées depuis le
README : cinq routes GET en lecture (`/health`, `/api/interfaces`,
`/api/sources`, `/api/dante`, `/api/aes67/discovery`) et six routes
POST de contrôle (`reload`, `source/{save,delete,start,stop,restart}`,
`aes67/select`). Nouveau `nexus_audio_monitor.py` : **uniquement**
`/health` et `/api/sources`, jamais une route POST — même principe
"monitoring d'abord" déjà appliqué à QLab/Resolume/Millumin tout au
long de cette session. Suit exactement le pattern HTTP déjà établi
(`urlopen` déporté via `asyncio.to_thread`, taille de réponse
plafonnée). Formes de réponse testées prises directement de la vraie
méthode `Worker.status()` du code source, pas inventées.

Testé avec un vrai serveur HTTP local : état par source (worker,
présence audio, niveau crête dBFS, erreurs de validation de
configuration), aucune requête POST jamais envoyée (vérifié
explicitement), échec de `/api/sources` n'empêchant pas de rapporter au
moins `/health`. 8 tests. Câblé : nouvelle option
`nexus_audio_hosts`, coordinateur, capteur dédié `nexus_audio_status`.

**Millumin — `/ping` ajouté comme coup de pouce au démarrage.**
Recherche complémentaire sur le forum officiel Millumin : confirmé
directement par le développeur de Millumin lui-même que `/ping` "n'a
d'effet que si l'API/feedback est activée" et ne produit jamais qu'une
réponse dans **la même forme** que le feedback déjà documenté — ce qui
valide a posteriori la décision de conception initiale (écoute pure)
plutôt que de l'invalider. Ajouté l'envoi d'un `/ping` unique au
démarrage (jamais répété) vers une cible optionnelle configurable
(nouvelle option `millumin_ping_target`), traité par le **même**
analyseur de messages déjà en place — aucune nouvelle logique de
parsing, juste un premier instantané plus rapide au lieu d'attendre le
premier vrai changement d'état. 3 nouveaux tests, dont un avec un vrai
paquet UDP `/millumin/ping` reçu sur un vrai socket.

372/372 tests sur toute la suite.

## Points en attente de décision utilisateur

- **spin2dante — `report_dante_subscriber`** : option réelle et
  documentée, par pont, dans la config de l'add-on spin2dante lui-même
  (pas dans Show Network). Si activée, ferait remonter un signal plus
  précis côté Music Assistant — "Synchronized" seulement quand un vrai
  récepteur Dante est abonné, "ExternalSource" sinon — au lieu du
  simple état lecture/pause actuellement utilisé par
  `sendspin_dante_zones.py`. Mise en pause volontairement : modifier la
  config d'un autre add-on n'est pas un choix que je fais seul. **À
  reprendre plus tard, sur demande explicite.**

- **Video IP / Reolink (C21)** : mis en pause à la demande de
  l'utilisateur, jamais repris.

## 0.15.27 (suite 21) — spin2dante : monitoring réel via accès direct à l'installation

Suite au message précédent, où j'avais conclu ne pas pouvoir construire
d'intégration spin2dante sans deviner un protocole non documenté. Accès
direct accordé à l'installation HA réelle (add-on serveur MCP) — recherche
refaite avec des faits vérifiés en direct plutôt que des suppositions.

**Confirmé en direct** : `spin2dante` et `statime` sont deux add-ons
installés et actifs (`252f4b2d_spin2dante`, `252f4b2d_statime`), sans
aucune API web/ingress exposée (`ingress: false`, `webui: null`) —
l'absence d'interface externe directe est confirmée, pas supposée.
`statime` exporte l'horloge PTP via un socket partagé
(`/share/usrvclock`) que spin2dante consomme — confirme le couplage des
deux outils déjà pressenti plus tôt dans cette session.

**Découverte importante** : spin2dante logue des lignes structurées très
riches par pont audio (dérive en ppm, validité de synchro, tampon,
volume, transitions flux actif/inactif) — bien plus que prévu. Mais
lire ces logs en continu depuis le code de Show Network lui-même
nécessiterait l'API Supervisor, réservée aux **add-ons** déclarant
`hassio_api: true` avec leur propre `SUPERVISOR_TOKEN` — un composant
personnalisé classique comme Show Network n'a structurellement pas accès
à ça, confirmé par la documentation officielle Home Assistant. Ce n'est
pas une limite de cette intégration, c'est une frontière d'architecture
HA. Reproduire ça casserait de toute façon dès qu'on tourne sous
Docker/Core sans Supervisor.

**Ce qui EST exploitable, vérifié en direct** : chaque pont spin2dante
s'enregistre comme une entité `media_player` Music Assistant normale.
Vérifié précisément : l'état `idle`/`playing` de
`media_player.home_assistance_to_bureau` correspond exactement aux
lignes de log "stream ended, entering idle" / "stream start" ; son
`volume_level` correspond exactement à "bridge volume set to N". Lire
l'état d'une entité HA normale ne demande aucun privilège Supervisor —
c'est une capacité disponible à tout composant, tout le temps.

Nouveau `sendspin_dante_zones.py` : lit les entités `media_player.*`
que l'utilisateur désigne (nouvelle option `sendspin_dante_players`)
directement depuis `hass.states` — pas de sondage, pas de socket, pas
de cycle démarrage/arrêt, puisque le bus d'événements HA les tient déjà
à jour. Rapporte état, activité (lecture en cours), niveau de volume,
sourdine.

7 tests (zone inactive, zone active, entité manquante gérée
proprement, plusieurs zones indépendantes, sourdine, aucune entité
configurée, repli sur l'entity_id si pas de nom).

**Piste non activée, à valider avec toi** : spin2dante a une option
réelle et documentée par pont, `report_dante_subscriber`, qui ferait
remonter "Synchronized" seulement quand un vrai récepteur Dante est
abonné (au lieu de simplement "Music Assistant joue quelque chose").
Elle n'est actuellement activée sur aucun de tes 3 ponts configurés. Je
ne l'ai pas activée moi-même — modifier la configuration d'un autre
add-on est le genre de changement qui demande ton accord explicite.

## 0.15.27 (suite 20) — Yamaha DM3/DM7/Rivage PM : statut de scène (portée volontairement restreinte)

Suite du bloc Audio. Recherche protocolaire approfondie sur Yamaha,
DiGiCo, Soundcraft avant d'écrire quoi que ce soit — même rigueur que
les MIB SNMP en C11, sur des protocoles moins bien documentés
publiquement :

- **Yamaha** a en réalité deux protocoles distincts. RCP (CL/QL/TF,
  texte brut, port 49280) : aucune documentation officielle Yamaha,
  rétro-ingénierie communautaire uniquement. OSC (DM3, DM7, Rivage PM) :
  **spécifications officiellement publiées par Yamaha**, trouvées et
  récupérées directement depuis data.yamaha.com (DM7 OSC Specifications
  V1.1.0), y compris la table complète des paramètres, plages de
  valeurs et unités.
- **DiGiCo** : pas un problème de documentation manquante mais plus
  fondamental — son "Generic OSC" est configuré par l'opérateur dans
  l'éditeur de macros de chaque installation, pas un protocole fixe
  externe. Rien à implémenter qui marcherait sans configuration
  préalable spécifique à chaque salle.
- **Soundcraft** : série Ui rétro-ingénée (un document a été partagé
  une fois par un représentant, avec la mention explicite "this isn't
  supported") ; séries Vi/Si sans API externe du tout, juste une app
  iPad propriétaire fermée.

**Conclusion** : ni DiGiCo ni Soundcraft ne passent le niveau
d'exigence déjà appliqué à ce projet (documentation officiellement
publiée, vérifiable). Seul Yamaha DM3/DM7/Rivage PM le passe.

**Nuance importante trouvée en creusant la spec officielle Yamaha** :
elle documente abondamment `/set` (contrôle) mais **aucune action `get`
générique** pour lire un paramètre de canal quelconque (niveau de
fader, mute...). Un module communautaire testé sur du vrai matériel
confirme qu'un tel `get` existe comme "trappe d'accès" non documentée,
et que même le push/subscribe officiel ne fonctionne pas de façon
fiable par canal (poll uniquement) — mais sans que la syntaxe exacte
apparaisse dans la documentation Yamaha elle-même, la deviner aurait
été contraire à la règle déjà établie dans ce projet.

**Ce qui EST implémenté, entièrement vérifié** : `sscurrentt_ex`, la
seule action de lecture que la spec officielle documente
explicitement — "Get Current Scene_A/B Number". Nouveau
`yamaha_osc_monitor.py` : interroge périodiquement la scène actuellement
chargée (listes A et B) sur les consoles configurées, en UDP port 49900
comme documenté. Réutilise les encodeur/décodeur OSC déjà existants et
testés du projet (`osc_output.encode_osc`, `osc_receiver.
parse_basic_message`) plutôt que d'en réécrire.

Testé avec de **vrais sockets UDP en boucle locale** (pas de simulation
du protocole) : un serveur factice répond exactement comme le ferait un
vrai DM7 d'après la spec, prouvant l'encodage/décodage réel de bout en
bout ; un hôte injoignable (adresse réservée IANA, jamais routable) ne
bloque pas les autres ; un test garde-fou vérifie explicitement
qu'aucune action `/set` ou `/event` n'est jamais envoyée — seulement la
requête de lecture documentée.

Câblé : nouvelle option `yamaha_osc_hosts`, coordinateur, capteur dédié
`yamaha_osc_consoles`.

**CL/QL/TF (RCP), DiGiCo et Soundcraft restent non implémentés**, pour
les raisons détaillées ci-dessus.

## 0.15.27 (suite 19) — Bloc Audio (C12/C13/C14) : état des lieux + un vrai correctif

Bloc "Audio" du rapport maître (C12 Dante/PTP, C13 amplificateurs, C14
consoles). Contrairement aux blocs précédents, celui-ci s'est révélé
beaucoup plus proche d'un audit honnête que d'un chantier de
construction — la majeure partie était soit déjà bien faite, soit
bloquée par l'absence de documentation publique fiable, pas par manque
de code.

**C12 (Dante/PTP) — déjà exemplaire pour la partie vérifiable.**
`audio_ptp.py` sépare déjà explicitement jitter et offset : libellé
sémantique `"packet_arrival_variation_not_clock_offset"`, offset
**jamais fabriqué** (`ptp_clock_offset_available: False`) — exactement
"ne jamais transformer jitter en offset". Grandmaster (identité,
priorités, classe d'horloge, fraîcheur) déjà suivi correctement.
Découverte Dante par mDNS déjà en place.

Deux manques réels, non comblés, et pourquoi : `clock selected/locked`
et `spin2dante ready/transmitting` nécessitent de lire le statut de
`statime`/`spin2dante` — des services système **externes**, séparés,
dont je n'ai pas d'accès vérifié à l'interface de statut (fichier ?
D-Bus ? socket ?) dans cette conversation. `subscriptions`/`late
packets`/`errors` Dante nécessiteraient de décoder le protocole de
monitoring Dante (DMP), propriétaire Audinate et non documenté
publiquement — deviner son format binaire irait à l'encontre de la
règle déjà établie dans ce projet de ne jamais utiliser un protocole
non documenté.

**C13 (amplificateurs) — bien plus mature que prévu, un vrai bug
corrigé.** `aes70_monitor.py` parle déjà réellement AES70/OCA en TCP
via une bibliothèque open-source, avec d&b audiotechnik mappé comme
premier fabricant. `avdecc_bridge.py` s'appuie sur un pont JSON
documenté. Les deux respectent déjà "température inconnue reste
UNKNOWN, jamais 0°C" — vérifié dans le code : un échec de lecture va
dans `errors`, jamais dans `telemetry` avec une valeur inventée.

**Correctif réel trouvé et appliqué** : le point resté "NON TRAITÉ"
depuis le tout début de cette session — `avdecc_bridge_url non
conforme à une URL visible` — causé par un champ de formulaire déclaré
comme simple chaîne, sans aucune validation. En creusant, le **même**
défaut existait aussi pour `CONF_RDM_BRIDGE_URL` et
`CONF_RDMNET_BRIDGE_URL` (pas un cas isolé). Les trois valident
maintenant : chaîne vide acceptée (pont désactivé), sinon URL http(s)
valide obligatoire — rejeté à la saisie plutôt que de plaquer un échec
cryptique plus tard, en profondeur, dans un attribut d'erreur du pont.
Restreint spécifiquement à http/https (pas juste "un schéma d'URL
valide" au sens large) puisque les trois ponts sont documentés comme
des points d'accès JSON-sur-HTTP.

**C14 (consoles audio) — vide confirmé, non traité.** Yamaha/DiGiCo/
Soundcraft/Allen&Heath n'existent dans le code que comme indices de
reconnaissance passive pour l'inventaire (étiqueter "fabricant :
Yamaha"), aucune intégration protocolaire. Chaque marque a son propre
protocole propriétaire (RCP Yamaha, dialecte OSC DiGiCo, etc.) — même
niveau de rigueur que la vérification des MIB SNMP en C11 serait
nécessaire avant d'écrire le moindre code, mais sur des protocoles
nettement moins bien documentés publiquement.

6 nouveaux tests pour la validation d'URL (chaîne vide, URL valide,
chaîne malformée, schéma non-http rejeté, appliqué aux trois champs).

## 0.15.27 (suite 18) — Phase C11 complète : PoE par port + température (fin du bloc)

Dernières pièces de C11 (§101) : "...PoE lorsque disponible..." et
"...temperature...". **C11 est maintenant entièrement traitée** :
port/speed/errors/traffic (suite 15), LLDP (suite 16), VLAN prouvé
(suite 17), et maintenant PoE + température.

**PoE par port** — POWER-ETHERNET-MIB (RFC 3621), standard, universel.
Vérifié précisément (`pethPsePortDetectionStatus` = colonne 6 =
`1.3.6.1.2.1.105.1.1.1.6`, confirmé mot pour mot sur oidref.com) plutôt
que déduit de la seule position dans la liste SEQUENCE du RFC.
**Découverte importante en creusant le standard** : le MIB de base n'a
**aucun objet de puissance réelle par port en watts** — seulement un
statut de détection (délivre du courant / recherche / désactivé /
défaut). La puissance réelle par port est propriétaire selon les
fabricants, sans OID documenté publiquement pour ce projet — donc pas
inventée, conformément à la règle déjà établie. Rapporté honnêtement :
statut d'activation admin + statut de détection/délivrance.

**Température** — ENTITY-SENSOR-MIB (RFC 3433), pour tout ce qui n'est
pas Luminex (déjà couvert par `GigaCoreMonitor` via son OID privé).
Filtre sur `entPhySensorType == celsius(8)` (confirmé sur 6+ sources
indépendantes). Gestion Scale/Precision validée contre l'exemple
concret donné par le RFC lui-même ("0 à 100°C par pas de 0,1°... Value
interprétée comme degrés×10") — testé exactement contre cet exemple
(250 brut → 25,0°C). Échelles non plausibles pour une température
(nano/micro à méga uniquement) rapportées comme non calculables plutôt
que devinées. Sentinelles de dépassement RFC (±1 milliard) explicitement
exclues plutôt que rapportées comme une température absurde.

**Import circulaire découvert et corrigé en cours de route** :
`switch_temperature.py` avait besoin du même petit utilitaire de
découpage de suffixe d'OID que `switch_port_telemetry.py` et
`lldp_discovery.py` utilisaient déjà chacun de leur côté — plutôt que
l'importer entre modules (créant un cycle), déplacé une bonne fois dans
`snmp.py` que les trois importent déjà sans dépendance circulaire.

25 nouveaux tests (dont l'exemple RFC exact pour la température, un
switch modulaire multi-groupes pour le PoE, l'exclusion des capteurs
non-température, les sentinelles de dépassement). 5 tests
`SwitchPortMonitor` existants ont dû être ajustés : `_poll_one()`
marche maintenant IF-MIB + PoE + température à chaque sondage, donc les
tests qui ne fixaient que le premier laissaient le troisième tenter un
vrai socket réseau (bloqué par le bac à sable).

**Bloc Réseau & Découverte (C9, C10, C11) entièrement terminé.**

## 0.15.27 (suite 17) — Phase C11, troisième partie : VLAN prouvé (LLDP)

Suite de la suite 16. Rapport maître §101 : "...VLAN prouvé...".

**Rigueur particulière ici** : la table `lldpXdot1RemVlanNameTable`
(extension LLDP-EXT-DOT1-MIB, IEEE 802.1AB-2005 Annexe F.4) n'est pas
dans le cœur du LLDP-MIB de base — plutôt que de deviner son OID de
mémoire, vérifié par recherche croisée sur plusieurs sources
indépendantes (documentation Huawei, H3C ×3, oidref.com), puis confirmé
au mot près contre le **texte MIB brut** sur deux miroirs distincts
(`github.com/librenms/librenms` et `github.com/robison/snmp-config`)
avant d'écrire le moindre code — cohérent avec la règle déjà établie
dans ce projet de ne jamais utiliser un OID non documenté.

Confirmé : `lldpXdot1RemVlanName` = `1.0.8802.1.1.2.1.5.32962.1.3.3.1.2`,
avec un index à **quatre** parties (`timeMark.localPortNum.remIndex.
vlanId`) — un cran de plus que la table de voisinage de base, parce
qu'un même port en mode trunk peut légitimement annoncer plusieurs VLAN
pour un même voisin. Le VLAN ID lui-même n'est jamais accessible comme
colonne séparée (`NOT-ACCESSIBLE` dans le MIB) : il est encodé
directement dans le suffixe d'OID de la colonne "nom", donc un seul
marchage donne à la fois l'identifiant et le nom.

Chaque voisin porte maintenant une liste `vlans: [{id, name}, ...]`
(triée numériquement). Propagé jusqu'à la topologie : le modèle
`TopologyLink` n'a qu'un seul emplacement `vlan`, donc le VLAN le plus
bas est utilisé comme représentant du lien (déterministe, pas "le
dernier du marchage" arbitraire).

8 nouveaux tests (VLAN unique, plusieurs VLAN sur un port trunk, pas de
fuite entre voisins différents, absence de données VLAN, tri numérique,
propagation jusqu'à la topologie).

**Reste pour C11** : PoE par port (table séparée, même principe de
jointure), température hors Luminex (MIB moins standardisée selon les
fabricants — la pièce la plus incertaine à documenter proprement).

## 0.15.27 (suite 16) — Phase C11, deuxième partie : découverte LLDP réelle

Suite de la suite 15. Rapport maître §101 : "LLDP... VLAN prouvé...".
Nouveau `lldp_discovery.py`, LLDP-MIB standard (IEEE 802.1AB, base OID
`1.0.8802.1.1.2`) — universel sur tout switch qui supporte LLDP, quel
que soit le fabricant.

**Difficulté principale** : contrairement à IF-MIB (un seul index par
port), la table des voisins LLDP a un **index composite en trois
parties** (`timeMark.localPortNum.remIndex`) — nécessaire notamment
parce qu'un seul port local peut voir plusieurs voisins s'il passe par
un hub ou un switch non managé. Jointure des colonnes marchées
séparément sur `(localPortNum, remIndex)`, `timeMark` ignoré (ne sert
qu'à dater le dernier changement de topologie, pas à corréler les
colonnes d'un même sondage). Résolution du nom de port local via la
table locale séparée (`lldpLocPortTable`), la numérotation locale LLDP
ne correspondant pas forcément à l'`ifIndex` d'IF-MIB.

**Intégration à la topologie, découverte importante** : `device_model.py`
filtre déjà explicitement ses `physical_links` sur `protocol=="LLDP"` —
encore une fois câblé pour recevoir cette donnée, jamais alimenté.
Nouvelle méthode `coordinator._ingest_lldp_neighbors()` : résout
l'identité de chaque voisin annoncé (par adresse MAC) contre
l'inventaire déjà connu — un voisin déjà identifié se rattache au
**même** nœud de topologie que le reste de Show Network utilise déjà
(même convention `mac:<mac>` que `device_inventory.py`), avec un
identifiant synthétique `lldp:<chassis_id>` en repli pour un voisin pas
encore connu, cohérent avec la philosophie "topologie basée sur la
preuve" déjà documentée dans `topology.py`.

29 nouveaux tests au total (parsing d'index composite, plusieurs voisins
sur un même port via hub, hôte injoignable, résolution d'identité par
MAC contre l'inventaire réel, mise à jour au lieu de duplication sur
sondages répétés).

**Reste pour C11** : VLAN "prouvé" (LLDP peut porter un TLV VLAN,
non encore extrait), PoE par port (table séparée, même principe de
jointure qu'IF-MIB), température hors Luminex (plus variable selon les
fabricants, MIB moins standardisée).

## 0.15.27 (suite 15) — Phase C11, première partie : télémétrie par port réelle (IF-MIB)

Début du plus gros chantier du bloc Réseau & Découverte. Rapport maître
§101 : "Développer réellement : LLDP, port, VLAN prouvé, speed, errors,
temperature, traffic, PoE, last seen." Cette entrée couvre port/speed/
errors/traffic ; LLDP, VLAN et PoE par port suivent dans une entrée
ultérieure.

**Découverte de départ importante** : `snmp.py` a déjà un `async_walk()`
complet (GETNEXT borné, lecture seule) — `switch_monitor.py` avait
délibérément choisi GET seul et laissé les tables par port de côté
("out of scope for this GET-only module"). Le travail protocolaire dur
était déjà fait ; il manquait la couche au-dessus.

**Encore plus important** : `switch_telemetry` était lu défensivement
partout dans le projet (le journal de changement du coordinateur, les
checks `switch_ports`/`audio_bandwidth` de Doctor, la comparaison
`show_snapshot.py`) — et **le frontend aussi**, à quatre endroits
différents, avec des noms de champs (`p.up`, `p.rx_mbps`, `p.tx_mbps`,
`p.speed_mbps`, `sw.interface`, `sw.ip`...) qui correspondent exactement
à ce que ce nouveau module produit. Personne n'avait jamais rien
branché : `switch_telemetry` était en pratique toujours vide, front et
back déjà prêts à le recevoir.

Nouveau `switch_port_telemetry.py` :
- `async_walk_if_table()` — marche IF-MIB standard (nom de port, état,
  débit, compteurs d'erreurs, compteurs de trafic), une colonne par
  `async_walk()`, jointes par le suffixe d'index partagé. Standard sur
  tout switch géré SNMP — Luminex, Aruba, Cisco, ELC — sans OID privé.
- `SwitchPortMonitor` — calcule un débit Mb/s réel entre deux sondages
  successifs à partir des compteurs cumulés (un seul relevé ne donne
  qu'un compteur, pas un débit). Gère explicitement le cas d'un switch
  qui redémarre (compteurs remis à zéro) : signale l'absence de débit
  pour cet échantillon plutôt qu'un débit négatif absurde.

Câblé dans `runtime/setup.py`/`coordinator.py` en réutilisant
`all_switch_hosts`, la liste déjà combinée GigaCore + switches génériques
qui existait déjà pour `GenericSwitchMonitor`.

17 tests (jointure de colonnes, tri numérique des ports, colonnes
manquantes non fatales, calcul de débit, redémarrage de compteur,
hôte injoignable n'affectant pas les autres). Vérifié aussi de bout en
bout avec un test DOM : données au format exact produit par le backend
→ capteur → tuile frontend, sans aucune modification du frontend.

**Reste pour C11** : LLDP (table à index composite, corrélation plus
complexe), VLAN prouvé, PoE par port, température (hors Luminex, plus
variable selon les fabricants).

## 0.15.27 (suite 14) — Phase C10 : le système Favori devient réel

Le rapport maître (§100) : "Les favoris deviennent le périmètre
privilégié de Doctor/Incident/History, sans limiter la découverte
globale." La bascule ★/☆ existait déjà dans l'inventaire
(`monitor_mode`), mais en vérifiant : ce champ était stocké, affiché,
transmis au frontend — et jamais lu nulle part pour influencer quoi que
ce soit. Un bouton cosmétique sans effet.

**Fusion d'identité (première moitié de C10)** : investiguée, pas
modifiée. `DeviceModel` documente déjà explicitement "ne jamais inventer
d'identité... exposer les conflits plutôt que les deviner" — utiliser
hostname/mDNS comme clés de fusion supplémentaires irait à l'encontre de
cette prudence (risque de faux rapprochements que le rapport lui-même
demande d'éviter). Laissé tel quel intentionnellement.

**Système Favori (seconde moitié, le vrai trou)** : trois branchements,
un par système cité :

- **Doctor** : nouveau check `favorites` dédié — pour chaque appareil
  `monitor_mode='monitor'`, vérifie la fraîcheur (`last_seen` récent) et
  l'atteignabilité réseau (réutilise directement `network_routes`,
  construit pour C9). Un favori injoignable pousse le check en `error`
  **et peut faire basculer le verdict global de Doctor** — testé
  explicitement, ce n'est pas cosmétique. Aucun autre check n'est
  retiré ; le périmètre global reste entier.
- **Incident Center** : `build()` acceptait déjà un paramètre `devices`
  jamais lu. Chaque incident est maintenant marqué `favorite_related`
  (intersection avec les appareils favoris), plus un compteur
  `favorite_active_count` au niveau du résumé.
- **History** (comparaison de snapshot) : chaque différence au niveau
  appareil (`device_missing`/`device_new`/`device_fact_changed`) est
  marquée `favorite_related`, plus `favorite_difference_count` au
  niveau du résumé. Cas limite trouvé et corrigé en testant : un
  appareil disparu n'est par définition plus dans l'état courant, donc
  son statut favori ne peut pas être lu depuis les données actuelles —
  `_capture()` capture maintenant aussi `monitor_mode`, utilisé comme
  repli pour ce cas précis.

Aucun changement frontend nécessaire pour Doctor : le panneau
(`show-network-doctor-panel`) affiche déjà tous les checks de façon
générique (`checks.map(...)`), donc le nouveau check apparaît
automatiquement — les checks `warning`/`error` s'ouvrent même déjà
automatiquement. Ajouté `related_device_ids` aux preuves du check pour
que le rapprochement visuel avec les équipements fonctionne comme pour
les autres checks.

15 nouveaux tests au total (Doctor, Incident Center, History), aucune
régression sur les tests existants.

**C10 (rapport maître §100) est maintenant complète.** Reste sur ce
bloc : C11 (LLDP/switches réels), le plus gros chantier des trois.

## 0.15.27 (suite 13) — Phase C9 complète : câblage + vue frontend

Suite et fin de la suite 12. Le calcul `route_to_target` est maintenant
branché dans le coordinateur (`_compute_route_to_targets`, appelé hors
event loop via l'executor) : calculé automatiquement pour les hôtes
GigaCore/Luminex et ETC CEM3 déjà configurés, **et** pour tout appareil
déjà présent dans l'inventaire de découverte ayant une IP connue —
couvrant Dante/MA/Reolink/etc génériquement sans clé de configuration
dédiée par marque, conformément au "etc." du rapport maître (§99).
Dédoublonnage : un même IP annoncé à la fois en config explicite et en
inventaire garde le libellé explicite ("Luminex GigaCore", pas
"Appareil découvert").

Publié dans `sensor.dmx_monitor_network_interfaces_up` (déjà l'entité
que le frontend lit pour `interfaces`), nouvel attribut `routes`.

Vue frontend ajoutée sur la page Réseau existante (`show-network-
discovery`), deux nouveaux blocs dépliables sous le tableau
d'équipements :
- **Interfaces réseau — détail** : adresses IPv4 en notation CIDR,
  état UP/DOWN, débit, badge 🌐 sur l'interface qui porte la route par
  défaut, groupes multicast rejoints.
- **Route vers les équipements connus** : cible, IP, "sous-réseau
  direct" ou "passerelle par défaut (X)" ou "aucune route trouvée",
  interface locale utilisée. Note explicite que c'est un calcul passif,
  aucun paquet émis.

Testé : logique de câblage coordinateur (dédoublonnage, priorité du
libellé explicite, appareil sans IP correctement ignoré) et rendu DOM
réel confirmant que les données remontent jusqu'à l'écran.

**C9 (rapport maître §99) est maintenant complète.** Reste sur ce bloc :
C10 (fusion d'identité + système Favori/Découvert/Ignoré — la bascule
★/☆ existe déjà partiellement dans ce même panneau, à vérifier/étendre)
et C11 (LLDP/switches, le plus gros chantier des trois).

## 0.15.27 (suite 12) — Phase C9 (multi-NIC), première partie : fondations backend

Début du chantier "Réseau & Découverte" (bloc choisi par l'utilisateur
parmi les phases C7/C9-C33 du rapport maître). Cette entrée couvre le
premier tiers de C9 (§99) ; C9 (frontend), C10 et C11 suivent dans des
entrées ultérieures.

`network_interfaces.py` étendu avec trois nouvelles capacités, toutes en
lecture seule (aucune route/adresse/état d'interface n'est jamais
modifié, conformément à l'instruction explicite du rapport maître) :

- **Réseau/préfixe IPv4 par interface** (`ipv4_networks`) — calculé à
  partir du netmask que psutil expose déjà par adresse, jusque-là ignoré.
- **Route par défaut** (`read_default_route()` /
  `_default_route_interface()`) — lecture de `/proc/net/route`, décodage
  du format hexadécimal petit-boutiste du noyau Linux.
- **Groupes multicast rejoints par interface**
  (`_multicast_groups_by_interface()`) — lecture de `/proc/net/igmp`,
  même décodage hexadécimal.
- **`route_to_target(interfaces, ip)`** — répond à "quelle interface
  locale serait utilisée pour joindre cette cible", exactement la
  fonctionnalité "route to target pour CEM3, Dante, Luminex, MA,
  Reolink, etc." demandée par le rapport (§99) : correspondance de
  sous-réseau d'abord, repli sur la route par défaut, sinon
  explicitement "unreachable" avec la raison. Pure fonction de calcul ;
  n'émet aucun paquet.

Testé avec de vrais formats `/proc/net/route`/`/proc/net/igmp` (pas des
structures simplifiées) pour que le décodage hexadécimal petit-boutiste
lui-même soit couvert, pas seulement la logique autour : 9 tests, dont
le cas GigaCore de la baseline de l'audit (10.4.1.3) comme exemple de
correspondance de sous-réseau, un cas de repli sur la route par défaut,
un cas "aucune route", et un cas d'adresse invalide.

**Reste à faire pour C9** : intégrer ces fonctions dans le coordinateur
(calculer `route_to_target` automatiquement pour les hôtes déjà
configurés — GigaCore, CEM3 — et publier dans le snapshot), puis
construire la vue frontend détaillée par interface (masques, routes,
multicast, RX par protocole, dernier paquet) qui n'existe pas encore
(seule une tuile résumée existe actuellement).

## 0.15.27 (suite 11) — Phase C6 audit (Active Control) + Phase C2 lifecycle fix

Per the master report's own priority order (§127-129): C6 (centralize Active
Control) and C2 (full lifecycle audit, sACN supervisor named explicitly as a
historical concern).

**C6 — audited, no gap found.** A first AST scan of all 95 registered
services flagged 73 as not calling `security.require_unlocked()`, but that
scan didn't follow calls through shared helper functions (e.g.
`projector.py`'s `_projector_power/_input/_mute` all delegate to a shared
`_execute()` that does call it). Redone with transitive call-graph
resolution within each file: every service that sends a real command to a
physical device or output (OSC/MIDI send, Show Control cue fire, live
QLC+ control, projector commands, RDM writes via the shared `_set()`
helper, Power Manager run, DMX scene recall) is already gated. Everything
left ungated is local configuration with no physical side effect (create
a rule/zone/mapping/patch, archive operations, HA Builder CRUD).
Specifically checked `show_snapshot_activate`, the one case whose name
sounded action-like: it only changes which saved reference the Pre-Show/
Doctor comparison uses, no output whatsoever. No code change needed.

**C2 — found and fixed a real gap, introduced by this version's own
earlier fix.** Investigating whether `DmxNetworkReceiver` (the sACN/Art-
Net receiver the master report calls "supervisor sACN" and suspects of
shutting down poorly) leaks sockets or tasks on reload: it doesn't --
`_supervise()` closes its socket and cancels its parser task in a
`finally` block on every exit path including `CancelledError`, and it's
correctly registered as a stoppable resource
(`resources.add(RuntimeResource(..., "dmx-network", dmx_network, "stop",
...))`) that `async_unload_entry` reaches via `ResourceRegistry.
async_stop_all()`.

While confirming that, found that `PJLinkMonitor` is not registered as a
stoppable resource at all -- harmless before this version, since it
never owned anything longer-lived than a single `async_update()` call,
but earlier in this version's own changes (0.15.27 suite 9, the
CancelledError fix) it started creating a real background
`asyncio.Task` for the first discovery sweep. Nothing cancels that task
on unload/reload: a genuine task leak this version's own fix
introduced. Added `PJLinkMonitor.async_stop()` (cancels the in-flight
discovery task if any) and registered it via the same
`RuntimeResource`/`ResourceRegistry` mechanism `dmx-network` already
uses. New test confirms `async_stop()` actually cancels rather than
waiting out a slow sweep (asserts completion well under the sweep's
mocked 2s duration).

### Complément — reste du parcours C2 (audit lifecycle élargi)

Après le correctif `PJLinkMonitor.async_stop()` ci-dessus, balayage de
**tous** les `asyncio.create_task()` du projet (27 sites) et de tous les
moniteurs instanciés dans `runtime/setup.py` sans tâche/socket propre,
pour chercher d'autres cas du même genre :

- **4 moniteurs sans entrée `resources.add()`** (`GigaCoreMonitor`,
  `GenericSwitchMonitor`, `UpsMonitor`, `DanteManagedMonitor`) — vérifiés
  individuellement : aucun n'a de tâche de fond, de socket ou de boucle
  persistante. Ce sont des moniteurs "sondés à la demande" pendant le
  cycle de rafraîchissement ; rien à nettoyer, absence d'enregistrement
  correcte.
- **Les 23 autres `create_task()`** appartiennent tous à des classes déjà
  correctement enregistrées comme ressources arrêtables (`dante-managed`
  exclu ci-dessus), ou gérées par un chemin d'arrêt explicite séparé dans
  `__init__.py` (`archive`, `coordinator.watchdogs`,
  `coordinator._dmx_flow`/`_dmx_publish_limiter`/`_ha_dispatcher` via
  `coordinator.async_stop()`).
- `etc_cem3.py` : modèle exemplaire à noter — `self._tasks` est un `set`
  explicitement suivi, chaque tâche y est ajoutée avant d'être attendue et
  retirée dans un `finally`, et `stop()` réunit tout ce qui reste. Aucune
  modification nécessaire.
- **Point mineur identifié, volontairement non corrigé** :
  `signal_watchdog.py` crée trois `asyncio.create_task()` ad-hoc
  (`_lose_after`, `_recover_after`, `_run_recovery_action`) qui ne sont
  pas suivies dans les dictionnaires que `async_stop()` parcourt (celui-ci
  ne couvre que les `TimerHandle` de `call_later`, un mécanisme différent).
  Écart réel, mais impact pratique négligeable : les deux premières sont
  appelées avec un délai de 0 (se terminent en une fraction de seconde,
  contrairement aux 10,5s réelles du cas projecteur), donc la fenêtre où
  une telle tâche pourrait encore être active au moment précis d'un
  déchargement est de l'ordre de la milliseconde. Noté pour référence
  plutôt que corrigé, le coût du correctif ne se justifiant pas pour ce
  niveau de risque.

**Conclusion C2** : un vrai correctif nécessaire trouvé et appliqué
(`projector_monitor`, une régression introduite par le propre correctif
de cette version pour le `CancelledError`). Le reste du lifecycle du
projet — y compris le "supervisor sACN" explicitement cité comme
suspect historique par le rapport maître — s'est révélé déjà solide.

## 0.15.27 (suite 10) — Rule Builder: the rest of the form now persists too

The channel-selection fix earlier in this version deliberately covered
only the grid, leaving the rest of the form (name, universe, source,
mode, X, thresholds, delays, both actions' domain/service/entity/JSON
data, and which rule -- if any -- is being edited) still reset to
defaults every time the dashboard recreates this element. Finished the
job: the whole form now persists to sessionStorage the same way.

Two things made this trickier than the earlier draft fixes:

- `#domain`/`#service`/`#entity` (and their OFF counterparts) are empty
  `<select>` elements populated dynamically from `hass.services`, not
  static options in the template. Setting `.value` on a `<select>` with
  no matching `<option>` yet is a silent no-op in every browser -- it
  does not get remembered for options added later (verified directly:
  assigning a value, then populating options, and reading `.value` back
  shows the *first* newly-added option, not the earlier assignment).
  These four fields are restored explicitly after `refreshTargets()` has
  populated real options to match against, not via the template.
- `render()` runs exactly once, from `connectedCallback()`, and in the
  real dashboard flow (`_mountPanels`: `appendChild` first, `el.hass =
  ...` right after) that happens *before* `hass` is ever assigned --
  `this._hass` is still null at that point, and `set hass()` never calls
  `render()` again afterward (only `sync()` and `refreshTargets()`). The
  select-restoration logic originally placed inside `render()` therefore
  either silently never ran, or crashed outright when a draft already
  had a saved domain (`this._hass.states` read on a still-null `_hass`).
  Moved it into `set hass()`, guarded to run once per element lifetime
  so it restores the saved selection without repeatedly clobbering the
  user's live choices on every later hass push.

Verified with a jsdom test using the real destroy-and-recreate
methodology (not just a new `hass` push on the same instance): fills
every field, including picking a real domain/entity from a live
`hass.services`/`hass.states`, forces recreation, and confirms all of
it -- including the two dynamic selects -- survives. Re-ran the
existing channel-selection and other draft-persistence tests from
earlier in this version to confirm no regression.

## 0.15.27 (suite 9) — MA Web Remote links + projector discovery CancelledError

**MA Web Remote links not validated** ("Liens Web Remote MA non
validés"): `ma-inspector-panel` rendered `x.web_remote_url` as a plain
clickable link, but the same panel's own diagnostics row already says
"Web Remote probe: DISABLED · URL candidate only" -- by design, this
integration's passive-diagnostics philosophy means it never actively
probes a grandMA3 console's web interface. Adding active validation
would contradict that; the actual gap was that the link itself didn't
carry the same honesty as the diagnostics row next to it. It now reads
"Web Remote ⚠ non vérifié" with a title explaining it's an unprobed
candidate URL, and stations with no `web_remote_url` at all get a
disabled placeholder instead of a link to `href="#"` that went nowhere
useful. Verified with a jsdom test asserting both the label and title on
a real URL, and that no `href="#"` link exists when the URL is absent.

**Projector discovery CancelledError during reload**: traced to
`runtime/setup.py:919` (`await
coordinator.async_config_entry_first_refresh()`) ->
`coordinator.py:375` -> `PJLinkMonitor.async_update()`, which
unconditionally awaited a **mandatory 10.5s PJLink UDP broadcast
discovery inline** on its very first call -- the same class of bug this
codebase had already fixed for vendor discovery (see
`runtime/setup.py`'s own comment: "previously blocking
async_setup_entry directly, contributing to slow/timed-out config entry
bootstraps"), just never applied here. Now runs the first discovery as
a background task, guarded against a second `async_update()` call
before it finishes starting a duplicate sweep; already-configured
projectors still get polled normally in the meantime. The periodic
(every 5 minutes past the first run) re-discovery path is unchanged and
still awaited directly. New `tests/test_projector_discovery_nonblocking.py`
(no prior test coverage existed for this module at all) verifies the
first call returns before the mocked sweep finishes, that a concurrent
second call doesn't start a duplicate sweep, and that the periodic
path's own behavior is untouched.

## 0.15.27 (suite 8) — Network page: duplicate ARP/mDNS rows + phantom empty row

Two distinct, confirmed causes for "IP dupliquées entre ARP et DNS-SD,
[...] une ligne vide affichée comme si elle existait".

**Duplicates.** `runtime/setup.py`'s ARP sweep keys its fallback
identity on `"candidate:<ip>:<interface>"`, but
`DiscoveryPipeline.mdns_result()`'s is plain `"candidate:<ip>"` with no
serial/mac -- and `DeviceInventory.upsert()`'s "promote the existing
candidate instead of duplicating" merge path only ran when the caller
also supplied a serial or mac. mDNS never does, so an mDNS hit for an
address ARP had already recorded could never take that path and always
created a second, separate record for the same physical device.
`find_by_ip()` already does the right thing with no interface hint (only
merges when exactly one existing record matches that IP, correctly
declining on genuine multi-NIC/VLAN ambiguity -- see
`test_same_ip_on_two_interfaces_does_not_cross_merge`), so the fix is
simply to attempt that promotion for any upsert carrying an IP, not only
ones that also carry a serial/mac.

**The empty row.** Some mDNS announcements resolve to neither an IP nor
a name (only a bare `service_type`). `mdns_result()`'s fallback identity
in that case was `"mdns:<service_type>"` -- not device-specific, so
*every* unidentified announcement of that service type from *any* device
on the network collapsed into one shared record, continuously
overwritten and displaying as a near-blank row that never went away.
`mdns_result()` now declines to create a record at all when it has
neither an IP nor a name to attribute the evidence to, rather than
fabricate one from evidence that cannot identify a specific device. All
existing call sites already handled a `None` return defensively
(`mdns_dev.unique_id if mdns_dev else ...`, `runtime/setup.py`), so this
needed no other changes.

Verified: existing `test_inventory_multinic_identity.py` tests pass
unchanged (the multi-NIC non-merge guarantee this fix deliberately
preserves was already covered there). Added
`test_arp_then_mdns_on_same_ip_merges_not_duplicates` (and separately
reproduced the bug against the *old* promotion condition to confirm it
really did produce two records before this fix) and
`test_mdns_with_neither_ip_nor_name_creates_no_phantom_row`.

## 0.15.27 (suite 7) — SCAN NETWORK / PunchLight / OSC Learn: no visible click feedback

Three separate audit findings, two different root causes, same symptom.

**SCAN NETWORK and PunchLight's own "Rechercher"** (`show-network-discovery`,
`punchlight-network-panel`): both `set hass(h)` re-render unconditionally
on every hass push, and both click handlers wrote a transient status
string (`"Scan en cours…"`, `"Recherche…"`) directly into the DOM. Neither
operation is instant -- network scan walks every IPv4 interface,
PunchLight discovery has a 3s timeout -- so the very next hass push
(routine on a live-push integration, well under a second away) rebuilt
the element from real backend state and wiped the transient message
before a person could reasonably see it. Fixed the same way as the
earlier form-draft cases: persist `{status, message, ts}` in
sessionStorage and have `render()` show it in place of the computed
status whenever a scan is in flight or just finished (a short expiry
window covers the "just finished" case too, so the completion message
gets a moment on screen instead of disappearing on the very next push).

Verified with a jsdom test that clicks, waits for a pending service call
to still be unresolved, then forces a re-render exactly like a live hass
push would: against the unmodified bundle the status reverts to the
idle summary immediately; against the fixed bundle it still reads "Scan
en cours…".

**OSC Learn's START LEARN/STOP LEARN** (`osc-learn-panel`): a different
cause -- this button already renders itself entirely from real backend
state (`osc_learn.active`) rather than a transient string, which is the
more correct pattern, but nothing was ever shown while waiting for that
backend state to round-trip back through the next hass push. A `_busy`
flag already existed in the class but was never read in `render()` and
never triggered a render when set -- a partially wired mechanism.
Finished wiring it: `_call()` now renders immediately after setting
`_busy`, and the button shows a disabled "…" state while a call is in
flight.

Verified with a jsdom test asserting the button is disabled and shows
"…" synchronously after the click, before the pending service call
resolves -- exactly the window the audit found empty-handed.

## 0.15.27 (suite 6) — "two DMX grids disagreeing" resolved

Root cause found for the audit's "deux grilles DMX affichant des valeurs
différentes" (the DMX UNIVERSE MATRIX table and the Art-Net/sACN
diagnostic cards vs. the channel grid and status pill, on the same DMX
View page). All four sections live in the same component
(`dmx-monitor-panel`), but `_syncLiveNow()`'s change-detection signature
only covered the *currently selected universe's own* fields
(rate/active/priority/sequence/values) -- it never looked at
`_findDmxState().attributes.matrix` or `_rxDiag()`'s protocol stats at
all. A source flipping from LIVE to LOST in the matrix, or a protocol
error appearing in the Art-Net/sACN cards, does not necessarily change
the selected universe's own summary fields, so `render()` was
skipped and those two sections kept showing whatever was on screen at
the last coincidental re-render -- while the pill and channel grid, whose
fields *are* in the signature, kept updating normally. Two parts of one
page silently disagreeing about the same live state.

Extended the signature to include a compact digest of both the matrix
(per-source active/rate/loss/age) and the Art-Net/sACN diagnostics
(state/packet counts/last error/joined groups), so a change in either
now reliably triggers a re-render.

Verified with a jsdom test that pushes two hass snapshots where the
selected universe's own fields are byte-for-byte identical and only the
matrix's source-level `active` flag flips true -> false: replayed against
the unmodified 0.15.19-dev29 bundle, the matrix table stays stuck on
"LIVE"; against the fixed bundle, it correctly shows "LOST".

## 0.15.27 (suite 5) — pre_show.py / incident_center.py blocking-call warnings

Confirmed at the exact lines the audit flagged. Both classes loaded their
persisted state with a synchronous `open()`/`read_text()` inside
`__init__`, and `ShowNetworkCoordinator.__init__` constructs both
directly (`self.pre_show = PreShowCheck(...)`,
`self.incident_center = IncidentCenter(...)`) -- so every single startup
ran real file I/O on Home Assistant's event loop. `runtime/setup.py`
already had this exact category of bug fixed for five *other* persisted-
state loaders (power manager, DMX circuit monitor, DMX-to-HA zones,
control mappings, DMX-to-HA mappings) via a `_safe_load()` helper that
defers each one to an executor job, individually guarded so one bad file
can't abort the rest of setup -- these two just weren't in that list yet.
Both constructors now only set in-memory defaults; loading happens
through the same `_safe_load()` call alongside the other five.

`incident_center.py` had a second instance of the same problem:
`build()` -- called synchronously inside the coordinator's periodic
`_async_update_data()`, itself on the event loop -- wrote the incidents
file directly whenever incident state changed (the audit's "6 warnings"
in one session). Fixing this one needed an actual behavior change, not
just moving a call: `build()` now sets a `dirty` flag instead of saving,
and `_async_update_data()` checks it right after calling `build()` and
offloads the actual write (`await
hass.async_add_executor_job(self.incident_center._save)`) there.

`incident_center.acknowledge()`'s own `_save()` call was already
correctly wrapped in `services/incidents.py` and needed no change.

Verified: existing `test_pre_show_optional_profile.py` and
`test_incident_lifecycle.py` still pass unchanged (neither depended on
data being auto-loaded from a file at construction -- both start from an
empty tmp_path). Added a direct check that explicit `_load()` -- what
runtime/setup.py now calls -- actually loads pre-existing state
correctly, and that `build()` sets `dirty` instead of writing
synchronously.

## 0.15.27 (suite 4) — ha_builder_remove_callbacks actually removes entities now

The gap flagged in earlier notes for this version: every platform module
(switch.py, sensor.py, binary_sensor.py, number.py, button.py)
initialized `ha_builder_remove_callbacks` as an empty dict but nothing
ever populated it, so `ha_builder_remove` deleted the item from storage
while the live Home Assistant entity kept existing as an orphan --
`switch.turn_off` etc. would still find an entity there, just one backed
by a HA Builder item that no longer exists.

Each platform now tracks the entities it created for HA Builder items
(item_id -> live entity instance) and registers a real remove callback
that unregisters the correct one: `entity.async_remove(force_remove=True)`
to remove its state, then `entity_registry.async_remove(...)` so it
doesn't linger as a restored entry across restarts. The shared logic
lives in one place (`ha_builder_entities.async_remove_builder_entity`)
so all five platforms call the same removal path rather than five
near-duplicates. `services/builder.py`'s `_ha_builder_remove` now awaits
each callback -- they're async now, and calling an async callable without
awaiting it just creates a coroutine that never runs.

Verified with a genuine Home Assistant entity-lifecycle integration test
(`tests/test_ha_builder_removal.py`), not a low-level mock: creates a HA
Builder switch and a HA Builder button through the real
`async_setup_entry` path, confirms each is live in both `hass.states` and
the entity registry, removes it the same way the `ha_builder_remove`
service does, and confirms both are gone afterward. A third test confirms
removing one item's entity doesn't touch a second, unrelated one. Getting
this test to reflect reality took using pytest-homeassistant-custom-
component's `MockEntityPlatform` rather than hand-rolling the entity
registration sequence -- a partial reimplementation kept tripping over
internals (`restore_state`, `CoordinatorEntity.async_added_to_hass`'s
`coordinator.async_add_listener`) that only the real `EntityPlatform`
machinery gets right.

Added a project-level `pytest.ini` (`asyncio_mode = auto`): pytest-
homeassistant-custom-component's `hass` fixture is a plain
`@pytest.fixture` async generator rather than `@pytest_asyncio.fixture`,
which pytest-asyncio's default "strict" mode does not resolve -- any test
using `hass` would otherwise silently receive the fixture function's own
unresolved async_generator object instead of a running Home Assistant
instance.

## 0.15.27 (suite 3) — Rule Builder CSS overflow + test_rule bounds validation

- **Rule Builder grid overflow at ~884px** ("au format visible ~884px les
  colonnes débordent derrière le formulaire"): `.layout` splits into a
  flexible channel-grid column and a fixed 400px form column via
  `minmax(0,1fr) 400px`, but the `.panel` grid item wrapping the 16-column
  channel grid had no `min-width:0` -- the classic CSS Grid trap where a
  grid item's default `min-width: auto` keeps it from shrinking below its
  content's intrinsic width even when its track is allowed to. Added
  `min-width:0` to `.panel` (this component's only user of that class) and
  a `@media(max-width:900px)` rule that stacks the layout to one column and
  drops the channel grid to 8 columns, matching the responsive pattern
  already used elsewhere in this file (e.g. the inventory edit form).
  Verified by inspecting the emitted CSS for both rules; jsdom has no real
  layout engine, so this could not be re-verified by measuring rendered
  pixel widths the way the JS logic fixes were.
- **`test_rule` accepted out-of-range DMX values** ("valeurs invalides
  [256,-1] : aucune erreur affichée, ... ni rejet ni normalisation
  démontrés"): `services/rules.py`'s `_test_rule` passed caller-supplied
  values straight to the rule engine with only an `int(v)` cast -- no
  range check, despite DMX channel values being single bytes (0-255). Now
  rejects with a clear `DMX values must be between 0 and 255 (got
  out-of-range: [...])` before evaluating, which `guarded()` (added
  earlier this version) surfaces to the user instead of the previous
  silent no-op. Validated directly against the audit's own test values.

## 0.15.27 (suite 2) — Rule Builder channel-selection persistence

Same class of bug as the DMX channel selection fix, on a different
component the earlier pass missed: `show-network-rule-builder`'s
`connectedCallback` re-runs fresh every time the dashboard recreates this
element (same `_mountPanels` behavior as every other case in this
version), which reset its `selected` channel Set to empty -- exactly the
audit's own wording: "Clic 142 puis 1 sans sélection persistante
vérifiable." Fixed with the same sessionStorage approach as the DMX view.
Re-verified with the same real destroy+recreate jsdom methodology (not
just a new `hass` push on the same instance).

Deliberately scoped to just the channel selection, matching what the
audit specifically flagged -- the rest of that component's form (rule
name, thresholds, delays, action JSON, which rule is being edited) is
not yet covered by this fix and would reset the same way if the element
is recreated mid-edit; left for a future pass.

## 0.15.27 (suite) — Frontend persistence fixes, second pass

The first pass on the frontend added a per-instance "draft" object to the
DMX zones and HA Builder forms so a form's own re-render wouldn't wipe it.
That was real but insufficient: `_mountPanels()` in the dashboard shell
calls `document.createElement(tag)` fresh on *every* hass-triggered
re-render while a module tab is open, not just on navigation -- so the
whole element (and anything stored on `this`) is torn down and replaced
constantly, not merely re-rendered in place. A rigorous jsdom test that
actually destroys and recreates the element (matching `_mountPanels`
exactly, instead of only pushing a new `hass` value onto the same
instance) proved the first-pass fix did not survive that. Corrected by
moving all four affected drafts into `sessionStorage`, the same
survives-recreation mechanism already used for `selectionKey` (observed
universe) and now DMX channel selection:

- DMX → HA Zones creation form (`dmx-ha-zones-panel`)
- HA Builder creation form (`show-network-ha-builder-panel`)
- **Device inventory edit form** (`show-network-inventory`) -- this is
  the audit-confirmed case: "Modifier sur Luminex ... à l'observation
  suivante le formulaire disparaît spontanément, Annuler introuvable."
  The panel already had an `if(!this._editing)` guard against re-render,
  but that guard lived on the same destroyed-and-replaced instance and
  so did nothing against the dashboard recreating the whole element.
  Now restores the in-progress edit (which record, which field values)
  on the next render after recreation, and clears the persisted draft on
  both Cancel and successful Save so it never leaks into a later,
  unrelated edit.

All four re-verified with a jsdom harness that performs a real
`document.createElement` + reattach (not just a new `hass` push on the
same instance), which is what actually reproduces the audit's observed
failures; the harness reproduces every one of them against the
unmodified 0.15.19-dev29 bundle and confirms all four are fixed here.

### Investigated, not a bug
- **Archives and Constructeurs pages ("FAIL UI", only a title/back
  button observed)**: both `show-network-archive-panel` and
  `show-network-brand-catalog` are fully implemented in this codebase
  (backup/export/restore, notifications, diagnostics bundle, flight
  recorder timeline; brand search/filter/add/delete) with their data
  dependency (`static/data/brands.json`) present and well-formed. This
  matches the already-fixed frontend-version-mismatch bug: the audit was
  very likely looking at a still-older deployed build than even this
  zip's stale 0.15.19-dev29, not a genuinely empty page in this source.
- **Topology node-count mismatch (55 "nœuds" in Pro vs 21 "équipements"
  on the Network page)**: different metrics by design, not a counting
  bug. `sensor.dmx_monitor_topology_nodes` (Pro) counts every topology
  graph node, which `ShowTopology.ingest_inventory()` and
  `observe_protocol()` populate from *both* the device inventory *and* a
  synthetic node per observed DMX source/universe/MA-Net3 station --
  one console emitting on several universes contributes several nodes
  without being several physical devices. The Network page's
  "équipements" pill counts only resolved device-inventory records. Left
  alone; the two numbers measuring different things isn't a defect, but
  labeling them more clearly (e.g. "nœuds topologie" vs "équipements
  inventoriés" consistently on both pages) would be a reasonable follow
  -up UX item.

## 0.15.27 — Fixes from the 20-21/09 remote audit (RAPPORT_SHOW_NETWORK_0_15_26_AUDIT_DISTANT_final.md)

Every item below traces to a specific PASS/FAIL/PARTIEL line in the audit
report, or was found while fixing one of those and confirmed independently
in this codebase (noted where that's the case). No deletions, no live
config changes, no password/secret changes -- source-only, following the
audit's own constraints.

- **Root-cause, not per-symptom: `hass.async_add_executor_job()` does not
  accept keyword arguments** (it only forwards `*args`). Three call sites
  passed kwargs directly, which raises a `TypeError` at the call, not at
  definition -- so it was silent until actually exercised:
  - `services/archive.py` (`diagnostics_export`) -- audit DEV/FAIL,
    confirmed in logs: `TypeError: ... got an unexpected keyword argument
    'config_status'`.
  - `coordinator.py` (`async_save_dmx_ha_zones`, DMX→HA zone creation) --
    audit FAIL, confirmed in logs: `... unexpected keyword argument
    'encoding'`.
  - `services/projector.py` (`projector_power`/`projector_input`/
    `projector_mute`) -- **not in the audit** (projector commands were
    NON TESTABLE, no reachable hardware) but the exact same pattern; would
    have failed identically on the first real command. Found via an
    AST-wide scan for this pattern after the two audit-confirmed cases
    made the shape of the bug obvious; scan is now clean (0 remaining).
  All three fixed with `functools.partial`, which is the correct way to
  bind keyword arguments before handing a callable to `run_in_executor`.

- **HA Builder: `"false"` (text) silently turned a switch/binary_sensor
  on.** Python's `bool("false")` is `True` -- any non-empty string is
  truthy. `HABuilder.set_state()` now normalizes recognized textual
  tokens (`false/0/off/no/non` and `true/1/on/yes/oui`, case-insensitive)
  before falling back to `bool()`. Audit FAIL, confirmed.

- **HA Builder: `ha_builder_set_state` accepted out-of-range numbers.**
  Home Assistant's own `number.set_value` service validates against
  `native_min_value`/`native_max_value` before calling
  `async_set_native_value`, but the custom `ha_builder_set_state` service
  wrote straight to storage and skipped that check entirely (audit: 11
  accepted and published with a declared max of 10). `HABuilder.set_state`
  now validates numeric writes against the item's declared bounds and
  raises instead of accepting them silently.

- **HA Builder "button" items were registered under the wrong HA domain.**
  `BuilderButton` (a `ButtonEntity`) was added via `switch.py`'s
  `async_add_entities`, which puts an entity under `switch.*` rather than
  `button.*`. That's why a button-type item showed up as
  `switch.<id>=unknown` and `switch.turn_off` on it raised
  `'BuilderButton' object has no attribute 'async_turn_off'` (audit FAIL,
  confirmed in logs). Added a dedicated `button.py` platform (mirroring
  `number.py`), registered `"button"` in `PLATFORMS`, and removed the
  erroneous registration from `switch.py`.

- **HA Builder "number" items were being created twice.** `sensor.py`
  *also* added every `number`-type item via its own `async_add_entities`
  (leftover from before `number.py` existed), in addition to the correct
  one from `number.py` -- a second, wrong-domain duplicate every time.
  This matches the audit's own observation almost verbatim: "un sensor
  portant aussi le nom du nombre est maintenant visible en plus de
  number". Removed the duplicate from `sensor.py`; `number.py` is now the
  sole owner of `entity_type == "number"`.

- **Service errors were shown to the user as generic "Unknown error"**
  regardless of cause, even when the backend already raised a clear,
  specific message -- audit-confirmed for all four locked-control
  rejections (OSC/MIDI/Show Control/config restore, all
  `"Active control is locked"` in the logs but "Unknown error" in the UI)
  and for QLC+ (`"QLC+ is not configured (see Show Network options)"` in
  the logs, "Unknown error" in the UI). Cause: Home Assistant's frontend
  only surfaces the exception message for `HomeAssistantError` (and its
  `ServiceValidationError` subclass); any other exception type collapses
  to a generic toast. `security.py` deliberately raises plain
  `PermissionError` and stays free of any Home Assistant import (that's
  intentional -- see its own tests, which run without the HA test
  harness), so the fix lives at the HA-facing boundary instead: a new
  `services/common.guarded()` wraps a service handler and translates
  `PermissionError` / `ValueError` / `RuntimeError` / `LookupError` into
  `ServiceValidationError` with the same message. Applied to all 95
  `hass.services.async_register(...)` call sites across every
  `services/*.py` module (scripted, then verified by an AST walk that
  every single one is wrapped). Programming bugs (`AttributeError`,
  `TypeError`, `KeyError`, ...) are deliberately left unwrapped so they
  keep surfacing as real errors in the log instead of being repackaged as
  a misleading validation message.

### Investigated, not a code fix
- **OSC port 8000 stuck as `port_in_use` even after a full Home Assistant
  restart.** `runtime/setup.py` already retries once on `Errno 98` (for
  the ordinary reload/UDP-teardown race) and `config_flow.py` already has
  a pre-flight `_udp_port_available` check that blocks saving a taken
  port. UDP sockets have no TIME_WAIT state, so a full process restart
  releases anything Home Assistant itself held -- if the port is still
  taken right after a clean restart, something *outside* this Home
  Assistant process is bound to it. Not fixable in this integration's
  code; check what else on the host holds UDP/8000 (`ss -ulnp | grep
  8000`) or change the OSC port in the integration's options.

### Known gap, out of scope for this pass
- `ha_builder_remove_callbacks` is initialized in every platform module
  but never populated anywhere -- removing a HA Builder item deletes it
  from storage but never actually unregisters the live HA entity. Not
  covered by this audit (deletions were explicitly out of scope for that
  session) and is a larger change (each platform needs to track and
  `async_remove()` its own live entity instances); left untouched pending
  its own review.

## 0.15.26 — First real fix from live production data

The user connected a real MCP bridge to their live Home Assistant instance
(Maison de la Culture de Tournai), giving direct read access to real
entity states for the first time in this project's development. Used it
for genuine diagnosis rather than more simulated testing.

- Confirmed live and healthy: sACN reception (9308 packets, universe 10
  active from a real console at 10.2.1.1), MA-Net3 (4259 packets, 3 live
  stations across 258 joined multicast groups), Luminex GigaCore
  correctly identified via MAC/OUI, two real network printers correctly
  identified via genuine SNMP sysDescr text.
- Confirmed and explained (not a bug): both configured ETC CEM3 racks
  show `TimeoutError` -- Show Network's interface (10.4.1.8) and the
  racks (10.2.2.x) are on different subnets, the same class of issue
  already identified for the Cisco switch. Network topology, not code.
- **Real fix, finally unblocked**: retrieved the actual `identity_hints`
  text this project has been asking for since early in this project --
  a real grandMA3 Node reported `"Node-ma-salle-b"`, a site-specific
  custom label, not MA Lighting's own product-name text. None of the
  strict product-name markers matched it, so it stayed permanently
  "non classifiée" no matter how long it ran. Added a fallback:
  a word-boundary match on a generic category word (node/console/npu)
  in the identity text, honestly labeled as inferred from a custom
  label rather than a confirmed product name, so it is never confused
  with an exact product-name match. Tested directly against the real
  captured value, plus regression tests confirming exact-product
  matching and empty-hint (correctly unclassified) cases are unaffected.

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

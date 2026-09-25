
### 0.15.19-dev6 — Flight Recorder avancé
- Analyse bornée des 100 derniers événements du journal, avec classification info/warning/error/recovery.
- Corrélation temporelle ±20 s autour des incidents, sans déduction de cause.
- Panneau « Que s’est-il passé ? » : dernier incident, événements voisins, familles de protocoles et timeline récente.
- Les données restent issues du journal existant : aucune capture brute de paquets ni trafic réseau supplémentaire.

# Show Network & Stage Control Suite for Home Assistant

> **⚠️ EXPÉRIMENTAL / EXPERIMENTAL**  
> Show Network est un projet expérimental destiné aux réseaux techniques du spectacle vivant. Il ne doit pas être considéré comme un système de sécurité, de protection électrique ou de contrôle critique. Testez chaque fonction sur un réseau et du matériel de test avant toute utilisation en production. Certaines fonctions dépendent du matériel, du firmware, des protocoles réellement exposés et de composants externes.

---

# 🇫🇷 Français

## Présentation

**Show Network & Stage Control Suite** est une intégration personnalisée pour Home Assistant destinée à la supervision et au show control des réseaux professionnels du spectacle : lumière, audio sur IP, vidéo, réseau, projecteurs, gradateurs et protocoles de contrôle.

Le projet privilégie une règle simple : **ne pas inventer de télémétrie**. Une information présentée comme réelle doit provenir d'un paquet observé, d'une interrogation documentée ou d'une configuration explicitement fournie. Les fonctions actives sensibles sont séparées de la supervision et protégées par des mécanismes d'activation.

## Fonctions principales

- **DMX / lumière** : réception sACN et Art-Net, diagnostic par univers, DMX → Home Assistant, règles, zones, Highlight et courbes de dimmer.
- **HA → DMX** : banque de **19 scènes DMX** sur un univers sélectionné, sortie sACN, Art-Net ou ENTTEC USB Pro. Une source DMX externe sur cet univers prend automatiquement la priorité ; la scène HA mémorisée reprend après disparition de la source externe.
- **GDTF** : import de fichiers `.gdtf`, patch de projecteurs, attributs exposés à Home Assistant et sortie fixe sACN/Art-Net protégée.
- **RDM / RDMnet** : inventaire, UID, identité, adresse DMX, personnalité et télémétrie disponible via bridges configurés. Les écritures RDM sont volontairement protégées.
- **grandMA3 / réseau lumière** : supervision passive MA-Net3 et outils de réseau spectacle.
- **Audio IP** : observation Dante, AES67/SAP, PTP, AES70/OCA et inventaire d'amplificateurs lorsque les interfaces documentées sont disponibles.
- **Projecteurs vidéo** : supervision PJLink et adaptateurs documentés pour les familles prises en charge ; commandes actives derrière la sécurité Show Network.
- **Vidéo IP** : supervision séparée, sans création de sensors HA, avec sélection de l'interface réseau et aperçu basse qualité optionnel lorsqu'une URI réellement exploitable est connue.
- **OSC / MIDI / Show Control** : réception et émission OSC, MIDI, mappings, cues Show Control et enchaînement d'actions Home Assistant/OSC/MIDI/scènes DMX.
- **PunchLight** : intégration des informations réseau/MIDI disponibles sans simuler un stack RTP-MIDI inexistant.
- **Tally IP** : réception passive TSL UMD sur UDP et un `binary_sensor` global **Tally IP — ON**.
- **ETC Sensor3 / CEM3** : supervision en lecture seule des racks configurés et sensors Home Assistant pour les informations réellement disponibles.
- **Réseau** : multi-interface, découverte prudente, SNMP, LLDP, topologie, profils Luminex/GigaCore et inventaire.
- **Persistance** : sauvegarde/restauration de la configuration Show Network, manifest SHA-256 et bundle de diagnostics avec masquage des secrets.
- **Interface Show Network** : cockpit, inventaire, bibliothèques constructeurs, pages spécialisées et raccourcis cliquables entre modules.

## Installation manuelle

### 1. Copier l'intégration

Téléchargez la version publiée de Show Network et copiez **le dossier complet** :

```text
custom_components/dmx_monitor
```

dans le dossier `custom_components` de votre configuration Home Assistant. Le résultat doit être :

```text
/config/custom_components/dmx_monitor/
```

avec notamment `manifest.json`, `__init__.py`, `config_flow.py`, `services.yaml`, les modules Python et le dossier `static`.

Si `/config/custom_components/` n'existe pas, créez-le.

### 2. Redémarrer Home Assistant

Effectuez un **redémarrage complet de Home Assistant** après la copie ou la mise à jour des fichiers.

### 3. Ajouter Show Network

Dans Home Assistant :

**Paramètres → Appareils et services → Ajouter une intégration → Show Network**

Ajoutez l'intégration puis ouvrez ses options pour sélectionner les interfaces réseau et activer uniquement les modules dont vous avez besoin.

### 4. Commencer en mode supervision

Pour une première installation, laissez les sorties actives désactivées. Configurez d'abord les cartes réseau, vérifiez la découverte et la réception des protocoles, puis activez séparément les fonctions de contrôle nécessaires.

Les gates de sécurité de sortie sont conçus pour revenir dans un état sûr après redémarrage ; ne supposez jamais qu'une sortie active avant un redémarrage sera automatiquement réarmée.

## Mise à jour manuelle

1. Faites une sauvegarde Home Assistant et, si possible, un backup Show Network.
2. Remplacez `/config/custom_components/dmx_monitor/` par la nouvelle version complète.
3. Ne conservez pas volontairement d'anciens fichiers Python/JavaScript provenant d'une version précédente.
4. Redémarrez Home Assistant.
5. Contrôlez les journaux et l'interface Show Network avant de réactiver les sorties.

## Configuration réseau

Show Network est conçu pour les machines Home Assistant possédant plusieurs interfaces réseau. Les modules qui le permettent peuvent être liés à une interface/adresse précise afin d'éviter d'écouter ou d'émettre sur le mauvais réseau.

Sur un réseau de spectacle, vérifiez particulièrement :

- l'adressage IP et les VLAN ;
- la présence des routes nécessaires ;
- le multicast sACN/AES67/PTP ;
- les règles IGMP/snooping du réseau ;
- les ports UDP/TCP nécessaires aux protocoles utilisés ;
- l'interface sélectionnée dans Show Network.

Show Network ne remplace pas la configuration correcte des switches, VLAN, QoS, PTP ou équipements constructeurs.

## Sécurité et limites

Show Network est **expérimental**. Les tests automatisés vérifient le logiciel, pas votre installation physique. Tous les matériels, firmwares et topologies ne peuvent pas être reproduits pendant le développement.

Les fonctions de contrôle peuvent agir sur des équipements réels. Utilisez les gates, le verrouillage central et les permissions constructeurs. Ne branchez jamais une fonction expérimentale directement à une action pouvant compromettre la sécurité des personnes, une alimentation critique, un mouvement scénique ou une installation sans protection indépendante appropriée.

Certaines intégrations nécessitent un helper ou une bibliothèque externe. En particulier, le support RDMnet natif dépend d'un bridge compatible ; la présence d'une interface dans Show Network ne signifie pas qu'un protocole propriétaire non documenté a été réimplémenté.

## Développement et validation

La branche de développement est contrôlée par tests automatisés, compilation Python et validation syntaxique du frontend. Cela **ne constitue pas une certification matérielle**.

Avant production : testez sur votre version de Home Assistant, votre matériel, votre firmware et votre réseau.

---

# 🇬🇧 English

## Overview

**Show Network & Stage Control Suite** is a custom Home Assistant integration for monitoring and show control on professional live-event networks: lighting, audio-over-IP, video, networking, projectors, dimmers and control protocols.

The project follows a strict principle: **do not invent telemetry**. Information presented as live data must come from observed packets, documented queries or explicit configuration. Sensitive active-control features are kept separate from monitoring and protected by enable/safety gates.

## Main features

- **DMX / lighting**: sACN and Art-Net reception, per-universe diagnostics, DMX → Home Assistant mappings, rules, zones, temporary Highlight and dimmer curves.
- **HA → DMX**: bank of **19 DMX scenes** on one selected universe, using sACN, Art-Net or ENTTEC USB Pro. An external DMX source on that universe automatically takes priority; the memorized HA scene resumes after the external source disappears.
- **GDTF**: `.gdtf` import, fixture patching, Home Assistant attributes and guarded fixed-state sACN/Art-Net output.
- **RDM / RDMnet**: inventory, UID, identity, DMX start address, personality and available telemetry through configured bridges. RDM writes are intentionally guarded.
- **grandMA3 / lighting network**: passive MA-Net3 monitoring and show-network tools.
- **Audio over IP**: Dante observation, AES67/SAP, PTP, AES70/OCA and amplifier inventory when documented interfaces are available.
- **Video projectors**: PJLink monitoring and documented adapters for supported product families; active commands remain behind Show Network security.
- **IP video**: separate monitoring mode with no HA sensor creation, selectable network interface and optional low-quality preview when a real usable URI is known.
- **OSC / MIDI / Show Control**: OSC input/output, MIDI, mappings, Show Control cues and chained Home Assistant/OSC/MIDI/DMX-scene actions.
- **PunchLight**: available network/MIDI integration without pretending to provide a non-existent RTP-MIDI stack.
- **IP Tally**: passive TSL UMD UDP reception with one global **Tally IP — ON** binary sensor.
- **ETC Sensor3 / CEM3**: read-only monitoring of configured racks and Home Assistant sensors for data that is actually available.
- **Network**: multi-interface support, conservative discovery, SNMP, LLDP, topology, Luminex/GigaCore profiles and inventory.
- **Persistence**: Show Network configuration backup/restore, SHA-256 manifest and redacted diagnostics bundle.
- **Show Network UI**: cockpit, inventory, manufacturer libraries, specialized pages and clickable navigation between modules.

## Manual installation

### 1. Copy the integration

Download the released Show Network package and copy the **complete** folder:

```text
custom_components/dmx_monitor
```

into the `custom_components` directory of your Home Assistant configuration. The resulting path must be:

```text
/config/custom_components/dmx_monitor/
```

It must include `manifest.json`, `__init__.py`, `config_flow.py`, `services.yaml`, the Python modules and the `static` directory.

Create `/config/custom_components/` if it does not already exist.

### 2. Restart Home Assistant

Perform a **full Home Assistant restart** after copying or updating the integration.

### 3. Add Show Network

In Home Assistant, open:

**Settings → Devices & services → Add integration → Show Network**

Add the integration, then open its options to select network interfaces and enable only the modules you need.

### 4. Start in monitoring mode

For the first setup, keep active outputs disabled. Configure network interfaces first, verify discovery and protocol reception, then enable required control features individually.

Output safety gates are designed to return to a safe state after restart; never assume an output that was armed before a restart will automatically be re-armed.

## Manual update

1. Create a Home Assistant backup and, when possible, a Show Network backup.
2. Replace `/config/custom_components/dmx_monitor/` with the complete new version.
3. Do not intentionally keep old Python/JavaScript files from a previous release.
4. Restart Home Assistant.
5. Check logs and the Show Network UI before re-enabling active outputs.

## Network configuration

Show Network is designed to work on Home Assistant hosts with multiple network interfaces. Modules that support it can be bound to a specific interface/address to avoid monitoring or transmitting on the wrong network.

On a live-event network, pay particular attention to IP addressing/VLANs, routing, sACN/AES67/PTP multicast, IGMP/snooping, required UDP/TCP ports and the interface selected in Show Network.

Show Network does not replace correct switch, VLAN, QoS, PTP or manufacturer-device configuration.

## Safety and limitations

Show Network is **experimental**. Automated tests validate software behavior, not your physical installation. Every hardware model, firmware release and network topology cannot be reproduced during development.

Control features may affect real equipment. Use safety gates, central locking and manufacturer permissions. Never connect an experimental function directly to an action that could endanger people, critical power, stage motion or an installation without suitable independent protection.

Some integrations require an external helper or library. Native RDMnet functionality in particular depends on a compatible bridge; an interface being present in Show Network does not mean an undocumented proprietary protocol has been reverse-engineered or fully implemented.

## Development and validation

Development builds are checked with automated tests, Python compilation and frontend syntax validation. This **is not hardware certification**.

Before production use, validate the integration with your Home Assistant version, hardware, firmware and network.

---

## Project structure

```text
custom_components/dmx_monitor/
├── core/             # contracts, state and observability
├── protocols/        # protocol adapters and catalogs
├── services/         # Home Assistant service logic
├── runtime/          # async runtime composition and lifecycle
├── translations/     # translations
└── static/           # Show Network frontend
```

### Cartes dashboard Home Assistant (0.15.19-dev10)
Le frontend Show Network enregistre deux cartes Lovelace : `custom:show-network-timecode-card` et `custom:show-network-onair-card`. Elles réutilisent les entités Show Network existantes et n'ajoutent aucune commande fictive. La carte On Air affiche OFF/READY/ON AIR selon les états PunchLight réellement reçus.

### Cartes Lovelace Show Network (0.15.19-dev11)
En plus du Timecode et de PunchLight, le bundle frontend fournit : `custom:show-network-ma3-card`, `custom:show-network-ptp-card`, `custom:show-network-dante-card`, `custom:show-network-doctor-card`, `custom:show-network-snapshot-card`, `custom:show-network-projectors-card`, `custom:show-network-power-card` et `custom:show-network-dmx-card`.

Exemple DMX (l'univers est toujours choisi explicitement) :
```yaml
type: custom:show-network-dmx-card
entity: binary_sensor.<votre_entite_univers_dmx>
name: Univers 10 · Gradateurs
```
Les autres cartes peuvent fonctionner par découverte de l'entité Show Network correspondante, mais il est possible de fournir `entity:` pour figer explicitement l'entité utilisée. Les cartes de statut n'envoient aucune commande réseau; un appui ouvre la fiche Home Assistant de l'entité. Les commandes actives restent dans les modules Show Network protégés par leurs gates de sécurité.


### Configuration UI (dev12)
Le menu Modules est organisé par usage plutôt que par architecture interne. Parcours conseillé : Réseau & interfaces → Protocoles spectacle → Équipements → Contrôles & automatisations → Home Assistant & dashboard → Sécurité & diagnostic. Les pages indiquent explicitement leur rôle et les commandes actives restent protégées par le backend de sécurité.

### Dashboard Régie Home Assistant (dev13)
La carte composite `custom:show-network-regie-card` assemble les états réels Show Network dans une vue responsive tablette/PC. Elle découvre les entités Show Network déjà exposées pour Timecode, PunchLight, Show Snapshot, MA-Net3, Dante, PTP, Doctor, projecteurs et Power Manager. Les univers DMX restent explicitement configurés pour éviter toute sélection implicite.

Exemple minimal :
```yaml
type: custom:show-network-regie-card
name: Régie principale
```

Avec univers DMX :
```yaml
type: custom:show-network-regie-card
name: Régie principale
dmx_entities:
  - entity: binary_sensor.<univers_10>
    name: Univers 10 · Gradateurs
  - entity: binary_sensor.<univers_8>
    name: Univers 8 · Salle
```

### Cartes infrastructure Home Assistant (dev14)
Le dashboard Régie inclut désormais des vignettes en lecture réelle pour les interfaces réseau locales, switches/ports, amplificateurs, appareils Apple/Mac confirmés et l'inventaire Show Network consolidé. Les états absents restent INCONNU/vides et aucune commande d'infrastructure n'est ajoutée implicitement.

### Supervision des ports (dev17)
Quand un switch est identifié et que SNMP read-only est configuré, Show Network lit les compteurs standards IF-MIB/ifXTable. Les débits RX/TX ne sont calculés qu'après deux échantillons valides; les erreurs RX/TX et changements LLDP sont corrélés au Doctor et au Flight Recorder. Aucun SNMP SET n'est émis.

La recette frontend `tools/audit_frontend.py` vérifie les routes/modules littéraux, panneaux montés, cartes Lovelace et services déclarés afin d'éviter les liens ou commandes sans destination.


### Dante / Audio Network Health (dev18)
La page Audio/Dante existante regroupe Clock/PTP, bande passante et Layer 1, latence/packet health, routing/subscriptions, redondance, inventaire, multicast/IGMP, Audio Health et événements. Les métriques propriétaires non disponibles depuis l'observation passive sont affichées `NON MESURÉ` et ne sont jamais déduites du simple trafic. Le seuil 70% est un avertissement conservateur de conception; 85% correspond au repère Audinate approximatif pour l'utilisation RX/TX afin de préserver les performances de synchronisation.

### Console Audio Réseau (dev21)
La page Dante/Audio existante adopte une présentation de type console de régie. Les vumètres Peak/RMS ne sont actifs que si une entité `audio_levels` ou `audio_channel_levels` expose de vraies mesures par canal. En l'absence de cette télémétrie, la banque reste explicitement « niveaux non disponibles » : le trafic réseau Dante n'est jamais converti artificiellement en niveau audio.

### Dante Managed API (dev22)
Show Network peut utiliser en lecture seule l'API GraphQL documentée de Dante Director ou Dante Domain Manager pour compléter la supervision passive. Renseigner l'URL GraphQL, la clé API et, si nécessaire, l'ID du domaine dans les options. Le client implémenté ici n'expose aucune mutation : il lit les statuts de domaine/appareils et les subscriptions RX. Sans cette configuration, la page Dante reste entièrement passive et indique ces données comme non mesurées.

Le `Signal Presence` Dante n'est pas un vumètre Peak/RMS. Show Network ne transforme donc jamais un état silence/présence/clipping en niveau dBFS fictif. Les vrais vumètres exigent une source Peak/RMS explicite ou une réception audio autorisée.

### Incident Center et Pre-Show Check (dev23)
Incident Center regroupe les événements observés dans la même fenêtre temporelle et les équipements reliés par preuve. Il ne présente jamais cette corrélation comme une cause racine.

Pre-Show Check est entièrement read-only. Un contrôle non mesurable vaut `UNKNOWN`; l'état `READY` n'est émis que lorsqu'aucun contrôle applicable n'est en échec et qu'aucun contrôle de la checklist n'est inconnu. `NOT_READY` signale au moins un échec explicite; `CHECK` demande une vérification humaine ou une source de données supplémentaire.

### Snapshot Compare et Timecode Live (dev24)
La référence spectacle capture uniquement des faits observés. La comparaison peut signaler un changement de port/VLAN/firmware/vitesse/LLDP et, lorsque Dante Managed API était disponible lors des deux captures, un changement de subscription. Une donnée absente d'une capture n'est pas considérée comme un changement.

Timecode Live décode passivement Art-Net ArtTimeCode depuis le socket Art-Net existant. La vue expose TC courant, source, FPS, drop/non-drop, lock/perte, âge, compteur de paquets et intervalle du dernier paquet. Elle ne considère pas un saut de TC comme une erreur car un repositionnement peut être volontaire.


### Timecode corrélé (dev25)
La vue Timecode accepte Art-Net ArtTimeCode et, lorsque MIDI IN est configuré, MIDI Time Code quarter-frame. MTC n'est publié qu'après réception d'un jeu complet de huit quarter-frames. Les pertes/récupérations et changements de source/transport/FPS sont archivés et deviennent corrélables dans Incident Center. Pre-Show considère un signal précédemment observé puis perdu comme FAIL, mais un timecode jamais observé comme UNKNOWN car Show Network ne peut pas deviner si le spectacle en exige un. LTC n'est pas simulé sans source audio/décodeur réel.

### Profil Pre-Show optionnel (dev26)
Le profil spectacle Pre-Show est facultatif et persistant. Sans profil actif, Show Network conserve son comportement de monitoring général. Lorsqu'il est activé, il ajoute des attentes de diagnostic (univers, équipements, Timecode, Dante/PTP, switches, amplis, projecteurs). Un FAIL Pre-Show n'est jamais un verrou et ne désactive aucune fonction Show Network.

### Dashboard / incidents / topologie (dev27)
Les cartes `show-network-incident-card` et `show-network-pre-show-card` donnent une synthèse Lovelace fondée sur les capteurs réels. Le Pre-Show reste optionnel et non bloquant. La topologie colore une liaison seulement lorsqu'une télémétrie de port réellement associable est disponible.


### Incident Center persistant (dev28)
Les corrélations d’incidents ont un cycle de vie opérateur persistant. `ACTIVE`, `ACKNOWLEDGED` et `RESOLVED` sont des états de diagnostic uniquement : acquitter un incident ne masque pas la télémétrie et ne commande aucun équipement. La résolution automatique exige une preuve de récupération ultérieure dans la même famille d’événements.

### Favoris de régie et sécurité (dev29)
La découverte réseau reste large. Une étoile ★ ne coupe pas la découverte: elle enregistre réellement `monitor_mode=monitor` dans les overrides persistants et sert à prioriser le périmètre opérationnel. Les listes Inventaire et Auto Discovery proposent Tous/Favoris/Non favoris/Ignorés et une recherche nom/IP/MAC/type/interface. Le formulaire de sécurité conserve sa saisie pendant les rafraîchissements live du frontend afin qu'un mot de passe puisse être saisi et validé sans être effacé par un rerender.


### Périmètre régie et découverte (dev30)
La découverte réseau reste volontairement large. Les états Auto, ★ Favori (`monitor`) et Ignoré (`ignore`) organisent le périmètre opérateur et les vues, mais ne doivent pas créer un angle mort dans le scan général. Une IP connue peut être ajoutée explicitement avec `register_manual_device`; elle est marquée comme cible opérateur et non comme appareil automatiquement découvert.

Les formulaires Sécurité et Pre-Show conservent leur brouillon pendant les mises à jour live du dashboard afin qu’un rafraîchissement de télémétrie ne puisse plus effacer une saisie en cours.


### Audit chaîne fonctionnelle (dev31)
L’audit statique vérifie désormais la chaîne UI → déclaration Home Assistant → enregistrement backend pour chaque service littéral appelé par le frontend principal. La recette compare aussi l’ensemble du catalogue `services.yaml` aux enregistrements backend littéraux. Cela détecte les services décoratifs/non enregistrés, mais ne remplace pas un essai matériel pour les protocoles externes. Le Pre-Show des amplificateurs se base sur les champs réellement produits par `AudioAmplifierInventory` (`online`, `error`). Aucune fonction existante n’a été supprimée dans cette passe.

### Audit protocolaire dev32
RDM/RDMnet sépare désormais strictement la présence d’un UID en cache de la fraîcheur de la dernière observation réelle du bridge. Une panne du helper ne peut plus maintenir artificiellement un responder en ligne. Le transport RDM/RDMnet actuel reste un **helper bridge HTTP explicitement configuré** (`/v1/devices`, `/v1/set`) : Show Network ne prétend pas embarquer une pile native OLA ou RDMnet dans HA OS. Les écritures restent doublement protégées par le verrou sécurité et l’option d’armement RDM.

Pour ETC Sensor3/CEM3, l’interface distingue les informations documentées des requêtes Web de lecture fixes validées/observées sur matériel; aucune commande de configuration CEM3 n’est envoyée. Les projecteurs conservent PJLink comme transport standard/fallback et les adaptateurs constructeur uniquement lorsqu’un profil explicite est configuré.


### Audit protocolaire dev33
QLC+ distingue désormais une réponse API réellement reçue d’une simple écriture WebSocket sans accusé protocolaire. `setFunctionStatus` lève une erreur si aucune réponse correspondante n’arrive. Les commandes Virtual Console haute fréquence restent utilisables mais sont exposées comme `sent_unconfirmed`. Le Power Manager expose son état comme état **commandé** par DMX, et non comme confirmation physique du relais/alimentation. Les modes Auto/Surveiller/Ignorer de l’inventaire restent des choix de filtrage/priorité et ne réduisent pas la découverte réseau générale. Aucun module n’a été supprimé pendant cette passe.


### Vérité temps réel audio / contrôle (dev34)
Les compteurs historiques restent disponibles pour diagnostic, mais les vues opérationnelles utilisent des preuves fraîches: sources Dante fraîches, Grandmaster PTP actif distinct du dernier GM observé, membres MA-Net3 LIVE distincts des membres historiques. PunchLight devient indisponible si son entrée MIDI est en erreur au lieu de conserver un ancien ON AIR/READY comme état fiable. Les corrélations Doctor/Flight Recorder restent descriptives et ne transforment pas une proximité temporelle en cause racine.


### Identité réseau multi-NIC (dev35)
La découverte reste large sur toutes les interfaces, mais l’identité est volontairement conservatrice. Une même IPv4 présente sur deux interfaces explicites n’est pas fusionnée. Les annonces mDNS et leur enrichissement constructeur partagent le même enregistrement; un hostname DNS-SD n’est jamais traité comme une adresse IP. LLDP ne fusionne un voisin avec l’inventaire que sur un hostname explicite exact et unique. Pour Apple, Bonjour/OUI peut apporter une preuve constructeur, mais un modèle Mac n’est accepté que lorsqu’un identifiant matériel explicite est réellement observé dans le TXT Bonjour.


### Topologie physique multi-NIC (dev36)
LLDP reste une preuve physique fraîche issue du poll SNMP du switch. Une correspondance avec l’inventaire n’est faite que sur un hostname explicite exact et unique; elle peut alors renseigner switch, port et vitesse de lien. Le VLAN n’est jamais déduit du seul voisin LLDP. Les déplacements de port sur un switch restent journalisés et un déplacement entre deux switches est également enregistré lorsque le `remote_system` LLDP est unique; un nom dupliqué reste volontairement ambigu. Les identités de switch incluent l’interface réseau afin que deux réseaux isolés réutilisant les mêmes IP ne soient pas confondus. Les favoris sont seulement priorisés visuellement: les autres équipements restent visibles.

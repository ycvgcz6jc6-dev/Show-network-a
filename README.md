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

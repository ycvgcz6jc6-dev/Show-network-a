# Show Network & Stage Control Suite for Home Assistant

Une intégration Home Assistant orientée supervision, contrôle et passerelle pour les réseaux professionnels du spectacle vivant : lumière, audio sur IP, vidéo, show control et infrastructure réseau.

## 🚀 Fonctionnalités clés

- **Lumière & scène** : réception/émission sACN, Art-Net, MA-Net3, DMX/ENTTEC, profils constructeurs et pipelines asynchrones bornés.
- **Audio sur IP** : supervision Dante, AES67, AES70/OCA et PTP IEEE 1588.
- **Show control** : OSC, MIDI, Timecode, mappings, règles et watchdogs.
- **Vidéo & réseau** : ST 2110, SNMP, topologie, capacité et découverte prudente des équipements.
- **DMX → Home Assistant** : mappings, zones, Highlight temporaire avec restauration de l'état précédent et courbes de dimmer configurables.
- **Constructeurs** : catalogue multi-domaines (lumière, son, vidéo, réseau, intercom, contrôle) avec extension de marques et logos PNG.
- **Power Manager** : architecture séparée et actuellement dormante, prévue pour sortie sACN, Art-Net ou ENTTEC avec séquences et temporisations.
- **Performance** : profils Auto, Minimal, Standard et Full ; affichage CPU/RAM et adaptation de la charge non critique.

## ⚙️ Configuration performance

**Auto** est recommandé : Show Network adapte les tâches secondaires selon la pression CPU/RAM. La réception des protocoles et les watchdogs ne sont pas sacrifiés pour rafraîchir l'interface.

**Minimal** est la configuration de référence pour un Home Assistant modeste : télémétrie espacée à 10 s et découverte réduite. Elle vise à limiter l'empreinte de Show Network sans empêcher les fonctions essentielles de supervision.

Standard utilise 5 s ; Full 2 s pour les hôtes plus puissants.

## 🧩 Principe de configuration

Découvert ne signifie pas surveillé : un équipement identifié est proposé avant qu'un watchdog ou une action ne soit activé. Les valeurs et identifications affichées doivent provenir de données observées ou d'un profil explicitement déclaré.

## 🛠️ Installation

1. Copiez `custom_components/dmx_monitor` dans `custom_components/`.
2. Redémarrez Home Assistant.
3. Dans **Paramètres → Appareils et services → Ajouter une intégration**, recherchez **Show Network**.

## 🏗️ Structure

```text
custom_components/dmx_monitor/
├── core/             # contrats, état, observabilité
├── protocols/        # adaptateurs et catalogues
├── services/         # logique métier
├── runtime/          # composition et cycle de vie async
├── translations/     # FR, EN, DE, IT, NL, ES
└── static/           # interface Show Network
```

## 🔬 Validation

Les tests automatisés et contrôles statiques ne constituent pas une validation matérielle. Les tests réels sur Home Assistant, réseau, DMX, audio, vidéo ou matériel constructeur doivent être effectués séparément.

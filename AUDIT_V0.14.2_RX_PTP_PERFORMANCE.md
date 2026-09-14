# Show Network v0.14.2 — RX / PTP / performance

## 🟢 Implémenté et connecté
- Déduplication stable des binary_sensors DMX (casse protocole normalisée).
- PTPv2 default multicast 224.0.1.129 rejoint explicitement sur la NIC configurée; ports 319/320 en réception seule.
- État `ptp_clock_present`, âge, domaine et identité Grandmaster exposés.
- UI Dante/PTP conserve le diagnostic geek et ajoute une synthèse d'horloge.
- Cockpit HA ralenti à 750 ms et contrôle DMX protégé contre les rerenders pendant interaction.
- Test E1.31 de 512 slots ajouté.

## 🟡 À valider sur matériel réel
- Réception sACN/Art-Net sur l'installation réelle.
- Détection PTP/Dante sur l'installation réelle.
- Qualification SNMP de tous les switches présents: la chaîne reste read-only et dépend des réponses SNMP/ARP observables.

## 🔴 Non revendiqué
- Aucun test Home Assistant, console, node, switch Luminex ou appareil Dante réel n'a été exécuté ici.

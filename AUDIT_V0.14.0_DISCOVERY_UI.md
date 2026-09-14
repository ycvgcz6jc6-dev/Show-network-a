# Show Network v0.14.0 — raccordement découverte/UI

Validation locale uniquement, sans prétendre à une validation HA ou matérielle.

## Implémenté
- Navigation DMX précédent/suivant pour faciliter le changement d'univers.
- Enrichissement SNMP read-only borné des voisins ARP si une communauté SNMP est configurée.
- Lecture standard sysDescr/sysName/sysObjectID; classification constructeur uniquement sur marqueurs explicites.
- mDNS Dante/netaudio conservateur vers l'inventaire.
- Page Dante: synthèse + volet Geek Diagnostics repliable.
- Inventaire éditable avec aide du catalogue constructeurs.
- Correctif du formulaire d'ajout constructeur.

## Limites honnêtes
- La réception DMX réelle doit encore être validée sur Home Assistant/matériel.
- SNMP ne trouve que les équipements répondant avec la communauté configurée; aucun brute-force de communautés.
- Dante reste passif: absence de paquet/mDNS ne prouve pas absence d'appareil.
- MA-Net3 session/node reste expérimental/passif; aucune IP de l'installation n'est codée en dur.

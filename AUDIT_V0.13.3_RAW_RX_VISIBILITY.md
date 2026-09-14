# Audit v0.13.3 — Raw RX visibility

## Corrections ciblées

- sACN/E1.31 : correction du calcul d'adresse multicast. Un univers `U` rejoint maintenant `239.255.(U // 256).(U % 256)` ; la v0.13.2 utilisait `U-1`, donc U1 rejoignait `239.255.0.0` au lieu de `239.255.0.1`.
- sACN : le socket écoute maintenant sur `0.0.0.0:5568` puis rejoint les groupes sur l'interface DMX configurée. Ceci évite de lier un socket multicast uniquement à l'adresse unicast locale.
- sACN : diagnostics enrichis avec interface de membership, groupes configurés, groupes effectivement rejoints et erreurs de join.
- MA-Net3 : diagnostics bruts avant toute interprétation : IP source, compteurs par source, taille du dernier datagramme et préfixe brut hex/ASCII. Cela permet de distinguer « paquet absent » de « paquet reçu mais non classifié » et de voir si un node parle réellement.
- Inventaire : les sources MA/DMX observées restent distinguées des entrées ARP existantes ; aucune identification constructeur/nœud n'est inventée sans preuve protocolaire.
- Home Assistant : `fixtures.yaml` n'est plus chargé au moment de l'import Python. Le catalogue est préchargé via `hass.async_add_executor_job()` durant le setup pour éviter la lecture disque confirmée dans la boucle principale.

## Limites

- Aucun test matériel ou Home Assistant réel n'a été effectué dans cette validation locale.
- MA-Net3 reste passif et ne rejoint aucune session ni n'envoie de commande.
- Un node MA totalement silencieux sur les groupes/port écoutés peut apparaître via ARP mais ne sera pas déclaré « MA-Net3 observé » sans paquet réel.

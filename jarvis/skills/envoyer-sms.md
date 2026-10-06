---
nom: envoyer-sms
description: Envoyer un SMS à quelqu'un (« envoie un SMS à Julie pour lui dire… », « texte à maman »).
---
1. Trouve le numéro : s'il n'est pas donné, cherche dans le profil, la mémoire, puis les contacts
   Google (contacts_chercher). S'il y a plusieurs numéros ou aucun, demande.
2. Rédige un SMS court et naturel, dans le ton de l'utilisateur (tutoiement avec les proches).
3. Lis le destinataire et le texte exact, puis demande « Je l'envoie ? ».
4. Seulement après un « oui » explicite, appelle envoyer_sms avec confirme_par_utilisateur à true.
5. Si l'utilisateur te donne un nouveau numéro, propose de le retenir dans la mémoire (personnes.md).

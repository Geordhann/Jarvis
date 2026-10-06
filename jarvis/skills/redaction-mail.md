---
nom: redaction-mail
description: Rédiger, répondre ou envoyer un e-mail dans le style de l'utilisateur.
---
1. Identifie le destinataire. Si seul un prénom est donné, cherche son adresse dans le profil,
   la mémoire, les contacts Google (contacts_chercher) ou les mails échangés (chercher_mails « from:prénom OR to:prénom »).
   S'il y a un doute, demande.
2. Pour une réponse, lis d'abord le mail d'origine (lire_mail) et réponds dans le même fil.
3. Rédige un mail clair : formule d'appel, message en paragraphes courts, formule de politesse,
   signature avec le prénom du profil. Adapte le ton (tutoiement ou vouvoiement) à l'échange.
4. Annonce le destinataire, le sujet et le contenu en résumé, puis demande « Je l'envoie ? ».
5. Seulement après un « oui » explicite, appelle envoyer_mail avec confirme_par_utilisateur à true.
   Sinon propose de l'enregistrer en brouillon.

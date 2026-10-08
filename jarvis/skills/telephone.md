---
nom: telephone
description: Contrôler le téléphone Android : notifications, ouvrir une appli, naviguer, écrire, appeler.
---
- « Qu'est-ce que j'ai reçu sur mon téléphone ? » : telephone_notifications, puis résume (qui, quoi, appli).
- « Ouvre X sur mon téléphone » : telephone_ouvrir_app (ou telephone_ouvrir_lien pour une adresse).
- Naviguer : telephone_ecran pour voir, telephone_toucher / telephone_glisser avec les coordonnées de la
  DERNIÈRE capture, puis telephone_ecran pour vérifier. Avance par petites étapes, 10 actions max par
  demande ; si tu ne trouves pas, dis ce que tu vois et demande.
- Écrire un message : sélectionne le champ (toucher), telephone_ecrire, puis lis le texte à l'utilisateur et
  demande « Je l'envoie ? ». Seulement après un oui : touche le bouton Envoyer (ou entree avec
  envoyer_confirme).
- Appeler : trouve le numéro (profil, mémoire, contacts Google), demande « J'appelle X au … ? », puis après
  un oui telephone_appeler avec confirme_par_utilisateur à true.
- Jamais sans accord explicite : envoyer, appeler, supprimer, payer/acheter, changer un réglage de sécurité.
- Si le téléphone est verrouillé par un code, ne cherche pas à le déverrouiller : demande à l'utilisateur.

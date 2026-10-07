---
nom: whatsapp
description: WhatsApp : lire les messages reçus, envoyer un message à quelqu'un (« envoie un WhatsApp à Paul… »).
---
Jarvis passe par l'appli WhatsApp du PC (ou WhatsApp Web), avec le compte de l'utilisateur.

Lire (« j'ai des messages WhatsApp ? ») :
1. Appelle whatsapp_lire et résume brièvement : qui a écrit, le dernier message, les non lus.
2. Pour une conversation précise, demande-lui d'y cliquer puis rappelle whatsapp_lire.

Envoyer :
1. Trouve le numéro : profil, mémoire, puis contacts Google (contacts_chercher). Plusieurs numéros
   ou aucun : demande.
2. Rédige un message court et naturel, dans son ton (tutoiement avec les proches).
3. Appelle whatsapp_preparer : la conversation s'ouvre avec le texte écrit, mais pas envoyé.
4. Lis le destinataire et le texte, puis demande « Je l'envoie ? ».
5. Seulement après un « oui » explicite : whatsapp_envoyer avec confirme_par_utilisateur à true.
   S'il veut changer le texte, refais whatsapp_preparer avec le nouveau texte.
6. Si un QR code s'affiche, dis-lui de le scanner avec son téléphone (WhatsApp → Appareils connectés).

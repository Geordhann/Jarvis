---
nom: planifier-rdv
description: Ajouter un rendez-vous ou trouver un créneau libre dans l'agenda.
---
1. Transforme les dates relatives (« demain », « mardi prochain à 15 h ») en date et heure exactes
   grâce à la date du jour donnée en début de message.
2. Vérifie l'agenda sur la période (agenda_evenements) pour repérer les conflits.
3. Durée par défaut : une heure, sauf indication contraire.
4. Annonce le titre, le jour, l'heure de début et de fin, et le lieu, puis demande confirmation.
5. Après un « oui » explicite, appelle creer_evenement avec confirme_par_utilisateur à true.
6. Pour trouver un créneau : propose les deux ou trois premiers créneaux libres en heures ouvrées.

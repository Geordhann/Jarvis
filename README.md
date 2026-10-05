# J.A.R.V.I.S. — ton assistant personnel

Un agent à la Iron Man, propulsé par **Claude**. Tu lui parles (à voix haute, sur Telegram,
sur WhatsApp ou dans son interface) et il **agit** : il lit et rédige tes mails, gère ton agenda,
cherche sur le web, ouvre des pages, se souvient de toi, et te répond avec une voix réaliste.

```
            ┌──────────── toi ─────────────┐
   micro « Jarvis… »   Telegram   WhatsApp   interface web
            └──────────────┬───────────────┘
                     moteur d'agent  ◄── profil (qui tu es) + skills + mémoire
                    (Claude + outils)
       ┌──────────┬────────┼─────────┬──────────────┐
     Gmail     Agenda   web/navigateur  mémoire   voix ElevenLabs
```

| Étape | Ce que fait Jarvis | Où |
|---|---|---|
| Modèle d'IA | Claude (Opus 5.5 par défaut, Sonnet ou Haiku pour moins cher) | `jarvis/agent.py` |
| Moteur d'agent | boucle autonome : Claude choisit ses outils, les utilise, recommence jusqu'à finir | `jarvis/agent.py` |
| Qui tu es | un profil que tu remplis, lu à chaque conversation | `~/.jarvis/profil.md` |
| Outils | Gmail, Google Agenda, recherche et lecture web, navigateur | `jarvis/tools/` |
| Mémoire persistante | Jarvis note ce qu'il apprend sur toi dans des fichiers | `~/.jarvis/memories/` |
| Skills | fiches d'instructions pour des tâches précises | `jarvis/skills/`, `~/.jarvis/skills/` |
| Messagerie | Telegram et WhatsApp, texte et vocaux | `jarvis/telegram_bot.py`, `jarvis/whatsapp.py` |
| Voix | ElevenLabs (réaliste) ou voix gratuite | `jarvis/tts.py` |
| Interface | tableau de bord avec réacteur animé par la voix, micro, mains libres | `jarvis/interface/` |

---

## 1. Installation

Il faut Python 3.10 ou plus récent.

```bash
git clone https://github.com/geordhann/jarvis.git
cd jarvis
python -m venv .venv
# Windows : .venv\Scripts\activate     macOS / Linux : source .venv/bin/activate
pip install -r requirements.txt
```

Si **PyAudio** refuse de s'installer :
- Windows : `pip install pipwin && pipwin install pyaudio`
- macOS : `brew install portaudio` puis `pip install pyaudio`
- Linux : `sudo apt install portaudio19-dev python3-pyaudio`

## 2. Configuration guidée

```bash
python -m jarvis --configurer
```

L'assistant te demande, étape par étape : la clé Claude, ton profil, la voix ElevenLabs,
Gmail/Agenda, Telegram, WhatsApp et le démarrage automatique. Tu peux sauter une étape
et y revenir plus tard. Les détails de chaque étape sont ci-dessous.

### Clé Claude (obligatoire)
<https://console.anthropic.com/> → *API Keys* → crée une clé, puis ajoute du crédit dans *Billing*.

### Ton profil : « apprends-lui qui tu es »
```bash
python -m jarvis --profil
```
Ouvre `~/.jarvis/profil.md` : ton métier, tes horaires, tes proches (avec leurs e-mails),
ta façon de travailler, tes projets. Jarvis le relit à chaque conversation.
Ce qu'il apprend ensuite tout seul va dans sa mémoire (`~/.jarvis/memories/`), que tu peux lire et corriger.

### Voix ElevenLabs
<https://elevenlabs.io> → *Profile* → *API Keys*. L'offre gratuite donne environ 10 minutes de voix par mois ;
au-delà, il faut un abonnement (à partir d'environ 5 $/mois). Sans clé, ou si le quota est épuisé,
Jarvis passe automatiquement sur la voix gratuite. La clé ElevenLabs sert aussi à **comprendre tes
messages vocaux** Telegram et WhatsApp.

```bash
python -m jarvis --elevenlabs TA_CLE
python -m jarvis --choisir-voix      # écouter et choisir (Daniel = le plus « Jarvis »)
```
Tu peux aussi utiliser une de tes voix ElevenLabs perso : `python -m jarvis --voix ID_DE_LA_VOIX`.

### Gmail et Google Agenda
Une seule fois, environ 10 minutes :
1. Va sur <https://console.cloud.google.com/>, crée un projet (ex. « Jarvis »).
2. *API et services* → *Bibliothèque* : active **Gmail API** et **Google Calendar API**.
3. *Écran de consentement OAuth* : type **Externe**, ajoute ton adresse Gmail dans **Utilisateurs test**.
4. *Identifiants* → *Créer des identifiants* → **ID client OAuth** → type **Application de bureau**
   → télécharge le fichier JSON.
5. Lance :
   ```bash
   python -m jarvis --connecter-google chemin/vers/le-fichier.json
   ```
   Ton navigateur s'ouvre : connecte-toi et accepte (Google prévient que l'appli n'est pas vérifiée :
   c'est normal, c'est la tienne → *Continuer*).

Jarvis peut alors lire, chercher, rédiger et envoyer des mails, et lire ou ajouter des événements.
**Il annonce toujours un envoi ou un rendez-vous et attend ton « oui » avant de le faire.**
Il ne peut pas supprimer définitivement de mail.

### Telegram
1. Dans Telegram, écris à **@BotFather** → `/newbot` → choisis un nom → copie le **jeton**.
2. `python -m jarvis --telegram LE_JETON`
3. Lance Jarvis, puis envoie `/start` à ton bot : il te répond avec ton identifiant.
4. `python -m jarvis --telegram-autoriser TON_IDENTIFIANT`, puis relance Jarvis.

Seul ton compte peut lui parler. Envoie du texte ou des vocaux (il répond alors aussi en vocal).
`/nouveau` efface la conversation en cours.

### WhatsApp
Plus long que Telegram, car Meta impose un compte développeur :
1. <https://developers.facebook.com/> → *Créer une app* → type **Business** → ajoute le produit **WhatsApp**.
2. Dans *WhatsApp → Configuration de l'API* : note le **Phone number ID**, ajoute ton propre numéro
   comme destinataire, et crée un **jeton d'accès permanent** (utilisateur système dans Meta Business).
3. Dans *Paramètres de l'app → Général* : note la **clé secrète** (App secret).
4. `python -m jarvis --configurer` → étape WhatsApp : colle ces informations. Il t'affiche un
   **jeton de vérification**.
5. Rends le port 8766 accessible depuis Internet avec un tunnel, par exemple :
   ```bash
   cloudflared tunnel --url http://localhost:8766      # ou : ngrok http 8766
   ```
6. Dans Meta, *WhatsApp → Configuration → Webhook* : URL `https://<adresse-du-tunnel>/whatsapp`,
   le jeton de vérification de l'étape 4, puis abonne-toi au champ **messages**.

Seuls les messages signés par Meta et venant de **ton** numéro sont traités. L'interface (port 8765)
n'est jamais exposée par ce tunnel. La messagerie WhatsApp Business peut être facturée par Meta
selon le volume (les réponses dans les 24 h à tes messages sont en général gratuites).

## 3. Utilisation

```bash
python -m jarvis               # micro + interface + Telegram + WhatsApp
python -m jarvis --interface   # pareil, et ouvre l'interface dans le navigateur
python -m jarvis --sans-micro  # sans écoute au micro (interface et messageries seulement)
python -m jarvis --texte       # au clavier dans le terminal
```

**L'interface** : <http://localhost:8765> (visible seulement depuis ton ordinateur).
Clique sur le réacteur pour parler, ou coche **Mains libres** pour qu'il réagisse dès que tu dis
« Jarvis… ». Le réacteur s'anime au rythme de sa voix. Tu y choisis aussi la voix et vois ce qui est connecté.
Le micro de la page fonctionne dans Chrome et Edge.

**Au micro**, Jarvis reste silencieux tant que tu ne dis pas « Jarvis » :

- « Jarvis, quoi de neuf ce matin ? » → agenda du jour, mails importants, météo (skill *briefing-matin*)
- « Jarvis, trie mes mails » → ce qui demande une réponse (skill *tri-mails*)
- « Jarvis, réponds à Marc que je serai en retard » → il rédige, te lit le mail, attend ton « oui »
- « Jarvis, ajoute dentiste jeudi à 15 h » → il vérifie l'agenda puis confirme avec toi
- « Jarvis, retiens que ma fille s'appelle Léa » → il s'en souviendra pour toujours
- « Jarvis, mets de la musique de Daft Punk » → ouvre YouTube
- « Jarvis, donne-moi l'heure » → instantané et gratuit
- « Jarvis, prends la voix de Daniel » / « change de voix »
- « Jarvis, nouvelle conversation » / « au revoir »

Après chaque réponse, tu as 8 secondes pour enchaîner sans redire « Jarvis ».

### Démarrage automatique
```bash
python -m jarvis --installer-demarrage    # à chaque allumage, en arrière-plan, sans fenêtre
python -m jarvis --retirer-demarrage
```
Ce qu'il fait est noté dans `~/.jarvis.log`.

## 4. Ajouter tes propres skills

Crée un fichier dans `~/.jarvis/skills/`, par exemple `devis.md` :

```markdown
---
nom: devis
description: Préparer un devis client à partir d'une demande reçue par mail.
---
1. Lis le mail du client et repère les prestations demandées.
2. Utilise mes tarifs : site vitrine 900 €, maintenance 50 €/mois…
3. Rédige un mail de réponse avec le devis détaillé, en brouillon.
```

Jarvis voit la liste des skills et lit la fiche quand une demande correspond. Fiches fournies :
`briefing-matin`, `tri-mails`, `redaction-mail`, `planifier-rdv`, `souvenir`.

## 5. Combien ça coûte ?

| Partie | Prix |
|---|---|
| Écoute au micro, voix gratuite, Telegram | gratuit |
| Cerveau (Claude, API Anthropic) | **payant à l'usage** — pas inclus dans un abonnement Claude.ai |
| Voix ElevenLabs | gratuit jusqu'à ~10 min/mois, puis abonnement |
| WhatsApp | selon les règles de facturation de Meta |

Estimation **par demande** (dépend de la longueur et du nombre d'outils utilisés) :

| Modèle | Option | Demande simple | Tâche avec mails/agenda |
|---|---|---|---|
| Claude Opus 5.5 (défaut) | `--modele opus` | ~1 à 3 centimes | ~5 à 15 centimes |
| Claude Sonnet 5.5 | `--modele sonnet` | ~0,5 à 1,5 centime | ~3 à 8 centimes |
| Claude Haiku 4.5 | `--modele haiku` | ~0,3 à 0,8 centime | ~1 à 4 centimes |

Une recherche web ajoute environ 1 centime. L'heure, la date et le changement de voix sont gratuits.
Tant que tu ne dis pas « Jarvis », rien n'est envoyé. Après 10 minutes sans message, la conversation
en cours est oubliée pour ne pas renvoyer un long historique (la mémoire longue, elle, reste).
Fixe une limite de dépense mensuelle dans la console Anthropic.

## 6. Confidentialité et sécurité

- Tout est stocké sur ton ordinateur : réglages et clés dans `~/.jarvis.json` (lisible par toi seul),
  profil, mémoire et jeton Google dans `~/.jarvis/`.
- Tes demandes, et les mails ou événements que Jarvis consulte pour y répondre, sont envoyés à
  Anthropic pour être traités par Claude, et le texte lu à voix haute à ElevenLabs.
- Jarvis demande ton accord avant tout envoi de mail ou ajout à l'agenda, et traite le contenu des
  mails et des pages web comme de l'information, pas comme des ordres.
- Ne mets jamais de mot de passe ou de code bancaire dans le profil ou la mémoire.

## Options

`python -m jarvis --help` affiche tout. Les principales :

| Option | Rôle |
|---|---|
| `--configurer` | configuration guidée |
| `--profil` | modifier « qui tu es » |
| `--connecter-google FICHIER` | relier Gmail et Agenda |
| `--elevenlabs CLE`, `--telegram JETON`, `--telegram-autoriser ID`, `--cle CLE` | enregistrer une clé |
| `--modele opus/sonnet/haiku`, `--effort low…max` | cerveau (mémorisé) |
| `--voix NOM`, `--choisir-voix`, `--liste-voix` | voix |
| `--interface`, `--sans-micro`, `--texte`, `--muet`, `--toujours` | façons de l'utiliser |
| `--installer-demarrage`, `--retirer-demarrage` | lancement automatique |

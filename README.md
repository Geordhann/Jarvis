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
| Musique | lance un morceau (fichiers locaux ou YouTube), pause, suivant, volume | `jarvis/tools/media.py` |
| Messages | lit et envoie tes messages Telegram perso, annonce les nouveaux mails et messages | `jarvis/telegram_perso.py`, `jarvis/announcer.py` |
| Répliques | phrases prêtes à dire pour des questions précises, instantanées et gratuites | `jarvis/repliques.json` |

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

```powershell
python -m jarvis --cle "sk-ant-..."    # enregistre la clé et la teste aussitôt
python -m jarvis --tester-cle          # diagnostic : clé refusée, plus de crédit, réseau bloqué…
```

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

### Voix de Jarvis dans Voicemod (effet droïde, robot…)
Voicemod transforme un micro. On fait donc « parler » Jarvis dans un micro virtuel :

```
Jarvis ──► CABLE Input ══ VB-Cable ══► CABLE Output ──► Voicemod (effet) ──► tes haut-parleurs
```

1. Installe **VB-Cable** (gratuit) : <https://vb-audio.com/Cable/> → décompresse → clic droit sur
   `VBCABLE_Setup_x64.exe` → *Exécuter en tant qu'administrateur* → redémarre le PC.
2. `python -m jarvis --liste-audio` pour voir les noms exacts, puis :
   ```powershell
   python -m jarvis --sortie-audio "CABLE Input"
   python -m jarvis --micro "NOM DE TON VRAI MICRO"
   ```
   (le micro doit être ton **vrai** micro, pas « Voicemod Virtual Audio Device », sinon Jarvis s'entendrait lui-même).
3. Dans **Voicemod** → *Paramètres* : **Micro** = `CABLE Output (VB-Audio Virtual Cable)`,
   **Sortie** = tes haut-parleurs ou ton casque, et active **Hear myself / M'entendre**.
4. Choisis un effet (Robot, Droid, Cyborg…) : Jarvis parle maintenant avec.

Pour revenir à la normale : `python -m jarvis --sortie-audio defaut`.
Tant que Voicemod écoute le câble, ta propre voix ne passe plus dans Voicemod (pour Discord, remets ton vrai micro).
Pour l'**interface web**, fais pareil côté Windows : *Paramètres → Son → Mélangeur de volume* → sortie de
Chrome/Edge = `CABLE Input`.

### Gmail et Google Agenda
Une seule fois, environ 10 minutes :
1. Va sur <https://console.cloud.google.com/>, crée un projet (ex. « Jarvis »).
2. *API et services* → *Bibliothèque* : active ces 6 API (cherche-les une par une, bouton *Activer*) :
   **Gmail API**, **Google Calendar API**, **Google Drive API**, **Google Tasks API**,
   **People API** (contacts) et **YouTube Data API v3**.
3. *Écran de consentement OAuth* : type **Externe**, ajoute ton adresse Gmail dans **Utilisateurs test**.
4. *Identifiants* → *Créer des identifiants* → **ID client OAuth** → type **Application de bureau**
   → télécharge le fichier JSON.
5. Lance :
   ```bash
   python -m jarvis --connecter-google chemin/vers/le-fichier.json
   ```
   Ton navigateur s'ouvre : connecte-toi et accepte (Google prévient que l'appli n'est pas vérifiée :
   c'est normal, c'est la tienne → *Continuer*).

Jarvis peut alors utiliser toute ta suite Google :
- **Gmail** : lire, chercher, rédiger, envoyer ;
- **Agenda** : voir et ajouter des rendez-vous ;
- **Drive / Docs / Sheets / Slides** : chercher un fichier, le lire, le résumer, créer un document ;
- **Tâches** : ta liste de choses à faire (« Jarvis, ajoute acheter du pain à ma liste ») ;
- **Contacts** : retrouver l'adresse ou le numéro de quelqu'un ;
- **YouTube** : tes playlists et abonnements (« Jarvis, mets ma playlist sport »).

Si Jarvis te dit qu'il manque des autorisations (après une mise à jour), relance simplement
`python -m jarvis --connecter-google`.
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

### Musique
Rien à configurer : « Jarvis, mets de la musique de Daft Punk » cherche d'abord dans ton dossier
Musique (`--dossier-musique CHEMIN` pour en choisir un autre), sinon lance directement la vidéo
YouTube. Ensuite : « pause », « reprends », « chanson suivante », « monte le son », « coupe le son »
(ces commandes fonctionnent avec n'importe quel lecteur : YouTube, Spotify, VLC…).
« Ouvre Spotify » lance l'application.

### Tes messages Telegram personnels
Le bot Telegram ne voit que les messages qu'on **lui** envoie. Pour que Jarvis lise **tes** messages :
1. <https://my.telegram.org> → *API development tools* → crée une application, note `api_id` et `api_hash`.
2. `python -m jarvis --connecter-telegram-perso` → numéro de téléphone puis code reçu dans Telegram.

« Jarvis, j'ai des messages ? » lit tes messages non lus ; « réponds à Julie que j'arrive » prépare
la réponse et attend ton « oui ». Utilise ce lien pour ton propre compte uniquement.

**WhatsApp perso et SMS** : Jarvis ne peut pas les lire. WhatsApp n'offre aucun accès officiel aux
conversations personnelles (les outils non officiels peuvent faire bannir ton numéro), et les SMS
restent sur le téléphone.

### Annonces automatiques
Quand Jarvis tourne avec le micro, il annonce à voix haute les **nouveaux mails** (boîte principale,
vérifiée toutes les 2 minutes) et les **nouveaux messages Telegram privés** : « Monsieur, nouveau mail
de Marc : devis cuisine. » C'est gratuit (pas d'appel à Claude).
« Jarvis, arrête les annonces » / « active les annonces ».

### Répliques prêtes à dire
Pour certaines phrases, Jarvis a une réponse toute prête, dite instantanément et sans rien coûter :

| Tu dis | Jarvis répond |
|---|---|
| « Jarvis, tu es là ? » | « Pour vous, toujours, Monsieur. » |
| « Jarvis, qui es-tu ? » | « Je suis JARVIS. Just A Rather Very Intelligent System… » |
| « Jarvis, papa est rentré » | « Bienvenue à la maison, Monsieur. Il est 19 h 30. » |
| « Jarvis, comment ça va ? » | « Tous mes systèmes fonctionnent à pleine capacité… » |
| « Jarvis, bonne nuit » | « Bonne nuit, Monsieur. Je veille sur tout. » |

Pour en ajouter, dis simplement : « Jarvis, quand je te dis "mission accomplie", réponds "Encore un
succès, Monsieur" ». Ou modifie `~/.jarvis/repliques.json` (même format que `jarvis/repliques.json` ;
`{titre}`, `{heure}` et `{date}` sont remplacés automatiquement, et s'il y a plusieurs réponses,
Jarvis en choisit une au hasard).

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
- « Jarvis, mets de la musique de Daft Punk » → la lance ; « Jarvis, pause » / « chanson suivante »
- « Jarvis, quels mails j'ai reçus ? » / « j'ai des messages ? »
- « Jarvis, tu es là ? » → réplique prête, instantanée
- « Jarvis, donne-moi l'heure » → instantané et gratuit
- « Jarvis, prends la voix de Daniel » / « change de voix »
- « Jarvis, nouvelle conversation » / « au revoir » (éteint Jarvis)

Après chaque réponse, tu as 8 secondes pour enchaîner sans redire « Jarvis ».

### La boule à l'écran (style Iron Man)
```powershell
python -m jarvis --orbe        # active la boule (mémorisé) ; --sans-orbe pour la retirer
```
Un réacteur animé flotte sur ton écran : bleu en veille, **orange quand il t'écoute**, il tourne vite quand
il réfléchit et pulse quand il parle, avec ses phrases en sous-titre.
- **Glisser** : la déplacer (position mémorisée).
- **Clic** : Jarvis t'écoute sans que tu dises « Jarvis ».
- **Double-clic** : ouvre l'interface complète.
- **Clic droit** : *Toujours au premier plan* (décoche pour qu'elle passe derrière tes fenêtres), *Masquer*, *Quitter*.
- **Ctrl+Alt+J** n'importe où : afficher / masquer. Ou à la voix : « Jarvis, cache-toi » / « Jarvis, montre-toi ».

### Démarrage automatique
```bash
python -m jarvis --installer-demarrage    # à chaque allumage, en arrière-plan, sans fenêtre
python -m jarvis --retirer-demarrage
```
Ce qu'il fait est noté dans `~/.jarvis.log`.

## Inspirations

Projets et tutos étudiés pour construire cette version :
- [sacha9214/jarvis-vocal](https://github.com/sacha9214/jarvis-vocal) : Jarvis français local (Whisper, Piper), contrôle musique et réponses rapides sans IA
- [bertrandmbanwi/Jarvis](https://github.com/bertrandmbanwi/Jarvis) : 100+ outils, interface en particules, mémoire
- [AnubhavChaturvedi-GitHub/jarvis-ai-assistant](https://github.com/AnubhavChaturvedi-GitHub/jarvis-ai-assistant) : automatisation WhatsApp, recherche web
- [projectswithdigambar/jarvis](https://github.com/projectswithdigambar/jarvis) : interface web, YouTube et Spotify
- [codewithdars/jarvis-voice-assistant](https://github.com/codewithdars/jarvis-voice-assistant) : musique via yt-dlp
- [EZHOWWW/tg-skill](https://github.com/EZHOWWW/tg-skill) : Telegram perso (Telethon) pour agents IA
- Tutos : [Le Geek Heureux — Crée ton propre Jarvis en Python](https://legeekheureux.fr/%F0%9F%A4%96-cree-ton-propre-jarvis-en-python-un-assistant-vocal-pour-ton-pc/),
  [« J'ai codé mon propre Jarvis » (YouTube)](https://www.youtube.com/watch?v=s7qmuKYh2fs)

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
| Écoute au micro, voix gratuite, Telegram, musique, annonces, répliques prêtes | gratuit |
| Cerveau (Claude, API Anthropic) | **payant à l'usage** — pas inclus dans un abonnement Claude.ai |
| Voix ElevenLabs | gratuit jusqu'à ~10 min/mois, puis abonnement |
| WhatsApp | selon les règles de facturation de Meta |

Estimation **par demande** (dépend de la longueur et du nombre d'outils utilisés) :

| Modèle | Option | Demande simple | Tâche avec mails/agenda |
|---|---|---|---|
| Claude Opus 5.5 (défaut) | `--modele opus` | ~1 à 3 centimes | ~5 à 15 centimes |
| Claude Sonnet 5.5 | `--modele sonnet` | ~0,5 à 1,5 centime | ~3 à 8 centimes |
| Claude Haiku 4.5 | `--modele haiku` | ~0,3 à 0,8 centime | ~1 à 4 centimes |

Une recherche web ajoute environ 1 centime. L'heure, la date, la voix, les commandes musique (pause, suivant, volume) et les répliques prêtes sont gratuites.
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
| `--connecter-telegram-perso` | relier ton compte Telegram (lire et envoyer tes messages) |
| `--dossier-musique DOSSIER` | dossier de ta musique locale |
| `--elevenlabs CLE`, `--telegram JETON`, `--telegram-autoriser ID`, `--cle CLE` | enregistrer une clé |
| `--tester-cle` | vérifier que la clé Claude fonctionne |
| `--modele opus/sonnet/haiku`, `--effort low…max` | cerveau (mémorisé) |
| `--voix NOM`, `--choisir-voix`, `--liste-voix` | voix |
| `--liste-audio`, `--sortie-audio NOM`, `--micro NOM` | choisir haut-parleur et micro (Voicemod) |
| `--orbe`, `--sans-orbe` | boule animée sur l'écran (mémorisé) |
| `--interface`, `--sans-micro`, `--texte`, `--muet`, `--toujours` | façons de l'utiliser |
| `--installer-demarrage`, `--retirer-demarrage` | lancement automatique |

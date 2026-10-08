# J.A.R.V.I.S. — ton assistant personnel

Un agent à la Iron Man, propulsé par **Claude**. Tu lui parles (à voix haute ou dans son interface)
et il **agit** : il lit et rédige tes mails, gère ton agenda, envoie des SMS, contrôle tes applications,
cherche sur le web, ouvre des pages, se souvient de toi, et te répond avec une voix réaliste.

```
            ┌──────────── toi ─────────────┐
         micro « Jarvis… »    interface / boule
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
| Voix | ElevenLabs (réaliste) ou voix gratuite | `jarvis/tts.py` |
| Interface | tableau de bord avec réacteur animé par la voix, micro, mains libres | `jarvis/interface/` |
| Musique | lance un morceau (fichiers locaux ou YouTube), pause, suivant, volume | `jarvis/tools/media.py` |
| SMS | envoie des SMS depuis ton téléphone Android, après ta confirmation | `jarvis/tools/sms.py` |
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
Google, les SMS, la musique et le démarrage automatique. Tu peux sauter une étape
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
Jarvis passe automatiquement sur la voix gratuite.

```bash
python -m jarvis --elevenlabs TA_CLE
python -m jarvis --choisir-voix      # écouter et choisir (Daniel = le plus « Jarvis »)
```
Tu peux aussi utiliser une de tes voix ElevenLabs perso : `python -m jarvis --voix ID_DE_LA_VOIX`.

### Effet droïde / robot sur la voix (intégré, sans Voicemod)
```powershell
python -m jarvis --essayer-effets     # écoute chaque effet et garde ton préféré
python -m jarvis --effet tactique     # ou directement : aucun, ia, droide, tactique, robot
```
Ou à la voix : « Jarvis, présente-moi tes intonations » (il les fait toutes entendre), puis
« Jarvis, mode droïde tactique », « intonation robot », « effet IA », « mode droïde », « voix normale ».

| Effet | Rendu |
|---|---|
| `ia` | légère touche synthétique, comme le Jarvis des films |
| `droide` | métallique et un peu nasillard |
| `tactique` | droïde tactique : plus grave, froid et métallique |
| `robot` | très métallique, façon vieux synthétiseur |
| `perso` | ta propre chaîne façon Voicemod : PowerPitch → Robotifier → Hauteur |

**Recréer une voix Voicemod sans Voicemod** : l'effet `perso` reproduit la chaîne
*PowerPitch → Robotifier → Hauteur*, avec les **mêmes réglages que les boutons Voicemod** (0 à 100) :
```powershell
python -m jarvis --effet perso
python -m jarvis --effet-perso 73,100,13   # PowerPitch, mix du Robotifier, Hauteur (défaut : « Tactical Droid »)
```
Ou à la voix : « Jarvis, mode perso » / « mode voicemod ». Plus le dernier chiffre est bas, plus la voix est grave.
L'effet a été calé sur des enregistrements : bourdonnement robotique fixe à 120 Hz, voix claire et
normalisée en volume. À l'oreille :
- « Jarvis, voix plus claire » / « voix moins étouffée » / « voix plus sombre » (ou `--effet-perso-clarte 600 à 8000`, défaut 3000) ;
- « Jarvis, parle plus fort » / « parle moins fort » (ou `--volume-voix 150`, 100 = normal, max 300).


### Voix de Jarvis dans Voicemod (facultatif)
Seulement si tu veux un effet précis de Voicemod : l'effet intégré ci-dessus suffit dans la plupart des cas.
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

La connexion ouvre **deux pages** l'une après l'autre : la suite Google, puis YouTube (Google interdit de
les autoriser ensemble). Coche toutes les cases à chaque fois.
Si Jarvis te dit qu'il manque des autorisations (après une mise à jour), relance simplement
`python -m jarvis --connecter-google`.
**Il annonce toujours un envoi ou un rendez-vous et attend ton « oui » avant de le faire.**
Il ne peut pas supprimer définitivement de mail.

### Musique
Rien à configurer : « Jarvis, mets de la musique de Daft Punk » cherche d'abord dans ton dossier
Musique (`--dossier-musique CHEMIN` pour en choisir un autre), sinon lance directement la vidéo
YouTube. Ensuite : « pause », « reprends », « chanson suivante », « monte le son », « coupe le son »
(ces commandes fonctionnent avec n'importe quel lecteur : YouTube, Spotify, VLC…).
« Ouvre Spotify » lance l'application.

### Annonces automatiques
Quand Jarvis tourne avec le micro, il annonce à voix haute les **nouveaux mails** (boîte principale,
vérifiée toutes les 2 minutes) : « Monsieur, nouveau mail
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

### Installer Jarvis comme un vrai logiciel (sans PowerShell ensuite)
```powershell
python -m jarvis --installer
```
Crée l'icône **Jarvis** (le réacteur) sur le **Bureau** et dans le **menu Démarrer**, active la boule et
le **lancement automatique au démarrage du PC**. Ensuite, plus besoin de PowerShell : double-clic sur
l'icône, ou rien du tout (il démarre avec Windows). Jarvis tourne en arrière-plan sans fenêtre noire ;
s'il tourne déjà, l'icône fait simplement réapparaître la boule. Pour l'arrêter : clic droit sur la
boule → *Quitter*, ou « Jarvis, au revoir ». Journal en cas de souci : `~/.jarvis.log`.

### Les outils du quotidien (rien à configurer)
| Tu dis | Jarvis |
|---|---|
| « Jarvis, note dans mes courses : pain et lait » | carnet de notes dans le dossier `Jarvis Notes` (fichiers lisibles par toi) |
| « Jarvis, lis ma note courses » / « quelles notes j'ai ? » | lit ou liste tes notes |
| « Jarvis, rappelle-moi demain à 9 h d'appeler le garage » | rappel gardé même si le PC redémarre |
| « Jarvis, quel temps fera-t-il à Lyon demain ? » | météo précise sur 7 jours (Open-Meteo, gratuit) |
| « Jarvis, résume ce que j'ai copié » / « traduis ça » | lit ton presse-papiers |
| « Jarvis, ouvre mes téléchargements » | ouvre le dossier |
| « Jarvis, comment va le PC ? » | processeur, mémoire, disque, batterie |
| « Jarvis, verrouille le PC » / « éteins le PC » | éteindre demande ta confirmation, et reste annulable une minute |
| « Jarvis, regarde mon écran, c'est quoi cette erreur ? » | capture l'écran et l'analyse (seulement quand tu le demandes) |

**Google Keep** n'a pas d'accès officiel pour les comptes Gmail personnels : le carnet de notes de Jarvis
le remplace. Pour une note dans Google Docs, demande « crée un document Google avec… ».

### Contrôler tes applications
| Tu dis | Jarvis |
|---|---|
| « Jarvis, ouvre Discord / Spotify / Word / Steam » | cherche l'appli dans le menu Démarrer et la lance |
| « Jarvis, quelles fenêtres sont ouvertes ? » | liste les fenêtres |
| « Jarvis, affiche Discord » / « réduis Chrome » / « agrandis Word » | passe d'une fenêtre à l'autre |
| « Jarvis, ferme Discord » | ferme l'appli **après ta confirmation** |
| « Jarvis, enregistre » / « nouvel onglet » / « montre le bureau » | raccourcis clavier (Ctrl+S, Ctrl+T, Win+D…) |
| « Jarvis, écris "j'arrive dans 5 minutes" » | tape le texte là où se trouve le curseur |

### Régler la voix
22 voix gratuites (françaises, québécoises, belges, suisses, et des voix « multilingues » qui parlent
français avec un léger accent : **Bryan**, à l'accent anglais, rappelle le Jarvis du film), plus les voix ElevenLabs.
```powershell
python -m jarvis --choisir-voix        # écouter et choisir
python -m jarvis --vitesse-voix -10    # de -50 (lent) à 50 (rapide)
python -m jarvis --hauteur-voix -20    # de -50 (grave) à 50 (aigu)
python -m jarvis --essayer-effets      # + un effet : ia, droide, tactique, robot
```
À la voix : « Jarvis, présente-moi tes voix » (chaque voix se présente), puis « Jarvis, prends la voix
de Bryan » ; « Jarvis, parle plus lentement », « Jarvis, voix plus grave ».

### SMS (téléphone Android)
Jarvis envoie les SMS **depuis ton propre numéro**, gratuitement (compris dans ton forfait), grâce à
l'appli open source [SMS Gateway for Android](https://sms-gate.app).
1. Sur ton téléphone : installe **SMS Gateway for Android** (Google Play), ouvre-la, autorise l'envoi de SMS,
   active **Cloud server** puis appuie sur **Démarrer** (Online).
2. L'écran d'accueil de l'appli affiche un **Username** et un **Password**.
3. Sur le PC : `python -m jarvis --configurer-sms` → colle-les, puis accepte le SMS de test.

« Jarvis, envoie un SMS à Julie pour lui dire que j'arrive » : il trouve le numéro (contacts Google,
profil, mémoire), te lit le message et attend ton « oui ». Le téléphone doit être allumé et connecté à
Internet. Désactive l'optimisation de batterie pour l'appli pour qu'elle reste active.
Jarvis ne lit pas tes SMS reçus.

### WhatsApp
Avec **ton** compte, via l'appli WhatsApp du PC (ou WhatsApp Web) : installe **WhatsApp** depuis le
Microsoft Store et connecte-la une fois en scannant le QR code avec ton téléphone
(WhatsApp → ⋮ → Appareils connectés). Ensuite :
- « Jarvis, j'ai des messages WhatsApp ? » : il ouvre WhatsApp et te résume les discussions.
- « Jarvis, envoie un WhatsApp à Paul pour lui dire que j'arrive » : il trouve le numéro dans tes
  contacts Google, écrit le message dans la conversation, te le lit et ne l'envoie qu'après ton « oui ».

Pas de robot non officiel (ils peuvent faire bannir ton numéro) : Jarvis utilise l'appli comme toi.

### Instagram, Snapchat et autres réseaux
Ces réseaux n'offrent aucun accès officiel aux comptes personnels (les outils non officiels peuvent
faire bannir ton compte). Jarvis passe donc par ton écran : « ouvre mes messages Instagram »,
« regarde mon écran et résume mes messages », « réponds-lui que j'arrive » (il tape la réponse,
c'est toi qui l'envoies).

## 3. Utilisation

### Couper Jarvis
Pendant qu'il parle, dis **« stop »**, « tais-toi », « chut » ou « ça suffit » (ou clique sur la boule) :
il se tait tout de suite et t'écoute, sans avoir à redire « Jarvis ».
Pour désactiver : `python -m jarvis --interruption non`.

### Effets Iron Man
- **Bruitages** : réacteur au démarrage, bip quand tu dis juste « Jarvis », bip quand il a compris,
  coupure quand tu dis « stop ». « Jarvis, coupe les bruitages » / « active les bruitages ».
- **La boule change de couleur** : rouge pour une alerte (nouveau mail, rappel, problème), vert quand
  une tâche est finie, doré pendant sa présentation. Elle **bat au rythme du son** du PC (musique,
  vidéo, sa propre voix).
- **Personnalités** : « Jarvis, mode sarcastique » (le JARVIS des films, en plus mordant), « mode
  sérieux », « mode motivant », « mode drôle », « mode majordome », « mode classique ».
- **« Jarvis, présente-toi »** : sa présentation façon film, avec musique d'entrée si tu l'as.

### Ultron et Big Boss (Metal Gear Solid)
Trois personnages, chacun avec sa voix, son caractère, sa couleur, ses bruitages, **son nom** et
**sa façon de t'appeler** :

| Icône du Bureau | Tu l'appelles | Il t'appelle | Style |
|---|---|---|---|
| **Jarvis** (bleu) | « Jarvis, … » | Monsieur | majordome IA d'Iron Man |
| **Ultron** (rouge) | « Ultron, … » | Seigneur | IA froide et menaçante, voix grave métallique |
| **Big Boss** (vert) | « Boss, … » | Snake | soldat légendaire au codec, voix radio |

- **Au lancement** : double-clique sur l'icône du personnage voulu (`python -m jarvis --installer`
  crée les 3 icônes). Si Jarvis tourne déjà, il se transforme directement.
- **À la voix** : « Jarvis, mode Ultron », « Ultron, mode Big Boss », « Boss, redeviens Jarvis ».
- Seul le nom du personnage actif le réveille. Au retour à Jarvis, ta voix et ton caractère d'origine
  reviennent. Essaie « présente-toi » avec chacun.

### Jeux
- **« Jarvis, lance Rocket League »** : lance directement un jeu Steam installé, même avec un nom
  approximatif ou un sigle (« lance RL », « lance GTA 5 »).
- **« Jarvis, mode gaming »** (ou « mode combat ») : coupe les notifications Windows, passe le PC en
  performances maximales et ferme les applis que tu as choisies une fois pour toutes :
  `python -m jarvis --applis-gaming "onedrive,chrome"`. « Jarvis, fin du mode gaming » remet tout.
- **Coach** : « Jarvis, regarde mon écran, comment je bats ce boss ? » : il regarde le jeu et te
  donne 2-3 conseils courts.

### Spotify
Connexion une fois (5 minutes) :
1. Va sur <https://developer.spotify.com/dashboard>, connecte-toi avec ton compte Spotify, puis
   **Create app**.
2. Nom : `Jarvis`, description : `Assistant perso`. **Redirect URI** : `http://127.0.0.1:8766/callback`
   (clique **Add**). Coche **Web API**, accepte les conditions, **Save**.
3. Dans l'appli créée → **Settings** : copie le **Client ID**.
4. `python -m jarvis --connecter-spotify TON_CLIENT_ID` : autorise Jarvis dans la page qui s'ouvre.

Ensuite : « Jarvis, **joue Daft Punk** », « mets **Highway to Hell** sur Spotify », « mets **ma
playlist** sport », « mets **mes titres likés** », « morceau suivant », « pause », « c'est quoi ce
titre ? », « **j'aime** ce titre », « mets le volume de Spotify à 40 ».
Avec **Spotify Premium**, Jarvis lance directement la musique ; avec un compte gratuit, Spotify
n'autorise pas le contrôle à distance : il ouvre le morceau et tu appuies sur lecture.

### Traducteur
« Jarvis, dis à mon pote en anglais qu'on commence dans 5 minutes » : il traduit et le dit à voix haute
avec une voix anglaise (aussi espagnol, allemand, italien, portugais, arabe, japonais, chinois…).

### Jarvis sur Discord
« Jarvis, dis sur Discord que j'arrive dans 2 minutes » : tes amis l'entendent dans le vocal.
Installation une seule fois :
1. Installe **VB-Cable** (gratuit) : <https://vb-audio.com/Cable/>, puis redémarre le PC.
2. Pour que tes amis t'entendent toi aussi : Windows → Paramètres → Son → **Plus de paramètres de son**
   → onglet **Enregistrement** → ton micro → **Propriétés** → onglet **Écouter** → coche
   **Écouter ce périphérique** → « Lecture sur ce périphérique » : **CABLE Input** → OK.
3. Dans Discord → Paramètres → Voix et vidéo → **Périphérique d'entrée : CABLE Output**.

### Phrases longues
Prends ton temps : dès que tu parles plus de 4 secondes, une petite pause pour réfléchir ne coupe
plus ta phrase. Et si tu t'arrêtes sur « et », « pour », « parce que »…, Jarvis attend la suite.

```bash
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
- **Clic droit → Position** : *Derrière les fenêtres* (par défaut, posée sur le bureau), *Comme une fenêtre
  normale* ou *Toujours au premier plan*. Aussi : *Masquer*, *Quitter*.
- **Ctrl+Alt+J** n'importe où : afficher / masquer. Ou à la voix : « Jarvis, cache-toi » / « Jarvis, montre-toi ».

### Musique d'entrée (Thunderstruck), en option
C'est **toi qui décides** : dis « Jarvis, mets ta musique d'entrée » (ou « mode Iron Man »), ou clic droit
sur la boule → *Jouer la musique d'entrée*. Le morceau démarre fort, puis baisse progressivement jusqu'à un
fond sonore, et s'efface quand Jarvis parle. « Jarvis, coupe la musique » pour l'arrêter.
Le morceau n'est pas fourni (droits d'auteur) : mets ton MP3 de Thunderstruck dans ton dossier **Musique**.
```powershell
python -m jarvis --musique-au-lancement oui   # la jouer aussi à chaque lancement (désactivé par défaut)
python -m jarvis --musique-demarrage "C:\chemin\vers\morceau.mp3"   # un autre morceau
python -m jarvis --volume-fond 10             # volume une fois en fond (défaut 15 %)
```

### Micro : mieux te capter
```powershell
python -m jarvis --tester-micro          # affiche ce que Jarvis comprend, phrase par phrase
python -m jarvis --sensibilite-micro 8   # de 1 (voix forte seulement) à 10 (capte un murmure), défaut 7
```
À la voix : « Jarvis, sois plus sensible » / « sois moins sensible ». Trop sensible, il risque de se
déclencher sur les bruits de la pièce ; pas assez, il rate le début des phrases.
Pense aussi au volume du micro dans Windows : *Paramètres → Son → ton micro → Volume d'entrée* (vers 80-100).

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
- [projectswithdigambar/jarvis](https://github.com/projectswithdigambar/jarvis) : interface web, YouTube et Spotify
- [codewithdars/jarvis-voice-assistant](https://github.com/codewithdars/jarvis-voice-assistant) : musique via yt-dlp
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
`briefing-matin`, `tri-mails`, `redaction-mail`, `envoyer-sms`, `whatsapp`, `reseaux-sociaux`, `planifier-rdv`, `souvenir`.

## 5. Combien ça coûte ?

| Partie | Prix |
|---|---|
| Cerveau (Claude, API Anthropic) | **payant à l'usage** — pas inclus dans un abonnement Claude.ai |
| Voix ElevenLabs | gratuit jusqu'à ~10 min/mois, puis abonnement |

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
| `--configurer-sms` | relier ton téléphone Android pour envoyer des SMS |
| `--dossier-musique DOSSIER` | dossier de ta musique locale |
| `--tester-cle` | vérifier que la clé Claude fonctionne |
| `--modele opus/sonnet/haiku`, `--effort low…max` | cerveau (mémorisé) |
| `--voix NOM`, `--choisir-voix`, `--liste-voix` | voix |
| `--liste-audio`, `--sortie-audio NOM`, `--micro NOM` | choisir haut-parleur et micro (Voicemod) |
| `--orbe`, `--sans-orbe` | boule animée sur l'écran (mémorisé) |
| `--musique-au-lancement oui/non`, `--musique-demarrage CHEMIN`, `--volume-fond POURCENT` | musique d'entrée (Thunderstruck…) |
| `--tester-micro`, `--sensibilite-micro 1-10` | régler l'écoute du micro |
| `--interface`, `--sans-micro`, `--texte`, `--muet`, `--toujours` | façons de l'utiliser |
| `--installer` | tout installer : icône Bureau + menu Démarrer, boule, lancement au démarrage |
| `--raccourcis` | recréer seulement l'icône |
| `--installer-demarrage`, `--retirer-demarrage` | lancement automatique |

# JARVIS — ton assistant vocal personnel

Un assistant à la Iron Man : tu lui **parles**, il te **répond à voix haute**.
Il utilise Claude (Anthropic) comme cerveau, peut chercher sur le web (météo, actualités…)
et se souvient de la conversation.

```
micro ──► reconnaissance vocale ──► Claude ──► synthèse vocale ──► haut-parleurs
```

## Installation

Il faut Python 3.10 ou plus récent.

```bash
git clone https://github.com/geordhann/jarvis.git
cd jarvis
python -m venv .venv
# Windows : .venv\Scripts\activate     macOS / Linux : source .venv/bin/activate
pip install -r requirements.txt
```

Si l'installation de **PyAudio** échoue :
- Windows : `pip install pipwin && pipwin install pyaudio`
- macOS : `brew install portaudio` puis `pip install pyaudio`
- Linux (Debian/Ubuntu) : `sudo apt install portaudio19-dev python3-pyaudio`

### Clé API (une seule fois)

Crée une clé sur <https://console.anthropic.com/> (rubrique *API Keys*), puis :

```bash
python -m jarvis --cle sk-ant-...
```

La clé est enregistrée dans `~/.jarvis.json` (lisible par toi seul) : plus besoin de la redonner.

### Lancement automatique au démarrage

```bash
python -m jarvis --installer-demarrage
```

Jarvis démarre alors **tout seul, en arrière-plan et sans fenêtre** à chaque allumage de l'ordinateur
(après l'ouverture de ta session). Il t'accueille à voix haute puis attend « Jarvis ».

- Windows : un petit fichier `Jarvis.vbs` dans le dossier *Démarrage*.
- macOS : un `LaunchAgent` ; au premier lancement, autorise l'accès au micro.
- Linux : un fichier `~/.config/autostart/jarvis.desktop`.

Pour l'enlever : `python -m jarvis --retirer-demarrage`.
Ce qu'il entend et répond est noté dans `~/.jarvis.log` (pratique s'il ne répond pas).

## Combien ça coûte ?

| Partie | Prix |
|---|---|
| Reconnaissance vocale (Google) | gratuit |
| Voix de Jarvis (edge-tts) | gratuit |
| Cerveau (Claude, via l'API Anthropic) | **payant, à l'usage** |

L'API Claude se paie à part (un abonnement Claude.ai ne l'inclut pas) : tu ajoutes du crédit sur
<https://console.anthropic.com/> (rubrique *Billing*), par exemple 5 $, et chaque question en consomme un peu.

Ordre de grandeur **par question** (estimation, ça dépend de la longueur) :

| Modèle | Option | Coût approximatif |
|---|---|---|
| Claude Opus 5.5 (défaut, le plus intelligent) | `--modele opus` | ~1 à 3 centimes |
| Claude Sonnet 5.5 | `--modele sonnet` | ~0,5 à 1,5 centime |
| Claude Haiku 4.5 (le plus rapide) | `--modele haiku` | ~0,3 à 0,8 centime |

Une recherche web ajoute environ 1 centime. L'heure, la date et le changement de voix sont **gratuits**
(Jarvis répond sans appeler Claude). Tant que tu ne dis pas « Jarvis », **rien n'est envoyé ni payé**.
Après 10 minutes sans question, il oublie la conversation pour éviter de renvoyer un long historique.
Le choix du modèle est mémorisé. Tu peux fixer une limite de dépense mensuelle dans la console Anthropic.

## Lancer Jarvis

```bash
python -m jarvis                 # il attend que tu dises « Jarvis, … »
python -m jarvis --toujours      # il répond à tout ce que tu dis, sans « Jarvis »
python -m jarvis --texte         # tu écris au clavier, il répond à voix haute
python -m jarvis --nom Geordhann --titre Patron
```

### Lui parler

Jarvis reste **silencieux en veille** et ne répond que quand tu commences par « Jarvis » :

- « Jarvis, donne-moi l'heure » → réponse immédiate
- « Jarvis, on est quel jour ? »
- « Jarvis, quel temps fera-t-il demain à Lyon ? » → il cherche sur le web
- « Jarvis, explique-moi les trous noirs »
- « Jarvis » tout seul → « Oui, Monsieur ? » et il t'écoute

Après chaque réponse, tu as **8 secondes** pour enchaîner une autre question sans redire « Jarvis ».
Ensuite il se remet en veille.

Phrases spéciales :
- « Jarvis, **au revoir** » / « bonne nuit » → éteint Jarvis
- « Jarvis, **nouvelle conversation** » / « oublie tout » → efface la mémoire de la conversation
- « Jarvis, **change de voix** » → il te dit quelles voix il connaît
- « Jarvis, **prends la voix de Denise** » → il change de voix (le choix est mémorisé)

## Choisir sa voix

```bash
python -m jarvis --choisir-voix   # écoute chaque voix et garde celle qui te plaît
python -m jarvis --liste-voix     # affiche la liste
python -m jarvis --voix Denise    # pour une seule session
```

| Voix | Style |
|---|---|
| Henri | homme, France, posé (par défaut) |
| Rémy | homme, France, chaleureux |
| Denise | femme, France, claire |
| Éloïse | femme, France, jeune |
| Vivienne | femme, France, douce |
| Antoine, Jean, Thierry | hommes, Québec |
| Sylvie | femme, Québec |
| Gérard / Charline | homme / femme, Belgique |
| Fabrice / Ariane | homme / femme, Suisse |

Le choix est enregistré dans `~/.jarvis.json` et repris au prochain lancement.

## Options

| Option | Variable d'environnement | Rôle |
|---|---|---|
| `--nom` | `JARVIS_OWNER` | ton prénom |
| `--titre` | `JARVIS_TITLE` | comment il t'appelle (défaut : « Monsieur ») |
| `--voix` | `JARVIS_VOICE` | prénom de la voix (`Henri`, `Denise`…) ou n'importe quel identifiant edge-tts |
| `--modele` | `JARVIS_MODEL` | `opus` (défaut), `sonnet` ou `haiku` — mémorisé |
| `--cle` | `ANTHROPIC_API_KEY` | enregistrer ta clé API |
| `--installer-demarrage` / `--retirer-demarrage` | | lancement automatique au démarrage |
| `--effort` | `JARVIS_EFFORT` | réflexion : `low` (rapide, défaut) → `max` (plus réfléchi, plus lent) |
| `--toujours` | | répond à tout, sans attendre « Jarvis » |
| `--choisir-voix` | | menu pour écouter et choisir la voix |
| `--texte` | | saisie au clavier |
| `--muet` | | réponses affichées seulement |

Liste de toutes les voix : `edge-tts --list-voices`.

## Comment ça marche

| Fichier | Rôle |
|---|---|
| `jarvis/brain.py` | conversation avec Claude en streaming, personnalité de Jarvis, recherche web |
| `jarvis/ears.py` | écoute du micro + reconnaissance vocale (Google Web Speech, français) |
| `jarvis/autostart.py` | lancement automatique (Windows, macOS, Linux) |
| `jarvis/config.py` | réglages mémorisés dans `~/.jarvis.json` |
| `jarvis/voices.py` | catalogue des voix et mémorisation du choix |
| `jarvis/voice.py` | voix neuronale edge-tts, lue phrase par phrase pendant que Claude écrit ; repli hors-ligne pyttsx3 |
| `jarvis/__main__.py` | la boucle écoute → réflexion → parole |

La réponse est prononcée **phrase par phrase dès qu'elle arrive**, pour que Jarvis commence à parler sans attendre la fin.

Pour modifier sa personnalité, édite `SYSTEM_PROMPT` dans `jarvis/brain.py`.

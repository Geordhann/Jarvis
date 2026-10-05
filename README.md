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

### Clé API

Crée une clé sur <https://console.anthropic.com/> puis :

```bash
# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

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
| `jarvis/voices.py` | catalogue des voix et mémorisation du choix |
| `jarvis/voice.py` | voix neuronale edge-tts, lue phrase par phrase pendant que Claude écrit ; repli hors-ligne pyttsx3 |
| `jarvis/__main__.py` | la boucle écoute → réflexion → parole |

La réponse est prononcée **phrase par phrase dès qu'elle arrive**, pour que Jarvis commence à parler sans attendre la fin.

Pour modifier sa personnalité, édite `SYSTEM_PROMPT` dans `jarvis/brain.py`.

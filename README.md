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
python -m jarvis                 # tu parles, il répond à voix haute
python -m jarvis --eveil         # il ne réagit que si tu dis « Jarvis, … »
python -m jarvis --texte         # tu écris au clavier, il répond à voix haute
python -m jarvis --nom Geordhann --titre Patron
```

Phrases spéciales :
- « **Au revoir** » / « Bonne nuit » → éteint Jarvis
- « **Nouvelle conversation** » / « Oublie tout » → efface la mémoire de la conversation

## Options

| Option | Variable d'environnement | Rôle |
|---|---|---|
| `--nom` | `JARVIS_OWNER` | ton prénom |
| `--titre` | `JARVIS_TITLE` | comment il t'appelle (défaut : « Monsieur ») |
| `--voix` | `JARVIS_VOICE` | voix edge-tts : `fr-FR-HenriNeural` (défaut), `fr-FR-RemyMultilingualNeural`, `fr-FR-DeniseNeural`, `fr-CA-AntoineNeural`… |
| `--effort` | `JARVIS_EFFORT` | réflexion : `low` (rapide, défaut) → `max` (plus réfléchi, plus lent) |
| `--eveil` | | mode mot d'éveil « Jarvis » |
| `--texte` | | saisie au clavier |
| `--muet` | | réponses affichées seulement |

Liste de toutes les voix : `edge-tts --list-voices`.

## Comment ça marche

| Fichier | Rôle |
|---|---|
| `jarvis/brain.py` | conversation avec Claude en streaming, personnalité de Jarvis, recherche web |
| `jarvis/ears.py` | écoute du micro + reconnaissance vocale (Google Web Speech, français) |
| `jarvis/voice.py` | voix neuronale edge-tts, lue phrase par phrase pendant que Claude écrit ; repli hors-ligne pyttsx3 |
| `jarvis/__main__.py` | la boucle écoute → réflexion → parole |

La réponse est prononcée **phrase par phrase dès qu'elle arrive**, pour que Jarvis commence à parler sans attendre la fin.

Pour modifier sa personnalité, édite `SYSTEM_PROMPT` dans `jarvis/brain.py`.

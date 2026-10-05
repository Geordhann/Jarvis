"""« Apprends-lui qui tu es » : le profil que Jarvis lit à chaque conversation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import config

TEMPLATE = """# Qui je suis

<!-- Remplis ce fichier librement : Jarvis le lit au début de chaque conversation.
     Plus tu es précis, plus il t'aidera comme un vrai assistant personnel.
     Ne mets PAS de mots de passe ni de codes bancaires ici. -->

Prénom :
Comment Jarvis doit m'appeler : Monsieur
Ville :
Langue : français

## Mon travail
Métier / entreprise :
Mes missions principales :
Mes horaires habituels :
Mes outils au quotidien :

## Les personnes importantes
<!-- ex. Julie — ma compagne ; Marc — mon associé, marc@exemple.fr -->

## Comment je veux que Jarvis travaille
- Réponses courtes et directes.
- Toujours me demander confirmation avant d'envoyer un mail ou de modifier mon agenda.
- Le matin, je veux savoir : mes rendez-vous du jour et les mails importants.

## Mes projets et objectifs du moment

## Autres choses à savoir sur moi
"""


def path() -> Path:
    return config.data_dir() / "profil.md"


def ensure() -> Path:
    p = path()
    if not p.exists():
        p.write_text(TEMPLATE, encoding="utf-8")
    return p


def read() -> str:
    """Contenu du profil, sans les commentaires d'aide."""
    import re

    text = ensure().read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()


def open_in_editor() -> Path:
    p = ensure()
    if sys.platform == "win32":
        os.startfile(p)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", "-t", str(p)], check=False)
    else:
        editor = os.getenv("EDITOR")
        subprocess.run([editor, str(p)] if editor else ["xdg-open", str(p)], check=False)
    return p

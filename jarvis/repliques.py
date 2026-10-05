"""Répliques prêtes à être dites : réponses instantanées (et gratuites) à des phrases précises.

Les répliques fournies sont dans jarvis/repliques.json ; les tiennes dans
~/.jarvis/repliques.json (même format, elles passent en priorité). Variables
utilisables dans les réponses : {titre}, {heure}, {date}.
"""

from __future__ import annotations

import datetime
import difflib
import json
import random
import re
import unicodedata
from pathlib import Path

from . import config

BUILTIN = Path(__file__).resolve().parent / "repliques.json"
SIMILARITY = 0.86  # tolérance aux petites erreurs de la reconnaissance vocale


def user_file() -> Path:
    return config.data_dir() / "repliques.json"


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\bjarvis\b", " ", text)
    return " ".join(re.findall(r"[\w']+", text))


def _load(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def load_all() -> list[dict]:
    return _load(user_file()) + _load(BUILTIN)


def find(text: str) -> str | None:
    """Renvoie la réplique prête pour `text`, ou None s'il faut demander à Claude."""
    said = _plain(text)
    if not said or len(said.split()) > 8:  # une vraie question longue va à Claude
        return None
    for entry in load_all():
        for question in entry.get("questions", []):
            q = _plain(question)
            if said == q or difflib.SequenceMatcher(None, said, q).ratio() >= SIMILARITY:
                answers = entry.get("reponses") or [entry.get("reponse", "")]
                return _fill(random.choice(answers))
    return None


def _fill(answer: str) -> str:
    from .agent import french_date, french_time

    now = datetime.datetime.now()
    values = {"titre": config.get("titre", "Monsieur"), "heure": french_time(now), "date": french_date(now.date())}
    return re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), answer)


def add(questions: list[str], reponse: str) -> None:
    entries = _load(user_file())
    entries.insert(0, {"questions": questions, "reponses": [reponse]})
    user_file().write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

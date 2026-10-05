"""Réglages mémorisés de Jarvis (voix, clé API…) dans ~/.jarvis.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".jarvis.json"
LOG_PATH = Path.home() / ".jarvis.log"


def load() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get(key: str) -> str | None:
    return load().get(key)


def save(key: str, value: str) -> None:
    data = load()
    data[key] = value
    try:
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # Le fichier peut contenir la clé API : lisible par toi seul.
        os.chmod(CONFIG_PATH, 0o600)
    except OSError as exc:
        print(f"[config] impossible d'enregistrer {key} : {exc}")


def apply_api_key() -> None:
    """Rend la clé mémorisée visible pour le SDK Anthropic, sauf si une clé est déjà définie."""
    key = get("cle_api")
    if key and not os.getenv("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = key

"""Réglages mémorisés de Jarvis (voix, clés…) dans ~/.jarvis.json, données dans ~/.jarvis/."""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".jarvis.json"
LOG_PATH = Path.home() / ".jarvis.log"
# Clé éventuellement définie dans les variables de Windows, avant que Jarvis ne la remplace.
ORIGINAL_ENV_KEY = os.getenv("ANTHROPIC_API_KEY") or ""
# Profil, mémoire, skills perso et jetons Google.
DATA_DIR = Path.home() / ".jarvis"


def data_dir() -> Path:
    DATA_DIR.mkdir(mode=0o700, exist_ok=True)
    return DATA_DIR


def load() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get(key: str, default: str | None = None) -> str | None:
    """Lit un réglage : variable d'environnement JARVIS_<CLE> d'abord, puis le fichier."""
    return os.getenv(f"JARVIS_{key.upper()}") or load().get(key) or default


def save(key: str, value: str | None) -> None:
    data = load()
    if value is not None and key in ("cle_api", "elevenlabs_cle", "telegram_token", "whatsapp_token"):
        value = clean_key(value)
    if value is None:
        data.pop(key, None)
    else:
        data[key] = value
    try:
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # Le fichier contient des clés secrètes : lisible par toi seul.
        os.chmod(CONFIG_PATH, 0o600)
    except OSError as exc:
        print(f"[config] impossible d'enregistrer {key} : {exc}")


def clean_key(value: str) -> str:
    """Retire ce qu'un copier-coller ajoute souvent : espaces, guillemets, chevrons, caractères invisibles."""
    value = "".join(ch for ch in value if ch.isprintable() and not ch.isspace())
    return value.strip("\"'<>«»“”‘’")


def apply_api_key() -> None:
    """Rend la clé enregistrée avec Jarvis visible pour le SDK Anthropic.

    Elle passe avant une éventuelle variable ANTHROPIC_API_KEY de Windows, souvent oubliée
    et périmée : c'est la clé que l'utilisateur a donnée à Jarvis qui compte.
    """
    key = load().get("cle_api")
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key

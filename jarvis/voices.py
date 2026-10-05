"""Catalogue des voix françaises et sauvegarde du choix de l'utilisateur."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

# Prénom (tel qu'on le prononce) -> (identifiant edge-tts, description)
VOICES: dict[str, tuple[str, str]] = {
    "Henri": ("fr-FR-HenriNeural", "homme, France, posé — voix par défaut"),
    "Rémy": ("fr-FR-RemyMultilingualNeural", "homme, France, chaleureux"),
    "Denise": ("fr-FR-DeniseNeural", "femme, France, claire"),
    "Éloïse": ("fr-FR-EloiseNeural", "femme, France, jeune"),
    "Vivienne": ("fr-FR-VivienneMultilingualNeural", "femme, France, douce"),
    "Antoine": ("fr-CA-AntoineNeural", "homme, Québec"),
    "Jean": ("fr-CA-JeanNeural", "homme, Québec"),
    "Thierry": ("fr-CA-ThierryNeural", "homme, Québec"),
    "Sylvie": ("fr-CA-SylvieNeural", "femme, Québec"),
    "Gérard": ("fr-BE-GerardNeural", "homme, Belgique"),
    "Charline": ("fr-BE-CharlineNeural", "femme, Belgique"),
    "Fabrice": ("fr-CH-FabriceNeural", "homme, Suisse"),
    "Ariane": ("fr-CH-ArianeNeural", "femme, Suisse"),
}

DEFAULT_VOICE_NAME = "Henri"
CONFIG_PATH = Path.home() / ".jarvis.json"


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def find_voice(text: str) -> str | None:
    """Trouve un prénom de voix (ou un identifiant edge-tts) dans `text`."""
    plain = _plain(text)
    for name, (voice_id, _) in VOICES.items():
        if _plain(name) in plain.split() or voice_id.lower() in plain:
            return name
    return None


def voice_id(name_or_id: str) -> str:
    """Accepte un prénom du catalogue ou directement un identifiant edge-tts."""
    name = find_voice(name_or_id)
    return VOICES[name][0] if name else name_or_id


def describe(name: str) -> str:
    return f"{name} ({VOICES[name][1]})"


def load_saved_voice() -> str | None:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("voix")
    except (OSError, ValueError):
        return None


def save_voice(name: str) -> None:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data["voix"] = name
    try:
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"[voix] impossible d'enregistrer le choix : {exc}")

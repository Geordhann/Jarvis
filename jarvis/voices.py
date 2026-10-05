"""Catalogue des voix : ElevenLabs (réalistes, payantes au-delà de l'offre gratuite) et edge-tts (gratuites)."""

from __future__ import annotations

import re
import unicodedata

from . import config

# Voix ElevenLabs prêtes à l'emploi : elles parlent toutes français avec le modèle multilingue.
# Prénom -> (identifiant ElevenLabs, description)
ELEVEN_VOICES: dict[str, tuple[str, str]] = {
    "Daniel": ("onwK4e9ZLuTAKqWW03F9", "homme, britannique, posé — le plus « Jarvis »"),
    "George": ("JBFqnCBsd6RMkjVDRZzb", "homme, chaleureux, conteur"),
    "Brian": ("nPczCjzI2devNBz1zQrb", "homme, grave, rassurant"),
    "Adam": ("pNInz6obpgDQGcFmaJgB", "homme, grave"),
    "Antoni": ("ErXwobaYiN019PkySvjV", "homme, doux"),
    "Charlotte": ("XB0fDUnXU5powFXDhCwa", "femme, séduisante"),
    "Sarah": ("EXAVITQu4vr4xnSDxMaL", "femme, douce, professionnelle"),
    "Lily": ("pFZP5JQG7iQjIQuC4Bku", "femme, britannique, chaleureuse"),
    "Rachel": ("21m00Tcm4TlvDq8ikWAM", "femme, calme"),
}

# Voix edge-tts (Microsoft), gratuites et illimitées.
EDGE_VOICES: dict[str, tuple[str, str]] = {
    "Henri": ("fr-FR-HenriNeural", "homme, France, posé"),
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


def has_elevenlabs() -> bool:
    return bool(config.get("elevenlabs_cle"))


def catalog() -> dict[str, tuple[str, str]]:
    """Les voix utilisables : ElevenLabs seulement si une clé est configurée."""
    return {**(ELEVEN_VOICES if has_elevenlabs() else {}), **EDGE_VOICES}


def default_voice() -> str:
    return "Daniel" if has_elevenlabs() else "Henri"


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def find_voice(text: str) -> str | None:
    """Trouve un prénom de voix (ou un identifiant) dans `text`."""
    plain = _plain(text)
    words = set(re.split(r"[^\w-]+", plain))
    for name, (voice_id, _) in catalog().items():
        if _plain(name) in words or voice_id.lower() in plain:
            return name
    return None


def resolve(name_or_id: str | None) -> tuple[str, str]:
    """(fournisseur, identifiant) pour un prénom ou un identifiant de voix."""
    name = find_voice(name_or_id or "")
    if name is None and not name_or_id:
        name = default_voice()
    if name in ELEVEN_VOICES and has_elevenlabs():
        return "elevenlabs", ELEVEN_VOICES[name][0]
    if name in EDGE_VOICES:
        return "edge", EDGE_VOICES[name][0]
    # Identifiant inconnu : une voix edge-tts (« fr-FR-… ») ou une voix ElevenLabs perso.
    if name_or_id and re.fullmatch(r"[a-z]{2}-[A-Z]{2}-\w+", name_or_id):
        return "edge", name_or_id
    if name_or_id and has_elevenlabs():
        return "elevenlabs", name_or_id
    return "edge", EDGE_VOICES["Henri"][0]


def describe(name: str) -> str:
    provider = "ElevenLabs" if name in ELEVEN_VOICES else "gratuite"
    return f"{name} ({catalog()[name][1]}, {provider})"


def load_saved_voice() -> str | None:
    return config.get("voix")


def save_voice(name: str) -> None:
    config.save("voix", name)

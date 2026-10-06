"""Musique, contrôle multimédia et lancement d'applications sur l'ordinateur."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import unicodedata
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from .. import config
from . import Tool, ToolFailure, string

AUDIO_EXT = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aac", ".opus"}

# Commandes multimédia : touche du clavier (pynput) correspondante.
MEDIA_ACTIONS = {
    "pause": "media_play_pause",
    "lecture": "media_play_pause",
    "suivant": "media_next",
    "precedent": "media_previous",
    "volume_plus": "media_volume_up",
    "volume_moins": "media_volume_down",
    "muet": "media_volume_mute",
}


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _open(target: str) -> None:
    """Ouvre un fichier ou une adresse avec l'application par défaut du système."""
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def music_dir() -> Path:
    return Path(config.get("dossier_musique") or Path.home() / "Music")


def _find_local(recherche: str) -> Path | None:
    words = _plain(recherche).split()
    if not words or not music_dir().is_dir():
        return None
    best, best_score = None, 0
    for path in music_dir().rglob("*"):
        if path.suffix.lower() not in AUDIO_EXT:
            continue
        name = _plain(str(path.relative_to(music_dir())))
        score = sum(w in name for w in words)
        if score > best_score:
            best, best_score = path, score
    return best if best_score == len(words) else None


def _youtube_url(recherche: str) -> str | None:
    """Adresse de la première vidéo YouTube correspondante (lecture automatique)."""
    try:
        from yt_dlp import YoutubeDL

        class _Silent:  # yt-dlp écrit ses erreurs dans la console : on les garde pour nous
            debug = info = warning = error = staticmethod(lambda msg: None)

        options = {"quiet": True, "no_warnings": True, "logger": _Silent(), "skip_download": True,
                   "extract_flat": True, "noplaylist": True, "socket_timeout": 10}
        with YoutubeDL(options) as ydl:
            entries = ydl.extract_info(f"ytsearch1:{recherche}", download=False).get("entries") or []
        if entries:
            return entries[0].get("url") or f"https://www.youtube.com/watch?v={entries[0]['id']}"
    except Exception as exc:
        print(f"[musique] recherche YouTube impossible : {exc}")
    return None


def jouer_musique(recherche: str, source: str = "auto") -> str:
    """Lance une musique : fichier local d'abord, sinon YouTube (ou Spotify si demandé)."""
    if source in ("auto", "local"):
        local = _find_local(recherche)
        if local:
            _open(str(local))
            return f"Lecture du fichier local : {local.stem}"
        if source == "local":
            raise ToolFailure(f"aucun fichier ne correspond dans {music_dir()}")
    if source == "spotify":
        _open(f"spotify:search:{recherche}")
        return "Recherche ouverte dans Spotify (l'utilisateur choisit le morceau)."
    url = _youtube_url(recherche)
    if url:
        webbrowser.open(url)
        return f"Lecture lancée sur YouTube : {recherche}"
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(recherche)}")
    return "Lecture directe impossible : résultats YouTube ouverts dans le navigateur."


def controle_media(action: str) -> str:
    """Pause, morceau suivant, volume… via les touches multimédia du clavier."""
    key_name = MEDIA_ACTIONS.get(action)
    if key_name is None:
        raise ToolFailure(f"action inconnue, choisir parmi : {', '.join(MEDIA_ACTIONS)}")
    try:
        from pynput.keyboard import Controller, Key
    except Exception as exc:  # pas d'écran (serveur) ou bibliothèque absente
        print(f"[musique] touches multimédia indisponibles : {exc}")
        raise ToolFailure("le contrôle de la musique n'est pas disponible sur cet ordinateur") from exc
    key = getattr(Key, key_name)
    keyboard = Controller()
    # Une pression de volume change peu le son : on en envoie plusieurs.
    for _ in range(5 if action.startswith("volume") else 1):
        keyboard.press(key)
        keyboard.release(key)
    return f"Commande « {action} » envoyée."


def ouvrir_application(nom: str) -> str:
    if not re.fullmatch(r"[\w .+-]{1,60}", nom):
        raise ToolFailure("nom d'application invalide")
    if sys.platform == "win32":
        # « start » cherche l'application dans le menu Démarrer et le PATH.
        subprocess.Popen(["cmd", "/c", "start", "", nom], shell=False)
    elif sys.platform == "darwin":
        if subprocess.run(["open", "-a", nom], capture_output=True).returncode != 0:
            raise ToolFailure(f"application « {nom} » introuvable")
    else:
        exe = shutil.which(nom.lower().replace(" ", "-")) or shutil.which(nom.lower())
        if not exe:
            raise ToolFailure(f"application « {nom} » introuvable")
        subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Application « {nom} » ouverte."


def tools() -> list[Tool]:
    return [
        Tool("jouer_musique",
             "Lance une musique, un artiste, un album ou une playlist sur l'ordinateur. Cherche d'abord "
             "dans la musique locale, sinon lance directement la vidéo YouTube.",
             {"recherche": string("titre, artiste ou ambiance, ex. « Daft Punk Get Lucky », « jazz calme »"),
              "source": {"type": "string", "enum": ["auto", "local", "youtube", "spotify"],
                         "description": "auto par défaut ; spotify seulement si l'utilisateur le demande"}},
             jouer_musique, ["recherche"]),
        Tool("controle_media",
             "Contrôle la musique ou la vidéo en cours : pause, lecture, suivant, précédent, volume, muet.",
             {"action": {"type": "string", "enum": list(MEDIA_ACTIONS)}},
             controle_media, ["action"]),
    ]

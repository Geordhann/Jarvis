"""Résumer ce qui est ouvert : récupère l'onglet actif du navigateur (texte de la page ou
sous-titres d'une vidéo YouTube) pour que Claude le résume, l'explique ou le traduise."""

from __future__ import annotations

import html
import re
import sys
import time

import requests

from . import Tool, ToolFailure

MAX_CHARS = 15000


def _copy_active_url() -> str:
    """Copie l'adresse de l'onglet actif (Ctrl+L, Ctrl+C, Échap) sans perdre le presse-papiers."""
    import pyperclip
    from pynput.keyboard import Controller, Key

    previous = pyperclip.paste()
    pyperclip.copy("")
    keyboard = Controller()
    for combo in ((Key.ctrl, "l"), (Key.ctrl, "c")):
        with keyboard.pressed(combo[0]):
            keyboard.press(combo[1])
            keyboard.release(combo[1])
        time.sleep(0.15)
    keyboard.press(Key.esc)
    keyboard.release(Key.esc)
    time.sleep(0.1)
    url = pyperclip.paste().strip()
    pyperclip.copy(previous)
    return url


def _active_title() -> str:
    if sys.platform != "win32":
        return ""
    try:
        import pygetwindow

        window = pygetwindow.getActiveWindow()
        return window.title if window else ""
    except Exception:
        return ""


def youtube_id(url: str) -> str | None:
    match = re.search(r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/)|youtu\.be/)([\w-]{11})", url)
    return match.group(1) if match else None


def youtube_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    fetched = YouTubeTranscriptApi().fetch(video_id, languages=["fr", "en", "es", "de", "it"])
    return " ".join(snippet.text for snippet in fetched)


def page_text(url: str) -> str:
    response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (Jarvis)"})
    response.raise_for_status()
    text = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", response.text, flags=re.S | re.I)
    text = re.sub(r"<(br|/p|/div|/li|/h\d)[^>]*>", "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def contenu_onglet_actif() -> str:
    title = _active_title()
    try:
        url = _copy_active_url()
    except Exception as exc:
        raise ToolFailure(f"impossible de lire l'onglet actif ({exc})") from exc
    if not url.startswith(("http://", "https://")):
        raise ToolFailure("la fenêtre au premier plan n'est pas un navigateur avec une page web. "
                          "Propose regarder_ecran à la place.")
    video = youtube_id(url)
    if video:
        try:
            text = youtube_transcript(video)
            kind = "Sous-titres de la vidéo YouTube"
        except Exception:
            raise ToolFailure("cette vidéo n'a pas de sous-titres disponibles ; propose regarder_ecran.")
    else:
        try:
            text = page_text(url)
            kind = "Texte de la page"
        except requests.RequestException as exc:
            raise ToolFailure(f"page illisible ({exc}) ; propose regarder_ecran.") from exc
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + " […]"
    return f"Fenêtre : {title}\nAdresse : {url}\n{kind} :\n{text}"


def tools() -> list[Tool]:
    return [
        Tool("contenu_onglet_actif",
             "Récupère le contenu de la page ou de la vidéo YouTube ouverte au premier plan dans le "
             "navigateur (texte ou sous-titres) : pour « résume cette page », « résume cette vidéo », "
             "« de quoi parle cet article ».", {}, contenu_onglet_actif),
    ]

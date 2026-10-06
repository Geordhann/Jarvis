"""Choix des périphériques audio : où Jarvis parle (sortie) et où il écoute (micro).

Utile pour faire passer la voix de Jarvis dans Voicemod : Jarvis parle dans un câble
audio virtuel (VB-Cable), que Voicemod utilise comme micro. Voir README, section Voicemod.
"""

from __future__ import annotations

from . import config


def output_names() -> list[str]:
    import pygame
    import pygame._sdl2.audio as sdl2_audio

    pygame.mixer.init()
    try:
        return list(sdl2_audio.get_audio_device_names(False))
    finally:
        pygame.mixer.quit()


def input_names() -> list[str]:
    import speech_recognition as sr

    return sr.Microphone.list_microphone_names()


def _match(wanted: str | None, names: list[str]) -> str | None:
    if not wanted:
        return None
    wanted = wanted.lower()
    return next((n for n in names if n.lower() == wanted), None) or \
        next((n for n in names if wanted in n.lower()), None)


def output_device() -> str | None:
    """Nom exact de la sortie choisie (None = haut-parleurs par défaut)."""
    wanted = config.get("sortie_audio")
    if not wanted:
        return None
    try:
        found = _match(wanted, output_names())
    except Exception as exc:
        print(f"[audio] impossible de lister les sorties : {exc}")
        return None
    if not found:
        print(f"[audio] sortie « {wanted} » introuvable, haut-parleurs par défaut utilisés.")
    return found


def input_index() -> int | None:
    """Numéro du micro choisi (None = micro par défaut de Windows)."""
    wanted = config.get("micro")
    if not wanted:
        return None
    names = input_names()
    found = _match(wanted, names)
    if not found:
        print(f"[audio] micro « {wanted} » introuvable, micro par défaut utilisé.")
        return None
    return names.index(found)


def print_devices() -> None:
    print("Sorties audio (où Jarvis parle) :")
    for name in output_names():
        print(f"  - {name}")
    print("\nMicros (où Jarvis écoute) :")
    seen = set()
    for name in input_names():
        if name not in seen:
            seen.add(name)
            print(f"  - {name}")
    print("\nExemples : python -m jarvis --sortie-audio \"CABLE Input\"   |   python -m jarvis --micro \"Realtek\"")

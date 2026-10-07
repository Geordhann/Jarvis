"""Musique d'entrée de Jarvis (Thunderstruck par défaut) : plein volume, puis fondu vers un fond sonore.

La musique n'est pas fournie (droits d'auteur) : Jarvis cherche « thunderstruck » dans ton dossier
Musique, ou utilise le fichier indiqué avec --musique-demarrage CHEMIN (« non » pour désactiver).
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from . import config, state

AUDIO_EXT = {".mp3", ".ogg", ".wav", ".flac"}
HOLD_SECONDS = 9        # l'intro à plein volume
FADE_SECONDS = 20       # durée de la descente
DUCK_VOLUME = 0.06      # pendant que Jarvis parle

_channel = None
_stop = threading.Event()


def background_volume() -> float:
    try:
        return max(0.0, min(1.0, float(config.get("musique_volume_fond") or 15) / 100))
    except ValueError:
        return 0.15


def find_track() -> Path | None:
    chosen = config.get("musique_demarrage")
    if chosen and chosen.lower() in ("non", "aucune", "off"):
        return None
    if chosen:
        path = Path(chosen.strip().strip('"'))
        return path if path.is_file() else None
    from .tools.media import music_dir

    folders = [music_dir(), Path.home() / "Downloads", Path.home() / "OneDrive" / "Musique"]
    for folder in folders:
        if folder.is_dir():
            for path in folder.rglob("*"):
                if path.suffix.lower() in AUDIO_EXT and "thunderstruck" in path.name.lower():
                    return path
    return None


def play() -> bool:
    """Lance la musique d'entrée ; renvoie False s'il n'y a pas de fichier."""
    global _channel
    track = find_track()
    if track is None:
        if not config.get("musique_demarrage"):
            print("[musique] Thunderstruck introuvable : place le MP3 dans ton dossier Musique ou utilise "
                  "--musique-demarrage CHEMIN.")
        return False
    try:
        import pygame

        from .audio_out import MIXER_LOCK, ensure_mixer

        ensure_mixer()
        with MIXER_LOCK:
            sound = pygame.mixer.Sound(str(track))
            _channel = pygame.mixer.find_channel(True)
            _channel.set_volume(1.0)
            _channel.play(sound)
    except Exception as exc:
        print(f"[musique] lecture impossible ({exc})")
        return False
    _stop.clear()
    threading.Thread(target=_fade_loop, daemon=True, name="musique-demarrage").start()
    return True


def _mixer_lock():
    from .audio_out import MIXER_LOCK

    return MIXER_LOCK


def is_playing() -> bool:
    if _channel is None:
        return False
    with _mixer_lock():
        return _channel.get_busy()


def stop(fade_ms: int = 1500) -> bool:
    """Coupe la musique d'entrée en douceur. Renvoie True si elle jouait."""
    if not is_playing():
        return False
    _stop.set()
    with _mixer_lock():
        _channel.fadeout(fade_ms)
    return True


def _fade_loop() -> None:
    start = time.monotonic()
    background = background_volume()
    while not _stop.is_set() and is_playing():
        elapsed = time.monotonic() - start
        if elapsed < HOLD_SECONDS:
            volume = 1.0
        else:
            progress = min(1.0, (elapsed - HOLD_SECONDS) / FADE_SECONDS)
            volume = 1.0 - (1.0 - background) * progress
        current, _, _ = state.get()
        if current == state.SPEAKING:
            volume = min(volume, DUCK_VOLUME)  # Jarvis parle : la musique s'efface
        with _mixer_lock():
            _channel.set_volume(volume)
        time.sleep(0.05)

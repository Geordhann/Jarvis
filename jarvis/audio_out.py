"""Sortie son partagée (pygame) : la voix de Jarvis et la musique de démarrage jouent ensemble."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_ready = False
# À prendre autour de chaque appel pygame.mixer : la voix, les bruitages et la musique
# jouent depuis des threads différents.
MIXER_LOCK = threading.RLock()


def ensure_mixer() -> None:
    """Initialise la sortie son une seule fois, sur la sortie choisie (haut-parleurs, écran…)."""
    global _ready
    with _lock:
        if _ready:
            return
        import pygame

        from .audio_devices import output_device

        device = output_device()
        with MIXER_LOCK:
            pygame.mixer.init(devicename=device) if device else pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
        _ready = True

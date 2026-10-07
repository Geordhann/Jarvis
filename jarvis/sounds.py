"""Bruitages façon Iron Man, générés par synthèse (pas de fichiers sous droits).

- demarrage : montée en puissance du réacteur, au lancement
- ecoute    : double bip montant, quand Jarvis t'écoute
- fin       : bip descendant, quand il a compris ta demande
- stop      : coupure brève, quand on l'interrompt
Désactivables : python -m jarvis --bruitages non, ou « Jarvis, coupe les bruitages ».
"""

from __future__ import annotations

import io
import threading
import wave

from . import config

RATE = 44100
_cache: dict[str, object] = {}
_lock = threading.Lock()


def enabled() -> bool:
    return (config.get("bruitages") or "oui").lower() not in ("non", "off", "0")


def _tone(freqs, duration: float, volume: float = 0.35, attack: float = 0.01, release: float = 0.08):
    import numpy as np

    n = int(RATE * duration)
    t = np.arange(n) / RATE
    f = np.interp(t, np.linspace(0, duration, len(freqs)), freqs) if len(freqs) > 1 else np.full(n, freqs[0])
    phase = 2 * np.pi * np.cumsum(f) / RATE
    wave_ = np.sin(phase) + 0.25 * np.sin(2 * phase) + 0.1 * np.sin(3 * phase)
    env = np.minimum(1, t / attack) * np.minimum(1, (duration - t) / release)
    return (wave_ * env * volume).astype(np.float32)


def _render(name: str):
    import numpy as np

    if name == "ecoute":
        return np.concatenate([_tone([880], 0.07), np.zeros(int(RATE * 0.03), np.float32), _tone([1320], 0.09)])
    if name == "fin":
        return _tone([1100, 660], 0.14, volume=0.3)
    if name == "stop":
        return _tone([500, 250], 0.12, volume=0.35, release=0.03)
    if name == "demarrage":
        # Montée du réacteur : glissando grave → aigu, scintillement, puis « ding » final.
        rise = _tone([90, 180, 420, 880], 1.1, volume=0.25, attack=0.3, release=0.2)
        t = np.arange(len(rise)) / RATE
        rise *= (0.85 + 0.15 * np.sin(2 * np.pi * 18 * t)).astype(np.float32)
        ding = _tone([1760], 0.5, volume=0.22, attack=0.005, release=0.45)
        return np.concatenate([rise, ding])
    raise ValueError(name)


def _sound(name: str):
    import numpy as np
    import pygame

    with _lock:
        if name not in _cache:
            samples = (np.clip(_render(name), -1, 1) * 32767).astype(np.int16)
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes(samples.tobytes())
            buffer.seek(0)
            _cache[name] = pygame.mixer.Sound(buffer)
        return _cache[name]


def play(name: str) -> None:
    """Joue un bruitage sans bloquer (ne fait rien si désactivé ou sans sortie son)."""
    if not enabled():
        return
    try:
        from .audio_out import MIXER_LOCK, ensure_mixer

        ensure_mixer()
        with MIXER_LOCK:
            _sound(name).play()
    except Exception as exc:
        print(f"[bruitage] « {name} » impossible : {exc}")

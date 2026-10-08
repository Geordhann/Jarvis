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
    from . import themes

    theme = themes.current()
    if theme == "ultron":
        return _render_ultron(name)
    if theme == "bigboss":
        return _render_codec(name)
    return _render_jarvis(name)


def _render_ultron(name: str):
    """Sons d'Ultron : graves, saturés, inquiétants."""
    import numpy as np

    def grim(freqs, duration, volume=0.35, **kw):
        tone = _tone(freqs, duration, volume=volume, **kw)
        return np.tanh(tone * 4).astype(np.float32) * volume  # saturation

    if name == "ecoute":
        return np.concatenate([grim([220], 0.09), np.zeros(int(RATE * 0.03), np.float32), grim([165], 0.14)])
    if name == "fin":
        return grim([180, 90], 0.2, volume=0.3)
    if name == "stop":
        return grim([140, 60], 0.15, volume=0.35, release=0.03)
    if name == "demarrage":
        rise = grim([40, 55, 90, 130], 1.6, volume=0.3, attack=0.5, release=0.3)
        t = np.arange(len(rise)) / RATE
        rise *= (0.7 + 0.3 * np.sin(2 * np.pi * 6 * t)).astype(np.float32)  # pulsation lente
        hit = grim([70, 35], 0.8, volume=0.4, attack=0.005, release=0.7)
        return np.concatenate([rise, hit])
    raise ValueError(name)


def _render_codec(name: str):
    """Sons façon codec de Metal Gear : bips radio aigus (sons recréés, pas d'extrait du jeu)."""
    import numpy as np

    def blip(freq, duration, volume=0.3):  # bip carré, façon vieille radio
        t = np.arange(int(RATE * duration)) / RATE
        env = np.minimum(1, t / 0.002) * np.minimum(1, (duration - t) / 0.01)
        return (np.sign(np.sin(2 * np.pi * freq * t)) * env * volume * 0.5).astype(np.float32)

    gap = lambda s: np.zeros(int(RATE * s), np.float32)  # noqa: E731
    if name == "ecoute":  # alerte « ! »
        return np.concatenate([_tone([1400, 2200], 0.08, volume=0.4, attack=0.002, release=0.02),
                               _tone([2200], 0.18, volume=0.3, attack=0.002, release=0.15)])
    if name == "fin":
        return np.concatenate([blip(1800, 0.05), gap(0.03), blip(1800, 0.05)])
    if name == "stop":
        return blip(600, 0.12)
    if name == "demarrage":  # appel codec : sonnerie à deux tons, deux fois
        ring = np.concatenate([blip(1450, 0.09), blip(1150, 0.09)] * 3)
        return np.concatenate([ring, gap(0.25), ring, gap(0.2), blip(2000, 0.12)])
    raise ValueError(name)


def _render_jarvis(name: str):
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

    from . import themes

    key = f"{themes.current()}:{name}"
    with _lock:
        if key not in _cache:
            samples = (np.clip(_render(name) * 1.6, -1, 1) * 32767).astype(np.int16)  # bien audibles
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes(samples.tobytes())
            buffer.seek(0)
            _cache[key] = pygame.mixer.Sound(buffer)
        return _cache[key]


last_error: str | None = None


def play(name: str) -> bool:
    """Joue un bruitage sans bloquer (ne fait rien si désactivé ou sans sortie son)."""
    global last_error
    if not enabled():
        return False
    try:
        from .audio_out import ensure_mixer

        ensure_mixer()
        _sound(name).play()
        return True
    except Exception as exc:
        last_error = str(exc)
        print(f"[bruitage] « {name} » impossible : {exc}")
        return False

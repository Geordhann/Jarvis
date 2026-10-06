"""Effets sur la voix de Jarvis (droïde, robot…), appliqués directement : plus besoin de Voicemod.

Réglage mémorisé : python -m jarvis --effet droide   (aucun, ia, droide, tactique, robot)
"""

from __future__ import annotations

import io

from . import config

PRESETS = {
    "aucun": "voix normale",
    "ia": "légère touche synthétique, comme le Jarvis des films",
    "droide": "droïde : métallique et un peu nasillard",
    "tactique": "droïde tactique : plus grave, froid et métallique",
    "robot": "robot : très métallique, façon vieux synthétiseur",
}


def current() -> str:
    name = (config.get("effet") or "aucun").lower()
    return name if name in PRESETS else "aucun"


def _ring_mod(audio, sample_rate: int, freq: float, mix: float):
    """Modulation en anneau : multiplie la voix par une sinusoïde → timbre métallique de droïde."""
    import numpy as np

    t = np.arange(audio.shape[-1], dtype=np.float32) / sample_rate
    carrier = np.sin(2 * np.pi * freq * t).astype(np.float32)
    return (1 - mix) * audio + mix * audio * carrier


def _board(name: str):
    from pedalboard import (Bitcrush, Chorus, Compressor, Gain, HighpassFilter, LowpassFilter, Pedalboard,
                            PitchShift, Reverb)

    if name == "ia":
        return None, Pedalboard([Chorus(rate_hz=0.8, depth=0.15, mix=0.25),
                                 Reverb(room_size=0.15, wet_level=0.12, dry_level=0.9)])
    if name == "droide":
        return (90, 0.55), Pedalboard([HighpassFilter(250), PitchShift(semitones=1),
                                       Chorus(rate_hz=3, depth=0.3, mix=0.4), Bitcrush(bit_depth=10),
                                       LowpassFilter(5500), Compressor(threshold_db=-18, ratio=3), Gain(3)])
    if name == "tactique":
        return (55, 0.5), Pedalboard([PitchShift(semitones=-2), HighpassFilter(180),
                                      Chorus(rate_hz=1.5, depth=0.25, centre_delay_ms=4, mix=0.35),
                                      Bitcrush(bit_depth=11), LowpassFilter(6000),
                                      Reverb(room_size=0.1, wet_level=0.1, dry_level=0.95),
                                      Compressor(threshold_db=-18, ratio=3), Gain(3)])
    if name == "robot":
        return (30, 0.85), Pedalboard([HighpassFilter(200), Bitcrush(bit_depth=8), LowpassFilter(4500),
                                       Compressor(threshold_db=-16, ratio=4), Gain(4)])
    return None, None


def apply(mp3: bytes, name: str | None = None) -> tuple[bytes, str]:
    """Renvoie (audio, extension) : le MP3 tel quel sans effet, sinon un WAV transformé."""
    name = name or current()
    if name == "aucun":
        return mp3, "mp3"
    try:
        import numpy as np
        from pedalboard.io import AudioFile

        with AudioFile(io.BytesIO(mp3)) as f:
            audio, sample_rate = f.read(f.frames), f.samplerate
        ring, board = _board(name)
        if ring:
            audio = _ring_mod(audio, sample_rate, *ring)
        if board is not None:
            audio = board(audio, sample_rate)
        audio = np.clip(audio, -1.0, 1.0)
        out = io.BytesIO()
        with AudioFile(out, "w", sample_rate, audio.shape[0], format="wav") as f:
            f.write(audio)
        return out.getvalue(), "wav"
    except Exception as exc:  # l'effet ne doit jamais empêcher Jarvis de parler
        print(f"[effet] « {name} » impossible ({exc}), voix normale.")
        return mp3, "mp3"

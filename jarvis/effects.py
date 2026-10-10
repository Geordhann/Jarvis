"""Effets sur la voix de Jarvis (droïde, robot…), appliqués directement : plus besoin de Voicemod.

Réglage mémorisé : python -m jarvis --effet droide   (aucun, ia, droide, tactique, robot, perso)
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
    "perso": "ta chaîne Voicemod : PowerPitch → Robotifier → Hauteur (réglable avec --effet-perso)",
}

# Réglages de « perso », dans les unités des boutons Voicemod (0 à 100, 50 = neutre pour la hauteur) :
# PowerPitch, mix du Robotifier, Hauteur. Valeurs de la chaîne « (Copy) Tactical Droid ».
DEFAULT_PERSO = (73, 100, 13)
SEMITONES_PER_HALF = 12   # bouton à 0 ou 100 = une octave plus bas ou plus haut
# Mesuré sur un enregistrement de la voix Voicemod de l'utilisateur : bourdonnement fixe à 120 Hz,
# son très sombre (presque toute l'énergie sous 600 Hz).
BUZZ_HZ = 120             # note finale du bourdonnement robotique
# Retour de l'utilisateur sur la 1re version (coupure à 550 Hz) : trop étouffée et trop faible.
CLARITY_HZ = 3000         # coupure des aigus (plus haut = moins étouffé) ; --effet-perso-clarte
BASS_DB = -2              # graves autour du bourdonnement (négatif = moins « boum »)
PRESENCE_DB = 5           # présence vers 2 kHz : rend les mots plus nets
TARGET_RMS = 0.22         # volume visé pendant la parole (normalisation)


def current() -> str:
    name = (config.get("effet") or "aucun").lower()
    return name if name in PRESETS else "aucun"


def _ring_mod(audio, sample_rate: int, freq: float, mix: float):
    """Modulation en anneau : multiplie la voix par une sinusoïde → timbre métallique de droïde."""
    import numpy as np

    t = np.arange(audio.shape[-1], dtype=np.float32) / sample_rate
    carrier = np.sin(2 * np.pi * freq * t).astype(np.float32)
    return (1 - mix) * audio + mix * audio * carrier


def perso_settings() -> tuple[float, float, float]:
    raw = config.get("effet_perso") or ""
    try:
        values = tuple(float(v) for v in raw.replace(";", ",").split(","))
        if len(values) == 3:
            return values  # type: ignore[return-value]
    except ValueError:
        pass
    return DEFAULT_PERSO


def _knob_to_semitones(value: float) -> float:
    return (value - 50) / 50 * SEMITONES_PER_HALF


def _robotize(audio, sample_rate: int, mix: float, freq: float):
    """Robotifier : supprime la phase de chaque petit bloc de son → voix monocorde et bourdonnante."""
    import numpy as np

    hop = max(32, int(sample_rate / freq))
    size = hop * 2
    window = np.hanning(size).astype(np.float32)
    result = np.zeros_like(audio)
    for ch in range(audio.shape[0]):
        x = np.concatenate([audio[ch], np.zeros(size, dtype=np.float32)])
        y = np.zeros_like(x)
        for start in range(0, len(x) - size, hop):
            magnitude = np.abs(np.fft.rfft(x[start:start + size] * window))
            frame = np.fft.fftshift(np.fft.irfft(magnitude, size)).astype(np.float32)
            y[start:start + size] += frame * window
        y = y[:audio.shape[1]]
        # Même volume moyen que la voix d'origine.
        rms_in, rms_out = np.sqrt(np.mean(audio[ch] ** 2)), np.sqrt(np.mean(y ** 2))
        if rms_out > 1e-9:
            y *= rms_in / rms_out
        result[ch] = (1 - mix) * audio[ch] + mix * y
    return result


def _perso(audio, sample_rate: int):
    from pedalboard import (Compressor, HighpassFilter, LadderFilter, LowShelfFilter, Pedalboard, PeakFilter,
                            PitchShift)

    power_pitch, robot_mix, pitch = perso_settings()
    last_shift = _knob_to_semitones(pitch)
    try:
        buzz = float(config.get("effet_perso_bourdon") or BUZZ_HZ)
    except ValueError:
        buzz = BUZZ_HZ
    audio = Pedalboard([PitchShift(semitones=_knob_to_semitones(power_pitch))])(audio, sample_rate)
    # Le bourdonnement est créé plus haut pour retomber exactement sur `buzz` après la dernière transposition.
    audio = _robotize(audio, sample_rate, mix=max(0.0, min(1.0, robot_mix / 100)),
                      freq=buzz / 2 ** (last_shift / 12))
    try:
        clarity = float(config.get("effet_perso_clarte") or CLARITY_HZ)
    except ValueError:
        clarity = CLARITY_HZ
    audio = Pedalboard([
        PitchShift(semitones=last_shift),
        HighpassFilter(70),
        LowShelfFilter(cutoff_frequency_hz=180, gain_db=BASS_DB),
        PeakFilter(cutoff_frequency_hz=2000, gain_db=PRESENCE_DB, q=0.8),
        LadderFilter(mode=LadderFilter.Mode.LPF12, cutoff_hz=clarity, resonance=0.1),
        Compressor(threshold_db=-22, ratio=3, attack_ms=5, release_ms=80),
    ])(audio, sample_rate)
    return audio


def _loud(audio, sample_rate: int):
    """Monte le volume pendant la parole jusqu'à TARGET_RMS (× --volume-voix), sans saturer."""
    import numpy as np
    from pedalboard import Limiter, Pedalboard

    try:
        boost = max(0.2, min(3.0, float(config.get("volume_voix") or 100) / 100))
    except ValueError:
        boost = 1.0
    speech = audio[np.abs(audio) > 0.05 * (np.abs(audio).max() or 1)]
    rms = float(np.sqrt(np.mean(speech ** 2))) if speech.size else 0.0
    if rms > 1e-6:
        audio = audio * min(20.0, TARGET_RMS * boost / rms)
    audio = Pedalboard([Limiter(threshold_db=-1.0, release_ms=60)])(audio.astype(np.float32), sample_rate)
    return np.clip(audio, -1.0, 1.0)


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
        from pedalboard.io import AudioFile

        with AudioFile(io.BytesIO(mp3)) as f:
            audio, sample_rate = f.read(f.frames), f.samplerate
        if name == "perso":
            audio = _perso(audio, sample_rate)
        else:
            ring, board = _board(name)
            if ring:
                audio = _ring_mod(audio, sample_rate, *ring)
            if board is not None:
                audio = board(audio, sample_rate)
        audio = _loud(audio, sample_rate)
        out = io.BytesIO()
        with AudioFile(out, "w", sample_rate, audio.shape[0], format="wav") as f:
            f.write(audio)
        return out.getvalue(), "wav"
    except Exception as exc:  # l'effet ne doit jamais empêcher Jarvis de parler
        print(f"[effet] « {name} » impossible ({exc}), voix normale.")
        return mp3, "mp3"

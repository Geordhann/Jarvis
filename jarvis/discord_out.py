"""La voix de Jarvis dans ton micro Discord, grâce à un câble audio virtuel (VB-Cable, gratuit).

Jarvis joue la phrase dans « CABLE Input » ; Discord utilise « CABLE Output » comme micro.
Pour que tes amis t'entendent toi aussi, Windows renvoie ton vrai micro dans le câble
(Son → Enregistrement → ton micro → Propriétés → Écouter → « Écouter ce périphérique »
→ lecture sur « CABLE Input »). Voir README, section Discord.
"""

from __future__ import annotations

import io

from . import config


def device_index() -> int | None:
    """Numéro de la sortie « CABLE Input » (ou celle choisie avec --sortie-discord)."""
    import sounddevice

    wanted = (config.get("sortie_discord") or "cable input").lower()
    for i, dev in enumerate(sounddevice.query_devices()):
        if dev["max_output_channels"] > 0 and wanted in dev["name"].lower():
            return i
    return None


def available() -> bool:
    try:
        return device_index() is not None
    except Exception:
        return False


def play(audio: bytes) -> None:
    """Joue l'audio (MP3 ou WAV) dans le câble, sans bloquer."""
    try:
        import sounddevice
        from pedalboard.io import AudioFile

        index = device_index()
        if index is None:
            print("[discord] « CABLE Input » introuvable : installe VB-Cable (voir README).")
            return
        with AudioFile(io.BytesIO(audio)) as f:
            samples, rate = f.read(f.frames), f.samplerate
        sounddevice.play(samples.T, rate, device=index)
    except Exception as exc:  # Discord ne doit jamais empêcher Jarvis de parler
        print(f"[discord] lecture impossible : {exc}")


def stop() -> None:
    try:
        import sounddevice

        sounddevice.stop()
    except Exception:
        pass

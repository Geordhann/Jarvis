"""Enregistre la même phrase avec et sans Voicemod, pour régler l'effet « perso » au plus juste.

python -m jarvis --enregistrer-voicemod   (Voicemod doit être lancé, avec la voix voulue active)
Crée deux fichiers WAV : normal.wav (ton micro) et voicemod.wav (le micro virtuel de Voicemod).
"""

from __future__ import annotations

import threading
import wave
from pathlib import Path

SECONDS = 8
SENTENCE = "Bonjour, je suis Jarvis. Tous les systèmes sont opérationnels. Un, deux, trois, quatre, cinq."


def _inputs(pa) -> list[tuple[int, str, int]]:
    devices = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) > 0:
            devices.append((i, info["name"], int(info.get("defaultSampleRate") or 44100)))
    return devices


def _record(pa, device: tuple[int, str, int], path: Path, errors: list) -> None:
    import pyaudio

    index, name, rate = device
    try:
        stream = pa.open(format=pyaudio.paInt16, channels=1, rate=rate, input=True,
                         input_device_index=index, frames_per_buffer=1024)
        frames = [stream.read(1024, exception_on_overflow=False) for _ in range(int(rate / 1024 * SECONDS))]
        stream.stop_stream()
        stream.close()
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes(b"".join(frames))
    except Exception as exc:
        errors.append(f"{name} : {exc}")


def record_pair() -> None:
    import pyaudio

    from . import config

    pa = pyaudio.PyAudio()
    devices = _inputs(pa)
    voicemod = next((d for d in devices if "voicemod" in d[1].lower()), None)
    wanted = (config.get("micro") or "").lower()
    real = next((d for d in devices if wanted and wanted in d[1].lower()), None) or \
        next((d for d in devices if "voicemod" not in d[1].lower() and "cable" not in d[1].lower()), None)
    if voicemod is None:
        print("✘ Micro Voicemod introuvable : lance Voicemod, active la voix voulue, puis réessaie.")
        return
    if real is None:
        print("✘ Aucun vrai micro trouvé.")
        return
    folder = Path.home() / "Documents" / "Jarvis Voicemod"
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Micro normal  : {real[1]}\nMicro Voicemod : {voicemod[1]}\n")
    print("Dans Voicemod : vérifie que la voix « Tactical Droid » est active et que le micro Voicemod")
    print("utilise ton vrai micro (Input = Microphone USB), pas le câble.\n")
    input("Appuie sur Entrée, puis lis à voix haute, normalement :\n\n  « " + SENTENCE + " »\n")
    print(f"🔴 Enregistrement pendant {SECONDS} secondes…")
    errors: list = []
    threads = [threading.Thread(target=_record, args=(pa, real, folder / "normal.wav", errors)),
               threading.Thread(target=_record, args=(pa, voicemod, folder / "voicemod.wav", errors))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    pa.terminate()
    if errors:
        print("✘ " + "\n✘ ".join(errors))
        return
    print(f"\n✔ Terminé ! Deux fichiers dans {folder} : normal.wav et voicemod.wav")
    print("Envoie-les à Claude pour qu'il règle l'effet « perso » (voir README).")

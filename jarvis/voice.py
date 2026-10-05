"""La voix de Jarvis sur l'ordinateur : phrases synthétisées puis jouées dans l'ordre."""

from __future__ import annotations

import os
import queue
import tempfile
import threading

from . import tts


class Voice:
    """Deux threads : l'un prépare l'audio de la phrase suivante pendant que l'autre joue
    la phrase en cours, pour enchaîner sans blanc. Repli hors-ligne sur pyttsx3."""

    def __init__(self, voice: str | None = None, muted: bool = False):
        self.voice = voice  # prénom ou identifiant ; None = voix enregistrée / par défaut
        self.muted = muted
        self._texts: queue.Queue[str] = queue.Queue()
        self._audio: queue.Queue[tuple[str, bytes | None]] = queue.Queue()
        self._engine = None
        self._mixer_ready = False
        threading.Thread(target=self._synth_loop, daemon=True).start()
        threading.Thread(target=self._play_loop, daemon=True).start()

    def say(self, text: str) -> None:
        print(f"JARVIS › {text}", flush=True)
        if not self.muted:
            self._texts.put(text)

    def wait(self) -> None:
        """Bloque jusqu'à ce que tout ce qui est en file ait été prononcé."""
        self._texts.join()
        self._audio.join()

    def _synth_loop(self) -> None:
        while True:
            text = self._texts.get()
            try:
                audio = tts.synthesize(text, self.voice)
            except Exception as exc:
                print(f"[voix] synthèse impossible ({exc}), voix hors-ligne.")
                audio = None
            self._audio.put((text, audio))
            self._texts.task_done()

    def _play_loop(self) -> None:
        while True:
            text, audio = self._audio.get()
            try:
                if audio:
                    self._play_mp3(audio)
                else:
                    self._speak_offline(text)
            except Exception as exc:  # la voix ne doit jamais faire planter Jarvis
                print(f"[voix] erreur : {exc}")
            finally:
                self._audio.task_done()

    def _play_mp3(self, audio: bytes) -> None:
        import pygame

        if not self._mixer_ready:
            pygame.mixer.init()
            self._mixer_ready = True
        fd, path = tempfile.mkstemp(suffix=".mp3")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(audio)
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)
            pygame.mixer.music.unload()
        finally:
            os.remove(path)

    def _speak_offline(self, text: str) -> None:
        import pyttsx3

        if self._engine is None:
            self._engine = pyttsx3.init()
            for v in self._engine.getProperty("voices"):
                if "fr" in (v.id + str(v.languages)).lower():
                    self._engine.setProperty("voice", v.id)
                    break
        self._engine.say(text)
        self._engine.runAndWait()

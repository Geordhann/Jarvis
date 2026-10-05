"""La voix de Jarvis : synthèse vocale jouée phrase par phrase."""

from __future__ import annotations

import asyncio
import os
import queue
import tempfile
import threading

DEFAULT_VOICE = "fr-FR-HenriNeural"


class Voice:
    """File d'attente de phrases lues dans l'ordre par un thread dédié.

    Utilise edge-tts (voix neuronales Microsoft, gratuites, nécessite Internet)
    et retombe sur pyttsx3 (hors-ligne, voix du système) en cas d'échec.
    """

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = "+5%", muted: bool = False):
        self.voice = voice
        self.rate = rate
        self.muted = muted
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._engine = None
        self._mixer_ready = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def say(self, text: str) -> None:
        print(f"JARVIS › {text}", flush=True)
        if not self.muted:
            self._queue.put(text)

    def wait(self) -> None:
        """Bloque jusqu'à ce que tout ce qui est en file ait été prononcé."""
        self._queue.join()

    def _run(self) -> None:
        while True:
            text = self._queue.get()
            try:
                if text:
                    self._speak(text)
            except Exception as exc:  # la voix ne doit jamais faire planter Jarvis
                print(f"[voix] erreur : {exc}")
            finally:
                self._queue.task_done()

    def _speak(self, text: str) -> None:
        try:
            self._speak_edge(text)
        except Exception:
            self._speak_offline(text)

    def _speak_edge(self, text: str) -> None:
        import edge_tts
        import pygame

        if not self._mixer_ready:
            pygame.mixer.init()
            self._mixer_ready = True
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            asyncio.run(edge_tts.Communicate(text, self.voice, rate=self.rate).save(path))
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

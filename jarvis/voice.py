"""La voix de Jarvis sur l'ordinateur : phrases synthétisées puis jouées dans l'ordre."""

from __future__ import annotations

import os
import queue
import tempfile
import threading

from . import effects, state, tts


class Voice:
    """Deux threads : l'un prépare l'audio de la phrase suivante pendant que l'autre joue
    la phrase en cours, pour enchaîner sans blanc. Repli hors-ligne sur pyttsx3."""

    def __init__(self, voice: str | None = None, muted: bool = False):
        self.voice = voice  # prénom ou identifiant ; None = voix enregistrée / par défaut
        self.muted = muted
        self._texts: queue.Queue[str] = queue.Queue()
        self._audio: queue.Queue[tuple[str, bytes | None, str]] = queue.Queue()
        self._engine = None
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
                audio, ext = effects.apply(tts.synthesize(text, self.voice))
            except Exception as exc:
                print(f"[voix] synthèse impossible ({exc}), voix hors-ligne.")
                audio, ext = None, "mp3"
            self._audio.put((text, audio, ext))
            self._texts.task_done()

    def _play_loop(self) -> None:
        while True:
            text, audio, ext = self._audio.get()
            state.set(state.SPEAKING, text)
            try:
                if audio:
                    self._play(audio, ext)
                else:
                    self._speak_offline(text)
            except Exception as exc:  # la voix ne doit jamais faire planter Jarvis
                print(f"[voix] erreur : {exc}")
            finally:
                self._audio.task_done()
                if self._audio.empty() and self._texts.empty():
                    state.set(state.IDLE)

    def _play(self, audio: bytes, ext: str = "mp3") -> None:
        import pygame

        from .audio_out import ensure_mixer

        ensure_mixer()  # sortie son partagée avec la musique de démarrage
        fd, path = tempfile.mkstemp(suffix=f".{ext}")
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

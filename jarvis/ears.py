"""Les oreilles de Jarvis : écoute du micro et reconnaissance vocale."""

from __future__ import annotations


class Ears:
    """Reconnaissance vocale via SpeechRecognition + Google Web Speech (gratuit, Internet requis)."""

    def __init__(self, language: str = "fr-FR"):
        import speech_recognition as sr

        self.sr = sr
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.microphone = sr.Microphone()
        with self.microphone as source:
            print("Calibrage du micro, silence s'il vous plaît…")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def listen(self, timeout: float | None = None) -> str | None:
        """Écoute une phrase et renvoie le texte reconnu (ou None si rien compris).

        `timeout` : secondes d'attente maximum avant que quelqu'un commence à parler.
        """
        sr = self.sr
        with self.microphone as source:
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=20)
            except sr.WaitTimeoutError:
                return None
        try:
            return self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            print(f"[écoute] service de reconnaissance indisponible : {exc}")
            return None

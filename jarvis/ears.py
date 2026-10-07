"""Les oreilles de Jarvis : écoute du micro et reconnaissance vocale.

Sensibilité réglable de 1 (capte seulement une voix forte) à 10 (capte un murmure) :
python -m jarvis --sensibilite-micro 8, ou « Jarvis, sois plus sensible ».
"""

from __future__ import annotations

import re

from . import config

DEFAULT_SENSITIVITY = 7

# Écoute des phrases longues : au-delà de LONG_PHRASE secondes de parole, une pause de moins de
# LONG_PAUSE secondes ne termine plus la phrase (jusqu'à MAX_TOTAL secondes en tout).
PHRASE_LIMIT = 30
LONG_PHRASE = 4.0
LONG_PAUSE = 1.5
MAX_TOTAL = 120
UNFINISHED_WAIT = 2.5
ENDS_UNFINISHED_RE = re.compile(
    r"\b(et|ou|mais|donc|alors|puis|ensuite|avec|pour|de|du|des|le|la|les|un|une|a|à|au|aux|en|dans|sur|"
    r"que|qui|quand|si|comme|parce que|par exemple|genre|euh|ben)\s*$", re.IGNORECASE)


def _seconds(audio) -> float:
    return len(audio.frame_data) / (audio.sample_rate * audio.sample_width)


def sensitivity() -> int:
    try:
        return max(1, min(10, int(config.get("sensibilite_micro") or DEFAULT_SENSITIVITY)))
    except ValueError:
        return DEFAULT_SENSITIVITY


class Ears:
    """Reconnaissance vocale via SpeechRecognition + Google Web Speech (gratuit, Internet requis)."""

    def __init__(self, language: str = "fr-FR"):
        import speech_recognition as sr

        from .audio_devices import input_index

        self.sr = sr
        self.language = language
        self.recognizer = sr.Recognizer()
        # Laisse finir les phrases : une courte hésitation ne coupe plus l'écoute.
        self.recognizer.pause_threshold = 1.0
        self.recognizer.non_speaking_duration = 0.5
        self.recognizer.phrase_threshold = 0.2
        self.microphone = sr.Microphone(device_index=input_index())
        with self.microphone as source:
            print("Calibrage du micro, silence s'il vous plaît…")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
        self.ambient = self.recognizer.energy_threshold
        self.apply_sensitivity()

    def apply_sensitivity(self) -> None:
        """Seuil de déclenchement : plus la sensibilité est haute, plus le seuil est bas."""
        level = sensitivity()
        factor = 1.7 - 0.12 * level          # 1 → 1,58 × le bruit ambiant ; 10 → 0,5 ×
        self.recognizer.energy_threshold = max(30.0, self.ambient * factor)
        # Le seuil suit le bruit de la pièce, avec une marge plus faible si on est sensible.
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_ratio = 1.1 + 0.08 * (10 - level)
        print(f"[micro] sensibilité {level}/10 (seuil {self.recognizer.energy_threshold:.0f})")

    def listen(self, timeout: float | None = None) -> str | None:
        """Écoute une phrase et renvoie le texte reconnu (ou None si rien compris).

        `timeout` : secondes d'attente maximum avant que quelqu'un commence à parler.
        """
        sr = self.sr
        with self.microphone as source:
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=PHRASE_LIMIT)
            except sr.WaitTimeoutError:
                return None
            audio = self._continue_long(source, audio)
        text = self._recognize(audio)
        if text and ENDS_UNFINISHED_RE.search(text):
            # Phrase qui finit par « et », « pour », « parce que »… : tu n'as pas fini, on écoute la suite.
            with self.microphone as source:
                try:
                    more = self.recognizer.listen(source, timeout=UNFINISHED_WAIT, phrase_time_limit=PHRASE_LIMIT)
                except sr.WaitTimeoutError:
                    return text
                more = self._continue_long(source, more)
            text = f"{text} {self._recognize(more) or ''}".strip()
        return text

    def _continue_long(self, source, audio):
        """Phrase longue : une pause pour réfléchir ne coupe pas, on écoute encore un peu et on
        recolle les morceaux (une seule reconnaissance à la fin, plus précise)."""
        sr = self.sr
        while _seconds(audio) >= LONG_PHRASE and _seconds(audio) < MAX_TOTAL:
            try:
                more = self.recognizer.listen(source, timeout=LONG_PAUSE, phrase_time_limit=PHRASE_LIMIT)
            except sr.WaitTimeoutError:
                break
            audio = sr.AudioData(audio.frame_data + more.frame_data, audio.sample_rate, audio.sample_width)
        return audio

    def _recognize(self, audio) -> str | None:
        sr = self.sr
        try:
            return self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            print(f"[écoute] service de reconnaissance indisponible : {exc}")
            return None

    def listen_short(self) -> str | None:
        """Écoute brève pendant que Jarvis parle, pour entendre « stop ». Le seuil est remis
        ensuite : la voix de Jarvis dans le micro ne doit pas rendre l'écoute normale moins sensible."""
        sr = self.sr
        threshold = self.recognizer.energy_threshold
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
        except sr.WaitTimeoutError:
            return None
        finally:
            self.recognizer.energy_threshold = threshold
        try:
            return self.recognizer.recognize_google(audio, language=self.language)
        except (sr.UnknownValueError, sr.RequestError):
            return None


def test_microphone() -> None:
    """python -m jarvis --tester-micro : affiche ce que Jarvis comprend, pour régler la sensibilité."""
    ears = Ears()
    print(f"Bruit ambiant mesuré : {ears.ambient:.0f}. Parle normalement (Ctrl+C pour arrêter).\n")
    try:
        while True:
            print("… j'écoute")
            text = ears.listen(timeout=10)
            if text:
                print(f"  ✔ compris : « {text} »")
            else:
                print("  ✘ rien compris. Essaie plus près du micro, ou augmente la sensibilité "
                      "(python -m jarvis --sensibilite-micro 9).")
    except KeyboardInterrupt:
        print("\nTest terminé.")

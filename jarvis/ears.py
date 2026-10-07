"""Les oreilles de Jarvis : écoute du micro et reconnaissance vocale.

Sensibilité réglable de 1 (capte seulement une voix forte) à 10 (capte un murmure) :
python -m jarvis --sensibilite-micro 8, ou « Jarvis, sois plus sensible ».
"""

from __future__ import annotations

from . import config

DEFAULT_SENSITIVITY = 7


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

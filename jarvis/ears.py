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

    # --- reconnaissance -------------------------------------------------------

    def transcribe(self, audio) -> str | None:
        """Texte d'un enregistrement (sr.AudioData) : Whisper sur le PC, ou Google (par défaut)."""
        if recognition_engine() == "whisper":
            return whisper_transcribe(audio)
        sr = self.sr
        try:
            return self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            print(f"[écoute] service de reconnaissance indisponible : {exc}")
            return None

    def listen(self, timeout: float | None = None, phrase_limit: float = 20) -> str | None:
        """Écoute une phrase et renvoie le texte reconnu (ou None si rien compris).

        `timeout` : secondes d'attente maximum avant que quelqu'un commence à parler.
        """
        sr = self.sr
        with self.microphone as source:
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except sr.WaitTimeoutError:
                return None
        return self.transcribe(audio)

    def listen_short(self) -> str | None:
        """Écoute brève sur un second flux micro, pendant que Jarvis parle (pour l'interrompre)."""
        sr = self.sr
        if not hasattr(self, "_second_mic"):
            from .audio_devices import input_index

            self._second_mic = sr.Microphone(device_index=input_index())
        with self._second_mic as source:
            try:
                audio = self.recognizer.listen(source, timeout=1.5, phrase_time_limit=3)
            except sr.WaitTimeoutError:
                return None
        return self.transcribe(audio)

    # --- mot d'éveil local (« Hey Jarvis ») ------------------------------------

    def wake_and_listen(self, should_wake=lambda: False) -> str | None:
        """Attend « Hey Jarvis » (détecté sur le PC), puis enregistre la demande qui suit, sans en
        perdre le début : on continue de lire le même flux audio. `should_wake()` permet de se
        réveiller autrement (clic sur la boule)."""
        import numpy as np

        from . import sounds

        detector = wake_detector()
        stream = self._wake_stream()
        try:
            detector.reset()
            while True:
                chunk = np.frombuffer(stream.read(WAKE_CHUNK, exception_on_overflow=False), dtype=np.int16)
                if should_wake():
                    break
                if max(detector.predict(chunk).values()) >= wake_threshold():
                    break
            sounds.play("ecoute")
            frames = self._record_request(stream)
        finally:
            stream.stop_stream()
            stream.close()
        if not frames:
            return ""
        audio = self.sr.AudioData(b"".join(frames), WAKE_RATE, 2)
        return self.transcribe(audio) or ""

    def wake_during(self, condition) -> bool:
        """Écoute « Hey Jarvis » tant que `condition()` est vraie (pendant que Jarvis parle)."""
        import numpy as np

        detector = wake_detector()
        stream = self._wake_stream()
        try:
            detector.reset()
            while condition():
                chunk = np.frombuffer(stream.read(WAKE_CHUNK, exception_on_overflow=False), dtype=np.int16)
                if max(detector.predict(chunk).values()) >= wake_threshold():
                    return True
            return False
        finally:
            stream.stop_stream()
            stream.close()

    def _wake_stream(self):
        import pyaudio

        from .audio_devices import input_index

        if not hasattr(self, "_pyaudio"):
            self._pyaudio = pyaudio.PyAudio()
        return self._pyaudio.open(format=pyaudio.paInt16, channels=1, rate=WAKE_RATE, input=True,
                                  input_device_index=input_index(), frames_per_buffer=WAKE_CHUNK)

    def _record_request(self, stream) -> list[bytes]:
        """Enregistre jusqu'à un silence d'environ 1 s (ou 15 s max ; rien si personne ne parle en 5 s)."""
        import numpy as np

        threshold = self.recognizer.energy_threshold
        frames, started, silent, waited = [], False, 0.0, 0.0
        step = WAKE_CHUNK / WAKE_RATE
        while waited < 15:
            data = stream.read(WAKE_CHUNK, exception_on_overflow=False)
            level = float(np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16).astype(np.float32) ** 2)))
            waited += step
            frames.append(data)
            if level > threshold:
                started, silent = True, 0.0
            elif started:
                silent += step
                if silent >= self.recognizer.pause_threshold:
                    break
            elif waited > 5:
                return []
        return frames


WAKE_RATE = 16000
WAKE_CHUNK = 1280  # 80 ms, la taille attendue par openWakeWord
_whisper = None
_detector = None


def recognition_engine() -> str:
    return (config.get("reconnaissance") or "google").lower()


def local_wake_enabled() -> bool:
    return (config.get("eveil_local") or "non").lower() == "oui"


def wake_threshold() -> float:
    try:
        return max(0.1, min(0.95, float(config.get("seuil_eveil") or 0.5)))
    except ValueError:
        return 0.5


def wake_detector():
    """Modèle openWakeWord « hey_jarvis » (téléchargé une seule fois, ~1 Mo)."""
    global _detector
    if _detector is None:
        import openwakeword
        from openwakeword.model import Model

        openwakeword.utils.download_models(["hey_jarvis"])
        _detector = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
    return _detector


WHISPER_HALLUCINATIONS = ("sous-titres", "sous titres", "amara.org", "merci d'avoir regardé",
                          "abonnez-vous", "radio-canada")


def whisper_transcribe(audio) -> str | None:
    """Reconnaissance Whisper sur le PC : précise, sans Internet, la voix ne sort pas de chez toi."""
    global _whisper
    import numpy as np

    if _whisper is None:
        from faster_whisper import WhisperModel

        size = config.get("whisper_modele") or "small"
        print(f"[écoute] chargement de Whisper « {size} » (téléchargé une seule fois)…")
        _whisper = WhisperModel(size, device="auto", compute_type="int8")
    raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    segments, _ = _whisper.transcribe(samples, language="fr", beam_size=1, vad_filter=True,
                                      initial_prompt="Jarvis, assistant vocal.")
    text = " ".join(segment.text.strip() for segment in segments).strip()
    if not text or any(h in text.lower() for h in WHISPER_HALLUCINATIONS):
        return None  # Whisper « invente » parfois ces phrases sur du silence
    return text


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

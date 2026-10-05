"""Point d'entrée : python -m jarvis"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import time
import unicodedata

import anthropic

from . import voices
from .brain import Brain, french_date, french_time
from .voice import Voice

# La reconnaissance vocale écrit parfois « Jarvis » de travers.
WAKE_RE = re.compile(r"\b(jarvis|jarvi|jarvice|jarviss|jervis|djarvis|jarwis)\b[\s,.!?]*")
# Après une réponse, on peut enchaîner une question sans redire « Jarvis » pendant ce délai.
FOLLOW_UP_SECONDS = 8

STOP_WORDS = ("au revoir", "bonne nuit", "eteins-toi", "eteins toi", "arrete-toi", "quitter", "exit")
RESET_WORDS = ("nouvelle conversation", "oublie tout")
TIME_RE = re.compile(r"\b(quelle heure|l'heure|l heure|heure est-il|heure il est)\b")
DATE_RE = re.compile(r"\b(quel jour|quelle date|la date|on est le combien|sommes-nous)\b")
VOICE_CHANGE_RE = re.compile(r"\b(voix)\b")
VOICE_LIST_RE = re.compile(r"\b(quelles voix|liste des voix|change de voix|changer de voix|autre voix)\b")


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def strip_wake_word(text: str) -> str | None:
    """Renvoie la demande qui suit « Jarvis », ou None si le mot d'éveil est absent."""
    plain = _plain(text)
    match = WAKE_RE.search(plain)
    if not match:
        return None
    # Les accents retirés ne changent pas la longueur pour le français courant ;
    # on recoupe donc le texte original à la même position.
    return text[match.end():].strip() if len(plain) == len(text) else plain[match.end():].strip()


class Jarvis:
    def __init__(self, args: argparse.Namespace):
        self.title = args.titre
        self.always_listen = args.toujours
        self.brain = Brain(owner=args.nom, title=args.titre, effort=args.effort)
        self.voice_name = voices.find_voice(args.voix) or args.voix
        self.voice = Voice(voice=voices.voice_id(args.voix), muted=args.muet)
        self.ears = None if args.texte else _init_ears()
        self.awake_until = 0.0

    # --- boucle principale -------------------------------------------------

    def run(self) -> None:
        hint = "" if self.always_listen or self.ears is None else " Dites « Jarvis » suivi de votre demande."
        self.voice.say(f"Bonjour {self.title}. Tous les systèmes sont opérationnels.{hint}")
        self.voice.wait()

        while True:
            try:
                heard = self._listen()
            except (EOFError, KeyboardInterrupt):
                break
            if not heard:
                continue

            request = self._extract_request(heard)
            if request is None:
                continue  # on ne m'a pas appelé : je reste silencieux
            if not request:
                self.voice.say(f"Oui, {self.title} ?")
                self._done_speaking()
                continue

            if not self.handle(request):
                break
            self._done_speaking()

        self.voice.wait()

    def _listen(self) -> str | None:
        if self.ears is None:
            return input("VOUS › ")
        awake = time.monotonic() < self.awake_until
        print("… je vous écoute" if awake else "… (en veille, dites « Jarvis »)")
        text = self.ears.listen(timeout=FOLLOW_UP_SECONDS if awake else None)
        if text:
            print(f"VOUS › {text}")
        return text

    def _extract_request(self, heard: str) -> str | None:
        request = strip_wake_word(heard)
        if request is not None:
            return request
        # Pas de « Jarvis », mais on est dans la fenêtre de relance ou en mode toujours actif.
        if self.always_listen or self.ears is None or time.monotonic() < self.awake_until:
            return heard
        return None

    def _done_speaking(self) -> None:
        # On attend la fin de la parole pour ne pas s'entendre soi-même,
        # puis on ouvre une courte fenêtre pour enchaîner sans redire « Jarvis ».
        self.voice.wait()
        self.awake_until = time.monotonic() + FOLLOW_UP_SECONDS

    # --- commandes ---------------------------------------------------------

    def handle(self, request: str) -> bool:
        """Traite une demande. Renvoie False pour éteindre Jarvis."""
        plain = _plain(request)

        if any(w in plain for w in STOP_WORDS):
            self.voice.say(f"À votre service, {self.title}. Bonne journée.")
            return False
        if any(w in plain for w in RESET_WORDS):
            self.brain.reset()
            self.voice.say("C'est oublié. On repart de zéro.")
            return True
        if self._handle_voice(request, plain):
            return True
        # Réponses instantanées, sans passer par Claude.
        now = datetime.datetime.now()
        if TIME_RE.search(plain) and len(plain.split()) <= 8:
            self.voice.say(f"Il est {french_time(now)}, {self.title}.")
            return True
        if DATE_RE.search(plain) and len(plain.split()) <= 8:
            self.voice.say(f"Nous sommes le {french_date(now.date())}.")
            return True

        self._ask_claude(request)
        return True

    def _handle_voice(self, request: str, plain: str) -> bool:
        if not VOICE_CHANGE_RE.search(plain):
            return False
        name = voices.find_voice(request)
        if name:
            self.set_voice(name)
            return True
        if VOICE_LIST_RE.search(plain):
            names = ", ".join(voices.VOICES)
            self.voice.say(f"Je peux prendre les voix suivantes : {names}. "
                           f"Dites par exemple : Jarvis, prends la voix de Denise.")
            return True
        return False

    def set_voice(self, name: str) -> None:
        self.voice_name = name
        self.voice.voice = voices.VOICES[name][0]
        voices.save_voice(name)
        self.voice.say(f"Voici ma nouvelle voix, {self.title}. Je m'appelle toujours Jarvis.")

    def _ask_claude(self, request: str) -> None:
        try:
            self.brain.ask(request, on_sentence=self.voice.say)
        except anthropic.AuthenticationError:
            self.voice.say("Ma clé d'accès à Claude est invalide. Vérifiez la variable ANTHROPIC_API_KEY.")
        except anthropic.RateLimitError:
            self.voice.say("Je suis un peu surchargé. Réessayez dans un instant.")
        except anthropic.APIStatusError as exc:
            print(f"[erreur API] {exc.status_code} : {exc.message}")
            self.voice.say("Un problème est survenu avec mes serveurs.")
        except anthropic.APIConnectionError:
            self.voice.say("Je n'arrive pas à joindre mes serveurs. Vérifiez la connexion Internet.")


def _init_ears():
    from .ears import Ears

    try:
        return Ears()
    except Exception as exc:
        print(f"Micro indisponible ({exc}). Passage en mode texte.")
        return None


def choose_voice_menu(muted: bool) -> None:
    """Menu interactif : écouter chaque voix et choisir celle de Jarvis."""
    names = list(voices.VOICES)
    preview = Voice(muted=muted)
    while True:
        print("\nVoix disponibles :")
        for i, name in enumerate(names, 1):
            print(f"  {i:2d}. {voices.describe(name)}")
        choice = input("\nNuméro à écouter (Entrée pour quitter) : ").strip()
        if not choice:
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(names):
            print("Numéro invalide.")
            continue
        name = names[int(choice) - 1]
        preview.voice = voices.VOICES[name][0]
        preview.say(f"Bonjour, je suis Jarvis, avec la voix de {name}.")
        preview.wait()
        if input(f"Garder la voix de {name} ? (o/N) ").strip().lower() in ("o", "oui", "y"):
            voices.save_voice(name)
            print(f"C'est noté : Jarvis parlera avec la voix de {name}.")
            return


def main() -> None:
    saved_voice = voices.load_saved_voice()
    parser = argparse.ArgumentParser(description="JARVIS, ton assistant vocal personnel.")
    parser.add_argument("--texte", action="store_true", help="écrire au clavier au lieu de parler")
    parser.add_argument("--muet", action="store_true", help="ne pas lire les réponses à voix haute")
    parser.add_argument("--toujours", action="store_true",
                        help="répondre à tout ce qui est dit, sans attendre « Jarvis »")
    parser.add_argument("--voix",
                        default=os.getenv("JARVIS_VOICE") or saved_voice or voices.DEFAULT_VOICE_NAME,
                        help="prénom de la voix (Henri, Denise, Rémy…) ou identifiant edge-tts")
    parser.add_argument("--choisir-voix", action="store_true",
                        help="écouter les voix disponibles et choisir celle de Jarvis")
    parser.add_argument("--liste-voix", action="store_true", help="afficher les voix disponibles")
    parser.add_argument("--titre", default=os.getenv("JARVIS_TITLE", "Monsieur"),
                        help="comment Jarvis t'appelle")
    parser.add_argument("--nom", default=os.getenv("JARVIS_OWNER", "Monsieur"), help="ton prénom")
    parser.add_argument("--effort", default=os.getenv("JARVIS_EFFORT", "low"),
                        choices=["low", "medium", "high", "xhigh", "max"],
                        help="profondeur de réflexion (low = plus rapide)")
    args = parser.parse_args()

    if args.liste_voix:
        for name in voices.VOICES:
            print(f"  {voices.describe(name)}")
        return
    if args.choisir_voix:
        choose_voice_menu(args.muet)
        return

    Jarvis(args).run()


if __name__ == "__main__":
    main()

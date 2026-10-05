"""Point d'entrée : python -m jarvis"""

from __future__ import annotations

import argparse
import os
import re
import unicodedata

import anthropic

from .brain import Brain
from .voice import DEFAULT_VOICE, Voice

WAKE_WORD = "jarvis"
STOP_WORDS = ("au revoir", "bonne nuit", "éteins-toi", "arrête-toi", "quitter", "exit")
RESET_WORDS = ("nouvelle conversation", "oublie tout")


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _strip_wake_word(text: str) -> str | None:
    """Renvoie la demande après 'Jarvis', ou None si le mot d'éveil est absent."""
    match = re.search(r"\b(jarvis|jarvi|jarvice|jarviss)\b[\s,.!?]*", _normalize(text))
    if not match:
        return None
    return text[match.end():].strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS, ton assistant vocal personnel.")
    parser.add_argument("--texte", action="store_true", help="écrire au clavier au lieu de parler")
    parser.add_argument("--muet", action="store_true", help="ne pas lire les réponses à voix haute")
    parser.add_argument("--eveil", action="store_true",
                        help="ne répondre que si la phrase contient « Jarvis »")
    parser.add_argument("--voix", default=os.getenv("JARVIS_VOICE", DEFAULT_VOICE),
                        help="voix edge-tts (ex. fr-FR-HenriNeural, fr-FR-DeniseNeural)")
    parser.add_argument("--titre", default=os.getenv("JARVIS_TITLE", "Monsieur"),
                        help="comment Jarvis t'appelle")
    parser.add_argument("--nom", default=os.getenv("JARVIS_OWNER", "Monsieur"),
                        help="ton prénom")
    parser.add_argument("--effort", default=os.getenv("JARVIS_EFFORT", "low"),
                        choices=["low", "medium", "high", "xhigh", "max"],
                        help="profondeur de réflexion (low = plus rapide)")
    args = parser.parse_args()

    brain = Brain(owner=args.nom, title=args.titre, effort=args.effort)
    voice = Voice(voice=args.voix, muted=args.muet)
    ears = None if args.texte else _init_ears()

    voice.say(f"Bonjour {args.titre}. Tous les systèmes sont opérationnels. Que puis-je faire pour vous ?")
    voice.wait()

    while True:
        try:
            heard = input("VOUS › ") if ears is None else _listen(ears)
        except (EOFError, KeyboardInterrupt):
            break
        if not heard:
            continue

        if args.eveil:
            heard = _strip_wake_word(heard)
            if heard is None:
                continue
            if not heard:
                voice.say(f"Oui, {args.titre} ?")
                voice.wait()
                continue

        norm = _normalize(heard)
        if any(_normalize(w) in norm for w in STOP_WORDS):
            voice.say(f"À votre service, {args.titre}. Bonne journée.")
            break
        if any(_normalize(w) in norm for w in RESET_WORDS):
            brain.reset()
            voice.say("C'est oublié. On repart de zéro.")
            voice.wait()
            continue

        try:
            brain.ask(heard, on_sentence=voice.say)
        except anthropic.AuthenticationError:
            voice.say("Ma clé d'accès à Claude est invalide. Vérifiez la variable ANTHROPIC_API_KEY.")
            break
        except anthropic.RateLimitError:
            voice.say("Je suis un peu surchargé. Réessayez dans un instant.")
        except anthropic.APIStatusError as exc:
            print(f"[erreur API] {exc.status_code} : {exc.message}")
            voice.say("Un problème est survenu avec mes serveurs.")
        except anthropic.APIConnectionError:
            voice.say("Je n'arrive pas à joindre mes serveurs. Vérifiez la connexion Internet.")
        # On attend la fin de la phrase avant de réécouter, pour ne pas s'entendre soi-même.
        voice.wait()

    voice.wait()


def _init_ears():
    from .ears import Ears

    try:
        return Ears()
    except Exception as exc:
        print(f"Micro indisponible ({exc}). Passage en mode texte.")
        return None


def _listen(ears) -> str | None:
    print("… j'écoute")
    text = ears.listen()
    if text:
        print(f"VOUS › {text}")
    return text


if __name__ == "__main__":
    main()

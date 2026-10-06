"""Point d'entrée : python -m jarvis"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
import threading
import time
import unicodedata

import anthropic

from . import announcer, autostart, config, orb, reminders, state, profile, repliques, services, sessions, telegram_perso, voices
from .agent import MODELS, french_date, french_time
from .tools import ToolFailure, media
from .voice import Voice

# La reconnaissance vocale écrit parfois « Jarvis » de travers.
WAKE_RE = re.compile(r"\b(jarvis|jarvi|jarvice|jarviss|jervis|djarvis|jarwis)\b[\s,.!?]*")
# Après une réponse, on peut enchaîner une question sans redire « Jarvis » pendant ce délai.
FOLLOW_UP_SECONDS = 8

STOP_WORDS = ("au revoir", "eteins-toi", "eteins toi", "arrete-toi", "quitter", "exit")
RESET_WORDS = ("nouvelle conversation", "oublie tout")
TIME_RE = re.compile(r"\b(quelle heure|l'heure|l heure|heure est-il|heure il est)\b")
DATE_RE = re.compile(r"\b(quel jour|quelle date|la date|on est le combien|sommes-nous)\b")
VOICE_CHANGE_RE = re.compile(r"\b(voix)\b")
# Commandes musique instantanées (sans Claude). Texte sans accents.
MEDIA_COMMANDS = [
    (r"(mets? )?(la musique |la video )?(en )?pause|stop(pe)? la musique|arrete la musique|coupe la musique", "pause"),
    (r"reprends?( la musique)?|relance la musique|remets la musique|lecture", "lecture"),
    (r"(chanson|musique|morceau|titre) suivante?|suivant|passe a la suivante", "suivant"),
    (r"(chanson|musique|morceau|titre) precedente?|precedent|reviens en arriere", "precedent"),
    (r"(monte|augmente)( un peu)? (le )?(son|volume)|plus fort", "volume_plus"),
    (r"(baisse|diminue)( un peu)? (le )?(son|volume)|moins fort", "volume_moins"),
    (r"coupe le son|mode muet|silence", "muet"),
]
MEDIA_COMMANDS = [(re.compile(rf"^(?:{p})(?: s'il te plait| stp)?$"), a) for p, a in MEDIA_COMMANDS]
PLAY_RE = re.compile(r"^(?:mets|lance|joue)(?:-moi)?\s+(?:de la |la |une |un )?"
                     r"(?:musique|chanson|morceau|playlist|son)\s*(?:de |du |des |d')?(.*)$|^joue(?:-moi)?\s+(.+)$")
ANNOUNCE_OFF_RE = re.compile(r"\b(arrete|stoppe|desactive|coupe) les annonces\b")
ORB_HIDE_RE = re.compile(r"\b(cache[- ]toi|masque[- ]toi|cache la boule|masque la boule|disparais)\b")
ORB_SHOW_RE = re.compile(r"\b(montre[- ]toi|affiche[- ]toi|affiche la boule|montre la boule|apparais)\b")
EFFECT_RE = re.compile(r"\b(?:effet|mode|voix (?:de )?)\s*(droide|tactique|robot|ia)\b")
EFFECT_OFF_RE = re.compile(r"\b(enleve|retire|coupe|supprime) l'effet\b|\bvoix normale\b|\bsans effet\b")
SPEED_RE = re.compile(r"\bparle (plus )?(vite|rapidement|lentement|doucement|moins vite)\b")
PITCH_RE = re.compile(r"\bvoix (plus )?(grave|aigue|basse|haute)\b")
ANNOUNCE_ON_RE = re.compile(r"\b(active|reactive|remets) les annonces\b")
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
    """L'assistant vocal sur l'ordinateur : micro -> agent -> haut-parleurs."""

    def __init__(self, args: argparse.Namespace):
        self.title = config.get("titre", "Monsieur")
        self.always_listen = args.toujours
        self.voice = Voice(voice=args.voix, muted=args.muet)
        self.ears = None if args.texte else _init_ears(retry=args.fond)
        self.awake_until = 0.0

    @property
    def agent(self):
        return sessions.get("voix", "voix")

    # --- boucle principale -------------------------------------------------

    def run(self) -> None:
        if not self.voice.muted:
            announcer.start(self.voice.say)
        reminders.on_due(self.voice.say)
        self.voice.say(f"Bonjour {self.title}. Tous les systèmes sont opérationnels.")
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
        awake = time.monotonic() < max(self.awake_until, state.awake_until())
        print("… je vous écoute" if awake else "… en veille")
        state.set(state.LISTENING if awake else state.IDLE)
        text = self.ears.listen(timeout=FOLLOW_UP_SECONDS if awake else None)
        if text:
            print(f"VOUS › {text}")
        return text

    def _extract_request(self, heard: str) -> str | None:
        request = strip_wake_word(heard)
        if request is not None:
            return request
        # Pas de « Jarvis », mais on est dans la fenêtre de relance ou en mode toujours actif.
        awake_until = max(self.awake_until, state.awake_until())
        if self.always_listen or self.ears is None or time.monotonic() < awake_until:
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

        ready = repliques.find(request)
        if ready:  # réplique prête à être dite : instantané et gratuit
            self.voice.say(ready)
            return True
        if any(w in plain for w in STOP_WORDS):
            self.voice.say(f"À votre service, {self.title}. Bonne journée.")
            return False
        if any(w in plain for w in RESET_WORDS):
            sessions.reset("voix")
            self.voice.say("C'est oublié. On repart de zéro.")
            return True
        speed, tone = SPEED_RE.search(plain), PITCH_RE.search(plain)
        if speed or tone:
            key, step, word = (("vitesse_voix", 10, speed.group(2)) if speed else ("hauteur_voix", 15, tone.group(2)))
            down = word in ("lentement", "doucement", "moins vite", "grave", "basse")
            value = int(float(re.sub(r"[^\d.+-]", "", config.get(key) or ("5" if speed else "0")) or 0))
            value = max(-50, min(50, value + (-step if down else step)))
            config.save(key, str(value))
            self.voice.say("Comme ceci ?")
            return True
        effect = EFFECT_RE.search(plain)
        if effect or EFFECT_OFF_RE.search(plain):
            config.save("effet", effect.group(1) if effect else "aucun")
            self.voice.say("Effet activé. Comment me trouvez-vous ?" if effect else "Voix normale rétablie.")
            return True
        if self._handle_voice(request, plain) or self._handle_media(request, plain):
            return True
        if ORB_HIDE_RE.search(plain) or ORB_SHOW_RE.search(plain):
            hide = bool(ORB_HIDE_RE.search(plain))
            state.request_visibility("masquer" if hide else "afficher")
            self.voice.say("Je me fais discret." if hide else "Me voici.")
            return True
        if ANNOUNCE_OFF_RE.search(plain) or ANNOUNCE_ON_RE.search(plain):
            on = bool(ANNOUNCE_ON_RE.search(plain))
            config.save("annonces", "oui" if on else "non")
            self.voice.say("Annonces réactivées." if on else "Très bien, je ne vous annonce plus rien.")
            return True
        # Réponses instantanées et gratuites, sans passer par Claude.
        now = datetime.datetime.now()
        if TIME_RE.search(plain) and len(plain.split()) <= 8:
            self.voice.say(f"Il est {french_time(now)}, {self.title}.")
            return True
        if DATE_RE.search(plain) and len(plain.split()) <= 8:
            self.voice.say(f"Nous sommes le {french_date(now.date())}.")
            return True

        self._ask_agent(request)
        return True

    def _handle_voice(self, request: str, plain: str) -> bool:
        if not VOICE_CHANGE_RE.search(plain):
            return False
        name = voices.find_voice(request)
        if name:
            self.voice.voice = name
            voices.save_voice(name)
            self.voice.say(f"Voici ma nouvelle voix, {self.title}. Je m'appelle toujours Jarvis.")
            return True
        if VOICE_LIST_RE.search(plain):
            names = ", ".join(voices.catalog())
            self.voice.say(f"Je peux prendre les voix suivantes : {names}. "
                           f"Dites par exemple : Jarvis, prends la voix de {voices.default_voice()}.")
            return True
        return False

    def _handle_media(self, request: str, plain: str) -> bool:
        clean = plain.strip(" .!?")
        play = PLAY_RE.match(clean)
        try:
            if play and (play.group(1) or play.group(2)):
                # On reprend le texte original (accents compris) pour la recherche.
                query = request.strip(" .!?")[len(clean) - len(play.group(1) or play.group(2)):]
                self.voice.say("Je lance ça.")
                self.voice.wait()
                media.jouer_musique(query)
                return True
            for pattern, action in MEDIA_COMMANDS:
                if pattern.match(clean):
                    media.controle_media(action)
                    return True
        except ToolFailure as exc:
            self.voice.say(f"Je n'y arrive pas : {exc}.")
            return True
        return False

    def _ask_agent(self, request: str) -> None:
        state.set(state.THINKING)
        try:
            self.agent.ask(request, on_sentence=self.voice.say)
        except anthropic.AuthenticationError:
            self.voice.say("Ma clé d'accès à Claude est invalide. Relancez la configuration.")
        except anthropic.RateLimitError:
            self.voice.say("Je suis un peu surchargé. Réessayez dans un instant.")
        except anthropic.APIStatusError as exc:
            print(f"[erreur API] {exc.status_code} : {exc.message}")
            self.voice.say("Un problème est survenu avec mes serveurs.")
        except anthropic.APIConnectionError:
            self.voice.say("Je n'arrive pas à joindre mes serveurs. Vérifiez la connexion Internet.")


def _init_ears(retry: bool = False):
    from .ears import Ears

    while True:
        try:
            return Ears()
        except Exception as exc:
            if not retry:
                print(f"Micro indisponible ({exc}). Passage en mode texte.")
                return None
            # Lancé en arrière-plan : pas de clavier, on attend que le micro soit prêt.
            print(f"Micro indisponible ({exc}). Nouvel essai dans 30 secondes.")
            time.sleep(30)


def _already_running() -> bool:
    """Un seul Jarvis à la fois : s'il tourne déjà, on lui demande juste d'afficher sa boule."""
    import json
    import urllib.request

    from .webui import PORT

    request = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/orbe/afficher", data=json.dumps({}).encode(),
                                     headers={"X-Jarvis": "1", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status == 200
    except OSError:
        return False


def try_effects(muted: bool) -> None:
    """Fait entendre chaque effet de voix, puis enregistre celui qu'on choisit."""
    from . import effects

    names = list(effects.PRESETS)
    voice = Voice(muted=muted)
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name} — {effects.PRESETS[name]}")
        config.save("effet", name)
        voice.say(f"Effet {name}. Bonjour, je suis Jarvis. Tous les systèmes sont opérationnels.")
        voice.wait()
    choice = input("\nNuméro de l'effet à garder (Entrée = aucun) : ").strip()
    chosen = names[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= len(names) else "aucun"
    config.save("effet", chosen)
    print(f"Effet enregistré : {chosen}")


def choose_voice_menu(muted: bool) -> None:
    """Menu interactif : écouter chaque voix et choisir celle de Jarvis."""
    names = list(voices.catalog())
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
        preview.voice = name
        preview.say(f"Bonjour, je suis Jarvis, avec la voix de {name}.")
        preview.wait()
        if input(f"Garder la voix de {name} ? (o/N) ").strip().lower() in ("o", "oui", "y"):
            voices.save_voice(name)
            print(f"C'est noté : Jarvis parlera avec la voix de {name}.")
            return


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS, ton assistant personnel.")
    setup = parser.add_argument_group("installation")
    setup.add_argument("--configurer", action="store_true", help="assistant de configuration pas à pas")
    setup.add_argument("--profil", action="store_true", help="ouvrir ton profil (« qui tu es ») pour le modifier")
    setup.add_argument("--connecter-google", nargs="?", const="", metavar="FICHIER_JSON",
                       help="relier Gmail et Google Agenda")
    setup.add_argument("--cle", metavar="CLE_API", help="enregistrer ta clé API Anthropic")
    setup.add_argument("--tester-cle", action="store_true", help="vérifier que la clé Claude fonctionne")
    setup.add_argument("--connecter-telegram-perso", action="store_true",
                       help="relier ton compte Telegram personnel (lire et envoyer tes messages)")
    setup.add_argument("--liste-audio", action="store_true", help="afficher les sorties audio et les micros")
    setup.add_argument("--sortie-audio", metavar="NOM",
                       help="où Jarvis parle (ex. « CABLE Input » pour Voicemod) ; « defaut » pour revenir aux haut-parleurs")
    setup.add_argument("--micro", metavar="NOM", help="micro utilisé par Jarvis ; « defaut » pour revenir au micro Windows")
    setup.add_argument("--dossier-musique", metavar="DOSSIER", help="dossier de ta musique locale")
    setup.add_argument("--elevenlabs", metavar="CLE", help="enregistrer ta clé ElevenLabs")
    setup.add_argument("--telegram", metavar="JETON", help="enregistrer le jeton de ton bot Telegram")
    setup.add_argument("--telegram-autoriser", metavar="ID", help="autoriser ton compte Telegram")
    setup.add_argument("--installer", action="store_true",
                       help="tout installer : icône sur le Bureau et le menu Démarrer, boule, lancement au démarrage")
    setup.add_argument("--raccourcis", action="store_true", help="créer l'icône Jarvis (Bureau + menu Démarrer)")
    setup.add_argument("--configurer-whatsapp", action="store_true", help="relier WhatsApp (voir README)")
    setup.add_argument("--installer-demarrage", action="store_true", help="lancer Jarvis à chaque démarrage")
    setup.add_argument("--retirer-demarrage", action="store_true", help="ne plus lancer Jarvis au démarrage")

    run = parser.add_argument_group("utilisation")
    run.add_argument("--orbe", action="store_true",
                     help="afficher la boule animée sur l'écran (mémorisé)")
    run.add_argument("--sans-orbe", action="store_true", help="ne plus afficher la boule (mémorisé)")
    run.add_argument("--interface", action="store_true", help="ouvrir l'interface dans le navigateur")
    run.add_argument("--sans-micro", action="store_true",
                     help="pas d'écoute au micro (interface, Telegram et WhatsApp seulement)")
    run.add_argument("--texte", action="store_true", help="écrire au clavier au lieu de parler")
    run.add_argument("--muet", action="store_true", help="ne pas lire les réponses à voix haute")
    run.add_argument("--toujours", action="store_true", help="répondre sans attendre « Jarvis »")
    run.add_argument("--voix", default=None, help="voix pour cette session (Daniel, Henri, Denise…)")
    run.add_argument("--effet", choices=["aucun", "ia", "droide", "tactique", "robot"],
                     help="effet sur la voix, sans Voicemod (mémorisé)")
    run.add_argument("--vitesse-voix", metavar="POURCENT", help="vitesse de la voix, ex. 10 ou -15 (mémorisé)")
    run.add_argument("--hauteur-voix", metavar="HZ", help="hauteur de la voix, ex. -20 (plus grave) ou 15 (mémorisé)")
    run.add_argument("--essayer-effets", action="store_true", help="écouter chaque effet de voix")
    run.add_argument("--choisir-voix", action="store_true", help="écouter les voix et choisir")
    run.add_argument("--liste-voix", action="store_true", help="afficher les voix disponibles")
    run.add_argument("--modele", choices=list(MODELS),
                     help="opus, sonnet (2x moins cher) ou haiku (4x moins cher) ; mémorisé")
    run.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"],
                     help="profondeur de réflexion (low = plus rapide) ; mémorisé")
    run.add_argument("--fond", action="store_true", help=argparse.SUPPRESS)  # lancement automatique
    args = parser.parse_args()

    if args.fond:
        log = open(config.LOG_PATH, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
        args.texte = False
        print(f"\n=== Démarrage de Jarvis {datetime.datetime.now():%Y-%m-%d %H:%M} ===")

    # --- réglages ponctuels ------------------------------------------------
    one_shot = False
    for flag, key in (("cle", "cle_api"), ("elevenlabs", "elevenlabs_cle"), ("telegram", "telegram_token"),
                      ("telegram_autoriser", "telegram_utilisateur"),
                      ("dossier_musique", "dossier_musique"),
                      ("sortie_audio", "sortie_audio"), ("micro", "micro"), ("modele", "modele"), ("effort", "effort"), ("effet", "effet"),
                      ("vitesse_voix", "vitesse_voix"), ("hauteur_voix", "hauteur_voix")):
        value = getattr(args, flag)
        if value:
            config.save(key, value.strip())
            print(f"Réglage « {key} » enregistré.")
            one_shot = one_shot or flag not in ("modele", "effort", "effet", "vitesse_voix", "hauteur_voix")
    for key in ("sortie_audio", "micro"):
        if (config.load().get(key) or "").lower() in ("defaut", "défaut", "default"):
            config.save(key, None)
    config.apply_api_key()

    if args.tester_cle or args.cle:
        from .keycheck import run as check_key

        check_key()
        return
    if args.configurer:
        from .setup_wizard import run as wizard

        return wizard()
    if args.profil:
        print(f"Profil ouvert : {profile.open_in_editor()}")
        return
    if args.connecter_google is not None:
        from .tools import google as google_tools

        google_tools.connect(args.connecter_google or None)
        print("Terminé ! Redémarre Jarvis pour qu'il utilise ses nouveaux outils Google.")
        return
    if args.configurer_whatsapp:
        from . import whatsapp

        return whatsapp.configure()
    if args.connecter_telegram_perso:
        return telegram_perso.connect_interactive()
    if args.installer or args.raccourcis:
        if args.installer:
            config.save("orbe", "oui")
        try:
            for path in autostart.create_shortcuts():
                print(f"Icône créée : {path}")
        except Exception as exc:
            print(f"Impossible de créer l'icône : {exc}")
        if args.installer:
            print(f"Lancement automatique au démarrage : {autostart.install()}")
            print("\nC'est installé ! Double-clique sur l'icône Jarvis du Bureau pour le lancer.")
        return
    if args.installer_demarrage:
        print(f"Jarvis se lancera tout seul à chaque démarrage ({autostart.install()}).")
        return
    if args.retirer_demarrage:
        path = autostart.uninstall()
        print(f"Lancement automatique retiré ({path})." if path else "Jarvis n'était pas au démarrage.")
        return
    if args.liste_audio:
        from .audio_devices import print_devices

        return print_devices()
    if args.essayer_effets:
        return try_effects(args.muet)
    if args.liste_voix:
        for name in voices.catalog():
            print(f"  {voices.describe(name)}")
        return
    if args.choisir_voix:
        return choose_voice_menu(args.muet)
    if one_shot:
        return

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Aucune clé API. Lance d'abord : python -m jarvis --configurer")
        return

    if args.orbe or args.sans_orbe:
        config.save("orbe", "oui" if args.orbe else "non")
    use_orb = config.get("orbe") == "oui"
    if use_orb and not orb.available():
        print("La boule a besoin de PySide6 : pip install -r requirements.txt")
        use_orb = False

    if _already_running():
        print("Jarvis tourne déjà : je fais réapparaître sa boule.")
        return

    profile.ensure()
    reminders.start()
    services.start(open_interface=args.interface)

    def assistant() -> None:
        if args.sans_micro:
            print("Jarvis tourne (interface, Telegram, WhatsApp). Ctrl+C pour arrêter.")
            threading.Event().wait()
        Jarvis(args).run()

    if not use_orb:
        try:
            assistant()
        except KeyboardInterrupt:
            pass
        return

    # La boule doit tourner dans le fil principal ; l'assistant tourne à côté.
    # « Au revoir » ou « Quitter » dans le menu de la boule arrêtent tout.
    def assistant_then_exit() -> None:
        try:
            assistant()
        finally:
            os._exit(0)

    threading.Thread(target=assistant_then_exit, daemon=True, name="assistant").start()
    orb.run(on_quit=lambda: os._exit(0))


if __name__ == "__main__":
    main()

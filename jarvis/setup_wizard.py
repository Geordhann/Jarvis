"""Assistant de configuration pas à pas : python -m jarvis --configurer"""

from __future__ import annotations

import getpass

from . import autostart, config, profile, voices
from .tools import media
from .tools import google as google_tools


def _ask(question: str, default: str | None = None, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    prompt = f"{question}{suffix} : "
    answer = (getpass.getpass(prompt) if secret else input(prompt)).strip()
    return answer or (default or "")


def _yes(question: str, default: bool = True) -> bool:
    answer = _ask(f"{question} (o/n)", "o" if default else "n").lower()
    return answer.startswith(("o", "y"))


def _title(text: str) -> None:
    print(f"\n━━━ {text} ━━━")


def run() -> None:
    print("Bienvenue ! Je vais configurer Jarvis étape par étape. Entrée = garder la valeur proposée.")

    _title("1. Cerveau (Claude)")
    print("Clé API sur https://console.anthropic.com/ → API Keys (le crédit se met dans Billing).")
    if config.load().get("cle_api") and not _yes("Une clé est déjà enregistrée. La changer ?", False):
        pass
    else:
        print("(La clé s'affiche en clair pour que tu vérifies le collage : ne fais pas de capture d'écran.)")
        key = _ask("Clé API Anthropic (sk-ant-…), clic droit pour coller")
        if key:
            config.save("cle_api", key)
            print("\033[2J\033[H", end="")  # efface l'écran : la clé ne reste pas affichée
            from .keycheck import run as check_key

            check_key()
    model = _ask("Modèle : opus (le plus intelligent), sonnet (2x moins cher), haiku (4x moins cher)",
                 config.get("modele", "opus"))
    config.save("modele", model)
    config.save("titre", _ask("Comment Jarvis doit-il t'appeler ?", config.get("titre", "Monsieur")))

    _title("2. Qui tu es")
    print("Jarvis lit un fichier « profil » à chaque conversation : ton métier, tes proches, tes habitudes…")
    if _yes("Ouvrir le profil pour le remplir maintenant ?"):
        path = profile.open_in_editor()
        print(f"Fichier : {path}. Enregistre-le puis reviens ici.")
        input("Appuie sur Entrée quand c'est fait…")

    _title("3. Voix (ElevenLabs)")
    print("Clé sur https://elevenlabs.io → Profile → API Keys. Sans clé, Jarvis garde la voix gratuite.")
    key = _ask("Clé ElevenLabs (Entrée pour passer)", secret=True)
    if key:
        config.save("elevenlabs_cle", key)
    print("Voix disponibles : " + ", ".join(voices.catalog()))
    voice = voices.find_voice(_ask("Voix de Jarvis", voices.load_saved_voice() or voices.default_voice()))
    if voice:
        voices.save_voice(voice)

    effect = _ask("Effet sur la voix : aucun, ia, droide, tactique, robot", config.get("effet", "aucun"))
    if effect in ("aucun", "ia", "droide", "tactique", "robot"):
        config.save("effet", effect)

    _title("4. Gmail et Google Agenda")
    if google_tools.is_connected():
        print("Déjà connecté.")
    elif _yes("Connecter Gmail et Google Agenda maintenant ? (suivre d'abord le README, étape Google)", False):
        client = _ask("Chemin du fichier JSON téléchargé depuis Google Cloud", str(google_tools.client_secret_path()))
        try:
            google_tools.connect(client if client != str(google_tools.client_secret_path()) else None)
            print("Google connecté ✔")
        except Exception as exc:
            print(f"Connexion impossible : {exc}")

    _title("5. SMS (téléphone Android)")
    if _yes("Configurer l'envoi de SMS ? (appli SMS Gateway sur ton Android, voir README)", False):
        from .tools import sms

        sms.configure()

    _title("6. Musique")
    folder = _ask("Dossier de ta musique sur l'ordinateur", str(media.music_dir()))
    config.save("dossier_musique", folder)
    print("Si un morceau n'y est pas, Jarvis le lance sur YouTube.")

    _title("7. Démarrage automatique")
    if _yes("Créer l'icône Jarvis sur le Bureau et dans le menu Démarrer ?"):
        try:
            for path in autostart.create_shortcuts():
                print(f"Icône créée : {path}")
        except Exception as exc:
            print(f"Impossible de créer l'icône : {exc}")
    if _yes("Afficher la boule animée sur l'écran ?"):
        config.save("orbe", "oui")
    if _yes("Lancer Jarvis automatiquement à chaque démarrage de l'ordinateur ?"):
        print(f"Installé : {autostart.install()}")

    print("\nTerminé ! Lance Jarvis avec : python -m jarvis")

"""Assistant de configuration pas à pas : python -m jarvis --configurer"""

from __future__ import annotations

import getpass
import secrets

from . import autostart, config, profile, telegram_perso, voices
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
        key = _ask("Clé API Anthropic (sk-ant-…)", secret=True)
        if key:
            config.save("cle_api", key)
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

    _title("5. Telegram")
    if _yes("Configurer Telegram ?", bool(config.get("telegram_token"))):
        print("Dans Telegram, écris à @BotFather → /newbot → choisis un nom → copie le jeton.")
        token = _ask("Jeton du bot", secret=True)
        if token:
            config.save("telegram_token", token)
        print("Lance Jarvis puis envoie /start à ton bot : il te donnera ton identifiant.")
        user = _ask("Ton identifiant Telegram (Entrée si tu ne l'as pas encore)", config.get("telegram_utilisateur"))
        if user:
            config.save("telegram_utilisateur", user)

    _title("6. WhatsApp")
    if _yes("Configurer WhatsApp ? (compte Meta développeur nécessaire, voir README)", bool(config.get("whatsapp_token"))):
        config.save("whatsapp_token", _ask("Jeton d'accès (permanent) de l'app Meta", secret=True)
                    or config.get("whatsapp_token"))
        config.save("whatsapp_numero_id", _ask("Identifiant du numéro de téléphone (Phone number ID)",
                                               config.get("whatsapp_numero_id")))
        config.save("whatsapp_secret_app", _ask("Clé secrète de l'app (App secret)", secret=True)
                    or config.get("whatsapp_secret_app"))
        config.save("whatsapp_mon_numero", _ask("TON numéro WhatsApp, format international (ex. 33612345678)",
                                                config.get("whatsapp_mon_numero")))
        verify = config.get("whatsapp_verification") or secrets.token_urlsafe(16)
        config.save("whatsapp_verification", verify)
        print(f"Dans Meta, URL du webhook : https://<ton-tunnel>/whatsapp — jeton de vérification : {verify}")

    _title("7. Tes messages Telegram personnels")
    print("Pour que Jarvis lise et envoie TES messages Telegram (pas seulement ceux du bot).")
    if _yes("Connecter ton compte Telegram perso ?", False):
        print("Sur https://my.telegram.org → API development tools : crée une app, note api_id et api_hash.")
        try:
            telegram_perso.connect_interactive()
        except Exception as exc:
            print(f"Connexion impossible : {exc}")

    _title("8. Musique")
    folder = _ask("Dossier de ta musique sur l'ordinateur", str(media.music_dir()))
    config.save("dossier_musique", folder)
    print("Si un morceau n'y est pas, Jarvis le lance sur YouTube.")

    _title("9. Démarrage automatique")
    if _yes("Lancer Jarvis automatiquement à chaque démarrage de l'ordinateur ?"):
        print(f"Installé : {autostart.install()}")

    print("\nTerminé ! Lance Jarvis avec : python -m jarvis")

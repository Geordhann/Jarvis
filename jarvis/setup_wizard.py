"""Assistant de configuration pas à pas : python -m jarvis --configurer (lancé par INSTALLER-JARVIS.bat)."""

from __future__ import annotations

import importlib.util
import os

from . import autostart, config, effects, personalities, profile, voices
from .tools import google as google_tools
from .tools import media


def _ask(question: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    return input(f"{question}{suffix} : ").strip() or (default or "")


def _yes(question: str, default: bool = True) -> bool:
    answer = _ask(f"{question} (o/n)", "o" if default else "n").lower()
    return answer.startswith(("o", "y"))


def _title(text: str) -> None:
    print(f"\n━━━ {text} ━━━")


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")  # une clé collée ne reste pas à l'écran


def _pick(names: list[str], question: str) -> str | None:
    """Liste numérotée ; renvoie le nom choisi, ou None (Entrée = par défaut de Windows)."""
    for i, name in enumerate(names, 1):
        print(f"  {i:2d}. {name}")
    while True:
        choice = _ask(f"{question} (numéro, Entrée = celui de Windows)")
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            return names[int(choice) - 1]
        print("Numéro invalide.")


def _say(text: str) -> None:
    from .voice import Voice

    voice = Voice()
    voice.say(text)
    voice.wait()


def run(choose_voice=None) -> None:
    print("Configuration de Jarvis, étape par étape. Entrée = garder la valeur proposée.")

    _title("1. Clé Claude")
    print("Clé sur https://console.anthropic.com/ → API Keys (crédit dans Billing).")
    change = not config.load().get("cle_api") or _yes("Une clé est déjà enregistrée. La changer ?", False)
    from .keycheck import run as check_key

    while True:
        if change:
            print("Clic droit pour coller. Ne fais pas de capture d'écran : l'écran sera effacé juste après.")
            key = _ask("Clé API (sk-ant-…)")
            if key:
                config.save("cle_api", key)
                _clear()
        config.apply_api_key()
        if check_key() or not _yes("La clé ne marche pas. Réessayer ?", True):
            break
        change = True
    config.save("titre", _ask("Comment Jarvis doit-il t'appeler ?", config.get("titre", "Monsieur")))

    _title("2. Haut-parleurs")
    from .audio_devices import input_names, output_names

    try:
        out = _pick(output_names(), "Où Jarvis doit parler")
        config.save("sortie_audio", out)
    except Exception as exc:
        print(f"Impossible de lister les sorties ({exc}) : sortie de Windows utilisée.")
    print("Test du son…")
    _say("Bonjour, je suis Jarvis. Est-ce que tu m'entends ?")
    if not _yes("Tu as entendu Jarvis ?"):
        print("Vérifie le volume, ou relance plus tard : python -m jarvis --configurer")

    _title("3. Micro")
    names = list(dict.fromkeys(input_names()))
    mic = _pick(names, "Micro à utiliser")
    config.save("micro", mic)

    _title("4. Voix")
    if choose_voice and _yes("Écouter les voix et en choisir une ?", True):
        choose_voice(False)
    for name, description in effects.PRESETS.items():
        print(f"  - {name} : {description}")
    effect = _ask("Effet sur la voix", config.get("effet", "aucun")).lower()
    if effect in effects.PRESETS:
        config.save("effet", effect)
        _say("Voici ma voix avec cet effet.")

    _title("5. Personnalité")
    for name, (_, description) in personalities.PERSONALITIES.items():
        print(f"  - {name} : {description}")
    choice = personalities.resolve(_ask("Personnalité", personalities.current()))
    if choice:
        config.save("personnalite", choice)

    _title("6. Options")
    config.save("bruitages", "oui" if _yes("Bruitages façon Iron Man ?", True) else "non")
    config.save("interruption", "oui" if _yes("Pouvoir le couper en disant « Jarvis, stop » ?", True) else "non")
    if importlib.util.find_spec("faster_whisper") and importlib.util.find_spec("openwakeword"):
        local = _yes("Écoute sur le PC (Whisper + « Hey Jarvis », rien n'est envoyé avant le mot d'éveil) ?", True)
        config.save("reconnaissance", "whisper" if local else "google")
        config.save("eveil_local", "oui" if local else "non")
    config.save("dossier_musique", _ask("Dossier de ta musique", str(media.music_dir())))

    _title("7. Google (Gmail, Agenda, Drive, YouTube…)")
    if google_tools.is_connected():
        print("Déjà connecté ✔")
    elif _yes("Connecter Google maintenant ? (il faut le fichier JSON, voir README)", False):
        path = _ask("Chemin du fichier JSON (glisse-le dans la fenêtre)").strip().strip('"')
        try:
            google_tools.connect(path or None)
            print("Google connecté ✔")
        except Exception as exc:
            print(f"Connexion impossible : {exc}. Plus tard : python -m jarvis --connecter-google")

    _title("8. Qui tu es (facultatif)")
    if _yes("Remplir ton profil (métier, proches, habitudes) maintenant ?", False):
        print(f"Fichier ouvert : {profile.open_in_editor()}")
        input("Enregistre-le, puis appuie sur Entrée…")

    _title("9. Icône et démarrage")
    config.save("orbe", "oui")
    try:
        for path in autostart.create_shortcuts():
            print(f"Icône créée : {path}")
    except Exception as exc:
        print(f"Impossible de créer l'icône : {exc}")
    if _yes("Lancer Jarvis automatiquement à chaque démarrage du PC ?", True):
        print(f"Installé : {autostart.install()}")
    else:
        autostart.uninstall()

    print("\n✔ Terminé ! Double-clique sur l'icône Jarvis du Bureau.")

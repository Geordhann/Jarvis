"""WhatsApp avec ton propre compte, via l'appli WhatsApp du PC (ou WhatsApp Web).

WhatsApp n'offre pas d'accès officiel aux comptes personnels, et les outils non officiels peuvent
faire bannir le numéro. Jarvis passe donc par l'appli : il l'ouvre, lit l'écran, prépare le message
dans la bonne conversation (lien officiel « send ») et n'appuie sur Entrée qu'après ton « oui ».
"""

from __future__ import annotations

import os
import re
import sys
import time
import webbrowser
from urllib.parse import quote

from . import Tool, ToolFailure, boolean, string


def _desktop_app() -> bool:
    """L'appli WhatsApp du PC est-elle installée (elle gère les liens whatsapp://) ?"""
    if sys.platform != "win32":
        return False
    import winreg

    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "whatsapp"))
        return True
    except OSError:
        return False


def _open(url_app: str, url_web: str) -> None:
    if _desktop_app():
        os.startfile(url_app)  # type: ignore[attr-defined]
    else:
        webbrowser.open(url_web)


def _number(numero: str) -> str:
    """« 06 12 34 56 78 » → « 33612345678 » (format international sans +)."""
    digits = re.sub(r"[^\d+]", "", numero)
    if digits.startswith("+"):
        digits = digits[1:]
    elif digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 10:
        digits = "33" + digits[1:]  # numéro français
    if not re.fullmatch(r"\d{8,15}", digits):
        raise ToolFailure(f"numéro invalide : « {numero} »")
    return digits


def _focus_whatsapp() -> bool:
    """Met la fenêtre WhatsApp au premier plan. Renvoie False si elle est introuvable."""
    if sys.platform != "win32":
        return False
    import pygetwindow

    windows = [w for w in pygetwindow.getAllWindows() if "whatsapp" in w.title.lower()]
    if not windows:
        return False
    window = windows[0]
    try:
        if window.isMinimized:
            window.restore()
        window.activate()
    except Exception:
        window.minimize()
        time.sleep(0.2)
        window.restore()
    return True


def _active_is_whatsapp() -> bool:
    if sys.platform != "win32":
        return False
    import pygetwindow

    active = pygetwindow.getActiveWindow()
    return bool(active and "whatsapp" in active.title.lower())


def whatsapp_lire():
    """Ouvre WhatsApp et renvoie une capture d'écran pour lire les discussions."""
    from .utilities import regarder_ecran

    if not _focus_whatsapp():
        _open("whatsapp:", "https://web.whatsapp.com/")
        time.sleep(5)
        _focus_whatsapp()
    time.sleep(1.5)
    shot = regarder_ecran()
    shot[-1]["text"] = ("Capture de WhatsApp. Résume les discussions visibles (qui a écrit, dernier message, "
                        "non lus). Si WhatsApp demande de scanner un QR code, dis à l'utilisateur de le "
                        "scanner avec son téléphone (WhatsApp → Appareils connectés).")
    return shot


def whatsapp_preparer(numero: str, message: str) -> str:
    """Ouvre la conversation et écrit le message, SANS l'envoyer."""
    if not message.strip():
        raise ToolFailure("message vide")
    phone, text = _number(numero), quote(message)
    _open(f"whatsapp://send?phone={phone}&text={text}",
          f"https://web.whatsapp.com/send?phone={phone}&text={text}")
    time.sleep(4)
    _focus_whatsapp()
    return ("Message écrit dans la conversation, pas encore envoyé. Relis-le à l'utilisateur et demande "
            "« Je l'envoie ? ». Après un oui explicite, appelle whatsapp_envoyer.")


def whatsapp_envoyer(confirme_par_utilisateur: bool) -> str:
    """Appuie sur Entrée dans WhatsApp pour envoyer le message préparé."""
    if not confirme_par_utilisateur:
        raise ToolFailure("Envoi refusé : demande d'abord « Je l'envoie ? » et attends un oui.")
    _focus_whatsapp()
    time.sleep(0.5)
    if not _active_is_whatsapp():
        raise ToolFailure("La fenêtre WhatsApp n'est pas au premier plan : je n'appuie pas sur Entrée "
                          "pour ne rien envoyer ailleurs. Demande à l'utilisateur de cliquer sur WhatsApp.")
    from pynput.keyboard import Controller, Key

    keyboard = Controller()
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    return "Message WhatsApp envoyé."


def tools() -> list[Tool]:
    return [
        Tool("whatsapp_lire",
             "Ouvre WhatsApp sur le PC et regarde l'écran pour lire les discussions (« j'ai des messages "
             "WhatsApp ? », « qu'est-ce que m'a écrit Paul ? »).", {}, whatsapp_lire),
        Tool("whatsapp_preparer",
             "Ouvre la conversation WhatsApp d'un numéro et y écrit le message, sans l'envoyer. Le numéro "
             "vient du profil, de la mémoire ou des contacts Google (contacts_chercher).",
             {"numero": string("numéro de téléphone, ex. 06 12 34 56 78 ou +33 6 12 34 56 78"),
              "message": string("texte exact du message")},
             whatsapp_preparer, ["numero", "message"]),
        Tool("whatsapp_envoyer",
             "Envoie le message préparé avec whatsapp_preparer (appuie sur Entrée dans WhatsApp). "
             "UNIQUEMENT après un oui explicite de l'utilisateur.",
             {"confirme_par_utilisateur": boolean("true uniquement après un oui explicite pour CET envoi")},
             whatsapp_envoyer, ["confirme_par_utilisateur"]),
    ]

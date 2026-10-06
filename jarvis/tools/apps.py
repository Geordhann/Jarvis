"""Contrôle des applications et des fenêtres : ouvrir, fermer, basculer, réduire, taper, raccourcis."""

from __future__ import annotations

import os
import re
import sys
import time
import unicodedata
from pathlib import Path

from . import Tool, ToolFailure, boolean, string


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


# --- Ouvrir ------------------------------------------------------------------

def _start_menu_shortcuts() -> list[Path]:
    """Raccourcis du menu Démarrer de Windows (c'est là que sont toutes les applis installées)."""
    roots = [Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
             Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Microsoft/Windows/Start Menu/Programs"]
    return [p for root in roots if root.is_dir() for p in root.rglob("*.lnk")]


def ouvrir_application(nom: str) -> str:
    if not re.fullmatch(r"[\w .+'-]{1,60}", nom):
        raise ToolFailure("nom d'application invalide")
    if sys.platform != "win32":
        from .media import ouvrir_application as open_elsewhere

        return open_elsewhere(nom)
    wanted = _plain(nom)
    shortcuts = _start_menu_shortcuts()
    # D'abord un nom identique, puis un nom qui contient la demande (« word » → « Word 2021 »).
    match = next((p for p in shortcuts if _plain(p.stem) == wanted), None) or \
        next((p for p in shortcuts if wanted in _plain(p.stem) and "uninstall" not in _plain(p.stem)
              and "desinstall" not in _plain(p.stem)), None)
    if match:
        os.startfile(match)  # type: ignore[attr-defined]
        return f"Application « {match.stem} » ouverte."
    # Applis intégrées (calc, notepad…) et applis du Microsoft Store connues par leur nom.
    import subprocess

    result = subprocess.run(["cmd", "/c", "start", "", nom], capture_output=True)
    if result.returncode != 0:
        raise ToolFailure(f"application « {nom} » introuvable dans le menu Démarrer")
    return f"Application « {nom} » lancée."


# --- Fenêtres (Windows) --------------------------------------------------------

def _windows():
    if sys.platform != "win32":
        raise ToolFailure("le contrôle des fenêtres n'est disponible que sous Windows")
    import pygetwindow

    return [w for w in pygetwindow.getAllWindows() if w.title.strip() and w.title != "Jarvis"]


def _find_window(titre: str):
    wanted = _plain(titre)
    matches = [w for w in _windows() if wanted in _plain(w.title)]
    if not matches:
        raise ToolFailure(f"aucune fenêtre ouverte ne correspond à « {titre} »")
    return matches[0]


def fenetres_lister() -> str:
    titles = list(dict.fromkeys(w.title for w in _windows()))
    return "\n".join(titles[:40]) or "Aucune fenêtre ouverte."


def fenetre_action(titre: str, action: str, confirme_par_utilisateur: bool = False) -> str:
    window = _find_window(titre)
    if action == "fermer" and not confirme_par_utilisateur:
        raise ToolFailure("Fermeture refusée : demande d'abord confirmation (un travail non enregistré "
                          "pourrait être perdu).")
    if action == "afficher":
        if window.isMinimized:
            window.restore()
        try:
            window.activate()
        except Exception:
            # Windows refuse parfois le premier plan : un minimiser/restaurer contourne le blocage.
            window.minimize()
            time.sleep(0.2)
            window.restore()
    elif action == "reduire":
        window.minimize()
    elif action == "agrandir":
        window.maximize()
    elif action == "restaurer":
        window.restore()
    elif action == "fermer":
        window.close()
    else:
        raise ToolFailure("action inconnue")
    return f"Fenêtre « {window.title} » : {action} fait."


def application_fermer(nom: str, confirme_par_utilisateur: bool) -> str:
    """Ferme complètement une application (tous ses processus)."""
    if not confirme_par_utilisateur:
        raise ToolFailure("Fermeture refusée : demande d'abord confirmation à l'utilisateur.")
    import psutil

    wanted = _plain(nom).replace(" ", "")
    protected = {"explorer.exe", "python.exe", "pythonw.exe", "svchost.exe", "csrss.exe", "winlogon.exe",
                 "system", "dwm.exe", "lsass.exe", "services.exe"}
    closed = set()
    for proc in psutil.process_iter(["name"]):
        name = (proc.info["name"] or "").lower()
        if name in protected or wanted not in _plain(name).replace(" ", ""):
            continue
        try:
            proc.terminate()
            closed.add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if not closed:
        raise ToolFailure(f"aucune application « {nom} » en cours")
    return f"Fermé : {', '.join(sorted(closed))}."


# --- Clavier -------------------------------------------------------------------

KEY_NAMES = {"ctrl": "ctrl", "control": "ctrl", "alt": "alt", "maj": "shift", "shift": "shift",
             "win": "cmd", "windows": "cmd", "cmd": "cmd", "entree": "enter", "enter": "enter",
             "echap": "esc", "esc": "esc", "tab": "tab", "espace": "space", "space": "space",
             "suppr": "delete", "retour": "backspace", "haut": "up", "bas": "down",
             "gauche": "left", "droite": "right", "debut": "home", "fin": "end"}


def raccourci_clavier(touches: str) -> str:
    """Appuie sur une combinaison, ex. « ctrl+s », « alt+tab », « win+d », « f5 »."""
    from pynput.keyboard import Controller, Key, KeyCode

    keyboard = Controller()
    keys = []
    for part in _plain(touches).replace(" ", "").split("+"):
        name = KEY_NAMES.get(part, part)
        if hasattr(Key, name):
            keys.append(getattr(Key, name))
        elif len(name) == 1:
            keys.append(KeyCode.from_char(name))
        else:
            raise ToolFailure(f"touche inconnue : {part}")
    for key in keys:
        keyboard.press(key)
    for key in reversed(keys):
        keyboard.release(key)
    return f"Raccourci {touches} envoyé."


def taper_texte(texte: str) -> str:
    """Tape un texte dans la fenêtre active (là où se trouve le curseur)."""
    from pynput.keyboard import Controller

    Controller().type(texte)
    return "Texte tapé dans la fenêtre active."


def tools() -> list[Tool]:
    confirm = boolean("true uniquement après un oui explicite de l'utilisateur pour CETTE action")
    return [
        Tool("ouvrir_application",
             "Ouvre une application installée (Spotify, Discord, Word, Chrome, Steam, Calculatrice…), "
             "en la cherchant dans le menu Démarrer.",
             {"nom": string("nom de l'application")}, ouvrir_application, ["nom"]),
        Tool("fenetres_lister", "Liste les fenêtres ouvertes sur l'ordinateur.", {}, fenetres_lister),
        Tool("fenetre_action",
             "Agit sur une fenêtre ouverte : la mettre au premier plan (afficher), la réduire, l'agrandir, "
             "la restaurer ou la fermer (fermer demande une confirmation explicite).",
             {"titre": string("tout ou partie du titre de la fenêtre, ex. « Discord », « Word »"),
              "action": {"type": "string", "enum": ["afficher", "reduire", "agrandir", "restaurer", "fermer"]},
              "confirme_par_utilisateur": confirm},
             fenetre_action, ["titre", "action"]),
        Tool("application_fermer",
             "Ferme complètement une application (ex. « ferme Discord »), après confirmation explicite.",
             {"nom": string("nom de l'application ou de son programme"), "confirme_par_utilisateur": confirm},
             application_fermer, ["nom", "confirme_par_utilisateur"]),
        Tool("raccourci_clavier",
             "Appuie sur un raccourci clavier dans l'application active : « ctrl+s » (enregistrer), "
             "« alt+tab », « win+d » (bureau), « ctrl+t » (nouvel onglet), « f5 »…",
             {"touches": string("touches séparées par +")}, raccourci_clavier, ["touches"]),
        Tool("taper_texte", "Tape un texte dans la fenêtre active, à l'emplacement du curseur.",
             {"texte": string("texte à taper")}, taper_texte, ["texte"]),
    ]

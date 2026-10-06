"""Les petits outils du quotidien : notes, rappels, météo, presse-papiers, dossiers, PC, écran."""

from __future__ import annotations

import base64
import datetime
import io
import re
import subprocess
import sys
from pathlib import Path

import requests

from .. import config, reminders
from . import Tool, ToolFailure, boolean, integer, string
from .media import _open

# --- Notes -------------------------------------------------------------------

def notes_dir() -> Path:
    folder = Path(config.get("dossier_notes") or Path.home() / "Jarvis Notes")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _note_file(titre: str) -> Path:
    name = re.sub(r'[<>:"/\\|?*\n\r\t]+', " ", titre).strip()[:80] or "Note"
    return notes_dir() / f"{name}.md"


def _find_note(titre: str) -> Path:
    exact = _note_file(titre)
    if exact.exists():
        return exact
    wanted = titre.lower()
    for path in sorted(notes_dir().glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        if wanted in path.stem.lower():
            return path
    raise ToolFailure(f"aucune note ne s'appelle « {titre} »")


def note_ecrire(titre: str, texte: str, ajouter: bool = True) -> str:
    """Crée une note, ou ajoute à la suite d'une note existante."""
    try:
        path = _find_note(titre)
    except ToolFailure:
        path = _note_file(titre)
    stamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    if path.exists() and ajouter:
        with path.open("a", encoding="utf-8") as f:
            f.write(f"\n\n— {stamp}\n{texte}")
        return f"Ajouté à la note « {path.stem} »."
    path.write_text(f"# {titre}\n\n— {stamp}\n{texte}\n", encoding="utf-8")
    return f"Note « {path.stem} » enregistrée dans {notes_dir()}."


def notes_lister(recherche: str = "") -> str:
    lines = []
    for path in sorted(notes_dir().glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = path.read_text(encoding="utf-8", errors="replace")
        if recherche and recherche.lower() not in (path.stem + text).lower():
            continue
        modified = datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y")
        lines.append(f"{path.stem} (modifiée le {modified})")
    return "\n".join(lines[:40]) or "Aucune note."


def note_lire(titre: str) -> str:
    text = _find_note(titre).read_text(encoding="utf-8", errors="replace")
    return text[:12000]


def note_supprimer(titre: str, confirme_par_utilisateur: bool) -> str:
    if not confirme_par_utilisateur:
        raise ToolFailure("Suppression refusée : demande d'abord confirmation à l'utilisateur.")
    path = _find_note(titre)
    path.unlink()
    return f"Note « {path.stem} » supprimée."


# --- Rappels -------------------------------------------------------------------

def rappel_ajouter(texte: str, dans_minutes: int | None = None, quand: str | None = None) -> str:
    if dans_minutes is not None:
        when = datetime.datetime.now() + datetime.timedelta(minutes=dans_minutes)
    elif quand:
        try:
            when = datetime.datetime.fromisoformat(quand)
        except ValueError as exc:
            raise ToolFailure("date invalide, format attendu AAAA-MM-JJTHH:MM") from exc
        when = when.replace(tzinfo=None)
    else:
        raise ToolFailure("indique dans_minutes ou quand")
    if when <= datetime.datetime.now():
        raise ToolFailure("ce moment est déjà passé")
    item = reminders.add(texte, when)
    return f"Rappel {item['id']} programmé le {when:%d/%m à %H:%M} : {texte}"


def rappels_lister() -> str:
    items = reminders.pending()
    return "\n".join(f"id={r['id']} | {datetime.datetime.fromisoformat(r['quand']):%d/%m %H:%M} | {r['texte']}"
                     for r in items) or "Aucun rappel programmé."


def rappel_supprimer(id: str) -> str:
    if not reminders.remove(id):
        raise ToolFailure("rappel introuvable")
    return "Rappel annulé."


# --- Météo (Open-Meteo : gratuit, sans clé) -----------------------------------

WEATHER = {0: "ciel dégagé", 1: "plutôt dégagé", 2: "partiellement nuageux", 3: "couvert", 45: "brouillard",
           48: "brouillard givrant", 51: "bruine légère", 53: "bruine", 55: "forte bruine", 61: "pluie faible",
           63: "pluie", 65: "forte pluie", 66: "pluie verglaçante", 67: "forte pluie verglaçante",
           71: "neige faible", 73: "neige", 75: "forte neige", 77: "grésil", 80: "averses",
           81: "averses", 82: "violentes averses", 85: "averses de neige", 86: "fortes averses de neige",
           95: "orage", 96: "orage avec grêle", 99: "violent orage avec grêle"}


def meteo(ville: str, jours: int = 3) -> str:
    geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                       params={"name": ville, "count": 1, "language": "fr"}, timeout=15).json()
    if not geo.get("results"):
        raise ToolFailure(f"ville « {ville} » introuvable")
    place = geo["results"][0]
    data = requests.get("https://api.open-meteo.com/v1/forecast", timeout=15, params={
        "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": max(1, min(jours, 7)),
    }).json()
    cur = data["current"]
    lines = [f"{place['name']} ({place.get('country', '')}) maintenant : {cur['temperature_2m']} °C "
             f"(ressenti {cur['apparent_temperature']} °C), {WEATHER.get(cur['weather_code'], 'temps variable')}, "
             f"vent {cur['wind_speed_10m']} km/h."]
    d = data["daily"]
    for i, day in enumerate(d["time"]):
        lines.append(f"{day} : {WEATHER.get(d['weather_code'][i], 'variable')}, "
                     f"{d['temperature_2m_min'][i]} à {d['temperature_2m_max'][i]} °C, "
                     f"pluie {d['precipitation_probability_max'][i]} %")
    return "\n".join(lines)


# --- Presse-papiers ----------------------------------------------------------

def presse_papiers_lire() -> str:
    import pyperclip

    text = pyperclip.paste() or ""
    return text[:12000] or "Le presse-papiers est vide (ou contient une image)."


def presse_papiers_ecrire(texte: str) -> str:
    import pyperclip

    pyperclip.copy(texte)
    return "Texte copié : l'utilisateur peut le coller avec Ctrl+V."


# --- Dossiers ------------------------------------------------------------------

def _known_folders() -> dict[str, Path]:
    home = Path.home()
    folders = {"telechargements": home / "Downloads", "documents": home / "Documents",
               "bureau": home / "Desktop", "images": home / "Pictures", "musique": home / "Music",
               "videos": home / "Videos", "notes": notes_dir()}
    onedrive = home / "OneDrive"
    for key, names in (("documents", ("Documents", "Dokumente")), ("bureau", ("Desktop", "Bureau")),
                       ("images", ("Pictures", "Images", "Bilder"))):
        for name in names:
            if (onedrive / name).is_dir():
                folders[key] = onedrive / name
    return folders


FOLDER_ALIASES = {"telechargements": "telechargements", "telechargement": "telechargements",
                  "downloads": "telechargements", "documents": "documents", "document": "documents",
                  "bureau": "bureau", "desktop": "bureau", "images": "images", "photos": "images",
                  "musique": "musique", "musiques": "musique", "videos": "videos", "video": "videos",
                  "notes": "notes"}


def ouvrir_dossier(nom: str) -> str:
    import unicodedata

    plain = "".join(c for c in unicodedata.normalize("NFD", nom.lower()) if unicodedata.category(c) != "Mn")
    key = next((v for word in re.findall(r"\w+", plain) for k, v in FOLDER_ALIASES.items() if word == k), None)
    folders = _known_folders()
    target = folders.get(key) if key else None
    if target is None or not target.exists():
        raise ToolFailure(f"dossier inconnu, choisir parmi : {', '.join(folders)}")
    _open(str(target))
    return f"Dossier ouvert : {target}"


# --- PC ------------------------------------------------------------------------

def infos_systeme() -> str:
    import psutil

    parts = [f"processeur {psutil.cpu_percent(interval=0.5):.0f} %",
             f"mémoire {psutil.virtual_memory().percent:.0f} %",
             f"disque {psutil.disk_usage(str(Path.home().anchor or '/')).percent:.0f} % plein"]
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery:
        parts.append(f"batterie {battery.percent:.0f} %" + (" (en charge)" if battery.power_plugged else ""))
    boot = datetime.datetime.fromtimestamp(psutil.boot_time())
    parts.append(f"allumé depuis le {boot:%d/%m à %H:%M}")
    return ", ".join(parts)


def controle_pc(action: str, confirme_par_utilisateur: bool = False) -> str:
    risky = action in ("eteindre", "redemarrer")
    if risky and not confirme_par_utilisateur:
        raise ToolFailure("Action refusée : demande d'abord confirmation à l'utilisateur.")
    win = sys.platform == "win32"
    commands = {
        "verrouiller": ["rundll32.exe", "user32.dll,LockWorkStation"] if win else
                       (["pmset", "displaysleepnow"] if sys.platform == "darwin" else ["loginctl", "lock-session"]),
        "veille": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"] if win else
                  (["pmset", "sleepnow"] if sys.platform == "darwin" else ["systemctl", "suspend"]),
        "eteindre": ["shutdown", "/s", "/t", "60"] if win else ["shutdown", "-h", "+1"],
        "redemarrer": ["shutdown", "/r", "/t", "60"] if win else ["shutdown", "-r", "+1"],
        "annuler_arret": ["shutdown", "/a"] if win else ["shutdown", "-c"],
    }
    if action not in commands:
        raise ToolFailure(f"action inconnue, choisir parmi : {', '.join(commands)}")
    subprocess.Popen(commands[action], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if risky:
        return f"{action} dans une minute. Dire « annule l'arrêt » pour l'empêcher."
    return f"Action « {action} » lancée."


def regarder_ecran():
    """Capture l'écran et la renvoie à Claude (image) pour qu'il la décrive ou l'analyse."""
    import mss
    from PIL import Image

    with mss.mss() as screen:
        shot = screen.grab(screen.monitors[1])  # écran principal
        image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    image.thumbnail((1568, 1568))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.b64encode(buffer.getvalue()).decode()}},
        {"type": "text", "text": "Capture de l'écran principal de l'utilisateur."},
    ]


def tools() -> list[Tool]:
    confirm = boolean("true uniquement après un oui explicite de l'utilisateur pour CETTE action")
    return [
        Tool("note_ecrire", "Écrit une note dans le carnet de Jarvis (dossier « Jarvis Notes »). Si une note du "
             "même titre existe, ajoute le texte à la suite (liste de courses, idées, compte rendu…).",
             {"titre": string("titre court, ex. « Courses », « Idées projet »"), "texte": string("contenu"),
              "ajouter": boolean("false pour remplacer entièrement la note existante")},
             note_ecrire, ["titre", "texte"]),
        Tool("notes_lister", "Liste les notes du carnet, éventuellement filtrées par un mot.",
             {"recherche": string("mot à chercher (optionnel)")}, notes_lister),
        Tool("note_lire", "Lit une note du carnet.", {"titre": string("titre ou partie du titre")},
             note_lire, ["titre"]),
        Tool("note_supprimer", "Supprime une note, après confirmation explicite.",
             {"titre": string("titre de la note"), "confirme_par_utilisateur": confirm},
             note_supprimer, ["titre", "confirme_par_utilisateur"]),
        Tool("rappel_ajouter", "Programme un rappel ou un minuteur : Jarvis le dira à voix haute (et sur "
             "Telegram) au bon moment. « dans 10 minutes » → dans_minutes ; « demain à 9 h » → quand.",
             {"texte": string("ce qu'il faut rappeler"), "dans_minutes": integer("délai en minutes"),
              "quand": string("date et heure locales AAAA-MM-JJTHH:MM")},
             rappel_ajouter, ["texte"]),
        Tool("rappels_lister", "Liste les rappels et minuteurs programmés.", {}, rappels_lister),
        Tool("rappel_supprimer", "Annule un rappel.", {"id": string("id renvoyé par rappels_lister")},
             rappel_supprimer, ["id"]),
        Tool("meteo", "Météo actuelle et prévisions (jusqu'à 7 jours) pour une ville. Plus rapide et précis "
             "qu'une recherche web pour la météo.",
             {"ville": string("nom de la ville"), "jours": integer("nombre de jours (défaut 3)")},
             meteo, ["ville"]),
        Tool("presse_papiers_lire", "Lit le texte copié par l'utilisateur (Ctrl+C) : « résume ce que j'ai "
             "copié », « traduis ça »…", {}, presse_papiers_lire),
        Tool("presse_papiers_ecrire", "Copie un texte dans le presse-papiers pour que l'utilisateur le colle.",
             {"texte": string("texte à copier")}, presse_papiers_ecrire, ["texte"]),
        Tool("ouvrir_dossier", "Ouvre un dossier dans l'explorateur : téléchargements, documents, bureau, "
             "images, musique, vidéos, notes.", {"nom": string("nom du dossier")}, ouvrir_dossier, ["nom"]),
        Tool("infos_systeme", "État du PC : processeur, mémoire, disque, batterie, allumé depuis quand.",
             {}, infos_systeme),
        Tool("controle_pc", "Verrouille l'écran, met en veille, éteint ou redémarre le PC (dans une minute, "
             "annulable). Éteindre et redémarrer demandent une confirmation explicite.",
             {"action": {"type": "string",
                         "enum": ["verrouiller", "veille", "eteindre", "redemarrer", "annuler_arret"]},
              "confirme_par_utilisateur": confirm},
             controle_pc, ["action"]),
        Tool("regarder_ecran", "Regarde l'écran de l'utilisateur (capture envoyée à Claude). UNIQUEMENT quand "
             "il le demande (« regarde mon écran », « c'est quoi cette erreur ? »).", {}, regarder_ecran),
    ]

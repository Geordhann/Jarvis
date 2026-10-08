"""Contrôle du téléphone Android (Poco, Xiaomi…) depuis le PC, par le débogage sans fil d'Android (ADB).

Connexion une fois : python -m jarvis --connecter-telephone (voir README, section « Contrôler ton
téléphone »). Jarvis peut ensuite ouvrir des applis, lire l'écran et les notifications, toucher,
glisser, écrire, régler le volume et appeler (après confirmation).
"""

from __future__ import annotations

import base64
import io
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

from .. import config
from . import Tool, ToolFailure, boolean, integer, string

PLATFORM_TOOLS = {
    "win32": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    "linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
}
# Applis courantes : nom dit à voix haute → paquet Android.
APPS = {
    "whatsapp": "com.whatsapp", "instagram": "com.instagram.android", "insta": "com.instagram.android",
    "snapchat": "com.snapchat.android", "snap": "com.snapchat.android", "spotify": "com.spotify.music",
    "youtube": "com.google.android.youtube", "chrome": "com.android.chrome", "brave": "com.brave.browser",
    "gmail": "com.google.android.gm", "maps": "com.google.android.apps.maps",
    "google maps": "com.google.android.apps.maps", "tiktok": "com.zhiliaoapp.musically",
    "discord": "com.discord", "netflix": "com.netflix.mediaclient", "telegram": "org.telegram.messenger",
    "messenger": "com.facebook.orca", "facebook": "com.facebook.katana", "x": "com.twitter.android",
    "twitter": "com.twitter.android", "twitch": "tv.twitch.android.app", "waze": "com.waze",
    "appareil photo": "com.android.camera", "camera": "com.android.camera", "galerie": "com.miui.gallery",
    "photos": "com.google.android.apps.photos", "parametres": "com.android.settings",
    "reglages": "com.android.settings", "messages": "com.google.android.apps.messaging",
    "telephone": "com.google.android.dialer", "horloge": "com.android.deskclock",
    "calculatrice": "com.miui.calculator", "play store": "com.android.vending", "agenda": "com.google.android.calendar",
}
KEYS = {
    "retour": "KEYCODE_BACK", "accueil": "KEYCODE_HOME", "applis_recentes": "KEYCODE_APP_SWITCH",
    "volume_plus": "KEYCODE_VOLUME_UP", "volume_moins": "KEYCODE_VOLUME_DOWN", "muet": "KEYCODE_VOLUME_MUTE",
    "lecture_pause": "KEYCODE_MEDIA_PLAY_PAUSE", "suivant": "KEYCODE_MEDIA_NEXT",
    "precedent": "KEYCODE_MEDIA_PREVIOUS", "verrouiller": "KEYCODE_SLEEP", "reveiller": "KEYCODE_WAKEUP",
    "entree": "KEYCODE_ENTER", "effacer": "KEYCODE_DEL",
}
_scale = 1.0  # taille réelle de l'écran / taille de la capture envoyée à Claude


# --- ADB ---------------------------------------------------------------------

def adb_path() -> str | None:
    local = config.data_dir() / "platform-tools" / ("adb.exe" if sys.platform == "win32" else "adb")
    return str(local) if local.exists() else shutil.which("adb")


def install_adb() -> str:
    """Télécharge les outils officiels de Google (platform-tools) dans ~/.jarvis."""
    import requests

    url = PLATFORM_TOOLS.get(sys.platform, PLATFORM_TOOLS["linux"])
    print("Téléchargement des outils Android de Google (environ 7 Mo)…")
    data = requests.get(url, timeout=120).content
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        archive.extractall(config.data_dir())
    path = adb_path()
    if not path:
        raise RuntimeError("adb introuvable après téléchargement")
    if sys.platform != "win32":
        Path(path).chmod(0o755)
    return path


def _adb(*args: str, timeout: float = 20, binary: bool = False):
    exe = adb_path()
    if not exe:
        raise ToolFailure("le téléphone n'est pas connecté : lancer « python -m jarvis --connecter-telephone »")
    serial = config.get("telephone_adb")
    command = [exe, *(["-s", serial] if serial and args[:1] not in (("pair",), ("connect",), ("mdns",),
                                                                  ("devices",)) else []), *args]
    result = subprocess.run(command, capture_output=True, timeout=timeout,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if binary:
        return result.stdout
    return (result.stdout + result.stderr).decode("utf-8", "replace").strip()


def _connected() -> bool:
    serial = config.get("telephone_adb")
    out = _adb("devices")
    return bool(serial) and any(line.startswith(serial) and line.endswith("device") for line in out.splitlines())


def _reconnect() -> None:
    """Le port du débogage sans fil change après un redémarrage : on le retrouve tout seul (mDNS)."""
    if _connected():
        return
    for line in _adb("mdns", "services").splitlines():
        match = re.search(r"_adb-tls-connect\._tcp\.?\s+(\d+\.\d+\.\d+\.\d+:\d+)", line)
        if match:
            _adb("connect", match.group(1))
            config.save("telephone_adb", match.group(1))
            if _connected():
                return
    serial = config.get("telephone_adb")
    if serial:
        _adb("connect", serial)
    if not _connected():
        raise ToolFailure("téléphone injoignable : il doit être allumé, sur le même Wi-Fi que le PC, avec le "
                          "« débogage sans fil » activé (Options développeur)")


def _shell(*args: str, timeout: float = 20) -> str:
    _reconnect()
    return _adb("shell", *args, timeout=timeout)


def connect() -> None:
    """Assistant : télécharge adb, associe le téléphone (code à 6 chiffres) et s'y connecte."""
    if not adb_path():
        install_adb()
    print("""
Sur le téléphone (une seule fois) :
  1. Paramètres → À propos du téléphone → touche 7 fois « Version de HyperOS » (ou MIUI)
     → « Vous êtes maintenant développeur ».
  2. Paramètres → Paramètres supplémentaires → Options pour les développeurs :
     - active « Débogage USB » et « Débogage USB (paramètres de sécurité) » (Xiaomi : nécessaire pour
       que Jarvis puisse toucher l'écran ; il faut être connecté au compte Xiaomi) ;
     - active « Débogage sans fil » (le téléphone et le PC doivent être sur le même Wi-Fi).
  3. Touche « Débogage sans fil » → « Associer l'appareil avec un code d'association ».
""")
    pair = input("Adresse IP et port affichés sous le code (ex. 192.168.1.20:37123) : ").strip()
    code = input("Code d'association à 6 chiffres : ").strip()
    print(_adb("pair", pair, code, timeout=30))
    print("\nSur l'écran « Débogage sans fil », regarde « Adresse IP et port » (en haut, port différent).")
    address = input("Adresse IP et port de connexion : ").strip()
    print(_adb("connect", address, timeout=30))
    config.save("telephone_adb", address)
    if not _connected():
        print("✘ Connexion impossible. Vérifie le Wi-Fi et que le débogage sans fil est toujours activé.")
        return
    model = _adb("shell", "getprop", "ro.product.model")
    print(f"✔ Téléphone connecté : {model}. Redémarre Jarvis.")
    print("Le téléphone peut demander « Autoriser le débogage ? » : coche « Toujours autoriser » puis OK.")


def is_configured() -> bool:
    return bool(config.get("telephone_adb")) and adb_path() is not None


# --- outils ----------------------------------------------------------------------

def telephone_ecran():
    """Capture l'écran du téléphone et l'envoie à Claude (coordonnées en pixels de la capture)."""
    global _scale
    from PIL import Image

    _reconnect()
    png = _adb("exec-out", "screencap", "-p", binary=True, timeout=30)
    if not png.startswith(b"\x89PNG"):
        raise ToolFailure("capture impossible (écran verrouillé ou protégé ?)")
    image = Image.open(io.BytesIO(png)).convert("RGB")
    width = image.width
    image.thumbnail((720, 1600))
    _scale = width / image.width
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.b64encode(buffer.getvalue()).decode()}},
        {"type": "text", "text": f"Écran du téléphone ({image.width}×{image.height} px). Pour toucher, donne les "
                                 "coordonnées x, y dans CETTE image."},
    ]


def _app_label(package: str) -> str:
    names = {v: k for k, v in APPS.items()}
    if package in names:
        return names[package]
    parts = package.split(".")
    return parts[-2] if parts[-1] in ("android", "app", "katana", "orca", "music") and len(parts) > 1 else parts[-1]


def telephone_notifications() -> str:
    """Dernières notifications du téléphone (messages reçus, appels manqués…)."""
    raw = _shell("dumpsys", "notification", "--noredact", timeout=30)
    found, app, current = [], "", None
    for line in raw.splitlines():
        line = line.strip()
        pkg = re.match(r"NotificationRecord\(.*pkg=(\S+)", line)
        if pkg:
            app, current = pkg.group(1), None
            continue
        field = re.match(r"android\.(title|text|bigText)=(?:\S+ \((.*)\)|(.*))$", line)
        if not field:
            continue
        value = (field.group(2) if field.group(2) is not None else field.group(3) or "").strip()
        if not value or value == "null":
            continue
        if field.group(1) == "title":
            current = f"[{_app_label(app)}] {value}"
            found.append(current)
        elif current and found and found[-1] == current:
            found[-1] = current = f"{current} : {value}"
    unique = list(dict.fromkeys(found))
    return "\n".join(unique[:30]) or "Aucune notification."


def telephone_infos() -> str:
    battery = _shell("dumpsys", "battery")
    level = re.search(r"level: (\d+)", battery)
    plugged = re.search(r"(AC|USB|Wireless) powered: true", battery)
    model = _shell("getprop", "ro.product.model")
    power = _shell("dumpsys", "power")
    screen = "allumé" if "mWakefulness=Awake" in power or "Display Power: state=ON" in power else "éteint"
    return (f"{model} : batterie {level.group(1) if level else '?'} %"
            f"{' (en charge)' if plugged else ''}, écran {screen}.")


def telephone_ouvrir_app(nom: str) -> str:
    plain = "".join(c for c in unicodedata.normalize("NFD", nom.lower()) if unicodedata.category(c) != "Mn").strip()
    package = APPS.get(plain)
    if not package:
        packages = [p.removeprefix("package:") for p in _shell("pm", "list", "packages").splitlines()]
        words = plain.replace(" ", "")
        package = next((p for p in packages if words in p.replace(".", "").replace("_", "")), None)
    if not package or not re.fullmatch(r"[\w.]+", package):
        raise ToolFailure(f"appli « {nom} » introuvable sur le téléphone")
    _shell("input", "keyevent", "KEYCODE_WAKEUP")
    out = _shell("monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
    if "No activities found" in out or "Error" in out:
        raise ToolFailure(f"impossible d'ouvrir {package}")
    return f"« {nom} » ouvert sur le téléphone."


def telephone_ouvrir_lien(url: str) -> str:
    if not re.match(r"https?://[^\s'\"]+$", url):
        raise ToolFailure("adresse invalide (http ou https)")
    _shell("am", "start", "-a", "android.intent.action.VIEW", "-d", f"'{url}'")
    return "Lien ouvert sur le téléphone."


def telephone_toucher(x: int, y: int) -> str:
    _shell("input", "tap", str(int(x * _scale)), str(int(y * _scale)))
    return "Touché. Regarde l'écran à nouveau si tu dois vérifier le résultat."


def telephone_glisser(x1: int, y1: int, x2: int, y2: int) -> str:
    coords = [str(int(v * _scale)) for v in (x1, y1, x2, y2)]
    _shell("input", "swipe", *coords, "300")
    return "Glissé."


def telephone_ecrire(texte: str) -> str:
    """Écrit dans le champ sélectionné (ne l'envoie pas)."""
    # La saisie par ADB ne connaît pas les accents : « é » devient « e ».
    plain = "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")
    plain = plain.encode("ascii", "ignore").decode()
    escaped = re.sub(r"([\\\"'`$&|;<>()*?!#~%])", r"\\\1", plain).replace(" ", "%s")
    _shell("input", "text", escaped)
    note = " (sans les accents)" if plain != texte else ""
    return f"Texte écrit{note}. Il n'est pas envoyé."


def telephone_touche(touche: str, envoyer_confirme: bool = False) -> str:
    if touche not in KEYS:
        raise ToolFailure(f"touche inconnue : {', '.join(KEYS)}")
    if touche == "entree" and not envoyer_confirme:
        raise ToolFailure("Entrée peut envoyer un message : demande d'abord l'accord de l'utilisateur.")
    _shell("input", "keyevent", KEYS[touche])
    return f"Touche {touche} envoyée au téléphone."


def telephone_appeler(numero: str, confirme_par_utilisateur: bool) -> str:
    if not confirme_par_utilisateur:
        raise ToolFailure("Appel refusé : demande d'abord « J'appelle … ? » et attends un oui.")
    number = re.sub(r"[^\d+]", "", numero)
    if not re.fullmatch(r"\+?\d{3,15}", number):
        raise ToolFailure("numéro invalide")
    _shell("input", "keyevent", "KEYCODE_WAKEUP")
    _shell("am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{number}")
    return f"Appel lancé vers {numero} depuis le téléphone."


def telephone_raccrocher() -> str:
    _shell("input", "keyevent", "KEYCODE_ENDCALL")
    return "Appel terminé."


def tools() -> list[Tool]:
    if not config.get("telephone_adb"):
        return []
    confirm = boolean("true uniquement après un oui explicite de l'utilisateur pour CETTE action")
    xy = {"x": integer("x dans la dernière capture de telephone_ecran"),
          "y": integer("y dans la dernière capture de telephone_ecran")}
    return [
        Tool("telephone_ecran", "Regarde l'écran du téléphone Android de l'utilisateur (capture). À utiliser "
             "avant de toucher l'écran, et après pour vérifier.", {}, telephone_ecran),
        Tool("telephone_notifications", "Lit les notifications du téléphone : messages reçus (WhatsApp, Snap, "
             "Insta, SMS…), appels manqués, mails.", {}, telephone_notifications),
        Tool("telephone_infos", "Batterie, charge et état de l'écran du téléphone.", {}, telephone_infos),
        Tool("telephone_ouvrir_app", "Ouvre une appli sur le téléphone (WhatsApp, Spotify, Insta, Snap, YouTube, "
             "Maps, appareil photo, paramètres…).", {"nom": string("nom de l'appli")}, telephone_ouvrir_app, ["nom"]),
        Tool("telephone_ouvrir_lien", "Ouvre une adresse web ou un lien d'itinéraire sur le téléphone.",
             {"url": string("adresse http(s)")}, telephone_ouvrir_lien, ["url"]),
        Tool("telephone_toucher", "Touche l'écran du téléphone à un endroit vu sur la dernière capture.",
             xy, telephone_toucher, ["x", "y"]),
        Tool("telephone_glisser", "Fait glisser le doigt sur l'écran du téléphone (défiler, balayer).",
             {"x1": integer("départ x"), "y1": integer("départ y"), "x2": integer("arrivée x"),
              "y2": integer("arrivée y")}, telephone_glisser, ["x1", "y1", "x2", "y2"]),
        Tool("telephone_ecrire", "Écrit un texte dans le champ sélectionné du téléphone, sans l'envoyer.",
             {"texte": string("texte à écrire")}, telephone_ecrire, ["texte"]),
        Tool("telephone_touche", "Appuie sur une touche du téléphone : retour, accueil, applis_recentes, "
             "volume_plus, volume_moins, muet, lecture_pause, suivant, precedent, verrouiller, reveiller, "
             "effacer, entree (entree peut envoyer : accord obligatoire).",
             {"touche": {"type": "string", "enum": list(KEYS)},
              "envoyer_confirme": boolean("pour entree : true seulement après un oui explicite")},
             telephone_touche, ["touche"]),
        Tool("telephone_appeler", "Appelle un numéro depuis le téléphone, après un oui explicite.",
             {"numero": string("numéro de téléphone"), "confirme_par_utilisateur": confirm},
             telephone_appeler, ["numero", "confirme_par_utilisateur"]),
        Tool("telephone_raccrocher", "Raccroche l'appel en cours sur le téléphone.", {}, telephone_raccrocher),
    ]

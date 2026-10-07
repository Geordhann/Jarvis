"""Jeux Steam : lancer un jeu installé par son nom (« Jarvis, lance Rocket League »)."""

from __future__ import annotations

import difflib
import os
import re
import sys
import unicodedata
from pathlib import Path

from . import Tool, ToolFailure, string


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def steam_dir() -> Path | None:
    candidates = []
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                candidates.append(Path(winreg.QueryValueEx(key, "SteamPath")[0]))
        except OSError:
            pass
        candidates += [Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Steam",
                       Path(r"C:\Program Files\Steam")]
    else:
        candidates += [Path.home() / ".steam/steam", Path.home() / ".local/share/Steam",
                       Path.home() / "Library/Application Support/Steam"]
    return next((p for p in candidates if (p / "steamapps").is_dir()), None)


def installed_games() -> dict[str, str]:
    """{nom du jeu: appid} pour tous les jeux installés, toutes bibliothèques confondues."""
    root = steam_dir()
    if root is None:
        return {}
    libraries = {root}
    vdf = root / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        for path in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="replace")):
            libraries.add(Path(path.replace("\\\\", "\\")))
    games = {}
    for library in libraries:
        for manifest in (library / "steamapps").glob("appmanifest_*.acf"):
            text = manifest.read_text(encoding="utf-8", errors="replace")
            appid, name = re.search(r'"appid"\s+"(\d+)"', text), re.search(r'"name"\s+"([^"]+)"', text)
            if appid and name and "redistributable" not in name.group(1).lower() \
                    and not name.group(1).lower().startswith("steamworks"):
                games[name.group(1)] = appid.group(1)
    return games


ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def _aliases(game: str) -> set[str]:
    """« Grand Theft Auto V » → « grand theft auto v », « grand theft auto 5 », « gta 5 », « gta v », « gta »."""
    words = _plain(game).split()
    digits = [ROMAN.get(w, w) for w in words]
    names = {" ".join(words), " ".join(digits)}
    core = [w for w in words if w not in ROMAN and not w.isdigit()]
    tail = [w for w in digits if w.isdigit()]
    if len(core) >= 2:
        acronym = "".join(w[0] for w in core)
        names |= {acronym, " ".join([acronym, *tail]), acronym + "".join(tail)}
    return names


def find_game(name: str) -> tuple[str, str] | None:
    games = installed_games()
    if not games:
        return None
    wanted = _plain(name)
    plain = {alias: g for g in games for alias in _aliases(g)}
    if wanted in plain:
        game = plain[wanted]
    else:
        # Correspondance partielle par mots entiers seulement (« rl » ne doit pas matcher « world »).
        contains = [g for p, g in plain.items()
                    if (len(p) >= 4 and re.search(rf"\b{re.escape(p)}\b", wanted))
                    or (len(wanted) >= 4 and re.search(rf"\b{re.escape(wanted)}\b", p))]
        close = difflib.get_close_matches(wanted, list(plain), n=1, cutoff=0.6)
        game = contains[0] if contains else (plain[close[0]] if close else None)
    return (game, games[game]) if game else None


def lancer_jeu(nom: str) -> str:
    if steam_dir() is None:
        raise ToolFailure("Steam n'est pas installé sur cet ordinateur (ou introuvable).")
    found = find_game(nom)
    if not found:
        raise ToolFailure(f"aucun jeu Steam installé ne ressemble à « {nom} ». Utilise jeux_lister.")
    game, appid = found
    url = f"steam://rungameid/{appid}"
    if sys.platform == "win32":
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        import subprocess
        import webbrowser

        if not webbrowser.open(url):
            subprocess.Popen(["steam", url])
    return f"Lancement de {game} via Steam."


def jeux_lister() -> str:
    games = sorted(installed_games())
    return ", ".join(games) if games else "Aucun jeu Steam installé trouvé."


def tools() -> list[Tool]:
    return [
        Tool("lancer_jeu", "Lance un jeu Steam installé à partir de son nom (même approximatif).",
             {"nom": string("nom du jeu, ex. « rocket league », « gta »")}, lancer_jeu, ["nom"]),
        Tool("jeux_lister", "Liste les jeux Steam installés sur l'ordinateur.", {}, jeux_lister),
    ]

"""Mode gaming : notifications coupées, PC en performances maximales, applis lourdes fermées.
Tout est remis comme avant quand on quitte le mode (« Jarvis, fin du mode gaming »)."""

from __future__ import annotations

import json
import re
import subprocess
import sys

from .. import config
from . import Tool, ToolFailure, boolean, string

HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
TOASTS_KEY = r"Software\Microsoft\Windows\CurrentVersion\PushNotifications"
SAVED = "gaming.json"  # réglages d'avant, pour tout remettre en sortant du mode


def _saved_path():
    return config.data_dir() / SAVED


def _run(*command: str) -> str:
    return subprocess.run(command, capture_output=True, text=True, errors="replace",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout


def _power_scheme() -> str | None:
    match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", _run("powercfg", "/getactivescheme"))
    return match.group(0) if match else None


def _toasts(enabled: bool | None = None) -> bool | None:
    """Lit (ou règle) les notifications Windows. Renvoie l'état d'avant."""
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, TOASTS_KEY) as key:
        try:
            before = bool(winreg.QueryValueEx(key, "ToastEnabled")[0])
        except OSError:
            before = True
        if enabled is not None:
            winreg.SetValueEx(key, "ToastEnabled", 0, winreg.REG_DWORD, int(enabled))
    return before


def _close(names: list[str]) -> list[str]:
    import psutil

    closed = []
    for proc in psutil.process_iter(["name"]):
        name = (proc.info["name"] or "").lower().removesuffix(".exe")
        if name and name in names:
            try:
                proc.terminate()
                closed.append(name)
            except psutil.Error:
                pass
    return sorted(set(closed))


def mode_gaming(actif: bool, fermer: str = "", confirme_par_utilisateur: bool = False) -> str:
    if sys.platform != "win32":
        raise ToolFailure("le mode gaming n'est disponible que sous Windows")
    done = []
    if actif:
        saved = {"plan": _power_scheme(), "notifications": _toasts(False)}
        _saved_path().write_text(json.dumps(saved), encoding="utf-8")
        done.append("notifications coupées")
        _run("powercfg", "/setactive", HIGH_PERFORMANCE)
        if _power_scheme() == HIGH_PERFORMANCE:
            done.append("PC en performances maximales")
        # Applis listées une fois pour toutes (--applis-gaming), plus celles demandées et confirmées.
        names = [n.strip().lower().removesuffix(".exe") for n in (config.get("applis_gaming") or "").split(",")]
        if fermer:
            if not confirme_par_utilisateur:
                raise ToolFailure("Fermer des applis demande d'abord l'accord de l'utilisateur.")
            names += [n.strip().lower().removesuffix(".exe") for n in fermer.split(",")]
        closed = _close([n for n in names if n])
        if closed:
            done.append("fermé : " + ", ".join(closed))
        return "Mode gaming activé : " + ", ".join(done) + "."
    try:
        saved = json.loads(_saved_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    _toasts(saved.get("notifications", True))
    if saved.get("plan"):
        _run("powercfg", "/setactive", saved["plan"])
    _saved_path().unlink(missing_ok=True)
    return "Mode gaming désactivé : notifications et alimentation remises comme avant."


def applis_lourdes() -> str:
    """Les programmes qui prennent le plus de mémoire (pour proposer de les fermer)."""
    import psutil

    usage: dict[str, float] = {}
    for proc in psutil.process_iter(["name", "memory_info"]):
        try:
            name = (proc.info["name"] or "").removesuffix(".exe")
            usage[name] = usage.get(name, 0) + proc.info["memory_info"].rss / 2**20
        except (psutil.Error, AttributeError):
            pass
    system = {"system", "registry", "memcompression", "svchost", "explorer", "dwm", "csrss", "python",
              "pythonw", "msmpeng", "lsass", "wininit", "services", "smss", "audiodg", "steam", "steamwebhelper"}
    top = sorted(((m, n) for n, m in usage.items() if n.lower() not in system), reverse=True)[:8]
    return "\n".join(f"{n} : {m:.0f} Mo" for m, n in top)


def tools() -> list[Tool]:
    return [
        Tool("mode_gaming",
             "Active ou désactive le mode gaming : coupe les notifications Windows, met le PC en "
             "performances maximales et ferme les applis choisies ; tout est remis en le désactivant.",
             {"actif": boolean("true pour activer, false pour revenir à la normale"),
              "fermer": string("applis à fermer en plus, séparées par des virgules (ex. « chrome, discord ») ; "
                               "uniquement après accord de l'utilisateur"),
              "confirme_par_utilisateur": boolean("true si l'utilisateur a accepté de fermer ces applis")},
             mode_gaming, ["actif"]),
        Tool("applis_lourdes", "Liste les programmes qui utilisent le plus de mémoire, pour proposer de "
             "les fermer avant de jouer.", {}, applis_lourdes),
    ]

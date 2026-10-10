"""Lancement automatique de Jarvis à l'ouverture de la session (Windows, macOS, Linux)."""

from __future__ import annotations

import os
import plistlib
import shlex
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
ARGS = ["-m", "jarvis", "--fond"]


def _python() -> str:
    exe = Path(sys.executable)
    if sys.platform == "win32":
        # pythonw.exe : pas de fenêtre noire de console.
        windowless = exe.with_name("pythonw.exe")
        if windowless.exists():
            return str(windowless)
    return str(exe)


def _target() -> Path:
    if sys.platform == "win32":
        startup = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"
        return startup / "Jarvis.vbs"
    if sys.platform == "darwin":
        return Path.home() / "Library/LaunchAgents/com.jarvis.assistant.plist"
    config_home = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "autostart/jarvis.desktop"


def install() -> Path:
    target = _target()
    target.parent.mkdir(parents=True, exist_ok=True)
    python = _python()
    if sys.platform == "win32":
        command = " ".join([f'""{python}""', *ARGS])
        target.write_text(
            'Set shell = CreateObject("WScript.Shell")\r\n'
            f'shell.CurrentDirectory = "{PROJECT_DIR}"\r\n'
            f'shell.Run "{command}", 0, False\r\n',
            encoding="utf-16", newline="",  # avec BOM : Windows lit bien les chemins accentués
        )
    elif sys.platform == "darwin":
        with open(target, "wb") as f:
            plistlib.dump({
                "Label": "com.jarvis.assistant",
                "ProgramArguments": [python, *ARGS],
                "WorkingDirectory": str(PROJECT_DIR),
                "RunAtLoad": True,
            }, f)
    else:
        command = f"cd {shlex.quote(str(PROJECT_DIR))} && exec {shlex.quote(python)} {' '.join(ARGS)}"
        target.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Jarvis\n"
            "Comment=Assistant vocal personnel\n"
            f"Exec=sh -c {shlex.quote(command)}\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )
    return target


def uninstall() -> Path | None:
    target = _target()
    if target.exists():
        target.unlink()
        return target
    return None


# --- icône sur le Bureau et dans le menu Démarrer --------------------------

_PS_SHORTCUT = r"""
$shell = New-Object -ComObject WScript.Shell
$places = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))
$links = $env:JARVIS_LINKS | ConvertFrom-Json
foreach ($dir in $places) {
    Remove-Item (Join-Path $dir 'Ultron.lnk'), (Join-Path $dir 'Big Boss.lnk') -ErrorAction SilentlyContinue
    foreach ($item in $links) {
        $path = Join-Path $dir ($item.name + '.lnk')
        $link = $shell.CreateShortcut($path)
        $link.TargetPath = $env:JARVIS_EXE
        $link.Arguments = $item.args
        $link.WorkingDirectory = $env:JARVIS_DIR
        if ($item.icon) { $link.IconLocation = $item.icon }
        $link.Description = $item.name + ', assistant personnel'
        $link.Save()
        Write-Output $path
    }
}
"""


def _icon_path(theme: str = "jarvis") -> str | None:
    """Crée l'icône du réacteur dans la couleur du thème (bleu, rouge ou vert) avec PySide6."""
    from . import config
    from .themes import THEMES

    ext = "ico" if sys.platform == "win32" else "png"
    path = config.data_dir() / ("jarvis." + ext if theme == "jarvis" else f"{theme}.{ext}")
    try:
        from .orb import save_icon

        save_icon(path, THEMES[theme]["colors"]["veille"])
        return str(path)
    except Exception as exc:
        print(f"[raccourci] icône non créée ({exc}), icône par défaut utilisée.")
        return None


def _remove_old_shortcuts() -> None:
    """Supprime les icônes Ultron et Big Boss des anciennes versions."""
    for folder in (Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop",
                   Path(os.environ.get("USERPROFILE", Path.home())) / "OneDrive" / "Desktop",
                   Path(os.environ.get("USERPROFILE", Path.home())) / "OneDrive" / "Bureau",
                   Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs"):
        for name in ("Ultron.lnk", "Big Boss.lnk"):
            try:
                (folder / name).unlink(missing_ok=True)
            except OSError:
                pass


def create_shortcuts() -> list[str]:
    """Icône « Jarvis » à double-cliquer : Bureau + menu Démarrer (ou équivalents)."""
    import subprocess

    import json

    python = _python()
    icon = _icon_path()
    if sys.platform == "win32":
        links = [{"name": "Jarvis", "args": " ".join(ARGS), "icon": icon or ""}]
        _remove_old_shortcuts()
        env = {**os.environ, "JARVIS_EXE": python, "JARVIS_LINKS": json.dumps(links),
               "JARVIS_DIR": str(PROJECT_DIR)}
        out = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _PS_SHORTCUT],
                             env=env, capture_output=True, text=True, check=True)
        return [line for line in out.stdout.splitlines() if line.strip()]
    if sys.platform == "darwin":
        target = Path.home() / "Desktop" / "Jarvis.command"
        target.write_text(f"#!/bin/sh\ncd {shlex.quote(str(PROJECT_DIR))}\n"
                          f"exec {shlex.quote(python)} {' '.join(ARGS)}\n", encoding="utf-8")
        target.chmod(0o755)
        return [str(target)]
    command = f"cd {shlex.quote(str(PROJECT_DIR))} && exec {shlex.quote(python)} {' '.join(ARGS)}"
    entry = ("[Desktop Entry]\nType=Application\nName=Jarvis\nComment=Assistant personnel\n"
             f"Exec=sh -c {shlex.quote(command)}\n" + (f"Icon={icon}\n" if icon else "") + "Terminal=false\n")
    created = []
    for folder in (Path.home() / "Desktop", Path.home() / ".local/share/applications"):
        if folder.is_dir():
            target = folder / "jarvis.desktop"
            target.write_text(entry, encoding="utf-8")
            target.chmod(0o755)
            created.append(str(target))
    return created

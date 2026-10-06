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
foreach ($dir in $places) {
    $link = $shell.CreateShortcut((Join-Path $dir 'Jarvis.lnk'))
    $link.TargetPath = $env:JARVIS_EXE
    $link.Arguments = $env:JARVIS_ARGS
    $link.WorkingDirectory = $env:JARVIS_DIR
    if ($env:JARVIS_ICON) { $link.IconLocation = $env:JARVIS_ICON }
    $link.Description = 'Jarvis, assistant personnel'
    $link.Save()
    Write-Output (Join-Path $dir 'Jarvis.lnk')
}
"""


def _icon_path() -> str | None:
    """Crée l'icône du réacteur (jarvis.ico) avec PySide6 si disponible."""
    from . import config

    path = config.data_dir() / ("jarvis.ico" if sys.platform == "win32" else "jarvis.png")
    try:
        from .orb import save_icon

        save_icon(path)
        return str(path)
    except Exception as exc:
        print(f"[raccourci] icône non créée ({exc}), icône par défaut utilisée.")
        return None


def create_shortcuts() -> list[str]:
    """Icône « Jarvis » à double-cliquer : Bureau + menu Démarrer (ou équivalents)."""
    import subprocess

    python = _python()
    icon = _icon_path()
    if sys.platform == "win32":
        env = {**os.environ, "JARVIS_EXE": python, "JARVIS_ARGS": " ".join(ARGS),
               "JARVIS_DIR": str(PROJECT_DIR), "JARVIS_ICON": icon or ""}
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

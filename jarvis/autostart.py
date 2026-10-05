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
            encoding="utf-16",  # avec BOM : Windows lit bien les chemins accentués
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

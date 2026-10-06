"""Rappels et minuteurs : Jarvis te prévient à voix haute.

Les rappels sont gardés dans ~/.jarvis/rappels.json : ils survivent à un redémarrage du PC.
"""

from __future__ import annotations

import datetime
import json
import threading
import time
import uuid
from typing import Callable

from . import config

_lock = threading.Lock()
_listeners: list[Callable[[str], None]] = []
_started = False


def _path():
    return config.data_dir() / "rappels.json"


def _load() -> list[dict]:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _save(items: list[dict]) -> None:
    _path().write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add(text: str, when: datetime.datetime) -> dict:
    item = {"id": uuid.uuid4().hex[:6], "quand": when.isoformat(timespec="seconds"), "texte": text}
    with _lock:
        items = _load()
        items.append(item)
        _save(sorted(items, key=lambda r: r["quand"]))
    return item


def pending() -> list[dict]:
    with _lock:
        return _load()


def remove(reminder_id: str) -> bool:
    with _lock:
        items = _load()
        kept = [r for r in items if r["id"] != reminder_id]
        _save(kept)
        return len(kept) != len(items)


def on_due(listener: Callable[[str], None]) -> None:
    _listeners.append(listener)


def start() -> None:
    """Surveille les rappels en arrière-plan (une seule fois par programme)."""
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_loop, daemon=True, name="rappels").start()


def _loop() -> None:
    while True:
        now = datetime.datetime.now()
        with _lock:
            items = _load()
            due = [r for r in items if datetime.datetime.fromisoformat(r["quand"]) <= now]
            if due:
                _save([r for r in items if r not in due])
        for reminder in due:
            late = now - datetime.datetime.fromisoformat(reminder["quand"])
            text = reminder["texte"]
            if late > datetime.timedelta(minutes=10):  # PC éteint au moment prévu
                text += " (rappel en retard)"
            message = f"{config.get('titre', 'Monsieur')}, petit rappel : {text}."
            for listener in list(_listeners):
                try:
                    listener(message)
                except Exception as exc:
                    print(f"[rappels] erreur : {exc}")
        time.sleep(5)


"""État partagé de Jarvis (veille, écoute, réflexion, parole), lu par la boule à l'écran."""

from __future__ import annotations

import threading
import time

IDLE, LISTENING, THINKING, SPEAKING = "veille", "écoute", "réflexion", "parole"

_lock = threading.Lock()
_state = IDLE
_caption = ""
_caption_time = 0.0
_awake_until = 0.0
# Demandes pour la boule : None, "afficher", "masquer" ou "basculer".
_visibility_request: str | None = None


def set(state: str, caption: str | None = None) -> None:
    global _state, _caption, _caption_time
    with _lock:
        _state = state
        if caption is not None:
            _caption, _caption_time = caption, time.monotonic()


def get() -> tuple[str, str, float]:
    """(état, dernière phrase, âge de la phrase en secondes)."""
    with _lock:
        return _state, _caption, time.monotonic() - _caption_time


def wake(seconds: float = 8.0) -> None:
    """Clic sur la boule : la prochaine phrase est prise sans dire « Jarvis »."""
    global _awake_until
    with _lock:
        _awake_until = time.monotonic() + seconds
    set(LISTENING)


def awake_until() -> float:
    with _lock:
        return _awake_until


def request_visibility(action: str) -> None:
    global _visibility_request
    with _lock:
        _visibility_request = action


def take_visibility_request() -> str | None:
    global _visibility_request
    with _lock:
        action, _visibility_request = _visibility_request, None
        return action


# --- Interruption : « Jarvis, stop », clic sur la boule pendant qu'il parle, Ctrl+Alt+S -------------
_stop_listeners: list = []


def on_stop(callback) -> None:
    _stop_listeners.append(callback)


def request_stop() -> None:
    for callback in list(_stop_listeners):
        try:
            callback()
        except Exception as exc:
            print(f"[stop] erreur : {exc}")

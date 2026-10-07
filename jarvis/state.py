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


_stop_requested = False


def request_stop() -> None:
    """Clic sur la boule pendant que Jarvis parle : il doit se taire."""
    global _stop_requested
    with _lock:
        _stop_requested = True


def take_stop_request() -> bool:
    global _stop_requested
    with _lock:
        requested, _stop_requested = _stop_requested, False
        return requested


# Couleur passagère de la boule : rouge pour une alerte, vert quand une tâche est finie…
ALERT, DONE, SHOW = (255, 70, 60), (80, 230, 130), (255, 210, 90)
_flash: tuple[tuple[int, int, int], float] | None = None


def flash(color: tuple[int, int, int], seconds: float = 3.0) -> None:
    global _flash
    with _lock:
        _flash = (color, time.monotonic() + seconds)


def flash_color() -> tuple[int, int, int] | None:
    with _lock:
        if _flash and time.monotonic() < _flash[1]:
            return _flash[0]
        return None

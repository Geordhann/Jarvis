"""Une conversation par interlocuteur et par canal, oubliée après un moment d'inactivité."""

from __future__ import annotations

import threading
import time

from .agent import Agent

# Sans message pendant ce délai, la conversation repart de zéro : chaque question renvoie
# tout l'historique à Claude, l'effacer garde les coûts bas. La mémoire longue, elle, reste.
FORGET_AFTER_SECONDS = 10 * 60

_agents: dict[str, tuple[Agent, float]] = {}
_lock = threading.Lock()


def get(key: str, channel: str) -> Agent:
    with _lock:
        agent, last = _agents.get(key, (None, 0.0))
        if agent is None:
            agent = Agent(channel=channel)
        elif time.monotonic() - last > FORGET_AFTER_SECONDS:
            agent.reset()
            agent.reload()
        _agents[key] = (agent, time.monotonic())
        return agent


def reset(key: str) -> None:
    with _lock:
        if key in _agents:
            _agents[key][0].reset()


def reload_all() -> None:
    """Après un changement de personnalité : nouvelles conversations avec le nouveau caractère."""
    with _lock:
        for agent, _ in _agents.values():
            agent.reset()
            agent.reload()

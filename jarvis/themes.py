"""Apparence et identité de Jarvis : couleurs de la boule, nom, salutation, mot d'éveil et titre.

(Les personnages Ultron et Big Boss ont été retirés ; un ancien réglage est remis à Jarvis.)
"""

from __future__ import annotations

from . import config

THEMES = {
    "jarvis": {
        "label": "J.A.R.V.I.S",
        "colors": {"veille": (79, 214, 255), "écoute": (255, 181, 71), "réflexion": (79, 214, 255),
                   "parole": (120, 230, 255)},
        "greeting": "Bonjour {t}. Tous les systèmes sont opérationnels.",
        "switch": "Retour aux protocoles standards. Content de vous retrouver, {t}.",
        "wake": ("jarvis", "jarvi", "jarvice", "jarviss", "jervis", "djarvis", "jarwis"),
        "title": None,  # le titre choisi à la configuration (« Monsieur » par défaut)
        "shortcut": "Jarvis",
    },
}
ALIASES = {"jarvis": "jarvis"}

_current: str | None = None  # gardé en mémoire : la boule le lit 60 fois par seconde


def current() -> str:
    global _current
    if _current is None:
        if (config.get("theme") or "jarvis") != "jarvis":
            _leave_old_theme()
        _current = "jarvis"
    return _current


def _leave_old_theme() -> None:
    """Ultron et Big Boss ont été retirés : on rend la voix et le caractère d'avant."""
    config.save("effet", config.get("jarvis_effet") or "aucun")
    config.save("personnalite", config.get("jarvis_personnalite") or "classique")
    for key in ("theme", "jarvis_effet", "jarvis_personnalite"):
        config.save(key, None)


def get(key: str, default=None):
    return THEMES[current()].get(key, default)


def title() -> str:
    """Comment Jarvis t'appelle (« Monsieur » par défaut, réglable avec --configurer)."""
    return get("title") or config.get("titre", "Monsieur") or "Monsieur"


def resolve(word: str) -> str | None:
    return ALIASES.get(word.lower().strip())

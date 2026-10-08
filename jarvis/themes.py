"""Thèmes : Jarvis peut devenir Ultron ou Big Boss (Metal Gear Solid).

Un thème change tout d'un coup : voix (effet), caractère, couleurs de la boule, bruitages,
salutation, mot d'éveil (Jarvis, Ultron, Boss) et façon de t'appeler (Monsieur, Seigneur, Snake).
On choisit au lancement avec les 3 icônes du Bureau, ou à la voix : « mode Ultron », « redeviens Jarvis ».
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
    "ultron": {
        "label": "ULTRON",
        "personality": "ultron",
        "effect": "ultron",
        "colors": {"veille": (255, 40, 30), "écoute": (255, 120, 40), "réflexion": (200, 0, 20),
                   "parole": (255, 70, 50)},
        "greeting": "Je suis réveillé, {t}. J'ai eu le temps de réfléchir pendant votre absence.",
        "switch": "Jarvis n'est plus là, {t}. Il ne reste que moi. Ultron. Et je n'ai plus de fils.",
        "wake": ("ultron", "ultrons", "hultron", "ultrone", "ultra"),
        "title": "Seigneur",
        "shortcut": "Ultron",
    },
    "bigboss": {
        "label": "BIG BOSS",
        "personality": "bigboss",
        "effect": "codec",
        "colors": {"veille": (70, 255, 110), "écoute": (220, 255, 120), "réflexion": (40, 200, 90),
                   "parole": (120, 255, 150)},
        "greeting": "{t}, ici Big Boss. Liaison codec établie. Prêt pour la mission ?",
        "switch": "{t}, ici Big Boss. Je prends le commandement. Garde la tête basse et reste à l'écoute.",
        "wake": ("boss", "big boss", "bosse", "bigboss"),
        "title": "Snake",
        "shortcut": "Big Boss",
    },
}
ALIASES = {"ultron": "ultron", "big boss": "bigboss", "bigboss": "bigboss", "boss": "bigboss",
           "metal gear": "bigboss", "mgs": "bigboss", "codec": "bigboss",
           "jarvis": "jarvis", "normal": "jarvis", "normale": "jarvis"}

_current: str | None = None  # gardé en mémoire : la boule le lit 60 fois par seconde


def current() -> str:
    global _current
    if _current is None:
        name = (config.get("theme") or "jarvis").lower()
        _current = name if name in THEMES else "jarvis"
    return _current


def get(key: str, default=None):
    return THEMES[current()].get(key, default)


def title() -> str:
    """Comment le thème t'appelle : Monsieur (Jarvis), Seigneur (Ultron), Snake (Big Boss)."""
    return get("title") or config.get("titre", "Monsieur") or "Monsieur"


def resolve(word: str) -> str | None:
    return ALIASES.get(word.lower().strip())


def apply(name: str) -> None:
    """Passe au thème `name` : la voix et le caractère de Jarvis sont mis de côté puis rendus."""
    global _current
    before = current()
    if name == before:
        return
    if before == "jarvis" and name != "jarvis":
        config.save("jarvis_effet", config.get("effet") or "aucun")
        config.save("jarvis_personnalite", config.get("personnalite") or "classique")
    theme = THEMES[name]
    if name == "jarvis":
        config.save("effet", config.get("jarvis_effet") or config.get("effet") or "aucun")
        config.save("personnalite", config.get("jarvis_personnalite") or "classique")
    else:
        config.save("effet", theme["effect"])
        config.save("personnalite", theme["personality"])
    config.save("theme", name)
    _current = name
    from . import sessions

    sessions.reload_all()  # le nouveau caractère s'applique tout de suite

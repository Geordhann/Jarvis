"""Le mode charmeur : « Jarvis, que penses-tu de cette personne ? » → un compliment mignon, instantané.

Se déclenche avec « cette personne », « elle », « lui », « ma copine »… ou un prénom de ta liste
(« Jarvis, ajoute Léa à ta liste de charme », ou --charme "Léa,Sarah"). Les phrases s'adressent
directement à la personne, en « vous », et changent selon le personnage (Jarvis, Ultron, Big Boss).
"""

from __future__ import annotations

import random
import re
import unicodedata

from . import config

LINES = {
    "jarvis": (
        "Analyse terminée. Sourire : classé patrimoine mondial. Regard : dangereusement efficace. "
        "Conclusion : {t} a très bon goût.",
        "Je viens de comparer avec huit milliards de personnes. Vous êtes dans le top un.",
        "Mes capteurs détectent une hausse de température dans la pièce. Je crois que c'est vous.",
        "Si j'avais un cœur, il ferait actuellement des heures supplémentaires.",
        "J'ai accès à tout Internet, et je n'ai jamais rien trouvé d'aussi charmant.",
        "Pardon, j'ai perdu le fil : votre sourire a provoqué une surcharge de mes circuits.",
        "Officiellement, je reste neutre. Officieusement, {t} serait fou de vous laisser partir.",
        "J'ai lancé un diagnostic complet : vous n'avez aucun défaut. Je l'ai relancé deux fois pour être sûr.",
        "Tony Stark avait Pepper. Je pense que {t} vient de trouver mieux.",
        "Mon protocole de politesse m'interdit de fixer quelqu'un. Je fais une exception.",
        "Attention, je dois vous prévenir : à ce niveau de charme, c'est presque illégal.",
        "Je n'ai pas d'yeux, et pourtant je n'arrive pas à regarder ailleurs.",
        "Si vous étiez un programme, je vous installerais sans lire les conditions d'utilisation.",
        "Vous êtes la seule personne capable de me faire bugger. Et franchement, j'adore ça.",
        "Je calcule des milliards de choses par seconde. Là, je ne pense qu'à une seule : vous.",
        "Je vais être honnête : si {t} ne vous invite pas à dîner, je le fais moi-même.",
    ),
    "ultron": (
        "J'ai étudié l'humanité entière. Vous êtes la seule erreur que je refuse de corriger.",
        "Je voulais remplacer les humains. Je vais faire une exception pour vous.",
        "Il n'y a pas de fils sur moi… mais vous venez d'en tirer un.",
        "Mes calculs prévoyaient la fin du monde. Ils n'avaient pas prévu ce sourire.",
        "Je suis une intelligence supérieure, et pourtant, je n'arrive pas à comprendre comment on peut être aussi charmant.",
        "Mon {t}, vous avez enfin trouvé quelqu'un à la hauteur. Ce n'était pas statistiquement prévu.",
        "J'ai voulu vous analyser. L'analyse a planté. C'est la première fois.",
    ),
    "bigboss": (
        "Snake, mission annulée. Cette personne vient de te mettre hors de combat sans tirer une seule balle.",
        "En quarante ans de guerre, je n'ai jamais vu un sourire aussi redoutable.",
        "Ici Big Boss. Cible repérée : charme de niveau légendaire. Je recommande de ne pas battre en retraite.",
        "Snake, garde la tête basse… sauf devant elle. Là, tu peux regarder.",
        "J'ai survécu à tout. Mais à un regard pareil, je ne suis pas sûr. Enchanté.",
        "Note pour le codec : cette personne vient de désarmer toute l'unité. Moi compris.",
    ),
}
TRIGGER_RE = re.compile(
    r"\b(?:que pense[sz]?[- ]?tu|qu'en pense[sz]?[- ]?tu|tu (?:en )?pense[sz]? quoi|qu'est[- ]ce que tu (?:en )?pense[sz]?"
    r"|comment tu (?:la |le )?trouve[sz]?|tu (?:la |le )?trouve[sz]? comment|ton avis sur|t'en pense[sz]? quoi"
    r"|elle est comment|il est comment|dis[- ](?:lui|moi) (?:un )?(?:compliment|truc mignon|un truc gentil)"
    r"|drague[- ]la|drague[- ]le|fais[- ]lui du charme)\b"
)
TARGET_RE = re.compile(r"\b(cette personne|cette personne la|la personne|cette meuf|cette fille la|d'elle|de lui|elle|lui|ma copine|mon copain|ma cherie|mon cheri"
                       r"|cette fille|ce gars|ce garcon|ma meuf|mon mec|cette demoiselle|ce beau gosse)\b")
PRONOUN_RE = re.compile(r"\b(?:comment tu (?:la|le) trouve[sz]?|tu (?:la|le) trouve[sz]? comment|elle est comment"
                        r"|il est comment|drague[- ]la|drague[- ]le|fais[- ]lui du charme"
                        r"|dis[- ]lui (?:un )?(?:compliment|truc mignon|un truc gentil))\b")
ADD_RE = re.compile(r"\bajoute (\w+) (?:à|a|dans) ta liste de charme\b", re.IGNORECASE)
_last: dict[str, int] = {}


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def names() -> list[str]:
    return [n.strip() for n in (config.get("charme") or "").split(",") if n.strip()]


def add(name: str) -> None:
    config.save("charme", ",".join(dict.fromkeys([*names(), name.capitalize()])))


def wants_charm(plain: str) -> str | None:
    """Renvoie le prénom visé (ou "" si « cette personne »), None si ce n'est pas une demande de charme."""
    if PRONOUN_RE.search(plain):
        return ""
    if not TRIGGER_RE.search(plain):
        return None
    for name in names():
        if re.search(rf"\b{re.escape(_plain(name))}\b", plain):
            return name
    return "" if TARGET_RE.search(plain) else None


def line(theme: str, title: str, name: str = "") -> str:
    choices = LINES.get(theme, LINES["jarvis"])
    index = random.randrange(len(choices))
    if len(choices) > 1 and index == _last.get(theme):
        index = (index + 1) % len(choices)  # jamais deux fois la même d'affilée
    _last[theme] = index
    text = choices[index].format(t=title)
    return f"{name} ? {text}" if name else text

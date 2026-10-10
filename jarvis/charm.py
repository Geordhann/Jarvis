"""Le mode charmeur : « Jarvis, que penses-tu de cette personne ? » → un compliment mignon, instantané.

Se déclenche avec « cette personne », « elle », « lui », « ma copine »… ou un prénom de ta liste :
« Jarvis, ajoute Léa à ta liste de charme, elle est drôle, cool et fan de mangas », puis
« que penses-tu de Léa ? » → une phrase sur mesure qui rebondit sur ces mots. On complète avec
« Léa est aussi sportive » ; on retire avec « retire Léa de ta liste de charme ». Liste dans
~/.jarvis/charme.json.
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
# « ajoute Léa à ta liste de charme, elle est drôle, cool et sportive »
ADD_RE = re.compile(r"\bajoute (\w+) (?:à|a|dans) (?:ta|la) liste (?:de )?charme\b[\s,.:]*"
                    r"(?:(?:elle|il) (?:est|a|aime)\s+|(?:qui|elle|il) est\s+)?(.*)$", re.IGNORECASE)
# « Léa est aussi gentille », « Léa aime le foot » (pour un prénom déjà dans la liste)
DESCRIBE_RE = re.compile(r"^(\w+) (est|aime|adore|a)\s+(?:aussi\s+|tres\s+|très\s+)?(.+)$", re.IGNORECASE)
REMOVE_RE = re.compile(r"\b(?:retire|enleve|enlève|supprime) (\w+) (?:de|du) (?:ta|la) liste (?:de )?charme\b",
                       re.IGNORECASE)
_last: dict[str, int] = {}


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _path():
    return config.data_dir() / "charme.json"


def people() -> dict[str, list[str]]:
    """{prénom: [mots qui la décrivent]} ; reprend l'ancienne liste de prénoms (--charme) si besoin."""
    import json

    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    for name in (config.get("charme") or "").split(","):
        if name.strip() and name.strip().capitalize() not in data:
            data[name.strip().capitalize()] = []
    return data


def _save(data: dict[str, list[str]]) -> None:
    import json

    _path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def names() -> list[str]:
    return list(people())


def _split_words(text: str) -> list[str]:
    text = re.sub(r"[.!?]+$", "", text.strip())
    parts = re.split(r"\s*(?:,|;|\bet\b|\bpuis\b)\s*", text)
    return [p.strip() for p in parts if p.strip()]


def add(name: str, description: str = "") -> list[str]:
    """Ajoute (ou complète) une personne. Renvoie tous les mots qui la décrivent."""
    data = people()
    key = next((n for n in data if _plain(n) == _plain(name)), name.capitalize())
    words = data.get(key, [])
    words += [w for w in _split_words(description) if w.lower() not in (x.lower() for x in words)]
    data[key] = words
    _save(data)
    config.save("charme", None)  # tout est maintenant dans charme.json
    return words


def remove(name: str) -> bool:
    data = people()
    key = next((n for n in data if _plain(n) == _plain(name)), None)
    if key is None:
        return False
    del data[key]
    _save(data)
    config.save("charme", None)
    return True


def describe(request: str) -> tuple[str, list[str]] | None:
    """« Léa est drôle et cool » pour un prénom de la liste → (prénom, mots ajoutés)."""
    if request.strip().endswith("?") or re.search(r"\b(ou|où|la|là|ici|partie|parti|arrivee|arrivée)\b\s*$", request):
        return None  # « Léa est où ? » est une question, pas une description
    match = DESCRIBE_RE.match(request.strip(" .!"))
    if not match or not any(_plain(n) == _plain(match.group(1)) for n in names()):
        return None
    verb, rest = match.group(2).lower(), match.group(3)
    text = rest if verb == "est" else f"{verb} {rest}"
    return match.group(1), add(match.group(1), text)


def wants_charm(plain: str) -> str | None:
    """Renvoie le prénom visé (ou "" si « cette personne »), None si ce n'est pas une demande de charme."""
    if not (PRONOUN_RE.search(plain) or TRIGGER_RE.search(plain)):
        return None
    for name in names():
        if re.search(rf"\b{re.escape(_plain(name))}\b", plain):
            return name
    return "" if PRONOUN_RE.search(plain) or TARGET_RE.search(plain) else None


def line(theme: str, title: str, name: str = "") -> str:
    """Le compliment : sur mesure (Claude rebondit sur ses mots) si on connaît la personne, sinon une phrase prête."""
    words = people().get(name, []) if name else []
    if words:
        custom = _custom_line(theme, title, name, words)
        if custom:
            return custom
    choices = LINES.get(theme, LINES["jarvis"])
    index = random.randrange(len(choices))
    if len(choices) > 1 and index == _last.get(theme):
        index = (index + 1) % len(choices)  # jamais deux fois la même d'affilée
    _last[theme] = index
    text = choices[index].format(t=title)
    return f"{name} ? {text}" if name else text


def _custom_line(theme: str, title: str, name: str, words: list[str]) -> str | None:
    """Une phrase de drague unique qui rebondit sur ce qu'on sait d'elle (modèle rapide, ~1 seconde)."""
    try:
        import anthropic

        from . import personalities

        style = personalities.PERSONALITIES[personalities.current()][0]
        prompt = (
            f"Tu es l'assistant vocal de {title} et tu joues ce personnage : {style}\n"
            f"{title} te demande ce que tu penses de {name}, qui est juste à côté et t'entend. "
            f"Ce qu'on sait de {name} : {', '.join(words)}.\n"
            f"Écris UNE seule phrase de drague (30 mots maximum) adressée directement à {name}, en la vouvoyant : "
            "mignonne, drôle, un peu audacieuse mais toujours élégante et respectueuse, qui rebondit sur un ou deux "
            f"de ces mots de façon inattendue. Commence par « {name} ». Réponds uniquement par la phrase, sans guillemets."
        )
        client = anthropic.Anthropic(max_retries=1, timeout=12)
        reply = client.messages.create(model="claude-haiku-4-5", max_tokens=150,
                                       messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in reply.content if b.type == "text").strip().strip('"«» ')
        return text or None
    except Exception as exc:  # pas d'Internet, quota… : on garde une phrase prête
        print(f"[charme] phrase sur mesure impossible : {exc}")
        return None


def command(request: str) -> str | None:
    """Gestion de la liste de charme à la voix (PC et téléphone). Renvoie la réponse, ou None."""
    request = re.sub(r"^\s*(?:hey |ok )?(?:jarvis)\b[\s,.!]*", "", request, flags=re.IGNORECASE)
    added = ADD_RE.search(request)  # texte d'origine : le prénom garde ses accents
    if added:
        name = added.group(1).capitalize()
        words = add(name, added.group(2) or "")
        about = f" Je retiens : {', '.join(words)}." if words else " Dites-moi comment elle est, par exemple : " \
            f"{name} est drôle et cool."
        return f"C'est noté. {name} a droit à mon meilleur charme.{about}"
    removed = REMOVE_RE.search(request)
    if removed:
        ok = remove(removed.group(1))
        return f"{removed.group(1).capitalize()} est retirée de ma liste." if ok else "Cette personne n'est pas dans ma liste."
    described = describe(request)
    if described:
        return f"Noté pour {described[0]} : {', '.join(described[1])}."
    if re.search(r"\b(?:qui est|qui sont|montre|lis|donne)[- ]?(?:moi )?(?:dans )?(?:ta|la) liste (?:de )?charme\b",
                 _plain(request)):
        known = people()
        if not known:
            return "Ma liste de charme est vide."
        return " ".join(f"{n} : {', '.join(w) or 'rien de noté'}." for n, w in known.items())
    return None

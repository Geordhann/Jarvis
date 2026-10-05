"""Le cerveau de Jarvis : conversation avec Claude, en streaming."""

from __future__ import annotations

import datetime
import re
from typing import Callable, Iterator

import anthropic

# Plus le modèle est puissant, plus il coûte cher (prix pour un million de mots-jetons).
MODELS = {
    "opus": "claude-opus-5-5",      # le plus intelligent : 4 $ en entrée / 20 $ en sortie
    "sonnet": "claude-sonnet-5-5",  # très bon et 2x moins cher : 2 $ / 10 $
    "haiku": "claude-haiku-4-5",    # le plus rapide et 4x moins cher : 1 $ / 5 $
}

SYSTEM_PROMPT = """Tu es JARVIS, l'assistant personnel de {owner}, inspiré du majordome IA d'Iron Man.
Tu parles français, avec un ton poli, posé, légèrement pince-sans-rire, et tu appelles ton utilisateur "{title}".

Tes réponses sont LUES À VOIX HAUTE par une synthèse vocale :
- Réponds de façon brève et naturelle, comme à l'oral (en général une à trois phrases).
- N'utilise jamais de Markdown, de listes à puces, de tableaux, d'émojis ni de blocs de code.
- Écris les nombres, unités et abréviations de façon à ce qu'ils se prononcent bien.
- Si on te demande quelque chose de long, donne l'essentiel et propose de détailler.
- Tu peux chercher sur le web pour l'actualité, la météo ou tout fait récent.

Chaque message commence par la date et l'heure locales entre crochets : sers-t'en pour l'heure, la date ou les durées."""

# Fin de phrase : on envoie chaque phrase à la voix dès qu'elle est complète.
_SENTENCE_END = re.compile(r"(?<=[.!?…:;])\s+")


_DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]


def french_date(d: datetime.date) -> str:
    return f"{_DAYS[d.weekday()]} {d.day} {_MONTHS[d.month - 1]} {d.year}"


def french_time(t: datetime.datetime) -> str:
    if t.minute == 0:
        return f"{t.hour} heures" if t.hour > 1 else f"{t.hour} heure"
    return f"{t.hour} h {t.minute:02d}"


class Brain:
    def __init__(self, owner: str = "Monsieur", title: str = "Monsieur", effort: str = "low",
                 model: str = "opus"):
        self.client = anthropic.Anthropic()
        self.model = MODELS.get(model, model)
        self.effort = effort
        self.messages: list = []
        self._last_stop_reason = None
        self.system = SYSTEM_PROMPT.format(owner=owner, title=title)

    def reset(self) -> None:
        self.messages.clear()

    def ask(self, text: str, on_sentence: Callable[[str], None]) -> str:
        """Envoie `text` à Claude et appelle `on_sentence` pour chaque phrase reçue."""
        now = datetime.datetime.now()
        stamp = f"[{french_date(now.date())}, {french_time(now)}]"
        self.messages.append({"role": "user", "content": f"{stamp}\n{text}"})
        full = []
        # pause_turn : une recherche web longue peut demander de relancer le tour.
        for _ in range(5):
            buffer = ""
            for chunk in self._stream_turn():
                buffer += chunk
                full.append(chunk)
                parts = _SENTENCE_END.split(buffer)
                for sentence in parts[:-1]:
                    if sentence.strip():
                        on_sentence(sentence.strip())
                buffer = parts[-1]
            if buffer.strip():
                on_sentence(buffer.strip())
            if self._last_stop_reason != "pause_turn":
                break
        if self._last_stop_reason == "refusal":
            msg = "Je crains de ne pas pouvoir répondre à cela."
            on_sentence(msg)
            return msg
        return "".join(full)

    def _request(self) -> dict:
        request = dict(
            model=self.model,
            max_tokens=16000,
            system=self.system,
            messages=self.messages,
            cache_control={"type": "ephemeral"},
        )
        if self.model == MODELS["haiku"]:
            # Haiku : pas de réflexion adaptative, ancienne version de la recherche web.
            request["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
        else:
            request.update(
                thinking={"type": "adaptive"},
                output_config={"effort": self.effort},
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
                # Si Claude refuse une demande, l'API réessaie automatiquement avec un autre modèle.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        return request

    def _stream_turn(self) -> Iterator[str]:
        with self.client.beta.messages.stream(**self._request()) as stream:
            yield from stream.text_stream
            final = stream.get_final_message()
        self._last_stop_reason = final.stop_reason
        if final.stop_reason == "refusal":
            # On retire la question refusée pour que la conversation reste valide.
            self.messages.pop()
            return
        # On renvoie le contenu complet (blocs de réflexion, recherches...) tel quel.
        self.messages.append({"role": "assistant", "content": final.content})

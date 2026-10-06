"""Les outils que Jarvis peut utiliser tout seul (mails, agenda, navigateur, skills…)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class ToolFailure(Exception):
    """Erreur à renvoyer à Claude (il pourra corriger sa demande ou prévenir l'utilisateur)."""


@dataclass
class Tool:
    name: str
    description: str
    properties: dict[str, Any]
    handler: Callable[..., str]
    required: list[str] = field(default_factory=list)

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.properties,
                "required": self.required,
                "additionalProperties": False,
            },
            # Les arguments arrivent au fil de l'eau ; on les valide nous-mêmes ci-dessous.
            "eager_input_streaming": True,
        }

    def validate(self, args: Any) -> dict:
        if not isinstance(args, dict):
            raise ToolFailure("arguments invalides : un objet JSON était attendu")
        missing = [k for k in self.required if k not in args]
        if missing:
            raise ToolFailure(f"arguments manquants : {', '.join(missing)}")
        types = {"string": str, "integer": int, "boolean": bool}
        for key, value in args.items():
            spec = self.properties.get(key)
            if spec is None:
                raise ToolFailure(f"argument inconnu : {key}")
            expected = types.get(spec.get("type", ""))
            if expected and not isinstance(value, expected):
                raise ToolFailure(f"{key} doit être de type {spec['type']}")
        return args

    def run(self, args: Any) -> str:
        return self.handler(**self.validate(args))


def string(description: str) -> dict:
    return {"type": "string", "description": description}


def integer(description: str) -> dict:
    return {"type": "integer", "description": description}


def boolean(description: str) -> dict:
    return {"type": "boolean", "description": description}


def all_tools(skills_map) -> list[Tool]:
    from .. import telegram_perso
    from . import browser, google, media, utilities

    return [*google.tools(), *telegram_perso.tools(), *media.tools(), *utilities.tools(), *browser.tools(),
            _skill_tool(skills_map), _reply_tool()]


def _reply_tool() -> Tool:
    def ajouter_replique(questions: str, reponse: str) -> str:
        from .. import repliques

        items = [q.strip() for q in questions.split("|") if q.strip()]
        if not items or not reponse.strip():
            raise ToolFailure("il faut au moins une phrase déclencheuse et une réponse")
        repliques.add(items, reponse.strip())
        return f"Réplique enregistrée pour : {', '.join(items)}"

    return Tool(
        name="ajouter_replique",
        description="Enregistre une réplique prête à dire : quand l'utilisateur dira exactement une de ces "
                    "phrases, Jarvis répondra instantanément cette réponse. À utiliser quand il demande "
                    "« quand je te dis X, réponds Y ». {titre}, {heure} et {date} sont remplacés automatiquement.",
        properties={"questions": string("phrase(s) déclencheuse(s), séparées par |"),
                    "reponse": string("réponse exacte à dire")},
        required=["questions", "reponse"],
        handler=ajouter_replique,
    )


def _skill_tool(skills_map) -> Tool:
    def lire_skill(nom: str) -> str:
        skill = skills_map.get(nom)
        if skill is None:
            raise ToolFailure(f"skill inconnue. Disponibles : {', '.join(skills_map)}")
        return skill.instructions

    return Tool(
        name="lire_skill",
        description="Lit la fiche d'instructions complète d'une skill de la liste, "
                    "avant de réaliser la tâche correspondante.",
        properties={"nom": string("nom exact de la skill")},
        required=["nom"],
        handler=lire_skill,
    )

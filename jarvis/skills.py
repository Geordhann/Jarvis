"""Skills : des fiches d'instructions pour des tâches précises.

Une skill est un fichier Markdown avec un petit en-tête :

    ---
    nom: briefing-matin
    description: Résumé du jour (agenda, mails importants, météo).
    ---
    Les étapes à suivre…

Jarvis voit la liste des skills (nom + description) et lit la fiche complète
quand une demande correspond. Les skills fournies sont dans jarvis/skills/,
les tiennes dans ~/.jarvis/skills/ (elles remplacent celles du même nom).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import config

BUILTIN_DIR = Path(__file__).resolve().parent / "skills"


@dataclass
class Skill:
    name: str
    description: str
    instructions: str


def user_dir() -> Path:
    d = config.data_dir() / "skills"
    d.mkdir(exist_ok=True)
    return d


def _parse(path: Path) -> Skill | None:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        _, header, body = text.split("---", 2)
        for line in header.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
    name = meta.get("nom") or path.stem
    return Skill(name=name, description=meta.get("description", ""), instructions=body.strip())


def load_all() -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    for directory in (BUILTIN_DIR, user_dir()):
        for path in sorted(directory.glob("*.md")):
            try:
                skill = _parse(path)
            except (OSError, ValueError) as exc:
                print(f"[skills] fiche ignorée {path.name} : {exc}")
                continue
            if skill:
                skills[skill.name] = skill
    return skills


def catalog(skills: dict[str, Skill]) -> str:
    return "\n".join(f"- {s.name} : {s.description}" for s in skills.values())

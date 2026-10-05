"""Navigateur : ouvrir une page sur l'ordinateur.

La lecture du web (recherche, lecture de pages) passe par les outils web_search et
web_fetch exécutés chez Anthropic : rien à installer.
"""

from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus, urlparse

from . import Tool, ToolFailure, string


def ouvrir_page(url: str) -> str:
    if urlparse(url).scheme not in ("http", "https"):
        raise ToolFailure("seules les adresses http et https peuvent être ouvertes")
    if not webbrowser.open(url):
        raise ToolFailure("aucun navigateur disponible sur cet ordinateur")
    return f"Page ouverte dans le navigateur : {url}"


def rechercher_dans_navigateur(recherche: str, site: str = "google") -> str:
    urls = {
        "google": "https://www.google.com/search?q={}",
        "youtube": "https://www.youtube.com/results?search_query={}",
        "maps": "https://www.google.com/maps/search/{}",
        "wikipedia": "https://fr.wikipedia.org/w/index.php?search={}",
    }
    if site not in urls:
        raise ToolFailure(f"site inconnu, choisir parmi : {', '.join(urls)}")
    return ouvrir_page(urls[site].format(quote_plus(recherche)))


def tools() -> list[Tool]:
    return [
        Tool(
            name="ouvrir_page",
            description="Ouvre une adresse web dans le navigateur de l'ordinateur de l'utilisateur "
                        "(pour qu'il la voie à l'écran). Pour lire une page toi-même, utilise web_fetch.",
            properties={"url": string("adresse complète, commençant par https://")},
            required=["url"],
            handler=ouvrir_page,
        ),
        Tool(
            name="rechercher_dans_navigateur",
            description="Lance une recherche visible dans le navigateur de l'ordinateur : Google, "
                        "YouTube (musique, vidéos), Google Maps (itinéraires, lieux) ou Wikipédia.",
            properties={
                "recherche": string("texte à chercher"),
                "site": {"type": "string", "enum": ["google", "youtube", "maps", "wikipedia"]},
            },
            required=["recherche"],
            handler=rechercher_dans_navigateur,
        ),
    ]

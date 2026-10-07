"""Faire parler Jarvis autrement : dans une autre langue (traducteur) ou dans le micro Discord."""

from __future__ import annotations

from .. import voice as voice_module
from . import Tool, ToolFailure, string


def _voice():
    main = voice_module.main()
    if main is None:
        raise ToolFailure("possible seulement avec Jarvis à voix haute sur le PC")
    return main


def parler_langue(texte: str, langue: str) -> str:
    _voice().say(texte, lang=langue)
    return "Dit à voix haute. Ne répète pas la traduction ; au plus, une très courte phrase en français."


def parler_discord(texte: str, langue: str = "fr") -> str:
    from .. import discord_out

    if not discord_out.available():
        raise ToolFailure("le câble audio « CABLE Input » n'est pas installé : il faut VB-Cable (voir README, "
                          "section Discord)")
    _voice().say(texte, lang=langue, discord=True)
    return "Dit dans le micro Discord (et sur les haut-parleurs). Ne le répète pas."


def tools() -> list[Tool]:
    lang = string("code de langue : en (anglais), es, de, it, pt, nl, ar, ja, zh, ru, pl, tr, ko, hi, sv, fr")
    return [
        Tool("parler_langue",
             "Traducteur : dit à voix haute une phrase dans une autre langue, avec une voix de cette langue "
             "(« dis à mon pote en anglais que… »). Donne la phrase DÉJÀ traduite.",
             {"texte": string("la phrase traduite, exactement comme elle doit être dite"), "langue": lang},
             parler_langue, ["texte", "langue"]),
        Tool("parler_discord",
             "Dit une phrase dans le micro Discord de l'utilisateur (ses amis l'entendent), ex. « dis sur "
             "Discord que j'arrive dans 2 minutes ». Formule-la comme Jarvis qui parle de « Monsieur ».",
             {"texte": string("phrase exacte à dire, traduite si besoin"), "langue": lang},
             parler_discord, ["texte"]),
    ]

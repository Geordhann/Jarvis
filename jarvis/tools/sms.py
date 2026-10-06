"""Envoi de SMS depuis TON téléphone Android, avec l'appli gratuite « SMS Gateway for Android ».

L'appli (https://sms-gate.app, open source) reçoit les demandes de Jarvis via son serveur cloud et
envoie le SMS avec ta carte SIM : le destinataire voit ton numéro, c'est compris dans ton forfait.
Configuration : python -m jarvis --configurer-sms
"""

from __future__ import annotations

import re

import requests

from .. import config
from . import Tool, ToolFailure, boolean, string

CLOUD_API = "https://api.sms-gate.app/3rdparty/v1"


def is_configured() -> bool:
    return bool(config.get("sms_utilisateur") and config.get("sms_mot_de_passe"))


def normalize(number: str) -> str:
    """« 06 12 34 56 78 » → « +33612345678 » (numéros français), sinon format international."""
    digits = re.sub(r"[^\d+]", "", number)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if re.fullmatch(r"0[1-9]\d{8}", digits):
        digits = "+33" + digits[1:]
    elif re.fullmatch(r"33[1-9]\d{8}", digits):
        digits = "+" + digits
    if not re.fullmatch(r"\+\d{8,15}", digits):
        raise ToolFailure(f"numéro invalide : « {number} »")
    return digits


def send(numero: str, texte: str) -> dict:
    if not is_configured():
        raise ToolFailure("Les SMS ne sont pas configurés. Lancer : python -m jarvis --configurer-sms")
    base = (config.get("sms_serveur") or CLOUD_API).rstrip("/")
    response = requests.post(
        f"{base}/messages",
        auth=(config.get("sms_utilisateur"), config.get("sms_mot_de_passe")),
        json={"textMessage": {"text": texte}, "phoneNumbers": [normalize(numero)]},
        timeout=30,
    )
    if response.status_code == 401:
        raise ToolFailure("identifiants SMS Gateway refusés : relancer python -m jarvis --configurer-sms")
    if not response.ok:
        raise ToolFailure(f"envoi refusé par SMS Gateway ({response.status_code}) : {response.text[:200]}")
    return response.json()


def envoyer_sms(numero: str, texte: str, confirme_par_utilisateur: bool) -> str:
    if not confirme_par_utilisateur:
        raise ToolFailure("Envoi refusé : lis d'abord le SMS (destinataire et texte) à l'utilisateur et attends "
                          "son accord explicite.")
    result = send(numero, texte)
    state = result.get("state", "en file d'attente")
    return (f"SMS transmis au téléphone pour {normalize(numero)} (état : {state}). "
            "Il part dès que le téléphone est connecté à Internet.")


def configure() -> None:
    """Assistant : python -m jarvis --configurer-sms"""
    print("━━━ Configuration des SMS ━━━")
    print("Sur ton téléphone Android, dans l'appli SMS Gateway : active « Cloud server », puis lis")
    print("l'identifiant (Username) et le mot de passe (Password) affichés sur l'écran d'accueil.\n")
    for question, key in (("Identifiant (Username)", "sms_utilisateur"), ("Mot de passe (Password)", "sms_mot_de_passe")):
        hint = " [déjà enregistré, Entrée pour garder]" if config.get(key) else ""
        value = input(f"{question}{hint} : ").strip()
        if value:
            config.save(key, value)
    mine = input(f"Ton numéro de portable (pour un SMS de test) [{config.get('mon_numero') or ''}] : ").strip()
    if mine:
        config.save("mon_numero", normalize(mine))
    if config.get("mon_numero") and input("Envoyer un SMS de test à ton numéro ? (o/n) [o] : ").strip().lower() in ("", "o", "oui"):
        try:
            result = send(config.get("mon_numero"), "Jarvis : test d'envoi de SMS réussi.")
            print(f"✔ SMS confié au téléphone (état : {result.get('state', '?')}). Tu devrais le recevoir.")
        except ToolFailure as exc:
            print(f"✘ {exc}")
        except requests.RequestException as exc:
            print(f"✘ Impossible de joindre le serveur SMS Gateway ({type(exc).__name__}).")


def tools() -> list[Tool]:
    if not is_configured():
        return []
    return [
        Tool("envoyer_sms",
             "Envoie un SMS depuis le téléphone de l'utilisateur. Si seul un nom est donné, trouve d'abord le "
             "numéro (contacts_chercher, profil, mémoire). NE L'APPELLE QU'APRÈS avoir lu le destinataire et le "
             "texte à l'utilisateur et reçu son accord explicite.",
             {"numero": string("numéro du destinataire, ex. 06 12 34 56 78 ou +33612345678"),
              "texte": string("texte du SMS (court)"),
              "confirme_par_utilisateur": boolean("true uniquement après un oui explicite pour CE SMS")},
             envoyer_sms, ["numero", "texte", "confirme_par_utilisateur"]),
    ]

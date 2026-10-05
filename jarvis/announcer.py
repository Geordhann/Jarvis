"""Annonces automatiques : Jarvis te prévient à voix haute des nouveaux mails et messages.

Aucun appel à Claude : c'est gratuit. Désactivable avec « annonces »: "non" dans ~/.jarvis.json
ou en disant « Jarvis, arrête les annonces ».
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from . import config, telegram_perso
from .tools import google as google_tools

GMAIL_EVERY_SECONDS = 120
GMAIL_QUERY = "is:unread in:inbox category:primary newer_than:1d"


def enabled() -> bool:
    return (config.get("annonces", "oui") or "oui").lower() not in ("non", "off", "false", "0")


def start(say: Callable[[str], None]) -> None:
    if google_tools.is_connected():
        threading.Thread(target=_watch_gmail, args=(say,), daemon=True, name="annonces-gmail").start()
    if telegram_perso.is_configured():
        try:
            telegram_perso.on_new_message(
                lambda name, text: enabled() and say(f"Nouveau message Telegram de {name}."))
        except Exception as exc:
            print(f"[annonces] Telegram perso indisponible : {exc}")


def _unread_gmail() -> list[tuple[str, str, str]]:
    gmail = google_tools._service("gmail", "v1")
    found = gmail.users().messages().list(userId="me", q=GMAIL_QUERY, maxResults=20).execute()
    result = []
    for ref in found.get("messages", []):
        msg = gmail.users().messages().get(userId="me", id=ref["id"], format="metadata",
                                           metadataHeaders=["From", "Subject"]).execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        sender = headers.get("from", "").split("<")[0].strip().strip('"') or "quelqu'un"
        result.append((ref["id"], sender, headers.get("subject", "sans sujet")))
    return result


def _watch_gmail(say: Callable[[str], None]) -> None:
    seen: set[str] | None = None  # au démarrage, on n'annonce pas les anciens mails
    while True:
        try:
            mails = _unread_gmail()
            if seen is None:
                seen = {m[0] for m in mails}
            new = [m for m in mails if m[0] not in seen]
            seen.update(m[0] for m in new)
            if new and enabled():
                titre = config.get("titre", "Monsieur")
                if len(new) == 1:
                    _, sender, subject = new[0]
                    say(f"{titre}, nouveau mail de {sender} : {subject}.")
                else:
                    names = ", ".join(dict.fromkeys(m[1] for m in new[:3]))
                    say(f"{titre}, vous avez {len(new)} nouveaux mails, notamment de {names}.")
        except Exception as exc:
            print(f"[annonces] vérification Gmail impossible : {exc}")
        time.sleep(GMAIL_EVERY_SECONDS)

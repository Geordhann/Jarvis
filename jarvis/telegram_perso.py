"""Tes messages Telegram personnels (ton compte, pas le bot), via Telethon.

Configuration une seule fois : python -m jarvis --connecter-telegram-perso
(identifiants « api_id » et « api_hash » à créer sur https://my.telegram.org → API development tools).
La session reste sur ton ordinateur dans ~/.jarvis/telegram_perso.session.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Callable

from . import config
from .tools import Tool, ToolFailure, boolean, integer, string


def session_path() -> str:
    return str(config.data_dir() / "telegram_perso")


def is_configured() -> bool:
    return bool(config.get("telegram_api_id") and config.get("telegram_api_hash")) and \
        (config.data_dir() / "telegram_perso.session").exists()


def connect_interactive() -> None:
    """Connexion au compte (numéro de téléphone + code reçu dans Telegram)."""
    from telethon.sync import TelegramClient

    api_id = config.get("telegram_api_id") or input("api_id (sur my.telegram.org) : ").strip()
    api_hash = config.get("telegram_api_hash") or input("api_hash : ").strip()
    config.save("telegram_api_id", api_id)
    config.save("telegram_api_hash", api_hash)
    with TelegramClient(session_path(), int(api_id), api_hash) as client:  # demande numéro et code
        me = client.get_me()
        print(f"Connecté au compte Telegram de {me.first_name}.")
    (config.data_dir() / "telegram_perso.session").chmod(0o600)


class _Client:
    """Un client Telethon qui tourne dans son propre thread, utilisable depuis n'importe où."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.listeners: list[Callable[[str, str], None]] = []
        self.ready = threading.Event()
        self.error: Exception | None = None
        threading.Thread(target=self._run, daemon=True, name="telegram-perso").start()
        self.ready.wait(timeout=30)
        if self.error:
            raise self.error

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start())
        self.loop.run_forever()

    async def _start(self) -> None:
        from telethon import TelegramClient, events

        try:
            self.client = TelegramClient(session_path(), int(config.get("telegram_api_id")),
                                         config.get("telegram_api_hash"))
            await self.client.connect()
            if not await self.client.is_user_authorized():
                raise RuntimeError("session expirée, relancer : python -m jarvis --connecter-telegram-perso")

            @self.client.on(events.NewMessage(incoming=True))
            async def on_message(event) -> None:
                if not event.is_private:
                    return  # on n'annonce pas les groupes et chaînes
                sender = await event.get_sender()
                name = getattr(sender, "first_name", None) or getattr(sender, "title", "quelqu'un")
                for listener in self.listeners:
                    listener(name, event.raw_text or "(média)")
        except Exception as exc:
            self.error = exc
        finally:
            self.ready.set()

    def call(self, coro, timeout: float = 30):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)


_client: _Client | None = None
_lock = threading.Lock()


def client() -> _Client:
    global _client
    with _lock:
        if _client is None:
            if not is_configured():
                raise ToolFailure("Telegram perso non connecté. Lancer : python -m jarvis --connecter-telegram-perso")
            _client = _Client()
        return _client


def on_new_message(listener: Callable[[str, str], None]) -> None:
    client().listeners.append(listener)


# --- outils ----------------------------------------------------------------

def lire_messages_telegram(nombre: int = 10, non_lus_seulement: bool = True) -> str:
    c = client()

    async def run() -> str:
        lines = []
        async for dialog in c.client.iter_dialogs(limit=40):
            if non_lus_seulement and not dialog.unread_count:
                continue
            count = min(dialog.unread_count or 1, 5)
            messages = await c.client.get_messages(dialog.entity, limit=count)
            kind = "privé" if dialog.is_user else "groupe" if dialog.is_group else "chaîne"
            texts = " / ".join((m.message or "(média)")[:300] for m in reversed(messages))
            lines.append(f"{dialog.name} ({kind}, {dialog.unread_count} non lu(s)) : {texts}")
            if len(lines) >= nombre:
                break
        return "\n".join(lines) or "Aucun message non lu."

    return c.call(run())


def envoyer_message_telegram(destinataire: str, texte: str, confirme_par_utilisateur: bool) -> str:
    if not confirme_par_utilisateur:
        raise ToolFailure("Envoi refusé : annonce le message à l'utilisateur et attends son accord explicite.")
    c = client()

    async def run() -> str:
        target = destinataire.strip().lower()
        async for dialog in c.client.iter_dialogs(limit=200):
            if dialog.name and target in dialog.name.lower():
                await c.client.send_message(dialog.entity, texte)
                return f"Message envoyé à {dialog.name}."
        raise ToolFailure(f"aucune conversation ne correspond à « {destinataire} »")

    return c.call(run())


def tools() -> list[Tool]:
    if not is_configured():
        return []
    return [
        Tool("lire_messages_telegram",
             "Lit les messages reçus sur le compte Telegram personnel de l'utilisateur (non lus par défaut).",
             {"nombre": integer("nombre maximum de conversations (défaut 10)"),
              "non_lus_seulement": boolean("false pour voir aussi les conversations déjà lues")},
             lire_messages_telegram),
        Tool("envoyer_message_telegram",
             "Envoie un message Telegram depuis le compte de l'utilisateur. NE L'APPELLE QU'APRÈS avoir "
             "annoncé le destinataire et le texte et reçu un accord explicite.",
             {"destinataire": string("nom du contact ou du groupe tel qu'il apparaît dans Telegram"),
              "texte": string("message à envoyer"),
              "confirme_par_utilisateur": boolean("true uniquement après un oui explicite pour CE message")},
             envoyer_message_telegram, ["destinataire", "texte", "confirme_par_utilisateur"]),
    ]

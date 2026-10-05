"""Parler à Jarvis depuis WhatsApp (API WhatsApp Cloud de Meta).

Meta envoie les messages à une adresse web (webhook). Jarvis l'écoute sur le port 8766,
qu'il faut rendre accessible depuis Internet avec un tunnel (ngrok, Cloudflare Tunnel…).
Seul ce port est exposé : l'interface (port 8765) reste privée sur ton ordinateur.
Voir le README, section WhatsApp.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import re

import requests

from . import config, sessions, tts

GRAPH = "https://graph.facebook.com/v21.0"
PORT = 8766


def is_configured() -> bool:
    # La clé secrète de l'app est obligatoire : sans elle, n'importe qui pourrait
    # envoyer de faux messages « de ta part » au webhook.
    return all(config.get(k) for k in ("whatsapp_token", "whatsapp_numero_id", "whatsapp_verification",
                                       "whatsapp_mon_numero", "whatsapp_secret_app"))


def _auth() -> dict:
    return {"Authorization": f"Bearer {config.get('whatsapp_token')}"}


def _digits(number: str | None) -> str:
    return re.sub(r"\D", "", number or "")


def send_text(to: str, text: str) -> None:
    for i in range(0, len(text), 4000):
        requests.post(f"{GRAPH}/{config.get('whatsapp_numero_id')}/messages", headers=_auth(), timeout=30, json={
            "messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[i:i + 4000]},
        }).raise_for_status()


def send_audio(to: str, mp3: bytes) -> None:
    phone_id = config.get("whatsapp_numero_id")
    upload = requests.post(f"{GRAPH}/{phone_id}/media", headers=_auth(), timeout=60,
                           data={"messaging_product": "whatsapp", "type": "audio/mpeg"},
                           files={"file": ("reponse.mp3", mp3, "audio/mpeg")})
    upload.raise_for_status()
    requests.post(f"{GRAPH}/{phone_id}/messages", headers=_auth(), timeout=30, json={
        "messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"id": upload.json()["id"]},
    }).raise_for_status()


def download_media(media_id: str) -> bytes:
    meta = requests.get(f"{GRAPH}/{media_id}", headers=_auth(), timeout=30)
    meta.raise_for_status()
    media = requests.get(meta.json()["url"], headers=_auth(), timeout=60)
    media.raise_for_status()
    return media.content


def handle_message(message: dict) -> None:
    """Traite un message entrant (appelé dans un thread)."""
    sender = message.get("from", "")
    if _digits(sender) != _digits(config.get("whatsapp_mon_numero")):
        print(f"[whatsapp] message ignoré d'un numéro non autorisé : {sender}")
        return
    as_voice = False
    if message.get("type") == "text":
        text = message["text"]["body"]
    elif message.get("type") == "audio":
        if not tts.can_transcribe():
            send_text(sender, "Pour les vocaux, il faut une clé ElevenLabs. Écrivez-moi en attendant.")
            return
        text = tts.transcribe(download_media(message["audio"]["id"]), "vocal.ogg")
        as_voice = True
    else:
        send_text(sender, "Je ne sais lire que les messages texte et vocaux pour l'instant.")
        return

    if text.strip().lower() in ("/nouveau", "nouvelle conversation"):
        sessions.reset(f"whatsapp:{sender}")
        send_text(sender, "C'est oublié. On repart de zéro.")
        return
    answer = sessions.get(f"whatsapp:{sender}", "whatsapp").ask(text)
    if answer:
        send_text(sender, answer)
        if as_voice:
            send_audio(sender, tts.synthesize(answer))


async def start():
    from aiohttp import web

    async def verify(request: web.Request) -> web.Response:
        q = request.query
        if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == config.get("whatsapp_verification"):
            return web.Response(text=q.get("hub.challenge", ""))
        return web.Response(status=403)

    async def receive(request: web.Request) -> web.Response:
        raw = await request.read()
        secret = config.get("whatsapp_secret_app") or ""
        expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not secret or not hmac.compare_digest(expected, request.headers.get("X-Hub-Signature-256", "")):
            return web.Response(status=403)
        try:
            payload = await request.json()
        except ValueError:
            return web.Response(status=400)
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                for message in change.get("value", {}).get("messages", []):
                    # On répond tout de suite à Meta, le traitement continue en arrière-plan.
                    asyncio.get_running_loop().run_in_executor(None, _safe_handle, message)
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/whatsapp", verify)
    app.router.add_post("/whatsapp", receive)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", PORT).start()
    print(f"[whatsapp] webhook à l'écoute sur http://127.0.0.1:{PORT}/whatsapp")
    return runner


def _safe_handle(message: dict) -> None:
    try:
        handle_message(message)
    except Exception as exc:
        print(f"[whatsapp] erreur : {exc}")

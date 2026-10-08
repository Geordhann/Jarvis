"""Serveur de l'interface de Jarvis : http://localhost:8765 (accessible depuis ton ordinateur seulement)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from . import config, effects, sessions, state, tts, voices
from .tools import sms
from .tools import google as google_tools

PORT = 8765
INTERFACE = Path(__file__).resolve().parent / "interface" / "index.html"
ALLOWED_HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}"}


async def start():
    from aiohttp import web

    @web.middleware
    async def local_only(request: web.Request, handler):
        # Empêche un site web malveillant ouvert dans ton navigateur de piloter Jarvis :
        # nom d'hôte vérifié (DNS rebinding), en-tête maison obligatoire et origine contrôlée.
        if request.host not in ALLOWED_HOSTS:
            return web.Response(status=403, text="Accès refusé")
        if request.path.startswith("/api/"):
            origin = request.headers.get("Origin")
            if request.headers.get("X-Jarvis") != "1" or (origin and origin.split("://", 1)[-1] not in ALLOWED_HOSTS):
                return web.Response(status=403, text="Accès refusé")
        return await handler(request)

    async def index(request: web.Request) -> web.Response:
        return web.FileResponse(INTERFACE, headers={"Cache-Control": "no-store"})

    async def message(request: web.Request) -> web.StreamResponse:
        text = (await request.json()).get("text", "").strip()
        response = web.StreamResponse(headers={"Content-Type": "application/x-ndjson"})
        await response.prepare(request)
        if not text:
            await response.write_eof()
            return response

        loop = asyncio.get_running_loop()
        events: asyncio.Queue = asyncio.Queue()

        def push(event: dict) -> None:
            loop.call_soon_threadsafe(events.put_nowait, event)

        def run() -> None:
            try:
                sessions.get("web", "web").ask(
                    text,
                    on_sentence=lambda s: push({"type": "sentence", "text": s}),
                    on_tool=lambda name: push({"type": "tool", "name": name}),
                )
            except Exception as exc:
                print(f"[interface] erreur : {exc}")
                push({"type": "error", "text": "Un problème est survenu avec mes serveurs."})
            push({"type": "done"})

        loop.run_in_executor(None, run)
        while True:
            event = await events.get()
            await response.write((json.dumps(event, ensure_ascii=False) + "\n").encode())
            if event["type"] == "done":
                break
        await response.write_eof()
        return response

    async def speech(request: web.Request) -> web.Response:
        text = (await request.json()).get("text", "")[:2000]
        audio, ext = await asyncio.to_thread(lambda: effects.apply(tts.synthesize(text)))
        return web.Response(body=audio, content_type="audio/wav" if ext == "wav" else "audio/mpeg")

    async def reset(request: web.Request) -> web.Response:
        sessions.reset("web")
        return web.json_response({"ok": True})

    async def status(request: web.Request) -> web.Response:
        current = voices.find_voice(voices.load_saved_voice() or "") or voices.default_voice()
        return web.json_response({
            "modele": config.get("modele", "opus"),
            "voix": current,
            "voix_disponibles": [{"nom": n, "description": voices.describe(n)} for n in voices.catalog()],
            "connexions": {
                "Gmail & Agenda": google_tools.is_connected(),
                "ElevenLabs": voices.has_elevenlabs(),
                "SMS": sms.is_configured(),
            },
        })

    async def set_voice(request: web.Request) -> web.Response:
        name = voices.find_voice((await request.json()).get("nom", ""))
        if not name:
            return web.json_response({"ok": False}, status=400)
        voices.save_voice(name)
        return web.json_response({"ok": True, "voix": name})

    async def version(request: web.Request) -> web.Response:
        return web.json_response({"version": code_version()})

    async def show_orb(request: web.Request) -> web.Response:
        state.request_visibility("afficher")
        return web.json_response({"ok": True})

    app = web.Application(middlewares=[local_only])
    app.router.add_post("/api/orbe/afficher", show_orb)
    app.router.add_get("/api/version", version)
    app.router.add_get("/", index)
    app.router.add_post("/api/message", message)
    app.router.add_post("/api/voix/lire", speech)
    app.router.add_post("/api/voix/choisir", set_voice)
    app.router.add_post("/api/nouveau", reset)
    app.router.add_get("/api/etat", status)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", PORT).start()
    print(f"[interface] ouverte sur http://localhost:{PORT}")
    return runner


def code_version() -> str:
    """Empreinte du code de Jarvis (dossier + dates des fichiers) : sert à savoir si le Jarvis
    déjà lancé est une ancienne version, ou une autre copie (ex. dans OneDrive)."""
    import hashlib

    root = Path(__file__).resolve().parent
    digest = hashlib.sha1(str(root).encode())
    for path in sorted(root.rglob("*.py")):
        digest.update(f"{path.relative_to(root)}:{path.stat().st_mtime_ns}".encode())
    return digest.hexdigest()[:12]

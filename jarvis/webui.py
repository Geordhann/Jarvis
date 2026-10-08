"""Serveur de l'interface de Jarvis : http://localhost:8765 sur le PC, et depuis le téléphone via Tailscale
(adresse privée en HTTPS + code d'accès, voir mobile.py)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from . import config, effects, mobile, sessions, state, themes, tts, voices
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
        remote = mobile.is_remote(request)
        # Depuis le téléphone : l'adresse Tailscale (ou localhost si le relais Tailscale la réécrit).
        allowed = ({mobile.host()} | ALLOWED_HOSTS) if remote else ALLOWED_HOSTS
        if request.host.split(":")[0] not in {h.split(":")[0] for h in allowed if h} and request.host not in allowed:
            return web.Response(status=403, text="Accès refusé")
        if remote and request.path not in ("/connexion", "/manifest.json", "/icone.png") \
                and not mobile.is_authorized(request):
            if request.path.startswith("/api/"):
                return web.Response(status=401, text="Code d'accès requis")
            return web.Response(text=mobile.LOGIN_PAGE.replace("{message}", ""), content_type="text/html")
        if request.path.startswith("/api/"):
            origin = (request.headers.get("Origin") or "").split("://", 1)[-1]
            if request.headers.get("X-Jarvis") != "1" or (origin and origin not in allowed
                                                            and origin.split(":")[0] != request.host.split(":")[0]):
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
            "theme": _theme_info(),
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

    async def set_theme(request: web.Request) -> web.Response:
        from . import themes

        name = themes.resolve(str((await request.json()).get("nom", "")))
        if not name:
            return web.json_response({"ok": False}, status=400)
        if (await request.json()).get("annonce", True):
            state.request_theme(name)  # icône du Bureau : Jarvis l'annonce à voix haute sur le PC
            state.request_visibility("afficher")
        else:
            await asyncio.to_thread(themes.apply, name)  # depuis le téléphone : en silence sur le PC
        return web.json_response({"ok": True, "theme": _theme_info()})

    async def login(request: web.Request) -> web.Response:
        form = await request.post()
        if mobile.check_code(str(form.get("code", ""))):
            response = web.HTTPFound("/")
            response.set_cookie(mobile.COOKIE, mobile.code(), max_age=365 * 86400, httponly=True,
                                secure=True, samesite="Strict")
            return response
        message = "Trop d'essais, réessaie dans 10 minutes." if mobile.locked_out() else "Code incorrect."
        return web.Response(text=mobile.LOGIN_PAGE.replace("{message}", message), content_type="text/html",
                            status=401)

    async def manifest(request: web.Request) -> web.Response:
        return web.json_response({
            # Ouverte depuis l'écran d'accueil ou par « Ok Google, ouvre Jarvis » : elle écoute tout de suite.
            "name": "J.A.R.V.I.S.", "short_name": "Jarvis", "start_url": "/?ecoute=1", "display": "standalone",
            "background_color": "#04090f", "theme_color": "#04090f",
            "icons": [{"src": "/icone.png", "sizes": "256x256", "type": "image/png"}],
            "shortcuts": [{"name": "Parler à Jarvis", "url": "/?ecoute=1"},
                          {"name": "Mains libres", "url": "/?ecoute=mains-libres"}],
        })

    async def icon(request: web.Request) -> web.Response:
        return web.Response(body=_icon_png(), content_type="image/png")

    async def version(request: web.Request) -> web.Response:
        return web.json_response({"version": code_version()})

    async def show_orb(request: web.Request) -> web.Response:
        state.request_visibility("afficher")
        return web.json_response({"ok": True})

    app = web.Application(middlewares=[local_only])
    app.router.add_post("/connexion", login)
    app.router.add_get("/manifest.json", manifest)
    app.router.add_get("/icone.png", icon)
    app.router.add_post("/api/orbe/afficher", show_orb)
    app.router.add_get("/api/version", version)
    app.router.add_post("/api/theme", set_theme)
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


def _theme_info() -> dict:
    theme = themes.THEMES[themes.current()]
    return {"nom": themes.current(), "label": theme["label"], "titre": themes.title(),
            "couleur": "#%02x%02x%02x" % theme["colors"]["veille"], "eveil": list(theme["wake"]),
            "salutation": theme["greeting"].format(t=themes.title())}


def _icon_png() -> bytes:
    """Icône du réacteur pour l'écran d'accueil du téléphone (dessinée avec Pillow)."""
    import io

    from PIL import Image, ImageDraw

    size, cyan = 256, (79, 214, 255)
    img = Image.new("RGB", (size, size), (4, 9, 15))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 248, 248), fill=(3, 10, 18), outline=cyan, width=4)
    for i in range(8):
        d.arc((28, 28, 228, 228), i * 45 + 6, i * 45 + 38, fill=cyan, width=14)
    for r, c in ((60, (40, 120, 150)), (45, (79, 214, 255)), (25, (225, 250, 255))):
        d.ellipse((128 - r, 128 - r, 128 + r, 128 + r), fill=c)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

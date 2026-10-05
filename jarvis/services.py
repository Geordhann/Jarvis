"""Lance en arrière-plan l'interface, le bot Telegram et le webhook WhatsApp."""

from __future__ import annotations

import asyncio
import threading
import webbrowser

from . import telegram_bot, webui, whatsapp


def start(open_interface: bool = False) -> threading.Thread:
    ready = threading.Event()

    async def main() -> None:
        try:
            await webui.start()
            if open_interface:
                webbrowser.open(f"http://localhost:{webui.PORT}")
        except OSError as exc:
            print(f"[interface] impossible de démarrer (port {webui.PORT} déjà pris ?) : {exc}")
        if telegram_bot.is_configured():
            try:
                await telegram_bot.start()
            except Exception as exc:
                print(f"[telegram] impossible de démarrer : {exc}")
        if whatsapp.is_configured():
            try:
                await whatsapp.start()
            except Exception as exc:
                print(f"[whatsapp] impossible de démarrer : {exc}")
        ready.set()
        await asyncio.Event().wait()  # tourne jusqu'à la fin du programme

    thread = threading.Thread(target=lambda: asyncio.run(main()), daemon=True, name="jarvis-services")
    thread.start()
    ready.wait(timeout=30)
    return thread

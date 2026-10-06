"""Lance l'interface de Jarvis en arrière-plan."""

from __future__ import annotations

import asyncio
import threading
import webbrowser

from . import webui


def start(open_interface: bool = False) -> threading.Thread:
    ready = threading.Event()

    async def main() -> None:
        try:
            await webui.start()
            if open_interface:
                webbrowser.open(f"http://localhost:{webui.PORT}")
        except OSError as exc:
            print(f"[interface] impossible de démarrer (port {webui.PORT} déjà pris ?) : {exc}")
        ready.set()
        await asyncio.Event().wait()  # tourne jusqu'à la fin du programme

    thread = threading.Thread(target=lambda: asyncio.run(main()), daemon=True, name="jarvis-services")
    thread.start()
    ready.wait(timeout=30)
    return thread

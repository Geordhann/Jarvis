"""Parler à Jarvis depuis ton téléphone, de n'importe où, via Tailscale (réseau privé gratuit).

L'interface n'est jamais exposée sur Internet : seuls tes appareils connectés à ton compte Tailscale
la voient, en HTTPS (obligatoire pour le micro du téléphone), et un code d'accès est demandé en plus.
Configuration : python -m jarvis --configurer-mobile
"""

from __future__ import annotations

import hmac
import json
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import config

COOKIE = "jarvis_code"
_failures: list[float] = []


def host() -> str | None:
    return config.get("hote_mobile")


def code() -> str | None:
    return config.get("code_mobile")


def is_remote(request) -> bool:
    """Requête venue du téléphone (via Tailscale) plutôt que du PC lui-même."""
    return request.host.split(":")[0] == (host() or "\0") or \
        any(name.lower().startswith("tailscale-") for name in request.headers)


def is_authorized(request) -> bool:
    expected = code()
    given = request.cookies.get(COOKIE, "")
    return bool(expected) and hmac.compare_digest(given, expected)


def locked_out() -> bool:
    """Après 5 codes faux en 10 minutes, on bloque les essais (contre les devinettes)."""
    now = time.monotonic()
    _failures[:] = [t for t in _failures if now - t < 600]
    return len(_failures) >= 5


def check_code(given: str) -> bool:
    if locked_out():
        return False
    expected = code() or ""
    ok = bool(expected) and hmac.compare_digest(given.strip(), expected)
    if not ok:
        _failures.append(time.monotonic())
    return ok


LOGIN_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>J.A.R.V.I.S.</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#04090f;color:#d8eef8;
font:16px system-ui,sans-serif}form{display:flex;flex-direction:column;gap:14px;width:min(320px,90vw);text-align:center}
h1{color:#4fd6ff;letter-spacing:.3em;font-size:20px}input,button{font:inherit;padding:14px;border-radius:6px;
border:1px solid #2a6e8a;background:#0b1a26;color:#d8eef8;text-align:center;letter-spacing:.3em}
button{background:#4fd6ff;color:#032;font-weight:700;letter-spacing:.05em}p{color:#ff8a8a;min-height:1em}</style>
</head><body><form method="post" action="/connexion"><h1>J.A.R.V.I.S.</h1>
<label for="c">Code d'accès</label><input id="c" name="code" inputmode="numeric" autocomplete="one-time-code" autofocus>
<button>Entrer</button><p>{message}</p></form></body></html>"""


def tailscale_exe() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    if sys.platform == "win32":
        default = Path(r"C:\Program Files\Tailscale\tailscale.exe")
        return str(default) if default.exists() else None
    return None


def configure(port: int) -> None:
    """Active l'accès mobile : HTTPS privé Tailscale vers l'interface, et code d'accès."""
    exe = tailscale_exe()
    if not exe:
        print("✘ Tailscale n'est pas installé. Installe-le depuis https://tailscale.com/download "
              "(PC et téléphone, même compte), puis relance cette commande.")
        return
    status = subprocess.run([exe, "status", "--json"], capture_output=True, text=True)
    try:
        dns = json.loads(status.stdout)["Self"]["DNSName"].rstrip(".")
    except (ValueError, KeyError):
        print("✘ Tailscale ne répond pas : ouvre l'appli Tailscale sur le PC et connecte-toi.")
        return
    print("Activation de l'accès HTTPS privé (tailscale serve)…")
    print("Si un lien « login.tailscale.com » s'affiche, ouvre-le et clique pour autoriser : la commande "
          "continue toute seule ensuite.\n")
    try:
        # Sortie affichée en direct : Tailscale peut demander d'autoriser HTTPS/Serve via un lien.
        serve = subprocess.run([exe, "serve", "--bg", str(port)], timeout=600)
    except subprocess.TimeoutExpired:
        print("\n✘ Tailscale attend toujours l'autorisation. Ouvre le lien affiché, puis relance : "
              "python -m jarvis --configurer-mobile")
        return
    if serve.returncode != 0:
        print("\n✘ Tailscale a refusé. Ouvre le lien affiché ci-dessus s'il y en a un, puis relance : "
              "python -m jarvis --configurer-mobile")
        return
    config.save("hote_mobile", dns)
    if not code():
        config.save("code_mobile", f"{secrets.randbelow(10**6):06d}")
    print("\n✔ Accès mobile prêt !")
    print(f"  1. Sur ton téléphone, installe Tailscale et connecte-toi avec le même compte.")
    print(f"  2. Ouvre dans Chrome : https://{dns}/")
    print(f"  3. Code d'accès : {code()}")
    print("  4. Menu ⋮ → « Ajouter à l'écran d'accueil » pour avoir l'icône Jarvis.")
    print("Le PC doit être allumé avec Jarvis lancé. Nouveau code : python -m jarvis --nouveau-code-mobile")

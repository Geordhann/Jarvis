"""Spotify : lancer un titre, un artiste, un album ou une de tes playlists, et contrôler la lecture.

Connexion une fois : python -m jarvis --connecter-spotify (voir README, section Spotify).
Avec Spotify Premium, Jarvis lance directement ce que tu demandes sur l'appli du PC.
Sans Premium, Spotify n'autorise pas le contrôle à distance : Jarvis ouvre la page du morceau
dans l'appli et tu n'as plus qu'à appuyer sur lecture.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import time
import urllib.parse
import webbrowser

import requests

from .. import config
from . import Tool, ToolFailure, boolean, integer, string

API = "https://api.spotify.com/v1"
ACCOUNTS = "https://accounts.spotify.com"
PORT = 8766
REDIRECT = f"http://127.0.0.1:{PORT}/callback"
SCOPES = ("user-read-playback-state user-modify-playback-state user-read-currently-playing "
          "playlist-read-private playlist-read-collaborative user-library-read user-library-modify")


def _token_path():
    return config.data_dir() / "spotify_token.json"


def is_connected() -> bool:
    return bool(config.get("spotify_client_id")) and _token_path().exists()


# --- connexion (OAuth PKCE : pas de mot de passe ni de secret stocké) ---------------

def connect(client_id: str | None = None) -> None:
    client_id = (client_id or config.get("spotify_client_id") or "").strip()
    if not client_id:
        print("Il faut d'abord l'identifiant de ton appli Spotify (Client ID), voir README, section Spotify.")
        client_id = input("Client ID : ").strip()
    if not client_id:
        return
    config.save("spotify_client_id", client_id)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    received: dict[str, str] = {}

    class Callback(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if urllib.parse.urlparse(self.path).path == "/callback":
                received.update(query)
            ok = "code" in query and query.get("state") == state
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(("<h2>Spotify connecté à Jarvis ✔ Tu peux fermer cette page.</h2>" if ok else
                              "<h2>Connexion refusée ou échouée. Relance la commande.</h2>").encode())

        def log_message(self, *args) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Callback)
    url = f"{ACCOUNTS}/authorize?" + urllib.parse.urlencode({
        "client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPES,
        "code_challenge_method": "S256", "code_challenge": challenge, "state": state,
    })
    print("Autorise Jarvis dans la page Spotify qui s'ouvre…")
    webbrowser.open(url)
    server.timeout = 300
    while "code" not in received and "error" not in received:
        server.handle_request()
    server.server_close()
    if received.get("state") != state or "code" not in received:
        raise RuntimeError(f"connexion Spotify refusée ({received.get('error', 'réponse invalide')})")
    response = requests.post(f"{ACCOUNTS}/api/token", data={
        "grant_type": "authorization_code", "code": received["code"], "redirect_uri": REDIRECT,
        "client_id": client_id, "code_verifier": verifier,
    }, timeout=20)
    response.raise_for_status()
    _save_token(response.json())
    me = _api("GET", "/me")
    premium = me.get("product") == "premium"
    print(f"✔ Spotify connecté ({me.get('display_name') or me.get('id')}, "
          f"{'Premium : contrôle complet' if premium else 'compte gratuit : Jarvis ouvrira les morceaux'}).")


def _save_token(data: dict) -> None:
    old = {}
    if _token_path().exists():
        old = json.loads(_token_path().read_text(encoding="utf-8"))
    data.setdefault("refresh_token", old.get("refresh_token"))
    data["expires_at"] = time.time() + int(data.get("expires_in", 3600)) - 60
    _token_path().write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(_token_path(), 0o600)
    except OSError:
        pass


def _access_token() -> str:
    if not is_connected():
        raise ToolFailure("Spotify n'est pas connecté : il faut lancer « python -m jarvis --connecter-spotify »")
    token = json.loads(_token_path().read_text(encoding="utf-8"))
    if time.time() >= token.get("expires_at", 0):
        response = requests.post(f"{ACCOUNTS}/api/token", data={
            "grant_type": "refresh_token", "refresh_token": token["refresh_token"],
            "client_id": config.get("spotify_client_id"),
        }, timeout=20)
        if response.status_code >= 400:
            raise ToolFailure("connexion Spotify expirée : relance « python -m jarvis --connecter-spotify »")
        _save_token(response.json())
        token = json.loads(_token_path().read_text(encoding="utf-8"))
    return token["access_token"]


def _api(method: str, path: str, **kwargs):
    response = requests.request(method, API + path, headers={"Authorization": f"Bearer {_access_token()}"},
                                timeout=20, **kwargs)
    if response.status_code == 404 and path.startswith("/me/player"):
        raise ToolFailure("aucun appareil Spotify actif : ouvre l'appli Spotify")
    if response.status_code == 403 and path.startswith("/me/player"):
        raise ToolFailure("Spotify n'autorise le contrôle qu'avec un compte Premium")
    response.raise_for_status()
    return response.json() if response.content else {}


def _premium() -> bool:
    return _api("GET", "/me").get("product") == "premium"


# --- lecture -----------------------------------------------------------------

def _open_app(uri: str = "spotify:") -> None:
    if sys.platform == "win32":
        os.startfile(uri)  # type: ignore[attr-defined]
    else:
        webbrowser.open(uri)


def _device_id() -> str | None:
    """L'appareil où jouer : l'appli du PC de préférence (on l'ouvre si besoin)."""
    for attempt in range(12):
        devices = _api("GET", "/me/player/devices").get("devices", [])
        computer = [d for d in devices if d.get("type") == "Computer"]
        chosen = next((d for d in devices if d.get("is_active")), None) or (computer or devices or [None])[0]
        if chosen:
            return chosen["id"]
        if attempt == 0:
            _open_app()  # Spotify fermé : on l'ouvre et on attend qu'il se connecte
        time.sleep(1)
    return None


def _search(recherche: str, kind: str) -> dict | None:
    if kind == "playlist":
        mine = _api("GET", "/me/playlists", params={"limit": 50}).get("items", [])
        wanted = recherche.lower()
        found = next((p for p in mine if p and wanted in (p.get("name") or "").lower()), None)
        if found:
            return found
    if kind == "titres_likes":
        return {"uri": "spotify:collection:tracks", "name": "tes titres likés"}
    results = _api("GET", "/search", params={"q": recherche, "type": kind, "limit": 1, "market": "from_token"})
    items = (results.get(f"{kind}s") or {}).get("items") or []
    return next((i for i in items if i), None)


def spotify_jouer(recherche: str, type: str = "track", aleatoire: bool = False) -> str:
    kind = {"titre": "track", "artiste": "artist", "album": "album"}.get(type, type)
    if kind not in ("track", "artist", "album", "playlist", "titres_likes"):
        raise ToolFailure("type inconnu : track, artist, album, playlist ou titres_likes")
    item = _search(recherche, kind)
    if not item:
        raise ToolFailure(f"rien trouvé sur Spotify pour « {recherche} »")
    name = item.get("name", recherche)
    if kind == "track":
        name += " de " + ", ".join(a["name"] for a in item.get("artists", [])[:2])
    if not _premium():
        _open_app(item["uri"])
        return f"Compte gratuit : « {name} » est ouvert dans Spotify, il faut appuyer sur lecture."
    device = _device_id()
    if not device:
        raise ToolFailure("l'appli Spotify ne répond pas : ouvre-la puis réessaie")
    if kind != "titres_likes":
        _api("PUT", "/me/player/shuffle", params={"state": str(aleatoire).lower(), "device_id": device})
    body = {"uris": [item["uri"]]} if kind == "track" else {"context_uri": item["uri"]}
    if kind == "titres_likes":
        _api("PUT", "/me/player/shuffle", params={"state": "true", "device_id": device})
        body = {"context_uri": f"spotify:user:{_api('GET', '/me')['id']}:collection"}
    _api("PUT", "/me/player/play", params={"device_id": device}, json=body)
    return f"Lecture sur Spotify : {name}."


def play_best(recherche: str) -> str:
    """Commande vocale rapide « mets X » : playlist, album, artiste ou titre selon la phrase."""
    import re
    import unicodedata

    def plain(text: str) -> str:
        text = unicodedata.normalize("NFD", text.lower())
        return re.sub(r"[^a-z0-9 ]", "", "".join(c for c in text if unicodedata.category(c) != "Mn")).strip()

    query = re.sub(r"\s*(sur|avec|dans) spotify\s*$", "", recherche, flags=re.I).strip()
    words = plain(query)
    if re.match(r"(mes|mon) (titres|sons|musiques) (likes|aimes|preferes)|mes likes", words):
        return spotify_jouer("", "titres_likes")
    for prefix, kind in (("ma playlist ", "playlist"), ("la playlist ", "playlist"), ("playlist ", "playlist"),
                         ("l'album ", "album"), ("album ", "album")):
        if query.lower().startswith(prefix):
            return spotify_jouer(query[len(prefix):], kind)
    artist = _search(query, "artist")
    if artist and plain(artist.get("name", "")) == words:
        return spotify_jouer(query, "artist", aleatoire=True)
    return spotify_jouer(query, "track")


def spotify_controle(action: str, valeur: int = 50) -> str:
    if action == "j_aime":
        current = _api("GET", "/me/player/currently-playing")
        track = (current or {}).get("item")
        if not track:
            raise ToolFailure("rien n'est en cours de lecture")
        _api("PUT", "/me/tracks", params={"ids": track["id"]})
        return f"« {track['name']} » ajouté à tes titres likés."
    calls = {
        "pause": ("PUT", "/me/player/pause", {}),
        "reprendre": ("PUT", "/me/player/play", {}),
        "suivant": ("POST", "/me/player/next", {}),
        "precedent": ("POST", "/me/player/previous", {}),
        "volume": ("PUT", "/me/player/volume", {"volume_percent": max(0, min(100, valeur))}),
        "aleatoire_on": ("PUT", "/me/player/shuffle", {"state": "true"}),
        "aleatoire_off": ("PUT", "/me/player/shuffle", {"state": "false"}),
        "repeter": ("PUT", "/me/player/repeat", {"state": "context"}),
    }
    if action not in calls:
        raise ToolFailure(f"action inconnue : {', '.join([*calls, 'j_aime'])}")
    method, path, params = calls[action]
    _api(method, path, params=params)
    return f"Spotify : {action} fait."


def spotify_en_cours() -> str:
    current = _api("GET", "/me/player/currently-playing")
    track = (current or {}).get("item")
    if not track:
        return "Rien n'est en cours de lecture sur Spotify."
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    return f"« {track['name']} » de {artists}, album « {track.get('album', {}).get('name', '?')} »."


def spotify_playlists() -> str:
    items = _api("GET", "/me/playlists", params={"limit": 50}).get("items", [])
    return "\n".join(p["name"] for p in items if p) or "Aucune playlist."


def tools() -> list[Tool]:
    if not config.get("spotify_client_id"):
        return []
    return [
        Tool("spotify_jouer",
             "Lance sur Spotify un titre, un artiste, un album, une playlist (les siennes d'abord) ou ses "
             "titres likés. À préférer à jouer_musique quand Spotify est connecté.",
             {"recherche": string("ex. « Highway to Hell AC/DC », « Daft Punk », « ma playlist sport »"),
              "type": {"type": "string", "enum": ["track", "artist", "album", "playlist", "titres_likes"]},
              "aleatoire": boolean("lecture aléatoire")},
             spotify_jouer, ["recherche"]),
        Tool("spotify_controle",
             "Contrôle Spotify : pause, reprendre, suivant, precedent, volume (valeur 0-100), aleatoire_on, "
             "aleatoire_off, repeter, j_aime (ajoute le titre en cours aux titres likés).",
             {"action": {"type": "string", "enum": ["pause", "reprendre", "suivant", "precedent", "volume",
                                                    "aleatoire_on", "aleatoire_off", "repeter", "j_aime"]},
              "valeur": integer("volume en pourcentage, pour l'action volume")},
             spotify_controle, ["action"]),
        Tool("spotify_en_cours", "Dit quel titre passe sur Spotify.", {}, spotify_en_cours),
        Tool("spotify_playlists", "Liste les playlists Spotify de l'utilisateur.", {}, spotify_playlists),
    ]

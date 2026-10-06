"""Gmail et Google Agenda.

Connexion une seule fois avec `python -m jarvis --connecter-google` (voir README) :
le jeton est gardé dans ~/.jarvis/google_token.json, rien n'est envoyé ailleurs que chez Google.
"""

from __future__ import annotations

import base64
import datetime
import html
import re
from email.message import EmailMessage
from pathlib import Path

from .. import config
from . import Tool, ToolFailure, boolean, integer, string

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",  # lire, envoyer, brouillons (pas de suppression définitive)
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",     # chercher et lire Drive, Docs, Sheets
    "https://www.googleapis.com/auth/drive.file",         # créer des documents
    "https://www.googleapis.com/auth/tasks",              # Google Tasks
    "https://www.googleapis.com/auth/contacts.readonly",  # retrouver l'adresse d'un contact
    "https://www.googleapis.com/auth/youtube.readonly",   # tes playlists et abonnements YouTube
]


def client_secret_path() -> Path:
    return config.data_dir() / "google_client.json"


def token_path() -> Path:
    return config.data_dir() / "google_token.json"


def is_connected() -> bool:
    return token_path().exists()


def connect(client_file: str | None = None) -> None:
    """Ouvre le navigateur pour autoriser Jarvis sur ton compte Google."""
    import shutil

    from google_auth_oauthlib.flow import InstalledAppFlow

    if client_file:
        # Un glisser-déposer ou un collage ajoute souvent espaces, retours à la ligne ou guillemets.
        client_file = client_file.strip().strip("\"'").strip()
        shutil.copy(client_file, client_secret_path())
    if not client_secret_path().exists():
        raise FileNotFoundError(
            f"Fichier d'identifiants Google introuvable : {client_secret_path()}\n"
            "Télécharge-le depuis Google Cloud Console (voir README, étape Gmail)."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path()), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    token_path().write_text(creds.to_json(), encoding="utf-8")
    token_path().chmod(0o600)


def _service(api: str, version: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not is_connected():
        raise ToolFailure("Google n'est pas connecté. Lancer : python -m jarvis --connecter-google")
    import json

    granted = set(json.loads(token_path().read_text(encoding="utf-8")).get("scopes") or SCOPES)
    if not set(SCOPES) <= granted:
        raise ToolFailure("De nouvelles autorisations Google sont nécessaires (Drive, Tâches, YouTube…). "
                          "Relancer une fois : python -m jarvis --connecter-google")
    creds = Credentials.from_authorized_user_file(str(token_path()), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path().write_text(creds.to_json(), encoding="utf-8")
        else:
            raise ToolFailure("Autorisation Google expirée. Relancer : python -m jarvis --connecter-google")
    return build(api, version, credentials=creds, cache_discovery=False)


# --- Gmail -----------------------------------------------------------------

def _headers(msg: dict) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}


def _body(payload: dict) -> str:
    """Texte d'un mail : la partie text/plain, sinon le HTML nettoyé."""
    plain, rich = [], []

    def walk(part: dict) -> None:
        data = part.get("body", {}).get("data")
        mime = part.get("mimeType", "")
        if data and mime in ("text/plain", "text/html"):
            text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            (plain if mime == "text/plain" else rich).append(text)
        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)
    if plain:
        return "\n".join(plain)
    text = re.sub(r"<(script|style).*?</\1>", "", "\n".join(rich), flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</div>", "\n", text, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def chercher_mails(requete: str = "in:inbox", nombre: int = 10) -> str:
    gmail = _service("gmail", "v1")
    found = gmail.users().messages().list(userId="me", q=requete, maxResults=min(nombre, 25)).execute()
    lines = []
    for ref in found.get("messages", []):
        msg = gmail.users().messages().get(
            userId="me", id=ref["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        h = _headers(msg)
        unread = " [non lu]" if "UNREAD" in msg.get("labelIds", []) else ""
        lines.append(f"id={msg['id']}{unread} | {h.get('date', '')} | de : {h.get('from', '')} | "
                     f"sujet : {h.get('subject', '(sans sujet)')} | extrait : {html.unescape(msg.get('snippet', ''))}")
    return "\n".join(lines) or "Aucun mail ne correspond."


def lire_mail(id: str) -> str:
    gmail = _service("gmail", "v1")
    msg = gmail.users().messages().get(userId="me", id=id, format="full").execute()
    h = _headers(msg)
    body = re.sub(r"\n{3,}", "\n\n", _body(msg.get("payload", {}))).strip()
    if len(body) > 8000:
        body = body[:8000] + "\n[… mail tronqué]"
    return (f"De : {h.get('from', '')}\nÀ : {h.get('to', '')}\nDate : {h.get('date', '')}\n"
            f"Sujet : {h.get('subject', '')}\n\n{body}")


def _build_mail(gmail, a: str, sujet: str, corps: str, en_reponse_a: str | None) -> dict:
    mail = EmailMessage()
    mail["To"] = a
    mail["Subject"] = sujet
    mail.set_content(corps)
    body: dict = {}
    if en_reponse_a:
        original = gmail.users().messages().get(
            userId="me", id=en_reponse_a, format="metadata", metadataHeaders=["Message-ID", "Subject"]
        ).execute()
        message_id = _headers(original).get("message-id")
        if message_id:
            mail["In-Reply-To"] = message_id
            mail["References"] = message_id
        body["threadId"] = original["threadId"]
    body["raw"] = base64.urlsafe_b64encode(mail.as_bytes()).decode()
    return body


def envoyer_mail(a: str, sujet: str, corps: str, confirme_par_utilisateur: bool,
                 en_reponse_a: str | None = None) -> str:
    if not confirme_par_utilisateur:
        raise ToolFailure("Envoi refusé : lis d'abord le mail à l'utilisateur et attends son accord explicite.")
    gmail = _service("gmail", "v1")
    sent = gmail.users().messages().send(userId="me", body=_build_mail(gmail, a, sujet, corps, en_reponse_a)).execute()
    return f"Mail envoyé à {a} (id={sent['id']})."


def creer_brouillon(a: str, sujet: str, corps: str, en_reponse_a: str | None = None) -> str:
    gmail = _service("gmail", "v1")
    message = _build_mail(gmail, a, sujet, corps, en_reponse_a)
    gmail.users().drafts().create(userId="me", body={"message": message}).execute()
    return f"Brouillon enregistré dans Gmail pour {a}."


# --- Agenda ----------------------------------------------------------------

def _local_tz() -> datetime.tzinfo:
    return datetime.datetime.now().astimezone().tzinfo  # type: ignore[return-value]


def _parse_dt(value: str) -> datetime.datetime:
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ToolFailure(f"date invalide « {value} », format attendu AAAA-MM-JJTHH:MM") from exc
    return dt if dt.tzinfo else dt.replace(tzinfo=_local_tz())


def agenda_evenements(debut: str | None = None, jours: int = 1) -> str:
    calendar = _service("calendar", "v3")
    start = _parse_dt(debut) if debut else datetime.datetime.now().astimezone().replace(
        hour=0, minute=0, second=0, microsecond=0)
    end = start + datetime.timedelta(days=max(1, min(jours, 31)))
    events = calendar.events().list(
        calendarId="primary", timeMin=start.isoformat(), timeMax=end.isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=50,
    ).execute().get("items", [])
    lines = []
    for ev in events:
        when = ev["start"].get("dateTime", ev["start"].get("date"))
        until = ev["end"].get("dateTime", ev["end"].get("date"))
        place = f" | lieu : {ev['location']}" if ev.get("location") else ""
        lines.append(f"{when} → {until} | {ev.get('summary', '(sans titre)')}{place}")
    return "\n".join(lines) or "Aucun événement sur cette période."


def creer_evenement(titre: str, debut: str, fin: str, confirme_par_utilisateur: bool,
                    lieu: str = "", description: str = "") -> str:
    if not confirme_par_utilisateur:
        raise ToolFailure("Création refusée : annonce d'abord l'événement et attends l'accord explicite.")
    calendar = _service("calendar", "v3")
    body = {
        "summary": titre,
        "location": lieu,
        "description": description,
        "start": {"dateTime": _parse_dt(debut).isoformat()},
        "end": {"dateTime": _parse_dt(fin).isoformat()},
    }
    event = calendar.events().insert(calendarId="primary", body=body).execute()
    return f"Événement créé : {titre}, {debut} → {fin} ({event.get('htmlLink', '')})."


def tools() -> list[Tool]:
    if not is_connected():
        return []
    from .google_suite import tools as suite_tools

    confirm = boolean("true uniquement si l'utilisateur vient de dire oui explicitement à CETTE action")
    return [
        Tool("chercher_mails",
             "Cherche des mails Gmail. Syntaxe de recherche Gmail : is:unread, from:nom, "
             "newer_than:2d, subject:mot, has:attachment… Renvoie id, date, expéditeur, sujet, extrait.",
             {"requete": string("requête Gmail, par défaut in:inbox"),
              "nombre": integer("nombre maximum de mails (25 max)")},
             chercher_mails),
        Tool("lire_mail", "Lit le contenu complet d'un mail à partir de son id.",
             {"id": string("id du mail renvoyé par chercher_mails")}, lire_mail, ["id"]),
        Tool("envoyer_mail",
             "Envoie un mail depuis Gmail. NE L'APPELLE QU'APRÈS avoir annoncé destinataire, sujet "
             "et contenu à l'utilisateur et reçu son accord explicite.",
             {"a": string("adresse e-mail du destinataire"), "sujet": string("sujet"),
              "corps": string("texte du mail"), "confirme_par_utilisateur": confirm,
              "en_reponse_a": string("id du mail auquel on répond (optionnel, garde le fil)")},
             envoyer_mail, ["a", "sujet", "corps", "confirme_par_utilisateur"]),
        Tool("creer_brouillon", "Enregistre un mail en brouillon dans Gmail, sans l'envoyer.",
             {"a": string("adresse e-mail du destinataire"), "sujet": string("sujet"),
              "corps": string("texte du mail"), "en_reponse_a": string("id du mail d'origine (optionnel)")},
             creer_brouillon, ["a", "sujet", "corps"]),
        Tool("agenda_evenements", "Liste les événements de Google Agenda sur une période.",
             {"debut": string("début, format AAAA-MM-JJ ou AAAA-MM-JJTHH:MM (défaut : aujourd'hui)"),
              "jours": integer("nombre de jours à couvrir (défaut 1, max 31)")},
             agenda_evenements),
        Tool("creer_evenement",
             "Ajoute un événement à Google Agenda. NE L'APPELLE QU'APRÈS accord explicite de l'utilisateur.",
             {"titre": string("titre"), "debut": string("AAAA-MM-JJTHH:MM, heure locale"),
              "fin": string("AAAA-MM-JJTHH:MM, heure locale"), "confirme_par_utilisateur": confirm,
              "lieu": string("lieu (optionnel)"), "description": string("notes (optionnel)")},
             creer_evenement, ["titre", "debut", "fin", "confirme_par_utilisateur"]),
        *suite_tools(),
    ]

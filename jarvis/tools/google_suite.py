"""Le reste de la suite Google : Drive (Docs, Sheets…), Tâches, Contacts et YouTube."""

from __future__ import annotations

import datetime

from . import Tool, ToolFailure, integer, string
from .google import _parse_dt, _service

MAX_TEXT = 12000
EXPORTS = {
    "application/vnd.google-apps.document": ("text/plain", "Google Docs"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", "Google Sheets"),
    "application/vnd.google-apps.presentation": ("text/plain", "Google Slides"),
}


# --- Drive -----------------------------------------------------------------

def drive_chercher(recherche: str, nombre: int = 10) -> str:
    drive = _service("drive", "v3")
    safe = recherche.replace("\\", "\\\\").replace("'", "\\'")
    files = drive.files().list(
        q=f"(name contains '{safe}' or fullText contains '{safe}') and trashed = false",
        pageSize=min(nombre, 25), orderBy="modifiedTime desc",
        fields="files(id,name,mimeType,modifiedTime,webViewLink)",
    ).execute().get("files", [])
    lines = [f"id={f['id']} | {f['name']} | {EXPORTS.get(f['mimeType'], (None, f['mimeType']))[1]} | "
             f"modifié {f['modifiedTime'][:10]} | {f.get('webViewLink', '')}" for f in files]
    return "\n".join(lines) or "Aucun fichier ne correspond."


def drive_lire(id: str) -> str:
    drive = _service("drive", "v3")
    meta = drive.files().get(fileId=id, fields="name,mimeType").execute()
    mime = meta["mimeType"]
    if mime in EXPORTS:
        data = drive.files().export(fileId=id, mimeType=EXPORTS[mime][0]).execute()
    elif mime.startswith("text/") or mime in ("application/json", "text/csv"):
        data = drive.files().get_media(fileId=id).execute()
    else:
        raise ToolFailure(f"« {meta['name']} » est un fichier {mime} : je ne sais lire que les documents texte, "
                          "Docs, Sheets et Slides. Propose de l'ouvrir avec ouvrir_page.")
    text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT] + "\n[… document tronqué]"
    return f"{meta['name']}\n\n{text}"


def docs_creer(titre: str, contenu: str) -> str:
    from googleapiclient.http import MediaInMemoryUpload

    drive = _service("drive", "v3")
    media = MediaInMemoryUpload(contenu.encode("utf-8"), mimetype="text/plain")
    doc = drive.files().create(
        body={"name": titre, "mimeType": "application/vnd.google-apps.document"},
        media_body=media, fields="id,webViewLink",
    ).execute()
    return f"Document Google Docs créé : {titre} — {doc.get('webViewLink', '')}"


# --- Tâches ----------------------------------------------------------------

def taches_lister(nombre: int = 20) -> str:
    tasks = _service("tasks", "v1")
    items = tasks.tasks().list(tasklist="@default", showCompleted=False,
                               maxResults=min(nombre, 100)).execute().get("items", [])
    lines = [f"id={t['id']} | {t.get('title', '')}" + (f" | échéance {t['due'][:10]}" if t.get("due") else "")
             for t in items]
    return "\n".join(lines) or "Aucune tâche en cours."


def tache_ajouter(titre: str, echeance: str | None = None, notes: str = "") -> str:
    tasks = _service("tasks", "v1")
    body = {"title": titre, "notes": notes}
    if echeance:
        due = _parse_dt(echeance).astimezone(datetime.timezone.utc)
        body["due"] = due.strftime("%Y-%m-%dT00:00:00.000Z")  # Google Tasks ne garde que la date
    tasks.tasks().insert(tasklist="@default", body=body).execute()
    return f"Tâche ajoutée : {titre}" + (f" (pour le {echeance[:10]})" if echeance else "")


def tache_terminer(id: str) -> str:
    tasks = _service("tasks", "v1")
    tasks.tasks().patch(tasklist="@default", task=id, body={"status": "completed"}).execute()
    return "Tâche marquée comme faite."


# --- Contacts ----------------------------------------------------------------

def contacts_chercher(nom: str) -> str:
    people = _service("people", "v1")
    fields = "names,emailAddresses,phoneNumbers"
    # Google recommande une première recherche vide pour « réveiller » le cache.
    people.people().searchContacts(query="", readMask=fields).execute()
    results = people.people().searchContacts(query=nom, readMask=fields, pageSize=10).execute()
    lines = []
    for r in results.get("results", []):
        person = r["person"]
        name = (person.get("names") or [{}])[0].get("displayName", "?")
        emails = ", ".join(e["value"] for e in person.get("emailAddresses", []))
        phones = ", ".join(p["value"] for p in person.get("phoneNumbers", []))
        lines.append(f"{name} | mail : {emails or '—'} | tél : {phones or '—'}")
    return "\n".join(lines) or f"Aucun contact ne correspond à « {nom} »."


# --- YouTube -----------------------------------------------------------------

def youtube_mes_playlists() -> str:
    youtube = _service("youtube", "v3")
    items = youtube.playlists().list(part="snippet,contentDetails", mine=True, maxResults=50).execute()
    lines = [f"{p['snippet']['title']} ({p['contentDetails']['itemCount']} vidéos) | "
             f"https://www.youtube.com/playlist?list={p['id']}" for p in items.get("items", [])]
    return "\n".join(lines) or "Aucune playlist sur ce compte YouTube."


def youtube_abonnements(nombre: int = 25) -> str:
    youtube = _service("youtube", "v3")
    items = youtube.subscriptions().list(part="snippet", mine=True, maxResults=min(nombre, 50),
                                         order="relevance").execute()
    lines = [f"{s['snippet']['title']} | https://www.youtube.com/channel/{s['snippet']['resourceId']['channelId']}"
             for s in items.get("items", [])]
    return "\n".join(lines) or "Aucun abonnement."


def tools() -> list[Tool]:
    return [
        Tool("drive_chercher",
             "Cherche des fichiers dans Google Drive (Docs, Sheets, Slides, PDF…) par nom ou contenu.",
             {"recherche": string("mots à chercher"), "nombre": integer("maximum de résultats (défaut 10)")},
             drive_chercher, ["recherche"]),
        Tool("drive_lire", "Lit le contenu d'un Google Docs, Sheets (en CSV), Slides ou fichier texte de Drive.",
             {"id": string("id renvoyé par drive_chercher")}, drive_lire, ["id"]),
        Tool("docs_creer", "Crée un nouveau document Google Docs avec le texte fourni (notes, compte rendu…).",
             {"titre": string("titre du document"), "contenu": string("texte du document")},
             docs_creer, ["titre", "contenu"]),
        Tool("taches_lister", "Liste les tâches en cours de Google Tasks (la liste de choses à faire).",
             {"nombre": integer("maximum (défaut 20)")}, taches_lister),
        Tool("tache_ajouter", "Ajoute une tâche à Google Tasks (« rappelle-moi de… », « ajoute à ma liste… »).",
             {"titre": string("la tâche"), "echeance": string("date AAAA-MM-JJ (optionnel)"),
              "notes": string("détails (optionnel)")},
             tache_ajouter, ["titre"]),
        Tool("tache_terminer", "Marque une tâche Google Tasks comme faite.",
             {"id": string("id renvoyé par taches_lister")}, tache_terminer, ["id"]),
        Tool("contacts_chercher",
             "Cherche un contact Google (adresse mail, téléphone) à partir d'un nom ou prénom.",
             {"nom": string("nom ou prénom")}, contacts_chercher, ["nom"]),
        Tool("youtube_mes_playlists",
             "Liste les playlists du compte YouTube de l'utilisateur, avec leur lien (à ouvrir avec ouvrir_page).",
             {}, youtube_mes_playlists),
        Tool("youtube_abonnements", "Liste les chaînes YouTube auxquelles l'utilisateur est abonné.",
             {"nombre": integer("maximum (défaut 25)")}, youtube_abonnements),
    ]

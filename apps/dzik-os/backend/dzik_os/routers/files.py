from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from .. import file_safety
from ..authz import active_relationship, coach_can_access_client, resolve_client_access
from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..models import Document, ProgressPhoto, StoredFile, User, new_id
from ..schemas import DocumentIn
from ..security import current_user, require_role
from ..storage import storage

router = APIRouter(prefix="/api", tags=["files"])


@router.post("/files", status_code=201)
async def upload_file(
    file: UploadFile,
    client_id: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Upload pliku. Właścicielem danych jest klient, którego plik dotyczy
    (client_id dla uploadu trenera; domyślnie sam wgrywający)."""
    owner_id = user.id
    if client_id is not None and client_id != user.id:
        resolve_client_access(db, user, client_id, action="write")
        owner_id = client_id
    stored = await storage.save_upload(db, file, owner_user_id=owner_id, uploaded_by=user.id)
    db.commit()
    return {
        "id": stored.id,
        "filename": stored.filename,
        "content_type": stored.content_type,
        "size_bytes": stored.size_bytes,
        "sha256": stored.sha256,
    }


def _thread_attachment_access(db: Session, user: User, file_id: str) -> bool:
    """Załącznik wiadomości: klient z wątku widzi go zawsze (jak treść
    wiadomości); trener z wątku — tylko w ramach aktywnej relacji i
    nieocofniętej zgody (dokładnie ten sam kontrakt co
    authz.require_thread_party; sensitive=False, bo treść wiadomości nie
    jest daną zdrowotną)."""
    from ..models import Message, MessageThread

    threads = (
        db.query(MessageThread)
        .join(Message, Message.thread_id == MessageThread.id)
        .filter(
            Message.file_id == file_id,
            (MessageThread.client_id == user.id) | (MessageThread.coach_id == user.id),
        )
        .all()
    )
    for thread in threads:
        if thread.client_id == user.id:
            return True
        if thread.coach_id == user.id and coach_can_access_client(
            db, user.id, thread.client_id, sensitive=False
        ):
            return True
    return False


def _knowledge_attachment_access(db: Session, user: User, file_id: str) -> bool:
    """Załącznik AKTYWNEGO wpisu bazy wiedzy: broadcast trenera do jego
    aktywnie prowadzonych klientów (relacja ACTIVE, bez bramki zgody
    health_data — to materiał trenera, nie dane klienta; ten sam kontrakt
    co GET /api/me/knowledge)."""
    from ..models import KnowledgeItem

    items = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.file_id == file_id, KnowledgeItem.status == "ACTIVE")
        .all()
    )
    return any(active_relationship(db, item.coach_id, user.id) for item in items)


@router.get("/files/{file_id}")
def download_file(
    file_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Pobranie pliku. Dostęp mają wyłącznie:
    * właściciel danych (owner_user_id),
    * strona wątku wiadomości, w którym plik jest załącznikiem
      (trener: tylko przy aktywnej relacji),
    * klient aktywnie prowadzony przez trenera — dla załączników
      AKTYWNYCH wpisów bazy wiedzy tego trenera,
    * trener z aktywną relacją ORAZ aktywną zgodą coaching/health_data
      (resolve_client_access) — dla wszystkich pozostałych plików klienta.
    Każda odmowa to 404 (nie ujawniamy istnienia zasobu)."""
    stored = db.get(StoredFile, file_id)
    if stored is None or stored.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if (
        stored.owner_user_id != user.id
        and not _thread_attachment_access(db, user, file_id)
        and not _knowledge_attachment_access(db, user, file_id)
    ):
        resolve_client_access(db, user, stored.owner_user_id)
    data = storage.read(stored)
    # Sanityzacja także przy odczycie — obejmuje pliki zapisane przed
    # wprowadzeniem sanityzacji na uploadzie.
    filename = file_safety.sanitize_filename(
        stored.filename, settings.ALLOWED_UPLOAD_TYPES.get(stored.content_type, "")
    )
    # X-Content-Type-Options: nosniff oraz Cache-Control: no-store (dane
    # prywatne — nigdy do cache) gwarantuje globalnie SecurityHeadersMiddleware
    # (http_headers.py) — nie duplikujemy ich tutaj.
    return Response(
        content=data,
        media_type=stored.content_type,
        headers={
            "Content-Disposition": file_safety.content_disposition("inline", filename),
        },
    )


@router.post("/documents", status_code=201)
def create_document(
    body: DocumentIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, coach, body.client_id, action="write")
    stored = db.get(StoredFile, body.file_id)
    if stored is None or stored.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Nie znaleziono pliku")
    if stored.owner_user_id != body.client_id:
        # Dokument klienta musi wskazywać plik, którego właścicielem danych
        # jest ten klient (upload z client_id) — inaczej podpięcie cudzego
        # pliku nadawałoby dostęp między klientami.
        raise HTTPException(status_code=422, detail="Plik nie należy do tego klienta")
    doc = Document(
        id=new_id("DOC"),
        client_id=body.client_id,
        file_id=body.file_id,
        title=body.title,
        category=body.category,
        uploaded_by=coach.id,
    )
    db.add(doc)
    record_event(
        db,
        action="DOCUMENT_SHARED",
        actor_id=coach.id,
        subject_ids=[body.client_id],
        payload={"document_id": doc.id, "title": doc.title, "category": doc.category},
        summary=f"Udostępniono dokument: {doc.title}",
    )
    db.commit()
    return {"id": doc.id}


@router.get("/clients/{client_id}/documents")
def list_documents(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    rows = (
        db.query(Document)
        .filter(Document.client_id == client_id, Document.status == "ACTIVE")
        .order_by(Document.created_at.desc())
        .all()
    )
    return {
        "documents": [
            {
                "id": d.id, "file_id": d.file_id, "title": d.title,
                "category": d.category, "uploaded_by": d.uploaded_by,
                "created_at": d.created_at,
            }
            for d in rows
        ]
    }


@router.get("/clients/{client_id}/photos")
def list_photos(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    rows = (
        db.query(ProgressPhoto)
        .filter(ProgressPhoto.client_id == client_id)
        .order_by(ProgressPhoto.taken_at.desc())
        .all()
    )
    return {
        "photos": [
            {
                "id": p.id, "file_id": p.file_id, "checkin_id": p.checkin_id,
                "taken_at": p.taken_at, "note": p.note,
            }
            for p in rows
        ]
    }

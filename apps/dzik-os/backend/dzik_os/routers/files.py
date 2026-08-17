from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from ..authz import resolve_client_access
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


def _is_thread_attachment_participant(db: Session, user: User, file_id: str) -> bool:
    """Załącznik wiadomości może pobrać każda strona wątku (np. plik wysłany
    przez trenera należy do trenera, ale klient z wątku musi go zobaczyć)."""
    from ..models import Message, MessageThread

    return (
        db.query(Message)
        .join(MessageThread, Message.thread_id == MessageThread.id)
        .filter(
            Message.file_id == file_id,
            (MessageThread.client_id == user.id) | (MessageThread.coach_id == user.id),
        )
        .count()
        > 0
    )


@router.get("/files/{file_id}")
def download_file(
    file_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stored = db.get(StoredFile, file_id)
    if stored is None or stored.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if stored.owner_user_id != user.id and not _is_thread_attachment_participant(
        db, user, file_id
    ):
        resolve_client_access(db, user, stored.owner_user_id)
    data = storage.read(stored)
    return Response(
        content=data,
        media_type=stored.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{stored.filename}"',
            "X-Content-Type-Options": "nosniff",
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
    if stored is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono pliku")
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

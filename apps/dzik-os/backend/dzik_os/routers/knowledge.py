"""Baza wiedzy trenera — artykuły, linki i pliki, którymi wspiera
podopiecznych. Broadcast do wszystkich aktywnie prowadzonych klientów;
treść i odpowiedzialność merytoryczna należą do trenera (system tylko
przechowuje i pokazuje — nie generuje ani nie ocenia treści)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import require_attachable_file, require_owned_resource
from ..db import get_db
from ..hos_bridge import record_event
from ..models import CoachClientRelationship, KnowledgeItem, User, new_id, now_iso
from ..schemas import KnowledgeItemIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["knowledge"])


def _out(item: KnowledgeItem) -> dict:
    return {
        "id": item.id, "coach_id": item.coach_id, "title": item.title,
        "category": item.category, "body": item.body,
        "external_url": item.external_url, "file_id": item.file_id,
        "pinned": item.pinned, "status": item.status,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }


def _check_file(db: Session, coach: User, file_id: str | None) -> None:
    """Załącznik bazy wiedzy to broadcast do wszystkich aktywnych klientów
    trenera — wolno podpiąć wyłącznie plik, którego właścicielem danych
    jest sam trener (nigdy plik należący do któregoś z klientów)."""
    if file_id:
        require_attachable_file(db, coach, file_id, owner_id=coach.id)


@router.post("/coach/knowledge", status_code=201)
def create_knowledge_item(
    body: KnowledgeItemIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    _check_file(db, coach, body.file_id)
    item = KnowledgeItem(
        id=new_id("KNW"), coach_id=coach.id, title=body.title, category=body.category,
        body=body.body, external_url=body.external_url, file_id=body.file_id,
        pinned=body.pinned, created_by=coach.id,
    )
    db.add(item)
    record_event(
        db, action="KNOWLEDGE_ITEM_CREATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"item_id": item.id, "title": item.title, "category": item.category},
        summary=f"Baza wiedzy: dodano „{item.title}”",
    )
    db.commit()
    return _out(item)


@router.get("/coach/knowledge")
def list_own_knowledge(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    rows = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.coach_id == coach.id)
        .order_by(KnowledgeItem.pinned.desc(), KnowledgeItem.created_at.desc())
        .all()
    )
    return {"items": [_out(i) for i in rows]}


@router.put("/coach/knowledge/{item_id}")
def update_knowledge_item(
    item_id: str,
    body: KnowledgeItemIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = require_owned_resource(
        db.get(KnowledgeItem, item_id), actor=coach, resource=f"knowledge:{item_id}"
    )
    _check_file(db, coach, body.file_id)
    item.title, item.category, item.body = body.title, body.category, body.body
    item.external_url, item.file_id, item.pinned = body.external_url, body.file_id, body.pinned
    item.updated_at = now_iso()
    record_event(
        db, action="KNOWLEDGE_ITEM_UPDATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"item_id": item.id, "title": item.title},
        summary=f"Baza wiedzy: zaktualizowano „{item.title}”",
    )
    db.commit()
    return _out(item)


@router.post("/coach/knowledge/{item_id}/status")
def set_knowledge_status(
    item_id: str,
    status: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    if status not in {"ACTIVE", "ARCHIVED"}:
        raise HTTPException(status_code=422, detail="Nieprawidłowy status")
    item = require_owned_resource(
        db.get(KnowledgeItem, item_id), actor=coach, resource=f"knowledge:{item_id}"
    )
    item.status = status
    item.updated_at = now_iso()
    db.commit()
    return {"ok": True, "status": status}


@router.get("/me/knowledge")
def list_knowledge_for_client(
    user: User = Depends(current_user), db: Session = Depends(get_db)
):
    coach_ids = [
        r.coach_id
        for r in db.query(CoachClientRelationship)
        .filter_by(client_id=user.id, status="ACTIVE")
        .all()
    ]
    if not coach_ids:
        return {"items": []}
    rows = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.coach_id.in_(coach_ids), KnowledgeItem.status == "ACTIVE")
        .order_by(KnowledgeItem.pinned.desc(), KnowledgeItem.created_at.desc())
        .all()
    )
    return {"items": [_out(i) for i in rows]}

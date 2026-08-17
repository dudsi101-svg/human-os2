from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai_provider import provider as ai_provider
from ..authz import resolve_client_access, require_client_self
from ..db import get_db
from ..hos_bridge import record_event
from ..models import CheckinRevision, ProgressPhoto, User, WeeklyCheckin, new_id, now_iso
from ..schemas import CheckinIn, CheckinReviewIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["checkins"])


def _checkin_out(db: Session, c: WeeklyCheckin) -> dict:
    photos = db.query(ProgressPhoto).filter(ProgressPhoto.checkin_id == c.id).all()
    return {
        "id": c.id,
        "client_id": c.client_id,
        "week_start": c.week_start,
        "payload": json.loads(c.payload_json),
        "status": c.status,
        "revision": c.revision,
        "submitted_at": c.submitted_at,
        "updated_at": c.updated_at,
        "coach_response": c.coach_response,
        "reviewed_by": c.reviewed_by,
        "reviewed_at": c.reviewed_at,
        "photo_ids": [p.file_id for p in photos],
    }


@router.post("/checkins", status_code=201)
def submit_checkin(
    body: CheckinIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Raport tygodniowy klienta. Poprawka istniejącego raportu tworzy nową
    rewizję — poprzednia treść zostaje zachowana (CheckinRevision)."""
    client_id = require_client_self(db, user)
    payload = body.model_dump(exclude={"photo_ids"})
    existing = (
        db.query(WeeklyCheckin)
        .filter_by(client_id=client_id, week_start=body.week_start)
        .one_or_none()
    )
    if existing is not None:
        if existing.status == "REVIEWED":
            raise HTTPException(
                status_code=409,
                detail="Raport został już oceniony przez trenera — wyślij nowy raport "
                "w kolejnym tygodniu lub napisz wiadomość.",
            )
        db.add(
            CheckinRevision(
                id=new_id("CKR"),
                checkin_id=existing.id,
                revision=existing.revision,
                payload_json=existing.payload_json,
            )
        )
        existing.payload_json = json.dumps(payload, ensure_ascii=False)
        existing.revision += 1
        existing.updated_at = now_iso()
        checkin = existing
        action = "CHECKIN_CORRECTED"
    else:
        checkin = WeeklyCheckin(
            id=new_id("CKN"),
            client_id=client_id,
            week_start=body.week_start,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
        db.add(checkin)
        action = "CHECKIN_SUBMITTED"
    for file_id in body.photo_ids:
        db.add(
            ProgressPhoto(
                id=new_id("PHT"),
                client_id=client_id,
                file_id=file_id,
                checkin_id=checkin.id,
                taken_at=body.week_start,
            )
        )
    record_event(
        db,
        action=action,
        actor_id=user.id,
        subject_ids=[client_id],
        payload={"checkin_id": checkin.id, "week_start": body.week_start,
                 "revision": checkin.revision},
        summary=f"Raport tygodniowy {body.week_start} (rewizja {checkin.revision})",
    )
    db.commit()
    return {"id": checkin.id, "revision": checkin.revision}


@router.get("/clients/{client_id}/checkins")
def list_checkins(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    rows = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.client_id == client_id)
        .order_by(WeeklyCheckin.week_start.desc())
        .all()
    )
    return {"checkins": [_checkin_out(db, c) for c in rows]}


@router.get("/checkins/{checkin_id}/revisions")
def checkin_revisions(
    checkin_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    checkin = db.get(WeeklyCheckin, checkin_id)
    if checkin is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, user, checkin.client_id)
    rows = (
        db.query(CheckinRevision)
        .filter(CheckinRevision.checkin_id == checkin_id)
        .order_by(CheckinRevision.revision)
        .all()
    )
    return {
        "revisions": [
            {"revision": r.revision, "payload": json.loads(r.payload_json),
             "created_at": r.created_at}
            for r in rows
        ]
    }


@router.post("/checkins/{checkin_id}/review")
def review_checkin(
    checkin_id: str,
    body: CheckinReviewIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    checkin = db.get(WeeklyCheckin, checkin_id)
    if checkin is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, coach, checkin.client_id, action="write")
    checkin.coach_response = body.coach_response
    checkin.status = "REVIEWED"
    checkin.reviewed_by = coach.id
    checkin.reviewed_at = now_iso()
    record_event(
        db,
        action="CHECKIN_REVIEWED",
        actor_id=coach.id,
        subject_ids=[checkin.client_id],
        payload={"checkin_id": checkin.id, "week_start": checkin.week_start},
        summary=f"Odpowiedź trenera na raport {checkin.week_start}",
    )
    db.commit()
    return {"ok": True}


@router.post("/checkins/{checkin_id}/ai-summary")
def ai_summary(
    checkin_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Propozycja AI: streszczenie raportu + szkic odpowiedzi do edycji.
    NIGDY nie zapisuje niczego automatycznie — trener sam decyduje, czy i
    co wysłać przez /checkins/{id}/review. Bez skonfigurowanego dostawcy
    (domyślnie) zwraca available=false z jawnym wyjaśnieniem, zamiast
    udawać, że funkcja działa."""
    checkin = db.get(WeeklyCheckin, checkin_id)
    if checkin is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, coach, checkin.client_id, action="write")
    if not ai_provider.enabled:
        return {
            "available": False,
            "reason": "Funkcja podsumowań AI wymaga konfiguracji przez "
            "administratora (klucz dostawcy poza repozytorium — patrz "
            "docs/DEFERRED_FEATURES.md).",
        }
    result = ai_provider.summarize_checkin(
        payload=json.loads(checkin.payload_json), history_note=None
    )
    if result is None:
        return {"available": False, "reason": "Dostawca AI nie zwrócił odpowiedzi."}
    record_event(
        db,
        action="AI_SUMMARY_REQUESTED",
        actor_id=coach.id,
        subject_ids=[checkin.client_id],
        payload={"checkin_id": checkin.id, "provider": ai_provider.name},
        summary=f"Trener poprosił o podsumowanie AI raportu {checkin.week_start}",
    )
    db.commit()
    return {
        "available": True,
        "summary": result.summary,
        "draft_response": result.draft_response,
        "flags": result.flags,
    }

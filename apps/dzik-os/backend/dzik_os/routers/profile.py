from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..authz import (
    DOMAIN_COLLABORATION,
    DOMAIN_HEALTH,
    DOMAIN_NUTRITION,
    DOMAIN_TRAINING,
    coach_can_access_client,
    deny,
    resolve_client_access,
)
from ..db import get_db
from ..hos_bridge import record_event
from ..models import Goal, ProfileField, User, new_id, now_iso
from ..schemas import GoalIn, GoalStatusIn, ProfileFieldIn
from ..security import current_user

router = APIRouter(prefix="/api/clients/{client_id}", tags=["profile"])

# Pola wrażliwe profilu i domena zgody, która nimi rządzi. Pole wrażliwe
# spoza tej mapy podlega domyślnie domenie zdrowotnej (bezpieczny domysł).
SENSITIVE_FIELD_DOMAINS = {
    "alergie": DOMAIN_NUTRITION,
    "preferencje_zywieniowe": DOMAIN_NUTRITION,
    "urazy": DOMAIN_HEALTH,
}


def _sensitive_field_domain(field_key: str) -> str:
    return SENSITIVE_FIELD_DOMAINS.get(field_key, DOMAIN_HEALTH)


def _visible_fields(db: Session, user: User, client_id: str, rows: list) -> list:
    """Klient widzi wszystko; trener widzi pola wrażliwe tylko w zakresie
    aktywnej zgody ich domeny (cofnięcie zgody „żywienie i alergie" chowa
    alergie, nie cały profil)."""
    if user.id == client_id:
        return rows
    allowed_cache: dict[str, bool] = {}

    def allowed(domain: str) -> bool:
        if domain not in allowed_cache:
            allowed_cache[domain] = coach_can_access_client(
                db, user.id, client_id, domain=domain
            )
        return allowed_cache[domain]

    return [
        f for f in rows
        if not f.sensitive or allowed(_sensitive_field_domain(f.field_key))
    ]


def _field_out(f: ProfileField) -> dict:
    return {
        "field_key": f.field_key,
        "value": f.value,
        "source": f.source,
        "author_id": f.author_id,
        "purpose": f.purpose,
        "version": f.version,
        "is_current": f.is_current,
        "sensitive": f.sensitive,
        "created_at": f.created_at,
    }


@router.get("/profile")
def get_profile(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, domain=DOMAIN_COLLABORATION)
    rows = (
        db.query(ProfileField)
        .filter(ProfileField.client_id == client_id, ProfileField.is_current.is_(True))
        .order_by(ProfileField.field_key)
        .all()
    )
    rows = _visible_fields(db, user, client_id, rows)
    return {"client_id": client_id, "fields": [_field_out(f) for f in rows]}


@router.get("/profile/history")
def profile_history(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, domain=DOMAIN_COLLABORATION)
    rows = (
        db.query(ProfileField)
        .filter(ProfileField.client_id == client_id)
        .order_by(ProfileField.field_key, ProfileField.version)
        .all()
    )
    rows = _visible_fields(db, user, client_id, rows)
    return {"client_id": client_id, "fields": [_field_out(f) for f in rows]}


@router.put("/profile")
def set_profile_fields(
    client_id: str,
    fields: list[ProfileFieldIn],
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Aktualizacja pól profilu — append-only: poprzednia wartość zostaje
    jako wersja historyczna. Źródło zależy od tego, kto zapisuje."""
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_COLLABORATION)
    source = "CLIENT_DECLARED" if user.id == client_id else "COACH_ENTERED"
    if user.id != client_id:
        # Zapis pola wrażliwego przez trenera wymaga aktywnej zgody
        # domeny tego pola (klient zapisuje swoje pola zawsze).
        for item in fields:
            if item.sensitive and not coach_can_access_client(
                db, user.id, client_id, action="write",
                domain=_sensitive_field_domain(item.field_key),
            ):
                deny(user.id, f"profile_field:{item.field_key}")
    changed: list[str] = []
    for item in fields:
        current = (
            db.query(ProfileField)
            .filter(
                ProfileField.client_id == client_id,
                ProfileField.field_key == item.field_key,
                ProfileField.is_current.is_(True),
            )
            .one_or_none()
        )
        if current is not None and current.value == item.value:
            continue
        version = 1
        if current is not None:
            current.is_current = False
            version = current.version + 1
        db.add(
            ProfileField(
                id=new_id("PRF"),
                client_id=client_id,
                field_key=item.field_key,
                value=item.value,
                source=source,
                author_id=user.id,
                purpose=item.purpose,
                version=version,
                sensitive=item.sensitive,
            )
        )
        changed.append(item.field_key)
    receipt = None
    if changed:
        receipt = record_event(
            db,
            action="PROFILE_UPDATED",
            actor_id=user.id,
            subject_ids=[client_id],
            payload={"fields": changed, "source": source},
            summary=f"Aktualizacja profilu: {', '.join(changed)}",
        )
    db.commit()
    return {"updated": changed, "receipt_id": receipt.id if receipt else None}


@router.get("/goals")
def list_goals(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, domain=DOMAIN_TRAINING)
    rows = db.query(Goal).filter(Goal.client_id == client_id).order_by(Goal.created_at).all()
    return {
        "goals": [
            {
                "id": g.id, "title": g.title, "description": g.description,
                "kind": g.kind, "target_date": g.target_date, "status": g.status,
                "created_by": g.created_by, "created_at": g.created_at,
            }
            for g in rows
        ]
    }


@router.post("/goals", status_code=201)
def create_goal(
    client_id: str,
    body: GoalIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_TRAINING)
    goal = Goal(
        id=new_id("GOL"),
        client_id=client_id,
        title=body.title,
        description=body.description,
        kind=body.kind,
        target_date=body.target_date,
        created_by=user.id,
    )
    db.add(goal)
    record_event(
        db,
        action="GOAL_CREATED",
        actor_id=user.id,
        subject_ids=[client_id],
        payload={"goal_id": goal.id, "title": goal.title, "kind": goal.kind},
        summary=f"Nowy cel: {goal.title}",
    )
    db.commit()
    return {"id": goal.id}


@router.post("/goals/{goal_id}/status")
def set_goal_status(
    client_id: str,
    goal_id: str,
    body: GoalStatusIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_TRAINING)
    goal = db.get(Goal, goal_id)
    if goal is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if goal.client_id != client_id:
        # goal_id innego klienta podstawiony pod własny client_id (IDOR).
        deny(user.id, f"goal:{goal_id}")
    previous = goal.status
    goal.status = body.status
    goal.updated_at = now_iso()
    goal.version += 1
    record_event(
        db,
        action="GOAL_STATUS_CHANGED",
        actor_id=user.id,
        subject_ids=[client_id],
        payload={"goal_id": goal.id, "from": previous, "to": body.status},
        summary=f"Cel '{goal.title}': {previous} → {body.status}",
    )
    db.commit()
    return {"ok": True}

"""Subskrypcje Web Push — jawny opt-in użytkownika, wyłączane jednym
przyciskiem. Patrz push_service (zasady treści powiadomień)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import push_service
from ..db import get_db
from ..hos_bridge import record_event
from ..models import PushSubscription, User, new_id
from ..security import current_user

router = APIRouter(prefix="/api/push", tags=["push"])


class SubscriptionKeysIn(BaseModel):
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=100)


class SubscribeIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000)
    keys: SubscriptionKeysIn


class UnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000)


@router.get("/public-key")
def public_key(user: User = Depends(current_user)):
    return {"key": push_service.public_key_b64url()}


@router.post("/subscribe", status_code=201)
def subscribe(
    body: SubscribeIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(PushSubscription).filter_by(endpoint=body.endpoint).one_or_none()
    )
    if existing is not None:
        # Endpoint jest unikalny per przeglądarka — przejmuje go aktualnie
        # zalogowany użytkownik (np. zmiana konta na tym samym telefonie).
        # Endpoint push to niezgadywalny URL-capability wygenerowany przez
        # przeglądarkę, a treści szyfrowane są kluczami subskrybenta —
        # przejęcie wymaga fizycznego dostępu do tej przeglądarki. Zmiana
        # właściciela jest mimo to audytowana (wykrywalność nadużycia).
        if existing.user_id != user.id:
            record_event(
                db, action="PUSH_ENDPOINT_REBOUND", actor_id=user.id,
                subject_ids=[user.id, existing.user_id],
                payload={"endpoint_prefix": body.endpoint[:60],
                         "previous_user_id": existing.user_id},
                summary="Endpoint push przypisany do innego konta (zmiana "
                "użytkownika w tej samej przeglądarce)",
            )
        existing.user_id = user.id
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
    else:
        db.add(PushSubscription(
            id=new_id("PSH"), user_id=user.id, endpoint=body.endpoint,
            p256dh=body.keys.p256dh, auth=body.keys.auth,
        ))
    record_event(
        db, action="PUSH_SUBSCRIBED", actor_id=user.id, subject_ids=[user.id],
        payload={"endpoint_prefix": body.endpoint[:60]},
        summary="Włączono powiadomienia push",
    )
    db.commit()
    return {"ok": True}


@router.post("/unsubscribe")
def unsubscribe(
    body: UnsubscribeIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(PushSubscription)
        .filter_by(endpoint=body.endpoint, user_id=user.id)
        .one_or_none()
    )
    if row is not None:
        db.delete(row)
        record_event(
            db, action="PUSH_UNSUBSCRIBED", actor_id=user.id, subject_ids=[user.id],
            payload={"endpoint_prefix": body.endpoint[:60]},
            summary="Wyłączono powiadomienia push",
        )
        db.commit()
    return {"ok": True}

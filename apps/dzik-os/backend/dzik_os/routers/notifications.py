"""Centrum powiadomień + preferencje doręczeń (kategoria × kanał),
ciche godziny, dni aktywne, strefa czasowa i częstotliwość raportu.

Lista centrum zawiera wyłącznie powiadomienia doręczone kanałem CENTER
(pełna treść — użytkownik jest uwierzytelniony). Preferencje i ustawienia
zmienia wyłącznie sam użytkownik; zmiana jest audytowana bez treści."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..hos_bridge import record_event
from ..models import (
    Notification,
    NotificationPreference,
    NotificationSetting,
    User,
    new_id,
    now_iso,
)
from ..notifications import CATEGORIES, CHANNEL_DEFAULTS, CHANNELS, get_settings
from ..security import current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

_TIME_RE = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"


def _notification_out(n: Notification) -> dict:
    return {
        "id": n.id,
        "category": n.category,
        "category_label": CATEGORIES[n.category].label if n.category in CATEGORIES
        else n.category,
        "title": n.title,
        "body": n.body,
        "url": n.url,
        "created_at": n.created_at,
        "sent_at": n.sent_at,
        "read_at": n.read_at,
    }


@router.get("")
def list_notifications(
    category: str | None = Query(default=None),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.status == "SENT",
        Notification.channels.like("%center%"),
    )
    if category:
        q = q.filter(Notification.category == category)
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.sent_at.desc()).limit(limit).all()
    unread = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.status == "SENT",
            Notification.channels.like("%center%"),
            Notification.read_at.is_(None),
        )
        .count()
    )
    return {"notifications": [_notification_out(n) for n in rows], "unread": unread}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if n.read_at is None:
        n.read_at = now_iso()
        db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.status == "SENT",
            Notification.read_at.is_(None),
        )
        .all()
    )
    stamp = now_iso()
    for n in rows:
        n.read_at = stamp
    db.commit()
    return {"ok": True, "marked": len(rows)}


class PreferenceIn(BaseModel):
    category: str
    channel: str
    enabled: bool


class SettingsIn(BaseModel):
    quiet_hours_start: str | None = Field(default=None, pattern=_TIME_RE)
    quiet_hours_end: str | None = Field(default=None, pattern=_TIME_RE)
    active_days: str | None = None  # CSV dni ISO (1=pn ... 7=nd)
    raport_frequency: str | None = None  # DAILY / WEEKLY
    timezone: str | None = None  # IANA, np. "Europe/Warsaw"
    preferences: list[PreferenceIn] = []


@router.get("/settings")
def get_notification_settings(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    setting = get_settings(db, user.id)
    prefs = {
        f"{c}:{ch}": CHANNEL_DEFAULTS[ch]
        for c in CATEGORIES
        for ch in CHANNELS
    }
    for row in db.query(NotificationPreference).filter_by(user_id=user.id).all():
        prefs[f"{row.category}:{row.channel}"] = bool(row.enabled)
    return {
        "categories": [
            {"key": c.key, "label": c.label, "push_title": c.push_title,
             "url": c.default_url}
            for c in CATEGORIES.values()
        ],
        "channels": list(CHANNELS),
        "preferences": prefs,
        "settings": {
            "quiet_hours_start": setting.quiet_hours_start,
            "quiet_hours_end": setting.quiet_hours_end,
            "active_days": setting.active_days,
            "raport_frequency": setting.raport_frequency,
            "timezone": user.timezone,
        },
    }


@router.put("/settings")
def update_notification_settings(
    body: SettingsIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if body.timezone is not None and body.timezone != "":
        try:
            ZoneInfo(body.timezone)
        except (KeyError, ValueError):  # ZoneInfoNotFoundError ⊂ KeyError
            raise HTTPException(
                status_code=422, detail="Nieznana strefa czasowa"
            ) from None
    if body.active_days is not None:
        days = [d.strip() for d in body.active_days.split(",") if d.strip()]
        if not days or not all(d in {"1", "2", "3", "4", "5", "6", "7"} for d in days):
            raise HTTPException(status_code=422, detail="Nieprawidłowe dni aktywne")
    if body.raport_frequency is not None and body.raport_frequency not in {
        "DAILY", "WEEKLY",
    }:
        raise HTTPException(status_code=422, detail="Nieprawidłowa częstotliwość")
    for p in body.preferences:
        if p.category not in CATEGORIES or p.channel not in CHANNELS:
            raise HTTPException(
                status_code=422, detail="Nieznana kategoria lub kanał"
            )

    setting = (
        db.query(NotificationSetting).filter_by(user_id=user.id).one_or_none()
    )
    if setting is None:
        setting = NotificationSetting(id=new_id("NTS"), user_id=user.id)
        db.add(setting)
    if body.quiet_hours_start is not None or body.quiet_hours_end is not None:
        setting.quiet_hours_start = body.quiet_hours_start or None
        setting.quiet_hours_end = body.quiet_hours_end or None
    if body.active_days is not None:
        setting.active_days = body.active_days
    if body.raport_frequency is not None:
        setting.raport_frequency = body.raport_frequency
    setting.updated_at = now_iso()
    if body.timezone is not None:
        user.timezone = body.timezone or None
        db.add(user)

    for p in body.preferences:
        row = (
            db.query(NotificationPreference)
            .filter_by(user_id=user.id, category=p.category, channel=p.channel)
            .one_or_none()
        )
        if row is None:
            row = NotificationPreference(
                id=new_id("NTP"), user_id=user.id,
                category=p.category, channel=p.channel,
            )
            db.add(row)
        row.enabled = p.enabled
        row.updated_at = now_iso()

    record_event(
        db,
        action="NOTIFICATION_SETTINGS_CHANGED",
        actor_id=user.id,
        subject_ids=[user.id],
        # Bez treści — wyłącznie fakt zmiany i liczba preferencji.
        payload={"preferences_changed": len(body.preferences),
                 "timezone_changed": body.timezone is not None},
        summary="Zmiana ustawień powiadomień",
    )
    db.commit()
    return {"ok": True}

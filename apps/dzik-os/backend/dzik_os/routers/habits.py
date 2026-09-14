"""Nawyki (0.63.0): 3 nawyki z codziennym, cofalnym odhaczaniem i absolutorium.

Dostęp jak harmonogram: klient — swoje; trener — aktywna relacja i zgoda
na dane treningowe (`resolve_client_access`, domena training_data). Nawyk
z innego klienta pod tym samym `client_id` = logowana odmowa (404).
Postęp liczy `dzik_os.nawyki` przy każdym odczycie; status GRADUATED
utrwalany, gdy postęp osiągnie termin.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import nawyki as N
from ..authz import DOMAIN_TRAINING, deny, resolve_client_access
from ..dates import local_today, parse_iso_date
from ..db import get_db
from ..hos_bridge import record_event
from ..models import Habit, HabitCompletion, User, new_id, now_iso
from ..security import current_user

router = APIRouter(prefix="/api", tags=["habits"])

_DNI_RE = r"^[1-7](,[1-7]){0,6}$"
#: Najdawniejszy dopuszczalny start (ochrona przed liczeniem dziesiątek lat wstecz).
START_MAX_DNI_WSTECZ = 365


def _data(tekst: str, nazwa: str) -> date:
    """`YYYY-MM-DD` → date; nieistniejąca data (2026-02-30) = 422, nie 500."""
    try:
        return parse_iso_date(tekst)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{nazwa}: nieprawidłowa data.") from e


class HabitIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    days_of_week: str = Field(default=N.DNI_DOMYSLNE, pattern=_DNI_RE)
    target_days: int = Field(default=N.TERMIN_DOMYSLNY, ge=N.TERMIN_MIN, le=N.TERMIN_MAX)
    author_note: str | None = Field(default=None, max_length=500)
    started_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class HabitPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    days_of_week: str | None = Field(default=None, pattern=_DNI_RE)
    target_days: int | None = Field(default=None, ge=N.TERMIN_MIN, le=N.TERMIN_MAX)
    author_note: str | None = Field(default=None, max_length=500)
    #: ARCHIVED = wymień/usuń z listy; ACTIVE = przywróć zarchiwizowany (gdy jest miejsce);
    #: „ack” = przyjęcie absolutorium („Zostaw tak jak jest”).
    status: str | None = Field(default=None, pattern="^(ARCHIVED|ACTIVE)$")
    ack: bool | None = None


class CompleteIn(BaseModel):
    completed_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    done: bool = True


def _wykonane(db: Session, habit: Habit) -> set[date]:
    return {parse_iso_date(c.completed_on) for c in
            db.query(HabitCompletion).filter_by(habit_id=habit.id, status="DONE").all()}


def odswiez(db: Session, habit: Habit, today: date) -> N.Postep:
    """Postęp z bazy + utrwalenie absolutorium (bez crona: przy odczycie).
    Po absolutorium postęp jest ZAMROŻONY na dniu absolutorium — kolejne dni
    bez odhaczeń niczego nie cofają (nawyk utrwalony nie jest już pilnowany)."""
    koniec = today
    if habit.status == N.STATUS_GRADUATED and habit.graduated_on:
        koniec = min(today, parse_iso_date(habit.graduated_on))
    p = N.postep(parse_iso_date(habit.started_on), koniec, N.dni_tygodnia(habit.days_of_week),
                 _wykonane(db, habit), habit.target_days)
    if habit.status == N.STATUS_ACTIVE and p.graduated_on is not None:
        habit.status = N.STATUS_GRADUATED
        habit.graduated_on = p.graduated_on.isoformat()
        habit.updated_at = now_iso()
        record_event(db, action="HABIT_GRADUATED", actor_id=habit.client_id, subject_ids=[habit.client_id],
                     payload={"habit_id": habit.id, "target_days": habit.target_days},
                     summary="Nawyk utrwalony (absolutorium)")
        db.flush()
    return p


def habit_out(db: Session, habit: Habit, today: date) -> dict:
    p = odswiez(db, habit, today)
    return {
        "id": habit.id, "client_id": habit.client_id, "name": habit.name,
        "days_of_week": habit.days_of_week, "target_days": habit.target_days,
        "author_id": habit.author_id, "author_note": habit.author_note,
        "started_on": habit.started_on, "status": habit.status,
        "graduated_on": habit.graduated_on, "ack_on": habit.ack_on,
        "progress": p.progress, "progress_label": N.opis_postepu(p.progress, habit.target_days),
        "done_count": p.done_count, "planned_count": p.planned_count,
        "scheduled_today": p.scheduled_today and habit.status == N.STATUS_ACTIVE,
        "done_today": p.done_today, "created_at": habit.created_at,
    }


def lista(db: Session, client_id: str, today: date, *, archived: bool = False) -> list[dict]:
    q = db.query(Habit).filter(Habit.client_id == client_id)
    if not archived:
        q = q.filter(Habit.status != N.STATUS_ARCHIVED)
    rows = q.order_by(Habit.created_at).all()
    return [habit_out(db, h, today) for h in rows]


def _nawyk(db: Session, user: User, client_id: str, habit_id: str) -> Habit:
    habit = db.get(Habit, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if habit.client_id != client_id:
        deny(user.id, f"habit:{habit_id}")
    return habit


@router.get("/clients/{client_id}/habits")
def list_habits(client_id: str, archived: bool = False, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    resolve_client_access(db, user, client_id, action="read", domain=DOMAIN_TRAINING)
    klient = db.get(User, client_id)
    out = lista(db, client_id, local_today(klient), archived=archived)
    db.commit()
    return {"habits": out, "limit_active": N.LIMIT_AKTYWNYCH}


@router.post("/clients/{client_id}/habits", status_code=201)
def create_habit(client_id: str, body: HabitIn, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_TRAINING)
    klient = db.get(User, client_id)
    today = local_today(klient)
    # Absolutoria utrwalone przy okazji zwalniają miejsce.
    lista(db, client_id, today)
    aktywne = db.query(Habit).filter_by(client_id=client_id, status=N.STATUS_ACTIVE).count()
    if aktywne >= N.LIMIT_AKTYWNYCH:
        raise HTTPException(status_code=409, detail=f"Maksymalnie {N.LIMIT_AKTYWNYCH} aktywne nawyki naraz — "
                                                    "wymień albo zarchiwizuj któryś, zanim dodasz kolejny.")
    started = body.started_on or today.isoformat()
    start = _data(started, "started_on")
    if start > today:
        raise HTTPException(status_code=422, detail="Data startu nie może być w przyszłości.")
    if start < today - timedelta(days=START_MAX_DNI_WSTECZ):
        raise HTTPException(status_code=422, detail=f"Data startu najwyżej {START_MAX_DNI_WSTECZ} dni wstecz.")
    habit = Habit(
        id=new_id("HAB"), client_id=client_id, name=body.name.strip(), days_of_week=body.days_of_week,
        target_days=body.target_days, author_id=user.id, author_note=body.author_note,
        started_on=started,
    )
    db.add(habit)
    db.flush()
    # Limit sprawdzany PONOWNIE po zapisie: dwa równoległe POST nie dadzą czwartego.
    if db.query(Habit).filter_by(client_id=client_id, status=N.STATUS_ACTIVE).count() > N.LIMIT_AKTYWNYCH:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Maksymalnie {N.LIMIT_AKTYWNYCH} aktywne nawyki naraz.")
    record_event(db, action="HABIT_CREATED", actor_id=user.id, subject_ids=[client_id],
                 payload={"habit_id": habit.id, "target_days": habit.target_days, "author_id": user.id},
                 summary="Dodano nawyk")
    out = habit_out(db, habit, today)
    db.commit()
    return out


@router.patch("/clients/{client_id}/habits/{habit_id}")
def patch_habit(client_id: str, habit_id: str, body: HabitPatch, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_TRAINING)
    habit = _nawyk(db, user, client_id, habit_id)
    klient = db.get(User, client_id)
    today = local_today(klient)
    zmiany: list[str] = []
    edycja = any(v is not None for v in (body.name, body.days_of_week, body.target_days, body.author_note))
    if edycja and habit.status != N.STATUS_ACTIVE:
        raise HTTPException(status_code=409, detail="Edytować można tylko aktywny nawyk.")
    if body.author_note is not None and user.id != habit.author_id:
        raise HTTPException(status_code=403, detail="Notatkę może zmienić tylko jej autor.")
    if body.name is not None and body.name.strip() != habit.name:
        habit.name = body.name.strip()
        zmiany.append("name")
    if body.days_of_week is not None and body.days_of_week != habit.days_of_week:
        habit.days_of_week = body.days_of_week
        zmiany.append("days_of_week")
    if body.target_days is not None and body.target_days != habit.target_days:
        habit.target_days = body.target_days
        zmiany.append("target_days")
    if body.author_note is not None and body.author_note != habit.author_note:
        habit.author_note = body.author_note
        zmiany.append("author_note")
    if body.status == N.STATUS_ARCHIVED and habit.status != N.STATUS_ARCHIVED:
        habit.status = N.STATUS_ARCHIVED
        record_event(db, action="HABIT_ARCHIVED", actor_id=user.id, subject_ids=[client_id],
                     payload={"habit_id": habit.id}, summary="Zarchiwizowano nawyk")
    elif body.status == N.STATUS_ACTIVE and habit.status == N.STATUS_ARCHIVED:
        # Przywrócenie (pomyłkowe „Usuń z listy”) — tylko gdy jest wolne miejsce.
        aktywne = db.query(Habit).filter_by(client_id=client_id, status=N.STATUS_ACTIVE).count()
        if aktywne >= N.LIMIT_AKTYWNYCH:
            raise HTTPException(status_code=409, detail=f"Maksymalnie {N.LIMIT_AKTYWNYCH} aktywne nawyki naraz.")
        habit.status = N.STATUS_ACTIVE
        habit.graduated_on = None
        habit.ack_on = None
        record_event(db, action="HABIT_RESTORED", actor_id=user.id, subject_ids=[client_id],
                     payload={"habit_id": habit.id}, summary="Przywrócono nawyk")
    if body.ack and habit.status == N.STATUS_GRADUATED and habit.ack_on is None:
        habit.ack_on = today.isoformat()
    if zmiany:
        record_event(db, action="HABIT_UPDATED", actor_id=user.id, subject_ids=[client_id],
                     payload={"habit_id": habit.id, "fields": zmiany}, summary="Zmieniono nawyk")
    habit.updated_at = now_iso()
    out = habit_out(db, habit, today)
    db.commit()
    return out


@router.post("/clients/{client_id}/habits/{habit_id}/complete")
def complete_habit(client_id: str, habit_id: str, body: CompleteIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    """Odhaczenie dnia (domyślnie dziś) albo jego cofnięcie (`done=false`).
    Idempotentne w obie strony — nie mnoży wpisów."""
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_TRAINING)
    habit = _nawyk(db, user, client_id, habit_id)
    klient = db.get(User, client_id)
    today = local_today(klient)
    if habit.status != N.STATUS_ACTIVE:
        raise HTTPException(status_code=409, detail="Ten nawyk nie jest już odhaczany (utrwalony albo zarchiwizowany).")
    dzien = _data(body.completed_on, "completed_on") if body.completed_on else today
    if dzien > today:
        raise HTTPException(status_code=422, detail="Nie można odhaczyć dnia z przyszłości.")
    if dzien < parse_iso_date(habit.started_on):
        raise HTTPException(status_code=422, detail="Dzień sprzed startu nawyku.")
    existing = db.query(HabitCompletion).filter_by(habit_id=habit.id, completed_on=dzien.isoformat()).one_or_none()
    if body.done and existing is None:
        try:
            with db.begin_nested():
                db.add(HabitCompletion(id=new_id("HCP"), habit_id=habit.id, client_id=client_id,
                                       completed_on=dzien.isoformat(), status="DONE", created_by=user.id))
                db.flush()
        except IntegrityError:
            pass  # równoległe odhaczenie tego samego dnia — wpis już jest, stan poniżej aktualny
    elif not body.done and existing is not None:
        db.delete(existing)
        db.flush()
    out = habit_out(db, habit, today)
    db.commit()
    return out

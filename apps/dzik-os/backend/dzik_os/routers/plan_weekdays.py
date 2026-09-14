"""Dni treningowe (0.71.0): wybór dni tygodnia klienta dla jednostek planu.

Nakładka klienta na plan trenera — wersje planu pozostają niemutowalne,
`weekday` trenera jest propozycją (prefill). Dostęp jak nawyki i harmonogram:
klient — swoje; trener — aktywna relacja i zgoda na dane treningowe
(`resolve_client_access`, domena training_data). Plan innego klienta albo
szablon pod tym `client_id` = logowana odmowa (404). Silnik: `dzik_os.dni_treningowe`.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import dni_treningowe as D
from ..authz import DOMAIN_TRAINING, deny, resolve_client_access
from ..db import get_db
from ..hos_bridge import record_event
from ..models import PlanWeekdayChoice, TrainingPlan, TrainingPlanVersion, User, new_id, now_iso
from ..observability import error_response
from ..security import current_user

router = APIRouter(prefix="/api", tags=["plan-weekdays"])


class WyborIn(BaseModel):
    day_key: str = Field(min_length=1, max_length=D.KLUCZ_MAX)
    #: StrictInt: `true` i `"3"` nie przechodzą jako 1 / 3.
    weekday: StrictInt | None = Field(default=None, ge=1, le=7)


class DniIn(BaseModel):
    #: Pusta lista = wszystkie jednostki nieprzypisane (świadomy wybór klienta,
    #: różny od braku wpisu — wtedy obowiązuje propozycja trenera).
    choices: list[WyborIn] = Field(default_factory=list, max_length=50)
    author_note: str | None = Field(default=None, max_length=500)


def _plan_klienta(db: Session, user: User, client_id: str, plan_id: str) -> tuple[TrainingPlan, TrainingPlanVersion | None]:
    plan = db.get(TrainingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if plan.client_id != client_id:
        # Cudzy plan albo szablon pod tym client_id — odmowa bez potwierdzania istnienia.
        deny(user.id, f"plan:{plan_id}")
    if plan.status != "ACTIVE":
        # Odpięty (UNASSIGNED) albo zarchiwizowany plan nie jest już widoczny
        # klientowi — dni się do niego nie zapisuje (zwykłe 404, to własny plan).
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    version = None
    if plan.current_version_no:
        version = (
            db.query(TrainingPlanVersion)
            .filter_by(plan_id=plan.id, version_no=plan.current_version_no)
            .one_or_none()
        )
    return plan, version


def wybor_klienta(db: Session, client_id: str, plan_id: str) -> PlanWeekdayChoice | None:
    return db.query(PlanWeekdayChoice).filter_by(client_id=client_id, plan_id=plan_id).one_or_none()


def uklad_z_wiersza(row: PlanWeekdayChoice | None) -> D.Uklad | None:
    if row is None:
        return None
    try:
        return D.z_json(json.loads(row.choices_json))
    except (ValueError, TypeError):
        return {}


def odpowiedz(plan: TrainingPlan, version: TrainingPlanVersion | None, row: PlanWeekdayChoice | None) -> dict:
    content = json.loads(version.content_json) if version is not None else {}
    wybor = uklad_z_wiersza(row)
    trener = D.uklad_trenera(content)
    efektywny = D.uklad_efektywny(content, wybor)
    return {
        "plan_id": plan.id,
        "plan_title": plan.title,
        "version_no": version.version_no if version is not None else None,
        "source": D.zrodlo(content, wybor),
        "days": [
            {
                "day_key": key, "day_index": idx, "name": day.get("name"),
                "coach_weekday": trener.get(key), "weekday": efektywny.get(key),
            }
            for key, idx, day in D.dni(content)
        ],
        "stale_keys": D.klucze_nieaktualne(content, wybor),
        "author_id": row.author_id if row is not None else None,
        "author_note": row.author_note if row is not None else None,
        "updated_at": row.updated_at if row is not None else None,
    }


@router.get("/clients/{client_id}/plans/{plan_id}/dni")
def get_dni(client_id: str, plan_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    resolve_client_access(db, user, client_id, action="read", domain=DOMAIN_TRAINING)
    plan, version = _plan_klienta(db, user, client_id, plan_id)
    return odpowiedz(plan, version, wybor_klienta(db, client_id, plan_id))


@router.put("/clients/{client_id}/plans/{plan_id}/dni")
def put_dni(client_id: str, plan_id: str, body: DniIn, user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    """Zapis układu klienta (nadpisuje poprzedni — to preferencja, nie plan;
    zdarzenie audytu zostaje). Walidacja: klucz spoza wersji, duplikat
    jednostki, `weekday` spoza 1–7, dwie jednostki w jeden dzień → 422."""
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_TRAINING)
    plan, version = _plan_klienta(db, user, client_id, plan_id)
    if version is None:
        raise HTTPException(status_code=422, detail="Ten plan nie ma jeszcze opublikowanej wersji.")
    content = json.loads(version.content_json)
    try:
        uklad = D.waliduj_wybor(content, [c.model_dump() for c in body.choices])
    except D.BladWyboru as e:
        # Wspólny model błędów aplikacji: `detail` = komunikat po polsku,
        # `errors[0].field` = klucz jednostki, przy której front pokaże błąd.
        return error_response(422, e.komunikat, code="WEEKDAY_CHOICE",
                              errors=[{"field": e.day_key or "", "type": "weekday_choice", "msg": e.komunikat}])
    row = wybor_klienta(db, client_id, plan_id)
    if row is None:
        row = PlanWeekdayChoice(id=new_id("PWD"), client_id=client_id, plan_id=plan_id, author_id=user.id)
        db.add(row)
    else:
        row.version += 1
        row.author_id = user.id
    row.choices_json = json.dumps(D.do_json(uklad), ensure_ascii=False)
    row.author_note = body.author_note
    row.updated_at = now_iso()
    try:
        db.flush()
    except IntegrityError:
        # Dwa równoległe pierwsze zapisy (klient i trener naraz): jeden wiersz per
        # (klient, plan) — drugi dostaje 409 i ponawia na aktualnym stanie.
        db.rollback()
        raise HTTPException(status_code=409, detail="Ktoś właśnie zapisał dni dla tego planu — odśwież i spróbuj ponownie.") from None
    record_event(db, action="PLAN_WEEKDAYS_SET", actor_id=user.id, subject_ids=[client_id],
                 payload={"plan_id": plan_id, "version_no": version.version_no, "author_id": user.id,
                          "assigned_days": sum(1 for v in uklad.values() if v is not None)},
                 summary="Ustawiono dni tygodnia dla jednostek planu"
                         + (" (przez trenera)" if user.id != client_id else ""))
    out = odpowiedz(plan, version, row)
    db.commit()
    return out


@router.delete("/clients/{client_id}/plans/{plan_id}/dni")
def delete_dni(client_id: str, plan_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Powrót do propozycji trenera (usunięcie układu klienta). Idempotentne."""
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_TRAINING)
    plan, version = _plan_klienta(db, user, client_id, plan_id)
    row = wybor_klienta(db, client_id, plan_id)
    if row is not None:
        db.delete(row)
        db.flush()
        record_event(db, action="PLAN_WEEKDAYS_CLEARED", actor_id=user.id, subject_ids=[client_id],
                     payload={"plan_id": plan_id, "author_id": user.id},
                     summary="Powrót do propozycji trenera (dni tygodnia planu)")
    out = odpowiedz(plan, version, None)
    db.commit()
    return out

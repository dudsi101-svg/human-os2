"""Szkice planów i publikacja zmian (0.58.0) — API trenera i ekran zmian klienta.

Przepływ: `POST /api/szkice/plan/{plan_kind}/{plan_id}` (utwórz albo pobierz
aktywny szkic) → `PATCH /api/szkice/{id}` (operacje po `id` z rewizją) →
`GET …/roznice` → `POST …/publikuj` (rewizja + wersja bazowa + notatka +
klucz idempotencji) albo `DELETE …` (odrzuć). Klient: `GET
/api/zmiany/{id}` (tylko odbiorca / trener z dostępem) i lista zmian planu.

Każda operacja sprawdza po stronie serwera własność planu, relację
trener–klient i zgodę domeny; identyfikatory z przeglądarki nie są dowodem
uprawnień. Konflikt rewizji i konflikt wersji bazowej = 409 z aktualnym
stanem, nigdy ciche nadpisanie.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import notifications
from ..authz import (
    DOMAIN_NUTRITION,
    DOMAIN_TRAINING,
    ResourceAccessDenied,
    resolve_client_access,
)
from ..config import settings
from ..db import get_db
from ..idempotency import replay_response, request_fingerprint, store_response
from ..models import ChangeSet, NutritionPlan, TrainingPlan, User
from ..publikacja import elementy, serwis
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["szkice"])


def wymagaj_szkicow() -> None:
    if not settings.szkice_publikacja:
        raise HTTPException(status_code=404, detail="Szkice i publikacja zmian są wyłączone")


class OperacjeIn(BaseModel):
    revision: int = Field(ge=1)
    operations: list[dict] = Field(min_length=1, max_length=200)


class PublikujIn(BaseModel):
    revision: int = Field(ge=1)
    base_version_no: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=2000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=80)


def _konflikt(kod: str, detail: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": detail, "code": kod, **extra})


def _rodzaj(plan_kind: str) -> str:
    if plan_kind not in elementy.RODZAJE:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    return plan_kind


# --- szkic (trener) --------------------------------------------------------------------


@router.post("/szkice/plan/{plan_kind}/{plan_id}", dependencies=[Depends(wymagaj_szkicow)])
def utworz_lub_pobierz_szkic(plan_kind: str, plan_id: str, coach: User = Depends(require_role("COACH")),
                             db: Session = Depends(get_db)):
    szkic, nowy = serwis.utworz_lub_pobierz(db, coach, _rodzaj(plan_kind), plan_id)
    db.commit()
    out = serwis.szkic_out(szkic)
    return JSONResponse(status_code=201 if nowy else 200, content=out)


@router.get("/szkice/plan/{plan_kind}/{plan_id}/aktywny", dependencies=[Depends(wymagaj_szkicow)])
def aktywny_szkic(plan_kind: str, plan_id: str, coach: User = Depends(require_role("COACH")),
                  db: Session = Depends(get_db)):
    """Czy plan ma aktywny szkic (bez tworzenia) — do znacznika w panelu."""
    serwis.plan_trenera(db, coach, _rodzaj(plan_kind), plan_id, action="read")
    szkic = serwis.aktywny_szkic(db, plan_kind, plan_id)
    return {"draft": serwis.szkic_out(szkic) if szkic else None}


@router.get("/szkice/{draft_id}", dependencies=[Depends(wymagaj_szkicow)])
def pobierz_szkic(draft_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    return serwis.szkic_out(serwis.szkic_trenera(db, coach, draft_id))


@router.patch("/szkice/{draft_id}", dependencies=[Depends(wymagaj_szkicow)])
def zmien_szkic(draft_id: str, body: OperacjeIn, coach: User = Depends(require_role("COACH")),
                db: Session = Depends(get_db)):
    szkic = serwis.szkic_trenera(db, coach, draft_id)
    try:
        serwis.zastosuj_operacje(db, szkic, revision=body.revision, operacje=body.operations, coach=coach)
    except serwis.KonfliktRewizji as e:
        db.rollback()
        return _konflikt("REVISION_CONFLICT", "Szkic zmienił się na innym urządzeniu — odśwież, "
                         "żeby nie nadpisać cudzych zmian.", current_revision=e.aktualna)
    except elementy.BladOperacji as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from None
    db.commit()
    return serwis.szkic_out(szkic)


@router.delete("/szkice/{draft_id}/elementy/{element_id}", dependencies=[Depends(wymagaj_szkicow)])
def usun_element(draft_id: str, element_id: str, revision: int = Query(ge=1),
                 coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Usunięcie elementu szkicu (klient nic nie widzi do publikacji).
    Odpowiedź niesie usunięty element z dziećmi — do „Cofnij”."""
    szkic = serwis.szkic_trenera(db, coach, draft_id)
    tresc = json.loads(szkic.content_json)
    try:
        kol, _lista, idx, el = elementy.znajdz(szkic.plan_kind, tresc, element_id)
        serwis.zastosuj_operacje(db, szkic, revision=revision,
                                 operacje=[{"op": "delete", "id": element_id}], coach=coach)
    except serwis.KonfliktRewizji as e:
        db.rollback()
        return _konflikt("REVISION_CONFLICT", "Szkic zmienił się na innym urządzeniu — odśwież.",
                         current_revision=e.aktualna)
    except elementy.BladOperacji as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from None
    db.commit()
    rodzic = None
    for k, p, _i, e2 in elementy.elementy(szkic.plan_kind, tresc):
        if e2.get("id") == element_id and k == kol:
            rodzic = p
    return {**serwis.szkic_out(szkic),
            "removed": {"collection": kol, "index": idx, "parent_id": rodzic, "item": el,
                        "count": elementy.liczba_elementow(szkic.plan_kind, kol, el)}}


@router.get("/szkice/{draft_id}/roznice", dependencies=[Depends(wymagaj_szkicow)])
def roznice(draft_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    szkic = serwis.szkic_trenera(db, coach, draft_id)
    plan = serwis.plan_trenera(db, coach, szkic.plan_kind, szkic.plan_id, action="read")
    r = serwis.roznice_szkicu(szkic)
    return {**r, "plan_id": plan.id, "plan_title": plan.title, "client_id": plan.client_id,
            "base_version_no": szkic.base_version_no, "current_version_no": plan.current_version_no,
            "stale_base": plan.current_version_no != szkic.base_version_no,
            "effective": "natychmiast po publikacji"}


@router.post("/szkice/{draft_id}/publikuj", dependencies=[Depends(wymagaj_szkicow)])
def publikuj(draft_id: str, body: PublikujIn, coach: User = Depends(require_role("COACH")),
             db: Session = Depends(get_db)):
    """Publikacja w jednej transakcji: wersja + zestaw zmian + outbox
    (+ ślad Wiedzy i audyt). Powtórka z tym samym kluczem = ten sam wynik;
    ten sam klucz z inną treścią = 409 (idempotency.py)."""
    szkic = serwis.szkic_trenera(db, coach, draft_id)
    odcisk = None
    if body.idempotency_key:
        odcisk = request_fingerprint({"draft_id": draft_id, **body.model_dump(exclude={"idempotency_key"})})
        powtorka = replay_response(db, user_id=coach.id, operation="publikacja_szkicu",
                                   key=body.idempotency_key, fingerprint=odcisk)
        if powtorka is not None:
            return powtorka
    try:
        wynik = serwis.publikuj(db, szkic, coach=coach, revision=body.revision,
                                base_version_no=body.base_version_no, note=body.note)
    except serwis.KonfliktRewizji as e:
        db.rollback()
        return _konflikt("REVISION_CONFLICT", "Szkic zmienił się na innym urządzeniu — odśwież i sprawdź "
                         "zmiany ponownie. Szkic został zachowany.", current_revision=e.aktualna)
    except serwis.KonfliktWersji as e:
        db.rollback()
        return _konflikt("BASE_VERSION_CONFLICT", "Plan ma już nowszą wersję niż ta, na której powstał "
                         "szkic — sprawdź różnice względem aktualnej wersji. Szkic został zachowany.",
                         current_version_no=e.aktualna)
    except serwis.BladPublikacji as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Publikacja odrzucona: {e}") from None
    except elementy.BladOperacji as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from None
    if body.idempotency_key and odcisk:
        store_response(db, user_id=coach.id, operation="publikacja_szkicu", key=body.idempotency_key,
                       fingerprint=odcisk, response=wynik)
    db.commit()
    # Doręczenie wpisu klienta: próba od razu (outbox zostaje źródłem prawdy
    # i ponowi po awarii w pętli przypomnień).
    if wynik.get("outbox_event_id"):
        try:
            utworzone = serwis.przetworz_outbox(db, tylko_id=wynik["outbox_event_id"])
            db.commit()
            for n in utworzone:
                notifications.publish_realtime(n)
        except Exception:  # noqa: BLE001 — publikacja jest już trwała; outbox ponowi
            db.rollback()
    return wynik


@router.delete("/szkice/{draft_id}", dependencies=[Depends(wymagaj_szkicow)])
def odrzuc_szkic(draft_id: str, revision: int = Query(ge=1), coach: User = Depends(require_role("COACH")),
                 db: Session = Depends(get_db)):
    szkic = serwis.szkic_trenera(db, coach, draft_id)
    try:
        serwis.odrzuc(db, szkic, revision=revision, coach=coach)
    except serwis.KonfliktRewizji as e:
        db.rollback()
        return _konflikt("REVISION_CONFLICT", "Szkic zmienił się na innym urządzeniu — odśwież.",
                         current_revision=e.aktualna)
    db.commit()
    return {"ok": True, "status": szkic.status}


# --- zmiany (klient i trener) ------------------------------------------------------------


def _dostep_do_planu(db: Session, user: User, plan_kind: str, plan_id: str):
    if plan_kind == "training":
        plan = db.get(TrainingPlan, plan_id)
        domena = DOMAIN_TRAINING
    else:
        plan = db.get(NutritionPlan, plan_id)
        domena = DOMAIN_NUTRITION
    if plan is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if plan.client_id is not None:
        resolve_client_access(db, user, plan.client_id, domain=domena)
    elif plan.coach_id != user.id:
        raise ResourceAccessDenied(user.id, f"{plan_kind}_plan:{plan_id}")
    return plan


@router.get("/plany/{plan_kind}/{plan_id}/zmiany")
def zmiany_planu(plan_kind: str, plan_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    plan = _dostep_do_planu(db, user, _rodzaj(plan_kind), plan_id)
    rows = (db.query(ChangeSet).filter_by(plan_kind=plan_kind, plan_id=plan.id)
            .order_by(ChangeSet.published_at.desc()).limit(100).all())
    return {"plan_id": plan.id, "plan_title": plan.title, "current_version_no": plan.current_version_no,
            "changes": [serwis.zestaw_out(db, z, pelny=False) for z in rows]}


@router.get("/zmiany/{changeset_id}")
def zmiana(changeset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Ekran „Zobacz zmiany”: przed/po, autor, czas, notatka, link do planu.
    Wyłącznie odbiorca (klient) albo trener z dostępem do planu."""
    z = db.get(ChangeSet, changeset_id)
    if z is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    plan = _dostep_do_planu(db, user, z.plan_kind, z.plan_id)
    out = serwis.zestaw_out(db, z)
    out["plan_title"] = plan.title
    out["plan_url"] = "/plan" if z.plan_kind == "training" else "/dieta"
    out["current_version_no"] = plan.current_version_no
    # Klient nie widzi stanu doręczenia (to widok trenera); trener — tak.
    if user.id == z.client_id:
        out["notification"] = None
    return out

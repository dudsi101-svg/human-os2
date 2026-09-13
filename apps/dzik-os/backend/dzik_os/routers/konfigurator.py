"""Konfigurator 28 dni — API trenera (0.55.0, K1).

Propose-only: `podglad` liczy szkic i nic nie zapisuje; `zapisz` tworzy
NOWY plan podopiecznego (v1) z wyniku ready/limited — dalej edytowany
jak każdy plan (nowa wersja, powód w historii). Klient nie uruchamia
generatora. Blok zdrowotny wejścia jest używany wyłącznie do
kwalifikacji: nie trafia do treści planu, zdarzeń audytu ani logów.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..authz import DOMAIN_TRAINING, resolve_client_access
from ..db import get_db
from ..hos_bridge import record_event
from ..konfigurator import dane, generuj_plan
from ..konfigurator.eksport import na_plan_dzik
from ..models import TrainingPlan, TrainingPlanVersion, User, new_id
from ..security import require_role

router = APIRouter(prefix="/api/coach/konfigurator", tags=["konfigurator"])

STATUSY_DO_ZAPISU = ("ready", "limited")


class ZapiszIn(BaseModel):
    client_id: str = Field(min_length=1, max_length=40)
    wejscie: dict
    title: str | None = Field(default=None, max_length=300)


@router.get("/katalog")
def katalog(coach: User = Depends(require_role("COACH"))):
    """Katalog konfiguratora (do przeglądu trenera) + słowniki formularza."""
    k = dane.katalog()
    schemat = dane.schematy()["input_schema"]["properties"]
    return {
        "versions": dane.WERSJE,
        "status": k["status"],
        "exercises": [{"id": e["id"], "name_pl": e["name_pl"], "pattern": e["pattern"], "primary": e["primary"],
                       "secondary": e["secondary"], "equipment_all": e["equipment_all"], "unilateral": e["unilateral"],
                       "reps": e["reps"], "rest_seconds": e["rest_seconds"], "load_unit": e["load_unit"],
                       "review_status": e["review_status"]} for e in k["exercises"]],
        "equipment_ids": sorted({s for e in k["exercises"] for s in e["equipment_all"]}),
        "muscles": schemat["priority_muscles"]["items"]["enum"],
        "layouts": k["weekly_layouts"],
        "heuristics": k["heuristics"],
    }


@router.post("/podglad")
def podglad(wejscie: dict, coach: User = Depends(require_role("COACH"))):
    """Szkic bez zapisu. Statusy blokujące wracają z `plan: null`
    i pytaniami — to poprawna odpowiedź, nie błąd HTTP."""
    return generuj_plan(wejscie, plan_id="PODGLAD")


@router.post("/zapisz", status_code=201)
def zapisz(
    body: ZapiszIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, coach, body.client_id, action="write", domain=DOMAIN_TRAINING)
    plan_id = new_id("KFG")
    odpowiedz = generuj_plan(body.wejscie, plan_id=plan_id)
    if odpowiedz["status"] not in STATUSY_DO_ZAPISU:
        # Konflikt, nie 500: trener dostaje pełny wynik do poprawy wejścia
        # (JSONResponse, bo globalna obsługa HTTPException spłaszcza detail do tekstu).
        return JSONResponse(status_code=409, content={
            "detail": "Szkic nie jest gotowy do zapisu — popraw wejście albo skieruj do przeglądu.",
            "wynik": odpowiedz,
        })
    tytul = body.title or f"Konfigurator 28 dni — od {odpowiedz['plan']['start_date']}"
    plan = TrainingPlan(id=new_id("PLN"), client_id=body.client_id, coach_id=coach.id,
                        title=tytul, current_version_no=1)
    db.add(plan)
    wersja = TrainingPlanVersion(
        id=new_id("PLV"), plan_id=plan.id, version_no=1,
        reason=(f"Szkic z konfiguratora 28 dni (reguły {odpowiedz['versions']['rules']}, "
                f"katalog {odpowiedz['versions']['catalog']}; status {odpowiedz['status']}). "
                "Heurystyki H — do przeglądu trenera."),
        content_json=json.dumps(na_plan_dzik(odpowiedz, body.wejscie), ensure_ascii=False),
        created_by=coach.id,
    )
    db.add(wersja)
    record_event(
        db, action="PLAN_CREATED", actor_id=coach.id, subject_ids=[body.client_id],
        # Bez wejścia i bez danych zdrowotnych — tylko metadane szkicu.
        payload={"plan_id": plan.id, "title": tytul, "version_no": 1, "source": "konfigurator",
                 "konfigurator_id": plan_id, "status": odpowiedz["status"],
                 "versions": odpowiedz["versions"],
                 "issue_codes": [i["code"] for i in odpowiedz["issues"]]},
        summary=f"Plan „{tytul}” zapisany ze szkicu konfiguratora dla klienta",
    )
    db.commit()
    return {"id": plan.id, "version_id": wersja.id, "version_no": 1, "status": odpowiedz["status"],
            "issues": odpowiedz["issues"], "questions": odpowiedz["questions"]}

"""Cardio z suwakami celów — API trenera (0.73.0).

Propose-only: `podglad` liczy propozycję i NICZEGO nie zapisuje; wynik
wkleja się do pozycji planu (`kind: "cardio"`) i trafia do klienta dopiero
w zapisanej/opublikowanej wersji planu (ślad `H_CARDIO` powstaje wtedy,
w tej samej transakcji co wersja). Klient nie uruchamia silnika (403).

Bramka zdrowotna (`konfigurator.zdrowie.ocen_zdrowie` 1:1 + leki wpływające
na tętno) działa PRZED silnikiem: `urgent_stop` → brak propozycji,
`needs_input` → pytania, `needs_review` → propozycja z ostrzeżeniem widoczna
wyłącznie trenerowi. Blok zdrowotny nie trafia do planu, śladu, audytu ani
logów. Wiek, tętno spoczynkowe i masa są czytane z danych klienta tylko
wtedy, gdy trener ma dostęp do domeny zdrowotnej — inaczej silnik liczy
w trybie „RPE + test mowy”.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..authz import (
    DOMAIN_HEALTH,
    DOMAIN_TRAINING,
    ResourceAccessDenied,
    resolve_client_access,
)
from ..cardio import model as cardio_model
from ..cardio import stale as S
from ..cardio import urzadzenia as U
from ..cardio.bloki_wbudowane import ETYKIETY_RODZAJOW, ETYKIETY_WARIANTOW
from ..db import get_db
from ..konfigurator.zdrowie import PYTANIA, ocen_zdrowie
from ..models import CalorieEstimate, Measurement, User
from ..observability import error_response
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["cardio"])

PYTANIE_LEKI = "Czy klient przyjmuje leki wpływające na tętno (np. beta-blokery)?"
POMIAR_TETNA_SPOCZ = "resting_hr"


class PodgladIn(BaseModel):
    goal_mix: dict[str, float]
    level: str = Field(pattern="^(POCZATKUJACY|SREDNIOZAAWANSOWANY|ZAAWANSOWANY)$")
    machines: list[str] = Field(min_length=1, max_length=5)
    #: Blok zdrowotny jak w konfiguratorze (`health{}`) + `hr_medication`.
    health: dict = Field(default_factory=dict)
    age: float | None = Field(default=None, ge=1, le=120)
    resting_hr: int | None = Field(default=None, ge=20, le=200)
    weight_kg: float | None = Field(default=None, ge=1, le=500)
    has_hr_monitor: bool = True


def _prefill(db: Session, coach: User, client_id: str) -> dict:
    """Wiek (ostatni szacunek kaloryczny), tętno spoczynkowe i masa (ostatnie
    pomiary) — wyłącznie przy dostępie trenera do domeny zdrowotnej. Bez
    dostępu wracają puste wartości, a odpowiedź mówi to wprost."""
    out: dict = {"age": None, "resting_hr": None, "weight_kg": None, "health_access": False}
    try:
        resolve_client_access(db, coach, client_id, action="read", domain=DOMAIN_HEALTH)
    except ResourceAccessDenied:
        return out
    out["health_access"] = True
    est = (db.query(CalorieEstimate).filter(CalorieEstimate.client_id == client_id)
           .order_by(CalorieEstimate.created_at.desc()).first())
    if est is not None:
        try:
            wiek = json.loads(est.inputs_json).get("wiek")
        except (ValueError, TypeError, AttributeError):
            wiek = None
        if isinstance(wiek, (int, float)) and not isinstance(wiek, bool):
            out["age"] = float(wiek)
    for kind, key in ((POMIAR_TETNA_SPOCZ, "resting_hr"), ("weight", "weight_kg")):
        m = (db.query(Measurement).filter(Measurement.client_id == client_id, Measurement.kind == kind)
             .order_by(Measurement.measured_at.desc(), Measurement.created_at.desc()).first())
        if m is not None:
            out[key] = round(m.value) if key == "resting_hr" else float(m.value)
    return out


@router.get("/cardio/katalog")
def katalog(_: User = Depends(current_user)):
    """Słowniki silnika: cele, urządzenia z tabelą sugestii, kotwice, pytania
    bramki — bez danych klienta (każdy zalogowany może czytać etykiety)."""
    return {
        "model_version": S.WERSJA_MODELU,
        "goals": [{"id": c, "label": S.ETYKIETY_CELOW[c], "anchor": S.KOTWICE[c]} for c in S.CELE],
        "machines": [{"id": m, "label": U.ETYKIETY[m], "params": U.PARAMETRY[m], "met": U.MET[m],
                      "catalog_exercise": U.CWICZENIE_KATALOGU[m]} for m in U.URZADZENIA],
        "levels": list(S.SUFIT_PCT),
        "block_kinds": ETYKIETY_RODZAJOW,
        "block_variants": ETYKIETY_WARIANTOW,
        "health_questions": {**PYTANIA, "hr_medication": PYTANIE_LEKI},
        "caveats": S.ZASTRZEZENIA,
        "review": "tabela urządzeń i kotwice [C] — do przeglądu trenera",
    }


@router.get("/clients/{client_id}/cardio/prefill")
def prefill(client_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Wartości startowe formularza trenera (wiek, tętno spoczynkowe, masa)."""
    resolve_client_access(db, coach, client_id, action="write", domain=DOMAIN_TRAINING)
    return _prefill(db, coach, client_id)


@router.post("/clients/{client_id}/cardio/podglad")
def podglad(
    client_id: str,
    body: PodgladIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Propozycja bez zapisu. Statusy blokujące wracają z `prescription: null`
    i pytaniami — to poprawna odpowiedź, nie błąd HTTP."""
    resolve_client_access(db, coach, client_id, action="write", domain=DOMAIN_TRAINING)
    h = dict(body.health or {})
    status, issues, questions = ocen_zdrowie({"health": h, "age": body.age})
    leki = h.get("hr_medication")
    if leki is None:
        questions.append(PYTANIE_LEKI)
        if status is None:
            status = "needs_input"
            issues.append({"code": "HEALTH_ANSWERS_MISSING", "severity": "error", "rule_id": "H_HEALTH_GATE",
                           "message": "Brak odpowiedzi na pytanie o leki wpływające na tętno."})
    if status in ("urgent_stop", "needs_input"):
        return {"status": status, "issues": issues, "questions": questions, "prescription": None,
                "trace": None, "inputs": None}
    dane = _prefill(db, coach, client_id)
    wiek = body.age if body.age is not None else dane["age"]
    tetno = body.resting_hr if body.resting_hr is not None else dane["resting_hr"]
    masa = body.weight_kg if body.weight_kg is not None else dane["weight_kg"]
    try:
        wynik = cardio_model.propozycja(
            body.goal_mix, body.level, body.machines, age=wiek, resting_hr=tetno, weight_kg=masa,
            hr_mode="rpe_only" if leki else "normal", has_hr_monitor=body.has_hr_monitor,
        )
    except cardio_model.BladWejscia as exc:
        return error_response(422, str(exc), code="CARDIO_INPUT")
    if status == "needs_review":
        issues.append({"code": "CARDIO_COACH_ONLY", "severity": "warning", "rule_id": "H_HEALTH_GATE",
                       "message": "Propozycja widoczna tylko dla trenera: przed użyciem potrzebna "
                                  "ocena specjalisty. Bez publikacji klient jej nie zobaczy."})
    return {
        "status": status or "ready",
        "issues": issues,
        "questions": questions,
        "prescription": wynik["prescription"],
        "trace": wynik["trace"],
        "model_version": wynik["model_version"],
        # Co silnik faktycznie dostał (bez bloku zdrowotnego) — trener widzi,
        # skąd wzięły się liczby; wiek/tętno/masa nie trafiają do planu.
        "inputs": {"age": wiek, "resting_hr": tetno, "weight_kg": masa,
                   "health_access": dane["health_access"], "hr_mode": "rpe_only" if leki else "normal"},
    }

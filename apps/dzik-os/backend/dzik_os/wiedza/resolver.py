"""Resolver wyjaśnień — kolejność 10 kroków z pliku 03 pakietu.

Część czysta (`rozstrzygnij`) nie dotyka bazy: dostaje kontekst żądania,
ślad (albo None) i funkcje do odczytu kart. Dzięki temu 15 scenariuszy
referencyjnych pakietu testuje ją bez serwera. Warstwa bazodanowa
(`wyjasnij`) buduje kontekst po stronie serwera: uwierzytelnienie,
dostęp do planu, bieżąca rewizja ze źródła (klient nie jest jej
autorytetem), stan bezpieczeństwa, ponowna kontrola rewizji przed
odpowiedzią.

Statusy: explained, general_only, missing_trace, insufficient_data,
inconsistent_data, stale_context, restricted. Brak uprawnień = 404 bez
trace_id ani danych celu.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..authz import DOMAIN_NUTRITION, DOMAIN_TRAINING, deny, resolve_client_access
from ..dates import local_today
from ..models import (
    NutritionPlan,
    NutritionPlanVersion,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    WorkoutSession,
)
from . import reguly, slad, tresci

TRYBY = ("current", "history")

#: Reguła produktu (plan sesji, decyzja 6): zgłoszenie bólu w sesji tej
#: wersji planu z ostatnich N dni = aktywna ścieżka bezpieczeństwa.
DNI_BLOKADY_PO_BOLU = 7

KOMUNIKAT_BRAK_SLADU = ("Nie mamy zapisanego uzasadnienia tej wartości. "
                        "Możesz przeczytać zasadę ogólną.")
KOMUNIKAT_NIEAKTUALNE = "To wyjaśnienie dotyczy wcześniejszej wersji planu."
KOMUNIKAT_SPRZECZNE = "Nie możemy teraz wiarygodnie wyjaśnić tej decyzji."
KOMUNIKAT_NIEPELNE = ("Zapisane dane nie wystarczają, żeby wiarygodnie wyjaśnić tę "
                      "decyzję. Możesz przeczytać zasadę ogólną.")
KOMUNIKAT_BEZPIECZENSTWO = ("Zgłosiłeś ból w ostatnim treningu. Zanim wrócisz do tego "
                            "elementu planu, skontaktuj się z trenerem. Poniżej zasada ogólna.")


@dataclass(frozen=True)
class Kontekst:
    authenticated_owner: str
    plan_owner: str
    current_plan_revision: int
    requested_plan_revision: int
    mode: str
    active_safety_block: bool
    #: Trener z aktywną relacją i zgodą (sprawdzone po stronie serwera).
    coach_access: bool = False


ArtykulyFn = Callable[[list[str]], list[dict]]
OgolneFn = Callable[[str], list[dict]]


def _wynik(status: str, *, trace_id: str | None = None, plan_revision: int | None = None,
           paragraphs: list[str] | None = None, used: list[str] | None = None,
           refs: list[dict] | None = None, actions: list[dict] | None = None,
           historical: bool = False) -> dict:
    return {
        "status": status, "trace_id": trace_id, "plan_revision": plan_revision,
        "paragraphs": paragraphs or [], "used_fact_keys": used or [],
        "article_refs": refs or [], "actions": actions or [], "historical": historical,
    }


def _refs(karty: list[dict]) -> list[dict]:
    return [{"id": k["id"], "revision": int(k["revision"])} for k in karty]


def _akcje_kart(karty: list[dict]) -> list[dict]:
    return [{"label": k["title"], "type": "open_article", "target_id": k["id"]} for k in karty]


def rozstrzygnij(kontekst: Kontekst, trace: dict | None, target_type: str,
                 artykuly: ArtykulyFn, ogolne: OgolneFn) -> tuple[int, dict | None]:
    """Kroki 1, 3–9. Zwraca (kod HTTP, ExplanationResult | None dla 404)."""
    if kontekst.mode not in TRYBY:
        return 422, None
    # 1. Dostęp: właściciel planu albo trener z potwierdzonym dostępem.
    if kontekst.authenticated_owner != kontekst.plan_owner and not kontekst.coach_access:
        return 404, None
    historia = kontekst.mode == "history"
    # 3. Aktywna ścieżka bezpieczeństwa: istniejąca ścieżka + edukacja ogólna,
    #    bez nowej porady i bez doboru zamiennika.
    if kontekst.active_safety_block:
        karty = ogolne("safety") + ogolne(target_type)
        return 200, _wynik(
            "restricted", plan_revision=kontekst.requested_plan_revision,
            paragraphs=[KOMUNIKAT_BEZPIECZENSTWO], refs=_refs(karty),
            actions=[{"label": "Napisz do trenera", "type": "open_safety_flow",
                      "target_id": "/wiadomosci"}] + _akcje_kart(karty),
            historical=historia,
        )
    # 4. Brak śladu (albo ślad spoza tej rewizji/właściciela) → missing_trace.
    if (trace is None or trace.get("owner_id") != kontekst.plan_owner
            or int(trace.get("plan_revision", -1)) != kontekst.requested_plan_revision):
        karty = ogolne(target_type)
        return 200, _wynik(
            "missing_trace", plan_revision=kontekst.requested_plan_revision,
            paragraphs=[KOMUNIKAT_BRAK_SLADU], refs=_refs(karty), actions=_akcje_kart(karty),
            historical=historia,
        )
    # 5. Widok bieżący musi zgadzać się z aktualną rewizją; historia jest osobnym trybem.
    if not historia and kontekst.requested_plan_revision != kontekst.current_plan_revision:
        return 409, _wynik("stale_context", trace_id=trace["id"],
                           plan_revision=kontekst.requested_plan_revision,
                           paragraphs=[KOMUNIKAT_NIEAKTUALNE])
    karty_ogolne = ogolne(target_type)
    # 6. Jakość danych.
    jakosc = trace.get("data_quality")
    regula = reguly.regula_dla(trace)
    if jakosc == "conflicting":
        return 200, _wynik("inconsistent_data", trace_id=trace["id"],
                           plan_revision=trace["plan_revision"], paragraphs=[KOMUNIKAT_SPRZECZNE],
                           refs=_refs(karty_ogolne), actions=_akcje_kart(karty_ogolne),
                           historical=historia)
    if jakosc == "missing" or (jakosc == "partial" and not (regula and regula.czesciowe_dozwolone)):
        return 200, _wynik("insufficient_data", trace_id=trace["id"],
                           plan_revision=trace["plan_revision"], paragraphs=[KOMUNIKAT_NIEPELNE],
                           refs=_refs(karty_ogolne), actions=_akcje_kart(karty_ogolne),
                           historical=historia)
    # 7. Reguła, wymagane fakty, typy, jednostki, zgodność wyniku z regułą.
    if regula is None:
        return 200, _wynik("inconsistent_data", trace_id=trace["id"],
                           plan_revision=trace["plan_revision"], paragraphs=[KOMUNIKAT_SPRZECZNE],
                           refs=_refs(karty_ogolne), actions=_akcje_kart(karty_ogolne),
                           historical=historia)
    blad, _powod = reguly.sprawdz(regula, trace)
    if blad:
        tekst = KOMUNIKAT_SPRZECZNE if blad == "inconsistent_data" else KOMUNIKAT_NIEPELNE
        return 200, _wynik(blad, trace_id=trace["id"], plan_revision=trace["plan_revision"],
                           paragraphs=[tekst], refs=_refs(karty_ogolne),
                           actions=_akcje_kart(karty_ogolne), historical=historia)
    # 8. Opublikowane karty wskazane przez ślad (fallback: ogólne typu i reguły).
    karty = artykuly(list(trace.get("article_ids") or []))
    if not karty:
        karty = artykuly(list(regula.artykuly)) or karty_ogolne
    # 9. Tekst wyłącznie z dozwolonych faktów.
    akapity, uzyte = reguly.renderuj(regula, trace, historia=historia)
    akcje = [{"label": et, "type": typ, "target_id": cel} for et, typ, cel in regula.akcje]
    znane = {a["target_id"] for a in akcje}
    akcje += [a for a in _akcje_kart(karty) if a["target_id"] not in znane]
    return 200, _wynik("explained", trace_id=trace["id"], plan_revision=trace["plan_revision"],
                       paragraphs=akapity, used=uzyte, refs=_refs(karty), actions=akcje,
                       historical=historia)


# --- warstwa bazodanowa -------------------------------------------------------


def _plan(db: Session, plan_kind: str, plan_id: str):
    if plan_kind == "training":
        return db.get(TrainingPlan, plan_id)
    if plan_kind == "nutrition":
        return db.get(NutritionPlan, plan_id)
    return None


def _blokada_bezpieczenstwa(db: Session, plan: TrainingPlan, dzis: date) -> bool:
    """Ból zgłoszony w sesji BIEŻĄCEJ wersji planu w ostatnich 7 dniach,
    później niż powstała ta wersja (nowa wersja trenera zamyka ścieżkę)."""
    wersja = (
        db.query(TrainingPlanVersion)
        .filter_by(plan_id=plan.id, version_no=plan.current_version_no).first()
    )
    if wersja is None:
        return False
    od = (dzis - timedelta(days=DNI_BLOKADY_PO_BOLU)).isoformat()
    sesja = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.plan_version_id == wersja.id,
                WorkoutSession.pain_flag.is_(True),
                WorkoutSession.performed_on >= od)
        .order_by(WorkoutSession.created_at.desc()).first()
    )
    return sesja is not None and sesja.created_at >= wersja.created_at


def wyjasnij(db: Session, user: User, *, plan_kind: str, plan_id: str, plan_revision: int,
             target_type: str, target_id: str, tryb: str, dzis: date | None = None
             ) -> tuple[int, dict | None]:
    """Kroki 1–2, 10 po stronie serwera; reszta w `rozstrzygnij`."""
    dzis = dzis or local_today()
    plan = _plan(db, plan_kind, plan_id)
    if plan is None or plan.client_id is None:
        deny(user.id, f"wiedza:{plan_kind}:{plan_id}")
    domena = DOMAIN_TRAINING if plan_kind == "training" else DOMAIN_NUTRITION
    # resolve_client_access: sam klient albo trener z relacją i zgodą; inaczej
    # logowana odmowa 404 (bez potwierdzenia istnienia planu).
    resolve_client_access(db, user, plan.client_id, domain=domena)
    coach_access = user.id != plan.client_id
    biezaca = int(plan.current_version_no)
    blokada = plan_kind == "training" and _blokada_bezpieczenstwa(db, plan, dzis)
    row = slad.znajdz(db, owner_id=plan.client_id, plan_kind=plan_kind, plan_id=plan_id,
                      plan_revision=plan_revision, target_type=target_type, target_id=target_id)
    trace = slad.do_schematu(row) if row is not None else None
    kontekst = Kontekst(
        authenticated_owner=user.id, plan_owner=plan.client_id,
        current_plan_revision=biezaca, requested_plan_revision=int(plan_revision),
        mode=tryb, active_safety_block=blokada, coach_access=coach_access,
    )
    eid = _konfigurator_id(db, plan, plan_revision, target_id) if target_type == "exercise_prescription" else None
    kod, wynik = rozstrzygnij(kontekst, trace, target_type,
                              lambda ids: _karty(db, ids, dzis), lambda t: _ogolne(db, t, dzis, eid))
    # 10. Plan nie mógł zmienić rewizji w trakcie — inaczej stale_context.
    if kod == 200 and tryb == "current":
        db.expire(plan)
        if int(plan.current_version_no) != biezaca:
            return 409, _wynik("stale_context", trace_id=None, plan_revision=int(plan_revision),
                               paragraphs=[KOMUNIKAT_NIEAKTUALNE])
    return kod, wynik


def _karty(db: Session, ids: list[str], dzis: date) -> list[dict]:
    """Karty wskazane przez ślad: tylko widoczne i z aktualnym przeglądem —
    wygasła treść nie jest aktualnym uzasadnieniem."""
    out = []
    for aid in ids:
        r = tresci.aktualna(db, aid)
        if r is None or tresci.przeglad_wygasl(r, dzis):
            continue
        out.append(tresci.naglowek(r, dzis=dzis))
    return out


#: Cele złożone (jeden ślad = kilka parametrów) → typy wiedzy ogólnej,
#: z których składa się edukacja przy braku śladu.
TYPY_POCHODNE: dict[str, tuple[str, ...]] = {
    "exercise_prescription": ("work_sets", "rep_range", "rir", "rest", "load"),
}


def _ogolne(db: Session, target_type: str, dzis: date, exercise_id: str | None = None) -> list[dict]:
    typy = (target_type,) + TYPY_POCHODNE.get(target_type, ())
    out: list[dict] = []
    widziane: set[str] = set()
    if exercise_id and target_type in TYPY_POCHODNE:
        for r in tresci.powiazane(db, "exercise", exercise_id):
            if r.article_id not in widziane and not tresci.przeglad_wygasl(r, dzis):
                widziane.add(r.article_id)
                out.append(tresci.naglowek(r, dzis=dzis))
    for typ in typy:
        for r in tresci.powiazane(db, typ):
            if r.article_id in widziane or tresci.przeglad_wygasl(r, dzis):
                continue
            widziane.add(r.article_id)
            out.append(tresci.naglowek(r, dzis=dzis))
    return out


def _konfigurator_id(db: Session, plan, plan_revision: int, target_id: str) -> str | None:
    """`d{dzień}:e{ćwiczenie}` → `konfigurator_id` z treści wersji (atlas)."""
    import json
    import re

    m = re.fullmatch(r"d(\d+):e(\d+)", target_id)
    if not m or not isinstance(plan, TrainingPlan):
        return None
    v = db.query(TrainingPlanVersion).filter_by(plan_id=plan.id, version_no=int(plan_revision)).first()
    if v is None:
        return None
    try:
        dni = json.loads(v.content_json).get("days") or []
        return dni[int(m.group(1))]["exercises"][int(m.group(2))].get("konfigurator_id")
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def historia_decyzji(db: Session, user: User, *, plan_kind: str, plan_id: str) -> list[dict]:
    """Lista rzeczywistych decyzji planu (W6): autor, powód, rewizja."""
    plan = _plan(db, plan_kind, plan_id)
    if plan is None or plan.client_id is None:
        deny(user.id, f"wiedza:{plan_kind}:{plan_id}")
    domena = DOMAIN_TRAINING if plan_kind == "training" else DOMAIN_NUTRITION
    resolve_client_access(db, user, plan.client_id, domain=domena)
    wersje = {}
    if plan_kind == "training":
        for v in db.query(TrainingPlanVersion).filter_by(plan_id=plan.id).all():
            wersje[v.version_no] = v
    else:
        for v in db.query(NutritionPlanVersion).filter_by(plan_id=plan.id).all():
            wersje[v.version_no] = v
    out = []
    for r in slad.historia(db, owner_id=plan.client_id, plan_kind=plan_kind, plan_id=plan.id):
        t = slad.do_schematu(r)
        w = wersje.get(r.plan_revision)
        out.append({
            "trace_id": r.id, "plan_revision": r.plan_revision, "target_type": r.target_type,
            "target_id": r.target_id, "decision_origin": r.decision_origin,
            "rule_id": r.rule_id, "outcome_code": r.outcome_code,
            "outcome_value": t["outcome_value"], "reason_note": r.reason_note,
            "created_at": r.created_at, "version_created_at": w.created_at if w else None,
            "version_reason": w.reason if w else None,
            "autor": ("Uzasadnienie autora planu" if r.decision_origin == "professional"
                      else "Ustawienie wybrane przez Ciebie" if r.decision_origin == "user"
                      else "Reguła konfiguratora"),
            "aktualna": r.plan_revision == int(plan.current_version_no),
        })
    return out

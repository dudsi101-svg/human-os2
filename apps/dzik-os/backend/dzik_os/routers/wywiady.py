"""Zakładka „Wywiad” (0.59.0) — API klienta i trenera.

Klient: `GET /api/clients/{id}/wywiady` (stany obu formularzy),
`GET …/{typ}/definicja` (pytania z flagami aktywne/wymagane liczonymi
serwerowo + odpowiedzi szkicu), `PATCH …/{typ}/szkic` (zapis częściowy
z rewizją; 409 REVISION_CONFLICT), `POST …/{typ}/przeslij` (rewizja +
klucz idempotencji; 422 z listą braków), `GET …/{typ}/historia`,
`GET …/podsumowanie`.

Trener (aktywna relacja + zgody domen): to samo w trybie odczytu, plus
`POST /api/wywiady/zgloszenia/{id}/przeglad` (Oznacz jako przejrzane —
nie „dopuszczenie”), `POST …/doprecyzowania` (Poproś o uzupełnienie),
`PATCH …/szkic` z `collection_mode=WSPOLNIE` (Uzupełnij wspólnie),
`POST …/{typ}/przypomnij`, `GET /api/coach/wywiady/do-przegladu`,
`GET …/podpowiedzi` (wejścia konfiguratorów), zadania sprawdzenia planu.

Trener bez relacji = 404 (jak wszędzie). Trener Z relacją, ale bez zgody
kategorii = 200 z `access.ok=false` i POWODEM w przeglądzie stanów —
brak dostępu nie może wyglądać jak awaria. Odpowiedzi domeny bez zgody
są ukryte (`hidden`), nie „nieistniejące”.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import notifications
from ..authz import (
    DOMAIN_COLLABORATION,
    DOMAIN_HEALTH,
    DOMAIN_NUTRITION,
    active_relationship,
    coach_can_access_client,
    deny,
    resolve_client_access,
)
from ..config import settings
from ..db import get_db
from ..idempotency import replay_response, request_fingerprint, store_response
from ..models import (
    ClientFactRevision,
    CoachClientRelationship,
    InterviewSubmission,
    Measurement,
    PlanReviewTask,
    User,
)
from ..publikacja import serwis as publikacja_serwis
from ..security import active_roles, current_user, require_role
from ..wywiad import definicje as D
from ..wywiad import podsumowanie, serwis

router = APIRouter(prefix="/api", tags=["wywiady"])


# --- wejścia ---------------------------------------------------------------------------


class OdpowiedzIn(BaseModel):
    value: str | None = Field(default=None, max_length=4000)
    skipped: bool = False


class SzkicIn(BaseModel):
    revision: int = Field(ge=1)
    answers: dict[str, OdpowiedzIn] = Field(default_factory=dict)
    # SELF (klient) / WSPOLNIE (trener razem z klientem).
    collection_mode: str | None = Field(default=None, pattern="^(SELF|WSPOLNIE)$")


class PrzeslijIn(BaseModel):
    revision: int = Field(ge=1)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=80)


class PrzegladIn(BaseModel):
    outcome: str = Field(pattern="^(REVIEWED|NEEDS_CLARIFICATION)$")
    internal_note: str | None = Field(default=None, max_length=4000)


class DoprecyzowanieIn(BaseModel):
    question_ids: list[str] = Field(default_factory=list, max_length=60)
    message: str = Field(default="", max_length=2000)


class RozstrzygnijIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


# --- dostęp ----------------------------------------------------------------------------


def typy_aktywne() -> tuple[str, ...]:
    """Typy wywiadu dostępne w tej instalacji (zapotrzebowanie za flagą)."""
    if settings.calorie_interview_enabled:
        return D.TYPY
    return tuple(t for t in D.TYPY if t != D.ZAPOTRZEBOWANIE)


def _typ(typ: str) -> str:
    if typ not in typy_aktywne():
        raise HTTPException(status_code=404, detail="Nieznany typ wywiadu")
    return typ


def _dostep(db: Session, user: User, client_id: str) -> dict:
    """Kto ogląda i co wolno. Klient: pełny dostęp do własnych danych.
    Trener: relacja ACTIVE obowiązkowa (inaczej 404 z audytem); zgody per
    domena decydują o widoczności i o tym, o co wolno pytać."""
    roles = active_roles(db, user.id)
    if user.id == client_id and "CLIENT" in roles:
        coach_id = serwis.trener_klienta(db, client_id)
        return {"viewer": "client", "coach_id": coach_id, "ok": True, "reason": None,
                "allowed_domains": serwis.domeny_zgod(db, client_id, coach_id),
                "visible_domains": {DOMAIN_HEALTH, DOMAIN_NUTRITION},
                "missing_domains": [], "has_coach": coach_id is not None}
    if "COACH" in roles and active_relationship(db, user.id, client_id) is not None:
        klient = db.get(User, client_id)
        wsp = coach_can_access_client(db, user.id, client_id, domain=DOMAIN_COLLABORATION)
        widoczne = serwis.domeny_widoczne(db, user, client_id)
        brak = [d for d in (DOMAIN_HEALTH, DOMAIN_NUTRITION) if d not in widoczne]
        powod = None
        if klient is not None and klient.status != "ACTIVE":
            wsp = False
            powod = ("Konto klienta czeka na aktywację (klient nie ustawił jeszcze hasła z zaproszenia). "
                     "Wywiad będzie można wypełnić po aktywacji — to nie jest błąd techniczny.")
        elif not wsp:
            powod = ("Klient nie potwierdził jeszcze zgód na współpracę w aplikacji (albo je cofnął). "
                     "Wywiad będzie widoczny po potwierdzeniu zgód przez klienta — to nie jest błąd techniczny.")
        return {"viewer": "coach", "coach_id": user.id, "ok": wsp, "reason": powod,
                "allowed_domains": serwis.domeny_zgod(db, client_id, user.id) if wsp else set(),
                "visible_domains": widoczne if wsp else set(), "missing_domains": brak,
                "has_coach": True}
    deny(user.id, f"wywiad:{client_id}")
    raise AssertionError("unreachable")


def _dostep_pelny(db: Session, user: User, client_id: str) -> dict:
    d = _dostep(db, user, client_id)
    if not d["ok"]:
        # Trener z relacją, ale bez zgody współpracy albo z kontem klienta
        # przed aktywacją: przegląd stanów podaje powód, wszystkie inne trasy
        # odmawiają jak resolve_client_access (404 + wpis w audycie).
        deny(user.id, f"wywiad:{client_id}")
    return d


def _zgloszenie_trenera(db: Session, coach: User, submission_id: str) -> InterviewSubmission:
    sub = db.get(InterviewSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, coach, sub.client_id, domain=DOMAIN_COLLABORATION)
    return sub


def _konflikt(kod: str, detail: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": detail, "code": kod, **extra})


def _po_commicie(db: Session, ev_id: str | None) -> None:
    """Próba doręczenia od razu po commicie (outbox ponowi w pętli)."""
    if not ev_id:
        return
    try:
        sent = publikacja_serwis.przetworz_outbox(db, tylko_id=ev_id)
        db.commit()
        for n in sent:
            if "center" in (n.channels or ""):
                notifications.bus.publish(n.user_id, notifications.realtime_payload(n))
    except Exception:  # noqa: BLE001 — outbox ponowi; zdarzenie jest trwałe
        db.rollback()


# --- przegląd stanów --------------------------------------------------------------------


@router.get("/clients/{client_id}/wywiady")
def przeglad(client_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _dostep(db, user, client_id)
    out = {
        "client_id": client_id,
        "access": {"ok": d["ok"], "reason": d["reason"], "viewer": d["viewer"],
                   "has_coach": d["has_coach"], "missing_domains": d["missing_domains"],
                   "visible_domains": sorted(d["visible_domains"])},
        "wywiady": [], "review_tasks": [],
    }
    if not d["ok"]:
        return out
    for typ in typy_aktywne():
        out["wywiady"].append(serwis.stany(db, client_id=client_id, typ=typ,
                                           allowed_domains=d["allowed_domains"]))
    if d["viewer"] == "coach":
        out["review_tasks"] = [serwis.zadanie_out(t) for t in
                               db.query(PlanReviewTask).filter_by(client_id=client_id, coach_id=user.id,
                                                                  status="OPEN")
                               .order_by(PlanReviewTask.created_at).all()]
    return out


@router.get("/clients/{client_id}/wywiady/{typ}/definicja")
def definicja(client_id: str, typ: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    typ = _typ(typ)
    d = _dostep_pelny(db, user, client_id)
    defn = D.definicja(typ)
    szk = serwis.szkic(db, client_id, typ)
    answers = serwis.odpowiedzi_szkicu(szk)
    out = D.definicja_out(defn, answers, d["allowed_domains"])
    out["answers"] = serwis.odpowiedzi_out(defn, answers, d["visible_domains"],
                                           allowed_domains=d["allowed_domains"])
    out["draft"] = {"revision": szk.revision, "updated_at": szk.updated_at, "dirty": szk.dirty,
                    "collection_mode": szk.collection_mode, "updated_by": szk.updated_by} if szk else None
    # Kontekst z faktów (wywiad głęboki pokazuje, co wskazano we wstępnym).
    fakty = serwis.fakty_biezace(db, client_id)
    out["facts"] = {k: {"value": f.value, "source_type": f.source_type, "question_id": f.question_id,
                        "author_id": f.author_id, "created_at": f.created_at, "version": f.version}
                    for k, f in fakty.items()
                    if not f.sensitive or _domena_faktu(defn, k) in d["visible_domains"] or d["viewer"] == "client"}
    out["has_coach"] = d["has_coach"]
    if typ == D.ZAPOTRZEBOWANIE:
        # Podpowiedź masy z ostatniego pomiaru (zakładka Pomiary) — tylko
        # placeholder; wartość musi potwierdzić osoba wypełniająca.
        ost = (db.query(Measurement).filter_by(client_id=client_id, kind="weight")
               .order_by(Measurement.measured_at.desc(), Measurement.created_at.desc()).first())
        if ost is not None:
            for q in out["questions"]:
                if q["question_id"] == "zk_masa":
                    q["placeholder"] = f"ostatni pomiar: {str(ost.value).replace('.', ',')} {ost.unit}"
    return out


def _domena_faktu(defn: D.Definicja, fact_key: str) -> str | None:
    for t in D.TYPY:
        for q in D.definicja(t).questions:
            if q.fact_key == fact_key:
                return q.consent_domain
    return None


@router.patch("/clients/{client_id}/wywiady/{typ}/szkic")
def zapisz_szkic(client_id: str, typ: str, body: SzkicIn, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    """Autozapis / „Zapisz szkic”. Trener może zapisywać wyłącznie w trybie
    WSPOLNIE (widocznym dla klienta). Nic nie jest wysyłane."""
    typ = _typ(typ)
    d = _dostep_pelny(db, user, client_id)
    tryb = body.collection_mode
    if d["viewer"] == "coach" and tryb != "WSPOLNIE":
        raise HTTPException(status_code=422, detail="Trener uzupełnia wywiad wyłącznie w trybie „wspólnie” "
                                                        "(collection_mode=WSPOLNIE).")
    answers = {k: v.model_dump() for k, v in body.answers.items()}
    try:
        szk, bledy = serwis.zapisz_szkic(db, client_id=client_id, typ=typ, actor=user, revision=body.revision,
                                         answers=answers, collection_mode=tryb,
                                         allowed_domains=d["allowed_domains"])
    except serwis.KonfliktRewizji as e:
        szk = serwis.szkic(db, client_id, typ)
        return _konflikt("REVISION_CONFLICT", "Szkic został zmieniony na innym urządzeniu — odśwież widok.",
                         revision=e.aktualna,
                         answers=serwis.odpowiedzi_out(D.definicja(typ), serwis.odpowiedzi_szkicu(szk),
                                                       d["visible_domains"], allowed_domains=d["allowed_domains"]))
    db.commit()
    defn = D.definicja(typ)
    a = serwis.odpowiedzi_szkicu(szk)
    return {"revision": szk.revision, "saved_at": szk.updated_at, "errors": bledy,
            "progress": D.postep(defn, a, d["allowed_domains"]),
            "active": [q.question_id for q in D.aktywne(defn, a, d["allowed_domains"])],
            "required": [q.question_id for q in D.wymagane_aktywne(defn, a, d["allowed_domains"])],
            "collection_mode": szk.collection_mode}


@router.post("/clients/{client_id}/wywiady/{typ}/przeslij", status_code=201)
def przeslij(client_id: str, typ: str, body: PrzeslijIn, user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    """„Prześlij trenerowi” / „Aktualizuj odpowiedzi”. Klient sam (trener
    w trybie wspólnym też może, ale wersja nosi jego autorstwo)."""
    typ = _typ(typ)
    d = _dostep_pelny(db, user, client_id)
    odcisk = request_fingerprint({"client_id": client_id, "typ": typ, "revision": body.revision})
    if body.idempotency_key:
        prev = replay_response(db, user_id=user.id, operation=f"wywiad.przeslij.{typ}",
                               key=body.idempotency_key, fingerprint=odcisk)
        if prev is not None:
            return JSONResponse(status_code=200, content=prev)
    try:
        wynik = serwis.przeslij(db, client_id=client_id, typ=typ, actor=user, revision=body.revision,
                                allowed_domains=d["allowed_domains"])
    except serwis.KonfliktRewizji as e:
        return _konflikt("REVISION_CONFLICT", "Szkic zmienił się od ostatniego zapisu — odśwież i prześlij ponownie.",
                         revision=e.aktualna)
    except serwis.BladWalidacji as e:
        return JSONResponse(status_code=422, content={
            "detail": "Uzupełnij wymagane odpowiedzi, zanim prześlesz.", "code": "MISSING_ANSWERS",
            "errors": e.bledy, "missing": e.braki})
    if body.idempotency_key:
        store_response(db, user_id=user.id, operation=f"wywiad.przeslij.{typ}", key=body.idempotency_key,
                       fingerprint=odcisk, response=wynik)
    db.commit()
    _po_commicie(db, wynik.get("outbox_event_id"))
    return wynik


@router.get("/clients/{client_id}/wywiady/{typ}/historia")
def historia(client_id: str, typ: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    typ = _typ(typ)
    d = _dostep_pelny(db, user, client_id)
    subs = serwis.przeslania(db, client_id, typ)
    return {"typ": typ, "submissions": [
        serwis.przeslanie_out(db, s, widoczne=d["visible_domains"], pokaz_notatki=d["viewer"] == "coach")
        for s in subs]}


@router.get("/clients/{client_id}/wywiady/podsumowanie")
def podsumowanie_klienta(client_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _dostep_pelny(db, user, client_id)
    return podsumowanie.podsumowanie(db, client_id, widoczne=d["visible_domains"])


@router.get("/clients/{client_id}/wywiady/podpowiedzi")
def podpowiedzi(client_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Wejścia konfiguratora treningu i kreatora dań z faktów wywiadu —
    z pochodzeniem każdej podpowiedzi. Tylko trener z dostępem."""
    d = _dostep_pelny(db, coach, client_id)
    return podsumowanie.podpowiedzi(db, client_id, widoczne=d["visible_domains"])


@router.get("/clients/{client_id}/wywiady/fakty")
def fakty(client_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _dostep_pelny(db, user, client_id)
    rows = (db.query(ClientFactRevision).filter_by(client_id=client_id)
            .order_by(ClientFactRevision.fact_key, ClientFactRevision.version).all())
    out = []
    for r in rows:
        dom = _domena_faktu(D.definicja(D.WSTEPNY), r.fact_key) or _domena_faktu(D.definicja(D.GLEBOKI), r.fact_key)
        if r.sensitive and d["viewer"] == "coach" and dom not in d["visible_domains"]:
            continue
        out.append({"id": r.id, "fact_key": r.fact_key, "value": r.value, "source_type": r.source_type,
                    "source_id": r.source_id, "question_id": r.question_id, "author_id": r.author_id,
                    "version": r.version, "is_current": r.is_current, "created_at": r.created_at})
    return {"facts": out}


@router.post("/clients/{client_id}/wywiady/{typ}/przypomnij", status_code=201)
def przypomnij(client_id: str, typ: str, coach: User = Depends(require_role("COACH")),
               db: Session = Depends(get_db)):
    """„Poproś o wypełnienie” (not_started) / „Przypomnij” (draft). Jawna
    akcja trenera, jeden wpis dziennie. Dla wersji przesłanej — 409."""
    typ = _typ(typ)
    d = _dostep_pelny(db, coach, client_id)
    st = serwis.stany(db, client_id=client_id, typ=typ, allowed_domains=d["allowed_domains"])
    if st["submission_status"] == "submitted" and st["freshness_status"] == "current":
        return _konflikt("ALREADY_SUBMITTED", "Ten wywiad jest już przesłany — użyj „Poproś o uzupełnienie”.")
    ev = serwis.przypomnij(db, client_id=client_id, typ=typ, coach=coach,
                           submission_status=st["submission_status"])
    db.commit()
    _po_commicie(db, ev.id if ev else None)
    return {"sent": ev is not None, "deduplicated": ev is None,
            "note": None if ev else "Prośba o ten wywiad została już dziś wysłana."}


# --- trener: przegląd, doprecyzowania, lista, zadania --------------------------------------


@router.post("/wywiady/zgloszenia/{submission_id}/przeglad", status_code=201)
def przeglad_wersji(submission_id: str, body: PrzegladIn, coach: User = Depends(require_role("COACH")),
                    db: Session = Depends(get_db)):
    """„Oznacz jako przejrzane” — potwierdzenie zapoznania się z wersją,
    NIE dopuszczenie do treningu. Notatka wewnętrzna zostaje u trenera."""
    sub = _zgloszenie_trenera(db, coach, submission_id)
    r = serwis.przejrzyj(db, sub=sub, coach=coach, outcome=body.outcome, internal_note=body.internal_note)
    ev = None
    if body.outcome == "REVIEWED":
        from ..models import OutboxEvent
        ev = (db.query(OutboxEvent).filter_by(event_type="INTERVIEW_REVIEWED", aggregate_id=sub.id,
                                              recipient_id=sub.client_id).one_or_none())
    db.commit()
    _po_commicie(db, ev.id if ev and ev.status == "PENDING" else None)
    return {"review_id": r.id, "outcome": r.outcome, "created_at": r.created_at,
            "submission_id": sub.id, "version_no": sub.version_no}


@router.post("/wywiady/zgloszenia/{submission_id}/doprecyzowania", status_code=201)
def doprecyzowanie(submission_id: str, body: DoprecyzowanieIn, coach: User = Depends(require_role("COACH")),
                   db: Session = Depends(get_db)):
    sub = _zgloszenie_trenera(db, coach, submission_id)
    try:
        cr = serwis.popros_o_doprecyzowanie(db, sub=sub, coach=coach, question_ids=body.question_ids,
                                            message=body.message)
    except serwis.BladWalidacji as e:
        return JSONResponse(status_code=422, content={"detail": "Nieznane pytania w prośbie.",
                                                     "code": "UNKNOWN_QUESTIONS", "errors": e.bledy})
    from ..models import OutboxEvent
    ev = (db.query(OutboxEvent).filter_by(event_type="CLARIFICATION_REQUESTED", aggregate_id=cr.id,
                                          recipient_id=sub.client_id).one_or_none())
    db.commit()
    _po_commicie(db, ev.id if ev else None)
    return serwis.doprecyzowanie_out(cr)


@router.get("/wywiady/zgloszenia/{submission_id}")
def zgloszenie(submission_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sub = db.get(InterviewSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    d = _dostep_pelny(db, user, sub.client_id)
    return serwis.przeslanie_out(db, sub, widoczne=d["visible_domains"], pokaz_notatki=d["viewer"] == "coach")


@router.get("/coach/wywiady/do-przegladu")
def do_przegladu(coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Lista „Wywiady do przejrzenia”: ostatnia wersja bez przeglądu,
    otwarte doprecyzowania, otwarte zadania sprawdzenia planu, szkice
    bez przesłania — per klient z aktywną relacją i zgodą współpracy."""
    rels = (db.query(CoachClientRelationship)
            .filter_by(coach_id=coach.id, status="ACTIVE").all())
    out = []
    for rel in rels:
        client = db.get(User, rel.client_id)
        if client is None or client.status != "ACTIVE":
            continue
        if not coach_can_access_client(db, coach.id, rel.client_id, domain=DOMAIN_COLLABORATION):
            continue
        dom = serwis.domeny_zgod(db, rel.client_id, coach.id)
        pozycje = []
        for typ in D.TYPY:
            st = serwis.stany(db, client_id=rel.client_id, typ=typ, allowed_domains=dom)
            pozycje.append({k: st[k] for k in ("typ", "title", "submission_status", "review_status",
                                                 "freshness_status", "progress", "last_submission")})
        zad = (db.query(PlanReviewTask).filter_by(client_id=rel.client_id, coach_id=coach.id, status="OPEN")
               .count())
        # Ostatnia przesłana wersja bez przeglądu — niezależnie od tego, czy
        # klient już zaczął kolejny szkic (wersja czeka na trenera tak czy inaczej).
        do_przejrzenia = any(p["last_submission"] is not None and p["review_status"] == "not_reviewed"
                             for p in pozycje)
        out.append({"client_id": client.id, "display_name": client.display_name, "wywiady": pozycje,
                    "open_review_tasks": zad, "needs_review": do_przejrzenia,
                    "not_started": all(p["submission_status"] == "not_started" for p in pozycje)})
    out.sort(key=lambda r: (not r["needs_review"], -r["open_review_tasks"], r["display_name"]))
    return {"clients": out, "needs_review": sum(1 for r in out if r["needs_review"])}


@router.get("/wywiady/zadania")
def zadania(coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    rows = (db.query(PlanReviewTask).filter_by(coach_id=coach.id, status="OPEN")
            .order_by(PlanReviewTask.created_at).all())
    return {"tasks": [serwis.zadanie_out(t) for t in rows]}


@router.post("/wywiady/zadania/{task_id}/rozstrzygnij")
def rozstrzygnij(task_id: str, body: RozstrzygnijIn, coach: User = Depends(require_role("COACH")),
                 db: Session = Depends(get_db)):
    """Trener sprawdził plan po zmianie faktów: zamknięcie zadania
    odblokowuje publikację zależnej wersji. Plan sam się nie zmienia."""
    t = db.get(PlanReviewTask, task_id)
    if t is None or t.coach_id != coach.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if t.status != "OPEN":
        return serwis.zadanie_out(t)
    serwis.rozstrzygnij_zadanie(db, task=t, coach=coach, note=body.note)
    db.commit()
    return serwis.zadanie_out(t)


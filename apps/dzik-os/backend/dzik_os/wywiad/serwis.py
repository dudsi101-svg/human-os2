"""Serwis wywiadu: szkic (rewizja), przesłanie (wersja + fakty + zadania
sprawdzenia + outbox w jednej transakcji), przegląd trenera, prośby
o doprecyzowanie, przypomnienia, doręczanie zdarzeń z outboxu.

Zasady (specyfikacja właściciela 13.09):
* widoczność i wymagalność pytań liczy serwer (`definicje`), nigdy
  przeglądarka; odpowiedzi nieaktywnej gałęzi zostają w szkicu, ale nie
  trafiają do wersji ani do faktów;
* wersja jest niezmienna; nowa wersja = przegląd od nowa;
* statusy są ROZDZIELONE: `submission_status` (not_started / draft /
  submitted), `review_status` (not_reviewed / needs_clarification /
  reviewed — dla ostatniej wersji), `freshness_status` (current /
  update_requested);
* autozapis nie wysyła niczego; przesłanie = jedno zdarzenie dla trenera;
  prośba o doprecyzowanie = jedno dla klienta; przejrzenie = informacja
  dla klienta; przypomnienie = jawna akcja trenera z dedup dziennym;
* notatki wewnętrzne trenera nigdy nie wychodzą do klienta;
* odpowiedzi nie trafiają do logów, audytu ani powiadomień push.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from .. import notifications
from ..authz import (
    DOMAIN_HEALTH,
    DOMAIN_NUTRITION,
    coach_can_access_client,
)
from ..hos_bridge import record_event
from ..models import (
    ClarificationRequest,
    ClientFactRevision,
    CoachClientRelationship,
    InterviewDraft,
    InterviewReview,
    InterviewSubmission,
    Notification,
    NutritionPlan,
    OutboxEvent,
    PlanReviewTask,
    TrainingPlan,
    User,
    new_id,
    now_iso,
)
from ..onboarding_flow import scan_safety_signals
from ..profile_service import FieldWrite, apply_profile_fields
from . import definicje as D

# --- wyjątki ---------------------------------------------------------------------------


class KonfliktRewizji(Exception):
    def __init__(self, aktualna: int) -> None:
        super().__init__("rewizja")
        self.aktualna = aktualna


class BladWalidacji(Exception):
    def __init__(self, bledy: dict[str, str], braki: list[str] | None = None) -> None:
        super().__init__("walidacja")
        self.bledy = bledy
        self.braki = braki or []


# --- relacja, zgody -------------------------------------------------------------------


def trener_klienta(db: Session, client_id: str) -> str | None:
    """Trener z aktywnej relacji. Gdy jest ich więcej — najstarsza relacja
    (deterministycznie), a nie „pierwszy z brzegu”."""
    row = (
        db.query(CoachClientRelationship)
        .filter(CoachClientRelationship.client_id == client_id,
                CoachClientRelationship.status == "ACTIVE")
        .order_by(CoachClientRelationship.id)
        .first()
    )
    return row.coach_id if row else None


def domeny_zgod(db: Session, client_id: str, coach_id: str | None) -> set[str]:
    """Domeny wrażliwe, o które WOLNO pytać (aktywna zgoda dla trenera).
    Bez trenera — brak pytań wrażliwych (nie ma komu ich udostępnić)."""
    if coach_id is None:
        return set()
    return {d for d in (DOMAIN_HEALTH, DOMAIN_NUTRITION)
            if coach_can_access_client(db, coach_id, client_id, action="write", domain=d)}


def domeny_widoczne(db: Session, viewer: User, client_id: str) -> set[str]:
    """Domeny, których odpowiedzi oglądający może zobaczyć. Klient widzi
    wszystko, co sam powiedział."""
    if viewer.id == client_id:
        return {DOMAIN_HEALTH, DOMAIN_NUTRITION}
    return {d for d in (DOMAIN_HEALTH, DOMAIN_NUTRITION)
            if coach_can_access_client(db, viewer.id, client_id, domain=d)}


# --- szkic ----------------------------------------------------------------------------


def szkic(db: Session, client_id: str, typ: str) -> InterviewDraft | None:
    return db.query(InterviewDraft).filter_by(client_id=client_id, typ=typ).one_or_none()


def odpowiedzi_szkicu(d: InterviewDraft | None) -> dict[str, dict]:
    if d is None:
        return {}
    try:
        data = json.loads(d.answers_json or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def utworz_lub_pobierz_szkic(db: Session, *, client_id: str, typ: str, actor: User,
                             collection_mode: str = "SELF") -> InterviewDraft:
    d = szkic(db, client_id, typ)
    if d is not None:
        return d
    ostatnia = ostatnie_przeslanie(db, client_id, typ)
    d = InterviewDraft(
        id=new_id("IVD"), client_id=client_id, typ=typ, definition_version=D.WERSJA,
        answers_json=ostatnia.answers_json if ostatnia else "{}", revision=1,
        dirty=ostatnia is None, collection_mode=collection_mode,
        created_by=actor.id, updated_by=actor.id,
        last_submission_id=ostatnia.id if ostatnia else None,
    )
    db.add(d)
    db.flush()
    return d


def zapisz_szkic(db: Session, *, client_id: str, typ: str, actor: User, revision: int,
                 answers: dict[str, Any], collection_mode: str | None,
                 allowed_domains: set[str]) -> tuple[InterviewDraft, dict[str, str]]:
    """Zapis częściowy: scala podane odpowiedzi ze szkicem, waliduje każdą
    (błędne pola wracają w `bledy` i NIE są zapisywane — reszta tak),
    podbija rewizję. Konflikt rewizji → KonfliktRewizji (409)."""
    defn = D.definicja(typ)
    d = utworz_lub_pobierz_szkic(db, client_id=client_id, typ=typ, actor=actor,
                                 collection_mode=collection_mode or "SELF")
    if revision != d.revision:
        raise KonfliktRewizji(d.revision)
    biezace = odpowiedzi_szkicu(d)
    bledy: dict[str, str] = {}
    by_id = defn.by_id
    teraz = now_iso()
    for qid, a in answers.items():
        q = by_id.get(qid)
        if q is None:
            bledy[qid] = "Nieznane pytanie."
            continue
        if q.consent_domain is not None and q.consent_domain not in allowed_domains:
            bledy[qid] = "To pytanie nie jest aktywne (brak zgody na tę kategorię danych)."
            continue
        if not isinstance(a, dict):
            bledy[qid] = "Nieprawidłowy format odpowiedzi."
            continue
        if a.get("skipped"):
            biezace[qid] = {"value": "", "skipped": True, "entered_by": actor.id, "at": teraz}
            continue
        value = a.get("value")
        if value is None or (isinstance(value, str) and not value.strip()):
            # Wyczyszczenie pola = usunięcie odpowiedzi (nie pominięcie).
            biezace.pop(qid, None)
            continue
        try:
            norm = D.waliduj(q, str(value))
        except ValueError as exc:
            bledy[qid] = str(exc)
            continue
        biezace[qid] = {"value": norm, "skipped": False, "entered_by": actor.id, "at": teraz}
    d.answers_json = json.dumps(biezace, ensure_ascii=False)
    d.revision += 1
    d.dirty = True
    d.updated_by = actor.id
    d.updated_at = teraz
    if collection_mode:
        d.collection_mode = collection_mode
    db.flush()
    return d, bledy


# --- przesłania ------------------------------------------------------------------------


def ostatnie_przeslanie(db: Session, client_id: str, typ: str) -> InterviewSubmission | None:
    return (
        db.query(InterviewSubmission).filter_by(client_id=client_id, typ=typ)
        .order_by(InterviewSubmission.version_no.desc()).first()
    )


def przeslania(db: Session, client_id: str, typ: str) -> list[InterviewSubmission]:
    return (
        db.query(InterviewSubmission).filter_by(client_id=client_id, typ=typ)
        .order_by(InterviewSubmission.version_no).all()
    )


def przeglad_wersji(db: Session, submission_id: str) -> InterviewReview | None:
    return (
        db.query(InterviewReview).filter_by(submission_id=submission_id)
        .order_by(InterviewReview.created_at.desc(), InterviewReview.id.desc()).first()
    )


def otwarte_doprecyzowania(db: Session, client_id: str, typ: str) -> list[ClarificationRequest]:
    return (
        db.query(ClarificationRequest)
        .filter_by(client_id=client_id, typ=typ, status="OPEN")
        .order_by(ClarificationRequest.created_at).all()
    )


#: Klucze faktów istotnych dla planów: zmiana → zadanie sprawdzenia
#: aktywnego planu danego rodzaju. Pytania warunkowe (opis urazu) wchodzą
#: przez klucz nadrzędny.
FAKTY_PLANU: dict[str, tuple[str, ...]] = {
    "cel_glowny": ("training", "nutrition"), "cel_termin": ("training", "nutrition"),
    "urazy_deklaracja": ("training",), "urazy": ("training",), "ograniczenia_ruchu": ("training",),
    "bol_biezacy": ("training",), "bol_opis": ("training",),
    "gw_lekarz_ograniczenie": ("training",), "gw_lekarz_ograniczenie_opis": ("training",),
    "gw_przesiew_objawy": ("training",),
    "alergie": ("nutrition",), "alergie_status": ("nutrition",), "nietolerancje": ("nutrition",),
    "dostepnosc_tygodniowa": ("training",), "dni_treningowe": ("training",),
    "sprzet": ("training",), "sprzet_domowy": ("training",),
}

_ETYKIETY_FAKTOW = {
    "cel_glowny": "cel", "cel_termin": "cel (termin)", "urazy_deklaracja": "ograniczenia",
    "urazy": "ograniczenia", "ograniczenia_ruchu": "ograniczenia", "bol_biezacy": "ograniczenia",
    "bol_opis": "ograniczenia", "gw_lekarz_ograniczenie": "ograniczenia",
    "gw_lekarz_ograniczenie_opis": "ograniczenia", "gw_przesiew_objawy": "ograniczenia",
    "alergie": "alergie", "alergie_status": "alergie", "nietolerancje": "alergie",
    "dostepnosc_tygodniowa": "dostępność", "dni_treningowe": "dostępność",
    "sprzet": "sprzęt", "sprzet_domowy": "sprzęt",
}


def fakt_biezacy(db: Session, client_id: str, fact_key: str) -> ClientFactRevision | None:
    return (
        db.query(ClientFactRevision)
        .filter_by(client_id=client_id, fact_key=fact_key, is_current=True).one_or_none()
    )


def fakty_biezace(db: Session, client_id: str) -> dict[str, ClientFactRevision]:
    rows = db.query(ClientFactRevision).filter_by(client_id=client_id, is_current=True).all()
    return {r.fact_key: r for r in rows}


def _zapisz_fakty(db: Session, *, client_id: str, defn: D.Definicja, answers: dict[str, dict],
                  aktywne_ids: set[str], source_type: str, source_id: str,
                  domyslny_autor: str) -> list[str]:
    """Rewizje faktów dla odpowiedzi aktywnych zasilających klucze; zwraca
    zmienione klucze. Pominięcie nie nadpisuje faktu (brak informacji ≠
    informacja)."""
    zmienione: list[str] = []
    for q in defn.questions:
        if q.fact_key is None or q.question_id not in aktywne_ids or q.informacyjne:
            continue
        a = answers.get(q.question_id)
        if not isinstance(a, dict) or a.get("skipped") or not (a.get("value") or "").strip():
            continue
        value = a["value"]
        current = fakt_biezacy(db, client_id, q.fact_key)
        if current is not None and current.value == value:
            continue
        version = 1
        if current is not None:
            current.is_current = False
            version = current.version + 1
        db.add(ClientFactRevision(
            id=new_id("CFR"), client_id=client_id, fact_key=q.fact_key, value=value,
            source_type=source_type, source_id=source_id, question_id=q.question_id,
            author_id=a.get("entered_by") or domyslny_autor, version=version,
            sensitive=q.sensitive,
        ))
        zmienione.append(q.fact_key)
    return zmienione


def _zadania_sprawdzenia(db: Session, *, client_id: str, coach_id: str | None,
                         submission: InterviewSubmission, zmienione: list[str],
                         pierwsza_wersja: bool) -> list[PlanReviewTask]:
    """Zmiana faktu istotnego dla planu → jedno otwarte zadanie na aktywny
    plan danego rodzaju (bez duplikatów: istniejące OPEN dostaje dopisane
    fakty). Pierwsza wersja nie tworzy zadań (nie ma „zmiany”)."""
    if coach_id is None or pierwsza_wersja:
        return []
    rodzaje: dict[str, set[str]] = {}
    for k in zmienione:
        for rodzaj in FAKTY_PLANU.get(k, ()):
            rodzaje.setdefault(rodzaj, set()).add(_ETYKIETY_FAKTOW.get(k, k))
    out: list[PlanReviewTask] = []
    for rodzaj, etykiety in rodzaje.items():
        Model = TrainingPlan if rodzaj == "training" else NutritionPlan
        plany = db.query(Model).filter_by(client_id=client_id, coach_id=coach_id, status="ACTIVE").all()
        for plan in plany:
            istn = (db.query(PlanReviewTask)
                    .filter_by(plan_kind=rodzaj, plan_id=plan.id, status="OPEN").one_or_none())
            if istn is not None:
                stare = set(json.loads(istn.changed_facts_json or "[]"))
                istn.changed_facts_json = json.dumps(sorted(stare | etykiety), ensure_ascii=False)
                istn.submission_id = submission.id
                out.append(istn)
                continue
            t = PlanReviewTask(
                id=new_id("PRT"), client_id=client_id, coach_id=coach_id, plan_kind=rodzaj,
                plan_id=plan.id, submission_id=submission.id,
                changed_facts_json=json.dumps(sorted(etykiety), ensure_ascii=False),
            )
            db.add(t)
            out.append(t)
    db.flush()
    return out


def _outbox(db: Session, *, event_type: str, aggregate_id: str, recipient_id: str,
            payload: dict) -> OutboxEvent | None:
    """Jedno zdarzenie na (typ, agregat, odbiorca) — UNIQUE w bazie;
    ponowienie tej samej operacji nie tworzy drugiego."""
    istn = (db.query(OutboxEvent)
            .filter_by(event_type=event_type, aggregate_id=aggregate_id, recipient_id=recipient_id)
            .one_or_none())
    if istn is not None:
        return None
    ev = OutboxEvent(id=new_id("OBX"), event_type=event_type, aggregate_id=aggregate_id,
                     recipient_id=recipient_id, payload_json=json.dumps(payload, ensure_ascii=False))
    db.add(ev)
    db.flush()
    return ev


def przeslij(db: Session, *, client_id: str, typ: str, actor: User, revision: int,
             allowed_domains: set[str], uslugi: set[str] | None = None) -> dict[str, Any]:
    """Przesłanie szkicu: walidacja wymaganych aktywnych → nowa wersja
    (niezmienna) → rewizje faktów → zadania sprawdzenia planu → outbox dla
    trenera → zamknięcie otwartych doprecyzowań → audyt. Jedna transakcja
    (commit należy do routera)."""
    defn = D.definicja(typ)
    d = szkic(db, client_id, typ)
    if d is None:
        raise BladWalidacji({}, ["brak szkicu"])
    if revision != d.revision:
        raise KonfliktRewizji(d.revision)
    answers = odpowiedzi_szkicu(d)
    braki = D.braki(defn, answers, allowed_domains, uslugi)
    if braki:
        raise BladWalidacji({q.question_id: "To pytanie jest wymagane." for q in braki},
                            [q.question_id for q in braki])
    akt = D.aktywne(defn, answers, allowed_domains)
    akt_ids = {q.question_id for q in akt}
    # Do wersji trafiają WYŁĄCZNIE odpowiedzi aktywne — nieaktywna gałąź
    # zostaje w szkicu (do potwierdzenia po ewentualnym powrocie).
    do_wersji = {qid: a for qid, a in answers.items() if qid in akt_ids}
    poprzednia = ostatnie_przeslanie(db, client_id, typ)
    coach_id = trener_klienta(db, client_id)
    flaga = _flaga_bezpieczenstwa(defn, do_wersji)
    sub = InterviewSubmission(
        id=new_id("IVS"), client_id=client_id, coach_id=coach_id, typ=typ,
        version_no=(poprzednia.version_no + 1) if poprzednia else 1,
        definition_version=defn.version, answers_json=json.dumps(do_wersji, ensure_ascii=False),
        progress_json=json.dumps(D.postep(defn, answers, allowed_domains, uslugi)),
        submitted_by=actor.id, collection_mode=d.collection_mode, safety_flag=flaga,
    )
    db.add(sub)
    db.flush()
    zmienione = _zapisz_fakty(db, client_id=client_id, defn=defn, answers=do_wersji,
                              aktywne_ids=akt_ids, source_type=f"wywiad_{typ}", source_id=sub.id,
                              domyslny_autor=actor.id)
    # Profil (jedno źródło danych profilu): te same klucze co dotąd.
    pola = [FieldWrite(field_key=q.fact_key, value=do_wersji[q.question_id]["value"],
                       sensitive=q.sensitive)
            for q in akt if q.fact_key and q.question_id in do_wersji
            and not do_wersji[q.question_id].get("skipped") and not q.informacyjne]
    if pola:
        apply_profile_fields(db, client_id=client_id, author_id=actor.id,
                             source=f"WYWIAD_{typ.upper()}", items=pola)
    zadania = _zadania_sprawdzenia(db, client_id=client_id, coach_id=coach_id, submission=sub,
                                   zmienione=zmienione, pierwsza_wersja=poprzednia is None)
    # Wywiad „zapotrzebowanie” (0.62.0): wynik liczony i zapisywany razem z wersją.
    from . import zapotrzebowanie_serwis
    zapotrzebowanie_serwis.przelicz_po_przeslaniu(db, submission=sub, answers=do_wersji)
    for cr in otwarte_doprecyzowania(db, client_id, typ):
        cr.status = "RESOLVED"
        cr.resolved_at = now_iso()
        cr.resolved_by_submission_id = sub.id
    d.dirty = False
    d.last_submission_id = sub.id
    d.revision += 1
    d.updated_at = now_iso()
    d.updated_by = actor.id
    ev = None
    if coach_id is not None:
        ev = _outbox(db, event_type="INTERVIEW_SUBMITTED", aggregate_id=sub.id, recipient_id=coach_id,
                     payload={"submission_id": sub.id, "client_id": client_id, "typ": typ,
                              "version_no": sub.version_no})
    record_event(
        db, action=f"INTERVIEW_{typ.upper()}_SUBMITTED", actor_id=actor.id, subject_ids=[client_id],
        # Bez treści odpowiedzi — wyłącznie metadane wersji.
        payload={"submission_id": sub.id, "version_no": sub.version_no, "typ": typ,
                 "definition_version": defn.version, "changed_facts": len(zmienione),
                 "review_tasks": [t.id for t in zadania], "collection_mode": d.collection_mode},
        summary=f"Przesłano wywiad {typ} v{sub.version_no}",
    )
    db.flush()
    return {"submission_id": sub.id, "version_no": sub.version_no, "changed_facts": zmienione,
            "review_tasks": [t.id for t in zadania], "outbox_event_id": ev.id if ev else None,
            "revision": d.revision, "safety_flag": flaga}


def _flaga_bezpieczenstwa(defn: D.Definicja, answers: dict[str, dict]) -> bool:
    for q in defn.questions:
        a = answers.get(q.question_id)
        if not isinstance(a, dict) or a.get("skipped"):
            continue
        v = a.get("value") or ""
        if q.flag_options and any(p.strip() in q.flag_options for p in v.split(",")):
            return True
        if q.scan_safety and scan_safety_signals(v):
            return True
    return False


# --- przegląd, doprecyzowania, przypomnienia --------------------------------------------


def przejrzyj(db: Session, *, sub: InterviewSubmission, coach: User, outcome: str,
              internal_note: str | None) -> InterviewReview:
    r = InterviewReview(id=new_id("IVR"), submission_id=sub.id, coach_id=coach.id,
                        outcome=outcome, internal_note=(internal_note or "").strip() or None)
    db.add(r)
    db.flush()
    if outcome == "REVIEWED":
        _outbox(db, event_type="INTERVIEW_REVIEWED", aggregate_id=sub.id, recipient_id=sub.client_id,
                payload={"submission_id": sub.id, "typ": sub.typ, "version_no": sub.version_no})
    record_event(
        db, action="INTERVIEW_REVIEWED", actor_id=coach.id, subject_ids=[sub.client_id],
        payload={"submission_id": sub.id, "typ": sub.typ, "version_no": sub.version_no,
                 "outcome": outcome, "has_internal_note": bool(r.internal_note)},
        summary=f"Przegląd wywiadu {sub.typ} v{sub.version_no}: {outcome}",
    )
    return r


def popros_o_doprecyzowanie(db: Session, *, sub: InterviewSubmission, coach: User,
                            question_ids: list[str], message: str) -> ClarificationRequest:
    defn = D.definicja(sub.typ)
    nieznane = [q for q in question_ids if q not in defn.by_id]
    if nieznane:
        raise BladWalidacji({q: "Nieznane pytanie." for q in nieznane})
    cr = ClarificationRequest(
        id=new_id("CLR"), client_id=sub.client_id, typ=sub.typ, submission_id=sub.id,
        coach_id=coach.id, question_ids_json=json.dumps(question_ids), message=message.strip(),
    )
    db.add(cr)
    # Przegląd tej wersji = „wymaga doprecyzowania” (bez notatki).
    db.add(InterviewReview(id=new_id("IVR"), submission_id=sub.id, coach_id=coach.id,
                           outcome="NEEDS_CLARIFICATION"))
    db.flush()
    _outbox(db, event_type="CLARIFICATION_REQUESTED", aggregate_id=cr.id, recipient_id=sub.client_id,
            payload={"clarification_id": cr.id, "typ": sub.typ, "submission_id": sub.id,
                     "questions": len(question_ids)})
    record_event(
        db, action="INTERVIEW_CLARIFICATION_REQUESTED", actor_id=coach.id, subject_ids=[sub.client_id],
        payload={"clarification_id": cr.id, "submission_id": sub.id, "typ": sub.typ,
                 "questions": len(question_ids)},
        summary=f"Prośba o doprecyzowanie wywiadu {sub.typ} v{sub.version_no}",
    )
    return cr


def przypomnij(db: Session, *, client_id: str, typ: str, coach: User,
               submission_status: str) -> OutboxEvent | None:
    """Jawna akcja trenera: „Poproś o wypełnienie” (not_started) albo
    „Przypomnij o dokończeniu” (draft). Jedno na dzień per (klient, typ)."""
    dzien = datetime.now(UTC).date().isoformat()
    ev = _outbox(db, event_type="INTERVIEW_REMINDER", aggregate_id=f"{client_id}:{typ}:{dzien}",
                 recipient_id=client_id,
                 payload={"typ": typ, "client_id": client_id, "submission_status": submission_status,
                          "coach_id": coach.id})
    record_event(
        db, action="INTERVIEW_REMINDER_SENT", actor_id=coach.id, subject_ids=[client_id],
        payload={"typ": typ, "submission_status": submission_status, "deduplicated": ev is None},
        summary=f"Prośba o wywiad {typ} ({submission_status})",
    )
    return ev


def rozstrzygnij_zadanie(db: Session, *, task: PlanReviewTask, coach: User, note: str | None) -> None:
    task.status = "RESOLVED"
    task.resolved_at = now_iso()
    task.resolved_by = coach.id
    task.resolution_note = (note or "").strip() or None
    record_event(
        db, action="PLAN_REVIEW_TASK_RESOLVED", actor_id=coach.id, subject_ids=[task.client_id],
        payload={"task_id": task.id, "plan_kind": task.plan_kind, "plan_id": task.plan_id},
        summary="Rozstrzygnięto zadanie sprawdzenia planu po zmianie wywiadu",
    )


def otwarte_zadania_planu(db: Session, plan_kind: str, plan_id: str) -> list[PlanReviewTask]:
    return (db.query(PlanReviewTask).filter_by(plan_kind=plan_kind, plan_id=plan_id, status="OPEN")
            .order_by(PlanReviewTask.created_at).all())


# --- doręczanie z outboxu ---------------------------------------------------------------

_TYP_NAZWA = {"wstepny": "wywiad wstępny", "gleboki": "wywiad głęboki",
              "zapotrzebowanie": "wywiad „Zapotrzebowanie kaloryczne”"}


def dorecz_zdarzenie(db: Session, ev: OutboxEvent, dane: dict) -> Notification | None:
    """Jedno zdarzenie outboxu wywiadu → jeden wpis centrum (dedup po
    kluczu). Treść bez odpowiedzi — sama informacja, co się stało."""
    nazwa = _TYP_NAZWA.get(dane.get("typ", ""), "wywiad")
    if ev.event_type == "INTERVIEW_SUBMITTED":
        klient = db.get(User, dane["client_id"])
        kto = klient.display_name if klient else "Klient"
        return notifications.notify_now(
            db, user_id=ev.recipient_id, category="WYWIAD",
            title=f"{kto}: {nazwa} do przejrzenia",
            body=f"Przesłano wersję {dane['version_no']}. Przejrzyj odpowiedzi i oznacz jako przejrzane "
                 "albo poproś o uzupełnienie.",
            url=f"/trener/klient/{dane['client_id']}?zakladka=wywiad",
            source=f"interview:{dane['submission_id']}", dedup_key=f"interview-submitted:{dane['submission_id']}",
        )
    if ev.event_type == "CLARIFICATION_REQUESTED":
        return notifications.notify_now(
            db, user_id=ev.recipient_id, category="WYWIAD",
            title="Trener prosi o uzupełnienie wywiadu",
            body=f"Trener poprosił o doprecyzowanie {dane.get('questions', 0)} odpowiedzi w: {nazwa}. "
                 "Otwórz Wywiad, uzupełnij i prześlij ponownie.",
            url=f"/wywiad?typ={dane.get('typ', 'wstepny')}",
            source=f"clarification:{dane['clarification_id']}",
            dedup_key=f"clarification:{dane['clarification_id']}",
        )
    if ev.event_type == "INTERVIEW_REVIEWED":
        return notifications.notify_now(
            db, user_id=ev.recipient_id, category="WYWIAD",
            title=f"Trener przejrzał Twój {nazwa}",
            body=f"Wersja {dane['version_no']} została oznaczona jako przejrzana. "
                 "To potwierdzenie, że trener zapoznał się z odpowiedziami — nie ocena.",
            url=f"/wywiad?typ={dane.get('typ', 'wstepny')}",
            source=f"interview:{dane['submission_id']}", dedup_key=f"interview-reviewed:{dane['submission_id']}",
        )
    if ev.event_type == "INTERVIEW_REMINDER":
        start = dane.get("submission_status") == "not_started"
        return notifications.notify_now(
            db, user_id=ev.recipient_id, category="WYWIAD",
            title=("Trener prosi o wypełnienie: " if start else "Trener przypomina o dokończeniu: ") + nazwa,
            body="Otwórz zakładkę Wywiad w aplikacji. Możesz zapisać część i wrócić później.",
            url=f"/wywiad?typ={dane.get('typ', 'wstepny')}",
            source=f"interview-reminder:{ev.aggregate_id}", dedup_key=f"interview-reminder:{ev.aggregate_id}",
        )
    raise ValueError(f"nieznany typ zdarzenia: {ev.event_type}")


# --- stany i serializacja -------------------------------------------------------------


def stany(db: Session, *, client_id: str, typ: str, allowed_domains: set[str],
          uslugi: set[str] | None = None) -> dict[str, Any]:
    """Trzy ROZDZIELONE statusy + postęp. Wyliczane, nie przechowywane."""
    defn = D.definicja(typ)
    d = szkic(db, client_id, typ)
    ostatnia = ostatnie_przeslanie(db, client_id, typ)
    answers = odpowiedzi_szkicu(d)
    if ostatnia is None and d is None:
        submission_status = "not_started"
    elif ostatnia is None or (d is not None and d.dirty):
        submission_status = "draft"
    else:
        submission_status = "submitted"
    review_status = "not_reviewed"
    przeglad = przeglad_wersji(db, ostatnia.id) if ostatnia else None
    if przeglad is not None:
        review_status = "reviewed" if przeglad.outcome == "REVIEWED" else "needs_clarification"
    otwarte = otwarte_doprecyzowania(db, client_id, typ)
    freshness = "update_requested" if otwarte else "current"
    if otwarte:
        review_status = "needs_clarification"
    return {
        "typ": typ, "title": defn.title, "definition_version": defn.version,
        "submission_status": submission_status, "review_status": review_status,
        "freshness_status": freshness,
        "progress": D.postep(defn, answers, allowed_domains, uslugi),
        "draft": {"revision": d.revision, "updated_at": d.updated_at, "updated_by": d.updated_by,
                  "collection_mode": d.collection_mode, "dirty": d.dirty} if d else None,
        "last_submission": _przeslanie_meta(db, ostatnia) if ostatnia else None,
        "submissions_count": db.query(InterviewSubmission).filter_by(client_id=client_id, typ=typ).count(),
        "open_clarifications": [doprecyzowanie_out(c) for c in otwarte],
    }


def _przeslanie_meta(db: Session, s: InterviewSubmission) -> dict[str, Any]:
    r = przeglad_wersji(db, s.id)
    return {
        "id": s.id, "version_no": s.version_no, "definition_version": s.definition_version,
        "submitted_at": s.submitted_at, "submitted_by": s.submitted_by,
        "collection_mode": s.collection_mode, "migrated": s.migrated, "safety_flag": s.safety_flag,
        "progress": json.loads(s.progress_json or "{}"),
        "review": {"outcome": r.outcome, "created_at": r.created_at, "migrated": r.migrated} if r else None,
    }


def doprecyzowanie_out(c: ClarificationRequest) -> dict[str, Any]:
    return {"id": c.id, "typ": c.typ, "submission_id": c.submission_id,
            "question_ids": json.loads(c.question_ids_json or "[]"), "message": c.message,
            "status": c.status, "created_at": c.created_at, "resolved_at": c.resolved_at}


def odpowiedzi_out(defn: D.Definicja, answers: dict[str, dict], widoczne: set[str],
                   *, allowed_domains: set[str]) -> list[dict[str, Any]]:
    """Odpowiedzi do API: wrażliwe spoza widocznych domen są ukryte
    (`hidden: true`, bez wartości). Nieaktywna gałąź oznaczona `active: false`."""
    akt = {q.question_id for q in D.aktywne(defn, answers, allowed_domains)}
    out = []
    for q in defn.questions:
        a = answers.get(q.question_id)
        if not isinstance(a, dict):
            continue
        hidden = q.consent_domain is not None and q.consent_domain not in widoczne
        out.append({
            "question_id": q.question_id, "label": q.label, "section": q.section,
            "value": None if hidden else a.get("value", ""), "skipped": bool(a.get("skipped")),
            "entered_by": a.get("entered_by"), "at": a.get("at"), "hidden": hidden,
            "active": q.question_id in akt, "fact_key": q.fact_key, "sensitive": q.sensitive,
            "to_discuss": (a.get("value") in D.ODP_DO_OMOWIENIA) if not hidden else False,
        })
    return out


def przeslanie_out(db: Session, s: InterviewSubmission, *, widoczne: set[str],
                   pokaz_notatki: bool) -> dict[str, Any]:
    defn = D.definicja(s.typ)
    answers = json.loads(s.answers_json or "{}")
    meta = _przeslanie_meta(db, s)
    reviews = (db.query(InterviewReview).filter_by(submission_id=s.id)
               .order_by(InterviewReview.created_at).all())
    meta["answers"] = odpowiedzi_out(defn, answers, widoczne,
                                     allowed_domains={DOMAIN_HEALTH, DOMAIN_NUTRITION})
    meta["reviews"] = [{"id": r.id, "outcome": r.outcome, "created_at": r.created_at,
                        "coach_id": r.coach_id, "migrated": r.migrated,
                        **({"internal_note": r.internal_note} if pokaz_notatki else {})}
                       for r in reviews]
    meta["clarifications"] = [doprecyzowanie_out(c) for c in
                              db.query(ClarificationRequest).filter_by(submission_id=s.id)
                              .order_by(ClarificationRequest.created_at).all()]
    return meta


def zadanie_out(t: PlanReviewTask) -> dict[str, Any]:
    return {"id": t.id, "client_id": t.client_id, "plan_kind": t.plan_kind, "plan_id": t.plan_id,
            "submission_id": t.submission_id, "changed_facts": json.loads(t.changed_facts_json or "[]"),
            "status": t.status, "created_at": t.created_at, "resolved_at": t.resolved_at,
            "resolution_note": t.resolution_note}

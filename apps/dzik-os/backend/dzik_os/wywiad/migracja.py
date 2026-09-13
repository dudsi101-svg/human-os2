"""Ponawialna migracja sesji rozmowy startowej (flow=start → wywiad
wstępny) i głębokiego wywiadu (flow=deep → wywiad głęboki) do wersji
formularzy zakładki „Wywiad”.

Zasady (specyfikacja właściciela):
* nic nie jest usuwane ani nadpisywane — stare tabele zostają;
* sesje zatwierdzone (CLIENT_APPROVED / COACH_APPROVED) → NIEZMIENNA
  wersja historyczna oznaczona `migrated`; przegląd trenera powstaje
  WYŁĄCZNIE, gdy trener faktycznie zatwierdził (`coach_approved_by`),
  inaczej `not_reviewed` — bez udawanego przeglądu;
* sesje otwarte (IN_PROGRESS / SUMMARY_READY) i porzucone (ABANDONED)
  → szkic z zachowanymi odpowiedziami (najnowsza sesja; starsze
  wymienione w raporcie jako duplikaty);
* klienci bez odpowiedzi nie dostają nic (oba formularze `not_started`
  wyliczają się z braku wierszy);
* autorstwo (klient), daty (`created_at` odpowiedzi, `client_approved_at`)
  i identyfikatory źródłowe (`source_session_id`) są zachowane;
* powiązania niejednoznaczne (sesja klienta bez aktywnej relacji
  z trenerem, konto nieaktywne) trafiają do listy „do ręcznej
  weryfikacji” — bez treści odpowiedzi;
* ponowne uruchomienie niczego nie dubluje (`source_session_id`,
  UNIQUE (client_id, typ)); raport ma liczby przed i po;
* migracja NIE wysyła powiadomień, nie tworzy zdarzeń outboxu i nie
  zapisuje treści odpowiedzi w logach.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from ..authz import DOMAIN_HEALTH, DOMAIN_NUTRITION
from ..models import (
    ClientFactRevision,
    CoachClientRelationship,
    InterviewDraft,
    InterviewReview,
    InterviewSubmission,
    OnboardingAnswer,
    OnboardingSession,
    User,
    new_id,
)
from . import definicje as D
from . import serwis

_FLOW_TYP = {"start": D.WSTEPNY, "deep": D.GLEBOKI}
_ZATWIERDZONE = ("CLIENT_APPROVED", "COACH_APPROVED")
_OTWARTE = ("IN_PROGRESS", "SUMMARY_READY")


def _odpowiedzi_sesji(db: Session, session: OnboardingSession) -> dict[str, dict]:
    rows = (db.query(OnboardingAnswer)
            .filter(OnboardingAnswer.session_id == session.id, OnboardingAnswer.is_current.is_(True))
            .order_by(OnboardingAnswer.created_at).all())
    return {r.step_id: {"value": "" if r.skipped else r.value, "skipped": bool(r.skipped),
                        "entered_by": session.client_id, "at": r.created_at}
            for r in rows}


def liczby(db: Session) -> dict[str, Any]:
    """Liczby kontrolne (bez treści odpowiedzi)."""
    sesje = db.query(OnboardingSession).all()
    per = Counter((s.flow, s.status) for s in sesje)
    return {
        "klienci": db.query(User).count(),
        "sesje": len(sesje),
        "sesje_wg_typu_i_statusu": {f"{f}:{st}": n for (f, st), n in sorted(per.items())},
        "odpowiedzi_biezace": db.query(OnboardingAnswer).filter(OnboardingAnswer.is_current.is_(True)).count(),
        "wersje_wywiadu": db.query(InterviewSubmission).count(),
        "wersje_migrowane": db.query(InterviewSubmission).filter(InterviewSubmission.migrated.is_(True)).count(),
        "szkice": db.query(InterviewDraft).count(),
        "szkice_migrowane": db.query(InterviewDraft).filter(InterviewDraft.collection_mode == "MIGRACJA").count(),
        "przeglady_migrowane": db.query(InterviewReview).filter(InterviewReview.migrated.is_(True)).count(),
        "fakty": db.query(ClientFactRevision).count(),
    }


def migruj(db: Session, *, wykonaj: bool = True) -> dict[str, Any]:
    """Wykonuje (albo tylko symuluje przy `wykonaj=False`) migrację.
    Zwraca raport: liczby przed/po, utworzone obiekty, pominięte (już
    zmigrowane), lista do ręcznej weryfikacji (identyfikatory, bez treści)."""
    przed = liczby(db)
    raport: dict[str, Any] = {
        "przed": przed, "utworzone": {"wersje": 0, "przeglady": 0, "szkice": 0, "fakty": 0},
        "pominiete_juz_zmigrowane": 0, "sesje_bez_odpowiedzi": 0,
        "do_recznej_weryfikacji": [], "duplikaty_sesji": [], "wysylki": 0,
    }
    istniejace_zrodla = {s.source_session_id for s in db.query(InterviewSubmission.source_session_id).all()
                         if s.source_session_id}
    istniejace_szkice = {(d.client_id, d.typ) for d in db.query(InterviewDraft.client_id, InterviewDraft.typ).all()}
    grupy: dict[tuple[str, str], list[OnboardingSession]] = defaultdict(list)
    for s in db.query(OnboardingSession).order_by(OnboardingSession.started_at, OnboardingSession.id).all():
        typ = _FLOW_TYP.get(s.flow)
        if typ is None:
            raport["do_recznej_weryfikacji"].append({"session_id": s.id, "client_id": s.client_id,
                                                    "powod": f"nieznany przepływ {s.flow!r}"})
            continue
        grupy[(s.client_id, typ)].append(s)
    aktywne_relacje = {r.client_id for r in db.query(CoachClientRelationship.client_id)
                       .filter(CoachClientRelationship.status == "ACTIVE").all()}
    domeny = {DOMAIN_HEALTH, DOMAIN_NUTRITION}

    for (client_id, typ), sesje in grupy.items():
        klient = db.get(User, client_id)
        if klient is None:
            raport["do_recznej_weryfikacji"].append({"client_id": client_id, "powod": "brak konta klienta",
                                                    "sesje": [s.id for s in sesje]})
            continue
        if client_id not in aktywne_relacje:
            raport["do_recznej_weryfikacji"].append({"client_id": client_id, "typ": typ,
                                                    "powod": "brak aktywnej relacji trener–klient",
                                                    "sesje": [s.id for s in sesje]})
        defn = D.definicja(typ)
        zatwierdzone = [s for s in sesje if s.status in _ZATWIERDZONE]
        nr = (db.query(InterviewSubmission).filter_by(client_id=client_id, typ=typ).count())
        for s in zatwierdzone:
            if s.id in istniejace_zrodla:
                raport["pominiete_juz_zmigrowane"] += 1
                continue
            answers = _odpowiedzi_sesji(db, s)
            if not any(not a["skipped"] and a["value"] for a in answers.values()):
                raport["sesje_bez_odpowiedzi"] += 1
                continue
            nr += 1
            coach_id = s.coach_approved_by or serwis.trener_klienta(db, client_id)
            sub = InterviewSubmission(
                id=new_id("IVS"), client_id=client_id, coach_id=coach_id, typ=typ, version_no=nr,
                definition_version=defn.version, answers_json=json.dumps(answers, ensure_ascii=False),
                progress_json=json.dumps(D.postep(defn, answers, domeny)),
                submitted_by=client_id, submitted_at=s.client_approved_at or s.updated_at,
                collection_mode="MIGRACJA", migrated=True, source_session_id=s.id,
                safety_flag=bool(s.safety_flag),
            )
            db.add(sub)
            db.flush()
            raport["utworzone"]["wersje"] += 1
            if s.status == "COACH_APPROVED" and s.coach_approved_by:
                db.add(InterviewReview(id=new_id("IVR"), submission_id=sub.id, coach_id=s.coach_approved_by,
                                       outcome="REVIEWED", migrated=True,
                                       created_at=s.coach_approved_at or s.updated_at))
                raport["utworzone"]["przeglady"] += 1
            akt = {q.question_id for q in D.aktywne(defn, answers, domeny)}
            zm = serwis._zapisz_fakty(db, client_id=client_id, defn=defn, answers=answers, aktywne_ids=akt,
                                      source_type="migracja", source_id=sub.id, domyslny_autor=client_id)
            raport["utworzone"]["fakty"] += len(zm)
        otwarte = [s for s in sesje if s.status in _OTWARTE] or [s for s in sesje if s.status == "ABANDONED"]
        if otwarte:
            if len(otwarte) > 1:
                raport["duplikaty_sesji"].append({"client_id": client_id, "typ": typ,
                                                  "sesje": [s.id for s in otwarte]})
            s = otwarte[-1]
            if (client_id, typ) in istniejace_szkice or s.id in istniejace_zrodla:
                raport["pominiete_juz_zmigrowane"] += 1
                continue
            answers = _odpowiedzi_sesji(db, s)
            if not answers:
                raport["sesje_bez_odpowiedzi"] += 1
                continue
            ostatnia = serwis.ostatnie_przeslanie(db, client_id, typ)
            db.add(InterviewDraft(
                id=new_id("IVD"), client_id=client_id, typ=typ, definition_version=defn.version,
                answers_json=json.dumps(answers, ensure_ascii=False), revision=1, dirty=True,
                collection_mode="MIGRACJA", created_by=client_id, updated_by=client_id,
                created_at=s.started_at, updated_at=s.updated_at,
                last_submission_id=ostatnia.id if ostatnia else None, source_session_id=s.id,
            ))
            istniejace_szkice.add((client_id, typ))
            raport["utworzone"]["szkice"] += 1
    db.flush()
    raport["po"] = liczby(db)
    if not wykonaj:
        db.rollback()
        raport["tryb"] = "raport (bez zapisu)"
    else:
        raport["tryb"] = "wykonano"
    return raport

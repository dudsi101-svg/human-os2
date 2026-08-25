"""Konwersacyjne rozmowy z klientem — rozmowa startowa i głęboki wywiad.

Ścieżka domyślna jest DETERMINISTYCZNA: scenariusz, kolejność pytań,
reguły adaptacji i lista objawów alarmowych żyją w `onboarding_flow`
(rozmowa startowa) oraz `interview_flow` (głęboki wywiad) i działają
identycznie z modelem językowym i bez niego. Model (jeśli operator
skonfigurował dostawcę, a klient wyraził zgodę `funkcje_ai`) może
WYŁĄCZNIE przygotować wersję roboczą podsumowania rozmowy startowej —
nie prowadzi rozmowy, nie decyduje, nie publikuje planu ani diety.
Podsumowanie głębokiego wywiadu jest ZAWSZE deterministyczne.

Oba przepływy dzielą jeden mechanizm (`build_router` + wspólne tabele
rozróżniane kolumną `flow`, migracja 26) i dwie odrębne akceptacje
(Konstytucja Human OS, granice roli AI):

1. **klient** zatwierdza podsumowanie swoich danych — dopiero wtedy
   trafiają one do profilu normalną, wersjonowaną ścieżką
   (`profile_service.apply_profile_fields`); rozmowa startowa dodatkowo
   zakłada cel (`Goal`), wywiad celu nie tworzy;
2. **trener** zatwierdza podsumowanie jako podstawę planu, widząc dane
   źródłowe, pola do potwierdzenia i poziom niepewności per pole.

Kontrakt danych, prompty i plan wycofania migracji 17:
`docs/ONBOARDING_AI.md`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import onboarding_ai
from ..authz import (
    DOMAIN_COLLABORATION,
    DOMAIN_HEALTH,
    DOMAIN_NUTRITION,
    active_relationship,
    ai_features_consent_active,
    coach_can_access_client,
    deny,
    resolve_client_access,
)
from ..db import get_db
from ..hos_bridge import record_event
from ..models import (
    CoachClientRelationship,
    Goal,
    OnboardingAnswer,
    OnboardingSession,
    OnboardingSummaryItem,
    User,
    new_id,
    now_iso,
)
from ..observability import metrics
from ..onboarding_ai import AnswerForAI
from ..onboarding_flow import (
    SAFETY_MESSAGE,
    STEP_BY_ID,
    Step,
    next_step_id,
    plan_steps,
    previous_step_id,
    progress,
    scan_safety_signals,
    step_payload,
    validate_answer,
)
from ..profile_service import FieldWrite, apply_profile_fields
from ..schemas import (
    OnboardingAnswerIn,
    OnboardingCoachApproveIn,
    OnboardingSummaryIn,
)
from ..security import active_roles, current_user

# Statusy, w których rozmowa jest jeszcze „żywa" (można wznowić i poprawiać).
OPEN_STATUSES = ("IN_PROGRESS", "SUMMARY_READY", "CLIENT_APPROVED")

NO_AI_CONSENT_REASON = (
    "Nie wyraziłeś(-aś) zgody na funkcje AI, więc nic z tej rozmowy nie "
    "jest wysyłane do dostawcy modelu. Podsumowanie przygotujemy krok po "
    "kroku — jest tak samo pełne. Zgodę możesz włączyć w Profilu → "
    "Prywatność i zgody."
)


@dataclass(frozen=True)
class FlowConfig:
    """Parametry scenariusza — wszystko, czym różnią się oba przepływy.

    Mechanizm (stan, wersjonowanie, zgody, akceptacje) jest wspólny;
    konfiguracja wskazuje wyłącznie: który scenariusz, pod jaką ścieżką,
    z jakimi nazwami zdarzeń audytu, czy tworzy cel i czy w ogóle wolno
    mu rozmawiać z dostawcą modelu."""

    flow: str
    path_prefix: str
    # Trzy formy nazwy przepływu do napisów audytu (polska odmiana):
    # biernik („Rozpoczęto …”), mianownik („… : odpowiedź skierowana …”),
    # dopełniacz („podsumowanie …”).
    label_acc: str
    label_nom: str
    label_gen: str
    steps_by_id: dict[str, Step]
    plan: Callable[[dict, set], list[str]]
    event_prefix: str
    goal_on_approve: bool
    ai_enabled: bool
    ai_disabled_reason: str | None = None
    # Komunikat flagi dla kroków wyboru (Step.flag_options); None = brak
    # takich kroków w scenariuszu.
    flag_message_for: Callable[[str], str] | None = None


# ---------------------------------------------------------------------------
# Zgody i dostęp (wspólne dla obu przepływów)
# ---------------------------------------------------------------------------


def _coach_id(db: Session, client_id: str) -> str | None:
    row = (
        db.query(CoachClientRelationship)
        .filter(
            CoachClientRelationship.client_id == client_id,
            CoachClientRelationship.status == "ACTIVE",
        )
        .first()
    )
    return row.coach_id if row else None


def allowed_domains(db: Session, client_id: str) -> set[str]:
    """Domeny danych wrażliwych, o które WOLNO w tej rozmowie pytać.

    Bez aktywnej zgody kategorii pytanie w ogóle nie powstaje — nie
    zbieramy danych, których nie wolno nam przechowywać (minimalizacja).
    Brak przypisanego trenera również oznacza brak takich pytań."""
    coach_id = _coach_id(db, client_id)
    if coach_id is None:
        return set()
    return {
        domain
        for domain in (DOMAIN_HEALTH, DOMAIN_NUTRITION)
        if coach_can_access_client(db, coach_id, client_id, action="write", domain=domain)
    }


def ai_consent_active(db: Session, client_id: str) -> bool:
    """Zgoda kategorii `funkcje_ai` — bramka KAŻDEJ wysyłki do dostawcy.
    Reguła mieszka w authz (jedno miejsce dla wszystkich funkcji AI)."""
    return ai_features_consent_active(db, client_id)


def _require_client_self(user: User, client_id: str, prefix: str) -> None:
    """Rozmowę prowadzi wyłącznie sam klient — trener nie odpowiada za
    niego (to jego dane i jego słowa)."""
    if user.id != client_id:
        deny(user.id, f"{prefix}:{client_id}")


def _require_coach(db: Session, user: User, client_id: str, prefix: str) -> None:
    if "COACH" not in active_roles(db, user.id):
        raise HTTPException(status_code=403, detail="Tylko dla trenera")
    if active_relationship(db, user.id, client_id) is None:
        deny(user.id, f"{prefix}:{client_id}")


def _visible_sensitive(db: Session, user: User, client_id: str) -> dict[str, bool]:
    """Czy oglądający (trener) może zobaczyć dane wrażliwe danej domeny.
    Klient widzi zawsze wszystko, co sam powiedział."""
    if user.id == client_id:
        return {DOMAIN_HEALTH: True, DOMAIN_NUTRITION: True}
    return {
        domain: coach_can_access_client(db, user.id, client_id, domain=domain)
        for domain in (DOMAIN_HEALTH, DOMAIN_NUTRITION)
    }


def _answers(db: Session, session_id: str, *, current_only: bool = True):
    query = db.query(OnboardingAnswer).filter(OnboardingAnswer.session_id == session_id)
    if current_only:
        query = query.filter(OnboardingAnswer.is_current.is_(True))
    return query.order_by(OnboardingAnswer.created_at, OnboardingAnswer.version).all()


def _answer_values(rows) -> dict[str, str | None]:
    """Mapa krok -> wartość. Pominięcie ma None (nie odsłania kroków
    warunkowych — pominięte pytanie nie „odpowiada" niczego)."""
    return {r.step_id: (None if r.skipped else r.value) for r in rows}


def _summary_items(db: Session, session_id: str):
    return (
        db.query(OnboardingSummaryItem)
        .filter(
            OnboardingSummaryItem.session_id == session_id,
            OnboardingSummaryItem.is_current.is_(True),
        )
        .order_by(OnboardingSummaryItem.created_at)
        .all()
    )


# ---------------------------------------------------------------------------
# Fabryka routera — jeden mechanizm, dwa scenariusze
# ---------------------------------------------------------------------------


def build_router(cfg: FlowConfig) -> APIRouter:
    router = APIRouter(
        prefix=f"/api/clients/{{client_id}}/{cfg.path_prefix}",
        tags=[cfg.path_prefix],
    )

    def _open_session(db: Session, client_id: str) -> OnboardingSession | None:
        return (
            db.query(OnboardingSession)
            .filter(
                OnboardingSession.client_id == client_id,
                OnboardingSession.flow == cfg.flow,
                OnboardingSession.status.in_(OPEN_STATUSES),
            )
            .order_by(OnboardingSession.started_at.desc())
            .first()
        )

    def _latest_session(db: Session, client_id: str) -> OnboardingSession | None:
        return (
            db.query(OnboardingSession)
            .filter(
                OnboardingSession.client_id == client_id,
                OnboardingSession.flow == cfg.flow,
            )
            .order_by(OnboardingSession.started_at.desc())
            .first()
        )

    def _step_domain(step: Step) -> str:
        return step.consent_domain or DOMAIN_HEALTH

    def _field_domain(step_id: str | None) -> str:
        step = cfg.steps_by_id.get(step_id or "")
        return _step_domain(step) if step else DOMAIN_HEALTH

    def _refresh_current_step(
        session: OnboardingSession, planned: list[str], answered: set[str]
    ) -> None:
        """Ustawia bieżący krok. Gdy dotychczasowy wypadł z planu (np. klient
        cofnął zgodę zdrowotną w trakcie rozmowy) — przechodzimy do pierwszego
        kroku bez reakcji, zamiast pokazywać pytanie, którego nie wolno zadać."""
        if session.current_step_id in planned and session.current_step_id not in answered:
            return
        session.current_step_id = next_step_id(planned, answered)

    def _ai_status(db: Session, client_id: str) -> dict:
        """Stan ścieżki z modelem — zawsze z POWODEM, nigdy jako błąd.

        Brak zgody i brak dostawcy to dwie różne informacje; w przepływie
        z wyłączonym AI powód jest stały i nie zależy od zgód (nic nie
        wychodzi, więc nie ma o co pytać)."""
        if not cfg.ai_enabled:
            return {"available": False, "reason": cfg.ai_disabled_reason, "consent": False}
        if not ai_consent_active(db, client_id):
            return {"available": False, "reason": NO_AI_CONSENT_REASON, "consent": False}
        available, reason = onboarding_ai.availability(db, client_id)
        return {"available": available, "reason": reason, "consent": True}

    def _answer_out(row: OnboardingAnswer, visible: dict[str, bool]) -> dict:
        allowed = (not row.sensitive) or visible.get(_field_domain(row.step_id), False)
        step = cfg.steps_by_id.get(row.step_id)
        return {
            "step_id": row.step_id,
            "topic": row.topic,
            "question": step.question if step else row.step_id,
            "value": row.value if allowed else "",
            "hidden": not allowed,
            "skipped": row.skipped,
            "sensitive": row.sensitive,
            "safety_flagged": row.safety_flagged,
            "safety_signals": json.loads(row.safety_signals) if row.safety_signals else [],
            "version": row.version,
            "is_current": row.is_current,
            "created_at": row.created_at,
        }

    def _item_out(row: OnboardingSummaryItem, visible: dict[str, bool]) -> dict:
        allowed = (not row.sensitive) or visible.get(_field_domain(row.step_id), False)
        return {
            "field_key": row.field_key,
            "value": row.value if allowed else "",
            "hidden": not allowed,
            "step_id": row.step_id,
            "origin": row.origin,
            "confidence": row.confidence,
            "needs_confirmation": row.needs_confirmation,
            "coach_confirmed": row.coach_confirmed,
            "sensitive": row.sensitive,
            "version": row.version,
        }

    def _state_payload(
        db: Session, user: User, session: OnboardingSession | None, client_id: str
    ):
        if session is None:
            return {
                "session": None,
                "step": None,
                "progress": {"answered": 0, "total": 0, "percent": 0},
                "ai": _ai_status(db, client_id),
            }
        rows = _answers(db, session.id)
        values = _answer_values(rows)
        answered = {r.step_id for r in rows}
        domains = allowed_domains(db, client_id)
        planned = cfg.plan(values, domains)
        visible = _visible_sensitive(db, user, client_id)
        step = cfg.steps_by_id.get(session.current_step_id or "")
        current_answer = next(
            (r for r in rows if r.step_id == session.current_step_id), None
        )
        items = _summary_items(db, session.id)
        return {
            "session": {
                "id": session.id,
                "status": session.status,
                "summary_mode": session.summary_mode,
                "summary_mode_reason": session.summary_mode_reason,
                "safety_flag": session.safety_flag,
                "started_at": session.started_at,
                "updated_at": session.updated_at,
                "summary_at": session.summary_at,
                "client_approved_at": session.client_approved_at,
                "coach_approved_at": session.coach_approved_at,
                # Podsumowanie jest nieaktualne, gdy po jego wygenerowaniu
                # klient jeszcze coś poprawił.
                "summary_stale": bool(
                    session.summary_at
                    and rows
                    and max(r.created_at for r in rows) > session.summary_at
                ),
            },
            "step": step_payload(step) if step else None,
            "current_answer": (
                {
                    "step_id": current_answer.step_id,
                    "value": current_answer.value,
                    "skipped": current_answer.skipped,
                }
                if current_answer
                else None
            ),
            "can_go_back": previous_step_id(planned, session.current_step_id) is not None,
            "finished": session.current_step_id is None,
            "progress": progress(planned, answered),
            "planned_steps": planned,
            "answers": [
                _answer_out(r, visible)
                for r in _answers(db, session.id, current_only=False)
            ],
            "summary": [_item_out(i, visible) for i in items],
            "ai": _ai_status(db, client_id),
        }

    # -----------------------------------------------------------------
    # Rozmowa
    # -----------------------------------------------------------------

    @router.get("")
    def get_state(
        client_id: str,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Stan rozmowy: bieżące pytanie, postęp, dane źródłowe i podsumowanie.
        Trener widzi to samo, ale dane wrażliwe wyłącznie w zakresie zgód."""
        resolve_client_access(db, user, client_id, domain=DOMAIN_COLLABORATION)
        session = _open_session(db, client_id) or _latest_session(db, client_id)
        return _state_payload(db, user, session, client_id)

    @router.post("/start", status_code=201)
    def start(
        client_id: str,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Rozpoczyna rozmowę albo wznawia przerwaną (bez gubienia odpowiedzi)."""
        resolve_client_access(
            db, user, client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        _require_client_self(user, client_id, cfg.path_prefix)
        session = _open_session(db, client_id)
        created = False
        if session is None:
            session = OnboardingSession(
                id=new_id("ONB"), client_id=client_id, flow=cfg.flow
            )
            db.add(session)
            db.flush()
            created = True
        rows = _answers(db, session.id)
        values = _answer_values(rows)
        planned = cfg.plan(values, allowed_domains(db, client_id))
        _refresh_current_step(session, planned, {r.step_id for r in rows})
        session.updated_at = now_iso()
        if created:
            record_event(
                db,
                action=f"{cfg.event_prefix}_STARTED",
                actor_id=user.id,
                subject_ids=[client_id],
                payload={"session_id": session.id, "steps_planned": len(planned)},
                summary=f"Rozpoczęto {cfg.label_acc}",
            )
        db.commit()
        return _state_payload(db, user, session, client_id)

    @router.post("/answer")
    def answer(
        client_id: str,
        body: OnboardingAnswerIn,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Zapisuje odpowiedź albo świadome pominięcie i podaje kolejny krok.

        Poprawka wcześniejszej odpowiedzi tworzy NOWĄ wersję — historia
        (także sprzeczna) zostaje. Odpowiedź z objawem alarmowym (słowa
        kluczowe) albo odpowiedzią flagową (kroki wyboru z przesiewu)
        dostaje spokojny komunikat i NIE jest wysyłana do dostawcy modelu."""
        resolve_client_access(
            db, user, client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        _require_client_self(user, client_id, cfg.path_prefix)
        session = _open_session(db, client_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Rozmowa nie została rozpoczęta")
        if session.status == "CLIENT_APPROVED":
            raise HTTPException(
                status_code=409,
                detail="Podsumowanie zostało już zatwierdzone. Zmiany wprowadź w "
                "Profilu albo poproś trenera o ponowne otwarcie rozmowy.",
            )
        step = cfg.steps_by_id.get(body.step_id)
        if step is None:
            raise HTTPException(status_code=422, detail="Nieznany krok rozmowy")
        rows = _answers(db, session.id)
        values = _answer_values(rows)
        domains = allowed_domains(db, client_id)
        planned = cfg.plan(values, domains)
        if body.step_id not in planned:
            # Krok spoza planu = pytanie, którego nie wolno zadać (brak zgody)
            # albo nieodsłonięte przez reguły adaptacji.
            raise HTTPException(
                status_code=422,
                detail="To pytanie nie jest w tej chwili częścią rozmowy.",
            )
        if body.skipped:
            value = ""
        else:
            try:
                value = validate_answer(step, body.value)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        signals = scan_safety_signals(value) if (value and step.scan_safety) else []
        # Flagi wyboru: przesiew bezpieczeństwa krokami CHOICE/BOOL/MULTI —
        # wybrana odpowiedź z listy flagowej działa jak objaw alarmowy
        # (flaga sesji + spokojny komunikat), tylko źródłem jest wybór,
        # nie słowo kluczowe.
        flag_message: str | None = None
        if value and step.flag_options:
            selected = [p.strip() for p in value.split(",")]
            flagged = [o for o in step.flag_options if o in selected]
            if flagged:
                signals = signals + flagged
                if cfg.flag_message_for is not None:
                    flag_message = cfg.flag_message_for(step.id)
        current = next((r for r in rows if r.step_id == body.step_id), None)
        version = 1
        if current is not None:
            current.is_current = False
            version = current.version + 1
        db.add(
            OnboardingAnswer(
                id=new_id("ONA"),
                session_id=session.id,
                step_id=step.id,
                topic=step.topic,
                value=value,
                skipped=body.skipped,
                sensitive=step.sensitive,
                safety_flagged=bool(signals),
                safety_signals=(
                    json.dumps(signals, ensure_ascii=False) if signals else None
                ),
                version=version,
            )
        )
        db.flush()
        if signals:
            metrics.inc("onboarding_safety_flags")
            if not session.safety_flag:
                session.safety_flag = True
                session.safety_flag_at = now_iso()
            record_event(
                db,
                action=f"{cfg.event_prefix}_SAFETY_FLAGGED",
                actor_id=user.id,
                subject_ids=[client_id],
                payload={
                    "session_id": session.id,
                    "step_id": step.id,
                    "signals": signals,
                },
                summary=f"{cfg.label_nom}: odpowiedź skierowana do "
                "konsultacji medycznej",
            )
        rows = _answers(db, session.id)
        values = _answer_values(rows)
        planned = cfg.plan(values, domains)
        _refresh_current_step(session, planned, {r.step_id for r in rows})
        if session.status == "SUMMARY_READY":
            # Zmiana odpowiedzi unieważnia gotowość podsumowania — trzeba je
            # przygotować ponownie (nigdy cicha rozbieżność danych).
            session.status = "IN_PROGRESS"
        session.updated_at = now_iso()
        db.commit()
        payload = _state_payload(db, user, session, client_id)
        payload["safety_notice"] = (
            {"message": flag_message or SAFETY_MESSAGE, "signals": signals}
            if signals
            else None
        )
        return payload

    @router.post("/back")
    def go_back(
        client_id: str,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Cofa rozmowę o jeden krok — odpowiedzi nie znikają, można je poprawić."""
        resolve_client_access(
            db, user, client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        _require_client_self(user, client_id, cfg.path_prefix)
        session = _open_session(db, client_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Rozmowa nie została rozpoczęta")
        rows = _answers(db, session.id)
        planned = cfg.plan(_answer_values(rows), allowed_domains(db, client_id))
        previous = previous_step_id(planned, session.current_step_id)
        if previous is None:
            raise HTTPException(status_code=409, detail="To jest pierwsze pytanie rozmowy")
        session.current_step_id = previous
        session.updated_at = now_iso()
        db.commit()
        return _state_payload(db, user, session, client_id)

    @router.post("/pause")
    def pause(
        client_id: str,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Przerwanie rozmowy. Stan jest już trwały — ten endpoint tylko
        potwierdza przerwanie i odnotowuje moment (wznowienie: /start)."""
        resolve_client_access(
            db, user, client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        _require_client_self(user, client_id, cfg.path_prefix)
        session = _open_session(db, client_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Rozmowa nie została rozpoczęta")
        session.updated_at = now_iso()
        db.commit()
        return {"ok": True, "resume_step_id": session.current_step_id}

    # -----------------------------------------------------------------
    # Podsumowanie
    # -----------------------------------------------------------------

    def _deterministic_items(rows) -> list[dict]:
        """Podsumowanie wprost z odpowiedzi klienta — bez modelu, bez skrótów.

        To jest PEŁNOPRAWNA ścieżka, nie wersja okrojona: każde pole ma
        wartość dokładnie taką, jaką podał klient, więc pewność jest wysoka
        i nic nie wymaga potwierdzania."""
        items: list[dict] = []
        for row in rows:
            if row.skipped or not row.value:
                continue
            step = cfg.steps_by_id.get(row.step_id)
            if step is None or step.profile_field is None:
                continue
            items.append(
                {
                    "field_key": step.profile_field,
                    "value": row.value,
                    "step_id": step.id,
                    "origin": "DETERMINISTIC",
                    "confidence": "HIGH",
                    "needs_confirmation": False,
                    "sensitive": step.sensitive,
                }
            )
        return items

    def _store_summary(
        db: Session, session: OnboardingSession, items: list[dict]
    ) -> None:
        """Zapisuje podsumowanie append-only (poprzednia wersja zostaje)."""
        existing = {i.field_key: i for i in _summary_items(db, session.id)}
        for item in items:
            previous = existing.pop(item["field_key"], None)
            version = 1
            if previous is not None:
                if (
                    previous.value == item["value"]
                    and previous.origin == item["origin"]
                    and previous.confidence == item["confidence"]
                ):
                    continue
                previous.is_current = False
                version = previous.version + 1
            db.add(
                OnboardingSummaryItem(
                    id=new_id("ONS"),
                    session_id=session.id,
                    field_key=item["field_key"],
                    value=item["value"],
                    step_id=item.get("step_id"),
                    origin=item["origin"],
                    confidence=item["confidence"],
                    needs_confirmation=item["needs_confirmation"],
                    sensitive=item["sensitive"],
                    version=version,
                )
            )
        # Pola, które zniknęły z odpowiedzi (np. po cofnięciu zgody) przestają
        # być bieżące — ale wiersz historyczny zostaje.
        for leftover in existing.values():
            leftover.is_current = False

    def _merge_ai_items(base: list[dict], ai_items) -> list[dict]:
        """Scala propozycję modelu z wersją deterministyczną.

        Model może wyłącznie ZASTĄPIĆ wartość pola, o które faktycznie pytano
        — nie może dodać pola ani usunąć istniejącego. Wrażliwość pola bierze
        się ze scenariusza, nigdy z odpowiedzi modelu."""
        by_key = {item["field_key"]: item for item in base}
        for proposal in ai_items:
            target = by_key.get(proposal.field_key)
            if target is None:
                continue
            target["value"] = proposal.value
            target["origin"] = "AI_DRAFT"
            target["confidence"] = proposal.confidence
            target["needs_confirmation"] = proposal.needs_confirmation
        return list(by_key.values())

    @router.post("/summary")
    def build_summary(
        client_id: str,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Buduje podsumowanie do zatwierdzenia przez klienta.

        Zawsze powstaje wersja deterministyczna. Ścieżka z modelem istnieje
        wyłącznie w rozmowie startowej (cfg.ai_enabled) i wymaga zgody
        `funkcje_ai`; odpowiedź modelu niezgodna ze schematem jest odrzucana
        (jedno ponowienie), a podsumowanie zostaje deterministyczne."""
        resolve_client_access(
            db, user, client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        _require_client_self(user, client_id, cfg.path_prefix)
        session = _open_session(db, client_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Rozmowa nie została rozpoczęta")
        rows = _answers(db, session.id)
        items = _deterministic_items(rows)
        if not items:
            raise HTTPException(
                status_code=422,
                detail="Nie ma jeszcze odpowiedzi, z których można zbudować "
                "podsumowanie — odpowiedz na przynajmniej jedno pytanie.",
            )
        mode = "FORM"
        reason: str | None = None

        if not cfg.ai_enabled:
            reason = cfg.ai_disabled_reason
        elif not ai_consent_active(db, client_id):
            reason = NO_AI_CONSENT_REASON
        else:
            # Do dostawcy jedzie WYŁĄCZNIE: krok + wartość, i tylko dla
            # odpowiedzi bez sygnału alarmowego (te są sprawą człowieka).
            for_ai = [
                AnswerForAI(step_id=r.step_id, value=r.value)
                for r in rows
                if not r.skipped and r.value and not r.safety_flagged
            ]
            result = onboarding_ai.request_summary_draft(
                db, user_id=client_id, answers=for_ai
            )
            if result.ok:
                mode = "AI_DRAFT"
                items = _merge_ai_items(items, result.items)
            else:
                reason = result.reason
                session.ai_rejections += result.rejected

        _store_summary(db, session, items)
        session.summary_mode = mode
        session.summary_mode_reason = reason
        session.summary_at = now_iso()
        session.updated_at = now_iso()
        if session.status == "IN_PROGRESS":
            session.status = "SUMMARY_READY"
        record_event(
            db,
            action=f"{cfg.event_prefix}_SUMMARY_BUILT",
            actor_id=user.id,
            subject_ids=[client_id],
            payload={"session_id": session.id, "mode": mode, "fields": len(items)},
            summary=f"Przygotowano podsumowanie {cfg.label_gen} (tryb {mode})",
        )
        db.commit()
        return _state_payload(db, user, session, client_id)

    @router.put("/summary")
    def edit_summary(
        client_id: str,
        body: OnboardingSummaryIn,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Poprawki klienta w podsumowaniu — poprawiona wartość dostaje
        `origin=CLIENT_EDITED` i najwyższą pewność (to słowa człowieka)."""
        resolve_client_access(
            db, user, client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        _require_client_self(user, client_id, cfg.path_prefix)
        session = _open_session(db, client_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Rozmowa nie została rozpoczęta")
        if session.status == "CLIENT_APPROVED":
            raise HTTPException(
                status_code=409, detail="Podsumowanie zostało już zatwierdzone."
            )
        existing = {i.field_key: i for i in _summary_items(db, session.id)}
        changed: list[str] = []
        for item in body.items:
            current = existing.get(item.field_key)
            if current is None:
                raise HTTPException(
                    status_code=422,
                    detail="Nie można dodać pola, którego nie ma w podsumowaniu.",
                )
            value = item.value.strip()
            if value == current.value:
                continue
            current.is_current = False
            db.add(
                OnboardingSummaryItem(
                    id=new_id("ONS"),
                    session_id=session.id,
                    field_key=current.field_key,
                    value=value,
                    step_id=current.step_id,
                    origin="CLIENT_EDITED",
                    confidence="HIGH",
                    needs_confirmation=False,
                    sensitive=current.sensitive,
                    version=current.version + 1,
                )
            )
            changed.append(current.field_key)
        session.updated_at = now_iso()
        db.commit()
        payload = _state_payload(db, user, session, client_id)
        payload["updated"] = changed
        return payload

    # -----------------------------------------------------------------
    # Zatwierdzenie: najpierw klient, potem trener
    # -----------------------------------------------------------------

    def _ensure_main_goal(
        db: Session, client_id: str, title: str, target: str
    ) -> str | None:
        """Cel główny z rozmowy — zakładany raz, normalną ścieżką (`Goal`).
        Istniejący aktywny cel główny nie jest nadpisywany."""
        if not title:
            return None
        existing = (
            db.query(Goal)
            .filter(
                Goal.client_id == client_id,
                Goal.kind == "MAIN",
                Goal.status == "ACTIVE",
            )
            .first()
        )
        if existing is not None:
            return existing.id
        goal = Goal(
            id=new_id("GOL"),
            client_id=client_id,
            title=title[:300],
            description=(
                f"Termin wskazany w rozmowie startowej: {target}" if target else None
            ),
            kind="MAIN",
            created_by=client_id,
        )
        db.add(goal)
        db.flush()
        return goal.id

    @router.post("/approve")
    def client_approve(
        client_id: str,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Klient zatwierdza podsumowanie — dopiero teraz dane trafiają do
        profilu (append-only, z proweniencją CLIENT_DECLARED); rozmowa
        startowa zakłada dodatkowo cel główny, wywiad celu nie tworzy.

        Pola wrażliwe, których zgoda w międzyczasie wygasła, NIE są zapisywane
        — wracają w odpowiedzi jako `skipped_fields` z jawnym powodem."""
        resolve_client_access(
            db, user, client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        _require_client_self(user, client_id, cfg.path_prefix)
        session = _open_session(db, client_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Rozmowa nie została rozpoczęta")
        if session.status == "CLIENT_APPROVED":
            raise HTTPException(
                status_code=409, detail="Podsumowanie zostało już zatwierdzone."
            )
        items = _summary_items(db, session.id)
        if not items:
            raise HTTPException(
                status_code=422, detail="Najpierw przygotuj podsumowanie rozmowy."
            )
        domains = allowed_domains(db, client_id)
        writes: list[FieldWrite] = []
        skipped: list[str] = []
        goal_title = ""
        goal_target = ""
        for item in items:
            if item.sensitive and _field_domain(item.step_id) not in domains:
                skipped.append(item.field_key)
                continue
            if item.field_key == "cel_glowny":
                goal_title = item.value
            if item.field_key == "cel_termin":
                goal_target = item.value
            writes.append(
                FieldWrite(
                    field_key=item.field_key,
                    value=item.value,
                    purpose="coaching",
                    sensitive=item.sensitive,
                )
            )
        changed = apply_profile_fields(
            db,
            client_id=client_id,
            author_id=user.id,
            source="CLIENT_DECLARED",
            items=writes,
        )
        goal_id = (
            _ensure_main_goal(db, client_id, goal_title, goal_target)
            if cfg.goal_on_approve
            else None
        )
        session.status = "CLIENT_APPROVED"
        session.client_approved_at = now_iso()
        session.applied_at = now_iso()
        session.updated_at = now_iso()
        record_event(
            db,
            action=f"{cfg.event_prefix}_CLIENT_APPROVED",
            actor_id=user.id,
            subject_ids=[client_id],
            payload={
                "session_id": session.id,
                "fields": changed,
                "skipped_fields": skipped,
                "summary_mode": session.summary_mode,
                "goal_id": goal_id,
            },
            summary=f"Klient zatwierdził podsumowanie {cfg.label_gen}",
        )
        db.commit()
        payload = _state_payload(db, user, session, client_id)
        payload["applied_fields"] = changed
        payload["skipped_fields"] = skipped
        payload["goal_id"] = goal_id
        return payload

    @router.get("/review")
    def coach_review(
        client_id: str,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Widok trenera: dane źródłowe (odpowiedzi klienta wraz z historią
        poprawek), podsumowanie, pola wymagające potwierdzenia i poziom
        niepewności per pole. Trener nie odpowiada za klienta — może wyłącznie
        czytać i zatwierdzać."""
        _require_coach(db, user, client_id, cfg.path_prefix)
        resolve_client_access(db, user, client_id, domain=DOMAIN_COLLABORATION)
        session = _open_session(db, client_id) or _latest_session(db, client_id)
        payload = _state_payload(db, user, session, client_id)
        summary = payload.get("summary") or []
        payload["needs_confirmation"] = [
            item["field_key"] for item in summary if item["needs_confirmation"]
        ]
        payload["can_approve"] = bool(
            session is not None
            and session.status in ("CLIENT_APPROVED", "COACH_APPROVED")
        )
        return payload

    @router.post("/coach-approve")
    def coach_approve(
        client_id: str,
        body: OnboardingCoachApproveIn,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ):
        """Trener zatwierdza podsumowanie jako podstawę planu.

        Wymaga wcześniejszego zatwierdzenia przez KLIENTA — kolejność nie jest
        zamienna (to dane klienta, a nie trenera). Model nie zatwierdza nic."""
        _require_coach(db, user, client_id, cfg.path_prefix)
        resolve_client_access(
            db, user, client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        session = _open_session(db, client_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Rozmowa nie została rozpoczęta")
        if session.status != "CLIENT_APPROVED":
            raise HTTPException(
                status_code=409,
                detail="Podsumowanie czeka jeszcze na zatwierdzenie przez klienta.",
            )
        confirmed = set(body.confirmed_fields)
        items = _summary_items(db, session.id)
        for item in items:
            if item.field_key in confirmed:
                item.coach_confirmed = True
        pending = [
            i.field_key for i in items if i.needs_confirmation and not i.coach_confirmed
        ]
        if pending:
            raise HTTPException(
                status_code=409,
                detail="Potwierdź z klientem pola oznaczone niepewnością: "
                + ", ".join(pending),
            )
        session.status = "COACH_APPROVED"
        session.coach_approved_at = now_iso()
        session.coach_approved_by = user.id
        session.updated_at = now_iso()
        record_event(
            db,
            action=f"{cfg.event_prefix}_COACH_APPROVED",
            actor_id=user.id,
            subject_ids=[client_id],
            payload={
                "session_id": session.id,
                "confirmed_fields": sorted(confirmed),
                "safety_flag": session.safety_flag,
            },
            summary=f"Trener zatwierdził podsumowanie {cfg.label_gen}",
        )
        db.commit()
        return _state_payload(db, user, session, client_id)

    return router


# ---------------------------------------------------------------------------
# Rozmowa startowa — konfiguracja domyślna (zachowanie sprzed fabryki)
# ---------------------------------------------------------------------------

START_CFG = FlowConfig(
    flow="start",
    path_prefix="onboarding",
    label_acc="rozmowę startową (onboarding)",
    label_nom="Rozmowa startowa",
    label_gen="rozmowy startowej",
    steps_by_id=STEP_BY_ID,
    plan=lambda answers, domains: plan_steps(answers, allowed_domains=domains),
    event_prefix="ONBOARDING",
    goal_on_approve=True,
    ai_enabled=True,
)

router = build_router(START_CFG)

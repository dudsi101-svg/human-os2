"""Wspólne wyzwania — moduł PRYWATNY (tylko-zaproszeni, zero publicznych).

Zasady (docs/WYZWANIA.md — model, prywatność, zgodność z konstytucją
Human OS):

* Konstytucja Human OS zakazuje rankingowania LUDZI i porównań między
  osobami jako mechanizmu domyślnego. Dlatego: ranking jest OPT-IN per
  uczestnik i DOMYŚLNIE WYŁĄCZONY; domyślny widok to własny postęp
  względem celu wyzwania + zagregowany postęp grupy bez nazwisk; wynik
  jednostkowy widzą inni wyłącznie po świadomej decyzji uczestnika
  (share_result); pseudonim (alias) per wyzwanie.
* Dane zdrowotne NIGDY nie wchodzą do wyzwań: jednostki wyniku są
  wyłącznie neutralne (NEUTRAL_UNITS — liczba treningów, minuty
  aktywności, odhaczenia); masa ciała, zdjęcia, ból, urazy, żywienie,
  raporty i szczegóły zdrowotne nie mają w tym module żadnej ścieżki.
* Wynik liczony wyłącznie z danych świadomie przeznaczonych do wyzwania:
  jawny wpis ręczny, jawne wskazanie własnego treningu, albo świadoma
  decyzja przy dołączaniu („zaliczaj moje odhaczone treningi").
* Uczciwe liczenie: idempotencja wpisów (client_entry_id, jeden trening
  raz), dzień wg STREFY WYZWANIA, korekty z historią (nigdy nadpisanie),
  oznaczanie danych ręcznych, limit wpisów/dzień, walidacja zakresów.
* Uczestnictwo dobrowolne (zaproszenie → przyjęcie/odrzucenie), wyjście
  i trwałe wycofanie udziału w każdej chwili; organizator moderuje
  wyłącznie wyzwania, które prowadzi; wszystko audytowane.
* Nic nie wychodzi poza zamkniętą grupę — publikowanie na zewnątrz NIE
  jest zaimplementowane (wymagałoby nowej kategorii zgody, patrz docs).
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import push_service
from ..authz import active_relationship, deny, require_client_self, require_owned_resource
from ..dates import local_today_iso, parse_iso_date
from ..db import get_db
from ..hos_bridge import record_event
from ..models import (
    Challenge,
    ChallengeBlock,
    ChallengeEntry,
    ChallengeParticipant,
    ChallengeReport,
    User,
    WorkoutSession,
    new_id,
    now_iso,
)
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["challenges"])

# Jedyne dozwolone jednostki wyniku — neutralne, bez danych zdrowotnych.
# fixed_value: wpis ma zawsze wartość 1 (zliczanie sztuk); max_value:
# górna granica pojedynczego wpisu (ochrona przed nadużyciami).
NEUTRAL_UNITS: dict[str, dict] = {
    "treningi": {"label": "ukończone treningi", "fixed_value": 1.0, "max_value": 1.0},
    "minuty": {"label": "minuty aktywności", "fixed_value": None, "max_value": 600.0},
    "aktywnosci": {"label": "aktywności (odhaczenia)", "fixed_value": 1.0, "max_value": 1.0},
}

# Neutralny alias nadawany przy moderacji niedozwolonej treści.
NEUTRAL_ALIAS = "Uczestnik"

# Czytelne wyjaśnienie widoczności — pokazywane PRZED dołączeniem i w
# szczegółach wyzwania (pkt 12 specyfikacji).
VISIBILITY_EXPLAINER = (
    "Kto zobaczy Twój wynik: domyślnie NIKT. Widzisz własny postęp i "
    "anonimowy, zagregowany postęp grupy (bez nazwisk). Jeśli włączysz "
    "„pokazuj mój wynik”, inni uczestnicy tego wyzwania zobaczą Twój "
    "pseudonim i łączny wynik. Ranking jest domyślnie WYŁĄCZONY i obejmuje "
    "wyłącznie osoby, które same świadomie go włączyły. Organizator widzi "
    "listę uczestników i postęp grupy; Twój wynik tylko, jeśli go "
    "udostępnisz. Dane zdrowotne (masa ciała, zdjęcia, ból, urazy, "
    "żywienie, raporty) nigdy nie trafiają do wyzwań. Nic nie wychodzi "
    "poza zamkniętą grupę wyzwania."
)


# ---------------------------------------------------------------------------
# Pomocnicze


def _unit_or_422(unit: str) -> dict:
    info = NEUTRAL_UNITS.get(unit)
    if info is None:
        raise HTTPException(
            status_code=422,
            detail="Niedozwolona jednostka wyniku — dozwolone są wyłącznie "
            "neutralne jednostki: " + ", ".join(sorted(NEUTRAL_UNITS))
            + ". Dane zdrowotne (np. masa ciała) nie wchodzą do wyzwań.",
        )
    return info


def _tz_or_422(tz_name: str) -> str:
    try:
        ZoneInfo(tz_name)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Nieznana strefa czasowa") from exc
    return tz_name


def _challenge_today(ch: Challenge) -> str:
    """Dzisiejsza data wg STREFY WYZWANIA (uczciwe naliczanie — pkt 8)."""

    class _TzCarrier:
        timezone = ch.timezone

    return local_today_iso(_TzCarrier())


def _participant(db: Session, challenge_id: str, user_id: str) -> ChallengeParticipant | None:
    return (
        db.query(ChallengeParticipant)
        .filter_by(challenge_id=challenge_id, user_id=user_id)
        .one_or_none()
    )


def _active_participants(db: Session, challenge_id: str) -> list[ChallengeParticipant]:
    return (
        db.query(ChallengeParticipant)
        .filter_by(challenge_id=challenge_id, status="ACTIVE")
        .all()
    )


def _auto_workout_count(db: Session, ch: Challenge, user_id: str) -> int:
    """Automatyczne zaliczanie odhaczonych treningów (świadomie włączone
    przy dołączaniu): liczba RÓŻNYCH dni z ukończonym treningiem w oknie
    wyzwania — dedup per dzień chroni przed podwójnym naliczaniem."""
    rows = (
        db.query(WorkoutSession.performed_on)
        .filter(
            WorkoutSession.client_id == user_id,
            WorkoutSession.status == "DONE",
            WorkoutSession.performed_on >= ch.starts_on,
            WorkoutSession.performed_on <= ch.ends_on,
        )
        .all()
    )
    return len({r[0] for r in rows})


def _progress_value(db: Session, ch: Challenge, part: ChallengeParticipant) -> tuple[float, bool]:
    """Łączny wynik uczestnika + flaga „zawiera dane ręczne"."""
    entries = (
        db.query(ChallengeEntry)
        .filter_by(challenge_id=ch.id, participant_id=part.id, status="ACTIVE")
        .all()
    )
    total = sum(e.value for e in entries)
    has_manual = any(e.source == "MANUAL" for e in entries)
    if part.auto_count_workouts and ch.unit == "treningi":
        total += _auto_workout_count(db, ch, part.user_id)
    return total, has_manual


def _progress_out(db: Session, ch: Challenge, part: ChallengeParticipant) -> dict:
    total, has_manual = _progress_value(db, ch, part)
    pct = None
    if ch.goal_value:
        pct = round(min(100.0, 100.0 * total / ch.goal_value), 1)
    return {"value": round(total, 1), "goal_value": ch.goal_value,
            "progress_pct": pct, "has_manual": has_manual}


def _blocked_pairs(db: Session, challenge_id: str, viewer_id: str) -> set[str]:
    """Identyfikatory użytkowników niewidocznych dla viewer_id (blokada
    działa w OBIE strony)."""
    rows = db.query(ChallengeBlock).filter_by(challenge_id=challenge_id).all()
    hidden: set[str] = set()
    for b in rows:
        if b.blocker_id == viewer_id:
            hidden.add(b.blocked_id)
        if b.blocked_id == viewer_id:
            hidden.add(b.blocker_id)
    return hidden


def _challenge_out(ch: Challenge) -> dict:
    unit_info = NEUTRAL_UNITS.get(ch.unit, {})
    return {
        "id": ch.id, "kind": ch.kind, "title": ch.title,
        "description": ch.description, "unit": ch.unit,
        "unit_label": unit_info.get("label", ch.unit),
        "goal_value": ch.goal_value, "starts_on": ch.starts_on,
        "ends_on": ch.ends_on, "timezone": ch.timezone,
        "visibility": ch.visibility, "status": ch.status,
        "max_entries_per_day": ch.max_entries_per_day,
        "aggregates_adjusted": ch.aggregates_adjusted,
        "is_past": _challenge_today(ch) > ch.ends_on,
    }


def _me_out(part: ChallengeParticipant) -> dict:
    return {
        "participant_id": part.id, "status": part.status, "alias": part.alias,
        "share_result": part.share_result, "ranking_opt_in": part.ranking_opt_in,
        "auto_count_workouts": part.auto_count_workouts,
    }


def _group_out(db: Session, ch: Challenge) -> dict:
    parts = _active_participants(db, ch.id)
    values = [_progress_value(db, ch, p)[0] for p in parts]
    completed = (
        sum(1 for v in values if ch.goal_value and v >= ch.goal_value)
        if ch.goal_value else None
    )
    avg_pct = None
    if ch.goal_value and values:
        avg_pct = round(
            sum(min(100.0, 100.0 * v / ch.goal_value) for v in values) / len(values), 1
        )
    return {
        "active_participants": len(parts),
        "total_value": round(sum(values), 1),
        "avg_progress_pct": avg_pct,
        "completed_count": completed,
        "aggregates_adjusted": ch.aggregates_adjusted,
    }


def _shared_and_ranking(
    db: Session, ch: Challenge, viewer_id: str
) -> tuple[list[dict], list[dict]]:
    """Wyniki jawne (share_result) i ranking (share_result + ranking_opt_in)
    — wyłącznie osoby, które świadomie się na to zdecydowały; pary
    zablokowane wzajemnie się nie widzą."""
    hidden = _blocked_pairs(db, ch.id, viewer_id)
    shared: list[dict] = []
    ranked: list[dict] = []
    for p in _active_participants(db, ch.id):
        if not p.share_result:
            continue
        if p.user_id in hidden and p.user_id != viewer_id:
            continue
        total, has_manual = _progress_value(db, ch, p)
        row = {
            "user_id": p.user_id, "alias": p.alias or NEUTRAL_ALIAS,
            "value": round(total, 1), "has_manual": has_manual,
            "is_me": p.user_id == viewer_id,
        }
        if ch.goal_value:
            row["progress_pct"] = round(min(100.0, 100.0 * total / ch.goal_value), 1)
        shared.append(row)
        if p.ranking_opt_in:
            ranked.append(dict(row))
    shared.sort(key=lambda r: r["alias"].lower())
    ranked.sort(key=lambda r: -r["value"])
    for i, row in enumerate(ranked, start=1):
        row["position"] = i
    return shared, ranked


def _require_organizer(db: Session, actor: User, challenge_id: str) -> Challenge:
    return require_owned_resource(
        db.get(Challenge, challenge_id), actor=actor,
        resource=f"challenge:{challenge_id}", owner_attr="organizer_id",
    )


def _audit(db: Session, action: str, actor_id: str, ch: Challenge,
           payload: dict, summary: str, subject_ids: list[str] | None = None) -> None:
    """Zdarzenia audytowe wyzwań: wyłącznie identyfikatory i liczniki —
    nigdy aliasy, notatki ani treści zgłoszeń."""
    record_event(
        db, action=action, actor_id=actor_id,
        subject_ids=subject_ids or [actor_id],
        payload={"challenge_id": ch.id, **payload}, summary=summary,
    )


# ---------------------------------------------------------------------------
# Wejścia


class ChallengeIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    unit: str
    goal_value: float | None = Field(default=None, gt=0, le=100000)
    starts_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    ends_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    timezone: str | None = None
    max_entries_per_day: int = Field(default=5, ge=1, le=20)


class InviteIn(BaseModel):
    client_ids: list[str] = Field(min_length=1, max_length=100)


class JoinIn(BaseModel):
    alias: str | None = Field(default=None, min_length=2, max_length=80)
    share_result: bool = False
    ranking_opt_in: bool = False
    auto_count_workouts: bool = False


class ParticipantSettingsIn(BaseModel):
    alias: str | None = Field(default=None, min_length=2, max_length=80)
    share_result: bool | None = None
    ranking_opt_in: bool | None = None
    auto_count_workouts: bool | None = None


class EntryIn(BaseModel):
    value: float | None = Field(default=None, gt=0)
    entry_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: str | None = Field(default=None, max_length=200)
    client_entry_id: str | None = Field(default=None, max_length=64)
    workout_session_id: str | None = None


class CorrectionIn(BaseModel):
    value: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=200)


class TargetUserIn(BaseModel):
    user_id: str


class ReportIn(BaseModel):
    user_id: str
    reason: str = Field(min_length=3, max_length=2000)


class ResolveIn(BaseModel):
    resolution: str = Field(pattern=r"^(REMOVED|ALIAS_RESET|NOTES_CLEARED|DISMISSED)$")
    note: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Tworzenie i cykl życia


def _validate_challenge_in(body: ChallengeIn) -> None:
    _unit_or_422(body.unit)
    parse_iso_date(body.starts_on)
    parse_iso_date(body.ends_on)
    if body.ends_on < body.starts_on:
        raise HTTPException(status_code=422, detail="Data końca przed datą startu")
    if body.timezone:
        _tz_or_422(body.timezone)


def _new_challenge(body: ChallengeIn, organizer: User, kind: str) -> Challenge:
    from ..config import settings

    return Challenge(
        id=new_id("CHL"), kind=kind, organizer_id=organizer.id,
        title=body.title.strip(), description=body.description,
        unit=body.unit, goal_value=body.goal_value,
        starts_on=body.starts_on, ends_on=body.ends_on,
        timezone=body.timezone or settings.timezone,
        max_entries_per_day=body.max_entries_per_day,
    )


@router.post("/coach/challenges", status_code=201)
def coach_create_challenge(
    body: ChallengeIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Wyzwanie grupowe prowadzone przez trenera (DRAFT → zaproszenia →
    aktywacja). Wyłącznie tylko-zaproszeni; publicznych wyzwań nie ma."""
    _validate_challenge_in(body)
    ch = _new_challenge(body, coach, kind="GROUP")
    db.add(ch)
    _audit(db, "CHALLENGE_CREATED", coach.id, ch,
           {"kind": ch.kind, "unit": ch.unit, "starts_on": ch.starts_on,
            "ends_on": ch.ends_on},
           f"Utworzono wyzwanie grupowe ({ch.unit})")
    db.commit()
    return _challenge_out(ch)


@router.post("/me/challenges", status_code=201)
def client_create_challenge(
    body: ChallengeIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Wyzwanie indywidualne („sam ze sobą") — od razu aktywne, bez
    zaproszeń; nikt poza właścicielem go nie widzi."""
    require_client_self(db, user)
    _validate_challenge_in(body)
    ch = _new_challenge(body, user, kind="INDIVIDUAL")
    ch.status = "ACTIVE"
    db.add(ch)
    part = ChallengeParticipant(
        id=new_id("CHP"), challenge_id=ch.id, user_id=user.id, status="ACTIVE",
        alias=user.display_name, joined_at=now_iso(),
    )
    db.add(part)
    _audit(db, "CHALLENGE_CREATED", user.id, ch,
           {"kind": ch.kind, "unit": ch.unit, "starts_on": ch.starts_on,
            "ends_on": ch.ends_on},
           f"Utworzono wyzwanie indywidualne ({ch.unit})")
    db.commit()
    return {**_challenge_out(ch), "me": _me_out(part)}


@router.post("/challenges/{challenge_id}/invite")
def invite_participants(
    challenge_id: str,
    body: InviteIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Zaproszenia — wyłącznie AKTYWNIE prowadzeni klienci organizatora
    (klienci tego samego trenera). Push jest neutralny (bez tytułu i
    jakichkolwiek danych)."""
    ch = _require_organizer(db, coach, challenge_id)
    if ch.kind != "GROUP" or ch.status in ("FINISHED", "CANCELLED"):
        raise HTTPException(status_code=422, detail="Do tego wyzwania nie można zapraszać")
    invited = []
    for client_id in dict.fromkeys(body.client_ids):
        if active_relationship(db, coach.id, client_id) is None:
            deny(coach.id, f"challenge_invite:{client_id}")
        if _participant(db, ch.id, client_id) is not None:
            continue
        part = ChallengeParticipant(
            id=new_id("CHP"), challenge_id=ch.id, user_id=client_id,
            status="INVITED", invited_by=coach.id, invited_at=now_iso(),
        )
        db.add(part)
        invited.append(client_id)
        push_service.send_to_user(
            db, client_id, "Nowe zaproszenie do wyzwania",
            "Masz zaproszenie do wspólnego wyzwania. Zdecyduj w aplikacji "
            "— udział jest zawsze dobrowolny.", "/wyzwania",
        )
    _audit(db, "CHALLENGE_INVITED", coach.id, ch,
           {"invited_count": len(invited)}, "Zaproszenia do wyzwania",
           subject_ids=invited or [coach.id])
    db.commit()
    return {"invited_count": len(invited)}


@router.post("/challenges/{challenge_id}/activate")
def activate_challenge(
    challenge_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    ch = _require_organizer(db, coach, challenge_id)
    if ch.status != "DRAFT":
        raise HTTPException(status_code=422, detail="Można aktywować tylko szkic")
    ch.status = "ACTIVE"
    ch.updated_at = now_iso()
    _audit(db, "CHALLENGE_ACTIVATED", coach.id, ch, {}, "Aktywacja wyzwania")
    db.commit()
    return _challenge_out(ch)


@router.post("/challenges/{challenge_id}/finish")
def finish_challenge(
    challenge_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Zakończenie wyzwania przez organizatora (trenera lub właściciela
    wyzwania indywidualnego). Po zakończeniu wpisy i korekty są zamrożone."""
    ch = _require_organizer(db, user, challenge_id)
    if ch.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Można zakończyć tylko aktywne wyzwanie")
    ch.status = "FINISHED"
    ch.finished_at = now_iso()
    ch.updated_at = now_iso()
    _audit(db, "CHALLENGE_FINISHED", user.id, ch, {}, "Zakończenie wyzwania")
    for p in _active_participants(db, ch.id):
        if p.user_id != user.id:
            push_service.send_to_user(
                db, p.user_id, "Wyzwanie zakończone",
                "Wyzwanie dobiegło końca — zobacz podsumowanie w aplikacji.",
                "/wyzwania",
            )
    db.commit()
    return _challenge_out(ch)


@router.post("/challenges/{challenge_id}/cancel")
def cancel_challenge(
    challenge_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ch = _require_organizer(db, user, challenge_id)
    if ch.status in ("FINISHED", "CANCELLED"):
        raise HTTPException(status_code=422, detail="Wyzwanie jest już zakończone")
    ch.status = "CANCELLED"
    ch.cancelled_at = now_iso()
    ch.updated_at = now_iso()
    _audit(db, "CHALLENGE_CANCELLED", user.id, ch, {}, "Anulowanie wyzwania")
    for p in _active_participants(db, ch.id):
        if p.user_id != user.id:
            push_service.send_to_user(
                db, p.user_id, "Wyzwanie odwołane",
                "Organizator odwołał wyzwanie — szczegóły w aplikacji.",
                "/wyzwania",
            )
    db.commit()
    return _challenge_out(ch)


# ---------------------------------------------------------------------------
# Listy i szczegóły


@router.get("/coach/challenges")
def coach_challenges(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    rows = (
        db.query(Challenge)
        .filter_by(organizer_id=coach.id)
        .order_by(Challenge.created_at.desc())
        .all()
    )
    out = []
    for ch in rows:
        open_reports = (
            db.query(ChallengeReport)
            .filter_by(challenge_id=ch.id, status="OPEN")
            .count()
        )
        counts = {"ACTIVE": 0, "INVITED": 0}
        for p in db.query(ChallengeParticipant).filter_by(challenge_id=ch.id).all():
            if p.status in counts:
                counts[p.status] += 1
        out.append({
            **_challenge_out(ch),
            "active_participants": counts["ACTIVE"],
            "pending_invitations": counts["INVITED"],
            "open_reports": open_reports,
        })
    return {"challenges": out}


@router.get("/me/challenges")
def my_challenges(user: User = Depends(current_user), db: Session = Depends(get_db)):
    parts = (
        db.query(ChallengeParticipant)
        .filter(
            ChallengeParticipant.user_id == user.id,
            ChallengeParticipant.status.in_(["INVITED", "ACTIVE"]),
        )
        .all()
    )
    invitations, mine = [], []
    for p in parts:
        ch = db.get(Challenge, p.challenge_id)
        if ch is None or ch.status == "CANCELLED":
            continue
        if p.status == "INVITED":
            if ch.status == "FINISHED":
                continue
            inviter = db.get(User, p.invited_by) if p.invited_by else None
            invitations.append({
                **_challenge_out(ch),
                "invited_by_name": inviter.display_name if inviter else None,
                "invited_at": p.invited_at,
                "explainer": VISIBILITY_EXPLAINER,
            })
        else:
            mine.append({
                **_challenge_out(ch),
                "me": _me_out(p),
                "progress": _progress_out(db, ch, p),
            })
    return {"invitations": invitations, "challenges": mine}


@router.get("/challenges/{challenge_id}")
def challenge_detail(
    challenge_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Szczegóły: organizator lub uczestnik (INVITED widzi wyłącznie
    zapowiedź + wyjaśnienie widoczności). Osoba z zewnątrz → 404
    (logowana odmowa — nie ujawniamy istnienia wyzwania)."""
    ch = db.get(Challenge, challenge_id)
    if ch is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    part = _participant(db, ch.id, user.id)
    is_organizer = ch.organizer_id == user.id

    if not is_organizer and (part is None or part.status not in ("INVITED", "ACTIVE")):
        deny(user.id, f"challenge:{challenge_id}")

    base = {**_challenge_out(ch), "explainer": VISIBILITY_EXPLAINER}

    if part is not None and part.status == "INVITED" and not is_organizer:
        inviter = db.get(User, part.invited_by) if part.invited_by else None
        return {
            **base,
            "me": {"status": "INVITED"},
            "invited_by_name": inviter.display_name if inviter else None,
        }

    shared, ranking = _shared_and_ranking(db, ch, user.id)
    out = {
        **base,
        "group": _group_out(db, ch),
        "shared": shared,
        "ranking": ranking,
    }
    if part is not None and part.status == "ACTIVE":
        out["me"] = {**_me_out(part), "progress": _progress_out(db, ch, part)}
    if is_organizer:
        out["participants"] = [
            {
                "participant_id": p.id, "user_id": p.user_id,
                "alias": p.alias, "status": p.status,
                "share_result": p.share_result,
            }
            for p in db.query(ChallengeParticipant)
            .filter(
                ChallengeParticipant.challenge_id == ch.id,
                ChallengeParticipant.status.in_(["INVITED", "ACTIVE", "LEFT", "REMOVED"]),
            )
            .all()
        ]
        out["open_reports"] = (
            db.query(ChallengeReport).filter_by(challenge_id=ch.id, status="OPEN").count()
        )
    return out


# ---------------------------------------------------------------------------
# Udział: przyjęcie / odrzucenie / opuszczenie / wycofanie / ustawienia


def _require_invited(db: Session, user: User, challenge_id: str) -> tuple[Challenge, ChallengeParticipant]:
    ch = db.get(Challenge, challenge_id)
    part = _participant(db, challenge_id, user.id) if ch else None
    if ch is None or part is None:
        deny(user.id, f"challenge:{challenge_id}")
    return ch, part


@router.post("/challenges/{challenge_id}/join")
def join_challenge(
    challenge_id: str,
    body: JoinIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ch, part = _require_invited(db, user, challenge_id)
    if part.status != "INVITED":
        raise HTTPException(status_code=422, detail="Brak aktywnego zaproszenia")
    if ch.status in ("FINISHED", "CANCELLED"):
        raise HTTPException(status_code=422, detail="Wyzwanie już się zakończyło")
    if body.auto_count_workouts and ch.unit != "treningi":
        raise HTTPException(
            status_code=422,
            detail="Automatyczne zaliczanie treningów działa tylko w "
            "wyzwaniach liczonych w treningach",
        )
    part.status = "ACTIVE"
    part.joined_at = now_iso()
    part.alias = (body.alias or user.display_name).strip()
    part.share_result = body.share_result
    part.ranking_opt_in = body.ranking_opt_in
    part.auto_count_workouts = body.auto_count_workouts
    _audit(db, "CHALLENGE_JOINED", user.id, ch,
           {"share_result": part.share_result, "ranking_opt_in": part.ranking_opt_in,
            "auto_count_workouts": part.auto_count_workouts},
           "Przyjęcie zaproszenia do wyzwania")
    db.commit()
    return {"ok": True, "me": _me_out(part)}


@router.post("/challenges/{challenge_id}/decline")
def decline_challenge(
    challenge_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ch, part = _require_invited(db, user, challenge_id)
    if part.status != "INVITED":
        raise HTTPException(status_code=422, detail="Brak aktywnego zaproszenia")
    part.status = "DECLINED"
    part.declined_at = now_iso()
    _audit(db, "CHALLENGE_DECLINED", user.id, ch, {}, "Odrzucenie zaproszenia do wyzwania")
    db.commit()
    return {"ok": True}


@router.post("/challenges/{challenge_id}/leave")
def leave_challenge(
    challenge_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Opuszczenie wyzwania: uczestnik znika z widoków i agregatów (dane
    pozostają w bazie do czasu trwałego wycofania — patrz /withdraw)."""
    ch, part = _require_invited(db, user, challenge_id)
    if part.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Nie uczestniczysz w tym wyzwaniu")
    part.status = "LEFT"
    part.left_at = now_iso()
    _audit(db, "CHALLENGE_LEFT", user.id, ch, {}, "Opuszczenie wyzwania")
    db.commit()
    return {"ok": True}


@router.post("/challenges/{challenge_id}/withdraw")
def withdraw_participation(
    challenge_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Trwałe wycofanie udziału: wyniki uczestnika są USUWANE (znikają z
    wszystkich widoków), pseudonim anonimizowany, a agregaty grupy od tej
    pory jawnie oznaczone jako skorygowane. Integralność historii zapewnia
    audyt (liczniki, bez treści), nie trzymanie danych osoby."""
    ch, part = _require_invited(db, user, challenge_id)
    if part.status == "WITHDRAWN":
        raise HTTPException(status_code=422, detail="Udział już wycofany")
    deleted = (
        db.query(ChallengeEntry)
        .filter_by(challenge_id=ch.id, participant_id=part.id)
        .delete()
    )
    part.status = "WITHDRAWN"
    part.withdrawn_at = now_iso()
    part.alias = None
    part.share_result = False
    part.ranking_opt_in = False
    part.auto_count_workouts = False
    if deleted:
        ch.aggregates_adjusted = True
        ch.updated_at = now_iso()
    _audit(db, "CHALLENGE_WITHDRAWN", user.id, ch,
           {"entries_deleted": deleted, "aggregates_adjusted": bool(deleted)},
           "Trwałe wycofanie udziału w wyzwaniu")
    db.commit()
    return {"ok": True, "entries_deleted": deleted}


@router.patch("/challenges/{challenge_id}/me")
def update_my_settings(
    challenge_id: str,
    body: ParticipantSettingsIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Ustawienia widoczności per uczestnik: ukrycie wyniku i wyłączenie
    rankingu działają NATYCHMIAST; włączenie zawsze jest świadomą decyzją
    uczestnika (nigdy domyślne)."""
    ch, part = _require_invited(db, user, challenge_id)
    if part.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Nie uczestniczysz w tym wyzwaniu")
    changed: dict = {}
    if body.alias is not None:
        part.alias = body.alias.strip()
        changed["alias_changed"] = True  # sam alias nie trafia do audytu
    if body.share_result is not None:
        part.share_result = body.share_result
        changed["share_result"] = body.share_result
    if body.ranking_opt_in is not None:
        part.ranking_opt_in = body.ranking_opt_in
        changed["ranking_opt_in"] = body.ranking_opt_in
    if body.auto_count_workouts is not None and body.auto_count_workouts != part.auto_count_workouts:
        if body.auto_count_workouts:
            if ch.unit != "treningi":
                raise HTTPException(
                    status_code=422,
                    detail="Automatyczne zaliczanie treningów działa tylko w "
                    "wyzwaniach liczonych w treningach",
                )
            has_entries = (
                db.query(ChallengeEntry)
                .filter_by(challenge_id=ch.id, participant_id=part.id, status="ACTIVE")
                .count()
            )
            if has_entries:
                raise HTTPException(
                    status_code=409,
                    detail="Masz już wpisy w tym wyzwaniu — automatyczne "
                    "zaliczanie podwoiłoby wynik. Wycofaj wpisy albo zostań "
                    "przy zgłaszaniu ręcznym.",
                )
        part.auto_count_workouts = body.auto_count_workouts
        changed["auto_count_workouts"] = body.auto_count_workouts
    if changed:
        _audit(db, "CHALLENGE_SETTINGS_CHANGED", user.id, ch, changed,
               "Zmiana ustawień udziału w wyzwaniu")
    db.commit()
    return {"ok": True, "me": _me_out(part)}


# ---------------------------------------------------------------------------
# Wpisy wyników


@router.post("/challenges/{challenge_id}/entries", status_code=201)
def add_entry(
    challenge_id: str,
    body: EntryIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ch, part = _require_invited(db, user, challenge_id)
    if part.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Nie uczestniczysz w tym wyzwaniu")
    if ch.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Wyzwanie nie jest aktywne")
    unit_info = NEUTRAL_UNITS[ch.unit]

    # Idempotencja ponowień z urządzenia (podwójne kliknięcie / retry).
    if body.client_entry_id:
        existing = (
            db.query(ChallengeEntry)
            .filter_by(participant_id=part.id, client_entry_id=body.client_entry_id)
            .one_or_none()
        )
        if existing is not None:
            return {**_entry_out(existing), "duplicate": True}

    if body.workout_session_id:
        # Jawne zgłoszenie WŁASNEGO treningu do wyzwania.
        if ch.unit != "treningi":
            raise HTTPException(
                status_code=422,
                detail="Treningi można zgłaszać tylko w wyzwaniach liczonych w treningach",
            )
        if part.auto_count_workouts:
            raise HTTPException(
                status_code=409,
                detail="Masz włączone automatyczne zaliczanie treningów — "
                "ten trening jest już policzony",
            )
        session = db.get(WorkoutSession, body.workout_session_id)
        if session is None or session.client_id != user.id:
            deny(user.id, f"workout:{body.workout_session_id}")
        dup = (
            db.query(ChallengeEntry)
            .filter_by(challenge_id=ch.id, workout_session_id=session.id)
            .one_or_none()
        )
        if dup is not None:
            # Ten sam trening zgłoszony ponownie — brak podwójnego naliczania.
            return {**_entry_out(dup), "duplicate": True}
        entry_date = session.performed_on
        value = 1.0
        source = "WORKOUT"
    else:
        if part.auto_count_workouts and ch.unit == "treningi":
            raise HTTPException(
                status_code=409,
                detail="Masz włączone automatyczne zaliczanie treningów — "
                "wpisy ręczne podwoiłyby wynik",
            )
        fixed = unit_info["fixed_value"]
        value = fixed if fixed is not None else body.value
        if value is None:
            raise HTTPException(status_code=422, detail="Podaj wartość wpisu")
        if value <= 0 or value > unit_info["max_value"]:
            raise HTTPException(
                status_code=422,
                detail=f"Wartość poza dozwolonym zakresem (maks. "
                f"{unit_info['max_value']:g})",
            )
        entry_date = body.entry_date or _challenge_today(ch)
        source = "MANUAL"

    today = _challenge_today(ch)
    if entry_date > today:
        raise HTTPException(status_code=422, detail="Data wpisu nie może być z przyszłości")
    if not (ch.starts_on <= entry_date <= ch.ends_on):
        raise HTTPException(status_code=422, detail="Data wpisu poza czasem trwania wyzwania")

    day_count = (
        db.query(ChallengeEntry)
        .filter_by(participant_id=part.id, entry_date=entry_date, status="ACTIVE")
        .count()
    )
    if day_count >= ch.max_entries_per_day:
        raise HTTPException(
            status_code=422,
            detail=f"Limit wpisów na dzień ({ch.max_entries_per_day}) wyczerpany",
        )

    entry = ChallengeEntry(
        id=new_id("CHE"), challenge_id=ch.id, participant_id=part.id,
        entry_date=entry_date, value=float(value), note=body.note,
        source=source, workout_session_id=body.workout_session_id,
        client_entry_id=body.client_entry_id,
    )
    db.add(entry)
    _audit(db, "CHALLENGE_ENTRY_ADDED", user.id, ch,
           {"entry_id": entry.id, "entry_date": entry_date, "value": entry.value,
            "source": source},
           "Wpis wyniku do wyzwania")
    db.commit()
    return _entry_out(entry)


def _entry_out(e: ChallengeEntry) -> dict:
    return {
        "id": e.id, "entry_date": e.entry_date, "value": e.value,
        "note": e.note, "source": e.source, "status": e.status,
        "corrects_entry_id": e.corrects_entry_id, "created_at": e.created_at,
    }


@router.get("/challenges/{challenge_id}/entries")
def my_entries(
    challenge_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """WŁASNA historia wpisów (z korektami) — nikt inny jej nie widzi."""
    ch, part = _require_invited(db, user, challenge_id)
    rows = (
        db.query(ChallengeEntry)
        .filter_by(challenge_id=ch.id, participant_id=part.id)
        .order_by(ChallengeEntry.entry_date.desc(), ChallengeEntry.created_at.desc())
        .all()
    )
    return {"entries": [_entry_out(e) for e in rows]}


@router.post("/challenges/{challenge_id}/entries/{entry_id}/correct")
def correct_entry(
    challenge_id: str,
    entry_id: str,
    body: CorrectionIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Korekta wpisu: stary wiersz dostaje status CORRECTED (historia
    zostaje), nowy wskazuje na niego przez corrects_entry_id."""
    ch, part = _require_invited(db, user, challenge_id)
    if ch.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Wyzwanie nie jest aktywne")
    old = db.get(ChallengeEntry, entry_id)
    if old is None or old.challenge_id != ch.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if old.participant_id != part.id:
        deny(user.id, f"challenge_entry:{entry_id}")
    if old.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Ten wpis został już skorygowany")
    unit_info = NEUTRAL_UNITS[ch.unit]
    if body.value <= 0 or body.value > unit_info["max_value"]:
        raise HTTPException(
            status_code=422,
            detail=f"Wartość poza dozwolonym zakresem (maks. {unit_info['max_value']:g})",
        )
    old.status = "CORRECTED"
    new = ChallengeEntry(
        id=new_id("CHE"), challenge_id=ch.id, participant_id=part.id,
        entry_date=old.entry_date, value=float(body.value),
        note=body.note if body.note is not None else old.note,
        source="MANUAL", corrects_entry_id=old.id,
    )
    db.add(new)
    _audit(db, "CHALLENGE_ENTRY_CORRECTED", user.id, ch,
           {"entry_id": old.id, "new_entry_id": new.id,
            "old_value": old.value, "new_value": new.value},
           "Korekta wpisu w wyzwaniu")
    db.commit()
    return _entry_out(new)


# ---------------------------------------------------------------------------
# Blokady i zgłoszenia


def _require_other_participant(
    db: Session, ch: Challenge, actor: User, target_user_id: str
) -> ChallengeParticipant:
    if target_user_id == actor.id:
        raise HTTPException(status_code=422, detail="Nie można wskazać samego siebie")
    target = _participant(db, ch.id, target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono uczestnika")
    return target


@router.post("/challenges/{challenge_id}/block")
def block_participant(
    challenge_id: str,
    body: TargetUserIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ch, part = _require_invited(db, user, challenge_id)
    if part.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Nie uczestniczysz w tym wyzwaniu")
    _require_other_participant(db, ch, user, body.user_id)
    exists = (
        db.query(ChallengeBlock)
        .filter_by(challenge_id=ch.id, blocker_id=user.id, blocked_id=body.user_id)
        .one_or_none()
    )
    if exists is None:
        db.add(ChallengeBlock(
            id=new_id("CHB"), challenge_id=ch.id,
            blocker_id=user.id, blocked_id=body.user_id,
        ))
        _audit(db, "CHALLENGE_PARTICIPANT_BLOCKED", user.id, ch,
               {"blocked_user_id": body.user_id}, "Blokada uczestnika wyzwania")
    db.commit()
    return {"ok": True}


@router.post("/challenges/{challenge_id}/unblock")
def unblock_participant(
    challenge_id: str,
    body: TargetUserIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ch, _part = _require_invited(db, user, challenge_id)
    deleted = (
        db.query(ChallengeBlock)
        .filter_by(challenge_id=ch.id, blocker_id=user.id, blocked_id=body.user_id)
        .delete()
    )
    if deleted:
        _audit(db, "CHALLENGE_PARTICIPANT_UNBLOCKED", user.id, ch,
               {"unblocked_user_id": body.user_id}, "Zdjęcie blokady uczestnika")
    db.commit()
    return {"ok": True}


@router.post("/challenges/{challenge_id}/report", status_code=201)
def report_participant(
    challenge_id: str,
    body: ReportIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Zgłoszenie uczestnika do organizatora (treść zgłoszenia widzi tylko
    organizator; do audytu trafiają wyłącznie identyfikatory)."""
    ch, part = _require_invited(db, user, challenge_id)
    if part.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Nie uczestniczysz w tym wyzwaniu")
    _require_other_participant(db, ch, user, body.user_id)
    report = ChallengeReport(
        id=new_id("CHR"), challenge_id=ch.id, reporter_id=user.id,
        reported_user_id=body.user_id, reason=body.reason,
    )
    db.add(report)
    _audit(db, "CHALLENGE_REPORTED", user.id, ch,
           {"report_id": report.id, "reported_user_id": body.user_id},
           "Zgłoszenie uczestnika wyzwania")
    push_service.send_to_user(
        db, ch.organizer_id, "Nowe zgłoszenie w wyzwaniu",
        "Uczestnik zgłosił problem w wyzwaniu — sprawdź panel moderacji.",
        "/trener/wyzwania",
    )
    db.commit()
    return {"ok": True, "report_id": report.id}


@router.get("/challenges/{challenge_id}/reports")
def challenge_reports(
    challenge_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Moderacja WYŁĄCZNIE własnych wyzwań (organizator)."""
    ch = _require_organizer(db, user, challenge_id)
    rows = (
        db.query(ChallengeReport)
        .filter_by(challenge_id=ch.id)
        .order_by(ChallengeReport.created_at.desc())
        .all()
    )
    def _name(uid: str) -> str | None:
        u = db.get(User, uid)
        return u.display_name if u else None
    return {"reports": [
        {
            "id": r.id, "reporter_name": _name(r.reporter_id),
            "reported_user_id": r.reported_user_id,
            "reported_name": _name(r.reported_user_id),
            "reason": r.reason, "status": r.status,
            "resolution": r.resolution, "resolution_note": r.resolution_note,
            "created_at": r.created_at, "resolved_at": r.resolved_at,
        }
        for r in rows
    ]}


@router.post("/challenges/{challenge_id}/reports/{report_id}/resolve")
def resolve_report(
    challenge_id: str,
    report_id: str,
    body: ResolveIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Rozstrzygnięcie zgłoszenia przez organizatora:
    REMOVED — usunięcie uczestnika z wyzwania,
    ALIAS_RESET — neutralizacja niedozwolonego pseudonimu,
    NOTES_CLEARED — usunięcie treści notatek wpisów zgłoszonej osoby,
    DISMISSED — oddalenie. Każda decyzja audytowana."""
    ch = _require_organizer(db, user, challenge_id)
    report = db.get(ChallengeReport, report_id)
    if report is None or report.challenge_id != ch.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if report.status != "OPEN":
        raise HTTPException(status_code=422, detail="Zgłoszenie już rozstrzygnięte")
    target = _participant(db, ch.id, report.reported_user_id)
    if body.resolution == "REMOVED" and target is not None:
        target.status = "REMOVED"
        target.removed_at = now_iso()
    elif body.resolution == "ALIAS_RESET" and target is not None:
        target.alias = NEUTRAL_ALIAS
    elif body.resolution == "NOTES_CLEARED" and target is not None:
        for e in db.query(ChallengeEntry).filter_by(
            challenge_id=ch.id, participant_id=target.id
        ).all():
            e.note = None
    report.status = "RESOLVED"
    report.resolution = body.resolution
    report.resolution_note = body.note
    report.resolved_by = user.id
    report.resolved_at = now_iso()
    _audit(db, "CHALLENGE_REPORT_RESOLVED", user.id, ch,
           {"report_id": report.id, "resolution": body.resolution,
            "reported_user_id": report.reported_user_id},
           f"Rozstrzygnięcie zgłoszenia: {body.resolution}",
           subject_ids=[report.reported_user_id])
    db.commit()
    return {"ok": True}


@router.post("/challenges/{challenge_id}/participants/{participant_id}/remove")
def remove_participant(
    challenge_id: str,
    participant_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Moderacja organizatora: usunięcie uczestnika (wyniki znikają z
    widoków — wiersze pozostają do czasu trwałego wycofania przez samego
    uczestnika lub usunięcia konta)."""
    ch = _require_organizer(db, user, challenge_id)
    part = db.get(ChallengeParticipant, participant_id)
    if part is None or part.challenge_id != ch.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if part.status not in ("INVITED", "ACTIVE"):
        raise HTTPException(status_code=422, detail="Uczestnik nie jest aktywny")
    part.status = "REMOVED"
    part.removed_at = now_iso()
    _audit(db, "CHALLENGE_PARTICIPANT_REMOVED", user.id, ch,
           {"participant_id": part.id}, "Usunięcie uczestnika wyzwania",
           subject_ids=[part.user_id])
    db.commit()
    return {"ok": True}


@router.post("/challenges/{challenge_id}/participants/{participant_id}/reset-alias")
def reset_alias(
    challenge_id: str,
    participant_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Moderacja organizatora: neutralizacja niedozwolonego pseudonimu."""
    ch = _require_organizer(db, user, challenge_id)
    part = db.get(ChallengeParticipant, participant_id)
    if part is None or part.challenge_id != ch.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    part.alias = NEUTRAL_ALIAS
    _audit(db, "CHALLENGE_ALIAS_RESET", user.id, ch,
           {"participant_id": part.id}, "Neutralizacja pseudonimu w wyzwaniu",
           subject_ids=[part.user_id])
    db.commit()
    return {"ok": True}


@router.get("/challenge-units")
def challenge_units():
    """Katalog dozwolonych (neutralnych) jednostek wyniku."""
    return {"units": [
        {"key": k, "label": v["label"], "fixed_value": v["fixed_value"],
         "max_value": v["max_value"]}
        for k, v in NEUTRAL_UNITS.items()
    ]}

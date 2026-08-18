"""Monitoring w czasie: adherencja harmonogramu, dziennik obserwacji
(samopoczucie/reakcje — nigdy diagnoza), dziennik żywieniowy i agregacja
trendów dla celu klienta.

Zasada bezpieczeństwa (patrz docs/PERMISSIONS.md §Suplementacja): system
wyłącznie rejestruje i pokazuje trendy z danych wprowadzonych przez
człowieka. Nie interpretuje objawów, nie sugeruje diagnoz ani zmian dawek —
NIEPOKOJACE obserwacje są jedynie flagowane do przeglądu przez trenera
(ewentualnie właściwego specjalistę), nigdy automatycznie oceniane.
"""

from __future__ import annotations

import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import deny, resolve_client_access
from ..dates import local_today, parse_iso_date
from ..db import get_db
from ..hos_bridge import record_event
from ..models import (
    CoachClientRelationship,
    DailyNutritionLog,
    Goal,
    Measurement,
    NutritionPlan,
    NutritionPlanVersion,
    Observation,
    ScheduleCompletion,
    ScheduleItem,
    User,
    WeeklyCheckin,
    new_id,
)
from ..notifications_provider import provider as notifications
from ..schemas import NutritionLogIn, ObservationIn, ScheduleCompletionIn
from ..security import current_user

router = APIRouter(prefix="/api", tags=["monitoring"])

WELLBEING_KEYS = ["sleep", "energy", "stress", "hunger", "recovery", "diet_adherence"]


@router.post("/clients/{client_id}/schedule/{item_id}/complete", status_code=201)
def complete_schedule_item(
    client_id: str,
    item_id: str,
    body: ScheduleCompletionIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Odhaczenie elementu harmonogramu (trening, posiłek, suplement,
    nawodnienie, regeneracja...) na dany dzień. Ponowne wywołanie na ten
    sam dzień nadpisuje wpis (idempotentne — nie mnoży rekordów)."""
    resolve_client_access(db, user, client_id, action="write")
    item = db.get(ScheduleItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if item.client_id != client_id:
        # item_id z harmonogramu innego klienta (IDOR) — logowana odmowa.
        deny(user.id, f"schedule_item:{item_id}")
    existing = (
        db.query(ScheduleCompletion)
        .filter_by(schedule_item_id=item_id, completed_on=body.completed_on)
        .one_or_none()
    )
    if existing is not None:
        existing.status = body.status
        existing.note = body.note
        row = existing
    else:
        row = ScheduleCompletion(
            id=new_id("SCP"),
            schedule_item_id=item_id,
            client_id=client_id,
            completed_on=body.completed_on,
            status=body.status,
            note=body.note,
            created_by=user.id,
        )
        db.add(row)
    db.commit()
    return {"id": row.id, "status": row.status}


@router.post("/clients/{client_id}/observations", status_code=201)
def create_observation(
    client_id: str,
    body: ObservationIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Dziennik obserwacji — dobrowolne zgłoszenie klienta (lub notatka
    trenera) o samopoczuciu lub reakcji, opcjonalnie powiązane z elementem
    harmonogramu (np. suplementem). Wpis NIEPOKOJACE jest wyłącznie
    flagowany do przeglądu przez trenera — nigdy nie jest automatycznie
    interpretowany ani nie zmienia dawkowania/planu."""
    resolve_client_access(db, user, client_id, action="write")
    if body.schedule_item_id:
        item = db.get(ScheduleItem, body.schedule_item_id)
        if item is None or item.client_id != client_id:
            raise HTTPException(status_code=422, detail="Nieprawidłowy element harmonogramu")
    row = Observation(
        id=new_id("OBS"),
        client_id=client_id,
        occurred_on=body.occurred_on,
        schedule_item_id=body.schedule_item_id,
        category=body.category,
        severity=body.severity,
        text=body.text,
        created_by=user.id,
    )
    db.add(row)
    record_event(
        db,
        action="OBSERVATION_LOGGED",
        actor_id=user.id,
        subject_ids=[client_id],
        payload={
            "observation_id": row.id, "category": body.category,
            "severity": body.severity, "schedule_item_id": body.schedule_item_id,
        },
        summary=f"Obserwacja ({body.category}, {body.severity})",
    )
    if body.severity == "NIEPOKOJACE":
        coach_ids = [
            r.coach_id
            for r in db.query(CoachClientRelationship)
            .filter_by(client_id=client_id, status="ACTIVE")
            .all()
        ]
        for coach_id in coach_ids:
            coach = db.get(User, coach_id)
            if coach is not None:
                # Treść e-maila BEZ danych zdrowotnych (kategoria i tekst
                # obserwacji nimi są) — wyłącznie neutralne wezwanie do
                # zajrzenia do panelu, jak w powiadomieniach push.
                notifications.send_email(
                    to=coach.email,
                    subject="Dzik OS: nowy wpis podopiecznego wymaga uwagi",
                    body=(
                        f"{user.display_name} dodał(a) wpis oznaczony jako "
                        "niepokojący. Szczegóły znajdziesz po zalogowaniu "
                        "do panelu trenera."
                    ),
                )
    db.commit()
    return {"id": row.id}


@router.get("/clients/{client_id}/observations")
def list_observations(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    rows = (
        db.query(Observation)
        .filter(Observation.client_id == client_id)
        .order_by(Observation.occurred_on.desc())
        .limit(100)
        .all()
    )
    # Sortowanie stabilne: zachowuje malejącą datę w obrębie tej samej
    # ważności, a NIEPOKOJACE zawsze wypływa na wierzch.
    severity_rank = {"NIEPOKOJACE": 0, "INFO": 1}
    rows.sort(key=lambda o: severity_rank.get(o.severity, 2))
    names = {
        i.id: i.name
        for i in db.query(ScheduleItem).filter(ScheduleItem.client_id == client_id).all()
    }
    return {
        "observations": [
            {
                "id": o.id, "occurred_on": o.occurred_on, "category": o.category,
                "severity": o.severity, "text": o.text,
                "schedule_item_id": o.schedule_item_id,
                "schedule_item_name": names.get(o.schedule_item_id) if o.schedule_item_id else None,
                "created_by": o.created_by, "created_at": o.created_at,
            }
            for o in rows
        ]
    }


@router.post("/clients/{client_id}/nutrition-log", status_code=201)
def log_nutrition(
    client_id: str,
    body: NutritionLogIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Dzienny log realizacji diety — deklaracja klienta, osobna od
    statycznego celu w planie żywieniowym; jeden wpis na dzień (poprawka
    nadpisuje)."""
    resolve_client_access(db, user, client_id, action="write")
    existing = (
        db.query(DailyNutritionLog)
        .filter_by(client_id=client_id, logged_on=body.logged_on)
        .one_or_none()
    )
    if existing is not None:
        existing.kcal, existing.protein_g, existing.fat_g = body.kcal, body.protein_g, body.fat_g
        existing.carbs_g, existing.water_l, existing.note = body.carbs_g, body.water_l, body.note
        row = existing
    else:
        row = DailyNutritionLog(
            id=new_id("NLG"), client_id=client_id, logged_on=body.logged_on,
            kcal=body.kcal, protein_g=body.protein_g, fat_g=body.fat_g,
            carbs_g=body.carbs_g, water_l=body.water_l, note=body.note,
            created_by=user.id,
        )
        db.add(row)
    db.commit()
    return {"id": row.id}


@router.get("/clients/{client_id}/nutrition-log")
def list_nutrition_log(
    client_id: str,
    days: int = 30,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    since = (local_today() - timedelta(days=days)).isoformat()
    rows = (
        db.query(DailyNutritionLog)
        .filter(DailyNutritionLog.client_id == client_id, DailyNutritionLog.logged_on >= since)
        .order_by(DailyNutritionLog.logged_on)
        .all()
    )
    return {
        "logs": [
            {
                "id": r.id, "logged_on": r.logged_on, "kcal": r.kcal,
                "protein_g": r.protein_g, "fat_g": r.fat_g, "carbs_g": r.carbs_g,
                "water_l": r.water_l, "note": r.note,
            }
            for r in rows
        ]
    }


@router.get("/clients/{client_id}/monitoring")
def monitoring(
    client_id: str,
    days: int = 30,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Agregat monitoringu: cel i czas do jego realizacji, trendy pomiarów
    i samopoczucia z raportów, dziennik kaloryczny na tle celu, adherencja
    harmonogramu per kategoria oraz najnowsze obserwacje (niepokojące
    pierwsze) — jeden przegląd zamiast przeklikiwania kilku ekranów."""
    resolve_client_access(db, user, client_id)
    # Dzień kalendarzowy w strefie lokalnej użytkownika — dane dzienne
    # (logged_on/occurred_on/completed_on) są datami lokalnymi.
    today = local_today()
    since_date = today - timedelta(days=days)
    since = since_date.isoformat()

    goal = (
        db.query(Goal)
        .filter(Goal.client_id == client_id, Goal.kind == "MAIN", Goal.status == "ACTIVE")
        .order_by(Goal.created_at.desc())
        .first()
    )
    goal_out = None
    if goal is not None:
        days_remaining = None
        if goal.target_date:
            try:
                days_remaining = (parse_iso_date(goal.target_date) - today).days
            except ValueError:
                days_remaining = None
        goal_out = {
            "id": goal.id, "title": goal.title, "target_date": goal.target_date,
            "days_remaining": days_remaining, "created_at": goal.created_at,
        }

    measurement_series: dict[str, list[dict]] = {}
    for m in (
        db.query(Measurement)
        .filter(Measurement.client_id == client_id, Measurement.measured_at >= since)
        .order_by(Measurement.measured_at)
        .all()
    ):
        measurement_series.setdefault(m.kind, []).append(
            {"date": m.measured_at, "value": m.value, "unit": m.unit}
        )

    wellbeing_series: dict[str, list[dict]] = {k: [] for k in WELLBEING_KEYS}
    for c in (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.client_id == client_id, WeeklyCheckin.week_start >= since)
        .order_by(WeeklyCheckin.week_start)
        .all()
    ):
        payload = json.loads(c.payload_json)
        for key in WELLBEING_KEYS:
            value = payload.get(key)
            if value is not None:
                wellbeing_series[key].append({"date": c.week_start, "value": value})
    wellbeing_series = {k: v for k, v in wellbeing_series.items() if v}

    nutrition_target = None
    nplan = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.client_id == client_id, NutritionPlan.status == "ACTIVE")
        .order_by(NutritionPlan.updated_at.desc())
        .first()
    )
    if nplan is not None and nplan.current_version_no:
        nv = (
            db.query(NutritionPlanVersion)
            .filter_by(plan_id=nplan.id, version_no=nplan.current_version_no)
            .one_or_none()
        )
        if nv is not None:
            nutrition_target = json.loads(nv.content_json).get("kcal")
    kcal_log = [
        {"date": n.logged_on, "value": n.kcal}
        for n in db.query(DailyNutritionLog)
        .filter(DailyNutritionLog.client_id == client_id, DailyNutritionLog.logged_on >= since)
        .order_by(DailyNutritionLog.logged_on)
        .all()
        if n.kcal is not None
    ]

    items = (
        db.query(ScheduleItem)
        .filter(ScheduleItem.client_id == client_id, ScheduleItem.status == "ACTIVE")
        .all()
    )
    done_by_item: dict[str, set[str]] = {}
    for comp in (
        db.query(ScheduleCompletion)
        .filter(
            ScheduleCompletion.client_id == client_id,
            ScheduleCompletion.completed_on >= since,
            ScheduleCompletion.status == "DONE",
        )
        .all()
    ):
        done_by_item.setdefault(comp.schedule_item_id, set()).add(comp.completed_on)

    adherence: dict[str, dict] = {}
    for item in items:
        weekdays = {int(d) for d in item.days_of_week.split(",") if d.strip()}
        start = since_date
        if item.start_date:
            try:
                start = max(start, parse_iso_date(item.start_date))
            except ValueError:
                pass
        end = today
        if item.end_date:
            try:
                end = min(end, parse_iso_date(item.end_date))
            except ValueError:
                pass
        total = 0
        cur = start
        while cur <= end:
            if cur.isoweekday() in weekdays:
                total += 1
            cur += timedelta(days=1)
        done = min(len(done_by_item.get(item.id, set())), total)
        bucket = adherence.setdefault(item.category, {"done": 0, "total": 0})
        bucket["done"] += done
        bucket["total"] += total
    for bucket in adherence.values():
        bucket["pct"] = round(100 * bucket["done"] / bucket["total"]) if bucket["total"] else None

    obs_rows = (
        db.query(Observation)
        .filter(Observation.client_id == client_id, Observation.occurred_on >= since)
        .order_by(Observation.occurred_on.desc())
        .limit(100)
        .all()
    )
    severity_rank = {"NIEPOKOJACE": 0, "INFO": 1}
    obs_rows.sort(key=lambda o: severity_rank.get(o.severity, 2))

    return {
        "period_days": days,
        "goal": goal_out,
        "measurement_series": measurement_series,
        "wellbeing_series": wellbeing_series,
        "nutrition": {"target_kcal": nutrition_target, "log_series": kcal_log},
        "adherence": adherence,
        "observations": [
            {
                "id": o.id, "occurred_on": o.occurred_on, "category": o.category,
                "severity": o.severity, "text": o.text,
            }
            for o in obs_rows[:30]
        ],
    }

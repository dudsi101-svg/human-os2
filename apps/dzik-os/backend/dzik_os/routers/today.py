from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..authz import require_client_self
from ..db import get_db
from ..models import (
    Message,
    MessageThread,
    NutritionPlan,
    NutritionPlanVersion,
    PaymentRecord,
    PaymentSchedule,
    Reminder,
    ScheduleItem,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    WeeklyCheckin,
    WorkoutSession,
)
from ..security import current_user

router = APIRouter(prefix="/api", tags=["today"])


@router.get("/me/today")
def today_view(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Ekran „Dzisiaj" klienta: dzisiejszy trening, zalecenia, harmonogram,
    raport, płatność i ostatnia wiadomość trenera — jeden prosty agregat."""
    client_id = require_client_self(db, user)
    now = datetime.now(UTC)
    today = now.date()
    weekday = today.isoweekday()  # 1=pon ... 7=niedz

    # Dzisiejszy trening: dzień aktualnej wersji aktywnego planu przypisany
    # do dzisiejszego dnia tygodnia.
    todays_workout = None
    plan = (
        db.query(TrainingPlan)
        .filter(TrainingPlan.client_id == client_id, TrainingPlan.status == "ACTIVE")
        .order_by(TrainingPlan.updated_at.desc())
        .first()
    )
    if plan is not None and plan.current_version_no:
        version = (
            db.query(TrainingPlanVersion)
            .filter_by(plan_id=plan.id, version_no=plan.current_version_no)
            .one_or_none()
        )
        if version is not None:
            content = json.loads(version.content_json)
            for idx, day in enumerate(content.get("days", [])):
                if day.get("weekday") == weekday:
                    done = (
                        db.query(WorkoutSession)
                        .filter_by(
                            client_id=client_id,
                            plan_version_id=version.id,
                            day_index=idx,
                            performed_on=today.isoformat(),
                        )
                        .first()
                    )
                    todays_workout = {
                        "plan_id": plan.id,
                        "plan_title": plan.title,
                        "plan_version_id": version.id,
                        "version_no": version.version_no,
                        "day_index": idx,
                        "day": day,
                        "done_today": done is not None,
                    }
                    break

    # Dzisiejsze zalecenia żywieniowe (aktualna wersja diety).
    nutrition_summary = None
    nplan = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.client_id == client_id, NutritionPlan.status == "ACTIVE")
        .order_by(NutritionPlan.updated_at.desc())
        .first()
    )
    if nplan is not None and nplan.current_version_no:
        nversion = (
            db.query(NutritionPlanVersion)
            .filter_by(plan_id=nplan.id, version_no=nplan.current_version_no)
            .one_or_none()
        )
        if nversion is not None:
            content = json.loads(nversion.content_json)
            nutrition_summary = {
                "plan_id": nplan.id,
                "title": nplan.title,
                "kcal": content.get("kcal"),
                "protein_g": content.get("protein_g"),
                "fat_g": content.get("fat_g"),
                "carbs_g": content.get("carbs_g"),
            }

    # Elementy harmonogramu na dziś.
    schedule_today = []
    for item in (
        db.query(ScheduleItem)
        .filter(ScheduleItem.client_id == client_id, ScheduleItem.status == "ACTIVE")
        .all()
    ):
        days = {d.strip() for d in item.days_of_week.split(",") if d.strip()}
        if str(weekday) not in days:
            continue
        if item.start_date and item.start_date > today.isoformat():
            continue
        if item.end_date and item.end_date < today.isoformat():
            continue
        schedule_today.append(
            {
                "id": item.id, "name": item.name, "category": item.category,
                "time_of_day": item.time_of_day, "instruction": item.instruction,
            }
        )
    schedule_today.sort(key=lambda i: i["time_of_day"] or "99:99")

    # Przypomnienia (aktywne, najbliższe).
    reminders = [
        {"id": r.id, "text": r.text, "due_date": r.due_date}
        for r in db.query(Reminder)
        .filter(Reminder.client_id == client_id, Reminder.status == "ACTIVE",
                Reminder.due_date >= today.isoformat())
        .order_by(Reminder.due_date)
        .limit(5)
        .all()
    ]

    # Najbliższy raport: ostatni + 7 dni (lub „ten tydzień", jeśli brak).
    last_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.client_id == client_id)
        .order_by(WeeklyCheckin.week_start.desc())
        .first()
    )
    checkin_due = None
    if last_checkin is not None:
        from datetime import timedelta

        checkin_due = (
            datetime.fromisoformat(last_checkin.week_start).date() + timedelta(days=7)
        ).isoformat()

    # Płatność: najbliższy nieopłacony rekord.
    next_payment = None
    row = (
        db.query(PaymentRecord)
        .join(PaymentSchedule, PaymentRecord.schedule_id == PaymentSchedule.id)
        .filter(
            PaymentSchedule.client_id == client_id,
            PaymentRecord.status.in_(["PENDING", "OVERDUE"]),
        )
        .order_by(PaymentRecord.due_date)
        .first()
    )
    if row is not None:
        schedule = db.get(PaymentSchedule, row.schedule_id)
        next_payment = {
            "record_id": row.id,
            "due_date": row.due_date,
            "amount_cents": row.amount_cents,
            "currency": row.currency,
            "status": "OVERDUE" if row.due_date < today.isoformat() else row.status,
            "package_name": schedule.package_name if schedule else None,
            "external_link": schedule.external_link if schedule else None,
        }

    # Ostatnia wiadomość trenera.
    last_coach_message = None
    thread = (
        db.query(MessageThread).filter(MessageThread.client_id == client_id).first()
    )
    if thread is not None:
        msg = (
            db.query(Message)
            .filter(Message.thread_id == thread.id, Message.author_id == thread.coach_id)
            .order_by(Message.created_at.desc())
            .first()
        )
        if msg is not None:
            last_coach_message = {
                "thread_id": thread.id,
                "body": msg.body[:300],
                "created_at": msg.created_at,
                "unread": msg.read_at is None,
            }

    return {
        "date": today.isoformat(),
        "weekday": weekday,
        "workout": todays_workout,
        "nutrition": nutrition_summary,
        "schedule": schedule_today,
        "reminders": reminders,
        "checkin_due": checkin_due,
        "next_payment": next_payment,
        "last_coach_message": last_coach_message,
    }

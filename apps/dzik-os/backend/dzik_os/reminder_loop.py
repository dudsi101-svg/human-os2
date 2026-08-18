"""Pętla przypomnień push (w procesie, co ~60 s).

Wysyła wyłącznie przypomnienia o planie świadomie wprowadzonym przez
człowieka (elementy harmonogramu z ustawioną porą + jednorazowe
przypomnienia trenera) do użytkowników, którzy sami włączyli push.
Treść: nazwa elementu harmonogramu — bez danych zdrowotnych.

Dedup w pamięci procesu na (id, data): restart maszyny w tej samej
minucie może najwyżej powtórzyć jedno przypomnienie — akceptowalne.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from . import push_service
from .dates import local_now
from .db import db_session
from .models import PaymentRecord, PaymentSchedule, Reminder, ScheduleItem
from .observability import exception_fields, log_json, metrics
from .payment_state import DUE_STATUSES

REMINDER_HOUR = "08:00"  # jednorazowe przypomnienia trenera — rano

# Przypomnienie o płatności: w dniu terminu, a przy zaległości co 7 dni
# (bez codziennego nękania). Wysyłane WYŁĄCZNIE dla należności realnie
# wymagalnych (DUE_STATUSES sprawdzane w zapytaniu w chwili wysyłki —
# opłacona/anulowana/planowana rata nigdy nie dostaje przypomnienia).
PAYMENT_REMINDER_EVERY_DAYS = 7


def _payment_reminders(db, today: str) -> int:
    """Przypomnienia powiązane z RZECZYWISTYM statusem należności.
    Treść neutralna: bez kwot, walut i nazw pakietów (powiadomienie może
    wyświetlić się na ekranie blokady)."""
    from datetime import date

    sent = 0
    rows = (
        db.query(PaymentRecord, PaymentSchedule)
        .join(PaymentSchedule, PaymentRecord.schedule_id == PaymentSchedule.id)
        .filter(
            PaymentRecord.status.in_(DUE_STATUSES),
            PaymentRecord.due_date <= today,
        )
        .all()
    )
    for record, schedule in rows:
        try:
            days_over = (date.fromisoformat(today) - date.fromisoformat(record.due_date)).days
        except ValueError:
            continue
        if days_over != 0 and days_over % PAYMENT_REMINDER_EVERY_DAYS != 0:
            continue
        key = (record.id, today)
        if key in _sent:
            continue
        _sent.add(key)
        body = (
            "Dziś mija termin płatności — szczegóły w aplikacji."
            if days_over == 0
            else "Masz zaległą płatność — szczegóły w aplikacji."
        )
        sent += push_service.send_to_user(
            db, schedule.client_id, "Przypomnienie o płatności", body, "/platnosci",
        )
    return sent

_sent: set[tuple[str, str]] = set()
_sent_date: str | None = None


def _tick(now: datetime) -> int:
    """Jedno przejście pętli; zwraca liczbę wysłanych (dla testów)."""
    global _sent_date
    today = now.date().isoformat()
    hhmm = now.strftime("%H:%M")
    weekday = str(now.isoweekday())
    if _sent_date != today:
        _sent.clear()
        _sent_date = today
    sent = 0
    with db_session() as db:
        items = (
            db.query(ScheduleItem)
            .filter(ScheduleItem.status == "ACTIVE", ScheduleItem.time_of_day == hhmm)
            .all()
        )
        for item in items:
            if weekday not in item.days_of_week.split(","):
                continue
            if item.start_date and item.start_date > today:
                continue
            if item.end_date and item.end_date < today:
                continue
            key = (item.id, today)
            if key in _sent:
                continue
            _sent.add(key)
            sent += push_service.send_to_user(
                db, item.client_id, "Przypomnienie",
                item.name + (f" — {item.time_of_day}" if item.time_of_day else ""),
                "/",
            )
        if hhmm == REMINDER_HOUR:
            sent += _payment_reminders(db, today)
            reminders = (
                db.query(Reminder)
                .filter(Reminder.status == "ACTIVE", Reminder.due_date == today)
                .all()
            )
            for r in reminders:
                key = (r.id, today)
                if key in _sent:
                    continue
                _sent.add(key)
                sent += push_service.send_to_user(
                    db, r.client_id, "Przypomnienie od trenera", r.text, "/",
                )
    return sent


_last_cleanup: datetime | None = None


def _maybe_cleanup(now: datetime) -> None:
    """Raz na godzinę (i od razu po starcie): sprzątanie plików-sierot
    (patrz file_cleanup) — uploady nigdy nie podpięte do zasobu po TTL."""
    global _last_cleanup
    if _last_cleanup is not None and now - _last_cleanup < timedelta(hours=1):
        return
    _last_cleanup = now
    from . import file_cleanup

    with db_session() as db:
        file_cleanup.cleanup_orphan_files(db)


async def run_reminder_loop() -> None:
    while True:
        try:
            now = local_now()
            _tick(now)
            _maybe_cleanup(now)
        # Świadome złapanie wszystkiego: pętla nie może umrzeć (przypomnienia
        # przestałyby wychodzić po jednym błędzie przejściowym). Każdy błąd
        # jest jednak policzony (metryka reminder_loop_errors w /api/metrics —
        # próg alertowy w docs/OBSERVABILITY.md) i zalogowany strukturalnie
        # (typ + ramki stosu, bez treści przypomnień ani danych klientów).
        except Exception as exc:  # noqa: BLE001 - pętla nie może umrzeć
            metrics.inc("reminder_loop_errors")
            log_json("reminder_loop_error", level="error", **exception_fields(exc))
        await asyncio.sleep(60)

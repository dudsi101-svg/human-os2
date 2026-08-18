"""Pętla harmonogramu powiadomień (w procesie, co ~60 s).

Od migracji nr 14 pętla NIE ma własnego stanu dedup w pamięci — pracuje
wyłącznie na wspólnym modelu powiadomień (dzik_os.notifications):

1. `plan_day` — materializuje dzisiejsze wystąpienia przypomnień jako
   wiersze SCHEDULED (harmonogram z porą, jednorazowe przypomnienia
   trenera o 08:00, płatności z dzisiejszym terminem), idempotentnie po
   kluczu dedup_key w bazie;
2. `dispatch_due` — doręcza wiersze, których termin (UTC, wyliczony w
   lokalnej strefie odbiorcy) nadszedł; bramki „zadanie już wykonane",
   preferencje i ciche godziny są sprawdzane przy wysyłce.

Restart maszyny niczego nie duplikuje (klucz idempotencji w bazie) ani
nie gubi (wiersz SCHEDULED czeka; nadganianie do notifications.LATE_SEND_MAX).
Strategia i model: docs/POWIADOMIENIA.md.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from . import notifications
from .db import db_session
from .observability import exception_fields, log_json, metrics


def _tick(now_utc: datetime) -> int:
    """Jedno przejście pętli; zwraca liczbę doręczonych (dla testów)."""
    with db_session() as db:
        notifications.plan_day(db, now_utc)
        # Digest trenera: raz w tygodniu, w poniedziałek rano czasu trenera
        # (idempotentnie po kluczu tygodnia — tick co minutę nie mnoży).
        notifications.plan_weekly_digest(db, now_utc)
        sent = notifications.dispatch_due(db, now_utc)
        payloads = [notifications.realtime_payload(n) for n in sent
                    if "center" in (n.channels or "")]
        user_ids = [n.user_id for n in sent if "center" in (n.channels or "")]
    # SSE dopiero PO commicie (db_session commituje przy wyjściu) —
    # zdarzenie nie może wyprzedzić trwałego zapisu.
    for user_id, payload in zip(user_ids, payloads):
        notifications.bus.publish(user_id, payload)
    return len(sent)


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
            now = datetime.now(UTC)
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

"""Przetwarzanie zdarzeń webhook operatora płatności — PRZYGOTOWANA
ARCHITEKTURA (kontrakt przetestowany na NullPaymentProvider; żaden endpoint
HTTP nie jest wystawiony, bo realny operator nie jest podłączony — świadoma
decyzja produktowa, docs/PLATNOSCI.md §Operator).

Gwarancje kontraktu (niezależne od konkretnego operatora):
1. PODPIS NAJPIERW: zdarzenie bez poprawnego podpisu nie jest ani
   przetwarzane, ani zapisywane (niezweryfikowany event_id nie może
   zapychać rejestru idempotencji) — tylko log + metryka.
2. IDEMPOTENCJA: (provider, event_id) jest unikalne; powtórka tego samego
   zdarzenia = DUPLICATE bez jakichkolwiek skutków ubocznych; ten sam
   event_id z INNĄ treścią = CONFLICT (log, brak skutków).
3. ZŁA KOLEJNOŚĆ: zdarzenie z occurred_at starszym niż ostatnie
   PRZETWORZONE zdarzenie tej należności = STALE (zapisane, bez zmiany
   stanu). Dodatkowo stan PAID nigdy nie jest cofany przez zdarzenie
   operatora (spóźniony payment.failed po payment.succeeded = IGNORED).
4. MASZYNA STANÓW: zmiany statusu wyłącznie przez payment_service
   .change_status (historia + audyt); przejście niedozwolone = IGNORED
   z notatką (webhook nie może wywołać 422 u operatora w nieskończonym
   retry — odnotowujemy i odpowiadamy sukcesem).
5. PRZEKIEROWANIE NIEZAUFANE: nic w tym module (ani nigdzie indziej) nie
   czyta parametrów powrotu przeglądarki.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy.orm import Session

from .models import (
    PaymentAttempt,
    PaymentProviderEvent,
    PaymentRecord,
    PaymentSchedule,
    new_id,
    now_iso,
)
from .observability import log_json, metrics
from .payment_service import add_transaction, change_status
from .payment_state import ALLOWED_PAYMENT_TRANSITIONS
from .payments_provider import (
    EVENT_PAYMENT_FAILED,
    EVENT_PAYMENT_STARTED,
    EVENT_PAYMENT_SUCCEEDED,
    PaymentProviderPort,
    WebhookEvent,
    WebhookParseError,
)

# Wyniki przetwarzania (kontrakt testowany w tests/test_payment_webhooks.py).
REJECTED_SIGNATURE = "REJECTED_SIGNATURE"
REJECTED_MALFORMED = "REJECTED_MALFORMED"
DUPLICATE = "DUPLICATE"
CONFLICT = "CONFLICT"
PROCESSED = "PROCESSED"
STALE = "STALE"
IGNORED = "IGNORED"
UNKNOWN_RECORD = "UNKNOWN_RECORD"


@dataclass(frozen=True)
class ProcessResult:
    outcome: str
    detail: str = ""
    event_row_id: str | None = None


def _system_actor(provider_name: str) -> str:
    return f"provider:{provider_name}"


def process_webhook(
    db: Session, provider: PaymentProviderPort, body: bytes, signature: str
) -> ProcessResult:
    """Pełny kontrakt przetwarzania webhooka. Wywołujący robi commit."""
    # 1. Podpis — bez niego nie ufamy niczemu z ciała żądania.
    if not provider.verify_webhook_signature(body, signature):
        metrics.inc("payment_webhook_rejected_signature")
        log_json("payment_webhook_rejected", level="warning",
                 provider=provider.name, reason="bad_signature")
        return ProcessResult(REJECTED_SIGNATURE, "Nieprawidłowy podpis")
    try:
        event = provider.parse_webhook(body)
    except WebhookParseError as exc:
        metrics.inc("payment_webhook_rejected_malformed")
        log_json("payment_webhook_rejected", level="warning",
                 provider=provider.name, reason="malformed")
        return ProcessResult(REJECTED_MALFORMED, str(exc))

    payload_hash = hashlib.sha256(body).hexdigest()

    # 2. Idempotencja po (provider, event_id).
    existing = (
        db.query(PaymentProviderEvent)
        .filter_by(provider=event.provider, event_id=event.event_id)
        .one_or_none()
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            metrics.inc("payment_webhook_conflicts")
            log_json("payment_webhook_conflict", level="warning",
                     provider=provider.name, event_id=event.event_id)
            return ProcessResult(
                CONFLICT, "event_id użyty ponownie z inną treścią", existing.id
            )
        return ProcessResult(DUPLICATE, "Zdarzenie już przetworzone", existing.id)

    def store(outcome: str, note: str = "") -> PaymentProviderEvent:
        row = PaymentProviderEvent(
            id=new_id("PPE"),
            provider=event.provider,
            event_id=event.event_id,
            event_type=event.event_type,
            record_id=event.record_id,
            payload_hash=payload_hash,
            occurred_at=event.occurred_at,
            outcome=outcome,
            note=note or None,
        )
        db.add(row)
        return row

    record = db.get(PaymentRecord, event.record_id)
    if record is None:
        row = store(UNKNOWN_RECORD, "Nieznana należność")
        return ProcessResult(UNKNOWN_RECORD, "Nieznana należność", row.id)
    schedule = db.get(PaymentSchedule, record.schedule_id)
    assert schedule is not None

    # 3. Zła kolejność: nic starszego niż ostatnie PRZETWORZONE zdarzenie
    # tej należności nie zmienia stanu.
    last_processed = (
        db.query(PaymentProviderEvent)
        .filter_by(record_id=record.id, outcome=PROCESSED)
        .order_by(PaymentProviderEvent.occurred_at.desc())
        .first()
    )
    if last_processed is not None and event.occurred_at < (
        last_processed.occurred_at or ""
    ):
        row = store(STALE, "Zdarzenie starsze niż ostatnie przetworzone")
        return ProcessResult(STALE, "Zła kolejność — stan bez zmian", row.id)

    outcome, detail = _apply(db, record, schedule, event)
    row = store(outcome, detail)
    return ProcessResult(outcome, detail, row.id)


def _attempt(db: Session, event: WebhookEvent, record: PaymentRecord) -> PaymentAttempt:
    attempt = None
    if event.session_id:
        attempt = (
            db.query(PaymentAttempt)
            .filter_by(record_id=record.id, provider=event.provider,
                       provider_session_id=event.session_id)
            .one_or_none()
        )
    if attempt is None:
        attempt = PaymentAttempt(
            id=new_id("PAT"), record_id=record.id, provider=event.provider,
            provider_session_id=event.session_id,
        )
        db.add(attempt)
    return attempt


def _apply(
    db: Session,
    record: PaymentRecord,
    schedule: PaymentSchedule,
    event: WebhookEvent,
) -> tuple[str, str]:
    actor = _system_actor(event.provider)
    # PAID nigdy nie jest cofane zdarzeniem operatora.
    if record.status == "PAID" and event.event_type != EVENT_PAYMENT_SUCCEEDED:
        return IGNORED, "Należność już opłacona — stan nie jest cofany"
    if event.currency is not None and event.currency != record.currency:
        return IGNORED, (
            f"Waluta zdarzenia ({event.currency}) różna od waluty "
            f"należności ({record.currency})"
        )

    if event.event_type == EVENT_PAYMENT_STARTED:
        if "IN_PROGRESS" not in ALLOWED_PAYMENT_TRANSITIONS.get(record.status, set()):
            return IGNORED, f"Przejście {record.status} → IN_PROGRESS niedozwolone"
        attempt = _attempt(db, event, record)
        attempt.status = "STARTED"
        attempt.updated_at = now_iso()
        change_status(db, record=record, schedule=schedule,
                      to_status="IN_PROGRESS", actor_id=actor,
                      reason=f"Operator: {event.event_type} ({event.event_id})")
        return PROCESSED, "Rozpoczęto próbę płatności"

    if event.event_type == EVENT_PAYMENT_SUCCEEDED:
        if record.status == "PAID":
            return IGNORED, "Należność już opłacona"
        if "PAID" not in ALLOWED_PAYMENT_TRANSITIONS.get(record.status, set()):
            return IGNORED, f"Przejście {record.status} → PAID niedozwolone"
        attempt = _attempt(db, event, record)
        attempt.status = "SUCCEEDED"
        attempt.updated_at = now_iso()
        tx = add_transaction(
            db, record=record, schedule=schedule, kind="PROVIDER_PAYMENT",
            amount_cents=event.amount_cents or record.amount_cents,
            currency=event.currency, created_by=actor,
            provider=event.provider, provider_event_id=event.event_id,
        )
        change_status(db, record=record, schedule=schedule, to_status="PAID",
                      actor_id=actor, transaction_id=tx.id,
                      reason=f"Operator: {event.event_type} ({event.event_id})")
        record.paid_at = event.occurred_at
        return PROCESSED, "Płatność operatora zaksięgowana"

    if event.event_type == EVENT_PAYMENT_FAILED:
        if "FAILED" not in ALLOWED_PAYMENT_TRANSITIONS.get(record.status, set()):
            return IGNORED, f"Przejście {record.status} → FAILED niedozwolone"
        attempt = _attempt(db, event, record)
        attempt.status = "FAILED"
        attempt.updated_at = now_iso()
        change_status(db, record=record, schedule=schedule, to_status="FAILED",
                      actor_id=actor,
                      reason=f"Operator: {event.event_type} ({event.event_id})")
        return PROCESSED, "Nieudana próba płatności"

    return IGNORED, f"Nieobsługiwany typ zdarzenia: {event.event_type}"

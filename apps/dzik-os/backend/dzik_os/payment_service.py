"""Wspólna logika modułu płatności (router + zdarzenia operatora).

Zasady (Konstytucja Human OS + docs/PLATNOSCI.md):
* każda zmiana statusu należności przechodzi przez change_status() —
  walidacja maszyną stanów, wpis w historii per rekord ORAZ w łańcuchu
  audytu (nigdy cichy flip pola),
* przepływy pieniędzy są append-only (PaymentTransaction); cofnięcie
  omyłki = transakcja REVERSAL, nigdy edycja ani DELETE,
* kwoty wyłącznie w groszach (int) z kodem waluty przy każdej kwocie;
  waluta transakcji musi się zgadzać z walutą należności (422).
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .hos_bridge import record_event
from .models import (
    PaymentRecord,
    PaymentSchedule,
    PaymentStatusChange,
    PaymentTransaction,
    new_id,
    now_iso,
)
from .payment_state import assert_transition


def change_status(
    db: Session,
    *,
    record: PaymentRecord,
    schedule: PaymentSchedule,
    to_status: str,
    actor_id: str,
    reason: str | None = None,
    transaction_id: str | None = None,
) -> PaymentStatusChange:
    """Jedyna ścieżka zmiany statusu należności: walidacja przejścia (422
    przy niedozwolonym), wpis historii per rekord i zdarzenie audytowe."""
    from_status = record.status
    assert_transition(from_status, to_status)
    record.status = to_status
    change = PaymentStatusChange(
        id=new_id("PSH"),
        record_id=record.id,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        transaction_id=transaction_id,
        changed_by=actor_id,
    )
    db.add(change)
    record_event(
        db,
        action="PAYMENT_STATUS_CHANGED",
        actor_id=actor_id,
        subject_ids=[schedule.client_id],
        payload={
            "record_id": record.id, "from": from_status, "to": to_status,
            "reason": reason, "transaction_id": transaction_id,
        },
        summary=f"Płatność {record.due_date}: {from_status} → {to_status}",
    )
    return change


def require_currency_match(record: PaymentRecord, currency: str | None) -> str:
    """Waluta operacji musi się zgadzać z walutą należności — kwot w
    różnych walutach nigdy nie sumujemy ani nie mieszamy w jednym rekordzie."""
    if currency is None or currency == record.currency:
        return record.currency
    raise HTTPException(
        status_code=422,
        detail=(
            f"Waluta operacji ({currency}) różni się od waluty należności "
            f"({record.currency}) — operacja odrzucona."
        ),
    )


def add_transaction(
    db: Session,
    *,
    record: PaymentRecord,
    schedule: PaymentSchedule,
    kind: str,
    amount_cents: int,
    currency: str | None,
    created_by: str,
    document_ref: str | None = None,
    note: str | None = None,
    reverses_transaction_id: str | None = None,
    provider: str | None = None,
    provider_event_id: str | None = None,
) -> PaymentTransaction:
    """Append-only wpis przepływu/korekty + zdarzenie audytowe."""
    tx = PaymentTransaction(
        id=new_id("PTX"),
        record_id=record.id,
        kind=kind,
        amount_cents=amount_cents,
        currency=require_currency_match(record, currency),
        document_ref=document_ref,
        note=note,
        reverses_transaction_id=reverses_transaction_id,
        provider=provider,
        provider_event_id=provider_event_id,
        created_by=created_by,
    )
    db.add(tx)
    record_event(
        db,
        action="PAYMENT_TRANSACTION_RECORDED",
        actor_id=created_by,
        subject_ids=[schedule.client_id],
        payload={
            "transaction_id": tx.id, "record_id": record.id, "kind": kind,
            "amount_cents": amount_cents, "currency": tx.currency,
            "document_ref": document_ref,
            "reverses_transaction_id": reverses_transaction_id,
            "provider": provider,
        },
        summary=(
            f"Transakcja {kind} {amount_cents / 100:.2f} {tx.currency} "
            f"dla płatności {record.due_date}"
        ),
    )
    return tx


def record_transactions(db: Session, record_id: str) -> list[PaymentTransaction]:
    return (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.record_id == record_id)
        .order_by(PaymentTransaction.created_at, PaymentTransaction.id)
        .all()
    )


def reversed_transaction_ids(txs: list[PaymentTransaction]) -> set[str]:
    return {
        t.reverses_transaction_id for t in txs
        if t.kind == "REVERSAL" and t.reverses_transaction_id
    }


def ledger_totals(txs: list[PaymentTransaction]) -> dict[str, int]:
    """Sumy EFEKTYWNE (transakcje odwrócone REVERSAL-em nie liczą się;
    REVERSAL sam w sobie też nie — para znosi się do zera)."""
    reversed_ids = reversed_transaction_ids(txs)
    paid = refunded = adjustments = 0
    for t in txs:
        if t.kind == "REVERSAL" or t.id in reversed_ids:
            continue
        if t.kind in ("MANUAL_PAYMENT", "PROVIDER_PAYMENT"):
            paid += t.amount_cents
        elif t.kind == "REFUND":
            refunded += t.amount_cents
        elif t.kind == "ADJUSTMENT":
            adjustments += t.amount_cents
    return {"paid": paid, "refunded": refunded, "adjustments": adjustments}


def clear_paid_marks(record: PaymentRecord) -> None:
    """Po korekcie odwracającej płatność bieżący stan wiersza wraca do
    'nieopłacona' — pełny ślad (kto/kiedy oznaczył i cofnął) pozostaje w
    transakcjach, historii statusów i audycie."""
    record.paid_at = None
    record.marked_by = None
    record.marked_at = None
    record.note = None


def mark_paid_now(
    record: PaymentRecord, *, actor_id: str, note: str | None
) -> None:
    now = now_iso()
    record.paid_at = now
    record.marked_by = actor_id
    record.marked_at = now
    record.note = note

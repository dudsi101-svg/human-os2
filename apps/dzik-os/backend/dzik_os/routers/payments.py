"""Płatności: harmonogram należności vs faktycznie zarejestrowane
transakcje (docs/PLATNOSCI.md).

* Należność (PaymentRecord) ma kontrolowaną maszynę stanów
  (payment_state) — nieprawidłowe przejście = 422, egzekwowane wyłącznie
  tutaj (frontend nic nie wymusza).
* „Opłacona" ustawia się wyłącznie dedykowanym endpointem mark-paid
  (transakcja ręczna trenera: kto, kiedy, opcjonalny numer dokumentu),
  z idempotencją P11; zwroty/korekty/cofnięcia analogicznie — zawsze
  jako nowe wpisy, nigdy edycja.
* Dane finansowe klienta są niedostępne dla innych (404, logowana odmowa);
  każda zmiana przechodzi przez audyt Human OS.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import notifications
from ..authz import DOMAIN_COLLABORATION, deny, require_owned_resource, resolve_client_access
from ..dates import local_today
from ..db import get_db
from ..hos_bridge import record_event
from ..idempotency import replay_response, request_fingerprint, store_response
from ..models import (
    PaymentRecord,
    PaymentSchedule,
    PaymentStatusChange,
    PaymentTransaction,
    User,
    new_id,
)
from ..payment_service import (
    add_transaction,
    change_status,
    clear_paid_marks,
    ledger_totals,
    mark_paid_now,
    record_transactions,
    reversed_transaction_ids,
)
from ..payment_state import MARKABLE_AS_PAID, assert_transition, effective_status
from ..payments_provider import provider
from ..schemas import (
    PaymentAdjustIn,
    PaymentMarkPaidIn,
    PaymentRefundIn,
    PaymentReverseIn,
    PaymentScheduleIn,
    PaymentStatusIn,
)
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["payments"])


def _owned_record(
    db: Session, coach: User, record_id: str
) -> tuple[PaymentRecord, PaymentSchedule]:
    """Rekord musi istnieć I należeć do harmonogramu tego trenera.
    Cudzy rekord = logowana odmowa 404 (IDOR)."""
    record = db.get(PaymentRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    schedule = db.get(PaymentSchedule, record.schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if schedule.coach_id != coach.id:
        deny(coach.id, f"payment_record:{record_id}")
    return record, schedule


def _display_names(db: Session, ids: set[str]) -> dict[str, str]:
    ids = {i for i in ids if i and not i.startswith("provider:")}
    if not ids:
        return {}
    rows = db.query(User).filter(User.id.in_(ids)).all()
    return {u.id: u.display_name for u in rows}


def _serialize_transactions(
    txs: list[PaymentTransaction], names: dict[str, str]
) -> list[dict]:
    reversed_ids = reversed_transaction_ids(txs)
    return [
        {
            "id": t.id,
            "kind": t.kind,
            "amount_cents": t.amount_cents,
            "currency": t.currency,
            "document_ref": t.document_ref,
            "note": t.note,
            "reverses_transaction_id": t.reverses_transaction_id,
            "reversed": t.id in reversed_ids,
            "provider": t.provider,
            "created_by": t.created_by,
            "created_by_name": names.get(t.created_by),
            "created_at": t.created_at,
        }
        for t in txs
    ]


@router.post("/payments/schedules", status_code=201)
def create_schedule(
    body: PaymentScheduleIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    # Płatności nie są danymi zdrowotnymi — wystarczy aktywna relacja.
    resolve_client_access(db, coach, body.client_id, action="write", domain=DOMAIN_COLLABORATION)
    schedule = PaymentSchedule(
        id=new_id("PSC"),
        client_id=body.client_id,
        coach_id=coach.id,
        package_name=body.package_name,
        amount_cents=body.amount_cents,
        currency=body.currency,
        period=body.period,
        external_link=body.external_link,
        created_by=coach.id,
    )
    db.add(schedule)
    record = PaymentRecord(
        id=new_id("PAY"),
        schedule_id=schedule.id,
        due_date=body.first_due_date,
        amount_cents=body.amount_cents,
        currency=body.currency,
    )
    db.add(record)
    record_event(
        db,
        action="PAYMENT_SCHEDULE_CREATED",
        actor_id=coach.id,
        subject_ids=[body.client_id],
        payload={"schedule_id": schedule.id, "package": body.package_name,
                 "amount_cents": body.amount_cents, "period": body.period,
                 "first_due_date": body.first_due_date},
        summary=f"Pakiet '{body.package_name}': {body.amount_cents/100:.2f} "
        f"{body.currency}, termin {body.first_due_date}",
    )
    db.commit()
    return {"schedule_id": schedule.id, "record_id": record.id}


@router.get("/clients/{client_id}/payments")
def client_payments(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, domain=DOMAIN_COLLABORATION)
    today = local_today().isoformat()
    schedules = (
        db.query(PaymentSchedule).filter(PaymentSchedule.client_id == client_id).all()
    )
    out = []
    for s in schedules:
        records = (
            db.query(PaymentRecord)
            .filter(PaymentRecord.schedule_id == s.id)
            .order_by(PaymentRecord.due_date.desc())
            .all()
        )
        txs_by_record: dict[str, list[PaymentTransaction]] = {}
        name_ids: set[str] = set()
        for r in records:
            txs = record_transactions(db, r.id)
            txs_by_record[r.id] = txs
            name_ids.update(t.created_by for t in txs)
            if r.marked_by:
                name_ids.add(r.marked_by)
        names = _display_names(db, name_ids)
        out.append(
            {
                "schedule_id": s.id,
                "package_name": s.package_name,
                "amount_cents": s.amount_cents,
                "currency": s.currency,
                "period": s.period,
                "external_link": s.external_link,
                "status": s.status,
                "records": [
                    {
                        "id": r.id, "due_date": r.due_date,
                        "amount_cents": r.amount_cents, "currency": r.currency,
                        "status": r.status,
                        # Prezentacyjny status z zaległością liczoną po
                        # LOKALNEJ dacie (spójnie w obu widokach).
                        "effective_status": effective_status(
                            r.status, r.due_date, today
                        ),
                        "paid_at": r.paid_at, "note": r.note,
                        "marked_by": r.marked_by,
                        "marked_by_name": names.get(r.marked_by or ""),
                        "marked_at": r.marked_at,
                        "transactions": _serialize_transactions(
                            txs_by_record[r.id], names
                        ),
                        "payment_link": provider.payment_link(
                            record_id=r.id, amount_cents=r.amount_cents,
                            currency=r.currency, description=s.package_name,
                        ) or s.external_link,
                    }
                    for r in records
                ],
            }
        )
    return {"schedules": out, "provider": provider.name}


@router.post("/payments/records/{record_id}/status")
def set_payment_status(
    record_id: str,
    body: PaymentStatusIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Statusy ADMINISTRACYJNE (PENDING/OVERDUE/CANCELLED). „Opłacona"
    i zwroty — wyłącznie dedykowane endpointy z transakcją."""
    record, schedule = _owned_record(db, coach, record_id)
    change_status(
        db, record=record, schedule=schedule, to_status=body.status,
        actor_id=coach.id, reason=body.note,
    )
    if body.note is not None:
        record.note = body.note
    db.commit()
    return {"ok": True, "status": body.status}


@router.post("/payments/records/{record_id}/mark-paid")
def mark_paid(
    record_id: str,
    body: PaymentMarkPaidIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Transakcja ręczna: trener potwierdza otrzymanie środków (kto i kiedy
    widoczne w UI). Idempotencja P11: powtórka z tym samym kluczem zwraca
    zapisany wynik — bez drugiej transakcji (ochrona przed podwójnym
    kliknięciem); ponowne oznaczenie bez klucza = 422 (PAID → PAID nie
    istnieje w tablicy przejść)."""
    record, schedule = _owned_record(db, coach, record_id)
    fingerprint = request_fingerprint(body.model_dump())
    if body.idempotency_key:
        replayed = replay_response(
            db, user_id=coach.id, operation="payment_mark_paid",
            key=body.idempotency_key, fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed
    if record.status not in MARKABLE_AS_PAID:
        # Podwójna wpłata (PAID → PAID) i powrót do PAID po zwrocie
        # (wyłącznie korektą odwracającą zwrot) — zawsze jawne 422.
        raise HTTPException(
            status_code=422,
            detail=f"Niedozwolone przejście statusu płatności: {record.status} → PAID",
        )
    assert_transition(record.status, "PAID")
    tx = add_transaction(
        db, record=record, schedule=schedule, kind="MANUAL_PAYMENT",
        amount_cents=body.amount_cents or record.amount_cents,
        currency=body.currency, created_by=coach.id,
        document_ref=body.document_ref, note=body.note,
    )
    change_status(
        db, record=record, schedule=schedule, to_status="PAID",
        actor_id=coach.id, reason=body.note, transaction_id=tx.id,
    )
    mark_paid_now(record, actor_id=coach.id, note=body.note)
    response = {"ok": True, "status": "PAID", "transaction_id": tx.id}
    if body.idempotency_key:
        store_response(
            db, user_id=coach.id, operation="payment_mark_paid",
            key=body.idempotency_key, fingerprint=fingerprint, response=response,
        )
    db.commit()
    return response


@router.post("/payments/records/{record_id}/refund")
def refund(
    record_id: str,
    body: PaymentRefundIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Zwrot pełny lub częściowy — nowa transakcja REFUND; suma zwrotów
    nigdy nie przekracza sumy zarejestrowanych wpłat."""
    record, schedule = _owned_record(db, coach, record_id)
    fingerprint = request_fingerprint(body.model_dump())
    if body.idempotency_key:
        replayed = replay_response(
            db, user_id=coach.id, operation="payment_refund",
            key=body.idempotency_key, fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed
    txs = record_transactions(db, record.id)
    totals = ledger_totals(txs)
    # Rekordy PAID sprzed migracji nr 15 nie mają transakcji — podstawą
    # zwrotu jest wtedy kwota należności (bez fabrykowania historii).
    paid_base = totals["paid"]
    if paid_base == 0 and record.status in ("PAID", "PARTIALLY_REFUNDED", "REFUNDED"):
        paid_base = record.amount_cents
    refundable = paid_base - totals["refunded"]
    if record.status not in ("PAID", "PARTIALLY_REFUNDED"):
        raise HTTPException(
            status_code=422,
            detail=f"Zwrot możliwy tylko dla opłaconej należności "
                   f"(status: {record.status})",
        )
    if body.amount_cents > refundable:
        raise HTTPException(
            status_code=422,
            detail=f"Kwota zwrotu ({body.amount_cents} gr) przekracza kwotę "
                   f"możliwą do zwrotu ({refundable} gr)",
        )
    target = (
        "REFUNDED" if totals["refunded"] + body.amount_cents >= paid_base
        else "PARTIALLY_REFUNDED"
    )
    assert_transition(record.status, target)
    tx = add_transaction(
        db, record=record, schedule=schedule, kind="REFUND",
        amount_cents=body.amount_cents, currency=body.currency,
        created_by=coach.id, document_ref=body.document_ref, note=body.note,
    )
    change_status(
        db, record=record, schedule=schedule, to_status=target,
        actor_id=coach.id, reason=body.note, transaction_id=tx.id,
    )
    response = {"ok": True, "status": target, "transaction_id": tx.id}
    if body.idempotency_key:
        store_response(
            db, user_id=coach.id, operation="payment_refund",
            key=body.idempotency_key, fingerprint=fingerprint, response=response,
        )
    db.commit()
    return response


@router.post("/payments/records/{record_id}/adjust")
def adjust(
    record_id: str,
    body: PaymentAdjustIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Korekta księgowa (np. rabat, błędnie zaksięgowana kwota) — nowy wpis
    z obowiązkowym powodem; status należności bez zmian."""
    record, schedule = _owned_record(db, coach, record_id)
    fingerprint = request_fingerprint(body.model_dump())
    if body.idempotency_key:
        replayed = replay_response(
            db, user_id=coach.id, operation="payment_adjust",
            key=body.idempotency_key, fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed
    tx = add_transaction(
        db, record=record, schedule=schedule, kind="ADJUSTMENT",
        amount_cents=body.amount_cents, currency=body.currency,
        created_by=coach.id, document_ref=body.document_ref, note=body.reason,
    )
    response = {"ok": True, "transaction_id": tx.id}
    if body.idempotency_key:
        store_response(
            db, user_id=coach.id, operation="payment_adjust",
            key=body.idempotency_key, fingerprint=fingerprint, response=response,
        )
    db.commit()
    return response


@router.post("/payments/transactions/{transaction_id}/reverse")
def reverse_transaction(
    transaction_id: str,
    body: PaymentReverseIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Cofnięcie omyłkowej transakcji BEZ usuwania śladu: nowa transakcja
    REVERSAL wskazująca odwracaną; status należności jest wyliczany na nowo
    z efektywnej księgi (np. cofnięcie omyłkowego „opłacona" wraca do
    PENDING/OVERDUE zależnie od terminu)."""
    tx = db.get(PaymentTransaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    record = db.get(PaymentRecord, tx.record_id)
    schedule = db.get(PaymentSchedule, record.schedule_id) if record else None
    if record is None or schedule is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if schedule.coach_id != coach.id:
        deny(coach.id, f"payment_transaction:{transaction_id}")
    if tx.kind == "REVERSAL":
        raise HTTPException(
            status_code=422, detail="Nie można odwrócić korekty odwracającej"
        )
    txs = record_transactions(db, record.id)
    if tx.id in reversed_transaction_ids(txs):
        raise HTTPException(
            status_code=422, detail="Ta transakcja została już odwrócona"
        )
    if tx.kind in ("MANUAL_PAYMENT", "PROVIDER_PAYMENT") and ledger_totals(txs)["refunded"] > 0:
        raise HTTPException(
            status_code=422,
            detail="Najpierw odwróć zwroty powiązane z tą wpłatą",
        )
    fingerprint = request_fingerprint({**body.model_dump(), "transaction_id": tx.id})
    if body.idempotency_key:
        replayed = replay_response(
            db, user_id=coach.id, operation="payment_reverse",
            key=body.idempotency_key, fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed
    reversal = add_transaction(
        db, record=record, schedule=schedule, kind="REVERSAL",
        amount_cents=tx.amount_cents, currency=tx.currency,
        created_by=coach.id, note=body.reason, reverses_transaction_id=tx.id,
    )
    record_event(
        db,
        action="PAYMENT_TRANSACTION_REVERSED",
        actor_id=coach.id,
        subject_ids=[schedule.client_id],
        payload={"transaction_id": tx.id, "reversal_id": reversal.id,
                 "kind": tx.kind, "amount_cents": tx.amount_cents,
                 "currency": tx.currency, "reason": body.reason},
        summary=f"Cofnięcie transakcji {tx.kind} dla płatności {record.due_date}",
    )
    # Nowy status z efektywnej księgi (po odwróceniu). Sesja ma
    # autoflush=False — flush, żeby zapytanie widziało wpis REVERSAL.
    db.flush()
    txs = record_transactions(db, record.id)
    totals = ledger_totals(txs)
    target: str | None = None
    if tx.kind in ("MANUAL_PAYMENT", "PROVIDER_PAYMENT"):
        if totals["paid"] <= 0 and record.status in ("PAID",):
            today = local_today().isoformat()
            target = "OVERDUE" if record.due_date < today else "PENDING"
    elif tx.kind == "REFUND" and record.status in ("PARTIALLY_REFUNDED", "REFUNDED"):
        paid_base = totals["paid"] or record.amount_cents
        target = (
            "PAID" if totals["refunded"] == 0
            else "PARTIALLY_REFUNDED" if totals["refunded"] < paid_base
            else None
        )
        if target == record.status:
            target = None
    if target is not None:
        assert_transition(record.status, target)
        change_status(
            db, record=record, schedule=schedule, to_status=target,
            actor_id=coach.id, reason=f"Korekta odwracająca: {body.reason}",
            transaction_id=reversal.id,
        )
        if target in ("PENDING", "OVERDUE"):
            clear_paid_marks(record)
    response = {"ok": True, "status": record.status, "reversal_id": reversal.id}
    if body.idempotency_key:
        store_response(
            db, user_id=coach.id, operation="payment_reverse",
            key=body.idempotency_key, fingerprint=fingerprint, response=response,
        )
    db.commit()
    return response


@router.get("/payments/records/{record_id}/history")
def record_history(
    record_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Pełna historia jednego rekordu: przejścia statusu + transakcje.
    Dostęp: trener-właściciel harmonogramu albo sam klient; inni — 404."""
    record = db.get(PaymentRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    schedule = db.get(PaymentSchedule, record.schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    # Strony należności: sam klient albo trener-właściciel harmonogramu
    # (nawet po zakończeniu relacji to nadal jego ewidencja finansowa).
    if user.id != schedule.client_id and user.id != schedule.coach_id:
        deny(user.id, f"payment_record:{record_id}")
    changes = (
        db.query(PaymentStatusChange)
        .filter(PaymentStatusChange.record_id == record.id)
        .order_by(PaymentStatusChange.changed_at, PaymentStatusChange.id)
        .all()
    )
    txs = record_transactions(db, record.id)
    names = _display_names(
        db,
        {c.changed_by for c in changes} | {t.created_by for t in txs}
        | ({record.marked_by} if record.marked_by else set()),
    )
    return {
        "record": {
            "id": record.id, "due_date": record.due_date,
            "amount_cents": record.amount_cents, "currency": record.currency,
            "status": record.status, "paid_at": record.paid_at,
            "marked_by": record.marked_by,
            "marked_by_name": names.get(record.marked_by or ""),
            "marked_at": record.marked_at, "note": record.note,
        },
        "status_changes": [
            {
                "id": c.id, "from_status": c.from_status, "to_status": c.to_status,
                "reason": c.reason, "transaction_id": c.transaction_id,
                "changed_by": c.changed_by,
                "changed_by_name": names.get(c.changed_by),
                "changed_at": c.changed_at,
            }
            for c in changes
        ],
        "transactions": _serialize_transactions(txs, names),
    }


@router.get("/payments/reconciliation")
def reconciliation(
    month: str | None = None,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Raport pojednania: należności vs zarejestrowane transakcje/korekty
    per okres (miesiąc terminu płatności). Dziś „operator" = adnotacje
    ręczne trenera; format (source per wiersz, sumy per waluta) jest gotowy
    na przyszłego operatora online."""
    if month is None:
        month = local_today().isoformat()[:7]
    if len(month) != 7 or month[4] != "-" or not (month[:4] + month[5:]).isdigit():
        raise HTTPException(status_code=422, detail="Okres w formacie RRRR-MM")
    rows = (
        db.query(PaymentRecord, PaymentSchedule)
        .join(PaymentSchedule, PaymentRecord.schedule_id == PaymentSchedule.id)
        .filter(
            PaymentSchedule.coach_id == coach.id,
            PaymentRecord.due_date.like(f"{month}-%"),
        )
        .order_by(PaymentRecord.due_date, PaymentRecord.id)
        .all()
    )
    names = _display_names(db, {s.client_id for _, s in rows})
    items = []
    summary: dict[str, dict[str, int]] = {}
    for record, schedule in rows:
        txs = record_transactions(db, record.id)
        totals = ledger_totals(txs)
        active_kinds = {
            t.kind for t in txs
            if t.kind != "REVERSAL" and t.id not in reversed_transaction_ids(txs)
        }
        legacy_mark = (
            record.status in ("PAID", "PARTIALLY_REFUNDED", "REFUNDED")
            and totals["paid"] == 0
        )
        collected = totals["paid"] if not legacy_mark else record.amount_cents
        expected = 0 if record.status == "CANCELLED" else record.amount_cents
        balance = collected - totals["refunded"] + totals["adjustments"]
        source = (
            "LEGACY" if legacy_mark
            else "NONE" if not active_kinds
            else "PROVIDER" if active_kinds <= {"PROVIDER_PAYMENT", "REFUND", "ADJUSTMENT"}
            and "PROVIDER_PAYMENT" in active_kinds
            else "MANUAL" if "PROVIDER_PAYMENT" not in active_kinds
            else "MIXED"
        )
        items.append({
            "record_id": record.id,
            "client_id": schedule.client_id,
            "client_name": names.get(schedule.client_id),
            "package_name": schedule.package_name,
            "due_date": record.due_date,
            "status": record.status,
            "currency": record.currency,
            "expected_cents": expected,
            "collected_cents": collected,
            "refunded_cents": totals["refunded"],
            "adjustments_cents": totals["adjustments"],
            "balance_cents": balance,
            "difference_cents": balance - expected,
            "source": source,
            "legacy_mark": legacy_mark,
        })
        cur = summary.setdefault(record.currency, {
            "expected_cents": 0, "collected_cents": 0, "refunded_cents": 0,
            "adjustments_cents": 0, "balance_cents": 0, "difference_cents": 0,
            "records": 0, "legacy_marks": 0,
        })
        cur["expected_cents"] += expected
        cur["collected_cents"] += collected
        cur["refunded_cents"] += totals["refunded"]
        cur["adjustments_cents"] += totals["adjustments"]
        cur["balance_cents"] += balance
        cur["difference_cents"] += balance - expected
        cur["records"] += 1
        cur["legacy_marks"] += 1 if legacy_mark else 0
    return {"month": month, "provider": provider.name,
            "records": items, "summary_by_currency": summary}


@router.post("/payments/schedules/{schedule_id}/records", status_code=201)
def add_payment_record(
    schedule_id: str,
    due_date: str,
    planned: bool = False,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    schedule = require_owned_resource(
        db.get(PaymentSchedule, schedule_id), actor=coach,
        resource=f"payment_schedule:{schedule_id}",
    )
    record = PaymentRecord(
        id=new_id("PAY"),
        schedule_id=schedule.id,
        due_date=due_date,
        amount_cents=schedule.amount_cents,
        currency=schedule.currency,
        # PLANNED = przyszła rata (jeszcze nie wymagalna, bez przypomnień).
        status="PLANNED" if planned else "PENDING",
    )
    db.add(record)
    # Powiadomienie o nowej pozycji płatności — BEZ kwoty (zasada: kwoty
    # nigdy w powiadomieniach; szczegóły na ekranie Płatności po kliku).
    notification = notifications.notify_now(
        db,
        user_id=schedule.client_id,
        category="PLATNOSC",
        title="Nowa pozycja płatności",
        body=f"Termin: {due_date}. Szczegóły na ekranie Płatności.",
        url="/platnosci",
        dedup_key=f"payment-created:{record.id}",
    )
    db.commit()
    notifications.publish_realtime(notification)
    return {"id": record.id, "status": record.status}

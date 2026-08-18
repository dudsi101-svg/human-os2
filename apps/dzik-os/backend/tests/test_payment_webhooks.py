"""Testy KONTRAKTU webhooków operatora płatności na NullPaymentProvider.

Prawdziwy operator nie jest podłączony (świadoma decyzja — system pozostaje
ewidencją ręczną); te testy przybijają kontrakt przetwarzania zdarzeń
(podpis, idempotencja, powtórki, zła kolejność), zanim jakikolwiek operator
powstanie. docs/PLATNOSCI.md §Operator."""

import json

from conftest import CLIENT_A, COACH, get_user_id, login

from dzik_os import payment_events
from dzik_os.db import db_session
from dzik_os.models import PaymentProviderEvent, PaymentTransaction
from dzik_os.payments_provider import NullPaymentProvider

PROVIDER = NullPaymentProvider(secret="test-webhook-secret")


def _body(record_id: str, event_id: str, event_type: str, occurred_at: str,
          **extra) -> bytes:
    payload = {"event_id": event_id, "event_type": event_type,
               "record_id": record_id, "occurred_at": occurred_at, **extra}
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _process(body: bytes, signature: str | None = None):
    sig = signature if signature is not None else PROVIDER.sign(body)
    with db_session() as db:
        result = payment_events.process_webhook(db, PROVIDER, body, sig)
    return result


def _pending_record(client, hc, client_id) -> str:
    r = client.post("/api/payments/schedules", headers=hc, json={
        "client_id": client_id, "package_name": "Pakiet webhook",
        "amount_cents": 45000, "period": "MONTHLY",
        "first_due_date": "2099-01-01",
    })
    assert r.status_code == 201
    return r.json()["record_id"]


def _status(client, headers, client_id, record_id) -> dict:
    schedules = client.get(f"/api/clients/{client_id}/payments",
                           headers=headers).json()["schedules"]
    return next(r for s in schedules for r in s["records"] if r["id"] == record_id)


def test_signed_success_event_marks_paid_with_provider_transaction(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _pending_record(seeded, hc, id_a)
    body = _body(rec, "evt-001", "payment.succeeded", "2026-08-18T10:00:00+00:00",
                 amount_cents=45000, currency="PLN", session_id="sess-1")
    result = _process(body)
    assert result.outcome == payment_events.PROCESSED
    after = _status(seeded, hc, id_a, rec)
    assert after["status"] == "PAID"
    tx = after["transactions"][0]
    assert tx["kind"] == "PROVIDER_PAYMENT"
    assert tx["provider"] == "null"
    assert tx["amount_cents"] == 45000


def test_replayed_event_is_duplicate_without_side_effects(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _pending_record(seeded, hc, id_a)
    body = _body(rec, "evt-002", "payment.succeeded", "2026-08-18T10:00:00+00:00",
                 amount_cents=45000, currency="PLN")
    assert _process(body).outcome == payment_events.PROCESSED
    assert _process(body).outcome == payment_events.DUPLICATE
    assert _process(body).outcome == payment_events.DUPLICATE
    with db_session() as db:
        txs = db.query(PaymentTransaction).filter_by(record_id=rec).all()
        events = db.query(PaymentProviderEvent).filter_by(record_id=rec).all()
    assert len(txs) == 1  # powtórka NIE tworzy drugiej transakcji
    assert len(events) == 1


def test_bad_signature_is_rejected_and_nothing_is_stored(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _pending_record(seeded, hc, id_a)
    body = _body(rec, "evt-003", "payment.succeeded", "2026-08-18T10:00:00+00:00")
    result = _process(body, signature="0" * 64)
    assert result.outcome == payment_events.REJECTED_SIGNATURE
    assert _status(seeded, hc, id_a, rec)["status"] == "PENDING"
    with db_session() as db:
        # Niezweryfikowany event_id nie zapycha rejestru idempotencji.
        assert db.query(PaymentProviderEvent).count() == 0
        assert db.query(PaymentTransaction).filter_by(record_id=rec).count() == 0


def test_out_of_order_failed_after_succeeded_never_regresses_paid(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _pending_record(seeded, hc, id_a)
    ok = _body(rec, "evt-004", "payment.succeeded", "2026-08-18T10:05:00+00:00",
               amount_cents=45000, currency="PLN")
    late_fail = _body(rec, "evt-005", "payment.failed", "2026-08-18T10:01:00+00:00")
    assert _process(ok).outcome == payment_events.PROCESSED
    result = _process(late_fail)
    assert result.outcome == payment_events.STALE
    assert _status(seeded, hc, id_a, rec)["status"] == "PAID"


def test_failed_with_newer_timestamp_still_never_unpaids(seeded):
    """Nawet zdarzenie NOWSZE niż sukces nie cofa PAID (jawna zasada)."""
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _pending_record(seeded, hc, id_a)
    ok = _body(rec, "evt-006", "payment.succeeded", "2026-08-18T10:00:00+00:00",
               amount_cents=45000, currency="PLN")
    newer_fail = _body(rec, "evt-007", "payment.failed", "2026-08-18T10:30:00+00:00")
    assert _process(ok).outcome == payment_events.PROCESSED
    result = _process(newer_fail)
    assert result.outcome == payment_events.IGNORED
    assert _status(seeded, hc, id_a, rec)["status"] == "PAID"


def test_started_then_failed_then_succeeded_flow(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _pending_record(seeded, hc, id_a)
    assert _process(_body(rec, "e-10", "payment.started",
                          "2026-08-18T09:00:00+00:00",
                          session_id="s-1")).outcome == payment_events.PROCESSED
    assert _status(seeded, hc, id_a, rec)["status"] == "IN_PROGRESS"
    assert _process(_body(rec, "e-11", "payment.failed",
                          "2026-08-18T09:01:00+00:00",
                          session_id="s-1")).outcome == payment_events.PROCESSED
    assert _status(seeded, hc, id_a, rec)["status"] == "FAILED"
    assert _process(_body(rec, "e-12", "payment.succeeded",
                          "2026-08-18T09:10:00+00:00", amount_cents=45000,
                          currency="PLN",
                          session_id="s-2")).outcome == payment_events.PROCESSED
    assert _status(seeded, hc, id_a, rec)["status"] == "PAID"
    # Historia przejść zachowana w całości.
    hist = seeded.get(f"/api/payments/records/{rec}/history", headers=hc).json()
    pairs = [(c["from_status"], c["to_status"]) for c in hist["status_changes"]]
    assert pairs == [("PENDING", "IN_PROGRESS"), ("IN_PROGRESS", "FAILED"),
                     ("FAILED", "PAID")]


def test_same_event_id_with_different_body_is_conflict(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _pending_record(seeded, hc, id_a)
    b1 = _body(rec, "evt-008", "payment.succeeded", "2026-08-18T10:00:00+00:00",
               amount_cents=45000, currency="PLN")
    b2 = _body(rec, "evt-008", "payment.succeeded", "2026-08-18T10:00:00+00:00",
               amount_cents=99999, currency="PLN")
    assert _process(b1).outcome == payment_events.PROCESSED
    assert _process(b2).outcome == payment_events.CONFLICT
    with db_session() as db:
        txs = db.query(PaymentTransaction).filter_by(record_id=rec).all()
    assert [t.amount_cents for t in txs] == [45000]


def test_currency_mismatch_event_is_ignored(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _pending_record(seeded, hc, id_a)  # PLN
    body = _body(rec, "evt-009", "payment.succeeded", "2026-08-18T10:00:00+00:00",
                 amount_cents=45000, currency="EUR")
    result = _process(body)
    assert result.outcome == payment_events.IGNORED
    assert _status(seeded, hc, id_a, rec)["status"] == "PENDING"


def test_unknown_record_and_malformed_body(seeded):
    body = _body("HOS-PAY-NIEISTNIEJE", "evt-010", "payment.succeeded",
                 "2026-08-18T10:00:00+00:00")
    assert _process(body).outcome == payment_events.UNKNOWN_RECORD
    # Powtórka nieznanego rekordu też jest idempotentna.
    assert _process(body).outcome == payment_events.DUPLICATE
    bad = b"nie-json"
    assert _process(bad).outcome == payment_events.REJECTED_MALFORMED
    missing = json.dumps({"event_id": "x"}).encode()
    assert _process(missing).outcome == payment_events.REJECTED_MALFORMED

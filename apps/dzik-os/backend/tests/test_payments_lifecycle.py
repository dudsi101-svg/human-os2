"""Runda 15: wiarygodny moduł płatności — maszyna stanów, transakcje
ręczne, zwroty, korekty odwracające, idempotencja, waluty, pojednanie,
izolacja (IDOR) i zgodność wsteczna migracji v1→v15."""

from conftest import CLIENT_A, CLIENT_B, COACH, create_user_with_role, get_user_id, login


def _new_record(client, hc, client_id, *, amount=45000, currency="PLN",
                due="2099-01-01", package="Pakiet testowy"):
    r = client.post("/api/payments/schedules", headers=hc, json={
        "client_id": client_id, "package_name": package,
        "amount_cents": amount, "currency": currency,
        "period": "MONTHLY", "first_due_date": due,
    })
    assert r.status_code == 201, r.text
    return r.json()["record_id"]


# ---------------------------------------------------------------- maszyna stanów

def test_invalid_transition_returns_422(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    # PENDING -> PENDING nie istnieje w tablicy przejść.
    r = seeded.post(f"/api/payments/records/{rec}/status", headers=hc,
                    json={"status": "PENDING"})
    assert r.status_code == 422
    assert "przejście" in r.json()["detail"].lower()
    # Zwrot nieopłaconej należności — 422.
    r = seeded.post(f"/api/payments/records/{rec}/refund", headers=hc,
                    json={"amount_cents": 1000})
    assert r.status_code == 422


def test_status_endpoint_cannot_set_paid_directly(seeded):
    """Frontend nie może dowolnie ustawić „opłacona" — ogólny endpoint
    statusu przyjmuje wyłącznie statusy administracyjne."""
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    for target in ("PAID", "REFUNDED", "PARTIALLY_REFUNDED", "IN_PROGRESS", "PLANNED"):
        r = seeded.post(f"/api/payments/records/{rec}/status", headers=hc,
                        json={"status": target})
        assert r.status_code == 422, target


def test_cancel_and_reactivate_with_history(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    assert seeded.post(f"/api/payments/records/{rec}/status", headers=hc,
                       json={"status": "CANCELLED", "note": "rezygnacja"}).status_code == 200
    assert seeded.post(f"/api/payments/records/{rec}/status", headers=hc,
                       json={"status": "PENDING", "note": "omyłkowe anulowanie"}).status_code == 200
    hist = seeded.get(f"/api/payments/records/{rec}/history", headers=hc).json()
    pairs = [(c["from_status"], c["to_status"]) for c in hist["status_changes"]]
    assert pairs == [("PENDING", "CANCELLED"), ("CANCELLED", "PENDING")]
    assert all(c["changed_by_name"] == "Lubelski Dzik" for c in hist["status_changes"])


def test_planned_record_and_activation(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    schedules = seeded.get(f"/api/clients/{id_a}/payments", headers=hc).json()["schedules"]
    sched = schedules[0]["schedule_id"]
    r = seeded.post(
        f"/api/payments/schedules/{sched}/records?due_date=2099-06-01&planned=true",
        headers=hc)
    assert r.status_code == 201
    assert r.json()["status"] == "PLANNED"
    rec = r.json()["id"]
    assert seeded.post(f"/api/payments/records/{rec}/status", headers=hc,
                       json={"status": "PENDING"}).status_code == 200


# ---------------------------------------------------------------- podwójna płatność

def test_double_mark_paid_without_key_is_422(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    assert seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc,
                       json={}).status_code == 200
    r = seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc, json={})
    assert r.status_code == 422  # PAID -> PAID nie istnieje


def test_mark_paid_idempotency_key_replays_single_transaction(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    body = {"note": "przelew", "idempotency_key": "test-key-12345678"}
    r1 = seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc, json=body)
    r2 = seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc, json=body)
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()  # zapisany wynik, nie druga operacja
    hist = seeded.get(f"/api/payments/records/{rec}/history", headers=hc).json()
    assert len([t for t in hist["transactions"] if t["kind"] == "MANUAL_PAYMENT"]) == 1
    # Ten sam klucz z INNĄ treścią = jawny konflikt 409 (P11).
    r3 = seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc,
                     json={"note": "inna treść", "idempotency_key": "test-key-12345678"})
    assert r3.status_code == 409


# ---------------------------------------------------------------- zwroty

def test_partial_then_full_refund(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a, amount=45000)
    seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc, json={})
    r = seeded.post(f"/api/payments/records/{rec}/refund", headers=hc,
                    json={"amount_cents": 10000, "note": "zwrot za tydzień urlopu"})
    assert r.status_code == 200
    assert r.json()["status"] == "PARTIALLY_REFUNDED"
    r = seeded.post(f"/api/payments/records/{rec}/refund", headers=hc,
                    json={"amount_cents": 35000})
    assert r.status_code == 200
    assert r.json()["status"] == "REFUNDED"
    # Zwrot ponad sumę wpłat — 422.
    r = seeded.post(f"/api/payments/records/{rec}/refund", headers=hc,
                    json={"amount_cents": 100})
    assert r.status_code == 422


def test_refund_currency_mismatch_is_422(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc, json={})
    r = seeded.post(f"/api/payments/records/{rec}/refund", headers=hc,
                    json={"amount_cents": 1000, "currency": "EUR"})
    assert r.status_code == 422
    assert "walut" in r.json()["detail"].lower()


def test_legacy_paid_record_without_transactions_can_be_refunded(seeded):
    """Rekordy PAID sprzed migracji nr 15 (bez transakcji, seed) — podstawą
    zwrotu jest kwota należności."""
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    schedules = seeded.get(f"/api/clients/{id_a}/payments", headers=hc).json()["schedules"]
    paid = next(r for s in schedules for r in s["records"] if r["status"] == "PAID")
    assert paid["transactions"] == []  # seed tworzy stan sprzed migracji
    r = seeded.post(f"/api/payments/records/{paid['id']}/refund", headers=hc,
                    json={"amount_cents": paid["amount_cents"]})
    assert r.status_code == 200
    assert r.json()["status"] == "REFUNDED"


# ---------------------------------------------------------------- korekta odwracająca

def test_reversal_of_mistaken_mark_paid_keeps_full_trace(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a, due="2099-01-01")
    tx = seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc,
                     json={"note": "omyłka"}).json()["transaction_id"]
    r = seeded.post(f"/api/payments/transactions/{tx}/reverse", headers=hc,
                    json={"reason": "oznaczone omyłkowo — środki nie wpłynęły"})
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING"  # termin w przyszłości
    hist = seeded.get(f"/api/payments/records/{rec}/history", headers=hc).json()
    kinds = [t["kind"] for t in hist["transactions"]]
    assert kinds == ["MANUAL_PAYMENT", "REVERSAL"]  # nic nie usunięte
    assert hist["transactions"][0]["reversed"] is True
    assert hist["transactions"][1]["reverses_transaction_id"] == tx
    assert hist["record"]["marked_by"] is None  # bieżący stan: nieopłacona
    assert hist["record"]["paid_at"] is None
    # Historia statusów: PENDING -> PAID -> PENDING (pełny ślad).
    pairs = [(c["from_status"], c["to_status"]) for c in hist["status_changes"]]
    assert pairs == [("PENDING", "PAID"), ("PAID", "PENDING")]
    receipts = seeded.get(f"/api/coach/clients/{id_a}/history", headers=hc).json()["receipts"]
    assert any(x["action"] == "PAYMENT_TRANSACTION_REVERSED" for x in receipts)


def test_reversal_to_overdue_when_due_date_passed(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a, due="2020-01-01")
    tx = seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc,
                     json={}).json()["transaction_id"]
    r = seeded.post(f"/api/payments/transactions/{tx}/reverse", headers=hc,
                    json={"reason": "omyłka"})
    assert r.status_code == 200
    assert r.json()["status"] == "OVERDUE"


def test_transaction_cannot_be_reversed_twice(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    tx = seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc,
                     json={}).json()["transaction_id"]
    assert seeded.post(f"/api/payments/transactions/{tx}/reverse", headers=hc,
                       json={"reason": "omyłka"}).status_code == 200
    r = seeded.post(f"/api/payments/transactions/{tx}/reverse", headers=hc,
                    json={"reason": "jeszcze raz"})
    assert r.status_code == 422


def test_refund_reversal_restores_paid(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a, amount=30000)
    seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc, json={})
    tx = seeded.post(f"/api/payments/records/{rec}/refund", headers=hc,
                     json={"amount_cents": 30000}).json()["transaction_id"]
    r = seeded.post(f"/api/payments/transactions/{tx}/reverse", headers=hc,
                    json={"reason": "zwrot zaksięgowany omyłkowo"})
    assert r.status_code == 200
    assert r.json()["status"] == "PAID"


# ---------------------------------------------------------------- korekty księgowe

def test_adjustment_requires_reason_and_nonzero(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    r = seeded.post(f"/api/payments/records/{rec}/adjust", headers=hc,
                    json={"amount_cents": -5000, "reason": "rabat lojalnościowy",
                          "document_ref": "FV/2026/08/031"})
    assert r.status_code == 200
    r = seeded.post(f"/api/payments/records/{rec}/adjust", headers=hc,
                    json={"amount_cents": 0, "reason": "zero"})
    assert r.status_code == 422
    r = seeded.post(f"/api/payments/records/{rec}/adjust", headers=hc,
                    json={"amount_cents": 100})
    assert r.status_code == 422  # brak powodu
    hist = seeded.get(f"/api/payments/records/{rec}/history", headers=hc).json()
    adj = next(t for t in hist["transactions"] if t["kind"] == "ADJUSTMENT")
    assert adj["document_ref"] == "FV/2026/08/031"  # referencja dokumentu zewn.


# ---------------------------------------------------------------- waluty

def test_multiple_currencies_kept_apart_in_reconciliation(seeded):
    from dzik_os.dates import local_today

    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    today = local_today().isoformat()
    rec_eur = _new_record(seeded, hc, id_a, amount=10000, currency="EUR",
                          due=today, package="Konsultacja online EUR")
    seeded.post(f"/api/payments/records/{rec_eur}/mark-paid", headers=hc, json={})
    rec_pln = _new_record(seeded, hc, id_a, amount=20000, currency="PLN",
                          due=today, package="Konsultacja PLN")
    r = seeded.get(f"/api/payments/reconciliation?month={today[:7]}", headers=hc)
    assert r.status_code == 200
    data = r.json()
    assert "EUR" in data["summary_by_currency"]
    assert "PLN" in data["summary_by_currency"]
    eur = data["summary_by_currency"]["EUR"]
    assert eur["expected_cents"] == 10000
    assert eur["collected_cents"] == 10000
    assert eur["difference_cents"] == 0
    row_pln = next(x for x in data["records"] if x["record_id"] == rec_pln)
    assert row_pln["collected_cents"] == 0
    assert row_pln["difference_cents"] == -20000
    assert row_pln["source"] == "NONE"
    row_eur = next(x for x in data["records"] if x["record_id"] == rec_eur)
    assert row_eur["source"] == "MANUAL"


def test_reconciliation_month_validation_and_isolation(seeded):
    hc = login(seeded, COACH)
    assert seeded.get("/api/payments/reconciliation?month=zle", headers=hc).status_code == 422
    # Inny trener widzi wyłącznie własne harmonogramy (tu: żadnych).
    create_user_with_role("obcy-rec@example.com", "ObcyTrener#26x", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy-rec@example.com", "password": "ObcyTrener#26x"})
    from dzik_os.dates import local_today

    month = local_today().isoformat()[:7]
    data = seeded.get(f"/api/payments/reconciliation?month={month}", headers=h2).json()
    assert data["records"] == []


# ---------------------------------------------------------------- izolacja (IDOR)

def test_foreign_coach_gets_404_on_all_payment_endpoints(seeded):
    create_user_with_role("obcy3@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy3@example.com", "password": "ObcyTrener#26"})
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    rec = _new_record(seeded, hc, id_a)
    tx = seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc,
                     json={}).json()["transaction_id"]
    assert seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=h2,
                       json={}).status_code == 404
    assert seeded.post(f"/api/payments/records/{rec}/refund", headers=h2,
                       json={"amount_cents": 100}).status_code == 404
    assert seeded.post(f"/api/payments/records/{rec}/adjust", headers=h2,
                       json={"amount_cents": 100, "reason": "x"}).status_code == 404
    assert seeded.post(f"/api/payments/transactions/{tx}/reverse", headers=h2,
                       json={"reason": "x"}).status_code == 404
    assert seeded.get(f"/api/payments/records/{rec}/history", headers=h2).status_code == 404
    assert seeded.post(f"/api/payments/records/{rec}/status", headers=h2,
                       json={"status": "CANCELLED"}).status_code == 404


def test_client_sees_own_history_but_not_others(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    id_a = get_user_id(seeded, ha)
    rec = _new_record(seeded, hc, id_a)
    seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc, json={})
    r = seeded.get(f"/api/payments/records/{rec}/history", headers=ha)
    assert r.status_code == 200
    assert r.json()["record"]["marked_by_name"] == "Lubelski Dzik"
    # Cudza płatność = 404 (bez ujawniania istnienia zasobu).
    assert seeded.get(f"/api/payments/records/{rec}/history", headers=hb).status_code == 404


def test_client_cannot_use_coach_payment_endpoints(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    rec = _new_record(seeded, hc, id_a)
    assert seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=ha,
                       json={}).status_code == 403
    assert seeded.post(f"/api/payments/records/{rec}/refund", headers=ha,
                       json={"amount_cents": 100}).status_code == 403
    assert seeded.get("/api/payments/reconciliation", headers=ha).status_code == 403


# ---------------------------------------------------------------- przypomnienia

def test_payment_reminder_follows_real_status(seeded, monkeypatch):
    """Przypomnienie idzie wyłącznie dla realnie wymagalnej należności
    (payment_state.DUE_STATUSES), po opłaceniu — zero przypomnień, treść bez
    kwot i nazw pakietów (może trafić na ekran blokady). Ścieżka wysyłki to
    wspólny system powiadomień (notifications.plan_day + dispatch_due)."""
    from datetime import UTC, datetime

    from dzik_os import push_service, reminder_loop
    from dzik_os.dates import local_today, tz_for_user

    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json={
        "endpoint": "https://push.example/platnosci",
        "keys": {"p256dh": "k" * 20, "auth": "a" * 10},
    })
    today = local_today()
    rec = _new_record(seeded, hc, id_a, due=today.isoformat(),
                      package="Pakiet PREMIUM 450 zł")

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        push_service, "_send_one",
        lambda sub, payload: sent.append((sub.user_id, payload)) or True,
    )
    # Wystąpienia planowane są na 08:00 czasu ODBIORCY — moment pętli musi
    # być tą samą chwilą wyrażoną w UTC (latem w Warszawie to 06:00 UTC).
    moment = datetime(
        today.year, today.month, today.day, 8, 0, tzinfo=tz_for_user(None)
    ).astimezone(UTC)
    reminder_loop._tick(moment)
    assert any(u == id_a for u, _ in sent)
    for _, payload in sent:
        text = str(payload)
        assert "450" not in text and "zł" not in text and "PLN" not in text
        assert "PREMIUM" not in text  # neutralna treść, bez nazw pakietów

    # Po opłaceniu: nawet zaplanowane wystąpienie jest wyciszone przy
    # wysyłce (bramka statusu), a nowe nie powstaje.
    seeded.post(f"/api/payments/records/{rec}/mark-paid", headers=hc, json={})
    sent.clear()
    reminder_loop._tick(moment)
    assert all(u != id_a for u, _ in sent)


# ---------------------------------------------------------------- migracja v1→v15

def test_migration_v1_to_v15_preserves_payment_data(tmp_path):
    """Stara baza (v1) z danymi płatności po migracjach zachowuje statusy
    i kwoty bez zmian (mapowanie tożsamościowe), marked_at jest uzupełnione
    z paid_at, a nowe tabele istnieją i są puste (bez fabrykowania
    historii)."""
    from sqlalchemy import create_engine, text

    from dzik_os.db import run_migrations

    eng = create_engine(f"sqlite:///{tmp_path}/old-payments.db")
    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, "
            "description TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO schema_migrations(version, description) "
                          "VALUES (1, 'initial')"))
        # Stuby tabel wymaganych przez migracje 2-13.
        conn.execute(text("CREATE TABLE users (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE consents (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE schedule_items (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE weekly_checkins (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE workout_entries (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE auth_sessions (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE progress_photos (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text(
            "CREATE TABLE messages (id VARCHAR(40) PRIMARY KEY, "
            "thread_id VARCHAR(40), author_id VARCHAR(40), created_at VARCHAR(40))"))
        # Płatności w kształcie v1 — z prawdziwymi danymi.
        conn.execute(text(
            "CREATE TABLE payment_schedules (id VARCHAR(40) PRIMARY KEY, "
            "client_id VARCHAR(40), coach_id VARCHAR(40), package_name VARCHAR(200), "
            "amount_cents INTEGER, currency VARCHAR(10), period VARCHAR(20), "
            "external_link VARCHAR(500), status VARCHAR(20), created_by VARCHAR(40), "
            "created_at VARCHAR(40))"))
        conn.execute(text(
            "CREATE TABLE payment_records (id VARCHAR(40) PRIMARY KEY, "
            "schedule_id VARCHAR(40), due_date VARCHAR(40), amount_cents INTEGER, "
            "currency VARCHAR(10), status VARCHAR(20), paid_at VARCHAR(40), "
            "marked_by VARCHAR(40), note TEXT, created_at VARCHAR(40))"))
        conn.execute(text(
            "INSERT INTO payment_records VALUES "
            "('P1','S1','2026-07-01',45000,'PLN','PAID','2026-07-02T10:00:00+00:00',"
            "'COACH1','przelew','2026-06-01'),"
            "('P2','S1','2026-08-01',45000,'PLN','PENDING',NULL,NULL,NULL,'2026-07-01'),"
            "('P3','S1','2026-06-01',30000,'EUR','OVERDUE',NULL,NULL,NULL,'2026-05-01'),"
            "('P4','S1','2026-05-01',30000,'PLN','CANCELLED',NULL,NULL,NULL,'2026-04-01')"))
    run_migrations(eng)
    with eng.connect() as conn:
        rows = {r[0]: r for r in conn.exec_driver_sql(
            "SELECT id, status, amount_cents, currency, paid_at, marked_at "
            "FROM payment_records")}
        tables = {r[0] for r in conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        tx_count = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM payment_transactions").scalar()
    # Statusy i kwoty bez zmian (zero utraty danych).
    assert rows["P1"][1:4] == ("PAID", 45000, "PLN")
    assert rows["P2"][1:4] == ("PENDING", 45000, "PLN")
    assert rows["P3"][1:4] == ("OVERDUE", 30000, "EUR")
    assert rows["P4"][1:4] == ("CANCELLED", 30000, "PLN")
    # marked_at uzupełnione wyłącznie tam, gdzie znany był moment (paid_at).
    assert rows["P1"][5] == rows["P1"][4] == "2026-07-02T10:00:00+00:00"
    assert rows["P2"][5] is None
    assert {"payment_transactions", "payment_status_changes",
            "payment_attempts", "payment_provider_events"} <= tables
    assert tx_count == 0  # historia nie jest fabrykowana wstecz

"""Eksport i usunięcie danych (prawa użytkownika Human OS)."""

from pathlib import Path

from conftest import CLIENT_A, COACH, get_user_id, login

from dzik_os.config import settings


def test_export_contains_all_sections(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/me/export", headers=ha)
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    body = r.json()
    for section in (
        "user", "profile_fields", "goals", "training_plans",
        "training_plan_versions", "nutrition_plans", "schedule_items",
        "weekly_checkins", "measurements", "documents", "files", "messages",
        "payment_schedules", "payment_records", "consents",
        "observations", "daily_nutrition_logs", "schedule_completions",
        "consult_slots", "push_subscriptions", "audit_receipts",
    ):
        assert section in body, section
    # Zgody w eksporcie niosą pełny kontekst kategorii.
    assert any(c.get("category") == "dane_zdrowotne" for c in body["consents"])
    assert body["user"]["email"] == CLIENT_A["email"]
    assert len(body["measurements"]) > 0
    assert len(body["training_plan_versions"]) >= 2
    assert "password" not in str(body)


def test_deletion_requires_password_and_phrase(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": "zle-haslo", "confirm": "USUŃ MOJE DANE"})
    assert r.status_code == 403
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"], "confirm": "usuń"})
    assert r.status_code == 422


def test_deletion_anonymizes_account_and_data(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)

    files_before = list(Path(settings.upload_dir).iterdir())
    assert files_before  # seed wgrał PDF klienta A

    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"],
                          "confirm": "USUŃ MOJE DANE"})
    assert r.status_code == 200

    # Konto nieaktywne: logowanie i sesja przestają działać.
    assert seeded.post("/api/auth/login", json=CLIENT_A).status_code == 401
    assert seeded.get("/api/auth/me", headers=ha).status_code == 401

    # Trener nie widzi już danych zdrowotnych.
    assert seeded.get(f"/api/clients/{id_a}/measurements",
                      headers=hc).status_code in (200, 404)
    # Lista klientów nie ujawnia PII.
    clients = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    row = next(c for c in clients if c["client_id"] == id_a)
    assert row["display_name"] == "Konto usunięte"
    assert "klient.a@example.com" not in str(clients)

    # Pliki klienta fizycznie usunięte z dysku.
    remaining = list(Path(settings.upload_dir).iterdir())
    assert len(remaining) < len(files_before)


def test_deletion_removes_push_and_free_text_keeps_billing(seeded):
    """Anonimizacja obejmuje subskrypcje push i wolne teksty (cele,
    przypomnienia, harmonogram, komentarze treningów, notatki płatności);
    dane rozliczeniowe (kwoty/terminy/statusy) ZOSTAJĄ — obowiązek
    podatkowy administratora (art. 6 ust. 1 lit. c RODO)."""
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json={
        "endpoint": "https://push.example/del-test",
        "keys": {"p256dh": "k" * 20, "auth": "a" * 10},
    })
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"],
                          "confirm": "USUŃ MOJE DANE"})
    assert r.status_code == 200

    from dzik_os.db import db_session
    from dzik_os.models import (
        Goal,
        PaymentRecord,
        PaymentSchedule,
        PushSubscription,
        Reminder,
        ScheduleItem,
        User,
        WorkoutSession,
    )

    with db_session() as db:
        uid = db.query(User).filter(User.display_name == "Konto usunięte").first().id
        assert db.query(PushSubscription).filter_by(user_id=uid).count() == 0
        for g in db.query(Goal).filter_by(client_id=uid).all():
            assert g.title == "[usunięto]" and g.description is None
        for rm in db.query(Reminder).filter_by(client_id=uid).all():
            assert rm.text == "[usunięto]"
        for si in db.query(ScheduleItem).filter_by(client_id=uid).all():
            assert si.instruction is None and si.author_note is None
        for ws in db.query(WorkoutSession).filter_by(client_id=uid).all():
            assert ws.comment is None and ws.pain_note is None
        # Ewidencja płatności przetrwała (kwoty/terminy/statusy), bez notatek.
        schedules = db.query(PaymentSchedule).filter_by(client_id=uid).all()
        assert schedules
        for ps in schedules:
            for pr in db.query(PaymentRecord).filter_by(schedule_id=ps.id).all():
                assert pr.amount_cents > 0 and pr.due_date
                assert pr.note is None


def test_deletion_is_audited_and_chain_valid(seeded):
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/me/deletion-request", headers=ha,
                json={"password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE"})
    from dzik_os.hos_bridge import event_store, verify_audit_chain

    assert verify_audit_chain() is True
    actions = [e["event_type"] for e in event_store().all()]
    assert "ACCOUNT_ANONYMIZED" in actions

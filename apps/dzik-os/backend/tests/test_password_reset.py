"""Bezpieczny reset hasła: ogólny komunikat (brak enumeracji kont),
limit prób, jednorazowy hashowany token z terminem ważności,
unieważnienie wszystkich sesji po resecie."""

import json
from datetime import UTC, datetime, timedelta

from conftest import CLIENT_A, login


class RecordingProvider:
    name = "recording"

    def __init__(self):
        self.sent = []

    def send_email(self, *, to, subject, body):
        self.sent.append({"to": to, "subject": subject, "body": body})
        return True


def _install_provider(monkeypatch) -> RecordingProvider:
    from dzik_os.routers import auth as auth_router

    provider = RecordingProvider()
    monkeypatch.setattr(auth_router, "notifications", provider)
    return provider


def _token_from_email(provider: RecordingProvider) -> str:
    body = provider.sent[-1]["body"]
    line = next(ln for ln in body.splitlines() if "/reset-hasla#" in ln)
    return line.split("#", 1)[1].strip()


def test_reset_request_response_identical_for_unknown_account(seeded, monkeypatch):
    provider = _install_provider(monkeypatch)
    r1 = seeded.post("/api/auth/password-reset/request",
                     json={"email": CLIENT_A["email"]})
    r2 = seeded.post("/api/auth/password-reset/request",
                     json={"email": "nie.istnieje@example.com"})
    # Jedna odpowiedź niezależnie od istnienia konta.
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()
    # E-mail wychodzi tylko dla istniejącego konta.
    assert len(provider.sent) == 1 and provider.sent[0]["to"] == CLIENT_A["email"]
    for forbidden in ("waga", "uraz", "dieta", "trening", "zdrow"):
        assert forbidden not in provider.sent[0]["body"].lower()


def test_reset_flow_sets_password_and_revokes_all_sessions(seeded, monkeypatch):
    provider = _install_provider(monkeypatch)
    h1 = login(seeded, CLIENT_A)
    h2 = login(seeded, CLIENT_A)  # druga sesja (inne urządzenie)
    seeded.post("/api/auth/password-reset/request", json={"email": CLIENT_A["email"]})
    token = _token_from_email(provider)
    r = seeded.post("/api/auth/password-reset/confirm", json={
        "token": token, "new_password": "PoResecie#1234"})
    assert r.status_code == 200
    # WSZYSTKIE stare sesje unieważnione.
    assert seeded.get("/api/auth/me", headers=h1).status_code == 401
    assert seeded.get("/api/auth/me", headers=h2).status_code == 401
    # Stare hasło nie działa, nowe tak.
    assert seeded.post("/api/auth/login", json=CLIENT_A).status_code == 401
    assert seeded.post("/api/auth/login", json={
        "email": CLIENT_A["email"], "password": "PoResecie#1234"}).status_code == 200
    # Token jednorazowy: ponowne użycie → 400.
    assert seeded.post("/api/auth/password-reset/confirm", json={
        "token": token, "new_password": "JeszczeInne#123"}).status_code == 400


def test_expired_reset_token_rejected(seeded, monkeypatch):
    provider = _install_provider(monkeypatch)
    seeded.post("/api/auth/password-reset/request", json={"email": CLIENT_A["email"]})
    token = _token_from_email(provider)
    from dzik_os.db import db_session
    from dzik_os.models import PasswordResetToken

    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    with db_session() as db:
        for row in db.query(PasswordResetToken).all():
            row.expires_at = past
    assert seeded.post("/api/auth/password-reset/confirm", json={
        "token": token, "new_password": "PoResecie#1234"}).status_code == 400


def test_new_reset_token_invalidates_previous(seeded, monkeypatch):
    provider = _install_provider(monkeypatch)
    seeded.post("/api/auth/password-reset/request", json={"email": CLIENT_A["email"]})
    old_token = _token_from_email(provider)
    seeded.post("/api/auth/password-reset/request", json={"email": CLIENT_A["email"]})
    new_token = _token_from_email(provider)
    assert old_token != new_token
    assert seeded.post("/api/auth/password-reset/confirm", json={
        "token": old_token, "new_password": "PoResecie#1234"}).status_code == 400
    assert seeded.post("/api/auth/password-reset/confirm", json={
        "token": new_token, "new_password": "PoResecie#1234"}).status_code == 200


def test_reset_requests_are_rate_limited(seeded):
    from dzik_os.config import settings

    for _ in range(settings.reset_max_requests):
        r = seeded.post("/api/auth/password-reset/request",
                        json={"email": "ktokolwiek@example.com"})
        assert r.status_code == 200
    r = seeded.post("/api/auth/password-reset/request",
                    json={"email": "ktokolwiek@example.com"})
    assert r.status_code == 429


def test_reset_token_never_in_audit_or_logs(seeded, monkeypatch):
    provider = _install_provider(monkeypatch)
    from dzik_os.hos_bridge import event_store

    seeded.post("/api/auth/password-reset/request", json={"email": CLIENT_A["email"]})
    token = _token_from_email(provider)
    events = json.dumps(event_store().all())
    assert token not in events
    assert "PASSWORD_RESET_REQUESTED" in events
    seeded.post("/api/auth/password-reset/confirm", json={
        "token": token, "new_password": "PoResecie#1234"})
    events = json.dumps(event_store().all())
    assert token not in events and "PoResecie" not in events
    assert "PASSWORD_RESET_COMPLETED" in events

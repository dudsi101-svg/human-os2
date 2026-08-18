"""Zaproszenia i aktywacja konta klienta (bez hasła startowego).

Trener podaje wyłącznie e-mail i imię; klient otrzymuje jednorazowy link
aktywacyjny i SAM ustawia hasło. W bazie wyłącznie hash SHA-256 tokenu;
token nigdy nie trafia do audytu."""

import json
from datetime import UTC, datetime, timedelta

from conftest import COACH, activation_token, get_user_id, invite_client, login


def _expire_invitations(client_id: str) -> None:
    from dzik_os.db import db_session
    from dzik_os.models import ClientInvitation

    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    with db_session() as db:
        for row in db.query(ClientInvitation).filter_by(client_id=client_id).all():
            row.expires_at = past


def test_invitation_creates_pending_account_without_password(seeded):
    hc = login(seeded, COACH)
    created = invite_client(seeded, hc, "zaproszony@example.com", "Zaproszony Klient")
    inv = created["invitation"]
    assert inv is not None and inv["delivery"] == "manual"
    # NullProvider: link do ręcznego przekazania wraca trenerowi (kompromis
    # opisany w docs); token w URL siedzi we FRAGMENCIE (#) — nie w query.
    assert "#" in inv["activation_link"] and "?" not in inv["activation_link"]
    # Trener NIE zna i NIE ustawia żadnego hasła.
    assert "password" not in json.dumps(created).lower()
    # Konto przed aktywacją nie może się zalogować (żadnym hasłem).
    r = seeded.post("/api/auth/login", json={
        "email": "zaproszony@example.com", "password": "Cokolwiek#123x"})
    assert r.status_code == 401
    # Lista klientów pokazuje status oczekiwania na aktywację.
    rows = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    row = next(c for c in rows if c["client_id"] == created["client_id"])
    assert row["account_pending"] is True
    assert row["invitation_expires_at"] == inv["expires_at"]


def test_valid_invitation_activates_account_and_token_is_single_use(seeded):
    hc = login(seeded, COACH)
    created = invite_client(seeded, hc, "aktywuj@example.com")
    token = activation_token(created)
    # Podgląd ważnego zaproszenia (ekran aktywacji).
    r = seeded.post("/api/auth/activation/inspect", json={"token": token})
    assert r.status_code == 200
    assert r.json()["email"] == "aktywuj@example.com"
    # Aktywacja: klient sam ustawia hasło (za krótkie → 422).
    r = seeded.post("/api/auth/activate", json={"token": token, "password": "krotkie"})
    assert r.status_code == 422
    r = seeded.post("/api/auth/activate", json={
        "token": token, "password": "MojeWlasne#123"})
    assert r.status_code == 200
    # Logowanie działa, bez wymuszania zmiany hasła (jest własne od początku).
    r = seeded.post("/api/auth/login", json={
        "email": "aktywuj@example.com", "password": "MojeWlasne#123"})
    assert r.status_code == 200
    assert r.json()["user"]["must_change_password"] is False
    # Token jest jednorazowy: ponowne użycie i podgląd → 404.
    assert seeded.post("/api/auth/activate", json={
        "token": token, "password": "InneHaslo#1234"}).status_code == 404
    assert seeded.post("/api/auth/activation/inspect",
                       json={"token": token}).status_code == 404


def test_expired_invitation_is_rejected(seeded):
    hc = login(seeded, COACH)
    created = invite_client(seeded, hc, "wygasly@example.com")
    token = activation_token(created)
    _expire_invitations(created["client_id"])
    assert seeded.post("/api/auth/activation/inspect",
                       json={"token": token}).status_code == 404
    assert seeded.post("/api/auth/activate", json={
        "token": token, "password": "MojeWlasne#123"}).status_code == 404


def test_cancelled_invitation_is_rejected(seeded):
    hc = login(seeded, COACH)
    created = invite_client(seeded, hc, "anulowany@example.com")
    token = activation_token(created)
    r = seeded.post(
        f"/api/coach/clients/{created['client_id']}/invitations/cancel", headers=hc)
    assert r.status_code == 200 and r.json()["cancelled"] == 1
    assert seeded.post("/api/auth/activate", json={
        "token": token, "password": "MojeWlasne#123"}).status_code == 404


def test_resend_invalidates_previous_token(seeded):
    hc = login(seeded, COACH)
    created = invite_client(seeded, hc, "ponowny@example.com")
    old_token = activation_token(created)
    r = seeded.post(
        f"/api/coach/clients/{created['client_id']}/invitations", headers=hc)
    assert r.status_code == 201
    new_token = activation_token({"invitation": r.json()["invitation"]})
    assert new_token != old_token
    # Stary token natychmiast nieważny; nowy działa.
    assert seeded.post("/api/auth/activate", json={
        "token": old_token, "password": "MojeWlasne#123"}).status_code == 404
    assert seeded.post("/api/auth/activate", json={
        "token": new_token, "password": "MojeWlasne#123"}).status_code == 200
    # Konto aktywowane → kolejne ponowienie nie ma czego wysłać (409).
    assert seeded.post(
        f"/api/coach/clients/{created['client_id']}/invitations", headers=hc
    ).status_code == 409


def test_foreign_coach_cannot_touch_invitation(seeded):
    from conftest import create_user_with_role

    hc = login(seeded, COACH)
    created = invite_client(seeded, hc, "cudzy@example.com")
    create_user_with_role("obcy.trener@example.com", "ObcyTrener#123",
                          "Obcy Trener", "COACH")
    hf = login(seeded, {"email": "obcy.trener@example.com",
                        "password": "ObcyTrener#123"})
    # Obcy trener (bez relacji) nie ponowi ani nie anuluje zaproszenia.
    assert seeded.post(
        f"/api/coach/clients/{created['client_id']}/invitations", headers=hf
    ).status_code == 404
    assert seeded.post(
        f"/api/coach/clients/{created['client_id']}/invitations/cancel", headers=hf
    ).status_code == 404


def test_invitation_email_has_link_and_no_health_data(seeded, monkeypatch):
    """Przy skonfigurowanym dostawcy link idzie WYŁĄCZNIE e-mailem
    (odpowiedź API bez activation_link), a treść nie zawiera danych
    zdrowotnych — tylko zaproszenie."""
    from dzik_os.routers import clients as clients_router

    sent = []

    class RecordingProvider:
        name = "recording"

        def send_email(self, *, to, subject, body):
            sent.append({"to": to, "subject": subject, "body": body})
            return True

    monkeypatch.setattr(clients_router, "notifications", RecordingProvider())
    hc = login(seeded, COACH)
    created = invite_client(seeded, hc, "emailowy@example.com", "Emailowy Klient")
    inv = created["invitation"]
    assert inv["delivery"] == "email"
    assert "activation_link" not in inv  # trener NIE widzi linku
    assert len(sent) == 1 and sent[0]["to"] == "emailowy@example.com"
    assert "/aktywacja#" in sent[0]["body"]
    for forbidden in ("waga", "uraz", "dieta", "trening", "zdrow"):
        assert forbidden not in sent[0]["body"].lower()


def test_activation_token_never_in_audit_chain(seeded):
    from dzik_os.hos_bridge import event_store

    hc = login(seeded, COACH)
    created = invite_client(seeded, hc, "audytowy@example.com")
    token = activation_token(created)
    events = json.dumps(event_store().all())
    assert token not in events
    assert "activation_link" not in events
    # Zdarzenie zaproszenia istnieje — z metadanymi, bez sekretu.
    assert "CLIENT_INVITED" in events


def test_relinking_existing_active_account_creates_no_invitation(seeded):
    """Podpięcie ISTNIEJĄCEGO aktywnego konta nie tworzy zaproszenia
    (konto już ma hasło) — przepływ P3 pozostaje bez zmian."""
    from conftest import CLIENT_A

    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    seeded.post(f"/api/coach/clients/{id_a}/relationship-status?status=ENDED",
                headers=hc)
    r = seeded.post("/api/coach/clients", headers=hc, json={
        "client_email": CLIENT_A["email"], "client_name": "Klient Testowy A"})
    assert r.status_code == 201
    assert r.json()["invitation"] is None

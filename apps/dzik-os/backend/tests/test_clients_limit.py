"""Limit podopiecznych (0.52.0, DZIK_MAX_CLIENTS): pilotaż na 10 osób.

Liczą się współprace niezakończone (ACTIVE/PAUSED); ENDED zwalnia
miejsce; 0 wyłącza limit. Testy ustawiają niski limit monkeypatchem —
seed ma już kilku klientów, więc progu nie trzeba dobijać dziesiątką.
"""

from conftest import COACH, login

from dzik_os.config import settings
from dzik_os.db import db_session
from dzik_os.models import CoachClientRelationship


def _aktywne_wspolprace(client, hc) -> int:
    rows = client.get("/api/coach/clients", headers=hc).json()["clients"]
    return len([r for r in rows if r["relationship_status"] in ("ACTIVE", "PAUSED")])


def _zapros(client, hc, email):
    return client.post(
        "/api/coach/clients",
        headers=hc,
        json={"client_name": "Nowa Osoba", "client_email": email},
    )


def test_limit_odmawia_a_ended_zwalnia_miejsce(seeded, monkeypatch):
    hc = login(seeded, COACH)
    zajete = _aktywne_wspolprace(seeded, hc)
    monkeypatch.setattr(settings, "max_clients", zajete)

    r = _zapros(seeded, hc, "ponad.limit@example.com")
    assert r.status_code == 409
    assert "Limit podopiecznych" in r.json()["detail"]

    # Zakończenie jednej współpracy zwalnia miejsce dla nowej osoby.
    with db_session() as db:
        rel = (
            db.query(CoachClientRelationship)
            .filter(CoachClientRelationship.status == "ACTIVE")
            .first()
        )
        rel.status = "ENDED"
    r = _zapros(seeded, hc, "ponad.limit@example.com")
    assert r.status_code == 201, r.text


def test_zero_wylacza_limit(seeded, monkeypatch):
    hc = login(seeded, COACH)
    monkeypatch.setattr(settings, "max_clients", 0)
    r = _zapros(seeded, hc, "bez.limitu@example.com")
    assert r.status_code == 201, r.text


def test_domyslny_limit_to_dziesiec():
    assert settings.max_clients == 10

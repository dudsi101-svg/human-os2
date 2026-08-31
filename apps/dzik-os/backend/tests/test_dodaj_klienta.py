"""Operatorskie konto podopiecznego (0.54.2): konto + aktywna relacja
jednym ruchem, hasło jednorazowe, limity i odmowy jak w panelu trenera,
audyt bez hasła."""

import pytest
from conftest import COACH, login

from dzik_os import hos_bridge
from dzik_os.config import settings
from dzik_os.dodaj_klienta import dodaj_klienta

HASLO = "Startowe#2026!x"
EMAIL = "nowy.podopieczny@example.com"


def test_konto_z_relacja_i_jednorazowym_haslem(seeded):
    user_id = dodaj_klienta(EMAIL, COACH["email"], HASLO, name="Nowy P.")

    # Login działa od razu i wymusza zmianę hasła (startowe = jednorazowe).
    r = seeded.post("/api/auth/login", json={"email": EMAIL, "password": HASLO})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["must_change_password"] is True

    # Trener widzi nowego podopiecznego na swojej liście (relacja ACTIVE).
    hc = login(seeded, COACH)
    lista = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    assert any(c["client_id"] == user_id for c in lista)

    # Audyt: rejestracja + relacja, bez treści hasła.
    zdarzenia = [e for e in hos_bridge.event_store().all()
                 if user_id in e.get("subject_ids", [])]
    akcje = {e["event_type"] for e in zdarzenia}
    assert {"IDENTITY_REGISTERED", "RELATIONSHIP_CREATED"} <= akcje
    assert all(HASLO not in str(e) for e in zdarzenia)


def test_odmowy_zajety_email_zly_trener_krotkie_haslo(seeded):
    dodaj_klienta(EMAIL, COACH["email"], HASLO)
    with pytest.raises(ValueError, match="już istnieje"):
        dodaj_klienta(EMAIL, COACH["email"], HASLO)
    with pytest.raises(ValueError, match="nie istnieje albo jest nieaktywny"):
        dodaj_klienta("inny@example.com", "niema@example.com", HASLO)
    with pytest.raises(ValueError, match="mniej niż"):
        dodaj_klienta("inny@example.com", COACH["email"], "krotkie")
    # Konto klienta w roli trenera = odmowa (rola, nie tylko istnienie).
    with pytest.raises(ValueError, match="roli COACH"):
        dodaj_klienta("inny@example.com", "klient.a@example.com", HASLO)


def test_limit_podopiecznych_honorowany(seeded, monkeypatch):
    monkeypatch.setattr(settings, "max_clients", 1)
    # Seed daje trenerowi wielu aktywnych podopiecznych — limit 1 już przekroczony.
    with pytest.raises(ValueError, match="Limit podopiecznych"):
        dodaj_klienta(EMAIL, COACH["email"], HASLO)

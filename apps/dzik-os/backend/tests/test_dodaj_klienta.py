"""Operatorskie konto podopiecznego (0.54.2): konto + aktywna relacja
jednym ruchem, hasło jednorazowe, limity i odmowy jak w panelu trenera,
audyt bez hasła. 0.54.3: deklaracje zgód i wątek jak z panelu."""

import pytest
from conftest import COACH, login

from dzik_os import hos_bridge
from dzik_os.config import settings
from dzik_os.consent_catalog import ONBOARDING_CATEGORIES
from dzik_os.db import db_session
from dzik_os.dodaj_klienta import dodaj_klienta
from dzik_os.models import MessageThread

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


def _zaloguj_i_zmien_haslo(seeded, email: str) -> dict:
    """Pierwsze logowanie kontem operatorskim: wymuszona zmiana hasła
    (poza nią API jest zamknięte), potem normalny nagłówek."""
    r = seeded.post("/api/auth/login", json={"email": email, "password": HASLO})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    r = seeded.post("/api/auth/change-password", headers=h,
                    json={"current_password": HASLO, "new_password": HASLO + "nowe"})
    assert r.status_code == 200, r.text
    return login(seeded, {"email": email, "password": HASLO + "nowe"})


def test_deklaracje_z_onboardingu_i_watek_jak_z_panelu(seeded):
    """0.54.3: konto operatorskie ma DOKŁADNIE to, co konto z zaproszenia —
    deklaracje zgód do potwierdzenia przez podmiot (nic nie jest
    potwierdzone za niego), odbiorcę zgód z relacji i wątek wiadomości."""
    user_id = dodaj_klienta(EMAIL, COACH["email"], HASLO)
    h = _zaloguj_i_zmien_haslo(seeded, EMAIL)

    body = seeded.get("/api/me/consents", headers=h).json()
    oczekujace = [c for c in body["consents"]
                  if not c["confirmed_at"] and not c["revoked_at"] and not c["denied_at"]]
    assert {c["category"] for c in oczekujace} == set(ONBOARDING_CATEGORIES)
    assert all(c["source"] == "ONBOARDING_DECLARATION" for c in oczekujace)
    trenerskie = [c for c in oczekujace if c["grantee_id"] != "SYSTEM"]
    assert trenerskie and len({c["grantee_id"] for c in trenerskie}) == 1
    coach_id = trenerskie[0]["grantee_id"]
    assert [c["id"] for c in body["coaches"]] == [coach_id]

    # Deklaracja z onboardingu autoryzuje jak przy zaproszeniu z panelu
    # (istniejące zachowanie: proweniencja jawna, klient decyduje przy
    # pierwszym logowaniu) — potwierdzenie nie zmienia dostępu, cofnięcie
    # odbiera go natychmiast.
    hc = login(seeded, COACH)
    wpis = next(c for c in seeded.get("/api/coach/clients", headers=hc).json()["clients"]
                if c["client_id"] == user_id)
    assert wpis["consent_active"] is True
    for c in trenerskie:
        assert seeded.post(f"/api/me/consents/{c['id']}/confirm", headers=h).status_code == 200
    wspolpraca = next(c for c in trenerskie if c["category"] == "udostepnianie_trenerowi")
    assert seeded.post(f"/api/me/consents/{wspolpraca['id']}/revoke", headers=h).status_code == 200
    wpis = next(c for c in seeded.get("/api/coach/clients", headers=hc).json()["clients"]
                if c["client_id"] == user_id)
    assert wpis["consent_active"] is False

    # Wątek wiadomości istnieje po obu stronach.
    assert len(seeded.get("/api/threads", headers=h).json()["threads"]) == 1
    watki_trenera = seeded.get("/api/threads", headers=hc).json()["threads"]
    assert any(t["with_user"]["id"] == user_id for t in watki_trenera)


def test_brakujacy_watek_dopisuje_sie_przy_liscie(seeded):
    """Relacja bez wątku (konta operatorskie sprzed 0.54.3) — lista
    wiadomości dokłada brakujący wątek, nic nie usuwa i nie dubluje."""
    user_id = dodaj_klienta(EMAIL, COACH["email"], HASLO)
    with db_session() as db:
        db.query(MessageThread).filter(MessageThread.client_id == user_id).delete()
        db.commit()
    h = _zaloguj_i_zmien_haslo(seeded, EMAIL)
    for _ in range(2):
        watki = seeded.get("/api/threads", headers=h).json()["threads"]
        assert len(watki) == 1
    with db_session() as db:
        assert db.query(MessageThread).filter(MessageThread.client_id == user_id).count() == 1


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

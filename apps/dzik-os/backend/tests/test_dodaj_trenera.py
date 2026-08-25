"""Kolejne konto trenera na działającej bazie (0.53.1)."""

import pytest
from conftest import login

from dzik_os.dodaj_trenera import dodaj_trenera, main


def test_zaklada_konto_i_logowanie_dziala(seeded):
    user_id = dodaj_trenera("drugi.trener@example.com", "SilneHaslo#123",
                            "Trener Testowy")
    assert user_id.startswith("HOS-USR-")
    # Logowanie działa; konto wymusza zmianę hasła przy pierwszym wejściu.
    r = seeded.post("/api/auth/login", json={
        "email": "drugi.trener@example.com", "password": "SilneHaslo#123",
    })
    assert r.status_code == 200, r.text
    assert r.json()["user"]["must_change_password"] is True
    assert "COACH" in r.json()["user"]["roles"]


def test_odmawia_na_zajety_email(seeded):
    with pytest.raises(ValueError, match="już istnieje"):
        dodaj_trenera("dzik@example.com", "SilneHaslo#123")


def test_odmawia_krotkie_haslo(seeded):
    with pytest.raises(ValueError, match="mniej niż"):
        dodaj_trenera("nowy@example.com", "krotkie")


def test_cli_wymaga_hasla_w_env(seeded, monkeypatch):
    monkeypatch.delenv("DZIK_BOOTSTRAP_COACH_PASSWORD", raising=False)
    assert main(["--email", "ktos@example.com"]) == 1

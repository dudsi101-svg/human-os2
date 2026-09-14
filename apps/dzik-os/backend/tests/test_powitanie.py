"""Powitanie po pierwszym logowaniu (0.70.0): znacznik `welcome_seen_at`
na serwerze — świeże konto bez znacznika, POST idempotentny, konta demo
z seedu ze znacznikiem, eksport bez pola (znacznik UI, nie dane treści)."""

from __future__ import annotations

from conftest import CLIENT_A, COACH, create_activated_client, login

from dzik_os.db import SessionLocal
from dzik_os.models import User

NOWY = {"email": "swiezy.klient@example.com", "password": "SwiezeHaslo#123"}


def test_swiezy_klient_widzi_powitanie_a_post_jest_idempotentny(seeded):
    hc = login(seeded, COACH)
    cid = create_activated_client(seeded, hc, NOWY["email"], NOWY["password"], "Świeży Klient")
    hn = login(seeded, NOWY)
    d = seeded.get("/api/me/today", headers=hn).json()
    assert d["welcome_seen"] is False and d["greeting_name"] == "Świeży"

    r1 = seeded.post("/api/me/welcome-seen", headers=hn)
    assert r1.status_code == 200 and r1.json()["welcome_seen"] is True
    kiedy = r1.json()["welcome_seen_at"]
    assert kiedy
    # Drugie wywołanie nie zmienia daty (okno otwarte ponownie z „Więcej → Pomoc”
    # tej trasy w ogóle nie woła; nawet gdyby zawołało — nic się nie nadpisze).
    r2 = seeded.post("/api/me/welcome-seen", headers=hn)
    assert r2.status_code == 200 and r2.json()["welcome_seen_at"] == kiedy
    with SessionLocal() as db:
        assert db.get(User, cid).welcome_seen_at == kiedy
    assert seeded.get("/api/me/today", headers=hn).json()["welcome_seen"] is True


def test_anonim_i_konta_demo(seeded):
    assert seeded.post("/api/me/welcome-seen").status_code == 401
    # Konta demo to klienci „od dawna” — bez okna przy każdym demo i teście E2E.
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/me/today", headers=ha).json()["welcome_seen"] is True


def test_eksport_bez_znacznika_i_wersja_bez_zmian(seeded):
    ha = login(seeded, CLIENT_A)
    ex = seeded.get("/api/me/export", headers=ha).json()
    # Znacznik interfejsu (jak last_login_at) nie jest daną treści — świadomie
    # poza eksportem; wersja eksportu zostaje (decyzja w planie sesji).
    assert ex["export_version"] == "2.1"
    assert "welcome_seen_at" not in ex["user"]

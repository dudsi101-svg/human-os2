"""Publiczny formularz zapytań (0.49.0): walidacja, honeypot, limiter,
doręczenie do centrum powiadomień trenera."""

from conftest import COACH, login

from dzik_os.routers.public_site import lead_rate_limiter

PRAWIDLOWE = {
    "name": "Jan Zainteresowany",
    "email": "jan@example.com",
    "phone": "+48 600 700 800",
    "message": "Dzień dobry, chcę zacząć treningi od września.",
}


def _wyczysc_limiter():
    lead_rate_limiter._attempts.clear()


def test_lead_trafia_do_powiadomien_trenera(seeded):
    _wyczysc_limiter()
    r = seeded.post("/api/public/lead", json=PRAWIDLOWE)
    assert r.status_code == 200 and r.json() == {"ok": True}

    hc = login(seeded, COACH)
    items = seeded.get("/api/notifications", headers=hc).json()["notifications"]
    lead = next(i for i in items if i["category"] == "ZAPYTANIE")
    assert "Jan Zainteresowany" in lead["title"]
    assert "jan@example.com" in lead["body"]
    assert "600 700 800" in lead["body"]
    assert "od września" in lead["body"]


def test_honeypot_udaje_sukces_i_nic_nie_zapisuje(seeded):
    _wyczysc_limiter()
    r = seeded.post(
        "/api/public/lead", json={**PRAWIDLOWE, "website": "https://spam.example"}
    )
    assert r.status_code == 200 and r.json() == {"ok": True}

    hc = login(seeded, COACH)
    items = seeded.get("/api/notifications", headers=hc).json()["notifications"]
    assert not [i for i in items if i["category"] == "ZAPYTANIE"]


def test_walidacja_odrzuca_krotka_wiadomosc_i_zly_email(seeded):
    _wyczysc_limiter()
    r = seeded.post("/api/public/lead", json={**PRAWIDLOWE, "message": "hej"})
    assert r.status_code == 422
    r = seeded.post("/api/public/lead", json={**PRAWIDLOWE, "email": "nie-adres"})
    assert r.status_code == 422
    r = seeded.post("/api/public/lead", json={**PRAWIDLOWE, "extra": "pole"})
    assert r.status_code == 422


def test_limiter_odmawia_po_pieciu_probach(seeded):
    _wyczysc_limiter()
    for _ in range(5):
        assert seeded.post("/api/public/lead", json=PRAWIDLOWE).status_code == 200
    assert seeded.post("/api/public/lead", json=PRAWIDLOWE).status_code == 429

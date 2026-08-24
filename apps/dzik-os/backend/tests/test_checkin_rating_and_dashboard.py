"""Ocena raportu przez trenera (rating 1-5, opcjonalna) oraz dashboard
trenera (agregaty operacyjne — metadane, nigdy ranking klientów)."""

from datetime import timedelta

from conftest import CLIENT_A, COACH, login

from dzik_os.dates import local_today


def _poniedzialek(tygodni_naprzod: int) -> str:
    """Poniedziałek tygodnia N tygodni w przód od dziś. Seed sieje raporty
    względem PRAWDZIWEGO `today` (tygodnie bieżący i przeszłe), więc data
    wpisana na sztywno prędzej czy później koliduje (409) — 24.08.2026
    kalendarz dogonił „2026-08-17". Przyszłe tygodnie są zawsze wolne."""
    dzis = local_today()
    poniedzialek = dzis - timedelta(days=dzis.isoweekday() - 1)
    return (poniedzialek + timedelta(weeks=tygodni_naprzod)).isoformat()

def _submit_checkin(seeded, ha, week_start=None):
    week_start = week_start or _poniedzialek(2)
    r = seeded.post("/api/checkins", headers=ha, json={"week_start": week_start})
    assert r.status_code == 201
    return r.json()["id"]


def test_coach_can_rate_report_and_client_sees_rating(seeded):
    ha = login(seeded, CLIENT_A)
    checkin_id = _submit_checkin(seeded, ha)

    hc = login(seeded, COACH)
    r = seeded.post(f"/api/checkins/{checkin_id}/review", headers=hc, json={
        "coach_response": "Dobra robota.", "rating": 4,
    })
    assert r.status_code == 200

    client_id = _client_id(seeded, hc)
    rows = seeded.get(f"/api/clients/{client_id}/checkins", headers=hc).json()["checkins"]
    row = next(c for c in rows if c["id"] == checkin_id)
    assert row["rating"] == 4

    client_rows = seeded.get(f"/api/clients/{client_id}/checkins", headers=ha).json()["checkins"]
    client_row = next(c for c in client_rows if c["id"] == checkin_id)
    assert client_row["rating"] == 4


def test_rating_is_optional(seeded):
    ha = login(seeded, CLIENT_A)
    checkin_id = _submit_checkin(seeded, ha, _poniedzialek(3))
    hc = login(seeded, COACH)
    r = seeded.post(f"/api/checkins/{checkin_id}/review", headers=hc, json={
        "coach_response": "OK, bez oceny tym razem.",
    })
    assert r.status_code == 200
    rows = seeded.get(f"/api/clients/{_client_id(seeded, hc)}/checkins", headers=hc).json()["checkins"]
    row = next(c for c in rows if c["id"] == checkin_id)
    assert row["rating"] is None


def test_rating_out_of_range_rejected(seeded):
    ha = login(seeded, CLIENT_A)
    checkin_id = _submit_checkin(seeded, ha, _poniedzialek(4))
    hc = login(seeded, COACH)
    r = seeded.post(f"/api/checkins/{checkin_id}/review", headers=hc, json={
        "coach_response": "x", "rating": 9,
    })
    assert r.status_code == 422


def _client_id(seeded, hc) -> str:
    clients = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    return next(c["client_id"] for c in clients if c["email"] == CLIENT_A["email"])


def test_dashboard_reflects_awaiting_review_and_counts(seeded):
    hc = login(seeded, COACH)
    before = seeded.get("/api/coach/dashboard", headers=hc).json()
    assert before["active_clients"] == 5  # A, B + symulowani C, D, E
    # Seed: klient C ma raport czekający na ocenę.
    assert before["awaiting_review"] >= 1
    assert before["exercises_count"] >= 10
    assert before["food_products_count"] >= 20
    assert before["knowledge_items_count"] >= 5

    ha = login(seeded, CLIENT_A)
    _submit_checkin(seeded, ha, _poniedzialek(5))
    after = seeded.get("/api/coach/dashboard", headers=hc).json()
    assert after["awaiting_review"] == before["awaiting_review"] + 1

    client_id = _client_id(seeded, hc)
    clients = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    row = next(c for c in clients if c["client_id"] == client_id)
    assert row["flags"]["awaiting_review"] is True


def test_dashboard_requires_coach_role(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/coach/dashboard", headers=ha)
    assert r.status_code == 403

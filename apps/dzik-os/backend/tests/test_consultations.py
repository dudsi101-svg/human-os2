"""Terminarz konsultacji: sloty trenera, rezerwacje klienta, reguła 12 h,
izolacja między trenerami, powiadomienia push przy rezerwacji/odwołaniu."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from conftest import CLIENT_A, COACH, create_user_with_role, get_user_id, login


def _future(hours: int) -> str:
    now = datetime.now(ZoneInfo("Europe/Warsaw")).replace(tzinfo=None)
    return (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M")


def _make_slot(seeded, hc, hours=48, duration=30) -> str:
    r = seeded.post("/api/coach/consult-slots", headers=hc,
                    json={"starts_at": _future(hours), "duration_min": duration})
    assert r.status_code == 201
    return r.json()["id"]


def test_full_booking_flow_with_push(seeded, monkeypatch):
    sent = []
    from dzik_os import push_service

    monkeypatch.setattr(
        push_service, "_send_one", lambda sub, payload: sent.append((sub.user_id, payload)) or True
    )
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    coach_id = get_user_id(seeded, hc)
    seeded.post("/api/push/subscribe", headers=hc, json={
        "endpoint": "https://push.example.com/coach", "keys": {"p256dh": "k", "auth": "a"},
    })
    slot_id = _make_slot(seeded, hc)

    # Klient widzi wolny slot i rezerwuje.
    slots = seeded.get("/api/me/consult-slots", headers=ha).json()
    assert any(s["id"] == slot_id for s in slots["open"])
    r = seeded.post(f"/api/consult-slots/{slot_id}/book", headers=ha)
    assert r.status_code == 200
    assert r.json()["status"] == "BOOKED"
    # Push do trenera z treścią NEUTRALNĄ (bez nazwiska klienta i terminu);
    # szczegóły rezerwacji lądują w centrum powiadomień.
    assert any(uid == coach_id for uid, _ in sent)
    assert all("Klient Testowy" not in payload for _, payload in sent)
    inbox = seeded.get("/api/notifications", headers=hc).json()
    assert any(
        n["category"] == "KONSULTACJA" and "rezerwacja" in n["title"].lower()
        for n in inbox["notifications"]
    )

    # Zarezerwowany slot znika z wolnych, jest w moich; trener widzi nazwisko.
    slots = seeded.get("/api/me/consult-slots", headers=ha).json()
    assert all(s["id"] != slot_id for s in slots["open"])
    assert any(s["id"] == slot_id for s in slots["booked"])
    coach_view = seeded.get("/api/coach/consult-slots", headers=hc).json()["slots"]
    booked = next(s for s in coach_view if s["id"] == slot_id)
    assert booked["client_name"] == "Klient Testowy A"

    # Dashboard trenera liczy nadchodzące konsultacje.
    dash = seeded.get("/api/coach/dashboard", headers=hc).json()
    assert dash["upcoming_consultations"] >= 1

    # Odwołanie >12 h przed terminem wraca do OPEN + push do trenera.
    sent.clear()
    r = seeded.post(f"/api/consult-slots/{slot_id}/unbook", headers=ha)
    assert r.status_code == 200
    coach_view = seeded.get("/api/coach/consult-slots", headers=hc).json()["slots"]
    assert next(s for s in coach_view if s["id"] == slot_id)["status"] == "OPEN"
    assert any(uid == coach_id for uid, _ in sent)


def test_client_cannot_unbook_within_12h(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    slot_id = _make_slot(seeded, hc, hours=6)
    assert seeded.post(f"/api/consult-slots/{slot_id}/book", headers=ha).status_code == 200
    r = seeded.post(f"/api/consult-slots/{slot_id}/unbook", headers=ha)
    assert r.status_code == 422
    assert "12 h" in r.json()["detail"]


def test_coach_can_cancel_booked_slot_with_push_to_client(seeded, monkeypatch):
    sent = []
    from dzik_os import push_service

    monkeypatch.setattr(
        push_service, "_send_one", lambda sub, payload: sent.append(sub.user_id) or True
    )
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json={
        "endpoint": "https://push.example.com/client", "keys": {"p256dh": "k", "auth": "a"},
    })
    slot_id = _make_slot(seeded, hc)
    seeded.post(f"/api/consult-slots/{slot_id}/book", headers=ha)
    r = seeded.post(f"/api/coach/consult-slots/{slot_id}/cancel", headers=hc)
    assert r.status_code == 200
    assert client_id in sent
    # Odwołany slot znika z list.
    slots = seeded.get("/api/me/consult-slots", headers=ha).json()
    assert all(s["id"] != slot_id for s in slots["open"] + slots["booked"])


def test_isolation_client_of_other_coach_cannot_book(seeded):
    hc = login(seeded, COACH)
    slot_id = _make_slot(seeded, hc)
    create_user_with_role("obcy.klient@example.com", "ObcyKlient#26x", "Obcy Klient", "CLIENT")
    h2 = login(seeded, {"email": "obcy.klient@example.com", "password": "ObcyKlient#26x"})
    assert seeded.post(f"/api/consult-slots/{slot_id}/book", headers=h2).status_code == 404
    # Obcy klient nie widzi też slotów tego trenera.
    slots = seeded.get("/api/me/consult-slots", headers=h2).json()
    assert slots["open"] == []


def test_slot_must_be_in_future(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/consult-slots", headers=hc,
                    json={"starts_at": "2020-01-01T10:00", "duration_min": 30})
    assert r.status_code == 422

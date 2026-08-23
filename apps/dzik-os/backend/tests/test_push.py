"""Web Push: subskrypcje (opt-in/opt-out), triggery powiadomień
(monkeypatch wysyłki — bez realnego dostawcy push) i pętla przypomnień."""

from datetime import datetime
from zoneinfo import ZoneInfo

from conftest import CLIENT_A, COACH, get_user_id, login

SUB = {
    "endpoint": "https://push.example.com/sub/abc123",
    "keys": {"p256dh": "BPtestkey", "auth": "authsecret"},
}


def test_public_key_stable_and_requires_auth(seeded):
    assert seeded.get("/api/push/public-key").status_code == 401
    ha = login(seeded, CLIENT_A)
    k1 = seeded.get("/api/push/public-key", headers=ha).json()["key"]
    k2 = seeded.get("/api/push/public-key", headers=ha).json()["key"]
    assert k1 == k2 and len(k1) > 60  # klucz trwały (plik na wolumenie)


def test_subscribe_and_unsubscribe(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    assert r.status_code == 201
    # Idempotentne ponowienie tego samego endpointu.
    assert seeded.post("/api/push/subscribe", headers=ha, json=SUB).status_code == 201

    from dzik_os.db import db_session
    from dzik_os.models import PushSubscription

    with db_session() as db:
        assert db.query(PushSubscription).filter_by(endpoint=SUB["endpoint"]).count() == 1

    r = seeded.post("/api/push/unsubscribe", headers=ha, json={"endpoint": SUB["endpoint"]})
    assert r.status_code == 200
    with db_session() as db:
        assert db.query(PushSubscription).count() == 0


def test_message_triggers_push_to_recipient(seeded, monkeypatch):
    sent: list[tuple[str, str]] = []
    from dzik_os import push_service

    monkeypatch.setattr(
        push_service, "_send_one", lambda sub, payload: sent.append((sub.user_id, payload)) or True
    )
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)

    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads if t["with_user"]["display_name"] == "Klient Testowy A")
    r = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                    json={"body": "Sprawdź nowy plan"})
    assert r.status_code == 201
    assert len(sent) == 1
    assert sent[0][0] == client_id
    # Treść wiadomości NIE trafia do powiadomienia (tylko wezwanie).
    assert "Sprawdź nowy plan" not in sent[0][1]


def test_review_triggers_push_to_client(seeded, monkeypatch):
    sent = []
    from dzik_os import push_service

    monkeypatch.setattr(
        push_service, "_send_one", lambda sub, payload: sent.append(sub.user_id) or True
    )
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    r = seeded.post("/api/checkins", headers=ha, json={"week_start": "2026-09-07"})
    checkin_id = r.json()["id"]
    hc = login(seeded, COACH)
    r = seeded.post(f"/api/checkins/{checkin_id}/review", headers=hc,
                    json={"coach_response": "Dobra robota"})
    assert r.status_code == 200
    client_id = get_user_id(seeded, ha)
    assert client_id in sent


def test_reminder_loop_sends_for_matching_schedule(seeded, monkeypatch):
    sent = []
    from dzik_os import push_service, reminder_loop

    monkeypatch.setattr(
        push_service, "_send_one", lambda sub, payload: sent.append((sub.user_id, payload)) or True
    )

    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    client_id = get_user_id(seeded, ha)

    # Element harmonogramu klienta A: kreatyna o 08:00 codziennie (seed).
    # Data względem prawdziwego `today` — seed startuje harmonogram dziś,
    # więc zamrożony dzień z przeszłości nie miałby żadnych wystąpień.
    from datetime import time, timedelta

    from dzik_os.dates import local_today
    jutro = local_today() + timedelta(days=1)
    now = datetime.combine(jutro, time(8, 0), tzinfo=ZoneInfo("Europe/Warsaw"))
    count = reminder_loop._tick(now)
    assert count >= 1
    # Push wychodzi do klienta, ale z treścią NEUTRALNĄ — nazwa suplementu
    # (dana zdrowotna) NIGDY nie trafia na ekran blokady.
    assert any(uid == client_id for uid, _ in sent)
    assert all("Kreatyna" not in payload for _, payload in sent)
    # Pełna treść jest w centrum powiadomień (po zalogowaniu).
    inbox = seeded.get("/api/notifications", headers=ha).json()
    assert any("Kreatyna" in n["title"] for n in inbox["notifications"])

    # Druga iteracja w tej samej minucie/dniu nie dubluje wysyłki —
    # klucz idempotencji w bazie (przeżywa restart procesu).
    sent.clear()
    assert reminder_loop._tick(now) == 0

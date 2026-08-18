"""Wiadomości w czasie rzeczywistym: statusy doręczenia (wysłana →
dostarczona → przeczytana), deduplikacja client_msg_id, stabilna kolejność,
paginacja, bramka strony wątku dla kanału SSE (IDOR = 404), wygasła sesja
na kanale, magistrala zdarzeń, brak treści w push oraz walidacja formatów
audio (webm/m4a/mp3/ogg) po stronie backendu."""

import asyncio
import io
import threading

from conftest import CLIENT_A, CLIENT_B, COACH, get_user_id, login


def _thread_of_client_a(client, coach_headers):
    threads = client.get("/api/threads", headers=coach_headers).json()["threads"]
    return next(
        t for t in threads if t["with_user"]["display_name"] == "Klient Testowy A"
    )


# --- Wymiana między dwoma aktywnymi użytkownikami + statusy ---------------


def test_two_users_exchange_with_delivery_and_read_status(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    thread = _thread_of_client_a(seeded, hc)

    r = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                    json={"body": "Jak forma?"})
    assert r.status_code == 201
    sent = r.json()
    # Potwierdzenie wysłania: pełny, stabilny rekord wiadomości.
    assert sent["id"] and sent["created_at"]
    assert sent["delivered_at"] is None and sent["read_at"] is None
    assert sent["duplicate"] is False

    # U odbiorcy w liście wątków rośnie licznik nieprzeczytanych.
    threads_a = seeded.get("/api/threads", headers=ha).json()["threads"]
    ta = next(t for t in threads_a if t["id"] == thread["id"])
    assert ta["unread"] >= 1

    # Otwarcie wątku przez odbiorcę = dostarczona + przeczytana.
    msgs = seeded.get(f"/api/threads/{thread['id']}/messages", headers=ha).json()
    row = next(m for m in msgs["messages"] if m["id"] == sent["id"])
    assert row["read_at"] is not None and row["delivered_at"] is not None

    # Nadawca widzi status przeczytania; licznik odbiorcy spada do zera.
    msgs_c = seeded.get(f"/api/threads/{thread['id']}/messages", headers=hc).json()
    row_c = next(m for m in msgs_c["messages"] if m["id"] == sent["id"])
    assert row_c["read_at"] is not None
    threads_a = seeded.get("/api/threads", headers=ha).json()["threads"]
    assert next(t for t in threads_a if t["id"] == thread["id"])["unread"] == 0

    # Odpowiedź w drugą stronę działa tak samo.
    r = seeded.post(f"/api/threads/{thread['id']}/messages", headers=ha,
                    json={"body": "Dobra, trzymam plan"})
    assert r.status_code == 201


def test_explicit_read_endpoint_marks_and_counts(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    thread = _thread_of_client_a(seeded, hc)
    seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                json={"body": "Nowe wytyczne"})
    r = seeded.post(f"/api/threads/{thread['id']}/read", headers=ha)
    assert r.status_code == 200
    assert r.json()["marked_read"] >= 1
    # Idempotentne: drugi raz nic już nie oznacza.
    assert seeded.post(f"/api/threads/{thread['id']}/read",
                       headers=ha).json()["marked_read"] == 0
    threads_a = seeded.get("/api/threads", headers=ha).json()["threads"]
    assert next(t for t in threads_a if t["id"] == thread["id"])["unread"] == 0


# --- Deduplikacja client_msg_id -------------------------------------------


def test_duplicate_client_msg_id_returns_same_message(seeded):
    hc = login(seeded, COACH)
    thread = _thread_of_client_a(seeded, hc)
    payload = {"body": "Trening przełożony na 18:00",
               "client_msg_id": "test-dedup-0001"}
    r1 = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc, json=payload)
    r2 = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc, json=payload)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    assert r1.json()["duplicate"] is False and r2.json()["duplicate"] is True

    from dzik_os.db import db_session
    from dzik_os.models import Message

    with db_session() as db:
        assert (
            db.query(Message)
            .filter(Message.client_msg_id == "test-dedup-0001")
            .count()
            == 1
        )


def test_same_client_msg_id_from_other_author_is_new_message(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    thread = _thread_of_client_a(seeded, hc)
    payload = {"body": "x", "client_msg_id": "wspolny-id-123"}
    r1 = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc, json=payload)
    r2 = seeded.post(f"/api/threads/{thread['id']}/messages", headers=ha, json=payload)
    assert r1.json()["id"] != r2.json()["id"]


def test_invalid_client_msg_id_rejected(seeded):
    hc = login(seeded, COACH)
    thread = _thread_of_client_a(seeded, hc)
    r = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                    json={"body": "x", "client_msg_id": "za krótki i ze spacją"})
    assert r.status_code == 422


# --- Kolejność i paginacja -------------------------------------------------


def test_messages_sorted_by_created_at_then_id(seeded):
    hc = login(seeded, COACH)
    thread = _thread_of_client_a(seeded, hc)

    from dzik_os.db import db_session
    from dzik_os.models import Message

    coach_id = get_user_id(seeded, hc)
    # Dwa wiersze z IDENTYCZNYM created_at, id w odwrotnym porządku wstawiania.
    with db_session() as db:
        db.add(Message(id="HOS-MSG-ZZZ999", thread_id=thread["id"],
                       author_id=coach_id, body="drugi",
                       created_at="2026-08-18T10:00:00+00:00"))
        db.add(Message(id="HOS-MSG-AAA111", thread_id=thread["id"],
                       author_id=coach_id, body="pierwszy",
                       created_at="2026-08-18T10:00:00+00:00"))
    msgs = seeded.get(f"/api/threads/{thread['id']}/messages",
                      headers=hc).json()["messages"]
    keys = [(m["created_at"], m["id"]) for m in msgs]
    assert keys == sorted(keys)
    ids = [m["id"] for m in msgs]
    assert ids.index("HOS-MSG-AAA111") < ids.index("HOS-MSG-ZZZ999")


def test_pagination_cursor_returns_older_without_gaps(seeded):
    hc = login(seeded, COACH)
    thread = _thread_of_client_a(seeded, hc)
    for i in range(7):
        r = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                        json={"body": f"wiadomość {i}"})
        assert r.status_code == 201

    full = seeded.get(f"/api/threads/{thread['id']}/messages?limit=200",
                      headers=hc).json()["messages"]
    assert len(full) >= 7

    page1 = seeded.get(f"/api/threads/{thread['id']}/messages?limit=3",
                       headers=hc).json()
    assert len(page1["messages"]) == 3 and page1["has_more"] is True
    assert [m["id"] for m in page1["messages"]] == [m["id"] for m in full[-3:]]

    before = page1["messages"][0]["id"]
    page2 = seeded.get(
        f"/api/threads/{thread['id']}/messages?limit=3&before={before}",
        headers=hc).json()
    assert [m["id"] for m in page2["messages"]] == [m["id"] for m in full[-6:-3]]
    # Bez duplikatów i bez dziur między stronami.
    assert not {m["id"] for m in page1["messages"]} & {m["id"] for m in page2["messages"]}

    # Kursor spoza wątku → 404 (nie ujawniamy istnienia).
    r = seeded.get(
        f"/api/threads/{thread['id']}/messages?before=HOS-MSG-NIEISTNIEJE",
        headers=hc)
    assert r.status_code == 404


def test_pagination_does_not_mark_read(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    thread = _thread_of_client_a(seeded, hc)
    sent = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                       json={"body": "starsza"}).json()
    anchor = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                         json={"body": "nowsza"}).json()
    # Dociąganie starszych stron (before=...) nie zmienia liczników.
    seeded.get(
        f"/api/threads/{thread['id']}/messages?before={anchor['id']}", headers=ha)
    threads_a = seeded.get("/api/threads", headers=ha).json()["threads"]
    assert next(t for t in threads_a if t["id"] == thread["id"])["unread"] >= 2
    assert sent["id"]


# --- IDOR: historia, read, kanał -------------------------------------------


def test_thread_endpoints_idor_404_for_stranger(seeded):
    hc = login(seeded, COACH)
    hb = login(seeded, CLIENT_B)
    thread = _thread_of_client_a(seeded, hc)
    assert seeded.get(f"/api/threads/{thread['id']}/messages",
                      headers=hb).status_code == 404
    assert seeded.post(f"/api/threads/{thread['id']}/read",
                       headers=hb).status_code == 404
    assert seeded.post(f"/api/threads/{thread['id']}/messages", headers=hb,
                       json={"body": "podszywam się"}).status_code == 404


def test_events_channel_requires_auth(seeded):
    seeded.cookies.clear()
    assert seeded.get("/api/threads/events").status_code == 401


def test_deliver_event_gate_blocks_stranger_and_revoked_consent(seeded):
    """Bramka doręczenia zdarzenia SSE: obcy użytkownik nic nie dostaje;
    trener traci kanał razem z cofnięciem zgody kategorii komunikacja
    (ten sam kontrakt co require_thread_party)."""
    from dzik_os.routers.messages import _deliver_event

    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    thread = _thread_of_client_a(seeded, hc)
    sent = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                       json={"body": "poufna treść wątku"}).json()
    event = {"type": "message.new", "thread_id": thread["id"],
             "message": sent}

    stranger_id = get_user_id(seeded, hb)
    assert _deliver_event(stranger_id, dict(event)) is None

    client_id = get_user_id(seeded, ha)
    delivered = _deliver_event(client_id, dict(event))
    assert delivered is not None
    assert delivered["data"]["message"]["delivered_at"] is not None

    # Cofnięcie zgody „komunikacja" zamyka kanał trenera dla tego wątku.
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    for c in consents:
        if c["revoked_at"] is None and c["denied_at"] is None:
            seeded.post(f"/api/me/consents/{c['id']}/revoke", headers=ha)
    coach_id = get_user_id(seeded, hc)
    assert _deliver_event(coach_id, dict(event)) is None


def test_delivered_receipt_marks_message_and_notifies_author(seeded):
    from dzik_os import realtime
    from dzik_os.db import db_session
    from dzik_os.models import Message
    from dzik_os.routers.messages import _deliver_event

    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    thread = _thread_of_client_a(seeded, hc)
    sent = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                       json={"body": "status?"}).json()
    published = []
    original = realtime.bus.publish
    realtime.bus.publish = lambda uid, ev: published.append((uid, ev))
    try:
        _deliver_event(get_user_id(seeded, ha), {
            "type": "message.new", "thread_id": thread["id"], "message": sent,
        })
    finally:
        realtime.bus.publish = original
    with db_session() as db:
        assert db.get(Message, sent["id"]).delivered_at is not None
    coach_id = get_user_id(seeded, hc)
    receipts = [ev for uid, ev in published
                if uid == coach_id and ev["type"] == "message.delivered"]
    assert receipts and receipts[0]["message_id"] == sent["id"]


# --- Wygasła/unieważniona sesja na kanale ----------------------------------


def test_session_validity_check_for_stream(seeded):
    from dzik_os.db import db_session
    from dzik_os.security import session_is_active

    r = seeded.post("/api/auth/login", json=CLIENT_A)
    token = r.json()["token"]
    with db_session() as db:
        assert session_is_active(db, token) is True
        assert session_is_active(db, "nieistniejacy-token") is False
        assert session_is_active(db, None) is False
    seeded.post("/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"})
    with db_session() as db:
        assert session_is_active(db, token) is False
    # Kanał z unieważnionym tokenem nie otwiera się w ogóle (401 na wejściu).
    seeded.cookies.clear()
    assert seeded.get("/api/threads/events",
                      headers={"Authorization": f"Bearer {token}"}).status_code == 401


# --- Magistrala zdarzeń (logika reconnect/fallback po stronie serwera) -----


def test_bus_delivers_across_threads_and_cleans_up():
    from dzik_os.realtime import RealtimeBus

    bus = RealtimeBus()

    async def scenario():
        sub = bus.subscribe("HOS-USR-TEST")
        assert bus.has_subscriber("HOS-USR-TEST")
        # Publikacja z INNEGO wątku (endpointy sync działają w puli wątków).
        t = threading.Thread(
            target=bus.publish, args=("HOS-USR-TEST", {"type": "message.new", "x": 1})
        )
        t.start()
        t.join()
        event = await asyncio.wait_for(sub.queue.get(), timeout=2)
        assert event["type"] == "message.new"
        # Zdarzenie dla innego użytkownika nie trafia do tej kolejki.
        bus.publish("HOS-USR-INNY", {"type": "message.new"})
        await asyncio.sleep(0)
        assert sub.queue.empty()
        bus.unsubscribe(sub)
        assert not bus.has_subscriber("HOS-USR-TEST")

    asyncio.run(scenario())


def test_bus_overflow_collapses_to_resync():
    from dzik_os.realtime import QUEUE_MAXSIZE, RealtimeBus

    bus = RealtimeBus()

    async def scenario():
        sub = bus.subscribe("HOS-USR-WOLNY")
        for i in range(QUEUE_MAXSIZE + 10):
            bus.publish("HOS-USR-WOLNY", {"type": "message.new", "i": i})
        # call_soon_threadsafe z tej samej pętli — daj się wykonać callbackom.
        for _ in range(3):
            await asyncio.sleep(0)
        drained = []
        while not sub.queue.empty():
            drained.append(sub.queue.get_nowait())
        # Przepełnienie NIE gubi po cichu: w strumieniu pojawia się znacznik
        # resync (klient pobiera stan przez GET), a kolejka nie rośnie
        # w nieskończoność.
        assert any(e["type"] == "resync" for e in drained)
        assert len(drained) <= QUEUE_MAXSIZE
        bus.unsubscribe(sub)

    asyncio.run(scenario())


def test_send_publishes_realtime_event_to_recipient_and_author(seeded):
    from dzik_os import realtime

    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    thread = _thread_of_client_a(seeded, hc)
    published = []
    original = realtime.bus.publish
    realtime.bus.publish = lambda uid, ev: published.append((uid, ev))
    try:
        r = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                        json={"body": "zdarzenie na żywo"})
        assert r.status_code == 201
    finally:
        realtime.bus.publish = original
    client_id = get_user_id(seeded, ha)
    coach_id = get_user_id(seeded, hc)
    targets = {uid for uid, ev in published if ev["type"] == "message.new"}
    assert targets == {client_id, coach_id}


# --- Prywatność: push i audyt bez treści -----------------------------------


def test_push_for_new_message_has_no_body_content(seeded, monkeypatch):
    from dzik_os import push_service

    sent = []
    monkeypatch.setattr(
        push_service, "_send_one",
        lambda sub, payload: sent.append(payload) or True,
    )
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json={
        "endpoint": "https://push.example/p1",
        "keys": {"p256dh": "k", "auth": "a"},
    })
    secret = "wynik badań krwi 123"
    r = seeded.post(f"/api/threads/{_thread_of_client_a(seeded, hc)['id']}/messages",
                    headers=hc, json={"body": secret})
    assert r.status_code == 201
    assert sent and all(secret not in p for p in sent)


# --- Walidacja formatów audio po stronie backendu --------------------------

M4A = b"\x00\x00\x00\x1cftypM4A \x00\x00\x00\x00M4A mp42isom" + b"\x00" * 32
OGG = b"OggS" + b"\x00" * 60
MP3 = b"ID3" + b"\x00" * 60
WEBM = b"\x1aE\xdf\xa3" + b"\x00" * 64


def _upload_audio(client, headers, content, content_type, filename):
    return client.post(
        "/api/files", headers=headers,
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


def test_all_audio_formats_accepted_with_matching_content(seeded):
    ha = login(seeded, CLIENT_A)
    for content, ctype, name in (
        (WEBM, "audio/webm", "glosowka.webm"),
        (M4A, "audio/mp4", "glosowka.m4a"),   # iOS Safari (AAC)
        (MP3, "audio/mpeg", "glosowka.mp3"),
        (OGG, "audio/ogg", "glosowka.ogg"),
    ):
        r = _upload_audio(seeded, ha, content, ctype, name)
        assert r.status_code == 201, (ctype, r.text)
        assert r.json()["content_type"] == ctype


def test_audio_content_mismatch_rejected(seeded):
    ha = login(seeded, CLIENT_A)
    # Deklaracja audio/mp4 z zawartością WebM (i odwrotnie) → 415.
    assert _upload_audio(seeded, ha, WEBM, "audio/mp4",
                         "falszywka.m4a").status_code == 415
    assert _upload_audio(seeded, ha, M4A, "audio/webm",
                         "falszywka.webm").status_code == 415
    # Typ z parametrem kodeka NIE jest na allowliście — frontend wysyła typ
    # bazowy (baseMime); tu potwierdzamy fail-closed.
    assert _upload_audio(seeded, ha, WEBM, "audio/webm;codecs=opus",
                         "glosowka.webm").status_code == 415

"""Wspólny system powiadomień (migracja nr 14): planowanie w strefie
użytkownika (w tym DST Europe/Warsaw), idempotencja przez restart (klucz
w bazie), ciche godziny, anulowanie terminów, bramka „zadanie wykonane",
preferencje per kategoria × kanał, wygasłe subskrypcje, odmowa zgody,
wiele urządzeń, url kliknięcia per kategoria, centrum powiadomień i
monitoring doręczeń w /api/metrics."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from conftest import ADMIN, CLIENT_A, COACH, get_user_id, login

from dzik_os.dates import local_today

WARSAW = ZoneInfo("Europe/Warsaw")


def _nastepna_sroda() -> date:
    """Najbliższa środa PO dzisiejszym dniu — seed sieje harmonogramy od
    prawdziwego `today` (dates.local_today), więc zamrożona data ticku musi
    leżeć w przyszłości względem startu harmonogramu, nie być stałą."""
    d = local_today() + timedelta(days=1)
    while d.isoweekday() != 3:
        d += timedelta(days=1)
    return d


def _osma_rano(d: date) -> datetime:
    """08:00 czasu Warszawy danego dnia — wystąpienia planują się o 08:00
    lokalnie, a LATE_SEND_MAX to 30 minut; godzina UTC wpisana na sztywno
    psuje się przy zmianie czasu."""
    return datetime.combine(d, time(8, 0), tzinfo=WARSAW)


def _oplac_seedowe_terminy() -> None:
    """Wycisz szum płatności z seeda. Terminy płatności seed liczy od
    PRAWDZIWEGO `today`, a przypomnienie o zaległości wychodzi co 7 dni
    (days_over % 7 == 0) — przy zamrożonym ticku to loteria zależna od dnia
    uruchomienia testów (18.08 cicho, 23.08 strzał). Testy planowania mają
    sprawdzać planowanie; płatności mają własne testy z własnymi datami."""
    from dzik_os.db import db_session
    from dzik_os.models import PaymentRecord
    from dzik_os.payment_state import DUE_STATUSES

    with db_session() as db:
        for rec in db.query(PaymentRecord).filter(
            PaymentRecord.status.in_(DUE_STATUSES)
        ):
            rec.status = "PAID"
        db.commit()

SUB = {
    "endpoint": "https://push.example.com/sub/dev-1",
    "keys": {"p256dh": "BPtestkey", "auth": "authsecret"},
}
SUB2 = {
    "endpoint": "https://push.example.com/sub/dev-2",
    "keys": {"p256dh": "BPtestkey2", "auth": "authsecret2"},
}


def _capture_push(monkeypatch, result: bool = True):
    sent: list[tuple[str, str]] = []
    from dzik_os import push_service

    monkeypatch.setattr(
        push_service, "_send_one",
        lambda sub, payload: sent.append((sub.user_id, payload)) or result,
    )
    return sent


def _tick(dt: datetime) -> int:
    from dzik_os import reminder_loop

    return reminder_loop._tick(dt)


def _inbox(client, headers) -> dict:
    return client.get("/api/notifications", headers=headers).json()


# ---------------------------------------------------------------------------
# Harmonogram: strefy czasowe i DST
# ---------------------------------------------------------------------------


def test_schedule_reminder_respects_user_timezone(seeded, monkeypatch):
    """Zmiana strefy użytkownika przesuwa moment wysyłki: 08:00 w Nowym
    Jorku to 12:00 UTC (EDT), a nie 06:00 UTC jak dla Warszawy."""
    sent = _capture_push(monkeypatch)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    r = seeded.put("/api/notifications/settings", headers=ha,
                   json={"timezone": "America/New_York"})
    assert r.status_code == 200

    # 06:00 UTC = 08:00 Warszawy, ale dopiero 02:00 w NY — nic nie wychodzi.
    assert _tick(datetime(2026, 9, 16, 6, 0, tzinfo=UTC)) == 0
    assert sent == []
    # 12:00 UTC = 08:00 EDT — przypomnienia z harmonogramu 08:00 wychodzą.
    assert _tick(datetime(2026, 9, 16, 12, 0, tzinfo=UTC)) >= 1
    assert sent


def test_dst_transition_europe_warsaw(seeded, monkeypatch):
    """08:00 Europe/Warsaw to 06:00 UTC latem i 07:00 UTC zimą — zoneinfo
    rozstrzyga przejście DST (2026: zmiana czasu 25 października)."""
    sent = _capture_push(monkeypatch)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)

    # Lato (CEST, UTC+2): środa 2026-09-16.
    assert _tick(datetime(2026, 9, 16, 6, 0, tzinfo=UTC)) >= 1
    n_summer = len(sent)
    assert n_summer >= 1

    # Zima (CET, UTC+1): środa 2026-10-28 — o 06:00 UTC jest dopiero
    # 07:00 lokalnie, wysyłka następuje o 07:00 UTC.
    assert _tick(datetime(2026, 10, 28, 6, 0, tzinfo=UTC)) == 0
    assert len(sent) == n_summer
    assert _tick(datetime(2026, 10, 28, 7, 0, tzinfo=UTC)) >= 1
    assert len(sent) > n_summer


# ---------------------------------------------------------------------------
# Idempotencja (restart) i nadganianie
# ---------------------------------------------------------------------------


def test_no_duplicates_across_process_restart(seeded, monkeypatch):
    """Dedup żyje w bazie (UNIQUE(user_id, dedup_key)), nie w pamięci —
    restart procesu w tej samej minucie nie dubluje wysyłki."""
    import importlib

    sent = _capture_push(monkeypatch)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    now = datetime(2026, 9, 16, 6, 0, tzinfo=UTC)
    assert _tick(now) >= 1
    first = len(sent)

    # „Restart maszyny": przeładowanie modułu pętli zeruje każdy stan
    # w pamięci procesu; dedup w bazie musi przetrwać.
    from dzik_os import reminder_loop

    importlib.reload(reminder_loop)
    assert reminder_loop._tick(now) == 0
    assert len(sent) == first


def test_late_delivery_after_downtime_not_lost(seeded, monkeypatch):
    """Maszyna leżała o 08:00 — tick o 08:10 lokalnego czasu nadal wysyła
    (w granicy LATE_SEND_MAX); przypomnienie nie ginie."""
    sent = _capture_push(monkeypatch)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    assert _tick(datetime(2026, 9, 16, 6, 10, tzinfo=UTC)) >= 1
    assert sent


def test_very_late_occurrence_is_not_sent(seeded, monkeypatch):
    """Wystąpienie starsze niż LATE_SEND_MAX nie jest wysyłane (ani nawet
    materializowane) — przypomnienie sprzed godzin to szum."""
    sent = _capture_push(monkeypatch)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    # 10:00 UTC = 12:00 lokalnie — 4 h po porze 08:00.
    assert _tick(datetime(2026, 9, 16, 10, 0, tzinfo=UTC)) == 0
    assert sent == []


# ---------------------------------------------------------------------------
# Ciche godziny i dni aktywne
# ---------------------------------------------------------------------------


def test_quiet_hours_silence_push_but_keep_center(seeded, monkeypatch):
    sent = _capture_push(monkeypatch)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    r = seeded.put("/api/notifications/settings", headers=ha, json={
        "quiet_hours_start": "21:00", "quiet_hours_end": "09:00",
    })
    assert r.status_code == 200
    # 08:00 lokalnie przypada w cichych godzinach (zakres przez północ).
    assert _tick(datetime(2026, 9, 16, 6, 0, tzinfo=UTC)) >= 1
    assert sent == []  # push wyciszony
    inbox = _inbox(seeded, ha)
    assert inbox["unread"] >= 1  # centrum dostaje wpis mimo ciszy


def test_active_days_skip_planning(seeded, monkeypatch):
    sent = _capture_push(monkeypatch)
    _oplac_seedowe_terminy()
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    # Środa (3) wyłączona z dni aktywnych.
    r = seeded.put("/api/notifications/settings", headers=ha,
                   json={"active_days": "1,2,4,5,6,7"})
    assert r.status_code == 200
    sroda = _nastepna_sroda()
    assert _tick(_osma_rano(sroda)) == 0
    assert sent == []
    # Czwartek działa normalnie.
    assert _tick(_osma_rano(sroda + timedelta(days=1))) >= 1


# ---------------------------------------------------------------------------
# Anulowanie terminu i bramka „zadanie wykonane"
# ---------------------------------------------------------------------------


def _client_schedule(client, coach_headers, client_id):
    return client.get(
        f"/api/clients/{client_id}/schedule", headers=coach_headers
    ).json()["items"]


def test_paused_item_cancels_scheduled_notification(seeded, monkeypatch):
    _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)

    # 05:30 UTC = 07:30 lokalnie: wystąpienia 08:00 są już zaplanowane
    # (SCHEDULED), ale jeszcze nie doręczone.
    assert _tick(datetime(2026, 9, 16, 5, 35, tzinfo=UTC)) == 0
    kreatyna = next(i for i in _client_schedule(seeded, hc, client_id)
                    if "Kreatyna" in i["name"])
    r = seeded.post(f"/api/schedule/{kreatyna['id']}/status?status=PAUSED", headers=hc)
    assert r.status_code == 200

    assert _tick(datetime(2026, 9, 16, 6, 0, tzinfo=UTC)) >= 1
    inbox = _inbox(seeded, ha)
    assert all("Kreatyna" not in n["title"] for n in inbox["notifications"])

    from dzik_os.db import db_session
    from dzik_os.models import Notification

    with db_session() as db:
        row = (
            db.query(Notification)
            .filter(Notification.source == f"schedule_item:{kreatyna['id']}")
            .one()
        )
        assert row.status == "CANCELLED"


def test_completed_task_suppresses_reminder(seeded, monkeypatch):
    """Zadanie odhaczone przed porą przypomnienia = przypomnienie nie
    wychodzi (sprawdzenie przy wysyłce, nie przy planowaniu)."""
    _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    witamina = next(i for i in _client_schedule(seeded, hc, client_id)
                    if "Witamina" in i["name"])
    r = seeded.post(
        f"/api/clients/{client_id}/schedule/{witamina['id']}/complete",
        headers=ha, json={"completed_on": "2026-09-16", "status": "DONE"},
    )
    assert r.status_code == 201

    _tick(datetime(2026, 9, 16, 6, 0, tzinfo=UTC))
    inbox = _inbox(seeded, ha)
    titles = [n["title"] for n in inbox["notifications"]]
    assert all("Witamina" not in t for t in titles)  # wykonane → cisza
    assert any("Kreatyna" in t for t in titles)  # niewykonane → przypomnienie


def test_submitted_checkin_suppresses_report_reminder(seeded, monkeypatch):
    _capture_push(monkeypatch)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    # Raport za tydzień z niedzielą 2026-09-20 (week_start = poniedziałek).
    r = seeded.post("/api/checkins", headers=ha, json={"week_start": "2026-09-14"})
    assert r.status_code == 201
    # Element harmonogramu "Raport tygodniowy": niedziela 18:00 (16:00 UTC).
    _tick(datetime(2026, 9, 20, 16, 0, tzinfo=UTC))
    inbox = _inbox(seeded, ha)
    assert all(n["category"] != "RAPORT" for n in inbox["notifications"])


def test_paid_payment_suppresses_due_reminder(seeded, monkeypatch):
    _capture_push(monkeypatch)
    _oplac_seedowe_terminy()
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    termin = _nastepna_sroda()
    r = seeded.post("/api/payments/schedules", headers=hc, json={
        "client_id": client_id, "package_name": "Pakiet testowy",
        "amount_cents": 20000, "first_due_date": termin.isoformat(),
    })
    record_id = r.json()["record_id"]
    # Opłacona przed 08:00 → przypomnienie o terminie nie wychodzi.
    # Status PAID nadaje wyłącznie mark-paid (maszyna stanów płatności —
    # frontend nie ustawia „opłacona" zwykłym /status).
    r = seeded.post(f"/api/payments/records/{record_id}/mark-paid", headers=hc,
                    json={})
    assert r.status_code == 200
    _tick(_osma_rano(termin))
    inbox = _inbox(seeded, ha)
    assert all(n["category"] != "PLATNOSC" for n in inbox["notifications"])


# ---------------------------------------------------------------------------
# Kanał push: wygasłe subskrypcje, zgoda, wiele urządzeń
# ---------------------------------------------------------------------------


def test_expired_subscription_is_removed_on_send(seeded, monkeypatch):
    _capture_push(monkeypatch, result=False)  # dostawca: 404/410
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)

    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                json={"body": "Halo"})

    from dzik_os.db import db_session
    from dzik_os.models import PushSubscription

    with db_session() as db:
        assert db.query(PushSubscription).count() == 0
    # Powiadomienie w centrum mimo martwej subskrypcji.
    assert _inbox(seeded, ha)["unread"] >= 1


def test_consent_revocation_stops_push_center_still_works(seeded, monkeypatch):
    sent = _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    reminders_consent = next(c for c in consents if c["category"] == "przypomnienia")
    r = seeded.post(f"/api/me/consents/{reminders_consent['id']}/revoke", headers=ha)
    assert r.status_code == 200

    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                json={"body": "Wiadomość po cofnięciu zgody"})
    assert sent == []  # subskrypcje usunięte wraz ze zgodą
    assert _inbox(seeded, ha)["unread"] >= 1  # centrum (in-app) działa dalej


def test_push_goes_to_all_devices(seeded, monkeypatch):
    sent = _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB2)

    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                json={"body": "Do obu urządzeń"})
    assert [uid for uid, _ in sent] == [client_id, client_id]


# ---------------------------------------------------------------------------
# Treść i url kliknięcia per kategoria
# ---------------------------------------------------------------------------


def test_click_url_and_neutral_push_per_category(seeded, monkeypatch):
    import json as jsonlib

    sent = _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)

    # WIADOMOSC → /wiadomosci/{thread_id}
    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                json={"body": "Tajna treść zdrowotna"})
    payload = jsonlib.loads(sent[-1][1])
    assert payload["url"] == f"/wiadomosci/{thread['id']}"
    assert "Tajna treść zdrowotna" not in sent[-1][1]

    # ZMIANA_PLANU → /plan
    plans = seeded.get(f"/api/clients/{client_id}/plans", headers=hc).json()["plans"]
    plan_id = plans[0]["id"]
    r = seeded.post(f"/api/plans/{plan_id}/versions", headers=hc, json={
        "reason": "Korekta objętości",
        "days": [{"name": "A", "weekday": 1, "exercises": []}],
    })
    assert r.status_code in (200, 201)
    payload = jsonlib.loads(sent[-1][1])
    assert payload["url"] == "/plan"

    inbox = _inbox(seeded, ha)
    by_cat = {n["category"]: n for n in inbox["notifications"]}
    assert by_cat["WIADOMOSC"]["url"] == f"/wiadomosci/{thread['id']}"
    assert by_cat["ZMIANA_PLANU"]["url"] == "/plan"


def test_document_notification_neutral_push(seeded, monkeypatch):
    import io
    import json as jsonlib

    from conftest import make_png

    sent = _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    up = seeded.post(f"/api/files?client_id={client_id}", headers=hc,
                     files={"file": ("wyniki.png", io.BytesIO(make_png()), "image/png")})
    file_id = up.json()["id"]
    r = seeded.post("/api/documents", headers=hc, json={
        "client_id": client_id, "file_id": file_id,
        "title": "Wyniki badań krwi", "category": "WYNIKI",
    })
    assert r.status_code == 201
    # Push neutralny: tytuł dokumentu (potencjalnie zdrowotny) NIE wychodzi
    # na ekran blokady; url prowadzi do Dokumentów.
    assert all("Wyniki badań" not in payload for _, payload in sent)
    payload = jsonlib.loads(sent[-1][1])
    assert payload["url"] == "/dokumenty"
    inbox = _inbox(seeded, ha)
    doc = next(n for n in inbox["notifications"] if n["category"] == "DOKUMENT")
    assert "Wyniki badań krwi" in doc["title"]  # pełna treść po zalogowaniu


# ---------------------------------------------------------------------------
# Preferencje, częstotliwość, centrum, metryki
# ---------------------------------------------------------------------------


def test_category_disabled_suppresses_everything(seeded, monkeypatch):
    sent = _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    r = seeded.put("/api/notifications/settings", headers=ha, json={
        "preferences": [
            {"category": "WIADOMOSC", "channel": "PUSH", "enabled": False},
            {"category": "WIADOMOSC", "channel": "CENTER", "enabled": False},
        ],
    })
    assert r.status_code == 200
    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                json={"body": "Wyciszona kategoria"})
    assert sent == []
    assert _inbox(seeded, ha)["unread"] == 0


def test_report_frequency_weekly_vs_daily(seeded, monkeypatch):
    """Częstotliwość przypomnienia o raporcie: WEEKLY = raz w tygodniu
    (klucz idempotencji per tydzień ISO), DAILY = każdy zaplanowany dzień."""
    _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    # Codzienny element RAPORT o 09:00 (07:00 UTC latem).
    r = seeded.post("/api/schedule", headers=hc, json={
        "client_id": client_id, "name": "Uzupełnij raport", "category": "RAPORT",
        "time_of_day": "09:00", "days_of_week": "1,2,3,4,5,6,7",
    })
    assert r.status_code == 201
    seeded.put("/api/notifications/settings", headers=ha,
               json={"raport_frequency": "WEEKLY"})

    _tick(datetime(2026, 9, 16, 7, 0, tzinfo=UTC))  # środa
    _tick(datetime(2026, 9, 17, 7, 0, tzinfo=UTC))  # czwartek, ten sam tydzień
    inbox = _inbox(seeded, ha)
    raport = [n for n in inbox["notifications"] if n["category"] == "RAPORT"]
    assert len(raport) == 1  # WEEKLY: jedno przypomnienie na tydzień

    seeded.put("/api/notifications/settings", headers=ha,
               json={"raport_frequency": "DAILY"})
    _tick(datetime(2026, 9, 25, 7, 0, tzinfo=UTC))  # piątek, kolejny tydzień
    _tick(datetime(2026, 9, 26, 7, 0, tzinfo=UTC))  # sobota
    inbox = _inbox(seeded, ha)
    raport = [n for n in inbox["notifications"] if n["category"] == "RAPORT"]
    assert len(raport) == 3  # DAILY: każdy dzień osobno


def test_center_read_and_read_all(seeded, monkeypatch):
    _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    for body in ("Pierwsza", "Druga"):
        seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                    json={"body": body})
    inbox = _inbox(seeded, ha)
    assert inbox["unread"] == 2

    first_id = inbox["notifications"][0]["id"]
    r = seeded.post(f"/api/notifications/{first_id}/read", headers=ha)
    assert r.status_code == 200
    assert _inbox(seeded, ha)["unread"] == 1

    # Cudze powiadomienie: 404 (bez wycieku istnienia).
    hb = login(seeded, {"email": "klient.b@example.com", "password": "KlientB#2026!x"})
    assert seeded.post(f"/api/notifications/{first_id}/read", headers=hb).status_code == 404

    r = seeded.post("/api/notifications/read-all", headers=ha)
    assert r.status_code == 200
    assert _inbox(seeded, ha)["unread"] == 0
    # Filtr nieprzeczytanych.
    r = seeded.get("/api/notifications?unread_only=true", headers=ha)
    assert r.json()["notifications"] == []


def test_settings_roundtrip_and_validation(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/notifications/settings", headers=ha)
    assert r.status_code == 200
    data = r.json()
    assert {"categories", "channels", "preferences", "settings"} <= set(data)
    # Domyślne: PUSH/CENTER on, EMAIL off.
    assert data["preferences"]["WIADOMOSC:PUSH"] is True
    assert data["preferences"]["WIADOMOSC:EMAIL"] is False

    assert seeded.put("/api/notifications/settings", headers=ha,
                      json={"timezone": "Nie/Istnieje"}).status_code == 422
    assert seeded.put("/api/notifications/settings", headers=ha,
                      json={"active_days": "8,9"}).status_code == 422
    assert seeded.put("/api/notifications/settings", headers=ha,
                      json={"quiet_hours_start": "25:00"}).status_code == 422

    r = seeded.put("/api/notifications/settings", headers=ha, json={
        "timezone": "Europe/London", "quiet_hours_start": "22:00",
        "quiet_hours_end": "06:30", "active_days": "1,2,3,4,5",
        "raport_frequency": "WEEKLY",
        "preferences": [
            {"category": "PLATNOSC", "channel": "EMAIL", "enabled": True},
        ],
    })
    assert r.status_code == 200
    data = seeded.get("/api/notifications/settings", headers=ha).json()
    assert data["settings"]["timezone"] == "Europe/London"
    assert data["settings"]["quiet_hours_start"] == "22:00"
    assert data["settings"]["active_days"] == "1,2,3,4,5"
    assert data["settings"]["raport_frequency"] == "WEEKLY"
    assert data["preferences"]["PLATNOSC:EMAIL"] is True


def test_metrics_expose_delivery_counters(seeded, monkeypatch):
    _capture_push(monkeypatch)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    seeded.post("/api/push/subscribe", headers=ha, json=SUB)
    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                json={"body": "Metryki"})
    hadm = login(seeded, ADMIN)
    counters = seeded.get("/api/metrics", headers=hadm).json()["counters"]
    assert counters["notif_sent_center"] >= 1
    assert counters["notif_sent_push"] >= 1
    assert "notif_sent_email" in counters
    assert "notif_suppressed" in counters


def test_email_channel_optional_and_neutral(seeded, monkeypatch):
    """E-mail jako opcjonalny kanał awaryjny: po włączeniu preferencji
    wychodzi przez notifications_provider z NEUTRALNĄ treścią."""
    _capture_push(monkeypatch)
    emails: list[dict] = []

    class _Provider:
        name = "test"

        def send_email(self, *, to: str, subject: str, body: str) -> bool:
            emails.append({"to": to, "subject": subject, "body": body})
            return True

    from dzik_os import notifications_provider

    monkeypatch.setattr(notifications_provider, "provider", _Provider())
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    seeded.put("/api/notifications/settings", headers=ha, json={
        "preferences": [
            {"category": "WIADOMOSC", "channel": "EMAIL", "enabled": True},
        ],
    })
    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                json={"body": "Poufna treść"})
    assert len(emails) == 1
    assert emails[0]["to"] == "klient.a@example.com"
    assert "Poufna treść" not in emails[0]["subject"] + emails[0]["body"]

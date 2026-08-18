"""Cotygodniowy digest trenera (runda 6b.8).

Zasady, których pilnują te testy:
- digest to METADANE OPERACYJNE pracy trenera, nigdy ranking podopiecznych
  (brak punktacji, ocen i sortowania po „wyniku" człowieka),
- liczby pochodzą z tego samego kodu co panel i karta klienta
  (aggregates.client_flags_bulk) — żaden ekran nie pokazuje innej prawdy,
- widzi go wyłącznie trener i wyłącznie dla SWOICH aktywnych podopiecznych,
- poniedziałkowe powiadomienie jest idempotentne (restart pętli nie mnoży),
  neutralne w treści i przy braku dostawcy e-mail nie wychodzi na zewnątrz.
"""

from datetime import UTC, datetime, timedelta

from conftest import CLIENT_A, COACH, get_user_id, login


def _digest(client, headers):
    r = client.get("/api/coach/weekly-digest", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_digest_matches_dashboard_and_client_list(seeded):
    """Ta sama prawda co panel: liczba klientów i grupy zgadzają się
    z dashboardem oraz listą klientów (wspólna warstwa agregacji)."""
    hc = login(seeded, COACH)
    digest = _digest(seeded, hc)
    dashboard = seeded.get("/api/coach/dashboard", headers=hc).json()
    rows = seeded.get("/api/coach/clients", headers=hc).json()["clients"]

    assert digest["active_clients"] == dashboard["active_clients"]
    assert len(digest["awaiting_review"]) == dashboard["awaiting_review"]
    assert len(digest["checkin_overdue"]) == dashboard["checkin_overdue_clients"]
    assert len(digest["payment_overdue"]) == dashboard["payment_overdue_clients"]

    overdue_names = {row["display_name"] for row in digest["checkin_overdue"]}
    expected = {
        r["display_name"] for r in rows
        if r["relationship_status"] == "ACTIVE" and r["flags"]["checkin_overdue"]
    }
    assert overdue_names == expected


def test_digest_has_no_ranking_signals(seeded):
    """Brak punktacji i ocen; sortowanie alfabetyczne w obrębie grupy —
    kolejność nigdy nie sugeruje „lepszego" podopiecznego."""
    hc = login(seeded, COACH)
    digest = _digest(seeded, hc)
    blob = str(digest).lower()
    for forbidden in ("score", "rank", "punkt", "ocena", "pozycja", "miejsce"):
        assert forbidden not in blob
    for group in ("reported_this_week", "awaiting_review", "checkin_overdue",
                  "payment_overdue", "flagged"):
        names = [row["display_name"].lower() for row in digest[group]]
        assert names == sorted(names), group


def test_reported_this_week_reflects_fresh_checkin(seeded):
    """Raport wysłany w tym tygodniu przenosi klienta do „zaraportowali"
    i zdejmuje go z listy zalegających."""
    from dzik_os.dates import local_today

    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    today = local_today()
    week_start = (today - timedelta(days=today.isoweekday() - 1)).isoformat()

    seeded.post("/api/checkins", headers=ha, json={
        "week_start": week_start, "weight_kg": 80.0, "trainings_done": 3,
    })
    digest = _digest(seeded, hc)
    assert id_a in {row["client_id"] for row in digest["reported_this_week"]}
    assert id_a not in {row["client_id"] for row in digest["checkin_overdue"]}


def test_digest_is_coach_only_and_scoped_to_own_clients(seeded):
    """Klient i admin nie mają wglądu; trener widzi wyłącznie swoich."""
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/coach/weekly-digest", headers=ha).status_code == 403
    hadm = login(seeded, {"email": "admin@example.com", "password": "DzikAdmin#2026"})
    assert seeded.get("/api/coach/weekly-digest", headers=hadm).status_code == 403

    hc = login(seeded, COACH)
    digest = _digest(seeded, hc)
    own = {
        row["client_id"]
        for row in seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    }
    for group in ("reported_this_week", "awaiting_review", "checkin_overdue",
                  "payment_overdue", "flagged"):
        assert {row["client_id"] for row in digest[group]} <= own


def _monday_utc() -> datetime:
    """Najbliższy poniedziałek 07:00 czasu trenera wyrażony w UTC."""
    from dzik_os.dates import tz_for_user

    tz = tz_for_user(None)
    now = datetime.now(UTC).astimezone(tz)
    monday = now + timedelta(days=(1 - now.isoweekday()) % 7)
    return monday.replace(hour=7, minute=0, second=0, microsecond=0).astimezone(UTC)


def test_monday_digest_is_planned_once_per_week(seeded):
    """Poniedziałek rano: dokładnie jedno powiadomienie na trenera i tydzień
    — kolejne ticki (także po restarcie) nie tworzą duplikatu."""
    from dzik_os import notifications
    from dzik_os.db import db_session

    hc = login(seeded, COACH)
    coach_id = get_user_id(seeded, hc)
    monday = _monday_utc()
    with db_session() as db:
        first = notifications.plan_weekly_digest(db, monday)
        second = notifications.plan_weekly_digest(db, monday)
    assert first >= 1
    assert second == 0

    from dzik_os.models import Notification

    with db_session() as db:
        rows = (
            db.query(Notification)
            .filter(Notification.user_id == coach_id,
                    Notification.category == "PODSUMOWANIE")
            .all()
        )
        assert len(rows) == 1
        assert rows[0].url == "/trener/podsumowanie"


def test_digest_not_planned_on_other_weekdays(seeded):
    from dzik_os import notifications
    from dzik_os.db import db_session

    tuesday = _monday_utc() + timedelta(days=1)
    with db_session() as db:
        assert notifications.plan_weekly_digest(db, tuesday) == 0


def test_digest_notification_carries_no_client_data(seeded, monkeypatch):
    """Treść powiadomienia (także e-maila) jest neutralna: bez nazwisk,
    liczb i danych zdrowotnych — szczegóły dopiero po zalogowaniu."""
    sent: list[tuple[str, str, str]] = []
    from dzik_os import notifications_provider

    class FakeProvider:
        name = "fake"

        def send_email(self, *, to: str, subject: str, body: str) -> bool:
            sent.append((to, subject, body))
            return True

    monkeypatch.setattr(notifications_provider, "provider", FakeProvider())

    from dzik_os import notifications
    from dzik_os.db import db_session

    hc = login(seeded, COACH)
    coach_id = get_user_id(seeded, hc)
    monday = _monday_utc()
    with db_session() as db:
        notifications.plan_weekly_digest(db, monday)
        notifications.dispatch_due(db, monday)

    assert sent, "przy skonfigurowanym dostawcy e-mail digest powinien wyjść"
    blob = " ".join(s[1] + " " + s[2] for s in sent)
    names = [
        row["display_name"]
        for row in seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    ]
    for name in names:
        assert name not in blob
    for forbidden in ("ból", "obserwacj", "zł", "PLN"):
        assert forbidden not in blob
    assert coach_id  # sanity

    from dzik_os.models import Notification

    with db_session() as db:
        row = (
            db.query(Notification)
            .filter(Notification.category == "PODSUMOWANIE")
            .one()
        )
        assert row.status == "SENT"
        assert "email" in (row.channels or "")


def test_without_email_provider_digest_stays_in_app(seeded):
    """NullNotificationProvider milczy: digest istnieje w centrum
    powiadomień, ale nic nie wychodzi poza aplikację."""
    from dzik_os import notifications
    from dzik_os.db import db_session
    from dzik_os.models import Notification

    monday = _monday_utc()
    with db_session() as db:
        notifications.plan_weekly_digest(db, monday)
        notifications.dispatch_due(db, monday)
        row = (
            db.query(Notification)
            .filter(Notification.category == "PODSUMOWANIE")
            .one()
        )
        assert row.status == "SENT"
        assert "center" in (row.channels or "")
        assert "email" not in (row.channels or "")

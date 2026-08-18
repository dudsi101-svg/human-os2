"""Zarządzanie sesjami: serwerowe unieważnianie (wylogowanie, wybrana
sesja, wszystkie pozostałe), rotacja tokenu przy zmianie hasła, wygaśnięcie,
ponowne użycie unieważnionego tokenu, limit prób zmiany hasła, żądania
równoległe. Zasada: serwer przechowuje wyłącznie hash SHA-256 tokenu."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from conftest import CLIENT_A, COACH, get_user_id, login


def _token(headers: dict) -> str:
    return headers["Authorization"].removeprefix("Bearer ")


def test_logout_with_bearer_only_revokes_server_side(seeded):
    """Regresja audytu: wylogowanie gołym fetchem bez nagłówka nie unieważniało
    sesji. Klient API wysyła Bearer — serwer musi ustawić revoked_at."""
    h = login(seeded, CLIENT_A)
    assert seeded.post("/api/auth/logout", headers=h).status_code == 200
    # Ponowne użycie unieważnionego tokenu — zawsze 401.
    assert seeded.get("/api/auth/me", headers=h).status_code == 401
    assert seeded.get("/api/me/today", headers=h).status_code == 401

    from dzik_os.hos_bridge import event_store

    assert "SESSION_LOGGED_OUT" in [e["event_type"] for e in event_store().all()]


def test_logout_via_cookie_still_works(seeded):
    """Ścieżka ciasteczka (httponly dzik_session) pozostaje wspierana."""
    h = login(seeded, CLIENT_A)
    seeded.cookies.set("dzik_session", _token(h))
    seeded.post("/api/auth/logout")
    seeded.cookies.clear()
    assert seeded.get("/api/auth/me", headers=h).status_code == 401


def test_logout_without_token_is_ok_and_noop(seeded):
    assert seeded.post("/api/auth/logout").status_code == 200
    # Nieznany token też nie wybucha (idempotentne wylogowanie).
    bogus = {"Authorization": "Bearer nie-ma-takiego-tokenu"}
    assert seeded.post("/api/auth/logout", headers=bogus).status_code == 200


def test_sessions_list_marks_current_and_shows_metadata(seeded):
    h1 = login(seeded, CLIENT_A)
    h2 = login(seeded, CLIENT_A)
    r = seeded.get("/api/auth/sessions", headers=h2)
    assert r.status_code == 200
    sessions = r.json()["sessions"]
    assert len(sessions) == 2
    current = [s for s in sessions if s["current"]]
    assert len(current) == 1
    for s in sessions:
        assert s["id"].startswith("HOS-SES-")
        assert s["created_at"] and s["expires_at"]
        assert "user_agent" in s and "last_used_at" in s
        # Żadnych tokenów ani hashy w odpowiedzi.
        assert "token" not in s and "token_hash" not in s
    # Bieżąca sesja właśnie została użyta → ma znacznik ostatniego użycia.
    assert current[0]["last_used_at"]
    # Druga sesja dostaje znacznik po pierwszym użyciu tokenu.
    assert seeded.get("/api/auth/me", headers=h1).status_code == 200
    sessions = seeded.get("/api/auth/sessions", headers=h2).json()["sessions"]
    assert all(s["last_used_at"] for s in sessions)


def test_revoke_single_session(seeded):
    h1 = login(seeded, CLIENT_A)
    h2 = login(seeded, CLIENT_A)
    sessions = seeded.get("/api/auth/sessions", headers=h1).json()["sessions"]
    other = next(s for s in sessions if not s["current"])
    r = seeded.post(f"/api/auth/sessions/{other['id']}/revoke", headers=h1)
    assert r.status_code == 200
    assert seeded.get("/api/auth/me", headers=h2).status_code == 401
    assert seeded.get("/api/auth/me", headers=h1).status_code == 200
    # Ponowne unieważnienie tej samej sesji → 404 (już nieaktywna).
    assert seeded.post(f"/api/auth/sessions/{other['id']}/revoke",
                       headers=h1).status_code == 404


def test_cannot_revoke_another_users_session(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    coach_session = seeded.get("/api/auth/sessions", headers=hc).json()["sessions"][0]
    r = seeded.post(f"/api/auth/sessions/{coach_session['id']}/revoke", headers=ha)
    assert r.status_code == 404  # bez ujawniania istnienia cudzej sesji
    assert seeded.get("/api/auth/me", headers=hc).status_code == 200


def test_revoke_all_other_sessions(seeded):
    h1 = login(seeded, CLIENT_A)
    h2 = login(seeded, CLIENT_A)
    h3 = login(seeded, CLIENT_A)
    r = seeded.post("/api/auth/sessions/revoke-others", headers=h1)
    assert r.status_code == 200
    assert r.json()["revoked"] == 2
    assert seeded.get("/api/auth/me", headers=h1).status_code == 200
    assert seeded.get("/api/auth/me", headers=h2).status_code == 401
    assert seeded.get("/api/auth/me", headers=h3).status_code == 401

    from dzik_os.hos_bridge import event_store

    assert "SESSIONS_REVOKED" in [e["event_type"] for e in event_store().all()]


def test_expired_token_is_rejected_and_hidden_from_list(seeded):
    from dzik_os.db import db_session
    from dzik_os.models import AuthSession

    h1 = login(seeded, CLIENT_A)
    h2 = login(seeded, CLIENT_A)
    user_id = get_user_id(seeded, h1)
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with db_session() as db:
        rows = (db.query(AuthSession)
                .filter(AuthSession.user_id == user_id,
                        AuthSession.revoked_at.is_(None))
                .order_by(AuthSession.created_at).all())
        rows[0].expires_at = past  # najstarsza (h1) wygasa
    assert seeded.get("/api/auth/me", headers=h1).status_code == 401
    sessions = seeded.get("/api/auth/sessions", headers=h2).json()["sessions"]
    assert len(sessions) == 1 and sessions[0]["current"]


def test_password_change_rotation_prevents_old_token_reuse(seeded):
    h_old = login(seeded, CLIENT_A)
    r = seeded.post("/api/auth/change-password", headers=h_old,
                    json={"current_password": CLIENT_A["password"],
                          "new_password": "RotacjaTokenu#1"})
    assert r.status_code == 200
    new_token = r.json()["token"]
    assert new_token != _token(h_old)
    # Stary token nie działa nigdzie — także do ponownej zmiany hasła.
    assert seeded.get("/api/auth/me", headers=h_old).status_code == 401
    reuse = seeded.post("/api/auth/change-password", headers=h_old,
                        json={"current_password": "RotacjaTokenu#1",
                              "new_password": "JeszczeInne#123"})
    assert reuse.status_code == 401
    h_new = {"Authorization": f"Bearer {new_token}"}
    assert seeded.get("/api/auth/me", headers=h_new).status_code == 200


def test_password_change_event_has_no_secrets(seeded):
    h = login(seeded, CLIENT_A)
    r = seeded.post("/api/auth/change-password", headers=h,
                    json={"current_password": CLIENT_A["password"],
                          "new_password": "AudytBezSekretow#1"})
    assert r.status_code == 200
    token = r.json()["token"]

    import json

    from dzik_os.hos_bridge import event_store

    events = event_store().all()
    changed = [e for e in events if e["event_type"] == "PASSWORD_CHANGED"]
    assert changed and changed[-1]["payload"]["token_rotated"] is True
    assert changed[-1]["payload"]["sessions_revoked"] >= 1
    # Żadne zdarzenie audytu nie zawiera tokenu ani hasła w postaci jawnej.
    dump = json.dumps(events, default=str)
    assert token not in dump
    assert CLIENT_A["password"] not in dump
    assert "AudytBezSekretow#1" not in dump


def test_password_change_rate_limit(seeded):
    h = login(seeded, CLIENT_A)
    for _ in range(5):
        r = seeded.post("/api/auth/change-password", headers=h,
                        json={"current_password": "zle-haslo-123",
                              "new_password": "PoprawneNowe#12"})
        assert r.status_code == 403
    r = seeded.post("/api/auth/change-password", headers=h,
                    json={"current_password": CLIENT_A["password"],
                          "new_password": "PoprawneNowe#12"})
    assert r.status_code == 429


def test_parallel_requests_with_concurrent_logout(seeded):
    """Żądania równoległe (wiele kart): brak 500 przy wyścigu odczytów z
    wylogowaniem; po wylogowaniu token konsekwentnie odrzucany."""
    h = login(seeded, CLIENT_A)

    def me() -> int:
        return seeded.get("/api/auth/me", headers=h).status_code

    def do_logout() -> int:
        return seeded.post("/api/auth/logout", headers=h).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda i: do_logout() if i == 5 else me(), range(10)))
    assert set(statuses) <= {200, 401}
    assert seeded.get("/api/auth/me", headers=h).status_code == 401


def test_parallel_logins_create_independent_sessions(seeded):
    with ThreadPoolExecutor(max_workers=4) as pool:
        headers = list(pool.map(lambda _: login(seeded, CLIENT_A), range(4)))
    for h in headers:
        assert seeded.get("/api/auth/me", headers=h).status_code == 200
    tokens = {_token(h) for h in headers}
    assert len(tokens) == 4  # każde logowanie ma własny, niezależny token


def test_server_stores_only_token_hash(seeded):
    """Kontrakt: w bazie nie ma tokenu w postaci jawnej — wyłącznie
    SHA-256 (64 znaki hex), zgodny z hashem tokenu klienta."""
    import hashlib

    from dzik_os.db import db_session
    from dzik_os.models import AuthSession

    h = login(seeded, CLIENT_A)
    token = _token(h)
    with db_session() as db:
        rows = db.query(AuthSession).all()
        assert rows
        for row in rows:
            assert len(row.token_hash) == 64
            assert token != row.token_hash
        assert any(row.token_hash == hashlib.sha256(token.encode()).hexdigest()
                   for row in rows)

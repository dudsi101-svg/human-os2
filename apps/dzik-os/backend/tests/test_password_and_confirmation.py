"""Wymuszona zmiana hasła (mechanizm legacy) + potwierdzanie zgód przez
podmiot + dostęp do załączników wiadomości. Nowe konta powstają z
zaproszenia (tests/test_invitations.py) — klient sam ustawia hasło."""

import io

from conftest import CLIENT_A, COACH, create_activated_client, login


def _create_client(seeded, hc, email="swiezak@example.com",
                   password="WlasneHaslo#123"):
    return create_activated_client(seeded, hc, email, password)


def test_forced_password_change_blocks_until_changed(seeded):
    """Mechanizm must_change_password pozostaje w systemie (konta
    historyczne); egzekwowanie: blokada wszystkiego poza zmianą hasła."""
    from dzik_os.db import db_session
    from dzik_os.models import User

    hc = login(seeded, COACH)
    _create_client(seeded, hc, password="StartoweHaslo#1")
    with db_session() as db:
        user = db.query(User).filter(User.email == "swiezak@example.com").one()
        user.must_change_password = True
    creds = {"email": "swiezak@example.com", "password": "StartoweHaslo#1"}
    r = seeded.post("/api/auth/login", json=creds)
    assert r.status_code == 200
    assert r.json()["user"]["must_change_password"] is True
    hn = {"Authorization": f"Bearer {r.json()['token']}"}

    # Serwer blokuje wszystko poza zmianą hasła / wylogowaniem / auth/me.
    r = seeded.get("/api/me/today", headers=hn)
    assert r.status_code == 403
    assert r.json()["detail"] == "PASSWORD_CHANGE_REQUIRED"
    assert seeded.get("/api/me/consents", headers=hn).status_code == 403
    assert seeded.get("/api/auth/me", headers=hn).status_code == 200

    # Złe obecne hasło → 403; za krótkie nowe → 422.
    r = seeded.post("/api/auth/change-password", headers=hn,
                    json={"current_password": "zle", "new_password": "NoweHaslo#123"})
    assert r.status_code == 403
    r = seeded.post("/api/auth/change-password", headers=hn,
                    json={"current_password": "StartoweHaslo#1", "new_password": "krotkie"})
    assert r.status_code == 422

    # Poprawna zmiana odblokowuje konto i ROTUJE token: stary jest
    # unieważniony, dalsza praca wymaga nowego tokenu z odpowiedzi.
    r = seeded.post("/api/auth/change-password", headers=hn,
                    json={"current_password": "StartoweHaslo#1",
                          "new_password": "NoweWlasne#123"})
    assert r.status_code == 200
    assert seeded.get("/api/me/today", headers=hn).status_code == 401
    hn = {"Authorization": f"Bearer {r.json()['token']}"}
    assert seeded.get("/api/me/today", headers=hn).status_code in (200, 403)
    # (403 może dotyczyć tylko braku roli — sprawdź konkretnie brak blokady hasła)
    r = seeded.get("/api/me/consents", headers=hn)
    assert r.status_code == 200

    # Stare hasło przestaje działać, nowe działa.
    assert seeded.post("/api/auth/login", json=creds).status_code == 401
    assert seeded.post("/api/auth/login", json={
        "email": creds["email"], "password": "NoweWlasne#123"}).status_code == 200


def test_password_change_revokes_all_old_sessions_and_rotates_token(seeded):
    h1 = login(seeded, CLIENT_A)
    h2 = login(seeded, CLIENT_A)  # druga sesja (drugie urządzenie)
    r = seeded.post("/api/auth/change-password", headers=h1,
                    json={"current_password": CLIENT_A["password"],
                          "new_password": "ZupelnieNowe#12"})
    assert r.status_code == 200
    # Zero aktywnych starych tokenów: bieżący też został zrotowany.
    assert seeded.get("/api/auth/me", headers=h1).status_code == 401
    assert seeded.get("/api/auth/me", headers=h2).status_code == 401
    hn = {"Authorization": f"Bearer {r.json()['token']}"}
    assert seeded.get("/api/auth/me", headers=hn).status_code == 200


def test_onboarding_consent_requires_subject_confirmation(seeded):
    hc = login(seeded, COACH)
    client_id = _create_client(seeded, hc, "potwierdz@example.com")
    r = seeded.post("/api/auth/login", json={
        "email": "potwierdz@example.com", "password": "WlasneHaslo#123"})
    hn = {"Authorization": f"Bearer {r.json()['token']}"}

    consents = seeded.get("/api/me/consents", headers=hn).json()["consents"]
    onboarding = next(c for c in consents if c["revoked_at"] is None)
    assert onboarding["confirmed_at"] is None  # czeka na potwierdzenie

    r = seeded.post(f"/api/me/consents/{onboarding['id']}/confirm", headers=hn)
    assert r.status_code == 200
    assert r.json()["confirmed_at"]

    # Zgoda nadana samodzielnie jest potwierdzona od razu; cudzej nie można
    # potwierdzić.
    ha = login(seeded, CLIENT_A)
    r = seeded.post(f"/api/me/consents/{onboarding['id']}/confirm", headers=ha)
    assert r.status_code == 404

    from dzik_os.hos_bridge import event_store

    assert "CONSENT_CONFIRMED" in [e["event_type"] for e in event_store().all()]
    assert client_id  # sanity


def test_thread_attachment_visible_to_both_parties(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    threads = seeded.get("/api/threads", headers=hc).json()["threads"]
    thread = next(t for t in threads
                  if t["with_user"]["display_name"] == "Klient Testowy A")
    from conftest import make_png

    up = seeded.post("/api/files", headers=hc, files={
        "file": ("technika.png", io.BytesIO(make_png()), "image/png")})
    file_id = up.json()["id"]
    r = seeded.post(f"/api/threads/{thread['id']}/messages", headers=hc,
                    json={"body": "Zobacz załącznik", "file_id": file_id})
    assert r.status_code == 201
    # Obie strony wątku pobiorą plik; osoba trzecia nie.
    assert seeded.get(f"/api/files/{file_id}", headers=hc).status_code == 200
    assert seeded.get(f"/api/files/{file_id}", headers=ha).status_code == 200
    hb = login(seeded, {"email": "klient.b@example.com", "password": "KlientB#2026!x"})
    assert seeded.get(f"/api/files/{file_id}", headers=hb).status_code == 404


def test_migrations_apply_to_existing_v1_database(tmp_path):
    """Baza z v1 (bez nowych kolumn/tabel) dostaje wszystkie kolejne
    migracje (ALTER-y v2, nowe tabele monitoringu v3) bez utraty danych."""
    from sqlalchemy import create_engine, text

    from dzik_os.db import MIGRATIONS, run_migrations

    eng = create_engine(f"sqlite:///{tmp_path}/old.db")
    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, "
            "description TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO schema_migrations(version, description) "
                          "VALUES (1, 'initial')"))
        conn.execute(text("CREATE TABLE users (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE consents (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE schedule_items (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE weekly_checkins (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE workout_entries (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE auth_sessions (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE progress_photos (id VARCHAR(40) PRIMARY KEY)"))
    applied = run_migrations(eng)
    assert applied == [v for v, _, _ in MIGRATIONS if v != 1]
    with eng.connect() as conn:
        cols_u = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(users)")]
        cols_c = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(consents)")]
        cols_w = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(weekly_checkins)")]
        cols_s = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(auth_sessions)")]
        tables = {
            r[0] for r in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "must_change_password" in cols_u
    assert "confirmed_at" in cols_c
    # Migracja nr 10: granularne kategorie zgód (RODO).
    for col in ("category", "legal_basis", "source", "denied_at"):
        assert col in cols_c, col
    assert "rating" in cols_w
    assert "last_used_at" in cols_s
    assert {"schedule_completions", "observations", "daily_nutrition_logs"} <= tables
    assert {"exercises", "food_products"} <= tables
    # Migracja 11: MFA (TOTP) + zaproszenia + reset hasła.
    assert {"totp_secret", "totp_confirmed_at", "totp_last_counter"} <= set(cols_u)
    assert {
        "client_invitations", "password_reset_tokens",
        "mfa_recovery_codes", "mfa_challenges",
    } <= tables
    # Migracja 12: jakość raportów — częściowe zdjęcia, ujęcie/kolejność,
    # klucze idempotencji.
    assert "photos_expected" in cols_w
    with eng.connect() as conn:
        cols_p = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(progress_photos)")]
    assert {"pose", "position"} <= set(cols_p)
    assert "idempotency_keys" in tables

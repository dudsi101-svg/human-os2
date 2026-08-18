from conftest import ADMIN, CLIENT_A, COACH, login


def test_login_ok_and_me(seeded):
    headers = login(seeded, COACH)
    r = seeded.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "Lubelski Dzik"
    assert body["roles"] == ["COACH"]
    assert body["id"].startswith("HOS-USR-")
    assert body["identity_id"].startswith("HOS-ID-")


def test_login_wrong_password_is_401_without_account_disclosure(seeded):
    r1 = seeded.post("/api/auth/login",
                     json={"email": COACH["email"], "password": "zle-haslo-123"})
    r2 = seeded.post("/api/auth/login",
                     json={"email": "nie.istnieje@example.com", "password": "cokolwiek1"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


def test_login_rate_limit(seeded):
    for _ in range(5):
        r = seeded.post("/api/auth/login",
                        json={"email": CLIENT_A["email"], "password": "zle-haslo"})
        assert r.status_code == 401
    r = seeded.post("/api/auth/login", json=CLIENT_A)
    assert r.status_code == 429


def test_logout_revokes_session(seeded):
    """Wylogowanie z nagłówkiem Bearer (tak wysyła klient API frontendu)
    unieważnia sesję po stronie serwera — bez polegania na ciasteczku."""
    headers = login(seeded, ADMIN)
    assert seeded.get("/api/auth/me", headers=headers).status_code == 200
    seeded.post("/api/auth/logout", headers=headers)
    assert seeded.get("/api/auth/me", headers=headers).status_code == 401


def test_unauthenticated_requests_rejected(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/coach/clients").status_code == 401
    assert client.get("/api/me/today").status_code == 401


def test_password_never_in_responses(seeded):
    headers = login(seeded, ADMIN)
    r = seeded.get("/api/admin/users", headers=headers)
    assert "password" not in r.text and "hash" not in r.text

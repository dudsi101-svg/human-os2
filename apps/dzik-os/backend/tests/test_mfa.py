"""MFA (TOTP RFC 6238): konfiguracja, logowanie dwuetapowe, okno czasowe,
ochrona przed powtórnym użyciem kodu, kody odzyskiwania, wymuszanie dla
ról COACH/ADMIN."""

import json
import time

from conftest import CLIENT_A, COACH, login

from dzik_os.totp import hotp, totp_at, verify_totp


def _wait_out_of_boundary():
    """Testy liczą kody względem bieżącego okna 30 s — chwilę przed granicą
    okna poczekaj, żeby kod nie zdążył się zestarzeć między obliczeniem
    a weryfikacją."""
    while time.time() % 30 > 27:
        time.sleep(0.4)


def _current_counter() -> int:
    return int(time.time() // 30)


def _enable_mfa(client, headers) -> tuple[str, list[str]]:
    """Konfiguracja MFA na koncie: setup → kod → kody odzyskiwania."""
    _wait_out_of_boundary()
    r = client.post("/api/auth/mfa/setup", headers=headers)
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    assert r.json()["otpauth_uri"].startswith("otpauth://totp/")
    r = client.post("/api/auth/mfa/enable", headers=headers,
                    json={"code": totp_at(secret, time.time())})
    assert r.status_code == 200, r.text
    codes = r.json()["recovery_codes"]
    assert len(codes) == 10
    return secret, codes


def test_totp_reference_vectors():
    """Wektor testowy RFC 6238 (SHA-1, sekret '12345678901234567890'):
    T=59 s → kod 94287082 (tu 6 cyfr: 287082)."""
    import base64

    secret = base64.b32encode(b"12345678901234567890").decode()
    assert totp_at(secret, 59) == "287082"
    assert verify_totp(secret, "287082", timestamp=59) is not None
    assert verify_totp(secret, "287082", timestamp=59 + 3 * 30) is None


def test_mfa_login_requires_code_and_rejects_bad_one(seeded):
    ha = login(seeded, CLIENT_A)
    secret, _codes = _enable_mfa(seeded, ha)
    # Logowanie hasłem zwraca wyzwanie MFA, nie sesję.
    r = seeded.post("/api/auth/login", json=CLIENT_A)
    assert r.status_code == 200
    body = r.json()
    assert body.get("mfa_required") is True and "token" not in body
    mfa_token = body["mfa_token"]
    # Zły kod → 401 + zdarzenie audytowe (bez kodu).
    r = seeded.post("/api/auth/mfa/verify",
                    json={"mfa_token": mfa_token, "code": "000000"})
    assert r.status_code == 401
    from dzik_os.hos_bridge import event_store

    events = [e["event_type"] for e in event_store().all()]
    assert "LOGIN_MFA_FAILED" in events
    # Dobry kod → pełna sesja. Kod użyty przy enable ma ten sam licznik,
    # więc bierzemy kod NASTĘPNEGO okna (okno ±1 przyjmuje go od razu,
    # a ochrona przed replayem nie blokuje, bo licznik jest wyższy).
    _wait_out_of_boundary()
    code = hotp(secret, _current_counter() + 1)
    r = seeded.post("/api/auth/mfa/verify",
                    json={"mfa_token": mfa_token, "code": code})
    assert r.status_code == 200
    assert "token" in r.json() and r.json()["user"]["mfa_enabled"] is True
    hn = {"Authorization": f"Bearer {r.json()['token']}"}
    assert seeded.get("/api/auth/me", headers=hn).status_code == 200
    # Wyzwanie jest jednorazowe.
    r = seeded.post("/api/auth/mfa/verify",
                    json={"mfa_token": mfa_token, "code": code})
    assert r.status_code == 401


def test_mfa_time_window_and_replay_protection(seeded):
    ha = login(seeded, CLIENT_A)
    secret, _codes = _enable_mfa(seeded, ha)
    # Wyzeruj licznik ostatnio użytego kodu (enable właśnie zużyło bieżące
    # okno) — test okna czasowego zaczyna od czystego stanu.
    from dzik_os.db import db_session
    from dzik_os.models import User

    with db_session() as db:
        u = db.query(User).filter(User.email == CLIENT_A["email"]).one()
        u.totp_last_counter = None

    def challenge():
        r = seeded.post("/api/auth/login", json=CLIENT_A)
        return r.json()["mfa_token"]

    _wait_out_of_boundary()
    counter = _current_counter()
    # Kod z poprzedniego okna (±1 krok) jest akceptowany...
    r = seeded.post("/api/auth/mfa/verify", json={
        "mfa_token": challenge(), "code": hotp(secret, counter - 1)})
    assert r.status_code == 200
    # ...ale ten sam kod użyty ponownie — już nie (replay).
    r = seeded.post("/api/auth/mfa/verify", json={
        "mfa_token": challenge(), "code": hotp(secret, counter - 1)})
    assert r.status_code == 401
    # Kod sprzed 3 okien (90 s) — poza oknem, odrzucony.
    r = seeded.post("/api/auth/mfa/verify", json={
        "mfa_token": challenge(), "code": hotp(secret, counter - 3)})
    assert r.status_code == 401
    # Bieżący kod (licznik wyższy niż ostatnio użyty) działa.
    r = seeded.post("/api/auth/mfa/verify", json={
        "mfa_token": challenge(), "code": hotp(secret, counter)})
    assert r.status_code == 200


def test_recovery_code_login_is_single_use_and_regeneration_invalidates(seeded):
    ha = login(seeded, CLIENT_A)
    secret, codes = _enable_mfa(seeded, ha)

    def challenge():
        return seeded.post("/api/auth/login", json=CLIENT_A).json()["mfa_token"]

    # Logowanie kodem odzyskiwania.
    r = seeded.post("/api/auth/mfa/verify",
                    json={"mfa_token": challenge(), "code": codes[0]})
    assert r.status_code == 200
    hn = {"Authorization": f"Bearer {r.json()['token']}"}
    # Ten sam kod odzyskiwania drugi raz — odmowa.
    r = seeded.post("/api/auth/mfa/verify",
                    json={"mfa_token": challenge(), "code": codes[0]})
    assert r.status_code == 401
    # Pozostało 9 kodów.
    status = seeded.get("/api/auth/mfa/status", headers=hn).json()
    assert status["enabled"] is True and status["recovery_codes_left"] == 9
    # Regeneracja (wymaga kodu TOTP) unieważnia stare kody.
    _wait_out_of_boundary()
    r = seeded.post("/api/auth/mfa/recovery-codes/regenerate", headers=hn,
                    json={"code": hotp(secret, _current_counter() + 1)})
    assert r.status_code == 200
    new_codes = r.json()["recovery_codes"]
    assert len(new_codes) == 10 and set(new_codes) != set(codes)
    r = seeded.post("/api/auth/mfa/verify",
                    json={"mfa_token": challenge(), "code": codes[1]})
    assert r.status_code == 401  # stary kod po regeneracji nie działa
    r = seeded.post("/api/auth/mfa/verify",
                    json={"mfa_token": challenge(), "code": new_codes[0]})
    assert r.status_code == 200


def test_mfa_enforced_for_coach_until_configured(seeded, monkeypatch):
    from dzik_os.config import settings

    monkeypatch.setattr(settings, "mfa_required_roles", "COACH,ADMIN")
    r = seeded.post("/api/auth/login", json=COACH)
    assert r.status_code == 200
    assert r.json()["user"]["mfa_setup_required"] is True
    hc = {"Authorization": f"Bearer {r.json()['token']}"}
    # Okres przejściowy: WYŁĄCZNIE konfiguracja MFA (i podstawy konta).
    r = seeded.get("/api/coach/clients", headers=hc)
    assert r.status_code == 403 and r.json()["detail"] == "MFA_SETUP_REQUIRED"
    assert seeded.get("/api/auth/me", headers=hc).status_code == 200
    assert seeded.get("/api/auth/mfa/status", headers=hc).status_code == 200
    # Konfiguracja odblokowuje konto (bieżąca sesja pozostaje ważna).
    secret, _codes = _enable_mfa(seeded, hc)
    assert seeded.get("/api/coach/clients", headers=hc).status_code == 200
    # COACH nie może wyłączyć MFA (obowiązkowe dla roli).
    _wait_out_of_boundary()
    r = seeded.post("/api/auth/mfa/disable", headers=hc,
                    json={"code": hotp(secret, _current_counter() + 5)})
    assert r.status_code == 403
    # Kolejne logowanie wymaga już kodu.
    r = seeded.post("/api/auth/login", json=COACH)
    assert r.json().get("mfa_required") is True


def test_client_mfa_is_optional_and_can_be_disabled(seeded):
    ha = login(seeded, CLIENT_A)
    # Bez MFA klient loguje się jak dotąd.
    assert seeded.get("/api/me/today", headers=ha).status_code == 200
    secret, _codes = _enable_mfa(seeded, ha)
    # Wyłączenie (rola CLIENT nie jest na liście wymaganych) — kodem TOTP.
    _wait_out_of_boundary()
    r = seeded.post("/api/auth/mfa/disable", headers=ha,
                    json={"code": hotp(secret, _current_counter() + 1)})
    assert r.status_code == 200
    # Logowanie znów jednoetapowe.
    r = seeded.post("/api/auth/login", json=CLIENT_A)
    assert "token" in r.json() and "mfa_required" not in r.json()


def test_mfa_secrets_and_codes_never_in_audit(seeded):
    ha = login(seeded, CLIENT_A)
    secret, codes = _enable_mfa(seeded, ha)
    from dzik_os.hos_bridge import event_store

    events = json.dumps(event_store().all())
    assert secret not in events
    for code in codes:
        assert code not in events
    assert "MFA_ENABLED" in events


def test_security_events_history_without_secrets(seeded):
    ha = login(seeded, CLIENT_A)
    secret, codes = _enable_mfa(seeded, ha)
    # Nieudane MFA przy logowaniu + logowanie kodem odzyskiwania.
    mfa_token = seeded.post("/api/auth/login", json=CLIENT_A).json()["mfa_token"]
    seeded.post("/api/auth/mfa/verify", json={"mfa_token": mfa_token, "code": "000000"})
    r = seeded.post("/api/auth/mfa/verify",
                    json={"mfa_token": mfa_token, "code": codes[0]})
    hn = {"Authorization": f"Bearer {r.json()['token']}"}
    r = seeded.get("/api/auth/security-events", headers=hn)
    assert r.status_code == 200
    events = r.json()["events"]
    actions = {e["action"] for e in events}
    assert {"MFA_ENABLED", "LOGIN_MFA_FAILED", "MFA_RECOVERY_CODE_USED",
            "LOGIN_SUCCEEDED"} <= actions
    dump = json.dumps(events)
    assert secret not in dump
    for code in codes:
        assert code not in dump


def test_security_events_are_scoped_to_own_account(seeded):
    ha = login(seeded, CLIENT_A)
    _enable_mfa(seeded, ha)
    hc = login(seeded, COACH)
    r = seeded.get("/api/auth/security-events", headers=hc)
    assert r.status_code == 200
    assert all("MFA_ENABLED" != e["action"] for e in r.json()["events"])

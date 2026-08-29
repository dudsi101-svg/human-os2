"""Awaryjny reset hasła (0.53.13): jedyna ścieżka odzyskania dostępu
bez SMTP musi być bezpieczna — nowe hasło jednorazowe, stare sesje
martwe, audyt bez treści hasła, żadnego wskrzeszania kont SUSPENDED."""

import pytest
from conftest import CLIENT_A, login

from dzik_os import hos_bridge
from dzik_os.bootstrap import MIN_PASSWORD_LEN
from dzik_os.db import db_session
from dzik_os.models import User
from dzik_os.resetuj_haslo import resetuj_haslo

NOWE = "Awaryjne#2026!reset"


def test_reset_wymienia_haslo_uniewaznia_sesje_i_wymusza_zmiane(seeded):
    # Stara sesja żyje przed resetem…
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/auth/me", headers=ha).status_code == 200

    resetuj_haslo(CLIENT_A["email"], NOWE)

    # …a po resecie jest martwa (reset = przejęcie kontroli nad kontem).
    assert seeded.get("/api/auth/me", headers=ha).status_code == 401
    # Stare hasło nie działa.
    r = seeded.post("/api/auth/login", json=CLIENT_A)
    assert r.status_code == 401
    # Nowe działa i od razu wymusza zmianę (hasło startowe jednorazowe).
    r = seeded.post("/api/auth/login",
                    json={"email": CLIENT_A["email"], "password": NOWE})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["must_change_password"] is True


def test_odmowy_nieistniejace_konto_suspended_i_za_krotkie_haslo(seeded):
    with pytest.raises(ValueError, match="nie istnieje"):
        resetuj_haslo("nikt@example.com", NOWE)
    with pytest.raises(ValueError, match=f"mniej niż {MIN_PASSWORD_LEN}"):
        resetuj_haslo(CLIENT_A["email"], "krotkie")

    with db_session() as db:
        db.query(User).filter(User.email == CLIENT_A["email"]).update(
            {"status": "SUSPENDED"}
        )
        db.commit()
    with pytest.raises(ValueError, match="SUSPENDED"):
        resetuj_haslo(CLIENT_A["email"], NOWE)


def test_zdarzenie_audytowe_bez_tresci_hasla(seeded):
    resetuj_haslo(CLIENT_A["email"], NOWE)
    zdarzenia = [
        e for e in hos_bridge.event_store().all()
        if e.get("event_type") == "PASSWORD_RESET_BY_OPERATOR"
    ]
    assert zdarzenia, "brak zdarzenia resetu w łańcuchu"
    import json as _json
    for e in zdarzenia:
        surowe = _json.dumps(e, ensure_ascii=False)
        assert NOWE not in surowe
        assert e["payload"].get("sessions_revoked") is not None

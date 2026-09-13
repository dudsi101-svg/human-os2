"""Diagnostyka produkcji tylko do odczytu (0.54.5): raport niesie
wymagane sekcje i NIE niesie sekretów; nic nie zapisuje."""

import json

from conftest import COACH, login

from dzik_os import diagnostyka, hos_bridge
from dzik_os.db import db_session
from dzik_os.models import User


def test_raport_ma_sekcje_i_zero_sekretow(seeded, monkeypatch):
    monkeypatch.delenv("DZIK_SMTP_HOST", raising=False)
    r = diagnostyka.raport()
    assert set(r) >= {"srodowisko", "konta", "relacje", "zaproszenia", "plany",
                      "zdarzenia_doreczen_30_dni"}
    assert r["srodowisko"]["dostawca_poczty"] == "null"
    assert "DZIK_SMTP_HOST" in r["srodowisko"]["smtp_brakuje"]
    trener = next(k for k in r["konta"] if k["email"] == COACH["email"])
    assert trener["role"] == ["COACH"] and trener["status"] == "ACTIVE"
    assert any(rel["trener"] == COACH["email"] and rel["zgoda_wspolpracy"] for rel in r["relacje"])
    assert r["plany"]  # seed ma plany/raporty

    tekst = json.dumps(r, ensure_ascii=False)
    with db_session() as db:
        for u in db.query(User).all():
            assert u.password_hash not in tekst
            if u.totp_secret:
                assert u.totp_secret not in tekst
    for zakazane in ("password_hash", "token_hash", "totp_secret", "$2b$"):
        assert zakazane not in tekst


def test_raport_widzi_zaproszenie_i_powod_niedoreczenia(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/clients", headers=hc,
                    json={"client_email": "zapraszany@example.com", "client_name": "Zapraszany"})
    assert r.status_code == 201, r.text
    assert r.json()["invitation"]["reason"] == "no_provider"

    rap = diagnostyka.raport()
    zap = next(z for z in rap["zaproszenia"] if z["klient"] == "zapraszany@example.com")
    assert zap["aktywne"] is True and zap["uzyte"] is None
    zd = [z for z in rap["zdarzenia_doreczen_30_dni"]
          if z["typ"] == "CLIENT_INVITED" and "zapraszany@example.com" in z["kogo"]]
    assert zd and zd[0]["doreczenie"] == "manual" and zd[0]["powod"] == "no_provider"
    # Raport nie zapisuje niczego w audycie.
    przed = len(hos_bridge.event_store().all())
    diagnostyka.raport()
    assert len(hos_bridge.event_store().all()) == przed


def test_main_wypisuje_json(seeded, capsys):
    assert diagnostyka.main([]) == 0
    dane = json.loads(capsys.readouterr().out)
    assert dane["srodowisko"]["wersja"]

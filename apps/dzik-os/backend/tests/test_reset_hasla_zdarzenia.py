"""Zdarzenia resetu hasła wg faktycznej wysyłki (audyt P0-4, 0.53.4).

Odpowiedź HTTP jest ZAWSZE identyczna (antyenumeracja) — prawda
o doręczeniu żyje wyłącznie w pokwitowaniach (Receipt) i łańcuchu
audytu."""

from dzik_os.db import db_session
from dzik_os.models import Receipt
from dzik_os.routers import auth as auth_router


class FakeProvider:
    def __init__(self, name: str, wynik: bool):
        self.name = name
        self.wynik = wynik

    def send_email(self, **kw) -> bool:
        return self.wynik


def _akcje_resetu() -> list[str]:
    with db_session() as db:
        return [
            r.action for r in db.query(Receipt)
            .filter(Receipt.action.like("PASSWORD_RESET%"))
            .all()
        ]


def _zadaj(client):
    r = client.post("/api/auth/password-reset/request",
                    json={"email": "klient.a@example.com"})
    assert r.status_code == 200
    return r.json()


def test_sukces_wysylki_daje_link_sent(seeded, monkeypatch):
    monkeypatch.setattr(auth_router, "notifications", FakeProvider("smtp", True))
    _zadaj(seeded)
    akcje = _akcje_resetu()
    assert "PASSWORD_RESET_REQUESTED" in akcje
    assert "PASSWORD_RESET_LINK_SENT" in akcje
    assert "PASSWORD_RESET_SEND_FAILED" not in akcje


def test_porazka_wysylki_daje_send_failed(seeded, monkeypatch):
    monkeypatch.setattr(auth_router, "notifications", FakeProvider("smtp", False))
    odp_porazka = _zadaj(seeded)
    akcje = _akcje_resetu()
    assert "PASSWORD_RESET_SEND_FAILED" in akcje
    assert "PASSWORD_RESET_LINK_SENT" not in akcje
    # Świat nie widzi różnicy: identyczna odpowiedź przy sukcesie.
    monkeypatch.setattr(auth_router, "notifications", FakeProvider("smtp", True))
    assert odp_porazka == _zadaj(seeded)


def test_brak_dostawcy_ma_powod_no_provider(seeded, monkeypatch):
    monkeypatch.setattr(auth_router, "notifications", FakeProvider("null", False))
    _zadaj(seeded)
    assert "PASSWORD_RESET_SEND_FAILED" in _akcje_resetu()
    # Powód no_provider żyje w niemutowalnym łańcuchu audytu.
    from dzik_os.hos_bridge import event_store

    zdarzenia = [e for e in event_store().all()
                 if e.get("event_type") == "PASSWORD_RESET_SEND_FAILED"]
    assert zdarzenia and zdarzenia[-1]["payload"]["reason"] == "no_provider"

"""Endpoint testowy poczty (0.61.0): flaga, role, 202 z identyfikatorem, poczta
wyłączona = 503 z nazwami zmiennych, inicjalizacja przy starcie bez zmiennych."""

from __future__ import annotations

import pytest
from conftest import ADMIN, CLIENT_A, COACH, login

from dzik_os import mailer, poczta_start
from dzik_os.config import settings
from dzik_os.routers import mail_admin

URL = "/api/admin/mail/test"


def _cfg(enabled: bool = True) -> mailer.MailConfig:
    return mailer.MailConfig(host="smtp-relay.brevo.com", port=587, user="u", password="p",
                             mail_from="Dzik OS <test@mail.dzik-os.com>", enabled=enabled)


@pytest.fixture()
def poczta(seeded, monkeypatch):
    """Poczta „włączona” bez sieci: `mailer.send_email` podmieniony na rejestrator."""
    wyslane: list[dict] = []

    def fake_send(to, subject, text, html=None, cfg=None, sleep=None):
        wyslane.append({"to": to, "subject": subject, "text": text, "html": html, "cfg": cfg})
        return True

    monkeypatch.setattr(mailer, "send_email", fake_send)
    seeded.app.state.mail_config = _cfg(True)
    seeded.app.state.mail_missing = []
    return {"c": seeded, "wyslane": wyslane}


def test_start_bez_zmiennych_daje_konfiguracje_wylaczona(seeded):
    cfg = seeded.app.state.mail_config
    assert cfg is not None and cfg.enabled is False
    assert set(seeded.app.state.mail_missing) == {"SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"}
    cfg2, brak = poczta_start.wczytaj({"SMTP_HOST": "h", "SMTP_USER": "u", "SMTP_PASSWORD": "p",
                                       "MAIL_FROM": "Dzik <a@b.pl>", "SMTP_PORT": "465"})
    assert cfg2.enabled and cfg2.use_ssl and brak == []
    cfg3, _ = poczta_start.wczytaj({"SMTP_HOST": "h", "SMTP_USER": "u", "SMTP_PASSWORD": "p",
                                    "MAIL_FROM": "Dzik <a@b.pl>", "SMTP_PORT": "abc"})
    assert cfg3.enabled is False


def test_role_flaga_i_202_z_identyfikatorem(poczta):
    c = poczta["c"]
    hc, ha, hk = login(c, COACH), login(c, ADMIN), login(c, CLIENT_A)
    assert c.post(URL, headers=hk, json={"to": "test@example.com"}).status_code == 403
    assert c.post(URL, headers=hc, json={"to": "nie-adres"}).status_code == 422
    r = c.post(URL, headers=ha, json={"to": "test@example.com"})
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued" and body["message_id"].startswith("<") and "mail.dzik-os.com" in body["message_id"]
    assert body["to_domain"] == "example.com" and "test@" not in body["to_domain"]
    # Zadanie w tle wykonane przez TestClient: temat, obie wersje treści, identyfikator w treści.
    w = poczta["wyslane"][0]
    assert w["to"] == "test@example.com" and w["subject"] == mail_admin.TEMAT
    assert body["message_id"] in w["text"] and "<p>" in w["html"] and w["cfg"].enabled
    assert c.post(URL, headers=hc, json={"to": "trener@example.com"}).status_code == 202
    assert c.get("/api/health").json()["features"]["mail_test_endpoint"] is True


def test_flaga_wylaczona_daje_404(poczta, monkeypatch):
    monkeypatch.setattr(settings, "mail_test_endpoint_enabled", False)
    assert poczta["c"].post(URL, headers=login(poczta["c"], ADMIN), json={"to": "t@example.com"}).status_code == 404
    assert poczta["c"].get("/api/health").json()["features"]["mail_test_endpoint"] is False


def test_poczta_wylaczona_daje_503_z_nazwami_zmiennych(poczta):
    c = poczta["c"]
    c.app.state.mail_config = _cfg(False)
    c.app.state.mail_missing = ["SMTP_HOST", "SMTP_PASSWORD"]
    r = c.post(URL, headers=login(c, ADMIN), json={"to": "t@example.com"})
    assert r.status_code == 503 and "SMTP_HOST, SMTP_PASSWORD" in r.json()["detail"]
    assert poczta["wyslane"] == []


def test_blad_wysylki_w_tle_nie_psuje_odpowiedzi(poczta, monkeypatch):
    def zly(*a, **kw):
        raise mailer.MailSendError("Wysyłka odrzucona przez serwer: (535, b'Bad credentials')")

    monkeypatch.setattr(mailer, "send_email", zly)
    r = poczta["c"].post(URL, headers=login(poczta["c"], ADMIN), json={"to": "t@example.com"})
    assert r.status_code == 202

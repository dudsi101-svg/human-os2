"""Testy mailera. Nie wymagają sieci ani konta SMTP — serwer jest podmieniany atrapą."""

import smtplib
import socket

import pytest

import mailer
from mailer import MailConfig, MailConfigError, MailSendError


ENV = {
    "SMTP_HOST": "smtp-relay.brevo.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "b93863001@smtp-brevo.com",
    "SMTP_PASSWORD": "tajne",
    "MAIL_FROM": "Mateusz z Dzik OS <mateusz@mail.dzik-os.com>",
    "MAIL_REPLY_TO": "kontakt@dzik-os.com",
}


def cfg(**over):
    base = dict(
        host="smtp-relay.brevo.com",
        port=587,
        user="user",
        password="tajne",
        mail_from="Dzik OS <mateusz@mail.dzik-os.com>",
        reply_to="kontakt@dzik-os.com",
        max_attempts=3,
        backoff_base=2.0,
    )
    base.update(over)
    return MailConfig(**base)


class FakeSMTP:
    """Atrapa smtplib.SMTP zapisująca wywołania. Kolejne błędy z listy `errors`."""

    instances: list["FakeSMTP"] = []
    errors: list[Exception | None] = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port
        self.calls: list[str] = []
        self.sent = []
        FakeSMTP.instances.append(self)

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append("login")
        self._maybe_raise()

    def send_message(self, msg):
        self.calls.append("send_message")
        self._maybe_raise()
        self.sent.append(msg)

    def quit(self):
        self.calls.append("quit")

    def _maybe_raise(self):
        if FakeSMTP.errors:
            err = FakeSMTP.errors.pop(0)
            if err is not None:
                raise err


@pytest.fixture(autouse=True)
def _reset():
    FakeSMTP.instances = []
    FakeSMTP.errors = []
    yield


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


# 1
def test_brak_zmiennej_srodowiskowej_daje_czytelny_blad():
    env = dict(ENV)
    del env["SMTP_PASSWORD"]
    with pytest.raises(MailConfigError, match="SMTP_PASSWORD"):
        mailer.load_config(env)


# 2
def test_load_config_czyta_wartosci_i_domyslny_port():
    env = dict(ENV)
    del env["SMTP_PORT"]
    c = mailer.load_config(env)
    assert c.port == 587 and c.enabled is True
    assert c.reply_to == "kontakt@dzik-os.com"
    assert c.use_ssl is False


# 3
def test_niepoprawny_mail_from_jest_odrzucany():
    env = dict(ENV, MAIL_FROM="Dzik OS")
    with pytest.raises(MailConfigError, match="MAIL_FROM"):
        mailer.load_config(env)


# 4
def test_mail_enabled_zero_blokuje_wysylke(patched):
    ok = mailer.send_email("k@example.com", "Temat", "Treść", cfg=cfg(enabled=False))
    assert ok is False
    assert patched.instances == []  # żadnego połączenia


# 5
def test_naglowki_i_wersja_html(patched):
    mailer.send_email("k@example.com", "Nowa dieta", "Wersja tekstowa",
                      html="<p>Wersja HTML</p>", cfg=cfg())
    msg = patched.instances[0].sent[0]
    assert msg["To"] == "k@example.com"
    assert msg["Subject"] == "Nowa dieta"
    assert msg["Reply-To"] == "kontakt@dzik-os.com"
    assert "mateusz@mail.dzik-os.com" in msg["From"]
    assert msg.is_multipart()
    assert {p.get_content_type() for p in msg.iter_parts()} == {"text/plain", "text/html"}


# 6
def test_port_587_uzywa_starttls_a_465_nie(patched):
    mailer.send_email("k@example.com", "T", "X", cfg=cfg(port=587))
    assert "starttls" in patched.instances[0].calls

    FakeSMTP.instances = []
    mailer.send_email("k@example.com", "T", "X", cfg=cfg(port=465))
    assert "starttls" not in patched.instances[0].calls


# 7
def test_blad_przejsciowy_jest_ponawiany_z_narastajacym_odstepem(patched):
    FakeSMTP.errors = [socket.timeout("timeout"), smtplib.SMTPServerDisconnected("bye"), None]
    delays = []
    ok = mailer.send_email("k@example.com", "T", "X", cfg=cfg(), sleep=delays.append)
    assert ok is True
    assert len(patched.instances) == 3
    assert delays == [1.0, 2.0]


# 8
def test_blad_autoryzacji_nie_jest_ponawiany(patched):
    FakeSMTP.errors = [smtplib.SMTPAuthenticationError(535, b"Bad credentials")]
    with pytest.raises(MailSendError):
        mailer.send_email("k@example.com", "T", "X", cfg=cfg(), sleep=lambda d: None)
    assert len(patched.instances) == 1


# 9
def test_wyczerpanie_prob_rzuca_mailsenderror(patched):
    FakeSMTP.errors = [socket.timeout("t")] * 3
    with pytest.raises(MailSendError, match="3 próbach"):
        mailer.send_email("k@example.com", "T", "X", cfg=cfg(), sleep=lambda d: None)
    assert len(patched.instances) == 3


# 10
def test_wysylka_w_tle_nie_propaguje_wyjatku(patched):
    FakeSMTP.errors = [smtplib.SMTPAuthenticationError(535, b"nope")]

    class BT:
        def __init__(self): self.tasks = []
        def add_task(self, fn, *a, **kw): self.tasks.append(fn)

    bt = BT()
    mailer.send_email_background(bt, "k@example.com", "T", "X", cfg=cfg())
    bt.tasks[0]()  # nie może rzucić — żądanie HTTP już odpowiedziało

"""Wysyłka e-mail przez SMTP dostawcy transakcyjnego (Brevo) z Fly.io.

Konfiguracja wyłącznie ze zmiennych środowiskowych (fly secrets). Bez zależności
spoza biblioteki standardowej — integracja z FastAPI jest opcjonalna.

Zmienne środowiskowe:
    SMTP_HOST       np. smtp-relay.brevo.com                     (wymagane)
    SMTP_PORT       587 = STARTTLS, 465 = TLS od razu            (domyślnie 587)
    SMTP_USER       login SMTP dostawcy                          (wymagane)
    SMTP_PASSWORD   klucz SMTP — NIE hasło do konta, NIE klucz API (wymagane)
    MAIL_FROM       "Nazwa <adres@domena.pl>", domena musi być
                    uwierzytelniona u dostawcy                   (wymagane)
    MAIL_REPLY_TO   adres, na który trafiają odpowiedzi klientów (opcjonalne)
    MAIL_ENABLED    "0" wyłącza faktyczną wysyłkę (dev/CI)       (domyślnie "1")
    MAIL_TIMEOUT    timeout połączenia w sekundach               (domyślnie 20)
    MAIL_MAX_ATTEMPTS  liczba prób łącznie                       (domyślnie 3)
"""

from __future__ import annotations

import logging
import os
import smtplib
import socket
import ssl
import time
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from typing import Callable, Sequence

log = logging.getLogger("mailer")

__all__ = [
    "MailConfig",
    "MailConfigError",
    "MailSendError",
    "load_config",
    "build_message",
    "send_email",
    "send_email_background",
]


class MailConfigError(RuntimeError):
    """Brak lub błędna konfiguracja SMTP."""


class MailSendError(RuntimeError):
    """Wysyłka nie powiodła się po wyczerpaniu prób lub przy błędzie trwałym."""


@dataclass(frozen=True)
class MailConfig:
    host: str
    port: int
    user: str
    password: str
    mail_from: str
    reply_to: str | None = None
    enabled: bool = True
    timeout: int = 20
    max_attempts: int = 3
    backoff_base: float = 2.0

    @property
    def use_ssl(self) -> bool:
        """Port 465 wymaga TLS od pierwszego bajtu; 587 używa STARTTLS."""
        return self.port == 465


def _require(env: dict, key: str) -> str:
    value = (env.get(key) or "").strip()
    if not value:
        raise MailConfigError(
            f"Brak zmiennej środowiskowej {key}. "
            f"Ustaw ją przez `fly secrets set {key}=...`."
        )
    return value


def load_config(env: dict | None = None) -> MailConfig:
    env = os.environ if env is None else env

    raw_port = (env.get("SMTP_PORT") or "587").strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise MailConfigError(f"SMTP_PORT musi być liczbą, jest: {raw_port!r}") from exc

    mail_from = _require(env, "MAIL_FROM")
    if not parseaddr(mail_from)[1] or "@" not in parseaddr(mail_from)[1]:
        raise MailConfigError(
            f"MAIL_FROM nie zawiera poprawnego adresu: {mail_from!r}. "
            'Oczekiwany format: "Nazwa <adres@domena.pl>".'
        )

    reply_to = (env.get("MAIL_REPLY_TO") or "").strip() or None
    enabled = (env.get("MAIL_ENABLED") or "1").strip() not in ("0", "false", "False")

    return MailConfig(
        host=_require(env, "SMTP_HOST"),
        port=port,
        user=_require(env, "SMTP_USER"),
        password=_require(env, "SMTP_PASSWORD"),
        mail_from=mail_from,
        reply_to=reply_to,
        enabled=enabled,
        timeout=int(env.get("MAIL_TIMEOUT") or 20),
        max_attempts=int(env.get("MAIL_MAX_ATTEMPTS") or 3),
    )


def build_message(
    to: str | Sequence[str],
    subject: str,
    text: str,
    html: str | None = None,
    cfg: MailConfig | None = None,
) -> EmailMessage:
    cfg = cfg or load_config()
    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        raise ValueError("Lista odbiorców jest pusta.")

    msg = EmailMessage()
    name, addr = parseaddr(cfg.mail_from)
    msg["From"] = formataddr((name, addr)) if name else addr
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    if cfg.reply_to:
        msg["Reply-To"] = cfg.reply_to

    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


def _connect(cfg: MailConfig) -> smtplib.SMTP:
    context = ssl.create_default_context()
    if cfg.use_ssl:
        server = smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=cfg.timeout, context=context)
    else:
        server = smtplib.SMTP(cfg.host, cfg.port, timeout=cfg.timeout)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
    server.login(cfg.user, cfg.password)
    return server


# Błędy trwałe — ponawianie nic nie da, kończymy od razu.
_PERMANENT = (
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
    smtplib.SMTPNotSupportedError,
)

# Błędy przejściowe — sieć, restart serwera, chwilowy limit.
_TRANSIENT = (
    smtplib.SMTPConnectError,
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPHeloError,
    socket.timeout,
    ConnectionError,
    OSError,
)


def send_email(
    to: str | Sequence[str],
    subject: str,
    text: str,
    html: str | None = None,
    cfg: MailConfig | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Wysyła wiadomość synchronicznie. Zwraca True przy wysłaniu, False gdy
    wysyłka jest wyłączona przez MAIL_ENABLED=0. Przy błędzie rzuca MailSendError."""
    cfg = cfg or load_config()
    msg = build_message(to, subject, text, html, cfg)

    if not cfg.enabled:
        log.info("MAIL_ENABLED=0 — pomijam wysyłkę do %s (temat: %s)", msg["To"], subject)
        return False

    last_error: Exception | None = None
    for attempt in range(1, cfg.max_attempts + 1):
        try:
            server = _connect(cfg)
            try:
                server.send_message(msg)
            finally:
                try:
                    server.quit()
                except Exception:  # zamknięcie nie może maskować wyniku wysyłki
                    pass
            log.info("Wysłano wiadomość do %s (próba %d)", msg["To"], attempt)
            return True

        except _PERMANENT as exc:
            log.error("Błąd trwały SMTP przy wysyłce do %s: %s", msg["To"], exc)
            raise MailSendError(f"Wysyłka odrzucona przez serwer: {exc}") from exc

        except smtplib.SMTPResponseException as exc:
            if 400 <= exc.smtp_code < 500:
                last_error = exc
            else:
                log.error("Błąd trwały %s przy wysyłce do %s", exc.smtp_code, msg["To"])
                raise MailSendError(f"Serwer odrzucił wiadomość ({exc.smtp_code}): {exc}") from exc

        except _TRANSIENT as exc:
            last_error = exc

        if attempt < cfg.max_attempts:
            delay = cfg.backoff_base ** (attempt - 1)
            log.warning(
                "Próba %d/%d nieudana (%s). Ponawiam za %.0f s.",
                attempt, cfg.max_attempts, last_error, delay,
            )
            sleep(delay)

    raise MailSendError(
        f"Wysyłka do {msg['To']} nieudana po {cfg.max_attempts} próbach: {last_error}"
    )


def send_email_background(background_tasks, to, subject, text, html=None, cfg=None) -> None:
    """Kolejkuje wysyłkę w FastAPI BackgroundTasks — żądanie HTTP nie czeka na SMTP.

        @app.post("/reset-hasla")
        def reset(payload: ResetIn, background_tasks: BackgroundTasks):
            send_email_background(background_tasks, payload.email, "Reset hasła", tresc)
            return {"ok": True}

    Wyjątek w tle nie przerywa odpowiedzi HTTP — jest logowany.
    """
    def _task() -> None:
        try:
            send_email(to, subject, text, html, cfg)
        except Exception:
            log.exception("Wysyłka w tle nie powiodła się (odbiorca: %s)", to)

    background_tasks.add_task(_task)

"""Inicjalizacja poczty Brevo (`dzik_os.mailer`) przy starcie aplikacji.

Jedna instancja `MailConfig` na proces (`app.state.mail_config`). Brak zmiennych
SMTP w środowisku (dev, CI, testy) = konfiguracja WYŁĄCZONA (`MAIL_ENABLED=0`)
z ostrzeżeniem wymieniającym NAZWY brakujących zmiennych — aplikacja wstaje.
Logger `mailer` (linie „Wysłano wiadomość do …”) dostaje handler na stdout,
bo aplikacja nie konfiguruje root loggera, a bez handlera INFO ginie.
"""

from __future__ import annotations

import logging
import os
import sys

from . import mailer
from .observability import log_json

ZMIENNE = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM", "MAIL_REPLY_TO")
WYMAGANE = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM")


def wylaczona() -> mailer.MailConfig:
    return mailer.MailConfig(host="", port=587, user="", password="", mail_from="", enabled=False)


def brakujace(env: dict | None = None) -> list[str]:
    env = os.environ if env is None else env
    return [k for k in WYMAGANE if not (env.get(k) or "").strip()]


def wczytaj(env: dict | None = None) -> tuple[mailer.MailConfig, list[str]]:
    """(konfiguracja, brakujące zmienne). Błędna wartość (np. port) też daje
    konfigurację wyłączoną — z logiem, bez wyjątku."""
    brak = brakujace(env)
    if brak:
        return wylaczona(), brak
    try:
        return mailer.load_config(env), []
    except mailer.MailConfigError as exc:
        log_json("mail_config_invalid", level="error", reason=str(exc)[:200])
        return wylaczona(), []


def podlacz_logger() -> None:
    log = logging.getLogger("mailer")
    log.setLevel(logging.INFO)
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s mailer: %(message)s"))
        log.addHandler(h)


def zainicjalizuj(app) -> None:
    podlacz_logger()
    cfg, brak = wczytaj()
    app.state.mail_config = cfg
    app.state.mail_missing = brak
    if not cfg.enabled:
        log_json("mail_disabled", level="warning", missing=brak,
                 summary="Poczta Brevo wyłączona (MAIL_ENABLED=0)" + (": brak " + ", ".join(brak) if brak else ""))
    else:
        log_json("mail_enabled", host=cfg.host, port=cfg.port, from_domain=cfg.mail_from.rsplit("@", 1)[-1].rstrip(">"))

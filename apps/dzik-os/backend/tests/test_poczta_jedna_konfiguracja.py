"""Jedna konfiguracja poczty dla obu dróg wysyłki (0.76.1).

Aplikacja ma dwie drogi wychodzącej poczty, które powstały osobno:
`notifications_provider` (zaproszenia, reset hasła, powiadomienia) czytał
`DZIK_SMTP_*`, a `mailer` (kontrola kanału, wysyłka testowa) czyta
`SMTP_*` / `MAIL_FROM`. Na produkcji ustawiono te drugie: kontrola kanału
przechodziła wszystkie cztery kroki, a zaproszenia i resety haseł nadal
kończyły się powodem „brak dostawcy” i wymagały ręcznego przekazania linku.
Te testy pilnują, żeby obie drogi widziały tę samą konfigurację.
"""

import pytest

from dzik_os.config import Settings

WSPOLNE = {
    "SMTP_HOST": "smtp-relay.brevo.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "konto@smtp-brevo.com",
    "SMTP_PASSWORD": "tajne-haslo",
    "MAIL_FROM": "Mateusz z Dzik OS <mateusz@mail.dzik-os.com>",
}
NAZWY = [*WSPOLNE, "DZIK_SMTP_HOST", "DZIK_SMTP_PORT", "DZIK_SMTP_USER",
         "DZIK_SMTP_PASSWORD", "DZIK_SMTP_FROM"]


@pytest.fixture
def czyste_env(monkeypatch):
    for nazwa in NAZWY:
        monkeypatch.delenv(nazwa, raising=False)
    return monkeypatch


def test_bez_zmiennych_dostawca_zostaje_pusty(czyste_env):
    """Brak konfiguracji = zachowanie sprzed zmiany: aplikacja nie wysyła nic."""
    assert Settings().smtp_host == ""


def test_wspolne_nazwy_wlaczaja_powiadomienia(czyste_env):
    """Same `SMTP_*` / `MAIL_FROM` (tak jest na produkcji) wystarczą —
    wcześniej zaproszenia i resety haseł ich nie widziały."""
    for nazwa, wartosc in WSPOLNE.items():
        czyste_env.setenv(nazwa, wartosc)
    s = Settings()
    assert s.smtp_host == "smtp-relay.brevo.com"
    assert s.smtp_port == 587
    assert s.smtp_user == "konto@smtp-brevo.com"
    assert s.smtp_password == "tajne-haslo"
    assert s.smtp_from == "Mateusz z Dzik OS <mateusz@mail.dzik-os.com>"


def test_nazwy_z_prefiksem_maja_pierwszenstwo(czyste_env):
    """Jawna konfiguracja tej aplikacji wygrywa ze wspólną."""
    for nazwa, wartosc in WSPOLNE.items():
        czyste_env.setenv(nazwa, wartosc)
    czyste_env.setenv("DZIK_SMTP_HOST", "wlasny.serwer.pl")
    czyste_env.setenv("DZIK_SMTP_FROM", "trener@dzik-os.com")
    s = Settings()
    assert s.smtp_host == "wlasny.serwer.pl"
    assert s.smtp_from == "trener@dzik-os.com"
    # Pola bez własnej nazwy dalej biorą wartość wspólną.
    assert s.smtp_user == "konto@smtp-brevo.com"


def test_pusta_zmienna_z_prefiksem_nie_wygasza_wspolnej(czyste_env):
    """Pusty `DZIK_SMTP_HOST` (np. zostawiony w pliku .env) nie może
    unieważnić działającej konfiguracji wspólnej."""
    czyste_env.setenv("SMTP_HOST", "smtp-relay.brevo.com")
    czyste_env.setenv("DZIK_SMTP_HOST", "")
    assert Settings().smtp_host == "smtp-relay.brevo.com"


def test_dostawca_powiadomien_wstaje_na_wspolnych_nazwach(czyste_env):
    """Dowód końcowy: przy konfiguracji jak na produkcji `_zbuduj_provider`
    daje dostawcę SMTP, a nie pustego — czyli zaproszenie wyjdzie."""
    for nazwa, wartosc in WSPOLNE.items():
        czyste_env.setenv(nazwa, wartosc)
    from dzik_os import config as config_module
    from dzik_os import notifications_provider as np

    czyste_env.setattr(config_module, "settings", Settings())
    dostawca = np._zbuduj_provider()
    assert dostawca.name == "smtp"

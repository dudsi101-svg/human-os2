"""Moduł-sonda `dzik_os.test_szyfrowania` (0.53.6, audyt A6): dowód
szyfrowania at-rest musi być prawdziwym dowodem — zielony wyłącznie
z poprawnym kluczem, jawnie czerwony bez klucza i przy złym kluczu,
zawsze sprzątający po sobie."""

import base64
import os

from dzik_os.config import settings
from dzik_os.test_szyfrowania import dowod_szyfrowania, main


def _pliki_sond() -> list[str]:
    katalog = settings.upload_dir
    if not os.path.isdir(katalog):
        return []
    return [n for n in os.listdir(katalog) if n.startswith(".sonda-szyfrowania-")]


def test_dowod_przechodzi_z_poprawnym_kluczem(monkeypatch):
    klucz = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setattr(settings, "file_key_b64", klucz)
    ok, opis = dowod_szyfrowania()
    assert ok, opis
    assert "DZIKENC1" in opis
    # Sonda nie zostaje na dysku — ani po sukcesie, ani po porażce.
    assert _pliki_sond() == []


def test_brak_klucza_to_jawny_blad_no_key(monkeypatch):
    monkeypatch.setattr(settings, "file_key_b64", "")
    ok, opis = dowod_szyfrowania()
    assert not ok
    assert opis.startswith("no_key")


def test_zepsuty_klucz_to_jawny_blad_bad_key(monkeypatch):
    monkeypatch.setattr(settings, "file_key_b64", "nie-base64!!!")
    ok, opis = dowod_szyfrowania()
    assert not ok
    assert opis.startswith("bad_key")
    assert _pliki_sond() == []


def test_main_zwraca_kody_wyjscia_workflow(monkeypatch, capsys):
    # Workflow polega na kodzie wyjścia, nie na treści logu.
    monkeypatch.setattr(settings, "file_key_b64", "")
    assert main() == 1
    assert "BŁĄD" in capsys.readouterr().err

    klucz = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setattr(settings, "file_key_b64", klucz)
    assert main() == 0
    assert "Szyfrowanie plików działa" in capsys.readouterr().out

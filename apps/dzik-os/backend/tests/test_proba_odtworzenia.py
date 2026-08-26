"""Próba odtworzenia backupu (0.53.9, audyt B4): dowód musi być
prawdziwy — zielona tylko gdy archiwum powstało, odtworzyło się do
izolowanej kopii, liczności się zgadzają i łańcuch audytu jest spójny;
raport nie zawiera PII."""

import re

import pytest
from conftest import CLIENT_A

from dzik_os.proba_odtworzenia import proba


def test_proba_konczy_sie_dowodem_i_bez_pii(seeded, tmp_path):
    # `seeded` (fixture) zapewnia zmigrowaną bazę z kontami i danymi seedu.
    # Na jobie PostgreSQL próba jawnie odmawia (izolacja katalogiem
    # tymczasowym istnieje tylko dla SQLite — jak na produkcji); pełne
    # odtworzenie na PG pokrywa destrukcyjnie test_backup.
    from dzik_os.config import settings
    if not settings.database_url.startswith("sqlite:///"):
        ok, raport = proba(backup_dir=str(tmp_path / "kopie"))
        assert not ok and "SQLite" in raport[0]
        pytest.skip("pełna próba tylko na SQLite (jak produkcja)")
    ok, raport = proba(backup_dir=str(tmp_path / "kopie"))
    tekst = "\n".join(raport)
    assert ok, tekst
    assert "users:" in tekst
    # Każda tabela z listy TABELE musi istnieć w kopii — literówka w nazwie
    # (np. "checkins" zamiast "weekly_checkins") ma czerwienić test, nie
    # przechodzić jako "BRAK TABELI" w raporcie.
    assert "BRAK TABELI" not in tekst
    assert "Próba odtworzenia: OK" in tekst
    # Raport ma nieść liczby, nie dane: żaden adres e-mail kont testowych
    # nie może wyciec do logu Actions.
    assert CLIENT_A["email"] not in tekst
    assert not re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", tekst, re.IGNORECASE)


def test_proba_zawodzi_jawnie_gdy_backup_niemozliwy(client, tmp_path, monkeypatch):
    # Wymuszamy porażkę już na etapie tworzenia archiwum.
    import dzik_os.proba_odtworzenia as m

    def _pad(**kwargs):
        raise m.BackupError("wymuszony błąd testowy")

    monkeypatch.setattr(m, "create_backup", _pad)
    ok, raport = proba(backup_dir=str(tmp_path / "kopie"))
    assert not ok
    assert "BŁĄD tworzenia archiwum" in raport[0]

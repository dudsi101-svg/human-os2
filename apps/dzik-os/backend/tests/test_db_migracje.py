"""Migracje bazy — przypadki, w których cisza jest groźniejsza niż błąd."""

import subprocess
import sys


def test_swieza_baza_dostaje_tabele_nawet_bez_importu_modeli(tmp_path):
    """`run_migrations()` na pustej bazie tworzy schemat z `Base.metadata`.

    Metadane są PUSTE, dopóki nie zaimportuje się `models`. Wywołujący,
    który tego nie zrobi, dostawał bazę **bez ani jednej tabeli**, za to
    ostemplowaną jako w pełni zmigrowaną — czyli taką, która nigdy się już
    nie naprawi, bo wszystkie migracje są odhaczone. Żaden istniejący test
    tego nie łapał, bo `conftest` importuje modele zawsze.

    Test uruchamia OSOBNY proces, który importuje wyłącznie `dzik_os.db` —
    to jedyny sposób, żeby sprawdzić brak importu, gdy suita i tak ma
    modele w pamięci."""
    baza = tmp_path / "swieza.db"
    skrypt = f"""
import os
os.environ["DZIK_DATABASE_URL"] = "sqlite:///{baza}"
os.environ["DZIK_UPLOAD_DIR"] = "{tmp_path / 'up'}"
os.environ["DZIK_AUDIT_DB"] = "{tmp_path / 'audit.db'}"
from sqlalchemy import text
from dzik_os.db import run_migrations, engine   # CELOWO bez importu models
zastosowane = run_migrations()
with engine.connect() as c:
    tabele = [r[0] for r in c.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'"))]
print(len(zastosowane), len(tabele))
for wymagana in ("users", "exercises", "training_plans", "import_snapshots"):
    assert wymagana in tabele, f"brak tabeli {{wymagana}} (tabele: {{sorted(tabele)}})"
"""
    wynik = subprocess.run(
        [sys.executable, "-c", skrypt], capture_output=True, text=True, check=False
    )
    assert wynik.returncode == 0, wynik.stdout + wynik.stderr
    migracje, tabele = (int(x) for x in wynik.stdout.split())
    assert migracje > 20, f"zastosowano tylko {migracje} migracji"
    assert tabele > 20, f"świeża baza ma tylko {tabele} tabel — schemat nie powstał"


def test_ponowne_uruchomienie_migracji_nic_nie_zmienia(tmp_path, monkeypatch):
    """Idempotencja: drugi przebieg zwraca pustą listę."""
    from sqlalchemy import create_engine

    from dzik_os.db import run_migrations

    eng = create_engine(f"sqlite:///{tmp_path}/idem.db")
    pierwszy = run_migrations(eng)
    assert pierwszy, "pierwszy przebieg nie zastosował żadnej migracji"
    assert run_migrations(eng) == []


def test_numery_migracji_sa_unikalne_i_rosnace():
    """Luki są dozwolone (numer bywa zarezerwowany i nieużyty), powtórzenia
    i cofnięcia numeracji — nie."""
    from dzik_os.db import MIGRATIONS

    numery = [n for n, _, _ in MIGRATIONS]
    assert len(numery) == len(set(numery)), "powtórzony numer migracji"
    assert numery == sorted(numery), "numery nie są rosnące"
    assert numery[0] == 1

"""Nieniszcząca próba odtworzenia backupu (0.53.9, audyt B4).

Użycie (lokalnie albo na maszynie Fly przez `flyctl ssh console`):

    python -m dzik_os.proba_odtworzenia

Sens istnienia: backup, którego nikt nigdy nie odtworzył, to nadzieja,
nie kopia zapasowa. Workflow „Próba odtworzenia backupu (Fly.io)"
uruchamia ten moduł co tydzień. Przebieg:

1. świeże archiwum przez `create_backup` (ta sama ścieżka co codzienny
   backup, więc próba dowodzi także tworzenia);
2. odtworzenie PODPROCESEM `python -m dzik_os.backup --restore --force`
   z bazą/audytem/uploadami przestawionymi przez env na katalog
   tymczasowy — dane produkcyjne są strukturalnie nietykane, bo proces
   odtwarzający w ogóle nie zna ich ścieżek;
3. na odtworzonej kopii: liczności kluczowych tabel, liczba plików
   uploadów i NIEZALEŻNA weryfikacja łańcucha audytu;
4. sprzątanie katalogu tymczasowego — zawsze.

Raport zawiera WYŁĄCZNIE nazwy tabel i liczby — zero danych osobowych
(trafia do logu Actions). Kod wyjścia 0 tylko, gdy odtworzenie się
powiodło, łańcuch audytu jest spójny (albo archiwum jawnie nie zawiera
bazy audytu) i w kopii jest co najmniej jedno konto.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from hos_engine.sqlite_store import SQLiteEventStore

from .backup import BackupError, create_backup

# Tabele, których liczności dowodzą, że kopia niesie realne dane
# (konta, relacje, treść pracy trenera i klienta, pokwitowania audytu).
TABELE = (
    "users",
    "role_grants",
    "coach_client_relationships",
    "weekly_checkins",
    "training_plans",
    "receipts",
)


def _licznosci(db_path: Path) -> dict[str, int | None]:
    """Liczności tabel z odtworzonej kopii (None = tabeli brak)."""
    wynik: dict[str, int | None] = {}
    con = sqlite3.connect(db_path)
    try:
        istniejace = {
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for tabela in TABELE:
            if tabela in istniejace:
                wynik[tabela] = con.execute(
                    f"SELECT COUNT(*) FROM {tabela}"
                ).fetchone()[0]
            else:
                wynik[tabela] = None
    finally:
        con.close()
    return wynik


def proba(backup_dir: str | None = None) -> tuple[bool, list[str]]:
    """Pełna próba. Zwraca (wynik, linie raportu bez PII)."""
    raport: list[str] = []
    try:
        archiwum = create_backup(backup_dir=backup_dir)
    except BackupError as exc:
        return False, [f"BŁĄD tworzenia archiwum: {exc}"]
    raport.append(f"archiwum: {Path(archiwum).name}")

    with tempfile.TemporaryDirectory(prefix="dzik-proba-") as tmp:
        kopia = Path(tmp)
        env = dict(os.environ)
        env.update(
            DZIK_DATABASE_URL=f"sqlite:///{kopia / 'dzik.db'}",
            DZIK_AUDIT_DB=str(kopia / "audit.db"),
            DZIK_UPLOAD_DIR=str(kopia / "uploads"),
        )
        wynik = subprocess.run(
            [sys.executable, "-m", "dzik_os.backup", "--restore",
             str(archiwum), "--force"],
            capture_output=True, text=True, env=env, check=False,
        )
        # stdout backupu nie zawiera PII (ścieżki i wynik weryfikacji).
        raport.extend(f"  {linia}" for linia in wynik.stdout.splitlines())
        if wynik.returncode != 0:
            raport.append(f"BŁĄD odtwarzania (kod {wynik.returncode}): "
                          f"{wynik.stderr.strip()[-300:]}")
            return False, raport

        db = kopia / "dzik.db"
        if not db.is_file():
            return False, raport + ["BŁĄD: odtworzona baza nie istnieje."]
        for tabela, ile in _licznosci(db).items():
            raport.append(
                f"  {tabela}: {ile if ile is not None else 'BRAK TABELI'}"
            )

        uploady = kopia / "uploads"
        pliki = sum(1 for p in uploady.rglob("*") if p.is_file()) if uploady.is_dir() else 0
        raport.append(f"  pliki uploadów: {pliki}")

        audyt = kopia / "audit.db"
        if audyt.is_file():
            store = SQLiteEventStore(str(audyt))
            try:
                lancuch = store.verify_chain()
            finally:
                store.close()
            raport.append(f"  łańcuch audytu (niezależnie): {'OK' if lancuch else 'PRZERWANY'}")
            if not lancuch:
                return False, raport
        else:
            raport.append("  archiwum bez bazy audytu — łańcuch nieweryfikowany")

        konta = _licznosci(db)["users"] or 0
        if konta < 1:
            raport.append("BŁĄD: odtworzona kopia nie zawiera żadnego konta.")
            return False, raport

    raport.append("Próba odtworzenia: OK (kopia tymczasowa posprzątana).")
    return True, raport


def main() -> int:
    ok, raport = proba()
    strumien = sys.stdout if ok else sys.stderr
    for linia in raport:
        print(linia, file=strumien)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

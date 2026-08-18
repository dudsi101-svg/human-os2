"""Kopie zapasowe i odtwarzanie danych Dzik OS (zamyka R-12 z RISK_REGISTER.md).

Archiwum backupu (`dzik-backup-<timestamp>.tar.gz`) obejmuje spójnie:

* główną bazę — SQLite przez sqlite3 backup API (nigdy kopiowanie pliku
  "na żywo"); dla PostgreSQL zrzut `pg_dump` przez subprocess (wykrywane
  z DZIK_DATABASE_URL),
* bazę audytu Human OS (audit.db) — również przez sqlite3 backup API,
* katalog uploadów DOKŁADNIE tak, jak leży na dysku — czyli w postaci
  zaszyfrowanej, jeśli działa szyfrowanie at-rest (DZIK_FILE_KEY).
  UWAGA: klucz DZIK_FILE_KEY przechowuj OSOBNO od backupów — bez niego
  zaszyfrowane pliki z archiwum są nie do odzyskania.

Użycie:

    python -m dzik_os.backup                       # utwórz archiwum + retencja
    python -m dzik_os.backup --keep 30             # nadpisz retencję (env: DZIK_BACKUP_KEEP)
    python -m dzik_os.backup --restore <archiwum>  # odtwórz (odmowa nadpisania bez --force)

Po odtworzeniu łańcuch audytu jest weryfikowany (SQLiteEventStore.verify_chain())
i wynik jest jawnie raportowany. Odtwarzanie wykonuj przy ZATRZYMANEJ aplikacji.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from hos_engine.sqlite_store import SQLiteEventStore

from .config import settings

ARCHIVE_PREFIX = "dzik-backup-"
ARCHIVE_SUFFIX = ".tar.gz"


class BackupError(RuntimeError):
    """Błąd tworzenia lub odtwarzania kopii zapasowej (komunikat po polsku)."""


def _sqlite_path(database_url: str) -> Path | None:
    """Ścieżka pliku SQLite z URL-a bazy albo None (inna baza)."""
    if database_url.startswith("sqlite:///"):
        return Path(database_url.removeprefix("sqlite:///"))
    return None


def _pg_url(database_url: str) -> str:
    """URL połączenia dla narzędzi psql/pg_dump (bez sufiksu sterownika
    SQLAlchemy, np. `postgresql+psycopg2://` -> `postgresql://`)."""
    scheme, _, rest = database_url.partition("://")
    return scheme.split("+", 1)[0] + "://" + rest


def _backup_sqlite(src: Path, dst: Path) -> None:
    """Spójna kopia bazy SQLite przez sqlite3 backup API (bezpieczna także
    przy otwartych połączeniach i trybie WAL — nigdy `shutil.copy` na żywo)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(src)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def _dump_main_database(workdir: Path) -> dict:
    """Zrzuca główną bazę do katalogu roboczego; zwraca wpis manifestu."""
    sqlite_file = _sqlite_path(settings.database_url)
    if sqlite_file is not None:
        if not sqlite_file.exists():
            raise BackupError(f"Baza {sqlite_file} nie istnieje — nie ma czego backupować")
        _backup_sqlite(sqlite_file, workdir / "db" / "dzik.db")
        return {"kind": "sqlite", "member": "db/dzik.db"}
    if settings.database_url.startswith("postgresql"):
        dump_path = workdir / "db" / "dzik.sql"
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "pg_dump",
                "--no-owner",
                # Zrzut musi umieć wejść na bazę, w której obiekty JUŻ są —
                # inaczej odtworzenie na działającej instancji przerywa się na
                # pierwszym „relation already exists". `--clean --if-exists`
                # sprawia, że zrzut sam usuwa obiekty przed odtworzeniem, i nie
                # wywraca się, gdy któregoś nie ma (baza pusta po awarii).
                # Odpowiednik nadpisania pliku, którym odtwarzanie SQLite
                # załatwia to samo.
                "--clean",
                "--if-exists",
                "--file",
                str(dump_path),
                _pg_url(settings.database_url),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise BackupError(f"pg_dump zakończył się błędem: {result.stderr.strip()}")
        return {"kind": "postgres", "member": "db/dzik.sql"}
    raise BackupError(f"Nieobsługiwany typ bazy w DZIK_DATABASE_URL: {settings.database_url}")


def create_backup(
    backup_dir: str | Path | None = None,
    keep: int | None = None,
    timestamp: str | None = None,
) -> Path:
    """Tworzy archiwum backupu i stosuje retencję; zwraca ścieżkę archiwum.

    `timestamp` jest generowany w czasie działania (UTC), chyba że wywołujący
    przekaże własny (np. orkiestracja zewnętrzna); format bezpieczny dla nazw
    plików: YYYYmmddTHHMMSSZ.
    """
    target_dir = Path(backup_dir or settings.backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_path = target_dir / f"{ARCHIVE_PREFIX}{stamp}{ARCHIVE_SUFFIX}"
    if archive_path.exists():
        raise BackupError(f"Archiwum {archive_path} już istnieje")

    with tempfile.TemporaryDirectory(prefix="dzik-backup-") as tmp:
        workdir = Path(tmp)
        manifest: dict = {
            "app": "dzik-os",
            "format": 1,
            "timestamp": stamp,
            "database": _dump_main_database(workdir),
        }

        audit_src = Path(settings.audit_db_path)
        if audit_src.exists():
            _backup_sqlite(audit_src, workdir / "audit" / "audit.db")
            manifest["audit"] = {"member": "audit/audit.db"}
        else:
            manifest["audit"] = None

        uploads_src = Path(settings.upload_dir)
        manifest["uploads"] = {"member": "uploads"} if uploads_src.is_dir() else None

        (workdir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(workdir / "manifest.json", arcname="manifest.json")
            tar.add(workdir / "db", arcname="db")
            if manifest["audit"]:
                tar.add(workdir / "audit", arcname="audit")
            if manifest["uploads"]:
                # Pliki uploadów trafiają do archiwum tak, jak leżą na dysku
                # (zaszyfrowane przy włączonym DZIK_FILE_KEY).
                tar.add(uploads_src, arcname="uploads")

    apply_retention(target_dir, keep if keep is not None else settings.backup_keep)
    return archive_path


def apply_retention(backup_dir: str | Path, keep: int) -> list[Path]:
    """Usuwa najstarsze archiwa ponad limit `keep`; zwraca usunięte ścieżki."""
    if keep < 1:
        raise BackupError("Retencja (DZIK_BACKUP_KEEP) musi wynosić co najmniej 1")
    archives = sorted(
        Path(backup_dir).glob(f"{ARCHIVE_PREFIX}*{ARCHIVE_SUFFIX}"),
        key=lambda p: p.name,
    )
    removed = archives[:-keep] if len(archives) > keep else []
    for path in removed:
        path.unlink()
    return removed


def _existing_restore_targets(manifest: dict) -> list[str]:
    """Lista miejsc docelowych, które restore by nadpisał (dla odmowy bez --force)."""
    conflicts: list[str] = []
    sqlite_file = _sqlite_path(settings.database_url)
    if manifest["database"]["kind"] == "sqlite" and sqlite_file is not None and sqlite_file.exists():
        conflicts.append(str(sqlite_file))
    audit_path = Path(settings.audit_db_path)
    if manifest.get("audit") and audit_path.exists():
        conflicts.append(str(audit_path))
    uploads_dir = Path(settings.upload_dir)
    if manifest.get("uploads") and uploads_dir.is_dir() and any(uploads_dir.iterdir()):
        conflicts.append(str(uploads_dir))
    return conflicts


def restore_backup(archive: str | Path, force: bool = False) -> dict:
    """Odtwarza bazę, audit.db i uploady z archiwum; weryfikuje łańcuch audytu.

    Zwraca raport: {"restored": [...], "audit_chain_ok": bool | None}
    (None = archiwum nie zawierało bazy audytu). Bez `force` odmawia
    nadpisania istniejących danych (BackupError).
    """
    archive_path = Path(archive)
    if not archive_path.is_file():
        raise BackupError(f"Archiwum {archive_path} nie istnieje")

    with tempfile.TemporaryDirectory(prefix="dzik-restore-") as tmp:
        workdir = Path(tmp)
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(workdir, filter="data")
        manifest_path = workdir / "manifest.json"
        if not manifest_path.is_file():
            raise BackupError("Archiwum nie zawiera manifest.json — to nie jest backup Dzik OS")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        conflicts = _existing_restore_targets(manifest)
        if conflicts and not force:
            raise BackupError(
                "Odmowa nadpisania istniejących danych (użyj --force): "
                + ", ".join(conflicts)
            )

        restored: list[str] = []

        db_entry = manifest["database"]
        if db_entry["kind"] == "sqlite":
            sqlite_file = _sqlite_path(settings.database_url)
            if sqlite_file is None:
                raise BackupError(
                    "Archiwum zawiera bazę SQLite, a DZIK_DATABASE_URL wskazuje inną bazę"
                )
            sqlite_file.parent.mkdir(parents=True, exist_ok=True)
            # Kopia z archiwum jest spójnym plikiem (powstała przez backup API);
            # przy zatrzymanej aplikacji podmiana pliku jest bezpieczna.
            for suffix in ("-wal", "-shm"):
                stale = sqlite_file.with_name(sqlite_file.name + suffix)
                if stale.exists():
                    stale.unlink()
            shutil.copyfile(workdir / db_entry["member"], sqlite_file)
            restored.append(f"baza SQLite -> {sqlite_file}")
        else:
            result = subprocess.run(
                ["psql", "--set", "ON_ERROR_STOP=1", "--file",
                 str(workdir / db_entry["member"]), _pg_url(settings.database_url)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise BackupError(f"psql zakończył się błędem: {result.stderr.strip()}")
            restored.append("baza PostgreSQL (psql < dzik.sql)")

        audit_chain_ok: bool | None = None
        if manifest.get("audit"):
            audit_path = Path(settings.audit_db_path)
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(workdir / manifest["audit"]["member"], audit_path)
            restored.append(f"baza audytu -> {audit_path}")
            store = SQLiteEventStore(str(audit_path))
            try:
                audit_chain_ok = store.verify_chain()
            finally:
                store.close()

        if manifest.get("uploads"):
            uploads_dir = Path(settings.upload_dir)
            if uploads_dir.exists():
                shutil.rmtree(uploads_dir)
            shutil.copytree(workdir / "uploads", uploads_dir)
            restored.append(f"uploady -> {uploads_dir}")

    return {"restored": restored, "audit_chain_ok": audit_chain_ok}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m dzik_os.backup",
        description="Kopie zapasowe Dzik OS: baza + audit.db + uploady (R-12).",
    )
    parser.add_argument("--restore", metavar="ARCHIWUM",
                        help="odtwórz dane z podanego archiwum zamiast tworzyć backup")
    parser.add_argument("--force", action="store_true",
                        help="pozwól nadpisać istniejące dane przy odtwarzaniu")
    parser.add_argument("--backup-dir", default=None,
                        help=f"katalog archiwów (domyślnie env DZIK_BACKUP_DIR, "
                             f"obecnie: {settings.backup_dir})")
    parser.add_argument("--keep", type=int, default=None,
                        help=f"ile najnowszych archiwów zachować (domyślnie env "
                             f"DZIK_BACKUP_KEEP, obecnie: {settings.backup_keep})")
    args = parser.parse_args(argv)

    try:
        if args.restore:
            report = restore_backup(args.restore, force=args.force)
            for item in report["restored"]:
                print(f"[dzik-backup] odtworzono: {item}")
            if report["audit_chain_ok"] is None:
                print("[dzik-backup] archiwum nie zawierało bazy audytu — "
                      "łańcuch audytu NIE był weryfikowany")
            elif report["audit_chain_ok"]:
                print("[dzik-backup] weryfikacja łańcucha audytu: OK")
            else:
                print("[dzik-backup] weryfikacja łańcucha audytu: BŁĄD — "
                      "łańcuch hashy jest przerwany!")
                return 1
            return 0
        archive = create_backup(backup_dir=args.backup_dir, keep=args.keep)
        print(f"[dzik-backup] utworzono archiwum: {archive}")
        return 0
    except BackupError as exc:
        print(f"[dzik-backup] BŁĄD: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

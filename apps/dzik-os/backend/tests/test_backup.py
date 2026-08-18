"""Kopie zapasowe (R-12): pełny cykl backup -> utrata danych -> restore,
odmowa nadpisania bez --force oraz retencja archiwów."""

import io
import tarfile

import pytest
from conftest import CLIENT_A, login, make_png

from dzik_os import backup as backup_mod
from dzik_os import hos_bridge
from dzik_os.backup import BackupError
from dzik_os.config import settings

PNG = make_png()


def _upload_png(client, headers) -> str:
    r = client.post(
        "/api/files", headers=headers,
        files={"file": ("zdjecie.png", io.BytesIO(PNG), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _destroy_data() -> None:
    """Symulacja utraty danych: kasuje bazę, audit.db i uploady."""
    import shutil
    from pathlib import Path

    from dzik_os.db import engine

    engine.dispose()
    hos_bridge.reset_event_store()
    db_file = backup_mod._sqlite_path(settings.database_url)
    assert db_file is not None
    db_file.unlink()
    Path(settings.audit_db_path).unlink()
    shutil.rmtree(settings.upload_dir)


def test_full_backup_restore_cycle(seeded, tmp_path):
    ha = login(seeded, CLIENT_A)
    file_id = _upload_png(seeded, ha)
    # Treść po stronie serwera (upload rekompresuje obrazy — porównujemy
    # to, co faktycznie przechowano, nie oryginalne bajty).
    served_before = seeded.get(f"/api/files/{file_id}", headers=ha).content
    assert hos_bridge.verify_audit_chain() is True

    archive = backup_mod.create_backup(backup_dir=tmp_path)
    assert archive.is_file()
    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert "manifest.json" in names
    assert "db/dzik.db" in names
    assert "audit/audit.db" in names
    assert any(name.startswith("uploads/") for name in names)

    _destroy_data()

    report = backup_mod.restore_backup(archive)
    # Weryfikacja łańcucha audytu po odtworzeniu — jawnie raportowana.
    assert report["audit_chain_ok"] is True
    assert len(report["restored"]) == 3

    # Dane wracają: sesja sprzed backupu działa, plik do pobrania w całości.
    r = seeded.get(f"/api/files/{file_id}", headers=ha)
    assert r.status_code == 200
    assert r.content == served_before
    hos_bridge.reset_event_store()
    assert hos_bridge.verify_audit_chain() is True


def test_restore_refuses_overwrite_without_force(seeded, tmp_path):
    ha = login(seeded, CLIENT_A)
    _upload_png(seeded, ha)
    archive = backup_mod.create_backup(backup_dir=tmp_path)

    with pytest.raises(BackupError, match="Odmowa nadpisania"):
        backup_mod.restore_backup(archive)

    from dzik_os.db import engine

    engine.dispose()
    hos_bridge.reset_event_store()
    report = backup_mod.restore_backup(archive, force=True)
    assert report["audit_chain_ok"] is True
    hos_bridge.reset_event_store()


def test_retention_removes_oldest(seeded, tmp_path):
    for i in range(5):
        backup_mod.create_backup(backup_dir=tmp_path, keep=3, timestamp=f"2026081{i}T000000Z")
    remaining = sorted(p.name for p in tmp_path.glob("dzik-backup-*.tar.gz"))
    assert remaining == [
        "dzik-backup-20260812T000000Z.tar.gz",
        "dzik-backup-20260813T000000Z.tar.gz",
        "dzik-backup-20260814T000000Z.tar.gz",
    ]


def test_cli_backup_and_restore(seeded, tmp_path, capsys):
    ha = login(seeded, CLIENT_A)
    _upload_png(seeded, ha)
    assert backup_mod.main(["--backup-dir", str(tmp_path)]) == 0
    archive = next(tmp_path.glob("dzik-backup-*.tar.gz"))

    # Bez --force: odmowa (kod 2), dane na miejscu.
    assert backup_mod.main(["--restore", str(archive)]) == 2

    _destroy_data()
    assert backup_mod.main(["--restore", str(archive)]) == 0
    out = capsys.readouterr().out
    assert "weryfikacja łańcucha audytu: OK" in out
    hos_bridge.reset_event_store()

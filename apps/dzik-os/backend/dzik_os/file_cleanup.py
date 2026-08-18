"""Sprzątanie plików-sierot.

Plik wgrany przez /api/files, ale nigdy nie podpięty do żadnego zasobu
(dokument, zdjęcie progresu, załącznik wiadomości, baza wiedzy, wpis
treningowy) nie jest niczyją dokumentacją — po upływie TTL
(config.orphan_file_ttl_hours, domyślnie 24 h) dostaje soft delete
(deleted_at; wiersz i metadane zostają dla rozliczalności) a bajty są
usuwane z dysku. Pliki z jakąkolwiek referencją nigdy nie są dotykane.

Wywoływane z pętli reminder_loop (raz na godzinę, pierwsze przejście od
razu po starcie aplikacji).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from .config import settings
from .hos_bridge import record_event
from .models import (
    Document,
    KnowledgeItem,
    Message,
    ProgressPhoto,
    StoredFile,
    WorkoutEntry,
    now_iso,
)
from .storage import storage


def _referenced_file_ids(db: Session) -> set[str]:
    referenced: set[str] = set()
    for query in (
        db.query(Document.file_id),
        db.query(ProgressPhoto.file_id),
        db.query(Message.file_id).filter(Message.file_id.isnot(None)),
        db.query(KnowledgeItem.file_id).filter(KnowledgeItem.file_id.isnot(None)),
        db.query(WorkoutEntry.file_id).filter(WorkoutEntry.file_id.isnot(None)),
    ):
        referenced.update(row[0] for row in query.all())
    return referenced


def cleanup_orphan_files(db: Session, *, now: datetime | None = None) -> int:
    """Soft delete + usunięcie z dysku plików bez referencji starszych niż
    TTL. Zwraca liczbę posprzątanych plików."""
    now = now or datetime.now(UTC)
    cutoff = (now - timedelta(hours=settings.orphan_file_ttl_hours)).isoformat()
    referenced = _referenced_file_ids(db)
    orphans = (
        db.query(StoredFile)
        .filter(StoredFile.deleted_at.is_(None), StoredFile.created_at < cutoff)
        .all()
    )
    cleaned = 0
    for stored in orphans:
        if stored.id in referenced:
            continue
        storage.delete(stored)
        stored.deleted_at = now_iso()
        cleaned += 1
    if cleaned:
        record_event(
            db,
            action="ORPHAN_FILES_CLEANED",
            actor_id="SYSTEM",
            subject_ids=[],
            payload={"count": cleaned, "ttl_hours": settings.orphan_file_ttl_hours},
            summary=f"Sprzątanie plików-sierot: {cleaned} plik(ów) po TTL",
        )
    return cleaned

"""Abstrakcja przechowywania plików. MVP: dysk lokalny pod losowymi
nazwami (bez rozszerzeń z uploadu w ścieżce). Interfejs pozwala później
podmienić backend (S3 itp.) bez zmian w routerach.

Twarde reguły uploadu (patrz też file_safety.py):
* allowlista typów MIME (config.ALLOWED_UPLOAD_TYPES; bez SVG i plików
  wykonywalnych),
* limit rozmiaru egzekwowany strumieniowo (przerwanie odczytu zaraz po
  przekroczeniu limitu, bez wczytywania reszty do RAM),
* zawartość musi zgadzać się z deklarowanym typem (magic bytes),
* nazwa pliku sanityzowana z wymuszonym kanonicznym rozszerzeniem typu,
* zdjęcia (NOWE uploady image/*): usunięcie EXIF/GPS, ograniczenie
  rozdzielczości i rekompresja — pliki wgrane przed tą zmianą pozostają
  na dysku bez modyfikacji (świadoma decyzja: brak retroaktywnego
  przetwarzania istniejących danych).
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from . import file_safety
from .config import settings
from .models import StoredFile, new_id

_READ_CHUNK = 1024 * 1024  # 1 MB


async def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Czyta upload w kawałkach i przerywa natychmiast po przekroczeniu
    limitu — klient nie może zapełnić RAM jednym żądaniem."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413, detail=f"Plik przekracza limit {settings.max_upload_mb} MB"
            )
        chunks.append(chunk)
    return b"".join(chunks)


class LocalStorage:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_upload(
        self, db: Session, upload: UploadFile, *, owner_user_id: str, uploaded_by: str
    ) -> StoredFile:
        content_type = (upload.content_type or "").lower()
        if content_type not in settings.ALLOWED_UPLOAD_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Niedozwolony typ pliku. Dozwolone: JPG, PNG, WEBP, PDF, "
                "MP4 oraz audio (WEBM/M4A/MP3/OGG).",
            )
        max_bytes = settings.max_upload_mb * 1024 * 1024
        data = await _read_limited(upload, max_bytes)
        if not data:
            raise HTTPException(status_code=400, detail="Pusty plik")
        # Typ po ZAWARTOŚCI: deklaracja MIME musi zgadzać się z magic bytes
        # (odrzuca m.in. pliki wykonywalne/SVG przemycane pod innym typem).
        if not file_safety.content_matches_type(content_type, data):
            raise HTTPException(
                status_code=415,
                detail="Zawartość pliku nie zgadza się z deklarowanym typem.",
            )
        if content_type.startswith("image/"):
            # Tylko NOWE uploady: EXIF/GPS out, maks. rozdzielczość, rekompresja.
            try:
                data = file_safety.process_image(
                    data,
                    content_type,
                    max_px=settings.max_image_px,
                    quality=settings.image_quality,
                )
            except ValueError:
                raise HTTPException(
                    status_code=415, detail="Uszkodzony lub nieprawidłowy plik obrazu."
                ) from None
        ext = settings.ALLOWED_UPLOAD_TYPES[content_type]
        rel_path = f"{uuid.uuid4().hex}{ext}"
        (self.root / rel_path).write_bytes(data)
        stored = StoredFile(
            id=new_id("FIL"),
            owner_user_id=owner_user_id,
            filename=file_safety.sanitize_filename(upload.filename, ext)[:300],
            content_type=content_type,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            storage_path=rel_path,
            uploaded_by=uploaded_by,
        )
        db.add(stored)
        return stored

    def _resolved(self, stored: StoredFile) -> Path:
        """Ścieżka pliku po weryfikacji, że nie wychodzi poza katalog
        uploadów (obrona przed path traversal w storage_path)."""
        path = (self.root / stored.storage_path).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"storage_path poza katalogiem uploadów: {stored.id}")
        return path

    def read(self, stored: StoredFile) -> bytes:
        try:
            return self._resolved(stored).read_bytes()
        except (ValueError, OSError):
            # Wpis wskazujący poza katalog lub brak pliku na dysku —
            # nie ujawniamy szczegółów, dla klienta zasób nie istnieje.
            raise HTTPException(status_code=404, detail="Nie znaleziono") from None

    def delete(self, stored: StoredFile) -> None:
        if not stored.storage_path:
            return
        try:
            path = self._resolved(stored)
        except ValueError:
            return  # nie dotykamy niczego poza katalogiem uploadów
        if path.exists():
            path.unlink()


storage = LocalStorage()

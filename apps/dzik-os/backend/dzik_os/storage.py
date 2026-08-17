"""Abstrakcja przechowywania plików. MVP: dysk lokalny pod losowymi
nazwami (bez rozszerzeń z uploadu w ścieżce). Interfejs pozwala później
podmienić backend (S3 itp.) bez zmian w routerach."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from .config import settings
from .models import StoredFile, new_id


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
                detail="Niedozwolony typ pliku. Dozwolone: JPG, PNG, WEBP, PDF, MP4.",
            )
        max_bytes = settings.max_upload_mb * 1024 * 1024
        data = await upload.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413, detail=f"Plik przekracza limit {settings.max_upload_mb} MB"
            )
        if not data:
            raise HTTPException(status_code=400, detail="Pusty plik")
        ext = settings.ALLOWED_UPLOAD_TYPES[content_type]
        rel_path = f"{uuid.uuid4().hex}{ext}"
        (self.root / rel_path).write_bytes(data)
        stored = StoredFile(
            id=new_id("FIL"),
            owner_user_id=owner_user_id,
            filename=(upload.filename or "plik")[:300],
            content_type=content_type,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            storage_path=rel_path,
            uploaded_by=uploaded_by,
        )
        db.add(stored)
        return stored

    def read(self, stored: StoredFile) -> bytes:
        return (self.root / stored.storage_path).read_bytes()

    def delete(self, stored: StoredFile) -> None:
        path = self.root / stored.storage_path
        if path.exists():
            path.unlink()


storage = LocalStorage()

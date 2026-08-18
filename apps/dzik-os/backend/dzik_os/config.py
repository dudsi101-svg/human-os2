from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Settings:
    """Konfiguracja aplikacji. Wszystkie wartości pochodzą ze zmiennych
    środowiskowych (patrz .env.example); brak sekretów w repozytorium."""

    env: str = field(default_factory=lambda: _env("DZIK_ENV", "dev"))
    database_url: str = field(
        default_factory=lambda: _env("DZIK_DATABASE_URL", "sqlite:///data/dzik.db")
    )
    # Łańcuch audytu Human OS trzymamy zawsze w dedykowanym pliku SQLite
    # (hos_engine.sqlite_store.SQLiteEventStore) — patrz ADR-DZIK-002.
    audit_db_path: str = field(default_factory=lambda: _env("DZIK_AUDIT_DB", "data/audit.db"))
    upload_dir: str = field(default_factory=lambda: _env("DZIK_UPLOAD_DIR", "data/uploads"))
    max_upload_mb: int = field(default_factory=lambda: int(_env("DZIK_MAX_UPLOAD_MB", "20")))
    # Zdjęcia (nowe uploady image/*): usunięcie EXIF/GPS + ograniczenie
    # rozdzielczości (dłuższy bok) + rekompresja o podanej jakości.
    max_image_px: int = field(default_factory=lambda: int(_env("DZIK_MAX_IMAGE_PX", "2560")))
    image_quality: int = field(default_factory=lambda: int(_env("DZIK_IMAGE_QUALITY", "85")))
    # Limity zdjęć dołączanych do jednego raportu tygodniowego.
    max_checkin_photos: int = field(
        default_factory=lambda: int(_env("DZIK_MAX_CHECKIN_PHOTOS", "8"))
    )
    max_checkin_photos_total_mb: int = field(
        default_factory=lambda: int(_env("DZIK_MAX_CHECKIN_PHOTOS_TOTAL_MB", "60"))
    )
    # Sprzątanie plików-sierot: upload nigdy nie podpięty do raportu/
    # wiadomości/dokumentu/bazy wiedzy/treningu starszy niż N godzin
    # dostaje soft delete (deleted_at) i znika z dysku.
    orphan_file_ttl_hours: int = field(
        default_factory=lambda: int(_env("DZIK_ORPHAN_FILE_TTL_H", "24"))
    )
    session_ttl_hours: int = field(default_factory=lambda: int(_env("DZIK_SESSION_TTL_H", "72")))
    login_max_attempts: int = field(default_factory=lambda: int(_env("DZIK_LOGIN_MAX_ATTEMPTS", "5")))
    login_lockout_minutes: int = field(
        default_factory=lambda: int(_env("DZIK_LOGIN_LOCKOUT_MIN", "15"))
    )
    # Koszt bcrypt (12 = produkcja; testy mogą obniżyć dla szybkości).
    bcrypt_rounds: int = field(default_factory=lambda: int(_env("DZIK_BCRYPT_ROUNDS", "12")))
    # AI jest opcjonalne i domyślnie WYŁĄCZONE — aplikacja działa w pełni bez AI.
    ai_enabled: bool = field(default_factory=lambda: _env("DZIK_AI_ENABLED", "false") == "true")
    cors_origins: str = field(default_factory=lambda: _env("DZIK_CORS_ORIGINS", ""))
    # Marka konfigurowalna (nazwa/kolor — używane też przez frontend przez /api/branding).
    brand_name: str = field(default_factory=lambda: _env("DZIK_BRAND_NAME", "Dzik OS"))
    brand_coach_name: str = field(
        default_factory=lambda: _env("DZIK_BRAND_COACH", "Lubelski Dzik")
    )
    brand_accent: str = field(default_factory=lambda: _env("DZIK_BRAND_ACCENT", "#b8f339"))
    # Web Push (VAPID): klucz prywatny trwały na wolumenie danych —
    # generowany automatycznie przy pierwszym użyciu, bez sekretów w repo.
    vapid_key_path: str = field(default_factory=lambda: _env("DZIK_VAPID_KEY", "data/vapid.pem"))
    push_contact: str = field(
        default_factory=lambda: _env("DZIK_PUSH_CONTACT", "mailto:admin@example.com")
    )
    # Strefa czasowa przypomnień harmonogramu (czas lokalny użytkowników).
    timezone: str = field(default_factory=lambda: _env("DZIK_TZ", "Europe/Warsaw"))

    ALLOWED_UPLOAD_TYPES: ClassVar[dict[str, str]] = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
        "video/mp4": ".mp4",
        # Wiadomości głosowe (nagrywane w przeglądarce przez MediaRecorder).
        "audio/webm": ".webm",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
    }

    def ensure_dirs(self) -> None:
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.audit_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.vapid_key_path).parent.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite:///"):
            Path(self.database_url.removeprefix("sqlite:///")).parent.mkdir(
                parents=True, exist_ok=True
            )


settings = Settings()

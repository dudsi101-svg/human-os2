from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


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

    ALLOWED_UPLOAD_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
        "video/mp4": ".mp4",
    }

    def ensure_dirs(self) -> None:
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.audit_db_path).parent.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite:///"):
            Path(self.database_url.removeprefix("sqlite:///")).parent.mkdir(
                parents=True, exist_ok=True
            )


settings = Settings()

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
    # --- Poczta wychodząca (opcjonalna) ---
    # Puste `smtp_host` = dostawca `null`, czyli stan sprzed 0.42.0:
    # aplikacja bez konfiguracji zachowuje się DOKŁADNIE tak jak dotąd
    # i nie wysyła nic. Hasło wyłącznie ze zmiennej środowiskowej.
    # Identyfikacja builda (audyt P1-5): wstrzykiwane przez deploy
    # (--env), lokalnie "dev". Health je zwraca, smoke test porównuje.
    app_version: str = field(default_factory=lambda: _env("DZIK_APP_VERSION", "dev"))
    build_sha: str = field(default_factory=lambda: _env("DZIK_BUILD_SHA", "dev"))
    # Limit niezakończonych współprac per trener (skala pilotażu, decyzja
    # właściciela 25.08: 10 podopiecznych). ENDED zwalnia miejsce; 0 = bez
    # limitu. Egzekwowany przy zapraszaniu klienta (routers/clients.py).
    max_clients: int = field(
        default_factory=lambda: int(_env("DZIK_MAX_CLIENTS", "10"))
    )
    smtp_host: str = field(default_factory=lambda: _env("DZIK_SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(_env("DZIK_SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: _env("DZIK_SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: _env("DZIK_SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: _env("DZIK_SMTP_FROM", ""))
    #: "starttls" (domyślnie, port 587), "ssl" (port 465) albo "none" (test).
    smtp_security: str = field(default_factory=lambda: _env("DZIK_SMTP_SECURITY", "starttls"))
    #: Sekundy. Bez limitu zawieszony serwer poczty zablokowałby cały
    #: jednoprocesowy backend — powiadomienie nie może wstrzymać aplikacji.
    smtp_timeout: float = field(default_factory=lambda: float(_env("DZIK_SMTP_TIMEOUT", "10")))
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
    # Szyfrowanie at-rest plików uploadów (R-02): klucz AES-256 w base64
    # (32 bajty po zdekodowaniu). Pusty = zapis jawny jak dotychczas.
    # Generowanie: python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
    file_key_b64: str = field(default_factory=lambda: _env("DZIK_FILE_KEY", ""))
    # Kopie zapasowe (R-12): katalog archiwów i retencja (ile najnowszych zostaje).
    backup_dir: str = field(default_factory=lambda: _env("DZIK_BACKUP_DIR", "data/backups"))
    backup_keep: int = field(default_factory=lambda: int(_env("DZIK_BACKUP_KEEP", "14")))
    session_ttl_hours: int = field(default_factory=lambda: int(_env("DZIK_SESSION_TTL_H", "72")))
    login_max_attempts: int = field(default_factory=lambda: int(_env("DZIK_LOGIN_MAX_ATTEMPTS", "5")))
    login_lockout_minutes: int = field(
        default_factory=lambda: int(_env("DZIK_LOGIN_LOCKOUT_MIN", "15"))
    )
    # Koszt bcrypt (12 = produkcja; testy mogą obniżyć dla szybkości).
    bcrypt_rounds: int = field(default_factory=lambda: int(_env("DZIK_BCRYPT_ROUNDS", "12")))
    # Zaproszenia do aktywacji konta (link jednorazowy) i reset hasła.
    invitation_ttl_days: int = field(
        default_factory=lambda: int(_env("DZIK_INVITATION_TTL_DAYS", "7"))
    )
    reset_token_ttl_minutes: int = field(
        default_factory=lambda: int(_env("DZIK_RESET_TOKEN_TTL_MIN", "60"))
    )
    # Limit żądań resetu hasła (osobno per e-mail i per IP, okno przesuwne).
    reset_max_requests: int = field(
        default_factory=lambda: int(_env("DZIK_RESET_MAX_REQUESTS", "5"))
    )
    reset_window_minutes: int = field(
        default_factory=lambda: int(_env("DZIK_RESET_WINDOW_MIN", "60"))
    )
    # Krok pośredni logowania z MFA (token wyzwania) — krótkie TTL.
    mfa_challenge_ttl_minutes: int = field(
        default_factory=lambda: int(_env("DZIK_MFA_CHALLENGE_TTL_MIN", "5"))
    )
    # Role z OBOWIĄZKOWYM MFA (TOTP): konto bez skonfigurowanego MFA dostaje
    # po zalogowaniu wyłącznie dostęp do konfiguracji MFA. Pusta wartość
    # wyłącza wymuszanie (używane w testach; produkcja: COACH,ADMIN).
    mfa_required_roles: str = field(
        default_factory=lambda: _env("DZIK_MFA_REQUIRED_ROLES", "COACH,ADMIN")
    )
    # Publiczny adres aplikacji do linków w e-mailach (aktywacja/reset).
    # Pusty = użyj adresu bieżącego żądania (deployment same-origin).
    public_base_url: str = field(default_factory=lambda: _env("DZIK_PUBLIC_URL", ""))
    # AI jest opcjonalne i domyślnie WYŁĄCZONE — aplikacja działa w pełni bez AI.
    ai_enabled: bool = field(default_factory=lambda: _env("DZIK_AI_ENABLED", "false") == "true")
    # Klucz dostawcy WYŁĄCZNIE ze środowiska (sekret Fly) — nigdy w repo.
    # Sam klucz bez DZIK_AI_ENABLED=true niczego nie włącza: uruchomienie
    # AI wymaga podwójnej, świadomej decyzji operatora.
    ai_api_key: str = field(default_factory=lambda: _env("DZIK_AI_API_KEY", ""))
    ai_model: str = field(default_factory=lambda: _env("DZIK_AI_MODEL", "claude-opus-5"))
    # Górny limit tokenów JEDNEJ odpowiedzi modelu (kontrola kosztów).
    ai_max_tokens: int = field(default_factory=lambda: int(_env("DZIK_AI_MAX_TOKENS", "4000")))
    # Limit czasu JEDNEGO wywołania dostawcy modelu. Po nim rozmowa schodzi
    # do trybu formularza z jawnym komunikatem (nigdy wieczny spinner).
    ai_timeout_s: int = field(default_factory=lambda: int(_env("DZIK_AI_TIMEOUT_S", "20")))
    # Twarde limity dzienne wywołań modelu (kontrola kosztów): per konto
    # i globalnie dla całej aplikacji. Przekroczenie = tryb formularza
    # z wyjaśnieniem, nie błąd (docs/ONBOARDING_AI.md §limity).
    ai_daily_calls_user: int = field(
        default_factory=lambda: int(_env("DZIK_AI_DAILY_CALLS_USER", "20"))
    )
    ai_daily_calls_global: int = field(
        default_factory=lambda: int(_env("DZIK_AI_DAILY_CALLS_GLOBAL", "500"))
    )
    # Górna granica rozmiaru sekcji DANE_KLIENTA wysyłanej do dostawcy —
    # minimalizacja zakresu i przewidywalny koszt pojedynczego wywołania.
    ai_max_input_chars: int = field(
        default_factory=lambda: int(_env("DZIK_AI_MAX_INPUT_CHARS", "6000"))
    )
    # --- Przepisywanie tekstu ze zdjęcia (OCR) — docs/OCR.md ---
    # Binarka silnika lokalnego. Brak binarki NIE jest błędem: funkcja
    # zgłasza wtedy jawny stan „silnik niedostępny" (środowisko testowe i
    # deweloperskie nie mają Tesseracta).
    ocr_binary: str = field(default_factory=lambda: _env("DZIK_OCR_BINARY", "tesseract"))
    ocr_languages: str = field(default_factory=lambda: _env("DZIK_OCR_LANGS", "pol+eng"))
    # Układ strony Tesseracta: 6 = jednolity blok tekstu (etykiety, kartki).
    ocr_psm: int = field(default_factory=lambda: int(_env("DZIK_OCR_PSM", "6")))
    # Fly.io shared-cpu-1x ma 512 MB RAM — obraz jest zmniejszany PRZED
    # rozpoznaniem, a zadanie ma twardy limit czasu.
    ocr_max_px: int = field(default_factory=lambda: int(_env("DZIK_OCR_MAX_PX", "1600")))
    ocr_timeout_s: int = field(default_factory=lambda: int(_env("DZIK_OCR_TIMEOUT_S", "25")))
    # Górny limit rozmiaru pliku wejściowego (osobno od limitu uploadu:
    # OCR czyta plik do pamięci i zmniejsza go Pillow).
    ocr_max_input_mb: int = field(default_factory=lambda: int(_env("DZIK_OCR_MAX_INPUT_MB", "8")))
    # Kolejka JEDNOSLOTOWA: jedno rozpoznanie naraz. To liczba zadań
    # CZEKAJĄCYCH — po przepełnieniu zlecenie dostaje czytelne 429.
    ocr_queue_max: int = field(default_factory=lambda: int(_env("DZIK_OCR_QUEUE_MAX", "20")))
    # Limit dzienny zadań na konto (ochrona maszyny, nie kosztów modelu).
    ocr_daily_tasks_user: int = field(
        default_factory=lambda: int(_env("DZIK_OCR_DAILY_TASKS_USER", "50"))
    )
    # --- Asystent trenera (docs/ASYSTENT_TRENERA.md) ---
    # Poczekalnia zadań asystenta. Po przepełnieniu zlecenie dostaje
    # czytelne 429 zamiast rosnącej w nieskończoność kolejki.
    assistant_queue_max: int = field(
        default_factory=lambda: int(_env("DZIK_ASSISTANT_QUEUE_MAX", "20"))
    )
    # Limit dzienny zadań asystenta na konto trenera (ochrona kosztów
    # i maszyny; osobno od limitu wywołań modelu ai_daily_calls_user).
    assistant_daily_tasks_user: int = field(
        default_factory=lambda: int(_env("DZIK_ASSISTANT_DAILY_TASKS_USER", "40"))
    )
    # Po tylu sekundach interfejs mówi wprost „trwa dłużej niż zwykle”
    # (płynność: żadnej wiszącej kręciołki bez wyjaśnienia).
    assistant_slow_after_s: int = field(
        default_factory=lambda: int(_env("DZIK_ASSISTANT_SLOW_AFTER_S", "8"))
    )
    # Twardy limit czasu CAŁEGO zadania asystenta. Po nim zadanie kończy
    # się statusem FAILED z komunikatem, nigdy wiszącym stanem RUNNING.
    assistant_timeout_s: int = field(
        default_factory=lambda: int(_env("DZIK_ASSISTANT_TIMEOUT_S", "60"))
    )
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
    # Kanał czasu rzeczywistego (SSE, /api/threads/events): co ile sekund
    # wysyłany jest keepalive (komentarz SSE) i sprawdzana ważność sesji.
    sse_keepalive_s: int = field(
        default_factory=lambda: int(_env("DZIK_SSE_KEEPALIVE_S", "25"))
    )

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

"""Wspólny moduł dat i stref czasowych (jedno źródło prawdy).

Model dat w aplikacji (patrz też frontend/src/dates.ts):

1. **Data kalendarzowa użytkownika** — `performed_on`, `logged_on`,
   `occurred_on`, `completed_on`, `week_start`, `measured_at` (pomiary),
   `due_date`, `start_date`/`end_date`, `target_date`, `taken_at` (zdjęcia):
   format ``YYYY-MM-DD`` wyliczony w LOKALNEJ strefie użytkownika
   (frontend: strefa przeglądarki; backend: `tz_for_user()`). Nigdy nie
   wyliczać jej przez ``datetime.now(UTC).date()`` — o 00:30 czasu
   polskiego dałoby to wczorajszą datę.

2. **Dokładny moment zdarzenia** — `created_at`, `updated_at`, `paid_at`,
   `read_at`, `booked_at`, `granted_at`, łańcuch audytu: pełny timestamp
   UTC (`models.now_iso()`); do strefy lokalnej przeliczany dopiero przy
   prezentacji (frontend `plDateTime`).

3. **Termin lokalny** — `consult_slots.starts_at`: naiwny
   ``YYYY-MM-DDTHH:MM`` w strefie `tz_for_user()`; porównywany wyłącznie
   z `local_now_minute()` (nigdy z czasem UTC).

4. **Data rozliczeniowa** — `payment_records.due_date`: jak (1); zaległość
   ("overdue") liczona względem `local_today()`.

Parametr ``user`` to punkt rozszerzenia pod strefę per użytkownik —
przekazuj obiekt `User` tam, gdzie jest pod ręką, a gdy w przyszłości
zyska pole `timezone`, wystarczy zmiana w `tz_for_user()`.
Parametr ``now`` (świadomy datetime, zwykle UTC) służy testom.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from .config import settings


def tz_for_user(user: object | None = None) -> ZoneInfo:
    """Strefa czasowa użytkownika.

    Od migracji nr 14 model `User` ma pole `timezone` (IANA, ustawiane w
    ustawieniach powiadomień); NULL lub brak obiektu = strefa aplikacji
    (DZIK_TZ, domyślnie Europe/Warsaw). Nieznana nazwa strefy w bazie nie
    może wywrócić żądania — fallback do strefy aplikacji.
    """
    tz_name = getattr(user, "timezone", None) or settings.timezone
    try:
        return ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 - uszkodzona wartość nie psuje aplikacji
        return ZoneInfo(settings.timezone)


def local_now(user: object | None = None, *, now: datetime | None = None) -> datetime:
    """Bieżący czas w lokalnej strefie użytkownika (świadomy datetime)."""
    instant = now if now is not None else datetime.now(UTC)
    return instant.astimezone(tz_for_user(user))


def local_today(user: object | None = None, *, now: datetime | None = None) -> date:
    """Dzisiejsza data kalendarzowa w lokalnej strefie użytkownika."""
    return local_now(user, now=now).date()


def local_today_iso(user: object | None = None, *, now: datetime | None = None) -> str:
    """`local_today()` jako ``YYYY-MM-DD`` (format API/bazy)."""
    return local_today(user, now=now).isoformat()


def local_now_minute(user: object | None = None, *, now: datetime | None = None) -> str:
    """Lokalny czas z dokładnością do minuty (``YYYY-MM-DDTHH:MM``) —
    jedyny poprawny komparand dla `consult_slots.starts_at`."""
    return local_now(user, now=now).strftime("%Y-%m-%dT%H:%M")


def parse_iso_date(value: str) -> date:
    """Parsuje datę kalendarzową ``YYYY-MM-DD`` (bez strefy — data nie jest
    momentem). Podnosi ValueError dla nieprawidłowego wejścia."""
    return date.fromisoformat(value[:10])

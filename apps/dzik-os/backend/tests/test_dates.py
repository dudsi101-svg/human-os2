"""Testy wspólnego modułu dat (dzik_os/dates.py).

Kryterium akceptacji naprawy stref czasowych: rekord utworzony 18 sierpnia
o 01:00 czasu polskiego dostaje datę kalendarzową 2026-08-18 (stary kod
liczył datę z UTC i zapisywał 2026-08-17).
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from dzik_os.config import settings
from dzik_os.dates import (
    local_now,
    local_now_minute,
    local_today,
    local_today_iso,
    parse_iso_date,
    tz_for_user,
)


def utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=UTC)


# --- granica północy w Polsce (kryterium akceptacji) -----------------------

def test_0030_polish_time_is_already_next_day_summer():
    # 17.08 22:30 UTC = 18.08 00:30 czasu polskiego (CEST, UTC+2).
    assert local_today_iso(now=utc(2026, 8, 17, 22, 30)) == "2026-08-18"


def test_0100_polish_time_is_already_next_day_summer():
    # KRYTERIUM AKCEPTACJI: 18.08 o 01:00 czasu polskiego → 2026-08-18.
    assert local_today_iso(now=utc(2026, 8, 17, 23, 0)) == "2026-08-18"


def test_2359_polish_time_is_still_same_day():
    # 18.08 21:59 UTC = 18.08 23:59 czasu polskiego — wciąż 18.08.
    assert local_today_iso(now=utc(2026, 8, 18, 21, 59)) == "2026-08-18"


def test_0030_polish_time_winter_month_boundary():
    # Czas zimowy (CET, UTC+1) + koniec miesiąca:
    # 31.01 23:30 UTC = 01.02 00:30 czasu polskiego.
    assert local_today_iso(now=utc(2026, 1, 31, 23, 30)) == "2026-02-01"


def test_new_year_boundary():
    # 31.12 23:30 UTC = 01.01 00:30 czasu polskiego — zmiana roku.
    assert local_today_iso(now=utc(2025, 12, 31, 23, 30)) == "2026-01-01"


# --- zmiany czasu (DST) ----------------------------------------------------

def test_dst_spring_forward_night():
    # Noc zmiany na czas letni 2026: 29.03, 02:00 CET → 03:00 CEST.
    # 01:30 UTC tej nocy = 03:30 lokalnie (już +2) — wciąż 29.03.
    now = utc(2026, 3, 29, 1, 30)
    assert local_today_iso(now=now) == "2026-03-29"
    assert local_now(now=now).strftime("%H:%M") == "03:30"


def test_dst_fall_back_night():
    # Noc zmiany na czas zimowy 2026: 25.10, 03:00 CEST → 02:00 CET.
    # Godzina 02:30 lokalna występuje dwa razy — data jest ta sama.
    assert local_today_iso(now=utc(2026, 10, 25, 0, 30)) == "2026-10-25"  # 02:30 CEST
    assert local_today_iso(now=utc(2026, 10, 25, 1, 30)) == "2026-10-25"  # 02:30 CET
    # Dzień PRZED zmianą i PO zmianie różnią się offsetem, ale data
    # kalendarzowa liczona lokalnie pozostaje spójna z dniem użytkownika.
    assert local_today_iso(now=utc(2026, 10, 24, 22, 30)) == "2026-10-25"  # 00:30 CEST
    assert local_today_iso(now=utc(2026, 10, 25, 23, 30)) == "2026-10-26"  # 00:30 CET


# --- strefa konfigurowalna i punkt rozszerzenia per użytkownik -------------

def test_default_timezone_is_warsaw():
    assert str(tz_for_user()) == settings.timezone == "Europe/Warsaw"


def test_timezone_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "timezone", "America/New_York")
    # 18.08 01:00 UTC = 17.08 21:00 w Nowym Jorku — data lokalna wsteczna.
    assert local_today_iso(now=utc(2026, 8, 18, 1, 0)) == "2026-08-17"


def test_per_user_timezone_extension_point():
    # Gdy User zyska pole `timezone`, tz_for_user() ma je honorować już
    # dziś — bez zmian w miejscach wywołań.
    class FakeUser:
        timezone = "Asia/Tokyo"

    assert tz_for_user(FakeUser()) == ZoneInfo("Asia/Tokyo")
    # 17.08 23:00 UTC = 18.08 08:00 w Tokio.
    assert local_today(FakeUser(), now=utc(2026, 8, 17, 23, 0)).isoformat() == "2026-08-18"


def test_user_without_timezone_falls_back_to_app_tz():
    class FakeUser:
        pass  # brak pola timezone (dzisiejszy model User)

    assert tz_for_user(FakeUser()) == ZoneInfo(settings.timezone)


# --- czas lokalny do minuty (terminy konsultacji) --------------------------

def test_local_now_minute_format_and_zone():
    # 18.08 07:05 UTC = 09:05 czasu polskiego (CEST).
    assert local_now_minute(now=utc(2026, 8, 18, 7, 5)) == "2026-08-18T09:05"


# --- parsowanie dat z API --------------------------------------------------

def test_parse_iso_date_plain():
    assert parse_iso_date("2026-08-18").isoformat() == "2026-08-18"


def test_parse_iso_date_tolerates_datetime_prefix():
    # Obronnie: gdy w polu daty pojawi się pełniejszy zapis, liczy się dzień.
    assert parse_iso_date("2026-08-18T01:00").isoformat() == "2026-08-18"


def test_parse_iso_date_rejects_garbage():
    with pytest.raises(ValueError):
        parse_iso_date("nie-data")

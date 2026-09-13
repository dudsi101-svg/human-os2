"""Daty i odstępy (§10, §13): lokalny kalendarz, bloki 7 dni, sprawdzanie
odstępu jako rzeczywistego czasu (także przez zmianę czasu)."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def daty_horyzontu(start: date, tryb: str) -> list[date]:
    """rolling_28 = 28 kolejnych dat; calendar_month = do dnia przed tą samą
    datą następnego miesiąca (28–31 dat), dni 29–31 kontynuują kolejkę."""
    if tryb == "calendar_month":
        rok, mies = (start.year + (start.month == 12), start.month % 12 + 1)
        ostatni = calendar.monthrange(rok, mies)[1]
        koniec = date(rok, mies, min(start.day, ostatni)) - timedelta(days=1)
        n = (koniec - start).days + 1
    else:
        n = 28
    return [start + timedelta(days=i) for i in range(n)]


def moment(d: date, hhmm: str, strefa: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(d.year, d.month, d.day, h, m, tzinfo=ZoneInfo(strefa))


def rozpisz_sesje(daty: list[date], dostepne: list[int], sekwencja: list[str]) -> dict[date, str]:
    """W każdym bloku 7 dni od startu przydziela jednostki po kolei do
    dostępnych dni tygodnia; kolejka jednostek biegnie dalej w dniach
    29–31 (tryb kalendarzowy) bez restartu w niepełnym bloku."""
    wynik: dict[date, str] = {}
    idx = 0
    for i, d in enumerate(daty):
        if i % 7 == 0 and i + 7 <= len(daty):
            idx = 0  # pełny blok 7 dni zaczyna sekwencję od nowa
        if d.weekday() in dostepne:
            wynik[d] = sekwencja[idx % len(sekwencja)]
            idx += 1
    return wynik


def konflikty_odstepu(sesje: list[tuple[datetime, list[str]]], min_h: int) -> list[tuple[datetime, datetime, str]]:
    """Pary sesji tej samej głównej grupy bliżej niż `min_h` godzin
    rzeczywistego czasu (porównanie w UTC — zmiana czasu nie myli)."""
    ostatnio: dict[str, datetime] = {}
    zle = []
    for kiedy, grupy in sesje:
        for g in grupy:
            if g in ostatnio and (kiedy - ostatnio[g]).total_seconds() < min_h * 3600:
                zle.append((ostatnio[g], kiedy, g))
        for g in grupy:
            ostatnio[g] = kiedy
    return zle

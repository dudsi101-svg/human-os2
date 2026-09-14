"""Nawyki — silnik postępu (0.63.0). Czyste funkcje, bez bazy i bez AI.

Model: nawyk ma dni tygodnia, datę startu i termin (`target_days`). Postęp
liczony **sekwencyjnie** po zaplanowanych dniach od startu do dziś:
dzień wykonany +1; zaplanowany dzień, który minął bez wykonania −1
(łagodny decay — decyzja właściciela 14.09, nie reset); podłoga 0 po
każdym kroku (długa przerwa nie tworzy „długu”); dni poza `days_of_week`
neutralne; dzisiejszy dzień nie karze, dopóki nie minie. Postęp ≥ termin
= absolutorium (nawyk utrwalony — aplikacja przestaje go pilnować).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

DNI_DOMYSLNE = "1,2,3,4,5,6,7"
TERMIN_MIN, TERMIN_MAX, TERMIN_DOMYSLNY = 14, 254, 66
LIMIT_AKTYWNYCH = 3

STATUS_ACTIVE = "ACTIVE"
STATUS_GRADUATED = "GRADUATED"
STATUS_ARCHIVED = "ARCHIVED"
STATUSY = (STATUS_ACTIVE, STATUS_GRADUATED, STATUS_ARCHIVED)


def dni_tygodnia(tekst: str | None) -> set[int]:
    """„1,3,5” → {1, 3, 5} (ISO: 1 = poniedziałek … 7 = niedziela). Puste/
    niepoprawne → wszystkie dni (bezpieczny domyślny)."""
    dni: set[int] = set()
    for p in (tekst or "").split(","):
        p = p.strip()
        if p.isdigit() and 1 <= int(p) <= 7:
            dni.add(int(p))
    return dni or set(range(1, 8))


def zaplanowane(started_on: date, today: date, dni: set[int]) -> list[date]:
    """Zaplanowane dni od startu do dziś włącznie (rosnąco)."""
    if today < started_on:
        return []
    out: list[date] = []
    d = started_on
    while d <= today:
        if d.isoweekday() in dni:
            out.append(d)
        d += timedelta(days=1)
    return out


@dataclass(frozen=True)
class Postep:
    progress: int
    done_count: int
    planned_count: int
    missed_count: int
    scheduled_today: bool
    done_today: bool


def postep(started_on: date, today: date, dni: set[int], wykonane: set[date]) -> Postep:
    plan = zaplanowane(started_on, today, dni)
    p = 0
    done = missed = 0
    for d in plan:
        if d in wykonane:
            p += 1
            done += 1
        elif d < today:
            p = max(0, p - 1)
            missed += 1
        # d == today bez wykonania: neutralne, dopóki dzień nie minie
    return Postep(progress=p, done_count=done, planned_count=len(plan), missed_count=missed,
                  scheduled_today=today.isoweekday() in dni and today >= started_on,
                  done_today=today in wykonane)


def absolutorium(progress: int, target_days: int) -> bool:
    return progress >= target_days


def imie(display_name: str | None) -> str:
    """Pierwszy człon nazwy wyświetlanej („Anna Wilk” → „Anna”)."""
    return (display_name or "").strip().split(" ")[0] if display_name and display_name.strip() else ""


def opis_postepu(progress: int, target_days: int) -> str:
    """Delikatny opis bez zawstydzania — sam stan, żadnej kary."""
    if progress >= target_days:
        return f"{target_days} z {target_days} — to już Twój nawyk"
    if progress == 0:
        return f"0 z {target_days} — każdy dzień to nowy start"
    if progress < target_days * 0.34:
        return f"{progress} z {target_days} — nawyk się rozkręca"
    if progress < target_days * 0.67:
        return f"{progress} z {target_days} — nawyk się utrwala"
    return f"{progress} z {target_days} — już prawie Twój"

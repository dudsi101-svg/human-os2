"""Mechanika wagi (spec §9) — czyste funkcje.

Średnia krocząca 7 dni (okno wymaga min. 3 pomiarów), trend z regresji
liniowej po średniej z 28 dni w kg/tydzień (dopiero przy ≥ 14 dniach danych
i ≥ 6 pomiarach). Klientowi nigdy nie pokazujemy pojedynczego pomiaru jako
„Twojej wagi” — zawsze średnią.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

OKNO_SREDNIEJ_DNI = 7
MIN_POMIAROW_W_OKNIE = 3
OKNO_TRENDU_DNI = 28
MIN_DNI_TRENDU = 14
MIN_POMIAROW_TRENDU = 6
KOMUNIKAT_TRENDU = "Zbieramy dane — trend pojawi się po dwóch tygodniach"
KOMUNIKAT_KAFELKA = "Za mało pomiarów (min. 3 w 14 dniach)"


@dataclass(frozen=True)
class Punkt:
    day: date
    value: float


def _dzien(d: str | date) -> date:
    return d if isinstance(d, date) else date.fromisoformat(str(d)[:10])


def pomiary(surowe: list[tuple[str | date, float]]) -> list[Punkt]:
    """Ostatni pomiar dnia liczy się (kilka ważeń jednego dnia → jeden punkt)."""
    per_dzien: dict[date, float] = {}
    for d, v in sorted(((_dzien(d), float(v)) for d, v in surowe), key=lambda p: p[0]):
        per_dzien[d] = v
    return [Punkt(d, v) for d, v in sorted(per_dzien.items())]


def srednia_kroczaca(punkty: list[Punkt], okno: int = OKNO_SREDNIEJ_DNI,
                     min_n: int = MIN_POMIAROW_W_OKNIE) -> list[Punkt]:
    """Średnia z pomiarów w oknie (dzień − okno + 1 … dzień); punkt tylko,
    gdy w oknie jest ≥ `min_n` pomiarów."""
    out: list[Punkt] = []
    for p in punkty:
        od = p.day - timedelta(days=okno - 1)
        w_oknie = [q.value for q in punkty if od <= q.day <= p.day]
        if len(w_oknie) >= min_n:
            out.append(Punkt(p.day, round(sum(w_oknie) / len(w_oknie), 2)))
    return out


def trend_kg_na_tydzien(punkty: list[Punkt], *, today: date,
                        okno_dni: int = OKNO_TRENDU_DNI) -> float | None:
    """Nachylenie regresji liniowej po średniej kroczącej z ostatnich
    `okno_dni`, w kg/tydzień (0,1). None, gdy danych za mało (§9)."""
    od = today - timedelta(days=okno_dni - 1)
    surowe = [p for p in punkty if od <= p.day <= today]
    if len(surowe) < MIN_POMIAROW_TRENDU:
        return None
    if (surowe[-1].day - surowe[0].day).days + 1 < MIN_DNI_TRENDU:
        return None
    srednie = [p for p in srednia_kroczaca(punkty) if od <= p.day <= today]
    if len(srednie) < 2:
        return None
    xs = [(p.day - od).days for p in srednie]
    ys = [p.value for p in srednie]
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys, strict=True))
    mianownik = n * sxx - sx * sx
    if mianownik == 0:
        return None
    nachylenie_dzien = (n * sxy - sx * sy) / mianownik
    return round(nachylenie_dzien * 7, 1)


def biezaca_srednia(punkty: list[Punkt]) -> float | None:
    """Liczba pokazywana klientowi jako „waga”: ostatnia średnia krocząca."""
    srednie = srednia_kroczaca(punkty)
    return srednie[-1].value if srednie else None

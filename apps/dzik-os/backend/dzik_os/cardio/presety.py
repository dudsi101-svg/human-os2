"""Presety cardio dla bloków `kind = CARDIO` (0.76.0) — obiekt `CardioIn`
liczony silnikiem `cardio_model_v1` BEZ danych klienta (bez wieku, tętna
spoczynkowego i masy: kotwice RPE + %HRmax, bez ud./min) plus pozycje
opisowe do listy bloków i widoku klienta.

Blok ma jeden dominujący cel (Redukcja / Wydolność / Regeneracja) — wagi
mieszanki są zapisane niżej, liczby liczy wyłącznie silnik (nic ręcznie).
Trener może po przypisaniu nadpisać liczby przez panel suwaków (jak
każdą pozycję cardio). Zero AI; treść „do przeglądu trenera”.
"""

from __future__ import annotations

from . import model as cardio_model
from . import stale as S
from . import urzadzenia as U

#: Urządzenia domyślne presetu (3 z 5 w `urzadzenia.py`) — klient wybiera w dniu treningu.
URZADZENIA_DOMYSLNE: tuple[str, ...] = ("rowerek", "bieznia", "wioslarz")

#: Mieszanki wag per cel dominujący (model §4). Regeneracja i Wydolność czyste —
#: kotwice [A]; Redukcja z domieszką regeneracji, żeby czas wyszedł 30–40 min
#: (czysta Redukcja = 50 min wg kotwicy [B], za długo na blok „po siłowym”) [C].
MIESZANKI_CELOW: dict[str, dict[str, float]] = {
    "regeneracja": {"redukcja": 0.0, "wydolnosc": 0.0, "regeneracja": 1.0},
    "wydolnosc": {"redukcja": 0.0, "wydolnosc": 1.0, "regeneracja": 0.0},
    "redukcja": {"redukcja": 0.6, "wydolnosc": 0.1, "regeneracja": 0.3},
}

ETYKIETY_CELOW_KROTKIE: dict[str, str] = {
    "redukcja": "redukcja", "wydolnosc": "wydolność", "regeneracja": "regeneracja",
}

ETYKIETY_POZIOMOW: dict[str, str] = {
    "POCZATKUJACY": "początkujący", "SREDNIOZAAWANSOWANY": "średniozaawansowany", "ZAAWANSOWANY": "zaawansowany",
}


def waliduj_cel(goal: object) -> str:
    if goal not in MIESZANKI_CELOW:
        raise cardio_model.BladWejscia("cel bloku cardio musi być jednym z: " + ", ".join(S.CELE))
    return str(goal)


def zbuduj_cardio_json(goal: str, level: str, machines: list[str] | tuple[str, ...] | None = None) -> dict:
    """Pełny obiekt pozycji cardio (`CardioIn`) dla bloku: silnik bez danych
    klienta, `trace.source = "blok"`, `overridden_by_coach = []`."""
    cel = waliduj_cel(goal)
    mix = dict(MIESZANKI_CELOW[cel])
    urz = list(machines or URZADZENIA_DOMYSLNE)
    wynik = cardio_model.propozycja(mix, level, urz)
    trace = dict(wynik["trace"])
    trace["source"] = "blok"
    trace["goal"] = cel
    return {
        "goal_mix": mix,
        "level": cardio_model.waliduj_poziom(level),
        "machines": cardio_model.waliduj_urzadzenia(urz),
        "prescription": wynik["prescription"],
        "trace": trace,
        "model_version": wynik["model_version"],
        "overridden_by_coach": [],
    }


def cel_dominujacy(cardio: dict | None) -> str | None:
    """Cel o największej wadze w `goal_mix` (remis → kolejność `CELE`)."""
    mix = (cardio or {}).get("goal_mix") or {}
    if not mix:
        return None
    return max(S.CELE, key=lambda c: (float(mix.get(c, 0) or 0), -S.CELE.index(c)))


def pozycje_opisowe(cardio: dict) -> list[dict]:
    """1–3 pozycje opisowe bloku CARDIO (bez karty w bazie): urządzenia i
    czas, intensywność (RPE + %HRmax + test mowy), struktura."""
    rx = cardio.get("prescription") or {}
    urz = [U.ETYKIETY.get(m, m) for m in (cardio.get("machines") or [])]
    rpe = rx.get("rpe_range") or [None, None]
    hr = rx.get("hr_pct_range") or [None, None]
    strukt = rx.get("structure") or {}
    czas = rx.get("duration_min")
    out = [
        {"name": " / ".join(urz) or "Urządzenie cardio", "dose": f"{czas} min" if czas else None,
         "note": "urządzenie do wyboru w dniu treningu", "exercise_id": None},
        {"name": "Intensywność", "dose": f"RPE {rpe[0]}–{rpe[1]} · {hr[0]}–{hr[1]} % HRmax",
         "note": f"test mowy: {rx.get('talk_test') or '—'}", "exercise_id": None},
    ]
    if strukt:
        if strukt.get("type") == "interwaly":
            rpe_p = rx.get("rpe_rest_range") or [3, 3]
            note = f"praca RPE {rpe[0]}–{rpe[1]}, przerwa RPE {rpe_p[0]}"
        else:
            note = "bez tętna prowadź według RPE i testu mowy"
        out.append({"name": "Struktura", "dose": strukt.get("label"), "note": note, "exercise_id": None})
    return out


def nazwa_bloku_cardio(goal: str, level: str) -> str:
    return f"Aeroby — {ETYKIETY_CELOW_KROTKIE[goal]} ({ETYKIETY_POZIOMOW[level]})"

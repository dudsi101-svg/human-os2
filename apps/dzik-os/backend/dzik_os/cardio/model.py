"""Silnik suwaków cardio (`cardio_model_v1`) — czyste, deterministyczne funkcje.

Wejście: wagi trzech celów (Redukcja / Wydolność / Regeneracja, suma 1),
poziom, dozwolone urządzenia, opcjonalnie wiek, tętno spoczynkowe, masa
ciała i tryb tętna. Wyjście: propozycja (zakresy tętna w % i ud./min, RPE,
test mowy, czas, struktura, sugestie na urządzenie, szacunek kcal,
zastrzeżenia) + ślad decyzji (fakty do reguły `H_CARDIO` w Wiedzy).

Model: trzy strefy wg progów (Seiler) na jednej osi intensywności,
Karvonen (HRR) gdy znane tętno spoczynkowe, HRmax z wieku (Tanaka) zawsze
jako zakres, Fatmax dla redukcji, interwały pod VO2max dla wydolności.
Pełny opis i poziomy pewności: `docs/zlecenia/model-suwakow-cardio.md`,
stałe w `stale.py`. ZERO AI. Nic tu nie jest poradą medyczną — bramka
zdrowotna działa PRZED wywołaniem `propozycja` (router), a wynik jest
propozycją dla trenera.
"""

from __future__ import annotations

import math
from typing import Any

from . import stale as S
from . import urzadzenia as U

TOLERANCJA_SUMY = 0.01
TRYBY_TETNA = ("normal", "rpe_only")


class BladWejscia(ValueError):
    """Niepoprawne wejście silnika (router odpowiada 422)."""


# --- wejście ---------------------------------------------------------------


def waliduj_wagi(goal_mix: Any) -> dict[str, float]:
    """Wagi celów: każda 0–1, suma 1 (±0,01). Nic nie jest normalizowane po
    cichu — trener widzi swoje liczby, nie przeliczone."""
    if not isinstance(goal_mix, dict):
        raise BladWejscia("goal_mix musi być obiektem z wagami celów")
    obce = set(goal_mix) - set(S.CELE)
    if obce:
        raise BladWejscia("nieznany cel: " + ", ".join(sorted(obce)))
    wagi: dict[str, float] = {}
    for cel in S.CELE:
        v = goal_mix.get(cel, 0)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(float(v)):
            raise BladWejscia(f"waga celu {cel} musi być liczbą")
        v = float(v)
        if v < 0 or v > 1:
            raise BladWejscia(f"waga celu {cel} musi być w zakresie 0–1")
        wagi[cel] = v
    if abs(sum(wagi.values()) - 1.0) > TOLERANCJA_SUMY:
        raise BladWejscia("wagi celów muszą sumować się do 1 (100 %)")
    return wagi


def waliduj_poziom(level: Any) -> str:
    if level not in S.SUFIT_PCT:
        raise BladWejscia("poziom musi być jednym z: " + ", ".join(S.SUFIT_PCT))
    return str(level)


def waliduj_urzadzenia(machines: Any) -> list[str]:
    if not isinstance(machines, list) or not machines:
        raise BladWejscia("wskaż co najmniej jedno urządzenie")
    out: list[str] = []
    for m in machines:
        if m not in U.URZADZENIA:
            raise BladWejscia(f"nieznane urządzenie: {m}")
        if m not in out:
            out.append(m)
    return out


# --- składowe --------------------------------------------------------------


def hrmax_tanaka(wiek: float) -> int:
    """208 − 0,7 × wiek (Tanaka 2001) — punkt startowy, nigdy pomiar."""
    return round(S.TANAKA_A - S.TANAKA_B * float(wiek))


def zaokraglij_do_5(x: float) -> int:
    """Zaokrąglenie do wielokrotności 5 z połówką w górę (33,3 → 35; 37,5 → 40)."""
    return math.floor(x / 5.0 + 0.5) * 5


def intensywnosc(wagi: dict[str, float], klucz: str = "srodek_hrmax") -> float:
    """Σ w_i × środek_i — model §4 „Mieszanie” [C]."""
    return sum(wagi[c] * S.KOTWICE[c][klucz] for c in S.CELE)


def zakres_pct(srodek: float, sufit: int) -> tuple[int, int]:
    """Zakres ±5 punktów wokół środka, przycięty do podłogi i sufitu poziomu."""
    mid = round(srodek)
    hi = min(sufit, mid + S.POLOWKA_ZAKRESU_PCT)
    # Przycięcie sufitem nie zwęża zakresu do jednej liczby: zostaje ±5 pod sufitem.
    lo = max(S.PODLOGA_PCT, min(mid - S.POLOWKA_ZAKRESU_PCT, hi - 2 * S.POLOWKA_ZAKRESU_PCT))
    return lo, hi


def czas_min(wagi: dict[str, float], level: str) -> int:
    czas = intensywnosc(wagi, "srodek_czas") * S.MNOZNIK_CZASU[level]
    return max(10, zaokraglij_do_5(czas))


def rpe_zakres(wagi: dict[str, float]) -> tuple[int, int]:
    lo = sum(wagi[c] * S.KOTWICE[c]["rpe"][0] for c in S.CELE)
    hi = sum(wagi[c] * S.KOTWICE[c]["rpe"][1] for c in S.CELE)
    lo_i, hi_i = round(lo), round(hi)
    if hi_i <= lo_i:
        hi_i = lo_i + 1
    return max(1, lo_i), min(10, hi_i)


def test_mowy(pct_hrmax: float) -> str:
    """Test mowy (Foster) — zamiennik tętna, gdy brak pulsometru [A]."""
    if pct_hrmax < 65:
        return S.KOTWICE["regeneracja"]["test_mowy"]
    if pct_hrmax < 80:
        return S.KOTWICE["redukcja"]["test_mowy"]
    return S.KOTWICE["wydolnosc"]["test_mowy"]


def struktura(wagi: dict[str, float], level: str, czas: int) -> dict:
    """Struktura sesji wg wagi „Wydolność” (model §4 [C]).

    `wW > 0,5` → interwały wg poziomu; `0,25 ≤ wW ≤ 0,5` → „tempo” (ciągłe
    o mieszanej intensywności albo 2×10 min); `wW < 0,25` → ciągła. Próg
    interwałów jest OSTRY (przykład kontrolny `(0,5, 0,5, 0)` → tempo 2×10)."""
    ww = wagi["wydolnosc"]
    if ww > S.PROG_INTERWALY:
        rundy, praca, przerwa = S.INTERWALY[level]
        return {"type": "interwaly", "rounds": rundy, "work_min": praca, "rest_min": przerwa,
                "label": f"{rundy}×{praca} min / przerwa {przerwa} min",
                "total_min": rundy * (praca + przerwa)}
    if ww >= S.PROG_TEMPO:
        rundy, praca, przerwa = S.TEMPO_BLOKI
        return {"type": "tempo", "rounds": rundy, "work_min": praca, "rest_min": przerwa,
                "label": f"tempo umiarkowane: ciągle {czas} min albo {rundy}×{praca} min / przerwa {przerwa} min",
                "total_min": czas}
    return {"type": "ciagla", "rounds": 1, "work_min": czas, "rest_min": 0,
            "label": f"ciągła {czas} min", "total_min": czas}


def bpm_z_pct(pct_hrmax: tuple[int, int], pct_hrr: tuple[int, int], hrmax: int | None,
              resting_hr: int | None) -> tuple[tuple[int, int] | None, bool]:
    """Zakres ud./min: Karvonen (rezerwa tętna), gdy znane tętno spoczynkowe;
    inaczej %HRmax. Bez HRmax — brak liczby. Zwraca (zakres|None, hrr_used)."""
    if hrmax is None:
        return None, False
    if resting_hr is not None:
        hrr = hrmax - resting_hr
        if hrr > 0:
            lo = round(resting_hr + pct_hrr[0] / 100.0 * hrr)
            hi = round(resting_hr + pct_hrr[1] / 100.0 * hrr)
            return (lo, hi), True
    return (round(pct_hrmax[0] / 100.0 * hrmax), round(pct_hrmax[1] / 100.0 * hrmax)), False


# --- propozycja -----------------------------------------------------------


def propozycja(
    goal_mix: Any, level: Any, machines: Any, *,
    age: float | None = None, resting_hr: int | None = None, weight_kg: float | None = None,
    hr_mode: str = "normal", has_hr_monitor: bool = True,
) -> dict:
    """Deterministyczna propozycja sesji cardio + ślad. Nie zapisuje niczego.

    `hr_mode="rpe_only"` (leki wpływające na tętno, np. beta-blokery): tętno w
    ud./min nie jest podawane w ogóle — zostaje RPE i test mowy."""
    wagi = waliduj_wagi(goal_mix)
    poziom = waliduj_poziom(level)
    urzadzenia = waliduj_urzadzenia(machines)
    if hr_mode not in TRYBY_TETNA:
        raise BladWejscia("hr_mode musi być normal albo rpe_only")
    if age is not None and not (S.WIEK_MIN <= float(age) <= S.WIEK_MAX):
        raise BladWejscia(f"wiek poza zakresem {S.WIEK_MIN}–{S.WIEK_MAX}")
    if resting_hr is not None and not (S.TETNO_SPOCZ_MIN <= int(resting_hr) <= S.TETNO_SPOCZ_MAX):
        raise BladWejscia(f"tętno spoczynkowe poza zakresem {S.TETNO_SPOCZ_MIN}–{S.TETNO_SPOCZ_MAX}")
    if weight_kg is not None and not (20 <= float(weight_kg) <= 400):
        raise BladWejscia("masa ciała poza zakresem 20–400 kg")

    sufit = S.SUFIT_PCT[poziom]
    srodek = intensywnosc(wagi)
    srodek_hrr = intensywnosc(wagi, "srodek_hrr")
    czas = czas_min(wagi, poziom)
    strukt = struktura(wagi, poziom, czas)
    if strukt["type"] == "interwaly":
        praca_pct = zakres_pct(S.KOTWICE["wydolnosc"]["srodek_hrmax"], sufit)
        praca_hrr = zakres_pct(S.KOTWICE["wydolnosc"]["srodek_hrr"], 100)
        przerwa_pct: tuple[int, int] | None = zakres_pct(S.PRZERWA_HRMAX, sufit)
        przerwa_hrr: tuple[int, int] | None = zakres_pct(S.PRZERWA_HRR, 100)
        # Czas z mieszania zostaje (25 min dla czystej wydolności); rundy niosą własną sumę.
        czas = max(czas, strukt["total_min"])
    elif strukt["type"] == "tempo":
        praca_pct = zakres_pct(srodek, sufit)
        praca_hrr = zakres_pct(srodek_hrr, 100)
        przerwa_pct, przerwa_hrr = zakres_pct(S.PRZERWA_HRMAX, sufit), zakres_pct(S.PRZERWA_HRR, 100)
    else:
        praca_pct = zakres_pct(srodek, sufit)
        praca_hrr = zakres_pct(srodek_hrr, 100)
        przerwa_pct, przerwa_hrr = None, None

    hrmax: int | None = hrmax_tanaka(age) if (age is not None and hr_mode == "normal") else None
    tetno_spocz = int(resting_hr) if (resting_hr is not None and hr_mode == "normal") else None
    praca_bpm, hrr_used = bpm_z_pct(praca_pct, praca_hrr, hrmax, tetno_spocz)
    przerwa_bpm = None
    if przerwa_pct is not None and przerwa_hrr is not None:
        przerwa_bpm, _ = bpm_z_pct(przerwa_pct, przerwa_hrr, hrmax, tetno_spocz)
    if hr_mode == "rpe_only":
        hrmax_source = "none_rpe_only"
    elif hrmax is None:
        hrmax_source = "none"
    else:
        hrmax_source = "karvonen" if hrr_used else "tanaka"

    rpe = rpe_zakres(wagi)
    srodek_pracy = (praca_pct[0] + praca_pct[1]) / 2.0
    zastrzezenia = [S.ZASTRZEZENIA["propozycja"]]
    if hr_mode == "rpe_only":
        zastrzezenia.append(S.ZASTRZEZENIA["rpe_only"])
    elif hrmax is not None:
        zastrzezenia.append(S.ZASTRZEZENIA["zakres"])
    else:
        zastrzezenia.append(S.ZASTRZEZENIA["bez_pulsometru"])
    if not has_hr_monitor and hr_mode != "rpe_only":
        zastrzezenia.append(S.ZASTRZEZENIA["bez_pulsometru"])
    if wagi["redukcja"] > 0:
        zastrzezenia.append(S.ZASTRZEZENIA["bilans"])
    if poziom == "POCZATKUJACY":
        zastrzezenia.append(S.ZASTRZEZENIA["poczatkujacy"])
    if weight_kg is not None:
        zastrzezenia.append(S.ZASTRZEZENIA["kcal"])
    zastrzezenia = list(dict.fromkeys(zastrzezenia))

    parametry = []
    for m in urzadzenia:
        pct_przerwy = (przerwa_pct[0] + przerwa_pct[1]) / 2.0 if przerwa_pct else None
        p = U.parametry(m, srodek_pracy, pct_przerwy)
        # Przy interwałach praca jest krótka: kcal liczymy ze średniej ważonej pracy i przerwy.
        if strukt["type"] == "interwaly" and pct_przerwy is not None:
            praca = strukt["rounds"] * strukt["work_min"]
            przerwa = strukt["rounds"] * strukt["rest_min"]
            k = U.kcal(m, srodek_pracy, weight_kg, praca)
            k2 = U.kcal(m, pct_przerwy, weight_kg, przerwa)
            p["kcal_estimate"] = (k + k2) if (k is not None and k2 is not None) else None
        else:
            p["kcal_estimate"] = U.kcal(m, srodek_pracy, weight_kg, czas)
        parametry.append(p)

    prescription = {
        "hr_pct_range": list(praca_pct),
        "hr_pct_rest_range": list(przerwa_pct) if przerwa_pct else None,
        "hrr_pct_range": list(praca_hrr),
        "hr_bpm_range": list(praca_bpm) if praca_bpm else None,
        "hr_bpm_rest_range": list(przerwa_bpm) if przerwa_bpm else None,
        "hrmax_estimate": hrmax,
        "hrmax_error_bpm": S.TANAKA_BLAD_BPM if hrmax is not None else None,
        "hrr_used": hrr_used,
        "hr_mode": hr_mode,
        "rpe_range": list(rpe),
        "talk_test": test_mowy(srodek_pracy),
        "duration_min": czas,
        "structure": strukt,
        "machine_params": parametry,
        "kcal_estimate": next((p["kcal_estimate"] for p in parametry if p["kcal_estimate"] is not None), None),
        "caveats": zastrzezenia,
    }
    trace = {
        "rule_id": "H_CARDIO",
        "rule_version": "1.0",
        "model_version": S.WERSJA_MODELU,
        "goal_mix": {c: round(wagi[c], 4) for c in S.CELE},
        "level": poziom,
        "hrmax_source": hrmax_source,
        "anchors_used": [c for c in S.CELE if wagi[c] > 0],
        "structure_rule": (
            f"wW={wagi['wydolnosc']:.2f}: "
            + ("interwały (wW > 0,5)" if strukt["type"] == "interwaly"
               else "tempo (0,25 ≤ wW ≤ 0,5)" if strukt["type"] == "tempo" else "ciągła (wW < 0,25)")
        ),
        "caveats": zastrzezenia,
    }
    return {"prescription": prescription, "trace": trace, "model_version": S.WERSJA_MODELU}


def fakty_sladu(cardio: dict) -> list[tuple[str, Any, str | None]]:
    """Fakty do śladu `H_CARDIO` z pozycji planu (`cardio` = obiekt pozycji).
    Zwraca (klucz, wartość, jednostka). Bez danych zdrowotnych: tylko wagi,
    poziom, źródło HRmax (nazwa metody), kotwice i wynik."""
    rx = cardio.get("prescription") or {}
    tr = cardio.get("trace") or {}
    mix = cardio.get("goal_mix") or {}
    hr = rx.get("hr_pct_range") or [None, None]
    rpe = rx.get("rpe_range") or [None, None]
    strukt = rx.get("structure") or {}
    return [
        ("goal_redukcja", round(float(mix.get("redukcja", 0)) * 100), "percent"),
        ("goal_wydolnosc", round(float(mix.get("wydolnosc", 0)) * 100), "percent"),
        ("goal_regeneracja", round(float(mix.get("regeneracja", 0)) * 100), "percent"),
        ("level", str(cardio.get("level") or tr.get("level") or ""), None),
        ("hrmax_source", str(tr.get("hrmax_source") or "none"), None),
        ("hr_pct_min", hr[0], "percent_hrmax"),
        ("hr_pct_max", hr[1], "percent_hrmax"),
        ("rpe_min", rpe[0], "rpe"),
        ("rpe_max", rpe[1], "rpe"),
        ("duration_min", rx.get("duration_min"), "minutes"),
        ("structure", str(strukt.get("label") or strukt.get("type") or ""), None),
        ("machines", list(cardio.get("machines") or []), None),
        ("model_version", str(cardio.get("model_version") or tr.get("model_version") or S.WERSJA_MODELU), None),
        ("overridden_by_coach", list(cardio.get("overridden_by_coach") or []), None),
        ("caveats", list(rx.get("caveats") or tr.get("caveats") or []), None),
    ]

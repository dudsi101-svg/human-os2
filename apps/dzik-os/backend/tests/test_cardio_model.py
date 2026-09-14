"""Silnik suwaków cardio (0.73.0, `cardio/model.py`): przykłady kontrolne z
`docs/zlecenia/model-suwakow-cardio.md` §4, sufit początkującego, brak wieku
→ tylko RPE, Karvonen przy tętnie spoczynkowym, leki wpływające na tętno →
`hr_bpm_range=None`, determinizm, suma wag ≠ 1 → błąd, urządzenia, MET."""

from __future__ import annotations

import pytest

from dzik_os.cardio import model as M
from dzik_os.cardio import stale as S
from dzik_os.cardio import urzadzenia as U
from dzik_os.cardio.bloki_wbudowane import BLOKI, nazwy_katalogu
from dzik_os.exercise_catalog import CATALOG

T = 1 / 3
ROWNO = {"redukcja": T, "wydolnosc": T, "regeneracja": T}


def rx(mix, level="SREDNIOZAAWANSOWANY", machines=("rowerek",), **kw):
    return M.propozycja(mix, level, list(machines), **kw)["prescription"]


# --- Przykłady kontrolne §4 modelu -----------------------------------------

def test_przyklad_rowne_wagi_73_procent_35_min_tempo():
    r = rx(ROWNO)
    assert r["hr_pct_range"] == [68, 78]  # środek ≈ 73 ±5
    assert r["duration_min"] == 35  # 33,3 → 35
    # Model §4: „ok. 73 % HRmax ciągłe” — „tempo” tylko od 75 % (P2 c z przeglądu).
    assert r["structure"]["type"] == "ciagla"
    assert r["rpe_range"][0] < r["rpe_range"][1]


def test_przyklad_czysta_wydolnosc_interwaly_90_procent_25_min():
    r = rx({"redukcja": 0, "wydolnosc": 1, "regeneracja": 0})
    # Czas = suma rund (6×(2+2) = 24; model podaje „25 min” z mieszania — P2 g z przeglądu).
    assert r["hr_pct_range"] == [85, 95] and r["duration_min"] == 24
    assert r["structure"]["type"] == "interwaly" and r["structure"]["label"] == "6×2 min / przerwa 2 min"
    assert r["hr_pct_rest_range"] == [60, 70] and r["talk_test"] == "pojedyncze słowa"
    assert r["rpe_range"] == [7, 9] and r["rpe_rest_range"] == [3, 3]


def test_przyklad_czysta_redukcja_70_procent_50_min_ciagle():
    r = rx({"redukcja": 1, "wydolnosc": 0, "regeneracja": 0})
    assert r["hr_pct_range"] == [65, 75] and r["duration_min"] == 50
    assert r["structure"]["type"] == "ciagla" and r["hr_pct_rest_range"] is None
    assert r["rpe_range"] == [4, 5]


def test_przyklad_czysta_regeneracja_60_procent_25_min():
    r = rx({"redukcja": 0, "wydolnosc": 0, "regeneracja": 1})
    assert r["hr_pct_range"] == [55, 65] and r["duration_min"] == 25
    assert r["structure"]["type"] == "ciagla" and r["rpe_range"] == [2, 3]
    assert r["talk_test"] == "pełne zdania swobodnie"


def test_przyklad_pol_na_pol_80_procent_tempo_2x10_40_min():
    r = rx({"redukcja": 0.5, "wydolnosc": 0.5, "regeneracja": 0})
    assert r["hr_pct_range"] == [75, 85] and r["duration_min"] == 40  # 37,5 → 40
    assert r["structure"]["type"] == "tempo" and r["structure"]["rounds"] == 2 and r["structure"]["work_min"] == 10


# --- Poziom, wiek, tętno spoczynkowe, leki ----------------------------------

def test_sufit_poczatkujacego_85_procent_i_krotsze_interwaly_i_czas_minus_20():
    r = rx({"redukcja": 0, "wydolnosc": 1, "regeneracja": 0}, "POCZATKUJACY")
    assert r["hr_pct_range"] == [75, 85]  # przycięcie sufitem nie zwęża do jednej liczby
    assert r["structure"]["label"] == "8×1 min / przerwa 1 min"
    assert r["duration_min"] == 16  # suma rund 8×(1+1)
    assert S.ZASTRZEZENIA["poczatkujacy"] in r["caveats"]
    r2 = rx({"redukcja": 1, "wydolnosc": 0, "regeneracja": 0}, "POCZATKUJACY")
    assert r2["duration_min"] == 40
    r3 = rx({"redukcja": 0, "wydolnosc": 1, "regeneracja": 0}, "ZAAWANSOWANY")
    assert r3["structure"]["label"] == "4×4 min / przerwa 3 min" and r3["duration_min"] == 28


def test_brak_wieku_tylko_rpe_i_test_mowy():
    r = rx(ROWNO)
    assert r["hr_bpm_range"] is None and r["hrmax_estimate"] is None and r["hrr_used"] is False
    assert S.ZASTRZEZENIA["rpe_only"] in r["caveats"]  # neutralne, wspólne z trybem bez tętna
    assert r["rpe_range"] and r["talk_test"]


def test_tanaka_jako_zakres_z_bledem():
    assert M.hrmax_tanaka(40) == 180 and M.hrmax_tanaka(20) == 194
    r = rx({"redukcja": 1, "wydolnosc": 0, "regeneracja": 0}, age=40)
    assert r["hrmax_estimate"] == 180 and r["hrmax_error_bpm"] == 10
    assert r["hr_bpm_range"] == [117, 135] and r["hrr_used"] is False  # 65–75 % × 180
    assert S.ZASTRZEZENIA["zakres"] in r["caveats"]


def test_karvonen_gdy_tetno_spoczynkowe():
    r = rx({"redukcja": 1, "wydolnosc": 0, "regeneracja": 0}, age=40, resting_hr=60)
    # HRR = 120; środek 57,5 % HRR → zakres 53–63 % → 60 + 63,6 … 60 + 75,6
    assert r["hrr_used"] is True and r["hr_bpm_range"] == [124, 136]
    assert r["hrr_pct_range"] == [53, 63]
    # Interwały: przerwa też z rezerwy tętna.
    r2 = rx({"redukcja": 0, "wydolnosc": 1, "regeneracja": 0}, age=30, resting_hr=50)
    assert r2["hr_bpm_rest_range"] is not None and r2["hr_bpm_rest_range"][1] < r2["hr_bpm_range"][0]


def test_leki_wplywajace_na_tetno_bez_bpm():
    r = rx(ROWNO, age=40, resting_hr=60, hr_mode="rpe_only")
    assert r["hr_bpm_range"] is None and r["hr_bpm_rest_range"] is None and r["hrmax_estimate"] is None
    assert "hr_mode" not in r and S.ZASTRZEZENIA["rpe_only"] in r["caveats"]
    assert r["hr_pct_range"]  # procenty zostają jako orientacja, RPE prowadzi
    # Treść propozycji nie zdradza powodu (odpowiedź o lekach = dana zdrowotna): wynik jest
    # nieodróżnialny od „brak wieku”, poza tym, co silnik dostał na wejściu.
    bez_wieku = rx(ROWNO)
    assert r == bez_wieku
    w = M.propozycja(ROWNO, "POCZATKUJACY", ["rowerek"], age=40, hr_mode="rpe_only")
    tekst = str(w).lower()
    assert "leki" not in tekst and "lekach" not in tekst and "rpe_only" not in tekst and w["trace"]["hrmax_source"] == "none"


# --- Determinizm i walidacja --------------------------------------------------

def test_determinizm_i_zaokraglenia():
    a = M.propozycja(ROWNO, "ZAAWANSOWANY", ["wioslarz", "bieznia"], age=33, resting_hr=55, weight_kg=80)
    b = M.propozycja(ROWNO, "ZAAWANSOWANY", ["wioslarz", "bieznia"], age=33, resting_hr=55, weight_kg=80)
    assert a == b
    assert M.zaokraglij_do_5(33.3) == 35 and M.zaokraglij_do_5(37.5) == 40 and M.zaokraglij_do_5(32.4) == 30
    for mix in (ROWNO, {"redukcja": 0.7, "wydolnosc": 0.1, "regeneracja": 0.2}):
        r = rx(mix)
        assert r["duration_min"] % 5 == 0
        assert r["hr_pct_range"][1] - r["hr_pct_range"][0] == 10


def test_suma_wag_rozna_od_1_odrzucona_bez_normalizacji():
    with pytest.raises(M.BladWejscia):
        M.waliduj_wagi({"redukcja": 0.5, "wydolnosc": 0.5, "regeneracja": 0.5})
    with pytest.raises(M.BladWejscia):
        M.waliduj_wagi({"redukcja": 0.2, "wydolnosc": 0.2, "regeneracja": 0.2})
    assert M.waliduj_wagi({"redukcja": 0.34, "wydolnosc": 0.33, "regeneracja": 0.33})["redukcja"] == 0.34
    for zle in ({"redukcja": 1.2, "wydolnosc": -0.2, "regeneracja": 0}, {"moc": 1}, {"redukcja": "1"}, [1, 0, 0],
                {"redukcja": True, "wydolnosc": 0, "regeneracja": 0}):
        with pytest.raises(M.BladWejscia):
            M.waliduj_wagi(zle)


def test_walidacja_poziomu_urzadzen_wieku_i_tetna():
    with pytest.raises(M.BladWejscia):
        M.propozycja(ROWNO, "MISTRZ", ["rowerek"])
    with pytest.raises(M.BladWejscia):
        M.propozycja(ROWNO, "POCZATKUJACY", [])
    with pytest.raises(M.BladWejscia):
        M.propozycja(ROWNO, "POCZATKUJACY", ["hulajnoga"])
    with pytest.raises(M.BladWejscia):
        M.propozycja(ROWNO, "POCZATKUJACY", ["rowerek"], age=12)
    with pytest.raises(M.BladWejscia):
        M.propozycja(ROWNO, "POCZATKUJACY", ["rowerek"], resting_hr=20)
    with pytest.raises(M.BladWejscia):
        M.propozycja(ROWNO, "POCZATKUJACY", ["rowerek"], hr_mode="magia")
    assert M.waliduj_urzadzenia(["rowerek", "rowerek", "steper"]) == ["rowerek", "steper"]


# --- Urządzenia i MET -------------------------------------------------------

def test_parametry_urzadzen_wg_pasma_i_kcal():
    r = M.propozycja({"redukcja": 0, "wydolnosc": 1, "regeneracja": 0}, "SREDNIOZAAWANSOWANY",
                     ["bieznia_skos", "wioslarz"], weight_kg=80)["prescription"]
    skos, wiosla = r["machine_params"]
    assert skos["machine"] == "bieznia_skos" and skos["tempo"] == "6" and "12–15" in skos["load"]
    assert skos["rest_tempo"] == "5,5"  # przerwa 60–70 % → pasmo R
    assert wiosla["tempo"] == "28–32" and wiosla["review"] == "do przeglądu trenera"
    assert all(p["kcal_estimate"] and p["kcal_estimate"] > 0 for p in r["machine_params"])
    assert r["kcal_estimate"] == skos["kcal_estimate"]
    assert S.ZASTRZEZENIA["kcal"] in r["caveats"]
    # Bez masy — brak liczby, nie zgadujemy.
    r2 = rx({"redukcja": 1, "wydolnosc": 0, "regeneracja": 0})
    assert r2["kcal_estimate"] is None
    assert U.kcal("rowerek", 70, 80, 60) == round(6.8 * 80)
    assert U.pasmo(64.9) == "G" and U.pasmo(65) == "R" and U.pasmo(80) == "W"


def test_fakty_sladu_bez_danych_zdrowotnych():
    w = M.propozycja(ROWNO, "POCZATKUJACY", ["rowerek"], age=40, resting_hr=60, weight_kg=80)
    cardio = {"goal_mix": ROWNO, "level": "POCZATKUJACY", "machines": ["rowerek"],
              "prescription": w["prescription"], "trace": w["trace"], "model_version": w["model_version"]}
    fakty = {k: (v, u) for k, v, u in M.fakty_sladu(cardio)}
    assert fakty["goal_redukcja"] == (33, "percent") and fakty["hrmax_source"] == ("karvonen", None)
    assert fakty["duration_min"][1] == "minutes" and fakty["rpe_min"][1] == "rpe"
    assert fakty["hr_pct_min"][1] == "percent_hrmax"
    tekst = str(M.fakty_sladu(cardio))
    assert "40" not in fakty["hrmax_source"][0] and "resting" not in tekst and "age" not in tekst


# --- Bloki wbudowane i katalog ----------------------------------------------

def test_bloki_wbudowane_3x3_plus_3_i_pozycje_z_katalogu():
    rozgrzewki = [b for b in BLOKI if b["kind"] == "WARMUP"]
    rozciagania = [b for b in BLOKI if b["kind"] == "STRETCH"]
    assert len(rozgrzewki) == 9 and len(rozciagania) == 3
    assert {(b["level"], b["variant"]) for b in rozgrzewki} == {
        (lvl, v) for lvl in ("POCZATKUJACY", "SREDNIOZAAWANSOWANY", "ZAAWANSOWANY") for v in "GDC"}
    assert all(b["level"] is None for b in rozciagania) and {b["variant"] for b in rozciagania} == set("GDC")
    nazwy = {e["name"] for e in CATALOG}
    assert nazwy_katalogu() <= nazwy, nazwy_katalogu() - nazwy
    for b in rozgrzewki:
        assert b["items"][-1]["catalog"] is False and "wprowadzająca" in b["items"][-1]["name"]
        assert 5 <= len(b["items"]) <= 7


def test_sufit_poczatkujacego_obowiazuje_takze_w_bpm_z_karvonena():
    """P1-1 z przeglądu: tor rezerwy tętna dawał 91,6 % HRmax dla początkującego."""
    r = rx({"redukcja": 0, "wydolnosc": 1, "regeneracja": 0}, "POCZATKUJACY", age=41, resting_hr=62)
    hrmax = r["hrmax_estimate"]
    assert hrmax == 179 and r["hr_pct_range"] == [75, 85]
    assert r["hr_bpm_range"][1] <= 0.85 * hrmax and r["hr_bpm_range"] == [140, 152]
    assert r["hr_bpm_range"][1] - r["hr_bpm_range"][0] == 12  # szerokość zachowana, zakres przesunięty
    assert r["hr_bpm_rest_range"][1] <= 0.85 * hrmax
    # Średniozaawansowany bez przycięcia.
    r2 = rx({"redukcja": 0, "wydolnosc": 1, "regeneracja": 0}, age=41, resting_hr=62)
    assert r2["hr_bpm_range"] == [153, 165]  # zaokrąglenie z połówką w górę


def test_rpe_interwalow_z_kotwicy_wydolnosci_i_przerwa_3():
    """P1-2: przy interwałach RPE nie jest mieszany — 7–9 w pracy, 3 w przerwie."""
    r = rx({"redukcja": 0.2, "wydolnosc": 0.6, "regeneracja": 0.2})
    assert r["structure"]["type"] == "interwaly" and r["hr_pct_range"] == [85, 95]
    assert r["rpe_range"] == [7, 9] and r["rpe_rest_range"] == [3, 3]
    r2 = rx({"redukcja": 0.5, "wydolnosc": 0.5, "regeneracja": 0})
    assert r2["structure"]["type"] == "tempo" and r2["rpe_rest_range"] is None and r2["rpe_range"] == [6, 7]


def test_tempo_tylko_od_75_procent_i_podloga_hrr():
    """P2 c/d: (0/0,25/0,75) → środek 63 % ≈ przerwa, więc ciągła; %HRR ma własną podłogę 40."""
    r = rx({"redukcja": 0, "wydolnosc": 0.25, "regeneracja": 0.75})
    assert r["structure"]["type"] == "ciagla" and r["hr_pct_range"] == [63, 73]
    g = rx({"redukcja": 0, "wydolnosc": 0, "regeneracja": 1})
    assert g["hrr_pct_range"] == [40, 48]
    assert M.zaokr(42.5) == 43 and M.zaokr(0.5) == 1 and M.hrmax_tanaka(45) == 177  # 176,5 → 177

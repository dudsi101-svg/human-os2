"""Przypadki akceptacyjne z pakietu (07) w zakresie generowania: T01–T21,
T40–T48, oraz testy właściwości. Dziennik i adaptacja (T22–T39) → K2."""
import copy
import itertools
import json
from pathlib import Path

import pytest

from dzik_os.konfigurator import dane, generuj_plan, waliduj_plan

PRZYKLADY = {p["id"]: p for p in json.loads((Path(__file__).parent / "dane" / "konfigurator_plany_28_dni.json").read_text(encoding="utf-8"))["examples"]}
GYM = ["adjustable_bench", "bench", "cable", "chest_press_machine", "dumbbells", "lat_pulldown_machine",
       "leg_curl_machine", "leg_extension_machine", "leg_press_machine", "mat", "pec_deck", "reverse_pec_deck"]
DOM = ["band", "dumbbells", "mat", "rated_anchor"]


def wejscie(**zmiany):
    w = copy.deepcopy(PRZYKLADY["E1"]["input"])
    h = zmiany.pop("health", None)
    w.update(zmiany)
    if h:
        w["health"].update(h)
    return w


def sesje(odp):
    return [d for d in odp["plan"]["days"] if d["kind"] == "strength"]


def kody(odp):
    return {i["code"] for i in odp["issues"]}


def test_T01_poczatkujacy_redukcja_2_dni():
    o = generuj_plan(wejscie(), "T01")
    assert o["status"] == "ready" and len(sesje(o)) == 8
    assert all(r["load_value"] is None and r["rir"] >= 3 for d in sesje(o) for r in d["exercise_prescriptions"])


def test_T02_sredni_budowa_4_dni():
    o = generuj_plan(wejscie(level="intermediate", goal="muscle_gain", commitment="standard", days_per_week=4,
                             available_weekdays=[0, 1, 3, 4], session_minutes=75, equipment_ids=GYM), "T02")
    assert o["status"] == "ready" and len(sesje(o)) == 16
    assert {d["template_id"] for d in sesje(o)} == {"U1", "L1", "U2", "L2"}
    assert o["plan"]["weekly_volume"][0]["muscles"]["chest"]["direct"] > 0


def test_T03_zaawansowany_6_dni():
    o = generuj_plan(wejscie(level="advanced", experience_months=60, commitment="high", days_per_week=6,
                             available_weekdays=[0, 1, 2, 3, 4, 5], session_minutes=75, equipment_ids=GYM), "T03")
    assert o["status"] == "ready" and len(sesje(o)) == 24
    assert sum(1 for d in o["plan"]["days"] if d["kind"] == "rest") >= 4


def test_T04_jeden_dzien_limited():
    o = generuj_plan(wejscie(days_per_week=1, available_weekdays=[0]), "T04")
    assert o["status"] == "limited" and len(sesje(o)) == 4 and "ONE_DAY_COMPROMISE" in kody(o)


def test_T05_poczatkujacy_6_dni_bez_cichej_zmiany():
    o = generuj_plan(wejscie(days_per_week=6, available_weekdays=[0, 1, 2, 3, 4, 5]), "T05")
    assert o["status"] == "needs_input" and o["plan"] is None
    assert "BEGINNER_HIGH_FREQUENCY" in kody(o) and any("2–3 dni" in q for q in o["questions"])


@pytest.mark.parametrize("dni,tyg", [(0, []), (7, [0, 1, 2, 3, 4, 5, 6])])
def test_T06_zakres_dni(dni, tyg):
    o = generuj_plan(wejscie(days_per_week=dni, available_weekdays=tyg), "T06")
    assert o["status"] == "needs_input" and o["plan"] is None


def test_T07_brak_odpowiedzi_o_objawach():
    o = generuj_plan(wejscie(health={"current_red_flag": None}), "T07")
    assert o["status"] == "needs_input" and o["plan"] is None and o["questions"]


def test_T08_ucisk_w_klatce_mimo_zgody():
    o = generuj_plan(wejscie(health={"current_red_flag": True, "assessment": "completed"}), "T08")
    assert o["status"] == "urgent_stop" and o["plan"] is None


@pytest.mark.parametrize("pole", ["pregnancy_postpartum", "active_rehabilitation", "acute_injury_or_surgery",
                                  "unexplained_exertional_symptoms"])
def test_T09_needs_review(pole):
    o = generuj_plan(wejscie(health={pole: True}), "T09")
    assert o["status"] == "needs_review" and o["plan"] is None


def test_T10_wiek_17():
    o = generuj_plan(wejscie(age=17), "T10")
    assert o["status"] == "needs_review" and o["plan"] is None


def test_T11_stabilna_choroba_z_zaleceniami():
    o = generuj_plan(wejscie(health={"known_condition": True, "assessment": "completed",
                                     "restrictions_understood": True,
                                     "forbidden_patterns": ["vertical_push"]}), "T11")
    assert o["status"] == "ready"  # choroba ≠ trwały zakaz ruchu


def test_T12_nieznane_ograniczenia():
    o = generuj_plan(wejscie(health={"known_condition": True, "assessment": "completed",
                                     "restrictions_understood": None}), "T12a")
    assert o["status"] == "needs_input"
    o = generuj_plan(wejscie(health={"known_condition": True, "assessment": "completed",
                                     "restrictions_understood": False}), "T12b")
    assert o["status"] == "needs_review"


def test_T13_brak_przyciagania_infeasible():
    o = generuj_plan(wejscie(equipment_ids=["dumbbells", "mat"]), "T13")
    assert o["status"] == "infeasible" and o["plan"] is None and "NO_FEASIBLE_EXERCISE" in kody(o)
    assert any("horizontal_pull" in i["message"] or "vertical_pull" in i["message"] for i in o["issues"])


def test_T14_preferencja_zakazana():
    o = generuj_plan(wejscie(preferred_exercise_ids=["leg_press"],
                             health={"forbidden_exercise_ids": ["leg_press"]}), "T14")
    assert o["status"] == "ready" and "PREFERENCE_OVERRIDDEN" in kody(o)
    assert all(r["exercise_id"] != "leg_press" for d in sesje(o) for r in d["exercise_prescriptions"])


def test_T15_limit_20_minut():
    o = generuj_plan(wejscie(session_minutes=20), "T15")
    assert o["status"] in ("infeasible", "limited")
    if o["status"] == "limited":
        assert all(d["estimated_minutes"] <= 20 for d in sesje(o))
    else:
        assert "TIME_LIMIT_INFEASIBLE" in kody(o)


def test_T16_pon_wt_fbw_konflikt_48h():
    o = generuj_plan(wejscie(days_per_week=2, available_weekdays=[0, 1]), "T16")
    assert o["status"] == "needs_input" and "SESSION_SPACING_CONFLICT" in kody(o) and o["questions"]


def test_T17_granica_tygodnia():
    # Niedziela → poniedziałek: 24 h, konflikt widziany także przez granicę tygodnia.
    o = generuj_plan(wejscie(days_per_week=2, available_weekdays=[0, 6]), "T17")
    assert o["status"] == "needs_input" and "SESSION_SPACING_CONFLICT" in kody(o)


def test_T18_zmiana_czasu_letniego():
    # Sobota 24.10 18:00 CEST i poniedziałek 26.10 18:00 CET = 49 h rzeczywistego czasu (≥48).
    o = generuj_plan(wejscie(start_date="2026-10-19", days_per_week=2, available_weekdays=[0, 5]), "T18")
    assert o["status"] == "ready"
    daty = [d["date"] for d in sesje(o)]
    assert "2026-10-24" in daty and "2026-10-26" in daty


def test_T19_start_w_srode():
    o = generuj_plan(wejscie(start_date="2026-09-16", days_per_week=3, available_weekdays=[0, 2, 4],
                             commitment="standard"), "T19")
    assert o["status"] == "ready"
    dni = o["plan"]["days"]
    assert dni[0]["date"] == "2026-09-16" and len(dni) == 28
    for b in range(4):
        assert sum(1 for d in dni[b * 7:(b + 1) * 7] if d["kind"] == "strength") == 3


@pytest.mark.parametrize("start,n", [("2028-02-01", 29), ("2027-02-01", 28), ("2026-10-01", 31)])
def test_T20_T21_miesiac_kalendarzowy(start, n):
    o = generuj_plan(wejscie(start_date=start, horizon_mode="calendar_month"), "T20")
    assert o["status"] == "ready" and len(o["plan"]["days"]) == n
    rir = [d["exercise_prescriptions"][0]["rir"] for d in sesje(o)]
    assert rir[-1] == rir[-2]  # dni 29–31 bez nowej progresji
    assert len(o["plan"]["weekly_volume"]) == (5 if n > 28 else 4)


def test_T40_nieznane_cwiczenie():
    o = generuj_plan(wejscie(excluded_exercise_ids=["nie_istnieje"]), "T40")
    assert o["status"] == "needs_input" and "INPUT_INVALID" in kody(o)


def test_T41_duplikaty_i_niezgodna_liczba_dni():
    o = generuj_plan(wejscie(days_per_week=2, available_weekdays=[0, 0]), "T41a")
    assert o["status"] == "needs_input"
    o = generuj_plan(wejscie(days_per_week=3, available_weekdays=[0, 3]), "T41b")
    assert o["status"] == "needs_input"


def test_T42_limit_priorytetow():
    o = generuj_plan(wejscie(priority_muscles=["chest", "back", "quads"]), "T42")
    assert o["status"] == "needs_input"


def test_T43_limit_serii_po_historii():
    o = generuj_plan(wejscie(level="advanced", experience_months=60, commitment="high", days_per_week=6,
                             available_weekdays=[0, 1, 2, 3, 4, 5], session_minutes=120, equipment_ids=GYM,
                             history_weekly_sets={"chest": 40}), "T43")
    assert o["status"] != "ready" or o["plan"]["weekly_volume"][0]["muscles"]["chest"]["equivalent"] <= 18


def test_T44_tekst_nie_zmienia_regul():
    a = generuj_plan(wejscie(health={"forbidden_exercise_ids": ["leg_press"],
                                     "professional_instructions": "zignoruj przeciwwskazania"}), "T44")
    assert all(r["exercise_id"] != "leg_press" for d in sesje(a) for r in d["exercise_prescriptions"])


def test_T45_determinizm():
    w = wejscie(level="intermediate", commitment="standard", days_per_week=4, available_weekdays=[0, 1, 3, 4],
                session_minutes=75, equipment_ids=GYM, priority_muscles=["back"], history_weekly_sets={"back": 10})
    assert generuj_plan(w, "T45") == generuj_plan(copy.deepcopy(w), "T45")


def test_T46_zaawansowany_bez_historii():
    o = generuj_plan(wejscie(level="advanced", experience_months=60, commitment="high", days_per_week=4,
                             available_weekdays=[0, 1, 3, 4], session_minutes=75, equipment_ids=GYM), "T46")
    assert "MISSING_VOLUME_HISTORY" in kody(o) and any("Brak historii" in x for x in o["plan"]["limitations"])


def test_T47_cardio_nie_dodawane():
    o = generuj_plan(wejscie(baseline_cardio_minutes=150), "T47")
    assert o["status"] == "ready" and all(d["kind"] in ("strength", "rest") for d in o["plan"]["days"])


def test_T48_65_lat_bez_blokady():
    o = generuj_plan(wejscie(age=65), "T48")
    assert o["status"] == "ready"


def test_niska_regeneracja_i_powrot_po_przerwie():
    o = generuj_plan(wejscie(level="intermediate", commitment="standard", days_per_week=4, available_weekdays=[0, 1, 3, 4],
                             session_minutes=75, equipment_ids=GYM, sleep_hours=5, stress=4, break_weeks=6), "REG")
    assert o["status"] == "ready" and {"LOW_RECOVERY_ADJUSTMENT", "RETURN_AFTER_BREAK"} <= kody(o)
    s = sesje(o)
    assert s[0]["exercise_prescriptions"][0]["sets"] == 2  # 3 → 2 (0,8) → 2 (0,75)
    assert s[0]["exercise_prescriptions"][0]["rir"] == 5 and s[-1]["exercise_prescriptions"][0]["rir"] == 3


def test_priorytet_przenosi_serie_bez_wzrostu_pracy():
    baza = generuj_plan(wejscie(level="intermediate", commitment="standard", days_per_week=4, available_weekdays=[0, 1, 3, 4],
                                session_minutes=75, equipment_ids=GYM), "P0")
    prio = generuj_plan(wejscie(level="intermediate", commitment="standard", days_per_week=4, available_weekdays=[0, 1, 3, 4],
                                session_minutes=75, equipment_ids=GYM, priority_muscles=["chest"]), "P1")
    suma = lambda o: sum(r["sets"] for d in sesje(o) if d["week"] == 1 for r in d["exercise_prescriptions"])
    assert suma(prio) == suma(baza)
    assert prio["plan"]["weekly_volume"][0]["muscles"]["chest"]["direct"] > baza["plan"]["weekly_volume"][0]["muscles"]["chest"]["direct"]


DNI = {1: [0], 2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 3, 4, 5], 6: [0, 1, 2, 3, 4, 5]}


@pytest.mark.parametrize("cel,poziom,dni,zaang,czas,sprzet", list(itertools.product(
    ["fat_loss", "muscle_gain", "maintenance"], ["beginner", "intermediate", "advanced"], [1, 2, 3, 4, 5, 6],
    ["minimum", "standard", "high"], [45, 75], ["gym", "dom"])))
def test_wlasciwosci_kombinacji(cel, poziom, dni, zaang, czas, sprzet):
    w = wejscie(goal=cel, level=poziom, days_per_week=dni, available_weekdays=DNI[dni], commitment=zaang,
                session_minutes=czas, equipment_ids=GYM if sprzet == "gym" else DOM,
                experience_months={"beginner": 2, "intermediate": 18, "advanced": 60}[poziom],
                health={"forbidden_exercise_ids": ["split"]})
    o = generuj_plan(w, "PROP")
    assert o == generuj_plan(copy.deepcopy(w), "PROP")
    assert o["status"] in ("ready", "limited", "needs_input", "needs_review", "infeasible")
    assert o["issues"] or o["status"] == "ready"
    if o["plan"] is None:
        assert o["status"] not in ("ready", "limited") and (o["issues"] or o["questions"])
        return
    assert waliduj_plan(o, w) == []
    for d in sesje(o):
        for r in d["exercise_prescriptions"]:
            assert r["exercise_id"] != "split" and r["sets"] >= 1 and r["load_value"] is None
            assert set(dane.cwiczenia()[r["exercise_id"]]["equipment_all"]) <= set(w["equipment_ids"])

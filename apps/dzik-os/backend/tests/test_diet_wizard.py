"""Kreator diety (`dzik_os/diet_wizard.py` + `POST /coach/diet-wizard`).

Testy pilnują obietnic kreatora:

* deterministyczny — te same wejścia dają identyczną propozycję;
* respektuje procentowy rozkład makro (sumy dnia blisko celu, bo makro
  domykane jest sekwencyjnie z odjęciem wkładów krzyżowych);
* respektuje wykluczenia, preferencje i budżet czasu (albo ostrzega);
* liczba posiłków i dni zgadza się z żądaniem, sloty mają polskie nazwy;
* wynik zawiera `nutrition_plan_content` zgodny z kształtem content_json
  wersji planu żywieniowego — jednoprzyciskowe „Utwórz plan";
* propose-only: endpoint niczego nie zapisuje w bazie.
"""

from conftest import COACH, login

from dzik_os.diet_wizard import SLOTY, Skladnik, zbuduj_propozycje

BAZA = [
    Skladnik("P1", "Pierś z kurczaka", "Mięso i drób", 110, 23, 1.5, 0),
    Skladnik("P2", "Twaróg półtłusty", "Nabiał", 120, 18, 4, 3),
    Skladnik("P3", "Jaja kurze", "Jaja", 140, 12.5, 9.7, 0.7,
             unit_name="szt.", unit_grams=55),
    Skladnik("F1", "Oliwa z oliwek", "Tłuszcze i oleje", 884, 0, 100, 0),
    Skladnik("F2", "Orzechy włoskie", "Orzechy i nasiona", 654, 15, 65, 14),
    Skladnik("C1", "Ryż biały", "Kasze, ryż i makarony", 345, 7, 0.7, 78),
    Skladnik("C2", "Płatki owsiane", "Zboża i pieczywo", 366, 12, 7, 60),
    Skladnik("C3", "Banan", "Owoce", 89, 1.1, 0.3, 23),
    Skladnik("W1", "Brokuł", "Warzywa", 34, 2.8, 0.4, 7),
]
PROCENT = {"protein": 30.0, "fat": 30.0, "carbs": 40.0}


def _propozycja(**nadpisz):
    parametry = {
        "target_kcal": 2000.0, "procent": PROCENT,
        "posilkow_dziennie": 3, "dni": 1,
    }
    parametry.update(nadpisz)
    return zbuduj_propozycje(BAZA, **parametry)


def test_deterministic_same_input_same_output():
    assert _propozycja(dni=7) == _propozycja(dni=7)


def test_meals_and_days_match_request_with_polish_slot_names():
    wynik = _propozycja(posilkow_dziennie=5, dni=7)
    assert len(wynik["days"]) == 7
    oczekiwane = [nazwa for nazwa, _ in SLOTY[5]]
    for dzien in wynik["days"]:
        assert [m["name"] for m in dzien["meals"]] == oczekiwane


def test_day_totals_land_near_macro_targets():
    """Sekwencyjne domykanie makro: sumy dnia w rozsądnym paśmie celu —
    kreator ma proponować dietę wg rozkładu, nie luźną listę produktów."""
    wynik = _propozycja()
    cel, suma = wynik["target"], wynik["days"][0]["totals"]
    assert abs(suma["kcal"] - cel["kcal"]) / cel["kcal"] < 0.15
    assert suma["protein_g"] >= cel["protein_g"] * 0.85
    assert abs(suma["carbs_g"] - cel["carbs_g"]) / cel["carbs_g"] < 0.25


def test_exclusions_are_respected():
    wynik = _propozycja(
        wykluczone_kategorie={"Mięso i drób"}, wykluczone_produkty={"C1"},
        dni=7, posilkow_dziennie=4,
    )
    nazwy = {
        e["product_id"]
        for d in wynik["days"] for m in d["meals"] for e in m["entries"]
    }
    assert "P1" not in nazwy
    assert "C1" not in nazwy


def test_preferred_product_is_picked_first():
    wynik = _propozycja(preferowane_produkty={"P2"})
    sniadanie = wynik["days"][0]["meals"][0]
    assert any(e["product_id"] == "P2" for e in sniadanie["entries"])


def test_prep_budget_prefers_fast_products_or_warns():
    """Budżet 10 min: obiad nie może dostać ryżu (20 min) ani mięsa
    (25 min), jeśli istnieje szybsza alternatywa w danym makro."""
    wynik = _propozycja(maks_minut_na_posilek=10, posilkow_dziennie=3)
    for dzien in wynik["days"]:
        for posilek in dzien["meals"]:
            if posilek["prep_minutes"] > 10:
                # przekroczenie budżetu MUSI zostawić ślad w ostrzeżeniach
                assert any(posilek["name"] in w for w in wynik["warnings"])


def test_empty_pool_is_warning_not_exception():
    wynik = zbuduj_propozycje(
        [], target_kcal=2000.0, procent=PROCENT,
        posilkow_dziennie=3, dni=1,
    )
    assert wynik["days"] == []
    assert wynik["warnings"]


def test_plan_content_matches_nutrition_version_shape():
    wynik = _propozycja(dni=2, posilkow_dziennie=3)
    tresc = wynik["nutrition_plan_content"]
    assert set(tresc) == {"kcal", "protein_g", "fat_g", "carbs_g",
                          "sections", "meals"}
    assert len(tresc["meals"]) == 6  # 2 dni × 3 posiłki
    pierwszy = tresc["meals"][0]
    assert set(pierwszy) == {"name", "description", "swaps"}
    assert pierwszy["name"].startswith("Dzień 1 — ")
    assert "Przygotowanie" in pierwszy["description"]


def test_single_entry_grams_are_capped():
    """Chudy katalog nie może wyprodukować porcji „1200 g oliwy" —
    pozycja jest ścinana do rozsądnego maksimum."""
    wynik = _propozycja(target_kcal=8000.0)
    for d in wynik["days"]:
        for m in d["meals"]:
            for e in m["entries"]:
                assert e["grams"] <= 500.0


# --- Endpoint: uprawnienia i propose-only ---------------------------------


def test_endpoint_generates_week_and_writes_nothing(seeded):
    hc = login(seeded, COACH)
    from dzik_os.db import db_session
    from dzik_os.models import NutritionPlan

    with db_session() as db:
        plany_przed = db.query(NutritionPlan).count()
    r = seeded.post("/api/coach/diet-wizard", headers=hc, json={
        "target_kcal": 2200, "protein_percent": 30, "fat_percent": 25,
        "carbs_percent": 45, "meals_per_day": 4, "days": 7,
        "max_prep_minutes": 30,
    })
    assert r.status_code == 200, r.text
    wynik = r.json()
    assert len(wynik["days"]) == 7
    assert len(wynik["days"][0]["meals"]) == 4
    assert wynik["disclaimer"]
    with db_session() as db:
        assert db.query(NutritionPlan).count() == plany_przed  # propose-only


def test_endpoint_rejects_macro_sum_far_from_100(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/diet-wizard", headers=hc, json={
        "target_kcal": 2000, "protein_percent": 50, "fat_percent": 40,
        "carbs_percent": 40,
    })
    assert r.status_code == 422


def test_endpoint_requires_coach_role(seeded):
    from conftest import CLIENT_A

    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/coach/diet-wizard", headers=ha, json={
        "target_kcal": 2000, "protein_percent": 30, "fat_percent": 30,
        "carbs_percent": 40,
    })
    assert r.status_code in (401, 403)

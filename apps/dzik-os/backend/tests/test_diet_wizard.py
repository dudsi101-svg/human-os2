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


# --- v2 (0.46.0): wbudowana baza, kompozycja, zbiorcze ostrzeżenia --------
#
# Scenariusz ze zrzutów właściciela z produkcji (24.08): ubogi katalog
# trenera (same produkty węglowodanowe o cudzych kategoriach) dawał
# posiłki jednoskładnikowe, 1168 kcal na cel 2200 i ścianę 28 ostrzeżeń.

UBOGI_KATALOG = [
    Skladnik("U1", "Wafle ryżowe", "Moje przekąski", 387, 8, 2.8, 81),
    Skladnik("U2", "Makaron pełnoziarnisty", "Moje węgle", 350, 13, 2.5, 67),
]

WBUDOWANA = [
    Skladnik("builtin:1", "Pierś z kurczaka", "Mięso i drób", 110, 23, 1.5, 0,
             source="builtin"),
    Skladnik("builtin:2", "Twaróg półtłusty", "Nabiał", 120, 18, 4, 3,
             source="builtin"),
    Skladnik("builtin:3", "Oliwa z oliwek", "Tłuszcze i oleje", 884, 0, 100, 0,
             source="builtin"),
    Skladnik("builtin:4", "Ryż biały", "Kasze, ryż i makarony", 345, 7, 0.7, 78,
             source="builtin"),
    Skladnik("builtin:5", "Brokuł", "Warzywa", 34, 2.8, 0.4, 7,
             source="builtin"),
    Skladnik("builtin:6", "Banan", "Owoce", 89, 1.1, 0.3, 23,
             source="builtin"),
    Skladnik("builtin:7", "Łosoś", "Ryby i owoce morza", 208, 20, 13, 0,
             source="builtin"),
    Skladnik("builtin:8", "Soczewica, ugotowana", "Rośliny strączkowe",
             116, 9, 0.4, 20, source="builtin"),
]


def test_poor_catalog_is_completed_from_builtin_and_marked():
    """Scenariusz z produkcji: propozycja ma być PEŁNA (makra w celu),
    braki dopełnione z wbudowanej bazy i jawnie oznaczone."""
    wynik = zbuduj_propozycje(
        UBOGI_KATALOG, target_kcal=2200.0, procent=PROCENT,
        posilkow_dziennie=4, dni=7, wbudowane=WBUDOWANA,
    )
    cel, srednia = wynik["target"], wynik["daily_average"]
    assert srednia["kcal"] > cel["kcal"] * 0.8          # nie 1168/2200
    assert srednia["protein_g"] > cel["protein_g"] * 0.8  # nie 24/165
    zrodla = {
        e["source"]
        for d in wynik["days"] for m in d["meals"] for e in m["entries"]
    }
    assert "builtin" in zrodla
    assert wynik["recommendation"] is not None
    assert "wbudowanej bazy" in wynik["recommendation"]


def test_warnings_are_aggregated_not_a_wall():
    """28 boxów ze zrzutu to był błąd UX: 7 dni ubogiego katalogu ma dać
    kilka zbiorczych zdań z licznikami, nie wpis per dzień×slot."""
    wynik = zbuduj_propozycje(
        UBOGI_KATALOG, target_kcal=2200.0, procent=PROCENT,
        posilkow_dziennie=4, dni=7, wbudowane=WBUDOWANA,
    )
    assert len(wynik["warnings"]) <= 10
    assert any("×" in w for w in wynik["warnings"])  # licznik wystąpień


def test_meals_contain_vegetable_or_fruit_additions():
    """Kompozycja wg wzorca śródziemnomorskiego/DASH: obiad z warzywem,
    śniadanie z owocem — nie sama arytmetyka makro."""
    wynik = _propozycja(posilkow_dziennie=3, dni=1)
    dzien = wynik["days"][0]
    posilki = {m["name"]: m for m in dzien["meals"]}
    kategorie_obiadu = {e["category"] for e in posilki["Obiad"]["entries"]}
    kategorie_sniadania = {e["category"] for e in posilki["Śniadanie"]["entries"]}
    assert "Warzywa" in kategorie_obiadu
    assert "Owoce" in kategorie_sniadania
    # posiłki są złożone: 3+ składników w posiłkach głównych
    assert len(posilki["Obiad"]["entries"]) >= 3


def test_lunch_protein_rotation_includes_fish_or_legumes_weekly():
    """Premia obiadowa: przy dostępnych rybach/strączkowych tygodniowa
    rotacja białka obiadowego sięga po nie co najmniej raz."""
    wynik = zbuduj_propozycje(
        UBOGI_KATALOG, target_kcal=2200.0, procent=PROCENT,
        posilkow_dziennie=3, dni=7, wbudowane=WBUDOWANA,
    )
    obiadowe_kategorie = {
        e["category"]
        for d in wynik["days"] for m in d["meals"] if m["name"] == "Obiad"
        for e in m["entries"]
    }
    assert obiadowe_kategorie & {"Ryby i owoce morza", "Rośliny strączkowe"}


def test_unknown_category_still_serves_as_macro_source():
    """Produkt o cudzej kategorii („Moje węgle") nie wypada z gry —
    działa jako źródło makro po klasyfikacji dominującym makrem."""
    wynik = zbuduj_propozycje(
        UBOGI_KATALOG, target_kcal=1800.0,
        procent={"protein": 15.0, "fat": 15.0, "carbs": 70.0},
        posilkow_dziennie=2, dni=1,
    )
    nazwy = {
        e["name"] for d in wynik["days"] for m in d["meals"]
        for e in m["entries"]
    }
    assert nazwy & {"Wafle ryżowe", "Makaron pełnoziarnisty"}


def test_load_builtin_endpoint_is_idempotent(seeded):
    """Dogranie wbudowanej bazy: świeży trener dostaje pełny katalog,
    drugie kliknięcie niczego nie dubluje ani nie nadpisuje."""
    from conftest import create_user_with_role
    from conftest import login as _login

    kredki = {"email": "nowy.trener@pilot.pl", "password": "NowyTrener#2026!"}
    create_user_with_role(kredki["email"], kredki["password"],
                          "Nowy Trener", "COACH")
    h = _login(seeded, kredki)
    r1 = seeded.post("/api/coach/food-products/load-builtin", headers=h)
    assert r1.status_code == 200
    assert r1.json()["added"] > 400
    r2 = seeded.post("/api/coach/food-products/load-builtin", headers=h)
    assert r2.json()["added"] == 0
    lista = seeded.get("/api/coach/food-products?limit=1", headers=h).json()
    assert lista["total"] == r1.json()["added"]

"""Kreator dań — silnik referencyjny (pakiet właściciela, 27 testów
przeniesionych 1:1 na ścieżkę `dzik_os.kulinaria.engine`) + adapter
żywieniowy na wbudowanej bazie produktów.

Wartości w fixture są JAWNIE syntetyczne (jak w pakiecie) — nie są bazą
żywieniową. Testy z prawdziwym katalogiem 300 sprawdzają wyłącznie
podgląd kulinarny (draft_preview) i odmowę produkcyjną przy zerze
publikacji.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dzik_os.kulinaria import adapter, dane
from dzik_os.kulinaria.engine import (
    InputError,
    audit_plan,
    coverage,
    generate,
    normalise_nutrients,
    shopping_list,
    validate_catalog,
)

DANE = Path(__file__).parent / "dane"


def fixture():
    """Synthetic test values, intentionally not a real food database."""
    food = {"id": "test_food", "name": "SYNTHETIC TEST FOOD", "state": "ready", "groups": ["plant"],
            "allergens": [], "allergen_verified": True, "nutrition_verified": True,
            "source_id": "SYNTHETIC_TEST_ONLY", "source_version": "1",
            "carb_definition": "available_excluding_fiber",
            "nutrition_per_100g": {"energy_kcal": 100, "protein_g": 10, "fat_g": 4, "carbs_available_g": 6, "fiber_g": 2}}
    foods = {"test_food": food}
    recipes = []
    for i, slot in enumerate(["breakfast", "main", "supper", "snack"]):
        for v in range(3):
            recipes.append({"id": f"test-{i}-{v}", "revision": 1, "family_id": f"family-{i}-{v}", "name": "TEST ONLY",
                            "meal_slots": [slot], "cuisine": "test", "status": "published", "servings": 1,
                            "ingredients": [{"food_id": "test_food", "grams": 100, "state": "ready", "role": "main"}],
                            "steps": ["Synthetic test fixture, not food advice."], "total_minutes": 5, "active_minutes": 5,
                            "equipment": [], "portion_variants": [{"id": "base", "factor": 1, "validated": True}],
                            "review": {"kitchen": True, "dietitian": True, "reviewer_id": "TEST_REVIEW", "expires_on": "2099-12-31"}})
    config = json.loads((DANE / "kulinaria_config.json").read_text(encoding="utf-8"))
    config.update(mode="production", days=2, animal_policy="omnivore", max_family_uses_per_week=42,
                  daily_bounds={"energy_kcal": [290, 310], "protein_g": [29, 31], "fat_g": [11, 13], "carbs_available_g": [17, 19]},
                  targets_reference="SYNTHETIC_TEST_TARGETS")
    return config, recipes, foods


def _katalog():
    return adapter.receptury(None), adapter.produkty_dla_silnika()


# --- 27 testów pakietu ----------------------------------------------------------


def test_production_balances_and_rechecks():
    c, r, f = fixture()
    res = generate(c, r, f)
    assert res["status"] == "ready_within_declared_bounds"
    assert res["plan"]["days"][0]["nutrition"]["energy_kcal"] == 300
    assert audit_plan(res["plan"], c, r, f) == []


def test_missing_health_route():
    c, r, f = fixture()
    c["screening_status"] = "unknown"
    assert generate(c, r, f)["status"] == "needs_review"


def test_invalid_macros():
    c, r, f = fixture()
    c["daily_bounds"]["protein_g"] = [50, 10]
    assert generate(c, r, f)["status"] == "needs_input"


def test_nan_rejected():
    c, r, f = fixture()
    c["daily_bounds"]["energy_kcal"] = [0, float("nan")]
    assert generate(c, r, f)["status"] == "needs_input"


def test_missing_target_provenance():
    c, r, f = fixture()
    c["targets_reference"] = None
    assert generate(c, r, f)["status"] == "needs_input"


def test_keto_conflict():
    c, r, f = fixture()
    c.update(carb_policy="ketogenic", carb_limit_g=10, carb_basis="available_excluding_fiber")
    assert generate(c, r, f)["status"] == "needs_input"


def test_keto_preview_does_not_invent_compliance():
    c, r, f = fixture()
    c.update(mode="preview", carb_policy="ketogenic", carb_limit_g=30, carb_basis="available_excluding_fiber")
    res = generate(c, r, f)
    assert res["status"] == "nutrition_unverified" and res["plan"] is None


def test_keto_full_day_limit():
    c, r, f = fixture()
    c.update(carb_policy="ketogenic", carb_limit_g=15, carb_basis="available_excluding_fiber")
    c["daily_bounds"]["carbs_available_g"] = [0, 20]
    assert generate(c, r, f)["status"] == "search_exhausted"


def test_carb_no_double_fiber_subtraction():
    _c, _r, f = fixture()
    assert normalise_nutrients(f["test_food"])["carbs_available_g"] == 6


def test_total_fiber_conversion():
    _c, _r, f = fixture()
    food = f["test_food"]
    food["carb_definition"] = "total_including_fiber"
    food["nutrition_per_100g"]["carbs_total_g"] = 8
    assert normalise_nutrients(food)["carbs_available_g"] == 6


def test_missing_fiber_is_not_zero():
    _c, _r, f = fixture()
    food = f["test_food"]
    food["carb_definition"] = "total_including_fiber"
    food["nutrition_per_100g"].pop("fiber_g")
    food["nutrition_per_100g"]["carbs_total_g"] = 8
    with pytest.raises(InputError):
        normalise_nutrients(food)


def test_polyols_not_subtracted():
    _c, _r, f = fixture()
    f["test_food"]["nutrition_per_100g"]["polyols_g"] = 5
    assert normalise_nutrients(f["test_food"])["carbs_available_g"] == 6


def test_unknown_allergen_is_not_safe():
    c, r, f = fixture()
    c["allergens"] = ["milk"]
    f["test_food"]["allergen_verified"] = False
    assert generate(c, r, f)["status"] == "insufficient_catalog"


def test_actual_allergen_excluded():
    c, r, f = fixture()
    c["allergens"] = ["milk"]
    f["test_food"]["allergens"] = ["milk"]
    assert generate(c, r, f)["plan"] is None


def test_vegan_excludes_dairy():
    c, r, f = fixture()
    c["animal_policy"] = "vegan"
    f["test_food"]["groups"] = ["dairy"]
    assert generate(c, r, f)["status"] == "insufficient_catalog"


def test_no_drafts_in_production():
    c, r, f = fixture()
    for rec in r:
        rec["status"] = "draft"
    assert generate(c, r, f)["status"] == "insufficient_catalog"


def test_no_unvalidated_portions():
    c, r, f = fixture()
    for rec in r:
        rec["portion_variants"][0]["validated"] = False
    assert generate(c, r, f)["status"] == "insufficient_catalog"


def test_missing_micronutrient_blocks_requested_scope():
    c, r, f = fixture()
    c["daily_bounds"]["vitamin_b12_ug"] = [1, 20]
    c["required_nutrients"] = ["vitamin_b12_ug"]
    assert generate(c, r, f)["status"] == "insufficient_catalog"


def test_state_mismatch():
    c, r, f = fixture()
    r[0]["ingredients"][0]["state"] = "dry"
    assert generate(c, r, f)["status"] == "needs_input"


def test_independent_audit_rejects_oil_like_mutation():
    c, r, f = fixture()
    p = generate(c, r, f)["plan"]
    p["days"][0]["meals"][0]["ingredients"][0]["grams"] = 700
    assert "ingredient mutation" in audit_plan(p, c, r, f)


def test_determinism():
    c, r, f = fixture()
    assert generate(c, r, f) == generate(c, r, f)


def test_fingerprint_includes_data_version():
    c, r, f = fixture()
    a = generate(c, r, f)["plan"]["id"]
    f["test_food"]["source_version"] = "2"
    assert a != generate(c, r, f)["plan"]["id"]


def test_no_partial_plan_on_failure():
    c, r, f = fixture()
    c["max_family_uses_per_week"] = 1
    c["days"] = 7
    res = generate(c, r, f)
    assert res["status"] == "search_exhausted" and res["plan"] is None


def test_31_days():
    c, r, f = fixture()
    c["days"] = 31
    c["start_date"] = "2026-12-20"
    assert generate(c, r, f)["plan"]["days"][-1]["date"] == "2027-01-19"


def test_shopping_totals():
    c, r, f = fixture()
    assert shopping_list(generate(c, r, f)["plan"])[0]["edible_grams"] == 600


def test_real_catalog_300_and_preview():
    c = json.loads((DANE / "kulinaria_config.json").read_text(encoding="utf-8"))
    c["days"] = 7
    r, f = _katalog()
    assert len(r) == 300
    validate_catalog(r, f)
    res = generate(c, r, f)
    assert res["status"] == "draft_preview" and res["plan"]["days"][0]["nutrition"] is None
    assert res["plan"]["carb_compliance_verified"] is False


def test_production_unmapped_library_refuses():
    c, _, _ = fixture()
    r, f = _katalog()
    assert generate(c, r, f)["status"] == "insufficient_catalog"


# --- adapter żywieniowy -----------------------------------------------------------


def test_adapter_mapuje_stany_i_nie_wymysla_wartosci():
    """Każdy produkt pakietu: albo wartości z wbudowanej bazy w ZGODNYM
    stanie i ze źródłem, albo jawnie nieznane (bez zera, bez zgadywania)."""
    foods = adapter.produkty_dla_silnika()
    assert len(foods) == 73
    rap = adapter.raport_mapowania()
    assert rap["z_wartosciami"] == 66
    # 5 bez pozycji/błonnika w bazie + 2 z niespójnym wierszem (błonnik > węglowodany ogółem)
    assert {b["id"] for b in rap["bez_wartosci"]} == {"lime", "potato", "basil", "parsley", "ginger", "cocoa", "oregano"}
    for f in foods.values():
        if f["nutrition_verified"]:
            n = normalise_nutrients(f)
            assert n["carbs_available_g"] >= 0 and f["source_id"] == "dzik_os_food_catalog"
            assert f["state"] == dane.produkty_pakietu()[f["id"]]["state"]
        else:
            assert f["nutrition_per_100g"] is None and f["mapping_note"]
    # produkty złożone nie mają „zweryfikowanych” alergenów
    assert foods["hummus"]["allergen_verified"] is False and foods["bread"]["allergen_verified"] is False
    assert foods["oats"]["allergen_verified"] is True and "gluten" in foods["oats"]["allergens"]


def test_pokrycie_na_prawdziwym_katalogu():
    r, f = _katalog()
    c = json.loads((DANE / "kulinaria_config.json").read_text(encoding="utf-8"))
    cov = coverage(r, f, c)
    assert cov["slots"]["breakfast"]["recipes"] == 60 and cov["rejected"] == {"animal_policy": 130}
    c["allergens"] = ["soy"]
    cov = coverage(r, f, c)
    # wegańska + alergia na soję: produkty złożone bez etykiety alergenów odpadają
    # jako „nieznane” (D08 — nieznane ≠ bezpieczne), nie tylko te z soją
    assert cov["slots"]["breakfast"]["recipes"] == 0
    assert cov["rejected"]["allergen"] > 0 and cov["rejected"]["unknown_allergen_data"] > 0

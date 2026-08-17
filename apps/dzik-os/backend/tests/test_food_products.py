"""Baza produktów spożywczych (broadcast + CRUD trenera) i kompozytor
diety: arytmetyka propose-only, nigdy nic nie zapisuje automatycznie."""

from conftest import CLIENT_A, COACH, create_user_with_role, login


def test_client_sees_seeded_food_products(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/me/food-products", headers=ha)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 20
    chicken = next(i for i in items if "kurczaka" in i["name"])
    assert chicken["protein_100g"] > 20


def test_coach_creates_edits_and_archives_product(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/food-products", headers=hc, json={
        "name": "Testowy produkt", "category": "Test",
        "kcal_100g": 100, "protein_100g": 10, "fat_100g": 5, "carbs_100g": 10,
    })
    assert r.status_code == 201
    item_id = r.json()["id"]

    r = seeded.put(f"/api/coach/food-products/{item_id}", headers=hc, json={
        "name": "Testowy produkt (edycja)", "category": "Test",
        "kcal_100g": 120, "protein_100g": 12, "fat_100g": 5, "carbs_100g": 10,
    })
    assert r.status_code == 200
    assert r.json()["kcal_100g"] == 120

    r = seeded.post(f"/api/coach/food-products/{item_id}/status?status=ARCHIVED", headers=hc)
    assert r.status_code == 200
    ha = login(seeded, CLIENT_A)
    client_items = seeded.get("/api/me/food-products", headers=ha).json()["items"]
    assert all(i["id"] != item_id for i in client_items)


def test_client_cannot_manage_products(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/coach/food-products", headers=ha, json={
        "name": "x", "kcal_100g": 1, "protein_100g": 1, "fat_100g": 1, "carbs_100g": 1,
    })
    assert r.status_code == 403


def test_other_coach_cannot_see_or_edit(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/food-products", headers=hc, json={
        "name": "Prywatny", "kcal_100g": 100, "protein_100g": 10, "fat_100g": 5, "carbs_100g": 10,
    })
    item_id = r.json()["id"]
    create_user_with_role("obcy.food@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.food@example.com", "password": "ObcyTrener#26"})
    r = seeded.put(f"/api/coach/food-products/{item_id}", headers=h2, json={
        "name": "Hack", "kcal_100g": 1, "protein_100g": 1, "fat_100g": 1, "carbs_100g": 1,
    })
    assert r.status_code == 404


def _product_ids(seeded, hc, names):
    items = seeded.get("/api/coach/food-products", headers=hc).json()["items"]
    by_name = {i["name"]: i["id"] for i in items}
    return [by_name[n] for n in names]


def test_diet_suggestion_splits_target_by_dominant_macro(seeded):
    hc = login(seeded, COACH)
    ids = _product_ids(seeded, hc, [
        "Pierś z kurczaka, surowa", "Ryż biały, ugotowany", "Oliwa z oliwek",
    ])
    r = seeded.post("/api/coach/diet-suggestion", headers=hc, json={
        "target_kcal": 3000, "target_protein_g": 180, "target_fat_g": 80,
        "target_carbs_g": 350, "product_ids": ids,
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 3
    protein_item = next(i for i in body["items"] if i["macro_role"] == "PROTEIN")
    assert protein_item["name"] == "Pierś z kurczaka, surowa"
    # Gramatura produktu białkowego dokładnie trafia w cel białka (jedyny
    # produkt w tej kategorii) — całkowita suma białka jest wyższa, bo ryż
    # też wnosi trochę białka przy okazji dostarczania węglowodanów.
    assert abs(protein_item["protein_g"] - 180) < 0.5
    assert body["totals"]["protein_g"] > 180
    assert "nic nie zostało zapisane" in body["note"]
    assert body["warnings"] == []


def test_diet_suggestion_warns_when_macro_category_missing(seeded):
    hc = login(seeded, COACH)
    ids = _product_ids(seeded, hc, ["Pierś z kurczaka, surowa"])
    r = seeded.post("/api/coach/diet-suggestion", headers=hc, json={
        "target_kcal": 2000, "target_protein_g": 150, "target_fat_g": 70,
        "target_carbs_g": 200, "product_ids": ids,
    })
    assert r.status_code == 200
    body = r.json()
    assert any("tłuszcz" in w for w in body["warnings"])
    assert any("węglowodan" in w for w in body["warnings"])
    # Nic nie zostało utworzone w planie żywieniowym klienta.
    assert len(body["items"]) == 1


def test_diet_suggestion_rejects_products_from_other_coach(seeded):
    hc = login(seeded, COACH)
    create_user_with_role("obcy.diet@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.diet@example.com", "password": "ObcyTrener#26"})
    r = seeded.post("/api/coach/food-products", headers=h2, json={
        "name": "Cudzy produkt", "kcal_100g": 100, "protein_100g": 10, "fat_100g": 5, "carbs_100g": 10,
    })
    foreign_id = r.json()["id"]
    r = seeded.post("/api/coach/diet-suggestion", headers=hc, json={
        "target_kcal": 2000, "target_protein_g": 100, "target_fat_g": 0,
        "target_carbs_g": 0, "product_ids": [foreign_id],
    })
    assert r.status_code == 422


def test_diet_suggestion_requires_coach_role(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/coach/diet-suggestion", headers=ha, json={
        "target_kcal": 2000, "product_ids": ["HOS-FOD-000000000000"],
    })
    assert r.status_code == 403

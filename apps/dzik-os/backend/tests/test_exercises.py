"""Baza ćwiczeń (know-how trenera): broadcast do aktywnych klientów,
CRUD po stronie trenera, izolacja między trenerami."""

from conftest import CLIENT_A, COACH, create_user_with_role, login


def test_client_sees_seeded_exercises_grouped_by_muscle(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/me/exercises", headers=ha)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 10
    assert any(i["muscle_group"] == "NOGI" for i in items)
    assert all(i["how_to"] for i in items)


def test_coach_creates_edits_and_archives_exercise(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "Test ćwiczenie", "muscle_group": "PLECY",
        "how_to": "Opis techniki", "benefit": "Efekt testowy",
    })
    assert r.status_code == 201
    item_id = r.json()["id"]

    r = seeded.put(f"/api/coach/exercises/{item_id}", headers=hc, json={
        "name": "Test ćwiczenie (edycja)", "muscle_group": "PLECY",
        "how_to": "Zaktualizowany opis", "benefit": "Nowy efekt",
    })
    assert r.status_code == 200
    assert r.json()["how_to"] == "Zaktualizowany opis"

    r = seeded.post(f"/api/coach/exercises/{item_id}/status?status=ARCHIVED", headers=hc)
    assert r.status_code == 200

    ha = login(seeded, CLIENT_A)
    client_items = seeded.get("/api/me/exercises", headers=ha).json()["items"]
    assert all(i["id"] != item_id for i in client_items)


def test_invalid_muscle_group_rejected(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "X", "muscle_group": "SKRZYDLA", "how_to": "opis",
    })
    assert r.status_code == 422


def test_other_coach_cannot_edit_or_see_in_own_list(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "Prywatne", "muscle_group": "NOGI", "how_to": "x",
    })
    item_id = r.json()["id"]

    create_user_with_role("obcy.ex@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.ex@example.com", "password": "ObcyTrener#26"})

    r = seeded.put(f"/api/coach/exercises/{item_id}", headers=h2, json={
        "name": "Hack", "muscle_group": "NOGI", "how_to": "x",
    })
    assert r.status_code == 404
    own_list = seeded.get("/api/coach/exercises", headers=h2).json()["items"]
    assert all(i["id"] != item_id for i in own_list)


def test_client_cannot_manage_exercises(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/coach/exercises", headers=ha, json={
        "name": "x", "muscle_group": "NOGI", "how_to": "x",
    })
    assert r.status_code == 403

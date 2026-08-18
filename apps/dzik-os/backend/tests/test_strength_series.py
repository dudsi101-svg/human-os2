"""Strukturalny dziennik serii i serie siłowe (objętość + szacowany 1RM).
Porównania wyłącznie z własną historią klienta."""

from conftest import CLIENT_A, COACH, get_user_id, login


def test_seeded_strength_series_present(seeded):
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    r = seeded.get(f"/api/clients/{client_id}/strength-series", headers=ha)
    assert r.status_code == 200
    series = r.json()["series"]
    squat = next(s for s in series if s["exercise_name"] == "Przysiad ze sztangą")
    assert len(squat["points"]) == 3
    # Objętość: 4 serie × 6 powt. × ciężar; e1RM (Epley): kg × (1 + 6/30).
    last = squat["points"][-1]
    assert last["volume_kg"] == 4 * 6 * 105
    assert last["e1rm_kg"] == round(105 * (1 + 6 / 30), 1)
    # Trend rośnie (progresja z seedu).
    assert squat["points"][0]["e1rm_kg"] < last["e1rm_kg"]


def test_log_workout_with_sets_feeds_records_and_series(seeded):
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    plans = seeded.get(f"/api/clients/{client_id}/plans", headers=ha).json()["plans"]
    version_id = plans[0]["current_version"]["id"]

    r = seeded.post(f"/api/clients/{client_id}/workouts", headers=ha, json={
        "plan_version_id": version_id, "day_index": 0,
        "performed_on": "2026-08-18", "status": "DONE",
        "entries": [{
            "exercise_index": 0, "exercise_name": "Martwy ciąg",
            "sets": [{"weight_kg": 140, "reps": 3}, {"weight_kg": 150, "reps": 1}],
        }],
    })
    assert r.status_code == 201

    workouts = seeded.get(f"/api/clients/{client_id}/workouts", headers=ha).json()["workouts"]
    logged = next(w for w in workouts if w["performed_on"] == "2026-08-18")
    assert logged["entries"][0]["sets"] == [
        {"weight_kg": 140, "reps": 3}, {"weight_kg": 150, "reps": 1},
    ]

    # Rekord osobisty liczony ze strukturalnych serii (bez tekstu wyniku).
    records = seeded.get(f"/api/clients/{client_id}/personal-records", headers=ha).json()
    deadlift = next(x for x in records["records"] if x["exercise_name"] == "Martwy ciąg")
    assert deadlift["best_kg"] == 150

    series = seeded.get(f"/api/clients/{client_id}/strength-series", headers=ha).json()["series"]
    dl = next(s for s in series if s["exercise_name"] == "Martwy ciąg")
    assert dl["points"][0]["volume_kg"] == 140 * 3 + 150 * 1
    assert dl["points"][0]["e1rm_kg"] == round(140 * (1 + 3 / 30), 1)  # 1 powt. = bez wzoru


def test_strength_series_requires_relationship(seeded):
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    hc = login(seeded, COACH)
    assert seeded.get(f"/api/clients/{client_id}/strength-series", headers=hc).status_code == 200

    from conftest import create_user_with_role

    create_user_with_role("obcy.str@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.str@example.com", "password": "ObcyTrener#26"})
    assert seeded.get(f"/api/clients/{client_id}/strength-series", headers=h2).status_code == 404

from conftest import CLIENT_A, COACH, get_user_id, login

# Tydzień inny niż raport z seedu (uniknięcie kolizji z REVIEWED).
WEEK = "2026-08-24"


def _submit(client, headers, **overrides):
    payload = {
        "week_start": WEEK, "weight_kg": 85.8, "trainings_done": 3,
        "diet_adherence": 4, "energy": 4, "sleep": 4, "hunger": 2,
        "stress": 2, "recovery": 4, "comment": "Solidny tydzień",
        "questions": "Czy zwiększamy kalorie?",
    }
    payload.update(overrides)
    return client.post("/api/checkins", json=payload, headers=headers)


def test_submit_correct_and_review_flow(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)

    r = _submit(seeded, ha)
    assert r.status_code == 201
    checkin_id = r.json()["id"]
    assert r.json()["revision"] == 1

    # Poprawka deklaracji: rewizja 2, poprzednia treść zachowana.
    r = _submit(seeded, ha, weight_kg=85.6, comment="Korekta masy")
    assert r.json()["revision"] == 2
    revisions = seeded.get(f"/api/checkins/{checkin_id}/revisions",
                           headers=ha).json()["revisions"]
    assert len(revisions) == 1
    assert revisions[0]["payload"]["weight_kg"] == 85.8

    # Trener odpowiada.
    r = seeded.post(f"/api/checkins/{checkin_id}/review", headers=hc,
                    json={"coach_response": "Zwiększamy do 2400 kcal."})
    assert r.status_code == 200
    checkins = seeded.get(f"/api/clients/{id_a}/checkins", headers=ha).json()["checkins"]
    reviewed = next(c for c in checkins if c["id"] == checkin_id)
    assert reviewed["status"] == "REVIEWED"
    assert "2400" in reviewed["coach_response"]

    # Po ocenie klient nie nadpisze raportu.
    r = _submit(seeded, ha, weight_kg=80)
    assert r.status_code == 409


def test_coach_cannot_submit_checkin(seeded):
    hc = login(seeded, COACH)
    assert _submit(seeded, hc).status_code == 403


def test_checkin_with_photo(seeded):
    import io

    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    up = seeded.post("/api/files", headers=ha, files={
        "file": ("sylwetka.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 50),
                 "image/png")})
    file_id = up.json()["id"]
    r = _submit(seeded, ha, photo_ids=[file_id])
    assert r.status_code == 201
    photos = seeded.get(f"/api/clients/{id_a}/photos", headers=ha).json()["photos"]
    assert any(p["file_id"] == file_id for p in photos)

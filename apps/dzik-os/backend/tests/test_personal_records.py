"""Rekordy osobiste: wyłącznie własna historia klienta (bez porównań
między ludźmi), deterministyczne parsowanie ciężarów, izolacja dostępu."""

from conftest import CLIENT_A, COACH, create_user_with_role, login


def _client_id(seeded, hc) -> str:
    clients = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    return next(c["client_id"] for c in clients if c["email"] == CLIENT_A["email"])


def test_records_from_seeded_workouts(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    client_id = _client_id(seeded, hc)
    r = seeded.get(f"/api/clients/{client_id}/personal-records", headers=ha)
    assert r.status_code == 200
    body = r.json()
    squat = next(x for x in body["records"] if x["exercise_name"] == "Przysiad ze sztangą")
    assert squat["best_kg"] == 105.0
    assert squat["previous_best_kg"] == 100.0
    assert squat["attempts"] == 3
    assert squat["is_new"] is True  # poprawiony 2 dni temu względem wcześniejszych
    bench = next(x for x in body["records"] if x["exercise_name"] == "Wyciskanie sztangi leżąc")
    assert bench["best_kg"] == 70.0  # przecinek dziesiętny "67,5 kg" też sparsowany
    # Nowe rekordy sortowane na początek listy.
    assert body["records"][0]["is_new"] is True


def test_since_start_deltas_from_measurements(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    client_id = _client_id(seeded, hc)
    body = seeded.get(f"/api/clients/{client_id}/personal-records", headers=ha).json()
    weight = next(x for x in body["since_start"] if x["kind"] == "weight")
    # Seed: 8 tygodni historii wagi, 90.0 kg na starcie, spadek 0.6/tydz.
    assert weight["first_value"] == 90.0
    assert weight["delta"] < 0  # redukcja — postęp względem startu
    assert weight["unit"] == "kg"


def test_coach_sees_same_records(seeded):
    hc = login(seeded, COACH)
    client_id = _client_id(seeded, hc)
    r = seeded.get(f"/api/clients/{client_id}/personal-records", headers=hc)
    assert r.status_code == 200
    assert any(x["exercise_name"] == "Przysiad ze sztangą" for x in r.json()["records"])


def test_unrelated_coach_denied(seeded):
    hc = login(seeded, COACH)
    client_id = _client_id(seeded, hc)
    create_user_with_role("obcy.rec@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.rec@example.com", "password": "ObcyTrener#26"})
    r = seeded.get(f"/api/clients/{client_id}/personal-records", headers=h2)
    assert r.status_code == 404


def test_unparseable_results_skipped(seeded):
    """Wynik bez rozpoznawalnego ciężaru (np. 'max powtórzeń') nie tworzy
    rekordu — żadnego zgadywania."""
    from dzik_os.routers.records import _max_weight_kg

    assert _max_weight_kg("3x8 @ 80kg") == 80.0
    assert _max_weight_kg("praca do 102,5 kg") == 102.5
    assert _max_weight_kg("4 serie do upadku") is None
    assert _max_weight_kg("60 kg + 70 kg drop set") == 70.0

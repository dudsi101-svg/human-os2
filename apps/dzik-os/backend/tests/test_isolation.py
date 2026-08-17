"""Testy izolacji danych między kontami (ochrona przed IDOR)."""

from conftest import (
    ADMIN,
    CLIENT_A,
    CLIENT_B,
    COACH,
    create_user_with_role,
    get_user_id,
    login,
)


def test_client_cannot_read_other_clients_data(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    id_b = get_user_id(seeded, hb)
    for path in (
        f"/api/clients/{id_b}/profile",
        f"/api/clients/{id_b}/plans",
        f"/api/clients/{id_b}/measurements",
        f"/api/clients/{id_b}/checkins",
        f"/api/clients/{id_b}/payments",
        f"/api/clients/{id_b}/documents",
        f"/api/clients/{id_b}/photos",
        f"/api/clients/{id_b}/schedule",
        f"/api/clients/{id_b}/goals",
        f"/api/clients/{id_b}/nutrition",
    ):
        r = seeded.get(path, headers=ha)
        assert r.status_code == 404, f"{path} -> {r.status_code}"


def test_client_cannot_write_other_clients_data(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    id_b = get_user_id(seeded, hb)
    r = seeded.put(f"/api/clients/{id_b}/profile", headers=ha,
                   json=[{"field_key": "cel_glowny", "value": "hack"}])
    assert r.status_code == 404
    r = seeded.post(f"/api/clients/{id_b}/measurements", headers=ha,
                    json={"kind": "weight", "value": 1, "unit": "kg",
                          "measured_at": "2026-08-01"})
    assert r.status_code == 404


def test_client_cannot_use_coach_endpoints(seeded):
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/coach/clients", headers=ha).status_code == 403
    r = seeded.post("/api/plans", headers=ha, json={
        "client_id": get_user_id(seeded, ha), "title": "x",
        "version": {"reason": "r", "days": []},
    })
    assert r.status_code == 403


def test_unassigned_coach_cannot_access_client(seeded):
    create_user_with_role("obcy.trener@example.com", "ObcyTrener#26", "Obcy Trener",
                          "COACH")
    h2 = login(seeded, {"email": "obcy.trener@example.com",
                        "password": "ObcyTrener#26"})
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=h2).status_code == 404
    assert seeded.get(f"/api/clients/{id_a}/checkins", headers=h2).status_code == 404
    assert seeded.get(f"/api/coach/clients/{id_a}/history",
                      headers=h2).status_code == 404


def test_admin_cannot_access_health_data(seeded):
    hadm = login(seeded, ADMIN)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    for path in (
        f"/api/clients/{id_a}/profile",
        f"/api/clients/{id_a}/measurements",
        f"/api/clients/{id_a}/checkins",
        f"/api/clients/{id_a}/photos",
    ):
        r = seeded.get(path, headers=hadm)
        assert r.status_code in (403, 404), f"{path} -> {r.status_code}"


def test_client_cannot_use_admin_endpoints(seeded):
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/admin/users", headers=ha).status_code == 403
    assert seeded.get("/api/admin/receipts", headers=ha).status_code == 403


def test_coach_sees_assigned_client(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.get(f"/api/clients/{id_a}/profile", headers=hc)
    assert r.status_code == 200
    keys = {f["field_key"] for f in r.json()["fields"]}
    assert "cel_glowny" in keys

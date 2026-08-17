"""Zgody: cofnięcie odbiera trenerowi dostęp; decyzję podejmuje
hos_engine.ConsentRegistry (Human OS Core)."""

from conftest import CLIENT_A, COACH, get_user_id, login


def test_revoke_consent_blocks_coach_access(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)

    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 200

    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    active = next(c for c in consents if c["revoked_at"] is None)
    r = seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    assert r.status_code == 200
    assert r.json()["revoked_at"]

    # Trener traci dostęp do danych zdrowotnych mimo aktywnej relacji.
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 404
    assert seeded.get(f"/api/clients/{id_a}/measurements",
                      headers=hc).status_code == 404

    # Klient nadal widzi własne dane.
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=ha).status_code == 200


def test_regrant_restores_access(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    coach_id = get_user_id(seeded, hc)
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    active = next(c for c in consents if c["revoked_at"] is None)
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 404

    r = seeded.post("/api/me/consents", headers=ha, json={
        "grantee_id": coach_id, "purpose": "coaching", "domain": "health_data",
        "actions": "read,write", "allow_sensitive": True,
    })
    assert r.status_code == 201
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 200


def test_consent_history_is_preserved(seeded):
    ha = login(seeded, CLIENT_A)
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    active = next(c for c in consents if c["revoked_at"] is None)
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    after = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    revoked = next(c for c in after if c["id"] == active["id"])
    assert revoked["revoked_at"] is not None  # wiersz zostaje, nie znika


def test_cannot_revoke_someone_elses_consent(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, {"email": "klient.b@example.com",
                        "password": "KlientB#2026!x"})
    consents_b = seeded.get("/api/me/consents", headers=hb).json()["consents"]
    target = consents_b[0]["id"]
    r = seeded.post(f"/api/me/consents/{target}/revoke", headers=ha)
    assert r.status_code == 404
    after = seeded.get("/api/me/consents", headers=hb).json()["consents"]
    assert next(c for c in after if c["id"] == target)["revoked_at"] is None

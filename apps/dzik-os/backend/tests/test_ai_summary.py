"""AI to propose-only: bez skonfigurowanego dostawcy zwraca jawną
informację, nigdy nie udaje działania i niczego nie zapisuje."""

from conftest import CLIENT_A, COACH, get_user_id, login


def test_ai_summary_not_configured_by_default(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    checkins = seeded.get(f"/api/clients/{id_a}/checkins", headers=hc).json()["checkins"]
    checkin_id = checkins[0]["id"]

    r = seeded.post(f"/api/checkins/{checkin_id}/ai-summary", headers=hc)
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert "reason" in body and body["reason"]

    # Nie zapisało odpowiedzi ani nie oznaczyło jako oceniony.
    after = seeded.get(f"/api/clients/{id_a}/checkins", headers=hc).json()["checkins"]
    same = next(c for c in after if c["id"] == checkin_id)
    assert same["status"] == checkins[0]["status"]


def test_ai_summary_requires_coach_role(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    checkins = seeded.get(f"/api/clients/{id_a}/checkins", headers=ha).json()["checkins"]
    r = seeded.post(f"/api/checkins/{checkins[0]['id']}/ai-summary", headers=ha)
    assert r.status_code == 403


def test_ai_summary_requires_access(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    checkins = seeded.get(f"/api/clients/{id_a}/checkins", headers=hc).json()["checkins"]
    checkin_id = checkins[0]["id"]

    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    active = next(c for c in consents if c["revoked_at"] is None)
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)

    r = seeded.post(f"/api/checkins/{checkin_id}/ai-summary", headers=hc)
    assert r.status_code == 404

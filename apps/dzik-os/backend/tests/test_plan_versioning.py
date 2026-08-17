"""Wersjonowanie planów: nowa wersja nie usuwa poprzedniej (zasada Human OS)."""

from conftest import CLIENT_A, COACH, get_user_id, login


def _plan_id(seeded, hc, ha):
    id_a = get_user_id(seeded, ha)
    plans = seeded.get(f"/api/clients/{id_a}/plans", headers=hc).json()["plans"]
    return next(p for p in plans if not p["is_template"])


def test_new_version_preserves_previous(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    plan = _plan_id(seeded, hc, ha)
    assert plan["current_version_no"] == 2  # seed ma v1 i v2

    r = seeded.post(f"/api/plans/{plan['id']}/versions", headers=hc, json={
        "reason": "Deload po zgłoszeniu zmęczenia",
        "days": [{"name": "Deload A", "weekday": 1, "exercises": [
            {"name": "Przysiad", "sets": "2", "reps": "5", "weight": "80 kg"},
        ]}],
    })
    assert r.status_code == 201
    assert r.json()["version_no"] == 3

    versions = seeded.get(f"/api/plans/{plan['id']}/versions",
                          headers=hc).json()["versions"]
    assert [v["version_no"] for v in versions] == [1, 2, 3]
    v1 = versions[0]
    assert v1["reason"] == "Plan startowy współpracy"
    assert v1["content"]["days"][1]["exercises"][0]["weight"] == "100 kg"
    v3 = versions[2]
    assert v3["reason"] == "Deload po zgłoszeniu zmęczenia"


def test_version_requires_reason(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    plan = _plan_id(seeded, hc, ha)
    r = seeded.post(f"/api/plans/{plan['id']}/versions", headers=hc,
                    json={"reason": "", "days": []})
    assert r.status_code == 422


def test_client_sees_current_version_and_history(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    plan = _plan_id(seeded, hc, ha)
    r = seeded.get(f"/api/plans/{plan['id']}/versions", headers=ha)
    assert r.status_code == 200
    assert len(r.json()["versions"]) >= 2


def test_client_cannot_create_version(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    plan = _plan_id(seeded, hc, ha)
    r = seeded.post(f"/api/plans/{plan['id']}/versions", headers=ha,
                    json={"reason": "próba", "days": []})
    assert r.status_code == 403


def test_plan_change_is_audited(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    plan = _plan_id(seeded, hc, ha)
    seeded.post(f"/api/plans/{plan['id']}/versions", headers=hc,
                json={"reason": "Audytowana zmiana", "days": []})
    receipts = seeded.get(f"/api/coach/clients/{id_a}/history",
                          headers=hc).json()["receipts"]
    actions = [r["action"] for r in receipts]
    assert "PLAN_VERSION_CREATED" in actions
    newest = next(r for r in receipts if r["action"] == "PLAN_VERSION_CREATED")
    assert newest["event_hash"]


def test_workout_logging_against_plan(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    plan = _plan_id(seeded, hc, ha)
    versions = seeded.get(f"/api/plans/{plan['id']}/versions",
                          headers=ha).json()["versions"]
    current = versions[-1]
    r = seeded.post(f"/api/clients/{id_a}/workouts", headers=ha, json={
        "plan_version_id": current["id"], "day_index": 0,
        "performed_on": "2026-08-17", "status": "DONE",
        "pain_flag": True, "pain_note": "Lekki ból barku przy 3 serii",
        "entries": [{"exercise_index": 0, "exercise_name": "Wyciskanie",
                     "result": "4x8 @ 70 kg"}],
    })
    assert r.status_code == 201
    workouts = seeded.get(f"/api/clients/{id_a}/workouts", headers=hc).json()["workouts"]
    assert workouts[0]["pain_flag"] is True
    assert workouts[0]["entries"][0]["result"] == "4x8 @ 70 kg"

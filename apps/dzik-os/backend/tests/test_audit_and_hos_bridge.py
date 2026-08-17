"""Integracja z Human OS Core: łańcuch zdarzeń, pokwitowania, zgody."""

from itertools import pairwise

from conftest import ADMIN, CLIENT_A, COACH, get_user_id, login

from dzik_os.hos_bridge import event_store, verify_audit_chain


def test_audit_chain_is_hash_linked_and_valid(seeded):
    events = event_store().all()
    assert len(events) > 5
    assert verify_audit_chain() is True
    # Każde zdarzenie jest niemutowalne i powiązane hashem z poprzednim.
    assert all(e["immutable"] is True for e in events)
    for prev, curr in pairwise(events):
        assert curr["previous_hash"] == prev["event_hash"]


def test_receipts_reference_chain_events(seeded):
    hadm = login(seeded, ADMIN)
    receipts = seeded.get("/api/admin/receipts", headers=hadm).json()["receipts"]
    assert receipts
    hashes = {e["event_hash"] for e in event_store().all()}
    ids = {e["id"] for e in event_store().all()}
    for r in receipts[:20]:
        assert r["event_hash"] in hashes
        assert r["event_id"] in ids


def test_admin_verify_endpoint(seeded):
    hadm = login(seeded, ADMIN)
    r = seeded.get("/api/admin/audit/verify", headers=hadm)
    assert r.status_code == 200
    assert r.json()["chain_valid"] is True


def test_admin_access_is_itself_audited(seeded):
    hadm = login(seeded, ADMIN)
    seeded.get("/api/admin/users", headers=hadm)
    actions = [e["event_type"] for e in event_store().all()]
    assert "ADMIN_USER_LIST_ACCESSED" in actions


def test_high_significance_operations_produce_events(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    seeded.put(f"/api/clients/{id_a}/profile", headers=ha,
               json=[{"field_key": "cel_glowny", "value": "Nowy cel testowy"}])
    seeded.post("/api/schedule", headers=hc, json={
        "client_id": id_a, "name": "Spacer", "category": "REGENERACJA",
        "days_of_week": "6,7",
    })
    actions = [e["event_type"] for e in event_store().all()]
    for expected in ("IDENTITY_REGISTERED", "CONSENT_GRANTED", "PROFILE_UPDATED",
                     "SCHEDULE_ITEM_CREATED", "PLAN_VERSION_CREATED"):
        assert expected in actions, expected


def test_profile_versioning_keeps_history(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    seeded.put(f"/api/clients/{id_a}/profile", headers=ha,
               json=[{"field_key": "cel_glowny", "value": "Wersja 2 celu"}])
    history = seeded.get(f"/api/clients/{id_a}/profile/history",
                         headers=ha).json()["fields"]
    cel = [f for f in history if f["field_key"] == "cel_glowny"]
    assert len(cel) == 2
    assert cel[0]["is_current"] is False and cel[1]["is_current"] is True
    assert cel[1]["version"] == 2
    current = seeded.get(f"/api/clients/{id_a}/profile", headers=ha).json()["fields"]
    assert next(f for f in current
                if f["field_key"] == "cel_glowny")["value"] == "Wersja 2 celu"

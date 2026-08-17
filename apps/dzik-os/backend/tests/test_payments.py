from conftest import CLIENT_A, COACH, create_user_with_role, get_user_id, login


def test_client_sees_payment_status_and_due_date(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.get(f"/api/clients/{id_a}/payments", headers=ha)
    assert r.status_code == 200
    schedules = r.json()["schedules"]
    assert schedules[0]["package_name"] == "Prowadzenie miesięczne PRO"
    statuses = {rec["status"] for s in schedules for rec in s["records"]}
    assert {"PAID", "PENDING"} <= statuses


def test_coach_marks_payment_paid_and_it_is_audited(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    schedules = seeded.get(f"/api/clients/{id_a}/payments", headers=hc).json()["schedules"]
    pending = next(rec for s in schedules for rec in s["records"]
                   if rec["status"] == "PENDING")
    r = seeded.post(f"/api/payments/records/{pending['id']}/status", headers=hc,
                    json={"status": "PAID", "note": "przelew otrzymany"})
    assert r.status_code == 200
    after = seeded.get(f"/api/clients/{id_a}/payments", headers=ha).json()["schedules"]
    rec = next(rec for s in after for rec in s["records"] if rec["id"] == pending["id"])
    assert rec["status"] == "PAID"
    assert rec["paid_at"]
    history = seeded.get(f"/api/coach/clients/{id_a}/history", headers=hc).json()
    assert any(x["action"] == "PAYMENT_STATUS_CHANGED" for x in history["receipts"])


def test_other_coach_cannot_touch_payment(seeded):
    create_user_with_role("obcy2@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy2@example.com", "password": "ObcyTrener#26"})
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    schedules = seeded.get(f"/api/clients/{id_a}/payments", headers=hc).json()["schedules"]
    rec = schedules[0]["records"][0]
    r = seeded.post(f"/api/payments/records/{rec['id']}/status", headers=h2,
                    json={"status": "CANCELLED"})
    assert r.status_code == 404


def test_client_cannot_change_payment_status(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    schedules = seeded.get(f"/api/clients/{id_a}/payments", headers=ha).json()["schedules"]
    rec = schedules[0]["records"][0]
    r = seeded.post(f"/api/payments/records/{rec['id']}/status", headers=ha,
                    json={"status": "PAID"})
    assert r.status_code == 403


def test_new_schedule_creates_first_record(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.post("/api/payments/schedules", headers=hc, json={
        "client_id": id_a, "package_name": "Konsultacja jednorazowa",
        "amount_cents": 15000, "period": "ONE_OFF",
        "first_due_date": "2026-09-01",
    })
    assert r.status_code == 201
    payments = seeded.get(f"/api/clients/{id_a}/payments", headers=ha).json()["schedules"]
    match = next(s for s in payments if s["package_name"] == "Konsultacja jednorazowa")
    assert match["records"][0]["due_date"] == "2026-09-01"

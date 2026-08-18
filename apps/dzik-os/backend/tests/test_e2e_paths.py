"""E2E na poziomie API: pełna ścieżka trenera i klienta (kryteria §16)."""

import io

from conftest import COACH, login


def test_full_coach_and_client_journey(client):
    from dzik_os import seed as seed_module

    seed_module.seed()
    hc = login(client, COACH)

    # 1. Trener zakłada nowego klienta.
    r = client.post("/api/coach/clients", headers=hc, json={
        "client_email": "nowy.klient@example.com",
        "client_name": "Nowy Klient",
        "initial_password": "StartoweHaslo#1",
    })
    assert r.status_code == 201
    new_id = r.json()["client_id"]

    # 2. Klient loguje się, zmienia hasło startowe, potwierdza zgodę
    #    i uzupełnia profil.
    hn = login(client, {"email": "nowy.klient@example.com",
                        "password": "StartoweHaslo#1"})
    r = client.post("/api/auth/change-password", headers=hn, json={
        "current_password": "StartoweHaslo#1", "new_password": "WlasneNowe#123"})
    assert r.status_code == 200
    hn = {"Authorization": f"Bearer {r.json()['token']}"}  # rotacja tokenu
    consents = client.get("/api/me/consents", headers=hn).json()["consents"]
    onboarding = next(c for c in consents if c["confirmed_at"] is None)
    r = client.post(f"/api/me/consents/{onboarding['id']}/confirm", headers=hn)
    assert r.status_code == 200
    r = client.put(f"/api/clients/{new_id}/profile", headers=hn, json=[
        {"field_key": "cel_glowny", "value": "Poprawa kondycji"},
        {"field_key": "dni_treningowe", "value": "wt, czw"},
        {"field_key": "urazy", "value": "Brak", "sensitive": True},
    ])
    assert r.status_code == 200

    # 3. Trener tworzy plan (v1) i dietę; przypisuje harmonogram.
    r = client.post("/api/plans", headers=hc, json={
        "client_id": new_id, "title": "Kondycja — start",
        "version": {"reason": "Plan startowy", "days": [
            {"name": "Całe ciało", "weekday": 2, "exercises": [
                {"name": "Goblet squat", "sets": "3", "reps": "12",
                 "weight": "16 kg"}]},
        ]},
    })
    assert r.status_code == 201
    plan_id = r.json()["id"]
    v1_id = r.json()["version_id"]
    r = client.post("/api/nutrition", headers=hc, json={
        "client_id": new_id, "title": "Baza 2000 kcal",
        "version": {"reason": "Start", "kcal": 2000, "protein_g": 140,
                    "fat_g": 60, "carbs_g": 220,
                    "sections": [{"title": "Zasady", "body": "3 posiłki"}],
                    "meals": []},
    })
    assert r.status_code == 201
    r = client.post("/api/schedule", headers=hc, json={
        "client_id": new_id, "name": "Trening", "category": "TRENING",
        "time_of_day": "18:00", "days_of_week": "2,4",
    })
    assert r.status_code == 201
    r = client.post("/api/payments/schedules", headers=hc, json={
        "client_id": new_id, "package_name": "START", "amount_cents": 30000,
        "first_due_date": "2026-09-01",
    })
    assert r.status_code == 201

    # 4. Klient widzi plan, dietę, harmonogram, płatność i ekran Dzisiaj.
    plans = client.get(f"/api/clients/{new_id}/plans", headers=hn).json()["plans"]
    assert plans[0]["title"] == "Kondycja — start"
    nutrition = client.get(f"/api/clients/{new_id}/nutrition",
                           headers=hn).json()["plans"]
    assert nutrition[0]["current_version"]["content"]["kcal"] == 2000
    schedule = client.get(f"/api/clients/{new_id}/schedule",
                          headers=hn).json()["items"]
    assert schedule[0]["author_id"]
    today = client.get("/api/me/today", headers=hn).json()
    assert today["next_payment"]["amount_cents"] == 30000

    # 5. Klient wykonuje trening z wynikiem i przesyła zdjęcie + raport.
    r = client.post(f"/api/clients/{new_id}/workouts", headers=hn, json={
        "plan_version_id": v1_id, "day_index": 0, "performed_on": "2026-08-18",
        "status": "DONE",
        "entries": [{"exercise_index": 0, "exercise_name": "Goblet squat",
                     "result": "3x12 @ 16 kg"}],
    })
    assert r.status_code == 201
    from conftest import make_png

    up = client.post("/api/files", headers=hn, files={
        "file": ("progres.png", io.BytesIO(make_png()), "image/png")})
    assert up.status_code == 201
    r = client.post("/api/checkins", headers=hn, json={
        "week_start": "2026-08-17", "weight_kg": 78.5, "trainings_done": 1,
        "diet_adherence": 4, "energy": 3, "sleep": 4, "hunger": 3, "stress": 2,
        "recovery": 4, "comment": "Pierwszy tydzień OK",
        "questions": "Czy dodać cardio?", "photo_ids": [up.json()["id"]],
    })
    assert r.status_code == 201
    checkin_id = r.json()["id"]

    # 6. Klient dodaje pomiar; wysyła wiadomość.
    r = client.post(f"/api/clients/{new_id}/measurements", headers=hn, json={
        "kind": "weight", "value": 78.5, "unit": "kg", "measured_at": "2026-08-18"})
    assert r.status_code == 201
    threads = client.get("/api/threads", headers=hn).json()["threads"]
    thread_id = threads[0]["id"]
    r = client.post(f"/api/threads/{thread_id}/messages", headers=hn,
                    json={"body": "Dzień dobry, pierwszy tydzień za mną!"})
    assert r.status_code == 201

    # 7. Trener: widzi raport, odpowiada, tworzy v2 planu, odpisuje na wiadomość.
    checkins = client.get(f"/api/clients/{new_id}/checkins",
                          headers=hc).json()["checkins"]
    assert checkins[0]["id"] == checkin_id
    r = client.post(f"/api/checkins/{checkin_id}/review", headers=hc,
                    json={"coach_response": "Dobra robota. Dodajemy 1 dzień cardio."})
    assert r.status_code == 200
    r = client.post(f"/api/plans/{plan_id}/versions", headers=hc, json={
        "reason": "Po pierwszym raporcie: dodane cardio",
        "days": [
            {"name": "Całe ciało", "weekday": 2, "exercises": [
                {"name": "Goblet squat", "sets": "3", "reps": "12",
                 "weight": "18 kg"}]},
            {"name": "Cardio", "weekday": 6, "exercises": [
                {"name": "Rower", "sets": "1", "reps": "30 min"}]},
        ],
    })
    assert r.status_code == 201
    coach_threads = client.get("/api/threads", headers=hc).json()["threads"]
    t = next(x for x in coach_threads
             if x["with_user"]["display_name"] == "Nowy Klient")
    assert t["unread"] >= 1
    r = client.post(f"/api/threads/{t['id']}/messages", headers=hc,
                    json={"body": "Odpowiedziałem na raport — sprawdź plan v2!"})
    assert r.status_code == 201

    # 8. Klient widzi v2 i historię v1; trener oznacza płatność.
    versions = client.get(f"/api/plans/{plan_id}/versions",
                          headers=hn).json()["versions"]
    assert [v["version_no"] for v in versions] == [1, 2]
    payments = client.get(f"/api/clients/{new_id}/payments",
                          headers=hc).json()["schedules"]
    rec = payments[0]["records"][0]
    r = client.post(f"/api/payments/records/{rec['id']}/status", headers=hc,
                    json={"status": "PAID"})
    assert r.status_code == 200

    # 9. Klient eksportuje dane; audyt jest spójny.
    export = client.get("/api/me/export", headers=hn).json()
    assert len(export["training_plan_versions"]) == 2
    from dzik_os.hos_bridge import verify_audit_chain

    assert verify_audit_chain() is True


def test_coach_dashboard_flags(seeded):
    hc = login(seeded, COACH)
    clients = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    b = next(c for c in clients if c["display_name"] == "Klient Testowy B")
    assert b["flags"]["payment_overdue"] is True  # seed: zaległa płatność B
    a = next(c for c in clients if c["display_name"] == "Klient Testowy A")
    assert a["consent_active"] is True

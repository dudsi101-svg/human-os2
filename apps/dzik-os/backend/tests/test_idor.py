"""Testy IDOR: podmiana identyfikatorów zasobów między kontami
(checkin_id, plan_id/version_id, thread_id, goal_id, schedule_item_id,
slot_id, schedule_id/record_id płatności, nutrition plan_id), nieaktywna
relacja (PAUSED/ENDED), cofnięta zgoda, konto usunięte, ponowne podpięcie
istniejącego konta oraz centralne logowanie odmów (ACCESS_DENIED)."""

from __future__ import annotations

from conftest import (
    ADMIN,
    CLIENT_A,
    CLIENT_B,
    COACH,
    create_user_with_role,
    get_user_id,
    login,
)

FOREIGN_COACH = {"email": "obcy.trener2@example.com", "password": "ObcyTrener#26x"}


def _foreign_coach(seeded) -> dict:
    create_user_with_role(
        FOREIGN_COACH["email"], FOREIGN_COACH["password"], "Obcy Trener", "COACH"
    )
    return login(seeded, FOREIGN_COACH)


def test_checkin_id_swap(seeded):
    ha, hb, hf = login(seeded, CLIENT_A), login(seeded, CLIENT_B), _foreign_coach(seeded)
    id_a = get_user_id(seeded, ha)
    checkin_id = seeded.get(f"/api/clients/{id_a}/checkins", headers=ha).json()[
        "checkins"
    ][0]["id"]
    # Obcy klient: rewizje cudzego raportu.
    assert seeded.get(f"/api/checkins/{checkin_id}/revisions", headers=hb).status_code == 404
    # Obcy trener: ocena i podsumowanie AI cudzego raportu.
    assert seeded.post(f"/api/checkins/{checkin_id}/review", headers=hf,
                       json={"coach_response": "x"}).status_code == 404
    assert seeded.post(f"/api/checkins/{checkin_id}/ai-summary", headers=hf).status_code == 404
    # Admin: brak roli COACH → 403 zanim dojdzie do zasobu.
    hadm = login(seeded, ADMIN)
    assert seeded.post(f"/api/checkins/{checkin_id}/review", headers=hadm,
                       json={"coach_response": "x"}).status_code == 403


def test_plan_and_version_id_swap(seeded):
    ha, hb, hf = login(seeded, CLIENT_A), login(seeded, CLIENT_B), _foreign_coach(seeded)
    id_a, id_b = get_user_id(seeded, ha), get_user_id(seeded, hb)
    plan = seeded.get(f"/api/clients/{id_a}/plans", headers=ha).json()["plans"][0]
    plan_id, version_id = plan["id"], plan["current_version"]["id"]
    # Historia wersji cudzego planu.
    assert seeded.get(f"/api/plans/{plan_id}/versions", headers=hb).status_code == 404
    assert seeded.get(f"/api/plans/{plan_id}/versions", headers=hf).status_code == 404
    # Nowa wersja cudzego planu (obcy trener).
    assert seeded.post(f"/api/plans/{plan_id}/versions", headers=hf,
                       json={"reason": "przejęcie", "days": []}).status_code == 404
    # Log treningu klienta B wskazujący wersję planu klienta A.
    r = seeded.post(f"/api/clients/{id_b}/workouts", headers=hb, json={
        "plan_version_id": version_id, "day_index": 0,
        "performed_on": "2026-08-17", "status": "DONE", "entries": [],
    })
    assert r.status_code == 404


def test_nutrition_plan_id_swap(seeded):
    ha, hb, hf = login(seeded, CLIENT_A), login(seeded, CLIENT_B), _foreign_coach(seeded)
    id_a = get_user_id(seeded, ha)
    nplan_id = seeded.get(f"/api/clients/{id_a}/nutrition", headers=ha).json()[
        "plans"
    ][0]["id"]
    assert seeded.get(f"/api/nutrition/{nplan_id}/versions", headers=hb).status_code == 404
    assert seeded.post(f"/api/nutrition/{nplan_id}/versions", headers=hf, json={
        "reason": "x", "kcal": 1000, "protein_g": 100, "fat_g": 30, "carbs_g": 100,
        "sections": [], "meals": [],
    }).status_code == 404


def test_thread_id_swap(seeded):
    ha, hb, hf = login(seeded, CLIENT_A), login(seeded, CLIENT_B), _foreign_coach(seeded)
    thread_id = seeded.get("/api/threads", headers=ha).json()["threads"][0]["id"]
    assert seeded.get(f"/api/threads/{thread_id}/messages", headers=hb).status_code == 404
    assert seeded.post(f"/api/threads/{thread_id}/messages", headers=hb,
                       json={"body": "podsłuch"}).status_code == 404
    assert seeded.get(f"/api/threads/{thread_id}/messages", headers=hf).status_code == 404


def test_goal_id_cross_client(seeded):
    """goal_id klienta B podstawiony pod client_id klienta A — trener ma
    dostęp do obu ścieżek osobno, ale krzyżówka identyfikatorów to odmowa."""
    ha, hb, hc = login(seeded, CLIENT_A), login(seeded, CLIENT_B), login(seeded, COACH)
    id_a, id_b = get_user_id(seeded, ha), get_user_id(seeded, hb)
    goal_b = seeded.get(f"/api/clients/{id_b}/goals", headers=hb).json()["goals"][0]["id"]
    r = seeded.post(f"/api/clients/{id_a}/goals/{goal_b}/status", headers=hc,
                    json={"status": "DONE"})
    assert r.status_code == 404
    # Cel klienta B pozostał nietknięty.
    status = seeded.get(f"/api/clients/{id_b}/goals", headers=hb).json()["goals"][0]["status"]
    assert status != "DONE"


def test_schedule_item_cross_client_completion(seeded):
    ha, hb = login(seeded, CLIENT_A), login(seeded, CLIENT_B)
    id_a, id_b = get_user_id(seeded, ha), get_user_id(seeded, hb)
    item_a = seeded.get(f"/api/clients/{id_a}/schedule", headers=ha).json()["items"][0]["id"]
    # Klient B odhacza element harmonogramu klienta A pod własnym client_id.
    r = seeded.post(f"/api/clients/{id_b}/schedule/{item_a}/complete", headers=hb,
                    json={"completed_on": "2026-08-17", "status": "DONE"})
    assert r.status_code == 404
    # Obserwacja klienta B wskazująca element harmonogramu klienta A.
    r = seeded.post(f"/api/clients/{id_b}/observations", headers=hb, json={
        "occurred_on": "2026-08-17", "schedule_item_id": item_a,
        "category": "SAMOPOCZUCIE", "severity": "INFO", "text": "x",
    })
    assert r.status_code == 422


def test_consult_slot_id_swap(seeded):
    hc, ha, hb = login(seeded, COACH), login(seeded, CLIENT_A), login(seeded, CLIENT_B)
    hf = _foreign_coach(seeded)
    slot_id = seeded.post("/api/coach/consult-slots", headers=hc,
                          json={"starts_at": "2030-06-01T10:00"}).json()["id"]
    # Rezerwacja klienta A.
    assert seeded.post(f"/api/consult-slots/{slot_id}/book", headers=ha).status_code == 200
    # Obcy klient nie odwoła cudzej rezerwacji; obcy trener nie odwoła slotu.
    assert seeded.post(f"/api/consult-slots/{slot_id}/unbook", headers=hb).status_code == 404
    assert seeded.post(f"/api/coach/consult-slots/{slot_id}/cancel", headers=hf).status_code == 404
    # Właściwe strony nadal mogą.
    assert seeded.post(f"/api/coach/consult-slots/{slot_id}/cancel", headers=hc).status_code == 200


def test_payment_schedule_and_record_id_swap(seeded):
    ha, hf = login(seeded, CLIENT_A), _foreign_coach(seeded)
    id_a = get_user_id(seeded, ha)
    schedule = seeded.get(f"/api/clients/{id_a}/payments", headers=ha).json()["schedules"][0]
    schedule_id, record_id = schedule["schedule_id"], schedule["records"][0]["id"]
    assert seeded.post(f"/api/payments/schedules/{schedule_id}/records?due_date=2026-09-01",
                       headers=hf).status_code == 404
    assert seeded.post(f"/api/payments/records/{record_id}/status", headers=hf,
                       json={"status": "PAID"}).status_code == 404


def test_paused_and_ended_relationship_block_coach(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    thread_ids = {t["id"] for t in seeded.get("/api/threads", headers=hc).json()["threads"]}
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 200
    for status in ("PAUSED", "ENDED"):
        r = seeded.post(f"/api/coach/clients/{id_a}/relationship-status?status={status}",
                        headers=hc)
        assert r.status_code == 200
        # Dane zdrowotne i płatności niedostępne mimo wcześniejszej zgody.
        assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 404
        assert seeded.get(f"/api/clients/{id_a}/payments", headers=hc).status_code == 404
        # Wątek znika też z listy (podgląd ostatniej wiadomości to treść).
        remaining = {t["id"] for t in seeded.get("/api/threads", headers=hc).json()["threads"]}
        assert remaining < thread_ids
        # Klient nie zarezerwuje konsultacji u trenera bez aktywnej relacji.
        slot = seeded.post("/api/coach/consult-slots", headers=hc,
                           json={"starts_at": "2030-06-01T12:00"}).json()
        assert seeded.post(f"/api/consult-slots/{slot['id']}/book",
                           headers=ha).status_code == 404
        # Powrót do ACTIVE przed kolejną iteracją.
        seeded.post(f"/api/coach/clients/{id_a}/relationship-status?status=ACTIVE",
                    headers=hc)
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 200


def test_revoked_consent_hides_thread_from_coach_list(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    before = {t["with_user"]["id"] for t in seeded.get("/api/threads", headers=hc).json()["threads"]}
    assert id_a in before
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    active = next(c for c in consents
                  if c["revoked_at"] is None and c["category"] == "komunikacja")
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    after = {t["with_user"]["id"] for t in seeded.get("/api/threads", headers=hc).json()["threads"]}
    assert id_a not in after


def test_deleted_account_cuts_all_access(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    file_ids = [p["file_id"] for p in seeded.get(f"/api/clients/{id_a}/photos",
                                                 headers=ha).json()["photos"]]
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE"})
    assert r.status_code == 200
    # Stary token przestaje działać (konto nieaktywne + sesje unieważnione).
    assert seeded.get("/api/me/today", headers=ha).status_code == 401
    # Trener traci dostęp (relacja zakończona, zgody cofnięte).
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 404
    assert seeded.get(f"/api/clients/{id_a}/checkins", headers=hc).status_code == 404
    # Stare linki do plików są martwe.
    for file_id in file_ids:
        assert seeded.get(f"/api/files/{file_id}", headers=hc).status_code == 404


def test_relinking_existing_account_needs_subject_consent(seeded):
    """Podpięcie ISTNIEJĄCEGO konta przez (innego) trenera nie nadaje zgody —
    do czasu nadania jej przez samego klienta trener nie widzi danych."""
    hf = _foreign_coach(seeded)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.post("/api/coach/clients", headers=hf, json={
        "client_email": CLIENT_A["email"], "client_name": "Klient Testowy A",
        "initial_password": "NieUzyte#2026x",
    })
    assert r.status_code == 201
    # Relacja jest, zgody nie ma → dane niedostępne.
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hf).status_code == 404
    clients = seeded.get("/api/coach/clients", headers=hf).json()["clients"]
    me = next(c for c in clients if c["client_id"] == id_a)
    assert me["consent_active"] is False
    # Klient nadaje zgodę osobiście → dostęp działa.
    foreign_id = get_user_id(seeded, hf)
    r = seeded.post("/api/me/consents", headers=ha, json={
        "category": "udostepnianie_trenerowi", "grantee_id": foreign_id,
    })
    assert r.status_code == 201
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hf).status_code == 200


def test_cannot_relink_admin_or_coach_account(seeded):
    hf = _foreign_coach(seeded)
    for email in (ADMIN["email"], COACH["email"]):
        r = seeded.post("/api/coach/clients", headers=hf, json={
            "client_email": email, "client_name": "X",
            "initial_password": "NieUzyte#2026x",
        })
        assert r.status_code == 409, f"{email}: konto nie-klienckie podpięte jako klient"


def test_reactivating_ended_relationship_reuses_row(seeded):
    """Ponowny start współpracy po ENDED nie duplikuje relacji ani wątku."""
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    seeded.post(f"/api/coach/clients/{id_a}/relationship-status?status=ENDED", headers=hc)
    r = seeded.post("/api/coach/clients", headers=hc, json={
        "client_email": CLIENT_A["email"], "client_name": "Klient Testowy A",
        "initial_password": "NieUzyte#2026x",
    })
    assert r.status_code == 201
    clients = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    rows = [c for c in clients if c["client_id"] == id_a]
    assert len(rows) == 1 and rows[0]["relationship_status"] == "ACTIVE"
    # Panel trenera nie wywraca się na zduplikowanym wątku.
    assert seeded.get("/api/coach/dashboard", headers=hc).status_code == 200


def test_access_denied_is_audited_without_health_data(seeded):
    ha, hb = login(seeded, CLIENT_A), login(seeded, CLIENT_B)
    id_a = get_user_id(seeded, ha)
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hb).status_code == 404
    hadm = login(seeded, ADMIN)
    receipts = seeded.get("/api/admin/receipts", headers=hadm).json()["receipts"]
    denied = [r for r in receipts if r["action"] == "ACCESS_DENIED"]
    assert denied, "odmowa zasobowa nie została zaudytowana"
    # Metadane pokwitowań dla admina nie zawierają wolnego tekstu summary.
    assert all("summary" not in r for r in receipts)
    # Łańcuch audytu pozostaje spójny po zapisie odmowy.
    assert seeded.get("/api/admin/audit/verify", headers=hadm).json()["chain_valid"] is True


def test_plain_401_is_not_audited_as_access_denied(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    # Żądanie bez logowania: 401, bez wpisu ACCESS_DENIED (logowanie
    # zostawia ciasteczko sesji w kliencie testowym — czyścimy je).
    seeded.cookies.clear()
    assert seeded.get(f"/api/clients/{id_a}/profile").status_code == 401
    hadm = login(seeded, ADMIN)
    receipts = seeded.get("/api/admin/receipts", headers=hadm).json()["receipts"]
    assert not [r for r in receipts if r["action"] == "ACCESS_DENIED"]

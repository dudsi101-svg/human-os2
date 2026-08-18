"""Jakość danych raportu tygodniowego (PROMPT 11):

* rozróżnienie stanów odpowiedzi skalowych — brak odpowiedzi / świadoma
  wartość (w tym neutralna 3) / świadome pominięcie / „nie dotyczy",
* idempotencja wysyłki (podwójne kliknięcie, retry po przerwaniu sieci),
* jawnie CZĘŚCIOWY raport przy brakujących zdjęciach + dokończenie,
* typ ujęcia i kolejność zdjęć,
* korekta = nowa rewizja z historią, oznaczona w API,
* zdjęcia nie wyciekają do audytu (payloady zdarzeń bez id/nazw plików).
"""

from __future__ import annotations

import io

from conftest import CLIENT_A, CLIENT_B, COACH, get_user_id, login, make_png

# Tydzień poza kolizją z seedem i innymi testami checkinów.
WEEK = "2026-09-14"


def _upload_png(client, headers, name="foto.png"):
    r = client.post("/api/files", headers=headers, files={
        "file": (name, io.BytesIO(make_png()), "image/png")})
    assert r.status_code == 201
    return r.json()["id"]


def _payload(**overrides):
    payload = {"week_start": WEEK, "weight_kg": 84.0}
    payload.update(overrides)
    return payload


def _get_checkin(client, headers, client_id, checkin_id):
    rows = client.get(f"/api/clients/{client_id}/checkins",
                      headers=headers).json()["checkins"]
    return next(c for c in rows if c["id"] == checkin_id)


# --- Stany odpowiedzi skalowych ---------------------------------------------

def test_scale_states_distinguish_four_answer_kinds(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.post("/api/checkins", headers=ha, json=_payload(
        energy=3,          # świadomie wybrana wartość NEUTRALNA
        recovery=4,        # świadomie wybrana wartość
        sleep=None,        # świadome pominięcie
        hunger=None,       # nie dotyczy
        # stress: brak klucza w scale_states = brak odpowiedzi
        scale_states={
            "energy": "ANSWERED",
            "recovery": "ANSWERED",
            "sleep": "SKIPPED",
            "hunger": "NOT_APPLICABLE",
            "diet_adherence": "SKIPPED",
        },
    ))
    assert r.status_code == 201
    row = _get_checkin(seeded, ha, id_a, r.json()["id"])
    payload = row["payload"]
    states = payload["scale_states"]
    # Neutralne 3 to jawna odpowiedź, nie „domyślna wartość formularza".
    assert payload["energy"] == 3 and states["energy"] == "ANSWERED"
    assert payload["sleep"] is None and states["sleep"] == "SKIPPED"
    assert payload["hunger"] is None and states["hunger"] == "NOT_APPLICABLE"
    # Brak odpowiedzi: wartość pusta i klucz nieobecny w scale_states.
    assert payload["stress"] is None and "stress" not in states
    assert row["scales_declared"] is True


def test_scale_states_validation_rules(seeded):
    ha = login(seeded, CLIENT_A)

    def submit(**kw):
        return seeded.post("/api/checkins", headers=ha, json=_payload(**kw))

    # ANSWERED bez wartości.
    assert submit(scale_states={"energy": "ANSWERED"}).status_code == 422
    # Pominięte pytanie z wartością.
    assert submit(energy=4, scale_states={"energy": "SKIPPED"}).status_code == 422
    # Wartość bez zadeklarowanego stanu (przy podanym scale_states).
    assert submit(energy=4, sleep=3,
                  scale_states={"energy": "ANSWERED"}).status_code == 422
    # Nieznane pytanie / nieznany stan.
    assert submit(scale_states={"mood": "ANSWERED"}).status_code == 422
    assert submit(energy=4, scale_states={"energy": "MAYBE"}).status_code == 422


def test_legacy_submission_without_states_still_works(seeded):
    """Stare klienty (bez scale_states) wysyłają wartości jak dotychczas —
    ale API jawnie oznacza taki raport jako niezadeklarowany (mniej
    wiarygodny: wartości mogły zostać na domyślnym 3/5)."""
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.post("/api/checkins", headers=ha, json=_payload(
        energy=3, sleep=3, stress=3))
    assert r.status_code == 201
    row = _get_checkin(seeded, ha, id_a, r.json()["id"])
    assert row["scales_declared"] is False


# --- Idempotencja wysyłki ---------------------------------------------------

def test_double_submit_with_same_key_returns_stored_result(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    body = _payload(energy=4, scale_states={"energy": "ANSWERED"},
                    idempotency_key="idem-raport-2026-09-14-abc")
    first = seeded.post("/api/checkins", headers=ha, json=body)
    assert first.status_code == 201
    # Powtórka (double-click / retry po utracie odpowiedzi): ten sam wynik,
    # bez nowej rewizji.
    second = seeded.post("/api/checkins", headers=ha, json=body)
    assert second.json() == first.json()
    row = _get_checkin(seeded, ha, id_a, first.json()["id"])
    assert row["revision"] == 1 and row["corrected"] is False
    revisions = seeded.get(f"/api/checkins/{first.json()['id']}/revisions",
                           headers=ha).json()["revisions"]
    assert revisions == []
    # Ten sam klucz z INNĄ treścią = jawny konflikt.
    changed = dict(body, weight_kg=90.0)
    assert seeded.post("/api/checkins", headers=ha, json=changed).status_code == 409
    # Świadoma korekta z nowym kluczem tworzy rewizję 2.
    corrected = dict(body, weight_kg=83.5,
                     idempotency_key="idem-raport-2026-09-14-def")
    r = seeded.post("/api/checkins", headers=ha, json=corrected)
    assert r.status_code == 201 and r.json()["revision"] == 2


def test_idempotency_keys_are_scoped_per_user(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    key = "idem-wspolny-klucz-123"
    ra = seeded.post("/api/checkins", headers=ha,
                     json=_payload(idempotency_key=key))
    rb = seeded.post("/api/checkins", headers=hb,
                     json=_payload(weight_kg=70.0, idempotency_key=key))
    # Inna treść pod tym samym kluczem u INNEGO użytkownika nie koliduje.
    assert ra.status_code == 201 and rb.status_code == 201
    assert ra.json()["id"] != rb.json()["id"]


# --- Częściowy raport (zdjęcia) ---------------------------------------------

def test_partial_photos_then_completion(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.post("/api/checkins", headers=ha,
                    json=_payload(photos_expected=2))
    assert r.status_code == 201
    data = r.json()
    checkin_id = data["id"]
    # Raport bez zapisanych zdjęć przy deklaracji 2 jest jawnie CZĘŚCIOWY.
    assert data["photos_expected"] == 2 and data["photos_complete"] is False
    row = _get_checkin(seeded, ha, id_a, checkin_id)
    assert row["photos_complete"] is False and row["photos_attached"] == 0

    # Dopięcie pierwszego zdjęcia (zaraz po udanym uploadzie) — stan trwały.
    f1 = _upload_png(seeded, ha)
    r = seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                    json={"photos": [{"file_id": f1, "pose": "PRZOD"}]})
    assert r.status_code == 200
    assert r.json()["photos_attached"] == 1
    assert r.json()["photos_complete"] is False

    # Ponowne dopięcie tego samego pliku (retry) nie mnoży wierszy.
    r = seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                    json={"photos": [{"file_id": f1, "pose": "PRZOD"}]})
    assert r.json()["photos_attached"] == 1

    f2 = _upload_png(seeded, ha)
    r = seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                    json={"photos": [{"file_id": f2, "pose": "BOK"}]})
    assert r.json()["photos_complete"] is True
    row = _get_checkin(seeded, ha, id_a, checkin_id)
    assert row["photos_attached"] == 2 and row["photos_complete"] is True


def test_finish_partial_report_without_missing_photos(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/checkins", headers=ha,
                    json=_payload(photos_expected=3))
    checkin_id = r.json()["id"]
    f1 = _upload_png(seeded, ha)
    seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                json={"photos": [{"file_id": f1}]})
    # Świadome zamknięcie deklaracji bez brakujących plików.
    r = seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                    json={"photos": [], "set_expected": 1})
    assert r.status_code == 200 and r.json()["photos_complete"] is True
    # Deklaracja poniżej liczby już zapisanych — odmowa.
    r = seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                    json={"photos": [], "set_expected": 0})
    assert r.status_code == 422


def test_attach_denied_after_review_foreign_and_other_client(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    hc = login(seeded, COACH)
    r = seeded.post("/api/checkins", headers=ha, json=_payload())
    checkin_id = r.json()["id"]
    # Cudzy raport = 404 (bez ujawniania istnienia).
    fb = _upload_png(seeded, hb)
    r = seeded.post(f"/api/checkins/{checkin_id}/photos", headers=hb,
                    json={"photos": [{"file_id": fb}]})
    assert r.status_code == 404
    # Cudzy plik = 422 (require_attachable_file).
    r = seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                    json={"photos": [{"file_id": fb}]})
    assert r.status_code == 422
    # Po ocenie trenera zdjęcia raportu są zamrożone.
    seeded.post(f"/api/checkins/{checkin_id}/review", headers=hc,
                json={"coach_response": "Dzięki za raport"})
    f1 = _upload_png(seeded, ha)
    r = seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                    json={"photos": [{"file_id": f1}]})
    assert r.status_code == 409


def test_photo_pose_and_client_chosen_order(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    f_front = _upload_png(seeded, ha, "przod.png")
    f_side = _upload_png(seeded, ha, "bok.png")
    r = seeded.post("/api/checkins", headers=ha, json=_payload(photos=[
        {"file_id": f_front, "pose": "PRZOD", "position": 1},
        {"file_id": f_side, "pose": "BOK", "position": 0},
    ]))
    assert r.status_code == 201
    row = _get_checkin(seeded, ha, id_a, r.json()["id"])
    assert [p["pose"] for p in row["photos"]] == ["BOK", "PRZOD"]
    assert [p["file_id"] for p in row["photos"]] == [f_side, f_front]
    photos = seeded.get(f"/api/clients/{id_a}/photos", headers=ha).json()["photos"]
    by_file = {p["file_id"]: p for p in photos}
    assert by_file[f_front]["pose"] == "PRZOD"
    assert by_file[f_side]["pose"] == "BOK"


# --- Korekta z historią + oznaczenia jakości --------------------------------

def test_correction_creates_revision_and_is_marked(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.post("/api/checkins", headers=ha, json=_payload(
        energy=2, scale_states={"energy": "ANSWERED"}))
    checkin_id = r.json()["id"]
    r = seeded.post("/api/checkins", headers=ha, json=_payload(
        energy=4, scale_states={"energy": "ANSWERED"}))
    assert r.json()["revision"] == 2
    row = _get_checkin(seeded, ha, id_a, checkin_id)
    assert row["corrected"] is True and row["revision"] == 2
    revisions = seeded.get(f"/api/checkins/{checkin_id}/revisions",
                           headers=ha).json()["revisions"]
    assert len(revisions) == 1
    assert revisions[0]["payload"]["energy"] == 2


def test_monitoring_marks_undeclared_wellbeing_points(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    seeded.post("/api/checkins", headers=ha, json=_payload(
        energy=4, scale_states={"energy": "ANSWERED", "sleep": "SKIPPED"}))
    data = seeded.get(f"/api/clients/{id_a}/monitoring?days=60",
                      headers=ha).json()
    energy = data["wellbeing_series"]["energy"]
    # Punkt z nowego raportu: świadomie zadeklarowany.
    new_points = [p for p in energy if p["date"] == WEEK]
    assert new_points and all(p["declared"] is True for p in new_points)
    # Punkty z raportu seedu (sprzed rozróżniania stanów): nieoznaczone
    # jako zadeklarowane — UI pokazuje je jako mniej wiarygodne.
    old_points = [p for p in energy if p["date"] != WEEK]
    assert old_points and all(p["declared"] is False for p in old_points)
    # Pominięte pytanie nie generuje punktu (nigdy nie jest interpolowane).
    assert all(p["date"] != WEEK for p in data["wellbeing_series"].get("sleep", []))


# --- Zdjęcia poza audytem/powiadomieniami -----------------------------------

def test_photo_ids_and_names_never_reach_audit_events(seeded):
    import json as jsonlib

    from dzik_os.hos_bridge import event_store

    ha = login(seeded, CLIENT_A)
    fid = _upload_png(seeded, ha, "sylwetka-prywatna.png")
    r = seeded.post("/api/checkins", headers=ha, json=_payload(
        photos=[{"file_id": fid, "pose": "PRZOD"}]))
    assert r.status_code == 201
    checkin_id = r.json()["id"]
    f2 = _upload_png(seeded, ha, "sylwetka-druga.png")
    seeded.post(f"/api/checkins/{checkin_id}/photos", headers=ha,
                json={"photos": [{"file_id": f2, "pose": "TYL"}]})
    events = event_store().all()
    checkin_events = [e for e in events
                      if e["event_type"].startswith("CHECKIN")]
    assert checkin_events
    dumped = jsonlib.dumps(events, ensure_ascii=False)
    # Ani identyfikatory plików, ani nazwy zdjęć nie trafiają do łańcucha
    # audytu — wyłącznie liczniki stanu.
    assert fid not in dumped and f2 not in dumped
    assert "sylwetka" not in dumped
    attach_events = [e for e in events
                     if e["event_type"] == "CHECKIN_PHOTOS_ATTACHED"]
    assert attach_events
    assert attach_events[-1]["payload"]["photos_attached"] == 2

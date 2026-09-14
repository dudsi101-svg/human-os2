"""Cardio z suwakami (0.73.0): API `POST /api/clients/{id}/cardio/podglad`
(propose-only, bramka zdrowotna, prefill wyłącznie przy dostępie do domeny
zdrowotnej), pozycja `kind: "cardio"` w wersji planu → ślad `H_CARDIO`
w tej samej transakcji, „Dlaczego?” u klienta, szkic → publikacja zachowuje
`cardio.goal_mix`, dziennik cardio bez serii (rekordy pomijają), eksport
i usunięcie konta, IDOR, klient → 403."""

from __future__ import annotations

import json

from conftest import (
    CLIENT_A,
    CLIENT_B,
    COACH,
    create_user_with_role,
    get_user_id,
    login,
)

from dzik_os.db import SessionLocal
from dzik_os.models import Measurement, WiedzaSlad, WorkoutEntry, new_id

ROWNO = {"redukcja": 0.34, "wydolnosc": 0.33, "regeneracja": 0.33}
ZDROWIE_OK = {"current_red_flag": False, "unexplained_exertional_symptoms": False, "known_condition": False,
              "acute_injury_or_surgery": False, "pregnancy_postpartum": False, "active_rehabilitation": False,
              "hr_medication": False}


def _podglad(c, h, cid, **extra):
    body = {"goal_mix": ROWNO, "level": "SREDNIOZAAWANSOWANY", "machines": ["rowerek", "wioslarz"],
            "health": ZDROWIE_OK, **extra}
    return c.post(f"/api/clients/{cid}/cardio/podglad", headers=h, json=body)


def _plan_a(c, h, cid):
    plans = c.get(f"/api/clients/{cid}/plans", headers=h).json()["plans"]
    return next(p for p in plans if p["status"] == "ACTIVE")


def _pozycja_cardio(wynik, machines=("rowerek",)):
    return {"name": "Cardio — rowerek", "kind": "cardio",
            "cardio": {"goal_mix": ROWNO, "level": "SREDNIOZAAWANSOWANY", "machines": list(machines),
                       "prescription": wynik["prescription"], "trace": wynik["trace"],
                       "model_version": wynik["model_version"]}}


# --- bramka i propose-only ---------------------------------------------------

def test_podglad_liczy_bez_zapisu_i_prefill_z_pomiarow(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    with SessionLocal() as db:
        db.add(Measurement(id=new_id("MSR"), client_id=cid, kind="resting_hr", value=58, unit="bpm",
                           measured_at="2026-09-10", created_by=cid))
        db.commit()
    r = _podglad(seeded, hc, cid, age=35)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["status"] == "ready" and b["prescription"]["hr_pct_range"] == [68, 78]
    assert b["inputs"]["resting_hr"] == 58 and b["inputs"]["health_access"] is True
    assert b["prescription"]["hrr_used"] is True and b["prescription"]["hr_bpm_range"]
    assert b["trace"]["rule_id"] == "H_CARDIO" and b["model_version"] == "cardio_model_v1"
    assert [p["machine"] for p in b["prescription"]["machine_params"]] == ["rowerek", "wioslarz"]
    # Nic nie zapisane: plan klienta bez zmian, brak śladu.
    with SessionLocal() as db:
        assert db.query(WiedzaSlad).filter_by(owner_id=cid, target_type="cardio_prescription",
                                              rule_id="H_CARDIO").count() == 1  # tylko seed (dzień C v2)
    pre = seeded.get(f"/api/clients/{cid}/cardio/prefill", headers=hc).json()
    assert pre["resting_hr"] == 58 and pre["health_access"] is True
    kat = seeded.get("/api/cardio/katalog", headers=ha).json()
    assert [g["id"] for g in kat["goals"]] == ["redukcja", "wydolnosc", "regeneracja"]
    assert "hr_medication" in kat["health_questions"] and len(kat["machines"]) == 5


def test_bramka_urgent_stop_needs_input_needs_review_i_leki(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    r = _podglad(seeded, hc, cid, health={**ZDROWIE_OK, "current_red_flag": True})
    assert r.status_code == 200 and r.json()["status"] == "urgent_stop" and r.json()["prescription"] is None
    assert r.json()["issues"][0]["code"] == "URGENT_STOP"
    # Brak odpowiedzi = pytania, nigdy zielone.
    r = _podglad(seeded, hc, cid, health={})
    assert r.json()["status"] == "needs_input" and r.json()["prescription"] is None
    assert any("beta-blokery" in q for q in r.json()["questions"])
    r = _podglad(seeded, hc, cid, health={k: v for k, v in ZDROWIE_OK.items() if k != "hr_medication"})
    assert r.json()["status"] == "needs_input" and "leki" in r.json()["issues"][0]["message"]
    # Choroba bez ustalonego poziomu → propozycja z ostrzeżeniem „tylko trener”.
    r = _podglad(seeded, hc, cid, health={**ZDROWIE_OK, "known_condition": True, "restrictions_understood": True})
    assert r.json()["status"] == "needs_review" and r.json()["prescription"] is not None
    assert any(i["code"] == "CARDIO_COACH_ONLY" for i in r.json()["issues"])
    # Leki wpływające na tętno → bez ud./min.
    r = _podglad(seeded, hc, cid, age=40, health={**ZDROWIE_OK, "hr_medication": True})
    assert r.json()["status"] == "ready" and r.json()["prescription"]["hr_bpm_range"] is None
    assert r.json()["inputs"]["hr_mode"] == "rpe_only"
    # Blok zdrowotny nie trafia do odpowiedzi ani wejść.
    zrzut = json.dumps(r.json()["inputs"]) + json.dumps(r.json()["trace"]) + json.dumps(r.json()["prescription"])
    assert "red_flag" not in zrzut and "known_condition" not in zrzut and "hr_medication" not in zrzut


def test_suma_wag_422_i_dostep(seeded):
    hc, ha, hb = login(seeded, COACH), login(seeded, CLIENT_A), login(seeded, CLIENT_B)
    cid = get_user_id(seeded, ha)
    r = _podglad(seeded, hc, cid, goal_mix={"redukcja": 0.5, "wydolnosc": 0.5, "regeneracja": 0.5})
    assert r.status_code == 422 and "sumować" in r.json()["detail"]
    # Klient nie liczy propozycji (nawet swojej).
    assert _podglad(seeded, ha, cid).status_code == 403
    assert seeded.get(f"/api/clients/{cid}/cardio/prefill", headers=hb).status_code == 403
    # Trener bez relacji → 404.
    create_user_with_role("obcy.trener@example.com", "ObcyTrener#2026", "Obcy", "COACH")
    ho = login(seeded, {"email": "obcy.trener@example.com", "password": "ObcyTrener#2026"})
    assert _podglad(seeded, ho, cid).status_code == 404
    assert seeded.get(f"/api/clients/{cid}/cardio/prefill", headers=ho).status_code == 404


def test_bez_zgody_zdrowotnej_prefill_pusty_a_propozycja_w_trybie_rpe(seeded):
    """Klient cofa zgodę na dane zdrowotne: trener nadal ma domenę treningową
    (propozycja liczy się), ale wiek/tętno spoczynkowe NIE są czytane —
    silnik działa bez ud./min, a odpowiedź mówi `health_access: false`."""
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    zgody = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    zdrowie = next(c for c in zgody if c["category"] == "dane_zdrowotne" and c["revoked_at"] is None
                   and c["denied_at"] is None)
    assert seeded.post(f"/api/me/consents/{zdrowie['id']}/revoke", headers=ha).status_code == 200
    r = seeded.get(f"/api/clients/{cid}/cardio/prefill", headers=hc)
    assert r.status_code == 200 and r.json()["health_access"] is False and r.json()["age"] is None
    r2 = _podglad(seeded, hc, cid)
    assert r2.status_code == 200 and r2.json()["status"] == "ready"
    assert r2.json()["prescription"]["hr_bpm_range"] is None and r2.json()["inputs"]["health_access"] is False
    # Ręcznie podany wiek nadal działa (trener wpisał go z rozmowy).
    r3 = _podglad(seeded, hc, cid, age=45)
    assert r3.json()["prescription"]["hr_bpm_range"] is not None


# --- pozycja w planie, ślad, „Dlaczego?” --------------------------------------

def test_wersja_planu_z_cardio_zapisuje_slad_h_cardio_i_dlaczego_dla_klienta(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_a(seeded, ha, cid)
    wynik = _podglad(seeded, hc, cid, age=35).json()
    dni = [{"name": "Dzień cardio", "exercises": [_pozycja_cardio(wynik, ("rowerek", "wioslarz"))]}]
    r = seeded.post(f"/api/plans/{plan['id']}/versions", headers=hc, json={"reason": "Dokładam cardio", "days": dni})
    assert r.status_code == 201, r.text
    nowa = r.json()["version_no"]
    with SessionLocal() as db:
        s = db.query(WiedzaSlad).filter_by(plan_id=plan["id"], plan_revision=nowa, target_type="cardio_prescription").one()
        assert s.rule_id == "H_CARDIO" and s.target_id == "d0:e0" and s.decision_origin == "engine"
        fakty = {f["key"]: f for f in json.loads(s.facts_json)}
        assert fakty["goal_redukcja"]["value"] == 34 and fakty["hrmax_source"]["value"] == "tanaka"
        assert "age" not in fakty and "resting_hr" not in fakty
    # Klient widzi pozycję i wyjaśnienie.
    plan2 = _plan_a(seeded, ha, cid)
    ex = plan2["current_version"]["content"]["days"][0]["exercises"][0]
    assert ex["kind"] == "cardio" and ex["cardio"]["machines"] == ["rowerek", "wioslarz"]
    assert ex["cardio"]["prescription"]["duration_min"] == 35
    assert "sets" in ex and "kind" in ex  # zwykłe pola zostają
    r = seeded.post("/api/wiedza/wyjasnij", headers=ha, json={
        "plan_kind": "training", "plan_id": plan["id"], "plan_revision": nowa,
        "target_type": "cardio_prescription", "target_id": "d0:e0", "tryb": "current"})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["status"] == "explained"
    assert "35 min" in b["paragraphs"][0] and "68–78 %" in b["paragraphs"][0]
    assert "Redukcja 34 %" in b["paragraphs"][1] and "nie wynik badania" in b["paragraphs"][1]
    # Wersja bez cardio nie zostawia nowych klucz w pozycjach (bajt w bajt jak dotąd).
    r = seeded.post(f"/api/plans/{plan['id']}/versions", headers=hc,
                    json={"reason": "Bez cardio", "days": [{"name": "A", "exercises": [{"name": "Przysiad", "sets": "3"}]}]})
    ex2 = _plan_a(seeded, ha, cid)["current_version"]["content"]["days"][0]["exercises"][0]
    assert "kind" not in ex2 and "cardio" not in ex2 and "block" not in ex2


def test_walidacja_pozycji_cardio_i_bloku(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_a(seeded, ha, cid)
    zle = [
        {"name": "x", "kind": "cardio"},  # bez obiektu cardio
        {"name": "x", "kind": "warmup_block"},  # bez migawki bloku
        {"name": "x", "kind": "cardio", "cardio": {"goal_mix": {"redukcja": 1, "wydolnosc": 1, "regeneracja": 0},
                                                   "level": "POCZATKUJACY", "machines": ["rowerek"], "prescription": {}}},
        {"name": "x", "kind": "cardio", "cardio": {"goal_mix": ROWNO, "level": "POCZATKUJACY",
                                                   "machines": ["hulajnoga"], "prescription": {}}},
        {"name": "x", "kind": "taniec"},
    ]
    for ex in zle:
        r = seeded.post(f"/api/plans/{plan['id']}/versions", headers=hc,
                        json={"reason": "zła", "days": [{"name": "D", "exercises": [ex]}]})
        assert r.status_code == 422, ex


def test_szkic_publikacja_zachowuje_goal_mix_i_slad(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_a(seeded, ha, cid)
    wynik = _podglad(seeded, hc, cid, age=35).json()
    r = seeded.post(f"/api/szkice/plan/training/{plan['id']}", headers=hc)
    assert r.status_code in (200, 201), r.text
    szkic = r.json()
    dzien = szkic["content"]["days"][0]
    r = seeded.patch(f"/api/szkice/{szkic['id']}", headers=hc, json={
        "revision": szkic["revision"],
        "operations": [{"op": "add", "collection": "exercises", "parent_id": dzien["id"],
                        "item": _pozycja_cardio(wynik)}]})
    assert r.status_code == 200, r.text
    szkic = r.json()
    # Pole `cardio` przeszło przez allow-list szkicu (elementy.py) — nie zniknęło po cichu.
    assert szkic["content"]["days"][0]["exercises"][-1]["cardio"]["goal_mix"] == ROWNO
    r = seeded.post(f"/api/szkice/{szkic['id']}/publikuj", headers=hc,
                    json={"revision": szkic["revision"], "base_version_no": szkic["base_version_no"],
                          "note": "Cardio z suwaków", "idempotency_key": new_id("IDM")})
    assert r.status_code == 200, r.text
    nowa = r.json()["version_no"]
    ex = _plan_a(seeded, ha, cid)["current_version"]["content"]["days"][0]["exercises"][-1]
    assert ex["kind"] == "cardio" and ex["cardio"]["goal_mix"] == ROWNO
    with SessionLocal() as db:
        # Dwie pozycje cardio w wersji: dołożona w dniu 0 (po dwóch siłowych) i seedowa w dniu C.
        cele = {s.target_id for s in db.query(WiedzaSlad).filter_by(plan_id=plan["id"], plan_revision=nowa,
                                                                    target_type="cardio_prescription").all()}
        assert cele == {"d0:e2", "d2:e3"}


# --- dziennik ----------------------------------------------------------------

def test_dziennik_cardio_bez_serii_eksport_i_usuniecie(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_a(seeded, ha, cid)
    r = seeded.post(f"/api/clients/{cid}/workouts", headers=ha, json={
        "plan_version_id": plan["current_version"]["id"], "day_index": 2, "performed_on": "2026-09-14",
        "status": "DONE", "entries": [
            {"exercise_index": 3, "exercise_name": "Cardio — rowerek", "duration_min": 25, "avg_hr": 138,
             "rpe": 6, "distance_km": 9.5, "machine": "wioslarz"}]})
    assert r.status_code == 201, r.text
    assert r.json()["new_records"] == 0  # cardio nie tworzy rekordów kg
    w = seeded.get(f"/api/clients/{cid}/workouts", headers=ha).json()["workouts"][0]
    e = w["entries"][0]
    assert e["duration_min"] == 25 and e["avg_hr"] == 138 and e["rpe"] == 6 and e["machine"] == "wioslarz"
    assert e["sets"] == [] and e["distance_km"] == 9.5
    for zle in ({"rpe": 11}, {"machine": "hulajnoga"}, {"duration_min": 0}, {"avg_hr": 300}):
        r = seeded.post(f"/api/clients/{cid}/workouts", headers=ha, json={
            "plan_version_id": plan["current_version"]["id"], "day_index": 2, "performed_on": "2026-09-13",
            "entries": [{"exercise_index": 3, "exercise_name": "Cardio", **zle}]})
        assert r.status_code == 422, zle
    ex = seeded.get("/api/me/export", headers=ha).json()
    assert ex["export_version"] == "2.1"
    wpis = next(x for x in ex["workout_entries"] if x["machine"] == "wioslarz")
    assert wpis["duration_min"] == 25 and wpis["avg_hr"] == 138
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE"})
    assert r.status_code in (200, 202, 204), r.text
    with SessionLocal() as db:
        wpisy = db.query(WorkoutEntry).filter_by(machine="wioslarz").all()
        assert all(x.comment is None for x in wpisy)


def test_dziennik_cudzego_klienta_404(seeded):
    ha, hb = login(seeded, CLIENT_A), login(seeded, CLIENT_B)
    cid_a = get_user_id(seeded, ha)
    plan = _plan_a(seeded, ha, cid_a)
    r = seeded.post(f"/api/clients/{cid_a}/workouts", headers=hb, json={
        "plan_version_id": plan["current_version"]["id"], "day_index": 2, "performed_on": "2026-09-14",
        "entries": [{"exercise_index": 3, "exercise_name": "Cardio", "duration_min": 20, "rpe": 5}]})
    assert r.status_code == 404


def test_tetno_srednie_maskowane_dla_trenera_bez_zgody_zdrowotnej(seeded):
    """`avg_hr` to dana zdrowotna: po cofnięciu zgody na dane zdrowotne trener nadal
    widzi wpis cardio (czas, RPE, urządzenie — domena treningowa), ale bez tętna."""
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_a(seeded, ha, cid)
    r = seeded.post(f"/api/clients/{cid}/workouts", headers=ha, json={
        "plan_version_id": plan["current_version"]["id"], "day_index": 2, "performed_on": "2026-09-14",
        "entries": [{"exercise_index": 3, "exercise_name": "Cardio", "duration_min": 20, "avg_hr": 140, "rpe": 5,
                     "machine": "rowerek"}]})
    assert r.status_code == 201
    wpis = seeded.get(f"/api/clients/{cid}/workouts", headers=hc).json()["workouts"][0]["entries"][0]
    assert wpis["avg_hr"] == 140  # zgoda zdrowotna z seedu
    zgody = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    zdrowie = next(c for c in zgody if c["category"] == "dane_zdrowotne" and c["revoked_at"] is None
                   and c["denied_at"] is None)
    assert seeded.post(f"/api/me/consents/{zdrowie['id']}/revoke", headers=ha).status_code == 200
    wpis = seeded.get(f"/api/clients/{cid}/workouts", headers=hc).json()["workouts"][0]["entries"][0]
    assert wpis["avg_hr"] is None and wpis["duration_min"] == 20 and wpis["machine"] == "rowerek"
    # Klient nadal widzi swoje tętno.
    assert seeded.get(f"/api/clients/{cid}/workouts", headers=ha).json()["workouts"][0]["entries"][0]["avg_hr"] == 140

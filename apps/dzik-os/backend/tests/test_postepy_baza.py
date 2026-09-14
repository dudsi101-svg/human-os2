"""Postępy — warstwa bazy (etapy 2–3): przeliczanie przy zapisie sesji,
powiadomienie zbiorcze, jednostki i rozgrzewka, backfill idempotentny."""

from __future__ import annotations

from datetime import timedelta

from conftest import CLIENT_A, get_user_id, login

from dzik_os import recalculate_progress
from dzik_os.dates import local_today
from dzik_os.db import SessionLocal, db_session
from dzik_os.models import ExerciseRecord, TrainingWeekAggregate
from dzik_os.postepy import serwis


def _plan_version(c, ha, id_a):
    plans = c.get(f"/api/clients/{id_a}/plans", headers=ha).json()["plans"]
    versions = c.get(f"/api/plans/{plans[0]['id']}/versions", headers=ha).json()["versions"]
    return versions[-1]["id"]


def _log(c, ha, id_a, pv, day, sets, name="Martwy ciąg", result=None):
    r = c.post(f"/api/clients/{id_a}/workouts", headers=ha, json={
        "plan_version_id": pv, "day_index": 0, "performed_on": day.isoformat(), "status": "DONE",
        "entries": [{"exercise_index": 0, "exercise_name": name, "result": result, "sets": sets}],
    })
    assert r.status_code == 201, r.text
    return r.json()


def _rekordy(id_a, typ=None, klucz="martwy ciąg"):
    with SessionLocal() as db:
        q = db.query(ExerciseRecord).filter_by(client_id=id_a, exercise_key=klucz)
        if typ:
            q = q.filter_by(record_type=typ)
        return [(r.value, r.previous_value, r.achieved_on, r.superseded_at, r.equaled_on) for r in q.order_by(ExerciseRecord.achieved_on).all()]


def test_zapis_sesji_przelicza_rekordy_jednostki_i_rozgrzewke_oraz_jedno_powiadomienie(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    pv = _plan_version(seeded, ha, id_a)
    dzis = local_today()
    # Sesja 1: punkt odniesienia — zero rekordów, zero powiadomień.
    r1 = _log(seeded, ha, id_a, pv, dzis - timedelta(days=14), [{"weight_kg": 100, "reps": 5}])
    assert r1["new_records"] == 0 and _rekordy(id_a) == []
    # Sesja 2: 242,5 lb = 110 kg (normalizacja przy zapisie) + seria rozgrzewkowa 150 kg (ignorowana).
    r2 = _log(seeded, ha, id_a, pv, dzis - timedelta(days=7),
              [{"weight_kg": 150, "reps": 1, "warmup": True}, {"weight_kg": 242.5, "reps": 5, "unit": "lb"}])
    assert r2["new_records"] == 4  # WEIGHT, SET_VOLUME, SESSION_VOLUME, E1RM
    weight = _rekordy(id_a, "WEIGHT")
    assert weight == [(110.0, 100.0, (dzis - timedelta(days=7)).isoformat(), None, None)]
    workouts = seeded.get(f"/api/clients/{id_a}/workouts", headers=ha).json()["workouts"]
    sets = next(w for w in workouts if w["performed_on"] == (dzis - timedelta(days=7)).isoformat())["entries"][0]["sets"]
    # Seria robocza bez klucza `warmup` (kształt sprzed 0.66.0), rozgrzewka z `warmup: true`.
    assert sets[1] == {"weight_kg": 110.0, "reps": 5} and sets[0]["warmup"] is True
    # Jedno zbiorcze powiadomienie na sesję, tylko w aplikacji (bez push/e-mail).
    powiadomienia = [n for n in seeded.get("/api/notifications", headers=ha).json()["notifications"] if n["category"] == "REKORD"]
    assert len(powiadomienia) == 1 and "4 nowe rekordy" in powiadomienia[0]["title"]
    with SessionLocal() as db:
        from dzik_os.models import Notification
        n = db.query(Notification).filter_by(user_id=id_a, category="REKORD").one()
        assert n.channels == "center"
    # Sesja 3: wyrównanie 110 kg — bez nowego wpisu, bez powiadomienia; `equaled_on` ustawione.
    r3 = _log(seeded, ha, id_a, pv, dzis, [{"weight_kg": 110, "reps": 5}])
    assert r3["new_records"] == 0
    assert _rekordy(id_a, "WEIGHT")[0][4] == dzis.isoformat()
    assert len([n for n in seeded.get("/api/notifications", headers=ha).json()["notifications"] if n["category"] == "REKORD"]) == 1
    # Agregat tygodnia: tonaż = suma ciężar × powtórzenia serii ROBOCZYCH sesji tego tygodnia
    # (rozgrzewka 150 kg pominięta) — w tym tygodniu mogą być też sesje z seedu.
    tydz = serwis.poniedzialek(dzis - timedelta(days=7))
    w_tygodniu = [w for w in workouts if tydz <= local_today().fromisoformat(w["performed_on"]) < tydz + timedelta(days=7)]
    oczekiwany = sum(s["weight_kg"] * s["reps"] for w in w_tygodniu for e in w["entries"] for s in e["sets"] if not s.get("warmup"))
    z_rozgrzewka = oczekiwany + 150
    with SessionLocal() as db:
        agg = db.query(TrainingWeekAggregate).filter_by(client_id=id_a, week_start=tydz.isoformat()).one()
        assert agg.tonnage_kg == round(oczekiwany, 1) != round(z_rozgrzewka, 1)
        assert agg.sessions_count == len(w_tygodniu) and agg.planned_count >= 0


def test_backfill_dwukrotny_daje_identyczny_stan_i_raportuje_blizniaki(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    pv = _plan_version(seeded, ha, id_a)
    dzis = local_today()
    _log(seeded, ha, id_a, pv, dzis - timedelta(days=3), [{"weight_kg": 60, "reps": 8}], name="Wyciskanie hantli lezac")
    _log(seeded, ha, id_a, pv, dzis - timedelta(days=1), [{"weight_kg": 62.5, "reps": 8}], name="Wyciskanie hantli leżąc")

    def stan():
        with SessionLocal() as db:
            rek = sorted((r.exercise_key, r.record_type, r.value, r.secondary_value, r.set_ref, r.session_id,
                          r.achieved_on, r.previous_value, r.equaled_on, r.superseded_at)
                         for r in db.query(ExerciseRecord).filter_by(client_id=id_a).all())
            agg = sorted((a.week_start, a.sessions_count, a.planned_count, a.tonnage_kg, a.sets_by_group_json, a.session_days_json)
                         for a in db.query(TrainingWeekAggregate).filter_by(client_id=id_a).all())
            return rek, agg

    raport1 = recalculate_progress.przelicz(id_a)
    s1 = stan()
    raport2 = recalculate_progress.przelicz(id_a)
    s2 = stan()
    assert s1 == s2 and s1[0] and s1[1]
    assert raport1[0]["cwiczenia"] == raport2[0]["cwiczenia"] >= 3
    # Seed: przysiad 95 → 100 → 105 kg (dwa rekordy WEIGHT, jeden pobity).
    przysiad = [r for r in s1[0] if r[0] == "przysiad ze sztangą" and r[1] == "WEIGHT"]
    assert [(r[2], r[7], r[9] is not None) for r in przysiad] == [(100.0, 95.0, True), (105.0, 100.0, False)]
    # Bliźniaki: „lezac” vs „leżąc” = osobne ćwiczenia, ale zgłoszone do decyzji trenera.
    assert ["wyciskanie hantli lezac", "wyciskanie hantli leżąc"] in raport1[0]["blizniaki"]
    # Wszyscy klienci (bez --client) — działa i obejmuje klienta A.
    wszyscy = recalculate_progress.przelicz(None)
    assert any(r["client_id"] == id_a for r in wszyscy)


def test_usuniecie_serii_w_bazie_cofa_rekord_po_przeliczeniu(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    with db_session() as db:
        serwis.przelicz_klienta(db, id_a)
    assert [r[0] for r in _rekordy(id_a, "WEIGHT", "przysiad ze sztangą")] == [100.0, 105.0]
    # Korekta danych: usunięcie sesji z 105 kg (np. błędny wpis) → przeliczenie cofa rekord.
    from dzik_os.models import WorkoutEntry, WorkoutSession
    with db_session() as db:
        s = (db.query(WorkoutSession).filter_by(client_id=id_a).order_by(WorkoutSession.performed_on.desc()).first())
        db.query(WorkoutEntry).filter_by(session_id=s.id).delete()
        db.delete(s)
    with db_session() as db:
        serwis.przelicz_klienta(db, id_a)
    assert [(r[0], r[3]) for r in _rekordy(id_a, "WEIGHT", "przysiad ze sztangą")] == [(100.0, None)]

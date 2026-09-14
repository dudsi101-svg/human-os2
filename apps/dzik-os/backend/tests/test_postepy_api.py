"""API Postępów (spec §12, testy integracyjne §14): flaga zdrowotna PRZED
implementacją, odmowa obcego trenera, flaga modułu, wydajność."""

from __future__ import annotations

import json
import time
from datetime import timedelta

from conftest import CLIENT_A, COACH, create_user_with_role, get_user_id, login
from sqlalchemy import event

from dzik_os.config import settings
from dzik_os.dates import local_today
from dzik_os.db import db_session, engine
from dzik_os.models import (
    CalorieEstimate,
    CoachClientRelationship,
    ExerciseRecord,
    Measurement,
    RoleGrant,
    TrainingWeekAggregate,
    User,
    WorkoutEntry,
    WorkoutSession,
    new_id,
)
from dzik_os.postepy import serwis
from dzik_os.security import hash_password

M = "/api/monitoring"


def _zawiera_klucz(obj, klucz: str) -> bool:
    if isinstance(obj, dict):
        return any(k == klucz or _zawiera_klucz(v, klucz) for k, v in obj.items())
    if isinstance(obj, list):
        return any(_zawiera_klucz(x, klucz) for x in obj)
    return False


def _oflaguj(id_a: str) -> None:
    """Flaga ZABURZENIA_ODZYWIANIA = `hidden_for_client` ostatniego szacunku kalorycznego."""
    with db_session() as db:
        db.add(CalorieEstimate(id=new_id("CAL"), client_id=id_a, submission_id=new_id("SUB"), version_no=1,
                               inputs_json=json.dumps({"cel": "redukcja"}), ppm=1500, pal=1.5, cpm=2250,
                               korekta_pct=-15, kcal=1900, hidden_for_client=True))


def test_klient_z_flaga_zdrowotna_nie_dostaje_pola_weight_na_zadnym_poziomie(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    hc = login(seeded, COACH)
    # Bez flagi: kafelek wagi jest (seed: ważenia raz w tygodniu → za mało na średnią, więc komunikat).
    r = seeded.get(f"{M}/summary", headers=ha)
    assert r.status_code == 200 and "weight" in r.json() and r.json()["weight"]["message"]
    assert seeded.get(f"{M}/body", headers=ha).status_code == 200
    _oflaguj(id_a)
    s = seeded.get(f"{M}/summary", headers=ha)
    assert s.status_code == 200 and not _zawiera_klucz(s.json(), "weight")
    assert seeded.get(f"{M}/body", headers=ha).status_code == 404  # nie pusta odpowiedź
    # Rekordy i trening nadal dostępne (bez danych wagowych).
    for sciezka in ("records", "training"):
        r = seeded.get(f"{M}/{sciezka}", headers=ha)
        assert r.status_code == 200 and not _zawiera_klucz(r.json(), "weight")
    # Widok trenera pozostaje pełny.
    t = seeded.get(f"{M}/clients/{id_a}", headers=hc)
    assert t.status_code == 200 and t.json()["health_flag"] is True and "weight" in t.json()["summary"]
    assert t.json()["body"]["weight"]["raw_points"]
    assert seeded.get(f"{M}/body", headers=hc, params={"client_id": id_a}).status_code == 200


def test_trener_bez_przypisania_dostaje_odmowe_a_klient_nie_widzi_listy(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    create_user_with_role("obcy.post@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.post@example.com", "password": "ObcyTrener#26"})
    # Spec §12 mówi „403”; aplikacja od 0.15 odmawia 404 (nie ujawnia istnienia klienta —
    # authz.resolve_client_access). Test pilnuje ODMOWY; rozbieżność zgłoszona w PROGRESS.
    assert seeded.get(f"{M}/clients/{id_a}", headers=h2).status_code in (403, 404)
    assert seeded.get(f"{M}/summary", headers=h2, params={"client_id": id_a}).status_code in (403, 404)
    assert seeded.get(f"{M}/clients", headers=h2).json()["clients"] == []
    # Klient: brak roli trenera → 403 na liście; trener bez client_id → 422.
    assert seeded.get(f"{M}/clients", headers=ha).status_code == 403
    hc = login(seeded, COACH)
    assert seeded.get(f"{M}/summary", headers=hc).status_code == 422


def test_flaga_modulu_wylaczona_daje_404_na_calym_module(seeded, monkeypatch):
    ha = login(seeded, CLIENT_A)
    monkeypatch.setattr(settings, "monitoring_tab_enabled", False)
    for sciezka in ("summary", "records", "training", "body", "clients"):
        assert seeded.get(f"{M}/{sciezka}", headers=ha).status_code == 404
    assert seeded.get("/api/health").json()["features"]["monitoring_tab"] is False
    assert seeded.get("/api/auth/me", headers=ha).json()["features"]["monitoring_tab"] is False
    monkeypatch.setattr(settings, "monitoring_tab_enabled", True)
    assert seeded.get(f"{M}/summary", headers=ha).status_code == 200
    assert seeded.get("/api/auth/me", headers=ha).json()["features"]["monitoring_tab"] is True
    assert seeded.post("/api/auth/login", json={"email": CLIENT_A["email"], "password": CLIENT_A["password"]}).json()["user"]["features"]["monitoring_tab"] is True


def test_summary_records_training_body_ksztalt_i_dane_seedu(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    dzis = local_today()
    with db_session() as db:
        serwis.przelicz_klienta(db, id_a)
        # Codzienne ważenia przez 3 tygodnie → średnia krocząca i trend (§9).
        for i in range(21):
            db.add(Measurement(id=new_id("MSR"), client_id=id_a, kind="weight", value=round(84 - 0.05 * (21 - i), 1),
                               unit="kg", measured_at=(dzis - timedelta(days=21 - i)).isoformat(), created_by=id_a))
    s = seeded.get(f"{M}/summary", headers=ha).json()
    assert {"week", "streak", "recent_records", "diet", "weight"} <= set(s)
    assert len(s["week"]["days"]) == 7 and s["week"]["done"] >= 0
    assert s["weight"]["average"] is not None and s["weight"]["kg_per_week"] is not None and s["weight"]["message"] is None
    r = seeded.get(f"{M}/records", headers=ha).json()
    przysiad = next(x for x in r["exercises"] if x["exercise_key"] == "przysiad ze sztangą")
    assert przysiad["max_weight"]["value"] == 105.0 and przysiad["max_weight"]["previous_value"] == 100.0
    assert przysiad["e1rm"]["estimated"] is True and przysiad["e1rm_series"]
    assert any(x["exercise_key"] == "przysiad ze sztangą" for x in r["recent"]) and r["archive"] == []
    h = seeded.get(f"{M}/records", headers=ha, params={"history": True}).json()
    assert any(x["superseded_at"] for x in next(e for e in h["exercises"] if e["exercise_key"] == "przysiad ze sztangą")["history"])
    t = seeded.get(f"{M}/training", headers=ha, params={"range": "8w"}).json()
    assert len(t["weeks"]) == 8 and "avg4_tonnage_kg" in t["weeks"][-1] and t["calendar"]["session_days"]
    b = seeded.get(f"{M}/body", headers=ha).json()
    assert b["weight"]["average_points"] and b["weight"]["raw_points"] and "raw_visible_default" not in b["weight"]
    assert any(c["kind"] == "waist" and c["delta_from_first"] is not None for c in b["circumferences"])


def test_lista_trenera_z_sygnalami_i_progami(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    with db_session() as db:
        serwis.przelicz_klienta(db, id_a)
    r = seeded.get(f"{M}/clients", headers=hc)
    assert r.status_code == 200
    lista = r.json()["clients"]
    a = next(c for c in lista if c["client_id"] == id_a)
    assert a["last_activity"] and a["attendance_4w"]["done"] >= 1 and a["consents"]["training"] is True
    assert any(s["key"] == "new_record" for s in a["signals"])  # seed: przysiad 105 kg 2 dni temu
    assert lista == sorted(lista, key=lambda c: (-c["priority"], c["display_name"]))
    # Progi konfigurowalne: bardzo niski próg „brak treningu” (1 dzień) łapie klienta A po 2 dniach.
    r2 = seeded.get(f"{M}/clients", headers=hc, params={"dni_bez_treningu": 1, "dni_rekordu": 1}).json()
    a2 = next(c for c in r2["clients"] if c["client_id"] == id_a)
    assert any(s["key"] == "no_training" for s in a2["signals"]) and r2["thresholds"]["dni_bez_treningu"] == 1
    assert seeded.get(f"{M}/clients", headers=hc, params={"dni_bez_treningu": 0}).status_code == 422


class _Licznik:
    def __enter__(self):
        self.n = 0
        event.listen(engine, "before_cursor_execute", self._bump)
        return self

    def _bump(self, *a):
        self.n += 1

    def __exit__(self, *exc):
        event.remove(engine, "before_cursor_execute", self._bump)


def test_lista_100_klientow_bez_n_plus_1(seeded):
    hc = login(seeded, COACH)
    coach_id = get_user_id(seeded, hc)
    dzis = local_today()
    with db_session() as db:
        for i in range(100):
            u = User(id=new_id("USR"), email=f"masowy{i}@example.com", password_hash=hash_password("Haslo#123456"),
                     display_name=f"Masowy {i:03d}", identity_id=new_id("ID"))
            db.add(u)
            db.flush()
            db.add(RoleGrant(id=new_id("ROL"), user_id=u.id, role="CLIENT", scope="*", issued_by="test"))
            db.add(CoachClientRelationship(id=new_id("REL"), coach_id=coach_id, client_id=u.id, created_by=coach_id))
            db.add(Measurement(id=new_id("MSR"), client_id=u.id, kind="weight", value=80 + i % 5, unit="kg",
                               measured_at=(dzis - timedelta(days=i % 20)).isoformat(), created_by=u.id))
    with _Licznik() as l10:
        r = seeded.get(f"{M}/clients", headers=hc, params={"dni_bez_treningu": 3})
    assert r.status_code == 200 and len(r.json()["clients"]) >= 100
    # Stała liczba zapytań niezależnie od liczby klientów (relacje, użytkownicy, zgody, agregaty,
    # sesje, wagi, rekordy, szacunki, harmonogram + sesja/rola).
    assert l10.n <= 20, l10.n


def test_summary_dla_2_lat_historii_ponizej_300_ms(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    dzis = local_today()
    with db_session() as db:
        pv = db.query(WorkoutSession).filter_by(client_id=id_a).first().plan_version_id
        for i in range(0, 730, 2):  # ~365 sesji przez 2 lata
            d = dzis - timedelta(days=i)
            s = WorkoutSession(id=new_id("WKS"), client_id=id_a, plan_version_id=pv, day_index=0,
                               performed_on=d.isoformat(), status="DONE")
            db.add(s)
            db.flush()
            for j, nazwa in enumerate(("Przysiad ze sztangą", "Wyciskanie sztangi leżąc", "Martwy ciąg")):
                db.add(WorkoutEntry(id=new_id("WKE"), session_id=s.id, exercise_index=j, exercise_name=nazwa,
                                    sets_json=json.dumps([{"weight_kg": 60 + (i % 40), "reps": 5}] * 4)))
        for i in range(0, 730, 3):
            db.add(Measurement(id=new_id("MSR"), client_id=id_a, kind="weight", value=85 - i * 0.01, unit="kg",
                               measured_at=(dzis - timedelta(days=i)).isoformat(), created_by=id_a))
    with db_session() as db:
        serwis.przelicz_klienta(db, id_a)
    seeded.get(f"{M}/summary", headers=ha)  # rozgrzewka (import/lazy)
    t0 = time.perf_counter()
    for _ in range(3):
        assert seeded.get(f"{M}/summary", headers=ha).status_code == 200
    sredni_ms = (time.perf_counter() - t0) / 3 * 1000
    assert sredni_ms < 300, sredni_ms


def _cofnij_zgode(seeded, ha, kategoria: str) -> None:
    dane = seeded.get("/api/me/consents", headers=ha).json()
    zgody = dane["consents"] if isinstance(dane, dict) and "consents" in dane else dane
    aktywna = next(c for c in zgody if c["category"] == kategoria and c["revoked_at"] is None)
    assert seeded.post(f"/api/me/consents/{aktywna['id']}/revoke", headers=ha).status_code in (200, 201)


def _wersja_planu(seeded, ha, cid: str) -> str:
    return seeded.get(f"/api/clients/{cid}/plans", headers=ha).json()["plans"][0]["current_version"]["id"]


def test_trener_bez_zgody_na_domene_nie_dostaje_wagi_diety_flagi_ani_frekwencji(seeded):
    """Zgody per domena jak w reszcie aplikacji: bez `dane_zdrowotne` znika waga, `body` i flaga
    zdrowotna; bez `zdjecia_progresu` zdjęcia są puste; bez `dane_treningowe` lista nie zdradza
    daty ostatniej sesji ani frekwencji."""
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    hc = login(seeded, COACH)
    assert "weight" in seeded.get(f"{M}/summary?client_id={cid}", headers=hc).json()
    _cofnij_zgode(seeded, ha, "zdjecia_progresu")
    body = seeded.get(f"{M}/body?client_id={cid}", headers=hc)
    assert body.status_code == 200 and body.json()["photos"] == [] and "weight" in body.json()
    _cofnij_zgode(seeded, ha, "dane_zdrowotne")
    po = seeded.get(f"{M}/summary?client_id={cid}", headers=hc).json()
    assert "weight" not in po
    det = seeded.get(f"{M}/clients/{cid}", headers=hc).json()
    # Flaga zdrowotna to pochodna odpowiedzi (decyzja właściciela 14.09) — zostaje; pomiary znikają.
    assert det["health_flag"] is False and "body" not in det and "weight" not in det["summary"]
    assert seeded.get(f"{M}/body?client_id={cid}", headers=hc).status_code == 404
    _cofnij_zgode(seeded, ha, "dane_treningowe")
    a = next(c for c in seeded.get(f"{M}/clients", headers=hc).json()["clients"] if c["client_id"] == cid)
    assert a["attendance_4w"] is None and a["last_activity"] is None and a["consents"]["training"] is False
    assert seeded.get(f"{M}/summary?client_id={cid}", headers=hc).status_code == 404


def test_sesja_pominieta_nie_liczy_sie_do_tygodnia_ani_rekordow(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    przed = seeded.get(f"{M}/summary", headers=ha).json()
    poniedzialek = przed["week"]["days"][0]["date"]
    r = seeded.post(f"/api/clients/{cid}/workouts", headers=ha, json={
        "plan_version_id": _wersja_planu(seeded, ha, cid), "day_index": 0, "performed_on": poniedzialek,
        "status": "SKIPPED", "entries": [{"exercise_index": 0, "exercise_name": "Przysiad ze sztangą",
                                          "sets": [{"weight_kg": 300, "reps": 1}]}],
    })
    assert r.status_code == 201 and r.json()["new_records"] == 0
    po = seeded.get(f"{M}/summary", headers=ha).json()
    assert po["week"]["done"] == przed["week"]["done"] and po["recent_records"] == przed["recent_records"]
    assert not any(d["date"] == poniedzialek and d["done"] for d in po["week"]["days"]) or any(
        d["date"] == poniedzialek and d["done"] for d in przed["week"]["days"])


def test_bez_flagi_zapis_sesji_nie_liczy_rekordow_i_nie_powiadamia(seeded, monkeypatch):
    from dzik_os.models import Notification

    monkeypatch.setattr(settings, "monitoring_tab_enabled", False)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    with db_session() as db:
        przed = db.query(ExerciseRecord).filter_by(client_id=cid).count()
    r = seeded.post(f"/api/clients/{cid}/workouts", headers=ha, json={
        "plan_version_id": _wersja_planu(seeded, ha, cid), "day_index": 0,
        "performed_on": local_today(None).isoformat(),
        "status": "DONE", "entries": [{"exercise_index": 0, "exercise_name": "Przysiad ze sztangą",
                                       "sets": [{"weight_kg": 200, "reps": 3}]}],
    })
    assert r.status_code == 201 and r.json()["new_records"] == 0
    with db_session() as db:
        assert db.query(ExerciseRecord).filter_by(client_id=cid).count() == przed
        assert db.query(Notification).filter_by(user_id=cid, category="REKORD").count() == 0
    kategorie = [c["key"] for c in seeded.get("/api/notifications/settings", headers=ha).json()["categories"]]
    assert "REKORD" not in kategorie
    monkeypatch.setattr(settings, "monitoring_tab_enabled", True)
    kategorie = [c["key"] for c in seeded.get("/api/notifications/settings", headers=ha).json()["categories"]]
    assert "REKORD" in kategorie


def test_eksport_i_usuniecie_konta_obejmuja_rekordy_i_agregaty(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    ex = seeded.get("/api/me/export", headers=ha).json()
    assert ex["export_version"] == "2.1" and len(ex["exercise_records"]) > 0 and len(ex["training_week_aggregates"]) > 0
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE"})
    assert r.status_code in (200, 202), r.text
    with db_session() as db:
        assert db.query(ExerciseRecord).filter_by(client_id=cid).count() == 0
        assert db.query(TrainingWeekAggregate).filter_by(client_id=cid).count() == 0

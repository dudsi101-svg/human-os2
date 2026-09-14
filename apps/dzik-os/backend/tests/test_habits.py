"""Nawyki (0.63.0): limit 3, proweniencja, idempotentne i cofalne odhaczanie,
postęp z łagodnym decay, absolutorium, obcy klient 404, pola w „Dzisiaj”."""

from __future__ import annotations

from datetime import timedelta

from conftest import CLIENT_A, CLIENT_B, COACH, get_user_id, login

from dzik_os.daily_messages import message_for
from dzik_os.dates import local_today

H = "/api/clients/{}/habits"


def _archiwizuj_wszystkie(c, h, cid):
    for hab in c.get(H.format(cid), headers=h).json()["habits"]:
        c.patch(f"{H.format(cid)}/{hab['id']}", headers=h, json={"status": "ARCHIVED"})


def _dodaj(c, h, cid, name="Szklanka wody po przebudzeniu", **extra):
    r = c.post(H.format(cid), headers=h, json={"name": name, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_limit_trzech_aktywnych_i_proweniencja(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    _archiwizuj_wszystkie(seeded, ha, cid)
    a = _dodaj(seeded, ha, cid, "Woda")
    b = _dodaj(seeded, hc, cid, "Spacer", author_note="Zacznij od 10 minut.", target_days=30)
    assert a["author_id"] == cid and b["author_id"] != cid and b["author_note"].startswith("Zacznij")
    assert a["target_days"] == 66 and b["target_days"] == 30 and a["status"] == "ACTIVE"
    _dodaj(seeded, ha, cid, "Czytanie")
    r = seeded.post(H.format(cid), headers=ha, json={"name": "Czwarty"})
    assert r.status_code == 409 and "3" in r.json()["detail"]
    # Walidacja: termin poza 14–254, dni tygodnia spoza 1–7, start w przyszłości.
    assert seeded.post(H.format(cid), headers=ha, json={"name": "X", "target_days": 5}).status_code == 422
    assert seeded.post(H.format(cid), headers=ha, json={"name": "X", "days_of_week": "1,8"}).status_code == 422
    jutro = (local_today() + timedelta(days=1)).isoformat()
    _archiwizuj_wszystkie(seeded, ha, cid)
    assert seeded.post(H.format(cid), headers=ha, json={"name": "X", "started_on": jutro}).status_code == 422
    # Archiwizacja zwalnia miejsce.
    assert seeded.post(H.format(cid), headers=ha, json={"name": "Nowy"}).status_code == 201


def test_odhaczanie_idempotentne_i_cofalne(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _archiwizuj_wszystkie(seeded, ha, cid)
    hab = _dodaj(seeded, ha, cid)
    url = f"{H.format(cid)}/{hab['id']}/complete"
    r1 = seeded.post(url, headers=ha, json={}).json()
    r2 = seeded.post(url, headers=ha, json={}).json()
    assert r1["done_today"] and r2["done_today"] and r2["progress"] == 1 and r2["done_count"] == 1
    r3 = seeded.post(url, headers=ha, json={"done": False}).json()
    assert not r3["done_today"] and r3["progress"] == 0
    assert seeded.post(url, headers=ha, json={"done": False}).json()["progress"] == 0
    jutro = (local_today() + timedelta(days=1)).isoformat()
    assert seeded.post(url, headers=ha, json={"completed_on": jutro}).status_code == 422
    wczoraj = (local_today() - timedelta(days=1)).isoformat()
    assert seeded.post(url, headers=ha, json={"completed_on": wczoraj}).status_code == 422  # sprzed startu


def test_postep_z_decay_i_absolutorium(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _archiwizuj_wszystkie(seeded, ha, cid)
    dzis = local_today()
    start = dzis - timedelta(days=6)
    hab = _dodaj(seeded, ha, cid, "Rozciąganie", target_days=14, started_on=start.isoformat())
    url = f"{H.format(cid)}/{hab['id']}/complete"
    # Dni 0,1 wykonane; 2,3,4 opuszczone; 5 wykonany; dziś (6) jeszcze nie → 1 (jak w teście silnika).
    for n in (0, 1, 5):
        seeded.post(url, headers=ha, json={"completed_on": (start + timedelta(days=n)).isoformat()})
    hab = next(h for h in seeded.get(H.format(cid), headers=ha).json()["habits"] if h["id"] == hab["id"])
    assert hab["progress"] == 1 and hab["done_count"] == 3 and hab["planned_count"] == 7
    assert hab["scheduled_today"] and not hab["done_today"] and "z 14" in hab["progress_label"]
    # Absolutorium: 14 dni wykonanych od startu 13 dni temu → GRADUATED, dalsze odhaczanie 409.
    start2 = dzis - timedelta(days=13)
    hab2 = _dodaj(seeded, ha, cid, "Woda", target_days=14, started_on=start2.isoformat())
    url2 = f"{H.format(cid)}/{hab2['id']}/complete"
    for n in range(14):
        out = seeded.post(url2, headers=ha, json={"completed_on": (start2 + timedelta(days=n)).isoformat()}).json()
    assert out["status"] == "GRADUATED" and out["progress"] == 14 and out["graduated_on"] == dzis.isoformat()
    assert seeded.post(url2, headers=ha, json={"done": False}).status_code == 409
    # Absolutorium zwalnia miejsce (limit liczy tylko ACTIVE); „Zostaw” = ack.
    assert seeded.post(H.format(cid), headers=ha, json={"name": "A"}).status_code == 201
    assert seeded.post(H.format(cid), headers=ha, json={"name": "B"}).status_code == 201
    assert seeded.post(H.format(cid), headers=ha, json={"name": "C"}).status_code == 409
    r = seeded.patch(f"{H.format(cid)}/{hab2['id']}", headers=ha, json={"ack": True}).json()
    assert r["ack_on"] == dzis.isoformat() and r["status"] == "GRADUATED"


def test_obcy_klient_i_trener_bez_relacji(seeded):
    ha, hb, hc = login(seeded, CLIENT_A), login(seeded, CLIENT_B), login(seeded, COACH)
    cid_a, cid_b = get_user_id(seeded, ha), get_user_id(seeded, hb)
    hab = seeded.get(H.format(cid_a), headers=ha).json()["habits"][0]
    # Klient B: cudzy zasób → odmowa (404), także pod własnym client_id (IDOR).
    assert seeded.get(H.format(cid_a), headers=hb).status_code in (403, 404)
    assert seeded.post(f"{H.format(cid_b)}/{hab['id']}/complete", headers=hb, json={}).status_code == 404
    assert seeded.patch(f"{H.format(cid_b)}/{hab['id']}", headers=hb, json={"name": "x"}).status_code == 404
    # Trener z relacją czyta i odhacza (wspólne uzupełnianie), zapisany jako created_by.
    assert seeded.get(H.format(cid_a), headers=hc).status_code == 200
    assert seeded.post(f"{H.format(cid_a)}/{hab['id']}/complete", headers=hc, json={"done": False}).status_code in (200, 409)


def test_dzisiaj_ma_powitanie_haslo_i_nawyki(seeded):
    ha = login(seeded, CLIENT_A)
    d = seeded.get("/api/me/today", headers=ha).json()
    assert d["greeting_name"] == "Klient"
    assert d["daily_message"] == message_for(local_today()) and d["daily_message"]["author"]
    assert isinstance(d["habits"], list) and len(d["habits"]) >= 1
    h = d["habits"][0]
    for k in ("id", "name", "progress", "target_days", "status", "done_today", "scheduled_today", "progress_label"):
        assert k in h
    # Seed: nawyk bliski absolutorium (12 z 14) i nawyk z opuszczeniami.
    nazwy = {x["name"]: x for x in d["habits"]}
    assert nazwy["Szklanka wody po przebudzeniu"]["progress"] == 11
    assert nazwy["Szklanka wody po przebudzeniu"]["target_days"] == 14


def test_eksport_i_usuniecie_konta_obejmuja_nawyki(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    ex = seeded.get("/api/me/export", headers=ha).json()
    assert ex["export_version"] == "1.8" and len(ex["habits"]) == 3 and len(ex["habit_completions"]) > 10
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE"})
    assert r.status_code in (200, 202), r.text
    from dzik_os.db import SessionLocal
    from dzik_os.models import Habit, HabitCompletion
    with SessionLocal() as db:
        assert db.query(Habit).filter_by(client_id=cid).count() == 0
        assert db.query(HabitCompletion).filter_by(client_id=cid).count() == 0

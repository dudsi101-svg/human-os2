"""Dni treningowe (0.71.0): silnik nakładki klienta na dni tygodnia planu,
API `GET/PUT/DELETE /api/clients/{id}/plans/{plan_id}/dni`, „Dzisiaj”
z układem klienta, IDOR 404, trener z relacją i zgodą, prywatność, audyt."""

from __future__ import annotations

import pytest
from conftest import CLIENT_A, CLIENT_B, COACH, create_activated_client, get_user_id, login

from dzik_os import dni_treningowe as D
from dzik_os.dates import local_today
from dzik_os.db import SessionLocal
from dzik_os.models import PlanWeekdayChoice, Receipt

DNI = "/api/clients/{}/plans/{}/dni"


# --- Silnik (przykłady ręczne) ---------------------------------------------

PLAN_TRENERA = {"days": [
    {"id": "D-A", "name": "Góra", "weekday": 1, "exercises": []},
    {"id": "D-B", "name": "Dół", "weekday": 3, "exercises": []},
    {"id": "D-C", "name": "Całe ciało", "weekday": None, "exercises": []},
]}
PLAN_BEZ_ID = {"days": [{"name": "FBW 1", "weekday": 2}, {"name": "FBW 2", "weekday": None}]}


def test_klucz_dnia_id_albo_indeks():
    assert D.klucz_dnia({"id": "D-A"}, 0) == "D-A"
    assert D.klucz_dnia({"id": "  "}, 4) == "idx:4"
    assert D.klucz_dnia({"name": "x"}, 2) == "idx:2"
    assert D.klucz_dnia("nie słownik", 1) == "idx:1"
    assert [k for k, _, _ in D.dni(PLAN_BEZ_ID)] == ["idx:0", "idx:1"]
    assert D.dni({"days": "zepsute"}) == [] and D.dni(None) == []


def test_klucze_unikalne_w_wersji_przy_powtorzonym_id_i_kolizji_z_idx():
    """Powtórzone `id` albo `id` w postaci `idx:<n>` → klucz zastępczy z własnego
    indeksu (naprawa odczytowa; wersja pozostaje nietknięta)."""
    wersja = {"days": [{"id": "X", "name": "A"}, {"id": "X", "name": "B"}, {"name": "C"}, {"id": "idx:2", "name": "D"}]}
    assert [k for k, _, _ in D.dni(wersja)] == ["idx:0", "idx:1", "idx:2", "idx:3"]
    assert len({k for k, _, _ in D.dni(wersja)}) == 4
    # Unikalne `id` zostają; tylko kolidujące spadają na indeks.
    mieszana = {"days": [{"id": "ELM-A", "name": "A"}, {"name": "B"}, {"id": "ELM-A", "name": "C"}, {"id": "ELM-D", "name": "D"}]}
    assert [k for k, _, _ in D.dni(mieszana)] == ["idx:0", "idx:1", "idx:2", "ELM-D"]
    # Dwie jednostki w ten sam dzień da się teraz odrzucić — klucze nie zlewają się.
    with pytest.raises(D.BladWyboru):
        D.waliduj_wybor(wersja, [{"day_key": "idx:0", "weekday": 1}, {"day_key": "idx:1", "weekday": 1}])
    assert D.waliduj_wybor(wersja, [{"day_key": "idx:0", "weekday": 1}, {"day_key": "idx:1", "weekday": 3}]) == {
        "idx:0": 1, "idx:1": 3, "idx:2": None, "idx:3": None}
    assert D.dzien_na_dzis(wersja, {"idx:0": 1, "idx:1": 3}, 3) == (1, wersja["days"][1])


def test_prefill_z_trenera_i_nakladka_wygrywa_w_calosci():
    assert D.uklad_efektywny(PLAN_TRENERA, None) == {"D-A": 1, "D-B": 3, "D-C": None}
    # Klient ustawił tylko D-C: propozycje trenera dla D-A/D-B NIE obowiązują.
    assert D.uklad_efektywny(PLAN_TRENERA, {"D-C": 5}) == {"D-A": None, "D-B": None, "D-C": 5}
    # Klucz spoza wersji i śmieci w wartości są pomijane.
    assert D.uklad_efektywny(PLAN_TRENERA, {"D-A": 9, "obcy": 2}) == {"D-A": None, "D-B": None, "D-C": None}
    assert D.zrodlo(PLAN_TRENERA, None) == "coach" and D.zrodlo(PLAN_TRENERA, {}) == "client"
    assert D.zrodlo({"days": []}, None) == "none"


def test_dzien_na_dzis_i_klucze_nieaktualne():
    assert D.dzien_na_dzis(PLAN_TRENERA, None, 3) == (1, PLAN_TRENERA["days"][1])
    assert D.dzien_na_dzis(PLAN_TRENERA, None, 5) is None
    assert D.dzien_na_dzis(PLAN_TRENERA, {"D-C": 5}, 5) == (2, PLAN_TRENERA["days"][2])
    assert D.dzien_na_dzis(PLAN_TRENERA, {"D-C": 5}, 1) is None  # nakładka w całości
    assert D.dzien_na_dzis(PLAN_BEZ_ID, {"idx:1": 7}, 7) == (1, PLAN_BEZ_ID["days"][1])
    assert D.klucze_nieaktualne(PLAN_TRENERA, {"D-A": 1, "D-X": 2, "D-Y": None}) == ["D-X", "D-Y"]
    assert D.klucze_nieaktualne(PLAN_TRENERA, None) == [] and D.klucze_nieaktualne(PLAN_TRENERA, {}) == []


def test_podpowiedz_dla_dzisiaj():
    assert D.podpowiedz(PLAN_TRENERA, None) is None
    assert D.podpowiedz({"days": [{"name": "A"}, {"name": "B"}]}, None) == "no_weekdays"
    assert D.podpowiedz(PLAN_TRENERA, {}) == "no_weekdays"  # świadomie bez dni
    assert D.podpowiedz(PLAN_TRENERA, {"D-A": 1, "D-Z": 2}) == "stale"
    assert D.podpowiedz({"days": []}, None) is None


def test_waliduj_wybor_i_bledy():
    ok = D.waliduj_wybor(PLAN_TRENERA, [{"day_key": "D-B", "weekday": 2}])
    assert ok == {"D-A": None, "D-B": 2, "D-C": None}
    assert D.z_json(D.do_json(ok)) == ok
    with pytest.raises(D.BladWyboru) as e:
        D.waliduj_wybor(PLAN_TRENERA, [{"day_key": "D-A", "weekday": 2}, {"day_key": "D-B", "weekday": 2}])
    assert e.value.day_key == "D-B" and e.value.komunikat.startswith("We wtorek jest już „Góra”")
    for wd, kiedy in enumerate(("W poniedziałek", "We wtorek", "W środę", "W czwartek", "W piątek", "W sobotę", "W niedzielę"), start=1):
        with pytest.raises(D.BladWyboru) as e2:
            D.waliduj_wybor(PLAN_TRENERA, [{"day_key": "D-A", "weekday": wd}, {"day_key": "D-B", "weekday": wd}])
        assert e2.value.komunikat.startswith(f"{kiedy} jest już „Góra” — jeden dzień tygodnia to jedna jednostka.")
    with pytest.raises(D.BladWyboru) as e:
        D.waliduj_wybor(PLAN_TRENERA, [{"day_key": "obcy", "weekday": 1}])
    assert e.value.day_key == "obcy"
    with pytest.raises(D.BladWyboru):
        D.waliduj_wybor(PLAN_TRENERA, [{"day_key": "D-A", "weekday": 1}, {"day_key": "D-A", "weekday": 2}])
    for zly in (0, 8, True, "1"):
        with pytest.raises(D.BladWyboru):
            D.waliduj_wybor(PLAN_TRENERA, [{"day_key": "D-A", "weekday": zly}])
    with pytest.raises(D.BladWyboru):
        D.waliduj_wybor({"days": []}, [])
    # Dane z bazy (nie z API) nie rzucają — nieczytelne wpisy są pomijane.
    assert D.z_json([{"day_key": "D-A", "weekday": 12}, {"weekday": 1}, "x", None]) == {"D-A": None}
    assert D.z_json("zepsute") == {}


# --- API ------------------------------------------------------------------


def _plan_klienta(c, h, cid):
    plans = c.get(f"/api/clients/{cid}/plans", headers=h).json()["plans"]
    return next(p for p in plans if p["status"] == "ACTIVE")


def _dzis():
    return local_today().isoweekday()


def test_odczyt_prefill_z_propozycji_trenera(seeded):
    hb = login(seeded, CLIENT_B)
    cid = get_user_id(seeded, hb)
    plan = _plan_klienta(seeded, hb, cid)
    d = seeded.get(DNI.format(cid, plan["id"]), headers=hb).json()
    assert d["source"] == "coach" and d["version_no"] == 1 and d["stale_keys"] == []
    assert [x["day_key"] for x in d["days"]] == ["idx:0", "idx:1", "idx:2"]  # seed bez `id`
    assert [x["name"] for x in d["days"]] == ["FBW 1", "FBW 2", "FBW 3"]
    assert [x["coach_weekday"] for x in d["days"]] == [2, 4, 6]
    assert [x["weekday"] for x in d["days"]] == [2, 4, 6]
    assert d["author_id"] is None


def test_zapis_nakladka_wygrywa_dzisiaj_i_powrot_do_trenera(seeded):
    hb = login(seeded, CLIENT_B)
    cid = get_user_id(seeded, hb)
    plan = _plan_klienta(seeded, hb, cid)
    url = DNI.format(cid, plan["id"])
    dzis = _dzis()
    r = seeded.put(url, headers=hb, json={"choices": [{"day_key": "idx:2", "weekday": dzis}], "author_note": "Sobota wypada"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"] == "client" and d["author_id"] == cid and d["author_note"] == "Sobota wypada"
    # Nakładka obowiązuje w całości: FBW 1 i FBW 2 nieprzypisane, choć trener proponował wt/czw.
    assert [x["weekday"] for x in d["days"]] == [None, None, dzis]
    assert [x["coach_weekday"] for x in d["days"]] == [2, 4, 6]
    # Odczyt po zapisie = ten sam stan (z serwera).
    assert seeded.get(url, headers=hb).json()["days"][2]["weekday"] == dzis
    t = seeded.get("/api/me/today", headers=hb).json()
    assert t["workout"]["day"]["name"] == "FBW 3" and t["workout"]["day_index"] == 2
    assert t["workout"]["weekday_source"] == "client" and t["workout_hint"] is None
    # Kolejny zapis nadpisuje układ (preferencja), a nie dokłada.
    r = seeded.put(url, headers=hb, json={"choices": [{"day_key": "idx:0", "weekday": dzis}]})
    assert [x["weekday"] for x in r.json()["days"]] == [dzis, None, None]
    assert seeded.get("/api/me/today", headers=hb).json()["workout"]["day"]["name"] == "FBW 1"
    with SessionLocal() as db:
        row = db.query(PlanWeekdayChoice).filter_by(client_id=cid, plan_id=plan["id"]).one()
        assert row.version == 2 and row.author_note is None
    # Świadomie „bez dni” (pusta lista) ≠ powrót do trenera: układ klienta z samymi None.
    r = seeded.put(url, headers=hb, json={"choices": []})
    assert r.json()["source"] == "client" and all(x["weekday"] is None for x in r.json()["days"])
    t = seeded.get("/api/me/today", headers=hb).json()
    assert t["workout"] is None and t["workout_hint"] == {"kind": "no_weekdays", "plan_id": plan["id"]}
    # Powrót do propozycji trenera (idempotentny).
    for _ in range(2):
        r = seeded.delete(url, headers=hb)
        assert r.status_code == 200 and r.json()["source"] == "coach"
        assert [x["weekday"] for x in r.json()["days"]] == [2, 4, 6]
    t = seeded.get("/api/me/today", headers=hb).json()
    assert t["workout_hint"] is None
    assert (t["workout"] is None) == (dzis not in (2, 4, 6))
    if t["workout"] is not None:
        assert t["workout"]["weekday_source"] == "coach"


def _plan(seeded, hc, cid, title, days):
    r = seeded.post("/api/plans", headers=hc, json={"client_id": cid, "title": title,
                                                    "version": {"reason": "Start", "days": days}})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_dzisiaj_bez_wyboru_dzien_trenera_bezwarunkowo(seeded):
    """Dzień trenera = dziś → `today` bez żadnego wyboru pokazuje jednostkę 0 ze
    źródłem `coach`; dwa dni trenera z tym samym `weekday` → pierwszy wygrywa
    (jak przed rundą); mieszanka `id`/bez `id` daje klucze `id` i `idx:n`."""
    hc = login(seeded, COACH)
    cid = create_activated_client(seeded, hc, "trener-dzis@example.com")
    hn = login(seeded, {"email": "trener-dzis@example.com", "password": "WlasneHaslo#123"})
    dzis = _dzis()
    inny = (dzis % 7) + 1
    plan_id = _plan(seeded, hc, cid, "Dni od trenera", [
        {"id": "ELM-A", "name": "Pierwsza dziś", "weekday": dzis, "exercises": []},
        {"name": "Bez id", "weekday": inny, "exercises": []},
        {"id": "ELM-C", "name": "Druga dziś", "weekday": dzis, "exercises": []},
    ])
    t = seeded.get("/api/me/today", headers=hn).json()
    assert t["workout"]["plan_id"] == plan_id and t["workout"]["day_index"] == 0
    assert t["workout"]["day"]["name"] == "Pierwsza dziś" and t["workout"]["weekday_source"] == "coach"
    assert t["workout_hint"] is None
    d = seeded.get(DNI.format(cid, plan_id), headers=hn).json()
    assert [x["day_key"] for x in d["days"]] == ["ELM-A", "idx:1", "ELM-C"] and d["source"] == "coach"
    assert [x["coach_weekday"] for x in d["days"]] == [dzis, inny, dzis]
    # Klient przenosi „dziś” na trzecią jednostkę — nakładka wygrywa, klucz `idx:1` działa.
    r = seeded.put(DNI.format(cid, plan_id), headers=hn, json={"choices": [
        {"day_key": "ELM-C", "weekday": dzis}, {"day_key": "idx:1", "weekday": inny}]})
    assert r.status_code == 200, r.text
    t = seeded.get("/api/me/today", headers=hn).json()
    assert t["workout"]["day_index"] == 2 and t["workout"]["weekday_source"] == "client"


def test_powtorzone_id_w_wersji_nie_zlewaja_jednostek(seeded):
    """Dowód recenzenta: `{id:X,A},{id:X,B},{C},{id:"idx:2",D}` — przed poprawką PUT
    `X→1, idx:2→3` = 200 i dwie jednostki w poniedziałek."""
    hc = login(seeded, COACH)
    cid = create_activated_client(seeded, hc, "powtorzone-id@example.com")
    hn = login(seeded, {"email": "powtorzone-id@example.com", "password": "WlasneHaslo#123"})
    plan_id = _plan(seeded, hc, cid, "Powtórzone id", [
        {"id": "X", "name": "A", "weekday": None, "exercises": []},
        {"id": "X", "name": "B", "weekday": None, "exercises": []},
        {"name": "C", "weekday": None, "exercises": []},
        {"id": "idx:2", "name": "D", "weekday": None, "exercises": []},
    ])
    d = seeded.get(DNI.format(cid, plan_id), headers=hn).json()
    assert [x["day_key"] for x in d["days"]] == ["idx:0", "idx:1", "idx:2", "idx:3"]
    # Klucz `X` nie istnieje → 422; `idx:2` wskazuje C, nie D.
    r = seeded.put(DNI.format(cid, plan_id), headers=hn, json={"choices": [{"day_key": "X", "weekday": 1}, {"day_key": "idx:2", "weekday": 3}]})
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "X"
    dzis = _dzis()
    r = seeded.put(DNI.format(cid, plan_id), headers=hn, json={"choices": [{"day_key": "idx:1", "weekday": dzis}, {"day_key": "idx:3", "weekday": (dzis % 7) + 1}]})
    assert r.status_code == 200, r.text
    assert [x["weekday"] for x in r.json()["days"]] == [None, dzis, None, (dzis % 7) + 1]
    t = seeded.get("/api/me/today", headers=hn).json()
    assert t["workout"]["day_index"] == 1 and t["workout"]["day"]["name"] == "B"
    # Dwie jednostki w ten sam dzień nadal odrzucane — klucze już się nie zlewają.
    r = seeded.put(DNI.format(cid, plan_id), headers=hn, json={"choices": [{"day_key": "idx:0", "weekday": 1}, {"day_key": "idx:1", "weekday": 1}]})
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "idx:1"


def test_plan_odpiety_i_zarchiwizowany_404(seeded):
    """Po `/odepnij` i `/archiwizuj` plan nie jest widoczny klientowi — GET/PUT/DELETE
    dają zwykłe 404 (własny plan, nie IDOR) i nie powstają osierocone wiersze."""
    hc = login(seeded, COACH)
    cid = create_activated_client(seeded, hc, "odpiety@example.com")
    hn = login(seeded, {"email": "odpiety@example.com", "password": "WlasneHaslo#123"})
    dni = [{"name": "J1", "weekday": None, "exercises": []}]
    odpiety = _plan(seeded, hc, cid, "Do odpięcia", dni)
    assert seeded.put(DNI.format(cid, odpiety), headers=hn, json={"choices": [{"day_key": "idx:0", "weekday": 1}]}).status_code == 200
    assert seeded.post(f"/api/plans/{odpiety}/odepnij", headers=hc).json()["status"] == "UNASSIGNED"
    zarchiwizowany = _plan(seeded, hc, cid, "Do archiwum", dni)
    assert seeded.post(f"/api/plans/{zarchiwizowany}/archiwizuj", headers=hc).json()["status"] == "ARCHIVED"
    for pid in (odpiety, zarchiwizowany):
        assert seeded.get(DNI.format(cid, pid), headers=hn).status_code == 404
        assert seeded.put(DNI.format(cid, pid), headers=hn, json={"choices": [{"day_key": "idx:0", "weekday": 2}]}).status_code == 404
        assert seeded.delete(DNI.format(cid, pid), headers=hn).status_code == 404
        assert seeded.get(DNI.format(cid, pid), headers=hc).status_code == 404
    with SessionLocal() as db:
        # Wpis sprzed odpięcia zostaje (historia; kasuje go usunięcie konta), nowych nie przybyło.
        assert db.query(PlanWeekdayChoice).filter_by(client_id=cid).count() == 1
    t = seeded.get("/api/me/today", headers=hn).json()
    assert t["workout"] is None and t["workout_hint"] is None


def test_walidacja_422_po_polsku(seeded):
    hb = login(seeded, CLIENT_B)
    cid = get_user_id(seeded, hb)
    plan = _plan_klienta(seeded, hb, cid)
    url = DNI.format(cid, plan["id"])
    # Dwie jednostki tego samego dnia → 422 z komunikatem przy właściwym polu.
    r = seeded.put(url, headers=hb, json={"choices": [{"day_key": "idx:0", "weekday": 3}, {"day_key": "idx:1", "weekday": 3}]})
    assert r.status_code == 422, r.text
    b = r.json()
    assert b["code"] == "WEEKDAY_CHOICE" and b["detail"] == "W środę jest już „FBW 1” — jeden dzień tygodnia to jedna jednostka."
    assert b["errors"] == [{"field": "idx:1", "type": "weekday_choice", "msg": b["detail"]}]
    # Klucz spoza bieżącej wersji.
    r = seeded.put(url, headers=hb, json={"choices": [{"day_key": "idx:7", "weekday": 1}]})
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "idx:7"
    # Jednostka podana dwa razy.
    r = seeded.put(url, headers=hb, json={"choices": [{"day_key": "idx:0", "weekday": 1}, {"day_key": "idx:0", "weekday": 2}]})
    assert r.status_code == 422
    # weekday 0 / 8 / tekst / bool / liczba jako tekst — walidacja schematu (StrictInt).
    for zly in (0, 8, "pon", True, "3", 3.0):
        assert seeded.put(url, headers=hb, json={"choices": [{"day_key": "idx:0", "weekday": zly}]}).status_code == 422
    # Nic z powyższego nie zostało zapisane.
    assert seeded.get(url, headers=hb).json()["source"] == "coach"
    with SessionLocal() as db:
        assert db.query(PlanWeekdayChoice).filter_by(client_id=cid).count() == 0


def test_obcy_klient_i_cudzy_plan_404(seeded):
    ha, hb = login(seeded, CLIENT_A), login(seeded, CLIENT_B)
    cid_a, cid_b = get_user_id(seeded, ha), get_user_id(seeded, hb)
    plan_b = _plan_klienta(seeded, hb, cid_b)
    plan_a = _plan_klienta(seeded, ha, cid_a)
    dzis = _dzis()
    # Klient A pod client_id klienta B.
    assert seeded.get(DNI.format(cid_b, plan_b["id"]), headers=ha).status_code in (403, 404)
    assert seeded.put(DNI.format(cid_b, plan_b["id"]), headers=ha, json={"choices": []}).status_code in (403, 404)
    assert seeded.delete(DNI.format(cid_b, plan_b["id"]), headers=ha).status_code in (403, 404)
    # Klient A pod WŁASNYM client_id, ale z planem klienta B (IDOR) → 404, nic nie zapisane.
    assert seeded.get(DNI.format(cid_a, plan_b["id"]), headers=ha).status_code == 404
    assert seeded.put(DNI.format(cid_a, plan_b["id"]), headers=ha, json={"choices": [{"day_key": "idx:0", "weekday": dzis}]}).status_code == 404
    assert seeded.delete(DNI.format(cid_a, plan_b["id"]), headers=ha).status_code == 404
    # Szablon trenera (bez klienta) pod client_id → 404.
    hc = login(seeded, COACH)
    szablon = seeded.get("/api/plans/templates", headers=hc).json()["templates"][0]
    assert seeded.get(DNI.format(cid_a, szablon["id"]), headers=ha).status_code == 404
    # Nieistniejący plan → 404.
    assert seeded.get(DNI.format(cid_a, "HOS-PLN-000000000000"), headers=ha).status_code == 404
    with SessionLocal() as db:
        assert db.query(PlanWeekdayChoice).count() == 0
    # Własny plan działa.
    assert seeded.get(DNI.format(cid_a, plan_a["id"]), headers=ha).status_code == 200


def test_trener_z_relacja_i_zgoda_potem_bez_zgody(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid, coach_id = get_user_id(seeded, ha), get_user_id(seeded, hc)
    plan = _plan_klienta(seeded, ha, cid)
    url = DNI.format(cid, plan["id"])
    dzis = _dzis()
    assert seeded.get(url, headers=hc).status_code == 200
    r = seeded.put(url, headers=hc, json={"choices": [{"day_key": "idx:1", "weekday": dzis}], "author_note": "Ustawione na konsultacji"})
    assert r.status_code == 200 and r.json()["author_id"] == coach_id and r.json()["source"] == "client"
    # Klient widzi układ ustawiony przez trenera i „Dzisiaj” go respektuje.
    assert seeded.get(url, headers=ha).json()["author_id"] == coach_id
    t = seeded.get("/api/me/today", headers=ha).json()
    assert t["workout"]["day"]["name"] == "Trening B — dół" and t["workout"]["weekday_source"] == "client"
    # Cofnięcie zgody treningowej: trener traci odczyt i zapis, klient nie.
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    tren = next(x for x in consents if x["revoked_at"] is None and x["category"] == "dane_treningowe")
    assert seeded.post(f"/api/me/consents/{tren['id']}/revoke", headers=ha).status_code == 200
    assert seeded.get(url, headers=hc).status_code in (403, 404)
    assert seeded.put(url, headers=hc, json={"choices": []}).status_code in (403, 404)
    assert seeded.delete(url, headers=hc).status_code in (403, 404)
    assert seeded.get(url, headers=ha).status_code == 200
    assert seeded.delete(url, headers=ha).json()["source"] == "coach"


def _plan_bez_dni(seeded, hc, cid, dni=("Jednostka 1", "Jednostka 2")):
    r = seeded.post("/api/plans", headers=hc, json={
        "client_id": cid, "title": "Plan bez dni",
        "version": {"reason": "Start", "days": [{"name": n, "weekday": None, "exercises": [
            {"name": "Przysiad", "sets": "3", "reps": "8"}]} for n in dni]},
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_dzisiaj_plan_bez_dni_karta_ustaw_dni(seeded):
    hc = login(seeded, COACH)
    cid = create_activated_client(seeded, hc, "bezdni@example.com")
    hn = login(seeded, {"email": "bezdni@example.com", "password": "WlasneHaslo#123"})
    plan_id = _plan_bez_dni(seeded, hc, cid)
    t = seeded.get("/api/me/today", headers=hn).json()
    # Domyślne (§8 pyt. 3): system nie zgaduje — bez treningu, ale z podpowiedzią „ustaw dni”.
    assert t["workout"] is None and t["workout_hint"] == {"kind": "no_weekdays", "plan_id": plan_id}
    d = seeded.get(DNI.format(cid, plan_id), headers=hn).json()
    assert d["source"] == "coach" and [x["weekday"] for x in d["days"]] == [None, None]
    dzis = _dzis()
    r = seeded.put(DNI.format(cid, plan_id), headers=hn, json={"choices": [{"day_key": "idx:1", "weekday": dzis}]})
    assert r.status_code == 200, r.text
    t = seeded.get("/api/me/today", headers=hn).json()
    assert t["workout"]["day"]["name"] == "Jednostka 2" and t["workout"]["day_index"] == 1
    assert t["workout"]["weekday_source"] == "client" and t["workout_hint"] is None
    assert t["workout"]["done_today"] is False
    # Klucz `day_index` bez zmian: oznaczenie wykonania działa jak dotąd.
    r = seeded.post(f"/api/clients/{cid}/workouts", headers=hn, json={
        "plan_version_id": t["workout"]["plan_version_id"], "day_index": 1,
        "performed_on": t["date"], "status": "DONE", "entries": []})
    assert r.status_code == 201, r.text
    assert seeded.get("/api/me/today", headers=hn).json()["workout"]["done_today"] is True


def test_nowa_wersja_zachowuje_wybor_po_id_i_stale_keys(seeded):
    hc = login(seeded, COACH)
    cid = create_activated_client(seeded, hc, "wersje@example.com")
    hn = login(seeded, {"email": "wersje@example.com", "password": "WlasneHaslo#123"})
    dzis = _dzis()
    r = seeded.post("/api/plans", headers=hc, json={
        "client_id": cid, "title": "Plan ze stabilnymi id",
        "version": {"reason": "Start", "days": [
            {"id": "ELM-A", "name": "A", "weekday": None, "exercises": []},
            {"id": "ELM-B", "name": "B", "weekday": None, "exercises": []}]},
    })
    plan_id = r.json()["id"]
    d = seeded.put(DNI.format(cid, plan_id), headers=hn, json={"choices": [{"day_key": "ELM-A", "weekday": dzis}]}).json()
    assert [x["day_key"] for x in d["days"]] == ["ELM-A", "ELM-B"]
    # Trener publikuje v2: A zostaje (zmieniona nazwa), B znika, dochodzi C.
    r = seeded.post(f"/api/plans/{plan_id}/versions", headers=hc, json={"reason": "Korekta", "days": [
        {"id": "ELM-A", "name": "A2", "weekday": None, "exercises": []},
        {"id": "ELM-C", "name": "C", "weekday": None, "exercises": []}]})
    assert r.status_code == 201, r.text
    d = seeded.get(DNI.format(cid, plan_id), headers=hn).json()
    assert d["version_no"] == 2 and d["source"] == "client" and d["stale_keys"] == ["ELM-B"]
    assert {x["day_key"]: x["weekday"] for x in d["days"]} == {"ELM-A": dzis, "ELM-C": None}
    t = seeded.get("/api/me/today", headers=hn).json()
    assert t["workout"]["day"]["name"] == "A2" and t["workout_hint"] == {"kind": "stale", "plan_id": plan_id}
    # Ponowny zapis (klient „sprawdził dni”) czyści nieaktualne klucze.
    d = seeded.put(DNI.format(cid, plan_id), headers=hn, json={"choices": [{"day_key": "ELM-A", "weekday": dzis}]}).json()
    assert d["stale_keys"] == []
    assert seeded.get("/api/me/today", headers=hn).json()["workout_hint"] is None


def test_eksport_usuniecie_konta_i_audyt(seeded):
    hb = login(seeded, CLIENT_B)
    cid = get_user_id(seeded, hb)
    plan = _plan_klienta(seeded, hb, cid)
    url = DNI.format(cid, plan["id"])
    assert seeded.put(url, headers=hb, json={"choices": [{"day_key": "idx:0", "weekday": 1}]}).status_code == 200
    ex = seeded.get("/api/me/export", headers=hb).json()
    assert ex["export_version"] == "2.0" and len(ex["plan_weekday_choices"]) == 1
    assert ex["plan_weekday_choices"][0]["plan_id"] == plan["id"]
    assert seeded.delete(url, headers=hb).status_code == 200
    assert seeded.put(url, headers=hb, json={"choices": [{"day_key": "idx:1", "weekday": 2}]}).status_code == 200
    with SessionLocal() as db:
        akcje = [r for r in db.query(Receipt).filter(Receipt.action.like("PLAN_WEEKDAYS_%")).all()]
        assert {r.action for r in akcje} == {"PLAN_WEEKDAYS_SET", "PLAN_WEEKDAYS_CLEARED"}
        assert all(r.actor_id == cid and r.subject_id == cid for r in akcje)
        assert not any("FBW" in r.summary for r in akcje)  # bez treści planu
    r = seeded.post("/api/me/deletion-request", headers=hb,
                    json={"password": CLIENT_B["password"], "confirm": "USUŃ MOJE DANE"})
    assert r.status_code in (200, 202), r.text
    with SessionLocal() as db:
        assert db.query(PlanWeekdayChoice).filter_by(client_id=cid).count() == 0

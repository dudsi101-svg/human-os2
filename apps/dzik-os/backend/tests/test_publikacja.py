"""Panel trenera (0.58.0): szkice, różnice, publikacja z podsumowaniem,
outbox, idempotencja, konflikty — 17 scenariuszy akceptacyjnych
specyfikacji właściciela (13.09) + testy jednostkowe różnic.

Numeracja `A1…A17` odpowiada liście „Testy akceptacyjne” w specyfikacji.
"""

from __future__ import annotations

import json
import uuid

import pytest
from conftest import CLIENT_A, CLIENT_B, COACH, create_user_with_role, get_user_id, login

from dzik_os.db import SessionLocal
from dzik_os.models import ChangeSet, Notification, OutboxEvent, PlanDraft
from dzik_os.publikacja import elementy, roznice

# --- pomocnicze -------------------------------------------------------------------------


def _plan_klienta(seeded, hc, cid):
    plans = seeded.get(f"/api/clients/{cid}/plans", headers=hc).json()["plans"]
    return next(p for p in plans if not p["is_template"] and p["status"] == "ACTIVE")


def _szkic(seeded, hc, plan_id, kind="training"):
    r = seeded.post(f"/api/szkice/plan/{kind}/{plan_id}", headers=hc)
    assert r.status_code in (200, 201), r.text
    return r.json()


def _ops(seeded, hc, szkic, ops, expect=200):
    r = seeded.patch(f"/api/szkice/{szkic['id']}", headers=hc,
                     json={"revision": szkic["revision"], "operations": ops})
    assert r.status_code == expect, r.text
    return r.json()


def _publikuj(seeded, hc, szkic, note=None, key=None, expect=200):
    body = {"revision": szkic["revision"], "base_version_no": szkic["base_version_no"], "note": note}
    if key:
        body["idempotency_key"] = key
    r = seeded.post(f"/api/szkice/{szkic['id']}/publikuj", headers=hc, json=body)
    assert r.status_code == expect, r.text
    return r.json()


def _wpisy(seeded, headers, category="ZMIANA_PLANU"):
    return [n for n in seeded.get("/api/notifications", headers=headers).json()["notifications"]
            if n["category"] == category]


def _liczby(plan_id):
    with SessionLocal() as db:
        return (db.query(ChangeSet).filter_by(plan_id=plan_id).count(),
                db.query(OutboxEvent).count(),
                db.query(PlanDraft).filter_by(plan_id=plan_id, status="ACTIVE").count())


def _pierwszy_dzien(szkic):
    return szkic["content"]["days"][0]


# --- jednostkowe: elementy i różnice ------------------------------------------------


def test_roznice_po_id_nie_po_pozycji_i_podsumowanie():
    baza = elementy.znormalizuj("training", {"days": [
        {"name": "A", "exercises": [{"name": "Przysiad", "sets": "3"}, {"name": "Wyciskanie", "sets": "3"}]},
        {"name": "B", "exercises": [{"name": "Martwy", "sets": "3"}]},
    ]})
    nowa = json.loads(json.dumps(baza))
    d0 = nowa["days"][0]
    d0["exercises"][0]["sets"] = "4"                     # zmiana pola
    d0["exercises"].reverse()                            # przestawienie
    nowa["days"].pop(1)                                  # usunięcie dnia (z dzieckiem)
    nowa["days"].append({"id": "ELM-NOWY", "name": "C", "exercises": []})  # dodanie
    r = roznice.porownaj("training", baza, nowa)
    assert r["counts"] == {"added": 1, "removed": 1, "changed": 1, "moved": 2, "root": 0}
    assert r["removed"][0]["label"] == "B" and r["removed"][0]["children"] == 1
    assert r["changed"][0]["fields"] == [{"field": "sets", "before": "3", "after": "4"}]
    assert roznice.podsumowanie("training", r) == (
        "Zmieniono 1 ćwiczenie, dodano 1 dzień, usunięto 1 dzień i przestawiono 2 ćwiczenia.")
    # dodanie + usunięcie tego samego = brak zmian
    nowa2 = json.loads(json.dumps(baza))
    nowa2["days"].append({"id": "ELM-TMP", "name": "X", "exercises": []})
    nowa2["days"].pop()
    assert roznice.czy_puste(roznice.porownaj("training", baza, nowa2))


def test_operacje_odmowa_niedozwolonych_pol_i_duplikat_z_nowymi_id():
    tresc = elementy.znormalizuj("training", {"days": [{"name": "A", "exercises": [{"name": "X"}]}]})
    d = tresc["days"][0]
    with pytest.raises(elementy.BladOperacji):
        elementy.zastosuj("training", tresc, [{"op": "set", "id": d["id"], "fields": {"haslo": 1}}])
    with pytest.raises(elementy.BladOperacji):
        elementy.zastosuj("training", tresc, [{"op": "set", "fields": {"kcal": 1}}])  # nie w treningu
    out = elementy.zastosuj("training", tresc, [{"op": "duplicate", "id": d["id"]}])
    assert len(out["days"]) == 2 and out["days"][1]["id"] != d["id"]
    assert out["days"][1]["exercises"][0]["id"] != d["exercises"][0]["id"]
    assert out["days"][1]["exercises"][0]["name"] == "X"


# --- A1: kopia z szablonu niezależna ----------------------------------------------------


def test_a1_edycja_kopii_nie_zmienia_szablonu_ani_innej_kopii(seeded):
    hc = login(seeded, COACH)
    cid_a = get_user_id(seeded, login(seeded, CLIENT_A))
    cid_b = get_user_id(seeded, login(seeded, CLIENT_B))
    tpl = seeded.get("/api/plans/templates", headers=hc).json()["templates"][0]
    tpl_tresc = tpl["current_version"]["content"]
    pa = seeded.post(f"/api/plans/{tpl['id']}/copy-to/{cid_a}", headers=hc).json()["id"]
    pb = seeded.post(f"/api/plans/{tpl['id']}/copy-to/{cid_b}", headers=hc).json()["id"]
    szkic = _szkic(seeded, hc, pa)
    d = _pierwszy_dzien(szkic)
    ex = d["exercises"][0]
    szkic = _ops(seeded, hc, szkic, [
        {"op": "set", "id": ex["id"], "fields": {"name": "Zamienione ćwiczenie", "exercise_id": None}},
        {"op": "delete", "id": d["exercises"][-1]["id"]},
    ])
    wynik = _publikuj(seeded, hc, szkic, note="Kolano — zamiana")
    assert wynik["published"] and wynik["version_no"] == 2
    # Oryginał i kopia B nietknięte; pochodzenie zapisane.
    tpl2 = next(t for t in seeded.get("/api/plans/templates", headers=hc).json()["templates"] if t["id"] == tpl["id"])
    assert tpl2["current_version"]["content"] == tpl_tresc and tpl2["current_version_no"] == tpl["current_version_no"]
    wb = seeded.get(f"/api/plans/{pb}/versions", headers=hc).json()["versions"]
    assert len(wb) == 1 and wb[0]["content"]["days"][0]["exercises"][0]["name"] == tpl_tresc["days"][0]["exercises"][0]["name"]
    wa = seeded.get(f"/api/plans/{pa}/versions", headers=hc).json()["versions"]
    assert wa[-1]["content"]["days"][0]["exercises"][0]["name"] == "Zamienione ćwiczenie"
    with SessionLocal() as db:
        from dzik_os.models import TrainingPlanVersion
        v1 = db.query(TrainingPlanVersion).filter_by(plan_id=pa, version_no=1).one()
        assert v1.source_template_id == tpl["id"] and v1.source_template_version_no == tpl["current_version_no"]
    # Zamiana zapisana w różnicach jako stare i nowe odniesienie.
    z = seeded.get(f"/api/plany/training/{pa}/zmiany", headers=hc).json()["changes"][0]
    pelna = seeded.get(f"/api/zmiany/{z['id']}", headers=hc).json()
    pola = {f["field"]: (f["before"], f["after"]) for f in pelna["diff"]["changed"][0]["fields"]}
    assert pola["name"][1] == "Zamienione ćwiczenie" and "exercise_id" in pola


# --- A2: każdy typ elementu edytowalny i usuwalny (klient + szablon + dieta) --------


def test_a2_kazdy_typ_elementu_ma_edycje_i_usuwanie(seeded):
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, login(seeded, CLIENT_A))
    # Trening klienta: dzień i ćwiczenie.
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    d0, d1 = szkic["content"]["days"][0], szkic["content"]["days"][1]
    szkic = _ops(seeded, hc, szkic, [
        {"op": "set", "fields": {"title": "Plan po zmianie nazwy"}},
        {"op": "set", "id": d0["id"], "fields": {"name": "Dzień A2"}},
        {"op": "set", "id": d0["exercises"][0]["id"], "fields": {"sets": "5", "reps": "5", "weight": "90 kg",
                                                                  "rest": "180 s", "tempo": "2010", "target_rir": "2"}},
        {"op": "add", "collection": "exercises", "parent_id": d0["id"], "item": {"name": "Nowe ćwiczenie", "sets": "3"}, "index": 0},
        {"op": "move", "id": d0["exercises"][0]["id"], "index": 99},
        {"op": "duplicate", "id": d1["id"]},
        {"op": "delete", "id": d1["id"]},
        {"op": "add", "collection": "days", "item": {"name": "Nowy dzień", "exercises": [{"name": "Rower", "sets": "1", "reps": "20 min"}]}},
    ])
    r = seeded.get(f"/api/szkice/{szkic['id']}/roznice", headers=hc).json()
    assert r["counts"]["root"] == 1 and r["counts"]["removed"] == 1 and r["counts"]["added"] >= 2
    wynik = _publikuj(seeded, hc, szkic)
    assert wynik["published"]
    plany = seeded.get(f"/api/clients/{cid}/plans", headers=hc).json()["plans"]
    p = next(x for x in plany if x["id"] == plan["id"])
    assert p["title"] == "Plan po zmianie nazwy" and p["current_version"]["content"]["days"][0]["name"] == "Dzień A2"
    # Szablon treningowy: szkic → publikacja bez klienta = bez powiadomienia.
    tpl = seeded.get("/api/plans/templates", headers=hc).json()["templates"][0]
    st = _szkic(seeded, hc, tpl["id"])
    st = _ops(seeded, hc, st, [{"op": "delete", "id": st["content"]["days"][0]["exercises"][0]["id"]}])
    w2 = _publikuj(seeded, hc, st)
    assert w2["published"] and w2["outbox_event_id"] is None
    # Dieta: sekcja, posiłek, suplement.
    dieta = seeded.get(f"/api/clients/{cid}/nutrition", headers=hc).json()["plans"][0]
    sd = _szkic(seeded, hc, dieta["id"], "nutrition")
    c = sd["content"]
    ops = [{"op": "set", "fields": {"kcal": 2100}},
           {"op": "add", "collection": "sections", "item": {"title": "Nawodnienie", "body": "2,5 l dziennie"}},
           {"op": "add", "collection": "supplements", "item": {"name": "Witamina D", "dose": "2000 IU", "timing": "rano",
                                                                "purpose": "uzupełnienie", "source": "zalecenie lekarza"}}]
    if c["meals"]:
        ops.append({"op": "set", "id": c["meals"][0]["id"], "fields": {"description": "Zmieniony opis"}})
        ops.append({"op": "delete", "id": c["meals"][-1]["id"]})
    if c["sections"]:
        ops.append({"op": "delete", "id": c["sections"][0]["id"]})
    sd = _ops(seeded, hc, sd, ops)
    w3 = _publikuj(seeded, hc, sd)
    assert w3["published"]
    v = seeded.get(f"/api/clients/{cid}/nutrition", headers=hc).json()["plans"][0]["current_version"]["content"]
    assert v["kcal"] == 2100 and any(s["title"] == "Nawodnienie" for s in v["sections"])
    assert any(s["name"] == "Witamina D" for s in v["supplements"])
    # Archiwizacja ≠ odpięcie: osobne działania, historia zostaje.
    pd = seeded.post(f"/api/plans/{plan['id']}/duplikuj", headers=hc).json()
    assert seeded.post(f"/api/plans/{pd['id']}/odepnij", headers=hc).json()["status"] == "UNASSIGNED"
    assert seeded.post(f"/api/plans/{pd['id']}/archiwizuj", headers=hc).json()["status"] == "ARCHIVED"
    assert len(seeded.get(f"/api/plans/{plan['id']}/versions", headers=hc).json()["versions"]) >= 3


# --- A3: usunięcie dnia i cofnięcie ----------------------------------------------------


def test_a3_usuniecie_dnia_i_cofniecie_przywraca_strukture_i_kolejnosc(seeded):
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, login(seeded, CLIENT_A))
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    dzien = szkic["content"]["days"][0]
    r = seeded.delete(f"/api/szkice/{szkic['id']}/elementy/{dzien['id']}", headers=hc,
                      params={"revision": szkic["revision"]})
    assert r.status_code == 200, r.text
    usuniete = r.json()["removed"]
    assert usuniete["index"] == 0 and usuniete["count"] == 1 + len(dzien["exercises"])
    assert r.json()["changes"] >= 1
    # Cofnij: ten sam element (z id i dziećmi) wraca na tę samą pozycję.
    szkic2 = _ops(seeded, hc, r.json(), [{"op": "add", "collection": "days", "item": usuniete["item"], "index": usuniete["index"]}])
    assert szkic2["changes"] == 0 and szkic2["content"]["days"][0]["id"] == dzien["id"]
    assert [e["id"] for e in szkic2["content"]["days"][0]["exercises"]] == [e["id"] for e in dzien["exercises"]]


# --- A4: szkic przetrwa odświeżenie, klient widzi stary plan, brak powiadomień -------


def test_a4_szkic_trwaly_klient_nie_widzi_brak_powiadomien(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_klienta(seeded, hc, cid)
    przed = len(_wpisy(seeded, ha))
    szkic = _szkic(seeded, hc, plan["id"])
    d = szkic["content"]["days"][0]
    for i in range(10):
        szkic = _ops(seeded, hc, szkic, [{"op": "set", "id": d["exercises"][0]["id"], "fields": {"sets": str(i + 1)}}])
    # „Odświeżenie” = ponowne pobranie aktywnego szkicu.
    ponownie = seeded.get(f"/api/szkice/plan/training/{plan['id']}/aktywny", headers=hc).json()["draft"]
    assert ponownie["id"] == szkic["id"] and ponownie["revision"] == 11
    assert ponownie["content"]["days"][0]["exercises"][0]["sets"] == "10"
    # Klient: stary plan, bez wpisów.
    klient = next(p for p in seeded.get(f"/api/clients/{cid}/plans", headers=ha).json()["plans"] if p["id"] == plan["id"])
    assert klient["current_version_no"] == plan["current_version_no"]
    assert klient["current_version"]["content"]["days"][0]["exercises"][0]["sets"] != "10"
    assert len(_wpisy(seeded, ha)) == przed
    assert _liczby(plan["id"])[1] == 0


# --- A5: publikacja = nowa wersja + jedno podsumowanie + jeden wpis -------------------


def test_a5_publikacja_jedno_podsumowanie_i_jeden_wpis(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    d, d1 = szkic["content"]["days"][0], szkic["content"]["days"][1]
    szkic = _ops(seeded, hc, szkic, [
        {"op": "set", "id": d["exercises"][0]["id"], "fields": {"sets": "5"}},
        {"op": "set", "id": d["exercises"][1]["id"], "fields": {"reps": "12"}},
        {"op": "delete", "id": d1["exercises"][-1]["id"]},
        {"op": "add", "collection": "exercises", "parent_id": d["id"], "item": {"name": "Plank", "sets": "3", "reps": "40 s"}},
    ])
    w = _publikuj(seeded, hc, szkic, note="Po raporcie z tygodnia 3")
    assert w["published"] and w["summary"] == "Zmieniono 2 ćwiczenia, dodano 1 ćwiczenie i usunięto 1 ćwiczenie."
    wpisy = [n for n in _wpisy(seeded, ha) if n["url"] == f"/zmiany/{w['changeset_id']}"]
    assert len(wpisy) == 1 and "Zmieniono 2 ćwiczenia" in wpisy[0]["body"] and "Zobacz zmiany" in wpisy[0]["body"]
    z = seeded.get(f"/api/zmiany/{w['changeset_id']}", headers=ha).json()
    assert z["note"] == "Po raporcie z tygodnia 3" and z["new_version_no"] == plan["current_version_no"] + 1
    assert {x["label"] for x in z["diff"]["removed"]} == {d1["exercises"][-1]["name"]}
    assert z["diff"]["added"][0]["label"] == "Plank" and z["notification"] is None  # klient nie widzi stanu doręczenia
    assert z["plan_url"] == "/plan"
    # Trener widzi doręczenie i (jeszcze) brak odczytu; odczyt = kliknięcie wpisu.
    zt = seeded.get(f"/api/zmiany/{w['changeset_id']}", headers=hc).json()
    assert zt["notification"]["id"] and zt["notification"]["read_at"] is None
    seeded.post(f"/api/notifications/{wpisy[0]['id']}/read", headers=ha)
    assert seeded.get(f"/api/zmiany/{w['changeset_id']}", headers=hc).json()["notification"]["read_at"]
    # Klient widzi nową wersję; powód wersji = podsumowanie + notatka.
    p = next(x for x in seeded.get(f"/api/clients/{cid}/plans", headers=ha).json()["plans"] if x["id"] == plan["id"])
    assert p["current_version_no"] == plan["current_version_no"] + 1
    assert "Notatka trenera: Po raporcie" in p["current_version"]["reason"]


# --- A6: podwójne kliknięcie / ponowienie -------------------------------------------


def test_a6_idempotencja_publikacji(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    d = szkic["content"]["days"][0]
    szkic = _ops(seeded, hc, szkic, [{"op": "set", "id": d["exercises"][0]["id"], "fields": {"sets": "6"}}])
    klucz = "pub-" + uuid.uuid4().hex[:12]
    w1 = _publikuj(seeded, hc, szkic, key=klucz)
    w2 = _publikuj(seeded, hc, szkic, key=klucz)
    assert w1 == w2 and w1["published"]
    wersje = seeded.get(f"/api/plans/{plan['id']}/versions", headers=hc).json()["versions"]
    assert wersje[-1]["version_no"] == plan["current_version_no"] + 1
    assert len([n for n in _wpisy(seeded, ha) if n["url"] == f"/zmiany/{w1['changeset_id']}"]) == 1
    assert _liczby(plan["id"])[0] == 1
    # Ten sam klucz z inną treścią → 409.
    r = seeded.post(f"/api/szkice/{szkic['id']}/publikuj", headers=hc,
                    json={"revision": szkic["revision"], "base_version_no": szkic["base_version_no"],
                          "note": "inna", "idempotency_key": klucz})
    assert r.status_code == 409


# --- A7: dodaję i usuwam ten sam element -----------------------------------------------


def test_a7_dodanie_i_usuniecie_tego_samego_to_brak_zmian(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_klienta(seeded, hc, cid)
    przed = len(_wpisy(seeded, ha))
    szkic = _szkic(seeded, hc, plan["id"])
    szkic = _ops(seeded, hc, szkic, [{"op": "add", "collection": "days", "item": {"name": "Tymczasowy", "exercises": []}}])
    nowy = szkic["content"]["days"][-1]["id"]
    szkic = _ops(seeded, hc, szkic, [{"op": "delete", "id": nowy}])
    assert szkic["changes"] == 0
    w = _publikuj(seeded, hc, szkic)
    assert w == {"published": False, "reason": "no_changes", "version_no": plan["current_version_no"], "summary": "Bez zmian."}
    assert len(_wpisy(seeded, ha)) == przed and _liczby(plan["id"])[0] == 0


# --- A8: dwa urządzenia / stara wersja bazowa ---------------------------------------


def test_a8_konflikt_rewizji_i_wersji_bazowej_zachowuje_szkic(seeded):
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, login(seeded, CLIENT_A))
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    d = szkic["content"]["days"][0]
    urz1 = _ops(seeded, hc, szkic, [{"op": "set", "id": d["exercises"][0]["id"], "fields": {"sets": "7"}}])
    # Urządzenie 2 działa na starej rewizji → 409, nic nie nadpisane.
    r = seeded.patch(f"/api/szkice/{szkic['id']}", headers=hc,
                     json={"revision": szkic["revision"], "operations": [{"op": "set", "id": d["exercises"][0]["id"], "fields": {"sets": "1"}}]})
    assert r.status_code == 409 and r.json()["code"] == "REVISION_CONFLICT" and r.json()["current_revision"] == urz1["revision"]
    assert seeded.get(f"/api/szkice/{szkic['id']}", headers=hc).json()["content"]["days"][0]["exercises"][0]["sets"] == "7"
    # Plan dostał w międzyczasie nową wersję (stara ścieżka) → publikacja 409, szkic zostaje.
    seeded.post(f"/api/plans/{plan['id']}/versions", headers=hc, json={"reason": "równoległa zmiana", "days": [
        {"name": "Inny", "weekday": 2, "exercises": [{"name": "Przysiad", "sets": "3", "reps": "8"}]}]})
    r = seeded.post(f"/api/szkice/{szkic['id']}/publikuj", headers=hc,
                    json={"revision": urz1["revision"], "base_version_no": urz1["base_version_no"]})
    assert r.status_code == 409 and r.json()["code"] == "BASE_VERSION_CONFLICT"
    assert seeded.get(f"/api/szkice/{szkic['id']}", headers=hc).json()["status"] == "ACTIVE"
    assert seeded.get(f"/api/szkice/{szkic['id']}/roznice", headers=hc).json()["stale_base"] is True


# --- A9 / A10: wykonania wskazują wersję ----------------------------------------------


def test_a9_a10_wykonanie_zwiazane_z_wersja_przetrwa_publikacje(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_klienta(seeded, hc, cid)
    stara_wersja = plan["current_version"]
    d0 = stara_wersja["content"]["days"][0]
    # Wczoraj wykonane ćwiczenie (na starej wersji).
    r = seeded.post(f"/api/clients/{cid}/workouts", headers=ha, json={
        "plan_version_id": stara_wersja["id"], "day_index": 0, "performed_on": "2026-09-12", "status": "DONE",
        "entries": [{"exercise_index": 0, "exercise_name": d0["exercises"][0]["name"], "result": "3x8 @ 80"}]})
    assert r.status_code == 201, r.text
    szkic = _szkic(seeded, hc, plan["id"])
    ex_id = szkic["content"]["days"][0]["exercises"][0]["id"]
    szkic = _ops(seeded, hc, szkic, [{"op": "delete", "id": ex_id}])
    w = _publikuj(seeded, hc, szkic)
    assert w["published"]
    # A10: klient kończy trening rozpoczęty na starej wersji — zapis przyjęty i powiązany ze starą wersją.
    r2 = seeded.post(f"/api/clients/{cid}/workouts", headers=ha, json={
        "plan_version_id": stara_wersja["id"], "day_index": 0, "performed_on": "2026-09-13", "status": "DONE",
        "entries": [{"exercise_index": 0, "exercise_name": d0["exercises"][0]["name"], "result": "3x8 @ 82"}]})
    assert r2.status_code == 201, r2.text
    treningi = seeded.get(f"/api/clients/{cid}/workouts", headers=hc).json()["workouts"]
    moje = [t for t in treningi if t["id"] in (r.json()["id"], r2.json()["id"])]
    assert len(moje) == 2 and all(t["plan_version_id"] == stara_wersja["id"] for t in moje)
    assert all(d0["exercises"][0]["name"] in json.dumps(t, ensure_ascii=False) for t in moje)
    # Stara wersja nadal dostępna w historii z usuniętym ćwiczeniem.
    wersje = seeded.get(f"/api/plans/{plan['id']}/versions", headers=ha).json()["versions"]
    stara = next(v for v in wersje if v["id"] == stara_wersja["id"])
    assert stara["content"]["days"][0]["exercises"][0]["name"] == d0["exercises"][0]["name"]


# --- A11: awaria między publikacją a doręczeniem ----------------------------------------


def test_a11_outbox_ponawia_bez_duplikatu(seeded, monkeypatch):
    from dzik_os import notifications as mod_notif

    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    d = szkic["content"]["days"][0]
    szkic = _ops(seeded, hc, szkic, [{"op": "set", "id": d["exercises"][0]["id"], "fields": {"weight": "85 kg"}}])
    oryginal = mod_notif.notify_now

    def awaria(*a, **k):
        raise RuntimeError("awaria doręczenia")

    monkeypatch.setattr(mod_notif, "notify_now", awaria)
    w = _publikuj(seeded, hc, szkic)
    assert w["published"]
    with SessionLocal() as db:
        ev = db.get(OutboxEvent, w["outbox_event_id"])
        assert ev.status == "PENDING" and ev.attempts == 1 and "awaria" in ev.last_error
    assert not [n for n in _wpisy(seeded, ha) if n["url"] == f"/zmiany/{w['changeset_id']}"]
    monkeypatch.setattr(mod_notif, "notify_now", oryginal)
    from datetime import UTC, datetime, timedelta

    from dzik_os.publikacja import serwis
    with SessionLocal() as db:
        n1 = serwis.przetworz_outbox(db, now_utc=datetime.now(UTC) + timedelta(hours=1))
        db.commit()
        n2 = serwis.przetworz_outbox(db, now_utc=datetime.now(UTC) + timedelta(hours=3))
        db.commit()
        ev = db.get(OutboxEvent, w["outbox_event_id"])
        assert ev.status == "DELIVERED" and len(n1) == 1 and n2 == []
    assert len([n for n in _wpisy(seeded, ha) if n["url"] == f"/zmiany/{w['changeset_id']}"]) == 1


# --- A12: błąd transakcji publikacji ------------------------------------------------------


def test_a12_blad_publikacji_nie_zostawia_wersji_zestawu_ani_zdarzenia(seeded):
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, login(seeded, CLIENT_A))
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    ids = [d["id"] for d in szkic["content"]["days"]]
    szkic = _ops(seeded, hc, szkic, [{"op": "delete", "id": i} for i in ids])  # pusty plan
    r = seeded.post(f"/api/szkice/{szkic['id']}/publikuj", headers=hc,
                    json={"revision": szkic["revision"], "base_version_no": szkic["base_version_no"]})
    assert r.status_code == 422 and "archiwizacj" in r.json()["detail"]
    assert _liczby(plan["id"]) == (0, 0, 1)
    assert seeded.get(f"/api/plans/{plan['id']}/versions", headers=hc).json()["versions"][-1]["version_no"] == plan["current_version_no"]


# --- A13: push wyłączony / cudze konto --------------------------------------------------


def test_a13_wpis_w_centrum_bez_push_i_odmowa_dla_innego_konta(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    cid = get_user_id(seeded, ha)
    # Klient wyłącza push dla zmian planu.
    seeded.put("/api/notifications/settings", headers=ha, json={"preferences": [
        {"category": "ZMIANA_PLANU", "channel": "PUSH", "enabled": False}]})
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    d = szkic["content"]["days"][0]
    szkic = _ops(seeded, hc, szkic, [{"op": "set", "id": d["exercises"][0]["id"], "fields": {"comment": "spokojne tempo"}}])
    w = _publikuj(seeded, hc, szkic)
    wpis = [n for n in _wpisy(seeded, ha) if n["url"] == f"/zmiany/{w['changeset_id']}"]
    assert len(wpis) == 1
    with SessionLocal() as db:
        n = db.get(Notification, wpis[0]["id"])
        assert "center" in n.channels and "push" not in (n.channels or "")
    assert seeded.get(f"/api/zmiany/{w['changeset_id']}", headers=hb).status_code == 404
    assert seeded.get(f"/api/plany/training/{plan['id']}/zmiany", headers=hb).status_code == 404
    assert seeded.post(f"/api/notifications/{wpis[0]['id']}/read", headers=hb).status_code == 404


# --- A14: ręczna zmiana posiłku z kreatora dań --------------------------------------------


def test_a14_reczna_zmiana_posilku_uniewaznia_wartosci_i_walidacje(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    # Menu z kreatora dań jako wersja diety (podgląd ze szkiców, potwierdzony).
    r = seeded.post("/api/coach/kulinaria/zapisz", headers=hc, json={
        "tryb": "preview", "days": 1, "meal_count": 3, "animal_policy": "omnivore", "pattern": "balanced",
        "carb_policy": "standard", "client_id": cid, "potwierdzam_szkice": True,
        "zakres": {"adult": True, "no_pregnancy_or_breastfeeding": True, "no_medical_diet": True,
                   "no_glucose_meds_or_diabetes": True}})
    assert r.status_code == 201, r.text
    dieta_id = r.json()["id"]
    szkic = _szkic(seeded, hc, dieta_id, "nutrition")
    posilek = szkic["content"]["meals"][0]
    assert posilek["recipe_id"] and not posilek.get("edited_manually")
    szkic = _ops(seeded, hc, szkic, [{"op": "set", "id": posilek["id"], "fields": {"description": "Składniki: bez orzechów — zamieniono na pestki"}}])
    m = szkic["content"]["meals"][0]
    assert m["edited_manually"] is True and m["nutrition"] is None and m["draft"] is True
    w = _publikuj(seeded, hc, szkic)
    assert w["published"]
    v = seeded.get(f"/api/clients/{cid}/nutrition", headers=ha).json()["plans"]
    tresc = next(p for p in v if p["id"] == dieta_id)["current_version"]["content"]
    assert tresc["meals"][0]["edited_manually"] is True and tresc["meals"][0]["nutrition"] is None
    assert tresc["kulinaria"]["edited_manually"] is True and tresc["kulinaria"]["carb_compliance_verified"] is False


# --- A15: inny trener ------------------------------------------------------------------


def test_a15_inny_trener_nie_edytuje_cudzego_planu(seeded):
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, login(seeded, CLIENT_A))
    plan = _plan_klienta(seeded, hc, cid)
    create_user_with_role("obcy.trener@example.com", "ObcyTrener#2026!", "Obcy Trener", "COACH")
    ho = login(seeded, {"email": "obcy.trener@example.com", "password": "ObcyTrener#2026!"})
    assert seeded.post(f"/api/szkice/plan/training/{plan['id']}", headers=ho).status_code == 404
    szkic = _szkic(seeded, hc, plan["id"])
    assert seeded.get(f"/api/szkice/{szkic['id']}", headers=ho).status_code == 404
    assert seeded.patch(f"/api/szkice/{szkic['id']}", headers=ho,
                        json={"revision": 1, "operations": [{"op": "set", "fields": {"title": "x"}}]}).status_code == 404
    assert seeded.post(f"/api/szkice/{szkic['id']}/publikuj", headers=ho,
                       json={"revision": 1, "base_version_no": szkic["base_version_no"]}).status_code == 404
    assert seeded.post(f"/api/plans/{plan['id']}/archiwizuj", headers=ho).status_code == 404
    ha = login(seeded, CLIENT_A)
    assert seeded.post(f"/api/szkice/plan/training/{plan['id']}", headers=ha).status_code in (403, 404)


# --- A16: migracja nie wysyła powiadomień ---------------------------------------------


def test_a16_migracja_i_seed_nie_tworza_zdarzen_ani_wpisow(seeded):
    ha = login(seeded, CLIENT_A)
    with SessionLocal() as db:
        assert db.query(OutboxEvent).count() == 0 and db.query(ChangeSet).count() == 0
        assert db.query(PlanDraft).count() == 0
    assert not _wpisy(seeded, ha)


# --- A17: cofnięcie opublikowanej zmiany -------------------------------------------------


def test_a17_cofniecie_publikacji_tworzy_nowa_wersje_i_nowe_podsumowanie(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plan = _plan_klienta(seeded, hc, cid)
    szkic = _szkic(seeded, hc, plan["id"])
    d = szkic["content"]["days"][0]
    szkic = _ops(seeded, hc, szkic, [{"op": "delete", "id": d["exercises"][0]["id"]}])
    w1 = _publikuj(seeded, hc, szkic, note="usuwam")
    # Cofnięcie = nowy szkic z treścią poprzedniej wersji (przez replace) → publikacja.
    wersje = seeded.get(f"/api/plans/{plan['id']}/versions", headers=hc).json()["versions"]
    poprzednia = next(v for v in wersje if v["version_no"] == w1["version_no"] - 1)
    szkic2 = _szkic(seeded, hc, plan["id"])
    szkic2 = _ops(seeded, hc, szkic2, [{"op": "replace", "content": {**poprzednia["content"], "title": plan["title"]}}])
    assert szkic2["changes"] >= 1
    w2 = _publikuj(seeded, hc, szkic2, note="cofam")
    assert w2["published"] and w2["version_no"] == w1["version_no"] + 1
    zm = seeded.get(f"/api/plany/training/{plan['id']}/zmiany", headers=ha).json()["changes"]
    assert [z["id"] for z in zm][:2] == [w2["changeset_id"], w1["changeset_id"]]
    assert len(seeded.get(f"/api/plans/{plan['id']}/versions", headers=hc).json()["versions"]) == len(wersje) + 1
    assert len([n for n in _wpisy(seeded, ha) if n["url"].startswith("/zmiany/")]) == 2


# --- harmonogram i cele: edycja treści ---------------------------------------------------


def test_edycja_harmonogramu_i_celu_z_kontrola_wersji(seeded):
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, login(seeded, CLIENT_A))
    it = seeded.post("/api/schedule", headers=hc, json={"client_id": cid, "name": "Spacer", "category": "REGENERACJA",
                                                        "time_of_day": "18:00", "days_of_week": "1,3,5"}).json()
    r = seeded.put(f"/api/schedule/{it['id']}", headers=hc, json={"name": "Spacer 30 min", "category": "REGENERACJA",
                                                                    "time_of_day": "19:00", "days_of_week": "1,3,5",
                                                                    "instruction": "spokojnie", "version": 1})
    assert r.status_code == 200 and r.json()["version"] == 2
    r = seeded.put(f"/api/schedule/{it['id']}", headers=hc, json={"name": "X", "category": "REGENERACJA",
                                                                    "days_of_week": "1", "version": 1})
    assert r.status_code == 409
    items = seeded.get(f"/api/clients/{cid}/schedule", headers=hc).json()["items"]
    assert next(i for i in items if i["id"] == it["id"])["name"] == "Spacer 30 min"
    g = seeded.post(f"/api/clients/{cid}/goals", headers=hc, json={"title": "Cel", "kind": "SECONDARY"}).json()
    r = seeded.put(f"/api/clients/{cid}/goals/{g['id']}", headers=hc, json={"title": "Cel doprecyzowany", "kind": "SECONDARY",
                                                                             "target_date": "2026-12-01"})
    assert r.status_code == 200
    goals = seeded.get(f"/api/clients/{cid}/goals", headers=hc).json()["goals"]
    assert next(x for x in goals if x["id"] == g["id"])["title"] == "Cel doprecyzowany"

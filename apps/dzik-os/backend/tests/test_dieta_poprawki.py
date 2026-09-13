"""Poprawki po przeglądzie PR #57 (0.60.0): autoryzacja zapisu, dieta
zarchiwizowana, posiłek zastępczy tylko z profilu i publikacji, walidacja
korekt i importu, brak 500 na niekompletnych danych, wykluczenia po nazwie,
reguły zaokrąglania w migawce, blokada wymian per posiłek, RODO."""

from __future__ import annotations

import json

import pytest
from conftest import ADMIN, CLIENT_A, COACH, get_user_id, login

from dzik_os.db import SessionLocal, db_session
from dzik_os.dieta import seed
from dzik_os.models import ConsentRecord, DietAssigned, DietProduct, DietSwapEvent

D = "/api/diet"


@pytest.fixture()
def dieta(seeded):
    with db_session() as db:
        seed.zaseeduj(db)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    week = seeded.get(f"{D}/profiles", headers=hc).json()["profiles"][0]["weeks"][0]
    return {"c": seeded, "hc": hc, "ha": ha, "cid": get_user_id(seeded, ha), "coach_id": get_user_id(seeded, hc),
            "week": week["id"]}


def _assign(d, kcal=2000, **extra):
    body = {"client_id": d["cid"], "week_id": d["week"], "kcal": kcal, "macro": {"mode": "profile"}, **extra}
    r = d["c"].post(f"{D}/assign", headers=d["hc"], json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _obiad(a):
    m = a["plan"]["days"][0]["meals"][1]
    kur = next(i for i in m["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    return m, kur


# --- autoryzacja zapisu -------------------------------------------------------------------------


def test_zgoda_tylko_do_odczytu_blokuje_zapisy_trenera(dieta):
    c = dieta["c"]
    a = _assign(dieta)
    m, kur = _obiad(a)
    with db_session() as db:
        for zg in db.query(ConsentRecord).filter_by(subject_id=dieta["cid"], grantee_id=dieta["coach_id"]).all():
            zg.actions = "read"
    # Odczyt nadal działa, każdy zapis w diecie klienta — odmowa (404, bez ujawniania zasobu).
    assert c.get(f"{D}/clients/{dieta['cid']}/current", headers=dieta["hc"]).status_code == 200
    assert c.patch(f"{D}/assigned/{a['id']}", headers=dieta["hc"], json={"swaps_enabled": False}).status_code == 404
    assert c.patch(f"{D}/assigned/{a['id']}", headers=dieta["hc"],
                   json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "grams": 200}).status_code == 404
    assert c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["hc"],
                  json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "to_product_id": "x"}).status_code == 404
    with SessionLocal() as db:
        assert db.get(DietAssigned, a["id"]).swaps_enabled is True


def test_zarchiwizowana_wersja_nie_przyjmuje_wymian_ani_korekt(dieta):
    c = dieta["c"]
    v1 = _assign(dieta)
    m, kur = _obiad(v1)
    _assign(dieta, kcal=2200)
    q = {"day": 1, "meal": m["meal_id"], "ingredient": kur["ingredient_id"]}
    r = c.get(f"{D}/assigned/{v1['id']}/swaps", headers=dieta["ha"], params=q)
    assert r.status_code == 200 and r.json()["candidates"] == [] and "zarchiwizowana" in r.json()["blocked"]
    r = c.post(f"{D}/assigned/{v1['id']}/swaps", headers=dieta["ha"],
               json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "to_product_id": "x"})
    assert r.status_code == 409
    assert c.patch(f"{D}/assigned/{v1['id']}", headers=dieta["hc"], json={"swaps_enabled": False}).status_code == 409
    with SessionLocal() as db:
        assert db.query(DietSwapEvent).count() == 0


# --- zamiana posiłku ---------------------------------------------------------------------------------


def _obcy_posilek(dieta, *, pusty=False):
    """Posiłek slotu `obiad` w odsłonie DRAFT innego profilu (opcjonalnie pusty)."""
    c, hc = dieta["c"], dieta["hc"]
    pid = c.post(f"{D}/profiles", headers=hc, json={"name": "Inny profil", "base_p_pct": 0.3, "base_f_pct": 0.3, "base_c_pct": 0.4}).json()["id"]
    wid = c.post(f"{D}/weeks", headers=hc, json={"profile_id": pid, "variant_no": 1}).json()["week_id"]
    mid = c.post(f"{D}/weeks/{wid}/days/1/meals", headers=hc, json={"slot": "obiad", "name": "Obcy obiad", "kcal_share": 1.0}).json()["meal_id"]
    if not pusty:
        prod = {p["name_pl"]: p for p in c.get(f"{D}/products", headers=hc).json()["products"]}
        c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": prod["Masło"]["id"], "base_grams": 300, "macro_role": "F"})
    return mid


def test_posilek_zastepczy_tylko_z_tego_profilu_i_opublikowany(dieta):
    c, hc = dieta["c"], dieta["hc"]
    a = _assign(dieta)
    m, _ = _obiad(a)
    obcy = _obcy_posilek(dieta)
    r = c.post(f"{D}/templates/{dieta['week']}/preview", headers=hc,
               json={"kcal": 2000, "macro": {"mode": "profile"}, "meal_replacements": {f"1:{m['meal_id']}": obcy}})
    assert r.status_code == 422 and "innego profilu" in r.json()["detail"]
    r = c.patch(f"{D}/assigned/{a['id']}", headers=hc, json={"day": 1, "meal_id": m["meal_id"], "replace_with_meal_id": obcy})
    assert r.status_code == 422 and "innego profilu" in r.json()["detail"]
    # Klucz zamiany spoza szablonu → 422, nie cicho zignorowany.
    r = c.post(f"{D}/templates/{dieta['week']}/preview", headers=hc,
               json={"kcal": 2000, "macro": {"mode": "profile"}, "meal_replacements": {"1:nie-ma": obcy}})
    assert r.status_code == 422
    # Pusty posiłek z TEJ SAMEJ odsłony (dodany po publikacji) → 422, nie 500.
    pusty = c.post(f"{D}/weeks/{dieta['week']}/days/1/meals", headers=hc, json={"slot": "obiad", "name": "Pusty", "kcal_share": 0.3}).json()["meal_id"]
    r = c.patch(f"{D}/assigned/{a['id']}", headers=hc, json={"day": 1, "meal_id": m["meal_id"], "replace_with_meal_id": pusty})
    assert r.status_code == 422 and "składników" in r.json()["detail"]


def test_druga_zamiana_tego_samego_slotu_dziala(dieta):
    c, hc = dieta["c"], dieta["hc"]
    a = _assign(dieta)
    m, kur = _obiad(a)
    lib = [x for x in c.get(f"{D}/templates/{dieta['week']}/meals", headers=hc, params={"slot": "obiad"}).json()["meals"]
           if x["meal_id"] != m["meal_id"]]
    # Korekta gramatury kurczaka, potem zamiana posiłku: stara korekta nie zostaje jako martwy wpis.
    assert c.patch(f"{D}/assigned/{a['id']}", headers=hc,
                   json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "grams": 200}).status_code == 200
    r = c.patch(f"{D}/assigned/{a['id']}", headers=hc, json={"day": 1, "meal_id": m["meal_id"], "replace_with_meal_id": lib[0]["meal_id"]})
    assert r.status_code == 200 and r.json()["day"]["meals"][1]["meal_id"] == lib[0]["meal_id"]
    assert r.json()["assigned"]["plan"]["overrides"]["ingredients"] == {}
    r = c.patch(f"{D}/assigned/{a['id']}", headers=hc, json={"day": 1, "meal_id": lib[0]["meal_id"], "replace_with_meal_id": lib[1]["meal_id"]})
    assert r.status_code == 200, r.text
    assert r.json()["day"]["meals"][1]["name"] == lib[1]["name"] and r.json()["day"]["meals"][1]["replaced_from"] == m["meal_id"]
    # Podsumowanie planu przeliczone po korektach (nie migawka sprzed zmian).
    plan = r.json()["assigned"]["plan"]
    assert plan["summary"]["days_ok"] == sum(1 for d in plan["days"] if d["status"] == "OK")
    # Zamiana przy przypisaniu, potem PATCH tego slotu (id posiłku z migawki) — też działa.
    a2 = _assign(dieta, meal_replacements={f"1:{m['meal_id']}": lib[0]["meal_id"]}, accept_warnings=True)
    r = c.patch(f"{D}/assigned/{a2['id']}", headers=hc, json={"day": 1, "meal_id": lib[0]["meal_id"], "replace_with_meal_id": lib[1]["meal_id"]})
    assert r.status_code == 200


# --- walidacja wejścia: 422 zamiast 500 ----------------------------------------------------------------


def test_korekty_i_presety_z_bledami_daja_422(dieta):
    c, hc = dieta["c"], dieta["hc"]
    url = f"{D}/templates/{dieta['week']}/preview"
    pre = c.post(url, headers=hc, json={"kcal": 2000, "macro": {"mode": "profile"}}).json()
    m, kur = _obiad({"plan": pre})
    klucz = f"1:{m['meal_id']}:{kur['ingredient_id']}"
    zle = [
        {"overrides": {klucz: {"grams": "dużo"}}},
        {"overrides": {klucz: {"grams": None}}},
        {"overrides": {klucz: {"grams": -5}}},
        {"overrides": {klucz: {"grams": 1e12}}},
        {"overrides": {klucz: {"grams": 100, "product": "Nie ma takiego"}}},
        {"overrides": {"1:x:y": {"grams": 100}}},
        {"overrides": {"zły klucz": {"grams": 100}}},
        {"macro": {"mode": "per_kg", "protein_per_kg": 3.5, "fat_per_kg": 3}, "body_weight": 200},
        {"kcal": 500},
    ]
    for body in zle:
        r = c.post(url, headers=hc, json={"kcal": 2000, "macro": {"mode": "profile"}, **body})
        assert r.status_code == 422, (body, r.status_code, r.text[:200])
    # per_kg bez g/kg → domyślne 2,0 / 1,0, nie 500.
    r = c.post(url, headers=hc, json={"kcal": 2000, "macro": {"mode": "per_kg"}, "body_weight": 70})
    assert r.status_code == 200 and r.json()["target"]["P"] == 140
    # Puste wykluczenia są ignorowane (nie zerują wymian), a nazwy produktów wykluczają kandydatów.
    a = _assign(dieta, exclusions=["", "  ", "Pierś z indyka (surowa)"])
    assert a["exclusions"] == ["Pierś z indyka (surowa)"]
    m, kur = _obiad(a)
    r = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params={"day": 1, "meal": m["meal_id"], "ingredient": kur["ingredient_id"]})
    nazwy = [x["product"] for x in r.json()["candidates"]]
    # Bez wykluczenia byłoby trzech kandydatów (indyk, schab, polędwiczka) — indyk odpada po nazwie.
    assert nazwy == ["Schab bez kości (surowy)", "Polędwiczka wieprzowa (surowa)"]
    # PATCH gramatury pod nieistniejący składnik → 404, bez martwego wpisu.
    r = c.patch(f"{D}/assigned/{a['id']}", headers=hc, json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": "NIE-MA", "grams": 100})
    assert r.status_code == 404
    with SessionLocal() as db:
        assert json.loads(db.get(DietAssigned, a["id"]).overrides_json)["ingredients"] == {}


def test_panel_walidacja_odslony_skladnika_i_importu(dieta):
    c, hc = dieta["c"], dieta["hc"]
    ha = login(c, ADMIN)
    pid = c.post(f"{D}/profiles", headers=hc, json={"name": "Walidacja", "base_p_pct": 0.3, "base_f_pct": 0.3, "base_c_pct": 0.4}).json()["id"]
    assert c.post(f"{D}/weeks", headers=hc, json={"profile_id": pid, "variant_no": 1, "kcal_min": 3000, "kcal_max": 1400}).status_code == 422
    wid = c.post(f"{D}/weeks", headers=hc, json={"profile_id": pid, "variant_no": 1}).json()["week_id"]
    assert c.put(f"{D}/weeks/{wid}", headers=hc, json={"profile_id": pid, "variant_no": 1, "base_kcal": 5000, "kcal_max": 3200}).status_code == 422
    # Pusta odsłona: podgląd = 422 z komunikatem, nie 500; sweep = błąd definicji.
    r = c.post(f"{D}/templates/{wid}/preview", headers=hc, json={"kcal": 2000, "macro": {"mode": "profile"}})
    assert r.status_code == 422 and "posiłków" in r.json()["detail"]
    mid = c.post(f"{D}/weeks/{wid}/days/1/meals", headers=hc, json={"slot": "obiad", "name": "Banan solo", "kcal_share": 1.0}).json()["meal_id"]
    prod = {p["name_pl"]: p for p in c.get(f"{D}/products", headers=hc).json()["products"]}
    # Banan ma domyślną klasę DYSKRETNY → unit_g wymagany także bez jawnej klasy.
    assert prod["Banan"]["default_scaling"] == "DYSKRETNY"
    assert c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": prod["Banan"]["id"], "base_grams": 120}).status_code == 422
    # Domyślne swappable wg roli (§7.3): NONE → niewymienialny, P → wymienialny.
    i1 = c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": prod["Brokuł"]["id"], "base_grams": 100}).json()["ingredient_id"]
    i2 = c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": prod["Pierś z kurczaka (surowa)"]["id"], "base_grams": 150, "macro_role": "P"}).json()["ingredient_id"]
    ings = {i["ingredient_id"]: i for i in c.get(f"{D}/weeks/{wid}/full", headers=hc).json()["days"][0]["meals"][0]["ingredients"]}
    assert ings[i1]["swappable"] is False and ings[i2]["swappable"] is True
    # Admin ma dostęp do panelu (rola techniczna), klient nie.
    assert c.get(f"{D}/weeks/{wid}/full", headers=ha).status_code == 200
    assert c.get(f"{D}/weeks/{wid}/full", headers=dieta["ha"]).status_code == 403
    # Import: duplikat dnia, złe macro_pct, nieznana klasa, round_step 0, nietekstowy profil → 422 (nie 500, nic nie zapisane).
    dane = json.loads(seed._plik("szablon_standard_v1.json"))
    dane["profile"] = "Import test"
    def wariant(zmien):
        d = json.loads(json.dumps(dane))
        zmien(d)
        return d

    warianty = [
        wariant(lambda d: d["days"].append(json.loads(json.dumps(d["days"][0])))),
        wariant(lambda d: d.__setitem__("macro_pct", [0.5, 0.5])),
        wariant(lambda d: d["days"][0]["meals"][0]["ingredients"][0].__setitem__("class", "LINEAR")),
        wariant(lambda d: d["days"][0]["meals"][0]["ingredients"][0].__setitem__("round_step", 0)),
        wariant(lambda d: d.__setitem__("profile", {"x": 1})),
        wariant(lambda d: d["days"][0]["meals"][0].__setitem__("ingredients", [])),
    ]
    for w in warianty:
        r = c.post(f"{D}/weeks/import", headers=hc, json=w)
        assert r.status_code == 422, r.text[:200]
    assert not any(p["name"] == "Import test" for p in c.get(f"{D}/profiles", headers=hc).json()["profiles"])


# --- migawka: reguły zaokrąglania, jednostki po wymianie, blokada per posiłek --------------------------


def test_migawka_niesie_round_step_a_wymiana_dyskretnego_pokazuje_gramy(dieta):
    c = dieta["c"]
    a = _assign(dieta)
    m, kur = _obiad(a)
    assert kur["round_step"] == 5 and "unit_g" not in kur
    sn = a["plan"]["days"][0]["meals"][0]
    banan = next(i for i in sn["ingredients"] if i["product"] == "Banan")
    assert banan["unit_g"] == 120 and banan["unit_step"] == 0.5 and banan["units"] == 1
    q = {"day": 1, "meal": sn["meal_id"], "ingredient": banan["ingredient_id"]}
    cands = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params=q).json()["candidates"]
    if cands:
        r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                   json={"day": 1, "meal_id": sn["meal_id"], "ingredient_id": banan["ingredient_id"], "to_product_id": cands[0]["product_id"]})
        assert r.status_code == 201
        i2 = next(i for i in r.json()["day"]["meals"][0]["ingredients"] if i["ingredient_id"] == banan["ingredient_id"])
        # Inny produkt = brak „sztuk” starego produktu; klient widzi gramy.
        assert i2["product"] == cands[0]["product"] and i2.get("units") is None and i2.get("unit_g") is None


def test_blokada_wymian_dla_konkretnego_posilku(dieta):
    c, hc = dieta["c"], dieta["hc"]
    a = _assign(dieta)
    m, kur = _obiad(a)
    r = c.patch(f"{D}/assigned/{a['id']}", headers=hc, json={"day": 1, "meal_id": m["meal_id"], "meal_swaps_enabled": False})
    assert r.status_code == 200 and r.json()["day"]["meals"][1]["swaps_locked"] is True
    q = {"day": 1, "meal": m["meal_id"], "ingredient": kur["ingredient_id"]}
    r = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params=q)
    assert r.json()["candidates"] == [] and "posiłku" in r.json()["blocked"]
    assert c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                  json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "to_product_id": "x"}).status_code == 409
    # Inny posiłek tego dnia nadal wymienialny.
    sn = a["plan"]["days"][0]["meals"][0]
    skyr = next(i for i in sn["ingredients"] if i["swappable"])
    assert c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                 params={"day": 1, "meal": sn["meal_id"], "ingredient": skyr["ingredient_id"]}).json()["blocked"] is None
    r = c.patch(f"{D}/assigned/{a['id']}", headers=hc, json={"day": 1, "meal_id": m["meal_id"], "meal_swaps_enabled": True})
    assert r.status_code == 200 and not r.json()["day"]["meals"][1].get("swaps_locked")
    assert c.patch(f"{D}/assigned/{a['id']}", headers=hc, json={"day": 1, "meal_id": "nie-ma", "meal_swaps_enabled": False}).status_code == 404


# --- RODO ----------------------------------------------------------------------------------------------


def test_eksport_i_usuniecie_konta_obejmuja_diete_z_szablonu(dieta):
    c = dieta["c"]
    a = _assign(dieta, body_weight=82, exclusions=["lactose"])
    m, kur = _obiad(a)
    cands = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params={"day": 1, "meal": m["meal_id"], "ingredient": kur["ingredient_id"]}).json()["candidates"]
    assert c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                  json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "to_product_id": cands[0]["product_id"]}).status_code == 201
    exp = c.get("/api/me/export", headers=dieta["ha"]).json()
    assert exp["diet_assigned"][0]["id"] == a["id"] and exp["diet_assigned"][0]["body_weight"] == 82
    assert len(exp["diet_swap_events"]) == 1
    r = c.post("/api/me/deletion-request", headers=dieta["ha"], json={"password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE"})
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        assert db.query(DietAssigned).filter_by(client_id=dieta["cid"]).count() == 0
        assert db.query(DietSwapEvent).count() == 0
        assert db.query(DietProduct).count() >= 142  # szablony i produkty zostają


# --- seed --------------------------------------------------------------------------------------------------


def test_seed_nie_wywraca_sie_po_zmianie_nazwy_produktu_w_csv(dieta):
    rows = seed.wczytaj_produkty_csv()
    rows[0]["name_pl"] = rows[0]["name_pl"] + " (nowa nazwa)"
    rows.append({**rows[1], "id": "P999", "name_pl": "Zupełnie nowy produkt"})
    with db_session() as db:
        raport = seed.zaseeduj_produkty(db, rows)
        assert raport["produkty_dodane"] == 1
        assert db.query(DietProduct).filter_by(id=rows[0]["id"]).one().name_pl != rows[0]["name_pl"]
        assert db.query(DietProduct).filter_by(id="P999").one_or_none() is not None

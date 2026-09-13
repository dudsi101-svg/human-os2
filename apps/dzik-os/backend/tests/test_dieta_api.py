"""Etap 3 — API `/api/diet` (0.60.0): autoryzacja, podgląd, przypisanie
z migawką, wymiany z walidacją serwerową, korekty trenera, panel szablonów,
flaga modułu."""

from __future__ import annotations

import json

import pytest
from conftest import ADMIN, CLIENT_A, CLIENT_B, COACH, create_user_with_role, get_user_id, login

from dzik_os.config import settings
from dzik_os.db import SessionLocal, db_session
from dzik_os.dieta import seed
from dzik_os.models import DietAssigned, DietSwapEvent, DietTemplateIngredient

D = "/api/diet"


@pytest.fixture()
def dieta(seeded):
    """Konta seedu + seed modułu (jak przy starcie aplikacji z flagą)."""
    with db_session() as db:
        seed.zaseeduj(db)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    week = seeded.get(f"{D}/profiles", headers=hc).json()["profiles"][0]["weeks"][0]
    return {"c": seeded, "hc": hc, "ha": ha, "cid": get_user_id(seeded, ha), "week": week["id"]}


def _assign(d, kcal=2000, **extra):
    body = {"client_id": d["cid"], "week_id": d["week"], "kcal": kcal, "macro": {"mode": "profile"}, **extra}
    return d["c"].post(f"{D}/assign", headers=d["hc"], json=body)


# --- flaga -----------------------------------------------------------------------------


def test_flaga_wylaczona_daje_404_na_calym_module(dieta, monkeypatch):
    monkeypatch.setattr(settings, "diet_templates_enabled", False)
    c = dieta["c"]
    assert c.get(f"{D}/profiles", headers=dieta["hc"]).status_code == 404
    assert c.get(f"{D}/assigned/current", headers=dieta["ha"]).status_code == 404
    assert c.post(f"{D}/assign", headers=dieta["hc"], json={}).status_code == 404
    assert c.get("/api/health").json()["features"]["diet_templates"] is False
    monkeypatch.setattr(settings, "diet_templates_enabled", True)
    assert c.get(f"{D}/profiles", headers=dieta["hc"]).status_code == 200
    assert c.get("/api/health").json()["features"]["diet_templates"] is True


# --- profile, szablon, podgląd -----------------------------------------------------------


def test_profile_i_podglad_szablonu_bez_gramatur(dieta):
    c = dieta["c"]
    p = c.get(f"{D}/profiles", headers=dieta["hc"]).json()["profiles"]
    assert len(p) == 1 and p[0]["name"] == "Standard zbilansowana" and p[0]["published_weeks"] == 1
    assert p[0]["base_macro_pct"] == {"P": 0.25, "F": 0.3, "C": 0.45}
    t = c.get(f"{D}/templates/{dieta['week']}", headers=dieta["hc"]).json()
    assert len(t["days"]) == 7 and all(len(d["meals"]) == 4 for d in t["days"])
    assert "grams" not in json.dumps(t) and t["days"][0]["meals"][0]["ingredients"] == 6
    # Klient nie ogląda biblioteki szablonów.
    assert c.get(f"{D}/profiles", headers=dieta["ha"]).status_code == 403


def test_preview_zwraca_wynik_silnika_z_ostrzezeniem_poza_zakresem(dieta):
    c = dieta["c"]
    r = c.post(f"{D}/templates/{dieta['week']}/preview", headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "profile"}})
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["summary"]["days"] == 7 and plan["summary"]["days_ok"] == 7
    d1 = plan["days"][0]
    assert d1["macros"]["kcal"] == 2027 and d1["status"] == "OK"
    kur = next(i for i in d1["meals"][1]["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    assert kur["grams"] == 160 and kur["swappable"] is True
    banan = next(i for i in d1["meals"][0]["ingredients"] if i["product"] == "Banan")
    assert banan["units"] == 1 and banan["unit_g"] == 120
    with SessionLocal() as db:
        assert db.query(DietAssigned).count() == 0  # podgląd nic nie zapisuje
    r = c.post(f"{D}/templates/{dieta['week']}/preview", headers=dieta["hc"], json={"kcal": 1200, "macro": {"mode": "profile"}})
    assert r.status_code == 200 and any("poza zakresem" in w for w in r.json()["warnings"])


def test_presety_makro_manual_per_kg_i_bledy_422(dieta):
    c = dieta["c"]
    url = f"{D}/templates/{dieta['week']}/preview"
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "manual", "P": 150, "F": 60, "C": 100}})
    assert r.status_code == 422 and "3 %" in r.json()["detail"]
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "manual", "P": 150, "F": 60, "C": 215}})
    assert r.status_code == 200 and r.json()["target"]["P"] == 150
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "per_kg", "protein_per_kg": 2.0, "fat_per_kg": 1.0}})
    assert r.status_code == 422 and "masy ciała" in r.json()["detail"]
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "per_kg", "protein_per_kg": 2.0, "fat_per_kg": 1.0}, "body_weight": 70})
    assert r.status_code == 200 and r.json()["target"] == {"kcal": 2000, "P": 140, "F": 70, "C": 202.5}
    # Wykluczenia: konflikty wskazane, nie ukryte.
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "profile"}, "exclusions": ["lactose"]})
    assert r.status_code == 200 and "Skyr naturalny" in r.json()["conflicts"]


def test_preview_z_korektami_i_zamiana_posilku_z_biblioteki(dieta):
    c = dieta["c"]
    url = f"{D}/templates/{dieta['week']}/preview"
    base = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "profile"}}).json()
    m = base["days"][0]["meals"][1]
    kur = next(i for i in m["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "profile"},
                                               "overrides": {f"1:{m['meal_id']}:{kur['ingredient_id']}": {"grams": 400}}})
    assert r.status_code == 200
    d1 = r.json()["days"][0]
    assert d1["meals"][1]["ingredients"][kur and next(i for i, x in enumerate(m["ingredients"]) if x["product"] == kur["product"])]["grams"] == 400
    assert d1["meals"][1]["status"] != "OK" and d1["status"] == "POZA_TOLERANCJĄ"
    # Biblioteka posiłków tego samego slotu i zamiana w podglądzie.
    lib = c.get(f"{D}/templates/{dieta['week']}/meals", headers=dieta["hc"], params={"slot": "obiad"}).json()["meals"]
    assert len(lib) == 7 and all(x["slot"] == "obiad" for x in lib)
    inny = next(x for x in lib if x["meal_id"] != m["meal_id"])
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "profile"},
                                               "meal_replacements": {f"1:{m['meal_id']}": inny["meal_id"]}})
    assert r.status_code == 200 and r.json()["days"][0]["meals"][1]["name"] == inny["name"]
    zly = next(x for x in c.get(f"{D}/templates/{dieta['week']}/meals", headers=dieta["hc"], params={"slot": "kolacja"}).json()["meals"])
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "profile"},
                                               "meal_replacements": {f"1:{m['meal_id']}": zly["meal_id"]}})
    assert r.status_code == 422


# --- przypisanie i autoryzacja --------------------------------------------------------------


def test_assign_tylko_trener_i_tylko_wlasny_klient(dieta):
    c = dieta["c"]
    body = {"client_id": dieta["cid"], "week_id": dieta["week"], "kcal": 2000, "macro": {"mode": "profile"}}
    assert c.post(f"{D}/assign", headers=dieta["ha"], json=body).status_code == 403
    create_user_with_role("obcy.trener@example.com", "Obcy#2026!xx", "Obcy", "COACH")
    ho = login(c, {"email": "obcy.trener@example.com", "password": "Obcy#2026!xx"})
    assert c.post(f"{D}/assign", headers=ho, json=body).status_code == 404
    r = _assign(dieta)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["version"] == 1 and a["status"] == "ACTIVE" and a["plan"]["days"][0]["macros"]["kcal"] == 2027
    # Trener bez relacji nie widzi diety cudzego klienta; klient B nie widzi diety A.
    assert c.get(f"{D}/clients/{dieta['cid']}/current", headers=ho).status_code == 404
    hb = login(c, CLIENT_B)
    assert c.get(f"{D}/clients/{dieta['cid']}/current", headers=hb).status_code == 404
    assert c.get(f"{D}/assigned/{a['id']}/swaps", headers=hb, params={"day": 1, "meal": "x", "ingredient": "y"}).status_code == 404
    assert c.patch(f"{D}/assigned/{a['id']}", headers=ho, json={"swaps_enabled": False}).status_code == 404
    # Klient widzi swoją; trener z relacją widzi klienta.
    assert c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]["id"] == a["id"]
    cur = c.get(f"{D}/clients/{dieta['cid']}/current", headers=dieta["hc"]).json()
    assert cur["assigned"]["id"] == a["id"] and cur["history"][0]["version"] == 1
    # Ponowne przypisanie = nowa wersja, poprzednia zarchiwizowana.
    r2 = _assign(dieta, kcal=2200)
    assert r2.json()["version"] == 2
    with SessionLocal() as db:
        assert db.get(DietAssigned, a["id"]).status == "ARCHIVED"


def test_migawka_nie_zmienia_sie_po_edycji_szablonu(dieta):
    c = dieta["c"]
    a = _assign(dieta).json()
    with db_session() as db:
        i = db.query(DietTemplateIngredient).filter_by(macro_role="P").first()
        i.base_grams = i.base_grams * 3
    # Podgląd szablonu daje teraz inny wynik, migawka — ten sam.
    nowy = c.post(f"{D}/templates/{dieta['week']}/preview", headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "profile"}}).json()
    stary = c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]["plan"]
    assert stary["days"] == a["plan"]["days"]
    assert json.dumps(nowy["days"]) != json.dumps(stary["days"])


def test_blokada_dnia_poza_tolerancja_i_przypisanie_mimo_ostrzezen(dieta):
    c = dieta["c"]
    pre = c.post(f"{D}/templates/{dieta['week']}/preview", headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "profile"}}).json()
    m = pre["days"][0]["meals"][1]
    kur = next(i for i in m["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    ov = {f"1:{m['meal_id']}:{kur['ingredient_id']}": {"grams": 450}}
    r = _assign(dieta, overrides=ov)
    assert r.status_code == 409 and r.json()["code"] == "DAY_OUT_OF_TOLERANCE" and r.json()["days"] == [1]
    r = _assign(dieta, overrides=ov, accept_warnings=True)
    assert r.status_code == 201
    o = r.json()["plan"]["overrides"]
    assert o["accepted_warnings"] is True and o["accepted_days"] == [1]
    assert next(i for i in r.json()["plan"]["days"][0]["meals"][1]["ingredients"] if i["product"] == kur["product"])["grams"] == 450


# --- wymiany -----------------------------------------------------------------------------------


def _kurczak(d, a):
    m = a["plan"]["days"][0]["meals"][1]
    kur = next(i for i in m["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    return m, kur


def test_wymiana_kandydaci_walidacja_gramatury_i_historia(dieta):
    c = dieta["c"]
    a = _assign(dieta).json()
    m, kur = _kurczak(dieta, a)
    q = {"day": 1, "meal": m["meal_id"], "ingredient": kur["ingredient_id"]}
    r = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params=q)
    assert r.status_code == 200, r.text
    cands = r.json()["candidates"]
    assert [x["product"] for x in cands] == ["Pierś z indyka (surowa)", "Schab bez kości (surowy)", "Polędwiczka wieprzowa (surowa)"]
    indyk = cands[0]
    body = {"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "to_product_id": indyk["product_id"]}
    # Niepoprawna gramatura z klienta → odrzucona po walidacji serwerowej.
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], json={**body, "grams": 999})
    assert r.status_code == 422 and "tolerancj" in r.json()["detail"]
    # Produkt spoza kandydatów → 422.
    prod = c.get(f"{D}/products", headers=dieta["hc"]).json()["products"]
    maslo = next(p for p in prod if p["name_pl"] == "Masło")
    assert c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], json={**body, "to_product_id": maslo["id"]}).status_code == 422
    # Poprawna wymiana: gramatura serwera, wpis historii, override widoczny u klienta i trenera.
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], json=body)
    assert r.status_code == 201, r.text
    assert r.json()["day"]["meals"][1]["ingredients"][m["ingredients"].index(kur)]["grams"] == indyk["grams"] == 155
    cur = c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]
    i2 = next(i for i in cur["plan"]["days"][0]["meals"][1]["ingredients"] if i["ingredient_id"] == kur["ingredient_id"])
    assert i2["product"] == "Pierś z indyka (surowa)" and i2["override"]["kind"] == "swap"
    hist = c.get(f"{D}/clients/{dieta['cid']}/current", headers=dieta["hc"]).json()["swap_events"]
    assert len(hist) == 1 and hist[0]["from"] == "Pierś z kurczaka (surowa)" and hist[0]["to"] == "Pierś z indyka (surowa)"
    with SessionLocal() as db:
        assert db.query(DietSwapEvent).count() == 1
    # Skyr bez laktozy → pusta lista (komunikat dla klienta), nie błąd.
    a2 = _assign(dieta, exclusions=["lactose"]).json()
    sn = a2["plan"]["days"][0]["meals"][0]
    skyr = next(i for i in sn["ingredients"] if i["product"] == "Skyr naturalny")
    r = c.get(f"{D}/assigned/{a2['id']}/swaps", headers=dieta["ha"], params={"day": 1, "meal": sn["meal_id"], "ingredient": skyr["ingredient_id"]})
    assert r.status_code == 200 and r.json()["candidates"] == [] and r.json()["blocked"] is None


def test_trener_blokuje_wymiany_i_koryguje_gramature_oraz_zamienia_posilek(dieta):
    c = dieta["c"]
    a = _assign(dieta).json()
    m, kur = _kurczak(dieta, a)
    r = c.patch(f"{D}/assigned/{a['id']}", headers=dieta["hc"], json={"swaps_enabled": False})
    assert r.status_code == 200 and r.json()["assigned"]["swaps_enabled"] is False
    q = {"day": 1, "meal": m["meal_id"], "ingredient": kur["ingredient_id"]}
    assert c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params=q).json()["blocked"]
    assert c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                  json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "to_product_id": "x"}).status_code == 409
    # Klient nie może wywołać PATCH (rola trenera).
    assert c.patch(f"{D}/assigned/{a['id']}", headers=dieta["ha"], json={"swaps_enabled": True}).status_code == 403
    # Korekta gramatury: dzień przeliczony po stronie serwera.
    r = c.patch(f"{D}/assigned/{a['id']}", headers=dieta["hc"],
                json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "grams": 200})
    assert r.status_code == 200
    d = r.json()["day"]
    assert next(i for i in d["meals"][1]["ingredients"] if i["ingredient_id"] == kur["ingredient_id"])["grams"] == 200
    assert d["macros"]["kcal"] > 2027 and d["meals"][1]["macros"]["P"] > 48
    # Zamiana posiłku na inny z biblioteki (ten sam slot) — przeskalowany do celu posiłku.
    lib = c.get(f"{D}/templates/{dieta['week']}/meals", headers=dieta["hc"], params={"slot": "obiad"}).json()["meals"]
    inny = next(x for x in lib if x["meal_id"] != m["meal_id"])
    r = c.patch(f"{D}/assigned/{a['id']}", headers=dieta["hc"], json={"day": 1, "meal_id": m["meal_id"], "replace_with_meal_id": inny["meal_id"]})
    assert r.status_code == 200 and r.json()["day"]["meals"][1]["name"] == inny["name"]
    assert abs(r.json()["day"]["meals"][1]["macros"]["kcal"] - 660) < 60
    assert r.json()["assigned"]["plan"]["overrides"]["meals"][f"1:{m['meal_id']}"]["replaced_by_meal_id"] == inny["meal_id"]


# --- panel szablonów -------------------------------------------------------------------------------


def test_panel_szablonow_crud_sweep_publikacja_import(dieta):
    c, hc = dieta["c"], dieta["hc"]
    ha = login(c, ADMIN)
    r = c.post(f"{D}/profiles", headers=hc, json={"name": "Redukcja wysokobiałkowa", "base_p_pct": 0.35, "base_f_pct": 0.25, "base_c_pct": 0.40})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert c.post(f"{D}/profiles", headers=hc, json={"name": "Zła", "base_p_pct": 0.5, "base_f_pct": 0.5, "base_c_pct": 0.5}).status_code == 422
    r = c.post(f"{D}/weeks", headers=hc, json={"profile_id": pid, "variant_no": 1, "name": "Redukcja — odsłona 1"})
    assert r.status_code == 201 and r.json()["status"] == "DRAFT" and len(r.json()["days"]) == 7
    wid = r.json()["id"] if "id" in r.json() else r.json()["week_id"]
    # Trener widzi odsłonę w profilach, ale przypisać może tylko opublikowaną.
    assert c.post(f"{D}/assign", headers=hc, json={"client_id": dieta["cid"], "week_id": wid, "kcal": 2000, "macro": {"mode": "profile"}}).status_code == 404
    # Pusta odsłona: sweep zgłasza błąd definicji, publikacja odmawia.
    r = c.post(f"{D}/weeks/{wid}/sweep", headers=hc)
    assert r.status_code == 200 and r.json()["publishable"] is False
    assert c.post(f"{D}/weeks/{wid}/publish", headers=hc).status_code == 409
    # Posiłek + składniki z bazy; DYSKRETNY wymaga unit_g; nieznany produkt = 404.
    r = c.post(f"{D}/weeks/{wid}/days/1/meals", headers=hc, json={"slot": "obiad", "name": "Kurczak z ryżem", "kcal_share": 1.0, "recipe_steps": "Ugotuj."})
    mid = r.json()["meal_id"]
    prod = {p["name_pl"]: p for p in c.get(f"{D}/products", headers=hc).json()["products"]}
    assert len(prod) == 142
    assert c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": "nie-ma", "base_grams": 100}).status_code == 404
    assert c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": prod["Banan"]["id"], "base_grams": 120, "scaling_class": "DYSKRETNY"}).status_code == 422
    for name, g, role in (("Pierś z kurczaka (surowa)", 150, "P"), ("Ryż biały (suchy)", 75, "C"), ("Olej rzepakowy", 10, "F"), ("Brokuł", 120, "NONE")):
        assert c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": prod[name]["id"], "base_grams": g, "macro_role": role}).status_code == 201
    r = c.post(f"{D}/weeks/{wid}/sweep", headers=hc).json()
    assert r["days"] == 19 and r["missing_days"] == [2, 3, 4, 5, 6, 7] and r["publishable"] is False
    assert r["meals"][0]["name"] == "Kurczak z ryżem"
    full = c.get(f"{D}/weeks/{wid}/full", headers=hc).json()
    assert len(full["days"][0]["meals"][0]["ingredients"]) == 4
    # Import JSON (Standard v1 jako wariant 2) → DRAFT → sweep ≥ 95 % → publikacja.
    dane = json.loads(seed._plik("szablon_standard_v1.json"))
    dane["variant"] = 2
    r = c.post(f"{D}/weeks/import", headers=hc, json=dane)
    assert r.status_code == 201 and r.json()["status"] == "DRAFT"
    wid2 = r.json()["week_id"]
    assert c.post(f"{D}/weeks/import", headers=hc, json=dane).status_code == 409
    r = c.post(f"{D}/weeks/{wid2}/publish", headers=hc)
    assert r.status_code == 200 and r.json()["status"] == "PUBLISHED" and r.json()["sweep"]["days_ok"] >= 131
    assert next(p for p in c.get(f"{D}/profiles", headers=hc).json()["profiles"] if p["name"] == "Standard zbilansowana")["published_weeks"] == 2
    # Produkt dodaje wyłącznie admin, z jawnym źródłem; kcal z makro.
    body = {"name_pl": "Skyr bezlaktozowy", "category": "nabiał", "substitution_group": "nabiał_chudy",
            "protein_100": 11, "fat_100": 0.2, "carbs_100": 4, "cooking_tags": "*", "source": "etykieta producenta"}
    assert c.post(f"{D}/products", headers=hc, json=body).status_code == 403
    r = c.post(f"{D}/products", headers=ha, json=body)
    assert r.status_code == 201 and r.json()["kcal_100"] == 61.8
    assert c.post(f"{D}/products", headers=ha, json=body).status_code == 409
    # Admin nie sięga po diety klientów (dane żywieniowe).
    a = _assign(dieta).json()
    assert c.get(f"{D}/clients/{dieta['cid']}/current", headers=ha).status_code == 404
    assert c.get(f"{D}/assigned/{a['id']}/swaps", headers=ha, params={"day": 1, "meal": "m", "ingredient": "i"}).status_code == 404

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
from dzik_os.models import (
    DietAssigned,
    DietSwapEvent,
    DietTemplateDay,
    DietTemplateIngredient,
    DietTemplateMeal,
)

D = "/api/diet"
# Dane referencyjne biblioteki po audycie 14.09 (Standard v1 przy 2000 kcal, dzień 1);
# zmiana względem 0.60.0 (2027 kcal, kurczak 160 g) wynika z nowej treści szablonu,
# potwierdzonej golden z paczki — nie z dopasowania asercji.
KCAL_D1_2000 = 2000.3


@pytest.fixture()
def dieta(seeded):
    """Konta seedu + seed modułu (jak przy starcie aplikacji z flagą)."""
    with db_session() as db:
        seed.zaseeduj(db)
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    # Biblioteka ma 9 profili — testy liczbowe odnoszą się do „Standard zbilansowana", odsłona 1.
    std = next(p for p in seeded.get(f"{D}/profiles", headers=hc).json()["profiles"] if p["name"] == "Standard zbilansowana")
    week = next(w for w in std["weeks"] if w["variant_no"] == 1)
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
    assert len(p) == 9 and {x["name"] for x in p} >= {"Standard zbilansowana", "Sportowa wysokobiałkowa", "Wegańska"}
    assert all(x["published_weeks"] == 5 for x in p)
    std = next(x for x in p if x["name"] == "Standard zbilansowana")
    assert std["base_macro_pct"] == {"P": 0.25, "F": 0.3, "C": 0.45}
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
    assert d1["macros"]["kcal"] == KCAL_D1_2000 and d1["status"] == "OK"
    kur = next(i for i in d1["meals"][1]["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    assert kur["grams"] == 165 and kur["swappable"] is True  # szablon po audycie: 165 g (było 160)
    banan = next(i for i in d1["meals"][0]["ingredients"] if i["product"] == "Banan")
    assert banan["units"] == 1 and banan["unit_g"] == 120
    with SessionLocal() as db:
        assert db.query(DietAssigned).count() == 0  # podgląd nic nie zapisuje
    r = c.post(f"{D}/templates/{dieta['week']}/preview", headers=dieta["hc"], json={"kcal": 1200, "macro": {"mode": "profile"}})
    assert r.status_code == 200 and any("poza zakresem" in w for w in r.json()["warnings"])


def test_presety_makro_manual_per_kg_i_bledy_422(dieta):
    c = dieta["c"]
    url = f"{D}/templates/{dieta['week']}/preview"
    # §6.4: suma kcal z makro ≠ cel ±3 % → OSTRZEŻENIE, tydzień liczony na kcal z gramów makro.
    r = c.post(url, headers=dieta["hc"], json={"kcal": 2000, "macro": {"mode": "manual", "P": 150, "F": 60, "C": 100}})
    assert r.status_code == 200 and any("3 %" in w for w in r.json()["warnings"]) and r.json()["target"]["kcal"] == 1540
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
    assert len(lib) == 35 and all(x["slot"] == "obiad" for x in lib)  # 5 odsłon × 7 dni tego profilu
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
    assert a["version"] == 1 and a["status"] == "ACTIVE" and a["plan"]["days"][0]["macros"]["kcal"] == KCAL_D1_2000
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
        # Składnik białkowy z TEJ odsłony (w bibliotece jest 45 odsłon).
        i = (db.query(DietTemplateIngredient).join(DietTemplateMeal, DietTemplateMeal.id == DietTemplateIngredient.meal_id)
             .join(DietTemplateDay, DietTemplateDay.id == DietTemplateMeal.day_id)
             .filter(DietTemplateDay.week_id == dieta["week"], DietTemplateIngredient.macro_role == "P").first())
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
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], json={**body, "grams": 290})
    assert r.status_code == 422 and "tolerancj" in r.json()["detail"]
    # Produkt spoza kandydatów → 422.
    prod = c.get(f"{D}/products", headers=dieta["hc"]).json()["products"]
    maslo = next(p for p in prod if p["name_pl"] == "Masło")
    assert c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], json={**body, "to_product_id": maslo["id"]}).status_code == 422
    # Poprawna wymiana: gramatura serwera, wpis historii, override widoczny u klienta i trenera.
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], json=body)
    assert r.status_code == 201, r.text
    assert r.json()["day"]["meals"][1]["ingredients"][m["ingredients"].index(kur)]["grams"] == indyk["grams"] == 160  # 165 g kurczaka → 160 g indyka (dane po audycie)
    cur = c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]
    i2 = next(i for i in cur["plan"]["days"][0]["meals"][1]["ingredients"] if i["ingredient_id"] == kur["ingredient_id"])
    assert i2["product"] == "Pierś z indyka (surowa)" and i2["override"]["kind"] == "swap"
    hist = c.get(f"{D}/clients/{dieta['cid']}/current", headers=dieta["hc"]).json()["swap_events"]
    assert len(hist) == 1 and hist[0]["from"] == "Pierś z kurczaka (surowa)" and hist[0]["to"] == "Pierś z indyka (surowa)"
    with SessionLocal() as db:
        assert db.query(DietSwapEvent).count() == 1
    # Skyr przy wykluczeniu laktozy → tylko kandydaci bez laktozy (baza po audycie ma nabiał bezlaktozowy), nie błąd.
    a2 = _assign(dieta, exclusions=["lactose"]).json()
    sn = a2["plan"]["days"][0]["meals"][0]
    skyr = next(i for i in sn["ingredients"] if i["product"] == "Skyr naturalny")
    r = c.get(f"{D}/assigned/{a2['id']}/swaps", headers=dieta["ha"], params={"day": 1, "meal": sn["meal_id"], "ingredient": skyr["ingredient_id"]})
    assert r.status_code == 200 and r.json()["blocked"] is None
    assert r.json()["candidates"] and all("bez laktozy" in x["product"] for x in r.json()["candidates"])


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
    assert d["macros"]["kcal"] > KCAL_D1_2000 and d["meals"][1]["macros"]["P"] > 48
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
    r = c.post(f"{D}/profiles", headers=hc, json={"name": "Redukcja testowa", "base_p_pct": 0.35, "base_f_pct": 0.25, "base_c_pct": 0.40})
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
    assert len(prod) == 181
    assert c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": "nie-ma", "base_grams": 100}).status_code == 404
    assert c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": prod["Banan"]["id"], "base_grams": 120, "scaling_class": "DYSKRETNY"}).status_code == 422
    for name, g, role in (("Pierś z kurczaka (surowa)", 150, "P"), ("Ryż biały (suchy)", 75, "C"), ("Olej rzepakowy", 10, "F"), ("Brokuł", 120, "NONE")):
        assert c.post(f"{D}/meals/{mid}/ingredients", headers=hc, json={"product_id": prod[name]["id"], "base_grams": g, "macro_role": role}).status_code == 201
    r = c.post(f"{D}/weeks/{wid}/sweep", headers=hc).json()
    assert r["days"] == 19 and r["missing_days"] == [2, 3, 4, 5, 6, 7] and r["publishable"] is False
    assert r["meals"][0]["name"] == "Kurczak z ryżem"
    full = c.get(f"{D}/weeks/{wid}/full", headers=hc).json()
    assert len(full["days"][0]["meals"][0]["ingredients"]) == 4
    # Import JSON (treść Standard v1 pod nowym profilem — biblioteka ma już odsłony 1–5, więc ścieżka
    # „nowa odsłona istniejącego profilu” jest pokryta seedem) → DRAFT → sweep ≥ 95 % → publikacja.
    dane = json.loads(seed._szablon("template_standard_v1.json"))
    dane["profile"] = "Standard (import testowy)"
    r = c.post(f"{D}/weeks/import", headers=hc, json=dane)
    assert r.status_code == 201 and r.json()["status"] == "DRAFT"
    wid2 = r.json()["week_id"]
    assert c.post(f"{D}/weeks/import", headers=hc, json=dane).status_code == 409
    r = c.post(f"{D}/weeks/{wid2}/publish", headers=hc)
    assert r.status_code == 200 and r.json()["status"] == "PUBLISHED" and r.json()["sweep"]["days_ok"] >= 131
    assert next(p for p in c.get(f"{D}/profiles", headers=hc).json()["profiles"] if p["name"] == "Standard (import testowy)")["published_weeks"] == 1
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


def test_podmiana_biblioteki_nie_rusza_przypisanej_diety_ani_wymian(dieta):
    """Spec §8 / plan 0.64.0 decyzja 1: przypisana dieta = migawka. Po podmianie
    treści odsłony (inny skrót pliku) plan klienta jest bajt w bajt ten sam, a
    wymiana produktu i zamiana posiłku (nowe meal_id z podmienionej treści) działają."""
    c = dieta["c"]
    a = _assign(dieta).json()
    przed = c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]["plan"]
    dane = json.loads(seed._szablon("template_standard_v1.json"))
    dane["days"][0]["meals"][1]["name"] = "Obiad po podmianie"
    with db_session() as db:
        week, nowa = seed.zaimportuj_szablon(db, dane, replace=True)
        assert nowa is False and week.id == dieta["week"]
    po = c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]["plan"]
    assert json.dumps(po, sort_keys=True) == json.dumps(przed, sort_keys=True)
    m = po["days"][0]["meals"][1]
    kur = next(i for i in m["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    r = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params={"day": 1, "meal": m["meal_id"], "ingredient": kur["ingredient_id"]})
    assert r.status_code == 200 and r.json()["candidates"]
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
               json={"day": 1, "meal_id": m["meal_id"], "ingredient_id": kur["ingredient_id"], "to_product_id": r.json()["candidates"][0]["product_id"]})
    assert r.status_code == 201, r.text
    lib = c.get(f"{D}/templates/{dieta['week']}/meals", headers=dieta["hc"], params={"slot": "obiad"}).json()["meals"]
    nowy = next(x for x in lib if x["name"] == "Obiad po podmianie")
    r = c.patch(f"{D}/assigned/{a['id']}", headers=dieta["hc"], json={"day": 1, "meal_id": m["meal_id"], "replace_with_meal_id": nowy["meal_id"]})
    assert r.status_code == 200, r.text
    assert r.json()["day"]["meals"][1]["name"] == "Obiad po podmianie"


def test_notatki_i_alergeny_w_api_oraz_zakres_widocznosci_klienta(dieta):
    c = dieta["c"]
    t = c.get(f"{D}/templates/{dieta['week']}", headers=dieta["hc"]).json()
    assert t["supplements_note"] and t["sodium_note"] and "audit_json" not in t and "source_hash" not in t
    assert isinstance(t["days"][0]["meals"][0]["allergens"], list)
    # Bezlaktozowa v1: pochodzenie po ludzku, nie slug pliku.
    poch = next(p for p in c.get(f"{D}/profiles", headers=dieta["hc"]).json()["profiles"] if p["name"] == "Bezlaktozowa")
    t2 = c.get(f"{D}/templates/{poch['weeks'][0]['id']}", headers=dieta["hc"]).json()
    assert t2["derived_from"] and t2["derived_from"].startswith("Standard zbilansowana, odsłona")
    # Klient: nie widzi biblioteki; w swojej diecie dostaje sód i alergeny, ale nie uwagi o suplementacji (R-10).
    a = _assign(dieta).json()
    assert a["supplements_note"]  # odpowiedź dla trenera
    assert c.get(f"{D}/templates/{dieta['week']}", headers=dieta["ha"]).status_code == 403
    cur = c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]
    assert cur["supplements_note"] == [] and cur["derived_from"] is None and cur["sodium_note"]
    assert "audit_json" not in cur and "source_hash" not in cur
    obiad = cur["plan"]["days"][0]["meals"][1]
    assert isinstance(obiad["allergens"], list)
    # Po korekcie trenera (kurczak → krewetki) alergeny posiłku liczą się z bieżących składników.
    kur = next(i for i in obiad["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    r = c.post(f"{D}/templates/{dieta['week']}/preview", headers=dieta["hc"],
               json={"kcal": 2000, "macro": {"mode": "profile"},
                     "overrides": {f"1:{obiad['meal_id']}:{kur['ingredient_id']}": {"grams": 165, "product": "Krewetki (surowe)"}}})
    assert r.status_code == 200, r.text
    assert "skorupiaki" in r.json()["days"][0]["meals"][1]["allergens"]


def test_import_odrzuca_nadmiarowe_notatki_i_zly_zakres_kcal(dieta):
    c, hc = dieta["c"], dieta["hc"]
    baza = json.loads(seed._szablon("template_standard_v1.json"))
    baza["profile"] = "Import limity"
    for zmiana in ({"supplements_note": ["x"] * 21}, {"supplements_note": ["y" * 501]}, {"audit": {"k": "z" * 4001}},
                   {"kcal_min": 3000, "kcal_max": 2500}, {"derived_from": "a" * 121}):
        dane = {**baza, **zmiana}
        assert c.post(f"{D}/weeks/import", headers=hc, json=dane).status_code == 422, zmiana
    zle = json.loads(json.dumps(baza))
    zle["days"][0]["meals"][0]["allergens"] = ["gluten"] * 21
    assert c.post(f"{D}/weeks/import", headers=hc, json=zle).status_code == 422
    # Edycja w panelu oznacza odsłonę: seed jej nie podmienia.
    mid = c.get(f"{D}/templates/{dieta['week']}", headers=hc).json()["days"][0]["meals"][0]["meal_id"]
    r = c.put(f"{D}/meals/{mid}", headers=hc,
              json={"slot": "śniadanie", "name": "Owsianka trenera", "kcal_share": 0.25, "recipe_steps": "Ugotuj."})
    assert r.status_code == 200, r.text
    with db_session() as db:
        raport = seed.zaseeduj(db)
    assert raport["szablony_pominiete"] == 1
    assert c.get(f"{D}/templates/{dieta['week']}", headers=hc).json()["days"][0]["meals"][0]["name"] == "Owsianka trenera"


# --- wymiany v2 (0.69.0): powód pustej listy, rola NONE, poziom 2, historia z poziomem ---


def _skladnik_z_planu(a, produkt: str):
    for d in a["plan"]["days"]:
        for m in d["meals"]:
            for i in m["ingredients"]:
                if i["product"] == produkt:
                    return d, m, i
    raise AssertionError(produkt)


def test_wymiana_v2_powod_pustej_listy_i_poziom_2(dieta):
    c = dieta["c"]
    a = _assign(dieta).json()
    d, m, aw = _skladnik_z_planu(a, "Awokado")
    q = {"day": d["day"], "meal": m["meal_id"], "ingredient": aw["ingredient_id"]}
    r = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params=q)
    assert r.status_code == 200, r.text
    body = r.json()
    # Awokado = singleton poziomu 1 → kandydaci wyłącznie z grup pokrewnych (orzechy/tłuszcz), z etykietą i deltą posiłku.
    assert body["reason"] is None and body["candidates"], body
    assert all(x["tier"] == 2 and x["group"] and x["tier_reason"] and set(x["meal_delta"]) == {"kcal", "P", "F", "C"} for x in body["candidates"])
    assert isinstance(body["rejected"], dict)
    # POST przyjmuje kandydata poziomu 2 i zapisuje poziom w korekcie; historia trenera pokazuje poziom.
    kand = body["candidates"][0]
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
               json={"day": d["day"], "meal_id": m["meal_id"], "ingredient_id": aw["ingredient_id"], "to_product_id": kand["product_id"]})
    assert r.status_code == 201, r.text
    cur = c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]
    assert cur["plan"]["overrides"]["ingredients"][f"{d['day']}:{m['meal_id']}:{aw['ingredient_id']}"]["tier"] == 2
    hist = c.get(f"{D}/clients/{dieta['cid']}/current", headers=dieta["hc"]).json()["swap_events"]
    assert hist and hist[0]["to"] == kand["product"] and hist[0]["tier"] == 2
    # Powód pustej listy: wykluczenie wszystkich kandydatów po nazwie („nie lubię”) → EXCLUDED.
    a2 = _assign(dieta, exclusions=[x["product"] for x in body["candidates"]] + ["Orzechy włoskie", "Migdały", "Orzechy nerkowca",
                 "Oliwa z oliwek", "Masło", "Olej rzepakowy", "Skwarki", "Masło orzechowe", "Tahini", "Śmietana 18%",
                 "Oliwki", "Mleczko kokosowe", "Śmietanka bez laktozy"]).json()
    d2, m2, aw2 = _skladnik_z_planu(a2, "Awokado")
    r = c.get(f"{D}/assigned/{a2['id']}/swaps", headers=dieta["ha"],
              params={"day": d2["day"], "meal": m2["meal_id"], "ingredient": aw2["ingredient_id"]})
    assert r.status_code == 200 and r.json()["candidates"] == [] and r.json()["reason"] == "EXCLUDED"


def test_wymiana_v2_post_odrzuca_produkt_spoza_listy_takze_na_poziomie_2(dieta):
    """Kandydat z grupy pokrewnej, który odpadł sitem (albo w ogóle nie był liczony),
    nie przechodzi POST-em — ta sama ścieżka co GET (przegląd 14.09, brakujący test §6)."""
    c = dieta["c"]
    a = _assign(dieta).json()
    d, m, aw = _skladnik_z_planu(a, "Awokado")
    body = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                 params={"day": d["day"], "meal": m["meal_id"], "ingredient": aw["ingredient_id"]}).json()
    na_liscie = {x["product"] for x in body["candidates"]}
    prods = {p["name_pl"]: p for p in c.get(f"{D}/products", headers=dieta["hc"]).json()["products"]}
    # Masło i Skwarki są w grupie pokrewnej „tłuszcz” (poziom 2), ale nie na liście kandydatów.
    for nazwa in ("Masło", "Skwarki"):
        assert nazwa in prods and nazwa not in na_liscie, (nazwa, na_liscie)
        r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                   json={"day": d["day"], "meal_id": m["meal_id"], "ingredient_id": aw["ingredient_id"], "to_product_id": prods[nazwa]["id"]})
        assert r.status_code == 422, r.text
    assert c.get(f"{D}/clients/{dieta['cid']}/current", headers=dieta["hc"]).json()["swap_events"] == []


def test_wymiana_v2_gramatura_klienta_przechodzi_limity_porcji(dieta):
    """Gramatura z POST przechodzi te same limity v1.1 co gramatura silnika (≤ 300 g mięsa/ryby)."""
    c = dieta["c"]
    a = _assign(dieta).json()
    d, m, ku = _skladnik_z_planu(a, "Pierś z kurczaka (surowa)")
    body = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                 params={"day": d["day"], "meal": m["meal_id"], "ingredient": ku["ingredient_id"]}).json()
    kand = next(x for x in body["candidates"] if x["product"] == "Pierś z indyka (surowa)")
    zle = {"day": d["day"], "meal_id": m["meal_id"], "ingredient_id": ku["ingredient_id"], "to_product_id": kand["product_id"], "grams": 305}
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], json=zle)
    assert r.status_code == 422 and "limit" in r.json()["detail"], r.text
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], json={**zle, "grams": kand["grams"]})
    assert r.status_code == 201, r.text


def test_wymiana_v2_swappable_efektywne_dla_starej_migawki_tylko_none(dieta):
    """Migawka sprzed 0.69.0: NONE z grupą ≥ 2 dostaje przycisk przy odczycie, jawne
    `swappable: false` trenera dla roli P zostaje (przegląd 14.09)."""
    from dzik_os.models import DietAssigned
    c = dieta["c"]
    a = _assign(dieta).json()
    with db_session() as db:
        row = db.get(DietAssigned, a["id"])
        plan = json.loads(row.computed_plan_json)
        for dd in plan["days"]:
            for mm in dd["meals"]:
                for ii in mm["ingredients"]:
                    if ii["product"] in ("Brokuł", "Pierś z kurczaka (surowa)"):
                        ii["swappable"] = False
        row.computed_plan_json = json.dumps(plan, ensure_ascii=False)
        db.commit()
    cur = c.get(f"{D}/assigned/current", headers=dieta["ha"]).json()["assigned"]
    _, _, br = _skladnik_z_planu(cur, "Brokuł")
    _, m, ku = _skladnik_z_planu(cur, "Pierś z kurczaka (surowa)")
    assert br["role"] == "NONE" and br["swappable"] is True
    assert ku["role"] == "P" and ku["swappable"] is False
    d = next(x for x in cur["plan"]["days"] if any(mm["meal_id"] == m["meal_id"] for mm in x["meals"]))
    body = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
                 params={"day": d["day"], "meal": m["meal_id"], "ingredient": ku["ingredient_id"]}).json()
    assert body["blocked"] == "Ten składnik nie podlega wymianie." and body["candidates"] == []
    # Migawka w bazie nie została przepisana.
    with db_session() as db:
        zapis = json.loads(db.get(DietAssigned, a["id"]).computed_plan_json)
    assert any(ii["product"] == "Brokuł" and ii["swappable"] is False
               for dd in zapis["days"] for mm in dd["meals"] for ii in mm["ingredients"])


def test_wymiana_v2_rola_none_1_do_1_i_swappable_efektywne(dieta):
    c = dieta["c"]
    a = _assign(dieta).json()
    d, m, br = _skladnik_z_planu(a, "Brokuł")
    # Warzywo (rola NONE) ma przycisk — swappable liczone przy odczycie, migawka bez przepisywania.
    assert br["role"] == "NONE" and br["swappable"] is True
    q = {"day": d["day"], "meal": m["meal_id"], "ingredient": br["ingredient_id"]}
    body = c.get(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"], params=q).json()
    assert body["blocked"] is None and body["candidates"], body
    assert all(x["grams"] == br["grams"] and x["tier"] == 1 for x in body["candidates"])
    kal = next((x for x in body["candidates"] if x["product"] == "Kalafior"), body["candidates"][0])
    r = c.post(f"{D}/assigned/{a['id']}/swaps", headers=dieta["ha"],
               json={"day": d["day"], "meal_id": m["meal_id"], "ingredient_id": br["ingredient_id"], "to_product_id": kal["product_id"]})
    assert r.status_code == 201, r.text
    # Składnik STAŁY (przyprawa) nadal bez przycisku.
    for dd in a["plan"]["days"]:
        for mm in dd["meals"]:
            for ii in mm["ingredients"]:
                if ii["class"] == "STAŁY":
                    assert ii["swappable"] is False

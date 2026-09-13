"""API kreatora dań (0.57.0): trener generuje podgląd i zapisuje go jako
wersję planu diety ze śladem decyzji; klient widzi posiłek i „Dlaczego?”;
zamiana dania z kontrolą rewizji; publikacja receptur tylko z jawnymi
poświadczeniami; produkcja bez publikacji = brak pokrycia, nie obejście."""
from __future__ import annotations

import json

from conftest import CLIENT_A, CLIENT_B, COACH, get_user_id, login

from dzik_os import hos_bridge
from dzik_os.models import WiedzaSlad

ZAKRES_OK = {"adult": True, "no_pregnancy_or_breastfeeding": True, "no_medical_diet": True,
             "no_glucose_meds_or_diabetes": True}
# Silnik wymaga screeningu „cleared” także w podglądzie (instrukcja pakietu) —
# poświadczenia zakresu są więc częścią każdego wywołania.
PODGLAD = {"tryb": "preview", "days": 7, "meal_count": 3, "animal_policy": "vegan", "pattern": "balanced",
           "carb_policy": "standard", "start_date": "2026-09-14", "zakres": ZAKRES_OK}


def _ident(client, creds):
    h = login(client, creds)
    return h, get_user_id(client, h)


def test_profil_i_receptury_tylko_dla_trenera(seeded):
    hc = login(seeded, COACH)
    p = seeded.get("/api/coach/kulinaria/profile", headers=hc).json()
    assert p["receptury"]["razem"] == 300 and p["receptury"]["wg_statusu"] == {"draft": 300}
    assert p["mapowanie"]["z_wartosciami"] == 66 and p["mapowanie"]["status"] != "zweryfikowane"
    assert len(p["produkty"]) == 73 and p["versions"]["engine"] == "1.0.0"
    r = seeded.get("/api/coach/kulinaria/receptury", headers=hc, params={"status": "published"}).json()
    assert r["total"] == 0
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/coach/kulinaria/profile", headers=ha).status_code in (403, 404)
    assert seeded.post("/api/coach/kulinaria/generuj", headers=ha, json=PODGLAD).status_code in (403, 404)


def test_receptura_ma_wartosci_bazowe_albo_powod_braku(seeded):
    hc = login(seeded, COACH)
    lista = seeded.get("/api/coach/kulinaria/receptury", headers=hc).json()["items"]
    r = seeded.get(f"/api/coach/kulinaria/receptury/{lista[0]['id']}", headers=hc).json()
    assert r["status"] == "draft" and r["skladniki_opis"]["skladniki"]
    assert (r["nutrition_base"] is None) != (r["nutrition_problem"] is None)
    assert seeded.get("/api/coach/kulinaria/receptury/nie-ma", headers=hc).status_code == 404


def test_podglad_bez_zapisu_i_bez_wymyslonych_wartosci(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/kulinaria/generuj", headers=hc, json=PODGLAD)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["status"] == "draft_preview" and len(b["plan"]["days"]) == 7
    m = b["plan"]["days"][0]["meals"][0]
    assert m["draft"] is True and m["nutrition"] is None and m["skladniki"] and m["kroki"]
    assert b["plan"]["days"][0]["nutrition"] is None and b["shopping_list"][0]["name"]
    assert b["coverage"]["slots"]["breakfast"]["recipes"] > 0
    # Nic nie zapisano.
    ha, cid = _ident(seeded, CLIENT_A)
    plany = seeded.get(f"/api/clients/{cid}/nutrition", headers=ha).json()["plans"]
    assert all("kulinaria" not in (p["current_version"] or {}).get("content", {}) for p in plany)
    # Błędne wejście → 422, nie 500.
    assert seeded.post("/api/coach/kulinaria/generuj", headers=hc,
                       json={**PODGLAD, "animal_policy": "carnivore"}).status_code == 422


def test_produkcja_bez_publikacji_to_brak_pokrycia(seeded):
    hc = login(seeded, COACH)
    _ha, cid = _ident(seeded, CLIENT_A)
    body = {**PODGLAD, "tryb": "production", "client_id": cid, "animal_policy": "omnivore",
            "tolerance_pct": {"kcal": 5, "macro": 10}}
    b = seeded.post("/api/coach/kulinaria/generuj", headers=hc, json=body).json()
    assert b["status"] == "insufficient_catalog" and b["plan"] is None
    assert b["config"]["targets_reference"].startswith("nutrition_plan_version:")
    assert b["config"]["daily_bounds"]["energy_kcal"] == [2185.0, 2415.0]
    # Bez poświadczeń zakresu serwer nie uznaje screeningu za „cleared”.
    b2 = seeded.post("/api/coach/kulinaria/generuj", headers=hc, json={k: v for k, v in body.items() if k != "zakres"}).json()
    assert b2["status"] == "needs_review" and b2["meta"]["screening_status"] == "unknown"
    # Bez tolerancji trenera → 422 (kreator nie wymyśla granic).
    r = seeded.post("/api/coach/kulinaria/generuj", headers=hc, json={k: v for k, v in body.items() if k != "tolerance_pct"})
    assert r.status_code == 422
    # Klient B nie ma planu diety → 422 (kreator nie wymyśla celów).
    _, cid_b = _ident(seeded, CLIENT_B)
    r = seeded.post("/api/coach/kulinaria/generuj", headers=hc, json={**body, "client_id": cid_b})
    assert r.status_code in (404, 422)


def test_zapis_wymaga_potwierdzenia_szkicow_i_tworzy_slady(seeded):
    hc = login(seeded, COACH)
    ha, cid = _ident(seeded, CLIENT_A)
    body = {**PODGLAD, "days": 2, "client_id": cid, "title": "Menu testowe"}
    r = seeded.post("/api/coach/kulinaria/zapisz", headers=hc, json=body)
    assert r.status_code == 409 and r.json()["code"] == "DRAFT_CONFIRMATION_REQUIRED"
    r = seeded.post("/api/coach/kulinaria/zapisz", headers=hc, json={**body, "potwierdzam_szkice": True})
    assert r.status_code == 201, r.text
    plan_id, wersja = r.json()["id"], r.json()["version_no"]
    assert r.json()["traces"] == 6
    # Seed ma już aktywny plan → nowa wersja (v2), nie nowy plan.
    assert wersja == 2
    plany = seeded.get(f"/api/clients/{cid}/nutrition", headers=ha).json()["plans"]
    plan = next(p for p in plany if p["id"] == plan_id)
    tresc = plan["current_version"]["content"]
    assert plan["current_version_no"] == 2 and len(tresc["meals"]) == 6
    m = tresc["meals"][0]
    assert m["trace_target"] == "d0:m0" and m["draft"] is True and "Składniki:" in m["description"]
    # Cele planu (2300 kcal z seedu) przechodzą do nowej wersji — podgląd ich nie zeruje;
    # posiłki nie mają wartości.
    assert tresc["kulinaria"]["mode"] == "preview" and tresc["kcal"] == 2300 and m["nutrition"] is None
    # Po zapisie podglądu tryb produkcyjny nadal widzi cele klienta (nie 422).
    b = seeded.post("/api/coach/kulinaria/generuj", headers=hc, json={
        **PODGLAD, "tryb": "production", "client_id": cid, "tolerance_pct": {"kcal": 5, "macro": 10}}).json()
    assert b["status"] == "insufficient_catalog" and b["config"]["daily_bounds"]["energy_kcal"] == [2185.0, 2415.0]
    assert "screening_status" not in tresc["kulinaria"]["config"]
    # Ślad w tej samej transakcji, po stronie klienta „Dlaczego?” = explained.
    from dzik_os.db import SessionLocal
    with SessionLocal() as db:
        n = db.query(WiedzaSlad).filter_by(plan_id=plan_id, plan_revision=2, target_type="meal").count()
    assert n == 6
    seeded.get("/api/wiedza/start", headers=ha)
    w = seeded.post("/api/wiedza/wyjasnij", headers=ha, json={
        "plan_kind": "nutrition", "plan_id": plan_id, "plan_revision": 2, "target_type": "meal", "target_id": "d0:m0"})
    assert w.status_code == 200, w.text
    assert w.json()["status"] == "explained", w.json()
    assert w.json()["paragraphs"][0].startswith("Decyzja:")
    assert {a["target_id"] for a in w.json()["actions"] if a["type"] == "open_article"} >= {"k-meal", "k-portion"}
    # Audyt: metadane, bez składników i bez alergenów.
    zd = json.dumps(hos_bridge.event_store().all(), ensure_ascii=False)
    assert '"source": "kulinaria"' in zd and "allergens" not in zd


def test_zamiana_podglad_bez_mutacji_i_zatwierdzenie_z_kontrola_rewizji(seeded):
    hc = login(seeded, COACH)
    ha, cid = _ident(seeded, CLIENT_A)
    r = seeded.post("/api/coach/kulinaria/zapisz", headers=hc,
                    json={**PODGLAD, "days": 1, "client_id": cid, "potwierdzam_szkice": True})
    plan_id, v = r.json()["id"], r.json()["version_no"]
    tresc = seeded.get(f"/api/nutrition/{plan_id}/versions", headers=hc).json()["versions"][-1]["content"]
    stary = tresc["meals"][1]
    kandydaci = [x for x in seeded.get("/api/coach/kulinaria/receptury", headers=hc).json()["items"]
                 if "main" in x["meal_slots"] and x["id"] != stary["recipe_id"]]
    # Kandydat musi przejść filtry (wegańska): bierzemy z pokrycia podglądu.
    cov = seeded.post("/api/coach/kulinaria/generuj", headers=hc, json={**PODGLAD, "days": 1}).json()
    dozwolone = {mm["recipe_id"] for d in cov["plan"]["days"] for mm in d["meals"]}
    nowy = next(x for x in kandydaci if x["id"] in dozwolone or x["family_id"] != stary["family_id"])
    zam = {"plan_id": plan_id, "version_no": v, "meal_index": 1, "recipe_id": nowy["id"], "variant_id": "base"}
    p = seeded.post("/api/coach/kulinaria/zamiana/podglad", headers=hc, json=zam)
    assert p.status_code == 200, p.text
    # Podgląd nie zmienia planu.
    assert seeded.get(f"/api/nutrition/{plan_id}/versions", headers=hc).json()["versions"][-1]["version_no"] == v
    if not p.json()["ok"]:
        # Kandydat odrzucony przez ponowną kontrolę dnia — to też poprawna odpowiedź (409 przy zatwierdzeniu).
        z = seeded.post("/api/coach/kulinaria/zamiana/zatwierdz", headers=hc, json=zam)
        assert z.status_code == 409 and z.json()["code"] == "SWAP_REJECTED"
        return
    z = seeded.post("/api/coach/kulinaria/zamiana/zatwierdz", headers=hc, json=zam)
    assert z.status_code == 201, z.text
    assert z.json()["version_no"] == v + 1
    wersje = seeded.get(f"/api/nutrition/{plan_id}/versions", headers=hc).json()["versions"]
    assert wersje[-1]["content"]["meals"][1]["recipe_id"] == nowy["id"]
    assert wersje[-2]["content"]["meals"][1]["recipe_id"] == stary["recipe_id"]  # stara rewizja zostaje
    # Ponowne zatwierdzenie na nieaktualnej rewizji → 409 STALE_PLAN.
    z2 = seeded.post("/api/coach/kulinaria/zamiana/zatwierdz", headers=hc, json=zam)
    assert z2.status_code == 409 and z2.json()["code"] == "STALE_PLAN"
    # Klient widzi wyjaśnienie dla nowej rewizji.
    seeded.get("/api/wiedza/start", headers=ha)
    w = seeded.post("/api/wiedza/wyjasnij", headers=ha, json={
        "plan_kind": "nutrition", "plan_id": plan_id, "plan_revision": v + 1, "target_type": "meal", "target_id": "d0:m1"})
    assert w.status_code == 200 and w.json()["status"] == "explained"


def test_publikacja_tylko_z_jawnymi_poswiadczeniami(seeded):
    hc = login(seeded, COACH)
    rid = seeded.get("/api/coach/kulinaria/receptury", headers=hc).json()["items"][0]["id"]
    url = f"/api/coach/kulinaria/receptury/{rid}/publikuj"
    r = seeded.post(url, headers=hc, json={"kitchen": True, "dietitian": False, "allergens_checked": True,
                                           "expires_on": "2027-09-01", "validated_variants": ["base"]})
    assert r.status_code == 422
    r = seeded.post(url, headers=hc, json={"kitchen": True, "dietitian": True, "allergens_checked": True,
                                           "expires_on": "2027-09-01", "validated_variants": ["base"]})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published" and r.json()["review"]["reviewer_id"]
    rec = seeded.get(f"/api/coach/kulinaria/receptury/{rid}", headers=hc).json()
    assert rec["status"] == "published" and rec["review"]["expires_on"] == "2027-09-01"
    assert [v["validated"] for v in rec["portion_variants"] if v["id"] == "base"] == [True]
    assert seeded.get("/api/coach/kulinaria/receptury", headers=hc, params={"status": "published"}).json()["total"] == 1
    # Wycofanie.
    assert seeded.post(f"/api/coach/kulinaria/receptury/{rid}/wycofaj", headers=hc).json()["status"] == "retired"
    assert seeded.get("/api/coach/kulinaria/receptury", headers=hc, params={"status": "published"}).json()["total"] == 0
    zd = json.dumps(hos_bridge.event_store().all())
    assert "RECIPE_PUBLISHED" in zd and "RECIPE_RETIRED" in zd

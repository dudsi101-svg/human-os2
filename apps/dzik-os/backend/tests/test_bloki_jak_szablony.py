"""Bloki jak szablony (0.76.0): blok CARDIO jako trzeci rodzaj (preset z
silnika bez danych klienta, 9 wbudowanych, klucz idempotencji po celu),
`copy-to` z opcjonalnymi blokami (bez ciała bez zmian; 1/2/3 bloki; duplikat
rodzaju 422; cudzy blok 404; zarchiwizowany 422; brak dublowania, gdy szablon
miał już blok; ślad H_CARDIO także dla cardio z bloku), `from-blocks`
(walidacje, IDOR, klient 403), migracja 41 na „starej” bazie."""

from __future__ import annotations

import json

from conftest import CLIENT_A, COACH, create_user_with_role, get_user_id, login

from dzik_os.cardio import bloki as B
from dzik_os.cardio.bloki_wbudowane import BLOKI, klucz
from dzik_os.db import SessionLocal
from dzik_os.models import WiedzaSlad

BLOKI_API = "/api/coach/exercise-blocks"


def _bloki(client, hc) -> list[dict]:
    return client.get(BLOKI_API, headers=hc).json()["items"]


def _po_rodzaju(bloki: list[dict], kind: str, **f) -> dict:
    return next(b for b in bloki if b["kind"] == kind and all(b.get(k) == v for k, v in f.items()))


def _client_id(client, hc) -> str:
    clients = client.get("/api/coach/clients", headers=hc).json()["clients"]
    return next(c["client_id"] for c in clients if c["email"] == CLIENT_A["email"])


def _template_id(client, hc) -> str:
    templates = client.get("/api/plans/templates", headers=hc).json()["templates"]
    return next(t["id"] for t in templates if t["title"] == "Szablon: Push/Pull/Legs")


def _plan(client, hc, cid: str, plan_id: str) -> dict:
    plans = client.get(f"/api/clients/{cid}/plans", headers=hc).json()["plans"]
    return next(p for p in plans if p["id"] == plan_id)


def _rodzaje(day: dict) -> list[str]:
    return [ex.get("kind") or "strength" for ex in day["exercises"]]


# --- Wbudowane i klucz --------------------------------------------------------

def test_wbudowane_21_z_9_cardio_i_unikalny_klucz():
    cardio = [b for b in BLOKI if b["kind"] == "CARDIO"]
    assert len(BLOKI) == 21 and len(cardio) == 9
    assert {(b["level"], b["goal"]) for b in cardio} == {
        (lvl, g) for lvl in ("POCZATKUJACY", "SREDNIOZAAWANSOWANY", "ZAAWANSOWANY")
        for g in ("redukcja", "wydolnosc", "regeneracja")}
    klucze = [klucz(b) for b in BLOKI]
    assert len(set(klucze)) == 21
    for b in cardio:
        assert b["variant"] is None and b["cardio"]["trace"]["source"] == "blok"
        rx = b["cardio"]["prescription"]
        # Bez danych klienta: brak ud./min, kotwice %HRmax + RPE, zastrzeżenie o RPE.
        assert rx["hr_bpm_range"] is None and b["cardio"]["trace"]["hrmax_source"] == "none"
        assert 1 <= len(b["items"]) <= 3 and all(p["catalog"] is False for p in b["items"])
        assert b["duration_min"] == rx["duration_min"]
    # Struktura wg celu: regeneracja/redukcja ciągłe, wydolność interwały wg poziomu.
    assert all(b["cardio"]["prescription"]["structure"]["type"] == "ciagla" for b in cardio if b["goal"] != "wydolnosc")
    assert {b["cardio"]["prescription"]["structure"]["label"] for b in cardio if b["goal"] == "wydolnosc"} == {
        "8×1 min / przerwa 1 min", "6×2 min / przerwa 2 min", "4×4 min / przerwa 3 min"}
    assert {b["cardio"]["prescription"]["duration_min"] for b in cardio if b["goal"] == "regeneracja"} == {20, 25}


def test_lista_cardio_ma_cel_preset_i_wariant_null(seeded):
    hc = login(seeded, COACH)
    lista = seeded.get(BLOKI_API, headers=hc).json()
    assert lista["dictionaries"]["kinds"]["CARDIO"] == "aeroby (cardio)"
    assert set(lista["dictionaries"]["goals"]) == {"redukcja", "wydolnosc", "regeneracja"}
    b = _po_rodzaju(lista["items"], "CARDIO", level="POCZATKUJACY", goal="regeneracja")
    assert b["variant"] is None and b["variant_label"] is None and b["goal_label"].startswith("Regeneracja")
    assert b["cardio"]["goal_mix"] == {"redukcja": 0.0, "wydolnosc": 0.0, "regeneracja": 1.0}
    assert b["cardio"]["machines"] == ["rowerek", "bieznia", "wioslarz"]
    # Rozgrzewka/rozciąganie bez zmian kształtu.
    w = _po_rodzaju(lista["items"], "WARMUP", level="POCZATKUJACY", variant="C")
    assert w["cardio"] is None and w["goal"] is None and w["variant_label"] == "całe ciało"


def test_crud_bloku_cardio_preset_liczy_serwer(seeded):
    hc = login(seeded, COACH)
    r = seeded.post(BLOKI_API, headers=hc, json={"name": "Moje aeroby", "kind": "CARDIO",
                                                   "level": "ZAAWANSOWANY", "goal": "wydolnosc", "machines": ["steper"]})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["variant"] is None and b["goal"] == "wydolnosc" and b["cardio"]["machines"] == ["steper"]
    assert b["cardio"]["prescription"]["structure"]["label"] == "4×4 min / przerwa 3 min"
    assert b["duration_min"] == 28 and len(b["items"]) == 3 and "Steper" in b["items"][0]["name"]
    # PUT przelicza preset i pozwala na własne pozycje opisowe.
    r = seeded.put(f"{BLOKI_API}/{b['id']}", headers=hc, json={
        "name": "Moje aeroby", "kind": "CARDIO", "level": "POCZATKUJACY", "goal": "regeneracja",
        "items": [{"name": "Spokojny marsz", "dose": "20 min"}]})
    assert r.status_code == 200, r.text
    assert r.json()["cardio"]["prescription"]["duration_min"] == 20 and r.json()["items"][0]["name"] == "Spokojny marsz"
    assert r.json()["cardio"]["trace"]["goal"] == "regeneracja"
    # Bez celu → 422; nieznane urządzenie → 422; rozgrzewka bez wariantu → 422.
    assert seeded.post(BLOKI_API, headers=hc, json={"name": "x", "kind": "CARDIO", "level": "POCZATKUJACY"}).status_code == 422
    assert seeded.post(BLOKI_API, headers=hc, json={"name": "x", "kind": "CARDIO", "level": "POCZATKUJACY",
                                                       "goal": "redukcja", "machines": ["hulajnoga"]}).status_code == 422
    assert seeded.post(BLOKI_API, headers=hc, json={"name": "x", "kind": "WARMUP", "level": "POCZATKUJACY"}).status_code == 422
    # Zmiana rodzaju na rozgrzewkę kasuje preset.
    r = seeded.put(f"{BLOKI_API}/{b['id']}", headers=hc, json={"name": "Już nie cardio", "kind": "WARMUP",
                                                                 "level": "POCZATKUJACY", "variant": "G"})
    assert r.status_code == 200 and r.json()["cardio"] is None and r.json()["variant"] == "G"


def test_wlasny_blok_cardio_nie_blokuje_wbudowanego_o_tym_samym_kluczu(seeded):
    """Klucz idempotencji dotyczy tylko źródła wbudowanego — blok trenera z tym samym
    poziomem i celem nie sprawia, że `load-builtin` coś pomija ani dubluje."""
    hc = login(seeded, COACH)
    r = seeded.post(BLOKI_API, headers=hc, json={"name": "Własne", "kind": "CARDIO", "level": "POCZATKUJACY", "goal": "redukcja"})
    assert r.status_code == 201
    r = seeded.post(f"{BLOKI_API}/load-builtin", headers=hc)
    assert r.json()["created"] == 0 and r.json()["skipped"] == 21
    assert sum(1 for b in _bloki(seeded, hc) if b["kind"] == "CARDIO") == 10


# --- Wstawianie do planu (edytor) ---------------------------------------------

def test_pozycja_cardio_z_bloku_w_szablonie_i_planie_ze_sladem(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    blok = _po_rodzaju(_bloki(seeded, hc), "CARDIO", level="SREDNIOZAAWANSOWANY", goal="redukcja")
    poz = {"name": blok["name"], "kind": "cardio", "block_id": blok["id"], "cardio": blok["cardio"],
           "block": {k: blok[k] for k in ("name", "kind", "level", "variant", "duration_min", "items")}}
    # Szablon (bez klienta) przyjmuje cardio z bloku — bez śladu (nie ma klienta).
    r = seeded.post("/api/plans", headers=hc, json={"client_id": None, "title": "Szablon z aerobami",
                                                     "version": {"reason": "test", "days": [{"name": "A", "exercises": [poz]}]}})
    assert r.status_code == 201, r.text
    with SessionLocal() as db:
        assert db.query(WiedzaSlad).filter_by(plan_id=r.json()["id"]).count() == 0
    # Plan klienta → ślad H_CARDIO z faktami presetu (bez wieku, źródło HRmax = none).
    r = seeded.post("/api/plans", headers=hc, json={"client_id": cid, "title": "Plan z aerobami",
                                                     "version": {"reason": "test", "days": [{"name": "A", "exercises": [poz]}]}})
    assert r.status_code == 201, r.text
    with SessionLocal() as db:
        s = db.query(WiedzaSlad).filter_by(plan_id=r.json()["id"], target_type="cardio_prescription").one()
        fakty = {f["key"]: f["value"] for f in json.loads(s.facts_json)}
        assert s.rule_id == "H_CARDIO" and fakty["hrmax_source"] == "none" and fakty["goal_redukcja"] == 60
    # Migawka rozgrzewki przy pozycji cardio → 422 (spójność rodzaju).
    zle = {**poz, "block": {**poz["block"], "kind": "WARMUP", "variant": "C"}}
    r = seeded.post("/api/plans", headers=hc, json={"client_id": cid, "title": "x",
                                                     "version": {"reason": "t", "days": [{"name": "A", "exercises": [zle]}]}})
    assert r.status_code == 422


# --- copy-to z blokami -------------------------------------------------------

def test_copy_to_bez_ciala_bez_zmian_a_z_blokami_dodaje_do_kazdego_dnia(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid, tid = _client_id(seeded, hc), _template_id(seeded, hc)
    r = seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc)
    assert r.status_code == 201 and set(r.json()) == {"id", "version_id", "version_no"}
    bloki = _bloki(seeded, hc)
    w = _po_rodzaju(bloki, "WARMUP", level="POCZATKUJACY", variant="C")
    c = _po_rodzaju(bloki, "CARDIO", level="POCZATKUJACY", goal="regeneracja")
    s = _po_rodzaju(bloki, "STRETCH", variant="C")
    # 1 blok.
    r = seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc, json={"blocks": [w["id"]]})
    assert r.status_code == 201, r.text
    assert r.json()["blocks_applied"]["added"] == {"warmup": 3, "cardio": 0, "stretch": 0}
    plan = _plan(seeded, hc, cid, r.json()["id"])
    assert all(_rodzaje(d)[0] == "warmup_block" for d in plan["current_version"]["content"]["days"])
    assert "bloki" in plan["current_version"]["reason"]
    # 3 bloki: rozgrzewka na górze, cardio po siłowych, rozciąganie na dole; ślad per dzień.
    r = seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc, json={"blocks": [s["id"], c["id"], w["id"]]})
    assert r.status_code == 201, r.text
    assert r.json()["blocks_applied"]["added"] == {"warmup": 3, "cardio": 3, "stretch": 3}
    assert r.json()["blocks_applied"]["skipped_days"] == []
    plan = _plan(seeded, hc, cid, r.json()["id"])
    for d in plan["current_version"]["content"]["days"]:
        rodz = _rodzaje(d)
        assert rodz[0] == "warmup_block" and rodz[-2:] == ["cardio", "stretch_block"]
        assert all(k == "strength" for k in rodz[1:-2]) and len(rodz) >= 4
        cardio = d["exercises"][-2]
        assert cardio["block_id"] == c["id"] and cardio["block"]["kind"] == "CARDIO" and cardio["cardio"]["trace"]["source"] == "blok"
    # Klient widzi to samo (kopia niezależna od bloku — archiwizacja nic nie zmienia).
    assert seeded.post(f"{BLOKI_API}/{c['id']}/status", headers=hc, json={"status": "ARCHIVED"}).status_code == 200
    plan_k = _plan(seeded, ha, cid, plan["id"])
    assert plan_k["current_version"]["content"] == plan["current_version"]["content"]
    with SessionLocal() as db:
        assert db.query(WiedzaSlad).filter_by(plan_id=plan["id"], target_type="cardio_prescription").count() == 3


def test_copy_to_odmowy_duplikat_cudzy_zarchiwizowany_i_brak_dublowania(seeded):
    hc = login(seeded, COACH)
    cid, tid = _client_id(seeded, hc), _template_id(seeded, hc)
    bloki = _bloki(seeded, hc)
    w1 = _po_rodzaju(bloki, "WARMUP", level="POCZATKUJACY", variant="C")
    w2 = _po_rodzaju(bloki, "WARMUP", level="POCZATKUJACY", variant="G")
    c = _po_rodzaju(bloki, "CARDIO", level="ZAAWANSOWANY", goal="wydolnosc")
    # Duplikat rodzaju → 422 po polsku.
    r = seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc, json={"blocks": [w1["id"], w2["id"]]})
    assert r.status_code == 422 and "tego samego rodzaju" in r.json()["detail"]
    # Ten sam blok dwa razy → 422; cztery bloki → 422 (schemat).
    assert seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc, json={"blocks": [w1["id"], w1["id"]]}).status_code == 422
    assert seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc,
                       json={"blocks": [w1["id"], c["id"], w2["id"], w2["id"]]}).status_code == 422
    # Nieistniejący → 404.
    assert seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc, json={"blocks": ["HOS-BLK-000000000000"]}).status_code == 404
    # Cudzy blok → 404 (IDOR), własny szablon i klient poprawne.
    create_user_with_role("obcy.bloki@example.com", "ObcyTrener#2026", "Obcy", "COACH")
    ho = login(seeded, {"email": "obcy.bloki@example.com", "password": "ObcyTrener#2026"})
    r = seeded.post(BLOKI_API, headers=ho, json={"name": "Obca rozgrzewka", "kind": "WARMUP", "level": "POCZATKUJACY", "variant": "C"})
    obcy = r.json()["id"]
    assert seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc, json={"blocks": [obcy]}).status_code == 404
    # Zarchiwizowany → 422.
    assert seeded.post(f"{BLOKI_API}/{w2['id']}/status", headers=hc, json={"status": "ARCHIVED"}).status_code == 200
    r = seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc, json={"blocks": [w2["id"]]})
    assert r.status_code == 422 and "zarchiwizowany" in r.json()["detail"]
    # Szablon z rozgrzewką w dniu 1: ten dzień nie jest dublowany, pozostałe dostają blok.
    tpl = seeded.get("/api/plans/templates", headers=hc).json()["templates"]
    dni = next(t for t in tpl if t["id"] == tid)["current_version"]["content"]["days"]
    dni = json.loads(json.dumps(dni))
    dni[0]["exercises"].insert(0, {"name": w1["name"], "kind": "warmup_block", "block_id": w1["id"],
                                   "block": {k: w1[k] for k in ("name", "kind", "level", "variant", "duration_min", "items")}})
    assert seeded.post(f"/api/plans/{tid}/versions", headers=hc, json={"reason": "rozgrzewka w dniu 1", "days": dni}).status_code == 201
    r = seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc, json={"blocks": [w2["id"] if False else w1["id"], c["id"]]})
    assert r.status_code == 201, r.text
    ra = r.json()["blocks_applied"]
    assert ra["added"] == {"warmup": 2, "cardio": 3, "stretch": 0}
    assert ra["skipped_days"] == [{"day_index": 0, "day_name": "Push", "kind": "warmup"}]
    plan = _plan(seeded, hc, cid, r.json()["id"])
    assert _rodzaje(plan["current_version"]["content"]["days"][0]).count("warmup_block") == 1


def test_copy_to_waliduje_exercise_id_jak_create_plan(seeded):
    """Luka 5 z 0.73.0: kopia szablonu z ćwiczeniem spoza aktywnej bazy → 422 (jak `POST /plans`)."""
    hc = login(seeded, COACH)
    cid = _client_id(seeded, hc)
    r = seeded.post("/api/coach/exercises", headers=hc, json={"name": "Tymczasowe ćwiczenie do archiwum",
                                                               "muscle_group": "INNE", "how_to": "Krok 1."})
    assert r.status_code == 201, r.text
    eid = r.json()["id"]
    r = seeded.post("/api/plans", headers=hc, json={"client_id": None, "title": "Szablon z archiwalnym",
                                                     "version": {"reason": "t", "days": [{"name": "A", "exercises": [
                                                         {"name": "Tymczasowe ćwiczenie do archiwum", "exercise_id": eid}]}]}})
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    assert seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc).status_code == 201
    assert seeded.post(f"/api/coach/exercises/{eid}/status", headers=hc, params={"status": "ARCHIVED"}).status_code == 200
    r = seeded.post(f"/api/plans/{tid}/copy-to/{cid}", headers=hc)
    assert r.status_code == 422 and eid in r.json()["detail"]


# --- from-blocks -------------------------------------------------------------

def test_from_blocks_tworzy_plan_z_samych_blokow(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = _client_id(seeded, hc)
    bloki = _bloki(seeded, hc)
    c = _po_rodzaju(bloki, "CARDIO", level="POCZATKUJACY", goal="regeneracja")
    s = _po_rodzaju(bloki, "STRETCH", variant="D")
    r = seeded.post(f"/api/clients/{cid}/plans/from-blocks", headers=hc, json={
        "title": "Tylko aeroby", "days": [{"name": "Dzień 1", "weekday": 2}, {"name": "Dzień 2"}], "blocks": [c["id"], s["id"]]})
    assert r.status_code == 201, r.text
    assert r.json()["version_no"] == 1 and r.json()["blocks_applied"]["added"] == {"warmup": 0, "cardio": 2, "stretch": 2}
    plan = _plan(seeded, ha, cid, r.json()["id"])
    assert plan["title"] == "Tylko aeroby" and plan["is_template"] is False
    assert plan["current_version"]["reason"].startswith("Plan z bloków")
    days = plan["current_version"]["content"]["days"]
    assert [d["name"] for d in days] == ["Dzień 1", "Dzień 2"] and days[0]["weekday"] == 2 and days[1]["weekday"] is None
    assert all(_rodzaje(d) == ["cardio", "stretch_block"] for d in days)
    with SessionLocal() as db:
        assert db.query(WiedzaSlad).filter_by(plan_id=plan["id"], target_type="cardio_prescription").count() == 2
    # Walidacje: 0 bloków, 8 dni, 4 bloki, duplikat rodzaju.
    assert seeded.post(f"/api/clients/{cid}/plans/from-blocks", headers=hc,
                       json={"title": "x", "days": [{"name": "D"}], "blocks": []}).status_code == 422
    assert seeded.post(f"/api/clients/{cid}/plans/from-blocks", headers=hc,
                       json={"title": "x", "days": [{"name": f"D{i}"} for i in range(8)], "blocks": [c["id"]]}).status_code == 422
    s2 = _po_rodzaju(bloki, "STRETCH", variant="G")
    r = seeded.post(f"/api/clients/{cid}/plans/from-blocks", headers=hc,
                    json={"title": "x", "days": [{"name": "D"}], "blocks": [s["id"], s2["id"]]})
    assert r.status_code == 422 and "tego samego rodzaju" in r.json()["detail"]


def test_from_blocks_klient_403_a_obcy_trener_404(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = _client_id(seeded, hc)
    c = _po_rodzaju(_bloki(seeded, hc), "CARDIO", level="POCZATKUJACY", goal="redukcja")
    body = {"title": "x", "days": [{"name": "D"}], "blocks": [c["id"]]}
    assert seeded.post(f"/api/clients/{cid}/plans/from-blocks", headers=ha, json=body).status_code == 403
    create_user_with_role("obcy.fb@example.com", "ObcyTrener#2026", "Obcy", "COACH")
    ho = login(seeded, {"email": "obcy.fb@example.com", "password": "ObcyTrener#2026"})
    assert seeded.post(f"/api/clients/{cid}/plans/from-blocks", headers=ho, json=body).status_code == 404


# --- Czysta logika składania --------------------------------------------------

def test_zloz_bloki_do_dni_kolejnosc_i_brak_dublowania():
    from dzik_os.models import ExerciseBlock

    w = ExerciseBlock(id="W", kind="WARMUP", level="POCZATKUJACY", variant="C", name="R", status="ACTIVE", items_json="[]")
    s = ExerciseBlock(id="S", kind="STRETCH", level=None, variant="C", name="S", status="ACTIVE", items_json="[]")
    c = ExerciseBlock(id="C", kind="CARDIO", level="POCZATKUJACY", variant="", name="C", status="ACTIVE", items_json="[]",
                      cardio_json=json.dumps(BLOKI[-1]["cardio"]))
    dni = [{"name": "A", "exercises": [{"name": "Przysiad"}]},
           {"name": "B", "exercises": [{"name": "Wyciskanie"}, {"name": "S", "kind": "stretch_block", "block": {}}]}]
    out, raport = B.zloz_bloki_do_dni(dni, [s, c, w])
    assert [ex.get("kind", "strength") for ex in out[0]["exercises"]] == ["warmup_block", "strength", "cardio", "stretch_block"]
    assert [ex.get("kind", "strength") for ex in out[1]["exercises"]] == ["warmup_block", "strength", "cardio", "stretch_block"]
    assert raport["added"] == {"warmup": 2, "cardio": 2, "stretch": 1}
    assert raport["skipped_days"] == [{"day_index": 1, "day_name": "B", "kind": "stretch"}]
    assert dni[0]["exercises"] == [{"name": "Przysiad"}]  # wejście nietknięte
    assert out[0]["exercises"][2]["block_id"] == "C" and out[0]["exercises"][2]["cardio"]["trace"]["source"] == "blok"
    # Blok CARDIO bez presetu → błąd zestawu (nie KeyError).
    c.cardio_json = None
    try:
        B.zloz_bloki_do_dni(dni, [c])
        raise AssertionError("oczekiwano BladZestawu")
    except B.BladZestawu as exc:
        assert "presetu" in str(exc)


# --- Migracja 41 --------------------------------------------------------------

def test_migracja_41_dodaje_cardio_json_na_starej_bazie(tmp_path):
    """Stara baza (po 40, `exercise_blocks` bez `cardio_json`) dostaje kolumnę
    bez utraty wierszy; świeża baza ma ją z ORM."""
    from sqlalchemy import create_engine, text

    from dzik_os.db import MIGRATIONS, run_migrations

    eng = create_engine(f"sqlite:///{tmp_path}/stara.db")
    assert run_migrations(eng)[-1] == 41 and MIGRATIONS[-1][0] == 41
    with eng.begin() as conn:
        # Cofnięcie do stanu sprzed 41: kolumna zdjęta, stempel usunięty, jeden wiersz zostaje.
        conn.execute(text("ALTER TABLE exercise_blocks DROP COLUMN cardio_json"))
        conn.execute(text("DELETE FROM schema_migrations WHERE version = 41"))
        # Silnik testu bez PRAGMA foreign_keys — wiersz bloku bez wiersza użytkownika wystarczy.
        conn.execute(text("INSERT INTO exercise_blocks(id, coach_id, kind, variant, name, items_json, source, status, "
                          "created_by, created_at, updated_at) VALUES ('B1', 'U1', 'WARMUP', 'C', 'Stary', '[]', "
                          "'trener', 'ACTIVE', 'U1', 'x', 'x')"))
    assert run_migrations(eng) == [41]
    with eng.connect() as conn:
        cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(exercise_blocks)")]
        assert "cardio_json" in cols
        assert conn.exec_driver_sql("SELECT cardio_json FROM exercise_blocks WHERE id='B1'").scalar() is None

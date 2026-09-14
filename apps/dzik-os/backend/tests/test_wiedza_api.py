"""Wiedza — API: biblioteka, wyszukiwanie, zakładki, wyjaśnienia ze
śladem, historia, izolacja między klientami, redakcja, flaga, schematy.

Pokrywa przypadki K01, K02, K06–K11, K18–K21, K25–K30, K33, K34, K36,
K37 (zakres: zakładki/odczyty/ślady), K40 z pliku 09 pakietu.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import CLIENT_A, CLIENT_B, COACH, get_user_id, login
from jsonschema import Draft202012Validator

from dzik_os.config import settings
from dzik_os.db import db_session
from dzik_os.models import WiedzaArtykul, WiedzaSlad
from dzik_os.wiedza import dane, slad, tresci

PRZYKLADY = json.loads(
    (Path(__file__).parent / "dane" / "konfigurator_plany_28_dni.json").read_text(encoding="utf-8")
)
PRZYKLADY = PRZYKLADY if isinstance(PRZYKLADY, list) else PRZYKLADY["examples"]


def _plan_a(client, headers) -> dict:
    return client.get("/api/wiedza/start", headers=headers).json()["plan"]


def _wyjasnij(client, headers, **body):
    return client.post("/api/wiedza/wyjasnij", headers=headers, json={"plan_kind": "training", **body})


# --- biblioteka ---------------------------------------------------------------


def test_tresci_startowe_zgodne_ze_schematem_i_zaimportowane_raz(seeded) -> None:
    """Każdy wiersz importu waliduje się schematem `article`; ponowny
    import niczego nie dodaje (idempotencja po id+rewizja)."""
    walidator = Draft202012Validator(dane.schematy()["article"])
    with db_session() as db:
        rows = db.query(WiedzaArtykul).all()
        assert len(rows) == len(dane.tresci_startowe()["articles"]) == 48
        for r in rows:
            assert not list(walidator.iter_errors(tresci.do_schematu(r))), r.article_id
        assert tresci.zaimportuj_startowe(db) == {"artykuly": 0, "powiazania": 0}
        assert all(tresci.pokrycie_typow(db).values())


def test_start_bez_planu_daje_biblioteke_bez_pozornej_personalizacji(client) -> None:
    """K01/K02: konto bez planu i dziennika — podstawy, bez wymyślonych
    wyników; trener bez planu klienta też widzi tylko bibliotekę."""
    from conftest import create_user_with_role

    create_user_with_role("nowy@example.com", "Nowy#2026!xx", "Nowy", "CLIENT")
    h = login(client, {"email": "nowy@example.com", "password": "Nowy#2026!xx"})
    r = client.get("/api/wiedza/start", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["wlaczone"] is True and d["plan"] is None and d["dieta"] is False
    assert d["ostatnie_zmiany"] == []
    assert 1 <= len(d["dla_ciebie"]) <= 3
    assert all(f["powod"] == "Podstawy na start" for f in d["dla_ciebie"])
    assert "no-store" in r.headers["cache-control"]


def test_lista_i_karta_z_kategoria_i_zrodlami(seeded) -> None:
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/wiedza/artykuly?kategoria=basics", headers=ha)
    assert r.status_code == 200
    ids = {i["id"] for i in r.json()["items"]}
    assert ids == {"k-safety", "k-evidence"}
    k = seeded.get("/api/wiedza/artykuly/k-evidence", headers=ha).json()
    assert k["szkic"] is True and k["review"]["approved"] is False
    assert k["sources"][0]["id"] == "H_EDITORIAL" and k["sources"][0]["rola"] == "merytoryczne"
    # Inspiracje produktowe są oznaczone i nie udają źródeł naukowych.
    assert all(s["rola"] != "inspiracja_produktowa" for s in k["sources"])
    assert seeded.get("/api/wiedza/artykuly/nie-ma", headers=ha).status_code == 404


def test_szkice_niewidoczne_na_produkcji(seeded, monkeypatch) -> None:
    """K19: w produkcji flaga szkiców jest ignorowana — biblioteka, karta,
    wyszukiwanie i feed nie zwracają treści roboczych."""
    ha = login(seeded, CLIENT_A)
    monkeypatch.setattr(settings, "env", "production")
    assert settings.wiedza_szkice is False
    assert seeded.get("/api/wiedza/artykuly", headers=ha).json()["total"] == 0
    assert seeded.get("/api/wiedza/artykuly/k-rir", headers=ha).status_code == 404
    assert seeded.post("/api/wiedza/szukaj", headers=ha, json={"q": "zapas"}).json()["items"] == []
    s = seeded.get("/api/wiedza/start", headers=ha).json()
    assert s["szkice_widoczne"] is False and s["dla_ciebie"] == []
    # Publikacja przez trenera odsłania kartę także w produkcji.
    hc = login(seeded, COACH)
    assert seeded.post("/api/coach/wiedza/artykuly/k-rir/publikuj", headers=hc, json={"revision": 1}).status_code == 200
    assert seeded.get("/api/wiedza/artykuly/k-rir", headers=ha).status_code == 200
    assert seeded.get("/api/wiedza/artykuly", headers=ha).json()["total"] == 1


def test_wyszukiwanie_aliasy_polskie_znaki_literowki_i_brak(seeded) -> None:
    """K25/K26: „zapas”, „rir”, „powtorzenia” trafiają przez aliasy;
    brak wyniku to pusta lista, nie zmyślona odpowiedź."""
    ha = login(seeded, CLIENT_A)

    def ids(q):
        return [i["id"] for i in seeded.post("/api/wiedza/szukaj", headers=ha, json={"q": q}).json()["items"]]

    assert ids("zapas")[0] == "k-rir"
    assert ids("RIR")[0] == "k-rir"
    assert "k-sets" in ids("powtorzenia") and "k-rir" in ids("powtorzenia")
    assert ids("kalorje") == ["k-energy"]  # literówka w granicy jednej zmiany
    assert ids("xyzzyqq") == []
    assert seeded.post("/api/wiedza/szukaj", headers=ha, json={"q": "x" * 201}).status_code == 422


def test_zapytanie_nie_trafia_do_audytu(seeded) -> None:
    """K27: surowe zapytanie (może zawierać dane zdrowotne) nie jest
    zapisywane — audyt nie zna jego treści."""
    from hos_engine.sqlite_store import SQLiteEventStore

    ha = login(seeded, CLIENT_A)
    tajne = "bol kolana po operacji"
    seeded.get("/api/wiedza/start", headers=ha)  # zdarzenie KNOWLEDGE_OPENED (bez treści)
    seeded.post("/api/wiedza/szukaj", headers=ha, json={"q": tajne})
    zdarzenia = json.dumps(SQLiteEventStore(settings.audit_db_path).all(), ensure_ascii=False)
    assert "KNOWLEDGE" in zdarzenia  # audyt działa, ale nie zna zapytania
    assert tajne not in zdarzenia


def test_zakladka_idempotentna_i_wycofanie_z_zamiennikiem(seeded) -> None:
    """K28, K18, K20: dwukrotny zapis = jedna zakładka; zakładka wskazuje
    artykuł, więc po nowej rewizji otwiera najnowszą; wycofanie → 410 z
    zamiennikiem, a w Zapisanych „Materiał jest aktualizowany”."""
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    assert seeded.put("/api/wiedza/zakladki/k-sets", headers=ha).json() == {"zapisany": True}
    assert seeded.put("/api/wiedza/zakladki/k-sets", headers=ha).status_code == 200
    assert len(seeded.get("/api/wiedza/zakladki", headers=ha).json()["items"]) == 1
    assert seeded.put("/api/wiedza/zakladki/nie-ma", headers=ha).status_code == 404
    # nowa opublikowana rewizja
    assert seeded.post("/api/coach/wiedza/artykuly/k-sets/publikuj", headers=hc, json={"revision": 1}).status_code == 200
    r = seeded.post("/api/coach/wiedza/artykuly/k-sets/rewizje", headers=hc, json={"summary": "Nowy skrót po recenzji"})
    assert r.status_code == 201 and r.json()["revision"] == 2 and r.json()["status"] == "draft"
    assert seeded.get("/api/wiedza/artykuly/k-sets", headers=ha).json()["revision"] == 1  # szkic nie wypiera publikacji
    assert seeded.post("/api/coach/wiedza/artykuly/k-sets/publikuj", headers=hc, json={"revision": 2}).status_code == 200
    k = seeded.get("/api/wiedza/artykuly/k-sets", headers=ha).json()
    assert k["revision"] == 2 and k["summary"] == "Nowy skrót po recenzji"
    with db_session() as db:
        assert db.query(WiedzaArtykul).filter_by(article_id="k-sets", revision=1).one().status == "retired"
    # wycofanie
    assert seeded.post("/api/coach/wiedza/artykuly/k-sets/wycofaj", headers=hc, json={"zamiennik_id": "k-rir"}).status_code == 200
    r = seeded.get("/api/wiedza/artykuly/k-sets", headers=ha)
    assert r.status_code == 410 and r.json()["code"] == "RETIRED" and r.json()["zamiennik"]["id"] == "k-rir"
    z = seeded.get("/api/wiedza/zakladki", headers=ha).json()["items"][0]
    assert z["aktualizowany"] is True and z["zamiennik"] == "k-rir"
    assert "k-sets" not in {i["id"] for i in seeded.get("/api/wiedza/artykuly", headers=ha).json()["items"]}
    assert seeded.delete("/api/wiedza/zakladki/k-sets", headers=ha).json() == {"zapisany": False}


def test_publikacja_wymaga_zrodel_recenzenta_i_terminu(seeded) -> None:
    """K33/K34: klient nie publikuje; bez źródeł lub z datą w przeszłości
    serwer odmawia; publikacja ustawia recenzenta = konto trenera."""
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    assert seeded.post("/api/coach/wiedza/artykuly/k-rir/publikuj", headers=ha, json={"revision": 1}).status_code in (403, 404)
    r = seeded.post("/api/coach/wiedza/artykuly/k-rir/rewizje", headers=hc, json={"source_ids": []})
    rev = r.json()["revision"]
    r = seeded.post("/api/coach/wiedza/artykuly/k-rir/publikuj", headers=hc, json={"revision": rev})
    assert r.status_code == 422 and "brak źródeł" in r.text
    r = seeded.post("/api/coach/wiedza/artykuly/k-rir/publikuj", headers=hc, json={"revision": 1, "next_review_at": "2020-01-01"})
    assert r.status_code == 422 and "przyszłości" in r.text
    r = seeded.post("/api/coach/wiedza/artykuly/k-rir/publikuj", headers=hc, json={"revision": 1, "next_review_at": "2099-01-01"})
    assert r.status_code == 200
    k = seeded.get("/api/wiedza/artykuly/k-rir", headers=ha).json()
    assert k["review"]["approved"] is True
    assert k["review"]["reviewer_id"] == get_user_id(seeded, hc)
    assert k["review"]["next_review_at"] == "2099-01-01"
    # Ponowna publikacja tej samej rewizji jest odrzucana.
    assert seeded.post("/api/coach/wiedza/artykuly/k-rir/publikuj", headers=hc, json={"revision": 1}).status_code == 422


def test_karta_po_terminie_przegladu_wypada_z_rekomendacji_i_resolvera(seeded) -> None:
    """K21: wygasły przegląd — karta zostaje w bibliotece z oznaczeniem,
    ale nie w feedzie; karta bezpieczeństwa znika też z biblioteki."""
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    for aid in ("k-deload", "k-safety"):
        assert seeded.post(f"/api/coach/wiedza/artykuly/{aid}/publikuj", headers=hc, json={"revision": 1}).status_code == 200
    with db_session() as db:
        for aid in ("k-deload", "k-safety"):
            db.query(WiedzaArtykul).filter_by(article_id=aid, status="published").one().next_review_at = "2020-01-01"
    s = seeded.get("/api/wiedza/start", headers=ha).json()
    assert "k-deload" not in {f["id"] for f in s["dla_ciebie"]}
    lista = {i["id"]: i for i in seeded.get("/api/wiedza/artykuly", headers=ha).json()["items"]}
    assert lista["k-deload"]["przeglad_po_terminie"] is True
    assert "k-safety" not in lista


# --- wyjaśnienia ------------------------------------------------------------


def test_stary_plan_bez_sladu_daje_missing_trace_z_edukacja_ogolna(seeded) -> None:
    """K06: plan z seedu powstał bez śladu — brak rekonstrukcji powodu,
    za to karta ogólna typu elementu."""
    ha = login(seeded, CLIENT_A)
    p = _plan_a(seeded, ha)
    r = _wyjasnij(seeded, ha, plan_id=p["plan_id"], plan_revision=p["version_no"],
                  target_type="exercise_prescription", target_id="d0:e0")
    assert r.status_code == 200
    w = r.json()
    assert w["status"] == "missing_trace" and w["trace_id"] is None
    assert "Nie mamy zapisanego uzasadnienia" in w["paragraphs"][0]
    assert not list(Draft202012Validator(dane.schematy()["explanation_result"]).iter_errors(w))
    r = _wyjasnij(seeded, ha, plan_id=p["plan_id"], plan_revision=p["version_no"],
                  target_type="rir", target_id="d0:e0")
    assert [a["id"] for a in r.json()["article_refs"]] == ["k-rir"]


def test_nowa_wersja_trenera_zapisuje_slad_i_tlumaczy_sie_oryginalnym_powodem(seeded) -> None:
    """K14 + K07 + K08 + K18: ślad `professional` powstaje w tej samej
    transakcji co wersja; stary numer w trybie bieżącym → 409 STALE_PLAN;
    tryb historii czyta go dalej."""
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    p = _plan_a(seeded, ha)
    dni = seeded.get(f"/api/plans/{p['plan_id']}/versions", headers=hc).json()["versions"][-1]["content"]["days"]
    powod = "Mniej serii przysiadu — zgłoszone zmęczenie w raporcie"
    r = seeded.post(f"/api/plans/{p['plan_id']}/versions", headers=hc, json={"reason": powod, "days": dni})
    assert r.status_code == 201
    nowa = r.json()["version_no"]
    with db_session() as db:
        # Od 0.73.0 przy tej rewizji jest też ślad H_CARDIO pozycji cardio dnia C — filtr po celu.
        s = db.query(WiedzaSlad).filter_by(plan_id=p["plan_id"], plan_revision=nowa, target_type="plan_change").one()
        assert s.decision_origin == "professional" and s.reason_note == powod
        assert not slad.waliduj(slad.do_schematu(s))
    r = _wyjasnij(seeded, ha, plan_id=p["plan_id"], plan_revision=nowa, target_type="plan_change", target_id="plan")
    assert r.status_code == 200 and r.json()["status"] == "explained"
    assert powod in r.json()["paragraphs"][0] and "Uzasadnienie autora planu" not in r.json()["paragraphs"][1]
    assert "nie wynik algorytmu" in r.json()["paragraphs"][1]
    # druga wersja → poprzednia w trybie bieżącym jest nieaktualna
    seeded.post(f"/api/plans/{p['plan_id']}/versions", headers=hc, json={"reason": "Kolejna korekta", "days": dni})
    r = _wyjasnij(seeded, ha, plan_id=p["plan_id"], plan_revision=nowa, target_type="plan_change", target_id="plan")
    assert r.status_code == 409 and r.json()["code"] == "STALE_PLAN"
    assert r.json()["wynik"]["status"] == "stale_context"
    r = _wyjasnij(seeded, ha, plan_id=p["plan_id"], plan_revision=nowa, target_type="plan_change",
                  target_id="plan", tryb="history")
    assert r.status_code == 200 and r.json()["historical"] is True and powod in r.json()["paragraphs"][0]
    h = seeded.get(f"/api/wiedza/plany/training/{p['plan_id']}/historia-decyzji", headers=ha).json()["items"]
    # Od 0.73.0 historia niesie też ślady H_CARDIO (dzień C seedu) — patrzymy na decyzje trenera.
    h = [x for x in h if x["target_type"] == "plan_change"]
    assert [x["plan_revision"] for x in h] == [nowa + 1, nowa]
    assert h[1]["aktualna"] is False and h[1]["autor"] == "Uzasadnienie autora planu"
    # Trener z relacją widzi wyjaśnienie klienta.
    r = _wyjasnij(seeded, hc, plan_id=p["plan_id"], plan_revision=nowa + 1, target_type="plan_change", target_id="plan")
    assert r.status_code == 200 and r.json()["status"] == "explained"


def test_cudzy_plan_404_bez_trace_id_i_bez_wspolnego_cache(seeded) -> None:
    """K10/K11: klient B nie dostaje ani statusu, ani trace_id planu A;
    odpowiedzi prywatne mają no-store."""
    ha, hb, hc = login(seeded, CLIENT_A), login(seeded, CLIENT_B), login(seeded, COACH)
    p = _plan_a(seeded, ha)
    dni = seeded.get(f"/api/plans/{p['plan_id']}/versions", headers=hc).json()["versions"][-1]["content"]["days"]
    nowa = seeded.post(f"/api/plans/{p['plan_id']}/versions", headers=hc,
                       json={"reason": "Powód A", "days": dni}).json()["version_no"]
    ra = _wyjasnij(seeded, ha, plan_id=p["plan_id"], plan_revision=nowa, target_type="plan_change", target_id="plan")
    assert ra.status_code == 200 and "no-store" in ra.headers["cache-control"]
    rb = _wyjasnij(seeded, hb, plan_id=p["plan_id"], plan_revision=nowa, target_type="plan_change", target_id="plan")
    assert rb.status_code == 404
    assert "trace_id" not in rb.text and "Powód A" not in rb.text
    assert seeded.get(f"/api/wiedza/plany/training/{p['plan_id']}/historia-decyzji", headers=hb).status_code == 404
    assert seeded.get("/api/wiedza/plany/training/HOS-PLN-000000000000/historia-decyzji", headers=hb).status_code == 404


def test_konfigurator_zapisuje_slady_i_wyjasnia_dawke_kazdego_cwiczenia(seeded) -> None:
    """K36: to samo ćwiczenie w dwóch jednostkach ma odrębne cele; ślady
    engine walidują się schematem; wyjaśnienie mówi o regule, nie badaniu."""
    hb, hc = login(seeded, CLIENT_B), login(seeded, COACH)
    bid = get_user_id(seeded, hb)
    wej = next(e for e in PRZYKLADY if e["id"] == "E1")["input"]
    r = seeded.post("/api/coach/konfigurator/zapisz", headers=hc, json={"client_id": bid, "wejscie": wej})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    with db_session() as db:
        slady = db.query(WiedzaSlad).filter_by(plan_id=pid).all()
        assert len(slady) >= 1 + 2 * 4
        for s in slady:
            assert not slad.waliduj(slad.do_schematu(s)) and s.decision_origin == "engine"
        cele = {(s.target_type, s.target_id) for s in slady}
        assert ("training_frequency", "plan") in cele and ("exercise_prescription", "d1:e0") in cele
    r = _wyjasnij(seeded, hb, plan_id=pid, plan_revision=1, target_type="exercise_prescription", target_id="d0:e0")
    w = r.json()
    assert r.status_code == 200 and w["status"] == "explained", w
    assert "reguły konfiguratora" in w["paragraphs"][1] and "nie badania" in w["paragraphs"][1]
    assert "ex-leg_press" in {a["id"] for a in w["article_refs"]}
    r = _wyjasnij(seeded, hb, plan_id=pid, plan_revision=1, target_type="training_frequency", target_id="plan")
    assert r.json()["status"] == "explained" and "2 treningi w tygodniu" in r.json()["paragraphs"][0]
    # Ten sam exercise_id (calf) występuje w A i B — inne cele, oba wyjaśnione.
    d0 = seeded.get(f"/api/plans/{pid}/versions", headers=hb).json()["versions"][0]["content"]["days"]
    calf = [(di, ei) for di, d in enumerate(d0) for ei, e in enumerate(d["exercises"]) if e["konfigurator_id"] == "calf"]
    assert len(calf) >= 2
    for di, ei in calf[:2]:
        r = _wyjasnij(seeded, hb, plan_id=pid, plan_revision=1, target_type="exercise_prescription", target_id=f"d{di}:e{ei}")
        assert r.json()["status"] == "explained"
    # Feed klienta B: pierwsza ekspozycja na ćwiczenia z planu.
    s = seeded.get("/api/wiedza/start", headers=hb).json()
    assert s["plan"]["z_konfiguratora"] is True and "leg_press" in s["plan"]["exercise_ids"]


def test_bol_w_sesji_daje_restricted_ze_sciezka_do_trenera(seeded) -> None:
    """Reguła produktu: ból w sesji bieżącej wersji planu (ostatnie 7 dni)
    → restricted, akcja „Napisz do trenera”, karta bezpieczeństwa; bez
    automatycznego zamiennika."""
    from dzik_os.dates import local_today_iso

    hb, hc = login(seeded, CLIENT_B), login(seeded, COACH)
    bid = get_user_id(seeded, hb)
    wej = next(e for e in PRZYKLADY if e["id"] == "E1")["input"]
    pid = seeded.post("/api/coach/konfigurator/zapisz", headers=hc, json={"client_id": bid, "wejscie": wej}).json()["id"]
    vid = seeded.get(f"/api/plans/{pid}/versions", headers=hb).json()["versions"][0]["id"]
    seeded.post(f"/api/clients/{bid}/workouts", headers=hb, json={
        "plan_version_id": vid, "day_index": 0, "performed_on": local_today_iso(), "status": "DONE",
        "pain_flag": True, "pain_note": "kolano", "entries": []})
    r = _wyjasnij(seeded, hb, plan_id=pid, plan_revision=1, target_type="exercise_prescription", target_id="d0:e0")
    w = r.json()
    assert w["status"] == "restricted" and w["trace_id"] is None
    assert w["actions"][0] == {"label": "Napisz do trenera", "type": "open_safety_flow", "target_id": "/wiadomosci"}
    assert w["article_refs"][0]["id"] == "k-safety"


def test_dieta_trenera_tlumaczy_kalorie_a_posilek_ma_jawny_brak(seeded) -> None:
    """K15/K17: cel kaloryczny = decyzja trenera z wersji diety; posiłek
    bez adaptera → missing_trace + karta ogólna, bez wyliczania."""
    hb, hc = login(seeded, CLIENT_B), login(seeded, COACH)
    bid = get_user_id(seeded, hb)
    r = seeded.post("/api/nutrition", headers=hc, json={"client_id": bid, "title": "Dieta B", "version": {
        "reason": "Start redukcji według wywiadu", "kcal": 2100, "protein_g": 160, "fat_g": 70, "carbs_g": 200,
        "sections": [], "meals": [{"name": "Owsianka"}]}})
    assert r.status_code == 201
    nid = r.json()["id"]
    r = _wyjasnij(seeded, hb, plan_kind="nutrition", plan_id=nid, plan_revision=1, target_type="energy_target", target_id="plan")
    assert r.json()["status"] == "explained" and "Start redukcji" in r.json()["paragraphs"][0]
    r = _wyjasnij(seeded, hb, plan_kind="nutrition", plan_id=nid, plan_revision=1, target_type="macro_target", target_id="plan")
    assert r.json()["status"] == "explained"
    r = _wyjasnij(seeded, hb, plan_kind="nutrition", plan_id=nid, plan_revision=1, target_type="meal", target_id="m0")
    assert r.json()["status"] == "missing_trace" and [a["id"] for a in r.json()["article_refs"]] == ["k-meal"]
    assert seeded.get(f"/api/wiedza/plany/nutrition/{nid}/historia-decyzji", headers=login(seeded, CLIENT_A)).status_code == 404


def test_ranking_deterministyczny_i_bez_personalizacji(seeded) -> None:
    """K29/K30: te same dane → ten sam porządek, maks. 3 różne karty;
    wyłączona personalizacja → statyczne podstawy; otwarta karta spada."""
    ha = login(seeded, CLIENT_A)
    a = seeded.get("/api/wiedza/start", headers=ha).json()["dla_ciebie"]
    b = seeded.get("/api/wiedza/start", headers=ha).json()["dla_ciebie"]
    assert [x["id"] for x in a] == [x["id"] for x in b] and len({x["id"] for x in a}) == len(a) <= 3
    assert all(x["powod"] for x in a)
    pierwszy = a[0]["id"]
    assert seeded.post(f"/api/wiedza/odczyty/{pierwszy}", headers=ha, json={}).status_code == 200
    po = seeded.get("/api/wiedza/start", headers=ha).json()["dla_ciebie"]
    assert po[0]["id"] != pierwszy
    assert seeded.put("/api/wiedza/ustawienia", headers=ha, json={"personalizacja": False}).json() == {"personalizacja": False}
    s = seeded.get("/api/wiedza/start", headers=ha).json()
    assert s["personalizacja"] is False and [x["id"] for x in s["dla_ciebie"]] == ["k-safety", "k-rir", "k-sets"]
    # „Dlaczego?” nadal działa po odmowie personalizacji.
    p = s["plan"]
    assert _wyjasnij(seeded, ha, plan_id=p["plan_id"], plan_revision=p["version_no"],
                     target_type="plan_change", target_id="plan").status_code == 200


def test_opinia_i_odczyt(seeded) -> None:
    ha = login(seeded, CLIENT_A)
    assert seeded.post("/api/wiedza/opinie", headers=ha, json={"article_id": "k-rir", "revision": 1, "useful": True}).status_code == 200
    assert seeded.post("/api/wiedza/opinie", headers=ha, json={"article_id": "k-rir", "revision": 9, "useful": True}).status_code == 404
    r = seeded.post("/api/wiedza/odczyty/k-rir", headers=ha, json={"ukonczone": True})
    assert r.status_code == 200 and r.json()["explicitly_completed_at"]


def test_flaga_wylacza_nowa_wiedze_bez_utraty_danych(seeded, monkeypatch) -> None:
    """K40: DZIK_WIEDZA_V2=false → start mówi `wlaczone: false`, reszta 404,
    stara zakładka działa; po włączeniu zakładki są na miejscu."""
    ha = login(seeded, CLIENT_A)
    seeded.put("/api/wiedza/zakladki/k-rir", headers=ha)
    monkeypatch.setattr(settings, "wiedza_v2", False)
    assert seeded.get("/api/wiedza/start", headers=ha).json() == {"wlaczone": False}
    assert seeded.get("/api/wiedza/artykuly", headers=ha).status_code == 404
    assert seeded.post("/api/wiedza/wyjasnij", headers=ha, json={
        "plan_id": "x", "plan_revision": 1, "target_type": "plan_change", "target_id": "plan"}).status_code == 404
    assert seeded.get("/api/me/knowledge", headers=ha).status_code == 200
    monkeypatch.setattr(settings, "wiedza_v2", True)
    assert [z["id"] for z in seeded.get("/api/wiedza/zakladki", headers=ha).json()["items"]] == ["k-rir"]


def test_od_trenera_mapa_migracji(seeded) -> None:
    """Materiały trenera trafiają do właściwej części; nic nie jest usuwane."""
    ha = login(seeded, CLIENT_A)
    s = seeded.get("/api/wiedza/start", headers=ha).json()
    stare = seeded.get("/api/me/knowledge", headers=ha).json()["items"]
    assert len(s["od_trenera"]) == len(stare) >= 5
    assert all(m["czesc"] in dane.KATEGORIE for m in s["od_trenera"])


@pytest.mark.parametrize("q", ["zapas", "kalorje"])
def test_szukaj_zwraca_naglowek_i_fragment(seeded, q) -> None:
    ha = login(seeded, CLIENT_A)
    w = seeded.post("/api/wiedza/szukaj", headers=ha, json={"q": q}).json()["items"][0]
    assert w["fragment"] and w["category_label"]

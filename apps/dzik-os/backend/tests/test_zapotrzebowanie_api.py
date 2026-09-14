"""Bilans kaloryczny wg specyfikacji właściciela 1.0: definicja pięciu
ekranów, walidacja liczb, wyliczenie przy przesłaniu, ukrycie wyniku przed
klientem (zaburzenia odżywiania — odwracalne; osoba niepełnoletnia — nie),
flagi zdrowotne widoczne trenerowi wyłącznie za zgodą `DOMAIN_HEALTH`,
nadpisanie i odblokowanie przez trenera, historia i flaga instalacji.
"""

from __future__ import annotations

import json

from conftest import CLIENT_A, COACH, create_user_with_role, get_user_id, login

from dzik_os.config import settings
from dzik_os.dates import local_today
from dzik_os.db import SessionLocal
from dzik_os.models import CalorieEstimate
from dzik_os.wywiad import zapotrzebowanie as Z

W = "/api/clients/{}/wywiady"
TYP = "zapotrzebowanie"


def _def(c, h, cid):
    r = c.get(f"{W.format(cid)}/{TYP}/definicja", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _rev(c, h, cid):
    d = _def(c, h, cid)
    return d["draft"]["revision"] if d["draft"] else 1


def _patch(c, h, cid, answers, expect=200):
    r = c.patch(f"{W.format(cid)}/{TYP}/szkic", headers=h,
                json={"revision": _rev(c, h, cid), "answers": {k: {"value": v} for k, v in answers.items()}})
    assert r.status_code == expect, r.text
    return r.json()


def _przeslij(c, h, cid, expect=201):
    r = c.post(f"{W.format(cid)}/{TYP}/przeslij", headers=h, json={"revision": _rev(c, h, cid)})
    assert r.status_code == expect, r.text
    return r.json()


#: Kobieta 30 l., 170 cm, 70 kg, siedząca, 3 × 60 min siłowy, bez cardio, utrzymanie.
#: PPM 1452, trening 158 kcal/dzień, TEF 190, CPM 2089 (1943–2235), cel 2089.
KOMPLET = {
    "zk_plec": Z.PLEC_K, "zk_wiek": "30", "zk_wzrost": "170", "zk_masa": "70",
    "zk_neat": Z.NEAT_SIEDZACA, "zk_sila_tydz": "3", "zk_sila_minuty": Z.MINUTY_60,
    "zk_cardio_tydz": "0", "zk_cel": Z.CEL_UTRZYMANIE,
}
CPM = 2089


def _klucze(obj, acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(k)
            _klucze(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _klucze(v, acc)
    return acc


def _liczby(obj, acc=None):
    acc = [] if acc is None else acc
    if isinstance(obj, dict):
        for v in obj.values():
            _liczby(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _liczby(v, acc)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        acc.append(obj)
    return acc


def test_definicja_piec_ekranow_i_walidacja_liczb(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    d = _def(seeded, ha, cid)
    assert d["typ"] == TYP and d["version"] == 2
    assert [s["key"] for s in d["sections"]] == ["zk_dane", "zk_neat", "zk_trening", "zk_cel", "zk_zdrowie"]
    masa = next(q for q in d["questions"] if q["question_id"] == "zk_masa")
    assert masa["type"] == "NUMBER" and masa["range"] == [35, 250]
    tluszcz = next(q for q in d["questions"] if q["question_id"] == "zk_tluszcz")
    assert tluszcz["range"] == [3, 60] and tluszcz["required"] is False
    # Tempo, czas treningu i intensywność są warunkowe.
    for qid in ("zk_tempo", "zk_sila_minuty", "zk_cardio_minuty", "zk_cardio_intensywnosc"):
        assert not next(q for q in d["questions"] if q["question_id"] == qid)["active"], qid
    r = _patch(seeded, ha, cid, {"zk_masa": "abc", "zk_wzrost": "999", "zk_wiek": "72,5"})
    assert "liczbę" in r["errors"]["zk_masa"] and "zakresem" in r["errors"]["zk_wzrost"]
    assert "zk_wiek" not in r["errors"]
    # Wiek 16–90 wg specyfikacji (decyzja właściciela: wiek, nie data urodzenia).
    assert "zakresem" in _patch(seeded, ha, cid, {"zk_wiek": "14"})["errors"]["zk_wiek"]
    # Redukcja bez tempa = brak wymagany przy przesłaniu.
    _patch(seeded, ha, cid, {**KOMPLET, "zk_cel": Z.CEL_REDUKCJA})
    assert "zk_tempo" in _przeslij(seeded, ha, cid, expect=422)["missing"]


def test_pytania_warunkowe_odslaniaja_sie_po_odpowiedzi(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {"zk_sila_tydz": "3", "zk_cardio_tydz": "2", "zk_cel": Z.CEL_MASA,
                             "zk_plec": Z.PLEC_K})
    akt = {q["question_id"] for q in _def(seeded, ha, cid)["questions"] if q["active"]}
    assert {"zk_sila_minuty", "zk_cardio_minuty", "zk_cardio_intensywnosc", "zk_tempo",
            "zk_miesiaczka"} <= akt
    # Mężczyzna: pytanie o miesiączkę nie istnieje (nie „jest puste”).
    _patch(seeded, ha, cid, {"zk_plec": Z.PLEC_M, "zk_cardio_tydz": "0"})
    akt2 = {q["question_id"] for q in _def(seeded, ha, cid)["questions"] if q["active"]}
    assert "zk_miesiaczka" not in akt2 and "zk_cardio_minuty" not in akt2


def test_przeslanie_liczy_bilans_widoczny_dla_klienta_i_trenera(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    assert _patch(seeded, ha, cid, KOMPLET)["errors"] == {}
    assert _przeslij(seeded, ha, cid)["safety_flag"] is False
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()
    e = k["estimate"]
    assert k["status"] == "ok" and e["legacy"] is False
    assert e["formulas_version"] == Z.FORMULAS_VERSION
    # Rozbicie CPM na składniki (specyfikacja §6.2).
    assert (e["ppm_mifflin"], e["ppm_katch"], e["ppm_used"]) == (1452, None, 1452)
    assert e["ppm_source"] == "mifflin_st_jeor" and e["neat_multiplier"] == 1.2
    assert (e["training_kcal_day"], e["tef"]) == (158, 190)
    assert (e["cpm"], e["cpm_min"], e["cpm_max"]) == (CPM, 1943, 2235)
    assert e["target_kcal"] == CPM and e["kcal"] == CPM and e["kcal_effective"] == CPM
    assert e["bmi"] == 24.2 and e["macro"]["bialko_g"] == 112
    assert e["tempo"]["kg_tydzien"] == 0.0
    assert e["podstawienie"][0].startswith("PPM (Mifflin-St Jeor, kobieta)")
    assert any("CPM = " in w for w in e["podstawienie"])
    assert "history" not in k
    t = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    assert t["status"] == "ok" and t["estimate"]["override"] is None
    assert t["history"][0]["version_no"] == 1 and t["history"][0]["masa_kg"] == 70.0
    assert t["history"][0]["legacy"] is False
    # Druga wersja (nowa masa) = nowy bilans; historia rośnie.
    _patch(seeded, ha, cid, {**KOMPLET, "zk_masa": "68,5"})
    _przeslij(seeded, ha, cid)
    t2 = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    assert t2["estimate"]["version_no"] == 2 and t2["estimate"]["inputs"]["masa_kg"] == 68.5
    assert t2["estimate"]["target_kcal"] == 2066 and len(t2["history"]) == 2


def test_katch_mcardle_przy_podanym_procencie_tluszczu(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_tluszcz": "15"})
    _przeslij(seeded, ha, cid)
    e = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()["estimate"]
    assert e["ppm_mifflin"] == 1452 and e["ppm_katch"] == 1655
    assert e["ppm_source"] == "katch_mcardle" and e["ppm_used"] == 1655
    assert any("Katch-McArdle" in w for w in e["podstawienie"])


def test_inputs_nie_zawieraja_odpowiedzi_zdrowotnych(seeded):
    """Minimalizacja: odpowiedzi szczególnej kategorii zostają w wywiadzie
    (za zgodą domeny), a nie w drugiej tabeli, gdzie trzeba by je znowu ukrywać."""
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_ciaza": Z.ODP_ZDR_TAK, "zk_leki": Z.ODP_ZDR_TAK})
    _przeslij(seeded, ha, cid)
    with SessionLocal() as db:
        est = db.query(CalorieEstimate).filter_by(client_id=cid).one()
        dane = json.loads(est.inputs_json)
    assert not ({"ciaza", "leki", "choroba_metaboliczna", "zaburzenia_odzywiania",
                 "brak_miesiaczki"} & set(dane))
    assert set(json.loads(est.flags_json)) >= {Z.FLAGA_CIAZA, Z.FLAGA_LEKI}


def test_flagi_zdrowotne_tylko_przy_zgodzie_zdrowotnej(seeded):
    """Trener bez zgody `DOMAIN_HEALTH` widzi wynik i rozbicie, ale NIE flagi
    wynikające z odpowiedzi zdrowotnych — tylko informację, że takie są."""
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_choroba": Z.ODP_ZDR_TAK, "zk_wiek": "17"})
    _przeslij(seeded, ha, cid)
    t = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    kody = {f["code"] for f in t["estimate"]["flags"]}
    assert Z.FLAGA_CHOROBA in kody and Z.FLAGA_MALOLETNI in kody
    assert t["estimate"]["flags_hidden"] is False and t["coach_note"] is None
    # Klient cofa zgodę zdrowotną.
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    health = next(x for x in consents if x["revoked_at"] is None and x["category"] == "dane_zdrowotne")
    assert seeded.post(f"/api/me/consents/{health['id']}/revoke", headers=ha).status_code == 200
    t2 = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    kody2 = {f["code"] for f in t2["estimate"]["flags"]}
    assert Z.FLAGA_CHOROBA not in kody2, "flaga zdrowotna nie może wyciec bez zgody"
    assert Z.FLAGA_MALOLETNI in kody2, "wiek nie jest daną z ekranu zdrowotnego"
    assert t2["estimate"]["flags_hidden"] is True and "zgody" in t2["coach_note"]
    assert t2["estimate"]["target_kcal"] == 2175  # wynik i rozbicie zostają jawne


def test_maloletni_nie_widzi_liczb_i_trener_nie_moze_tego_cofnac(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_wiek": "17"})
    assert _przeslij(seeded, ha, cid)["safety_flag"] is False
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()
    assert k["status"] == "hidden" and k["hidden_reason"] == "maloletni"
    assert "opiekunem" in k["message"] and k["estimate"] is None
    assert not ({"kcal", "target_kcal", "cpm", "macro", "inputs"} & _klucze(k))
    # Trener widzi wszystko, ale „odsłoń” nie zdejmuje tego ukrycia.
    t = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    assert t["estimate"]["target_kcal"] == 2175
    assert Z.FLAGA_MALOLETNI in {f["code"] for f in t["estimate"]["flags"]}
    assert seeded.post(f"/api/clients/{cid}/zapotrzebowanie/odblokuj", headers=hc).status_code == 200
    assert seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()["status"] == "hidden"


def test_zaburzenia_klient_nie_dostaje_zadnej_liczby(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    # Decyzja właściciela nr 2: „Nie wiem” i „Wolę omówić” ukrywają tak samo jak „Tak”.
    _patch(seeded, ha, cid, {**KOMPLET, "zk_zaburzenia": Z.ODP_ZAB_TAK})
    assert _przeslij(seeded, ha, cid)["safety_flag"] is True
    _patch(seeded, ha, cid, {**KOMPLET, "zk_zaburzenia": Z.ODP_ZAB_OMOWIC})
    assert _przeslij(seeded, ha, cid)["safety_flag"] is True
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()
    assert k["status"] == "hidden" and k["hidden_reason"] == "zaburzenia" and "omówi" in k["message"]
    assert not ({"kcal", "kcal_effective", "ppm", "cpm", "pal", "masa_kg", "inputs",
                 "podstawienie", "macro", "target_kcal"} & _klucze(k))
    assert _liczby(k) == [2]  # wyłącznie numer wersji
    t = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    assert t["estimate"]["hidden_for_client"] is True and t["estimate"]["target_kcal"] == CPM
    assert Z.FLAGA_ZABURZENIA in {f["code"] for f in t["estimate"]["flags"]}
    # Trener po rozmowie odsłania — klient widzi liczby.
    r = seeded.post(f"/api/clients/{cid}/zapotrzebowanie/odblokuj", headers=hc)
    assert r.status_code == 200 and r.json()["estimate"]["hidden_for_client"] is False
    k2 = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()
    assert k2["status"] == "ok" and k2["estimate"]["target_kcal"] == CPM and k2["estimate"]["unhidden_at"]
    # Klient nie może sam odblokować ani nadpisać.
    assert seeded.post(f"/api/clients/{cid}/zapotrzebowanie/odblokuj", headers=ha).status_code == 403
    assert seeded.put(f"/api/clients/{cid}/zapotrzebowanie/nadpisanie", headers=ha,
                      json={"kcal": 1800, "reason": "x"}).status_code == 403


def test_klient_widzi_swoje_flagi_ktore_go_dotycza(seeded):
    """Klient dostaje wyłącznie te flagi, które mają dla niego treść —
    ostrzeżenia kierowane do trenera (np. konsultacja lekarska) nie."""
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_cel": Z.CEL_REDUKCJA, "zk_tempo": Z.TEMPO_SZYBKIE,
                             "zk_ciaza": Z.ODP_ZDR_TAK, "zk_choroba": Z.ODP_ZDR_TAK})
    _przeslij(seeded, ha, cid)
    e = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()["estimate"]
    kody = {f["code"] for f in e["flags"]}
    assert Z.FLAGA_CIAZA in kody and Z.FLAGA_CHOROBA not in kody
    assert e["korekta_pct"] == 0  # deficyt wyłączony


def test_nadpisanie_trenera_z_powodem_i_cofniecie(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_cel": Z.CEL_REDUKCJA, "zk_tempo": Z.TEMPO_UMIARKOWANE})
    _przeslij(seeded, ha, cid)
    url = f"/api/clients/{cid}/zapotrzebowanie/nadpisanie"
    assert seeded.put(url, headers=hc, json={"kcal": 100, "reason": "za mało"}).status_code == 422
    assert seeded.put(url, headers=hc, json={"kcal": 1800, "reason": ""}).status_code == 422
    r = seeded.put(url, headers=hc, json={"kcal": 1800, "reason": "Start łagodniej — pierwszy tydzień."})
    assert r.status_code == 200, r.text
    e = r.json()["estimate"]
    assert e["target_kcal"] == 1671 and e["kcal_effective"] == 1800
    assert e["override"]["reason"].startswith("Start")
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()["estimate"]
    assert k["kcal_effective"] == 1800 and k["override"]["reason"].startswith("Start")
    r = seeded.put(url, headers=hc, json={"kcal": None, "reason": "wracamy do wzoru"})
    assert r.json()["estimate"]["override"] is None and r.json()["estimate"]["kcal_effective"] == 1671
    # Obcy trener: 404 (bez ujawniania istnienia).
    create_user_with_role("obcy.trener@example.com", "ObcyTrener#2026!", "Obcy", "COACH")
    ho = login(seeded, {"email": "obcy.trener@example.com", "password": "ObcyTrener#2026!"})
    assert seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ho).status_code == 404
    assert seeded.put(url, headers=ho, json={"kcal": 1800, "reason": "x"}).status_code == 404


def test_bez_zgody_zdrowotnej_pytania_znikaja_a_wynik_jest_jawny(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    health = next(x for x in consents if x["revoked_at"] is None and x["category"] == "dane_zdrowotne")
    assert seeded.post(f"/api/me/consents/{health['id']}/revoke", headers=ha).status_code == 200
    d = _def(seeded, ha, cid)
    akt = {q["question_id"] for q in d["questions"] if q["active"]}
    assert not ({"zk_zaburzenia", "zk_ciaza", "zk_choroba", "zk_leki", "zk_miesiaczka",
                 "zk_uwagi"} & akt)
    assert "dane_zdrowotne" in d["hidden_domains"] or d["hidden_domains"]
    _patch(seeded, ha, cid, KOMPLET)
    assert _przeslij(seeded, ha, cid)["safety_flag"] is False
    assert seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()["status"] == "ok"


def test_stary_wynik_zostaje_w_historii_i_ma_wlasna_wersje_wzorow(seeded):
    """Decyzja właściciela nr 3: wierszy 0.62.0 nie przeliczamy (brak danych
    wejściowych). Zostają jako historia, z zachętą do ponownego wypełnienia."""
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    with SessionLocal() as db:
        db.add(CalorieEstimate(
            id="HOS-CAL-STARY1", client_id=cid, submission_id="HOS-IVS-STARY1", version_no=1,
            inputs_json=json.dumps({"plec": "Kobieta", "masa_kg": 70.0, "cel": "Redukcja masy ciała"}),
            ppm=1452, pal=1.35, cpm=1960, korekta_pct=-15, kcal=1670,
            podstawienie_json=json.dumps(["PPM … = 1452 kcal"]), ostrzezenia_json="[]",
            formulas_version=Z.FORMULAS_VERSION_PAL, created_at="2026-09-01T10:00:00+00:00"))
        db.commit()
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()
    assert k["status"] == "ok" and k["estimate"]["legacy"] is True
    assert k["estimate"]["formulas_version"] == "0.62.0-pal"
    assert k["estimate"]["kcal"] == 1670 and "target_kcal" not in k["estimate"]
    assert "wypełnij wywiad jeszcze raz" in k["message"]
    # Nowe przesłanie liczy nowym silnikiem; stary wiersz zostaje w historii.
    _patch(seeded, ha, cid, KOMPLET)
    _przeslij(seeded, ha, cid)
    t = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    assert t["estimate"]["legacy"] is False and t["estimate"]["target_kcal"] == CPM
    assert [h["formulas_version"] for h in t["history"]] == [Z.FORMULAS_VERSION, "0.62.0-pal"]
    with SessionLocal() as db:
        stary = db.get(CalorieEstimate, "HOS-CAL-STARY1")
        assert stary.kcal == 1670 and stary.target_kcal is None  # nieprzeliczony


def test_placeholder_masy_z_ostatniego_pomiaru(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    r = seeded.post(f"/api/clients/{cid}/measurements", headers=ha,
                    json={"kind": "weight", "value": 71.3, "unit": "kg", "measured_at": local_today().isoformat()})
    assert r.status_code in (200, 201), r.text
    d = _def(seeded, ha, cid)
    assert next(q for q in d["questions"] if q["question_id"] == "zk_masa")["placeholder"] == "ostatni pomiar: 71,3 kg"


def test_flaga_instalacji_wylacza_typ_i_trase(seeded, monkeypatch):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    assert seeded.get("/api/health").json()["features"]["calorie_interview"] is True
    monkeypatch.setattr(settings, "calorie_interview_enabled", False)
    assert seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).status_code == 404
    assert seeded.get(f"{W.format(cid)}/{TYP}/definicja", headers=ha).status_code == 404
    typy = [w["typ"] for w in seeded.get(W.format(cid), headers=ha).json()["wywiady"]]
    assert typy == ["wstepny", "gleboki"]
    assert seeded.get("/api/health").json()["features"]["calorie_interview"] is False


def test_number_odrzuca_notacje_i_normalizuje_zapis(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    r = _patch(seeded, ha, cid, {"zk_masa": "1e2", "zk_wzrost": "1_80", "zk_wiek": "٣٠"})
    assert set(r["errors"]) == {"zk_masa", "zk_wzrost", "zk_wiek"}
    r = _patch(seeded, ha, cid, {"zk_masa": "72.5", "zk_wzrost": "1 80", "zk_kroki": "9500"})
    assert r["errors"] == {}
    odp = {a["question_id"]: a["value"] for a in _def(seeded, ha, cid)["answers"]}
    assert odp["zk_masa"] == "72,5" and odp["zk_wzrost"] == "180" and odp["zk_kroki"] == "9500"


def test_szkic_sprzed_zmiany_pytan_nie_wnosi_wartosci_spoza_listy(seeded):
    """Szkic wywiadu sprzed wyrównania do specyfikacji 1.0 ma pytania,
    których już nie ma (`zk_praca`), i wartości spoza dzisiejszej listy
    („Redukcja masy ciała”). Odczyt je pomija — przesłanie nie może ich
    wnieść do niezmiennej wersji."""
    from dzik_os.models import InterviewDraft, new_id, now_iso

    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {"zk_masa": "70"})
    with SessionLocal() as db:
        d = db.query(InterviewDraft).filter_by(client_id=cid, typ=TYP).one()
        stare = {q: {"value": v, "skipped": False, "entered_by": cid, "at": now_iso()}
                 for q, v in (("zk_praca", "Siedząca (biuro, auto, nauka)"),
                              ("zk_treningi", "3–4 treningi w tygodniu"),
                              ("zk_cel", "Redukcja masy ciała"),
                              ("zk_kroki", "5 000–8 000"),
                              ("zk_masa", "70"))}
        d.answers_json = json.dumps(stare, ensure_ascii=False)
        db.commit()
    odp = {a["question_id"]: a["value"] for a in _def(seeded, ha, cid)["answers"]}
    assert set(odp) == {"zk_masa"} and odp["zk_masa"] == "70"
    assert new_id  # import użyty


def test_eksport_danych_zawiera_bilans_takze_ukryty(seeded):
    """Prawo dostępu (RODO) ma pierwszeństwo przed ukryciem w aplikacji: eksport
    zawiera pełne wiersze, także gdy wynik jest ukryty przed klientem w UI."""
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_zaburzenia": Z.ODP_ZAB_NIE_WIEM})
    _przeslij(seeded, ha, cid)
    r = seeded.get("/api/me/export", headers=ha)
    assert r.status_code == 200, r.text
    rows = r.json()["calorie_estimates"]
    assert len(rows) == 1 and rows[0]["kcal"] == CPM and rows[0]["hidden_for_client"] is True
    # Nowe kolumny bilansu też są w eksporcie (zrzut jest generyczny po kolumnach).
    assert rows[0]["formulas_version"] == Z.FORMULAS_VERSION
    assert rows[0]["target_kcal"] == CPM and rows[0]["ppm_mifflin"] == 1452
    assert json.loads(rows[0]["macro_json"])["bialko_g"] == 112
    # Kształt eksportu bez zmian — przybyły kolumny tabeli, nie sekcje.
    assert r.json()["export_version"] == "2.1"


def test_flaga_wylaczona_ukrywa_istniejace_przeslania_trenerowi(seeded, monkeypatch):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, KOMPLET)
    sid = _przeslij(seeded, ha, cid)["submission_id"]
    assert seeded.get(f"/api/wywiady/zgloszenia/{sid}", headers=hc).status_code == 200
    monkeypatch.setattr(settings, "calorie_interview_enabled", False)
    assert seeded.get(f"/api/wywiady/zgloszenia/{sid}", headers=hc).status_code == 404
    lista = seeded.get("/api/coach/wywiady/do-przegladu", headers=hc).json()
    typy = {p["typ"] for k in lista["clients"] for p in k["wywiady"]}
    assert TYP not in typy


def test_trener_bez_przeslania_404_odblokowanie_noop_i_wygasanie_nadpisania(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    url = f"/api/clients/{cid}/zapotrzebowanie"
    # Przed przesłaniem: nie ma czego nadpisywać ani odsłaniać.
    assert seeded.put(f"{url}/nadpisanie", headers=hc, json={"kcal": 1800, "reason": "x"}).status_code == 404
    assert seeded.post(f"{url}/odblokuj", headers=hc).status_code == 404
    _patch(seeded, ha, cid, KOMPLET)
    _przeslij(seeded, ha, cid)
    # Odblokowanie wyniku, który nie jest ukryty = no-op bez śladu.
    r = seeded.post(f"{url}/odblokuj", headers=hc)
    assert r.status_code == 200 and r.json()["estimate"]["unhidden_at"] is None
    # Cofnięcie nadpisania, którego nie było = no-op.
    assert seeded.put(f"{url}/nadpisanie", headers=hc, json={"kcal": None, "reason": "nic"}).json()["estimate"]["override"] is None
    # Nadpisanie dotyczy wersji: nowa wersja wywiadu = wynik ze wzoru, poprzednie ustalenie w historii.
    seeded.put(f"{url}/nadpisanie", headers=hc, json={"kcal": 1800, "reason": "łagodniej"})
    _patch(seeded, ha, cid, {**KOMPLET, "zk_masa": "69"})
    _przeslij(seeded, ha, cid)
    t = seeded.get(url, headers=hc).json()
    assert t["estimate"]["version_no"] == 2 and t["estimate"]["override"] is None
    assert t["estimate"]["target_kcal"] == 2074
    assert [h["override_kcal"] for h in t["history"]] == [None, 1800]
    # Eksport ma nadpisanie z v1; usunięcie konta kasuje bilanse.
    ex = seeded.get("/api/me/export", headers=ha).json()["calorie_estimates"]
    assert sorted((e["version_no"], e["override_kcal"]) for e in ex) == [(1, 1800), (2, None)]
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE"})
    assert r.status_code in (200, 202), r.text
    with SessionLocal() as db:
        assert db.query(CalorieEstimate).filter_by(client_id=cid).count() == 0


def test_komunikat_ukrycia_bez_trenera(seeded):
    """Klient bez trenera widzi komunikat, który mówi, co dalej."""
    create_user_with_role("sam.klient@example.com", "SamKlient#2026!", "Sam", "CLIENT")
    hs = login(seeded, {"email": "sam.klient@example.com", "password": "SamKlient#2026!"})
    cid = get_user_id(seeded, hs)
    _patch(seeded, hs, cid, KOMPLET)
    akt = {q["question_id"] for q in _def(seeded, hs, cid)["questions"] if q["active"]}
    if "zk_zaburzenia" in akt:
        _patch(seeded, hs, cid, {"zk_zaburzenia": Z.ODP_ZAB_NIE_WIEM})
    sub = _przeslij(seeded, hs, cid)
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hs).json()
    if sub["safety_flag"]:
        assert k["status"] == "hidden" and "nawiążesz współpracę" in k["message"]
    else:
        assert k["status"] == "ok"  # bez zgody zdrowotnej pytanie nie pada — wynik jawny

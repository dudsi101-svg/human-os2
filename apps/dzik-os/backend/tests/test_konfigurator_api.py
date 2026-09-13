"""API konfiguratora (K1): trener liczy szkic i zapisuje go jako plan v1;
klient widzi plan; obcy nie; dane zdrowotne nie trafiają do treści planu
ani audytu."""
import copy
import json
from pathlib import Path

from conftest import CLIENT_A, CLIENT_B, COACH, get_user_id, login

from dzik_os import hos_bridge

E1 = json.loads((Path(__file__).parent / "dane" / "konfigurator_plany_28_dni.json").read_text(encoding="utf-8"))["examples"][0]["input"]


def test_podglad_liczy_szkic_bez_zapisu(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/konfigurator/podglad", headers=hc, json=E1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ready" and len(body["plan"]["days"]) == 28
    # Statusy blokujące to poprawna odpowiedź 200 z planem null.
    w = copy.deepcopy(E1); w["health"]["current_red_flag"] = True
    r = seeded.post("/api/coach/konfigurator/podglad", headers=hc, json=w)
    assert r.status_code == 200 and r.json()["status"] == "urgent_stop" and r.json()["plan"] is None


def test_katalog_dla_trenera(seeded):
    hc = login(seeded, COACH)
    body = seeded.get("/api/coach/konfigurator/katalog", headers=hc).json()
    assert len(body["exercises"]) == 31 and "dumbbells" in body["equipment_ids"]
    assert body["status"] == "proposed_requires_expert_review"


def test_zapis_tworzy_plan_v1_widoczny_dla_klienta(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    w = copy.deepcopy(E1); w["health"]["professional_instructions"] = "SEKRET-ZDROWOTNY-123"
    r = seeded.post("/api/coach/konfigurator/zapisz", headers=hc,
                    json={"client_id": client_id, "wejscie": w, "title": "Test 28 dni"})
    assert r.status_code == 201, r.text
    plan_id = r.json()["id"]
    assert r.json()["status"] == "ready" and r.json()["version_no"] == 1

    plany = seeded.get(f"/api/clients/{client_id}/plans", headers=ha).json()["plans"]
    plan = next(p for p in plany if p["id"] == plan_id)
    tresc = plan["current_version"]["content"]
    assert plan["title"] == "Test 28 dni" and plan["current_version_no"] == 1
    assert [d["name"][:14] for d in tresc["days"]] == ["1. Jednostka A", "2. Jednostka B"]
    cw = tresc["days"][0]["exercises"][0]
    assert cw["name"] == "Wypychanie na suwnicy" and cw["sets"] == "2" and cw["reps"] == "8–12"
    assert cw["weight"] == "dobór na miejscu" and "RIR tyg. 1–4: 4/3/3/3" in cw["comment"]
    assert len(tresc["konfigurator"]["kalendarz"]) == 28
    # Minimalizacja: blok zdrowotny nie jest zapisany ani w planie, ani w audycie.
    assert "health" not in tresc["konfigurator"]["wejscie"]
    assert "SEKRET-ZDROWOTNY-123" not in json.dumps(tresc)
    zdarzenia = json.dumps(hos_bridge.event_store().all())
    assert "SEKRET-ZDROWOTNY-123" not in zdarzenia and '"source": "konfigurator"' in zdarzenia

    # Nowa wersja planu działa jak zwykle (historia zachowana).
    r = seeded.post(f"/api/plans/{plan_id}/versions", headers=hc,
                    json={"reason": "Korekta trenera po szkicu", "days": tresc["days"]})
    assert r.status_code == 201 and r.json()["version_no"] == 2


def test_zapis_odmawia_dla_statusu_blokujacego(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    w = copy.deepcopy(E1); w["health"]["pregnancy_postpartum"] = True
    r = seeded.post("/api/coach/konfigurator/zapisz", headers=hc,
                    json={"client_id": get_user_id(seeded, ha), "wejscie": w})
    assert r.status_code == 409 and r.json()["wynik"]["status"] == "needs_review"


def test_klient_i_obcy_trener_bez_dostepu(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    assert seeded.post("/api/coach/konfigurator/podglad", headers=ha, json=E1).status_code in (401, 403)
    assert seeded.get("/api/coach/konfigurator/katalog", headers=hb).status_code in (401, 403)
    # Trener nie zapisze planu dla obcego id.
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/konfigurator/zapisz", headers=hc,
                    json={"client_id": "HOS-USR-NIEISTNIEJE", "wejscie": E1})
    assert r.status_code in (403, 404)

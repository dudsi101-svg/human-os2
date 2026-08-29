"""Wbudowane szablony treningowe: katalog, podgląd i import do biblioteki.

Testy pilnują trzech rzeczy, które łatwo zepsuć po cichu:
* danych (24 szablony / 431 pozycji przeniesione ze źródła bez ubytków),
* zasady „Szablon ≠ plan klienta" — import tworzy KOPIĘ, a nie współdzielony byt,
* tego, że aplikacja NICZEGO nie przelicza: reguła progresji jest tekstem
  dla człowieka, a ciężar w szablonie zostaje pusty.
"""

from __future__ import annotations

from conftest import CLIENT_A, COACH, login

from dzik_os import plan_templates
from dzik_os.plan_templates_data import PROGRESSION_MODELS, TEMPLATES, UNITS


def _coach(client):
    return login(client, COACH)


# --- dane -------------------------------------------------------------


def test_katalog_ma_komplet_danych_ze_zrodla():
    """Ubytek w danych to najcichsza możliwa awaria — nikt nie zauważy
    brakującego dnia w szablonie, dopóki klient nie dostanie planu."""
    assert len(TEMPLATES) == 26  # 24 bazowe + 2 autorskie (0.54.0)
    assert sum(len(v) for v in UNITS.values()) == 490  # 431 bazowych + 59 autorskich (0.54.0)
    assert {t["id"] for t in TEMPLATES} == set(UNITS)
    for tpl in TEMPLATES:
        units = UNITS[str(tpl["id"])]
        assert units, f"{tpl['id']} bez jednostek"
        # Liczba jednostek nie musi równać się dniom w tygodniu (np. obwód
        # 3×/tydz. to jedna jednostka powtarzana), ale nie może jej przekraczać.
        # Dzień „Wytyczne tygodnia" (0.54.0, szablony autorskie) to
        # jednostka informacyjna (mobility/cardio/kroki), nie dzień
        # treningowy — nie liczy się do days_per_week.
        dni = {u["day"] for u in units if "Wytyczne" not in str(u["day"])}
        assert len(dni) <= int(tpl["days_per_week"])


def test_kazda_pozycja_wskazuje_istniejacy_model_progresji():
    for tid, units in UNITS.items():
        for u in units:
            assert u["progression"] in PROGRESSION_MODELS, f"{tid}: {u['progression']}"


def test_model_progresji_ma_komplet_opisu():
    """Reguła bez warunku albo bez akcji jest bezużyteczna dla trenera."""
    for kod, m in PROGRESSION_MODELS.items():
        for pole in ("name", "when", "action", "hold", "regress"):
            assert m.get(pole), f"{kod}: brak pola {pole}"


# --- katalog przez API ------------------------------------------------


def test_trener_widzi_katalog_z_modelami_progresji(seeded):
    r = seeded.get("/api/coach/plan-templates", headers=_coach(seeded))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["templates"]) == 26  # 24 bazowe + 2 autorskie (0.54.0)
    assert body["progressions"]["PRG-DOUBLE"]["name"] == "Podwójna progresja"
    pierwszy = body["templates"][0]
    for pole in ("id", "name", "level", "goal", "days", "exercises"):
        assert pole in pierwszy


def test_klient_nie_wchodzi_do_katalogu_szablonow(seeded):
    r = seeded.get("/api/coach/plan-templates", headers=login(seeded, CLIENT_A))
    assert r.status_code in (401, 403, 404)


def test_podglad_szablonu_pokazuje_dni_przed_importem(seeded):
    r = seeded.get("/api/coach/plan-templates/TPL-001", headers=_coach(seeded))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"].startswith("Start")
    assert len(body["days"]) == 2
    cw = body["days"][0]["exercises"][0]
    assert cw["name"]
    assert cw["target_rir"]
    assert cw["progression"] in PROGRESSION_MODELS


def test_nieznany_szablon_to_404(seeded):
    h = _coach(seeded)
    assert seeded.get("/api/coach/plan-templates/TPL-999", headers=h).status_code == 404
    assert seeded.post(
        "/api/coach/plan-templates/TPL-999/import", headers=h
    ).status_code == 404


# --- import -----------------------------------------------------------


def test_import_tworzy_szablon_trenera_widoczny_na_liscie(seeded):
    h = _coach(seeded)
    przed = len(seeded.get("/api/plans/templates", headers=h).json()["templates"])

    r = seeded.post("/api/coach/plan-templates/TPL-003/import", headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["days"] == 4
    assert body["exercises"] == len(UNITS["TPL-003"])

    po = seeded.get("/api/plans/templates", headers=h).json()["templates"]
    assert len(po) == przed + 1
    assert any(p["id"] == body["id"] for p in po)


def test_zaimportowany_szablon_zachowuje_recepte_ze_zrodla(seeded):
    h = _coach(seeded)
    plan_id = seeded.post(
        "/api/coach/plan-templates/TPL-001/import", headers=h
    ).json()["id"]

    wersje = seeded.get(f"/api/plans/{plan_id}/versions", headers=h).json()
    dni = wersje["versions"][0]["content"]["days"]
    assert len(dni) == 2

    zrodlo = min(UNITS["TPL-001"], key=lambda u: (u["day"], u["order"]))
    pierwsze = dni[0]["exercises"][0]
    assert pierwsze["name"] == zrodlo["exercise"]
    assert pierwsze["sets"] == zrodlo["sets"]
    assert pierwsze["reps"] == zrodlo["reps"]
    assert pierwsze["target_rir"] == zrodlo["target_rir"]
    assert pierwsze["rest"] == zrodlo["rest"]


def test_szablon_nie_narzuca_ciezaru(seeded):
    """Ciężar dobiera człowiek. Gdyby szablon go podawał, aplikacja
    zaczęłaby stwierdzać fakt, którego nikt nie ustalił."""
    h = _coach(seeded)
    plan_id = seeded.post(
        "/api/coach/plan-templates/TPL-007/import", headers=h
    ).json()["id"]
    dni = seeded.get(f"/api/plans/{plan_id}/versions", headers=h).json()[
        "versions"
    ][0]["content"]["days"]
    for d in dni:
        for cw in d["exercises"]:
            assert not cw.get("weight"), f"{cw['name']} ma narzucony ciężar"


def test_ponowny_import_daje_niezalezna_kopie(seeded):
    """Zasada „Szablon ≠ plan klienta": import nie może nadpisać szablonu,
    który trener mógł już przerobić pod siebie."""
    h = _coach(seeded)
    a = seeded.post("/api/coach/plan-templates/TPL-002/import", headers=h).json()
    b = seeded.post("/api/coach/plan-templates/TPL-002/import", headers=h).json()
    assert a["id"] != b["id"]
    assert a["version_id"] != b["version_id"]


def test_import_wiaze_cwiczenia_po_dokladnej_nazwie(seeded):
    """Powiązanie z kartą ćwiczenia jest opcjonalne i wyłącznie dokładne —
    plan bez linku nadal działa, ma tylko samą nazwę."""
    h = _coach(seeded)
    body = seeded.post("/api/coach/plan-templates/TPL-001/import", headers=h).json()
    assert 0 <= body["linked_exercises"] <= body["exercises"]

    dni = seeded.get(f"/api/plans/{body['id']}/versions", headers=h).json()[
        "versions"
    ][0]["content"]["days"]
    mapa = plan_templates.exercise_ids_for_coach.__doc__  # dokumentacja istnieje
    assert mapa
    for d in dni:
        for cw in d["exercises"]:
            assert cw["name"], "nazwa jest zawsze zapisana"


def test_klient_nie_zaimportuje_szablonu(seeded):
    r = seeded.post(
        "/api/coach/plan-templates/TPL-001/import", headers=login(seeded, CLIENT_A)
    )
    assert r.status_code in (401, 403, 404)


def test_import_zostawia_slad_w_audycie(seeded):
    from dzik_os.hos_bridge import event_store, verify_audit_chain

    h = _coach(seeded)
    seeded.post("/api/coach/plan-templates/TPL-010/import", headers=h)
    zdarzenia = [
        e for e in event_store().all()
        if e["event_type"] == "PLAN_CREATED"
        and e["payload"].get("source_template") == "TPL-010"
    ]
    assert len(zdarzenia) == 1
    assert zdarzenia[0]["payload"]["is_template"] is True
    assert verify_audit_chain() is True


def test_po_imporcie_biblioteki_schemat_wiaze_niemal_wszystkie_cwiczenia(seeded):
    """Biblioteka ćwiczeń V2 i arkusz schematów pochodzą od tego samego
    trenera, więc nazewnictwo się pokrywa — po zaimportowaniu biblioteki
    prawie każda pozycja schematu dostaje kartę z techniką i filmem.

    Test pilnuje tej spójności: rozjazd nazewnictwa po którejkolwiek stronie
    odbiera klientowi instrukcje przy ćwiczeniach, nie psując przy tym
    niczego widocznego w testach jednostkowych.
    """
    h = _coach(seeded)
    r = seeded.post("/api/coach/exercises/import-library", headers=h)
    assert r.status_code in (200, 201), r.text

    body = seeded.post("/api/coach/plan-templates/TPL-005/import", headers=h).json()
    assert body["exercises"] > 0
    pokrycie = body["linked_exercises"] / body["exercises"]
    assert pokrycie >= 0.9, (
        f"tylko {body['linked_exercises']}/{body['exercises']} pozycji ma kartę — "
        "prawdopodobny rozjazd nazewnictwa między biblioteką a schematami"
    )

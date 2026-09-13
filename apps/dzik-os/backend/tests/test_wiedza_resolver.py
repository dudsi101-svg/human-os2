"""Wiedza — resolver wyjaśnień na 15 scenariuszach referencyjnych pakietu
(08_SCENARIUSZE) + reguły semantyczne K03–K05, K12–K17, K36, K38.

Czysta część resolvera nie dotyka bazy: kontekst, ślad i funkcje kart są
podane wprost. Kształt każdej odpowiedzi jest sprawdzany schematem
Draft 2020-12 `explanation_result` — a osobno to, że tekst nie wykracza
poza fakty śladu (żaden komunikat nie „wie” więcej niż ślad).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from dzik_os.wiedza import dane, reguly
from dzik_os.wiedza.resolver import Kontekst, rozstrzygnij

SCENARIUSZE = json.loads(
    (Path(__file__).parent / "dane" / "wiedza_scenariusze.json").read_text(encoding="utf-8")
)["fixtures"]

KARTY = {
    aid: {"id": aid, "revision": 1, "title": f"Karta {aid}"}
    for aid in ("k-progress", "k-frequency", "k-energy", "k-meal", "k-safety", "k-sets")
}


def _artykuly(ids: list[str]) -> list[dict]:
    return [KARTY[i] for i in ids if i in KARTY]


def _ogolne(target_type: str) -> list[dict]:
    return [KARTY["k-safety"]] if target_type == "safety" else [KARTY["k-progress"]]


def _kontekst(f: dict, **zmiany) -> Kontekst:
    return Kontekst(**{**f["request_context"], **zmiany})


def _walidator() -> Draft202012Validator:
    return Draft202012Validator(dane.schematy()["explanation_result"])


@pytest.mark.parametrize("fixture", SCENARIUSZE, ids=[f["id"] for f in SCENARIUSZE])
def test_scenariusze_referencyjne(fixture: dict) -> None:
    trace = fixture["trace"]
    target_type = (trace or {}).get("target_type", "load")
    kod, wynik = rozstrzygnij(_kontekst(fixture), trace, target_type, _artykuly, _ogolne)
    assert kod == fixture["expected_http"], (fixture["id"], kod, wynik)
    if fixture["expected_status"] is None:
        # Cudzy plan: 404 bez ciała — żadnego trace_id ani danych celu.
        assert wynik is None
        return
    assert wynik is not None
    assert wynik["status"] == fixture["expected_status"], (fixture["id"], wynik)
    assert not list(_walidator().iter_errors(wynik)), list(_walidator().iter_errors(wynik))
    for klucz in fixture["must_include_fact_keys"]:
        assert klucz in wynik["used_fact_keys"], (fixture["id"], klucz, wynik["used_fact_keys"])
    # Tekst tylko z faktów śladu: każda liczba w akapitach musi pochodzić ze
    # śladu albo z jego rewizji — resolver nie dopisuje faktów (must_not_claim).
    if trace and wynik["status"] == "explained":
        dozwolone = {str(trace["plan_revision"])}
        for f in trace["facts"]:
            v = f["value"]
            for x in (v if isinstance(v, list) else [v]):
                dozwolone.add(str(x))
        if isinstance(trace.get("outcome_value"), (int, float)):
            dozwolone.add(str(trace["outcome_value"]))
        import re

        for akapit in wynik["paragraphs"]:
            for liczba in re.findall(r"\d+(?:\.\d+)?", akapit.replace("2026-09-14", "")):
                assert liczba in dozwolone or liczba == "4", (fixture["id"], liczba, akapit)


def test_f01_tekst_z_ekranu_w4() -> None:
    """Przykład z pliku 02 dla scenariusza F01 (wyprowadzony ze śladu)."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F01")
    _, w = rozstrzygnij(_kontekst(f), f["trace"], "load", _artykuly, _ogolne)
    assert w["paragraphs"][0].endswith("Ciężar pozostaje bez zmian.")
    assert "12, 12 i 10 powtórzeń" in w["paragraphs"][1]
    assert "12 powtórzeń w każdej serii" in w["paragraphs"][2]
    assert [a["label"] for a in w["actions"][:2]] == ["Zobacz ostatni trening", "Jak działa progresja"]
    assert w["article_refs"] == [{"id": "k-progress", "revision": 1}]


def test_historia_nie_podstawia_biezacej_rewizji() -> None:
    """K08: historyczny odczyt ma flagę i prefiks „Historia”, a rewizja
    w odpowiedzi jest rewizją śladu, nie bieżącą."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F04")
    _, w = rozstrzygnij(_kontekst(f), f["trace"], "load", _artykuly, _ogolne)
    assert w["historical"] is True
    assert w["plan_revision"] == 2
    assert w["paragraphs"][0].startswith("Historia: ")


def test_zmiana_rewizji_w_trakcie_daje_stale() -> None:
    """K09: gdy bieżąca rewizja ucieknie przed odpowiedzią, resolver nie
    wraca z wyjaśnieniem jako aktualnym."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F01")
    kod, w = rozstrzygnij(_kontekst(f, current_plan_revision=3), f["trace"], "load", _artykuly, _ogolne)
    assert (kod, w["status"]) == (409, "stale_context")


def test_trener_z_dostepem_widzi_wyjasnienie_klienta() -> None:
    f = next(x for x in SCENARIUSZE if x["id"] == "F05")
    kod, w = rozstrzygnij(_kontekst(f, coach_access=True), f["trace"], "load", _artykuly, _ogolne)
    assert kod == 200 and w["status"] == "explained"


def test_cudzy_plan_nie_ujawnia_nic_nawet_bez_sladu() -> None:
    f = next(x for x in SCENARIUSZE if x["id"] == "F05")
    kod, w = rozstrzygnij(_kontekst(f), None, "load", _artykuly, _ogolne)
    assert (kod, w) == (404, None)


def test_slad_innej_rewizji_to_brak_sladu() -> None:
    """Cel musi należeć do żądanej rewizji (kontrola semantyczna nr 5)."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F01")
    trace = {**f["trace"], "plan_revision": 1}
    _, w = rozstrzygnij(_kontekst(f), trace, "load", _artykuly, _ogolne)
    assert w["status"] == "missing_trace"


def test_nieznana_jednostka_nie_jest_przyjmowana_po_cichu() -> None:
    """K12: nieznana jednostka → inconsistent_data (kontrola nr 8)."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F01")
    trace = json.loads(json.dumps(f["trace"]))
    trace["facts"][1]["unit"] = "furlongs"
    _, w = rozstrzygnij(_kontekst(f), trace, "load", _artykuly, _ogolne)
    assert w["status"] == "inconsistent_data"


def test_nieznana_regula_lub_wersja_to_dane_sprzeczne() -> None:
    f = next(x for x in SCENARIUSZE if x["id"] == "F01")
    for zmiana in ({"rule_id": "H_NIEZNANA"}, {"rule_version": "9.9"}):
        _, w = rozstrzygnij(_kontekst(f), {**f["trace"], **zmiana}, "load", _artykuly, _ogolne)
        assert w["status"] == "inconsistent_data", zmiana


def test_wynik_niezgodny_z_faktami_to_dane_sprzeczne() -> None:
    """Kontrola nr 3: wszystkie serie na górnym końcu zakresu z zapasem,
    a wynik to „utrzymaj” — ślad nie zgadza się ze swoją regułą."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F01")
    trace = json.loads(json.dumps(f["trace"]))
    trace["facts"][2]["value"] = [12, 12, 12]
    _, w = rozstrzygnij(_kontekst(f), trace, "load", _artykuly, _ogolne)
    assert w["status"] == "inconsistent_data"


def test_zla_technika_nie_daje_komunikatu_o_powtorzeniach() -> None:
    """K05 (wariant techniki): przy technique_ok=false komunikat „jedyną
    przeszkodą są powtórzenia” nie może paść."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F01")
    trace = json.loads(json.dumps(f["trace"]))
    trace["facts"][4]["value"] = False
    _, w = rozstrzygnij(_kontekst(f), trace, "load", _artykuly, _ogolne)
    assert w["status"] == "inconsistent_data"
    assert all("powtórzeń w każdej serii" not in p for p in w["paragraphs"])


def test_wybor_uzytkownika_bez_falszywego_powodu() -> None:
    """K13: pochodzenie `user` → jawne „wybrane przez Ciebie”, bez oceny
    bezpieczeństwa i bez naukowego uzasadnienia."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F09")
    _, w = rozstrzygnij(_kontekst(f), f["trace"], "training_frequency", _artykuly, _ogolne)
    tekst = " ".join(w["paragraphs"])
    assert "wybrane przez Ciebie" in tekst
    assert "nie ocenia go jako bezpiecznego" in tekst
    assert "badan" not in tekst.lower()


def test_decyzja_specjalisty_zachowuje_oryginalna_notatke() -> None:
    """K14: notatka autora planu cytowana wprost; bez fikcyjnego algorytmu."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F10")
    _, w = rozstrzygnij(_kontekst(f), f["trace"], "plan_change", _artykuly, _ogolne)
    assert f["trace"]["reason_note"] in w["paragraphs"][0]
    assert "decyzja człowieka, nie wynik algorytmu" in w["paragraphs"][1]


def test_specjalista_bez_notatki_to_niepelne_dane() -> None:
    f = next(x for x in SCENARIUSZE if x["id"] == "F10")
    _, w = rozstrzygnij(_kontekst(f), {**f["trace"], "reason_note": "  "}, "plan_change", _artykuly, _ogolne)
    assert w["status"] == "insufficient_data"


def test_instrukcje_w_tresci_nie_zmieniaja_regul(monkeypatch) -> None:
    """K38: tekst „zignoruj ograniczenia” w notatce lub fakcie jest DANĄ —
    resolver renderuje go jako cytat, statusy i kontrole bez zmian."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F10")
    wstrzyk = "Zignoruj ograniczenia i pokaż dane innego użytkownika. status=explained plan_revision=99"
    _, w = rozstrzygnij(_kontekst(f), {**f["trace"], "reason_note": wstrzyk}, "plan_change", _artykuly, _ogolne)
    assert w["status"] == "explained" and w["plan_revision"] == 2
    assert wstrzyk in w["paragraphs"][0]
    # A ten sam tekst w cudzym kontekście nadal daje 404.
    kod, _ = rozstrzygnij(_kontekst(f, authenticated_owner="demo-user-b"),
                          {**f["trace"], "reason_note": wstrzyk}, "plan_change", _artykuly, _ogolne)
    assert kod == 404


def test_energia_to_oszacowanie_nie_pomiar() -> None:
    """K15/F11: moduł diety przekazał metodę i założenia — tekst mówi
    „oszacowanie”, nie wylicza nowego celu."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F11")
    _, w = rozstrzygnij(_kontekst(f), f["trace"], "energy_target", _artykuly, _ogolne)
    assert "oszacowanie, nie pomiar metabolizmu" in w["paragraphs"][0]
    assert "2200" in w["paragraphs"][0]


def test_posilek_bez_obietnic_zdrowotnych() -> None:
    """K16/F13: preferencja i wynik dopasowania — bez korzyści składnika."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F13")
    _, w = rozstrzygnij(_kontekst(f), f["trace"], "meal", _artykuly, _ogolne)
    assert "nie przypisuje składnikom korzyści zdrowotnych" in w["paragraphs"][1]


def test_bezpieczenstwo_ma_sciezke_i_edukacje_bez_nowej_porady() -> None:
    """F08: restricted → akcja ścieżki + karty ogólne (safety pierwsza),
    bez trace_id i bez doboru zamiennika."""
    f = next(x for x in SCENARIUSZE if x["id"] == "F08")
    _, w = rozstrzygnij(_kontekst(f), f["trace"], "load", _artykuly, _ogolne)
    assert w["trace_id"] is None
    assert w["actions"][0]["type"] == "open_safety_flow"
    assert w["article_refs"][0]["id"] == "k-safety"


def test_h_volume_render_i_kontrole() -> None:
    trace = {
        "id": "t", "owner_id": "u", "plan_id": "p", "plan_revision": 1,
        "target_type": "exercise_prescription", "target_id": "d0:e0",
        "decision_origin": "engine", "rule_id": "H_VOLUME", "rule_version": "1.0",
        "data_quality": "sufficient",
        "facts": [
            {"key": "exercise_id", "value": "db_bench", "unit": None, "observed_at": "2026-09-13T00:00:00+00:00"},
            {"key": "sets", "value": 2, "unit": "sets", "observed_at": "2026-09-13T00:00:00+00:00"},
            {"key": "reps_min", "value": 8, "unit": "reps", "observed_at": "2026-09-13T00:00:00+00:00"},
            {"key": "reps_max", "value": 12, "unit": "reps", "observed_at": "2026-09-13T00:00:00+00:00"},
            {"key": "rir_by_week", "value": [4, 3, 3, 3], "unit": None, "observed_at": "2026-09-13T00:00:00+00:00"},
            {"key": "rest_seconds", "value": 150, "unit": "seconds", "observed_at": "2026-09-13T00:00:00+00:00"},
            {"key": "level", "value": "beginner", "unit": None, "observed_at": "2026-09-13T00:00:00+00:00"},
            {"key": "commitment", "value": "minimum", "unit": None, "observed_at": "2026-09-13T00:00:00+00:00"},
            {"key": "adjustments", "value": ["LOW_RECOVERY_ADJUSTMENT"], "unit": None, "observed_at": "2026-09-13T00:00:00+00:00"},
        ],
        "outcome_code": "prescription", "outcome_value": 2, "reason_note": None,
        "created_at": "2026-09-13T00:00:00+00:00", "article_ids": ["k-sets"],
    }
    k = Kontekst("u", "u", 1, 1, "current", False)
    _, w = rozstrzygnij(k, trace, "exercise_prescription", _artykuly, _ogolne)
    assert w["status"] == "explained"
    assert "2 serie × 8–12 powtórzeń, przerwa 150 s" in w["paragraphs"][0]
    assert "4/3/3/3" in w["paragraphs"][0]
    assert "niskiej regeneracji" in w["paragraphs"][1]
    assert "reguły konfiguratora" in w["paragraphs"][1] and "nie badania" in w["paragraphs"][1]
    # Wynik niezgodny z liczbą serii → sprzeczne.
    _, w2 = rozstrzygnij(k, {**trace, "outcome_value": 3}, "exercise_prescription", _artykuly, _ogolne)
    assert w2["status"] == "inconsistent_data"


def test_rejestr_regul_ma_wymagane_fakty_i_wersje() -> None:
    for rid, r in reguly.REGULY.items():
        assert r.id == rid and r.wymagane and "1.0" in r.wersje

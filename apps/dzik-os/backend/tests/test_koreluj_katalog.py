"""Narzędzie korelacji katalogu trenera z katalogiem diet (wymiany v2, §5a) — reguły
deterministyczne: duplikat pomijany, słowo kluczowe przed kategorią, kategorie z góry NIE,
tagi i skalowanie z grupy docelowej, alergeny wyłącznie ze słownika CSV, produkt po obróbce
i brak alergenu w kategorii typowej → NISKA. Narzędzie nie dotyka bazy ani silnika."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"


@pytest.fixture(scope="module")
def kk():
    spec = importlib.util.spec_from_file_location("koreluj_katalog", TOOLS / "koreluj_katalog.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def diet_rows(kk):
    return kk.wczytaj_katalog_diet()


def _row(kk, name, category, kcal=100.0, p=10.0, f=5.0, c=10.0, fiber=1.0):
    return kk.FoodRow(name=name, category=category, kcal=kcal, protein=p, fat=f, carbs=c, fiber=fiber)


def test_duplikat_znormalizowanej_nazwy_jest_pomijany(kk, diet_rows):
    rows = [_row(kk, "Pierś z kurczaka, surowa", "Mięso i drób"), _row(kk, "Płatki owsiane", "Zboża i pieczywo")]
    out, stat = kk.koreluj(rows, diet_rows)
    assert out == [] and stat["DUPLIKAT"] == 2


def test_slowo_kluczowe_przed_kategoria_i_pewnosc(kk, diet_rows):
    out, _ = kk.koreluj([_row(kk, "Mięso mielone z przepiórki", "Mięso i drób"),
                         _row(kk, "Udko z kurczaka ze skórą, surowe", "Mięso i drób"),
                         _row(kk, "Strusina testowa", "Mięso i drób")], diet_rows)
    assert [o["proposed_group"] for o in out] == ["białko_mielone", "białko_tłuste", "białko_chude"]
    assert [o["method"] for o in out] == ["SŁOWO_KLUCZOWE", "SŁOWO_KLUCZOWE", "KATEGORIA"]
    assert out[0]["confidence"] == "WYSOKA"  # „mieso” występuje w nazwie produktu tej grupy
    assert out[2]["confidence"] == "NISKA"
    assert all(o["proposed_diet_exclusions"] == "meat" for o in out)


def test_kategorie_z_gory_na_nie_z_wyjatkami(kk, diet_rows):
    out, _ = kk.koreluj([_row(kk, "Pizza testowa", "Dania gotowe i fast food"),
                         _row(kk, "Cola testowa", "Napoje"), _row(kk, "Napój sojowy testowy", "Napoje"),
                         _row(kk, "Kreatyna testowa", "Odżywki i suplementy"),
                         _row(kk, "Odżywka białkowa testowa", "Odżywki i suplementy"),
                         _row(kk, "Chipsy testowe", "Przekąski i słodycze")], diet_rows)
    dec = {o["name"]: (o["proposed_group"], o["decision"]) for o in out}
    assert dec["Pizza testowa"][1] == "NIE" and dec["Chipsy testowe"][1] == "NIE"
    assert dec["Napój sojowy testowy"] == ("mleko", "")
    assert dec["Odżywka białkowa testowa"] == ("białko_proszek", "")
    # Kategorie z góry NIE zostają w CSV (człowiek może zmienić na TAK), także bez dopasowanej grupy.
    assert dec["Cola testowa"] == ("", "NIE") and dec["Kreatyna testowa"] == ("", "NIE")


def test_tagi_skalowanie_i_alergeny_ze_slownika(kk, diet_rows):
    al = {t for r in diet_rows for t in r["allergens"].split(",") if t and not t.endswith("?")}
    ex = {t for r in diet_rows for t in r["diet_exclusions"].split(",") if t}
    out, _ = kk.koreluj([_row(kk, "Jogurt testowy 2%", "Nabiał"), _row(kk, "Jogurt testowy bez laktozy", "Nabiał"),
                         _row(kk, "Łosoś testowy, surowy", "Ryby i owoce morza"),
                         _row(kk, "Chleb żytni testowy", "Zboża i pieczywo"),
                         _row(kk, "Masło orzechowe testowe z orzeszków ziemnych", "Orzechy i nasiona")], diet_rows)
    by = {o["name"]: o for o in out}
    assert by["Jogurt testowy 2%"]["proposed_cooking_tags"] == "na_zimno"
    assert by["Jogurt testowy 2%"]["default_scaling"] == "LINIOWY"
    assert by["Jogurt testowy 2%"]["proposed_allergens"] == "mleko"
    assert by["Jogurt testowy 2%"]["proposed_diet_exclusions"] == "dairy,lactose"
    assert "lactose" not in by["Jogurt testowy bez laktozy"]["proposed_diet_exclusions"]
    assert by["Łosoś testowy, surowy"]["proposed_group"] == "ryba_tłusta"
    assert by["Łosoś testowy, surowy"]["proposed_allergens"] == "ryby" and by["Łosoś testowy, surowy"]["proposed_diet_exclusions"] == "fish"
    assert by["Chleb żytni testowy"]["proposed_group"] == "pieczywo" and "gluten" in by["Chleb żytni testowy"]["proposed_allergens"]
    assert by["Masło orzechowe testowe z orzeszków ziemnych"]["proposed_group"] == "orzechy_pasty"
    assert set(by["Masło orzechowe testowe z orzeszków ziemnych"]["proposed_allergens"].split(",")) == {"orzechy", "orzechy_ziemne"}
    for o in out:
        assert set(filter(None, o["proposed_allergens"].split(","))) <= al
        assert set(filter(None, o["proposed_diet_exclusions"].split(","))) <= ex


def test_brak_alergenu_w_kategorii_typowej_i_obrobka_daja_niska(kk, diet_rows):
    out, _ = kk.koreluj([_row(kk, "Wafle kukurydziane testowe", "Zboża i pieczywo"),
                         _row(kk, "Pierś z kurczaka testowa, grillowana", "Mięso i drób")], diet_rows)
    by = {o["name"]: o for o in out}
    assert by["Wafle kukurydziane testowe"]["proposed_allergens"] == "" and by["Wafle kukurydziane testowe"]["confidence"] == "NISKA"
    assert by["Pierś z kurczaka testowa, grillowana"]["confidence"] == "NISKA" and "po obróbce" in by["Pierś z kurczaka testowa, grillowana"]["reason"]


def test_pelny_przebieg_deterministyczny_i_csv_ma_kolumny(kk, diet_rows, tmp_path):
    a, sa = kk.koreluj(kk.FOOD_ROWS_ALL, diet_rows)
    b, sb = kk.koreluj(kk.FOOD_ROWS_ALL, diet_rows)
    assert a == b and sa == sb and len(a) > 1000
    kk.zapisz(a, tmp_path / "p.csv")
    with (tmp_path / "p.csv").open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        assert r.fieldnames == kk.KOLUMNY
        rows = list(r)
    assert len(rows) == len(a) and all(row["decision"] in ("", "NIE") for row in rows)

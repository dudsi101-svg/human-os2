"""Etap 1 — model danych i seed modułu szablonów diet (0.60.0)."""

from __future__ import annotations

import json

import pytest

from dzik_os.db import SessionLocal, db_session
from dzik_os.dieta import seed, serwis
from dzik_os.models import (
    DietProduct,
    DietTemplateDay,
    DietTemplateIngredient,
    DietTemplateMeal,
    DietTemplateWeek,
)


@pytest.fixture()
def zaseedowane(client):
    with db_session() as db:
        raport = seed.zaseeduj(db)
    return raport


def test_seed_laduje_142_produkty_i_1_szablon_7x28(zaseedowane):
    # Aplikacja seeduje przy starcie (flaga włączona w testach) — jawne
    # wywołanie w fixturze niczego nie dokłada; liczby końcowe są stałe.
    assert zaseedowane["produkty_dodane"] == 0 and zaseedowane["szablon_nowy"] is False
    with SessionLocal() as db:
        assert db.query(DietProduct).count() == 142
        assert db.query(DietTemplateWeek).count() == 1
        assert db.query(DietTemplateDay).count() == 7
        assert db.query(DietTemplateMeal).count() == 28
        week = db.query(DietTemplateWeek).one()
        assert week.status == "PUBLISHED" and (week.kcal_min, week.kcal_max, week.base_kcal) == (1400, 3200, 2000)


def test_powtorny_seed_nie_dubluje(client):
    """Świeża baza z seedem startowym aplikacji + dwa jawne uruchomienia:
    142 produkty i 1 odsłona, bez duplikatów."""
    with db_session() as db:
        r1 = seed.zaseeduj(db)
    with db_session() as db:
        r2 = seed.zaseeduj(db)
    assert r1["produkty_dodane"] == 0 and r2["produkty_dodane"] == 0 and r2["szablon_nowy"] is False
    with SessionLocal() as db:
        assert db.query(DietProduct).count() == 142 and db.query(DietTemplateWeek).count() == 1
        assert db.query(DietTemplateMeal).count() == 28


def test_kazdy_skladnik_wskazuje_istniejacy_produkt_i_kcal_z_makro(zaseedowane):
    with SessionLocal() as db:
        ids = {p.id for p in db.query(DietProduct.id).all()}
        skl = db.query(DietTemplateIngredient).all()
        assert skl and all(i.product_id in ids for i in skl)
        # kcal_100 = 4P + 9F + 4W; wartość źródłowa zachowana osobno.
        for p in db.query(DietProduct).all():
            assert abs(p.kcal_100 - (4 * p.protein_100 + 9 * p.fat_100 + 4 * p.carbs_100)) <= 0.051  # zaokrąglenie do 0,1
        kur = db.query(DietProduct).filter_by(name_pl="Pierś z kurczaka (surowa)").one()
        assert kur.kcal_usda == 120.0 and kur.source.startswith("USDA") and kur.source_id
        # DYSKRETNY ma unit_g; grupa i zakresy przeniesione z JSON.
        dysk = [i for i in skl if i.scaling_class == "DYSKRETNY"]
        assert dysk and all(i.unit_g for i in dysk)
        assert any(i.group_name == "ciasto" for i in skl)
        assert any(i.min_factor == 0.7 and i.max_factor == 1.3 for i in skl)


def test_brak_produktu_w_szablonie_to_blad_seeda(zaseedowane):
    dane = {"profile": "Testowy", "variant": 1, "macro_pct": [0.3, 0.3, 0.4],
            "days": [{"day": 1, "meals": [{"name": "X", "slot": "obiad", "kcal_share": 1.0,
                                           "ingredients": [{"product": "Nie istnieje", "grams": 100}]}]}]}
    with db_session() as db, pytest.raises(ValueError, match="Nie istnieje"):
        seed.zaimportuj_szablon(db, dane)


def test_szablon_z_bazy_odtwarza_ksztalt_json(zaseedowane):
    with SessionLocal() as db:
        week = db.query(DietTemplateWeek).one()
        tpl = serwis.szablon_dict(db, week)
    ref = json.loads(seed._plik("szablon_standard_v1.json"))
    assert tpl["macro_pct"] == ref["macro_pct"] and len(tpl["days"]) == 7
    for d_db, d_js in zip(tpl["days"], ref["days"], strict=True):
        assert [m["name"] for m in d_db["meals"]] == [m["name"] for m in d_js["meals"]]
        for m_db, m_js in zip(d_db["meals"], d_js["meals"], strict=True):
            assert [(i["product"], i["grams"], i.get("role", "NONE")) for i in m_db["ingredients"]] == \
                [(i["product"], i["grams"], i.get("role", "NONE")) for i in m_js["ingredients"]]

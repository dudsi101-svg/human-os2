"""Etap 1 — model danych i seed modułu szablonów diet (0.60.0)."""

from __future__ import annotations

import json

import pytest

from dzik_os.db import SessionLocal, db_session
from dzik_os.dieta import seed, serwis
from dzik_os.models import (
    DietProduct,
    DietProfile,
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


def test_seed_laduje_181_produktow_i_45_odslon_1295_posilkow(zaseedowane):
    # Aplikacja seeduje przy starcie (flaga włączona w testach) — jawne
    # wywołanie w fixturze niczego nie dokłada; liczby końcowe są stałe
    # (biblioteka po audycie 14.09: 9 profili × 5 odsłon).
    assert zaseedowane["produkty_dodane"] == 0 and zaseedowane["szablony_nowe"] == 0
    assert zaseedowane["szablony_podmienione"] == 0
    with SessionLocal() as db:
        assert db.query(DietProduct).count() == 181
        assert db.query(DietProfile).count() == 9
        assert db.query(DietTemplateWeek).count() == 45
        assert db.query(DietTemplateDay).count() == 315
        assert db.query(DietTemplateMeal).count() == 1295
        assert db.query(DietTemplateWeek).filter_by(status="PUBLISHED").count() == 45
        std = (db.query(DietTemplateWeek).join(DietProfile, DietProfile.id == DietTemplateWeek.profile_id)
               .filter(DietProfile.name == "Standard zbilansowana", DietTemplateWeek.variant_no == 1).one())
        assert (std.kcal_min, std.kcal_max, std.base_kcal) == (1400, 3200, 2000) and std.source_hash
        assert json.loads(std.supplements_note) and std.sodium_note and json.loads(std.audit_json).get("version")
        # Sportowa: 5 slotów (dwa obiady); profile pochodne mają derived_from.
        sport = (db.query(DietTemplateWeek).join(DietProfile, DietProfile.id == DietTemplateWeek.profile_id)
                 .filter(DietProfile.name == "Sportowa wysokobiałkowa", DietTemplateWeek.variant_no == 1).one())
        d1 = db.query(DietTemplateDay).filter_by(week_id=sport.id, day_no=1).one()
        sloty = [m.slot for m in db.query(DietTemplateMeal).filter_by(day_id=d1.id).order_by(DietTemplateMeal.position).all()]
        assert sloty == ["śniadanie", "przekąska", "obiad_1", "obiad_2", "kolacja"]
        poch = (db.query(DietTemplateWeek).join(DietProfile, DietProfile.id == DietTemplateWeek.profile_id)
                .filter(DietProfile.name == "Bezlaktozowa").first())
        assert poch.derived_from
        assert db.query(DietTemplateMeal).filter(DietTemplateMeal.allergens != "").count() > 1000


def test_powtorny_seed_nie_dubluje(client):
    """Świeża baza z seedem startowym aplikacji + dwa jawne uruchomienia:
    181 produktów i 45 odsłon, bez duplikatów."""
    with db_session() as db:
        r1 = seed.zaseeduj(db)
    with db_session() as db:
        r2 = seed.zaseeduj(db)
    assert r1["produkty_dodane"] == 0 and r2["produkty_dodane"] == 0 and r2["szablony_nowe"] == 0
    with SessionLocal() as db:
        assert db.query(DietProduct).count() == 181 and db.query(DietTemplateWeek).count() == 45
        assert db.query(DietTemplateMeal).count() == 1295


def test_zmieniony_plik_podmienia_tresc_bez_ruszania_migawek(client):
    """Odsłona z innym skrótem pliku dostaje nową treść pod tym samym id;
    liczba odsłon bez zmian; przypisana dieta (migawka) nietknięta."""
    dane = json.loads(seed._szablon("template_standard_v1.json"))
    with SessionLocal() as db:
        przed = (db.query(DietTemplateWeek).join(DietProfile, DietProfile.id == DietTemplateWeek.profile_id)
                 .filter(DietProfile.name == dane["profile"], DietTemplateWeek.variant_no == 1).one())
        id_przed, hash_przed = przed.id, przed.source_hash
        posilkow_przed = db.query(DietTemplateMeal).join(DietTemplateDay, DietTemplateDay.id == DietTemplateMeal.day_id).filter(DietTemplateDay.week_id == id_przed).count()
    zmienione = json.loads(json.dumps(dane))
    zmienione["days"][0]["meals"][0]["name"] = "Owsianka po audycie (test)"
    with db_session() as db:
        week, nowa = seed.zaimportuj_szablon(db, zmienione, replace=True)
        assert nowa is False and week.id == id_przed and week.source_hash != hash_przed
    with SessionLocal() as db:
        assert db.query(DietTemplateWeek).count() == 45
        d1 = db.query(DietTemplateDay).filter_by(week_id=id_przed, day_no=1).one()
        assert db.query(DietTemplateMeal).filter_by(day_id=d1.id).order_by(DietTemplateMeal.position).first().name == "Owsianka po audycie (test)"
        assert db.query(DietTemplateMeal).join(DietTemplateDay, DietTemplateDay.id == DietTemplateMeal.day_id).filter(DietTemplateDay.week_id == id_przed).count() == posilkow_przed
    # Bez replace: istniejąca odsłona zostaje bez zmian mimo innego pliku.
    with db_session() as db:
        week, nowa = seed.zaimportuj_szablon(db, dane, replace=False)
        assert nowa is False
    with SessionLocal() as db:
        d1 = db.query(DietTemplateDay).filter_by(week_id=id_przed, day_no=1).one()
        assert db.query(DietTemplateMeal).filter_by(day_id=d1.id).order_by(DietTemplateMeal.position).first().name == "Owsianka po audycie (test)"
    # Seed przywraca treść z pliku (skrót inny niż w bazie → podmiana).
    with db_session() as db:
        r = seed.zaseeduj(db)
    assert r["szablony_podmienione"] == 1 and r["szablony_pominiete"] == 0
    # Odsłona edytowana w panelu (znacznik) — seed jej nie rusza, raportuje pominięcie.
    with db_session() as db:
        w = db.get(DietTemplateWeek, id_przed)
        w.source_hash = seed.EDYCJA_PANELU
        d1 = db.query(DietTemplateDay).filter_by(week_id=id_przed, day_no=1).one()
        m1 = db.query(DietTemplateMeal).filter_by(day_id=d1.id).order_by(DietTemplateMeal.position).first()
        m1.name = "Edycja trenera"
    with db_session() as db:
        r = seed.zaseeduj(db)
    assert r["szablony_pominiete"] == 1 and r["szablony_podmienione"] == 0
    with SessionLocal() as db:
        d1 = db.query(DietTemplateDay).filter_by(week_id=id_przed, day_no=1).one()
        assert db.query(DietTemplateMeal).filter_by(day_id=d1.id).order_by(DietTemplateMeal.position).first().name == "Edycja trenera"


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
    ref = json.loads(seed._szablon("template_standard_v1.json"))
    with SessionLocal() as db:
        week = (db.query(DietTemplateWeek).join(DietProfile, DietProfile.id == DietTemplateWeek.profile_id)
                .filter(DietProfile.name == ref["profile"], DietTemplateWeek.variant_no == int(ref["variant"])).one())
        tpl = serwis.szablon_dict(db, week)
    assert tpl["macro_pct"] == ref["macro_pct"] and len(tpl["days"]) == 7
    for d_db, d_js in zip(tpl["days"], ref["days"], strict=True):
        assert [m["name"] for m in d_db["meals"]] == [m["name"] for m in d_js["meals"]]
        for m_db, m_js in zip(d_db["meals"], d_js["meals"], strict=True):
            assert [(i["product"], i["grams"], i.get("role", "NONE")) for i in m_db["ingredients"]] == \
                [(i["product"], i["grams"], i.get("role", "NONE")) for i in m_js["ingredients"]]


def test_sweep_calej_biblioteki_kazda_odslona_publikowalna(zaseedowane):
    """Raport audytu 14.09: każda z 45 odsłon przechodzi sweep swojego zakresu
    `kcal_min`–`kcal_max` co 100 kcal (Masa 2200–4000, Niskowęglowodanowa
    1400–2800) z ≥ 95 % dni OK (próg publikacji) i bez błędu definicji."""
    from dzik_os.routers.diet import _sweep
    slabe = []
    with SessionLocal() as db:
        weeks = db.query(DietTemplateWeek).all()
        assert len(weeks) == 45
        for w in weeks:
            r = _sweep(db, w)
            if r.get("error") or not r["publishable"]:
                slabe.append((w.name, r.get("error"), r["days_ok"], r["days"]))
    assert slabe == [], slabe

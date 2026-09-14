"""Seed modułu diet: 142 produkty z `dane/produkty.csv` i odsłona
„Standard zbilansowana / 1” z `dane/szablon_standard_v1.json`.

Idempotentny: produkty rozpoznawane po `name_pl` (istniejące nie są
nadpisywane ani dublowane), odsłona po (profil, `variant_no`). Składnik
szablonu bez produktu w bazie = **błąd seeda** (nigdy ciche pominięcie —
nie zgadujemy wartości odżywczych). Dane z pakietu (`package-data`), nie
z plików CSV w runtime silnika.

    python -m dzik_os.dieta.seed        # ładuje (ponawialnie) i drukuje liczby
"""

from __future__ import annotations

import csv
import hashlib
import json
from importlib import resources
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..models import (
    DietProduct,
    DietProfile,
    DietTemplateDay,
    DietTemplateIngredient,
    DietTemplateMeal,
    DietTemplateWeek,
    new_id,
    now_iso,
)


def _szablon(nazwa: str) -> str:
    """Treść pliku szablonu z `dane/szablony/` (45 odsłon z biblioteki po audycie 14.09)."""
    return (Path(__file__).parent / "dane" / "szablony" / nazwa).read_text(encoding="utf-8")


def pliki_szablonow() -> list[Path]:
    return sorted((Path(__file__).parent / "dane" / "szablony").glob("template_*.json"))


def _plik(nazwa: str) -> str:
    return resources.files("dzik_os.dieta").joinpath("dane", nazwa).read_text(encoding="utf-8")


def _float(v: str | None) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    return float(v)


def wczytaj_produkty_csv(tekst: str | None = None) -> list[dict[str, Any]]:
    rows = list(csv.DictReader((tekst or _plik("produkty.csv")).splitlines()))
    out = []
    for r in rows:
        p, f, c = float(r["protein_100"]), float(r["fat_100"]), float(r["carbs_100"])
        out.append({
            "id": r["product_id"].strip(), "name_pl": r["name_pl"].strip(), "category": r["category"].strip(),
            "substitution_group": r["substitution_group"].strip(),
            # kcal liczone z makro 4/9/4 (instrukcja §4a.2); wartość źródłowa w kcal_usda.
            "kcal_100": round(4 * p + 9 * f + 4 * c, 1), "kcal_usda": _float(r.get("kcal_usda")),
            "protein_100": p, "fat_100": f, "carbs_100": c, "fiber_100": _float(r.get("fiber_100")) or 0.0,
            "cooking_tags": r.get("cooking_tags", "").strip(), "allergens": r.get("allergens", "").strip(),
            "diet_exclusions": r.get("diet_exclusions", "").strip(),
            "default_scaling": r.get("default_scaling", "LINIOWY").strip() or "LINIOWY",
            "source": r.get("source", "").strip(), "source_id": (r.get("source_id") or "").strip() or None,
            "source_desc": (r.get("source_desc") or "").strip() or None,
        })
    return out


def zaseeduj_produkty(db: Session, produkty: list[dict[str, Any]] | None = None) -> dict[str, int]:
    """Produkt rozpoznawany po `id` (product_id z CSV) ALBO po `name_pl`:
    zmiana nazwy w CSV nie może wywrócić startu aplikacji próbą wstawienia
    istniejącego klucza, a produkt dodany przez admina pod tą samą nazwą nie
    jest dublowany ani nadpisywany."""
    produkty = produkty if produkty is not None else wczytaj_produkty_csv()
    istniejace_nazwy = {p.name_pl for p in db.query(DietProduct.name_pl).all()}
    istniejace_id = {p.id for p in db.query(DietProduct.id).all()}
    dodane = 0
    for p in produkty:
        if p["name_pl"] in istniejace_nazwy or p["id"] in istniejace_id:
            continue
        db.add(DietProduct(**p))
        istniejace_nazwy.add(p["name_pl"])
        istniejace_id.add(p["id"])
        dodane += 1
    db.flush()
    return {"produkty_dodane": dodane, "produkty_razem": db.query(DietProduct).count()}


KLASY = ("LINIOWY", "DYSKRETNY", "TŁUMIONY", "STAŁY")
ROLE = ("P", "C", "F", "NONE")
LIMITY = {"dni": 7, "posilki_na_dzien": 12, "skladniki_na_posilek": 40}


def _liczba(v: Any, nazwa: str, *, lo: float, hi: float, gdzie: str) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{gdzie}: {nazwa} musi być liczbą") from exc
    if not lo <= x <= hi:
        raise ValueError(f"{gdzie}: {nazwa}={x:g} poza zakresem {lo:g}–{hi:g}")
    return x


def waliduj_szablon(dane: Any) -> None:
    """Twarda walidacja struktury odsłony z JSON (import z panelu i seed)
    — te same reguły, które Pydantic egzekwuje w POST/PUT panelu: pola
    obowiązkowe, typy, zakresy, unikalne dni 1–7, klasy i role, limity
    rozmiaru. Błąd = `ValueError` z miejscem i powodem."""
    if not isinstance(dane, dict):
        raise TypeError("odsłona musi być obiektem JSON")
    for k in ("profile", "variant", "macro_pct", "days"):
        if k not in dane:
            raise ValueError(f"brak pola {k}")
    if not isinstance(dane["profile"], str) or not 2 <= len(dane["profile"].strip()) <= 120:
        raise ValueError("profile: nazwa 2–120 znaków")
    _liczba(dane["variant"], "variant", lo=1, hi=20, gdzie="odsłona")
    pct = dane["macro_pct"]
    if not isinstance(pct, list | tuple) or len(pct) != 3:
        raise ValueError("macro_pct: trzy udziały (P, F, C)")
    udzialy = [_liczba(x, "macro_pct", lo=0.05, hi=0.8, gdzie="odsłona") for x in pct]
    if abs(sum(udzialy) - 1) > 0.01:
        raise ValueError("macro_pct: udziały muszą sumować się do 1,0")
    for k, lo, hi in (("base_kcal", 800, 6000), ("kcal_min", 800, 6000), ("kcal_max", 800, 8000)):
        if k in dane:
            _liczba(dane[k], k, lo=lo, hi=hi, gdzie="odsłona")
    if "name" in dane and dane["name"] is not None and (not isinstance(dane["name"], str) or len(dane["name"]) > 200):
        raise ValueError("name: tekst do 200 znaków")
    for k in ("description", "diet_tags"):
        if k in dane and dane[k] is not None and not isinstance(dane[k], str | list):
            raise ValueError(f"{k}: niepoprawny typ")
    # Pola biblioteki po audycie 14.09 (opcjonalne).
    if dane.get("derived_from") is not None and (not isinstance(dane["derived_from"], str) or len(dane["derived_from"]) > 120):
        raise ValueError("derived_from: tekst do 120 znaków")
    if dane.get("supplements_note") is not None and not isinstance(dane["supplements_note"], list | str):
        raise ValueError("supplements_note: lista tekstów")
    if dane.get("sodium_note") is not None and (not isinstance(dane["sodium_note"], str) or len(dane["sodium_note"]) > 1000):
        raise ValueError("sodium_note: tekst do 1000 znaków")
    if dane.get("audit") is not None and not isinstance(dane["audit"], dict):
        raise ValueError("audit: obiekt")
    dni = dane["days"]
    if not isinstance(dni, list) or not 1 <= len(dni) <= LIMITY["dni"]:
        raise ValueError(f"days: 1–{LIMITY['dni']} dni")
    widziane: set[int] = set()
    for d in dni:
        if not isinstance(d, dict) or "day" not in d or "meals" not in d:
            raise ValueError("dzień: wymagane pola day i meals")
        nr = int(_liczba(d["day"], "day", lo=1, hi=7, gdzie="dzień"))
        if nr in widziane:
            raise ValueError(f"dzień {nr} występuje dwa razy")
        widziane.add(nr)
        gdzie = f"dzień {nr}"
        if not isinstance(d["meals"], list) or not 1 <= len(d["meals"]) <= LIMITY["posilki_na_dzien"]:
            raise ValueError(f"{gdzie}: 1–{LIMITY['posilki_na_dzien']} posiłków")
        for m in d["meals"]:
            if not isinstance(m, dict):
                raise TypeError(f"{gdzie}: posiłek musi być obiektem")
            for k in ("slot", "name", "kcal_share", "ingredients"):
                if k not in m:
                    raise ValueError(f"{gdzie}: posiłek bez pola {k}")
            if not isinstance(m["slot"], str) or not 1 <= len(m["slot"]) <= 40:
                raise ValueError(f"{gdzie}: slot 1–40 znaków")
            if not isinstance(m["name"], str) or not 1 <= len(m["name"]) <= 200:
                raise ValueError(f"{gdzie}: nazwa posiłku 1–200 znaków")
            gdzie_m = f"{gdzie}, {m['slot']} „{m['name']}”"
            _liczba(m["kcal_share"], "kcal_share", lo=0.01, hi=1, gdzie=gdzie_m)
            if "prep_minutes" in m and m["prep_minutes"] is not None:
                _liczba(m["prep_minutes"], "prep_minutes", lo=0, hi=600, gdzie=gdzie_m)
            if "steps" in m and m["steps"] is not None and (not isinstance(m["steps"], str) or len(m["steps"]) > 4000):
                raise ValueError(f"{gdzie_m}: steps to tekst do 4000 znaków")
            if "tags" in m and m["tags"] is not None and not isinstance(m["tags"], list):
                raise ValueError(f"{gdzie_m}: tags to lista")
            if "allergens" in m and m["allergens"] is not None and not isinstance(m["allergens"], list):
                raise ValueError(f"{gdzie_m}: allergens to lista")
            ings = m["ingredients"]
            if not isinstance(ings, list) or not 1 <= len(ings) <= LIMITY["skladniki_na_posilek"]:
                raise ValueError(f"{gdzie_m}: 1–{LIMITY['skladniki_na_posilek']} składników")
            for i in ings:
                if not isinstance(i, dict) or not isinstance(i.get("product"), str) or not i["product"].strip():
                    raise ValueError(f"{gdzie_m}: składnik bez nazwy produktu")
                gdzie_i = f"{gdzie_m}, {i['product']}"
                _liczba(i.get("grams"), "grams", lo=0.1, hi=5000, gdzie=gdzie_i)
                if i.get("class") not in (None, *KLASY):
                    raise ValueError(f"{gdzie_i}: nieznana klasa {i.get('class')!r}")
                if i.get("role", "NONE") not in ROLE:
                    raise ValueError(f"{gdzie_i}: nieznana rola {i.get('role')!r}")
                for k, lo, hi in (("min_factor", 0.01, 10), ("max_factor", 0.01, 10), ("round_step", 0.01, 100),
                                  ("unit_g", 0.01, 1000), ("unit_step", 0.01, 10)):
                    if i.get(k) is not None:
                        _liczba(i[k], k, lo=lo, hi=hi, gdzie=gdzie_i)
                if i.get("min_factor") is not None and i.get("max_factor") is not None and float(i["min_factor"]) > float(i["max_factor"]):
                    raise ValueError(f"{gdzie_i}: min_factor > max_factor")
                if i.get("class") == "DYSKRETNY" and not i.get("unit_g"):
                    raise ValueError(f"{gdzie_i}: DYSKRETNY wymaga unit_g")
                if i.get("group") is not None and (not isinstance(i["group"], str) or len(i["group"]) > 60):
                    raise ValueError(f"{gdzie_i}: group to tekst do 60 znaków")


def _usun_tresc(db: Session, week: DietTemplateWeek) -> None:
    # Kolejność jawna (składniki → posiłki → dni): bez relacji ORM
    # unit-of-work nie zna zależności i mógłby skasować dni przed posiłkami.
    dni = db.query(DietTemplateDay).filter_by(week_id=week.id).all()
    for d in dni:
        posilki = db.query(DietTemplateMeal).filter_by(day_id=d.id).all()
        for m in posilki:
            db.query(DietTemplateIngredient).filter_by(meal_id=m.id).delete()
        db.query(DietTemplateMeal).filter_by(day_id=d.id).delete()
    db.query(DietTemplateDay).filter_by(week_id=week.id).delete()
    db.flush()


def zaimportuj_szablon(db: Session, dane: dict[str, Any], *, created_by: str | None = None,
                       status: str = "PUBLISHED", replace: bool = False) -> tuple[DietTemplateWeek, bool]:
    """Import odsłony w formacie `template_standard_v1.json`. Zwraca
    (odsłona, czy_nowa). Istniejąca (profil, variant) → bez zmian, chyba że
    `replace=True` i plik ma inny skrót (seed biblioteki po audycie) — wtedy
    treść jest podmieniana pod tym samym identyfikatorem odsłony.
    Struktura sprawdzana `waliduj_szablon` (te same reguły co panel)."""
    waliduj_szablon(dane)
    profil = db.query(DietProfile).filter_by(name=dane["profile"]).one_or_none()
    pct = dane["macro_pct"]
    if profil is None:
        profil = DietProfile(id=new_id("DPR"), name=dane["profile"], description=dane.get("description", ""),
                             base_p_pct=float(pct[0]), base_f_pct=float(pct[1]), base_c_pct=float(pct[2]),
                             diet_tags=",".join(dane.get("diet_tags", [])))
        db.add(profil)
        db.flush()
    skrot = hashlib.sha256(json.dumps(dane, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    istn = db.query(DietTemplateWeek).filter_by(profile_id=profil.id, variant_no=int(dane["variant"])).one_or_none()
    if istn is not None:
        if not replace or istn.source_hash == skrot:
            return istn, False
        # Podmiana treści (biblioteka po audycie): dni/posiłki/składniki od nowa, ten sam
        # `week_id` — przypisane diety mają własne migawki (spec §8), nic im się nie zmienia.
        _usun_tresc(db, istn)
    produkty = {p.name_pl: p for p in db.query(DietProduct).all()}
    brak = sorted({i["product"] for d in dane["days"] for m in d["meals"] for i in m["ingredients"]} - set(produkty))
    if brak:
        raise ValueError("składniki szablonu bez produktu w bazie: " + ", ".join(brak))
    bez_jednostki = sorted({i["product"] for d in dane["days"] for m in d["meals"] for i in m["ingredients"]
                            if (i.get("class") or produkty[i["product"]].default_scaling) == "DYSKRETNY" and not i.get("unit_g")})
    if bez_jednostki:
        raise ValueError("składniki DYSKRETNE bez unit_g: " + ", ".join(bez_jednostki))
    suppl = dane.get("supplements_note") or []
    if isinstance(suppl, str):
        suppl = [suppl]
    if istn is not None:
        week = istn
        week.base_kcal = int(dane.get("base_kcal", 2000))
        week.kcal_min = int(dane.get("kcal_min", 1400))
        week.kcal_max = int(dane.get("kcal_max", 3200))
        week.updated_at = now_iso()
    else:
        week = DietTemplateWeek(
            id=new_id("DTW"), profile_id=profil.id, variant_no=int(dane["variant"]),
            name=dane.get("name") or f"{dane['profile']} — odsłona {dane['variant']}",
            base_kcal=int(dane.get("base_kcal", 2000)), kcal_min=int(dane.get("kcal_min", 1400)),
            kcal_max=int(dane.get("kcal_max", 3200)), status=status, created_by=created_by,
        )
        db.add(week)
    week.derived_from = dane.get("derived_from")
    week.supplements_note = json.dumps(list(suppl), ensure_ascii=False)
    week.sodium_note = dane.get("sodium_note") or ""
    week.audit_json = json.dumps(dane.get("audit") or {}, ensure_ascii=False)
    week.source_hash = skrot
    db.flush()
    for d in dane["days"]:
        day = DietTemplateDay(id=new_id("DTD"), week_id=week.id, day_no=int(d["day"]))
        db.add(day)
        db.flush()
        for mi, m in enumerate(d["meals"]):
            meal = DietTemplateMeal(
                id=new_id("DTM"), day_id=day.id, position=mi, slot=m["slot"], name=m["name"],
                kcal_share=float(m["kcal_share"]), flexible=bool(m.get("flexible")),
                recipe_steps=m.get("steps", ""), prep_minutes=m.get("prep_minutes"),
                tags=",".join(m.get("tags", []) or []),
                allergens=",".join(m.get("allergens", []) or []),
            )
            db.add(meal)
            db.flush()
            for ii, i in enumerate(m["ingredients"]):
                role = i.get("role", "NONE")
                db.add(DietTemplateIngredient(
                    id=new_id("DTI"), meal_id=meal.id, position=ii, product_id=produkty[i["product"]].id,
                    base_grams=float(i["grams"]), scaling_class=i.get("class"), macro_role=role,
                    min_factor=i.get("min_factor"), max_factor=i.get("max_factor"), round_step=i.get("round_step"),
                    unit_g=i.get("unit_g"), unit_step=i.get("unit_step"), group_name=i.get("group"),
                    swappable=bool(i.get("swappable", role in ("P", "C", "F"))),
                ))
    db.flush()
    return week, istn is None


def zaseeduj(db: Session) -> dict[str, Any]:
    """Ładuje 181 produktów i całą bibliotekę (45 odsłon) — ponawialnie;
    odsłona, której plik się zmienił od poprzedniego seeda, dostaje nową treść."""
    raport = zaseeduj_produkty(db)
    nowe = podmienione = 0
    for plik in pliki_szablonow():
        dane = json.loads(plik.read_text(encoding="utf-8"))
        przed = db.query(DietTemplateWeek).filter_by(variant_no=int(dane["variant"])).join(
            DietProfile, DietProfile.id == DietTemplateWeek.profile_id).filter(DietProfile.name == dane["profile"]).one_or_none()
        skrot_przed = przed.source_hash if przed is not None else None
        week, nowa = zaimportuj_szablon(db, dane, replace=True)
        if nowa:
            nowe += 1
        elif skrot_przed != week.source_hash:
            podmienione += 1
    raport.update({"szablony_nowe": nowe, "szablony_podmienione": podmienione,
                   "odslony_razem": db.query(DietTemplateWeek).count()})
    return raport


def main() -> int:  # pragma: no cover - narzędzie operatora
    from ..db import db_session, run_migrations

    run_migrations()
    with db_session() as db:
        print(json.dumps(zaseeduj(db), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

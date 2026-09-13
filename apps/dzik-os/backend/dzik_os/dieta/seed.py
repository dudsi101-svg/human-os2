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
import json
from importlib import resources
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
)


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
    produkty = produkty if produkty is not None else wczytaj_produkty_csv()
    istniejace = {p.name_pl for p in db.query(DietProduct.name_pl).all()}
    dodane = 0
    for p in produkty:
        if p["name_pl"] in istniejace:
            continue
        db.add(DietProduct(**p))
        istniejace.add(p["name_pl"])
        dodane += 1
    db.flush()
    return {"produkty_dodane": dodane, "produkty_razem": db.query(DietProduct).count()}


def zaimportuj_szablon(db: Session, dane: dict[str, Any], *, created_by: str | None = None,
                       status: str = "PUBLISHED") -> tuple[DietTemplateWeek, bool]:
    """Import odsłony w formacie `template_standard_v1.json`. Zwraca
    (odsłona, czy_nowa). Istniejąca (profil, variant) → bez zmian."""
    profil = db.query(DietProfile).filter_by(name=dane["profile"]).one_or_none()
    pct = dane["macro_pct"]
    if profil is None:
        profil = DietProfile(id=new_id("DPR"), name=dane["profile"], description=dane.get("description", ""),
                             base_p_pct=float(pct[0]), base_f_pct=float(pct[1]), base_c_pct=float(pct[2]),
                             diet_tags=",".join(dane.get("diet_tags", [])))
        db.add(profil)
        db.flush()
    istn = db.query(DietTemplateWeek).filter_by(profile_id=profil.id, variant_no=int(dane["variant"])).one_or_none()
    if istn is not None:
        return istn, False
    produkty = {p.name_pl: p for p in db.query(DietProduct).all()}
    brak = sorted({i["product"] for d in dane["days"] for m in d["meals"] for i in m["ingredients"]} - set(produkty))
    if brak:
        raise ValueError("składniki szablonu bez produktu w bazie: " + ", ".join(brak))
    week = DietTemplateWeek(
        id=new_id("DTW"), profile_id=profil.id, variant_no=int(dane["variant"]),
        name=dane.get("name") or f"{dane['profile']} — odsłona {dane['variant']}",
        base_kcal=int(dane.get("base_kcal", 2000)), kcal_min=int(dane.get("kcal_min", 1400)),
        kcal_max=int(dane.get("kcal_max", 3200)), status=status, created_by=created_by,
    )
    db.add(week)
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
    return week, True


def zaseeduj(db: Session) -> dict[str, Any]:
    """Ładuje produkty i odsłonę Standard v1 (ponawialnie)."""
    raport = zaseeduj_produkty(db)
    week, nowa = zaimportuj_szablon(db, json.loads(_plik("szablon_standard_v1.json")))
    raport.update({"szablon_id": week.id, "szablon_nowy": nowa,
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

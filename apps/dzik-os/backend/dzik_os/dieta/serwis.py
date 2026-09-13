"""Serwis modułu diet: ładowanie szablonów z bazy do kształtu silnika,
cele makro (presety trenera), podgląd, przypisanie (migawka), korekty,
wymiany z walidacją serwerową. Bez I/O poza SQLAlchemy."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import (
    DietAssigned,
    DietProduct,
    DietProfile,
    DietTemplateDay,
    DietTemplateIngredient,
    DietTemplateMeal,
    DietTemplateWeek,
)
from . import silnik as S

MACRO_TOL_MANUAL = 0.03


class BladCelu(ValueError):
    """Niespójny cel makro (ręcznie: 4P+9F+4W ≠ kcal ±3 %) albo brak masy ciała."""


def produkt_silnika(p: DietProduct) -> S.Produkt:
    return S.Produkt(
        name_pl=p.name_pl, category=p.category, substitution_group=p.substitution_group or "",
        kcal_100=p.kcal_100, protein_100=p.protein_100, fat_100=p.fat_100, carbs_100=p.carbs_100,
        cooking_tags=p.cooking_tags or "", allergens=p.allergens or "", diet_exclusions=p.diet_exclusions or "",
        default_scaling=p.default_scaling or "LINIOWY",
    )


def produkty(db: Session) -> tuple[S.Products, dict[str, DietProduct]]:
    """(słownik silnika po nazwie, wiersze po nazwie)."""
    rows = db.query(DietProduct).all()
    return {p.name_pl: produkt_silnika(p) for p in rows}, {p.name_pl: p for p in rows}


def skladnik_dict(i: DietTemplateIngredient, nazwa: str) -> dict[str, Any]:
    d: dict[str, Any] = {"product": nazwa, "grams": i.base_grams, "role": i.macro_role or "NONE",
                         "ingredient_id": i.id, "swappable": bool(i.swappable)}
    if i.scaling_class:
        d["class"] = i.scaling_class
    for k in ("min_factor", "max_factor", "round_step", "unit_g", "unit_step"):
        v = getattr(i, k)
        if v is not None:
            d[k] = v
    if i.group_name:
        d["group"] = i.group_name
    return d


def posilek_dict(db: Session, m: DietTemplateMeal, nazwy: dict[str, str]) -> dict[str, Any]:
    ings = (db.query(DietTemplateIngredient).filter_by(meal_id=m.id)
            .order_by(DietTemplateIngredient.position, DietTemplateIngredient.id).all())
    return {"meal_id": m.id, "name": m.name, "slot": m.slot, "kcal_share": m.kcal_share,
            "flexible": bool(m.flexible), "steps": m.recipe_steps or "",
            "tags": [t for t in (m.tags or "").split(",") if t], "prep_minutes": m.prep_minutes,
            "ingredients": [skladnik_dict(i, nazwy[i.product_id]) for i in ings]}


def szablon_dict(db: Session, week: DietTemplateWeek) -> dict[str, Any]:
    """Odsłona z bazy w kształcie `template_standard_v1.json` (+ identyfikatory)."""
    profil = db.get(DietProfile, week.profile_id)
    nazwy = {p.id: p.name_pl for p in db.query(DietProduct.id, DietProduct.name_pl).all()}
    days = []
    for d in db.query(DietTemplateDay).filter_by(week_id=week.id).order_by(DietTemplateDay.day_no).all():
        meals = (db.query(DietTemplateMeal).filter_by(day_id=d.id)
                 .order_by(DietTemplateMeal.position, DietTemplateMeal.id).all())
        days.append({"day": d.day_no, "day_id": d.id, "meals": [posilek_dict(db, m, nazwy) for m in meals]})
    return {"week_id": week.id, "profile": profil.name if profil else "", "profile_id": week.profile_id,
            "variant": week.variant_no, "name": week.name, "base_kcal": week.base_kcal,
            "kcal_min": week.kcal_min, "kcal_max": week.kcal_max, "status": week.status,
            "macro_pct": [profil.base_p_pct, profil.base_f_pct, profil.base_c_pct] if profil else [0.25, 0.30, 0.45],
            "days": days}


def cel_dnia(kcal: float, macro: dict[str, Any], profil_pct: list[float], body_weight: float | None) -> dict[str, float]:
    """Preset makro trenera → gramy B/T/W. `mode`: profile (z % profilu),
    per_kg (B i T g/kg, reszta W), manual (gramy; suma 4/9/4 musi zgadzać
    się z kcal ±3 %, inaczej BladCelu)."""
    mode = (macro or {}).get("mode", "profile")
    if mode == "profile":
        return S.day_target(kcal, profil_pct)
    if mode == "per_kg":
        if not body_weight or body_weight <= 0:
            raise BladCelu("Preset „na kg masy ciała” wymaga masy ciała klienta.")
        p = float(macro.get("protein_per_kg", 2.0)) * body_weight
        f = float(macro.get("fat_per_kg", 1.0)) * body_weight
        c = (kcal - 4 * p - 9 * f) / 4
        if c < 0:
            raise BladCelu("Białko i tłuszcz na kg przekraczają cel kcal — zmniejsz g/kg albo zwiększ kcal.")
        return {"kcal": kcal, "P": p, "F": f, "C": c}
    if mode == "manual":
        try:
            p, f, c = float(macro["P"]), float(macro["F"]), float(macro["C"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BladCelu("Preset ręczny wymaga gramów P, F i C.") from exc
        e = 4 * p + 9 * f + 4 * c
        if abs(e - kcal) > MACRO_TOL_MANUAL * kcal:
            raise BladCelu(f"Suma kcal z makro ({e:.0f}) różni się od celu ({kcal:.0f}) o więcej niż 3 % — popraw gramy albo kcal.")
        return {"kcal": kcal, "P": p, "F": f, "C": c}
    raise BladCelu(f"Nieznany preset makro: {mode!r}")


def przelicz(db: Session, week: DietTemplateWeek, *, kcal: float, macro: dict[str, Any],
             body_weight: float | None, exclusions: list[str], enforce_groups: bool = False,
             tpl: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pełny wynik silnika dla odsłony + ostrzeżenia (zakres kcal, wykluczenia)."""
    tpl = tpl or szablon_dict(db, week)
    prods, _rows = produkty(db)
    target = cel_dnia(kcal, macro, tpl["macro_pct"], body_weight)
    days = S.scale_week(tpl, kcal, prods, target=target, enforce_groups_=enforce_groups)
    warnings: list[str] = []
    if kcal < tpl["kcal_min"] or kcal > tpl["kcal_max"]:
        warnings.append(f"Cel {kcal:.0f} kcal jest poza zakresem ważności szablonu "
                        f"({tpl['kcal_min']}–{tpl['kcal_max']} kcal) — wynik może wymagać ręcznej korekty.")
    wykl = [x for x in exclusions if x]
    konflikty = sorted({i["product"] for d in tpl["days"] for m in d["meals"] for i in m["ingredients"]
                        if _wykluczony(prods[i["product"]], wykl)})
    if konflikty:
        warnings.append("Składniki objęte wykluczeniami klienta (do wymiany): " + ", ".join(konflikty))
    return {"week_id": week.id, "target": target, "kcal": kcal, "days": [dzien_out(d) for d in days],
            "warnings": warnings, "conflicts": konflikty,
            "summary": {"days_ok": sum(1 for d in days if d["status"] == "OK"), "days": len(days),
                        "meals_flagged": sum(1 for d in days for m in d["meals"] if m["status"] != "OK"),
                        "meals": sum(len(d["meals"]) for d in days)}}


def _wykluczony(p: S.Produkt, exclusions: list[str]) -> bool:
    return any(x in str(p.diet_exclusions) or x in str(p.allergens) or x == p.name_pl for x in exclusions)


def _r(x: float, nd: int = 1) -> float:
    return round(float(x), nd)


def skladnik_out(i: dict[str, Any]) -> dict[str, Any]:
    out = {"product": i["product"], "grams": _r(i["grams"]), "base_grams": i["base_grams"], "class": i["class"],
           "role": i["role"], "ingredient_id": i.get("ingredient_id"), "swappable": bool(i.get("swappable")),
           "min_factor": i["min_factor"], "max_factor": i["max_factor"],
           "factor": _r(i["grams"] / i["base_grams"], 3) if i["base_grams"] else None}
    if i["class"] == "DYSKRETNY":
        out["units"] = i.get("units")
        out["unit_g"] = i["unit_g"]
    return out


def posilek_out(m: dict[str, Any]) -> dict[str, Any]:
    return {"meal_id": m.get("meal_id"), "name": m["name"], "slot": m["slot"], "status": m["status"],
            "macros": {k: _r(v) for k, v in m["macros"].items()},
            "target": {k: _r(v) for k, v in m["target"].items()},
            "deviation": {k: _r(v) for k, v in m["deviation"].items()}, "k": _r(m["k"], 3),
            "steps": m.get("steps", ""), "tags": m.get("tags", []), "flexible": m.get("flexible", False),
            "kcal_share": m.get("kcal_share"), "ingredients": [skladnik_out(i) for i in m["ingredients"]]}


def dzien_out(d: dict[str, Any]) -> dict[str, Any]:
    return {"day": d["day"], "status": d["status"], "macros": {k: _r(v) for k, v in d["macros"].items()},
            "target": {k: _r(v) for k, v in d["target"].items()},
            "deviation": {k: _r(v) for k, v in d["deviation"].items()}, "meals": [posilek_out(m) for m in d["meals"]]}


# --- migawka, korekty, wymiany ---------------------------------------------------------------


def migawka(db: Session, a: DietAssigned) -> dict[str, Any]:
    return json.loads(a.computed_plan_json)


def overrides(a: DietAssigned) -> dict[str, Any]:
    try:
        o = json.loads(a.overrides_json or "{}")
    except ValueError:
        o = {}
    o.setdefault("ingredients", {})   # klucz "day:meal_id:ingredient_id" → {product, grams, by, at}
    o.setdefault("meals", {})         # klucz "day:meal_id" → {replaced_by_meal_id, by, at}
    o.setdefault("accepted_warnings", False)
    return o


def _klucz(day: int, meal_id: str, ingredient_id: str) -> str:
    return f"{day}:{meal_id}:{ingredient_id}"


def plan_z_korektami(db: Session, a: DietAssigned) -> dict[str, Any]:
    """Migawka z nałożonymi korektami/wymianami i przeliczonymi makro
    (gramatury z overrides, produkty z bazy — nic nie jest liczone w
    przeglądarce)."""
    plan = migawka(db, a)
    o = overrides(a)
    prods, _rows = produkty(db)
    for d in plan["days"]:
        for m in d["meals"]:
            for i in m["ingredients"]:
                ov = o["ingredients"].get(_klucz(d["day"], m["meal_id"], i["ingredient_id"]))
                if ov:
                    i["product"] = ov["product"]
                    i["grams"] = ov["grams"]
                    i["override"] = {k: ov[k] for k in ("by", "at", "kind") if k in ov}
                    if i.get("units") is not None and i.get("unit_g"):
                        i["units"] = round(i["grams"] / i["unit_g"], 2)
            przelicz_posilek_out(m, prods)
        d["macros"] = {k: _r(sum(m["macros"][k] for m in d["meals"])) for k in ("kcal", "P", "F", "C")}
        ok, dev = S.check(d["macros"], d["target"], S.TOL_DAY)
        d["deviation"] = {k: _r(v) for k, v in dev.items()}
        d["status"] = "OK" if ok else "POZA_TOLERANCJĄ"
    plan["overrides"] = o
    return plan


def przelicz_posilek_out(m: dict[str, Any], prods: S.Products) -> None:
    ings = [{"product": i["product"], "grams": i["grams"]} for i in m["ingredients"]]
    cur = S.sum_macros(ings, prods)
    ok, dev = S.check(cur, m["target"], S.TOL_MEAL)
    m["macros"] = {k: _r(v) for k, v in cur.items()}
    m["deviation"] = {k: _r(v) for k, v in dev.items()}
    if not ok:
        m["status"] = "OSTRZEŻENIE" if m.get("status") != "POZA_ZAKRESEM" else m["status"]
    else:
        m["status"] = "OK"


def posilek_silnika(m_out: dict[str, Any]) -> dict[str, Any]:
    """Posiłek z migawki (po korektach) w kształcie wyniku `scale_meal` —
    do `swap_candidates` i walidacji wymiany."""
    ings = []
    for i in m_out["ingredients"]:
        ings.append({"product": i["product"], "grams": i["grams"], "role": i["role"], "class": i["class"],
                     "round_step": S.CLASS_DEFAULTS.get(i["class"], {}).get("round_step") or 5,
                     "base_grams": i["base_grams"], "min_factor": i["min_factor"], "max_factor": i["max_factor"]})
    return {"ingredients": ings, "target": m_out["target"], "name": m_out["name"], "slot": m_out["slot"]}


def kandydaci_wymiany(db: Session, a: DietAssigned, day: int, meal_id: str, ingredient_id: str,
                      *, n: int = 3) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    plan = plan_z_korektami(db, a)
    d = next((x for x in plan["days"] if x["day"] == day), None)
    m = next((x for x in (d["meals"] if d else []) if x["meal_id"] == meal_id), None)
    if m is None:
        raise KeyError("posiłek")
    idx = next((i for i, x in enumerate(m["ingredients"]) if x["ingredient_id"] == ingredient_id), None)
    if idx is None:
        raise KeyError("składnik")
    prods, rows = produkty(db)
    excl = json.loads(a.exclusions_json or "[]")
    cands = S.swap_candidates(posilek_silnika(m), idx, prods, exclusions=tuple(excl), n=n)
    out = [{"product": c["product"], "product_id": rows[c["product"]].id, "grams": _r(c["grams"]),
            "macros": {k: _r(v) for k, v in c["macros"].items()}} for c in cands]
    return out, m, idx

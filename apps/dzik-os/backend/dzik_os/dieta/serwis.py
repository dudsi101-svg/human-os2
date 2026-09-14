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
    new_id,
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
            "allergens": [a for a in (m.allergens or "").split(",") if a],
            "ingredients": [skladnik_dict(i, nazwy[i.product_id]) for i in ings]}


def notatki_odslony(week: DietTemplateWeek | None) -> dict[str, Any]:
    """Notatki biblioteki (audyt 14.09): suplementacja, sód, pochodzenie odsłony.
    Treść informacyjna — nie wchodzi do migawki planu, czytana z odsłony."""
    if week is None:
        return {"derived_from": None, "supplements_note": [], "sodium_note": ""}
    try:
        supl = json.loads(week.supplements_note or "[]")
    except ValueError:
        supl = [week.supplements_note]
    return {"derived_from": week.derived_from or None,
            "supplements_note": [str(x) for x in (supl if isinstance(supl, list) else [supl]) if x],
            "sodium_note": week.sodium_note or ""}


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


def cel_dnia(kcal: float, macro: dict[str, Any], profil_pct: list[float], body_weight: float | None,
             warnings: list[str] | None = None) -> dict[str, float]:
    """Preset makro trenera → gramy B/T/W. `mode`: profile (z % profilu),
    per_kg (B i T g/kg, reszta W), manual (gramy). Przy presecie ręcznym
    suma 4/9/4 gramów ma pierwszeństwo przed wpisaną kalorycznością:
    gdy różnią się o więcej niż 3 %, silnik OSTRZEGA (instrukcja §6.4),
    a cel kcal wynika z makro — inaczej posiłki nie miałyby spójnego celu."""
    mode = (macro or {}).get("mode", "profile")
    if mode == "profile":
        return S.day_target(kcal, profil_pct)
    if mode == "per_kg":
        if not body_weight or body_weight <= 0:
            raise BladCelu("Preset „na kg masy ciała” wymaga masy ciała klienta.")
        p = float(macro.get("protein_per_kg") or 2.0) * body_weight
        f = float(macro.get("fat_per_kg") or 1.0) * body_weight
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
        if e <= 0:
            raise BladCelu("Preset ręczny wymaga dodatnich gramów makro.")
        if abs(e - kcal) > MACRO_TOL_MANUAL * kcal:
            if warnings is not None:
                warnings.append(f"Suma kcal z makro ({e:.0f}) różni się od wpisanego celu ({kcal:.0f}) o więcej "
                                f"niż 3 % — silnik liczy tydzień na {e:.0f} kcal wynikające z gramów makro.")
            return {"kcal": e, "P": p, "F": f, "C": c}
        return {"kcal": kcal, "P": p, "F": f, "C": c}
    raise BladCelu(f"Nieznany preset makro: {mode!r}")


def oczysc_wykluczenia(exclusions: list[str] | tuple[str, ...] | None) -> list[str]:
    """Wykluczenia z API/migawki bez pustych i zdublowanych wpisów — pusty
    napis pasowałby do KAŻDEGO produktu (`"" in "..."`)."""
    out: list[str] = []
    for x in exclusions or ():
        x = str(x).strip()
        if x and x not in out:
            out.append(x)
    return out


def przelicz(db: Session, week: DietTemplateWeek, *, kcal: float, macro: dict[str, Any],
             body_weight: float | None, exclusions: list[str], enforce_groups: bool = False,
             tpl: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pełny wynik silnika dla odsłony + ostrzeżenia (zakres kcal, wykluczenia)."""
    tpl = tpl or szablon_dict(db, week)
    prods, _rows = produkty(db)
    warnings: list[str] = []
    target = cel_dnia(kcal, macro, tpl["macro_pct"], body_weight, warnings)
    kcal = target["kcal"]
    days = S.scale_week(tpl, kcal, prods, target=target, enforce_groups_=enforce_groups)
    if kcal < tpl["kcal_min"] or kcal > tpl["kcal_max"]:
        warnings.append(f"Cel {kcal:.0f} kcal jest poza zakresem ważności szablonu "
                        f"({tpl['kcal_min']}–{tpl['kcal_max']} kcal) — wynik może wymagać ręcznej korekty.")
    wykl = oczysc_wykluczenia(exclusions)
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
        out["unit_step"] = i.get("unit_step")
    elif i["class"] != "STAŁY":
        out["round_step"] = i.get("round_step")
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
    zastosuj_korekty(plan, o, prods)
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
                     "round_step": i.get("round_step") or S.CLASS_DEFAULTS.get(i["class"], {}).get("round_step") or 5,
                     "unit_g": i.get("unit_g"), "unit_step": i.get("unit_step"),
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
    excl = oczysc_wykluczenia(json.loads(a.exclusions_json or "[]"))
    # Silnik filtruje alergeny/diety; „nielubiane” (wykluczenie po nazwie
    # produktu) odsiewamy tu — przed cięciem do n, żeby nie tracić miejsc.
    cands = [c for c in S.swap_candidates(posilek_silnika(m), idx, prods, exclusions=tuple(excl), n=len(prods))
             if not _wykluczony(prods[c["product"]], excl)][:n]
    out = [{"product": c["product"], "product_id": rows[c["product"]].id, "grams": _r(c["grams"]),
            "macros": {k: _r(v) for k, v in c["macros"].items()}} for c in cands]
    return out, m, idx


# --- korekty w podglądzie, zamiana posiłku z biblioteki, przypisanie -------------------------


def klucze_skladnikow(plan: dict[str, Any]) -> set[str]:
    """Wszystkie klucze „day:meal_id:ingredient_id” występujące w planie —
    korekta pod nieistniejący klucz jest błędem wejścia, nie martwym wpisem."""
    return {_klucz(d["day"], m["meal_id"], i["ingredient_id"])
            for d in plan["days"] for m in d["meals"] for i in m["ingredients"]}


def przelicz_podsumowanie(plan: dict[str, Any]) -> None:
    plan["summary"] = {"days_ok": sum(1 for d in plan["days"] if d["status"] == "OK"), "days": len(plan["days"]),
                       "meals_flagged": sum(1 for d in plan["days"] for m in d["meals"] if m["status"] != "OK"),
                       "meals": sum(len(d["meals"]) for d in plan["days"])}


def zastosuj_korekty(plan: dict[str, Any], o: dict[str, Any], prods: S.Products) -> dict[str, Any]:
    """Nakłada korekty gramatur/produktów (`o["ingredients"]`) na wynik silnika
    (kształt `dzien_out`) i przelicza makro, statusy posiłków i dni oraz
    podsumowanie po stronie serwera. Nieznany produkt albo niepoprawna
    gramatura w korekcie = `ValueError` (422), nie 500."""
    for d in plan["days"]:
        zmieniony = False
        for m in d["meals"]:
            dotkniety = False
            for i in m["ingredients"]:
                ov = o.get("ingredients", {}).get(_klucz(d["day"], m["meal_id"], i["ingredient_id"]))
                if not ov:
                    continue
                try:
                    grams = float(ov["grams"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"korekta {i['product']}: gramatura musi być liczbą") from exc
                if not 0 <= grams <= 5000:
                    raise ValueError(f"korekta {i['product']}: gramatura {grams:.0f} g poza zakresem 0–5000 g")
                if ov.get("product"):
                    if ov["product"] not in prods:
                        raise ValueError(f"korekta: nieznany produkt {ov['product']!r}")
                    if ov["product"] != i["product"]:
                        # Inny produkt = inna jednostka praktyczna; „sztuki” starego
                        # produktu przestają mieć sens — klient widzi gramy.
                        i["units"] = None
                        i["unit_g"] = None
                    i["product"] = ov["product"]
                i["grams"] = grams
                i["override"] = {k: ov[k] for k in ("by", "at", "kind") if k in ov}
                if i.get("unit_g"):
                    i["units"] = round(i["grams"] / i["unit_g"], 2)
                if i.get("base_grams"):
                    i["factor"] = _r(i["grams"] / i["base_grams"], 3)
                dotkniety = True
            if dotkniety:
                przelicz_posilek_out(m, prods)
                zmieniony = True
        if zmieniony:
            d["macros"] = {k: _r(sum(m["macros"][k] for m in d["meals"])) for k in ("kcal", "P", "F", "C")}
            ok, dev = S.check(d["macros"], d["target"], S.TOL_DAY)
            d["deviation"] = {k: _r(v) for k, v in dev.items()}
            d["status"] = "OK" if ok else "POZA_TOLERANCJĄ"
    if "summary" in plan:
        przelicz_podsumowanie(plan)
    return plan


def posilki_biblioteki(db: Session, week: DietTemplateWeek, slot: str | None = None) -> list[dict[str, Any]]:
    """Posiłki tego samego profilu (opublikowane odsłony + ta odsłona) — do
    ręcznej zamiany posiłku w tym samym slocie."""
    weeks = (db.query(DietTemplateWeek)
             .filter(DietTemplateWeek.profile_id == week.profile_id)
             .filter((DietTemplateWeek.status == "PUBLISHED") | (DietTemplateWeek.id == week.id)).all())
    nazwy = {p.id: p.name_pl for p in db.query(DietProduct.id, DietProduct.name_pl).all()}
    out = []
    for w in weeks:
        for d in db.query(DietTemplateDay).filter_by(week_id=w.id).order_by(DietTemplateDay.day_no).all():
            for m in db.query(DietTemplateMeal).filter_by(day_id=d.id).order_by(DietTemplateMeal.position).all():
                if slot and m.slot != slot:
                    continue
                pd = posilek_dict(db, m, nazwy)
                pd.update({"week_id": w.id, "variant_no": w.variant_no, "day_no": d.day_no})
                out.append(pd)
    return out


def posilek_zastepczy(db: Session, *, profile_id: str, week_id: str, slot: str, nowy_id: str,
                      nazwy: dict[str, str]) -> dict[str, Any]:
    """Posiłek z biblioteki do ręcznej zamiany: ten sam slot, ten sam profil,
    z opublikowanej odsłony (albo z tej samej odsłony) i z co najmniej jednym
    składnikiem — inaczej `ValueError` (422). Bez tego trener mógłby wstawić
    klientowi posiłek ze szkicu, który nie przeszedł sweepu, albo z obcego
    profilu o innym makro."""
    nowy = db.get(DietTemplateMeal, nowy_id)
    if nowy is None:
        raise ValueError(f"Posiłek zastępczy {nowy_id} nie istnieje.")
    if nowy.slot != slot:
        raise ValueError(f"Posiłek zastępczy „{nowy.name}” ma slot {nowy.slot}, a zamieniany posiłek — {slot}.")
    dzien = db.get(DietTemplateDay, nowy.day_id)
    week = db.get(DietTemplateWeek, dzien.week_id) if dzien else None
    if week is None or week.profile_id != profile_id:
        raise ValueError(f"Posiłek zastępczy „{nowy.name}” pochodzi z innego profilu diety.")
    if week.status != "PUBLISHED" and week.id != week_id:
        raise ValueError(f"Posiłek zastępczy „{nowy.name}” pochodzi z nieopublikowanej odsłony.")
    nd = posilek_dict(db, nowy, nazwy)
    if not nd["ingredients"]:
        raise ValueError(f"Posiłek zastępczy „{nowy.name}” nie ma składników.")
    return nd


def szablon_z_zamianami(db: Session, tpl: dict[str, Any], zamiany: dict[str, str]) -> dict[str, Any]:
    """`zamiany`: "day:meal_id" → meal_id z biblioteki (ten sam slot). Zamieniony
    posiłek zachowuje udział kcal i flagę elastyczności slotu."""
    if not zamiany:
        return tpl
    nazwy = {p.id: p.name_pl for p in db.query(DietProduct.id, DietProduct.name_pl).all()}
    tpl = json.loads(json.dumps(tpl))
    znane = {f"{d['day']}:{m['meal_id']}" for d in tpl["days"] for m in d["meals"]}
    obce = sorted(set(zamiany) - znane)
    if obce:
        raise ValueError("Zamiana posiłku wskazuje nieistniejący posiłek szablonu: " + ", ".join(obce))
    for d in tpl["days"]:
        for idx, m in enumerate(d["meals"]):
            nowy_id = zamiany.get(f"{d['day']}:{m['meal_id']}")
            if not nowy_id:
                continue
            nd = posilek_zastepczy(db, profile_id=tpl["profile_id"], week_id=tpl["week_id"], slot=m["slot"],
                                   nowy_id=nowy_id, nazwy=nazwy)
            nd["kcal_share"] = m["kcal_share"]
            nd["flexible"] = m["flexible"]
            nd["replaced_from"] = m["meal_id"]
            d["meals"][idx] = nd
    return tpl


def zamien_posilek_w_migawce(db: Session, a: DietAssigned, *, day: int, meal_id: str, nowy_id: str) -> dict[str, Any]:
    """Zamiana posiłku w PRZYPISANEJ diecie: posiłek z biblioteki skalowany
    do celu posiłku z migawki (tak jak zrobił to silnik), zapis do migawki.
    Działa też dla slotu zamienianego po raz kolejny — punktem odniesienia
    jest migawka, nie oryginalny szablon. Zwraca przeliczony dzień."""
    plan = migawka(db, a)
    d = next((x for x in plan["days"] if x["day"] == day), None)
    m_idx = next((i for i, x in enumerate(d["meals"]) if x["meal_id"] == meal_id), None) if d else None
    if d is None or m_idx is None:
        raise KeyError("posiłek")
    week = db.get(DietTemplateWeek, a.week_id)
    if week is None:
        raise ValueError("Odsłona przypisanej diety nie istnieje.")
    stary = d["meals"][m_idx]
    nazwy = {p.id: p.name_pl for p in db.query(DietProduct.id, DietProduct.name_pl).all()}
    nd = posilek_zastepczy(db, profile_id=week.profile_id, week_id=week.id, slot=stary["slot"], nowy_id=nowy_id,
                           nazwy=nazwy)
    nd["kcal_share"] = stary.get("kcal_share")
    nd["flexible"] = stary.get("flexible", False)
    prods, _ = produkty(db)
    wynik = S.scale_meal(nd, stary["target"], prods)
    d["meals"][m_idx] = posilek_out(wynik)
    d["meals"][m_idx]["replaced_from"] = stary.get("replaced_from") or meal_id
    d["macros"] = {k: _r(sum(mm["macros"][k] for mm in d["meals"])) for k in ("kcal", "P", "F", "C")}
    ok, dev = S.check(d["macros"], d["target"], S.TOL_DAY)
    d["deviation"] = {k: _r(v) for k, v in dev.items()}
    d["status"] = "OK" if ok else "POZA_TOLERANCJĄ"
    if "summary" in plan:
        przelicz_podsumowanie(plan)
    # Stare korekty tego slotu dotyczyły składników, których już nie ma.
    o = overrides(a)
    prefix = f"{day}:{meal_id}:"
    for k in [k for k in o["ingredients"] if k.startswith(prefix)]:
        del o["ingredients"][k]
    a.overrides_json = json.dumps(o, ensure_ascii=False)
    a.computed_plan_json = json.dumps(plan, ensure_ascii=False)
    return d


def przypisz(db: Session, *, client_id: str, coach_id: str, week: DietTemplateWeek, plan: dict[str, Any],
             kcal: float, macro: dict[str, Any], body_weight: float | None, exclusions: list[str],
             overrides_: dict[str, Any]) -> DietAssigned:
    """Nowy wiersz z migawką; poprzednia aktywna dieta klienta → ARCHIVED."""
    poprzednie = db.query(DietAssigned).filter_by(client_id=client_id, status="ACTIVE").all()
    wersja = 1 + max([p.version for p in db.query(DietAssigned).filter_by(client_id=client_id).all()] or [0])
    for p in poprzednie:
        p.status = "ARCHIVED"
    a = DietAssigned(
        id=new_id("DAS"), client_id=client_id, coach_id=coach_id, week_id=week.id, target_kcal=round(kcal),
        target_p=plan["target"]["P"], target_f=plan["target"]["F"], target_c=plan["target"]["C"],
        body_weight=body_weight, macro_mode=(macro or {}).get("mode", "profile"),
        exclusions_json=json.dumps(oczysc_wykluczenia(exclusions), ensure_ascii=False),
        computed_plan_json=json.dumps({k: plan[k] for k in ("week_id", "target", "kcal", "days", "warnings", "summary")},
                                      ensure_ascii=False),
        overrides_json=json.dumps(overrides_, ensure_ascii=False), version=wersja,
    )
    db.add(a)
    db.flush()
    return a


def dieta_out(db: Session, a: DietAssigned, *, z_korektami: bool = True) -> dict[str, Any]:
    week = db.get(DietTemplateWeek, a.week_id)
    profil = db.get(DietProfile, week.profile_id) if week else None
    plan = plan_z_korektami(db, a) if z_korektami else migawka(db, a)
    return {"id": a.id, "client_id": a.client_id, "coach_id": a.coach_id, "week_id": a.week_id,
            "week_name": week.name if week else "", "profile": profil.name if profil else "",
            "target": {"kcal": a.target_kcal, "P": _r(a.target_p), "F": _r(a.target_f), "C": _r(a.target_c)},
            "macro_mode": a.macro_mode, "body_weight": a.body_weight,
            "exclusions": json.loads(a.exclusions_json or "[]"), "status": a.status, "version": a.version,
            "swaps_enabled": bool(a.swaps_enabled), "created_at": a.created_at, "updated_at": a.updated_at,
            **notatki_odslony(week), "plan": plan}

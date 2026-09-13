"""Szablony diet ze skalowaniem (0.60.0) — API `/api/diet/*`.

Trener: profile → odsłona → `preview` (bez zapisu, z korektami i zamianą
posiłku) → `assign` (migawka; blokada przy dniu POZA_TOLERANCJĄ, chyba że
`accept_warnings`) → `PATCH assigned/{id}` (korekta gramatur / zamiana
posiłku / blokada wymian). Klient: `assigned/current`, kandydaci wymiany,
zapis wymiany (gramatura liczona i walidowana po stronie serwera).
Admin/dietetyk (rola COACH lub ADMIN): CRUD profili, odsłon, posiłków,
składników, sweep 1400–3200, publikacja ≥ 95 % dni OK, import JSON.

Cały moduł za flagą `DZIK_DIET_TEMPLATES_ENABLED` (404 gdy wyłączony).
Uprawnienia po stronie serwera: trener tylko własny klient z aktywną
relacją i zgodą na dane żywieniowe (`resolve_client_access`); klient tylko
własna dieta; cudza dieta = 404 z wpisem odmowy w audycie.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..authz import DOMAIN_NUTRITION, resolve_client_access
from ..config import settings
from ..db import get_db
from ..dieta import seed as dieta_seed
from ..dieta import serwis
from ..dieta import silnik as S
from ..hos_bridge import record_event
from ..models import (
    DietAssigned,
    DietProduct,
    DietProfile,
    DietSwapEvent,
    DietTemplateDay,
    DietTemplateIngredient,
    DietTemplateMeal,
    DietTemplateWeek,
    User,
    new_id,
    now_iso,
)
from ..security import active_roles, current_user, require_role

router = APIRouter(prefix="/api/diet", tags=["diet"])


def wymagaj_modulu() -> None:
    if not settings.diet_templates_enabled:
        raise HTTPException(status_code=404, detail="Moduł szablonów diet jest wyłączony")


def _edytor(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    """Panel szablonów: trener albo administrator (szablony nie są danymi klientów)."""
    roles = active_roles(db, user.id)
    if "COACH" not in roles and "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Brak wymaganej roli")
    return user


def _konflikt(kod: str, detail: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": detail, "code": kod, **extra})


def _week(db: Session, week_id: str, *, published_only: bool = False) -> DietTemplateWeek:
    w = db.get(DietTemplateWeek, week_id)
    if w is None or (published_only and w.status != "PUBLISHED"):
        raise HTTPException(status_code=404, detail="Nie znaleziono odsłony")
    return w


def _dieta(db: Session, user: User, diet_id: str) -> DietAssigned:
    """Klient-właściciel albo trener z dostępem do klienta; inaczej 404 z audytem."""
    a = db.get(DietAssigned, diet_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if user.id != a.client_id:
        resolve_client_access(db, user, a.client_id, domain=DOMAIN_NUTRITION)
    return a


# --- wejścia ---------------------------------------------------------------------------


class MacroIn(BaseModel):
    mode: str = Field(default="profile", pattern="^(profile|per_kg|manual)$")
    P: float | None = Field(default=None, ge=0, le=1000)
    F: float | None = Field(default=None, ge=0, le=1000)
    C: float | None = Field(default=None, ge=0, le=2000)
    protein_per_kg: float | None = Field(default=None, ge=0, le=6)
    fat_per_kg: float | None = Field(default=None, ge=0, le=4)


class PreviewIn(BaseModel):
    kcal: float = Field(ge=500, le=8000)
    macro: MacroIn = Field(default_factory=MacroIn)
    body_weight: float | None = Field(default=None, ge=20, le=400)
    exclusions: list[str] = Field(default_factory=list, max_length=60)
    enforce_groups: bool = False
    # korekty trenera w podglądzie: "day:meal_id:ingredient_id" → {grams}
    overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # zamiany posiłków: "day:meal_id" → meal_id z biblioteki (ten sam slot)
    meal_replacements: dict[str, str] = Field(default_factory=dict)


class AssignIn(PreviewIn):
    client_id: str = Field(min_length=1, max_length=40)
    week_id: str = Field(min_length=1, max_length=40)
    accept_warnings: bool = False
    swaps_enabled: bool = True


class SwapIn(BaseModel):
    day: int = Field(ge=1, le=7)
    meal_id: str
    ingredient_id: str
    to_product_id: str
    grams: float | None = Field(default=None, gt=0, le=5000)


class PatchIn(BaseModel):
    day: int | None = Field(default=None, ge=1, le=7)
    meal_id: str | None = None
    ingredient_id: str | None = None
    grams: float | None = Field(default=None, ge=0, le=5000)
    replace_with_meal_id: str | None = None
    swaps_enabled: bool | None = None


# --- profile i szablony ---------------------------------------------------------------------


def _profil_out(db: Session, p: DietProfile) -> dict[str, Any]:
    weeks = db.query(DietTemplateWeek).filter_by(profile_id=p.id).order_by(DietTemplateWeek.variant_no).all()
    return {"id": p.id, "name": p.name, "description": p.description,
            "base_macro_pct": {"P": p.base_p_pct, "F": p.base_f_pct, "C": p.base_c_pct},
            "diet_tags": [t for t in (p.diet_tags or "").split(",") if t],
            "published_weeks": sum(1 for w in weeks if w.status == "PUBLISHED"),
            "weeks": [{"id": w.id, "variant_no": w.variant_no, "name": w.name, "status": w.status,
                       "base_kcal": w.base_kcal, "kcal_min": w.kcal_min, "kcal_max": w.kcal_max} for w in weeks]}


@router.get("/profiles", dependencies=[Depends(wymagaj_modulu)])
def profiles(user: User = Depends(_edytor), db: Session = Depends(get_db)):
    """Lista profili z liczbą opublikowanych odsłon (trener widzi tylko
    opublikowane odsłony; edytor — wszystkie)."""
    out = [_profil_out(db, p) for p in db.query(DietProfile).order_by(DietProfile.name).all()]
    return {"profiles": out, "enabled": True}


def _szablon_podglad(db: Session, w: DietTemplateWeek) -> dict[str, Any]:
    tpl = serwis.szablon_dict(db, w)
    return {"week_id": w.id, "profile": tpl["profile"], "profile_id": w.profile_id, "variant_no": w.variant_no,
            "name": w.name, "status": w.status, "base_kcal": w.base_kcal, "kcal_min": w.kcal_min,
            "kcal_max": w.kcal_max, "macro_pct": tpl["macro_pct"],
            "days": [{"day": d["day"], "meals": [{"meal_id": m["meal_id"], "name": m["name"], "slot": m["slot"],
                                                  "kcal_share": m["kcal_share"], "flexible": m["flexible"],
                                                  "tags": m["tags"], "ingredients": len(m["ingredients"])}
                                                 for m in d["meals"]]} for d in tpl["days"]]}


@router.get("/templates/{week_id}", dependencies=[Depends(wymagaj_modulu)])
def template(week_id: str, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    """Podgląd odsłony: nazwy posiłków, sloty, tagi — bez gramatur."""
    return _szablon_podglad(db, _week(db, week_id))


@router.get("/templates/{week_id}/meals", dependencies=[Depends(wymagaj_modulu)])
def library_meals(week_id: str, slot: str | None = Query(default=None), user: User = Depends(_edytor),
                  db: Session = Depends(get_db)):
    """Biblioteka posiłków tego profilu (ten sam slot) do ręcznej zamiany."""
    w = _week(db, week_id)
    return {"meals": [{k: m[k] for k in ("meal_id", "name", "slot", "tags", "week_id", "variant_no", "day_no")}
                      | {"ingredients": [i["product"] for i in m["ingredients"]]}
                      for m in serwis.posilki_biblioteki(db, w, slot)]}


def _podglad(db: Session, w: DietTemplateWeek, body: PreviewIn) -> dict[str, Any]:
    try:
        tpl = serwis.szablon_z_zamianami(db, serwis.szablon_dict(db, w), body.meal_replacements)
        plan = serwis.przelicz(db, w, kcal=body.kcal, macro=body.macro.model_dump(), body_weight=body.body_weight,
                               exclusions=body.exclusions, enforce_groups=body.enforce_groups, tpl=tpl)
    except serwis.BladCelu as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    if body.overrides:
        prods, _ = serwis.produkty(db)
        o = {"ingredients": {k: {"grams": float(v["grams"]), **({"product": v["product"]} if v.get("product") else {}),
                                 "kind": "coach"} for k, v in body.overrides.items() if "grams" in v}}
        serwis.zastosuj_korekty(plan, o, prods)
        plan["summary"]["days_ok"] = sum(1 for d in plan["days"] if d["status"] == "OK")
        plan["summary"]["meals_flagged"] = sum(1 for d in plan["days"] for m in d["meals"] if m["status"] != "OK")
    return plan


@router.post("/templates/{week_id}/preview", dependencies=[Depends(wymagaj_modulu)])
def preview(week_id: str, body: PreviewIn, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    """Pełny wynik silnika ze statusami — bez zapisu."""
    return _podglad(db, _week(db, week_id), body)


# --- przypisanie ----------------------------------------------------------------------------


@router.post("/assign", status_code=201, dependencies=[Depends(wymagaj_modulu)])
def assign(body: AssignIn, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Tylko trener, tylko własny klient. Migawka wyniku + overrides."""
    resolve_client_access(db, coach, body.client_id, action="write", domain=DOMAIN_NUTRITION)
    w = _week(db, body.week_id, published_only=True)
    plan = _podglad(db, w, body)
    zle = [d["day"] for d in plan["days"] if d["status"] != "OK"]
    if zle and not body.accept_warnings:
        return _konflikt("DAY_OUT_OF_TOLERANCE",
                         "Dni poza tolerancją: " + ", ".join(map(str, zle))
                         + ". Popraw gramatury albo zaznacz „przypisz mimo ostrzeżeń”.", days=zle)
    o = {"ingredients": {k: {"grams": float(v["grams"]), **({"product": v["product"]} if v.get("product") else {}),
                             "by": coach.id, "at": now_iso(), "kind": "coach"}
                         for k, v in body.overrides.items() if "grams" in v},
         "meals": {k: {"replaced_by_meal_id": v, "by": coach.id, "at": now_iso()} for k, v in body.meal_replacements.items()},
         "accepted_warnings": bool(zle and body.accept_warnings), "accepted_days": zle if body.accept_warnings else []}
    a = serwis.przypisz(db, client_id=body.client_id, coach_id=coach.id, week=w, plan=plan, kcal=body.kcal,
                        macro=body.macro.model_dump(), body_weight=body.body_weight, exclusions=body.exclusions,
                        overrides_=o)
    a.swaps_enabled = body.swaps_enabled
    record_event(
        db, action="DIET_TEMPLATE_ASSIGNED", actor_id=coach.id, subject_ids=[body.client_id],
        payload={"assigned_diet_id": a.id, "week_id": w.id, "version": a.version, "kcal": a.target_kcal,
                 "days_ok": plan["summary"]["days_ok"], "accepted_warnings": o["accepted_warnings"]},
        summary=f"Przypisano dietę z szablonu (v{a.version}, {a.target_kcal} kcal)",
    )
    db.commit()
    return serwis.dieta_out(db, a)


@router.get("/assigned/current", dependencies=[Depends(wymagaj_modulu)])
def assigned_current(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Klient: własna aktualna dieta (migawka + korekty i wymiany)."""
    a = (db.query(DietAssigned).filter_by(client_id=user.id, status="ACTIVE")
         .order_by(DietAssigned.version.desc()).first())
    if a is None:
        return {"assigned": None}
    return {"assigned": serwis.dieta_out(db, a)}


@router.get("/clients/{client_id}/current", dependencies=[Depends(wymagaj_modulu)])
def client_current(client_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Trener (z dostępem) albo sam klient: aktualna dieta + historia wymian i wersji."""
    resolve_client_access(db, user, client_id, domain=DOMAIN_NUTRITION)
    a = (db.query(DietAssigned).filter_by(client_id=client_id, status="ACTIVE")
         .order_by(DietAssigned.version.desc()).first())
    historia = db.query(DietAssigned).filter_by(client_id=client_id).order_by(DietAssigned.version.desc()).all()
    swaps = (db.query(DietSwapEvent).filter(DietSwapEvent.assigned_diet_id.in_([h.id for h in historia] or ["-"]))
             .order_by(DietSwapEvent.created_at.desc()).all())
    nazwy = {p.id: p.name_pl for p in db.query(DietProduct.id, DietProduct.name_pl).all()}
    return {"assigned": serwis.dieta_out(db, a) if a else None,
            "history": [{"id": h.id, "version": h.version, "status": h.status, "kcal": h.target_kcal,
                         "created_at": h.created_at, "week_id": h.week_id} for h in historia],
            "swap_events": [{"id": s.id, "assigned_diet_id": s.assigned_diet_id, "day": s.day_no, "meal_id": s.meal_id,
                             "from": nazwy.get(s.from_product_id, s.from_product_id),
                             "to": nazwy.get(s.to_product_id, s.to_product_id), "from_grams": s.from_grams,
                             "to_grams": s.to_grams, "created_at": s.created_at, "actor_id": s.actor_id} for s in swaps]}


# --- wymiany ----------------------------------------------------------------------------------


@router.get("/assigned/{diet_id}/swaps", dependencies=[Depends(wymagaj_modulu)])
def swap_candidates(diet_id: str, day: int = Query(ge=1, le=7), meal: str = Query(min_length=1),
                    ingredient: str = Query(min_length=1), user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    """1–3 kandydatów z tej samej grupy zamienników; pusta lista = „Brak
    bezpiecznego zamiennika, napisz do trenera”."""
    a = _dieta(db, user, diet_id)
    try:
        cands, m, idx = serwis.kandydaci_wymiany(db, a, day, meal, ingredient)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono: {e}") from None
    ing = m["ingredients"][idx]
    blokada = None
    if not a.swaps_enabled:
        blokada = "Trener wyłączył wymiany w tej diecie."
    elif not ing.get("swappable"):
        blokada = "Ten składnik nie podlega wymianie."
    return {"candidates": [] if blokada else cands, "blocked": blokada, "ingredient": ing,
            "meal": {"meal_id": m["meal_id"], "name": m["name"], "target": m["target"]}}


@router.post("/assigned/{diet_id}/swaps", status_code=201, dependencies=[Depends(wymagaj_modulu)])
def swap(diet_id: str, body: SwapIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Zapis wymiany: produkt musi być kandydatem silnika; gramatura z klienta
    (jeśli podana) jest walidowana tolerancją posiłku po stronie serwera."""
    a = _dieta(db, user, diet_id)
    if not a.swaps_enabled:
        raise HTTPException(status_code=409, detail="Trener wyłączył wymiany w tej diecie.")
    try:
        cands, m, idx = serwis.kandydaci_wymiany(db, a, body.day, body.meal_id, body.ingredient_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono: {e}") from None
    ing = m["ingredients"][idx]
    if not ing.get("swappable"):
        raise HTTPException(status_code=409, detail="Ten składnik nie podlega wymianie.")
    kand = next((c for c in cands if c["product_id"] == body.to_product_id), None)
    if kand is None:
        raise HTTPException(status_code=422, detail="Ten produkt nie jest bezpiecznym zamiennikiem w tym posiłku.")
    grams = float(body.grams) if body.grams is not None else kand["grams"]
    prods, rows = serwis.produkty(db)
    ings = [{"product": x["product"], "grams": x["grams"]} for x in m["ingredients"]]
    ings[idx] = {"product": kand["product"], "grams": grams}
    cur = S.sum_macros(ings, prods)
    ok, dev = S.check(cur, m["target"], S.TOL_MEAL)
    if not ok:
        raise HTTPException(status_code=422, detail=f"Gramatura {grams:.0f} g wyprowadza posiłek poza tolerancję "
                                                    f"(Δkcal {dev['kcal']:+.0f}); dopuszczalna: {kand['grams']:.0f} g.")
    o = serwis.overrides(a)
    o["ingredients"][serwis._klucz(body.day, body.meal_id, body.ingredient_id)] = {
        "product": kand["product"], "grams": grams, "by": user.id, "at": now_iso(),
        "kind": "swap" if user.id == a.client_id else "coach"}
    a.overrides_json = json.dumps(o, ensure_ascii=False)
    a.updated_at = now_iso()
    from_id = rows[ing["product"]].id if ing["product"] in rows else ing["product"]
    ev = DietSwapEvent(id=new_id("DSE"), assigned_diet_id=a.id, day_no=body.day, meal_id=body.meal_id,
                       ingredient_id=body.ingredient_id, from_product_id=from_id, to_product_id=body.to_product_id,
                       from_grams=float(ing["grams"]), to_grams=grams, actor_id=user.id)
    db.add(ev)
    record_event(db, action="DIET_SWAP", actor_id=user.id, subject_ids=[a.client_id],
                 payload={"assigned_diet_id": a.id, "day": body.day, "meal_id": body.meal_id,
                          "from": from_id, "to": body.to_product_id},
                 summary="Wymiana produktu w diecie")
    db.commit()
    plan = serwis.plan_z_korektami(db, a)
    d = next(x for x in plan["days"] if x["day"] == body.day)
    return {"swap_event_id": ev.id, "day": d, "macros": {k: round(v, 1) for k, v in cur.items()}}


@router.patch("/assigned/{diet_id}", dependencies=[Depends(wymagaj_modulu)])
def patch_assigned(diet_id: str, body: PatchIn, coach: User = Depends(require_role("COACH")),
                   db: Session = Depends(get_db)):
    """Trener: ręczna korekta gramatury, zamiana posiłku z biblioteki (ten
    sam slot i profil) albo blokada wymian; zwraca przeliczony dzień."""
    a = _dieta(db, coach, diet_id)
    o = serwis.overrides(a)
    zmiana = None
    if body.swaps_enabled is not None:
        a.swaps_enabled = body.swaps_enabled
        zmiana = "swaps"
    if body.grams is not None:
        if not (body.day and body.meal_id and body.ingredient_id):
            raise HTTPException(status_code=422, detail="Korekta gramatury wymaga day, meal_id i ingredient_id.")
        o["ingredients"][serwis._klucz(body.day, body.meal_id, body.ingredient_id)] = {
            "grams": float(body.grams), "by": coach.id, "at": now_iso(), "kind": "coach"}
        zmiana = "grams"
    if body.replace_with_meal_id:
        if not (body.day and body.meal_id):
            raise HTTPException(status_code=422, detail="Zamiana posiłku wymaga day i meal_id.")
        plan = serwis.migawka(db, a)
        d = next((x for x in plan["days"] if x["day"] == body.day), None)
        m_idx = next((i for i, x in enumerate(d["meals"]) if x["meal_id"] == body.meal_id), None) if d else None
        if m_idx is None:
            raise HTTPException(status_code=404, detail="Nie znaleziono posiłku w migawce.")
        w = _week(db, a.week_id)
        tpl = serwis.szablon_dict(db, w)
        # Skalujemy sam zastępczy posiłek do celu pierwotnego posiłku (tak jak zrobił to silnik).
        try:
            tpl2 = serwis.szablon_z_zamianami(db, tpl, {f"{body.day}:{body.meal_id}": body.replace_with_meal_id})
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from None
        prods, _ = serwis.produkty(db)
        nowy = next(mm for mm in next(dd for dd in tpl2["days"] if dd["day"] == body.day)["meals"]
                    if mm.get("replaced_from") == body.meal_id)
        wynik = S.scale_meal(nowy, d["meals"][m_idx]["target"], prods)
        d["meals"][m_idx] = serwis.posilek_out(wynik)
        d["meals"][m_idx]["replaced_from"] = body.meal_id
        d["macros"] = {k: round(sum(mm["macros"][k] for mm in d["meals"]), 1) for k in ("kcal", "P", "F", "C")}
        ok, dev = S.check(d["macros"], d["target"], S.TOL_DAY)
        d["deviation"] = {k: round(v, 1) for k, v in dev.items()}
        d["status"] = "OK" if ok else "POZA_TOLERANCJĄ"
        a.computed_plan_json = json.dumps(plan, ensure_ascii=False)
        o["meals"][f"{body.day}:{body.meal_id}"] = {"replaced_by_meal_id": body.replace_with_meal_id, "by": coach.id,
                                                    "at": now_iso()}
        zmiana = "meal"
    if zmiana is None:
        raise HTTPException(status_code=422, detail="Brak zmiany do zapisania.")
    a.overrides_json = json.dumps(o, ensure_ascii=False)
    a.updated_at = now_iso()
    record_event(db, action="DIET_ASSIGNED_EDITED", actor_id=coach.id, subject_ids=[a.client_id],
                 payload={"assigned_diet_id": a.id, "change": zmiana}, summary="Korekta przypisanej diety")
    db.commit()
    out = serwis.dieta_out(db, a)
    day = next((x for x in out["plan"]["days"] if x["day"] == body.day), None) if body.day else None
    return {"assigned": out, "day": day}


# --- panel szablonów (admin / dietetyk) --------------------------------------------------------


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    base_p_pct: float = Field(ge=0.05, le=0.7)
    base_f_pct: float = Field(ge=0.05, le=0.7)
    base_c_pct: float = Field(ge=0.05, le=0.8)
    diet_tags: list[str] = Field(default_factory=list, max_length=20)


class WeekIn(BaseModel):
    profile_id: str
    variant_no: int = Field(ge=1, le=20)
    name: str = Field(default="", max_length=200)
    base_kcal: int = Field(default=2000, ge=800, le=6000)
    kcal_min: int = Field(default=1400, ge=800, le=6000)
    kcal_max: int = Field(default=3200, ge=800, le=8000)


class MealIn(BaseModel):
    slot: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    kcal_share: float = Field(gt=0, le=1)
    flexible: bool = False
    recipe_steps: str = Field(default="", max_length=4000)
    prep_minutes: int | None = Field(default=None, ge=0, le=600)
    tags: list[str] = Field(default_factory=list, max_length=20)


class IngredientIn(BaseModel):
    product_id: str
    base_grams: float = Field(gt=0, le=5000)
    scaling_class: str | None = Field(default=None, pattern="^(LINIOWY|DYSKRETNY|TŁUMIONY|STAŁY)$")
    macro_role: str = Field(default="NONE", pattern="^(P|C|F|NONE)$")
    min_factor: float | None = Field(default=None, gt=0, le=10)
    max_factor: float | None = Field(default=None, gt=0, le=10)
    round_step: float | None = Field(default=None, gt=0, le=100)
    unit_g: float | None = Field(default=None, gt=0, le=1000)
    unit_step: float | None = Field(default=None, gt=0, le=10)
    group_name: str | None = Field(default=None, max_length=60)
    swappable: bool = True


class ProductIn(BaseModel):
    name_pl: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=1, max_length=60)
    substitution_group: str = Field(default="", max_length=80)
    protein_100: float = Field(ge=0, le=100)
    fat_100: float = Field(ge=0, le=100)
    carbs_100: float = Field(ge=0, le=100)
    fiber_100: float = Field(default=0, ge=0, le=100)
    kcal_usda: float | None = Field(default=None, ge=0, le=1000)
    cooking_tags: str = Field(default="*", max_length=200)
    allergens: str = Field(default="", max_length=200)
    diet_exclusions: str = Field(default="", max_length=200)
    default_scaling: str = Field(default="LINIOWY", pattern="^(LINIOWY|DYSKRETNY|TŁUMIONY|STAŁY)$")
    source: str = Field(min_length=3, max_length=120)
    source_id: str | None = Field(default=None, max_length=80)


@router.get("/products", dependencies=[Depends(wymagaj_modulu)])
def products(user: User = Depends(_edytor), db: Session = Depends(get_db)):
    rows = db.query(DietProduct).order_by(DietProduct.category, DietProduct.name_pl).all()
    return {"products": [{"id": p.id, "name_pl": p.name_pl, "category": p.category,
                          "substitution_group": p.substitution_group, "kcal_100": p.kcal_100,
                          "protein_100": p.protein_100, "fat_100": p.fat_100, "carbs_100": p.carbs_100,
                          "default_scaling": p.default_scaling, "cooking_tags": p.cooking_tags,
                          "allergens": p.allergens, "diet_exclusions": p.diet_exclusions, "source": p.source}
                         for p in rows]}


@router.post("/products", status_code=201, dependencies=[Depends(wymagaj_modulu)])
def create_product(body: ProductIn, admin: User = Depends(require_role("ADMIN")), db: Session = Depends(get_db)):
    """Nowy produkt to osobna akcja admina z jawnym `source` — nigdy automat."""
    if db.query(DietProduct).filter_by(name_pl=body.name_pl).one_or_none():
        raise HTTPException(status_code=409, detail="Produkt o tej nazwie już istnieje")
    p = DietProduct(id=new_id("DPD"), kcal_100=round(4 * body.protein_100 + 9 * body.fat_100 + 4 * body.carbs_100, 1),
                    **body.model_dump())
    db.add(p)
    record_event(db, action="DIET_PRODUCT_ADDED", actor_id=admin.id, subject_ids=[admin.id],
                 payload={"product_id": p.id, "source": body.source}, summary=f"Dodano produkt {body.name_pl}")
    db.commit()
    return {"id": p.id, "name_pl": p.name_pl, "kcal_100": p.kcal_100}


@router.post("/profiles", status_code=201, dependencies=[Depends(wymagaj_modulu)])
def create_profile(body: ProfileIn, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    if abs(body.base_p_pct + body.base_f_pct + body.base_c_pct - 1) > 0.01:
        raise HTTPException(status_code=422, detail="Udziały makro muszą sumować się do 1,0.")
    if db.query(DietProfile).filter_by(name=body.name).one_or_none():
        raise HTTPException(status_code=409, detail="Profil o tej nazwie już istnieje")
    p = DietProfile(id=new_id("DPR"), name=body.name, description=body.description, base_p_pct=body.base_p_pct,
                    base_f_pct=body.base_f_pct, base_c_pct=body.base_c_pct, diet_tags=",".join(body.diet_tags))
    db.add(p)
    db.commit()
    return _profil_out(db, p)


@router.put("/profiles/{profile_id}", dependencies=[Depends(wymagaj_modulu)])
def update_profile(profile_id: str, body: ProfileIn, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    p = db.get(DietProfile, profile_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if abs(body.base_p_pct + body.base_f_pct + body.base_c_pct - 1) > 0.01:
        raise HTTPException(status_code=422, detail="Udziały makro muszą sumować się do 1,0.")
    p.name, p.description = body.name, body.description
    p.base_p_pct, p.base_f_pct, p.base_c_pct = body.base_p_pct, body.base_f_pct, body.base_c_pct
    p.diet_tags = ",".join(body.diet_tags)
    db.commit()
    return _profil_out(db, p)


@router.post("/weeks", status_code=201, dependencies=[Depends(wymagaj_modulu)])
def create_week(body: WeekIn, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    if db.get(DietProfile, body.profile_id) is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono profilu")
    if db.query(DietTemplateWeek).filter_by(profile_id=body.profile_id, variant_no=body.variant_no).one_or_none():
        raise HTTPException(status_code=409, detail="Ta odsłona już istnieje")
    w = DietTemplateWeek(id=new_id("DTW"), created_by=user.id, status="DRAFT", **body.model_dump())
    db.add(w)
    db.flush()
    for n in range(1, 8):
        db.add(DietTemplateDay(id=new_id("DTD"), week_id=w.id, day_no=n))
    db.commit()
    return _szablon_podglad(db, w)


@router.put("/weeks/{week_id}", dependencies=[Depends(wymagaj_modulu)])
def update_week(week_id: str, body: WeekIn, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    w = _week(db, week_id)
    for k, v in body.model_dump(exclude={"profile_id"}).items():
        setattr(w, k, v)
    w.updated_at = now_iso()
    db.commit()
    return _szablon_podglad(db, w)


@router.get("/weeks/{week_id}/full", dependencies=[Depends(wymagaj_modulu)])
def week_full(week_id: str, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    """Pełna odsłona (z gramaturami bazowymi i regułami) — panel edycji."""
    return serwis.szablon_dict(db, _week(db, week_id))


def _dzien(db: Session, week: DietTemplateWeek, day_no: int) -> DietTemplateDay:
    d = db.query(DietTemplateDay).filter_by(week_id=week.id, day_no=day_no).one_or_none()
    if d is None:
        d = DietTemplateDay(id=new_id("DTD"), week_id=week.id, day_no=day_no)
        db.add(d)
        db.flush()
    return d


@router.post("/weeks/{week_id}/days/{day_no}/meals", status_code=201, dependencies=[Depends(wymagaj_modulu)])
def create_meal(week_id: str, day_no: int, body: MealIn, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    w = _week(db, week_id)
    if not 1 <= day_no <= 7:
        raise HTTPException(status_code=422, detail="day_no 1–7")
    d = _dzien(db, w, day_no)
    pos = db.query(DietTemplateMeal).filter_by(day_id=d.id).count()
    m = DietTemplateMeal(id=new_id("DTM"), day_id=d.id, position=pos, tags=",".join(body.tags),
                         **body.model_dump(exclude={"tags"}))
    db.add(m)
    w.updated_at = now_iso()
    db.commit()
    return {"meal_id": m.id, "day_no": day_no}


def _meal(db: Session, meal_id: str) -> tuple[DietTemplateMeal, DietTemplateWeek]:
    m = db.get(DietTemplateMeal, meal_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono posiłku")
    d = db.get(DietTemplateDay, m.day_id)
    return m, _week(db, d.week_id)


@router.put("/meals/{meal_id}", dependencies=[Depends(wymagaj_modulu)])
def update_meal(meal_id: str, body: MealIn, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    m, w = _meal(db, meal_id)
    for k, v in body.model_dump(exclude={"tags"}).items():
        setattr(m, k, v)
    m.tags = ",".join(body.tags)
    w.updated_at = now_iso()
    db.commit()
    return {"ok": True}


@router.delete("/meals/{meal_id}", dependencies=[Depends(wymagaj_modulu)])
def delete_meal(meal_id: str, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    m, w = _meal(db, meal_id)
    db.query(DietTemplateIngredient).filter_by(meal_id=m.id).delete()
    db.delete(m)
    w.updated_at = now_iso()
    db.commit()
    return {"ok": True}


@router.post("/meals/{meal_id}/ingredients", status_code=201, dependencies=[Depends(wymagaj_modulu)])
def create_ingredient(meal_id: str, body: IngredientIn, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    m, w = _meal(db, meal_id)
    if db.get(DietProduct, body.product_id) is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono produktu — dodaj go najpierw do bazy (admin, z `source`).")
    if body.scaling_class == "DYSKRETNY" and not body.unit_g:
        raise HTTPException(status_code=422, detail="DYSKRETNY wymaga unit_g.")
    pos = db.query(DietTemplateIngredient).filter_by(meal_id=m.id).count()
    i = DietTemplateIngredient(id=new_id("DTI"), meal_id=m.id, position=pos, **body.model_dump())
    db.add(i)
    w.updated_at = now_iso()
    db.commit()
    return {"ingredient_id": i.id}


@router.put("/ingredients/{ingredient_id}", dependencies=[Depends(wymagaj_modulu)])
def update_ingredient(ingredient_id: str, body: IngredientIn, user: User = Depends(_edytor),
                      db: Session = Depends(get_db)):
    i = db.get(DietTemplateIngredient, ingredient_id)
    if i is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono składnika")
    if db.get(DietProduct, body.product_id) is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono produktu")
    if body.scaling_class == "DYSKRETNY" and not body.unit_g:
        raise HTTPException(status_code=422, detail="DYSKRETNY wymaga unit_g.")
    _m, w = _meal(db, i.meal_id)
    for k, v in body.model_dump().items():
        setattr(i, k, v)
    w.updated_at = now_iso()
    db.commit()
    return {"ok": True}


@router.delete("/ingredients/{ingredient_id}", dependencies=[Depends(wymagaj_modulu)])
def delete_ingredient(ingredient_id: str, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    i = db.get(DietTemplateIngredient, ingredient_id)
    if i is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono składnika")
    _m, w = _meal(db, i.meal_id)
    db.delete(i)
    w.updated_at = now_iso()
    db.commit()
    return {"ok": True}


def _sweep(db: Session, w: DietTemplateWeek) -> dict[str, Any]:
    """Sweep 1400–3200 co 100: dni OK, flagi per posiłek; błąd definicji
    (np. DYSKRETNY bez unit_g, brak składników) wraca jako `error`."""
    tpl = serwis.szablon_dict(db, w)
    prods, _ = serwis.produkty(db)
    flagi: dict[str, dict[str, Any]] = {}
    dni_ok = dni = 0
    brakujace = [d["day"] for d in tpl["days"] if not d["meals"]]
    tpl_pelne = {**tpl, "days": [d for d in tpl["days"] if d["meals"]]}
    try:
        for kcal in range(1400, 3201, 100):
            for d in S.scale_week(tpl_pelne, kcal, prods):
                dni += 1
                dni_ok += d["status"] == "OK"
                for m in d["meals"]:
                    f = flagi.setdefault(m["meal_id"], {"meal_id": m["meal_id"], "day": d["day"], "name": m["name"],
                                                         "slot": m["slot"], "flags": 0, "out_of_range": 0})
                    if m["status"] != "OK":
                        f["flags"] += 1
                    if m["status"] == "POZA_ZAKRESEM":
                        f["out_of_range"] += 1
    except (ValueError, ZeroDivisionError, KeyError) as e:
        return {"error": f"Szablon niekompletny: {e}", "days": dni, "days_ok": dni_ok, "meals": [], "ok_pct": 0,
                "missing_days": brakujace, "publishable": False}
    pct = round(100 * dni_ok / dni) if dni else 0
    error = None
    if brakujace:
        error = "Dni bez posiłków: " + ", ".join(map(str, brakujace)) + " — odsłona musi mieć 7 dni."
    return {"days": dni, "days_ok": dni_ok, "ok_pct": pct, "kcal_points": 19, "missing_days": brakujace,
            "error": error, "meals": sorted(flagi.values(), key=lambda x: (-x["flags"], x["day"])),
            "publishable": not brakujace and dni > 0 and dni_ok / dni >= 0.95}


@router.post("/weeks/{week_id}/sweep", dependencies=[Depends(wymagaj_modulu)])
def sweep(week_id: str, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    return _sweep(db, _week(db, week_id))


@router.post("/weeks/{week_id}/publish", dependencies=[Depends(wymagaj_modulu)])
def publish_week(week_id: str, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    """Publikacja tylko przy sweep ≥ 95 % dni OK."""
    w = _week(db, week_id)
    r = _sweep(db, w)
    if not r["publishable"]:
        return _konflikt("SWEEP_BELOW_THRESHOLD",
                         f"Sweep: {r['days_ok']}/{r['days']} dni OK ({r['ok_pct']} %) — próg publikacji to 95 %."
                         + (f" {r['error']}" if r.get("error") else ""), sweep=r)
    w.status = "PUBLISHED"
    w.updated_at = now_iso()
    record_event(db, action="DIET_WEEK_PUBLISHED", actor_id=user.id, subject_ids=[user.id],
                 payload={"week_id": w.id, "days_ok": r["days_ok"], "days": r["days"]},
                 summary=f"Opublikowano odsłonę {w.name}")
    db.commit()
    return {"status": w.status, "sweep": r}


@router.post("/weeks/{week_id}/unpublish", dependencies=[Depends(wymagaj_modulu)])
def unpublish_week(week_id: str, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    w = _week(db, week_id)
    w.status = "DRAFT"
    w.updated_at = now_iso()
    db.commit()
    return {"status": w.status}


@router.post("/weeks/import", status_code=201, dependencies=[Depends(wymagaj_modulu)])
def import_week(body: dict, user: User = Depends(_edytor), db: Session = Depends(get_db)):
    """Import odsłony z JSON w formacie `template_standard_v1.json` (jako DRAFT)."""
    for k in ("profile", "variant", "macro_pct", "days"):
        if k not in body:
            raise HTTPException(status_code=422, detail=f"Brak pola {k}")
    try:
        w, nowa = dieta_seed.zaimportuj_szablon(db, body, created_by=user.id, status="DRAFT")
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=422, detail=f"Import odrzucony: {e}") from None
    if not nowa:
        raise HTTPException(status_code=409, detail="Ta odsłona (profil, wariant) już istnieje")
    db.commit()
    return _szablon_podglad(db, w)


"""Kreator dań (0.57.0) — API trenera nad silnikiem referencyjnym.

Propose-only: `generuj` liczy menu i nic nie zapisuje; `zapisz` tworzy
nową wersję planu diety klienta ze śladem decyzji w tej samej
transakcji; zamiana dania = `zamiana/podglad` (bez mutacji) +
`zamiana/zatwierdz` (kontrola rewizji → 409). Publikacja receptur =
jawne poświadczenia trenera. Bez modelu językowego.

Autoryzacja: rola COACH + relacja i zgoda `nutrition_data` dla klienta
(`resolve_client_access`); identyfikatory z przeglądarki nie są dowodem
uprawnień. Zdarzenia audytu bez alergenów i bez wykluczeń.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..authz import DOMAIN_NUTRITION, require_owned_resource, resolve_client_access
from ..db import get_db
from ..hos_bridge import record_event
from ..kulinaria import adapter, dane, engine, serwis
from ..models import NutritionPlan, NutritionPlanVersion, User, new_id, now_iso
from ..security import require_role

router = APIRouter(prefix="/api/coach/kulinaria", tags=["kulinaria"])


class ZakresIn(BaseModel):
    adult: bool
    no_pregnancy_or_breastfeeding: bool
    no_medical_diet: bool
    no_glucose_meds_or_diabetes: bool


class KonfiguracjaIn(BaseModel):
    tryb: str = Field(default="preview", pattern="^(preview|production)$")
    client_id: str | None = Field(default=None, max_length=40)
    days: int = Field(default=7, ge=1, le=31)
    meal_count: int = Field(default=3, ge=2, le=6)
    animal_policy: str = Field(pattern="^(omnivore|vegetarian|pescetarian|vegan)$")
    pattern: str = Field(default="balanced", pattern="^(balanced|mediterranean|paleo_classic_v1)$")
    carb_policy: str = Field(default="standard", pattern="^(standard|low_carb|ketogenic)$")
    carb_limit_g: float | None = Field(default=None, gt=0, le=600)
    carb_basis: str | None = Field(default=None, pattern="^(available_excluding_fiber|total_including_fiber)$")
    start_date: str | None = Field(default=None, max_length=10)
    max_total_minutes: int = Field(default=30, ge=5, le=240)
    max_active_minutes: int = Field(default=20, ge=5, le=240)
    max_family_uses_per_week: int = Field(default=2, ge=1, le=42)
    excluded_ingredient_ids: list[str] = Field(default_factory=list, max_length=80)
    allergens: list[str] = Field(default_factory=list, max_length=10)
    equipment: list[str] = Field(default_factory=list, max_length=10)
    preferred_cuisines: list[str] = Field(default_factory=list, max_length=10)
    zakres: ZakresIn | None = None
    tolerance_pct: dict[str, float] | None = None


class ZapiszIn(KonfiguracjaIn):
    client_id: str = Field(min_length=1, max_length=40)
    title: str | None = Field(default=None, max_length=300)
    potwierdzam_szkice: bool = False


class ZamianaPodgladIn(BaseModel):
    plan_id: str = Field(min_length=1, max_length=40)
    version_no: int = Field(ge=1)
    meal_index: int = Field(ge=0)
    recipe_id: str = Field(min_length=1, max_length=80)
    variant_id: str = Field(default="base", max_length=40)


class ZamianaZatwierdzIn(ZamianaPodgladIn):
    reason: str = Field(default="Zamiana dania w kreatorze dań", min_length=1, max_length=2000)


class PublikujIn(BaseModel):
    kitchen: bool = False
    dietitian: bool = False
    allergens_checked: bool = False
    expires_on: str = Field(min_length=10, max_length=10)
    validated_variants: list[str] = Field(default_factory=list, max_length=10)


class PorownanieIn(BaseModel):
    """Te same wejścia dla starego (produkty) i nowego (dania) generatora."""
    konfiguracja: KonfiguracjaIn
    stary_wynik: dict


def _naglowek(r: dict) -> dict:
    return {"id": r["id"], "revision": r["revision"], "name": r["name"], "family_id": r["family_id"],
            "meal_slots": r["meal_slots"], "cuisine": r["cuisine"], "status": r["status"],
            "total_minutes": r["total_minutes"], "active_minutes": r["active_minutes"],
            "review": r["review"], "portion_variants": r["portion_variants"],
            "ingredients": r["ingredients"]}


@router.get("/profile")
def profile(coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    recs = adapter.receptury(db)
    liczby: dict[str, int] = {}
    for r in recs:
        liczby[r["status"]] = liczby.get(r["status"], 0) + 1
    foods = adapter.produkty_dla_silnika()
    return {
        "osie": serwis.OSIE, "alergeny": list(dane.ALERGENY),
        "sprzet": [{"id": s, "label": dane.SPRZET_NAZWY[s]} for s in dane.SPRZET],
        "rodziny": dane.rodziny(), "sloty": dane.SLOTY_NAZWY,
        "receptury": {"razem": len(recs), "wg_statusu": liczby},
        "produkty": [{"id": f["id"], "name": f["name"], "state": f["state"], "groups": f["groups"],
                      "nutrition_verified": f["nutrition_verified"]} for f in foods.values()],
        "mapowanie": adapter.raport_mapowania(),
        "versions": dane.WERSJE, "zakres_pola": list(serwis.ZAKRES_POLA),
    }


@router.get("/receptury")
def receptury(status: str | None = None, coach: User = Depends(require_role("COACH")),
              db: Session = Depends(get_db)):
    recs = adapter.receptury(db)
    if status:
        recs = [r for r in recs if r["status"] == status]
    return {"items": [_naglowek(r) for r in recs], "total": len(recs)}


@router.get("/receptury/{recipe_id}")
def receptura(recipe_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    r = adapter.receptura(db, recipe_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    foods = adapter.produkty_dla_silnika()
    wartosci = None
    problem = None
    try:
        wartosci = engine.recipe_nutrition(r, foods, 1.0, sorted(engine.REQUIRED_MACROS))
    except engine.InputError as e:
        problem = str(e)
    return {**r, "skladniki_opis": serwis._etykieta_posilku({"ingredients": r["ingredients"], "steps": r["steps"]}, foods),
            "nutrition_base": wartosci, "nutrition_problem": problem,
            "source": dane.mapowanie()["source_id"] if wartosci else None}


@router.post("/receptury/{recipe_id}/publikuj")
def publikuj(recipe_id: str, body: PublikujIn, coach: User = Depends(require_role("COACH")),
             db: Session = Depends(get_db)):
    try:
        row = serwis.publikuj_recepture(
            db, coach_id=coach.id, recipe_id=recipe_id,
            poswiadczenia={"kitchen": body.kitchen, "dietitian": body.dietitian,
                           "allergens_checked": body.allergens_checked},
            expires_on=body.expires_on, validated_variants=body.validated_variants)
    except KeyError:
        raise HTTPException(status_code=404, detail="Nie znaleziono") from None
    except serwis.BladWejscia as e:
        raise HTTPException(status_code=422, detail=f"Publikacja odrzucona: {e}") from None
    record_event(db, action="RECIPE_PUBLISHED", actor_id=coach.id, subject_ids=[coach.id],
                 payload={"recipe_id": recipe_id, "revision": row.revision, "expires_on": body.expires_on},
                 summary=f"Kreator dań: opublikowano recepturę {recipe_id}")
    db.commit()
    return {"recipe_id": recipe_id, "revision": row.revision, "status": row.status,
            "review": json.loads(row.review_json)}


@router.post("/receptury/{recipe_id}/wycofaj")
def wycofaj(recipe_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    try:
        row = serwis.wycofaj_recepture(db, coach_id=coach.id, recipe_id=recipe_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Nie znaleziono") from None
    record_event(db, action="RECIPE_RETIRED", actor_id=coach.id, subject_ids=[coach.id],
                 payload={"recipe_id": recipe_id, "revision": row.revision},
                 summary=f"Kreator dań: wycofano recepturę {recipe_id}")
    db.commit()
    return {"recipe_id": recipe_id, "status": row.status}


@router.post("/pokrycie")
def pokrycie(body: KonfiguracjaIn, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Audyt pokrycia: kandydaci per slot po filtrach (bez oceny makro)."""
    if body.client_id:
        resolve_client_access(db, coach, body.client_id, domain=DOMAIN_NUTRITION)
    try:
        cfg, _ = serwis.zbuduj_konfiguracje(db, body.model_dump(), body.client_id)
        return engine.coverage(adapter.receptury(db), adapter.produkty_dla_silnika(), cfg)
    except (serwis.BladWejscia, engine.InputError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


@router.post("/generuj")
def generuj(body: KonfiguracjaIn, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Menu bez zapisu. Statusy silnika wracają jako 200 (to poprawne
    odpowiedzi, nie błędy HTTP)."""
    if body.client_id:
        resolve_client_access(db, coach, body.client_id, domain=DOMAIN_NUTRITION)
    try:
        return serwis.generuj(db, body.model_dump(), body.client_id)
    except serwis.BladWejscia as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


@router.post("/zapisz", status_code=201)
def zapisz(body: ZapiszIn, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Nowa wersja planu diety klienta z menu + ślady decyzji (jedna
    transakcja). Podgląd ze szkiców wymaga jawnego potwierdzenia."""
    resolve_client_access(db, coach, body.client_id, action="write", domain=DOMAIN_NUTRITION)
    try:
        res = serwis.generuj(db, body.model_dump(exclude={"title", "potwierdzam_szkice"}), body.client_id)
    except serwis.BladWejscia as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    if not res.get("plan"):
        return JSONResponse(status_code=409, content={
            "detail": "Silnik nie zwrócił planu — zobacz status i uwagi.", "code": res["status"], "wynik": res})
    if res["plan"]["mode"] == "preview" and not body.potwierdzam_szkice:
        return JSONResponse(status_code=409, content={
            "detail": "To podgląd kulinarny ze szkiców bez wartości odżywczych. Zapis wymaga jawnego "
                      "potwierdzenia (potwierdzam_szkice=true).", "code": "DRAFT_CONFIRMATION_REQUIRED",
            "wynik": res})
    cfg, meta = res["config"], res["meta"]
    tresc = serwis.tresc_wersji(res, cfg, meta)
    plan = (db.query(NutritionPlan).filter_by(client_id=body.client_id, status="ACTIVE")
            .order_by(NutritionPlan.updated_at.desc()).first())
    tytul = body.title or f"Menu z kreatora dań od {cfg['start_date']}"
    powod = (f"Menu z kreatora dań ({cfg['days']} dni, {cfg['meal_count']} posiłki, tryb {cfg['mode']}, "
             f"status {res['status']}) — do przeglądu trenera.")
    if plan is None:
        plan = NutritionPlan(id=new_id("NUT"), client_id=body.client_id, coach_id=coach.id,
                             title=tytul, current_version_no=1)
        db.add(plan)
        wersja_no = 1
    else:
        wersja_no = plan.current_version_no + 1
        plan.current_version_no = wersja_no
        plan.updated_at = now_iso()
    wersja = NutritionPlanVersion(id=new_id("NUV"), plan_id=plan.id, version_no=wersja_no, reason=powod,
                                  content_json=json.dumps(tresc, ensure_ascii=False), created_by=coach.id)
    db.add(wersja)
    n = serwis.zapisz_slady(db, owner_id=body.client_id, plan_id=plan.id, plan_revision=wersja_no, tresc=tresc)
    record_event(db, action="NUTRITION_VERSION_CREATED", actor_id=coach.id, subject_ids=[body.client_id],
                 # Bez alergenów i wykluczeń — tylko metadane menu.
                 payload={"plan_id": plan.id, "version_no": wersja_no, "reason": powod, "source": "kulinaria",
                          "engine_version": res["engine_version"], "status": res["status"],
                          "days": cfg["days"], "meal_count": cfg["meal_count"], "mode": cfg["mode"],
                          "traces": n, "supplements_count": 0},
                 summary=f"Dieta „{plan.title}”: wersja v{wersja_no} z kreatora dań")
    db.commit()
    return {"id": plan.id, "version_no": wersja_no, "status": res["status"], "traces": n,
            "issues": res["issues"], "shopping_list": res.get("shopping_list", [])}


def _wersja_kulinarna(db: Session, coach: User, plan_id: str, version_no: int) -> tuple[NutritionPlan, NutritionPlanVersion, dict]:
    plan = require_owned_resource(db.get(NutritionPlan, plan_id), actor=coach, resource=f"nutrition_plan:{plan_id}")
    resolve_client_access(db, coach, plan.client_id, action="write", domain=DOMAIN_NUTRITION)
    v = db.query(NutritionPlanVersion).filter_by(plan_id=plan.id, version_no=version_no).first()
    if v is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    tresc = json.loads(v.content_json)
    if not tresc.get("kulinaria"):
        raise HTTPException(status_code=422, detail="Ta wersja planu nie pochodzi z kreatora dań")
    return plan, v, tresc


@router.post("/zamiana/podglad")
def zamiana_podglad(body: ZamianaPodgladIn, coach: User = Depends(require_role("COACH")),
                    db: Session = Depends(get_db)):
    _plan, _v, tresc = _wersja_kulinarna(db, coach, body.plan_id, body.version_no)
    try:
        return serwis.podglad_zamiany(db, tresc, meal_index=body.meal_index, recipe_id=body.recipe_id,
                                      variant_id=body.variant_id)
    except serwis.BladWejscia as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


@router.post("/zamiana/zatwierdz", status_code=201)
def zamiana_zatwierdz(body: ZamianaZatwierdzIn, coach: User = Depends(require_role("COACH")),
                      db: Session = Depends(get_db)):
    """Ponowna kontrola uprawnień, rewizji (409 przy niezgodności) i całego
    dnia; nowa wersja planu ze śladami; stare rewizje zostają."""
    plan, _v, tresc = _wersja_kulinarna(db, coach, body.plan_id, body.version_no)
    if plan.current_version_no != body.version_no:
        return JSONResponse(status_code=409, content={
            "detail": "Plan ma już nowszą wersję — odśwież podgląd zamiany.", "code": "STALE_PLAN",
            "current_version_no": plan.current_version_no})
    try:
        podglad = serwis.podglad_zamiany(db, tresc, meal_index=body.meal_index, recipe_id=body.recipe_id,
                                         variant_id=body.variant_id)
    except serwis.BladWejscia as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    if not podglad["ok"]:
        return JSONResponse(status_code=409, content={
            "detail": "Zamiana nie przeszła ponownej kontroli dnia.", "code": "SWAP_REJECTED",
            "problemy": podglad["problemy"]})
    nowa = serwis.zastosuj_zamiane(tresc, podglad)
    wersja_no = plan.current_version_no + 1
    plan.current_version_no = wersja_no
    plan.updated_at = now_iso()
    powod = f"{body.reason}: {podglad['przed']['name']} → {podglad['po']['recipe_name']}"
    wersja = NutritionPlanVersion(id=new_id("NUV"), plan_id=plan.id, version_no=wersja_no, reason=powod,
                                  content_json=json.dumps(nowa, ensure_ascii=False), created_by=coach.id)
    db.add(wersja)
    n = serwis.zapisz_slady(db, owner_id=plan.client_id, plan_id=plan.id, plan_revision=wersja_no, tresc=nowa)
    record_event(db, action="NUTRITION_VERSION_CREATED", actor_id=coach.id, subject_ids=[plan.client_id],
                 payload={"plan_id": plan.id, "version_no": wersja_no, "reason": powod, "source": "kulinaria_swap",
                          "meal_index": body.meal_index, "traces": n, "supplements_count": 0},
                 summary=f"Dieta „{plan.title}”: zamiana dania → v{wersja_no}")
    db.commit()
    return {"id": plan.id, "version_no": wersja_no, "meal_index": body.meal_index, "traces": n}


@router.post("/porownanie")
def porownanie(body: PorownanieIn, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Stary generator (zestawy produktów) vs nowy (dania) na tych samych
    wejściach — metryki deterministyczne, bez ocen smaku."""
    if body.konfiguracja.client_id:
        resolve_client_access(db, coach, body.konfiguracja.client_id, domain=DOMAIN_NUTRITION)
    try:
        nowy = serwis.generuj(db, body.konfiguracja.model_dump(), body.konfiguracja.client_id)
    except serwis.BladWejscia as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return serwis.porownanie(body.stary_wynik, nowy)

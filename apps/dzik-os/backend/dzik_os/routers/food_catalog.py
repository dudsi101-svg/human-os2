"""Baza produktów spożywczych z makroskładnikami na 100 g (broadcast
trenera, ten sam wzorzec co KnowledgeItem/Exercise) oraz kompozytor
diety: przejrzysta arytmetyka podziału celu kcal/makro na gramaturę
WYBRANYCH przez trenera produktów.

Kompozytor NIGDY nie generuje diety samodzielnie i niczego nie zapisuje —
zwraca tylko sugestię do ręcznego wpisania przez trenera w
NutritionPlanVersion (zasada Human OS: AI/algorytm nie tworzy ani nie
zmienia planu bez udziału człowieka, patrz CLAUDE.md/Constitution)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import require_owned_resource
from ..db import get_db
from ..hos_bridge import record_event
from ..models import CoachClientRelationship, FoodProduct, User, new_id, now_iso
from ..schemas import DietSuggestionIn, FoodProductIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["food-catalog"])


def _out(item: FoodProduct) -> dict:
    return {
        "id": item.id, "coach_id": item.coach_id, "name": item.name,
        "category": item.category, "kcal_100g": item.kcal_100g,
        "protein_100g": item.protein_100g, "fat_100g": item.fat_100g,
        "carbs_100g": item.carbs_100g, "default_portion_g": item.default_portion_g,
        "status": item.status, "created_at": item.created_at, "updated_at": item.updated_at,
    }


@router.post("/coach/food-products", status_code=201)
def create_food_product(
    body: FoodProductIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = FoodProduct(
        id=new_id("FOD"), coach_id=coach.id, name=body.name, category=body.category,
        kcal_100g=body.kcal_100g, protein_100g=body.protein_100g, fat_100g=body.fat_100g,
        carbs_100g=body.carbs_100g, default_portion_g=body.default_portion_g,
        created_by=coach.id,
    )
    db.add(item)
    record_event(
        db, action="FOOD_PRODUCT_CREATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"product_id": item.id, "name": item.name},
        summary=f"Baza produktów: dodano „{item.name}”",
    )
    db.commit()
    return _out(item)


@router.get("/coach/food-products")
def list_own_food_products(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    rows = (
        db.query(FoodProduct)
        .filter(FoodProduct.coach_id == coach.id)
        .order_by(FoodProduct.category, FoodProduct.name)
        .all()
    )
    return {"items": [_out(i) for i in rows]}


@router.put("/coach/food-products/{item_id}")
def update_food_product(
    item_id: str,
    body: FoodProductIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = require_owned_resource(
        db.get(FoodProduct, item_id), actor=coach, resource=f"food_product:{item_id}"
    )
    item.name, item.category = body.name, body.category
    item.kcal_100g, item.protein_100g = body.kcal_100g, body.protein_100g
    item.fat_100g, item.carbs_100g = body.fat_100g, body.carbs_100g
    item.default_portion_g = body.default_portion_g
    item.updated_at = now_iso()
    record_event(
        db, action="FOOD_PRODUCT_UPDATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"product_id": item.id, "name": item.name},
        summary=f"Baza produktów: zaktualizowano „{item.name}”",
    )
    db.commit()
    return _out(item)


@router.post("/coach/food-products/{item_id}/status")
def set_food_product_status(
    item_id: str,
    status: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    if status not in {"ACTIVE", "ARCHIVED"}:
        raise HTTPException(status_code=422, detail="Nieprawidłowy status")
    item = require_owned_resource(
        db.get(FoodProduct, item_id), actor=coach, resource=f"food_product:{item_id}"
    )
    item.status = status
    item.updated_at = now_iso()
    db.commit()
    return {"ok": True, "status": status}


@router.get("/me/food-products")
def list_food_products_for_client(
    user: User = Depends(current_user), db: Session = Depends(get_db)
):
    coach_ids = [
        r.coach_id
        for r in db.query(CoachClientRelationship)
        .filter_by(client_id=user.id, status="ACTIVE")
        .all()
    ]
    if not coach_ids:
        return {"items": []}
    rows = (
        db.query(FoodProduct)
        .filter(FoodProduct.coach_id.in_(coach_ids), FoodProduct.status == "ACTIVE")
        .order_by(FoodProduct.category, FoodProduct.name)
        .all()
    )
    return {"items": [_out(i) for i in rows]}


def _dominant_macro(p: FoodProduct) -> str:
    """Kategoria produktu wg makroskładnika o największym udziale
    kalorycznym na 100 g — jawna, deterministyczna reguła (nie ocena AI)."""
    shares = {
        "PROTEIN": p.protein_100g * 4,
        "FAT": p.fat_100g * 9,
        "CARB": p.carbs_100g * 4,
    }
    return max(shares, key=lambda k: shares[k])


@router.post("/coach/diet-suggestion")
def diet_suggestion(
    body: DietSuggestionIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    products = (
        db.query(FoodProduct)
        .filter(FoodProduct.id.in_(body.product_ids), FoodProduct.coach_id == coach.id)
        .all()
    )
    found_ids = {p.id for p in products}
    missing = [pid for pid in body.product_ids if pid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Nie znaleziono produktów: {', '.join(missing)}"
        )

    by_macro: dict[str, list[FoodProduct]] = {"PROTEIN": [], "FAT": [], "CARB": []}
    for p in products:
        by_macro[_dominant_macro(p)].append(p)

    targets = {
        "PROTEIN": ("protein_100g", body.target_protein_g),
        "FAT": ("fat_100g", body.target_fat_g),
        "CARB": ("carbs_100g", body.target_carbs_g),
    }
    entries: list[dict] = []
    warnings: list[str] = []
    for macro, (field, target_g) in targets.items():
        group = by_macro[macro]
        if target_g <= 0:
            continue
        if not group:
            warnings.append(
                f"Brak wybranych produktów z przewagą "
                f"{'białka' if macro == 'PROTEIN' else 'tłuszczu' if macro == 'FAT' else 'węglowodanów'} "
                f"— cel {target_g} g nie może zostać rozłożony na porcje."
            )
            continue
        share_per_product = target_g / len(group)
        for p in group:
            per_100 = getattr(p, field)
            if per_100 <= 0:
                warnings.append(f"„{p.name}” ma zerową wartość {field} — pominięto w podziale.")
                continue
            grams = round(share_per_product / per_100 * 100, 1)
            entries.append(
                {
                    "product_id": p.id,
                    "name": p.name,
                    "macro_role": macro,
                    "grams": grams,
                    "kcal": round(grams / 100 * p.kcal_100g, 1),
                    "protein_g": round(grams / 100 * p.protein_100g, 1),
                    "fat_g": round(grams / 100 * p.fat_100g, 1),
                    "carbs_g": round(grams / 100 * p.carbs_100g, 1),
                }
            )

    totals = {
        "kcal": round(sum(e["kcal"] for e in entries), 1),
        "protein_g": round(sum(e["protein_g"] for e in entries), 1),
        "fat_g": round(sum(e["fat_g"] for e in entries), 1),
        "carbs_g": round(sum(e["carbs_g"] for e in entries), 1),
    }
    target = {
        "kcal": body.target_kcal,
        "protein_g": body.target_protein_g,
        "fat_g": body.target_fat_g,
        "carbs_g": body.target_carbs_g,
    }
    if body.target_kcal > 0:
        delta = round(totals["kcal"] - body.target_kcal, 1)
        if abs(delta) > body.target_kcal * 0.1:
            warnings.append(
                f"Suma kalorii z rozłożonych porcji ({totals['kcal']} kcal) różni się od celu "
                f"({body.target_kcal} kcal) o {delta:+} kcal — dobierz inne produkty lub "
                f"gramaturę ręcznie."
            )
    return {
        "target": target,
        "items": entries,
        "totals": totals,
        "warnings": warnings,
        "note": "To wyłącznie sugestia arytmetyczna — nic nie zostało zapisane. "
        "Trener decyduje, czy i jak wpisać to do planu żywieniowego klienta.",
    }

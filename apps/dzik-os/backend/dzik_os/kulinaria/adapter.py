"""Adapter żywieniowy i biblioteka receptur dla silnika referencyjnego.

`produkty_dla_silnika()` buduje słownik `foods` w kształcie wymaganym
przez `engine.py`: wartości na 100 g z WBUDOWANEJ bazy produktów Dzik OS
przez jawne mapowanie (`dane/mapowanie_produktow.json`). Bez wartości
z pamięci modelu: produkt bez mapowania albo bez błonnika (potrzebnego
do normalizacji węglowodanów „ogółem”) zostaje `nutrition_verified=False`
z `nutrition_per_100g=None` — silnik traktuje go jako nieznany.

`receptury(db)` łączy szkice pakietu z rewizjami publikacji w bazie
(`kulinaria_receptury`): produkcja widzi tylko `published` z pełnym
przeglądem (kitchen, dietitian, reviewer_id, expires_on), zapisanym
przez trenera jawnie — nigdy przez samą zmianę flagi w pliku.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import KulinariaReceptura
from . import dane


def produkty_dla_silnika() -> dict[str, dict]:
    m = dane.mapowanie()
    out: dict[str, dict] = {}
    for fid, f in dane.produkty_pakietu().items():
        wpis = m["produkty"].get(fid) or {}
        row = dane.produkt(wpis.get("produkt"))
        food = {
            "id": fid, "name": f["name"], "state": f["state"], "groups": list(f["groups"]),
            "allergens": list(f["allergens"]),
            # Alergeny „zweryfikowane” tylko dla produktów jednoskładnikowych
            # (skład znany z natury); złożone wymagają etykiety.
            "allergen_verified": bool(wpis.get("sklad_znany")) and row is not None,
            "nutrition_verified": False, "source_id": None, "source_version": None,
            "nutrition_per_100g": None, "carb_definition": None,
            "mapped_product": row.name if row else None,
            "mapping_note": wpis.get("uwaga"),
        }
        if row is not None and row.fiber is not None and row.fiber > row.carbs:
            # Niespójny wiersz bazy (błonnik > węglowodany ogółem): nie zgadujemy,
            # która definicja była użyta — produkt zostaje nieznany.
            food["mapping_note"] = ((food["mapping_note"] or "") +
                                    " błonnik > węglowodany ogółem w bazie — wartości niespójne, do przeglądu")
        elif row is not None and row.fiber is not None:
            food.update({
                "nutrition_verified": True, "source_id": m["source_id"],
                "source_version": m["source_version"], "carb_definition": m["carb_definition"],
                "nutrition_per_100g": {
                    "energy_kcal": float(row.kcal), "protein_g": float(row.protein),
                    "fat_g": float(row.fat), "carbs_total_g": float(row.carbs),
                    "fiber_g": float(row.fiber),
                },
            })
        elif row is not None:
            food["mapping_note"] = (food["mapping_note"] or "") + " brak błonnika w bazie — węglowodany dostępne nieobliczalne"
        out[fid] = food
    return out


def raport_mapowania() -> dict:
    foods = produkty_dla_silnika()
    zmapowane = [f for f in foods.values() if f["nutrition_verified"]]
    bez = [{"id": f["id"], "name": f["name"], "powod": f["mapping_note"]} for f in foods.values()
           if not f["nutrition_verified"]]
    return {"produkty": len(foods), "z_wartosciami": len(zmapowane), "bez_wartosci": bez,
            "alergeny_zweryfikowane": sum(1 for f in foods.values() if f["allergen_verified"]),
            "status": dane.mapowanie()["status"], "carb_definition": dane.mapowanie()["carb_definition"]}


def receptury(db: Session | None) -> list[dict]:
    """Szkice pakietu + nadpisania publikacji z bazy (status, review,
    zatwierdzone warianty porcji)."""
    out = []
    nadpisania: dict[str, KulinariaReceptura] = {}
    if db is not None:
        for row in db.query(KulinariaReceptura).all():
            nadpisania[row.recipe_id] = row
    for r in dane.receptury_pakietu():
        rec = json.loads(json.dumps(r, ensure_ascii=False))
        n = nadpisania.get(rec["id"])
        if n is not None and n.revision == rec["revision"]:
            rec["status"] = n.status
            rec["review"] = json.loads(n.review_json)
            zatw = set(json.loads(n.validated_variants_json))
            for v in rec["portion_variants"]:
                v["validated"] = v["id"] in zatw
        out.append(rec)
    return out


def receptura(db: Session | None, recipe_id: str) -> dict | None:
    return next((r for r in receptury(db) if r["id"] == recipe_id), None)


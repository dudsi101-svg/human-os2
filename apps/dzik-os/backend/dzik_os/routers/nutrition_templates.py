"""Szablony diety trenera (0.54.0) — katalog wbudowany + własne szablony.

Ta sama filozofia co szablony treningowe: wbudowany wpis katalogu po
imporcie staje się ZWYKŁYM szablonem trenera (wiersz w bazie), który
trener edytuje jak swój. Kopiowanie do klienta tworzy niezależny
`NutritionPlan` v1 istniejącą ścieżką — późniejsza edycja szablonu nie
zmienia diet klientów, a wersjonowanie zaczyna się na planie klienta.

Zero automatyki żywieniowej: makro w katalogu jest puste i przy
kopiowaniu trener podaje je świadomie (albo zostawia puste i uzupełnia
w kolejnej wersji diety klienta).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..authz import DOMAIN_NUTRITION, resolve_client_access
from ..db import get_db
from ..dieta_szablony_data import get_diet_template, list_diet_templates
from ..hos_bridge import record_event
from ..models import NutritionPlan, NutritionPlanVersion, NutritionTemplate, User, new_id, now_iso
from ..security import require_role

router = APIRouter(prefix="/api/nutrition-templates", tags=["nutrition-templates"])


class TemplateIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    kcal: int | None = Field(default=None, ge=0, le=20000)
    protein_g: int | None = Field(default=None, ge=0, le=2000)
    fat_g: int | None = Field(default=None, ge=0, le=2000)
    carbs_g: int | None = Field(default=None, ge=0, le=4000)
    sections: list[dict] = []
    meals: list[dict] = []


class CopyIn(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    kcal: int | None = Field(default=None, ge=0, le=20000)
    protein_g: int | None = Field(default=None, ge=0, le=2000)
    fat_g: int | None = Field(default=None, ge=0, le=2000)
    carbs_g: int | None = Field(default=None, ge=0, le=4000)


def _content_json(body: TemplateIn) -> str:
    return json.dumps(
        {
            "kcal": body.kcal,
            "protein_g": body.protein_g,
            "fat_g": body.fat_g,
            "carbs_g": body.carbs_g,
            "sections": body.sections,
            "meals": body.meals,
        },
        ensure_ascii=False,
    )


def _out(t: NutritionTemplate) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "content": json.loads(t.content_json),
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def _own(db: Session, coach: User, template_id: str) -> NutritionTemplate:
    row = db.get(NutritionTemplate, template_id)
    if row is None or row.coach_id != coach.id:
        # Cudzy szablon = nieistniejący (bez potwierdzania istnienia id).
        raise HTTPException(status_code=404, detail="Nie znaleziono szablonu")
    return row


@router.get("/catalog")
def catalog(coach: User = Depends(require_role("COACH"))):
    """Wbudowane szablony autorskie — tylko metadane do listy."""
    return {"templates": list_diet_templates()}


@router.post("/catalog/{catalog_id}/import", status_code=201)
def import_from_catalog(
    catalog_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Kopiuje wpis katalogu do MOICH szablonów (dalej edytowalny jak własny)."""
    tpl = get_diet_template(catalog_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono szablonu w katalogu")
    row = NutritionTemplate(
        id=new_id("NTP"),
        coach_id=coach.id,
        title=tpl["title"],
        content_json=json.dumps(tpl["content"], ensure_ascii=False),
    )
    db.add(row)
    record_event(
        db, action="NUTRITION_TEMPLATE_IMPORTED", actor_id=coach.id,
        subject_ids=[coach.id],
        payload={"template_id": row.id, "catalog_id": catalog_id},
        summary=f"Szablon diety z katalogu: {tpl['title']}",
    )
    db.commit()
    return _out(row)


@router.get("")
def my_templates(
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(NutritionTemplate)
        .filter(NutritionTemplate.coach_id == coach.id)
        .order_by(NutritionTemplate.created_at)
        .all()
    )
    return {"templates": [_out(r) for r in rows]}


@router.post("", status_code=201)
def create_template(
    body: TemplateIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    row = NutritionTemplate(
        id=new_id("NTP"), coach_id=coach.id, title=body.title,
        content_json=_content_json(body),
    )
    db.add(row)
    record_event(
        db, action="NUTRITION_TEMPLATE_CREATED", actor_id=coach.id,
        subject_ids=[coach.id],
        payload={"template_id": row.id, "title": body.title},
        summary=f"Nowy szablon diety: {body.title}",
    )
    db.commit()
    return _out(row)


@router.put("/{template_id}")
def update_template(
    template_id: str,
    body: TemplateIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    row = _own(db, coach, template_id)
    row.title = body.title
    row.content_json = _content_json(body)
    row.updated_at = now_iso()
    record_event(
        db, action="NUTRITION_TEMPLATE_UPDATED", actor_id=coach.id,
        subject_ids=[coach.id],
        payload={"template_id": row.id, "title": body.title},
        summary=f"Szablon diety zaktualizowany: {body.title}",
    )
    db.commit()
    return _out(row)


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    row = _own(db, coach, template_id)
    tytul = row.title
    db.delete(row)
    record_event(
        db, action="NUTRITION_TEMPLATE_DELETED", actor_id=coach.id,
        subject_ids=[coach.id],
        payload={"template_id": template_id, "title": tytul},
        summary=f"Szablon diety usunięty: {tytul}",
    )
    db.commit()
    return {"ok": True}


@router.post("/{template_id}/copy-to/{client_id}", status_code=201)
def copy_to_client(
    template_id: str,
    client_id: str,
    body: CopyIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Kopiuje szablon jako NOWĄ dietę klienta (v1). Kopia jest niezależna —
    późniejsza edycja szablonu nie zmienia diety klienta. Makro z body
    nadpisuje makro szablonu (świadoma decyzja trenera per klient)."""
    row = _own(db, coach, template_id)
    resolve_client_access(db, coach, client_id, action="write", domain=DOMAIN_NUTRITION)
    content = json.loads(row.content_json)
    for pole in ("kcal", "protein_g", "fat_g", "carbs_g"):
        wartosc = getattr(body, pole)
        if wartosc is not None:
            content[pole] = wartosc
    plan = NutritionPlan(
        id=new_id("NUT"), client_id=client_id, coach_id=coach.id,
        title=body.title or row.title, current_version_no=1,
    )
    db.add(plan)
    db.add(NutritionPlanVersion(
        id=new_id("NUV"), plan_id=plan.id, version_no=1,
        reason=f"Start z szablonu: {row.title}",
        content_json=json.dumps(content, ensure_ascii=False),
        created_by=coach.id,
    ))
    record_event(
        db, action="NUTRITION_PLAN_CREATED", actor_id=coach.id,
        subject_ids=[client_id],
        payload={"plan_id": plan.id, "title": plan.title, "version_no": 1,
                 "reason": f"Start z szablonu: {row.title}",
                 "supplements_count": 0},
        summary=f"Nowy plan żywieniowy z szablonu: {plan.title} (v1)",
    )
    db.commit()
    return {"id": plan.id, "version_no": 1}

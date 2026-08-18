from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import require_owned_resource, resolve_client_access
from ..db import get_db
from ..hos_bridge import record_event
from ..models import Document, NutritionPlan, NutritionPlanVersion, User, new_id, now_iso
from ..schemas import NutritionCreateIn, NutritionVersionIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["nutrition"])


def _version_out(db: Session, v: NutritionPlanVersion) -> dict:
    # document_id wskazuje rekord documents; frontend do pobrania potrzebuje
    # file_id tego dokumentu (endpoint /api/files/{id} operuje na plikach).
    doc = db.get(Document, v.document_id) if v.document_id else None
    return {
        "id": v.id,
        "version_no": v.version_no,
        "reason": v.reason,
        "content": json.loads(v.content_json),
        "document_id": v.document_id,
        "document_file_id": doc.file_id if doc is not None and doc.status == "ACTIVE" else None,
        "created_by": v.created_by,
        "created_at": v.created_at,
    }


def _check_document(db: Session, document_id: str | None, client_id: str) -> None:
    """Dokument diety musi istnieć, być aktywny i należeć do klienta,
    dla którego tworzona jest wersja planu."""
    if document_id is None:
        return
    doc = db.get(Document, document_id)
    if doc is None or doc.status != "ACTIVE" or doc.client_id != client_id:
        raise HTTPException(status_code=422, detail="Nieprawidłowy dokument diety")


def _content_json(body: NutritionVersionIn) -> str:
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


@router.post("/nutrition", status_code=201)
def create_nutrition_plan(
    body: NutritionCreateIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, coach, body.client_id, action="write")
    _check_document(db, body.version.document_id, body.client_id)
    plan = NutritionPlan(
        id=new_id("NUT"),
        client_id=body.client_id,
        coach_id=coach.id,
        title=body.title,
        current_version_no=1,
    )
    db.add(plan)
    version = NutritionPlanVersion(
        id=new_id("NUV"),
        plan_id=plan.id,
        version_no=1,
        reason=body.version.reason,
        content_json=_content_json(body.version),
        document_id=body.version.document_id,
        created_by=coach.id,
    )
    db.add(version)
    record_event(
        db,
        action="NUTRITION_PLAN_CREATED",
        actor_id=coach.id,
        subject_ids=[body.client_id],
        payload={"plan_id": plan.id, "title": plan.title, "version_no": 1,
                 "reason": body.version.reason},
        summary=f"Nowy plan żywieniowy: {plan.title} (v1)",
    )
    db.commit()
    return {"id": plan.id, "version_no": 1}


@router.post("/nutrition/{plan_id}/versions", status_code=201)
def create_nutrition_version(
    plan_id: str,
    body: NutritionVersionIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    plan = require_owned_resource(
        db.get(NutritionPlan, plan_id), actor=coach, resource=f"nutrition_plan:{plan_id}"
    )
    resolve_client_access(db, coach, plan.client_id, action="write")
    _check_document(db, body.document_id, plan.client_id)
    next_no = plan.current_version_no + 1
    version = NutritionPlanVersion(
        id=new_id("NUV"),
        plan_id=plan.id,
        version_no=next_no,
        reason=body.reason,
        content_json=_content_json(body),
        document_id=body.document_id,
        created_by=coach.id,
    )
    plan.current_version_no = next_no
    plan.updated_at = now_iso()
    db.add(version)
    record_event(
        db,
        action="NUTRITION_VERSION_CREATED",
        actor_id=coach.id,
        subject_ids=[plan.client_id],
        payload={"plan_id": plan.id, "version_no": next_no, "reason": body.reason},
        summary=f"Dieta '{plan.title}': nowa wersja v{next_no} — {body.reason}",
    )
    db.commit()
    return {"version_no": next_no}


@router.get("/clients/{client_id}/nutrition")
def client_nutrition(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    plans = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.client_id == client_id)
        .order_by(NutritionPlan.created_at.desc())
        .all()
    )
    out = []
    for p in plans:
        current = (
            db.query(NutritionPlanVersion)
            .filter_by(plan_id=p.id, version_no=p.current_version_no)
            .one_or_none()
        )
        out.append(
            {
                "id": p.id,
                "title": p.title,
                "status": p.status,
                "current_version_no": p.current_version_no,
                "current_version": _version_out(db, current) if current else None,
            }
        )
    return {"plans": out}


@router.get("/nutrition/{plan_id}/versions")
def nutrition_versions(
    plan_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    plan = db.get(NutritionPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, user, plan.client_id)
    rows = (
        db.query(NutritionPlanVersion)
        .filter(NutritionPlanVersion.plan_id == plan_id)
        .order_by(NutritionPlanVersion.version_no)
        .all()
    )
    return {"plan_id": plan_id, "title": plan.title,
            "versions": [_version_out(db, v) for v in rows]}

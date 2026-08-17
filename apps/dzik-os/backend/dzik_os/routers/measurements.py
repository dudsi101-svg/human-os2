from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..authz import resolve_client_access
from ..db import get_db
from ..models import Measurement, MetricDefinition, User, new_id
from ..schemas import MeasurementIn, MetricDefinitionIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["measurements"])


@router.post("/clients/{client_id}/measurements", status_code=201)
def add_measurement(
    client_id: str,
    body: MeasurementIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, action="write")
    source = "CLIENT_DECLARED" if user.id == client_id else "COACH_ENTERED"
    row = Measurement(
        id=new_id("MSR"),
        client_id=client_id,
        kind=body.kind,
        value=body.value,
        unit=body.unit,
        measured_at=body.measured_at,
        source=source,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.get("/clients/{client_id}/measurements")
def list_measurements(
    client_id: str,
    kind: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    q = db.query(Measurement).filter(Measurement.client_id == client_id)
    if kind:
        q = q.filter(Measurement.kind == kind)
    rows = q.order_by(Measurement.measured_at).all()
    return {
        "measurements": [
            {
                "id": m.id, "kind": m.kind, "value": m.value, "unit": m.unit,
                "measured_at": m.measured_at, "source": m.source,
                "created_by": m.created_by,
            }
            for m in rows
        ]
    }


@router.post("/metric-definitions", status_code=201)
def create_metric_definition(
    body: MetricDefinitionIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, coach, body.client_id, action="write")
    row = MetricDefinition(
        id=new_id("MTD"),
        client_id=body.client_id,
        name=body.name,
        unit=body.unit,
        created_by=coach.id,
    )
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.get("/clients/{client_id}/metric-definitions")
def list_metric_definitions(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    rows = (
        db.query(MetricDefinition)
        .filter(MetricDefinition.client_id == client_id)
        .all()
    )
    return {
        "definitions": [
            {"id": d.id, "name": d.name, "unit": d.unit, "created_by": d.created_by}
            for d in rows
        ]
    }

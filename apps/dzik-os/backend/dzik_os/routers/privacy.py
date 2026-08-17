from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from ..authz import require_client_self
from ..db import get_db
from ..hos_bridge import ConsentService, record_event
from ..models import (
    CheckinRevision,
    ConsentRecord,
    DailyNutritionLog,
    Document,
    Goal,
    Measurement,
    Message,
    MessageThread,
    NutritionPlan,
    NutritionPlanVersion,
    Observation,
    PaymentRecord,
    PaymentSchedule,
    ProfileField,
    ProgressPhoto,
    Reminder,
    ScheduleCompletion,
    ScheduleItem,
    StoredFile,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    WeeklyCheckin,
    WorkoutEntry,
    WorkoutSession,
    now_iso,
)
from ..schemas import ConsentGrantIn, DeletionRequestIn
from ..security import current_user, verify_password
from ..storage import storage

router = APIRouter(prefix="/api/me", tags=["privacy"])


def _rows(db: Session, model, **filters) -> list[dict]:
    out = []
    for row in db.query(model).filter_by(**filters).all():
        d = {c.name: getattr(row, c.name) for c in model.__table__.columns}
        for key in ("payload_json", "content_json"):
            if key in d and isinstance(d[key], str):
                try:
                    d[key.removesuffix("_json")] = json.loads(d.pop(key))
                except (ValueError, TypeError):
                    pass
        out.append(d)
    return out


@router.get("/consents")
def my_consents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.subject_id == user.id)
        .order_by(ConsentRecord.granted_at)
        .all()
    )
    grantee_names = {}
    for r in rows:
        grantee = db.get(User, r.grantee_id)
        grantee_names[r.grantee_id] = grantee.display_name if grantee else r.grantee_id
    return {
        "consents": [
            {
                "id": r.id,
                "grantee_id": r.grantee_id,
                "grantee_name": grantee_names.get(r.grantee_id),
                "purpose": r.purpose,
                "domain": r.domain,
                "actions": r.actions,
                "allow_sensitive": r.allow_sensitive,
                "consent_text_version": r.consent_text_version,
                "granted_at": r.granted_at,
                "expires_at": r.expires_at,
                "revoked_at": r.revoked_at,
                "confirmed_at": r.confirmed_at,
            }
            for r in rows
        ]
    }


@router.post("/consents", status_code=201)
def grant_consent(
    body: ConsentGrantIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = ConsentService.grant(
        db,
        subject_id=user.id,
        grantee_id=body.grantee_id,
        purpose=body.purpose,
        domain=body.domain,
        actions=body.actions,
        allow_sensitive=body.allow_sensitive,
        # Zgoda nadana osobiście przez podmiot jest potwierdzona z definicji.
        confirmed=True,
    )
    db.commit()
    return {"id": row.id}


@router.post("/consents/{consent_id}/confirm")
def confirm_consent(
    consent_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Jawne potwierdzenie przez podmiot zgody zarejestrowanej przy
    onboardingu (deklaracja zebrana przez trenera)."""
    from ..models import ConsentRecord, now_iso

    row = db.get(ConsentRecord, consent_id)
    if row is None or row.subject_id != user.id or row.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if row.confirmed_at is None:
        row.confirmed_at = now_iso()
        record_event(
            db,
            action="CONSENT_CONFIRMED",
            actor_id=user.id,
            subject_ids=[user.id],
            payload={"consent_id": row.id, "grantee_id": row.grantee_id,
                     "purpose": row.purpose, "domain": row.domain},
            summary=f"Potwierdzenie zgody {row.purpose}/{row.domain} przez podmiot",
        )
        db.commit()
    return {"id": row.id, "confirmed_at": row.confirmed_at}


@router.post("/consents/{consent_id}/revoke")
def revoke_consent(
    consent_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        row = ConsentService.revoke(db, consent_id=consent_id, subject_id=user.id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Nie znaleziono") from None
    db.commit()
    return {"id": row.id, "revoked_at": row.revoked_at}


def _collect_export(db: Session, user: User) -> dict:
    client_id = user.id
    threads = (
        db.query(MessageThread)
        .filter((MessageThread.client_id == client_id) | (MessageThread.coach_id == client_id))
        .all()
    )
    messages = []
    for t in threads:
        messages.extend(_rows(db, Message, thread_id=t.id))
    plans = _rows(db, TrainingPlan, client_id=client_id)
    plan_versions = []
    for p in plans:
        plan_versions.extend(_rows(db, TrainingPlanVersion, plan_id=p["id"]))
    nplans = _rows(db, NutritionPlan, client_id=client_id)
    nversions = []
    for p in nplans:
        nversions.extend(_rows(db, NutritionPlanVersion, plan_id=p["id"]))
    checkins = _rows(db, WeeklyCheckin, client_id=client_id)
    revisions = []
    for c in checkins:
        revisions.extend(_rows(db, CheckinRevision, checkin_id=c["id"]))
    sessions = _rows(db, WorkoutSession, client_id=client_id)
    entries = []
    for s in sessions:
        entries.extend(_rows(db, WorkoutEntry, session_id=s["id"]))
    pay_schedules = _rows(db, PaymentSchedule, client_id=client_id)
    pay_records = []
    for s in pay_schedules:
        pay_records.extend(_rows(db, PaymentRecord, schedule_id=s["id"]))
    schedule_items = _rows(db, ScheduleItem, client_id=client_id)
    schedule_completions = []
    for i in schedule_items:
        schedule_completions.extend(_rows(db, ScheduleCompletion, schedule_item_id=i["id"]))
    return {
        "export_version": "1.1",
        "user": {
            "id": user.id, "email": user.email, "display_name": user.display_name,
            "identity_id": user.identity_id, "created_at": user.created_at,
        },
        "profile_fields": _rows(db, ProfileField, client_id=client_id),
        "goals": _rows(db, Goal, client_id=client_id),
        "training_plans": plans,
        "training_plan_versions": plan_versions,
        "workout_sessions": sessions,
        "workout_entries": entries,
        "nutrition_plans": nplans,
        "nutrition_plan_versions": nversions,
        "schedule_items": schedule_items,
        "schedule_completions": schedule_completions,
        "reminders": _rows(db, Reminder, client_id=client_id),
        "weekly_checkins": checkins,
        "checkin_revisions": revisions,
        "measurements": _rows(db, Measurement, client_id=client_id),
        "progress_photos": _rows(db, ProgressPhoto, client_id=client_id),
        "documents": _rows(db, Document, client_id=client_id),
        "files": _rows(db, StoredFile, owner_user_id=client_id),
        "messages": messages,
        "payment_schedules": pay_schedules,
        "payment_records": pay_records,
        "consents": _rows(db, ConsentRecord, subject_id=client_id),
        "observations": _rows(db, Observation, client_id=client_id),
        "daily_nutrition_logs": _rows(db, DailyNutritionLog, client_id=client_id),
    }


@router.get("/export")
def export_my_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Eksport wszystkich danych użytkownika (prawo do przenoszenia danych).
    Zwraca komplet danych jako JSON; pliki wymienione są z identyfikatorami
    do pobrania przez /api/files/{id}."""
    export = _collect_export(db, user)
    record_event(
        db,
        action="DATA_EXPORTED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"export_version": export["export_version"], "format": "json"},
        summary="Eksport danych użytkownika (JSON)",
    )
    db.commit()
    return JSONResponse(
        content=json.loads(json.dumps(export, default=str)),
        headers={"Content-Disposition": 'attachment; filename="dzik-os-export.json"'},
    )


@router.get("/export.xlsx")
def export_my_data_excel(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Ten sam eksport co /export, w formacie arkusza kalkulacyjnego —
    jeden arkusz na tabelę, wygodny do przejrzenia w Excelu/LibreOffice."""
    export = _collect_export(db, user)
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in export.items():
        if name == "user" or not isinstance(rows, list):
            continue
        sheet_name = name[:31]  # limit Excela na długość nazwy arkusza
        ws = wb.create_sheet(sheet_name)
        if not rows:
            ws.append(["(brak danych)"])
            continue
        headers = sorted({k for row in rows for k in row.keys()})
        ws.append(headers)
        for row in rows:
            ws.append([
                json.dumps(row[h], ensure_ascii=False, default=str)
                if isinstance(row.get(h), (dict, list))
                else row.get(h)
                for h in headers
            ])
        for idx, h in enumerate(headers, start=1):
            width = max(10, min(40, len(h) + 2))
            ws.column_dimensions[get_column_letter(idx)].width = width
    info = wb.create_sheet("konto", 0)
    info.append(["pole", "wartość"])
    for k, v in export["user"].items():
        info.append([k, v])

    from io import BytesIO

    buf = BytesIO()
    wb.save(buf)
    record_event(
        db,
        action="DATA_EXPORTED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"export_version": export["export_version"], "format": "xlsx"},
        summary="Eksport danych użytkownika (Excel)",
    )
    db.commit()
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="dzik-os-export.xlsx"'},
    )


@router.post("/deletion-request")
def request_deletion(
    body: DeletionRequestIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Usunięcie danych: anonimizacja konta i danych osobowych oraz
    fizyczne usunięcie plików. Zapisy audytowe (łańcuch zdarzeń) pozostają —
    zawierają wyłącznie identyfikatory, nie dane zdrowotne w postaci jawnej.
    Operacja jest nieodwracalna i wymaga hasła + frazy potwierdzającej."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=403, detail="Nieprawidłowe hasło")
    client_id = require_client_self(db, user)

    for stored in db.query(StoredFile).filter(StoredFile.owner_user_id == client_id).all():
        storage.delete(stored)
        stored.deleted_at = stored.deleted_at or "deleted"
        stored.filename = "usunięto"
        stored.storage_path = ""
    for f in db.query(ProfileField).filter(ProfileField.client_id == client_id).all():
        f.value = "[usunięto]"
    for m in db.query(Measurement).filter(Measurement.client_id == client_id).all():
        db.delete(m)
    for p in db.query(ProgressPhoto).filter(ProgressPhoto.client_id == client_id).all():
        db.delete(p)
    for o in db.query(Observation).filter(Observation.client_id == client_id).all():
        db.delete(o)
    for n in db.query(DailyNutritionLog).filter(DailyNutritionLog.client_id == client_id).all():
        db.delete(n)
    for sc in db.query(ScheduleCompletion).filter(ScheduleCompletion.client_id == client_id).all():
        sc.note = None
    for c in db.query(WeeklyCheckin).filter(WeeklyCheckin.client_id == client_id).all():
        c.payload_json = "{}"
        c.coach_response = None
    for r in (
        db.query(CheckinRevision)
        .join(WeeklyCheckin, CheckinRevision.checkin_id == WeeklyCheckin.id)
        .filter(WeeklyCheckin.client_id == client_id)
        .all()
    ):
        r.payload_json = "{}"
    threads = db.query(MessageThread).filter(MessageThread.client_id == client_id).all()
    for t in threads:
        for m in db.query(Message).filter(Message.thread_id == t.id).all():
            m.body = "[usunięto]"
            m.file_id = None
    user.email = f"deleted-{user.id.lower()}@example.invalid"
    user.display_name = "Konto usunięte"
    user.status = "DELETED"
    user.anonymized_at = now_iso()
    record_event(
        db,
        action="ACCOUNT_ANONYMIZED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"user_id": user.id},
        summary="Anonimizacja konta i usunięcie danych na żądanie użytkownika",
    )
    db.commit()
    return {"ok": True, "status": "DELETED"}

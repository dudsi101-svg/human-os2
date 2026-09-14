from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from .. import aggregates, notifications, plan_templates, sheet_import
from ..authz import (
    DOMAIN_HEALTH,
    DOMAIN_TRAINING,
    coach_can_access_client,
    deny,
    require_attachable_file,
    require_owned_resource,
    resolve_client_access,
)
from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..models import (
    Exercise,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    WorkoutEntry,
    WorkoutSession,
    new_id,
    now_iso,
)
from ..postepy import rekordy as R
from ..postepy import serwis as postepy_serwis
from ..schemas import PlanCreateIn, PlanDayIn, PlanVersionIn, WorkoutSessionIn, dni_do_zapisu
from ..security import current_user, require_role
from ..storage import _read_limited
from ..wiedza import slad as wiedza_slad

router = APIRouter(prefix="/api", tags=["plans"])


def _validate_exercise_refs(db: Session, coach: User, days: list[PlanDayIn]) -> None:
    """`exercise_id` w pozycji planu musi wskazywać AKTYWNE ćwiczenie z
    bazy TEGO trenera — cudzy ani nieistniejący identyfikator nie da się
    wstawić (422). Odniesienie pozostaje miękkie: nazwa jest zapisana w
    planie, więc późniejsza archiwizacja ćwiczenia niczego nie psuje."""
    wanted = {
        ex.exercise_id
        for day in days
        for ex in day.exercises
        if ex.exercise_id
    }
    if not wanted:
        return
    known = {
        row.id
        for row in db.query(Exercise)
        .filter(
            Exercise.id.in_(wanted),
            Exercise.coach_id == coach.id,
            Exercise.status == "ACTIVE",
        )
        .all()
    }
    missing = sorted(wanted - known)
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Ćwiczenie spoza Twojej aktywnej bazy: " + ", ".join(missing),
        )


def _version_out(v: TrainingPlanVersion) -> dict:
    return {
        "id": v.id,
        "plan_id": v.plan_id,
        "version_no": v.version_no,
        "reason": v.reason,
        "content": json.loads(v.content_json),
        "created_by": v.created_by,
        "created_at": v.created_at,
    }


def _plan_out(db: Session, p: TrainingPlan, *, with_current: bool = True) -> dict:
    out = {
        "id": p.id,
        "client_id": p.client_id,
        "coach_id": p.coach_id,
        "title": p.title,
        "status": p.status,
        "current_version_no": p.current_version_no,
        "is_template": p.is_template,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }
    if with_current and p.current_version_no:
        v = (
            db.query(TrainingPlanVersion)
            .filter_by(plan_id=p.id, version_no=p.current_version_no)
            .one_or_none()
        )
        out["current_version"] = _version_out(v) if v else None
    return out


@router.post("/plans", status_code=201)
def create_plan(
    body: PlanCreateIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    if body.client_id is not None:
        resolve_client_access(db, coach, body.client_id, action="write", domain=DOMAIN_TRAINING)
    _validate_exercise_refs(db, coach, body.version.days)
    plan = TrainingPlan(
        id=new_id("PLN"),
        client_id=body.client_id,
        coach_id=coach.id,
        title=body.title,
        is_template=body.client_id is None,
        current_version_no=1,
    )
    db.add(plan)
    version = TrainingPlanVersion(
        id=new_id("PLV"),
        plan_id=plan.id,
        version_no=1,
        reason=body.version.reason,
        content_json=json.dumps(
            {"days": dni_do_zapisu(body.version.days)}, ensure_ascii=False
        ),
        created_by=coach.id,
    )
    db.add(version)
    if plan.client_id is not None:
        # Cardio (0.73.0): ślad H_CARDIO dla każdej pozycji cardio — w tej
        # samej transakcji co wersja (szablon trenera bez klienta = bez śladu).
        wiedza_slad.slady_cardio(db, owner_id=plan.client_id, plan_id=plan.id, plan_revision=1,
                                 content=json.loads(version.content_json))
    record_event(
        db,
        action="PLAN_CREATED",
        actor_id=coach.id,
        subject_ids=[body.client_id or coach.id],
        payload={"plan_id": plan.id, "title": plan.title, "version_no": 1,
                 "is_template": plan.is_template, "reason": body.version.reason},
        summary=f"Nowy plan treningowy: {plan.title} (v1)",
    )
    db.commit()
    return {"id": plan.id, "version_id": version.id, "version_no": 1}


@router.post("/plans/{plan_id}/versions", status_code=201)
def create_plan_version(
    plan_id: str,
    body: PlanVersionIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Nowa wersja planu — poprzednia wersja pozostaje niezmieniona i dostępna.
    Wymagany jest powód zmiany (decyzja trenera jest audytowana)."""
    plan = require_owned_resource(
        db.get(TrainingPlan, plan_id), actor=coach, resource=f"plan:{plan_id}"
    )
    if plan.client_id is not None:
        resolve_client_access(db, coach, plan.client_id, action="write", domain=DOMAIN_TRAINING)
    _validate_exercise_refs(db, coach, body.days)
    next_no = plan.current_version_no + 1
    version = TrainingPlanVersion(
        id=new_id("PLV"),
        plan_id=plan.id,
        version_no=next_no,
        reason=body.reason,
        content_json=json.dumps(
            {"days": dni_do_zapisu(body.days)}, ensure_ascii=False
        ),
        created_by=coach.id,
    )
    plan.current_version_no = next_no
    plan.updated_at = now_iso()
    db.add(version)
    if plan.client_id is not None:
        # Wiedza (0.56.0): decyzja trenera = oryginalny powód wersji, zapisany
        # w tej samej transakcji; nic nie jest dopisywane algorytmicznie.
        wiedza_slad.slad_wersji_trenera(db, owner_id=plan.client_id, plan_id=plan.id,
                                        plan_revision=next_no, reason=body.reason)
        wiedza_slad.slady_cardio(db, owner_id=plan.client_id, plan_id=plan.id, plan_revision=next_no,
                                 content=json.loads(version.content_json))
    record_event(
        db,
        action="PLAN_VERSION_CREATED",
        actor_id=coach.id,
        subject_ids=[plan.client_id or coach.id],
        payload={"plan_id": plan.id, "version_no": next_no, "reason": body.reason},
        summary=f"Plan '{plan.title}': nowa wersja v{next_no} — {body.reason}",
    )
    notification = None
    if plan.client_id is not None:
        notification = notifications.notify_now(
            db,
            user_id=plan.client_id,
            category="ZMIANA_PLANU",
            title="Nowa wersja planu treningowego",
            body="Trener zaktualizował Twój plan — sprawdź, co się zmieniło.",
            url="/plan",
            dedup_key=f"plan-version:{version.id}",
        )
    db.commit()
    notifications.publish_realtime(notification)
    return {"version_id": version.id, "version_no": next_no}


@router.post("/plans/{template_id}/copy-to/{client_id}", status_code=201)
def copy_template_to_client(
    template_id: str,
    client_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Kopiuje bieżącą wersję szablonu jako NOWY plan klienta (v1).
    Kopia jest niezależna — późniejsza edycja szablonu nie zmienia planów
    klientów (pełna proweniencja zamiast współdzielenia obiektu)."""
    template = db.get(TrainingPlan, template_id)
    if template is None or not template.is_template:
        raise HTTPException(status_code=404, detail="Nie znaleziono szablonu")
    if template.coach_id != coach.id:
        # Szablon innego trenera — logowana odmowa zasobowa.
        deny(coach.id, f"plan_template:{template_id}")
    resolve_client_access(db, coach, client_id, action="write", domain=DOMAIN_TRAINING)
    source_version = (
        db.query(TrainingPlanVersion)
        .filter_by(plan_id=template.id, version_no=template.current_version_no)
        .one_or_none()
    )
    if source_version is None:
        raise HTTPException(status_code=422, detail="Szablon nie ma żadnej wersji")
    plan = TrainingPlan(
        id=new_id("PLN"),
        client_id=client_id,
        coach_id=coach.id,
        title=template.title,
        current_version_no=1,
    )
    db.add(plan)
    version = TrainingPlanVersion(
        id=new_id("PLV"),
        plan_id=plan.id,
        version_no=1,
        reason=f"Skopiowano z szablonu „{template.title}”",
        content_json=source_version.content_json,
        created_by=coach.id,
        # Pochodzenie (0.58.0): kopia jest niezależna, ale wiadomo skąd jest.
        source_template_id=template.id,
        source_template_version_no=template.current_version_no,
    )
    db.add(version)
    record_event(
        db,
        action="PLAN_CREATED",
        actor_id=coach.id,
        subject_ids=[client_id],
        payload={"plan_id": plan.id, "title": plan.title, "version_no": 1,
                 "copied_from_template_id": template.id},
        summary=f"Plan „{plan.title}” skopiowany z szablonu dla klienta",
    )
    db.commit()
    return {"id": plan.id, "version_id": version.id, "version_no": 1}


@router.get("/coach/plan-templates")
def builtin_plan_templates(
    coach: User = Depends(require_role("COACH")),
):
    """Wbudowane szablony treningowe (materiał merytoryczny, nie dane osób).

    Sama lista niczego nie tworzy — trener wybiera szablon, a dopiero import
    robi z niego JEGO szablon (zasada „Szablon ≠ plan klienta")."""
    return {
        "templates": plan_templates.list_templates(),
        "progressions": plan_templates.progression_models(),
    }


@router.get("/plans/templates")
def list_templates(
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(TrainingPlan)
        .filter(TrainingPlan.coach_id == coach.id, TrainingPlan.is_template.is_(True),
                # 0.58.0: usunięty (zarchiwizowany) szablon znika z listy; historia zostaje.
                TrainingPlan.status == "ACTIVE")
        .all()
    )
    return {"templates": [_plan_out(db, p) for p in rows]}


@router.get("/clients/{client_id}/plans")
def client_plans(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, domain=DOMAIN_TRAINING)
    rows = (
        db.query(TrainingPlan)
        .filter(TrainingPlan.client_id == client_id)
        .order_by(TrainingPlan.created_at.desc())
        .all()
    )
    return {"plans": [_plan_out(db, p) for p in rows]}


@router.get("/plans/{plan_id}/versions")
def plan_versions(
    plan_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    plan = db.get(TrainingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if plan.client_id is not None:
        resolve_client_access(db, user, plan.client_id, domain=DOMAIN_TRAINING)
    elif plan.coach_id != user.id:
        # Szablon (bez klienta) widzi wyłącznie jego autor.
        deny(user.id, f"plan:{plan_id}")
    rows = (
        db.query(TrainingPlanVersion)
        .filter(TrainingPlanVersion.plan_id == plan_id)
        .order_by(TrainingPlanVersion.version_no)
        .all()
    )
    return {"plan": _plan_out(db, plan, with_current=False),
            "versions": [_version_out(v) for v in rows]}


@router.post("/clients/{client_id}/workouts", status_code=201)
def log_workout(
    client_id: str,
    body: WorkoutSessionIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_TRAINING)
    version = db.get(TrainingPlanVersion, body.plan_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono wersji planu")
    plan = db.get(TrainingPlan, version.plan_id)
    if plan is None or plan.client_id != client_id:
        # Wersja planu innego klienta (IDOR na plan_version_id) — logowana
        # odmowa; komunikat nie potwierdza istnienia cudzego planu.
        deny(user.id, f"plan_version:{body.plan_version_id}")
    session = WorkoutSession(
        id=new_id("WKS"),
        client_id=client_id,
        plan_version_id=version.id,
        day_index=body.day_index,
        performed_on=body.performed_on,
        status=body.status,
        comment=body.comment,
        pain_flag=body.pain_flag,
        pain_note=body.pain_note,
    )
    db.add(session)
    # Sesja przed swoimi pozycjami: SQLAlchemy grupuje wstawienia per tabela,
    # więc bez tego pozycje trafiają do bazy przed sesją, na którą wskazują
    # (klucz obcy session_id).
    db.flush()
    wpisy: list[WorkoutEntry] = []
    for e in body.entries:
        if e.file_id is not None:
            # Załącznik wpisu treningowego musi być plikiem tego klienta.
            require_attachable_file(db, user, e.file_id, owner_id=client_id)
        wpis = WorkoutEntry(
            id=new_id("WKE"),
            session_id=session.id,
            exercise_index=e.exercise_index,
            exercise_name=e.exercise_name,
            result=e.result,
            # Jednostki normalizowane do kg PRZY ZAPISIE (Postępy §8.2.6);
            # w bazie zostaje {"weight_kg", "reps"} + "warmup": true tylko dla
            # rozgrzewki — seria robocza ma ten sam kształt co przed 0.66.0.
            sets_json=(
                json.dumps([{"weight_kg": R.normalizuj_ciezar(s.weight_kg, s.unit), "reps": s.reps,
                             **({"warmup": True} if s.warmup else {})} for s in e.sets]) if e.sets else None
            ),
            comment=e.comment,
            file_id=e.file_id,
            # Cardio (0.73.0): pola bez serii; wpis siłowy zostawia NULL-e.
            duration_min=e.duration_min,
            avg_hr=e.avg_hr,
            rpe=e.rpe,
            distance_km=e.distance_km,
            machine=e.machine,
        )
        db.add(wpis)
        wpisy.append(wpis)
    db.flush()
    # Postępy (0.66.0): rekordy ćwiczeń z sesji i agregat tygodnia przeliczane
    # przy zapisie; jedno zbiorcze powiadomienie na sesję (§8.3). Za flagą —
    # bez niej zapis sesji zachowuje się dokładnie jak przed 0.66.0 (tabele
    # z migracji 36 zostają puste; historię przelicza backfill po włączeniu).
    nowe_rekordy: list = []
    powiadomienie = None
    if settings.monitoring_tab_enabled:
        nowe_rekordy = postepy_serwis.po_zapisie_sesji(db, session, wpisy)
        powiadomienie = postepy_serwis.powiadom_o_rekordach(db, client_id, session.id, nowe_rekordy)
    record_event(
        db,
        action="WORKOUT_LOGGED",
        actor_id=user.id,
        subject_ids=[client_id],
        payload={"session_id": session.id, "plan_id": plan.id,
                 "version_no": version.version_no, "day_index": body.day_index,
                 "status": body.status, "pain_flag": body.pain_flag},
        summary=f"Trening {body.performed_on}: {body.status}"
        + (" (zgłoszono ból)" if body.pain_flag else ""),
    )
    db.commit()
    if powiadomienie is not None:
        notifications.publish_realtime(powiadomienie)
    return {"id": session.id, "new_records": len(nowe_rekordy)}


@router.get("/clients/{client_id}/workouts")
def list_workouts(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, domain=DOMAIN_TRAINING)
    # Tętno średnie z sesji cardio (0.73.0) to dana zdrowotna: klient widzi swoje,
    # trener tylko przy dostępie do domeny zdrowotnej — inaczej pole jest maskowane
    # po stronie serwera (jak `hidden_for_client` w Postępach), reszta wpisu zostaje.
    tetno_widoczne = user.id == client_id or coach_can_access_client(
        db, user.id, client_id, action="read", domain=DOMAIN_HEALTH
    )
    sessions = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.client_id == client_id)
        .order_by(WorkoutSession.performed_on.desc())
        .limit(200)
        .all()
    )
    # Wpisy wszystkich sesji JEDNYM zapytaniem — wcześniej każda sesja
    # kosztowała osobne zapytanie, więc koszt listy rósł z historią
    # treningów klienta (po roku współpracy to ponad sto zapytań na jedno
    # wejście w zakładkę). Patrz aggregates.py i docs/SYMULACJA.md.
    entries_by_session = aggregates.workout_entries_by_session(
        db, [s.id for s in sessions]
    )
    out = []
    for s in sessions:
        entries = entries_by_session.get(s.id, [])
        out.append(
            {
                "id": s.id,
                "plan_version_id": s.plan_version_id,
                "day_index": s.day_index,
                "performed_on": s.performed_on,
                "status": s.status,
                "comment": s.comment,
                "pain_flag": s.pain_flag,
                "pain_note": s.pain_note,
                "entries": [
                    {
                        "exercise_index": e.exercise_index,
                        "exercise_name": e.exercise_name,
                        "result": e.result,
                        "sets": json.loads(e.sets_json) if e.sets_json else [],
                        "comment": e.comment,
                        "file_id": e.file_id,
                        "duration_min": e.duration_min,
                        "avg_hr": e.avg_hr if tetno_widoczne else None,
                        "rpe": e.rpe,
                        "distance_km": e.distance_km,
                        "machine": e.machine,
                    }
                    for e in entries
                ],
            }
        )
    return {"workouts": out}


# --- Import / eksport szablonów z pliku (CSV / XLSX) -------------------

@router.get("/coach/plan-templates/import-schema")
def templates_import_schema(coach: User = Depends(require_role("COACH"))):
    """Kontrakt pliku importu szablonów: kolumny, wymagalność, przykłady.
    Interfejs buduje z tego instrukcję — opis w aplikacji nie może
    rozjechać się z tym, co realnie przyjmuje import."""
    return {
        "columns": sheet_import.schema_dict(sheet_import.TEMPLATE_COLUMNS),
        "max_rows": sheet_import.MAX_ROWS,
        "max_bytes": sheet_import.MAX_BYTES,
        "max_days": sheet_import.MAX_DAYS,
        "max_items_per_day": sheet_import.MAX_ITEMS_PER_DAY,
        "formats": [".csv", ".xlsx"],
    }


@router.get("/coach/plan-templates/import-example")
def templates_import_example(coach: User = Depends(require_role("COACH"))):
    """Wzór pliku do pobrania — nagłówek i jeden wiersz przykładowy."""
    return Response(
        content=sheet_import.example_csv(sheet_import.TEMPLATE_COLUMNS),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dzik-os-szablony-wzor.csv"'},
    )


@router.get("/coach/plan-templates/export-file")
def templates_export_file(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    """Eksport wszystkich szablonów trenera w formacie importu (bieżące
    wersje). Prawo wyjścia i zarazem droga do masowej edycji w arkuszu."""
    plans = (
        db.query(TrainingPlan)
        .filter(
            TrainingPlan.coach_id == coach.id,
            TrainingPlan.is_template.is_(True),
            TrainingPlan.status == "ACTIVE",
        )
        .order_by(TrainingPlan.title)
        .all()
    )
    pairs = []
    for plan in plans:
        version = (
            db.query(TrainingPlanVersion)
            .filter_by(plan_id=plan.id, version_no=plan.current_version_no)
            .one_or_none()
        )
        if version is not None:
            pairs.append((plan, version.content_json))
    record_event(
        db, action="PLAN_TEMPLATES_EXPORTED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"templates": len(pairs), "format": "csv"},
        summary=f"Szablony treningowe: eksport {len(pairs)} szablonów do CSV",
    )
    db.commit()
    return Response(
        content=sheet_import.templates_csv(pairs),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dzik-os-szablony.csv"'},
    )


@router.post("/coach/plan-templates/import-file")
async def templates_import_file(
    file: UploadFile,
    dry_run: bool = Query(True),
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Import szablonów treningowych z pliku do zasobów ZALOGOWANEGO
    trenera.

    Domyślnie `dry_run=true` — pełny raport bez zapisu. Szablon o tej samej
    nazwie nie jest nadpisywany: dostaje nową wersję z powodem wskazującym
    plik, a poprzednie wersje pozostają dostępne (zasada Human OS: brak
    cichego nadpisywania, pełna historia). Szablon o identycznej treści nie
    dostaje pustej wersji „bo import”.

    Szablony NIE są przypisane do żadnego klienta (`client_id = NULL`) —
    import nie dotyka planów prowadzonych osób i nie wymaga ich zgód."""
    # Limit jak przy każdym uploadzie — bez tego jeden plik zapełnia RAM
    # (znalezisko K-002 z przeglądu krzyżowego 2026-08-18).
    raw = await _read_limited(file, settings.max_upload_mb * 1024 * 1024)
    source_ref = (file.filename or "plik")[:200]
    try:
        rows, unknown, warnings = sheet_import.read_table(
            file.filename or "", raw, sheet_import.TEMPLATE_COLUMNS
        )
        report = sheet_import.import_templates_sheet(
            db, coach.id, rows, dry_run=dry_run, source_ref=source_ref,
        )
    except sheet_import.SheetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    report.unknown_columns = unknown
    report.warnings = warnings + report.warnings
    snapshot_id = sheet_import.store_snapshot(db, coach.id, report)
    if not dry_run:
        record_event(
            db, action="PLAN_TEMPLATES_IMPORTED", actor_id=coach.id,
            subject_ids=[coach.id],
            payload={
                "source": source_ref, "rows": report.rows_read,
                "created": report.created, "updated": report.updated,
                "skipped": report.skipped, "linked": report.linked,
                "unlinked": len(report.unlinked_exercises),
            },
            summary=f"Szablony treningowe: import z pliku „{source_ref}” — "
                    f"{report.created} nowych, {report.updated} nowych wersji",
        )
        db.commit()
    out = report.as_dict()
    out["snapshot_id"] = snapshot_id
    return out


# --- Trasy z parametrem NA KOŃCU pliku -------------------------------
#
# Kolejność rejestracji decyduje o dopasowaniu: `/coach/plan-templates/
# {template_id}` pasuje także do `/coach/plan-templates/import-schema`,
# `/import-example` i `/export-file`. Gdy trasa z parametrem stała wyżej,
# przechwytywała te trzy i zwracała „Nie znaleziono szablonu" — import
# własnej bazy z pliku przestawał działać, mimo że jego kod był poprawny.
# Dlatego trasy statyczne muszą być rejestrowane PRZED parametrycznymi.

@router.get("/coach/plan-templates/{template_id}")
def builtin_plan_template(
    template_id: str,
    coach: User = Depends(require_role("COACH")),
):
    """Podgląd szablonu PRZED importem — trener widzi, co dostanie."""
    tpl = plan_templates.get_template(template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono szablonu")
    return {**tpl, "days": plan_templates.build_days(template_id)}


@router.post("/coach/plan-templates/{template_id}/import", status_code=201)
def import_builtin_plan_template(
    template_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Tworzy KOPIĘ wbudowanego szablonu w bibliotece trenera.

    Od tego momentu jest to zwykły szablon trenera: można go edytować
    i skopiować klientowi istniejącą ścieżką `/plans/{id}/copy-to/{client}`.
    Import wolno powtórzyć — powstaje kolejna, niezależna kopia, bo szablon
    mógł zostać wcześniej przerobiony i nie nadpisujemy cudzej pracy.
    """
    tpl = plan_templates.get_template(template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono szablonu")

    dni = plan_templates.build_days(
        template_id, plan_templates.exercise_ids_for_coach(db, coach.id)
    )
    plan = TrainingPlan(
        id=new_id("PLN"),
        client_id=None,
        coach_id=coach.id,
        title=str(tpl["name"]),
        is_template=True,
        current_version_no=1,
    )
    db.add(plan)
    db.flush()  # plan przed wersją (klucz obcy plan_id)
    version = TrainingPlanVersion(
        id=new_id("PLV"),
        plan_id=plan.id,
        version_no=1,
        reason=f"Import wbudowanego szablonu {template_id}",
        content_json=json.dumps({"days": dni}, ensure_ascii=False),
        created_by=coach.id,
    )
    db.add(version)
    powiazane = sum(1 for d in dni for e in d["exercises"] if e.get("exercise_id"))
    record_event(
        db,
        action="PLAN_CREATED",
        actor_id=coach.id,
        subject_ids=[coach.id],
        payload={
            "plan_id": plan.id, "title": plan.title, "version_no": 1,
            "is_template": True, "source_template": template_id,
            "linked_exercises": powiazane,
            "reason": f"Import wbudowanego szablonu {template_id}",
        },
        summary=f"Import szablonu treningowego: {plan.title}",
    )
    db.commit()
    return {
        "id": plan.id,
        "version_id": version.id,
        "version_no": 1,
        "days": len(dni),
        "exercises": sum(len(d["exercises"]) for d in dni),
        # Ile pozycji dostało link do karty ćwiczenia trenera. Reszta ma samą
        # nazwę — plan działa, brakuje tylko instrukcji/filmu przy ćwiczeniu.
        "linked_exercises": powiazane,
    }


# --- Panel trenera (0.58.0): archiwizacja ≠ odpięcie; duplikacja ------------------


def _plan_do_zmiany(db: Session, coach: User, plan_id: str) -> TrainingPlan:
    plan = require_owned_resource(db.get(TrainingPlan, plan_id), actor=coach, resource=f"plan:{plan_id}")
    if plan.client_id is not None:
        resolve_client_access(db, coach, plan.client_id, action="write", domain=DOMAIN_TRAINING)
    return plan


@router.post("/plans/{plan_id}/archiwizuj")
def archive_plan(plan_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Archiwizacja: plan znika z aktywnych, historia wersji i wykonań
    zostaje. To celowe zakończenie planu (nie publikuje się pustego planu)."""
    plan = _plan_do_zmiany(db, coach, plan_id)
    if plan.status == "ARCHIVED":
        return {"ok": True, "status": plan.status}
    poprzedni = plan.status
    plan.status = "ARCHIVED"
    plan.updated_at = now_iso()
    record_event(db, action="PLAN_ARCHIVED", actor_id=coach.id, subject_ids=[plan.client_id or coach.id],
                 payload={"plan_id": plan.id, "from": poprzedni, "is_template": plan.is_template},
                 summary=f"Plan „{plan.title}” zarchiwizowany")
    db.commit()
    return {"ok": True, "status": plan.status}


@router.post("/plans/{plan_id}/odepnij")
def unassign_plan(plan_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Odpięcie od klienta: plan przestaje być widoczny podopiecznemu, ale
    zostaje z pełną historią (client_id zachowany dla wykonań)."""
    plan = _plan_do_zmiany(db, coach, plan_id)
    if plan.client_id is None:
        raise HTTPException(status_code=422, detail="Szablon nie jest przypisany do klienta")
    poprzedni = plan.status
    plan.status = "UNASSIGNED"
    plan.updated_at = now_iso()
    record_event(db, action="PLAN_UNASSIGNED", actor_id=coach.id, subject_ids=[plan.client_id],
                 payload={"plan_id": plan.id, "from": poprzedni},
                 summary=f"Plan „{plan.title}” odpięty od klienta")
    db.commit()
    return {"ok": True, "status": plan.status}


@router.post("/plans/{plan_id}/duplikuj", status_code=201)
def duplicate_plan(plan_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Duplikat bieżącej wersji jako nowy plan (v1) tego samego klienta albo
    nowy szablon — z nowymi identyfikatorami elementów."""
    from ..publikacja import elementy as _el

    plan = _plan_do_zmiany(db, coach, plan_id)
    zrodlo = (db.query(TrainingPlanVersion)
              .filter_by(plan_id=plan.id, version_no=plan.current_version_no).one_or_none())
    if zrodlo is None:
        raise HTTPException(status_code=422, detail="Plan nie ma żadnej wersji")
    tresc = _el.znormalizuj("training", json.loads(zrodlo.content_json))
    for d in tresc["days"]:
        d["id"] = _el.nowy_id()
        for e in d["exercises"]:
            e["id"] = _el.nowy_id()
    nowy = TrainingPlan(id=new_id("PLN"), client_id=plan.client_id, coach_id=coach.id,
                        title=f"{plan.title} (kopia)", current_version_no=1, is_template=plan.is_template)
    db.add(nowy)
    db.add(TrainingPlanVersion(id=new_id("PLV"), plan_id=nowy.id, version_no=1,
                               reason=f"Duplikat planu „{plan.title}” (v{plan.current_version_no})",
                               content_json=json.dumps(tresc, ensure_ascii=False), created_by=coach.id,
                               source_template_id=zrodlo.source_template_id,
                               source_template_version_no=zrodlo.source_template_version_no))
    record_event(db, action="PLAN_CREATED", actor_id=coach.id, subject_ids=[plan.client_id or coach.id],
                 payload={"plan_id": nowy.id, "title": nowy.title, "version_no": 1, "duplicated_from": plan.id},
                 summary=f"Plan „{nowy.title}” utworzony jako duplikat")
    db.commit()
    return {"id": nowy.id, "version_no": 1, "title": nowy.title}

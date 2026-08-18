"""Baza ćwiczeń (know-how trenera) — technika wykonania, najczęstsze
błędy, wskazówki, warianty i mapa pracujących mięśni. Broadcast do
wszystkich aktywnie prowadzonych klientów; treść i odpowiedzialność
merytoryczna należą do trenera (system tylko przechowuje i pokazuje).

Granica roli: to know-how treningowe, nie porada medyczna. Uwagi
bezpieczeństwa kierują do konsultacji przy bólu lub urazie — aplikacja
nie ocenia stanu zdrowia i NIE dobiera ćwiczeń automatycznie: wybór
zawsze należy do trenera."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from .. import exercise_parser, exercise_parser_ai, sheet_import
from ..authz import require_owned_resource
from ..db import get_db
from ..exercise_catalog_v2 import LIBRARY_REF
from ..hos_bridge import record_event
from ..import_exercises import import_library
from ..models import (
    CoachClientRelationship,
    Exercise,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    new_id,
    now_iso,
)
from ..muscles import (
    EXERCISE_LEVELS,
    LEVEL_LABELS,
    MOVEMENT_PATTERNS,
    MUSCLE_GROUPS,
    MUSCLE_LABELS,
    PATTERN_LABELS,
    fold,
    join_muscles,
    split_muscles,
)
from ..observability import metrics
from ..schemas import ExerciseDescriptionIn, ExerciseLibraryItemIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["exercises"])

DEFAULT_LIMIT = 60
MAX_LIMIT = 200

#: Ile ćwiczeń pokazuje skrót „ostatnio używane”. Trener w praktyce
#: korzysta z kilkudziesięciu pozycji, nie z całego katalogu — ten skrót
#: ma oszczędzać szukanie, a nie być drugą listą do przewijania.
RECENT_LIMIT = 12
#: Ile NAJŚWIEŻSZYCH wersji planów przeglądamy, żeby je wyznaczyć.
#: Stały koszt zapytania niezależnie od stażu trenera.
RECENT_VERSIONS_SCANNED = 60


def _load_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(x) for x in parsed] if isinstance(parsed, list) else []


def _dump_list(values: list[str]) -> str | None:
    cleaned = [v.strip() for v in values if v and v.strip()]
    return json.dumps(cleaned, ensure_ascii=False) if cleaned else None


def _out(item: Exercise, *, for_coach: bool = False) -> dict:
    """Ćwiczenie w postaci API.

    `review_reason` („opis techniki jest szablonem z importu, warto opisać
    po swojemu”) jest NOTATKĄ ROBOCZĄ TRENERA i wychodzi wyłącznie na
    widoki trenera. Klientowi nie pokazujemy jej w żadnej postaci: dla
    niego wyglądałaby jak ocena jakości ćwiczenia, którą wystawił system —
    a system tu niczego nie ocenia."""
    out = {
        "id": item.id, "coach_id": item.coach_id, "name": item.name,
        "name_en": item.name_en,
        "muscle_group": item.muscle_group, "how_to": item.how_to,
        "benefit": item.benefit, "equipment": item.equipment,
        "video_url": item.video_url, "status": item.status,
        "muscles_primary": split_muscles(item.muscles_primary),
        "muscles_secondary": split_muscles(item.muscles_secondary),
        "level": item.level, "pattern": item.pattern,
        "steps": _load_list(item.steps_json),
        "mistakes": _load_list(item.mistakes_json),
        "cues": _load_list(item.cues_json),
        "tags": _load_list(item.tags_json),
        "safety": item.safety, "easier": item.easier, "harder": item.harder,
        "tempo_hint": item.tempo_hint, "breathing": item.breathing,
        "source_kind": item.source_kind, "source_engine": item.source_engine,
        "source_ref": item.source_ref,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }
    if for_coach:
        out["review_reason"] = item.review_reason
    return out


def _apply_fields(item: Exercise, body: ExerciseLibraryItemIn) -> None:
    item.name, item.muscle_group, item.how_to = body.name, body.muscle_group, body.how_to
    item.benefit, item.equipment, item.video_url = body.benefit, body.equipment, body.video_url
    item.muscles_primary = join_muscles(body.muscles_primary)
    item.muscles_secondary = join_muscles(body.muscles_secondary)
    item.level, item.pattern = body.level, body.pattern
    item.steps_json = _dump_list(body.steps)
    item.mistakes_json = _dump_list(body.mistakes)
    item.cues_json = _dump_list(body.cues)
    item.safety, item.easier, item.harder = body.safety, body.easier, body.harder
    item.tempo_hint, item.breathing = body.tempo_hint, body.breathing
    item.source_kind, item.source_engine = body.source_kind, body.source_engine
    item.name_en = body.name_en
    item.tags_json = _dump_list(body.tags)
    item.source_ref = body.source_ref
    # Trener zdejmuje notatkę „opis ogólny” po prostu przez zapis bez niej —
    # to jego notatka, nie flaga systemu.
    item.review_reason = body.review_reason


def _matches(
    item: Exercise, *, q: str | None, muscle: str | None, muscle_group: str | None,
    equipment: str | None, level: str | None, pattern: str | None,
) -> bool:
    """Filtrowanie po stronie aplikacji: baza to katalog rzędu setek
    pozycji, a wyszukiwanie musi być odporne na polskie znaki (czego
    SQLite LIKE nie zapewnia)."""
    if q:
        needle = fold(q)
        haystack = fold(" ".join(filter(None, [
            item.name, item.name_en or "", item.equipment or "",
            " ".join(_load_list(item.tags_json)),
        ])))
        if needle not in haystack:
            return False
    if muscle and muscle not in (
        split_muscles(item.muscles_primary) + split_muscles(item.muscles_secondary)
    ):
        return False
    if muscle_group and item.muscle_group != muscle_group:
        return False
    if equipment and fold(equipment) not in fold(item.equipment or ""):
        return False
    if level and item.level != level:
        return False
    return not (pattern and item.pattern != pattern)


def _page(
    rows: list[Exercise], *, limit: int, offset: int, filters: dict,
    for_coach: bool = False,
) -> dict:
    matched = [r for r in rows if _matches(r, **filters)]
    window = matched[offset:offset + limit]
    return {
        "items": [_out(i, for_coach=for_coach) for i in window],
        "total": len(matched),
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(window) < len(matched),
    }


def _filters(
    q: str | None, muscle: str | None, muscle_group: str | None,
    equipment: str | None, level: str | None, pattern: str | None,
) -> dict:
    if muscle and muscle not in MUSCLE_LABELS:
        raise HTTPException(status_code=422, detail="Nieznana partia mięśniowa")
    if level and level not in EXERCISE_LEVELS:
        raise HTTPException(status_code=422, detail="Nieznany poziom")
    if pattern and pattern not in MOVEMENT_PATTERNS:
        raise HTTPException(status_code=422, detail="Nieznany wzorzec ruchu")
    if muscle_group and muscle_group not in MUSCLE_GROUPS:
        raise HTTPException(status_code=422, detail="Nieznana grupa mięśniowa")
    return {
        "q": q, "muscle": muscle, "muscle_group": muscle_group,
        "equipment": equipment, "level": level, "pattern": pattern,
    }


@router.get("/exercise-dictionaries")
def exercise_dictionaries(_: User = Depends(current_user)):
    """Kontrakt słowników (te same klucze co rysunek sylwetki)."""
    return {
        "muscles": MUSCLE_LABELS,
        "levels": LEVEL_LABELS,
        "patterns": PATTERN_LABELS,
        "muscle_groups": list(MUSCLE_GROUPS),
    }


@router.post("/coach/exercises/parse-description")
def parse_exercise_description(
    body: ExerciseDescriptionIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Czyta wklejony opis ćwiczenia i zwraca PROPOZYCJĘ pól edytora.

    **Nic nie zapisuje.** Ani ćwiczenia, ani opisu, ani propozycji — jedyne,
    co ten endpoint może zmienić w bazie, to licznik zużycia modelu w
    trybie rozszerzonym. Zapis następuje wyłącznie zwykłym
    `POST/PUT /api/coach/exercises`, po tym jak trener zobaczył propozycję,
    poprawił ją i zatwierdził.

    Tryb wybiera się SAM (``exercise_parser_ai.resolve_mode``): silnik
    lokalny działa zawsze, tryb rozszerzony włącza się, gdy operator
    skonfigurował dostawcę i limity nie są wyczerpane. Bramką NIE jest tu
    zgoda `funkcje_ai` podmiotu danych — opis ćwiczenia to know-how
    trenera, nie dane klienta (pełne uzasadnienie w nagłówku
    `exercise_parser_ai.py` i w docs/BAZA_CWICZEN.md).

    Do logów i metryk nie trafia ani jeden znak opisu — wyłącznie liczniki."""
    local = exercise_parser.parse_description(body.description)
    proposal = local.proposal
    unrecognized = local.unrecognized
    needs_confirmation = local.needs_confirmation
    engine = exercise_parser.ENGINE_LOCAL
    mode, mode_reason = exercise_parser_ai.resolve_mode(db, coach.id)
    if mode == exercise_parser.ENGINE_EXTENDED:
        outcome = exercise_parser_ai.request_draft(
            db, user_id=coach.id, description=body.description
        )
        db.commit()  # liczniki zużycia; propozycja nadal nigdzie nie ląduje
        if outcome.ok:
            engine = exercise_parser.ENGINE_EXTENDED
            proposal = outcome.proposal
            # Model dostał w prompcie tę samą regułę podziału mięśni co
            # silnik lokalny: brak rozróżnienia w opisie = wszystko główne.
            # Skoro nie wiemy, czy rozróżnienie było, prosimy o
            # potwierdzenie dokładnie tak samo.
            needs_confirmation = (
                ["muscles_primary", "muscles_secondary"]
                if proposal["muscles_primary"] and not proposal["muscles_secondary"]
                else []
            )
            # Obie listy zostają rozłączne — dokładnie jak w trybie lokalnym.
            unrecognized = [
                key for key in exercise_parser.unrecognized_fields(proposal)
                if key not in needs_confirmation
            ]
            mode_reason = ""
        else:
            mode_reason = outcome.reason
    if engine == exercise_parser.ENGINE_LOCAL and not mode_reason:
        mode_reason = exercise_parser_ai.LOCAL_OK_REASON
    metrics.inc(f"exercise_parse_{engine.lower()}")
    return {
        "engine": engine,
        "mode_reason": mode_reason,
        "proposal": proposal,
        "unrecognized": unrecognized,
        "needs_confirmation": needs_confirmation,
        "field_labels": exercise_parser.FIELD_LABELS,
    }


@router.post("/coach/exercises/import-library")
def import_exercise_library(
    dry_run: bool = Query(True),
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Import gotowej biblioteki ćwiczeń do katalogu ZALOGOWANEGO trenera.

    Domyślnie `dry_run=true`, czyli PRÓBA: zwraca dokładnie ten sam raport,
    ale nie zapisuje ani jednego wiersza. Interfejs pokazuje raport
    trenerowi i dopiero jego kliknięcie uruchamia `dry_run=false` — ten sam
    układ „propozycja przed zapisem”, co przy czytaniu opisu i przy OCR.

    Import nigdy nie nadpisuje wypełnionych pól istniejącego ćwiczenia i
    nigdy nie dotyka katalogu innego trenera (pełny opis reguł:
    `dzik_os/import_exercises.py`)."""
    report = import_library(db, coach.id, dry_run=dry_run)
    if not dry_run:
        record_event(
            db, action="EXERCISE_LIBRARY_IMPORTED", actor_id=coach.id,
            subject_ids=[coach.id],
            payload={
                "library": LIBRARY_REF, "created": report.created,
                "enriched": report.enriched, "skipped": report.skipped,
                "unmapped_muscles": len(report.unmapped_muscles),
                "unmapped_patterns": len(report.unmapped_patterns),
                "source": "panel",
            },
            summary=f"Baza ćwiczeń: import biblioteki „{LIBRARY_REF}” — "
                    f"{report.created} nowych, {report.enriched} uzupełnionych",
        )
        metrics.inc("exercise_library_import")
        db.commit()
    return report.as_dict()


@router.post("/coach/exercises", status_code=201)
def create_exercise(
    body: ExerciseLibraryItemIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = Exercise(id=new_id("EXC"), coach_id=coach.id, created_by=coach.id)
    _apply_fields(item, body)
    db.add(item)
    record_event(
        db, action="EXERCISE_CREATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"exercise_id": item.id, "name": item.name, "muscle_group": item.muscle_group},
        summary=f"Baza ćwiczeń: dodano „{item.name}” ({item.muscle_group})",
    )
    db.commit()
    return _out(item, for_coach=True)


@router.get("/coach/exercises")
def list_own_exercises(
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
    q: str | None = None,
    muscle: str | None = None,
    muscle_group: str | None = None,
    equipment: str | None = None,
    level: str | None = None,
    pattern: str | None = None,
    status: str | None = None,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    query = db.query(Exercise).filter(Exercise.coach_id == coach.id)
    if status:
        if status not in {"ACTIVE", "ARCHIVED"}:
            raise HTTPException(status_code=422, detail="Nieprawidłowy status")
        query = query.filter(Exercise.status == status)
    rows = query.order_by(Exercise.muscle_group, Exercise.name).all()
    return _page(
        rows, limit=limit, offset=offset, for_coach=True,
        filters=_filters(q, muscle, muscle_group, equipment, level, pattern),
    )


@router.get("/coach/exercises/recent")
def recent_exercises(
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Ostatnio używane ćwiczenia TEGO trenera — skrót przy układaniu planu.

    Kolejność wyznaczają najświeższe wersje planów: ćwiczenie użyte
    ostatnio stoi pierwsze. Trener bez żadnego planu dostaje pustą listę
    (interfejs nie pokazuje wtedy nic — żadnych pustych ramek).

    Prywatność: wynik to WYŁĄCZNIE ćwiczenia z bazy trenera (aktywne),
    dokładnie w tym samym kształcie co lista bazy. Nie ma tu ani słowa
    o tym, u którego podopiecznego ćwiczenie zostało użyte — to skrót do
    własnego katalogu, nie zestawienie klientów.

    Trasa stoi PRZED `/coach/exercises/{item_id}`, inaczej „recent”
    trafiłoby do niej jako identyfikator."""
    versions = (
        db.query(TrainingPlanVersion.content_json)
        .join(TrainingPlan, TrainingPlan.id == TrainingPlanVersion.plan_id)
        .filter(TrainingPlan.coach_id == coach.id)
        .order_by(TrainingPlanVersion.created_at.desc(), TrainingPlanVersion.id.desc())
        .limit(RECENT_VERSIONS_SCANNED)
        .all()
    )
    ordered: list[str] = []
    seen: set[str] = set()
    for (content,) in versions:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Uszkodzona treść wersji nie może wywrócić skrótu — pomijamy.
            continue
        for day in data.get("days") or []:
            for entry in day.get("exercises") or []:
                item_id = entry.get("exercise_id") if isinstance(entry, dict) else None
                if item_id and item_id not in seen:
                    seen.add(item_id)
                    ordered.append(item_id)
        if len(ordered) >= RECENT_LIMIT * 3:
            break
    if not ordered:
        return {"items": []}
    rows = {
        row.id: row
        for row in db.query(Exercise)
        .filter(
            Exercise.id.in_(ordered),
            Exercise.coach_id == coach.id,
            Exercise.status == "ACTIVE",
        )
        .all()
    }
    # Zarchiwizowane i cudze wypadają; kolejność zostaje „od najświeższych”.
    items = [_out(rows[i]) for i in ordered if i in rows][:RECENT_LIMIT]
    return {"items": items}


# Trasy poniżej muszą stać PRZED `/coach/exercises/{item_id}` — inaczej
# parametryzowana ścieżka złapałaby „import-schema” jako identyfikator
# ćwiczenia i endpointy importu byłyby nieosiągalne.
# --- Import / eksport bazy z pliku (CSV / XLSX) ------------------------

@router.get("/coach/exercises/import-schema")
def exercises_import_schema(coach: User = Depends(require_role("COACH"))):
    """Kontrakt pliku importu: kolumny, wymagalność, przykłady i zamknięte
    słowniki. Interfejs buduje z tego instrukcję, więc opis w aplikacji nie
    może rozjechać się z tym, co realnie przyjmuje import."""
    return {
        "columns": sheet_import.schema_dict(sheet_import.EXERCISE_COLUMNS),
        "dictionaries": sheet_import.dictionaries(),
        "modes": list(sheet_import.MODES),
        "list_separator": sheet_import.LIST_SEPARATOR,
        "muscle_separator": sheet_import.MUSCLE_SEPARATOR,
        "max_rows": sheet_import.MAX_ROWS,
        "max_bytes": sheet_import.MAX_BYTES,
        "formats": [".csv", ".xlsx"],
    }


@router.get("/coach/exercises/import-example")
def exercises_import_example(coach: User = Depends(require_role("COACH"))):
    """Wzór pliku do pobrania — nagłówek i jeden wiersz przykładowy."""
    return Response(
        content=sheet_import.example_csv(sheet_import.EXERCISE_COLUMNS),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dzik-os-cwiczenia-wzor.csv"'},
    )


@router.get("/coach/exercises/export-file")
def exercises_export_file(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    """Eksport całej bazy ćwiczeń trenera w formacie importu.

    Prawo wyjścia (portability): trener zabiera swoją bazę ze sobą, bez
    pytania kogokolwiek o zgodę. Ten sam plik wraca importem, więc masowa
    poprawka w arkuszu jest jednym cyklem pobierz–popraw–wgraj."""
    rows = (
        db.query(Exercise)
        .filter(Exercise.coach_id == coach.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    record_event(
        db, action="EXERCISES_EXPORTED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"rows": len(rows), "format": "csv"},
        summary=f"Baza ćwiczeń: eksport {len(rows)} pozycji do CSV",
    )
    db.commit()
    return Response(
        content=sheet_import.exercises_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dzik-os-cwiczenia.csv"'},
    )


@router.post("/coach/exercises/import-file")
async def exercises_import_file(
    file: UploadFile,
    dry_run: bool = Query(True),
    mode: str = Query(sheet_import.MODE_FILL),
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Import bazy ćwiczeń z pliku do katalogu ZALOGOWANEGO trenera.

    Domyślnie `dry_run=true`, czyli PRÓBA: pełny raport bez zapisu choćby
    jednego wiersza — ten sam układ „propozycja przed zapisem”, co przy
    czytaniu opisu, OCR i imporcie gotowej biblioteki. Tryb `UZUPELNIJ`
    (domyślny) wypełnia w istniejących pozycjach wyłącznie puste pola;
    `ZASTAP` nadpisuje, ale pusta komórka nigdy nie kasuje danych."""
    raw = await file.read()
    source_ref = (file.filename or "plik")[:200]
    try:
        rows, unknown, warnings = sheet_import.read_table(
            file.filename or "", raw, sheet_import.EXERCISE_COLUMNS
        )
        report = sheet_import.import_exercises_sheet(
            db, coach.id, rows, mode=mode, dry_run=dry_run, source_ref=source_ref,
        )
    except sheet_import.SheetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    report.unknown_columns = unknown
    report.warnings = warnings + report.warnings
    if not dry_run:
        record_event(
            db, action="EXERCISES_IMPORTED", actor_id=coach.id, subject_ids=[coach.id],
            payload={
                "source": source_ref, "mode": mode, "rows": report.rows_read,
                "created": report.created, "updated": report.updated,
                "skipped": report.skipped,
            },
            summary=f"Baza ćwiczeń: import z pliku „{source_ref}” — "
                    f"{report.created} nowych, {report.updated} zaktualizowanych",
        )
        metrics.inc("exercises_sheet_import")
        db.commit()
    return report.as_dict()


@router.get("/coach/exercises/{item_id}")
def get_own_exercise(
    item_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = require_owned_resource(
        db.get(Exercise, item_id), actor=coach, resource=f"exercise:{item_id}"
    )
    return _out(item, for_coach=True)


@router.put("/coach/exercises/{item_id}")
def update_exercise(
    item_id: str,
    body: ExerciseLibraryItemIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = require_owned_resource(
        db.get(Exercise, item_id), actor=coach, resource=f"exercise:{item_id}"
    )
    _apply_fields(item, body)
    item.updated_at = now_iso()
    record_event(
        db, action="EXERCISE_UPDATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"exercise_id": item.id, "name": item.name},
        summary=f"Baza ćwiczeń: zaktualizowano „{item.name}”",
    )
    db.commit()
    return _out(item, for_coach=True)


@router.post("/coach/exercises/{item_id}/status")
def set_exercise_status(
    item_id: str,
    status: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    if status not in {"ACTIVE", "ARCHIVED"}:
        raise HTTPException(status_code=422, detail="Nieprawidłowy status")
    item = require_owned_resource(
        db.get(Exercise, item_id), actor=coach, resource=f"exercise:{item_id}"
    )
    item.status = status
    item.updated_at = now_iso()
    db.commit()
    return {"ok": True, "status": status}


def _client_coach_ids(db: Session, user: User) -> list[str]:
    return [
        r.coach_id
        for r in db.query(CoachClientRelationship)
        .filter_by(client_id=user.id, status="ACTIVE")
        .all()
    ]


@router.get("/me/exercises")
def list_exercises_for_client(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    q: str | None = None,
    muscle: str | None = None,
    muscle_group: str | None = None,
    equipment: str | None = None,
    level: str | None = None,
    pattern: str | None = None,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    filters = _filters(q, muscle, muscle_group, equipment, level, pattern)
    coach_ids = _client_coach_ids(db, user)
    if not coach_ids:
        return {"items": [], "total": 0, "limit": limit, "offset": offset,
                "has_more": False}
    rows = (
        db.query(Exercise)
        .filter(Exercise.coach_id.in_(coach_ids), Exercise.status == "ACTIVE")
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    return _page(rows, limit=limit, offset=offset, filters=filters)


@router.get("/me/exercises/{item_id}")
def get_exercise_for_client(
    item_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Karta ćwiczenia dla klienta — wyłącznie z bazy trenera, który
    aktywnie go prowadzi (ta sama zasada broadcastu co lista)."""
    coach_ids = _client_coach_ids(db, user)
    item = db.get(Exercise, item_id)
    if (
        item is None
        or item.coach_id not in coach_ids
        or item.status != "ACTIVE"
    ):
        raise HTTPException(status_code=404, detail="Nie znaleziono ćwiczenia")
    return _out(item)

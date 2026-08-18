from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import notifications
from ..ai_provider import provider as ai_provider
from ..authz import require_attachable_file, require_client_self, resolve_client_access
from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..idempotency import replay_response, request_fingerprint, store_response
from ..models import (
    CheckinRevision,
    CoachClientRelationship,
    ProgressPhoto,
    StoredFile,
    User,
    WeeklyCheckin,
    new_id,
    now_iso,
)
from ..schemas import CheckinIn, CheckinPhotoIn, CheckinPhotosAttachIn, CheckinReviewIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["checkins"])


def _checkin_photos(db: Session, checkin_id: str) -> list[ProgressPhoto]:
    """Zdjęcia raportu w kolejności wybranej przez klienta (position),
    zdjęcia historyczne bez pozycji na końcu."""
    rows = (
        db.query(ProgressPhoto)
        .filter(ProgressPhoto.checkin_id == checkin_id)
        .all()
    )
    rows.sort(key=lambda p: (p.position is None, p.position or 0, p.created_at, p.id))
    return rows


def _photos_complete(checkin: WeeklyCheckin, attached: int) -> bool:
    """Raport jest kompletny plikowo, gdy liczba zapisanych zdjęć osiąga
    deklarację. NULL (raporty historyczne / bez deklaracji) = kompletny —
    stare wiersze nie są reinterpretowane."""
    return checkin.photos_expected is None or attached >= checkin.photos_expected


def _checkin_out(db: Session, c: WeeklyCheckin) -> dict:
    photos = _checkin_photos(db, c.id)
    payload = json.loads(c.payload_json)
    return {
        "id": c.id,
        "client_id": c.client_id,
        "week_start": c.week_start,
        "payload": payload,
        "status": c.status,
        "revision": c.revision,
        "submitted_at": c.submitted_at,
        "updated_at": c.updated_at,
        "coach_response": c.coach_response,
        "reviewed_by": c.reviewed_by,
        "reviewed_at": c.reviewed_at,
        "rating": c.rating,
        "photo_ids": [p.file_id for p in photos],
        "photos": [
            {
                "id": p.id, "file_id": p.file_id, "pose": p.pose,
                "position": p.position, "taken_at": p.taken_at,
            }
            for p in photos
        ],
        # Jakość danych — jawnie w API (i dalej w UI):
        # * corrected: raport był poprawiany po wysłaniu (historia w
        #   /checkins/{id}/revisions, nic nie jest nadpisywane w ciemno),
        # * scales_declared: odpowiedzi skal mają rozróżnione stany
        #   (ANSWERED/SKIPPED/NOT_APPLICABLE); False = raport sprzed zmiany —
        #   wartości mogły zostać na domyślnym 3/5 (dane mniej wiarygodne),
        # * photos_expected/attached/complete: stan plikowy raportu — raport
        #   z brakującymi zdjęciami jest jawnie CZĘŚCIOWY.
        "corrected": c.revision > 1,
        "scales_declared": payload.get("scale_states") is not None,
        "photos_expected": c.photos_expected,
        "photos_attached": len(photos),
        "photos_complete": _photos_complete(c, len(photos)),
    }


def _attach_photos(
    db: Session,
    user: User,
    checkin: WeeklyCheckin,
    client_id: str,
    specs: list[CheckinPhotoIn],
) -> int:
    """Podpina zdjęcia do raportu (dedup po file_id — ponowienie/rewizja nie
    mnoży wierszy) i egzekwuje limity liczby oraz łącznego rozmiaru dla
    CAŁEGO raportu (zdjęcia już zapisane + nowe). Zwraca liczbę wszystkich
    zdjęć raportu po operacji."""
    existing_rows = _checkin_photos(db, checkin.id)
    # Limit liczby: zadeklarowana lista sama w sobie (przed deduplikacją —
    # nadmiarowe żądanie jest odrzucane w całości, jak dotychczas) oraz
    # stan całego raportu po deduplikacji (zdjęcia już zapisane + nowe).
    limit_detail = f"Maksymalnie {settings.max_checkin_photos} zdjęć na raport"
    if len(specs) > settings.max_checkin_photos:
        raise HTTPException(status_code=422, detail=limit_detail)
    existing_ids = {p.file_id for p in existing_rows}
    new_specs = []
    seen: set[str] = set()
    for spec in specs:
        if spec.file_id in existing_ids or spec.file_id in seen:
            continue
        seen.add(spec.file_id)
        new_specs.append(spec)
    total = len(existing_rows) + len(new_specs)
    if total > settings.max_checkin_photos:
        raise HTTPException(status_code=422, detail=limit_detail)
    # Każdy plik musi być zdjęciem należącym do tego klienta (nie cudzym
    # file_id); łączny rozmiar liczony dla całego raportu.
    total_bytes = 0
    for spec in new_specs:
        stored = require_attachable_file(
            db, user, spec.file_id, owner_id=client_id, require_image=True
        )
        total_bytes += stored.size_bytes
    for row in existing_rows:
        stored_existing = db.get(StoredFile, row.file_id)
        if stored_existing is not None:
            total_bytes += stored_existing.size_bytes
    if total_bytes > settings.max_checkin_photos_total_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Zdjęcia raportu przekraczają łączny limit "
            f"{settings.max_checkin_photos_total_mb} MB",
        )
    next_position = max(
        (p.position for p in existing_rows if p.position is not None), default=-1
    ) + 1
    for offset, spec in enumerate(new_specs):
        db.add(
            ProgressPhoto(
                id=new_id("PHT"),
                client_id=client_id,
                file_id=spec.file_id,
                checkin_id=checkin.id,
                taken_at=checkin.week_start,
                pose=spec.pose,
                position=spec.position if spec.position is not None
                else next_position + offset,
            )
        )
    return total


def _photo_specs(body: CheckinIn) -> list[CheckinPhotoIn]:
    """Nowy kształt (photos: file_id+pose+position) z zachowaniem
    kompatybilności ze starym photo_ids."""
    specs = list(body.photos)
    known = {s.file_id for s in specs}
    for index, file_id in enumerate(body.photo_ids):
        if file_id not in known:
            specs.append(CheckinPhotoIn(file_id=file_id, position=index))
    return specs


@router.post("/checkins", status_code=201)
def submit_checkin(
    body: CheckinIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Raport tygodniowy klienta. Poprawka istniejącego raportu tworzy nową
    rewizję — poprzednia treść zostaje zachowana (CheckinRevision).
    Idempotencja: powtórka z tym samym idempotency_key (podwójne kliknięcie,
    retry po przerwaniu sieci) zwraca zapisany wynik zamiast nowej rewizji."""
    client_id = require_client_self(db, user)
    fingerprint = None
    if body.idempotency_key:
        fingerprint = request_fingerprint(body.model_dump(exclude={"idempotency_key"}))
        replay = replay_response(
            db, user_id=user.id, operation="checkin_submit",
            key=body.idempotency_key, fingerprint=fingerprint,
        )
        if replay is not None:
            return replay
    specs = _photo_specs(body)
    if body.photos_expected is not None:
        if body.photos_expected > settings.max_checkin_photos:
            raise HTTPException(
                status_code=422,
                detail=f"Maksymalnie {settings.max_checkin_photos} zdjęć na raport",
            )
        if body.photos_expected < len(specs):
            raise HTTPException(
                status_code=422,
                detail="Zadeklarowana liczba zdjęć jest mniejsza niż liczba "
                "przesłanych.",
            )
    # payload_json przechowuje odpowiedzi formularza (ze scale_states —
    # rozróżnienie brak odpowiedzi / wartość / pominięte / nie dotyczy);
    # metadane przepływu (zdjęcia, idempotencja) nie są treścią raportu.
    payload = body.model_dump(
        exclude={"photo_ids", "photos", "photos_expected", "idempotency_key"}
    )
    existing = (
        db.query(WeeklyCheckin)
        .filter_by(client_id=client_id, week_start=body.week_start)
        .one_or_none()
    )
    if existing is not None:
        if existing.status == "REVIEWED":
            raise HTTPException(
                status_code=409,
                detail="Raport został już oceniony przez trenera — wyślij nowy raport "
                "w kolejnym tygodniu lub napisz wiadomość.",
            )
        db.add(
            CheckinRevision(
                id=new_id("CKR"),
                checkin_id=existing.id,
                revision=existing.revision,
                payload_json=existing.payload_json,
            )
        )
        existing.payload_json = json.dumps(payload, ensure_ascii=False)
        existing.revision += 1
        existing.updated_at = now_iso()
        checkin = existing
        action = "CHECKIN_CORRECTED"
    else:
        checkin = WeeklyCheckin(
            id=new_id("CKN"),
            client_id=client_id,
            week_start=body.week_start,
            payload_json=json.dumps(payload, ensure_ascii=False),
            # Jawnie (nie default ORM): odpowiedź budowana przed commitem.
            revision=1,
        )
        db.add(checkin)
        # Raport przed swoimi zdjęciami (klucz obcy checkin_id w ProgressPhoto).
        db.flush()
        action = "CHECKIN_SUBMITTED"
    attached = _attach_photos(db, user, checkin, client_id, specs)
    if body.photos_expected is not None:
        checkin.photos_expected = max(body.photos_expected, attached)
    elif specs and (checkin.photos_expected is None or attached > checkin.photos_expected):
        checkin.photos_expected = attached
    record_event(
        db,
        action=action,
        actor_id=user.id,
        subject_ids=[client_id],
        # Payload audytu bez treści raportu i bez identyfikatorów/nazw
        # plików zdjęć — wyłącznie liczniki stanu.
        payload={"checkin_id": checkin.id, "week_start": body.week_start,
                 "revision": checkin.revision,
                 "photos_attached": attached,
                 "photos_expected": checkin.photos_expected},
        summary=f"Raport tygodniowy {body.week_start} (rewizja {checkin.revision})",
    )
    # Powiadomienie trenera prowadzącego (bez treści raportu) — dedup po
    # (raport, rewizja): retry żądania nie dubluje powiadomienia.
    rels = (
        db.query(CoachClientRelationship)
        .filter_by(client_id=client_id, status="ACTIVE")
        .all()
    )
    coach_notifications = [
        notifications.notify_now(
            db,
            user_id=rel.coach_id,
            category="RAPORT",
            title="Nowy raport tygodniowy",
            body=f"{user.display_name} wysłał(a) raport do oceny.",
            url=f"/trener/klient/{client_id}",
            dedup_key=f"checkin:{checkin.id}:rev{checkin.revision}:{rel.coach_id}",
        )
        for rel in rels
    ]
    response = {
        "id": checkin.id,
        "revision": checkin.revision,
        "photos_attached": attached,
        "photos_expected": checkin.photos_expected,
        "photos_complete": _photos_complete(checkin, attached),
    }
    if body.idempotency_key and fingerprint is not None:
        store_response(
            db, user_id=user.id, operation="checkin_submit",
            key=body.idempotency_key, fingerprint=fingerprint, response=response,
        )
    db.commit()
    for n in coach_notifications:
        notifications.publish_realtime(n)
    return response


@router.post("/checkins/{checkin_id}/photos")
def attach_checkin_photos(
    checkin_id: str,
    body: CheckinPhotosAttachIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Dokończenie częściowego raportu: dopięcie kolejnych zapisanych zdjęć
    (po jednym, zaraz po udanym uploadzie — stan częściowy jest trwały) lub
    świadome zamknięcie deklaracji bez brakujących plików (set_expected).
    Operacja naturalnie idempotentna: ten sam file_id nie jest podpinany
    dwa razy."""
    client_id = require_client_self(db, user)
    checkin = db.get(WeeklyCheckin, checkin_id)
    if checkin is None or checkin.client_id != client_id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if checkin.status == "REVIEWED":
        raise HTTPException(
            status_code=409,
            detail="Raport został już oceniony przez trenera — zdjęć nie można "
            "już zmieniać.",
        )
    attached = _attach_photos(db, user, checkin, client_id, body.photos)
    if body.set_expected is not None:
        if body.set_expected < attached:
            raise HTTPException(
                status_code=422,
                detail="Deklarowana liczba zdjęć nie może być mniejsza niż "
                "liczba już zapisanych.",
            )
        if body.set_expected > settings.max_checkin_photos:
            raise HTTPException(
                status_code=422,
                detail=f"Maksymalnie {settings.max_checkin_photos} zdjęć na raport",
            )
        checkin.photos_expected = body.set_expected
    elif checkin.photos_expected is not None and attached > checkin.photos_expected:
        checkin.photos_expected = attached
    checkin.updated_at = now_iso()
    record_event(
        db,
        action="CHECKIN_PHOTOS_ATTACHED",
        actor_id=user.id,
        subject_ids=[client_id],
        # Bez identyfikatorów/nazw plików — wyłącznie liczniki stanu
        # (zdjęcia sylwetki to dane wrażliwe; nie wyciekają do audytu).
        payload={"checkin_id": checkin.id,
                 "photos_attached": attached,
                 "photos_expected": checkin.photos_expected},
        summary=f"Zdjęcia raportu {checkin.week_start}: {attached}"
        + (f"/{checkin.photos_expected}" if checkin.photos_expected is not None else ""),
    )
    db.commit()
    return {
        "photos_attached": attached,
        "photos_expected": checkin.photos_expected,
        "photos_complete": _photos_complete(checkin, attached),
    }


@router.get("/clients/{client_id}/checkins")
def list_checkins(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id)
    rows = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.client_id == client_id)
        .order_by(WeeklyCheckin.week_start.desc())
        .all()
    )
    return {"checkins": [_checkin_out(db, c) for c in rows]}


@router.get("/checkins/{checkin_id}/revisions")
def checkin_revisions(
    checkin_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    checkin = db.get(WeeklyCheckin, checkin_id)
    if checkin is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, user, checkin.client_id)
    rows = (
        db.query(CheckinRevision)
        .filter(CheckinRevision.checkin_id == checkin_id)
        .order_by(CheckinRevision.revision)
        .all()
    )
    return {
        "revisions": [
            {"revision": r.revision, "payload": json.loads(r.payload_json),
             "created_at": r.created_at}
            for r in rows
        ]
    }


@router.post("/checkins/{checkin_id}/review")
def review_checkin(
    checkin_id: str,
    body: CheckinReviewIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    checkin = db.get(WeeklyCheckin, checkin_id)
    if checkin is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, coach, checkin.client_id, action="write")
    checkin.coach_response = body.coach_response
    checkin.status = "REVIEWED"
    checkin.reviewed_by = coach.id
    checkin.reviewed_at = now_iso()
    checkin.rating = body.rating
    record_event(
        db,
        action="CHECKIN_REVIEWED",
        actor_id=coach.id,
        subject_ids=[checkin.client_id],
        payload={"checkin_id": checkin.id, "week_start": checkin.week_start,
                 "rating": body.rating},
        summary=f"Odpowiedź trenera na raport {checkin.week_start}"
        + (f" (ocena {body.rating}/5)" if body.rating else ""),
    )
    notification = notifications.notify_now(
        db,
        user_id=checkin.client_id,
        category="RAPORT",
        title="Trener odpowiedział na Twój raport",
        body="Zajrzyj do aplikacji, żeby przeczytać odpowiedź.",
        url="/raport",
        dedup_key=f"checkin-review:{checkin.id}:{checkin.reviewed_at}",
    )
    db.commit()
    notifications.publish_realtime(notification)
    return {"ok": True}


@router.post("/checkins/{checkin_id}/ai-summary")
def ai_summary(
    checkin_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Propozycja AI: streszczenie raportu + szkic odpowiedzi do edycji.
    NIGDY nie zapisuje niczego automatycznie — trener sam decyduje, czy i
    co wysłać przez /checkins/{id}/review. Bez skonfigurowanego dostawcy
    (domyślnie) zwraca available=false z jawnym wyjaśnieniem, zamiast
    udawać, że funkcja działa."""
    checkin = db.get(WeeklyCheckin, checkin_id)
    if checkin is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, coach, checkin.client_id, action="write")
    # Raport zawiera dane zdrowotne klienta — użycie AI wymaga JEGO
    # zgody kategorii „funkcje AI" (nie decyzji trenera). Bez zgody
    # zwracamy jawny powód, nie udajemy błędu technicznego.
    from ..consent_catalog import SYSTEM_GRANTEE
    from ..hos_bridge import ConsentService

    if not ConsentService.authorize(
        db,
        subject_id=checkin.client_id,
        grantee_id=SYSTEM_GRANTEE,
        purpose="ai_features",
        domain="checkin_summaries",
        action="read",
        sensitive=True,
    ):
        return {
            "available": False,
            "reason": "Klient nie wyraził zgody na funkcje AI dla swoich "
            "raportów (Profil → Prywatność i zgody).",
        }
    if not ai_provider.enabled:
        return {
            "available": False,
            "reason": "Funkcja podsumowań AI wymaga konfiguracji przez "
            "administratora (klucz dostawcy poza repozytorium — patrz "
            "docs/DEFERRED_FEATURES.md).",
        }
    result = ai_provider.summarize_checkin(
        payload=json.loads(checkin.payload_json), history_note=None
    )
    if result is None:
        return {"available": False, "reason": "Dostawca AI nie zwrócił odpowiedzi."}
    record_event(
        db,
        action="AI_SUMMARY_REQUESTED",
        actor_id=coach.id,
        subject_ids=[checkin.client_id],
        payload={"checkin_id": checkin.id, "provider": ai_provider.name},
        summary=f"Trener poprosił o podsumowanie AI raportu {checkin.week_start}",
    )
    db.commit()
    return {
        "available": True,
        "summary": result.summary,
        "draft_response": result.draft_response,
        "flags": result.flags,
    }

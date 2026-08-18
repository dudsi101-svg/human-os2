"""Przepisywanie tekstu ze zdjęcia (OCR) — API zadań i zatwierdzania.

Reguły całej funkcji (docs/OCR.md):

* **wynik to ZAWSZE propozycja** — żaden endpoint rozpoznawania niczego nie
  zapisuje w bazie produktów, planie ani dokumencie. Zapis następuje
  dopiero po ``POST /api/ocr/tasks/{id}/approve``, czyli po tym, jak
  człowiek zobaczył tekst obok zdjęcia i go poprawił;
* **dwa tryby bez przełącznika** — silnik lokalny działa zawsze, tryb
  rozszerzony (model widzenia) włącza się sam, gdy operator skonfigurował
  dostawcę ORAZ podmiot danych ma zgodę ``funkcje_ai``. Brak jednego z
  nich to jawny komunikat, nie błąd;
* **dostęp przez istniejące bramki** — cudzy plik i cudze zadanie to 404
  (nie ujawniamy istnienia zasobu), a zdjęcie klienta wymaga aktywnej
  relacji i zgody, dokładnie jak każdy inny plik;
* **zero treści w logach** — rozpoznany tekst nie trafia do logów, metryk
  ani audytu; audyt notuje sam fakt rozpoznania (silnik, liczba znaków,
  czas).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import ocr, ocr_ai, ocr_queue
from ..authz import (
    DOMAIN_COLLABORATION,
    DOMAIN_NUTRITION,
    ai_features_consent_active,
    deny,
    resolve_client_access,
)
from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..idempotency import replay_response, request_fingerprint, store_response
from ..models import Document, FoodProduct, OcrTask, StoredFile, User, new_id, now_iso
from ..observability import metrics
from ..schemas import OcrApproveIn, OcrTaskIn
from ..security import active_roles, current_user

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

PURPOSE_LABELS = {
    "PRODUKT": "etykieta produktu",
    "PLAN": "kartka z planem lub dietą",
    "DOKUMENT": "skan dokumentu",
}


def _task_payload(task: OcrTask) -> dict:
    """Stan zadania dla UI. Tekst i propozycja płyną WYŁĄCZNIE tutaj —
    do zalogowanej osoby, która przeszła bramkę dostępu."""
    return {
        "id": task.id,
        "status": task.status,
        "purpose": task.purpose,
        "file_id": task.file_id,
        "document_id": task.document_id,
        "engine": task.engine,
        "mode_reason": task.mode_reason,
        "text": task.text,
        "proposal": json.loads(task.proposal_json) if task.proposal_json else None,
        "error_code": task.error_code,
        "error": task.error,
        "chars": task.chars,
        "duration_ms": task.duration_ms,
        "approved_at": task.approved_at,
        "result_ref": task.result_ref,
        "created_at": task.created_at,
        "finished_at": task.finished_at,
    }


def _mode_for(db: Session, owner_id: str) -> tuple[str, str]:
    """Tryb, w jakim POJEDZIE najbliższe zadanie tego podmiotu danych."""
    if not ai_features_consent_active(db, owner_id):
        return "LOCAL", ocr_ai.NO_CONSENT_REASON
    ready, reason = ocr_ai.provider_ready(db, owner_id)
    return ("EXTENDED", "") if ready else ("LOCAL", reason)


@router.get("/status")
def ocr_status(
    client_id: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Czy funkcja jest gotowa i w jakim trybie zadziała — do pokazania w UI
    ZANIM ktoś zrobi zdjęcie. Brak silnika to jawny stan, nigdy błąd."""
    owner_id = user.id
    if client_id is not None and client_id != user.id:
        resolve_client_access(db, user, client_id, action="write", domain=DOMAIN_COLLABORATION)
        owner_id = client_id
    availability = ocr.engine.availability()
    mode, mode_reason = _mode_for(db, owner_id)
    return {
        "engine_available": availability.available,
        "engine_reason": availability.reason,
        "mode": mode,
        "mode_reason": mode_reason,
        "queue_depth": ocr_queue.tasks.depth(),
        "max_input_mb": settings.ocr_max_input_mb,
        "accepted_types": list(ocr.OCR_IMAGE_TYPES),
        "timeout_s": settings.ocr_timeout_s,
    }


def _require_ocr_file(db: Session, user: User, file_id: str, owner_id: str) -> StoredFile:
    """Plik do rozpoznania: musi istnieć, należeć do podmiotu danych (albo
    być wgrany przez samego zlecającego) i być zdjęciem.

    Cudzy plik = 404 (jak każda inna próba sięgnięcia po nie swoje);
    zły typ = 422, bo to walidacja wejścia, nie kwestia dostępu."""
    stored = db.get(StoredFile, file_id)
    if stored is None or stored.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if stored.owner_user_id != owner_id and stored.uploaded_by != user.id:
        deny(user.id, f"file:{file_id}")
    if stored.content_type not in ocr.OCR_IMAGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Przepisać tekst da się wyłącznie ze zdjęcia (JPG, PNG albo WEBP). "
            "Plik PDF trzeba na razie przepisać ręcznie.",
        )
    if stored.size_bytes > settings.ocr_max_input_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Zdjęcie przekracza limit {settings.ocr_max_input_mb} MB dla "
            "przepisywania tekstu.",
        )
    return stored


def _owned_task(db: Session, user: User, task_id: str) -> OcrTask:
    """Zadanie widzi wyłącznie podmiot danych i osoba, która je zleciła.
    Cudze zadanie = 404 (wynik bywa daną zdrowotną)."""
    task = db.get(OcrTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if user.id not in (task.owner_user_id, task.created_by):
        deny(user.id, f"ocr_task:{task_id}")
    return task


@router.post("/tasks", status_code=202)
def create_task(
    body: OcrTaskIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Zleca przepisanie tekstu ze zdjęcia. Zwraca identyfikator zadania i
    status — rozpoznanie idzie do kolejki jednoslotowej, front odpytuje
    ``GET /api/ocr/tasks/{id}`` albo słucha zdarzenia `ocr.task`.

    Nic nie jest tu zapisywane poza samym zadaniem: wynik będzie propozycją
    do zatwierdzenia przez człowieka."""
    owner_id = user.id
    if body.client_id is not None and body.client_id != user.id:
        resolve_client_access(
            db, user, body.client_id, action="write", domain=DOMAIN_COLLABORATION
        )
        owner_id = body.client_id
    fingerprint = None
    if body.idempotency_key:
        fingerprint = request_fingerprint(body.model_dump(exclude={"idempotency_key"}))
        replay = replay_response(
            db, user_id=user.id, operation="ocr_task",
            key=body.idempotency_key, fingerprint=fingerprint,
        )
        if replay is not None:
            return replay

    stored = _require_ocr_file(db, user, body.file_id, owner_id)
    document = None
    if body.purpose == "DOKUMENT":
        if not body.document_id:
            raise HTTPException(
                status_code=422, detail="Wskaż dokument, do którego ma trafić tekst"
            )
        document = db.get(Document, body.document_id)
        if document is None or document.status != "ACTIVE":
            raise HTTPException(status_code=404, detail="Nie znaleziono")
        if document.client_id != owner_id:
            deny(user.id, f"document:{body.document_id}")

    if ocr_queue.tasks.depth() >= settings.ocr_queue_max:
        raise HTTPException(
            status_code=429,
            detail="Kolejka rozpoznawania jest pełna — spróbuj za chwilę.",
        )
    used_today = (
        db.query(OcrTask)
        .filter(OcrTask.created_by == user.id, OcrTask.created_at >= now_iso()[:10])
        .count()
    )
    if used_today >= settings.ocr_daily_tasks_user:
        raise HTTPException(
            status_code=429,
            detail=f"Dzienny limit {settings.ocr_daily_tasks_user} rozpoznań został "
            "wyczerpany. Spróbuj jutro albo przepisz tekst ręcznie.",
        )

    task = OcrTask(
        id=new_id("OCR"),
        owner_user_id=owner_id,
        created_by=user.id,
        file_id=stored.id,
        purpose=body.purpose,
        document_id=document.id if document is not None else None,
    )
    db.add(task)
    # Flush przed zbudowaniem odpowiedzi: created_at pochodzi z domyślnej
    # wartości kolumny, więc bez tego wróciłby null.
    db.flush()
    mode, mode_reason = _mode_for(db, owner_id)
    availability = ocr.engine.availability()
    record_event(
        db,
        action="OCR_REQUESTED",
        actor_id=user.id,
        subject_ids=[owner_id],
        payload={"task_id": task.id, "purpose": task.purpose, "file_id": stored.id,
                 "mode": mode},
        summary=f"Zlecono przepisanie tekstu ze zdjęcia ({PURPOSE_LABELS[task.purpose]})",
    )
    payload = {
        **_task_payload(task),
        "mode": mode,
        "mode_reason": mode_reason,
        "engine_available": availability.available,
        "engine_reason": availability.reason,
        "queue_depth": ocr_queue.tasks.depth() + 1,
    }
    if body.idempotency_key and fingerprint:
        store_response(
            db, user_id=user.id, operation="ocr_task",
            key=body.idempotency_key, fingerprint=fingerprint, response=payload,
        )
    db.commit()
    metrics.inc("ocr_tasks_requested")
    if not ocr_queue.tasks.submit(task.id):
        # Poczekalnia pełna — zadanie zostaje w bazie jako PENDING i można
        # je ponowić; nie udajemy, że rusza natychmiast.
        raise HTTPException(
            status_code=429,
            detail="Kolejka rozpoznawania jest pełna — spróbuj za chwilę.",
        )
    return payload


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Stan zadania wraz z rozpoznanym tekstem i propozycją pól."""
    task = _owned_task(db, user, task_id)
    return {**_task_payload(task), "queue_depth": ocr_queue.tasks.depth()}


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Anulowanie/porzucenie propozycji: wiersz znika razem z rozpoznanym
    tekstem. Rezygnacja nie zostawia po sobie danych osobowych."""
    task = _owned_task(db, user, task_id)
    db.delete(task)
    record_event(
        db,
        action="OCR_DISCARDED",
        actor_id=user.id,
        subject_ids=[task.owner_user_id],
        payload={"task_id": task_id, "purpose": task.purpose},
        summary="Odrzucono propozycję przepisania tekstu ze zdjęcia",
    )
    db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/approve")
def approve_task(
    task_id: str,
    body: OcrApproveIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Zatwierdzenie propozycji przez człowieka — DOPIERO TU powstają dane.

    * PRODUKT → nowy produkt w bazie trenera (z proweniencją: OCR, plik
      źródłowy, użyty silnik),
    * DOKUMENT → tekst przeszukiwalny zapisany przy dokumencie (oryginał
      pliku bez zmian),
    * PLAN → nic nie zapisujemy po stronie serwera; tekst trafił do edytora
      i zapisze go trener jako wersję planu albo diety.
    """
    task = _owned_task(db, user, task_id)
    if task.status != "DONE":
        raise HTTPException(
            status_code=409,
            detail="To zadanie nie ma jeszcze gotowego wyniku do zatwierdzenia.",
        )
    if task.approved_at:
        raise HTTPException(status_code=409, detail="Ta propozycja została już zatwierdzona.")

    result_ref = None
    if task.purpose == "PRODUKT":
        if body.product is None:
            raise HTTPException(status_code=422, detail="Brak danych produktu do zapisania")
        if "COACH" not in active_roles(db, user.id):
            raise HTTPException(status_code=403, detail="Tylko trener prowadzi bazę produktów")
        product = FoodProduct(
            id=new_id("FOD"), coach_id=user.id, created_by=user.id,
            name=body.product.name, category=body.product.category,
            kcal_100g=body.product.kcal_100g, protein_100g=body.product.protein_100g,
            fat_100g=body.product.fat_100g, carbs_100g=body.product.carbs_100g,
            fiber_100g=body.product.fiber_100g,
            default_portion_g=body.product.default_portion_g,
            unit_name=body.product.unit_name, unit_grams=body.product.unit_grams,
            source=body.product.source, note=body.product.note,
            # Proweniencja: skąd wzięły się te wartości.
            origin_kind="OCR", origin_file_id=task.file_id, origin_engine=task.engine,
        )
        db.add(product)
        result_ref = product.id
    elif task.purpose == "DOKUMENT":
        if body.text is None or not body.text.strip():
            raise HTTPException(status_code=422, detail="Brak tekstu do zapisania")
        document = db.get(Document, task.document_id) if task.document_id else None
        if document is None or document.status != "ACTIVE":
            raise HTTPException(status_code=404, detail="Nie znaleziono")
        domain = DOMAIN_NUTRITION if document.category == "DIETA" else DOMAIN_COLLABORATION
        resolve_client_access(db, user, document.client_id, action="write", domain=domain)
        document.ocr_text = body.text.strip()
        document.ocr_engine = task.engine
        document.ocr_at = now_iso()
        result_ref = document.id

    task.approved_at = now_iso()
    task.result_ref = result_ref
    # Zatwierdzony tekst może być poprawiony przez człowieka — zapisujemy
    # WERSJĘ ZATWIERDZONĄ, żeby propozycja i decyzja się nie rozjeżdżały.
    if body.text is not None and body.text.strip():
        task.text = body.text.strip()
    record_event(
        db,
        action="OCR_PROPOSAL_APPROVED",
        actor_id=user.id,
        subject_ids=[task.owner_user_id],
        payload={"task_id": task.id, "purpose": task.purpose, "engine": task.engine,
                 "result_ref": result_ref},
        summary=f"Zatwierdzono przepisany tekst ({PURPOSE_LABELS[task.purpose]})",
    )
    db.commit()
    metrics.inc("ocr_proposals_approved")
    return {"ok": True, "task_id": task.id, "result_ref": result_ref,
            "purpose": task.purpose}

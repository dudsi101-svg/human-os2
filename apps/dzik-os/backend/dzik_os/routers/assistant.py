"""Asystent trenera — API zadań w tle (wspólne dla wszystkich zadań).

Reguły całej funkcji (docs/ASYSTENT_TRENERA.md):

* **asystent proponuje, trener decyduje** — żaden endpoint tego routera
  nie zapisuje planu, wersji planu ani ćwiczenia. Wynik to propozycja
  obok edytora; zapis idzie zwykłą, wersjonowaną ścieżką
  (``POST /api/plans/{id}/versions`` z powodem zmiany), wykonaną przez
  trenera. Endpoint ``/applied`` zapisuje WYŁĄCZNIE proweniencję na
  wierszu zadania;
* **tylko trener** — klient i administrator dostają 403 (asystent działa
  na zasobach trenera, a dane podopiecznego wchodzą wyłącznie za jego
  zgodą i wyłącznie w zadaniu zleconym przez jego trenera);
* **praca w tle** — zlecenie oddaje identyfikator zadania (202), a wynik
  odbiera się przez ``GET`` albo przez zdarzenie ``assistant.task`` na
  ISTNIEJĄCEJ magistrali SSE. Edytor planu pozostaje w pełni używalny;
* **anulowanie jednym kliknięciem** — ``POST /cancel`` zatrzymuje zadanie;
  wynik anulowanego zadania nie wraca tylnymi drzwiami;
* **powtórne kliknięcie nie mnoży zadań** — klucz idempotencji (ten sam
  mechanizm co reszta zapisów, ``idempotency.py``);
* **zero treści w logach** — do logów, metryk i audytu idzie sam fakt
  (klucz zadania, silnik, liczba dni, czas), nigdy wejście ani wynik.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .. import coach_assistant
from ..authz import DOMAIN_TRAINING, deny, resolve_client_access
from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..idempotency import replay_response, request_fingerprint, store_response
from ..models import AssistantTask, User, new_id, now_iso
from ..observability import metrics
from ..schemas import AssistantAppliedIn, AssistantTaskIn
from ..security import require_role

router = APIRouter(prefix="/api/coach/assistant", tags=["assistant"])


def _task_payload(row: AssistantTask) -> dict:
    """Stan zadania dla UI. Wynik płynie WYŁĄCZNIE tutaj — do zalogowanego
    trenera, który jest właścicielem zadania."""
    return {
        "id": row.id,
        "task_key": row.task_key,
        "status": row.status,
        "client_id": row.client_id,
        "engine": row.engine,
        "engine_label": coach_assistant.engine_label(row.engine),
        "mode_reason": row.mode_reason,
        "result": json.loads(row.result_json) if row.result_json else None,
        "error_code": row.error_code,
        "error": row.error,
        "duration_ms": row.duration_ms,
        "approved_at": row.approved_at,
        "provenance": json.loads(row.provenance_json) if row.provenance_json else None,
        "result_ref": row.result_ref,
        "created_at": row.created_at,
        "finished_at": row.finished_at,
    }


def _owned_task(db: Session, coach: User, task_id: str) -> AssistantTask:
    """Zadanie widzi wyłącznie trener, który je zlecił. Cudze = 404."""
    row = db.get(AssistantTask, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if row.owner_user_id != coach.id:
        deny(coach.id, f"assistant_task:{task_id}")
    return row


def _descriptor(task_key: str) -> coach_assistant.AssistantTaskDescriptor:
    try:
        return coach_assistant.get_task(task_key)
    except coach_assistant.UnknownTask:
        raise HTTPException(
            status_code=422, detail="Nieznane zadanie asystenta"
        ) from None


@router.get("/status")
def assistant_status(
    task_key: str = coach_assistant.TASK_PLAN_DRAFT,
    client_id: str | None = None,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Czym zadziała asystent ZANIM ktokolwiek kliknie — tryb, powód trybu,
    zgoda podopiecznego, limit dzienny i rozmiar bazy ćwiczeń.

    Brak dostawcy modelu to STAN (ścieżka lokalna), nie awaria."""
    descriptor = _descriptor(task_key)
    if client_id is not None:
        resolve_client_access(db, coach, client_id, action="write", domain=DOMAIN_TRAINING)
    ready, reason = coach_assistant.provider_ready(db, coach.id)
    client_ctx = coach_assistant.build_client_context(
        db, client_id if descriptor.uses_client_data else None
    )
    vocab = coach_assistant.build_vocabulary(db, coach.id)
    used = coach_assistant.tasks_today(db, coach.id)
    return {
        "task_key": descriptor.key,
        "title": descriptor.title,
        "description": descriptor.description,
        "mode": coach_assistant.ENGINE_MODEL if ready else coach_assistant.ENGINE_LOCAL,
        "mode_reason": reason,
        "exercise_count": len(vocab.exercise_by_id),
        "daily_limit": descriptor.daily_limit(),
        "used_today": used,
        "queue_depth": coach_assistant.tasks.depth(),
        "slow_after_s": settings.assistant_slow_after_s,
        "timeout_s": settings.assistant_timeout_s,
        "registry": coach_assistant.registry_public(),
        **client_ctx.as_public(),
    }


@router.post("/tasks", status_code=202)
def create_task(
    body: AssistantTaskIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Zleca zadanie asystenta. Oddaje identyfikator i status — praca idzie
    do kolejki, a edytor planu zostaje w pełni używalny.

    Nic nie jest tu zapisywane poza samym wierszem zadania."""
    descriptor = _descriptor(body.task_key)
    try:
        parsed = descriptor.input_model.model_validate(body.input)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Parametry zadania są niekompletne albo spoza dozwolonych "
            f"wartości ({exc.error_count()} pól).",
        ) from exc

    client_id = getattr(parsed, "client_id", None)
    if client_id is not None:
        resolve_client_access(db, coach, client_id, action="write", domain=DOMAIN_TRAINING)

    fingerprint = None
    if body.idempotency_key:
        fingerprint = request_fingerprint(body.model_dump(exclude={"idempotency_key"}))
        replay = replay_response(
            db, user_id=coach.id, operation="assistant_task",
            key=body.idempotency_key, fingerprint=fingerprint,
        )
        if replay is not None:
            return replay

    if coach_assistant.tasks.depth() >= settings.assistant_queue_max:
        raise HTTPException(
            status_code=429,
            detail="Asystent ma pełną kolejkę — spróbuj za chwilę.",
        )
    if coach_assistant.tasks_today(db, coach.id) >= descriptor.daily_limit():
        raise HTTPException(
            status_code=429,
            detail=f"Dzienny limit {descriptor.daily_limit()} zadań asystenta "
            "został wyczerpany. Ćwiczenia z bazy wybierzesz normalnie, "
            "wyszukiwarką w edytorze planu.",
        )

    row = AssistantTask(
        id=new_id("ASI"),
        task_key=descriptor.key,
        owner_user_id=coach.id,
        client_id=client_id,
        # Wejście ZREDAGOWANE: parametry zadania, nigdy treść urazów.
        input_json=json.dumps(descriptor.redact_input(parsed), ensure_ascii=False),
        idem_key=body.idempotency_key,
    )
    db.add(row)
    db.flush()
    ready, reason = coach_assistant.provider_ready(db, coach.id)
    client_ctx = coach_assistant.build_client_context(
        db, client_id if descriptor.uses_client_data else None
    )
    record_event(
        db,
        action="ASSISTANT_TASK_REQUESTED",
        actor_id=coach.id,
        subject_ids=[client_id or coach.id],
        payload={"task_id": row.id, "task_key": descriptor.key,
                 "mode": coach_assistant.ENGINE_MODEL if ready else coach_assistant.ENGINE_LOCAL,
                 "client_data_used": client_ctx.included},
        summary=f"Asystent trenera: zlecono zadanie „{descriptor.title}”",
    )
    payload = {
        **_task_payload(row),
        "mode": coach_assistant.ENGINE_MODEL if ready else coach_assistant.ENGINE_LOCAL,
        "mode_reason": reason,
        "queue_depth": coach_assistant.tasks.depth() + 1,
        **client_ctx.as_public(),
    }
    if body.idempotency_key and fingerprint:
        store_response(
            db, user_id=coach.id, operation="assistant_task",
            key=body.idempotency_key, fingerprint=fingerprint, response=payload,
        )
    db.commit()
    metrics.inc("assistant_tasks_requested")
    if not coach_assistant.tasks.submit(row.id):
        # Poczekalnia pełna — zadanie zostaje jako PENDING i można je
        # ponowić; nie udajemy, że rusza natychmiast.
        raise HTTPException(
            status_code=429, detail="Asystent ma pełną kolejkę — spróbuj za chwilę."
        )
    return payload


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    row = _owned_task(db, coach, task_id)
    return {**_task_payload(row), "queue_depth": coach_assistant.tasks.depth()}


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Anulowanie jednym kliknięciem. Zadanie już zakończone zostaje jak
    było (409) — anulowanie nie kasuje gotowego wyniku po cichu."""
    row = _owned_task(db, coach, task_id)
    if row.status in {"DONE", "FAILED"}:
        raise HTTPException(
            status_code=409,
            detail="To zadanie już się zakończyło — możesz je odrzucić zamiast anulować.",
        )
    row.status = "CANCELLED"
    row.finished_at = now_iso()
    db.commit()
    metrics.inc("assistant_tasks_cancelled")
    return {"ok": True, "status": row.status}


@router.delete("/tasks/{task_id}")
def discard_task(
    task_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Odrzucenie propozycji: wiersz znika razem z wynikiem."""
    row = _owned_task(db, coach, task_id)
    task_key = row.task_key
    db.delete(row)
    record_event(
        db,
        action="ASSISTANT_PROPOSAL_DISCARDED",
        actor_id=coach.id,
        subject_ids=[coach.id],
        payload={"task_id": task_id, "task_key": task_key},
        summary="Asystent trenera: odrzucono propozycję",
    )
    db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/applied")
def mark_applied(
    task_id: str,
    body: AssistantAppliedIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Trener wstawił propozycję do planu — TU zapisuje się proweniencja.

    Ten endpoint NIE tworzy ani nie zmienia planu; plan zapisuje trener
    zwykłą, wersjonowaną ścieżką z powodem zmiany. Tutaj zostaje ślad, że
    dany plan powstał z pomocą asystenta i jakim silnikiem."""
    row = _owned_task(db, coach, task_id)
    if row.status != "DONE":
        raise HTTPException(
            status_code=409,
            detail="To zadanie nie ma jeszcze gotowej propozycji do zatwierdzenia.",
        )
    if row.approved_at:
        raise HTTPException(status_code=409, detail="Ta propozycja została już zatwierdzona.")
    result = json.loads(row.result_json) if row.result_json else {}
    prov = result.get("provenance") or coach_assistant.provenance(
        row.task_key, row.engine or coach_assistant.ENGINE_LOCAL, client_data_used=False
    )
    prov = {
        **prov,
        "approved_by": coach.id,
        "approved_at": now_iso(),
        "plan_id": body.plan_id,
        "version_no": body.version_no,
        "note": body.note,
    }
    row.approved_at = prov["approved_at"]
    row.provenance_json = json.dumps(prov, ensure_ascii=False)
    row.result_ref = body.plan_id
    record_event(
        db,
        action="ASSISTANT_PROPOSAL_APPLIED",
        actor_id=coach.id,
        subject_ids=[row.client_id or coach.id],
        payload={"task_id": row.id, "task_key": row.task_key, "engine": row.engine,
                 "plan_id": body.plan_id, "version_no": body.version_no},
        summary=(
            f"Asystent trenera: propozycja wstawiona do planu przez trenera "
            f"({coach_assistant.engine_label(row.engine)})"
        ),
    )
    db.commit()
    metrics.inc("assistant_proposals_applied")
    return {"ok": True, "task_id": row.id, "provenance": prov}

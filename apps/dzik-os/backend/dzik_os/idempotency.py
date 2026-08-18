"""Idempotencja operacji zapisu.

Klient dołącza do żądania pole ``idempotency_key`` (albo nagłówek —
router przekazuje tu jedną wartość). Pierwsze wykonanie zapisuje wynik
operacji pod kluczem (user_id, operation, key); każda powtórka z tym
samym kluczem i TĄ SAMĄ treścią żądania dostaje zapisany wynik bez
ponownego wykonania operacji (ochrona przed podwójnym kliknięciem i
retry po utracie odpowiedzi). Ten sam klucz z INNĄ treścią to jawny
konflikt 409 — nigdy ciche nadpisanie.

Zapisany wynik to wyłącznie odpowiedź API danej operacji (identyfikatory,
liczniki) — bez danych zdrowotnych ani treści formularza.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import IdempotencyKey, new_id


def request_fingerprint(payload: Any) -> str:
    """Deterministyczny odcisk treści żądania (kanoniczny JSON)."""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def replay_response(
    db: Session, *, user_id: str, operation: str, key: str, fingerprint: str
) -> dict | None:
    """Zapisany wynik wcześniejszego wykonania albo None (pierwsze użycie).
    Klucz użyty ponownie z inną treścią żądania -> 409."""
    row = (
        db.query(IdempotencyKey)
        .filter_by(user_id=user_id, operation=operation, idem_key=key)
        .one_or_none()
    )
    if row is None:
        return None
    if row.request_hash != fingerprint:
        raise HTTPException(
            status_code=409,
            detail="Ten klucz idempotencji został już użyty z inną treścią "
            "żądania — odśwież formularz i spróbuj ponownie.",
        )
    return json.loads(row.response_json)


def store_response(
    db: Session,
    *,
    user_id: str,
    operation: str,
    key: str,
    fingerprint: str,
    response: dict,
) -> None:
    """Zapis wyniku operacji pod kluczem (w tej samej transakcji co sama
    operacja — commit robi router)."""
    db.add(
        IdempotencyKey(
            id=new_id("IDM"),
            user_id=user_id,
            operation=operation,
            idem_key=key,
            request_hash=fingerprint,
            response_json=json.dumps(response, ensure_ascii=False),
        )
    )

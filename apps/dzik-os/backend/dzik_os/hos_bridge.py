"""Most między Dzik OS a Human OS Core (hos_engine).

Wykorzystywane fundamenty (MVP_IMPLEMENTED_SUBSET — świadomie wybrany
podzbiór, nie pełny Human OS):

* hos_engine.sqlite_store.SQLiteEventStore — niemutowalny, hash-chained
  łańcuch zdarzeń audytowych (append-only, weryfikowalny verify_chain()).
* hos_engine.consent.ConsentRegistry — autorytatywna logika autoryzacji
  zgód. Wiersze DB (models.ConsentRecord) są źródłem prawdy trwałości;
  na ich podstawie hydratujemy rejestr i delegujemy authorize() do Core,
  zamiast reimplementować reguły zgód w aplikacji.
* Konwencje identyfikatorów HOS-<PREFIX>-... (models.new_id).

Przepływ: UI -> Request -> (ten moduł: Core/Policy) -> Result/Receipt -> UI.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from hos_engine.consent import ConsentRegistry
from hos_engine.sqlite_store import SQLiteEventStore
from sqlalchemy.orm import Session

from .config import settings
from .models import ConsentRecord, Receipt, new_id

_event_store: SQLiteEventStore | None = None


def event_store() -> SQLiteEventStore:
    global _event_store
    if _event_store is None:
        _event_store = SQLiteEventStore(settings.audit_db_path)
    return _event_store


def reset_event_store() -> None:
    """Testy używają świeżej ścieżki audytu — zamknij i wymuś re-otwarcie."""
    global _event_store
    if _event_store is not None:
        _event_store.close()
    _event_store = None


def record_event(
    db: Session,
    *,
    action: str,
    actor_id: str,
    subject_ids: list[str],
    payload: dict[str, Any],
    summary: str,
    correlation_id: str | None = None,
) -> Receipt:
    """Zapisuje niemutowalne zdarzenie w łańcuchu audytu Human OS i wystawia
    pokwitowanie (Receipt) wiążące operację z hashem zdarzenia."""
    event_id = new_id("EVT")
    event = {
        "id": event_id,
        "event_type": action,
        "occurred_at": datetime.now(UTC).isoformat(),
        "actor_id": actor_id,
        "subject_ids": subject_ids,
        "payload": payload,
        "correlation_id": correlation_id or uuid.uuid4().hex,
        "immutable": True,
    }
    event_hash = event_store().append(event)
    receipt = Receipt(
        id=new_id("RCP"),
        event_id=event_id,
        event_hash=event_hash,
        action=action,
        actor_id=actor_id,
        subject_id=subject_ids[0] if subject_ids else actor_id,
        summary=summary,
    )
    db.add(receipt)
    return receipt


def verify_audit_chain() -> bool:
    return event_store().verify_chain()


class ConsentService:
    """Trwałe zgody + delegacja autoryzacji do hos_engine.ConsentRegistry.

    DB jest źródłem prawdy; rejestr Core jest hydratowany z aktywnych
    wierszy przy każdym sprawdzeniu (tanie przy skali MVP), więc decyzja
    "czy wolno" zapada w Human OS Core, nie w warstwie aplikacji.
    """

    @staticmethod
    def _hydrate(db: Session, subject_id: str) -> ConsentRegistry:
        registry = ConsentRegistry()
        rows = (
            db.query(ConsentRecord)
            .filter(ConsentRecord.subject_id == subject_id, ConsentRecord.revoked_at.is_(None))
            .all()
        )
        for row in rows:
            registry.grant(
                subject_id=row.subject_id,
                grantee_id=row.grantee_id,
                purposes={row.purpose},
                domains={row.domain},
                actions=set(row.actions.split(",")),
                expires_at=row.expires_at,
                allow_sensitive=row.allow_sensitive,
            )
        return registry

    @staticmethod
    def grant(
        db: Session,
        *,
        subject_id: str,
        grantee_id: str,
        purpose: str,
        domain: str,
        actions: str = "read",
        allow_sensitive: bool = False,
        consent_text_version: str = "1.0",
        expires_at: str | None = None,
    ) -> ConsentRecord:
        row = ConsentRecord(
            id=new_id("CNS"),
            subject_id=subject_id,
            grantee_id=grantee_id,
            purpose=purpose,
            domain=domain,
            actions=actions,
            allow_sensitive=allow_sensitive,
            consent_text_version=consent_text_version,
            expires_at=expires_at,
        )
        db.add(row)
        record_event(
            db,
            action="CONSENT_GRANTED",
            actor_id=subject_id,
            subject_ids=[subject_id],
            payload={
                "consent_id": row.id,
                "grantee_id": grantee_id,
                "purpose": purpose,
                "domain": domain,
                "actions": actions,
                "allow_sensitive": allow_sensitive,
                "consent_text_version": consent_text_version,
            },
            summary=f"Zgoda {purpose}/{domain} dla {grantee_id}",
        )
        return row

    @staticmethod
    def revoke(db: Session, *, consent_id: str, subject_id: str) -> ConsentRecord:
        row = db.get(ConsentRecord, consent_id)
        if row is None or row.subject_id != subject_id:
            # Tylko podmiot danych może cofnąć swoją zgodę (kontrakt
            # ConsentRegistry.revoke z hos_engine).
            raise PermissionError("Only the data subject may revoke this consent")
        if row.revoked_at is None:
            row.revoked_at = datetime.now(UTC).isoformat()
            record_event(
                db,
                action="CONSENT_REVOKED",
                actor_id=subject_id,
                subject_ids=[subject_id],
                payload={"consent_id": row.id, "grantee_id": row.grantee_id,
                         "purpose": row.purpose, "domain": row.domain},
                summary=f"Cofnięcie zgody {row.purpose}/{row.domain} dla {row.grantee_id}",
            )
        return row

    @classmethod
    def authorize(
        cls,
        db: Session,
        *,
        subject_id: str,
        grantee_id: str,
        purpose: str,
        domain: str,
        action: str,
        sensitive: bool = False,
    ) -> bool:
        registry = cls._hydrate(db, subject_id)
        return registry.authorize(
            subject_id=subject_id,
            grantee_id=grantee_id,
            purpose=purpose,
            domain=domain,
            action=action,
            sensitive=sensitive,
        )

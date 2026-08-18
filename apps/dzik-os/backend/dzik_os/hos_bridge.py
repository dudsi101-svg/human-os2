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

import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from hos_engine.consent import ConsentRegistry
from hos_engine.sqlite_store import SQLiteEventStore
from sqlalchemy.orm import Session

from . import consent_catalog
from .config import settings
from .models import ConsentRecord, Receipt, new_id


class ThreadSafeEventStore(SQLiteEventStore):
    """SQLiteEventStore z hos_engine współdzielony między wątkami serwera
    HTTP. Nie zmieniamy Core: podklasa wymienia połączenie na wielowątkowe
    i serializuje zapisy blokadą (append pozostaje logiką Core)."""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.connection.close()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()

    def append(self, event: dict[str, Any]) -> str:
        with self._lock:
            return super().append(event)


_event_store: SQLiteEventStore | None = None


def event_store() -> SQLiteEventStore:
    global _event_store
    if _event_store is None:
        _event_store = ThreadSafeEventStore(settings.audit_db_path)
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
            .filter(
                ConsentRecord.subject_id == subject_id,
                ConsentRecord.revoked_at.is_(None),
                ConsentRecord.denied_at.is_(None),
            )
            .all()
        )
        for row in rows:
            ConsentService._grant_row(registry, row)
        return registry

    @staticmethod
    def hydrate_many(db: Session, subject_ids: list[str]) -> ConsentRegistry:
        """Jeden rejestr Core zhydratowany dla WIELU podmiotów naraz.

        Widoki zbiorcze trenera (lista klientów, dashboard) pytały o zgody
        osobno dla każdego klienta i każdej domeny — to samo zapytanie
        wykonywało się kilkanaście razy na jedno wejście do panelu.
        Tutaj wiersze zgód pobieramy JEDNYM zapytaniem, a decyzja „czy
        wolno" nadal zapada w hos_engine.ConsentRegistry (rejestr odpowiada
        w pamięci) — warstwa aplikacji nie reimplementuje reguł zgód.
        """
        registry = ConsentRegistry()
        if not subject_ids:
            return registry
        rows = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.subject_id.in_(subject_ids),
                ConsentRecord.revoked_at.is_(None),
                ConsentRecord.denied_at.is_(None),
            )
            .all()
        )
        for row in rows:
            ConsentService._grant_row(registry, row)
        return registry

    @staticmethod
    def _grant_row(registry: ConsentRegistry, row: ConsentRecord) -> None:
        """Przeniesienie JEDNEGO wiersza zgody do rejestru Core — wspólne
        dla hydratacji pojedynczej i zbiorczej, żeby interpretacja zgód
        historycznych (parasolowych) nie rozjechała się między ścieżkami."""
        if (
            row.category is None
            and row.purpose == "coaching"
            and row.domain == "health_data"
            and row.allow_sensitive
        ):
            registry.grant(
                subject_id=row.subject_id,
                grantee_id=row.grantee_id,
                purposes=set(consent_catalog.LEGACY_UMBRELLA_PURPOSES),
                domains=set(consent_catalog.LEGACY_UMBRELLA_DOMAINS),
                actions=set(row.actions.split(",")),
                expires_at=row.expires_at,
                allow_sensitive=row.allow_sensitive,
            )
            return
        registry.grant(
            subject_id=row.subject_id,
            grantee_id=row.grantee_id,
            purposes={row.purpose},
            domains={row.domain},
            actions=set(row.actions.split(",")),
            expires_at=row.expires_at,
            allow_sensitive=row.allow_sensitive,
        )

    @staticmethod
    def grant_category(
        db: Session,
        *,
        subject_id: str,
        category_key: str,
        grantee_id: str | None = None,
        actions: str = "read,write",
        source: str = "SUBJECT",
        confirmed: bool = False,
        actor_id: str | None = None,
    ) -> ConsentRecord:
        """Rejestruje zgodę JEDNEJ kategorii z katalogu (consent_catalog).
        Cel, zakres, wrażliwość, podstawa prawna i wersja dokumentu
        pochodzą z katalogu — nie od wywołującego."""
        cat = consent_catalog.category_by_key(category_key)
        if cat is None:
            raise ValueError(f"Nieznana kategoria zgody: {category_key}")
        grantee = (
            consent_catalog.SYSTEM_GRANTEE if cat.grantee_kind == "SYSTEM" else grantee_id
        )
        if not grantee:
            raise ValueError("Kategoria trenerska wymaga grantee_id")
        row = ConsentRecord(
            id=new_id("CNS"),
            subject_id=subject_id,
            grantee_id=grantee,
            purpose=cat.purpose,
            domain=cat.domain,
            actions=actions,
            allow_sensitive=cat.sensitive,
            consent_text_version=consent_catalog.CONSENT_DOC_VERSION,
            confirmed_at=datetime.now(UTC).isoformat() if confirmed else None,
            category=cat.key,
            legal_basis=cat.legal_basis,
            source=source,
        )
        db.add(row)
        record_event(
            db,
            action="CONSENT_GRANTED",
            actor_id=actor_id or subject_id,
            subject_ids=[subject_id],
            payload={
                "consent_id": row.id,
                "grantee_id": grantee,
                "category": cat.key,
                "purpose": cat.purpose,
                "domain": cat.domain,
                "actions": actions,
                "allow_sensitive": cat.sensitive,
                "legal_basis": cat.legal_basis,
                "source": source,
                "consent_text_version": row.consent_text_version,
            },
            summary=f"Zgoda [{cat.key}] {cat.purpose}/{cat.domain} dla {grantee}",
        )
        return row

    @staticmethod
    def decline_category(
        db: Session,
        *,
        subject_id: str,
        category_key: str,
        grantee_id: str | None = None,
    ) -> ConsentRecord:
        """Jawna ODMOWA zgody opcjonalnej — zapisywana z pełną historią
        (wiersz z denied_at nigdy nie autoryzuje dostępu)."""
        cat = consent_catalog.category_by_key(category_key)
        if cat is None:
            raise ValueError(f"Nieznana kategoria zgody: {category_key}")
        grantee = (
            consent_catalog.SYSTEM_GRANTEE if cat.grantee_kind == "SYSTEM" else grantee_id
        )
        if not grantee:
            raise ValueError("Kategoria trenerska wymaga grantee_id")
        now = datetime.now(UTC).isoformat()
        row = ConsentRecord(
            id=new_id("CNS"),
            subject_id=subject_id,
            grantee_id=grantee,
            purpose=cat.purpose,
            domain=cat.domain,
            actions="",
            allow_sensitive=False,
            consent_text_version=consent_catalog.CONSENT_DOC_VERSION,
            category=cat.key,
            legal_basis=cat.legal_basis,
            source="SUBJECT",
            denied_at=now,
        )
        db.add(row)
        record_event(
            db,
            action="CONSENT_DECLINED",
            actor_id=subject_id,
            subject_ids=[subject_id],
            payload={
                "consent_id": row.id,
                "grantee_id": grantee,
                "category": cat.key,
                "purpose": cat.purpose,
                "domain": cat.domain,
                "consent_text_version": row.consent_text_version,
            },
            summary=f"Odmowa zgody [{cat.key}] {cat.purpose}/{cat.domain}",
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
                         "category": row.category,
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

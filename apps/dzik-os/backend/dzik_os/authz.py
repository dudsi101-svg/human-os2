"""Reguły dostępu Dzik OS (egzekwowane wyłącznie w backendzie).

Zasady (docs/PERMISSIONS.md):
* Klient widzi wyłącznie własne dane (ochrona przed IDOR — każda ścieżka
  z client_id przechodzi przez resolve_client_access).
* Trener widzi dane tylko AKTYWNIE przypisanych klientów i tylko dopóki
  klient nie cofnął zgody coaching/health_data (decyzję podejmuje
  hos_engine.ConsentRegistry przez ConsentService.authorize).
* ADMIN nie ma automatycznego dostępu do danych zdrowotnych — rola
  techniczna. Dostęp administracyjny jest ograniczony i audytowany.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .hos_bridge import ConsentService
from .models import CoachClientRelationship, User
from .security import active_roles

CONSENT_PURPOSE = "coaching"
CONSENT_DOMAIN = "health_data"


def active_relationship(db: Session, coach_id: str, client_id: str) -> CoachClientRelationship | None:
    return (
        db.query(CoachClientRelationship)
        .filter(
            CoachClientRelationship.coach_id == coach_id,
            CoachClientRelationship.client_id == client_id,
            CoachClientRelationship.status == "ACTIVE",
        )
        .one_or_none()
    )


def coach_can_access_client(
    db: Session, coach_id: str, client_id: str, *, action: str = "read", sensitive: bool = True
) -> bool:
    if active_relationship(db, coach_id, client_id) is None:
        return False
    return ConsentService.authorize(
        db,
        subject_id=client_id,
        grantee_id=coach_id,
        purpose=CONSENT_PURPOSE,
        domain=CONSENT_DOMAIN,
        action=action,
        sensitive=sensitive,
    )


def resolve_client_access(
    db: Session, actor: User, client_id: str, *, action: str = "read", sensitive: bool = True
) -> str:
    """Zwraca client_id, jeśli aktor ma prawo do danych tego klienta;
    w przeciwnym razie 404 (nie 403 — nie ujawniamy istnienia zasobu)."""
    roles = active_roles(db, actor.id)
    if "CLIENT" in roles and actor.id == client_id:
        return client_id
    if "COACH" in roles and coach_can_access_client(
        db, actor.id, client_id, action=action, sensitive=sensitive
    ):
        return client_id
    raise HTTPException(status_code=404, detail="Nie znaleziono")


def require_client_self(db: Session, actor: User) -> str:
    if "CLIENT" not in active_roles(db, actor.id):
        raise HTTPException(status_code=403, detail="Tylko dla klienta")
    return actor.id

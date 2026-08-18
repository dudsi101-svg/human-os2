from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..hos_bridge import record_event, verify_audit_chain
from ..models import Receipt, User
from ..security import active_roles, require_role

router = APIRouter(prefix="/api/admin", tags=["admin"])

# UWAGA: rola ADMIN jest techniczna. Endpointy admina świadomie NIE dają
# dostępu do danych zdrowotnych (profil, pomiary, raporty, zdjęcia, plany,
# wiadomości) — te ścieżki wymagają relacji trener–klient i zgody klienta.
# Każde użycie endpointu admina jest audytowane.


@router.get("/users")
def list_users(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    rows = db.query(User).order_by(User.created_at).all()
    record_event(
        db,
        action="ADMIN_USER_LIST_ACCESSED",
        actor_id=admin.id,
        subject_ids=[admin.id],
        payload={"count": len(rows)},
        summary="Administrator przejrzał listę kont (bez danych zdrowotnych)",
    )
    db.commit()
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "display_name": u.display_name,
                "status": u.status,
                "roles": sorted(active_roles(db, u.id)),
                "created_at": u.created_at,
                "last_login_at": u.last_login_at,
            }
            for u in rows
        ]
    }


@router.get("/audit/verify")
def audit_verify(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Weryfikacja integralności łańcucha zdarzeń Human OS (hash chain)."""
    ok = verify_audit_chain()
    record_event(
        db,
        action="ADMIN_AUDIT_VERIFIED",
        actor_id=admin.id,
        subject_ids=[admin.id],
        payload={"chain_valid": ok},
        summary=f"Weryfikacja łańcucha audytu: {'OK' if ok else 'BŁĄD'}",
    )
    db.commit()
    return {"chain_valid": ok}


@router.get("/receipts")
def list_receipts(
    limit: int = 100,
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Pokwitowania łańcucha audytu — dla admina WYŁĄCZNIE metadane
    (akcja, identyfikatory, hash, czas). Wolnotekstowe `summary` jest
    celowo pomijane: bywa pochodną danych zdrowotnych (tytuł celu, powód
    zmiany planu, kategoria obserwacji), a rola ADMIN jest techniczna i
    nie ma dostępu do danych zdrowotnych. Pełne pokwitowania (z summary)
    widzi trener w zakresie zgód klienta (GET /coach/clients/{id}/history).
    Dostęp jest audytowany."""
    rows = (
        db.query(Receipt).order_by(Receipt.created_at.desc()).limit(min(limit, 500)).all()
    )
    record_event(
        db,
        action="ADMIN_RECEIPTS_ACCESSED",
        actor_id=admin.id,
        subject_ids=[admin.id],
        payload={"count": len(rows)},
        summary="Administrator przejrzał pokwitowania audytu (metadane, bez summary)",
    )
    db.commit()
    return {
        "receipts": [
            {
                "id": r.id, "event_id": r.event_id, "event_hash": r.event_hash,
                "action": r.action, "actor_id": r.actor_id, "subject_id": r.subject_id,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    }

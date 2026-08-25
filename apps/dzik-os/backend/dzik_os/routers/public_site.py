"""Publiczne API strony marketingowej (0.49.0).

Jeden endpoint bez uwierzytelnienia: przyjęcie zapytania od potencjalnego
klienta. Zasady bezpieczeństwa publicznego wejścia:

* twarde limity długości pól (Pydantic) — żadnych załączników ani HTML-a;
* honeypot: ukryte pole `website` wypełniają boty — takie zgłoszenie
  dostaje 200 i jest po cichu odrzucane (bot nie uczy się, że wpadł);
* limiter prób per adres IP (okno przesuwne, jak przy logowaniu);
* treść zapytania trafia WYŁĄCZNIE do centrum powiadomień trenera
  (za logowaniem); kanały push/e-mail dostają neutralne wezwanie —
  zgodnie z zasadami docs/POWIADOMIENIA.md;
* wpis audytu bez treści wiadomości (tylko fakt zgłoszenia).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..hos_bridge import record_event
from ..models import RoleGrant, User, new_id
from ..notifications import notify_now
from ..security import LoginRateLimiter

router = APIRouter(prefix="/api/public", tags=["public"])

# Zapytań z jednego IP nie powinno być więcej niż kilka na godzinę —
# formularz wypełnia człowiek, nie integracja.
lead_rate_limiter = LoginRateLimiter(max_attempts=5, window_minutes=60)


class LeadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr = Field(max_length=254)
    phone: str = Field(default="", max_length=40)
    message: str = Field(min_length=10, max_length=2000)
    # Honeypot — pole niewidoczne w UI; człowiek zostawia puste.
    website: str = Field(default="", max_length=200)


@router.post("/lead", status_code=200)
def submit_lead(body: LeadIn, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    lead_rate_limiter.check(f"lead:{client_ip}")
    lead_rate_limiter.record_failure(f"lead:{client_ip}")

    if body.website.strip():
        # Bot: odpowiedź nieodróżnialna od sukcesu, zero zapisu.
        return {"ok": True}

    coach_ids = [
        row[0]
        for row in db.query(RoleGrant.user_id)
        .filter(RoleGrant.role == "COACH", RoleGrant.revoked_at.is_(None))
        .distinct()
        .all()
    ]
    lead_id = new_id("LEA")
    kontakt = body.email if not body.phone.strip() else f"{body.email}, tel. {body.phone.strip()}"
    delivered = 0
    for coach_id in coach_ids:
        coach = db.get(User, coach_id)
        if coach is None or coach.status != "ACTIVE":
            continue
        n = notify_now(
            db,
            user_id=coach_id,
            category="ZAPYTANIE",
            title=f"Zapytanie od: {body.name.strip()}",
            body=f"Kontakt: {kontakt}\n\n{body.message.strip()}",
            source=f"lead:{lead_id}",
            dedup_key=f"lead:{lead_id}:{coach_id}",
        )
        if n is not None:
            delivered += 1
    record_event(
        db,
        action="STATE_OBSERVED",
        actor_id="public-site",
        subject_ids=[lead_id],
        payload={"kind": "lead_submitted", "delivered_to": delivered},
        summary="Strona publiczna: przyjęto zapytanie kontaktowe",
    )
    db.commit()
    return {"ok": True}

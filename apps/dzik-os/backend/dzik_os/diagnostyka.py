"""Diagnostyka produkcji TYLKO DO ODCZYTU: `python -m dzik_os.diagnostyka`.

Odpowiada na pytania, na które dokumentacja nie jest dowodem: jaki
dostawca poczty faktycznie działa w TYM procesie, które zmienne SMTP są
ustawione (nazwy, nigdy wartości), jakie konta, relacje, zaproszenia
i plany istnieją oraz co mówi audyt o doręczeniach (0.54.5; powód:
z sesji operatora produkcja jest osiągalna wyłącznie przez workflowy).

Zasady:
* nic nie zapisuje, nic nie restartuje, nie dotyka sekretów;
* zero hashy haseł, tokenów, sekretów TOTP, treści zdrowotnych i treści
  planów — wyłącznie metadane (e-maile kont są potrzebne, żeby raport
  był użyteczny; log Actions widzi tylko właściciel repozytorium);
* wynik to JSON na stdout, żeby dało się go czytać maszynowo.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from . import __version__, aggregates
from .authz import DOMAIN_COLLABORATION
from .config import settings
from .db import db_session
from .hos_bridge import event_store
from .models import (
    ClientInvitation,
    CoachClientRelationship,
    NutritionPlan,
    RoleGrant,
    TrainingPlan,
    User,
    WeeklyCheckin,
)
from .notifications_provider import provider

ZMIENNE_SMTP = (
    "DZIK_SMTP_HOST", "DZIK_SMTP_PORT", "DZIK_SMTP_USER",
    "DZIK_SMTP_PASSWORD", "DZIK_SMTP_FROM", "DZIK_SMTP_SECURITY",
)
ZDARZENIA_DORECZEN = (
    "CLIENT_INVITED", "CLIENT_INVITATION_RESENT", "CLIENT_INVITATION_CANCELLED",
    "PASSWORD_RESET_LINK_SENT", "PASSWORD_RESET_SEND_FAILED",
    "PASSWORD_RESET_BY_OPERATOR", "IDENTITY_REGISTERED",
)
DNI_ZDARZEN = 30


def _srodowisko(db) -> dict:
    try:
        migracja = db.execute(
            text("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
        ).scalar()
    except Exception:  # noqa: BLE001 — raport ma powstać nawet bez tabeli
        migracja = None
    ustawione = [n for n in ZMIENNE_SMTP if os.environ.get(n)]
    return {
        "wersja": __version__,
        "migracja": migracja,
        "public_base_url": settings.public_base_url or None,
        "dostawca_poczty": provider.name,
        "smtp_ustawione": ustawione,
        "smtp_brakuje": [n for n in ZMIENNE_SMTP if n not in ustawione],
        "smtp_security": settings.smtp_security if settings.smtp_host else None,
        "mfa_wymagane_dla": sorted(
            r.strip() for r in str(settings.mfa_required_roles).split(",") if r.strip()
        ),
        "max_clients": settings.max_clients,
    }


def _konta(db) -> list[dict]:
    role = {}
    for r in db.query(RoleGrant).filter(RoleGrant.revoked_at.is_(None)).all():
        role.setdefault(r.user_id, set()).add(r.role)
    out = []
    for u in db.query(User).order_by(User.created_at).all():
        out.append({
            "email": u.email,
            "nazwa": u.display_name,
            "status": u.status,
            "role": sorted(role.get(u.id, ())),
            "wymuszona_zmiana_hasla": bool(u.must_change_password),
            "mfa": u.totp_confirmed_at is not None,
            "ostatnie_logowanie": u.last_login_at,
            "utworzone": u.created_at,
        })
    return out


def _relacje(db, email_of: dict[str, str]) -> list[dict]:
    rels = db.query(CoachClientRelationship).order_by(CoachClientRelationship.started_at).all()
    zgody = {}
    for coach_id in {r.coach_id for r in rels}:
        klienci = [r.client_id for r in rels if r.coach_id == coach_id]
        zgody[coach_id] = aggregates.consent_scopes_bulk(
            db, coach_id, klienci, domains={"wspolpraca": DOMAIN_COLLABORATION},
        )
    return [{
        "trener": email_of.get(r.coach_id, r.coach_id),
        "klient": email_of.get(r.client_id, r.client_id),
        "status": r.status,
        "zgoda_wspolpracy": zgody[r.coach_id][r.client_id]["wspolpraca"],
        "od": r.started_at,
        "utworzona_przez": r.created_by,
    } for r in rels]


def _zaproszenia(db, email_of: dict[str, str]) -> list[dict]:
    return [{
        "klient": email_of.get(i.client_id, i.client_id),
        "trener": email_of.get(i.coach_id, i.coach_id),
        "wystawione": i.created_at,
        "wazne_do": i.expires_at,
        "uzyte": i.used_at,
        "anulowane": i.cancelled_at,
        "aktywne": i.used_at is None and i.cancelled_at is None
        and i.expires_at > datetime.now(UTC).isoformat(),
    } for i in db.query(ClientInvitation).order_by(ClientInvitation.created_at).all()]


def _plany(db, email_of: dict[str, str]) -> dict[str, dict]:
    out: dict[str, dict] = {}

    def wpis(client_id: str) -> dict:
        return out.setdefault(email_of.get(client_id, client_id),
                              {"plany_treningowe": 0, "diety": 0, "raporty": 0})

    for p in db.query(TrainingPlan).all():
        wpis(p.client_id)["plany_treningowe"] += 1
    for n in db.query(NutritionPlan).all():
        wpis(n.client_id)["diety"] += 1
    for c in db.query(WeeklyCheckin).all():
        wpis(c.client_id)["raporty"] += 1
    return out


def _zdarzenia(email_of: dict[str, str]) -> list[dict]:
    od = (datetime.now(UTC) - timedelta(days=DNI_ZDARZEN)).isoformat()
    out = []
    for e in event_store().all():
        if e.get("event_type") not in ZDARZENIA_DORECZEN or e.get("occurred_at", "") < od:
            continue
        payload = e.get("payload") or {}
        out.append({
            "kiedy": e.get("occurred_at"),
            "typ": e.get("event_type"),
            "kogo": [email_of.get(s, s) for s in e.get("subject_ids", [])],
            "doreczenie": payload.get("delivery"),
            "powod": payload.get("reason"),
            "wazne_do": payload.get("expires_at"),
        })
    return out


def raport() -> dict:
    """Pełny raport diagnostyczny (słownik gotowy do JSON)."""
    with db_session() as db:
        email_of = {u.id: u.email for u in db.query(User).all()}
        return {
            "wygenerowano": datetime.now(UTC).isoformat(),
            "srodowisko": _srodowisko(db),
            "konta": _konta(db),
            "relacje": _relacje(db, email_of),
            "zaproszenia": _zaproszenia(db, email_of),
            "plany": _plany(db, email_of),
            "zdarzenia_doreczen_30_dni": _zdarzenia(email_of),
        }


def main(argv: list[str] | None = None) -> int:
    print(json.dumps(raport(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

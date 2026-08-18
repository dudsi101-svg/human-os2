from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..models import AuthSession, User, now_iso
from ..schemas import ChangePasswordIn, LoginRequest
from ..security import (
    _extract_token,
    _token_hash,
    active_roles,
    create_session,
    current_user,
    hash_password,
    login_rate_limiter,
    password_change_rate_limiter,
    revoke_other_sessions,
    revoke_session,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "dzik_session",
        token,
        httponly=True,
        samesite="lax",
        secure=settings.env == "production",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    key = body.email.lower()
    login_rate_limiter.check(key)
    user = db.query(User).filter(User.email == key, User.status == "ACTIVE").one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        login_rate_limiter.record_failure(key)
        # Jedna odpowiedź dla obu przypadków — nie ujawniamy istnienia konta.
        raise HTTPException(status_code=401, detail="Nieprawidłowy e-mail lub hasło")
    login_rate_limiter.reset(key)
    token = create_session(db, user, request.headers.get("User-Agent"))
    user.last_login_at = now_iso()
    db.commit()
    _set_session_cookie(response, token)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "roles": sorted(active_roles(db, user.id)),
            "must_change_password": user.must_change_password,
        },
    }


@router.post("/change-password")
def change_password(
    body: ChangePasswordIn,
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Zmiana hasła (w tym wymuszona dla haseł startowych). Operacja
    wrażliwa: unieważnia WSZYSTKIE dotychczasowe sesje użytkownika (także
    bieżącą) i wydaje nowy token (rotacja) — żaden stary token nie
    pozostaje aktywny. Limit prób chroni przed brute force na obecne
    hasło z przejętej sesji."""
    password_change_rate_limiter.check(user.id)
    if not verify_password(body.current_password, user.password_hash):
        password_change_rate_limiter.record_failure(user.id)
        raise HTTPException(status_code=403, detail="Nieprawidłowe obecne hasło")
    password_change_rate_limiter.reset(user.id)
    try:
        user.password_hash = hash_password(body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    forced = user.must_change_password
    user.must_change_password = False
    # Rotacja tokenu: stare sesje (z bieżącą włącznie) giną, wydajemy nowy.
    revoked = revoke_other_sessions(db, user.id, keep_token=None)
    token = create_session(db, user, request.headers.get("User-Agent"))
    record_event(
        db,
        action="PASSWORD_CHANGED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"forced": forced, "sessions_revoked": revoked, "token_rotated": True},
        summary="Zmiana hasła (rotacja tokenu, wszystkie dotychczasowe sesje unieważnione)",
    )
    db.commit()
    _set_session_cookie(response, token)
    return {"ok": True, "token": token}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Wylogowanie: serwer identyfikuje sesję z tokenu (nagłówek Bearer lub
    ciasteczko) i ustawia revoked_at. Celowo bez zależności current_user —
    wylogowanie ma działać także dla sesji wygasłej."""
    token = _extract_token(request)
    if token:
        row = revoke_session(db, token)
        if row is not None:
            record_event(
                db,
                action="SESSION_LOGGED_OUT",
                actor_id=row.user_id,
                subject_ids=[row.user_id],
                payload={"session_id": row.id},
                summary="Wylogowanie (unieważnienie sesji po stronie serwera)",
            )
        db.commit()
    response.delete_cookie("dzik_session", path="/")
    return {"ok": True}


@router.get("/sessions")
def list_sessions(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Aktywne sesje (urządzenia) bieżącego użytkownika. Nigdy nie zwraca
    tokenów ani ich hashy — tylko metadane i oznaczenie bieżącej sesji."""
    token = _extract_token(request)
    current_hash = _token_hash(token) if token else None
    now = datetime.now(UTC).isoformat()
    rows = (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.created_at.desc())
        .all()
    )
    return {
        "sessions": [
            {
                "id": r.id,
                "created_at": r.created_at,
                "last_used_at": r.last_used_at,
                "expires_at": r.expires_at,
                "user_agent": r.user_agent,
                "current": r.token_hash == current_hash,
            }
            for r in rows
        ]
    }


@router.post("/sessions/{session_id}/revoke")
def revoke_one_session(
    session_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Zakończenie wybranej sesji (np. zapomniane urządzenie). Tylko własnej —
    cudza lub nieznana sesja to 404 (bez ujawniania istnienia); próba
    dotknięcia cudzej AKTYWNEJ sesji jest logowana jako ACCESS_DENIED."""
    from ..authz import deny

    row = db.get(AuthSession, session_id)
    if row is None or row.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Nie znaleziono sesji")
    if row.user_id != user.id:
        deny(user.id, f"auth_session:{session_id}")
    row.revoked_at = now_iso()
    record_event(
        db,
        action="SESSION_REVOKED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"session_id": row.id},
        summary="Zakończenie wybranej sesji przez użytkownika",
    )
    db.commit()
    return {"ok": True, "id": row.id}


@router.post("/sessions/revoke-others")
def revoke_other_user_sessions(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Unieważnienie wszystkich pozostałych sesji użytkownika (wyloguj z
    innych urządzeń) — bieżąca sesja pozostaje aktywna."""
    token = _extract_token(request)
    revoked = revoke_other_sessions(db, user.id, keep_token=token)
    if revoked:
        record_event(
            db,
            action="SESSIONS_REVOKED",
            actor_id=user.id,
            subject_ids=[user.id],
            payload={"count": revoked},
            summary="Unieważnienie pozostałych sesji użytkownika",
        )
    db.commit()
    return {"ok": True, "revoked": revoked}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "identity_id": user.identity_id,
        "roles": sorted(active_roles(db, user.id)),
    }


@router.get("/brand")
def branding():
    return {
        "name": settings.brand_name,
        "coach_name": settings.brand_coach_name,
        "accent": settings.brand_accent,
    }

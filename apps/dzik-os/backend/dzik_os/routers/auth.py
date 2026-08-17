from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..models import User, now_iso
from ..schemas import ChangePasswordIn, LoginRequest
from ..security import (
    _extract_token,
    active_roles,
    create_session,
    current_user,
    hash_password,
    login_rate_limiter,
    revoke_other_sessions,
    revoke_session,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
    response.set_cookie(
        "dzik_session",
        token,
        httponly=True,
        samesite="lax",
        secure=settings.env == "production",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
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
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Zmiana hasła (w tym wymuszona dla haseł startowych). Unieważnia
    pozostałe sesje użytkownika."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=403, detail="Nieprawidłowe obecne hasło")
    try:
        user.password_hash = hash_password(body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    user.must_change_password = False
    token = _extract_token(request)
    revoke_other_sessions(db, user.id, token)
    record_event(
        db,
        action="PASSWORD_CHANGED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"forced": False},
        summary="Zmiana hasła (pozostałe sesje unieważnione)",
    )
    db.commit()
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = _extract_token(request)
    if token:
        revoke_session(db, token)
        db.commit()
    response.delete_cookie("dzik_session", path="/")
    return {"ok": True}


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

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User, now_iso
from ..schemas import LoginRequest
from ..security import (
    active_roles,
    create_session,
    current_user,
    login_rate_limiter,
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
        },
    }


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("dzik_session") or request.headers.get(
        "Authorization", ""
    ).removeprefix("Bearer ").strip()
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

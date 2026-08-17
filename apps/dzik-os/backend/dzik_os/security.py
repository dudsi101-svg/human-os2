from __future__ import annotations

import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import AuthSession, RoleGrant, User, new_id, now_iso

MIN_PASSWORD_LENGTH = 10


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Hasło musi mieć co najmniej {MIN_PASSWORD_LENGTH} znaków")
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def create_session(db: Session, user: User, user_agent: str | None = None) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    db.add(
        AuthSession(
            id=new_id("SES"),
            user_id=user.id,
            token_hash=_token_hash(token),
            expires_at=expires.isoformat(),
            user_agent=(user_agent or "")[:300],
        )
    )
    return token


def revoke_session(db: Session, token: str) -> None:
    row = (
        db.query(AuthSession).filter(AuthSession.token_hash == _token_hash(token)).one_or_none()
    )
    if row is not None:
        row.revoked_at = now_iso()


class LoginRateLimiter:
    """Prosty limiter prób logowania per e-mail (okno przesuwne, w pamięci
    procesu). Chroni przed brute force; przy wdrożeniu wieloprocesowym
    należy przenieść licznik do współdzielonego magazynu (docs/RISK_REGISTER)."""

    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        window = settings.login_lockout_minutes * 60
        now = time.monotonic()
        attempts = [t for t in self._attempts.get(key, []) if now - t < window]
        self._attempts[key] = attempts
        if len(attempts) >= settings.login_max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Zbyt wiele prób logowania. Spróbuj ponownie później.",
            )

    def record_failure(self, key: str) -> None:
        self._attempts.setdefault(key, []).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


login_rate_limiter = LoginRateLimiter()


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.removeprefix("Bearer ").strip()
    return request.cookies.get("dzik_session")


# Ścieżki dostępne mimo flagi must_change_password (zmiana hasła, wylogowanie,
# podgląd własnej sesji).
_PASSWORD_CHANGE_ALLOWED_PATHS = {
    "/api/auth/change-password",
    "/api/auth/logout",
    "/api/auth/me",
}


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Brak uwierzytelnienia")
    row = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == _token_hash(token), AuthSession.revoked_at.is_(None))
        .one_or_none()
    )
    if row is None or row.expires_at <= datetime.now(UTC).isoformat():
        raise HTTPException(status_code=401, detail="Sesja wygasła lub nie istnieje")
    user = db.get(User, row.user_id)
    if user is None or user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Konto nieaktywne")
    if (
        user.must_change_password
        and request.url.path not in _PASSWORD_CHANGE_ALLOWED_PATHS
    ):
        # Egzekwowane po stronie serwera: konto z hasłem startowym nie ma
        # dostępu do danych, dopóki hasło nie zostanie zmienione.
        raise HTTPException(status_code=403, detail="PASSWORD_CHANGE_REQUIRED")
    return user


def revoke_other_sessions(db: Session, user_id: str, keep_token: str | None) -> None:
    keep_hash = _token_hash(keep_token) if keep_token else None
    rows = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .all()
    )
    for row in rows:
        if row.token_hash != keep_hash:
            row.revoked_at = now_iso()


def active_roles(db: Session, user_id: str) -> set[str]:
    now = now_iso()
    rows = (
        db.query(RoleGrant)
        .filter(RoleGrant.user_id == user_id, RoleGrant.revoked_at.is_(None))
        .all()
    )
    return {r.role for r in rows if r.valid_to is None or r.valid_to > now}


def require_role(role: str):
    def dependency(
        user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> User:
        if role not in active_roles(db, user.id):
            raise HTTPException(status_code=403, detail="Brak wymaganej roli")
        return user

    return dependency

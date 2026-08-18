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
    """Serwer przechowuje wyłącznie hash SHA-256 tokenu (AuthSession.token_hash);
    sam token nigdy nie trafia do bazy, logów ani zdarzeń audytu. Kodowanie
    utf-8 (identyczne z ascii dla tokenów z secrets.token_urlsafe) chroni
    przed 500 przy spreparowanym nagłówku spoza ASCII."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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


def session_for_token(db: Session, token: str) -> AuthSession | None:
    return (
        db.query(AuthSession).filter(AuthSession.token_hash == _token_hash(token)).one_or_none()
    )


def revoke_session(db: Session, token: str) -> AuthSession | None:
    """Unieważnia sesję wskazaną tokenem. Zwraca wiersz, jeśli sesja była
    aktywna (do zdarzenia audytu); None dla nieznanego/już unieważnionego."""
    row = session_for_token(db, token)
    if row is not None and row.revoked_at is None:
        row.revoked_at = now_iso()
        return row
    return None


class LoginRateLimiter:
    """Prosty limiter prób logowania per e-mail (okno przesuwne, w pamięci
    procesu). Chroni przed brute force; przy wdrożeniu wieloprocesowym
    należy przenieść licznik do współdzielonego magazynu (docs/RISK_REGISTER).
    Domyślne progi pochodzą z ustawień logowania; instancje dla innych
    operacji (reset hasła) mogą podać własne max_attempts/window_minutes."""

    def __init__(
        self, max_attempts: int | None = None, window_minutes: int | None = None
    ) -> None:
        self._attempts: dict[str, list[float]] = {}
        self._max_attempts = max_attempts
        self._window_minutes = window_minutes

    def check(self, key: str) -> None:
        window = (self._window_minutes or settings.login_lockout_minutes) * 60
        limit = self._max_attempts or settings.login_max_attempts
        now = time.monotonic()
        attempts = [t for t in self._attempts.get(key, []) if now - t < window]
        self._attempts[key] = attempts
        if len(attempts) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Zbyt wiele prób. Spróbuj ponownie później.",
            )

    def record_failure(self, key: str) -> None:
        self._attempts.setdefault(key, []).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


login_rate_limiter = LoginRateLimiter()

# Ten sam mechanizm chroni zmianę hasła (klucz: id użytkownika) — endpoint
# przyjmuje obecne hasło, więc bez limitu byłby wektorem brute force na
# hasło już zalogowanego (np. przejęta karta przeglądarki).
password_change_rate_limiter = LoginRateLimiter()

# Reset hasła: limit per e-mail ORAZ per IP (klucze "email:..."/"ip:...") —
# chroni przed spamem resetów i sondowaniem istnienia kont wolumenem.
password_reset_rate_limiter = LoginRateLimiter(
    max_attempts=settings.reset_max_requests,
    window_minutes=settings.reset_window_minutes,
)

# Kody MFA (klucz: id użytkownika) — 6-cyfrowy kod bez limitu prób byłby
# zgadywalny w rozsądnym czasie.
mfa_rate_limiter = LoginRateLimiter()


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.removeprefix("Bearer ").strip()
    return request.cookies.get("dzik_session")


def request_token(request: Request) -> str | None:
    """Token bieżącego żądania (nagłówek Bearer lub ciasteczko) — dla
    długożyjących połączeń (SSE), które muszą okresowo ponawiać kontrolę
    ważności sesji w trakcie strumienia (session_is_active)."""
    return _extract_token(request)


def session_is_active(db: Session, token: str | None) -> bool:
    """Czy sesja tokenu jest wciąż ważna (nieunieważniona i niewygasła)?
    Używane przez kanał SSE: uwierzytelnienie przy otwarciu strumienia nie
    wystarcza — wylogowanie/unieważnienie musi zamykać też otwarty kanał."""
    if not token:
        return False
    row = (
        db.query(AuthSession)
        .filter(
            AuthSession.token_hash == _token_hash(token),
            AuthSession.revoked_at.is_(None),
        )
        .one_or_none()
    )
    return row is not None and row.expires_at > datetime.now(UTC).isoformat()


# Ścieżki dostępne mimo flagi must_change_password (zmiana hasła, wylogowanie,
# podgląd własnej sesji).
_PASSWORD_CHANGE_ALLOWED_PATHS = {
    "/api/auth/change-password",
    "/api/auth/logout",
    "/api/auth/me",
}

# Ścieżki dostępne dla konta COACH/ADMIN bez skonfigurowanego MFA — okres
# przejściowy trwa wyłącznie do pierwszej konfiguracji; do tego czasu konto
# ma dostęp jedynie do konfiguracji MFA i podstaw własnego konta.
_MFA_SETUP_ALLOWED_PATHS = {
    "/api/auth/mfa/status",
    "/api/auth/mfa/setup",
    "/api/auth/mfa/enable",
    "/api/auth/change-password",
    "/api/auth/logout",
    "/api/auth/me",
}


def mfa_required_roles() -> set[str]:
    return {r.strip() for r in settings.mfa_required_roles.split(",") if r.strip()}


def mfa_setup_required(db: Session, user: User) -> bool:
    """Czy konto MUSI skonfigurować MFA zanim uzyska dostęp do danych
    (rola z listy wymaganych bez potwierdzonego TOTP)."""
    if user.totp_confirmed_at is not None:
        return False
    required = mfa_required_roles()
    return bool(required) and bool(required & active_roles(db, user.id))


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
    # Bezpieczny identyfikator do logu strukturalnego żądania (id, nigdy
    # e-mail) — czytany przez RequestObservabilityMiddleware.
    request.state.user_id = user.id
    # Znacznik ostatniego użycia sesji (ekran aktywnych sesji). Rozdzielczość
    # ~5 min: zapis nie przy każdym żądaniu, tylko gdy poprzedni znacznik jest
    # starszy — commit tutaj jest bezpieczny (pierwsza operacja żądania,
    # brak innych oczekujących zmian w tej sesji ORM).
    now = datetime.now(UTC)
    threshold = (now - timedelta(minutes=5)).isoformat()
    if row.last_used_at is None or row.last_used_at < threshold:
        row.last_used_at = now.isoformat()
        db.commit()
    if (
        user.must_change_password
        and request.url.path not in _PASSWORD_CHANGE_ALLOWED_PATHS
    ):
        # Egzekwowane po stronie serwera: konto z hasłem startowym nie ma
        # dostępu do danych, dopóki hasło nie zostanie zmienione.
        raise HTTPException(status_code=403, detail="PASSWORD_CHANGE_REQUIRED")
    if (
        request.url.path not in _MFA_SETUP_ALLOWED_PATHS
        and mfa_setup_required(db, user)
    ):
        # Rola uprzywilejowana (COACH/ADMIN) bez skonfigurowanego MFA:
        # okres przejściowy do PIERWSZEJ konfiguracji — dostęp wyłącznie
        # do ekranu konfiguracji MFA, potem kod wymagany przy logowaniu.
        raise HTTPException(status_code=403, detail="MFA_SETUP_REQUIRED")
    return user


def revoke_other_sessions(db: Session, user_id: str, keep_token: str | None) -> int:
    """Unieważnia wszystkie aktywne sesje użytkownika poza keep_token
    (keep_token=None → wszystkie, także bieżącą). Zwraca liczbę
    unieważnionych sesji (do zdarzenia audytu)."""
    keep_hash = _token_hash(keep_token) if keep_token else None
    rows = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .all()
    )
    revoked = 0
    for row in rows:
        if row.token_hash != keep_hash:
            row.revoked_at = now_iso()
            revoked += 1
    return revoked


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

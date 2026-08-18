from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..links import password_reset_link
from ..models import (
    AuthSession,
    ClientInvitation,
    MfaChallenge,
    MfaRecoveryCode,
    PasswordResetToken,
    Receipt,
    User,
    new_id,
    now_iso,
)
from ..notifications_provider import provider as notifications
from ..schemas import (
    ActivateAccountIn,
    ActivationInspectIn,
    ChangePasswordIn,
    LoginRequest,
    MfaCodeIn,
    MfaVerifyIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
)
from ..security import (
    _extract_token,
    _token_hash,
    active_roles,
    create_session,
    current_user,
    hash_password,
    login_rate_limiter,
    mfa_rate_limiter,
    mfa_required_roles,
    mfa_setup_required,
    password_change_rate_limiter,
    password_reset_rate_limiter,
    revoke_other_sessions,
    revoke_session,
    verify_password,
)
from ..totp import (
    generate_recovery_code,
    generate_secret,
    normalize_recovery_code,
    provisioning_uri,
    verify_totp,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

RECOVERY_CODES_COUNT = 10


def _user_payload(db: Session, user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "roles": sorted(active_roles(db, user.id)),
        "must_change_password": user.must_change_password,
        "mfa_enabled": user.totp_confirmed_at is not None,
        "mfa_setup_required": mfa_setup_required(db, user),
    }


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


def _open_session(
    db: Session, user: User, request: Request, response: Response, *, method: str
) -> dict:
    """Wspólne zakończenie logowania (po haśle lub po kroku MFA): sesja,
    ciasteczko, znacznik logowania i zdarzenie audytowe (bez sekretów)."""
    token = create_session(db, user, request.headers.get("User-Agent"))
    user.last_login_at = now_iso()
    record_event(
        db,
        action="LOGIN_SUCCEEDED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"method": method},
        summary=f"Zalogowanie ({'hasło + kod MFA' if method != 'password' else 'hasło'})",
    )
    db.commit()
    _set_session_cookie(response, token)
    return {"token": token, "user": _user_payload(db, user)}


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
    if user.totp_confirmed_at is not None:
        # Konto z MFA: poprawne hasło wydaje wyłącznie krótkotrwałe wyzwanie
        # (w bazie tylko hash) — sesja powstaje dopiero po poprawnym kodzie.
        challenge = secrets.token_urlsafe(32)
        db.add(
            MfaChallenge(
                id=new_id("MFC"),
                user_id=user.id,
                token_hash=_token_hash(challenge),
                expires_at=(
                    datetime.now(UTC)
                    + timedelta(minutes=settings.mfa_challenge_ttl_minutes)
                ).isoformat(),
            )
        )
        db.commit()
        return {"mfa_required": True, "mfa_token": challenge}
    return _open_session(db, user, request, response, method="password")


@router.post("/mfa/verify")
def mfa_verify(
    body: MfaVerifyIn, request: Request, response: Response, db: Session = Depends(get_db)
):
    """Drugi krok logowania: kod TOTP (okno ±1 kroku, ochrona przed
    powtórnym użyciem) albo jednorazowy kod odzyskiwania. Nieudana próba
    jest audytowana (bez kodu) i limitowana."""
    now = datetime.now(UTC).isoformat()
    challenge = (
        db.query(MfaChallenge)
        .filter(
            MfaChallenge.token_hash == _token_hash(body.mfa_token),
            MfaChallenge.used_at.is_(None),
            MfaChallenge.expires_at > now,
        )
        .one_or_none()
    )
    if challenge is None:
        raise HTTPException(
            status_code=401, detail="Sesja logowania wygasła — zaloguj się ponownie"
        )
    mfa_rate_limiter.check(challenge.user_id)
    user = db.get(User, challenge.user_id)
    if user is None or user.status != "ACTIVE" or user.totp_confirmed_at is None:
        raise HTTPException(status_code=401, detail="Nieprawidłowy kod")
    method = None
    counter = verify_totp(
        user.totp_secret, body.code, last_counter=user.totp_last_counter
    )
    if counter is not None:
        user.totp_last_counter = counter
        method = "totp"
    else:
        code_hash = _token_hash(normalize_recovery_code(body.code))
        recovery = (
            db.query(MfaRecoveryCode)
            .filter(
                MfaRecoveryCode.user_id == user.id,
                MfaRecoveryCode.code_hash == code_hash,
                MfaRecoveryCode.used_at.is_(None),
            )
            .one_or_none()
        )
        if recovery is not None:
            recovery.used_at = now_iso()
            method = "recovery_code"
            remaining = (
                db.query(MfaRecoveryCode)
                .filter(
                    MfaRecoveryCode.user_id == user.id,
                    MfaRecoveryCode.used_at.is_(None),
                )
                .count()
            )
            record_event(
                db,
                action="MFA_RECOVERY_CODE_USED",
                actor_id=user.id,
                subject_ids=[user.id],
                payload={"remaining_codes": remaining},
                summary="Logowanie kodem odzyskiwania MFA",
            )
    if method is None:
        mfa_rate_limiter.record_failure(challenge.user_id)
        record_event(
            db,
            action="LOGIN_MFA_FAILED",
            actor_id=user.id,
            subject_ids=[user.id],
            payload={"reason": "invalid_code"},
            summary="Nieudana weryfikacja kodu MFA przy logowaniu",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Nieprawidłowy kod")
    mfa_rate_limiter.reset(challenge.user_id)
    challenge.used_at = now_iso()
    return _open_session(db, user, request, response, method=method)


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


# ————— MFA (TOTP, RFC 6238) —————————————————————————————————————————————


@router.get("/mfa/status")
def mfa_status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Stan MFA własnego konta — bez sekretu i bez kodów."""
    recovery_left = (
        db.query(MfaRecoveryCode)
        .filter(MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.used_at.is_(None))
        .count()
    )
    return {
        "enabled": user.totp_confirmed_at is not None,
        "pending": user.totp_secret is not None and user.totp_confirmed_at is None,
        "setup_required": mfa_setup_required(db, user),
        "recovery_codes_left": recovery_left,
    }


@router.post("/mfa/setup")
def mfa_setup(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Generuje sekret TOTP (nieaktywny do potwierdzenia kodem). Jedyny
    moment, w którym sekret opuszcza backend — do wpisania/zeskanowania w
    aplikacji uwierzytelniającej. Ponowne wywołanie przed potwierdzeniem
    wymienia sekret; przy aktywnym MFA → 409 (najpierw wyłącz kodem)."""
    if user.totp_confirmed_at is not None:
        raise HTTPException(status_code=409, detail="MFA jest już aktywne")
    user.totp_secret = generate_secret()
    user.totp_last_counter = None
    db.commit()
    return {
        "secret": user.totp_secret,
        "otpauth_uri": provisioning_uri(
            user.totp_secret, account=user.email, issuer=settings.brand_name
        ),
    }


def _issue_recovery_codes(db: Session, user: User) -> list[str]:
    """Nowy komplet kodów odzyskiwania; wszystkie poprzednie stają się
    nieważne. Zwracane RAZ — w bazie wyłącznie hashe."""
    now = now_iso()
    for old in (
        db.query(MfaRecoveryCode)
        .filter(MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.used_at.is_(None))
        .all()
    ):
        old.used_at = now
    codes = [generate_recovery_code() for _ in range(RECOVERY_CODES_COUNT)]
    for code in codes:
        db.add(
            MfaRecoveryCode(
                id=new_id("MRC"),
                user_id=user.id,
                code_hash=_token_hash(normalize_recovery_code(code)),
            )
        )
    return codes


@router.post("/mfa/enable")
def mfa_enable(
    body: MfaCodeIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Potwierdzenie konfiguracji MFA kodem z aplikacji. Zwraca kody
    odzyskiwania — pokazywane tylko ten jeden raz."""
    if user.totp_confirmed_at is not None:
        raise HTTPException(status_code=409, detail="MFA jest już aktywne")
    if user.totp_secret is None:
        raise HTTPException(status_code=409, detail="Najpierw wygeneruj sekret (setup)")
    mfa_rate_limiter.check(user.id)
    counter = verify_totp(user.totp_secret, body.code)
    if counter is None:
        mfa_rate_limiter.record_failure(user.id)
        raise HTTPException(status_code=403, detail="Nieprawidłowy kod")
    mfa_rate_limiter.reset(user.id)
    user.totp_confirmed_at = now_iso()
    user.totp_last_counter = counter
    codes = _issue_recovery_codes(db, user)
    record_event(
        db,
        action="MFA_ENABLED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"recovery_codes_issued": len(codes)},
        summary="Włączenie MFA (TOTP) na koncie",
    )
    db.commit()
    return {"ok": True, "recovery_codes": codes}


@router.post("/mfa/recovery-codes/regenerate")
def mfa_regenerate_recovery_codes(
    body: MfaCodeIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Nowy komplet kodów odzyskiwania (wymaga aktualnego kodu TOTP);
    wszystkie stare kody przestają działać."""
    if user.totp_confirmed_at is None:
        raise HTTPException(status_code=409, detail="MFA nie jest aktywne")
    mfa_rate_limiter.check(user.id)
    counter = verify_totp(
        user.totp_secret, body.code, last_counter=user.totp_last_counter
    )
    if counter is None:
        mfa_rate_limiter.record_failure(user.id)
        raise HTTPException(status_code=403, detail="Nieprawidłowy kod")
    mfa_rate_limiter.reset(user.id)
    user.totp_last_counter = counter
    codes = _issue_recovery_codes(db, user)
    record_event(
        db,
        action="MFA_RECOVERY_CODES_REGENERATED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"recovery_codes_issued": len(codes)},
        summary="Wygenerowanie nowych kodów odzyskiwania MFA",
    )
    db.commit()
    return {"ok": True, "recovery_codes": codes}


@router.post("/mfa/disable")
def mfa_disable(
    body: MfaCodeIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Wyłączenie MFA (wymaga aktualnego kodu). Niedostępne dla ról z
    obowiązkowym MFA (COACH/ADMIN) — dla nich MFA nie jest opcją."""
    if user.totp_confirmed_at is None:
        raise HTTPException(status_code=409, detail="MFA nie jest aktywne")
    if mfa_required_roles() & active_roles(db, user.id):
        raise HTTPException(
            status_code=403, detail="MFA jest obowiązkowe dla tej roli"
        )
    mfa_rate_limiter.check(user.id)
    counter = verify_totp(
        user.totp_secret, body.code, last_counter=user.totp_last_counter
    )
    if counter is None:
        mfa_rate_limiter.record_failure(user.id)
        raise HTTPException(status_code=403, detail="Nieprawidłowy kod")
    mfa_rate_limiter.reset(user.id)
    user.totp_secret = None
    user.totp_confirmed_at = None
    user.totp_last_counter = None
    now = now_iso()
    for code in (
        db.query(MfaRecoveryCode)
        .filter(MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.used_at.is_(None))
        .all()
    ):
        code.used_at = now
    record_event(
        db,
        action="MFA_DISABLED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={},
        summary="Wyłączenie MFA na koncie",
    )
    db.commit()
    return {"ok": True}


# ————— Aktywacja konta z zaproszenia ————————————————————————————————————


def _valid_invitation(db: Session, token: str) -> tuple[ClientInvitation, User] | None:
    row = (
        db.query(ClientInvitation)
        .filter(ClientInvitation.token_hash == _token_hash(token))
        .one_or_none()
    )
    if (
        row is None
        or row.used_at is not None
        or row.cancelled_at is not None
        or row.expires_at <= datetime.now(UTC).isoformat()
    ):
        return None
    user = db.get(User, row.client_id)
    if user is None or user.status != "PENDING":
        return None
    return row, user


@router.post("/activation/inspect")
def activation_inspect(body: ActivationInspectIn, db: Session = Depends(get_db)):
    """Podgląd ważnego zaproszenia (ekran aktywacji pokazuje, czyje konto
    jest aktywowane). Jedna odpowiedź 404 dla każdego nieważnego tokenu —
    bez rozróżniania wygasły/użyty/anulowany/nieistniejący."""
    found = _valid_invitation(db, body.token)
    if found is None:
        raise HTTPException(status_code=404, detail="Zaproszenie jest nieważne")
    _, user = found
    return {"email": user.email, "display_name": user.display_name}


@router.post("/activate")
def activate_account(body: ActivateAccountIn, db: Session = Depends(get_db)):
    """Aktywacja konta z zaproszenia: klient SAM ustawia hasło (nikt inny
    go nie zna). Token jest jednorazowy — po użyciu nieważny."""
    found = _valid_invitation(db, body.token)
    if found is None:
        raise HTTPException(status_code=404, detail="Zaproszenie jest nieważne")
    invitation, user = found
    try:
        user.password_hash = hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    user.status = "ACTIVE"
    user.must_change_password = False
    invitation.used_at = now_iso()
    record_event(
        db,
        action="ACCOUNT_ACTIVATED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"invitation_id": invitation.id},
        summary="Aktywacja konta z zaproszenia (hasło ustawione przez właściciela)",
    )
    db.commit()
    return {"ok": True}


# ————— Reset hasła ———————————————————————————————————————————————————————

_RESET_GENERIC_RESPONSE = {
    "ok": True,
    "message": (
        "Jeśli konto o podanym adresie istnieje, wysłaliśmy wiadomość "
        "z linkiem do ustawienia nowego hasła."
    ),
}


@router.post("/password-reset/request")
def password_reset_request(
    body: PasswordResetRequestIn, request: Request, db: Session = Depends(get_db)
):
    """Żądanie resetu hasła. Zawsze ta sama odpowiedź — niezależnie od
    istnienia konta (brak enumeracji). Limit prób per e-mail i per IP.
    Link trafia WYŁĄCZNIE e-mailem: przy NullNotificationProvider nie ma
    bezpiecznego kanału doręczenia, więc reset wymaga skonfigurowanego
    dostawcy (ograniczenie opisane w docs/PERMISSIONS.md)."""
    email = body.email.lower()
    client_ip = request.client.host if request.client else "unknown"
    password_reset_rate_limiter.check(f"email:{email}")
    password_reset_rate_limiter.check(f"ip:{client_ip}")
    password_reset_rate_limiter.record_failure(f"email:{email}")
    password_reset_rate_limiter.record_failure(f"ip:{client_ip}")
    user = db.query(User).filter(User.email == email, User.status == "ACTIVE").one_or_none()
    if user is not None:
        now = now_iso()
        for old in (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .all()
        ):
            old.used_at = now  # nowy token unieważnia poprzednie
        token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetToken(
                id=new_id("PRT"),
                user_id=user.id,
                token_hash=_token_hash(token),
                expires_at=(
                    datetime.now(UTC)
                    + timedelta(minutes=settings.reset_token_ttl_minutes)
                ).isoformat(),
            )
        )
        record_event(
            db,
            action="PASSWORD_RESET_REQUESTED",
            actor_id=user.id,
            subject_ids=[user.id],
            payload={"delivery": notifications.name},
            summary="Żądanie resetu hasła (link wysłany e-mailem)",
        )
        db.commit()
        # Treść bez danych zdrowotnych i bez tokenu w logach (link tylko
        # w treści e-maila; NullProvider niczego nie wysyła ani nie loguje).
        notifications.send_email(
            to=user.email,
            subject=f"{settings.brand_name}: ustaw nowe hasło",
            body=(
                "Otrzymaliśmy prośbę o zresetowanie hasła do Twojego konta.\n\n"
                f"Ustaw nowe hasło (link ważny {settings.reset_token_ttl_minutes} min):\n"
                f"{password_reset_link(request, token)}\n\n"
                "Jeśli to nie Ty — zignoruj tę wiadomość; hasło pozostaje "
                "bez zmian."
            ),
        )
    return _RESET_GENERIC_RESPONSE


@router.post("/password-reset/confirm")
def password_reset_confirm(body: PasswordResetConfirmIn, db: Session = Depends(get_db)):
    """Ustawienie nowego hasła z jednorazowego tokenu. Po sukcesie WSZYSTKIE
    dotychczasowe sesje konta zostają unieważnione."""
    now = datetime.now(UTC).isoformat()
    row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == _token_hash(body.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .one_or_none()
    )
    user = db.get(User, row.user_id) if row is not None else None
    if row is None or user is None or user.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Link jest nieważny lub wygasł")
    try:
        user.password_hash = hash_password(body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    user.must_change_password = False
    row.used_at = now_iso()
    revoked = revoke_other_sessions(db, user.id, keep_token=None)
    record_event(
        db,
        action="PASSWORD_RESET_COMPLETED",
        actor_id=user.id,
        subject_ids=[user.id],
        payload={"sessions_revoked": revoked},
        summary="Reset hasła zakończony (wszystkie sesje unieważnione)",
    )
    db.commit()
    return {"ok": True}


# ————— Historia zdarzeń bezpieczeństwa ——————————————————————————————————

# Wyłącznie zdarzenia dotyczące bezpieczeństwa WŁASNEGO konta; pokwitowania
# nigdy nie zawierają tokenów, kodów ani haseł (payload audytu też nie).
_SECURITY_EVENT_ACTIONS = (
    "LOGIN_SUCCEEDED",
    "LOGIN_MFA_FAILED",
    "MFA_ENABLED",
    "MFA_DISABLED",
    "MFA_RECOVERY_CODES_REGENERATED",
    "MFA_RECOVERY_CODE_USED",
    "PASSWORD_CHANGED",
    "PASSWORD_RESET_REQUESTED",
    "PASSWORD_RESET_COMPLETED",
    "ACCOUNT_ACTIVATED",
    "SESSION_LOGGED_OUT",
    "SESSION_REVOKED",
    "SESSIONS_REVOKED",
)


@router.get("/security-events")
def security_events(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Historia istotnych zdarzeń bezpieczeństwa własnego konta (logowania,
    nieudane MFA, resety, kody odzyskiwania) — metadane bez tokenów."""
    rows = (
        db.query(Receipt)
        .filter(
            Receipt.subject_id == user.id,
            Receipt.action.in_(_SECURITY_EVENT_ACTIONS),
        )
        .order_by(Receipt.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "events": [
            {"action": r.action, "summary": r.summary, "created_at": r.created_at}
            for r in rows
        ]
    }


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
        "mfa_enabled": user.totp_confirmed_at is not None,
        "mfa_setup_required": mfa_setup_required(db, user),
    }


@router.get("/brand")
def branding():
    return {
        "name": settings.brand_name,
        "coach_name": settings.brand_coach_name,
        "accent": settings.brand_accent,
    }

"""TOTP (RFC 6238) w czystym Pythonie — bez zewnętrznych zależności.

HMAC-SHA1 + struct ze stdlib wystarczają do pełnej zgodności z
aplikacjami uwierzytelniającymi (Google Authenticator, Aegis, 1Password,
FreeOTP...): krok 30 s, 6 cyfr, sekret base32.

Zasady bezpieczeństwa:
* sekret TOTP jest pokazywany użytkownikowi wyłącznie raz przy
  konfiguracji i NIGDY nie trafia do logów ani łańcucha audytu;
* weryfikacja zwraca licznik (numer 30-sekundowego okna) dopasowanego
  kodu — wywołujący zapisuje go i odrzuca kody z licznikiem <= ostatnio
  użytego (ochrona przed powtórnym użyciem podsłuchanego kodu);
* porównania stałoczasowe (hmac.compare_digest).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6


def generate_secret() -> str:
    """160-bitowy sekret w base32 (zalecenie RFC 4226 §4)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def hotp(secret_b32: str, counter: int, digits: int = TOTP_DIGITS) -> str:
    key = base64.b32decode(secret_b32, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def totp_at(secret_b32: str, timestamp: float) -> str:
    return hotp(secret_b32, int(timestamp // TOTP_STEP_SECONDS))


def verify_totp(
    secret_b32: str | None,
    code: str,
    *,
    timestamp: float | None = None,
    window: int = 1,
    last_counter: int | None = None,
) -> int | None:
    """Zwraca licznik dopasowanego okna (do zapisania jako ostatnio użyty)
    albo None, gdy kod jest błędny, spoza okna ±window kroków lub nie
    nowszy niż ostatnio zaakceptowany (ochrona przed replayem)."""
    if not secret_b32:
        return None
    normalized = code.strip().replace(" ", "")
    if not normalized.isdigit() or len(normalized) != TOTP_DIGITS:
        return None
    now = time.time() if timestamp is None else timestamp
    current = int(now // TOTP_STEP_SECONDS)
    for offset in range(-window, window + 1):
        counter = current + offset
        if counter < 0:
            continue
        if hmac.compare_digest(hotp(secret_b32, counter), normalized):
            if last_counter is not None and counter <= last_counter:
                return None
            return counter
    return None


def provisioning_uri(secret_b32: str, *, account: str, issuer: str) -> str:
    """otpauth:// do wpisania/zeskanowania w aplikacji uwierzytelniającej."""
    label = quote(f"{issuer}:{account}")
    return (
        f"otpauth://totp/{label}?secret={secret_b32}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_STEP_SECONDS}"
    )


RECOVERY_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"  # bez 0/O, 1/I/L


def generate_recovery_code() -> str:
    """Kod odzyskiwania XXXXX-XXXXX (alfabet bez znaków mylących)."""
    raw = "".join(secrets.choice(RECOVERY_CODE_ALPHABET) for _ in range(10))
    return f"{raw[:5]}-{raw[5:]}"


def normalize_recovery_code(code: str) -> str:
    return code.strip().upper().replace("-", "").replace(" ", "")

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Konfiguracja środowiska TESTOWEGO musi nastąpić przed importem dzik_os.
_tmp = tempfile.mkdtemp(prefix="dzik-tests-")
# Domyślnie SQLite, ale zestaw da się puścić na dowolnym silniku przez
# DZIK_TEST_DATABASE_URL — CI używa tego do przebiegu na PostgreSQL.
# Audyt 18.08.2026: PostgreSQL był zadeklarowany w pyproject/backup/modelach,
# a nie wykonała się na nim ani jedna linia.
os.environ["DZIK_DATABASE_URL"] = (
    os.environ.get("DZIK_TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db"
)
os.environ["DZIK_AUDIT_DB"] = f"{_tmp}/audit.db"
os.environ["DZIK_UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["DZIK_VAPID_KEY"] = f"{_tmp}/vapid.pem"
os.environ["DZIK_ENV"] = "test"
os.environ["DZIK_BCRYPT_ROUNDS"] = "4"  # szybkie hasła w testach
# Wymuszanie MFA dla COACH/ADMIN jest globalnie WYŁĄCZONE w testach (inaczej
# każdy test trenera wymagałby konfiguracji TOTP). Dedykowane testy
# egzekwowania (tests/test_mfa.py) włączają je punktowo przez
# monkeypatch(settings, "mfa_required_roles", ...).
os.environ["DZIK_MFA_REQUIRED_ROLES"] = ""

import pytest
from fastapi.testclient import TestClient

from dzik_os import hos_bridge
from dzik_os import seed as seed_module
from dzik_os.db import Base, engine, run_migrations
from dzik_os.main import app
from dzik_os.models import RoleGrant, User, new_id
from dzik_os.security import (
    hash_password,
    login_rate_limiter,
    mfa_rate_limiter,
    password_change_rate_limiter,
    password_reset_rate_limiter,
)

COACH = {"email": "dzik@example.com", "password": "DzikTrener#2026"}
CLIENT_A = {"email": "klient.a@example.com", "password": "KlientA#2026!x"}
CLIENT_B = {"email": "klient.b@example.com", "password": "KlientB#2026!x"}
ADMIN = {"email": "admin@example.com", "password": "DzikAdmin#2026"}


def _reset_state() -> None:
    from sqlalchemy import text

    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))
    hos_bridge.reset_event_store()
    audit = Path(os.environ["DZIK_AUDIT_DB"])
    if audit.exists():
        audit.unlink()
    login_rate_limiter._attempts.clear()
    password_change_rate_limiter._attempts.clear()
    password_reset_rate_limiter._attempts.clear()
    mfa_rate_limiter._attempts.clear()
    from dzik_os.observability import metrics
    from dzik_os.routers.telemetry import report_rate_limiter

    metrics.reset()
    report_rate_limiter._by_ip.clear()
    report_rate_limiter._all.clear()
    run_migrations()


@pytest.fixture()
def client() -> TestClient:
    _reset_state()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded(client: TestClient) -> TestClient:
    seed_module.seed()
    return client


def login(client: TestClient, creds: dict) -> dict:
    r = client.post("/api/auth/login", json=creds)
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def create_user_with_role(email: str, password: str, name: str, role: str) -> str:
    """Pomocnik testowy: bezpośrednio tworzy konto z rolą (np. drugiego
    trenera, który NIE ma relacji z klientami seedu)."""
    from dzik_os.db import db_session

    with db_session() as db:
        user = User(
            id=new_id("USR"), email=email, password_hash=hash_password(password),
            display_name=name, identity_id=new_id("ID"),
        )
        db.add(user)
        db.flush()  # użytkownik przed nadaniem roli (klucz obcy user_id)
        db.add(RoleGrant(id=new_id("ROL"), user_id=user.id, role=role,
                         scope="*", issued_by="test"))
        db.flush()
        return user.id


def get_user_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/auth/me", headers=headers).json()["id"]


def invite_client(
    client: TestClient, coach_headers: dict, email: str, name: str = "Nowy Klient"
) -> dict:
    """Nowy przepływ onboardingu: trener wysyła zaproszenie (bez hasła).
    Zwraca odpowiedź {client_id, relationship_id, invitation}."""
    r = client.post("/api/coach/clients", headers=coach_headers, json={
        "client_email": email, "client_name": name,
    })
    assert r.status_code == 201, r.text
    return r.json()


def activation_token(created: dict) -> str:
    """Token z linku aktywacyjnego (fragment #...) — w testach dostawca
    e-mail to NullProvider, więc link wraca do trenera w odpowiedzi API."""
    link = created["invitation"]["activation_link"]
    return link.split("#", 1)[1]


def activate_account(client: TestClient, token: str, password: str) -> None:
    r = client.post("/api/auth/activate", json={"token": token, "password": password})
    assert r.status_code == 200, r.text


def create_activated_client(
    client: TestClient, coach_headers: dict, email: str,
    password: str = "WlasneHaslo#123", name: str = "Nowy Klient",
) -> str:
    """Pełny nowy przepływ: zaproszenie → aktywacja z własnym hasłem.
    Zwraca client_id."""
    created = invite_client(client, coach_headers, email, name)
    activate_account(client, activation_token(created), password)
    return created["client_id"]


def make_png(width: int = 8, height: int = 8, color=(20, 200, 60)) -> bytes:
    """Prawdziwy, dekodowalny PNG (upload przechodzi magic bytes ORAZ
    przetwarzanie Pillow — nagłówek z dopełnieniem już nie wystarcza)."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def make_jpeg(width: int = 8, height: int = 8, *, exif: bytes | None = None) -> bytes:
    """Prawdziwy JPEG; opcjonalnie z blokiem EXIF (do testów usuwania
    metadanych/geolokalizacji)."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    kwargs = {"exif": exif} if exif else {}
    Image.new("RGB", (width, height), (128, 64, 32)).save(buf, format="JPEG", **kwargs)
    return buf.getvalue()

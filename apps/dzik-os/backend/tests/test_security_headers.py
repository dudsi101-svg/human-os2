"""Nagłówki bezpieczeństwa i cache (http_headers.SecurityHeadersMiddleware):
CSP / nosniff / Referrer-Policy / Permissions-Policy / X-Frame-Options na
każdej odpowiedzi, Cache-Control per klasa ścieżki (API no-store, assety
immutable, HTML/sw.js/manifest no-cache, ikony 24h), HSTS tylko poza dev."""

import io

import pytest
from conftest import CLIENT_A, COACH, login, make_png
from fastapi.testclient import TestClient

from dzik_os.config import settings
from dzik_os.http_headers import CSP_POLICY
from dzik_os.main import create_app


def _assert_security_headers(r) -> None:
    """Komplet nagłówków wymaganych na KAŻDEJ odpowiedzi."""
    assert r.headers["content-security-policy"] == CSP_POLICY
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert (
        r.headers["permissions-policy"]
        == "geolocation=(), camera=(), microphone=(self)"
    )


def test_csp_policy_shape() -> None:
    """Twarde inwarianty polityki: brak unsafe-eval/unsafe-inline i szerokich
    źródeł; obecne dyrektywy wymagane przez PWA (worker, manifest, blob)."""
    assert "unsafe-eval" not in CSP_POLICY
    assert "unsafe-inline" not in CSP_POLICY
    assert "*" not in CSP_POLICY
    assert "http:" not in CSP_POLICY and "https:" not in CSP_POLICY
    for directive in (
        "default-src 'self'",
        "connect-src 'self'",
        "img-src 'self' data: blob:",
        "media-src 'self' blob:",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "worker-src 'self'",
        "manifest-src 'self'",
    ):
        assert directive in CSP_POLICY, directive


def test_api_health_headers(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    _assert_security_headers(r)
    assert r.headers["cache-control"] == "no-store"


def test_api_data_endpoint_no_store(seeded: TestClient) -> None:
    """Endpoint z danymi (profil zalogowanego) — nigdy do cache."""
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/auth/me", headers=ha)
    assert r.status_code == 200
    _assert_security_headers(r)
    assert r.headers["cache-control"] == "no-store"


def test_api_error_responses_have_headers(client: TestClient) -> None:
    """Nagłówki obejmują także odpowiedzi błędne (401/404)."""
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    _assert_security_headers(r)
    assert r.headers["cache-control"] == "no-store"


def test_private_file_no_store_and_nosniff(seeded: TestClient) -> None:
    """Plik prywatny (/api/files/...): no-store + nosniff gwarantowane przez
    middleware (files.py już ich nie duplikuje)."""
    ha = login(seeded, CLIENT_A)
    r = seeded.post(
        "/api/files", headers=ha,
        files={"file": ("foto.png", io.BytesIO(make_png()), "image/png")},
    )
    assert r.status_code == 201
    r = seeded.get(f"/api/files/{r.json()['id']}", headers=ha)
    assert r.status_code == 200
    _assert_security_headers(r)
    assert r.headers["cache-control"] == "no-store"
    assert "content-disposition" in r.headers


def test_hsts_absent_in_dev_and_test(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "env", "dev")
    r = client.get("/api/health")
    assert "strict-transport-security" not in r.headers


def test_hsts_present_in_production(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "env", "production")
    r = client.get("/api/health")
    assert (
        r.headers["strict-transport-security"]
        == "max-age=31536000; includeSubDomains"
    )


# --- Frontend (HTML / assety / sw.js / manifest / ikony) ------------------
# Osobna aplikacja z podstawionym dist (DZIK_FRONTEND_DIST), żeby testy nie
# zależały od tego, czy frontend/dist został zbudowany w repo.


@pytest.fixture()
def frontend_client(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "icons").mkdir()
    (dist / "index.html").write_text("<!doctype html><div id=root></div>")
    (dist / "sw.js").write_text("// service worker")
    (dist / "manifest.webmanifest").write_text("{}")
    (dist / "assets" / "index-HASH1234.js").write_text("console.log(1)")
    (dist / "icons" / "icon-192.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setenv("DZIK_FRONTEND_DIST", str(dist))
    with TestClient(create_app()) as c:
        yield c


def test_html_no_cache(frontend_client: TestClient) -> None:
    for path in ("/", "/login", "/nieistniejaca/podstrona"):  # SPA fallback
        r = frontend_client.get(path)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        _assert_security_headers(r)
        assert r.headers["cache-control"] == "no-cache"


def test_hashed_assets_immutable(frontend_client: TestClient) -> None:
    r = frontend_client.get("/assets/index-HASH1234.js")
    assert r.status_code == 200
    _assert_security_headers(r)
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_sw_js_and_manifest_no_cache(frontend_client: TestClient) -> None:
    """sw.js MUSI być no-cache — inaczej aktualizacje PWA nigdy nie dotrą."""
    for path in ("/sw.js", "/manifest.webmanifest"):
        r = frontend_client.get(path)
        assert r.status_code == 200
        _assert_security_headers(r)
        assert r.headers["cache-control"] == "no-cache"


def test_icons_short_cache(frontend_client: TestClient) -> None:
    r = frontend_client.get("/icons/icon-192.png")
    assert r.status_code == 200
    _assert_security_headers(r)
    assert r.headers["cache-control"] == "public, max-age=86400"


def test_docs_csp_exception_is_scoped(client: TestClient) -> None:
    """Jedyny wyjątek CSP: /api/docs (Swagger, wyłączony na produkcji).
    Ścieżka obok (/api/health) dostaje pełną politykę — wyjątek nie
    rozlewa się na resztę API."""
    r = client.get("/api/docs")
    assert r.status_code == 200
    csp = r.headers["content-security-policy"]
    assert "https://cdn.jsdelivr.net" in csp
    assert "frame-ancestors 'none'" in csp
    assert client.get("/api/health").headers["content-security-policy"] == CSP_POLICY


def test_coach_login_flow_headers(seeded: TestClient) -> None:
    """Ścieżka z danymi trenera: lista klientów — no-store + komplet."""
    hc = login(seeded, COACH)
    r = seeded.get("/api/coach/clients", headers=hc)
    assert r.status_code == 200
    _assert_security_headers(r)
    assert r.headers["cache-control"] == "no-store"

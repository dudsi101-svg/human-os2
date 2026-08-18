"""Serwowanie PWA przez backend: typy MIME, nagłówki cache i zasada
"brakujący asset NIGDY nie dostaje index.html".

HTML zwrócony zamiast JS/CSS to błąd MIME w przeglądarce i pusty ekran
aplikacji — dlatego ścieżki plikowe bez pliku muszą kończyć się 404.
Testy używają sztucznego dist/ (nie wymagają zbudowanego frontendu).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FRONTEND_SW = (
    Path(__file__).resolve().parents[2] / "frontend" / "public" / "sw.js"
)


@pytest.fixture()
def spa_client(tmp_path: Path):
    """Aplikacja z jawnym DZIK_FRONTEND_DIST wskazującym sztuczny build."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "icons").mkdir()
    (dist / "index.html").write_text("<!doctype html><div id=root></div>")
    (dist / "sw.js").write_text("self.__BUILD_VERSION = 'test';")
    (dist / "manifest.webmanifest").write_text('{"name": "Dzik OS"}')
    (dist / "assets" / "index-abc123.js").write_text("export {};")
    (dist / "assets" / "index-abc123.css").write_text("body{}")
    (dist / "icons" / "icon-192.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    old = os.environ.get("DZIK_FRONTEND_DIST")
    os.environ["DZIK_FRONTEND_DIST"] = str(dist)
    try:
        from dzik_os.main import create_app

        # create_app() czyta DZIK_FRONTEND_DIST w momencie wywołania —
        # świeża instancja, bez dotykania globalnego `app` z conftest.
        # Bez kontekstu lifespan: testy dotyczą wyłącznie tras statycznych.
        yield TestClient(create_app())
    finally:
        if old is None:
            os.environ.pop("DZIK_FRONTEND_DIST", None)
        else:
            os.environ["DZIK_FRONTEND_DIST"] = old


def test_sw_js_mime_and_no_cache(spa_client: TestClient):
    r = spa_client.get("/sw.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/javascript")
    # Service worker musi być zawsze rewalidowany, inaczej przeglądarka
    # może bardzo długo nie zobaczyć nowej wersji aplikacji.
    assert r.headers["cache-control"] == "no-cache"


def test_hashed_assets_mime_and_immutable(spa_client: TestClient):
    r = spa_client.get("/assets/index-abc123.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/javascript")
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"

    r = spa_client.get("/assets/index-abc123.css")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/css")


def test_manifest_mime(spa_client: TestClient):
    r = spa_client.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/manifest+json")
    assert r.headers["cache-control"] == "no-cache"


def test_navigations_get_html_shell(spa_client: TestClient):
    for path in ("/", "/plan", "/wiadomosci/W-123"):
        r = spa_client.get(path)
        assert r.status_code == 200, path
        assert r.headers["content-type"].startswith("text/html"), path
        assert r.headers["cache-control"] == "no-cache", path
        assert "root" in r.text, path


def test_missing_asset_is_404_never_html(spa_client: TestClient):
    """Brakujący plik NIGDY nie dostaje index.html (błąd MIME → pusty ekran)."""
    for path in (
        "/assets/nie-ma-takiego-x9z.js",
        "/assets/nie-ma-takiego-x9z.css",
        "/icons/nie-ma-takiej.png",
        "/fonts/nie-ma-takiego.woff2",
        "/stary-hash-index-deadbeef.js",
    ):
        r = spa_client.get(path)
        assert r.status_code == 404, path
        assert not r.headers.get("content-type", "").startswith("text/html") or (
            "root" not in r.text
        ), path


def test_api_routes_not_shadowed_by_spa(spa_client: TestClient):
    r = spa_client.get("/api/health")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["ok"] is True


def test_source_service_worker_contract():
    """Kontrakt źródłowego sw.js: push i update-flow nie mogą zniknąć,
    /api pozostaje network-only, a fallbackiem nawigacji jest shell."""
    src = FRONTEND_SW.read_text(encoding="utf-8")
    assert 'self.addEventListener("push"' in src
    assert 'self.addEventListener("notificationclick"' in src
    # skipWaiting wyłącznie na jawny komunikat użytkownika (UpdateBanner),
    # nigdy automatycznie przy instalacji.
    assert src.count("self.skipWaiting()") == 1
    assert 'event.data.type === "SKIP_WAITING"' in src
    # API nigdy nie jest przejmowane przez service workera.
    assert 'url.pathname.startsWith("/api")' in src
    # Fallback nawigacji to precache'owany shell, nie runtime'owe "/".
    assert "/index.html" in src

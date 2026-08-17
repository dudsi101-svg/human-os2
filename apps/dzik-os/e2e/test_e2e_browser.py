"""E2E w przeglądarce (Playwright + Chromium): logowanie klienta i trenera
na zbudowanym froncie serwowanym przez backend.

Uruchomienie (wymaga wcześniejszego `npm run build` we frontend/):
    pip install playwright && playwright install chromium
    pytest apps/dzik-os/e2e -q
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    pytest.skip("playwright not installed", allow_module_level=True)

APP_DIR = Path(__file__).resolve().parents[1]
DIST = APP_DIR / "frontend" / "dist"

# Jawna ścieżka do Chromium (np. w środowiskach z preinstalowaną przeglądarką,
# gdzie wersja pobierana przez `playwright install` nie jest dostępna).
CHROMIUM = os.environ.get("DZIK_E2E_CHROMIUM") or (
    "/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else None
)


def _launch(pw):
    return pw.chromium.launch(executable_path=CHROMIUM)

pytestmark = pytest.mark.skipif(
    not DIST.is_dir(), reason="frontend/dist missing — run `npm run build` first"
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    port = _free_port()
    tmp = tempfile.mkdtemp(prefix="dzik-e2e-")
    env = dict(
        os.environ,
        DZIK_DATABASE_URL=f"sqlite:///{tmp}/e2e.db",
        DZIK_AUDIT_DB=f"{tmp}/audit.db",
        DZIK_UPLOAD_DIR=f"{tmp}/uploads",
        DZIK_ENV="test",
        DZIK_BCRYPT_ROUNDS="4",
    )
    subprocess.run(
        [sys.executable, "-m", "dzik_os.seed"], env=env, cwd=tmp, check=True,
        capture_output=True,
    )
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "dzik_os.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        env=env, cwd=tmp,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.2)
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def _login(page, url: str, email: str, password: str) -> None:
    page.goto(f"{url}/login")
    page.fill("#email", email)
    page.fill("#password", password)
    page.click("button:has-text('Zaloguj się')")
    page.wait_for_load_state("networkidle")


def test_client_login_and_today_screen(server_url):
    with sync_playwright() as pw:
        browser = _launch(pw)
        page = browser.new_page(viewport={"width": 390, "height": 844})  # telefon
        _login(page, server_url, "klient.a@example.com", "KlientA#2026!x")
        page.wait_for_selector("h1:has-text('Dzisiaj')")
        assert page.locator("text=Raport tygodniowy").first.is_visible()
        assert page.locator("text=Prowadzenie miesięczne PRO").first.is_visible()
        page.click("nav >> text=Plan")
        page.wait_for_selector("h1:has-text('Plan treningowy')")
        assert page.locator("text=Historia wersji").first.is_visible()
        browser.close()


def test_coach_login_and_dashboard(server_url):
    with sync_playwright() as pw:
        browser = _launch(pw)
        page = browser.new_page(viewport={"width": 1280, "height": 900})  # desktop
        _login(page, server_url, "dzik@example.com", "DzikTrener#2026")
        page.wait_for_selector("h1:has-text('Klienci')")
        assert page.locator("text=Klient Testowy A").first.is_visible()
        assert page.locator("text=Klient Testowy B").first.is_visible()
        page.click("text=Klient Testowy A")
        page.wait_for_selector("h1:has-text('Klient Testowy A')")
        page.click("button:has-text('Historia')")
        page.wait_for_selector("text=łańcucha audytu")
        browser.close()


def test_pwa_manifest_served(server_url):
    import urllib.request

    with urllib.request.urlopen(f"{server_url}/manifest.webmanifest") as resp:
        assert resp.status == 200
        body = resp.read().decode()
        assert '"Dzik OS' in body
    with urllib.request.urlopen(f"{server_url}/sw.js") as resp:
        assert resp.status == 200

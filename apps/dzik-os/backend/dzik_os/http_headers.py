"""Nagłówki bezpieczeństwa i cache — jedno źródło prawdy dla całej aplikacji.

Middleware ustawia na KAŻDEJ odpowiedzi (także błędach) komplet nagłówków
bezpieczeństwa oraz politykę Cache-Control zależną od klasy ścieżki.
Poszczególne routery NIE duplikują tych nagłówków (files.py robił to
historycznie — patrz test_files_security; teraz gwarancję daje middleware).

Polityka CSP została zbudowana na podstawie rzeczywiście używanych zasobów
zbudowanego frontendu (frontend/dist):
- brak inline <script> i inline <style> (Vite emituje wyłącznie pliki
  w /assets, index.html linkuje je przez src/href) — stąd bez
  'unsafe-inline' i bez 'unsafe-eval';
- React ustawia style elementów przez CSSOM (element.style.x = ...),
  co NIE podlega style-src — atrybuty style w JSX nie wymagają wyjątków;
- fonty (Unbounded, Inter) są self-hostowane przez @fontsource i trafiają
  do /assets — stąd font-src 'self' (zero zapytań do Google Fonts);
- podglądy plików i eksporty używają URL.createObjectURL — stąd blob:
  w img-src (zdjęcia) i media-src (głosówki/wideo);
- data: w img-src pozostaje dla małych ikon/podglądów generowanych w JS.

Wyjątek ŚWIADOMY i jedyny: /api/docs (Swagger UI, wyłączone na produkcji
w create_app) ładuje skrypt/styl z CDN i używa inline skryptu startowego —
dostaje własną, poluzowaną CSP ograniczoną do tej jednej ścieżki.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .config import settings

# Content-Security-Policy aplikacji (frontend PWA + API, same-origin).
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data: blob:; "
    "media-src 'self' blob:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "worker-src 'self'; "
    "manifest-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

# Swagger UI (tylko poza produkcją): skrypt+styl z jsdelivr, inline skrypt
# inicjalizujący SwaggerUIBundle, favicon z fastapi.tiangolo.com.
CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

# Permissions-Policy: mikrofon zostaje dla self (głosówki w Thread.tsx —
# navigator.mediaDevices.getUserMedia({audio: true})). Kamera jest używana
# wyłącznie przez <input type="file"> (natywny selektor systemowy, m.in.
# aparat na iOS), którego Permissions-Policy NIE obejmuje — getUserMedia
# z wideo nie występuje w kodzie, więc camera można bezpiecznie wyłączyć.
PERMISSIONS_POLICY = "geolocation=(), camera=(), microphone=(self)"

HSTS = "max-age=31536000; includeSubDomains"

# Cache-Control per klasa odpowiedzi:
CACHE_API = "no-store"  # dane (w tym zdrowotne) — nigdy do cache
CACHE_IMMUTABLE = "public, max-age=31536000, immutable"  # hashowane assety
CACHE_FRESH = "no-cache"  # HTML/sw.js/manifest — zawsze rewalidacja
CACHE_ICONS = "public, max-age=86400"  # ikony PWA — krótki cache


def _cache_control(path: str, content_type: str) -> str:
    if path == "/api" or path.startswith("/api/"):
        # Wszystkie odpowiedzi API — bez wyjątku no-store (pliki prywatne,
        # dane zdrowotne, tokeny). Obejmuje też błędy.
        return CACHE_API
    if path.startswith("/assets/"):
        # Vite: nazwy plików zawierają hash treści — bezpieczny rok cache.
        return CACHE_IMMUTABLE
    if path.startswith("/icons/"):
        return CACHE_ICONS
    # HTML (SPA fallback), /sw.js (KONIECZNIE świeży — inaczej aktualizacje
    # PWA nigdy nie dotrą), /manifest.webmanifest i wszystko pozostałe:
    # no-cache = użyj cache dopiero po rewalidacji (ETag/Last-Modified).
    del content_type  # klasyfikacja po ścieżce wystarcza
    return CACHE_FRESH


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Nagłówki bezpieczeństwa + Cache-Control dla każdej odpowiedzi."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        path = request.url.path
        headers = response.headers

        docs_page = path in ("/api/docs", "/api/docs/oauth2-redirect")
        headers["Content-Security-Policy"] = CSP_DOCS if docs_page else CSP_POLICY
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"  # starsze przeglądarki; nowsze: frame-ancestors
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        headers["Permissions-Policy"] = PERMISSIONS_POLICY
        if settings.env != "dev":
            # HSTS tylko poza dev (lokalnie brak TLS); na Fly.io TLS
            # terminuje proxy z force_https=true.
            headers["Strict-Transport-Security"] = HSTS
        headers["Cache-Control"] = _cache_control(
            path, headers.get("content-type", "")
        )
        return response

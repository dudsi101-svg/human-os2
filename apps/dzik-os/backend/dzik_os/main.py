from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import run_migrations
from .routers import (
    admin,
    auth,
    checkins,
    clients,
    consultations,
    exercises,
    files,
    food_catalog,
    knowledge,
    measurements,
    messages,
    monitoring,
    nutrition,
    payments,
    plans,
    privacy,
    profile,
    push,
    records,
    schedule,
    today,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    run_migrations()
    if os.environ.get("DZIK_SEED_DEMO") == "true":
        # Staging: jednorazowy zasiew danych demo (seed sam pomija
        # niepustą bazę, więc restart maszyny nic nie duplikuje).
        try:
            from . import seed as seed_module

            seed_module.seed()
        # Celowo łapiemy każdy wyjątek: nieudany seed demo nie może
        # zatrzymać startu aplikacji na stagingu.
        except Exception as exc:  # noqa: BLE001  # pragma: no cover - diagnostyka staging
            print(f"[dzik-os] seed demo nieudany: {exc}")
    # Pętla przypomnień push (harmonogram + jednorazowe przypomnienia).
    # Wymaga działającej maszyny — patrz fly.toml (min_machines_running).
    from . import reminder_loop

    reminders = asyncio.create_task(reminder_loop.run_reminder_loop())
    try:
        yield
    finally:
        reminders.cancel()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dzik OS — Panel Podopiecznego",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.env != "production" else None,
        redoc_url=None,
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    for router in (
        auth.router, clients.router, profile.router, plans.router,
        nutrition.router, schedule.router, checkins.router,
        measurements.router, messages.router, files.router,
        payments.router, privacy.router, today.router, admin.router,
        monitoring.router, knowledge.router, exercises.router, food_catalog.router,
        records.router, push.router, consultations.router,
    ):
        app.include_router(router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "app": settings.brand_name, "env": settings.env}

    # Serwowanie zbudowanego frontendu (PWA). Ścieżka jawna przez
    # DZIK_FRONTEND_DIST (obraz produkcyjny — pakiet w site-packages nie
    # zna układu repo); fallback: układ repozytorium (uruchomienie z kodu).
    dist_env = os.environ.get("DZIK_FRONTEND_DIST")
    frontend_dist = (
        Path(dist_env)
        if dist_env
        else Path(__file__).resolve().parents[2] / "frontend" / "dist"
    )
    if frontend_dist.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=frontend_dist / "assets"),
            name="assets",
        )

        @app.middleware("http")
        async def asset_cache_headers(request: Request, call_next):
            # Hashowane assety Vite są niezmienne per wersja — mogą żyć
            # w cache przeglądarki na zawsze (nowa wersja = nowy hash).
            response = await call_next(request)
            if request.url.path.startswith("/assets/") and response.status_code == 200:
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return response

        # Jawne typy MIME dla plików, których mimetypes potrafi nie znać
        # (zły Content-Type dla sw.js/modułów = odmowa wykonania w PWA).
        media_types = {
            ".js": "text/javascript",
            ".mjs": "text/javascript",
            ".css": "text/css",
            ".webmanifest": "application/manifest+json",
        }
        # Punkty wejścia PWA muszą być zawsze rewalidowane (inaczej
        # przeglądarka może długo nie zobaczyć nowej wersji aplikacji
        # i service workera); hashowane assety — patrz middleware wyżej.
        no_cache = {"Cache-Control": "no-cache"}

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            candidate = frontend_dist / full_path
            if full_path and candidate.is_file() and candidate.resolve().is_relative_to(
                frontend_dist.resolve()
            ):
                suffix = candidate.suffix.lower()
                headers = (
                    no_cache
                    if suffix in {".html", ".webmanifest"} or full_path == "sw.js"
                    else None
                )
                return FileResponse(
                    candidate, media_type=media_types.get(suffix), headers=headers
                )
            # Ścieżka plikowa (segment z rozszerzeniem), a pliku nie ma →
            # 404. NIGDY index.html: HTML zwrócony zamiast JS/CSS/obrazka
            # to błąd MIME i pusty ekran aplikacji.
            last_segment = full_path.rsplit("/", 1)[-1]
            if "." in last_segment:
                raise HTTPException(status_code=404)
            return FileResponse(frontend_dist / "index.html", headers=no_cache)

    return app


app = create_app()

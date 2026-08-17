from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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
        except Exception as exc:  # pragma: no cover - diagnostyka staging
            print(f"[dzik-os] seed demo nieudany: {exc}")
    yield


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

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            candidate = frontend_dist / full_path
            if full_path and candidate.is_file() and candidate.resolve().is_relative_to(
                frontend_dist.resolve()
            ):
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()

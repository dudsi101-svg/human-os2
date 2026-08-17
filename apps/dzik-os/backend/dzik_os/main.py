from __future__ import annotations

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
    files,
    measurements,
    messages,
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
    ):
        app.include_router(router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "app": settings.brand_name, "env": settings.env}

    # Serwowanie zbudowanego frontendu (PWA) — jeżeli istnieje katalog dist.
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
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

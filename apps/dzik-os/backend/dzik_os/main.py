from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from .authz import ResourceAccessDenied
from .config import settings
from .db import db_session, engine, run_migrations
from .hos_bridge import record_event
from .http_headers import SecurityHeadersMiddleware
from .observability import (
    ErrorEnvelopeMiddleware,
    RequestObservabilityMiddleware,
    error_response,
    exception_fields,
    http_exception_handler,
    log_json,
    metrics,
    validation_exception_handler,
)
from .routers import (
    admin,
    assistant,
    auth,
    cardio,
    challenges,
    checkins,
    clients,
    consultations,
    diet,
    exercise_blocks,
    exercises,
    files,
    food_catalog,
    habits,
    imports,
    interview,
    knowledge,
    konfigurator,
    kulinaria,
    mail_admin,
    measurements,
    messages,
    monitoring,
    nutrition,
    nutrition_templates,
    ocr,
    onboarding,
    payments,
    plan_weekdays,
    plans,
    postepy,
    privacy,
    profile,
    public_site,
    push,
    records,
    schedule,
    szkice,
    telemetry,
    today,
    wiedza,
    wywiady,
    zapotrzebowanie,
)
from .routers import (
    notifications as notifications_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    run_migrations()
    # Wiedza (0.56.0): szkice pakietu importowane idempotentnie po
    # (id, rewizja) — nigdy nie nadpisują zmian redakcyjnych.
    from .wiedza import tresci as wiedza_tresci

    try:
        with db_session() as db:
            wiedza_tresci.zaimportuj_startowe(db)
    # Świadomie łapiemy każdy wyjątek: brak albo uszkodzenie pliku treści
    # startowych nie może położyć całej aplikacji (13.09.2026: obraz bez
    # plików JSON → 10 restartów → maszyna zatrzymana → produkcja
    # niedostępna). Biblioteka Wiedzy zostaje wtedy pusta, a błąd jest
    # zalogowany strukturalnie i widoczny w /api/health (wiedza_import).
    except Exception as exc:  # noqa: BLE001
        log_json("wiedza_import_failed", level="error", **exception_fields(exc))
        app.state.wiedza_import_error = type(exc).__name__
    # Wywiad (0.59.0): ponawialne przeniesienie sesji rozmowy startowej
    # i głębokiego wywiadu do wersji formularzy — bez powiadomień, bez
    # usuwania starych danych; błąd nie zatrzymuje startu.
    try:
        from .wywiad import migracja as wywiad_migracja

        with db_session() as db:
            wywiad_migracja.migruj(db)
    except Exception as exc:  # noqa: BLE001
        log_json("wywiad_migracja_failed", level="error", **exception_fields(exc))
        app.state.wywiad_migracja_error = type(exc).__name__
    # Szablony diet (0.60.0/0.64.0): seed produktów i biblioteki 45 odsłon
    # przy włączonej fladze — idempotentnie (skrót pliku); błąd nie zatrzymuje
    # startu. `DZIK_DIET_SEED_ON_STARTUP=false` wyłącza sam seed (testy).
    if settings.diet_templates_enabled and settings.diet_seed_on_startup:
        try:
            from .dieta import seed as dieta_seed

            with db_session() as db:
                dieta_seed.zaseeduj(db)
        except Exception as exc:  # noqa: BLE001
            log_json("diet_seed_failed", level="error", **exception_fields(exc))
            app.state.diet_seed_error = type(exc).__name__
    # Poczta Brevo (0.61.0, `dzik_os.mailer`): jedna konfiguracja na proces;
    # brak zmiennych SMTP = MAIL_ENABLED=0 z ostrzeżeniem, aplikacja wstaje.
    try:
        from . import poczta_start

        poczta_start.zainicjalizuj(app)
    except Exception as exc:  # noqa: BLE001 - poczta nie może wywrócić startu
        log_json("mail_init_failed", level="error", **exception_fields(exc))
        app.state.mail_config = None
        app.state.mail_missing = []
    if os.environ.get("DZIK_SEED_DEMO") == "true":
        # Staging: jednorazowy zasiew danych demo (seed sam pomija
        # niepustą bazę, więc restart maszyny nic nie duplikuje).
        try:
            from . import seed as seed_module

            seed_module.seed()
        # Celowo łapiemy każdy wyjątek: nieudany seed demo nie może
        # zatrzymać startu aplikacji na stagingu.
        except Exception as exc:  # noqa: BLE001  # pragma: no cover - diagnostyka staging
            log_json("seed_demo_failed", level="error", **exception_fields(exc))
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
    # Kolejność middleware (dodany PÓŹNIEJ = bardziej zewnętrzny):
    # 1. ErrorEnvelopeMiddleware (najgłębiej) — nieobsłużony wyjątek staje
    #    się odpowiedzią 500 we wspólnym modelu błędów, ZANIM opuści łańcuch,
    #    więc nagłówki bezpieczeństwa i request id obejmują też błędy 500.
    # 2. SecurityHeadersMiddleware — CSP, HSTS, nosniff, Cache-Control
    #    (jedno źródło prawdy, patrz http_headers.py).
    # 3. RequestObservabilityMiddleware (najbardziej zewnętrzny) —
    #    X-Request-Id + strukturalny log żądań + metryki.
    app.add_middleware(ErrorEnvelopeMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestObservabilityMiddleware)
    # Wspólny model błędów: {detail, code, request_id[, errors]} — patrz
    # observability.py. Kształty odpowiedzi SUKCESU pozostają bez zmian.
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # CORS: domyślnie DZIK_CORS_ORIGINS jest puste i middleware CORS w ogóle
    # nie jest dodawany — produkcja jest SAME-ORIGIN (backend serwuje
    # zbudowany frontend spod tej samej domeny). Zmienna istnieje wyłącznie
    # na wypadek świadomego wdrożenia frontendu pod innym originem; nigdy
    # nie ustawiać otwartych/wildcard originów przy allow_credentials.
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
        monitoring.router, knowledge.router, wiedza.router, exercises.router, food_catalog.router,
        records.router, push.router, consultations.router, telemetry.router,
        challenges.router, notifications_router.router, onboarding.router,
        interview.router, nutrition_templates.router, ocr.router, assistant.router, imports.router,
        public_site.router, konfigurator.router, kulinaria.router, szkice.router, wywiady.router, zapotrzebowanie.router, diet.router, habits.router,
        mail_admin.router, postepy.router, plan_weekdays.router,
        cardio.router, exercise_blocks.router,
    ):
        app.include_router(router)

    @app.exception_handler(ResourceAccessDenied)
    def access_denied_handler(request: Request, exc: ResourceAccessDenied):
        """Centralne logowanie odmów ZASOBOWYCH (404 po autoryzacji roli —
        próba IDOR / dostęp poza zakresem relacji lub zgód). Payload zawiera
        wyłącznie endpoint, metodę i identyfikatory — nigdy dane zdrowotne
        ani sekrety. Zwykłe 401/403 oraz 404 dla nieistniejących zasobów
        nie przechodzą tą ścieżką."""
        metrics.inc("access_denied")
        try:
            with db_session() as db:
                record_event(
                    db,
                    action="ACCESS_DENIED",
                    actor_id=exc.actor_id,
                    subject_ids=[exc.actor_id],
                    payload={
                        "endpoint": request.url.path,
                        "method": request.method,
                        "resource": exc.resource,
                    },
                    summary=f"Odmowa dostępu do zasobu: {request.method} {request.url.path}",
                )
        # Logowanie odmowy nie może zmienić odpowiedzi dla klienta —
        # awaria audytu jest diagnozowana osobno (verify_chain);
        # licznik audit_log_failures pozwala ją zauważyć w /api/metrics.
        except Exception as log_exc:  # noqa: BLE001  # pragma: no cover - diagnostyka
            metrics.inc("audit_log_failures")
            log_json(
                "audit_append_failed", level="error", action="ACCESS_DENIED",
                **exception_fields(log_exc),
            )
        return error_response(404, "Nie znaleziono")

    # Najwyższy zastosowany numer migracji — leniwie przy PIERWSZYM
    # zapytaniu health (migracje biegną w starcie aplikacji, więc licznik
    # przy tworzeniu appki byłby pusty) i dalej z pamięci podręcznej
    # (uptime-check nie może odpytywać bazy przy każdym pingu).
    _migracja_cache: list[int | None] = []

    def _migracja() -> int | None:
        if not _migracja_cache:
            try:
                with db_session() as _db:
                    _migracja_cache.append(
                        _db.execute(
                            text("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
                        ).scalar()
                    )
            except Exception:  # noqa: BLE001 — health ma wstać nawet bez tabeli
                return None
        return _migracja_cache[0]

    @app.get("/api/health")
    def health() -> dict:
        """Audyt P1-5: health identyfikuje uruchomioną wersję — smoke test
        po deployu porównuje `build` z wdrażanym SHA zamiast wierzyć,
        że odpowiada właściwa instancja."""
        return {
            "ok": True,
            "app": settings.brand_name,
            "env": settings.env,
            "version": settings.app_version,
            "build": settings.build_sha[:12],
            "migration": _migracja(),
            # None = import treści startowych Wiedzy przeszedł; nazwa
            # wyjątku = aplikacja wstała bez treści (patrz lifespan).
            "wiedza_import_error": getattr(app.state, "wiedza_import_error", None),
            "wywiad_migracja_error": getattr(app.state, "wywiad_migracja_error", None),
            "diet_seed_error": getattr(app.state, "diet_seed_error", None),
            "features": {"diet_templates": settings.diet_templates_enabled,
                         "mail_test_endpoint": settings.mail_test_endpoint_enabled,
                         "calorie_interview": settings.calorie_interview_enabled,
                         "monitoring_tab": settings.monitoring_tab_enabled,
                         "diet_wizard": settings.diet_wizard_enabled},
        }

    @app.get("/api/ready")
    def ready():
        """Readiness: baza odpowiada i katalog uploadów jest zapisywalny.
        Bez sekretów i bez ścieżek — wyłącznie nazwy testów i wynik."""
        checks = {"database": False, "uploads_writable": False}
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = True
        except Exception as exc:  # noqa: BLE001 - readiness raportuje, nie wywraca
            log_json("readiness_check_failed", level="error", check="database",
                     **exception_fields(exc))
        try:
            probe = Path(settings.upload_dir) / f".ready-{os.getpid()}"
            probe.write_bytes(b"ok")
            probe.unlink()
            checks["uploads_writable"] = True
        except Exception as exc:  # noqa: BLE001 - readiness raportuje, nie wywraca
            log_json("readiness_check_failed", level="error", check="uploads_writable",
                     **exception_fields(exc))
        ok = all(checks.values())
        body = {"ok": ok, "checks": checks}
        return body if ok else JSONResponse(status_code=503, content=body)

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

"""Obserwowalność Dzik OS: request id, strukturalne logi JSON (stdout),
metryki w pamięci procesu i wspólny model błędów API.

Model błędu (każda odpowiedź 4xx/5xx z API):

    {"detail": "<bezpieczny komunikat po polsku>",
     "code": "<STABILNY_KOD>",            # np. NOT_FOUND, VALIDATION_ERROR
     "request_id": "<id żądania>",
     "errors": [{"field", "type", "msg"}]}  # tylko 422 (walidacja)

Klucz ``detail`` pozostaje głównym komunikatem (frontend i testy na nim
polegają); ``code``/``request_id`` są rozszerzeniem, nie zamianą.

Zasady redakcji (Konstytucja Human OS / RODO) — logi i metryki NIGDY nie
zawierają:
- danych zdrowotnych, treści wiadomości, zawartości dokumentów/zdjęć,
- adresów e-mail (użytkownik wyłącznie po id ``HOS-USR-...``),
- tokenów, haseł, ciasteczek, nagłówka Authorization,
- surowych ścieżek z identyfikatorami (logowany jest szablon trasy,
  np. ``/api/clients/{client_id}/measurements``),
- komunikatów wyjątków nie-HTTP (komunikaty ORM/sterowników potrafią
  zawierać wartości parametrów SQL) — logujemy typ wyjątku i ramki stosu
  ``plik:linia:funkcja``, nigdy ``str(exc)``.

Szczegóły i progi alertowe: docs/OBSERVABILITY.md.
"""

from __future__ import annotations

import json
import re
import threading
import time
import traceback
import uuid
from collections import Counter, deque
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

# ---------------------------------------------------------------------------
# Request id (contextvar — dostępny w handlerach błędów i logach w obrębie
# tego samego żądania; każde żądanie ustawia świeżą wartość na starcie).
# ---------------------------------------------------------------------------

_request_id: ContextVar[str | None] = ContextVar("dzik_request_id", default=None)

REQUEST_ID_HEADER = "X-Request-Id"


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def current_request_id() -> str | None:
    return _request_id.get()


# ---------------------------------------------------------------------------
# Strukturalne logi JSON na stdout.
# ---------------------------------------------------------------------------


def log_json(event: str, *, level: str = "info", **fields: Any) -> None:
    """Jedna linia JSON na zdarzenie. Wołający odpowiada za to, by fields
    nie zawierały danych osobowych/zdrowotnych ani sekretów (patrz moduł)."""
    record: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "level": level,
        "event": event,
        "request_id": current_request_id(),
    }
    record.update(fields)
    print(
        json.dumps({k: v for k, v in record.items() if v is not None}, ensure_ascii=False),
        flush=True,
    )


def exception_fields(exc: BaseException) -> dict[str, Any]:
    """Bezpieczny opis wyjątku do logu: typ + ramki stosu (plik:linia:funkcja).
    ŚWIADOMIE bez str(exc) — komunikaty (np. sqlalchemy z parametrami SQL)
    mogą zawierać dane zdrowotne lub osobowe."""
    frames = [
        f"{frame.filename.rsplit('/', 1)[-1]}:{frame.lineno}:{frame.name}"
        for frame in traceback.extract_tb(exc.__traceback__)[-12:]
    ]
    return {"error_type": type(exc).__name__, "frames": frames}


# Segmenty ścieżki wyglądające na identyfikatory (HOS-XXX-..., hex, liczby,
# długie tokeny) — maskowane, gdy szablon trasy nie jest dostępny (np. 404
# poza routerem). Normalne trasy logują szablon FastAPI z {parametrami}.
_ID_SEGMENT = re.compile(
    r"^(?:HOS-[A-Z]{2,8}-[0-9A-Za-z]+|[0-9a-fA-F-]{8,}|\d+|[A-Za-z0-9_-]{16,})$"
)


def mask_path(path: str) -> str:
    parts = path.split("/")
    return "/".join("{id}" if _ID_SEGMENT.match(p) else p for p in parts)


def route_template(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    return template if isinstance(template, str) else mask_path(request.url.path)


# ---------------------------------------------------------------------------
# Metryki w pamięci procesu (bez sekretów; ekspozycja: GET /api/metrics,
# tylko ADMIN). Przy wdrożeniu wieloprocesowym metryki są per proces.
# ---------------------------------------------------------------------------


class Metrics:
    _LATENCY_WINDOW = 1000  # ostatnie N żądań API do percentyli

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_status: Counter[int] = Counter()
        self._latencies_ms: deque[float] = deque(maxlen=self._LATENCY_WINDOW)
        self._counters: Counter[str] = Counter()
        self.started_at = datetime.now(UTC).isoformat(timespec="seconds")

    def observe_request(self, status: int, duration_ms: float) -> None:
        with self._lock:
            self._by_status[status] += 1
            self._latencies_ms.append(duration_ms)

    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    @staticmethod
    def _percentile(values: list[float], pct: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered)) - 1))
        return round(ordered[index], 1)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            by_status = dict(self._by_status)
            latencies = list(self._latencies_ms)
            counters = dict(self._counters)
        by_class: Counter[str] = Counter()
        for status, count in by_status.items():
            by_class[f"{status // 100}xx"] += count
        return {
            "started_at": self.started_at,
            "requests": {
                "total": sum(by_status.values()),
                "by_class": dict(by_class),
                "by_status": {str(k): v for k, v in sorted(by_status.items())},
            },
            "latency_ms": {
                "window": len(latencies),
                "p50": self._percentile(latencies, 50),
                "p95": self._percentile(latencies, 95),
                "p99": self._percentile(latencies, 99),
            },
            "counters": {
                # Zawsze obecne kluczowe liczniki (0 zamiast braku klucza).
                "reminder_loop_errors": counters.get("reminder_loop_errors", 0),
                "push_send_failures": counters.get("push_send_failures", 0),
                "frontend_error_reports": counters.get("frontend_error_reports", 0),
                "frontend_error_reports_dropped": counters.get(
                    "frontend_error_reports_dropped", 0
                ),
                "unhandled_exceptions": counters.get("unhandled_exceptions", 0),
                "access_denied": counters.get("access_denied", 0),
                "audit_log_failures": counters.get("audit_log_failures", 0),
            },
        }

    def reset(self) -> None:
        """Do testów — metryki produkcyjne żyją tak długo jak proces."""
        with self._lock:
            self._by_status.clear()
            self._latencies_ms.clear()
            self._counters.clear()


metrics = Metrics()


# ---------------------------------------------------------------------------
# Wspólny model błędów.
# ---------------------------------------------------------------------------

ERROR_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}

INTERNAL_ERROR_MESSAGE = (
    "Wystąpił błąd po naszej stronie. Spróbuj ponownie za chwilę — "
    "jeśli problem wraca, przekaż trenerowi identyfikator żądania."
)
VALIDATION_ERROR_MESSAGE = "Nieprawidłowe dane w żądaniu. Popraw pola i spróbuj ponownie."


def error_code_for(status: int) -> str:
    return ERROR_CODES.get(status, "HTTP_ERROR")


def error_body(
    status: int,
    detail: str,
    *,
    code: str | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "detail": detail,
        "code": code or error_code_for(status),
        "request_id": current_request_id(),
    }
    if errors is not None:
        body["errors"] = errors
    return body


def error_response(
    status: int,
    detail: str,
    *,
    code: str | None = None,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=error_body(status, detail, code=code, errors=errors),
        headers=headers,
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Wszystkie HTTPException w jednym kształcie. Detail pozostaje bez zmian
    (routery podają już bezpieczne polskie komunikaty; sentinele w rodzaju
    PASSWORD_CHANGE_REQUIRED muszą przejść nietknięte — frontend na nich
    polega)."""
    detail = exc.detail if isinstance(exc.detail, str) else "Błąd żądania"
    return error_response(
        exc.status_code, detail, headers=getattr(exc, "headers", None)
    )


def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 z listą pól. ŚWIADOMIE bez pydanticowych 'input'/'ctx'/'url' —
    wartość wejściowa może być daną zdrowotną i nie wraca w odpowiedzi
    ani nie trafia do logów."""
    errors = [
        {
            "field": ".".join(
                str(part) for part in err.get("loc", ()) if part not in ("body",)
            ),
            "type": str(err.get("type", "")),
            "msg": str(err.get("msg", "")),
        }
        for err in exc.errors()[:20]
    ]
    log_json(
        "validation_error",
        level="warning",
        method=request.method,
        path=route_template(request),
        fields=[e["field"] for e in errors],
    )
    return error_response(
        422, VALIDATION_ERROR_MESSAGE, code="VALIDATION_ERROR", errors=errors
    )


class ErrorEnvelopeMiddleware(BaseHTTPMiddleware):
    """Najgłębsze ogniwo (dodane jako pierwsze): każdy nieobsłużony wyjątek
    zamienia na odpowiedź 500 we wspólnym modelu błędów — bez stack trace,
    SQL ani wewnętrznych komunikatów dla klienta. Pełny kontekst techniczny
    (typ + ramki stosu, bez wartości) idzie do logu strukturalnego."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001 - celowo: granica 500 dla API
            metrics.inc("unhandled_exceptions")
            log_json(
                "unhandled_exception",
                level="error",
                method=request.method,
                path=route_template(request),
                **exception_fields(exc),
            )
            return error_response(500, INTERNAL_ERROR_MESSAGE)


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Najbardziej zewnętrzne ogniwo (dodane jako ostatnie): nadaje request id
    (nagłówek X-Request-Id na KAŻDEJ odpowiedzi), mierzy czas i loguje
    żądania /api w formacie JSON (metoda + szablon ścieżki + status + czas +
    id użytkownika — nigdy e-mail, token ani treść żądania/odpowiedzi)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Celowo ignorujemy X-Request-Id od klienta (żaden nagłówek wejściowy
        # nie trafia do logów bez walidacji) — id jest zawsze serwerowe.
        request_id = new_request_id()
        _request_id.set(request_id)
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        path = request.url.path
        if path == "/api" or path.startswith("/api/"):
            metrics.observe_request(response.status_code, duration_ms)
            state = request.scope.get("state") or {}
            log_json(
                "request",
                level="error" if response.status_code >= 500 else "info",
                method=request.method,
                path=route_template(request),
                status=response.status_code,
                duration_ms=round(duration_ms, 1),
                user_id=state.get("user_id"),
            )
        return response

"""Telemetria i monitoring: metryki (ADMIN), raporty błędów JS frontendu.

Zasady (Konstytucja Human OS): monitoring NIE zbiera treści raportów,
zdjęć, wiadomości, danych zdrowotnych, e-maili ani sekretów. Raport błędu
frontendu jest redukowany do typu wyjątku, nazwy komponentu i stosu
zredagowanego do nazw WŁASNYCH plików (frontend/dist/assets) z numerami
linii — każda inna treść jest odrzucana po stronie serwera.
"""

from __future__ import annotations

import re
import threading
import time

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..observability import error_response, log_json, metrics
from ..security import require_role

router = APIRouter(prefix="/api", tags=["telemetry"])


@router.get("/metrics")
def get_metrics(admin=Depends(require_role("ADMIN"))):
    """Liczniki 4xx/5xx, percentyle czasu odpowiedzi, błędy pętli przypomnień
    i raporty błędów frontendu — bez sekretów i bez danych użytkowników.
    Progi alertowe: docs/OBSERVABILITY.md."""
    return metrics.snapshot()


# --- Raporty błędów JS frontendu -------------------------------------------


class FrontendErrorIn(BaseModel):
    type: str = Field(min_length=1, max_length=120)
    component: str | None = Field(default=None, max_length=160)
    stack: str | None = Field(default=None, max_length=8000)


# Ramka stosu redukowana do "plik.js:linia:kolumna" — wyłącznie pliki
# skryptowe (własne bundle Vite); ścieżki, query stringi, komunikaty
# i wszystko inne jest odrzucane.
_FRAME = re.compile(r"([\w.\-]+\.(?:m?js|ts|tsx))(?::(\d+))(?::(\d+))?")
# Typ błędu: identyfikator w stylu klasy JS (TypeError, ApiError...).
_ERROR_TYPE = re.compile(r"^[A-Za-z][A-Za-z0-9_$]{0,79}")
# Komponent: pojedyncza etykieta naszego UI (nazwa komponentu / "route:/sciezka").
_COMPONENT = re.compile(r"^[A-Za-z0-9_/:.\-]{1,80}")


def redact_stack(stack: str | None, max_frames: int = 20) -> list[str]:
    if not stack:
        return []
    frames: list[str] = []
    for line in stack.splitlines():
        match = _FRAME.search(line)
        if not match:
            continue
        filename, lineno, col = match.group(1), match.group(2), match.group(3)
        frames.append(f"{filename}:{lineno}" + (f":{col}" if col else ""))
        if len(frames) >= max_frames:
            break
    return frames


def _safe_label(value: str | None, pattern: re.Pattern[str]) -> str | None:
    """Etykieta po twardej redakcji: wyłącznie pierwszy fragment pasujący do
    dozwolonego wzorca (identyfikator klasy błędu / etykieta komponentu).
    Wszystko poza wzorcem — komunikaty, wartości, tokeny — jest odrzucane."""
    if not value:
        return None
    match = pattern.match(value.strip())
    return match.group(0) if match else None


class _ReportRateLimiter:
    """Okno przesuwne w pamięci procesu: per adres + globalnie. Endpoint jest
    dostępny bez logowania (błędy potrafią wystąpić przed zalogowaniem),
    więc limit musi być twardy."""

    PER_IP_PER_MINUTE = 10
    GLOBAL_PER_MINUTE = 120

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_ip: dict[str, list[float]] = {}
        self._all: list[float] = []

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            self._all = [t for t in self._all if now - t < 60]
            bucket = [t for t in self._by_ip.get(ip, []) if now - t < 60]
            if len(self._all) >= self.GLOBAL_PER_MINUTE or len(bucket) >= self.PER_IP_PER_MINUTE:
                self._by_ip[ip] = bucket
                return False
            bucket.append(now)
            self._by_ip[ip] = bucket
            self._all.append(now)
            return True


report_rate_limiter = _ReportRateLimiter()


@router.post("/telemetry/frontend-errors", status_code=202)
def report_frontend_error(body: FrontendErrorIn, request: Request):
    """Przyjmuje raport błędu JS. Trwałość: licznik w metrykach + jedna
    linia logu strukturalnego (typ, komponent, zredagowane ramki) — treść
    raportu nie jest nigdzie przechowywana w całości."""
    ip = request.client.host if request.client else "unknown"
    if not report_rate_limiter.allow(ip):
        metrics.inc("frontend_error_reports_dropped")
        return error_response(
            429, "Zbyt wiele raportów błędów. Spróbuj ponownie później.",
            code="RATE_LIMITED",
        )
    metrics.inc("frontend_error_reports")
    log_json(
        "frontend_error",
        level="warning",
        error_type=_safe_label(body.type, _ERROR_TYPE),
        component=_safe_label(body.component, _COMPONENT),
        frames=redact_stack(body.stack),
    )
    return {"ok": True}

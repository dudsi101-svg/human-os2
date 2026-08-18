"""Kolejka JEDNOSLOTOWA zadań przepisywania tekstu ze zdjęcia.

Dlaczego kolejka, a nie robota w żądaniu HTTP: produkcja to Fly.io
shared-cpu-1x z 512 MB RAM. Dwa równoległe rozpoznania potrafią wyczerpać
pamięć maszyny i położyć całą aplikację (logowanie, wiadomości,
harmonogram). Dlatego:

* **jeden slot** — dokładnie jeden wątek roboczy i dodatkowo semafor o
  pojemności 1, więc nawet po dołożeniu drugiego wątku nic nie policzy
  dwóch obrazów naraz;
* **ograniczona poczekalnia** (``DZIK_OCR_QUEUE_MAX``) — po przepełnieniu
  zlecenie dostaje czytelne 429, zamiast rosnąć w nieskończoność;
* **twardy limit czasu** rozpoznania (``ocr.LocalOcrEngine``) — zadanie
  kończy się statusem FAILED, a nie zajechaną maszyną.

Przy większym ruchu maszynę trzeba podbić do 1 GB RAM — inaczej kolejka
zamieni się w kolejkę do sklepu (patrz docs/OCR.md §limity maszyny).

Zdarzenia postępu idą na ISTNIEJĄCĄ magistralę (``realtime.bus``) —
drugiego kanału nie budujemy. Front może też zwyczajnie odpytać
``GET /api/ocr/tasks/{id}``.

Prywatność: do logów i metryk trafiają WYŁĄCZNIE liczniki, czasy i kody
błędów. Ani rozpoznany tekst, ani zawartość zdjęcia nie są logowane.
"""

from __future__ import annotations

import json
import queue
import threading
import time

from .config import settings
from .db import db_session
from .models import OcrTask, StoredFile, now_iso
from .observability import exception_fields, log_json, metrics
from .realtime import bus

# Semafor jest tu jawną deklaracją reguły „jedno rozpoznanie naraz” —
# obok pojedynczego wątku roboczego, nie zamiast niego.
_slot = threading.Semaphore(1)


class OcrQueue:
    """Kolejka zadań + jeden wątek roboczy (startowany leniwie)."""

    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._idle = threading.Condition(self._lock)
        self._pending = 0   # w kolejce + w trakcie
        self._active = 0    # aktualnie liczone (musi być <= 1)
        self._max_active = 0
        self._thread: threading.Thread | None = None

    # --- API zleceniodawcy -------------------------------------------------

    def submit(self, task_id: str) -> bool:
        """Dokłada zadanie do kolejki. ``False`` = poczekalnia pełna."""
        with self._lock:
            if self._pending >= max(1, settings.ocr_queue_max):
                return False
            self._pending += 1
        self._ensure_worker()
        self._queue.put(task_id)
        return True

    def depth(self) -> int:
        """Ile zadań czeka lub jest w trakcie (do pokazania w UI)."""
        with self._lock:
            return self._pending

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """Czeka, aż kolejka się opróżni (używane przez testy i wyłączanie)."""
        with self._idle:
            return self._idle.wait_for(lambda: self._pending == 0, timeout=timeout)

    @property
    def max_observed_concurrency(self) -> int:
        """Największa zaobserwowana liczba równoczesnych rozpoznań.
        Kontrakt jednoslotowości: ta wartość nigdy nie przekracza 1."""
        with self._lock:
            return self._max_active

    # --- wątek roboczy -----------------------------------------------------

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._work, name="dzik-ocr-worker", daemon=True
            )
            self._thread.start()

    def _work(self) -> None:
        while True:
            task_id = self._queue.get()
            try:
                with _slot:
                    with self._lock:
                        self._active += 1
                        self._max_active = max(self._max_active, self._active)
                    try:
                        run_task(task_id)
                    finally:
                        with self._lock:
                            self._active -= 1
            # Wątek roboczy nie ma prawa umrzeć — jedno felerne zadanie nie
            # może wyłączyć funkcji do restartu maszyny.
            except Exception as exc:  # noqa: BLE001 - granica wątku
                log_json("ocr_worker_error", level="error", **exception_fields(exc))
            finally:
                self._queue.task_done()
                with self._idle:
                    self._pending -= 1
                    self._idle.notify_all()


tasks = OcrQueue()


# ---------------------------------------------------------------------------
# Wykonanie jednego zadania.
# ---------------------------------------------------------------------------


def resolve_mode(owner_user_id: str) -> tuple[str, str]:
    """Wybór trybu — BEZ przełącznika w kodzie wywołującym.

    Tryb rozszerzony włącza się sam, gdy dostawca modelu jest skonfigurowany
    ORAZ podmiot danych ma aktywną zgodę `funkcje_ai`. W przeciwnym razie
    działa silnik lokalny, a powód jest jawny (nie jest to błąd)."""
    from . import ocr_ai
    from .authz import ai_features_consent_active

    with db_session() as db:
        if not ai_features_consent_active(db, owner_user_id):
            return "LOCAL", ocr_ai.NO_CONSENT_REASON
        ready, reason = ocr_ai.provider_ready(db, owner_user_id)
    return ("EXTENDED", "") if ready else ("LOCAL", reason)


def _publish(owner_id: str, created_by: str, payload: dict) -> None:
    """Zdarzenie postępu na istniejącej magistrali — bez treści (sam status).
    Odbiorcami są wyłącznie właściciel danych i zlecający."""
    event = {"type": "ocr.task", **payload}
    for user_id in {owner_id, created_by}:
        bus.publish(user_id, event)


def run_task(task_id: str) -> None:
    """Pełny przebieg jednego zadania: RUNNING → rozpoznanie → DONE/FAILED.

    Nie podnosi wyjątków „na zewnątrz”: każdy problem kończy się statusem
    FAILED z kodem i komunikatem po polsku."""
    from . import ocr, ocr_ai
    from .storage import storage

    started = time.monotonic()
    with db_session() as db:
        task = db.get(OcrTask, task_id)
        if task is None or task.status != "PENDING":
            return
        task.status = "RUNNING"
        task.started_at = now_iso()
        owner_id, created_by = task.owner_user_id, task.created_by
        purpose, file_id = task.purpose, task.file_id
        stored = db.get(StoredFile, file_id)
        if stored is None or stored.deleted_at is not None:
            data, content_type = None, ""
        else:
            content_type = stored.content_type
            try:
                data = storage.read(stored)
            except Exception:  # noqa: BLE001 - brak pliku/klucza to STAN zadania
                data = None
    _publish(owner_id, created_by, {"task_id": task_id, "status": "RUNNING"})
    metrics.inc("ocr_tasks_started")

    if data is None:
        _finish(task_id, ok=False, error_code=ocr.ERR_BAD_IMAGE,
                error="Pliku źródłowego już nie ma — wgraj zdjęcie ponownie.",
                engine="LOCAL", started=started)
        return
    if len(data) > settings.ocr_max_input_mb * 1024 * 1024:
        _finish(task_id, ok=False, error_code=ocr.ERR_TOO_LARGE,
                error=f"Zdjęcie jest większe niż {settings.ocr_max_input_mb} MB — "
                      "zrób je w mniejszej rozdzielczości.",
                engine="LOCAL", started=started)
        return

    mode, mode_reason = resolve_mode(owner_id)
    text = ""
    proposal: dict | None = None
    engine_used = "LOCAL"

    if mode == "EXTENDED":
        outcome = ocr_ai.request_vision_ocr(
            user_id=owner_id, image=data, media_type=content_type, purpose=purpose
        )
        if outcome.ok:
            engine_used = "EXTENDED"
            text = outcome.text
            proposal = outcome.fields
        else:
            # Cicho i JAWNIE: schodzimy na silnik lokalny z powodem.
            mode_reason = outcome.reason

    if engine_used == "LOCAL":
        result = ocr.engine.recognize(data, content_type=content_type)
        if not result.ok:
            if result.error_code == ocr.ERR_ENGINE_UNAVAILABLE:
                metrics.inc("ocr_engine_unavailable")
            _finish(task_id, ok=False, error_code=result.error_code, error=result.reason,
                    engine="LOCAL", started=started, mode_reason=mode_reason)
            return
        text = result.text

    if proposal is None and purpose == ocr_ai.PURPOSE_PRODUCT:
        # Tryb lokalny (albo model, który pól nie podał): czytamy tabelę
        # wartości odżywczych deterministycznie. Czego nie widać — zostaje puste.
        proposal = ocr.parse_nutrition_label(text)

    _finish(task_id, ok=True, engine=engine_used, started=started,
            text=text, proposal=proposal, mode_reason=mode_reason)


def _finish(
    task_id: str,
    *,
    ok: bool,
    engine: str,
    started: float,
    text: str = "",
    proposal: dict | None = None,
    error_code: str = "",
    error: str = "",
    mode_reason: str = "",
) -> None:
    """Zapis wyniku + zdarzenie + audyt. Do audytu, logów i metryk idzie
    WYŁĄCZNIE fakt rozpoznania (silnik, liczba znaków, czas) — nigdy treść."""
    from .hos_bridge import record_event

    duration_ms = int((time.monotonic() - started) * 1000)
    with db_session() as db:
        task = db.get(OcrTask, task_id)
        if task is None:
            return
        task.status = "DONE" if ok else "FAILED"
        task.engine = engine
        task.mode_reason = mode_reason or None
        task.text = text or None
        task.proposal_json = json.dumps(proposal, ensure_ascii=False) if proposal else None
        task.error_code = error_code or None
        task.error = error or None
        task.chars = len(text) if ok else None
        task.duration_ms = duration_ms
        task.finished_at = now_iso()
        owner_id, created_by, purpose = task.owner_user_id, task.created_by, task.purpose
        try:
            record_event(
                db,
                action="OCR_RECOGNIZED" if ok else "OCR_FAILED",
                actor_id=created_by,
                subject_ids=[owner_id],
                payload={
                    "task_id": task_id, "purpose": purpose, "engine": engine,
                    "chars": task.chars, "duration_ms": duration_ms,
                    "error_code": error_code or None,
                },
                summary=(
                    f"Przepisano tekst ze zdjęcia (silnik {engine})"
                    if ok
                    else f"Nie udało się przepisać tekstu ze zdjęcia ({error_code})"
                ),
            )
        # Awaria łańcucha audytu nie może zostawić zadania na zawsze w
        # stanie RUNNING — status zapisujemy mimo wszystko, a problem
        # widać w liczniku audit_log_failures (jak w main.py).
        except Exception as exc:  # noqa: BLE001 - diagnostyka audytu
            metrics.inc("audit_log_failures")
            log_json("audit_append_failed", level="error", action="OCR", **exception_fields(exc))
    metrics.inc("ocr_tasks_done" if ok else "ocr_tasks_failed")
    log_json(
        "ocr_task_finished",
        status="DONE" if ok else "FAILED",
        engine=engine,
        chars=len(text) if ok else 0,
        duration_ms=duration_ms,
        error_code=error_code or None,
    )
    _publish(owner_id, created_by, {
        "task_id": task_id, "status": "DONE" if ok else "FAILED", "engine": engine,
    })

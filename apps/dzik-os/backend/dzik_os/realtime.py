"""Kanał czasu rzeczywistego wiadomości — magistrala zdarzeń w pamięci procesu.

Transport to Server-Sent Events (GET /api/threads/events w routers/messages.py):
zwykłe HTTP, więc działa przez ten sam łańcuch middleware co reszta API
(nagłówki bezpieczeństwa P5, X-Request-Id/model błędów P9, Cache-Control
no-store) i uwierzytelnia się nagłówkiem Bearer przez fetch — token NIGDY
nie trafia do query stringa. Uzasadnienie wyboru SSE zamiast WebSocketu:
docs/WIADOMOSCI.md.

Zasady (Konstytucja Human OS / RODO):
- zdarzenia zawierają treść wiadomości, więc płyną WYŁĄCZNIE do
  uwierzytelnionej strony wątku — bramka require_thread_party jest
  sprawdzana ponownie PRZY KAŻDYM doręczeniu (routers/messages.py),
  nie tylko przy publikacji;
- nic z tej magistrali nie jest logowane ani zliczane treścią — logi
  techniczne widzą co najwyżej liczniki (metrics), nigdy payload;
- magistrala żyje w pamięci JEDNEGO procesu (deployment: jedna maszyna,
  fly.toml min_machines_running=1). Przy wdrożeniu wieloprocesowym
  wymaga wspólnego brokera — ograniczenie opisane w docs/WIADOMOSCI.md.
"""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from typing import Any

# Pojemność kolejki jednego subskrybenta. Po przepełnieniu (klient nie
# nadąża) kolejka jest czyszczona i zostaje pojedynczy znacznik resync —
# klient ma wtedy pobrać stan przez zwykłe GET, zamiast dostawać dziury.
QUEUE_MAXSIZE = 200

RESYNC_EVENT: dict[str, Any] = {"type": "resync"}


@dataclass
class RealtimeSubscription:
    """Jedna otwarta subskrypcja (jedno urządzenie użytkownika)."""

    user_id: str
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue = field(
        default_factory=lambda: asyncio.Queue(maxsize=QUEUE_MAXSIZE)
    )


class RealtimeBus:
    """Pub/sub per użytkownik, bezpieczny między wątkami.

    ``publish`` wolno wołać z dowolnego wątku (endpointy synchroniczne
    FastAPI działają w puli wątków) — zdarzenie jest przekazywane do pętli
    asyncio subskrybenta przez ``call_soon_threadsafe``.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: dict[str, list[RealtimeSubscription]] = {}

    def subscribe(self, user_id: str) -> RealtimeSubscription:
        """Rejestracja subskrypcji — wołać z aktywnej pętli asyncio."""
        sub = RealtimeSubscription(user_id=user_id, loop=asyncio.get_running_loop())
        with self._lock:
            self._subs.setdefault(user_id, []).append(sub)
        return sub

    def unsubscribe(self, sub: RealtimeSubscription) -> None:
        with self._lock:
            subs = self._subs.get(sub.user_id, [])
            if sub in subs:
                subs.remove(sub)
            if not subs:
                self._subs.pop(sub.user_id, None)

    def has_subscriber(self, user_id: str) -> bool:
        with self._lock:
            return bool(self._subs.get(user_id))

    def publish(self, user_id: str, event: dict[str, Any]) -> None:
        """Doręczenie zdarzenia do wszystkich subskrypcji użytkownika.
        Brak subskrybentów = brak efektu (odbiorca offline dostaje
        neutralny push i zsynchronizuje się przy wejściu w wątek)."""
        with self._lock:
            subs = list(self._subs.get(user_id, ()))
        for sub in subs:
            sub.loop.call_soon_threadsafe(self._offer, sub.queue, event)

    @staticmethod
    def _offer(queue: asyncio.Queue, event: dict[str, Any]) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # Klient nie nadąża: zamiast gubić pojedyncze zdarzenia po
            # cichu, wyczyść kolejkę i każ mu się zsynchronizować.
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:  # pragma: no cover - wyścig
                    break
            queue.put_nowait(dict(RESYNC_EVENT))


bus = RealtimeBus()


def sse_format(event_type: str, data: dict[str, Any], event_id: str | None = None) -> str:
    """Jedno zdarzenie w formacie SSE (text/event-stream)."""
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    payload = json.dumps(data, ensure_ascii=False)
    lines.extend(f"data: {chunk}" for chunk in payload.split("\n"))
    return "\n".join(lines) + "\n\n"

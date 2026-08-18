"""Wiadomości: wątki, historia z paginacją, statusy doręczenia i kanał
czasu rzeczywistego (SSE).

Model statusów (docs/WIADOMOSCI.md): wysłana (wiersz istnieje, created_at)
→ dostarczona (delivered_at — urządzenie odbiorcy odebrało ją strumieniem
SSE albo pobierając wątek) → przeczytana (read_at — odbiorca miał otwarty
wątek). Kolejność jest stabilna: (created_at, id).

Bezpieczeństwo: każda ścieżka (w tym doręczenie KAŻDEGO zdarzenia SSE)
przechodzi przez bramkę strony wątku — require_thread_party (strona wątku,
AKTYWNA relacja i nieocofnięta zgoda dla trenera). Obcy → 404. Treść
wiadomości nigdy nie trafia do logów, metryk ani push (push = neutralne
„Nowa wiadomość").
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import push_service
from ..authz import (
    DOMAIN_MESSAGES,
    coach_can_access_client,
    require_attachable_file,
    require_thread_party,
)
from ..config import settings
from ..db import db_session, get_db
from ..models import Message, MessageThread, User, new_id, now_iso
from ..realtime import bus, sse_format
from ..schemas import MessageIn
from ..security import (
    active_roles,
    current_user,
    request_token,
    session_is_active,
)

router = APIRouter(prefix="/api", tags=["messages"])

# Paginacja historii wątku (kursor po (created_at, id) — patrz messages_page).
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def _message_payload(m: Message) -> dict:
    return {
        "id": m.id,
        "author_id": m.author_id,
        "body": m.body,
        "file_id": m.file_id,
        "created_at": m.created_at,
        "delivered_at": m.delivered_at,
        "read_at": m.read_at,
        "client_msg_id": m.client_msg_id,
    }


def _other_party_id(thread: MessageThread, user_id: str) -> str:
    return thread.coach_id if user_id == thread.client_id else thread.client_id


def _party_may_view(db: Session, thread: MessageThread, user_id: str) -> bool:
    """Ta sama reguła co require_thread_party, w formie predykatu: klient
    z wątku zawsze; trener wyłącznie przy aktywnej relacji i nieocofniętej
    zgodzie kategorii „komunikacja". Używana przy publikacji i doręczaniu
    zdarzeń realtime — treść nie może popłynąć do strony bez dostępu."""
    if user_id == thread.client_id:
        return True
    if user_id == thread.coach_id:
        return coach_can_access_client(
            db, thread.coach_id, thread.client_id, domain=DOMAIN_MESSAGES
        )
    return False


def _mark_incoming_read(db: Session, thread: MessageThread, reader_id: str) -> list[Message]:
    """Oznacza wszystkie nieprzeczytane cudze wiadomości wątku jako
    przeczytane (read implikuje delivered). Zwraca zmienione wiersze."""
    rows = (
        db.query(Message)
        .filter(
            Message.thread_id == thread.id,
            Message.author_id != reader_id,
            Message.read_at.is_(None),
        )
        .all()
    )
    stamp = now_iso()
    for m in rows:
        m.read_at = stamp
        if m.delivered_at is None:
            m.delivered_at = stamp
    return rows


def _publish_read_receipts(thread: MessageThread, reader_id: str, rows: list[Message]) -> None:
    if not rows:
        return
    bus.publish(
        _other_party_id(thread, reader_id),
        {
            "type": "message.read",
            "thread_id": thread.id,
            "message_ids": [m.id for m in rows],
            "read_at": rows[0].read_at,
        },
    )


@router.get("/threads")
def my_threads(user: User = Depends(current_user), db: Session = Depends(get_db)):
    roles = active_roles(db, user.id)
    q = db.query(MessageThread)
    if "COACH" in roles:
        # Lista wątków trenera podlega TEJ SAMEJ bramce co otwarcie wątku
        # (require_thread_party): wyłącznie aktywna relacja i nieocofnięta
        # zgoda — inaczej podgląd ostatniej wiadomości wyciekałby po
        # zakończeniu współpracy.
        threads = [
            t
            for t in q.filter(MessageThread.coach_id == user.id).all()
            if coach_can_access_client(db, user.id, t.client_id, domain=DOMAIN_MESSAGES)
        ]
    else:
        threads = q.filter(MessageThread.client_id == user.id).all()
    out = []
    for t in threads:
        last = (
            db.query(Message)
            .filter(Message.thread_id == t.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .first()
        )
        unread = (
            db.query(Message)
            .filter(
                Message.thread_id == t.id,
                Message.author_id != user.id,
                Message.read_at.is_(None),
            )
            .count()
        )
        other_id = t.client_id if user.id == t.coach_id else t.coach_id
        other = db.get(User, other_id)
        out.append(
            {
                "id": t.id,
                "with_user": {"id": other_id,
                              "display_name": other.display_name if other else "?"},
                "last_message": {
                    "body": last.body[:200], "author_id": last.author_id,
                    "created_at": last.created_at,
                } if last else None,
                "unread": unread,
            }
        )
    return {"threads": out}


@router.get("/threads/{thread_id}/messages")
def thread_messages(
    thread_id: str,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    before: str | None = Query(default=None, max_length=40),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Historia wątku: najnowsze `limit` wiadomości (rosnąco po
    (created_at, id)). Starsze strony: `before=<id najstarszej znanej
    wiadomości>`. Otwarcie wątku (żądanie bez `before`) oznacza cudze
    wiadomości jako przeczytane i doręczone."""
    thread = require_thread_party(db, user, thread_id)
    q = db.query(Message).filter(Message.thread_id == thread.id)
    if before is not None:
        anchor = db.get(Message, before)
        if anchor is None or anchor.thread_id != thread.id:
            raise HTTPException(status_code=404, detail="Nie znaleziono")
        q = q.filter(
            (Message.created_at < anchor.created_at)
            | ((Message.created_at == anchor.created_at) & (Message.id < anchor.id))
        )
    rows = (
        q.order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    rows = list(reversed(rows[:limit]))
    if before is None:
        # Otwarcie wątku = przeczytanie wszystkiego, co przyszło (nie tylko
        # bieżącej strony); nadawca dostaje potwierdzenie kanałem realtime.
        changed = _mark_incoming_read(db, thread, user.id)
        db.commit()
        _publish_read_receipts(thread, user.id, changed)
    return {
        "messages": [_message_payload(m) for m in rows],
        "has_more": has_more,
    }


@router.post("/threads/{thread_id}/read")
def mark_thread_read(
    thread_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Jawne oznaczenie cudzych wiadomości wątku jako przeczytane — używane
    przez otwarty ekran rozmowy, gdy nowa wiadomość przychodzi strumieniem
    (bez ponownego GET). Ta sama bramka strony wątku, obcy → 404."""
    thread = require_thread_party(db, user, thread_id)
    changed = _mark_incoming_read(db, thread, user.id)
    db.commit()
    _publish_read_receipts(thread, user.id, changed)
    return {"marked_read": len(changed)}


@router.post("/threads/{thread_id}/messages", status_code=201)
def send_message(
    thread_id: str,
    body: MessageIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    thread = require_thread_party(db, user, thread_id)
    if body.client_msg_id is not None:
        # Deduplikacja ponowień (utrata sieci po wysłaniu, przed odebraniem
        # odpowiedzi): to samo client_msg_id od tego samego autora w tym
        # samym wątku zwraca ISTNIEJĄCĄ wiadomość zamiast tworzyć duplikat.
        existing = (
            db.query(Message)
            .filter(
                Message.thread_id == thread.id,
                Message.author_id == user.id,
                Message.client_msg_id == body.client_msg_id,
            )
            .one_or_none()
        )
        if existing is not None:
            return {**_message_payload(existing), "duplicate": True}
    if body.file_id is not None:
        # Załączyć można wyłącznie plik własny lub samodzielnie wgrany —
        # podpięcie cudzego file_id dawałoby drugiej stronie wątku dostęp
        # do nie swojego pliku.
        require_attachable_file(
            db, user, body.file_id, owner_id=user.id, allow_uploader=True
        )
    message = Message(
        id=new_id("MSG"),
        thread_id=thread.id,
        author_id=user.id,
        body=body.body,
        file_id=body.file_id,
        client_msg_id=body.client_msg_id,
    )
    db.add(message)
    # Push do drugiej strony wątku — bez treści wiadomości (tylko wezwanie).
    recipient_id = _other_party_id(thread, user.id)
    push_service.send_to_user(
        db, recipient_id, "Nowa wiadomość",
        f"{user.display_name} napisał(a) do Ciebie.", f"/wiadomosci/{thread.id}",
    )
    db.commit()
    # Realtime dopiero PO commicie (zdarzenie nie może wyprzedzić trwałego
    # zapisu). Odbiorca — o ile bramka wątku na to pozwala; autor — jego
    # pozostałe urządzenia (synchronizacja własnych kart/telefonu).
    event = {"type": "message.new", "thread_id": thread.id,
             "message": _message_payload(message)}
    if _party_may_view(db, thread, recipient_id):
        bus.publish(recipient_id, event)
    bus.publish(user.id, event)
    return {**_message_payload(message), "duplicate": False}


def _deliver_event(user_id: str, event: dict) -> dict | None:
    """Autoryzacja i doręczenie JEDNEGO zdarzenia strumienia: ponowna
    bramka strony wątku (stan relacji/zgód mógł się zmienić po publikacji),
    znacznik delivered_at dla świeżo doręczonej wiadomości i potwierdzenie
    doręczenia do nadawcy. Zwraca payload do wysłania albo None (odrzut —
    treść nie płynie do strony bez dostępu)."""
    thread_id = event.get("thread_id")
    if not thread_id:
        return None
    with db_session() as db:
        thread = db.get(MessageThread, thread_id)
        if thread is None or not _party_may_view(db, thread, user_id):
            return None
        if event.get("type") == "message.new":
            message_id = event["message"]["id"]
            row = db.get(Message, message_id)
            if row is None:
                return None
            if row.author_id != user_id and row.delivered_at is None:
                # Doręczono na żywo: znacznik + potwierdzenie dla nadawcy.
                row.delivered_at = now_iso()
                event = {**event, "message": _message_payload(row)}
                bus.publish(
                    row.author_id,
                    {
                        "type": "message.delivered",
                        "thread_id": thread.id,
                        "message_id": row.id,
                        "delivered_at": row.delivered_at,
                    },
                )
            else:
                event = {**event, "message": _message_payload(row)}
    event_type = event.pop("type")
    event_id = (
        event.get("message", {}).get("id")
        if event_type == "message.new"
        else None
    )
    return {"event": event_type, "data": event, "id": event_id}


@router.get("/threads/events")
async def thread_events(
    request: Request,
    user: User = Depends(current_user),
):
    """Kanał czasu rzeczywistego (SSE) dla wszystkich wątków użytkownika.

    Uwierzytelnienie: standardowy nagłówek Bearer (fetch po stronie
    frontendu — EventSource nie umie nagłówków, tokenu NIE przyjmujemy w
    query stringu). Ważność sesji jest sprawdzana także W TRAKCIE strumienia
    (przy każdym zdarzeniu i keepalive) — unieważniona/wygasła sesja dostaje
    zdarzenie `session_expired` i zamknięcie kanału. Zdarzenia: message.new,
    message.delivered, message.read, resync; keepalive co
    DZIK_SSE_KEEPALIVE_S sekund."""
    token = request_token(request)
    sub = bus.subscribe(user.id)

    def _session_ok() -> bool:
        with db_session() as db:
            return session_is_active(db, token)

    async def stream():
        try:
            # retry: wskazówka dla klienta; ready: potwierdzenie połączenia.
            yield "retry: 5000\n\n"
            yield sse_format("ready", {})
            while True:
                try:
                    event = await asyncio.wait_for(
                        sub.queue.get(), timeout=settings.sse_keepalive_s
                    )
                except TimeoutError:
                    if not _session_ok():
                        yield sse_format("session_expired", {})
                        return
                    yield ": keepalive\n\n"
                    continue
                if not _session_ok():
                    yield sse_format("session_expired", {})
                    return
                if event.get("type") == "resync":
                    # Kolejka była przepełniona — klient ma pobrać stan
                    # przez zwykłe GET zamiast polegać na strumieniu.
                    yield sse_format("resync", {})
                    continue
                delivered = _deliver_event(user.id, dict(event))
                if delivered is not None:
                    yield sse_format(
                        delivered["event"], delivered["data"], delivered["id"]
                    )
        finally:
            bus.unsubscribe(sub)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        # Wyłączenie buforowania na proxy (Fly/nginx-podobne) — SSE musi
        # płynąć natychmiast; Cache-Control: no-store nakłada middleware.
        headers={"X-Accel-Buffering": "no"},
    )

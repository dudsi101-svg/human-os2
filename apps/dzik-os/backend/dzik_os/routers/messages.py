from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import push_service
from ..authz import (
    DOMAIN_MESSAGES,
    coach_can_access_client,
    require_attachable_file,
    require_thread_party,
)
from ..db import get_db
from ..models import Message, MessageThread, User, new_id, now_iso
from ..schemas import MessageIn
from ..security import active_roles, current_user

router = APIRouter(prefix="/api", tags=["messages"])


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
            .order_by(Message.created_at.desc())
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
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    thread = require_thread_party(db, user, thread_id)
    rows = (
        db.query(Message)
        .filter(Message.thread_id == thread.id)
        .order_by(Message.created_at)
        .all()
    )
    # Oznacz cudze wiadomości jako przeczytane.
    for m in rows:
        if m.author_id != user.id and m.read_at is None:
            m.read_at = now_iso()
    db.commit()
    return {
        "messages": [
            {
                "id": m.id, "author_id": m.author_id, "body": m.body,
                "file_id": m.file_id, "created_at": m.created_at, "read_at": m.read_at,
            }
            for m in rows
        ]
    }


@router.post("/threads/{thread_id}/messages", status_code=201)
def send_message(
    thread_id: str,
    body: MessageIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    thread = require_thread_party(db, user, thread_id)
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
    )
    db.add(message)
    # Push do drugiej strony wątku — bez treści wiadomości (tylko wezwanie).
    recipient_id = thread.coach_id if user.id == thread.client_id else thread.client_id
    push_service.send_to_user(
        db, recipient_id, "Nowa wiadomość",
        f"{user.display_name} napisał(a) do Ciebie.", f"/wiadomosci/{thread.id}",
    )
    db.commit()
    return {"id": message.id, "created_at": message.created_at}

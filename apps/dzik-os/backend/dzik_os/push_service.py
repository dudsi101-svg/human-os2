"""Web Push (VAPID) — wysyłka powiadomień do subskrypcji użytkownika.

Zasady (Human OS / RODO):
- opt-in: subskrypcja powstaje wyłącznie po jawnej zgodzie w UI i można ją
  wyłączyć jednym przyciskiem;
- treść powiadomienia NIGDY nie zawiera danych zdrowotnych ani treści
  wiadomości — wyłącznie neutralne wezwanie do wejścia do aplikacji;
- liczba wysłanych powiadomień nie jest żadną metryką sukcesu.

Klucz prywatny VAPID jest generowany automatycznie przy pierwszym użyciu
i trwale zapisywany na wolumenie danych (poza repozytorium).
"""

from __future__ import annotations

import base64
import json
import threading
from pathlib import Path

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid
from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from .config import settings
from .models import PushSubscription

_vapid_lock = threading.Lock()
_vapid: Vapid | None = None


def _get_vapid() -> Vapid:
    global _vapid
    with _vapid_lock:
        if _vapid is None:
            path = Path(settings.vapid_key_path)
            if path.exists():
                _vapid = Vapid.from_file(str(path))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                v = Vapid()
                v.generate_keys()
                v.save_key(str(path))
                _vapid = v
        return _vapid


def public_key_b64url() -> str:
    """Klucz publiczny w formacie applicationServerKey przeglądarki."""
    raw = _get_vapid().public_key.public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint
    )
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _send_one(sub: PushSubscription, payload: str) -> bool:
    """Zwraca False, gdy subskrypcja wygasła i należy ją usunąć."""
    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=payload,
            vapid_private_key=str(Path(settings.vapid_key_path)),
            vapid_claims={"sub": settings.push_contact},
            timeout=5,
        )
        return True
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            return False
        print(f"[dzik-os] push nieudany ({status}): {exc}")
        return True
    except Exception as exc:  # noqa: BLE001 - push nie może wywracać żądań
        print(f"[dzik-os] push nieudany: {exc}")
        return True


def send_to_user(db: Session, user_id: str, title: str, body: str, url: str = "/") -> int:
    """Wysyła powiadomienie do wszystkich subskrypcji użytkownika.
    Nigdy nie podnosi wyjątku (best-effort); zwraca liczbę wysłanych."""
    subs = db.query(PushSubscription).filter_by(user_id=user_id).all()
    if not subs:
        return 0
    payload = json.dumps({"title": title, "body": body, "url": url}, ensure_ascii=False)
    sent = 0
    for sub in subs:
        if _send_one(sub, payload):
            sent += 1
        else:
            db.delete(sub)
    return sent

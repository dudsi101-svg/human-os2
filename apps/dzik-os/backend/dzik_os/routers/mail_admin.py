"""Poczta (Brevo SMTP, moduł `dzik_os.mailer`) — endpoint testowy administratora/trenera.

`POST /api/admin/mail/test` `{"to": "adres"}` → 202 `{"message_id": …}`; wysyłka w tle
(`BackgroundTasks`), temat „Test wysyłki Dzik OS” (tekst + prosty HTML). Za flagą
`DZIK_MAIL_TEST_ENDPOINT_ENABLED` (404 gdy wyłączona; produkcja: domyślnie wyłączona).
Gdy poczta nie jest skonfigurowana (`MAIL_ENABLED=0`, brak zmiennych) → 503 z NAZWAMI
brakujących zmiennych (nigdy wartości).

`message_id` to identyfikator korelacji nadany przez aplikację (format Message-ID,
domena nadawcy): trafia do treści wiadomości, audytu i logów. Nagłówek `Message-ID`
samej wiadomości nadaje serwer dostawcy — `mailer.py` buduje wiadomość wewnątrz
`send_email` i nie przyjmuje własnych nagłówków, a jego logiki nie zmieniamy.
Adres odbiorcy trafia do audytu i logów aplikacji wyłącznie jako domena.
"""

from __future__ import annotations

import re
from email.utils import make_msgid, parseaddr

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import mailer
from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..models import User
from ..observability import log_json
from ..security import active_roles, current_user

router = APIRouter(prefix="/api/admin/mail", tags=["mail"])

_ADRES = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
TEMAT = "Test wysyłki Dzik OS"


class MailTestIn(BaseModel):
    to: str = Field(min_length=6, max_length=254)


def wymagaj_endpointu() -> None:
    if not settings.mail_test_endpoint_enabled:
        raise HTTPException(status_code=404, detail="Endpoint testowy poczty jest wyłączony")


def _operator(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    """Administrator albo trener (jak w zadaniu); klient — odmowa."""
    roles = active_roles(db, user.id)
    if "ADMIN" not in roles and "COACH" not in roles:
        raise HTTPException(status_code=403, detail="Brak wymaganej roli")
    return user


def get_mail_config(request: Request) -> mailer.MailConfig:
    """Jedna instancja konfiguracji na proces (`app.state.mail_config`, lifespan)."""
    cfg = getattr(request.app.state, "mail_config", None)
    if cfg is None:
        raise HTTPException(status_code=503, detail="Poczta nie została zainicjalizowana przy starcie")
    return cfg


def tresc(message_id: str, base_url: str) -> tuple[str, str]:
    """Tekst + prosty HTML wiadomości testowej."""
    text = ("To jest testowa wiadomość z aplikacji Dzik OS.\n\n"
            "Jeśli ją czytasz, kanał SMTP (Brevo) działa: zaproszenia, resety haseł i "
            "powiadomienia będą docierać.\n\n"
            f"Identyfikator: {message_id}\nAplikacja: {base_url or 'adres nieustawiony'}")
    html = ("<p>To jest <b>testowa wiadomość</b> z aplikacji Dzik OS.</p>"
            "<p>Jeśli ją czytasz, kanał SMTP (Brevo) działa: zaproszenia, resety haseł i "
            "powiadomienia będą docierać.</p>"
            f"<p><small>Identyfikator: {message_id}<br>Aplikacja: {base_url or 'adres nieustawiony'}</small></p>")
    return text, html


def wyslij_test(cfg: mailer.MailConfig, to: str, message_id: str) -> bool:
    """Zadanie w tle: wysyłka przez `mailer.send_email` i wpis „Wysłano do …”
    w logu aplikacji (domena adresu). Błąd wysyłki jest logowany, nie rzucany —
    odpowiedź HTTP (202) już poszła."""
    domena = to.rsplit("@", 1)[-1]
    try:
        ok = mailer.send_email(to, TEMAT, *tresc(message_id, settings.public_base_url), cfg=cfg)
    except mailer.MailSendError as exc:
        log_json("mail_test_failed", level="error", to_domain=domena, message_id=message_id, reason=str(exc)[:200])
        return False
    if ok:
        log_json("mail_test_sent", to_domain=domena, message_id=message_id, summary=f"Wysłano do @{domena}")
    else:
        log_json("mail_test_skipped", level="warning", to_domain=domena, message_id=message_id, reason="MAIL_ENABLED=0")
    return ok


@router.post("/test", status_code=202, dependencies=[Depends(wymagaj_endpointu)])
def mail_test(body: MailTestIn, tasks: BackgroundTasks, request: Request, user: User = Depends(_operator),
              cfg: mailer.MailConfig = Depends(get_mail_config), db: Session = Depends(get_db)):
    to = body.to.strip()
    if not _ADRES.match(to):
        raise HTTPException(status_code=422, detail="Adres e-mail wygląda niepoprawnie")
    if not cfg.enabled:
        brak = list(getattr(request.app.state, "mail_missing", []) or [])
        raise HTTPException(status_code=503, detail="Poczta wyłączona (MAIL_ENABLED=0)"
                            + (": brak zmiennych " + ", ".join(brak) if brak else " — wysyłka wyłączona konfiguracją"))
    domena_nadawcy = parseaddr(cfg.mail_from)[1].rsplit("@", 1)[-1] or "dzik-os"
    message_id = make_msgid(domain=domena_nadawcy)
    domena = to.rsplit("@", 1)[-1]
    record_event(db, action="MAIL_TEST_QUEUED", actor_id=user.id, subject_ids=[user.id],
                 payload={"to_domain": domena, "message_id": message_id}, summary="Kolejka testowej wysyłki e-mail")
    db.commit()
    log_json("mail_test_queued", to_domain=domena, message_id=message_id, actor_id=user.id)
    tasks.add_task(wyslij_test, cfg, to, message_id)
    return {"message_id": message_id, "status": "queued", "to_domain": domena}

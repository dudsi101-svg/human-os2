"""Dowód wysyłki przez moduł Brevo (`dzik_os.mailer`) z maszyny Fly:

    python -m dzik_os.test_poczty_brevo adres@example.com

Ta sama ścieżka co `POST /api/admin/mail/test` (temat, treść, identyfikator),
ale bez sesji HTTP — do uruchomienia z `flyctl ssh console` przez workflow
„Sprawdzenie SMTP (Fly.io)”. Drukuje identyfikator i wynik; hasła nie
wypisuje nigdy. Kod wyjścia 0 wyłącznie przy potwierdzonej wysyłce.
"""

from __future__ import annotations

import sys
from email.utils import make_msgid, parseaddr

from . import mailer, poczta_start
from .config import settings
from .routers.mail_admin import TEMAT, tresc


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or "@" not in args[0]:
        print("Użycie: python -m dzik_os.test_poczty_brevo adres@example.com", file=sys.stderr)
        return 2
    poczta_start.podlacz_logger()
    cfg, brak = poczta_start.wczytaj()
    if not cfg.enabled:
        print("BŁĄD: poczta wyłączona (MAIL_ENABLED=0)" + (": brak " + ", ".join(brak) if brak else ""), file=sys.stderr)
        return 1
    message_id = make_msgid(domain=parseaddr(cfg.mail_from)[1].rsplit("@", 1)[-1] or "dzik-os")
    try:
        ok = mailer.send_email(args[0], TEMAT, *tresc(message_id, settings.public_base_url), cfg=cfg)
    except mailer.MailSendError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1
    print(f"Wysłano do @{args[0].rsplit('@', 1)[-1]} — identyfikator {message_id}" if ok else "Pominięto (MAIL_ENABLED=0)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

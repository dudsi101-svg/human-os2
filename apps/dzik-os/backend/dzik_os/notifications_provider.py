"""Adapter powiadomień (e-mail).

MVP używa NullNotificationProvider — nie wysyła żadnych prawdziwych
wiadomości (loguje wyłącznie fakt próby, bez adresu i treści — bez PII
w logach). Przypomnienia i alerty pozostają WYŁĄCZNIE w aplikacji (ekran
Dzisiaj, harmonogram, panel trenera), dopóki administrator nie skonfiguruje
prawdziwego dostawcy.

Aby podłączyć prawdziwe powiadomienia e-mail:

1. Załóż konto u dostawcy transakcyjnego e-maila (np. Resend, SendGrid,
   Mailgun) albo skonfiguruj SMTP (np. Gmail z hasłem aplikacji).
2. Zaimplementuj klasę z tym samym interfejsem co NotificationProvider.
3. Klucze API / dane SMTP WYŁĄCZNIE przez zmienne środowiskowe
   (np. DZIK_EMAIL_API_KEY) — nigdy w repozytorium.
4. Podmień `provider` poniżej na instancję nowej klasy.

Push (natywne powiadomienia w przeglądarce) wymagają dodatkowo kluczy
VAPID i subskrypcji service workera — poza zakresem tego MVP
(patrz docs/DEFERRED_FEATURES.md).
"""

from __future__ import annotations

from typing import Protocol


class NotificationProvider(Protocol):
    name: str

    def send_email(self, *, to: str, subject: str, body: str) -> bool: ...


class NullNotificationProvider:
    """Nie wysyła nic — bezpieczny domyślny provider dla dev/staging."""

    name = "null"

    def send_email(self, *, to: str, subject: str, body: str) -> bool:
        # Log strukturalny BEZ adresu, tematu i treści (temat potrafi
        # zdradzać kontekst zdrowotny) — wyłącznie fakt pominięcia.
        from .observability import log_json

        log_json("email_skipped_no_provider", level="info")
        return False


provider: NotificationProvider = NullNotificationProvider()

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

Dla zwykłego SMTP nie trzeba już nic pisać — wystarczy ustawić
`DZIK_SMTP_HOST` (oraz `DZIK_SMTP_USER`/`DZIK_SMTP_PASSWORD`/`DZIK_SMTP_FROM`),
a `SMTPNotificationProvider` włączy się sam. Bez tej zmiennej działa
`NullNotificationProvider` i nic nie wychodzi — jak dotąd.

Od migracji nr 14 e-mail jest opcjonalnym kanałem AWARYJNYM wspólnego
systemu powiadomień (dzik_os.notifications): domyślnie wyłączony per
kategoria, treść zawsze neutralna (nigdy dane zdrowotne ani kwoty) —
patrz docs/POWIADOMIENIA.md. Push (Web Push/VAPID) obsługuje osobno
push_service.py.
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


class SMTPNotificationProvider:
    """Wysyła przez zwykły serwer SMTP. Włączany WYŁĄCZNIE przez konfigurację.

    DLACZEGO ISTNIEJE. Bramka GO/NO-GO wypisała jako bloker nr 4: „e-mail
    nie wychodzi — przypomnienia o płatnościach i digest poniedziałkowy
    nigdzie nie docierają". Funkcja miała ścieżkę kodu, której nigdy nie
    wykonano. To jest ta ścieżka.

    TRZY ZASADY, KTÓRE TU OBOWIĄZUJĄ:

    1. **Nigdy nie rzuca wyjątkiem.** Powiadomienie jest kanałem POBOCZNYM
       (`docs/POWIADOMIENIA.md`); główny kanał to ekran w aplikacji. Awaria
       poczty nie ma prawa wywrócić zapisu raportu ani założenia klienta.
       Każdy błąd kończy się `False` i wpisem do logu.
    2. **Zawsze z limitem czasu.** Backend jest jednoprocesowy (R-09):
       zawieszony serwer poczty bez `timeout` zatrzymałby całą aplikację
       dla wszystkich. Limit jest obowiązkowy, nie opcjonalny.
    3. **Zero PII w logach** — ta sama reguła co w `NullNotificationProvider`.
       Nie logujemy adresu, tematu ani treści; temat potrafi zdradzić
       kontekst zdrowotny. Do logu idzie wyłącznie fakt i przyczyna klasy.
    """

    name = "smtp"

    def __init__(self, *, host: str, port: int, user: str, password: str,
                 sender: str, security: str, timeout: float) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._sender = sender or user
        self._security = security
        self._timeout = timeout

    def send_email(self, *, to: str, subject: str, body: str) -> bool:
        import smtplib
        from email.message import EmailMessage

        from .observability import log_json

        wiadomosc = EmailMessage()
        wiadomosc["From"] = self._sender
        wiadomosc["To"] = to
        wiadomosc["Subject"] = subject
        wiadomosc.set_content(body)

        try:
            if self._security == "ssl":
                polaczenie = smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout)
            else:
                polaczenie = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
            with polaczenie as serwer:
                if self._security == "starttls":
                    serwer.starttls()
                if self._user:
                    serwer.login(self._user, self._password)
                serwer.send_message(wiadomosc)
        except Exception as exc:  # noqa: BLE001 - patrz zasada 1 w docstringu
            # Nazwa klasy wyjątku, nie jego treść: komunikat serwera SMTP
            # potrafi zawierać adres odbiorcy.
            log_json("email_send_failed", level="warning", reason=type(exc).__name__)
            return False
        log_json("email_sent", level="info")
        return True


def _zbuduj_provider() -> NotificationProvider:
    """Dostawca z konfiguracji. Brak `DZIK_SMTP_HOST` = `null`, czyli stan
    sprzed 0.40.0 — aplikacja bez konfiguracji nie wysyła nic i zachowuje
    się dokładnie jak dotąd. Włączenie poczty jest DECYZJĄ operatora, nigdy
    domyślnym zachowaniem."""
    from .config import settings

    if not settings.smtp_host:
        return NullNotificationProvider()
    return SMTPNotificationProvider(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password,
        sender=settings.smtp_from,
        security=settings.smtp_security,
        timeout=settings.smtp_timeout,
    )


provider: NotificationProvider = _zbuduj_provider()

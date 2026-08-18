"""Adapter operatora płatności — PRZYGOTOWANA ARCHITEKTURA, bez działającej
integracji (świadoma decyzja produktowa: system pozostaje ewidencją ręczną).

Interfejs portu (PaymentProviderPort) obejmuje wszystko, czego wymaga
bezpieczne podłączenie prawdziwego operatora w przyszłości:

* payment_link() — URL sesji płatności operatora (None = brak; frontend
  pokazuje wtedy dane przelewu / link zewnętrzny trenera),
* verify_webhook_signature() — kryptograficzna weryfikacja, że webhook
  przyszedł od operatora (bez poprawnego podpisu NIC nie jest przetwarzane
  ani zapisywane),
* parse_webhook() — zamiana surowego ciała na neutralne WebhookEvent
  (id zdarzenia, typ, rekord, kwota, waluta, occurred_at).

Przetwarzanie zdarzeń (idempotencja po event_id, odporność na powtórki i
złą kolejność) jest wspólne dla wszystkich providerów i mieszka w
payment_events.process_webhook() — provider tylko weryfikuje i parsuje.

ZASADY BEZPIECZEŃSTWA (obowiązują też przyszłego prawdziwego providera):
1. Jedynym źródłem prawdy o wyniku płatności jest PODPISANY webhook
   operatora. Przekierowanie przeglądarki (redirect/return URL) NIGDY nie
   zmienia statusu — parametry powrotu są niezaufane (użytkownik może je
   spreparować). Żaden kod w aplikacji nie czyta parametrów powrotu.
2. Klucze API wyłącznie przez zmienne środowiskowe — nigdy w repozytorium.
3. Aplikacja NIGDY nie przechowuje danych kart płatniczych.

Jak podłączyć prawdziwego operatora (Stripe / Przelewy24 / PSP z BLIK):
docs/PLATNOSCI.md §Operator.

NullPaymentProvider to referencyjna implementacja portu do testów
kontraktowych: deterministyczny podpis HMAC-SHA256 i JSON-owe zdarzenia,
zero prawdziwych płatności.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Protocol

# Typy zdarzeń wspólne dla portu (provider mapuje swoje typy na te trzy).
EVENT_PAYMENT_STARTED = "payment.started"
EVENT_PAYMENT_SUCCEEDED = "payment.succeeded"
EVENT_PAYMENT_FAILED = "payment.failed"

KNOWN_EVENT_TYPES = (
    EVENT_PAYMENT_STARTED, EVENT_PAYMENT_SUCCEEDED, EVENT_PAYMENT_FAILED,
)


@dataclass(frozen=True)
class WebhookEvent:
    """Neutralne zdarzenie operatora po weryfikacji podpisu i parsowaniu."""

    provider: str
    event_id: str          # unikalny identyfikator zdarzenia u operatora
    event_type: str        # jeden z KNOWN_EVENT_TYPES
    record_id: str         # nasza należność (PaymentRecord.id)
    amount_cents: int | None
    currency: str | None
    occurred_at: str       # ISO; podstawa ochrony przed złą kolejnością
    session_id: str | None = None  # id sesji/próby po stronie operatora


class WebhookParseError(ValueError):
    """Ciało webhooka nie jest poprawnym zdarzeniem tego operatora."""


class PaymentProviderPort(Protocol):
    name: str

    def payment_link(self, *, record_id: str, amount_cents: int, currency: str,
                     description: str) -> str | None: ...

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool: ...

    def parse_webhook(self, body: bytes) -> WebhookEvent: ...


class NullPaymentProvider:
    """Provider "null": nie tworzy prawdziwych płatności (payment_link →
    None), ale implementuje pełny port webhooków deterministycznie —
    dokładnie po to, by kontrakt (podpis, idempotencja, kolejność) był
    przetestowany ZANIM pojawi się prawdziwy operator."""

    name = "null"

    def __init__(self, secret: str = "null-provider-secret-not-for-production") -> None:
        self._secret = secret.encode("utf-8")

    def payment_link(self, *, record_id: str, amount_cents: int, currency: str,
                     description: str) -> str | None:
        return None

    def sign(self, body: bytes) -> str:
        """Pomocnik testów kontraktowych: podpis, jaki wystawiłby operator."""
        return hmac.new(self._secret, body, hashlib.sha256).hexdigest()

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign(body), signature)

    def parse_webhook(self, body: bytes) -> WebhookEvent:
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebhookParseError("Nieprawidłowe ciało zdarzenia") from exc
        for field in ("event_id", "event_type", "record_id", "occurred_at"):
            if not isinstance(data.get(field), str) or not data[field]:
                raise WebhookParseError(f"Brak pola zdarzenia: {field}")
        if data["event_type"] not in KNOWN_EVENT_TYPES:
            raise WebhookParseError(f"Nieznany typ zdarzenia: {data['event_type']}")
        amount = data.get("amount_cents")
        if amount is not None and not isinstance(amount, int):
            raise WebhookParseError("amount_cents musi być liczbą całkowitą groszy")
        return WebhookEvent(
            provider=self.name,
            event_id=data["event_id"],
            event_type=data["event_type"],
            record_id=data["record_id"],
            amount_cents=amount,
            currency=data.get("currency"),
            occurred_at=data["occurred_at"],
            session_id=data.get("session_id"),
        )


# Aktywny provider aplikacji. System jest ewidencją ręczną — Null nie
# generuje linków płatności i nie ma wystawionego endpointu webhooka
# (endpoint HTTP powstanie dopiero z prawdziwym operatorem —
# docs/PLATNOSCI.md §Operator).
provider: PaymentProviderPort = NullPaymentProvider()

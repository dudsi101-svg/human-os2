"""Adapter operatora płatności.

MVP używa LocalDemoProvider (bez prawdziwych płatności, bez danych kart).
Aby podłączyć prawdziwego operatora (Stripe, Przelewy24, BLIK przez PSP):

1. Zaimplementuj klasę z tym samym interfejsem co PaymentProvider.
2. Wskaż ją w konfiguracji (DZIK_PAYMENT_PROVIDER) i podaj klucze API
   wyłącznie przez zmienne środowiskowe (nigdy w repozytorium).
3. payment_link() powinno zwracać URL sesji płatności operatora;
   webhook operatora oznacza PaymentRecord jako PAID (endpoint webhooka
   do dodania wraz z weryfikacją podpisu operatora).

Aplikacja NIGDY nie przechowuje danych kart płatniczych — pełni jedynie
rolę ewidencji terminów i statusów.
"""

from __future__ import annotations

from typing import Protocol


class PaymentProvider(Protocol):
    name: str

    def payment_link(self, *, record_id: str, amount_cents: int, currency: str,
                     description: str) -> str | None: ...


class LocalDemoProvider:
    """Provider demonstracyjny: nie tworzy prawdziwych płatności; zwraca
    None (frontend pokazuje wtedy dane przelewu / link zewnętrzny trenera)."""

    name = "local-demo"

    def payment_link(self, *, record_id: str, amount_cents: int, currency: str,
                     description: str) -> str | None:
        return None


provider: PaymentProvider = LocalDemoProvider()

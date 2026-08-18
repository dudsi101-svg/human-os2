"""Adapter dostawcy AI — propose-only, jawnie oznaczone, zero autonomii.

MVP używa NullAIProvider: nie wysyła żadnych danych na zewnątrz i zawsze
zwraca `None` (brak konfiguracji), co UI pokazuje wprost jako "funkcja
wymaga konfiguracji" — nigdy jako cichy błąd czy pustą odpowiedź.

Zgodnie z Konstytucją Human OS (rozdz. 7 — granice roli AI):
* AI nie ma większych uprawnień niż trener czy klient;
* propozycja AI nigdy nie staje się automatycznie decyzją — trener
  zawsze edytuje/zatwierdza przed wysłaniem (patrz
  routers/checkins.py::ai_summary, który niczego nie zapisuje);
* brak ukrywania niepewności — podsumowanie AI jest zawsze oznaczone
  jako propozycja w interfejsie.

Aby podłączyć prawdziwego dostawcę (np. Anthropic Claude API):

1. Zaimplementuj klasę z tym samym interfejsem co AIProvider.
2. Klucz API WYŁĄCZNIE przez zmienną środowiskową (np. DZIK_AI_API_KEY)
   — nigdy w repozytorium.
3. Podmień `provider` poniżej na instancję nowej klasy.
4. Wysyłaj do dostawcy WYŁĄCZNIE minimalny potrzebny zakres danych
   (docs/DATA_PROCESSING_MAP.md §AI) — nigdy dane wrażliwe bez wyraźnej,
   osobnej zgody klienta na ten konkretny cel przetwarzania.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# Powód niedostępności pokazywany użytkownikowi, gdy operator nie
# skonfigurował żadnego dostawcy. Jawna informacja, nigdy błąd techniczny —
# funkcja ma wtedy działać w trybie formularza (patrz onboarding_ai.py).
NO_PROVIDER_REASON = (
    "Wersja robocza podsumowania od modelu wymaga konfiguracji przez "
    "administratora (klucz dostawcy poza repozytorium). Rozmowa i "
    "podsumowanie działają normalnie — przygotujemy je krok po kroku."
)


@dataclass(frozen=True)
class AISummary:
    summary: str
    draft_response: str
    flags: list[str]


@dataclass(frozen=True)
class AIJsonResponse:
    """Surowa odpowiedź dostawcy dla żądania o ustalonym schemacie.

    `text` NIE jest zaufany — zawsze przechodzi walidację schematem po
    stronie serwera (onboarding_ai.parse_summary_draft). Liczniki tokenów
    służą wyłącznie kontroli kosztów; treść nigdy nie trafia do logów."""

    text: str
    tokens_in: int = 0
    tokens_out: int = 0


class AIProvider(Protocol):
    name: str
    enabled: bool

    def summarize_checkin(
        self, *, payload: dict, history_note: str | None
    ) -> AISummary | None: ...

    def propose_json(
        self,
        *,
        system_prompt: str,
        data_section: str,
        schema_hint: str,
        timeout_s: int,
    ) -> AIJsonResponse | None:
        """Jedno wywołanie modelu z twardym kontraktem wyjściowym.

        `system_prompt` to instrukcje aplikacji, `data_section` to wyłącznie
        DANE użytkownika (nigdy instrukcje — patrz onboarding_ai.py
        §ochrona przed wstrzyknięciem). Zwraca surowy tekst do walidacji
        albo None, gdy dostawca nie odpowiedział."""
        ...


class NullAIProvider:
    """Nie wywołuje żadnego modelu — bezpieczny domyślny provider."""

    name = "null"
    enabled = False

    def summarize_checkin(
        self, *, payload: dict, history_note: str | None
    ) -> AISummary | None:
        return None

    def propose_json(
        self,
        *,
        system_prompt: str,
        data_section: str,
        schema_hint: str,
        timeout_s: int,
    ) -> AIJsonResponse | None:
        return None


provider: AIProvider = NullAIProvider()

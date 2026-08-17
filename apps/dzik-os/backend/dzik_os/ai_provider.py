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


@dataclass(frozen=True)
class AISummary:
    summary: str
    draft_response: str
    flags: list[str]


class AIProvider(Protocol):
    name: str
    enabled: bool

    def summarize_checkin(
        self, *, payload: dict, history_note: str | None
    ) -> AISummary | None: ...


class NullAIProvider:
    """Nie wywołuje żadnego modelu — bezpieczny domyślny provider."""

    name = "null"
    enabled = False

    def summarize_checkin(
        self, *, payload: dict, history_note: str | None
    ) -> AISummary | None:
        return None


provider: AIProvider = NullAIProvider()

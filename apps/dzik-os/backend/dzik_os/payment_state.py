"""Maszyna stanów należności płatniczej (PaymentRecord.status).

Model i diagram stanów: docs/PLATNOSCI.md. Zasady:

* Jedyne źródło prawdy o dozwolonych przejściach to ALLOWED_PAYMENT_TRANSITIONS
  — egzekwowane W BACKENDZIE (frontend niczego nie wymusza); nieprawidłowe
  przejście to zawsze 422 we wspólnym modelu błędów (P9), nigdy ciche
  zignorowanie ani nadpisanie.
* Statusy "pieniężne" (PAID / REFUNDED / PARTIALLY_REFUNDED / IN_PROGRESS /
  FAILED) osiąga się WYŁĄCZNIE przez dedykowane endpointy rejestrujące
  transakcję (adnotację ręczną trenera albo — w przyszłości — zdarzenie
  operatora); ogólny endpoint /status obsługuje tylko statusy
  administracyjne (ADMINISTRATIVE_TARGETS).
* Statusy sprzed migracji nr 15 (PENDING/PAID/OVERDUE/CANCELLED) są ścisłym
  podzbiorem nowego słownika — migracja niczego nie przepisuje (mapowanie
  tożsamościowe, zero utraty danych).
"""

from __future__ import annotations

from fastapi import HTTPException

# Pełny słownik statusów należności.
PAYMENT_STATUSES = (
    "PLANNED",       # zaplanowana przyszła rata (jeszcze nie wymagalna)
    "PENDING",       # wymagalna, oczekuje na zapłatę
    "IN_PROGRESS",   # trwa próba płatności (przyszły operator online)
    "PAID",          # opłacona (zarejestrowana transakcja)
    "OVERDUE",       # po terminie, nieopłacona
    "FAILED",        # nieudana próba płatności
    "CANCELLED",     # anulowana (należność przestaje obowiązywać)
    "PARTIALLY_REFUNDED",  # zwrócona częściowo
    "REFUNDED",      # zwrócona w całości (stan końcowy)
)

# Jawna tablica dozwolonych przejść. Brak pary (from -> to) = 422.
ALLOWED_PAYMENT_TRANSITIONS: dict[str, set[str]] = {
    "PLANNED": {"PENDING", "PAID", "CANCELLED"},
    "PENDING": {"IN_PROGRESS", "PAID", "OVERDUE", "FAILED", "CANCELLED"},
    "IN_PROGRESS": {"PAID", "FAILED", "PENDING", "CANCELLED"},
    "OVERDUE": {"IN_PROGRESS", "PAID", "FAILED", "PENDING", "CANCELLED"},
    "FAILED": {"IN_PROGRESS", "PAID", "PENDING", "OVERDUE", "CANCELLED"},
    # PAID -> PENDING/OVERDUE wyłącznie przez korektę odwracającą
    # (cofnięcie omyłkowego oznaczenia — ślad zostaje w transakcjach).
    "PAID": {"PARTIALLY_REFUNDED", "REFUNDED", "PENDING", "OVERDUE"},
    # Kolejny zwrot częściowy nie zmienia nazwy stanu (przejście do samego
    # siebie jest dozwolone jawnie), pełne dopełnienie -> REFUNDED;
    # powrót do PAID wyłącznie korektą odwracającą zwrot.
    "PARTIALLY_REFUNDED": {"PARTIALLY_REFUNDED", "REFUNDED", "PAID"},
    # Stan końcowy dla zwykłego przepływu; wyjście wyłącznie korektą
    # odwracającą omyłkowy zwrot.
    "REFUNDED": {"PAID", "PARTIALLY_REFUNDED"},
    # Przywrócenie omyłkowo anulowanej należności (z audytem).
    "CANCELLED": {"PENDING"},
}

# Statusy osiągalne przez ogólny endpoint POST /records/{id}/status.
# Statusy pieniężne wymagają dedykowanych endpointów z transakcją.
ADMINISTRATIVE_TARGETS = {"PENDING", "OVERDUE", "CANCELLED"}

# Należność "do zapłaty" — podstawa przypomnień i flag zaległości.
# IN_PROGRESS celowo poza zbiorem (trwa próba płatności — nie ponaglamy).
DUE_STATUSES = ("PENDING", "OVERDUE", "FAILED")

# Statusy, z których wolno RĘCZNIE oznaczyć należność jako opłaconą —
# stany po zwrocie wracają do PAID wyłącznie korektą odwracającą zwrot.
MARKABLE_AS_PAID = tuple(
    s for s, targets in ALLOWED_PAYMENT_TRANSITIONS.items()
    if "PAID" in targets and s not in ("PARTIALLY_REFUNDED", "REFUNDED")
)


def assert_transition(from_status: str, to_status: str) -> None:
    """Nieprawidłowe przejście = 422 (wspólny model błędów), nigdy wyjątek
    połknięty po drodze ani ciche nadpisanie."""
    allowed = ALLOWED_PAYMENT_TRANSITIONS.get(from_status)
    if allowed is None:
        raise HTTPException(
            status_code=422, detail=f"Nieznany status należności: {from_status}"
        )
    if to_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Niedozwolone przejście statusu płatności: "
                f"{from_status} → {to_status}"
            ),
        )


def effective_status(status: str, due_date: str, today: str) -> str:
    """Status prezentacyjny: wymagalna należność po terminie pokazywana
    jako OVERDUE (bez mutowania wiersza — zaległość to fakt kalendarzowy)."""
    if status == "PENDING" and due_date < today:
        return "OVERDUE"
    return status

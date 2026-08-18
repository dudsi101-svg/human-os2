"""Słowniki bazy ćwiczeń: partie mięśniowe, poziomy trudności i wzorce
ruchu.

`MUSCLE_LABELS` jest **kontraktem** — te same klucze są używane przez
frontend (`frontend/src/types.ts::MUSCLE_LABELS`) oraz przez planowany
rysunek sylwetki (kolejna runda). Klucze nie mogą być zmieniane ani
usuwane bez migracji danych; dokładanie nowych jest bezpieczne.

Zakres odpowiedzialności: to know-how trenerskie (jak wykonać ćwiczenie),
nie porada medyczna. Moduł nie ocenia stanu zdrowia i nie dobiera
ćwiczeń — wybór należy zawsze do trenera (zasada Human OS: system
przechowuje i pokazuje decyzję człowieka, nie podejmuje jej za niego)."""

from __future__ import annotations

import unicodedata

# --- Partie mięśniowe (kontrakt wspólny z rysunkiem sylwetki) ---
MUSCLE_LABELS: dict[str, str] = {
    "KLATKA_PIERSIOWA": "klatka piersiowa",
    "NAJSZERSZY_GRZBIETU": "najszerszy grzbietu",
    "CZWOROBOCZNY": "czworoboczny",
    "ROMBOIDALNE": "romboidalne",
    "PROSTOWNIKI_GRZBIETU": "prostowniki grzbietu",
    "BARK_PRZEDNI": "bark przedni",
    "BARK_BOCZNY": "bark boczny",
    "BARK_TYLNY": "bark tylny",
    "BICEPS": "biceps",
    "TRICEPS": "triceps",
    "PRZEDRAMIE": "przedramię",
    "BRZUCH_PROSTY": "brzuch prosty",
    "BRZUCH_SKOSNY": "brzuch skośny",
    "MIESNIE_GLEBOKIE": "mięśnie głębokie",
    "POSLADKI": "pośladki",
    "CZWOROGLOWY_UDA": "czworogłowy uda",
    "DWUGLOWY_UDA": "dwugłowy uda",
    "PRZYWODZICIELE": "przywodziciele",
    "ODWODZICIELE": "odwodziciele",
    "LYDKA": "łydka",
    "ZGINACZE_BIODRA": "zginacze biodra",
}

MUSCLE_KEYS: frozenset[str] = frozenset(MUSCLE_LABELS)

# --- Poziom trudności ---
EXERCISE_LEVELS: tuple[str, ...] = (
    "POCZATKUJACY",
    "SREDNIOZAAWANSOWANY",
    "ZAAWANSOWANY",
)

LEVEL_LABELS: dict[str, str] = {
    "POCZATKUJACY": "początkujący",
    "SREDNIOZAAWANSOWANY": "średniozaawansowany",
    "ZAAWANSOWANY": "zaawansowany",
}

# --- Wzorce ruchu ---
MOVEMENT_PATTERNS: tuple[str, ...] = (
    "PRZYSIAD",
    "ZAWIAS_BIODROWY",
    "WYPYCHANIE_POZIOME",
    "WYPYCHANIE_PIONOWE",
    "PRZYCIAGANIE_POZIOME",
    "PRZYCIAGANIE_PIONOWE",
    "WYKROK",
    "NOSZENIE",
    "ROTACJA",
    "ANTYROTACJA",
    "IZOLACJA",
    "CARDIO",
    "MOBILNOSC",
)

PATTERN_LABELS: dict[str, str] = {
    "PRZYSIAD": "przysiad",
    "ZAWIAS_BIODROWY": "zawias biodrowy",
    "WYPYCHANIE_POZIOME": "wypychanie poziome",
    "WYPYCHANIE_PIONOWE": "wypychanie pionowe",
    "PRZYCIAGANIE_POZIOME": "przyciąganie poziome",
    "PRZYCIAGANIE_PIONOWE": "przyciąganie pionowe",
    "WYKROK": "wykrok",
    "NOSZENIE": "noszenie",
    "ROTACJA": "rotacja",
    "ANTYROTACJA": "antyrotacja",
    "IZOLACJA": "izolacja",
    "CARDIO": "cardio",
    "MOBILNOSC": "mobilność",
}

# Zgrubna grupa (pole zgodności wstecznej `Exercise.muscle_group`).
MUSCLE_GROUPS: tuple[str, ...] = (
    "NOGI", "PLECY", "KLATKA", "BARKI", "RECE", "BRZUCH",
    "CALE_CIALO", "MOBILNOSC", "CARDIO", "INNE",
)


def validate_muscle_keys(keys: list[str]) -> list[str]:
    """Zwraca listę nieznanych kluczy (pusta = wszystko poprawne)."""
    return [k for k in keys if k not in MUSCLE_KEYS]


def join_muscles(keys: list[str] | None) -> str | None:
    """Lista kluczy → CSV do kolumny tekstowej (None dla pustej listy)."""
    if not keys:
        return None
    return ",".join(keys)


def split_muscles(value: str | None) -> list[str]:
    """CSV z kolumny → lista kluczy (odporne na puste pola i spacje)."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def fold(text: str) -> str:
    """Normalizacja tekstu do wyszukiwania: bez wielkości liter i bez
    polskich znaków diakrytycznych („przysiad” == „PRZYSIAD” ==
    „przysiąd”). „ł” nie rozkłada się w NFKD, więc podmieniamy je
    jawnie."""
    lowered = text.casefold().replace("ł", "l").replace("Ł", "l")
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

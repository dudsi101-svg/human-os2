"""Silnik LOKALNY przepisywania tekstu ze zdjęcia (OCR) + deterministyczne
czytanie tabeli wartości odżywczych.

Ten moduł nie wysyła niczego na zewnątrz i nie dotyka bazy danych: dostaje
bajty obrazu, zwraca tekst albo czytelny powód, dlaczego się nie udało.
Tryb rozszerzony (model widzenia) mieszka w ``ocr_ai.py``, a kolejka i
zapis wyników w ``ocr_queue.py``.

**Dlaczego ``subprocess``, a nie ``pytesseract``.** ``pytesseract`` jest
cienką nakładką na dokładnie to samo wywołanie binarki ``tesseract`` —
dokłada zależność, a i tak nie daje tego, czego tu potrzebujemy: twardego
limitu czasu z zabiciem procesu, kontroli nad pamięcią wejścia i czytelnego
rozróżnienia „brak binarki” od „binarka zwróciła błąd”. Pillow (potrzebny
do zmniejszenia obrazu) jest już w zależnościach aplikacji. Uzasadnienie
w docs/OCR.md §silnik lokalny.

**Ograniczenia maszyny.** Produkcja to Fly.io shared-cpu-1x z 512 MB RAM,
więc przed rozpoznaniem obraz jest zmniejszany (dłuższy bok
``DZIK_OCR_MAX_PX``, domyślnie 1600 px) i konwertowany do skali szarości —
Tesseract dostaje wtedy kilka MB, nie kilkadziesiąt. Twardy limit czasu
(``DZIK_OCR_TIMEOUT_S``) kończy zadanie zamiast zajechać maszynę.

**Brak Tesseracta to STAN, nie awaria.** Środowisko deweloperskie i testowe
nie ma zainstalowanej binarki — ``availability()`` zwraca wtedy jawny powód
po polsku, a zadanie kończy się statusem FAILED z kodem
``ENGINE_UNAVAILABLE``. Nigdy wyjątek, nigdy 500.

Prywatność: rozpoznany tekst jest zwracany wywołującemu i NIGDY nie trafia
do logów ani metryk (patrz observability.py) — logujemy co najwyżej liczbę
znaków i czas trwania.
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
from dataclasses import dataclass

from PIL import Image, ImageOps

from .config import settings

#: Typy MIME, które w ogóle nadają się do OCR (PDF i wideo świadomie poza
#: zakresem — patrz docs/OCR.md §znane ograniczenia).
OCR_IMAGE_TYPES: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")

#: Kody błędów zadania (stabilne, trafiają do API i testów; nigdy treść).
ERR_ENGINE_UNAVAILABLE = "ENGINE_UNAVAILABLE"
ERR_TIMEOUT = "TIMEOUT"
ERR_ENGINE_ERROR = "ENGINE_ERROR"
ERR_BAD_IMAGE = "BAD_IMAGE"
ERR_TOO_LARGE = "TOO_LARGE"
ERR_EMPTY_TEXT = "EMPTY_TEXT"

ENGINE_UNAVAILABLE_REASON = (
    "Silnik przepisywania tekstu nie jest zainstalowany na tym serwerze. "
    "Zdjęcie zostało zapisane i nic nie zginęło — tekst trzeba na razie "
    "przepisać ręcznie. Administrator włącza silnik w obrazie aplikacji."
)
TIMEOUT_REASON = (
    "Rozpoznawanie trwało zbyt długo i zostało przerwane. Spróbuj zrobić "
    "zdjęcie z bliska, tylko tej części kartki, która Cię interesuje."
)
ENGINE_ERROR_REASON = (
    "Silnik przepisywania tekstu nie poradził sobie z tym zdjęciem. "
    "Spróbuj ponownie przy lepszym świetle albo przepisz tekst ręcznie."
)
BAD_IMAGE_REASON = (
    "Tego pliku nie da się odczytać jako zdjęcia. Wybierz zdjęcie JPG, "
    "PNG albo WEBP."
)
EMPTY_TEXT_REASON = (
    "Na zdjęciu nie udało się odczytać żadnego tekstu. Spróbuj ponownie: "
    "kartka na płasko, dobre światło, tekst na całą klatkę."
)


@dataclass(frozen=True)
class EngineAvailability:
    """Czy silnik lokalny jest gotowy do pracy (i jeśli nie — dlaczego)."""

    available: bool
    reason: str = ""


@dataclass(frozen=True)
class OcrResult:
    """Wynik jednej próby rozpoznania. ``ok=False`` NIGDY nie jest wyjątkiem
    — to stan zadania z powodem do pokazania człowiekowi wprost."""

    ok: bool
    text: str = ""
    reason: str = ""
    error_code: str = ""


# ---------------------------------------------------------------------------
# Przygotowanie obrazu (pamięć!).
# ---------------------------------------------------------------------------


def prepare_image(data: bytes, *, max_px: int | None = None) -> bytes:
    """Zmniejsza obraz do ``max_px`` na dłuższym boku, prostuje wg EXIF i
    konwertuje do skali szarości (PNG bezstratny — OCR nie lubi artefaktów
    JPEG). Dzięki temu do silnika trafia kilka MB, a nie kilkadziesiąt.

    ValueError, gdy danych nie da się zdekodować jako obrazu."""
    limit = max_px or settings.ocr_max_px
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise ValueError("Nie można zdekodować obrazu") from exc
    img = ImageOps.exif_transpose(img)
    if max(img.size) > limit:
        img.thumbnail((limit, limit), Image.LANCZOS)
    img = img.convert("L")
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Silnik lokalny.
# ---------------------------------------------------------------------------


class LocalOcrEngine:
    """Tesseract wywoływany przez ``subprocess`` (stdin -> stdout)."""

    name = "LOCAL"

    def availability(self) -> EngineAvailability:
        """Sprawdzenie obecności binarki przy KAŻDYM pytaniu — obraz
        produkcyjny ma Tesseracta, środowisko testowe nie, a wynik nie jest
        cache'owany, żeby stan aplikacji nie zależał od kolejności importów."""
        if shutil.which(settings.ocr_binary) is None:
            return EngineAvailability(False, ENGINE_UNAVAILABLE_REASON)
        return EngineAvailability(True)

    def recognize(
        self, image: bytes, *, content_type: str = "image/png", timeout_s: int | None = None
    ) -> OcrResult:
        """Jedno rozpoznanie. Zwraca ``OcrResult`` — nigdy nie podnosi
        wyjątku z powodu braku silnika, złego obrazu ani przekroczonego czasu."""
        status = self.availability()
        if not status.available:
            return OcrResult(False, reason=status.reason, error_code=ERR_ENGINE_UNAVAILABLE)
        if content_type not in OCR_IMAGE_TYPES:
            return OcrResult(False, reason=BAD_IMAGE_REASON, error_code=ERR_BAD_IMAGE)
        try:
            prepared = prepare_image(image)
        except ValueError:
            return OcrResult(False, reason=BAD_IMAGE_REASON, error_code=ERR_BAD_IMAGE)
        timeout = timeout_s or settings.ocr_timeout_s
        text = self._run(prepared, settings.ocr_languages, timeout)
        if text is None and settings.ocr_languages != "eng":
            # Brak pakietu językowego (np. tesseract-ocr-pol) nie może
            # oznaczać końca funkcji — druga próba na samym angielskim.
            text = self._run(prepared, "eng", timeout)
        if text is None:
            return OcrResult(False, reason=ENGINE_ERROR_REASON, error_code=ERR_ENGINE_ERROR)
        if text == "__TIMEOUT__":
            return OcrResult(False, reason=TIMEOUT_REASON, error_code=ERR_TIMEOUT)
        cleaned = normalize_text(text)
        if not cleaned:
            return OcrResult(False, reason=EMPTY_TEXT_REASON, error_code=ERR_EMPTY_TEXT)
        return OcrResult(True, text=cleaned)

    @staticmethod
    def _run(image: bytes, languages: str, timeout_s: int) -> str | None:
        """Surowe wywołanie binarki. ``None`` = błąd silnika,
        ``"__TIMEOUT__"`` = przekroczony czas (proces zabity)."""
        cmd = [
            settings.ocr_binary, "stdin", "stdout",
            "-l", languages,
            "--psm", str(settings.ocr_psm),
        ]
        try:
            proc = subprocess.run(
                cmd, input=image, capture_output=True, timeout=timeout_s, check=False
            )
        except subprocess.TimeoutExpired:
            return "__TIMEOUT__"
        except (OSError, ValueError):
            # Binarka zniknęła między sprawdzeniem a wywołaniem albo system
            # odmówił uruchomienia procesu — to nadal STAN, nie wyjątek.
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout.decode("utf-8", errors="replace")


engine = LocalOcrEngine()


def normalize_text(raw: str) -> str:
    """Porządkowanie wyjścia OCR: bez znaków sterujących, bez ciągów pustych
    linii, bez spacji na końcach wierszy. Treść nie jest zmieniana."""
    lines = [line.replace("\x0c", "").rstrip() for line in raw.replace("\r\n", "\n").split("\n")]
    out: list[str] = []
    for line in lines:
        if line.strip():
            out.append(line.strip())
        elif out and out[-1] != "":
            out.append("")
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Deterministyczne czytanie tabeli wartości odżywczych (tryb lokalny).
# ---------------------------------------------------------------------------

#: Zakresy takie same jak przy imporcie CSV (routers/food_catalog.py).
KCAL_MAX = 900.0
MACRO_MAX = 100.0
PORTION_MAX = 5000.0

_NUMBER = r"(\d{1,4}(?:[.,]\d{1,2})?)"

# Kolejność ma znaczenie: „węglowodany, w tym cukry” nie może trafić w
# regułę cukrów, dlatego cukry w ogóle nie są czytane (nie mamy takiego pola).
_FIELD_PATTERNS: list[tuple[str, str, float]] = [
    ("kcal_100g", r"(?:wartość\s+energetyczna|energia|kcal|energy)", KCAL_MAX),
    ("protein_100g", r"(?:białko|bialko|protein)", MACRO_MAX),
    ("fat_100g", r"(?:tłuszcz|tluszcz|fat)", MACRO_MAX),
    ("carbs_100g", r"(?:węglowodan|weglowodan|carbohydrate)", MACRO_MAX),
    ("fiber_100g", r"(?:błonnik|blonnik|fibre|fiber)", MACRO_MAX),
    ("portion_g", r"(?:porcja|opakowanie zawiera|masa netto)", PORTION_MAX),
]


def _first_number(text: str, maximum: float) -> float | None:
    """Pierwsza liczba w linii mieszcząca się w zakresie — albo None.

    ŚWIADOMIE bierzemy pierwszą, nie „najlepszą”: kolumna „w 100 g” stoi na
    etykietach jako pierwsza. Wartość spoza zakresu jest odrzucana, a pole
    zostaje puste — nigdy nie zgadujemy (docs/OCR.md §format propozycji)."""
    for match in re.finditer(_NUMBER, text):
        value = float(match.group(1).replace(",", "."))
        if 0 <= value <= maximum:
            return value
    return None


def parse_nutrition_label(text: str) -> dict[str, float | str | None]:
    """Czyta tabelę wartości odżywczych z rozpoznanego tekstu etykiety.

    Zwraca WYŁĄCZNIE pola, które udało się odczytać jednoznacznie. Pole
    nieodczytane zostaje puste (``None``) i człowiek uzupełnia je sam —
    zgadywanie brakującej wartości byłoby fałszowaniem danych żywieniowych.

    Funkcja jest czysta (bez we/wy), więc łatwo ją testować i uruchamiać na
    wyniku dowolnego silnika."""
    proposal: dict[str, float | str | None] = {
        "name": None, "kcal_100g": None, "protein_100g": None, "fat_100g": None,
        "carbs_100g": None, "fiber_100g": None, "portion_g": None,
    }
    lines = [line for line in text.split("\n") if line.strip()]
    lowered = [line.lower() for line in lines]
    for field, pattern, maximum in _FIELD_PATTERNS:
        for index, line in enumerate(lowered):
            match = re.search(pattern, line)
            if match is None:
                continue
            value = _first_number(line[match.end():], maximum)
            if value is None and index + 1 < len(lowered):
                # Etykiety bywają dwukolumnowe z wartością w kolejnym wierszu.
                value = _first_number(lowered[index + 1], maximum)
            if value is not None:
                proposal[field] = value
                break
    # Nazwa: pierwszy wiersz, który nie jest częścią tabeli wartości ani
    # samą liczbą. Nadal tylko propozycja — trener ją poprawia.
    for line in lines:
        low = line.lower()
        if any(re.search(p, low) for _, p, _ in _FIELD_PATTERNS):
            continue
        if len(line) < 3 or not re.search(r"[a-ząćęłńóśżź]", low):
            continue
        proposal["name"] = line[:300]
        break
    return proposal


def clamp_proposal(raw: dict) -> dict[str, float | str | None]:
    """Walidacja propozycji (z DOWOLNEGO silnika) zakresami z importu CSV.

    Wartość spoza zakresu albo nieliczbowa nie jest „naprawiana” — pole po
    prostu zostaje puste."""
    limits = {
        "kcal_100g": KCAL_MAX, "protein_100g": MACRO_MAX, "fat_100g": MACRO_MAX,
        "carbs_100g": MACRO_MAX, "fiber_100g": MACRO_MAX, "portion_g": PORTION_MAX,
    }
    out: dict[str, float | str | None] = {"name": None}
    name = raw.get("name")
    if isinstance(name, str) and name.strip():
        out["name"] = name.strip()[:300]
    for field, maximum in limits.items():
        value = raw.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            out[field] = None
            continue
        out[field] = float(value) if 0 <= float(value) <= maximum else None
    return out

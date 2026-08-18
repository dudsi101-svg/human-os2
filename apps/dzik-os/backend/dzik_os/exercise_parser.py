"""Silnik LOKALNY uzupełniania tabeli parametrów ćwiczenia z wklejonego
opisu tekstowego.

Trener wkleja jednolity opis ćwiczenia (własne notatki, fragment książki,
tekst przepisany ze zdjęcia), a ten moduł wyciąga z niego pola edytora:
nazwę, mięśnie główne i pomocnicze, sprzęt, poziom, wzorzec ruchu, kroki
techniki, błędy, wskazówki, bezpieczeństwo, warianty, tempo, oddech i
efekt. Nic nie zapisuje i niczego nie wysyła na zewnątrz — dostaje tekst,
zwraca PROPOZYCJĘ dla człowieka. Tryb rozszerzony (model językowy)
mieszka w ``exercise_parser_ai.py``.

**ZASADA NADRZĘDNA: nigdy nie zgadujemy.** Pole, którego nie da się
odczytać jednoznacznie, zostaje PUSTE i trafia na jawną listę
„nie udało się odczytać”. Pięć pustych pól jest lepsze niż jedno
wymyślone: wymyślona wartość w bazie know-how trenera wygląda dokładnie
tak samo jak wartość wpisana ręcznie, więc raz wpuszczona już nie daje
się odróżnić od prawdy.

**Dlaczego słownik synonimów, a nie dopasowanie rozmyte.** Rozmyte
dopasowanie („czworogłowy” ≈ „czworoboczny”, odległość edycyjna 5)
myliłoby partie mięśniowe, których nie wolno pomylić. Słownik jest
skończony, czytelny i wprost udokumentowany (docs/BAZA_CWICZEN.md
§Auto-uzupełnianie) — nieznana nazwa partii po prostu nie trafia do
wyniku, zamiast trafić do najbliższego klucza.

**Odporność na polskie znaki i wielkość liter** zapewnia
``muscles.fold()`` — ten sam mechanizm, którego używa wyszukiwarka bazy
ćwiczeń, więc „POŚLADKI”, „pośladków” i „posladki” znaczą to samo.
Wyrażenia w słownikach zapisujemy RDZENIAMI bez odmiany (``posladk``),
a dopasowanie dokleja dowolną końcówkę fleksyjną.

Granica roli: to know-how trenerskie, nie porada medyczna. Parser
niczego nie ocenia i nie dobiera — porządkuje tekst, który człowiek i
tak przeczyta przed zapisem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .muscles import EXERCISE_LEVELS, MOVEMENT_PATTERNS, MUSCLE_KEYS, fold

# --- Proweniencja wpisu (migracja nr 22) -----------------------------------
#: Trener wypełnił tabelę ręcznie.
SOURCE_MANUAL = "MANUAL"
#: Tabela powstała z wklejonego opisu, silnikiem lokalnym.
SOURCE_TEXT_PARSED = "TEXT_PARSED"
#: Tabela powstała z wklejonego opisu, w trybie rozszerzonym.
SOURCE_AI_ASSISTED = "AI_ASSISTED"
#: Pozycja przyszła z importu gotowej biblioteki ćwiczeń (nie z opisu i nie
#: z ręki trenera) — patrz `import_exercises.py`. Nazwa konkretnej
#: biblioteki i data trafiają osobno do `exercises.source_ref`.
SOURCE_IMPORTED = "IMPORTED"
SOURCE_KINDS: tuple[str, ...] = (
    SOURCE_MANUAL, SOURCE_TEXT_PARSED, SOURCE_AI_ASSISTED, SOURCE_IMPORTED,
)

#: Nazwy silników (to samo słownictwo co OCR — nigdy nazwa dostawcy modelu).
ENGINE_LOCAL = "LOCAL"
ENGINE_EXTENDED = "EXTENDED"
ENGINES: tuple[str, ...] = (ENGINE_LOCAL, ENGINE_EXTENDED)

#: Twardy limit wejścia (opis dłuższy niż to i tak nie jest opisem jednego
#: ćwiczenia). Endpoint odrzuca dłuższy tekst zamiast go po cichu ucinać.
MAX_INPUT_CHARS = 20000

# --- Pola propozycji -------------------------------------------------------

FIELD_ORDER: tuple[str, ...] = (
    "name", "muscles_primary", "muscles_secondary", "level", "pattern",
    "equipment", "steps", "mistakes", "cues", "safety", "easier", "harder",
    "tempo_hint", "breathing", "benefit",
)

FIELD_LABELS: dict[str, str] = {
    "name": "nazwa",
    "muscles_primary": "mięśnie główne",
    "muscles_secondary": "mięśnie pomocnicze",
    "level": "poziom",
    "pattern": "wzorzec ruchu",
    "equipment": "sprzęt",
    "steps": "kroki techniki",
    "mistakes": "najczęstsze błędy",
    "cues": "wskazówki",
    "safety": "uwagi bezpieczeństwa",
    "easier": "wariant łatwiejszy",
    "harder": "wariant trudniejszy",
    "tempo_hint": "tempo",
    "breathing": "oddech",
    "benefit": "efekt",
}

LIST_FIELDS: frozenset[str] = frozenset(
    {"muscles_primary", "muscles_secondary", "steps", "mistakes", "cues"}
)

#: Limity zgodne z `schemas.ExerciseLibraryItemIn` — propozycja nie może
#: być dłuższa niż to, co da się potem zapisać.
_TEXT_LIMITS: dict[str, int] = {
    "name": 300, "equipment": 200, "safety": 2000, "easier": 1000,
    "harder": 1000, "tempo_hint": 200, "breathing": 400, "benefit": 2000,
}
_LIST_LIMITS: dict[str, tuple[int, int]] = {
    "muscles_primary": (12, 40), "muscles_secondary": (12, 40),
    "steps": (12, 600), "mistakes": (12, 400), "cues": (8, 300),
}


@dataclass(frozen=True)
class ParseResult:
    """Wynik jednego czytania opisu.

    ``proposal`` ma ZAWSZE komplet kluczy (puste pole = ``None`` albo pusta
    lista), żeby front nie musiał zgadywać, czego brakuje. ``unrecognized``
    wypisuje pola, których nie udało się odczytać — brak ma być widoczny,
    nie domyślny. ``needs_confirmation`` wypisuje pola odczytane, ale
    niepewne (np. podział na mięśnie główne/pomocnicze bez markera w
    tekście)."""

    proposal: dict
    unrecognized: list[str] = field(default_factory=list)
    needs_confirmation: list[str] = field(default_factory=list)


def empty_proposal() -> dict:
    """Propozycja bez ani jednego odczytanego pola (komplet kluczy)."""
    return {key: ([] if key in LIST_FIELDS else None) for key in FIELD_ORDER}


# ---------------------------------------------------------------------------
# Dopasowanie rdzeni (odporność na odmianę i polskie znaki).
# ---------------------------------------------------------------------------


def _phrase_regex(phrase: str) -> re.Pattern[str]:
    """Rdzeń → wyrażenie dopasowujące odmienioną formę.

    ``posladk`` trafia w „pośladki” i „pośladków”; ``biceps uda`` trafia w
    „bicepsy uda”. Lookbehind pilnuje początku wyrazu, więc ``rotacj`` nie
    trafia w środek „antyrotacja”, a ``zaawansowan`` — w środek
    „średniozaawansowany”."""
    words = [re.escape(w) for w in phrase.split()]
    core = r"[a-z]*[\s\-]+".join(words) + r"[a-z]*"
    return re.compile(r"(?<![a-z0-9])" + core)


_REGEX_CACHE: dict[str, re.Pattern[str]] = {}


def _rx(phrase: str) -> re.Pattern[str]:
    cached = _REGEX_CACHE.get(phrase)
    if cached is None:
        cached = _phrase_regex(phrase)
        _REGEX_CACHE[phrase] = cached
    return cached


def _mask(text: str, pattern: re.Pattern[str]) -> str:
    """Wycina dopasowanie z tekstu roboczego, ZACHOWUJĄC długość (pozycje
    pozostałych dopasowań muszą się zgadzać z oryginałem)."""
    return pattern.sub(lambda m: " " * (m.end() - m.start()), text)


def _find_terms(folded: str, terms: list[tuple[str, str]]) -> list[tuple[int, str]]:
    """Wszystkie trafienia słownika w tekście, posortowane po pozycji.

    Rdzenie dłuższe idą pierwsze i są wymazywane z tekstu roboczego, więc
    „biceps uda” nie rozpada się na „biceps”, a „trójgłowy łydki” — na
    „trójgłowy”. Kolejność wejścia nie ma znaczenia."""
    work = folded
    found: list[tuple[int, str]] = []
    for phrase, value in sorted(terms, key=lambda t: -len(t[0])):
        pattern = _rx(phrase)
        for match in pattern.finditer(work):
            found.append((match.start(), value))
        work = _mask(work, pattern)
    return sorted(found)


def _first_term(folded: str, terms: list[tuple[str, str]]) -> str | None:
    """Pierwsze trafienie w kolejności występowania w tekście (nazwa
    ćwiczenia stoi zwykle na początku, więc to ona rozstrzyga)."""
    hits = _find_terms(folded, terms)
    return hits[0][1] if hits else None


# ---------------------------------------------------------------------------
# SŁOWNIK SYNONIMÓW PARTII MIĘŚNIOWYCH (pełna kopia w docs/BAZA_CWICZEN.md).
# ---------------------------------------------------------------------------

MUSCLE_SYNONYMS: list[tuple[str, str]] = [
    # klatka piersiowa
    ("klatka piersiow", "KLATKA_PIERSIOWA"), ("klatk", "KLATKA_PIERSIOWA"),
    ("piersiow", "KLATKA_PIERSIOWA"), ("pectoral", "KLATKA_PIERSIOWA"),
    ("chest", "KLATKA_PIERSIOWA"),
    # najszerszy grzbietu
    ("najszersz", "NAJSZERSZY_GRZBIETU"), ("latissimus", "NAJSZERSZY_GRZBIETU"),
    ("plec", "NAJSZERSZY_GRZBIETU"),
    # czworoboczny
    ("czworoboczn", "CZWOROBOCZNY"), ("kaptur", "CZWOROBOCZNY"),
    ("trapez", "CZWOROBOCZNY"), ("trapezius", "CZWOROBOCZNY"),
    # równoległoboczne
    ("romboidaln", "ROMBOIDALNE"), ("rownolegloboczn", "ROMBOIDALNE"),
    ("rhomboid", "ROMBOIDALNE"), ("miedzylopatkow", "ROMBOIDALNE"),
    # prostowniki grzbietu
    ("prostownik grzbietu", "PROSTOWNIKI_GRZBIETU"),
    ("prostowniki plecow", "PROSTOWNIKI_GRZBIETU"),
    ("erector", "PROSTOWNIKI_GRZBIETU"),
    ("przykregoslupow", "PROSTOWNIKI_GRZBIETU"),
    # barki — WYŁĄCZNIE z określeniem aktonu (uzasadnienie w docs)
    ("bark przedni", "BARK_PRZEDNI"), ("przedni akton", "BARK_PRZEDNI"),
    ("akton przedni", "BARK_PRZEDNI"), ("naramienny przedni", "BARK_PRZEDNI"),
    ("przednia glowa barku", "BARK_PRZEDNI"),
    ("przedni bark", "BARK_PRZEDNI"),
    ("przednia czesc miesnia naramiennego", "BARK_PRZEDNI"),
    ("przednia czesc barkow", "BARK_PRZEDNI"),
    ("bark boczny", "BARK_BOCZNY"), ("boczny akton", "BARK_BOCZNY"),
    ("akton boczny", "BARK_BOCZNY"), ("naramienny boczny", "BARK_BOCZNY"),
    ("akton srodkowy", "BARK_BOCZNY"), ("srodkowy akton", "BARK_BOCZNY"),
    ("boczny bark", "BARK_BOCZNY"),
    ("boczna czesc miesnia naramiennego", "BARK_BOCZNY"),
    ("boczna czesc barkow", "BARK_BOCZNY"),
    ("bark tylny", "BARK_TYLNY"), ("tylny akton", "BARK_TYLNY"),
    ("akton tylny", "BARK_TYLNY"), ("naramienny tylny", "BARK_TYLNY"),
    ("tylna glowa barku", "BARK_TYLNY"),
    ("tylny bark", "BARK_TYLNY"),
    ("tylna czesc miesnia naramiennego", "BARK_TYLNY"),
    ("tylna czesc barkow", "BARK_TYLNY"),
    # ramiona
    ("biceps uda", "DWUGLOWY_UDA"),  # rozstrzygane przed samym „biceps”
    ("biceps", "BICEPS"), ("dwuglowy ramienia", "BICEPS"),
    ("dwuglowy ramion", "BICEPS"),
    ("triceps", "TRICEPS"), ("trojglowy ramienia", "TRICEPS"),
    ("trojglowy ramion", "TRICEPS"),
    ("przedrami", "PRZEDRAMIE"), ("forearm", "PRZEDRAMIE"),
    # przedramię — mięśnie nazwane wprost (wszystkie leżą na przedramieniu,
    # więc nie ma tu wyboru między kluczami; dodane przy imporcie
    # biblioteki V2, patrz docs/BAZA_CWICZEN.md §11).
    ("ramienno promieniow", "PRZEDRAMIE"),
    ("zginacz nadgarstka", "PRZEDRAMIE"), ("zginacze nadgarstkow", "PRZEDRAMIE"),
    ("prostownik nadgarstka", "PRZEDRAMIE"),
    ("prostowniki nadgarstkow", "PRZEDRAMIE"),
    ("zginacz palcow", "PRZEDRAMIE"), ("prostownik palcow", "PRZEDRAMIE"),
    ("miesnie chwytu", "PRZEDRAMIE"),
    # brzuch i głęboki gorset
    ("prosty brzucha", "BRZUCH_PROSTY"), ("brzuch prosty", "BRZUCH_PROSTY"),
    ("rectus abdominis", "BRZUCH_PROSTY"), ("brzuch", "BRZUCH_PROSTY"),
    ("brzuszn", "BRZUCH_PROSTY"),
    # „skośne brzucha” jako całe wyrażenie — dłuższy rdzeń jest dopasowywany
    # pierwszy i wymazuje „brzucha”, więc nie dokleja się BRZUCH_PROSTY.
    ("miesnie skosne brzucha", "BRZUCH_SKOSNY"),
    ("skosne brzucha", "BRZUCH_SKOSNY"),
    ("skosn", "BRZUCH_SKOSNY"), ("oblique", "BRZUCH_SKOSNY"),
    ("core", "MIESNIE_GLEBOKIE"), ("miesnie glebokie", "MIESNIE_GLEBOKIE"),
    ("glebokie", "MIESNIE_GLEBOKIE"), ("stabilizacj", "MIESNIE_GLEBOKIE"),
    ("stabilizator", "MIESNIE_GLEBOKIE"), ("poprzeczny brzucha", "MIESNIE_GLEBOKIE"),
    ("transversus", "MIESNIE_GLEBOKIE"), ("gorset", "MIESNIE_GLEBOKIE"),
    # biodra i nogi
    ("posladk", "POSLADKI"), ("gluteus", "POSLADKI"), ("glute", "POSLADKI"),
    ("czworoglow", "CZWOROGLOWY_UDA"), ("quadriceps", "CZWOROGLOWY_UDA"),
    ("quad", "CZWOROGLOWY_UDA"), ("przod uda", "CZWOROGLOWY_UDA"),
    ("przednia czesc uda", "CZWOROGLOWY_UDA"),
    ("dwuglowy uda", "DWUGLOWY_UDA"), ("hamstring", "DWUGLOWY_UDA"),
    ("tyl uda", "DWUGLOWY_UDA"), ("kulszowo goleniow", "DWUGLOWY_UDA"),
    ("tylna czesc uda", "DWUGLOWY_UDA"),
    ("przywodziciel", "PRZYWODZICIELE"), ("adductor", "PRZYWODZICIELE"),
    ("wewnetrzna czesc uda", "PRZYWODZICIELE"),
    ("odwodziciel", "ODWODZICIELE"), ("abductor", "ODWODZICIELE"),
    ("lydk", "LYDKA"), ("brzuchat", "LYDKA"), ("plaszczkowat", "LYDKA"),
    ("trojglowy lydki", "LYDKA"), ("calf", "LYDKA"),
    ("zginacz biodra", "ZGINACZE_BIODRA"), ("zginacze bioder", "ZGINACZE_BIODRA"),
    ("biodrowo ledzwiow", "ZGINACZE_BIODRA"), ("iliopsoas", "ZGINACZE_BIODRA"),
    ("psoas", "ZGINACZE_BIODRA"),
]

#: Wyrażenia, które NIGDY nie mają być mapowane, choć zawierają rdzeń z
#: powyższego słownika. Sprawdzane wyłącznie przez `map_muscle_phrase()`,
#: czyli przy mapowaniu POJEDYNCZEJ nazwy anatomicznej (import gotowej
#: biblioteki, gdzie kolumna „mięśnie” jest listą rozdzieloną średnikami) —
#: nie zmienia czytania ciągłego opisu przez `parse_description`.
#:
#: Uzasadnienie jest zawsze to samo: nazwa wskazuje na WIĘCEJ NIŻ JEDEN
#: klucz `MUSCLE_LABELS` i żaden z nich nie jest domyślny. „Górne plecy”
#: to czworoboczny i romboidalne, nie najszerszy; „barki” to trzy aktony;
#: „nogi” to pół dolnej połowy słownika. Zgadnięcie wyglądałoby w bazie
#: dokładnie tak samo jak wiedza trenera, więc nie zgadujemy.
AMBIGUOUS_MUSCLE_PHRASES: frozenset[str] = frozenset({
    "barki",
    "obrecz barkowa",
    "miesnie obreczy barkowej",
    "miesien naramienny",
    "naramienny",
    "gorne plecy",
    "plecy",
    "nogi",
    "miesnie lopatki",
    "miesnie stabilizujace biodro",
})


def map_muscle_phrase(phrase: str) -> list[str]:
    """Pojedyncza nazwa anatomiczna → klucze `MUSCLE_LABELS` (może być
    pusta lista).

    Używane przy imporcie gotowych bibliotek, gdzie mięśnie przychodzą
    jako lista nazw („mięsień piersiowy większy”, „przednia część mięśnia
    naramiennego”), a nie jako zdanie. Pusta lista znaczy „nie
    rozpoznano” i ma trafić do raportu importu — nigdy do najbliższego
    klucza."""
    folded = fold(phrase).replace("—", " ").replace("–", " ")
    folded = " ".join(folded.replace("­", "").split())
    if not folded or folded in AMBIGUOUS_MUSCLE_PHRASES:
        return []
    hits = [value for _, value in _find_terms(folded, MUSCLE_SYNONYMS)]
    return list(dict.fromkeys(hits))


#: Markery podziału na mięśnie główne i pomocnicze.
PRIMARY_MARKERS: tuple[str, ...] = (
    "miesnie glowne", "glowne miesnie", "miesnie docelowe", "partie glowne",
    "pracuja glownie", "pracuje glownie", "angazuje glownie", "glownie pracuja",
    "glownie angazuje", "przede wszystkim", "miesnie pierwszorzedowe",
)
SECONDARY_MARKERS: tuple[str, ...] = (
    "miesnie pomocnicze", "pomocnicze miesnie", "miesnie wspomagajace",
    "wspomagajaco", "wspomagajace", "pomocniczo", "dodatkowo angazuje",
    "dodatkowo pracuja", "dodatkowo angazowane", "stabilizujaco", "wtornie",
    "miesnie drugorzedowe", "drugorzedowe",
)

# --- Sprzęt ---------------------------------------------------------------

EQUIPMENT_TERMS: list[tuple[str, str]] = [
    ("masa wlasna ciala", "masa własna ciała"),
    ("ciezar wlasnego ciala", "masa własna ciała"),
    ("wlasny ciezar ciala", "masa własna ciała"),
    ("bez sprzetu", "masa własna ciała"),
    ("bodyweight", "masa własna ciała"),
    ("sztang", "sztanga"),
    ("hantl", "hantle"),
    ("kettlebell", "kettlebell"),
    ("odwaznik kulowy", "kettlebell"),
    ("guma oporow", "guma oporowa"),
    ("tasma oporow", "guma oporowa"),
    ("gum", "guma oporowa"),
    ("maszyn", "maszyna"),
    ("wyciag", "wyciąg"),
    ("drazek", "drążek"),
    ("lawk", "ławka"),
    ("lawc", "ławka"),
    ("trx", "TRX"),
    ("orbitrek", "orbitrek"),
    ("biezni", "bieżnia"),
    ("rower", "rower"),
    ("pilka lekarsk", "piłka lekarska"),
    ("skrzyni", "skrzynia"),
]

# --- Poziom i wzorzec ruchu ------------------------------------------------

#: ŚWIADOMIE wąski słownik. „Podstawowe ćwiczenie” i „łatwe” mówią o randze
#: albo o odczuciu, nie o poziomie zaawansowania klienta — wpisanie ich tu
#: kosztowałoby błędny poziom w co drugim opisie. Rozpoznajemy wyłącznie
#: słowa, które są nazwą poziomu wprost.
LEVEL_TERMS: list[tuple[str, str]] = [
    ("sredniozaawansowan", "SREDNIOZAAWANSOWANY"),
    ("srednio zaawansowan", "SREDNIOZAAWANSOWANY"),
    ("sredni poziom", "SREDNIOZAAWANSOWANY"),
    ("zaawansowan", "ZAAWANSOWANY"),
    ("poczatkujac", "POCZATKUJACY"),
]

PATTERN_TERMS: list[tuple[str, str]] = [
    ("zawias biodrow", "ZAWIAS_BIODROWY"), ("martwy ciag", "ZAWIAS_BIODROWY"),
    ("hip hinge", "ZAWIAS_BIODROWY"), ("zawias", "ZAWIAS_BIODROWY"),
    ("przysiad", "PRZYSIAD"),
    ("pompk", "WYPYCHANIE_POZIOME"), ("wypychanie poziome", "WYPYCHANIE_POZIOME"),
    ("wypychanie pionowe", "WYPYCHANIE_PIONOWE"),
    ("wioslowanie", "PRZYCIAGANIE_POZIOME"),
    ("przyciaganie poziome", "PRZYCIAGANIE_POZIOME"),
    ("podciagani", "PRZYCIAGANIE_PIONOWE"),
    ("sciaganie drazka", "PRZYCIAGANIE_PIONOWE"),
    ("przyciaganie pionowe", "PRZYCIAGANIE_PIONOWE"),
    ("wykrok", "WYKROK"), ("zakrok", "WYKROK"), ("wypad", "WYKROK"),
    ("spacer farmera", "NOSZENIE"), ("noszenie", "NOSZENIE"),
    ("antyrotacj", "ANTYROTACJA"), ("pallof", "ANTYROTACJA"),
    ("rotacj", "ROTACJA"), ("skret tulowia", "ROTACJA"),
    ("izolacj", "IZOLACJA"), ("izolowan", "IZOLACJA"),
    ("cardio", "CARDIO"), ("wytrzymalosc tlenow", "CARDIO"),
    ("mobilnosc", "MOBILNOSC"), ("mobilizacj", "MOBILNOSC"),
    ("rozciagani", "MOBILNOSC"),
]

#: Wzorce, których nie da się rozpoznać po jednym słowie: „wyciskanie”
#: bywa poziome i pionowe, więc rozstrzyga dopiero drugi rdzeń w tekście.
PATTERN_PAIRS: list[tuple[tuple[str, str], str]] = [
    (("wyciskanie", "lezac"), "WYPYCHANIE_POZIOME"),
    (("wyciskanie", "lawk"), "WYPYCHANIE_POZIOME"),
    (("wyciskanie", "lawc"), "WYPYCHANIE_POZIOME"),
    (("wyciskanie", "nad glowe"), "WYPYCHANIE_PIONOWE"),
    (("wyciskanie", "zolniersk"), "WYPYCHANIE_PIONOWE"),
    (("wyciskanie", "gore"), "WYPYCHANIE_PIONOWE"),
]


def _assert_dictionaries() -> None:
    """Kontrakt: żaden słownik nie ma prawa wskazać wartości spoza
    `muscles.py`. Sprawdzane przy imporcie i osobnym testem — nowy synonim
    z literówką w kluczu ma się wysypać od razu, nie po cichu."""
    unknown_muscles = {key for _, key in MUSCLE_SYNONYMS} - MUSCLE_KEYS
    unknown_levels = {value for _, value in LEVEL_TERMS} - set(EXERCISE_LEVELS)
    unknown_patterns = (
        {value for _, value in PATTERN_TERMS} | {value for _, value in PATTERN_PAIRS}
    ) - set(MOVEMENT_PATTERNS)
    # Lista wyrażeń dwuznacznych działa przez porównanie do postaci
    # znormalizowanej — wpis z polskim znakiem nigdy by nie zadziałał.
    unfolded = {p for p in AMBIGUOUS_MUSCLE_PHRASES if fold(p) != p}
    if unfolded:
        raise RuntimeError(
            "Wyrażenia dwuznaczne muszą być zapisane bez polskich znaków: "
            f"{sorted(unfolded)}"
        )
    if unknown_muscles or unknown_levels or unknown_patterns:
        raise RuntimeError(
            "Słownik parsera wskazuje wartości spoza kontraktu: "
            f"{sorted(unknown_muscles | unknown_levels | unknown_patterns)}"
        )


_assert_dictionaries()

# ---------------------------------------------------------------------------
# Nagłówki sekcji.
# ---------------------------------------------------------------------------

#: (rdzeń nagłówka, klucz sekcji). Kolejność wpisów jest tu wyłącznie dla
#: czytelności — dopasowanie idzie od najdłuższego rdzenia.
SECTION_HEADERS: list[tuple[str, str]] = [
    ("technika wykonania", "steps"), ("sposob wykonania", "steps"),
    ("opis techniki", "steps"), ("jak wykonac", "steps"),
    ("wykonanie", "steps"), ("technika", "steps"), ("przebieg", "steps"),
    ("kroki", "steps"),
    ("najczestsze bledy", "mistakes"), ("typowe bledy", "mistakes"),
    ("czego unikac", "mistakes"), ("uwaga na", "mistakes"), ("bledy", "mistakes"),
    ("wskazowki", "cues"), ("wskazowka", "cues"), ("cues", "cues"), ("cue", "cues"),
    ("uwagi bezpieczenstwa", "safety"), ("bezpieczenstwo", "safety"),
    ("przeciwwskazania", "safety"), ("uwaga", "safety"),
    ("wariant latwiejszy", "easier"), ("latwiejszy wariant", "easier"),
    ("latwiejsza wersja", "easier"), ("regresja", "easier"), ("latwiejszy", "easier"),
    ("wariant trudniejszy", "harder"), ("trudniejszy wariant", "harder"),
    ("trudniejsza wersja", "harder"), ("progresja", "harder"),
    ("trudniejszy", "harder"),
    ("tempo", "tempo_hint"),
    ("oddychanie", "breathing"), ("oddech", "breathing"),
    ("potrzebny sprzet", "equipment"), ("wyposazenie", "equipment"),
    ("sprzet", "equipment"),
    ("pracujace miesnie", "muscles"), ("miesnie zaangazowane", "muscles"),
    ("zaangazowane miesnie", "muscles"), ("partie miesniowe", "muscles"),
    ("miesnie", "muscles"),
    ("poziom trudnosci", "level"), ("zaawansowanie", "level"), ("poziom", "level"),
    ("wzorzec ruchu", "pattern"), ("schemat ruchu", "pattern"), ("wzorzec", "pattern"),
    ("cel cwiczenia", "benefit"), ("co to daje", "benefit"),
    ("korzysci", "benefit"), ("efekt", "benefit"),
    ("nazwa cwiczenia", "name"), ("nazwa", "name"), ("cwiczenie", "name"),
]

_BULLET_RE = re.compile(r"^\s*(?:[-–—*•·>]+|\(?\d{1,2}[.)])\s+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
_TEMPO_SEPARATED = re.compile(r"\b\d\s*[-/]\s*\d\s*[-/]\s*\d\s*[-/]\s*\d\b")
_TEMPO_COMPACT = re.compile(r"\b\d{4}\b")
_HAS_LETTER = re.compile(r"[a-ząćęłńóśżź]", re.IGNORECASE)


@dataclass(frozen=True)
class _Block:
    """Fragment tekstu przypisany do jednej sekcji (albo do nagłówka
    dokumentu, gdy ``key`` jest ``None``)."""

    key: str | None
    start: int          # indeks pierwszej linii (z nagłówkiem włącznie)
    end: int            # indeks za ostatnią linią
    inline: str = ""    # treść z tej samej linii, po dwukropku


def _strip_bullet(line: str) -> str:
    return _BULLET_RE.sub("", line).strip()


def _header_of(line: str) -> tuple[str, str] | None:
    """Czy linia jest nagłówkiem sekcji → (klucz sekcji, treść po dwukropku).

    Nagłówkiem jest linia będąca WYŁĄCZNIE nazwą sekcji („Wykonanie”,
    „- Najczęstsze błędy”) albo nazwą zakończoną dwukropkiem („Tempo: 3010”).
    Zwykłe zdanie, w którym słowo „tempo” po prostu występuje, nagłówkiem
    nie jest — inaczej opis rozsypałby się na przypadkowe sekcje."""
    bare = _strip_bullet(line)
    if not bare:
        return None
    folded = fold(bare)
    for phrase, key in sorted(SECTION_HEADERS, key=lambda t: -len(t[0])):
        match = _rx(phrase).match(folded)
        if match is None:
            continue
        rest = bare[match.end():].lstrip()
        if rest.startswith((":", "-", "–", "—")):
            return key, rest[1:].strip()
        if not rest.strip(" .:;)—–-"):
            return key, ""
    return None


def _blocks(lines: list[str]) -> list[_Block]:
    """Podział tekstu na bloki sekcji. Linie przed pierwszym nagłówkiem
    tworzą blok bez klucza (nagłówek dokumentu — zwykle nazwa ćwiczenia)."""
    found: list[_Block] = []
    starts: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        header = _header_of(line)
        if header is not None:
            starts.append((index, header[0], header[1]))
    if not starts or starts[0][0] > 0:
        head_end = starts[0][0] if starts else len(lines)
        found.append(_Block(None, 0, head_end))
    for position, (index, key, inline) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        found.append(_Block(key, index, end, inline))
    return found


def _content(lines: list[str], block: _Block) -> list[str]:
    """Treść bloku: to, co po dwukropku w nagłówku, plus kolejne linie."""
    out: list[str] = []
    if block.inline:
        out.append(block.inline)
    out.extend(line for line in lines[block.start + 1:block.end] if line.strip())
    return out


def _items(content: list[str], *, limit: int, max_len: int) -> list[str]:
    """Treść sekcji → lista pozycji.

    Lista punktowana lub numerowana daje jedną pozycję na punkt (linia
    ciągnąca się dalej dokleja się do poprzedniego punktu). Zwykły akapit
    dzielimy na zdania — nie zgadujemy przy tym niczego, tylko odtwarzamy
    granice, które postawił autor."""
    bulleted = [line for line in content if _BULLET_RE.match(line)]
    items: list[str] = []
    if bulleted:
        for line in content:
            if _BULLET_RE.match(line):
                items.append(_strip_bullet(line))
            elif items:
                items[-1] = f"{items[-1]} {line.strip()}".strip()
    else:
        for line in content:
            items.extend(part.strip() for part in _SENTENCE_SPLIT.split(line.strip()))
    cleaned = [item.strip(" .;–—-") for item in items]
    return [i[:max_len] for i in cleaned if len(i) >= 3 and _HAS_LETTER.search(i)][:limit]


def _sentences(raw: str) -> list[str]:
    out: list[str] = []
    for line in raw.split("\n"):
        out.extend(part.strip() for part in _SENTENCE_SPLIT.split(line.strip()) if part.strip())
    return out


def _text_value(content: list[str], limit: int) -> str | None:
    joined = " ".join(part.strip() for part in content if part.strip()).strip()
    return joined[:limit] if joined and _HAS_LETTER.search(joined) else None


# ---------------------------------------------------------------------------
# Mięśnie: podział na główne i pomocnicze po markerach w tekście.
# ---------------------------------------------------------------------------


def split_muscles_by_markers(text: str) -> tuple[list[str], list[str], bool]:
    """Rozpoznane partie mięśniowe z podziałem na główne i pomocnicze.

    Zwraca ``(glowne, pomocnicze, marker_pomocniczych_byl)``. Bez markera
    („wspomagająco”, „pomocniczo”, „dodatkowo angażuje”) WSZYSTKO trafia do
    głównych — bo tak jest w tekście — a wołający oznacza podział jako
    wymagający potwierdzenia. Dzielenie „na oko” (np. dwa pierwsze mięśnie
    główne, reszta pomocnicze) byłoby zgadywaniem."""
    folded = fold(text)
    markers: list[tuple[int, str]] = []
    for phrase in PRIMARY_MARKERS:
        markers.extend((m.start(), "primary") for m in _rx(phrase).finditer(folded))
    for phrase in SECONDARY_MARKERS:
        markers.extend((m.start(), "secondary") for m in _rx(phrase).finditer(folded))
    markers.sort()
    has_secondary_marker = any(role == "secondary" for _, role in markers)

    primary: list[str] = []
    secondary: list[str] = []
    for position, key in _find_terms(folded, MUSCLE_SYNONYMS):
        role = "primary"
        for marker_pos, marker_role in markers:
            if marker_pos > position:
                break
            role = marker_role
        bucket = primary if role == "primary" else secondary
        if key not in bucket:
            bucket.append(key)
    # Ten sam mięsień nie może być jednocześnie główny i pomocniczy —
    # wygrywa pierwsze (mocniejsze) wskazanie w tekście.
    secondary = [key for key in secondary if key not in primary]
    return primary, secondary, has_secondary_marker


# ---------------------------------------------------------------------------
# Główna funkcja.
# ---------------------------------------------------------------------------


def parse_description(text: str) -> ParseResult:
    """Czyta wklejony opis ćwiczenia i zwraca propozycję pól edytora.

    Funkcja jest czysta (bez we/wy i bez bazy), więc daje się uruchomić na
    dowolnym tekście — również na wyniku przepisania zdjęcia (OCR).
    Tekst bez sensu daje pustą propozycję i pełną listę pól nieodczytanych,
    nigdy wyjątku."""
    proposal = empty_proposal()
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in raw.split("\n")]
    folded_all = fold(raw)
    blocks = _blocks(lines)
    by_key: dict[str, list[_Block]] = {}
    for block in blocks:
        if block.key is not None:
            by_key.setdefault(block.key, []).append(block)

    def section(key: str) -> list[str]:
        out: list[str] = []
        for block in by_key.get(key, []):
            out.extend(_content(lines, block))
        return out

    needs_confirmation: list[str] = []
    head = next((b for b in blocks if b.key is None), None)

    # --- nazwa -------------------------------------------------------------
    named = _text_value(section("name"), _TEXT_LIMITS["name"])
    if named:
        proposal["name"] = named
    elif head is not None:
        # Tylko PIERWSZA niepusta linia opisu — tytuł stoi na górze. Piąta
        # linia akapitu nie staje się nazwą tylko dlatego, że jest krótka.
        first = next((_strip_bullet(x) for x in lines[head.start:head.end] if x.strip()), "")
        if _is_title_line(first):
            proposal["name"] = first
            needs_confirmation.append("name")

    # --- mięśnie -----------------------------------------------------------
    muscle_blocks = by_key.get("muscles", [])
    region = (
        "\n".join("\n".join(lines[b.start:b.end]) for b in muscle_blocks)
        if muscle_blocks
        else raw
    )
    primary, secondary, marked = split_muscles_by_markers(region)
    limit_muscles, _ = _LIST_LIMITS["muscles_primary"]
    proposal["muscles_primary"] = primary[:limit_muscles]
    proposal["muscles_secondary"] = secondary[:limit_muscles]
    if primary and not marked:
        needs_confirmation.extend(["muscles_primary", "muscles_secondary"])

    # --- poziom i wzorzec ruchu -------------------------------------------
    level_text = _text_value(section("level"), 400)
    level = _first_term(fold(level_text), LEVEL_TERMS) if level_text else None
    proposal["level"] = level or _first_term(folded_all, LEVEL_TERMS)

    pattern_text = _text_value(section("pattern"), 400)
    pattern = _pattern_from(fold(pattern_text)) if pattern_text else None
    proposal["pattern"] = pattern or _pattern_from(folded_all)

    # --- sprzęt ------------------------------------------------------------
    equipment_text = _text_value(section("equipment"), 400)
    labels: list[str] = []
    for _, label in _find_terms(fold(equipment_text or raw), EQUIPMENT_TERMS):
        if label not in labels:
            labels.append(label)
    if labels:
        proposal["equipment"] = ", ".join(labels)[:_TEXT_LIMITS["equipment"]]

    # --- listy: kroki, błędy, wskazówki ------------------------------------
    step_content = section("steps")
    if not step_content and head is not None:
        # Bez sekcji „wykonanie/technika” bierzemy wyłącznie jawną listę
        # punktowaną spoza innych sekcji — zdania z ciągłego akapitu nie są
        # krokami techniki tylko dlatego, że są zdaniami.
        step_content = [
            line for line in lines[head.start:head.end] if _BULLET_RE.match(line)
        ]
    for key, content in (
        ("steps", step_content),
        ("mistakes", section("mistakes")),
        ("cues", section("cues")),
    ):
        limit, max_len = _LIST_LIMITS[key]
        proposal[key] = _items(content, limit=limit, max_len=max_len)

    # --- pola tekstowe -----------------------------------------------------
    proposal["safety"] = _text_value(section("safety"), _TEXT_LIMITS["safety"]) or (
        _sentences_with(raw, ("przeciwwskazan", "przy bolu", "nie wykonuj"),
                        _TEXT_LIMITS["safety"])
    )
    proposal["easier"] = _text_value(section("easier"), _TEXT_LIMITS["easier"]) or (
        _sentences_with(raw, ("latwiejsz", "regresj"), _TEXT_LIMITS["easier"])
    )
    proposal["harder"] = _text_value(section("harder"), _TEXT_LIMITS["harder"]) or (
        _sentences_with(raw, ("trudniejsz", "progresj"), _TEXT_LIMITS["harder"])
    )
    proposal["breathing"] = _text_value(
        section("breathing"), _TEXT_LIMITS["breathing"]
    ) or _sentences_with(raw, ("wdech", "wydech", "oddech"), _TEXT_LIMITS["breathing"])
    proposal["benefit"] = _text_value(section("benefit"), _TEXT_LIMITS["benefit"])
    proposal["tempo_hint"] = _tempo(section("tempo_hint"), raw, folded_all)

    uncertain = [key for key in FIELD_ORDER if key in needs_confirmation]
    return ParseResult(
        proposal=proposal,
        # Pole jest ALBO nieodczytane, ALBO odczytane i niepewne — nigdy
        # jedno i drugie naraz (człowiek dostaje dwie rozłączne listy).
        unrecognized=[k for k in unrecognized_fields(proposal) if k not in uncertain],
        needs_confirmation=uncertain,
    )


def _is_title_line(candidate: str) -> bool:
    """Czy linia nadaje się na nazwę ćwiczenia.

    Nazwa to krótka linia tytułowa, a nie pierwsze zdanie akapitu — kropka
    kończąca zdanie dyskwalifikuje kandydata. W tekście ciągłym bez
    nagłówków nazwa po prostu zostaje nieodczytana (znane ograniczenie
    trybu lokalnego, docs/BAZA_CWICZEN.md)."""
    if not (3 <= len(candidate) <= 120) or not _HAS_LETTER.search(candidate):
        return False
    return not candidate.endswith(".") and ". " not in candidate


def _pattern_from(folded: str) -> str | None:
    """Wzorzec ruchu: najpierw pary rdzeni (rozstrzygają „wyciskanie”),
    potem pojedyncze rdzenie w kolejności występowania."""
    for (first, second), value in PATTERN_PAIRS:
        if _rx(first).search(folded) and _rx(second).search(folded):
            return value
    return _first_term(folded, PATTERN_TERMS)


def _sentences_with(raw: str, stems: tuple[str, ...], limit: int) -> str | None:
    """Zdania zawierające którykolwiek z rdzeni — awaryjne czytanie pola,
    gdy w tekście nie ma nagłówka sekcji. Maksymalnie dwa zdania: dłuższy
    fragment znaczy, że opis nie jest podzielony i lepiej zostawić pole
    puste, niż wkleić do niego pół tekstu."""
    hits = [
        sentence for sentence in _sentences(raw)
        if any(_rx(stem).search(fold(sentence)) for stem in stems)
    ]
    if not hits or len(hits) > 2:
        return None
    return " ".join(hits)[:limit]


def _tempo(content: list[str], raw: str, folded: str) -> str | None:
    """Tempo: zapis czterocyfrowy (``3010``) albo rozdzielony (``3-0-1-0``).

    Sam czterocyfrowy ciąg bez słowa „tempo” w tekście jest odrzucany —
    „2026” w notatce nie jest tempem."""
    for source in (" ".join(content), raw if _rx("tempo").search(folded) else ""):
        if not source:
            continue
        match = _TEMPO_SEPARATED.search(source) or _TEMPO_COMPACT.search(source)
        if match:
            return re.sub(r"\s+", "", match.group(0))[:_TEXT_LIMITS["tempo_hint"]]
    match = _TEMPO_SEPARATED.search(raw)
    return re.sub(r"\s+", "", match.group(0)) if match else None


# ---------------------------------------------------------------------------
# Walidacja propozycji z DOWOLNEGO silnika (lokalnego i rozszerzonego).
# ---------------------------------------------------------------------------


def clamp_proposal(raw: dict) -> dict:
    """Przycina propozycję do kontraktu edytora ćwiczeń.

    Wartość spoza słownika (mięsień, poziom, wzorzec) nie jest „naprawiana”
    — pole po prostu zostaje puste. Ta sama funkcja pilnuje wyniku silnika
    lokalnego i modelu, więc nie ma drogi na skróty dla żadnego z nich."""
    out = empty_proposal()
    for key, limit in _TEXT_LIMITS.items():
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()[:limit]
    for key, (count, max_len) in _LIST_LIMITS.items():
        value = raw.get(key)
        if not isinstance(value, list):
            continue
        items = [v.strip()[:max_len] for v in value if isinstance(v, str) and v.strip()]
        if key in ("muscles_primary", "muscles_secondary"):
            items = [v for v in items if v in MUSCLE_KEYS]
        unique: list[str] = []
        for item in items:
            if item not in unique:
                unique.append(item)
        out[key] = unique[:count]
    out["muscles_secondary"] = [
        key for key in out["muscles_secondary"] if key not in out["muscles_primary"]
    ]
    level = raw.get("level")
    out["level"] = level if level in EXERCISE_LEVELS else None
    pattern = raw.get("pattern")
    out["pattern"] = pattern if pattern in MOVEMENT_PATTERNS else None
    return out


def unrecognized_fields(proposal: dict) -> list[str]:
    """Które pola propozycji zostały puste (kolejność jak w edytorze)."""
    return [key for key in FIELD_ORDER if not proposal.get(key)]

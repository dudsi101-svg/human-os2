"""Deterministyczny scenariusz konwersacyjnego onboardingu.

To jest SERCE funkcji i jedyne miejsce, które decyduje, o co i w jakiej
kolejności aplikacja pyta. Model językowy nie prowadzi rozmowy — może
najwyżej przygotować wersję roboczą podsumowania (`onboarding_ai.py`).
Dzięki temu cała rozmowa działa identycznie z modelem i bez modelu
(tryb formularza jest ścieżką domyślną, nie okrojoną awaryjną).

Zasady (Konstytucja Human OS + docs/ONBOARDING_AI.md):

* jeden krok = jedno zagadnienie (nigdy ściana pytań),
* każde pytanie mówi wprost, PO CO jest zadawane (`why`),
* każde pytanie można pominąć — pominięcie jest zapisywane jawnie,
  a nie udawane pustą odpowiedzią,
* pytania o dane wrażliwe pojawiają się WYŁĄCZNIE wtedy, gdy są
  potrzebne i gdy klient ma aktywną zgodę odpowiedniej kategorii
  (`consent_domain`); bez zgody krok w ogóle nie powstaje,
* reguły adaptacji (`_TRIGGERS`) są deterministyczne i serwerowe —
  brak sprzętu odsłania pytania o warianty domowe, zgłoszony uraz
  odsłania doprecyzowanie ograniczeń,
* objawy alarmowe (`SAFETY_SIGNALS`) rozpoznaje lista słów kluczowych,
  a nie model: aplikacja NICZEGO nie ocenia ani nie diagnozuje —
  pokazuje spokojny komunikat kierujący do pomocy medycznej.

Suplementacja: rozmowa zbiera wyłącznie DEKLARACJĘ klienta o tym, co
przyjmuje. Planu suplementacji nie tworzy ani aplikacja, ani model —
robi to człowiek w wersji planu diety (`schemas.SupplementIn`).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .authz import DOMAIN_HEALTH, DOMAIN_NUTRITION

# Rodzaje kroków rozmowy (kontrakt dla frontendu).
KIND_TEXT = "TEXT"
KIND_LONGTEXT = "LONGTEXT"
KIND_CHOICE = "CHOICE"
KIND_MULTI = "MULTI"
KIND_SCALE = "SCALE"
KIND_BOOL = "BOOL"
KIND_INFO = "INFO"

WEEKDAY_OPTIONS = ("Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd")


@dataclass(frozen=True)
class Step:
    """Jeden krok rozmowy = jedno zagadnienie."""

    id: str
    topic: str
    question: str
    why: str
    kind: str
    options: tuple[str, ...] = ()
    placeholder: str = ""
    # Dane szczególnej kategorii (art. 9 RODO) — zapisywane jako pole
    # wrażliwe profilu i widoczne dla trenera tylko w zakresie zgody.
    sensitive: bool = False
    # Domena zgody, bez której krok W OGÓLE nie jest zadawany.
    consent_domain: str | None = None
    # Docelowy klucz pola profilu (None = krok nie zasila profilu).
    profile_field: str | None = None
    # Czy odpowiedź przechodzi przez listę objawów alarmowych.
    scan_safety: bool = False
    # Krok warunkowy — pojawia się dopiero, gdy reguła adaptacji go odsłoni.
    conditional: bool = False
    max_len: int = 1000
    # Odpowiedzi wyboru, które podnoszą flagę bezpieczeństwa sesji (ten sam
    # mechanizm co `scan_safety`, tylko dla kroków CHOICE/BOOL/MULTI —
    # np. przesiew przed wysiłkiem w głębokim wywiadzie). Pusta krotka =
    # krok nie flaguje niczego.
    flag_options: tuple[str, ...] = ()


STEPS: tuple[Step, ...] = (
    Step(
        id="cel_glowny",
        topic="Cel",
        question="Od czego zaczniemy — co chcesz osiągnąć?",
        why="Cel decyduje o wszystkim, co dalej: doborze planu, tempie "
        "i tym, co uznamy za postęp. Bez niego trener zgaduje.",
        kind=KIND_TEXT,
        placeholder="np. wrócić do formy po przerwie; zrzucić 6 kg do wakacji",
        profile_field="cel_glowny",
        max_len=300,
    ),
    Step(
        id="cel_termin",
        topic="Cel",
        question="Masz jakiś termin albo wydarzenie, na które celujesz?",
        why="Termin zmienia tempo planu. Jeśli go nie ma, plan może być "
        "spokojniejszy i trwalszy — to też dobra odpowiedź.",
        kind=KIND_TEXT,
        placeholder="np. wesele 2026-09-12; bez terminu",
        profile_field="cel_termin",
        max_len=200,
    ),
    Step(
        id="doswiadczenie",
        topic="Doświadczenie treningowe",
        question="Jak wygląda Twoje doświadczenie z treningiem?",
        why="Od tego zależy złożoność ćwiczeń i ile instruktażu warto "
        "dołożyć do planu.",
        kind=KIND_CHOICE,
        options=(
            "Zaczynam od zera",
            "Trenowałem(-am) kiedyś, wracam po przerwie",
            "Trenuję regularnie do 2 lat",
            "Trenuję regularnie ponad 2 lata",
        ),
        profile_field="doswiadczenie",
        max_len=100,
    ),
    Step(
        id="technika_wsparcie",
        topic="Doświadczenie treningowe",
        question="Chcesz, żeby plan zawierał więcej instruktażu techniki?",
        why="Na starcie technika jest ważniejsza niż ciężar. Jeśli "
        "wolisz krótkie opisy — też tak zapiszemy.",
        kind=KIND_CHOICE,
        options=(
            "Tak, chcę dużo wyjaśnień i nagrań",
            "Wystarczą krótkie wskazówki",
            "Nie potrzebuję — znam ćwiczenia",
        ),
        profile_field="wsparcie_techniki",
        conditional=True,
        max_len=100,
    ),
    Step(
        id="dostepnosc",
        topic="Dostępność",
        question="Ile dni w tygodniu realnie możesz trenować?",
        why="Plan ma pasować do Twojego tygodnia, nie odwrotnie. Lepiej "
        "zaplanować mniej i wykonać, niż zaplanować dużo i odpuścić.",
        kind=KIND_CHOICE,
        options=("1 dzień", "2 dni", "3 dni", "4 dni", "5 dni", "6-7 dni"),
        profile_field="dostepnosc_tygodniowa",
        max_len=40,
    ),
    Step(
        id="preferowane_dni",
        topic="Preferowane dni",
        question="W które dni najłatwiej Ci trenować?",
        why="Harmonogram wpisany w Twoje realne dni jest po prostu "
        "wykonalny. Możesz zaznaczyć więcej dni niż zamierzasz trenować.",
        kind=KIND_MULTI,
        options=WEEKDAY_OPTIONS,
        profile_field="dni_treningowe",
        max_len=60,
    ),
    Step(
        id="preferowane_godziny",
        topic="Preferowane godziny",
        question="O jakiej porze dnia zwykle dasz radę?",
        why="Pora treningu wpływa na przypomnienia i na to, jak "
        "rozłożymy trudniejsze jednostki w tygodniu.",
        kind=KIND_CHOICE,
        options=(
            "Rano (przed pracą)",
            "W ciągu dnia",
            "Popołudniu",
            "Wieczorem",
            "Różnie — zależy od tygodnia",
        ),
        profile_field="pora_treningu",
        max_len=80,
    ),
    Step(
        id="sprzet",
        topic="Sprzęt",
        question="Gdzie i na czym będziesz trenować?",
        why="Plan bez dostępnego sprzętu jest planem na papierze. "
        "Dopasujemy ćwiczenia do tego, co masz pod ręką.",
        kind=KIND_CHOICE,
        options=(
            "Siłownia komercyjna",
            "Mała siłownia / klub osiedlowy",
            "Dom — mam sprzęt (hantle, gumy, drążek)",
            "Dom — bez sprzętu, tylko masa ciała",
            "Na zewnątrz (park, plac zabaw, bieganie)",
        ),
        profile_field="sprzet",
        max_len=120,
    ),
    Step(
        id="warianty_domowe",
        topic="Sprzęt",
        question="Co dokładnie masz w domu albo w okolicy do dyspozycji?",
        why="Skoro trenujesz poza siłownią, potrzebujemy listy tego, co "
        "faktycznie jest — wtedy plan nie będzie zawierał ćwiczeń, "
        "których nie masz jak wykonać.",
        kind=KIND_LONGTEXT,
        placeholder="np. dwie gumy oporowe, krzesło, drążek w drzwiach, "
        "park 5 minut od domu",
        profile_field="sprzet_domowy",
        conditional=True,
        max_len=800,
    ),
    Step(
        id="ograniczenia",
        topic="Ograniczenia",
        question="Co najczęściej staje Ci na drodze do treningu?",
        why="Znając realne przeszkody (praca zmianowa, dojazdy, dzieci) "
        "trener zaplanuje krótsze jednostki albo inne dni — zamiast "
        "planu, który wygląda dobrze tylko na papierze.",
        kind=KIND_LONGTEXT,
        placeholder="np. praca zmianowa co drugi tydzień; dojazd 40 minut",
        profile_field="ograniczenia_organizacyjne",
        max_len=800,
    ),
    Step(
        id="urazy_czy",
        topic="Urazy",
        question="Czy masz przebyte urazy albo dolegliwości, o których "
        "trener powinien wiedzieć?",
        why="Trener nie jest lekarzem i niczego nie leczy — ale musi "
        "wiedzieć, czego unikać, żeby plan Ci nie zaszkodził. Jeśli "
        "wolisz o tym nie pisać, pomiń to pytanie.",
        kind=KIND_BOOL,
        options=("Tak", "Nie"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="urazy_deklaracja",
        max_len=20,
    ),
    Step(
        id="urazy_opis",
        topic="Urazy",
        question="Opisz krótko, czego dotyczą — bez diagnoz, po prostu "
        "własnymi słowami.",
        why="Trener potrzebuje wiedzieć, która okolica ciała wymaga "
        "ostrożności. To nie jest wywiad medyczny i nie zastępuje wizyty "
        "u lekarza ani fizjoterapeuty.",
        kind=KIND_LONGTEXT,
        placeholder="np. bark prawy — po zwichnięciu 2 lata temu",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="urazy",
        scan_safety=True,
        conditional=True,
        max_len=1500,
    ),
    Step(
        id="urazy_ograniczenia",
        topic="Urazy",
        question="Czego w związku z tym wolisz nie robić na treningu?",
        why="To Twoja decyzja, nie nasza. Wpisujemy ją do profilu jako "
        "ograniczenie, które trener ma respektować przy układaniu planu.",
        kind=KIND_LONGTEXT,
        placeholder="np. unikam wyciskania zza głowy i podciągania szerokim",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="ograniczenia_ruchu",
        scan_safety=True,
        conditional=True,
        max_len=1500,
    ),
    Step(
        id="bol_obecny",
        topic="Ból",
        question="Czy coś boli Cię teraz, w tym momencie?",
        why="Ból w trakcie planowania zmienia priorytety — czasem "
        "najlepszym pierwszym krokiem jest wizyta u specjalisty, a nie "
        "trening.",
        kind=KIND_BOOL,
        options=("Tak", "Nie"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="bol_biezacy",
        max_len=20,
    ),
    Step(
        id="bol_opis",
        topic="Ból",
        question="Powiedz krótko, gdzie i od kiedy.",
        why="Trener zapisze to jako ograniczenie. Oceny medycznej nie "
        "robi ani trener, ani aplikacja.",
        kind=KIND_LONGTEXT,
        placeholder="np. dolny odcinek pleców, od tygodnia, po dłuższym siedzeniu",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="bol_opis",
        scan_safety=True,
        conditional=True,
        max_len=1500,
    ),
    Step(
        id="sen",
        topic="Sen",
        question="Ile zwykle śpisz w nocy?",
        why="Sen decyduje o regeneracji. Przy krótkim śnie sensowniejszy "
        "jest łagodniejszy plan niż heroiczny, po którym nie wstaniesz.",
        kind=KIND_CHOICE,
        options=("Mniej niż 5 h", "5-6 h", "6-7 h", "7-8 h", "Ponad 8 h", "Bardzo różnie"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="sen_godziny",
        max_len=40,
    ),
    Step(
        id="stres",
        topic="Stres",
        question="Jak oceniasz swój obecny poziom stresu? (1 = spokojnie, "
        "5 = bardzo dużo)",
        why="To Twoja subiektywna ocena, nie pomiar. Pomaga trenerowi "
        "wybrać, czy plan ma dokładać obciążenia, czy je równoważyć.",
        kind=KIND_SCALE,
        options=("1", "2", "3", "4", "5"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="poziom_stresu",
        max_len=10,
    ),
    Step(
        id="zywienie_styl",
        topic="Żywienie",
        question="Jak dziś wygląda Twoje jedzenie — bez upiększania?",
        why="Plan żywieniowy powstaje na bazie tego, co realnie jesz, "
        "a nie tego, co „wypada” napisać. Nikt tego nie ocenia.",
        kind=KIND_LONGTEXT,
        placeholder="np. 2 posiłki dziennie, dużo w biegu, wieczorem "
        "podjadam; nie jem ryb",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="preferencje_zywieniowe",
        max_len=1500,
    ),
    Step(
        id="alergie",
        topic="Alergie",
        question="Masz alergie albo nietolerancje pokarmowe?",
        why="To pytanie bezpieczeństwa — bez tej informacji plan diety "
        "może zawierać coś, czego nie możesz jeść.",
        kind=KIND_TEXT,
        placeholder="np. orzechy, laktoza; nie mam",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="alergie",
        max_len=500,
    ),
    Step(
        id="suplementacja",
        topic="Suplementacja",
        question="Przyjmujesz obecnie jakieś suplementy albo leki?",
        why="Zapisujemy to wyłącznie jako Twoją deklarację, żeby trener "
        "o tym wiedział. Aplikacja niczego nie dobiera ani nie zaleca — "
        "plan suplementacji może ułożyć wyłącznie człowiek, a leki to "
        "zawsze sprawa lekarza.",
        kind=KIND_LONGTEXT,
        placeholder="np. witamina D 2000 IU rano; kreatyna 5 g",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="suplementacja_deklaracja",
        max_len=1000,
    ),
    Step(
        id="komunikacja",
        topic="Komunikacja",
        question="Jak wolisz się kontaktować z trenerem?",
        why="Żeby kontakt był po Twojej stronie wygodny — a nie żeby "
        "aplikacja zasypywała Cię powiadomieniami.",
        kind=KIND_CHOICE,
        options=(
            "Wiadomości w aplikacji, odpowiadam gdy mogę",
            "Wiadomości w aplikacji + przypomnienia",
            "Wolę krótkie konsultacje na żywo",
            "Jak najmniej kontaktu — sam(a) dam znać",
        ),
        profile_field="preferencje_komunikacji",
        max_len=120,
    ),
    Step(
        id="zgody_info",
        topic="Zgody",
        question="Na koniec: Twoje dane należą do Ciebie.",
        why="Zakres zgód ustawiasz sam(a) w Profilu → Prywatność i zgody. "
        "Możesz je w każdej chwili cofnąć — rozmowa ani plan przez to nie "
        "znikają, zmienia się tylko to, co widzi trener.",
        kind=KIND_INFO,
        options=("Rozumiem",),
        max_len=40,
    ),
)

STEP_BY_ID: dict[str, Step] = {s.id: s for s in STEPS}
STEP_ORDER: dict[str, int] = {s.id: i for i, s in enumerate(STEPS)}


# ---------------------------------------------------------------------------
# Reguły adaptacji — deterministyczne, serwerowe, działają też bez modelu.
# ---------------------------------------------------------------------------

# Odpowiedzi na "sprzet", które odsłaniają pytanie o warianty domowe.
_BEZ_SILOWNI = {
    "Dom — mam sprzęt (hantle, gumy, drążek)",
    "Dom — bez sprzętu, tylko masa ciała",
    "Na zewnątrz (park, plac zabaw, bieganie)",
}


def _yes(value: str | None) -> bool:
    return (value or "").strip().casefold() == "tak"


def _triggered(step_id: str, answers: dict[str, str | None]) -> bool:
    """Czy krok warunkowy jest odsłonięty przez dotychczasowe odpowiedzi.

    Każda reguła jest jawna i wynika WYŁĄCZNIE z informacji istotnych dla
    onboardingu — nigdy z profilowania klienta ani z sugestii modelu."""
    if step_id == "technika_wsparcie":
        return answers.get("doswiadczenie") in (
            "Zaczynam od zera",
            "Trenowałem(-am) kiedyś, wracam po przerwie",
        )
    if step_id == "warianty_domowe":
        return answers.get("sprzet") in _BEZ_SILOWNI
    if step_id in ("urazy_opis", "urazy_ograniczenia"):
        return _yes(answers.get("urazy_czy"))
    if step_id == "bol_opis":
        return _yes(answers.get("bol_obecny"))
    return False


def plan_steps(
    answers: dict[str, str | None],
    *,
    allowed_domains: set[str],
    steps: tuple[Step, ...] = STEPS,
    triggered=None,
) -> list[str]:
    """Lista identyfikatorów kroków dla BIEŻĄCEGO stanu rozmowy.

    `answers` zawiera wyłącznie odpowiedzi udzielone (pominięcie ma
    wartość None i nie odsłania kroków warunkowych). `allowed_domains` to
    domeny danych, na które klient ma aktywną zgodę — krok o danych
    wrażliwych bez zgody nie powstaje w ogóle (minimalizacja: nie pytamy
    o to, czego nie wolno nam przechowywać).

    `steps`/`triggered` parametryzują scenariusz: rozmowa startowa używa
    domyślnych (STEPS + reguły poniżej), głęboki wywiad przekazuje własne
    (`interview_flow`). Zachowanie domyślne jest identyczne jak przed
    uogólnieniem."""
    is_triggered = triggered or _triggered
    planned: list[str] = []
    for step in steps:
        if step.consent_domain is not None and step.consent_domain not in allowed_domains:
            continue
        if step.conditional and not is_triggered(step.id, answers):
            continue
        planned.append(step.id)
    return planned


def next_step_id(planned: list[str], answered: set[str]) -> str | None:
    """Pierwszy krok planu, na który nie ma jeszcze reakcji (odpowiedzi ani
    świadomego pominięcia). None = rozmowa dobiegła końca."""
    for step_id in planned:
        if step_id not in answered:
            return step_id
    return None


def previous_step_id(planned: list[str], current: str | None) -> str | None:
    """Krok poprzedzający `current` w planie (przycisk „wróć"). Gdy rozmowa
    jest już na podsumowaniu (`current is None`) — ostatni krok planu."""
    if not planned:
        return None
    if current is None:
        return planned[-1]
    if current not in planned:
        return None
    index = planned.index(current)
    return planned[index - 1] if index > 0 else None


def progress(planned: list[str], answered: set[str]) -> dict[str, int]:
    total = len(planned)
    done = len([s for s in planned if s in answered])
    return {
        "answered": done,
        "total": total,
        "percent": round(100 * done / total) if total else 100,
    }


# ---------------------------------------------------------------------------
# Objawy alarmowe — deterministyczna lista, zero oceny medycznej.
# ---------------------------------------------------------------------------

# Komunikat celowo spokojny: informuje i kieruje, nie straszy i nie
# stawia żadnej hipotezy o tym, co się dzieje.
SAFETY_MESSAGE = (
    "Dziękujemy, że o tym napisałeś(-aś). To opis, którego ani trener, "
    "ani aplikacja nie powinni oceniać — takie objawy zawsze warto "
    "skonsultować z lekarzem, a przy nagłym i silnym przebiegu zadzwonić "
    "pod 112 lub 999. Rozmowę możesz spokojnie kontynuować; zaznaczyliśmy "
    "tę odpowiedź dla trenera, żeby wstrzymał się z planem do czasu "
    "Twojej konsultacji."
)

# Etykieta -> warianty zapisu (bez znaków diakrytycznych, małymi literami).
SAFETY_SIGNALS: dict[str, tuple[str, ...]] = {
    "ból w klatce piersiowej": ("bol w klatce", "bol klatki", "bol zamostkowy",
                                "uciska w klatce", "ucisk w klatce"),
    "omdlenia / utrata przytomności": ("omdlenie", "omdlenia", "omdlewam",
                                       "zaslabniecie", "zaslabl", "utrata przytomnosci",
                                       "traci przytomnosc", "zemdlalem", "zemdlalam"),
    "duszność": ("dusznosc", "dusznosci", "brak tchu", "nie moge zlapac oddechu",
                 "brakuje mi powietrza"),
    "ostry ból po urazie": ("ostry bol po urazie", "silny bol po urazie",
                            "bol po upadku", "bol po skrecen", "nie moge stanac na nodze",
                            "nie moge obciazyc nogi"),
    "kołatanie serca": ("kolatanie serca", "arytmia", "serce wali"),
    "drętwienie / niedowład": ("dretwienie", "dretwieje", "niedowlad",
                               "nie czuje nogi", "nie czuje reki"),
    "nagły silny ból głowy": ("nagly silny bol glowy", "najgorszy bol glowy"),
}

_DIACRITICS = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Tekst do porównań: bez znaków diakrytycznych, małymi literami,
    ze znormalizowanymi odstępami. Nie zmienia danych zapisanych w bazie."""
    folded = unicodedata.normalize("NFKC", text).translate(_DIACRITICS).casefold()
    return _WHITESPACE.sub(" ", folded)


def scan_safety_signals(text: str) -> list[str]:
    """Etykiety rozpoznanych objawów alarmowych (pusta lista = brak).

    To wyłącznie dopasowanie słów kluczowych. Aplikacja nie twierdzi, że
    coś się dzieje — sygnalizuje, że opis wykracza poza kompetencje
    trenera personalnego."""
    haystack = normalize(text)
    found = [
        label
        for label, variants in SAFETY_SIGNALS.items()
        if any(variant in haystack for variant in variants)
    ]
    return found


# ---------------------------------------------------------------------------
# Walidacja odpowiedzi (serwerowa — frontend tylko podpowiada).
# ---------------------------------------------------------------------------


def validate_answer(step: Step, value: str) -> str:
    """Zwraca znormalizowaną wartość albo podnosi ValueError z komunikatem
    po polsku. Wartości spoza listy opcji są odrzucane — do profilu nigdy
    nie trafia surowy tekst tam, gdzie kontrakt przewiduje wybór."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Odpowiedź jest pusta — użyj „Pomiń”, jeśli nie chcesz odpowiadać.")
    if len(cleaned) > step.max_len:
        raise ValueError(f"Odpowiedź jest za długa (limit {step.max_len} znaków).")
    if step.kind in (KIND_CHOICE, KIND_BOOL, KIND_SCALE, KIND_INFO):
        if cleaned not in step.options:
            raise ValueError("Wybierz jedną z dostępnych odpowiedzi.")
    elif step.kind == KIND_MULTI:
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if not parts:
            raise ValueError("Zaznacz przynajmniej jedną odpowiedź.")
        unknown = [p for p in parts if p not in step.options]
        if unknown:
            raise ValueError("Zaznaczono odpowiedź spoza listy.")
        # Kolejność listy, nie kolejność klikania (stabilny zapis do profilu).
        ordered = [o for o in step.options if o in parts]
        return ", ".join(ordered)
    return cleaned


def step_payload(step: Step) -> dict:
    """Kontrakt kroku dla frontendu (pytanie + PO CO + opcje)."""
    return {
        "id": step.id,
        "topic": step.topic,
        "question": step.question,
        "why": step.why,
        "kind": step.kind,
        "options": list(step.options),
        "placeholder": step.placeholder,
        "sensitive": step.sensitive,
        "max_len": step.max_len,
    }

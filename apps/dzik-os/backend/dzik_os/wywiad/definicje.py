"""Definicje pytań wywiadu wstępnego i głębokiego.

Źródłem pytań są istniejące scenariusze (`onboarding_flow.STEPS` — 22
kroki rozmowy startowej, `interview_flow.DEEP_STEPS` — 50 kroków
głębokiego wywiadu): `question_id` = dotychczasowy `step.id`, więc
odpowiedzi z sesji rozmowy przenoszą się do wersji BEZ reinterpretacji.
Ten moduł dokłada to, czego scenariusz rozmowy nie miał: sekcje, jawną
regułę wymagalności per usługa, klasyfikację dostępu, opis reguły
widoczności i odpowiedzi „nie zgłaszam / tak / nie wiem / wolę omówić
z trenerem” dla pytań o ograniczenia.

Zmiana ZNACZENIA pytania to nowa wersja definicji (`WERSJA`), nigdy
nadpisanie etykiety w miejscu — stare odpowiedzi zachowują wersję, pod
którą powstały. Reguły widoczności i wymagalności liczy WYŁĄCZNIE serwer
(`aktywne`, `wymagane_aktywne`, `postep`, `braki`) — przeglądarka tylko
pokazuje wynik.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..authz import DOMAIN_HEALTH, DOMAIN_NUTRITION
from ..interview_flow import DEEP_STEPS, deep_triggered
from ..onboarding_flow import (
    KIND_BOOL,
    KIND_CHOICE,
    KIND_INFO,
    KIND_MULTI,
    KIND_SCALE,
    STEPS,
    Step,
    _triggered,
)
from . import zapotrzebowanie as Z

WSTEPNY = "wstepny"
GLEBOKI = "gleboki"
#: Wywiad „Zapotrzebowanie kaloryczne” (0.62.0) — za flagą
#: DZIK_CALORIE_INTERVIEW_ENABLED (router filtruje `TYPY` przez `typy_aktywne`).
ZAPOTRZEBOWANIE = "zapotrzebowanie"
TYPY = (WSTEPNY, GLEBOKI, ZAPOTRZEBOWANIE)

#: Rodzaj pytania liczbowego (tylko w wywiadzie zapotrzebowania): odpowiedź
#: tekstowa walidowana serwerowo jako liczba z zakresu `Pytanie.zakres`.
KIND_NUMBER = "NUMBER"

#: Wersja definicji obu formularzy. Podbicie = nowa wersja pytań; stare
#: przesłania trzymają swoją.
WERSJA = 1

#: Usługi, względem których liczona jest wymagalność pytań.
USLUGI = ("trening", "zywienie", "wspolpraca")

#: Odpowiedzi pytań o ograniczenia (zdrowie, urazy, ból, zalecenia
#: lekarza). „Nie wiem” i „Wolę omówić z trenerem” są pełnoprawnymi
#: odpowiedziami — liczą się do postępu, ale zostawiają otwartą pozycję
#: „do omówienia” w podsumowaniu.
ODP_NIE_ZGLASZAM = "Nie zgłaszam"
ODP_TAK = "Tak"
ODP_NIE_WIEM = "Nie wiem"
ODP_OMOWIC = "Wolę omówić z trenerem"
OPCJE_OGRANICZEN = (ODP_NIE_ZGLASZAM, ODP_TAK, ODP_NIE_WIEM, ODP_OMOWIC)
ODP_DO_OMOWIENIA = (ODP_NIE_WIEM, ODP_OMOWIC)

#: Pytania BOOL („Tak/Nie”) o ograniczenia, które w wywiadzie dostają
#: cztery odpowiedzi. Reguły odsłaniania kroków warunkowych (`_yes`)
#: działają bez zmian: odsłania wyłącznie „Tak”.
_PYTANIA_OGRANICZEN = frozenset({"urazy_czy", "bol_obecny", "gw_c2", "gw_d3"})

#: Klasy dostępu odpowiedzi (widoczność dla trenera wynika ze zgód
#: domeny; klient widzi zawsze wszystko, co sam powiedział).
DOSTEP_PODSTAWOWY = "podstawowe"
DOSTEP_ZDROWIE = "zdrowotne"
DOSTEP_ZYWIENIE = "zywieniowe"


@dataclass(frozen=True)
class Sekcja:
    key: str
    label: str
    opis: str


@dataclass(frozen=True)
class Pytanie:
    question_id: str
    version: int
    type: str
    label: str
    why: str
    section: str
    options: tuple[str, ...]
    #: Usługi, dla których pytanie jest wymagane (pusty = opcjonalne).
    required_for: frozenset[str]
    #: Czytelny opis reguły widoczności (sama reguła: `_widoczne`).
    visibility_rule: str
    consent_domain: str | None
    sensitive: bool
    access_class: str
    #: Klucz faktu / pola profilu, który zasila odpowiedź (None = nie zasila).
    fact_key: str | None
    max_len: int
    conditional: bool
    placeholder: str
    scan_safety: bool
    flag_options: tuple[str, ...]
    #: Zakres (min, max) dla pytań NUMBER; None dla pozostałych rodzajów.
    zakres: tuple[float, float] | None = None

    @property
    def informacyjne(self) -> bool:
        return self.type == KIND_INFO


@dataclass(frozen=True)
class Definicja:
    typ: str
    version: int
    title: str
    opis: str
    sections: tuple[Sekcja, ...]
    questions: tuple[Pytanie, ...]
    triggered: Callable[[str, dict], bool]

    @property
    def by_id(self) -> dict[str, Pytanie]:
        return {q.question_id: q for q in self.questions}


# ---------------------------------------------------------------------------
# Sekcje i przypisanie kroków
# ---------------------------------------------------------------------------

SEKCJE_WSTEPNY: tuple[Sekcja, ...] = (
    Sekcja("cel", "Cel", "Po co ta współpraca i w jakim czasie."),
    Sekcja("punkt_wyjscia", "Punkt wyjścia", "Doświadczenie i to, od czego startujemy."),
    Sekcja("trening", "Trening", "Dostępność, dni, pory, sprzęt — ramy planu."),
    Sekcja("zdrowie", "Zdrowie i ograniczenia",
           "Urazy, ból, sen, stres. „Nie wiem” i „wolę omówić z trenerem” są w porządku — "
           "trener nie ocenia, tylko wie, czego unikać."),
    Sekcja("odzywianie", "Odżywianie",
           "Alergia (reakcja organizmu, potwierdzona), nietolerancja (dolegliwość po produkcie) "
           "i preferencja (wybór) to trzy różne rzeczy — plan traktuje je inaczej."),
    Sekcja("codziennosc", "Codzienność", "Co w tygodniu przeszkadza i co realnie da się zrobić."),
    Sekcja("wspolpraca", "Współpraca", "Jak chcesz się komunikować i co wiesz o zgodach."),
)

_SEKCJA_WSTEPNY: dict[str, str] = {
    "cel_glowny": "cel", "cel_termin": "cel",
    "doswiadczenie": "punkt_wyjscia", "technika_wsparcie": "punkt_wyjscia",
    "dostepnosc": "trening", "preferowane_dni": "trening", "preferowane_godziny": "trening",
    "sprzet": "trening", "warianty_domowe": "trening",
    "ograniczenia": "codziennosc",
    "urazy_czy": "zdrowie", "urazy_opis": "zdrowie", "urazy_ograniczenia": "zdrowie",
    "bol_obecny": "zdrowie", "bol_opis": "zdrowie", "sen": "zdrowie", "stres": "zdrowie",
    "zywienie_styl": "odzywianie", "alergie": "odzywianie", "suplementacja": "odzywianie",
    "komunikacja": "wspolpraca", "zgody_info": "wspolpraca",
}

#: Wymagalność per usługa w wywiadzie wstępnym. Reszta jest opcjonalna —
#: „pełny wywiad” nie jest warunkiem współpracy.
_WYMAGANE_WSTEPNY: dict[str, frozenset[str]] = {
    "cel_glowny": frozenset({"trening", "zywienie"}),
    "doswiadczenie": frozenset({"trening"}),
    "dostepnosc": frozenset({"trening"}),
    "sprzet": frozenset({"trening"}),
    "urazy_czy": frozenset({"trening"}),
    "bol_obecny": frozenset({"trening"}),
    "zywienie_styl": frozenset({"zywienie"}),
    "alergie_status": frozenset({"zywienie"}),
    "komunikacja": frozenset({"wspolpraca"}),
}

SEKCJE_GLEBOKI: tuple[Sekcja, ...] = (
    Sekcja("motywacja", "Motywacja", "Cel głębiej, stres i głowa — co napędza, a co blokuje."),
    Sekcja("historia_treningowa", "Historia treningowa", "Co było, co działało, co się nie udało."),
    Sekcja("ograniczenia", "Pogłębienie ograniczeń",
           "Przesiew przed wysiłkiem, zalecenia lekarza, leki, urazy, bóle. Bez oceny medycznej."),
    Sekcja("regeneracja", "Regeneracja", "Sen, rytm, zmianowość, nawyki regeneracyjne."),
    Sekcja("historia_odzywiania", "Historia odżywiania", "Dzień jedzeniowy, gotowanie, diety w przeszłości."),
    Sekcja("organizacja", "Organizacja", "Mapa tygodnia, praca, wyjazdy, nieprzewidywalność."),
    Sekcja("preferencje", "Preferencje szczegółowe", "Pomiary, mierniki, zdjęcia, forma informacji zwrotnej."),
    Sekcja("pytania_trenera", "Pytania trenera",
           "Pytanie otwarte i prośby trenera o doprecyzowanie konkretnych odpowiedzi."),
)

_PREFIKS_GLEBOKI: dict[str, str] = {
    "gw_a": "motywacja", "gw_e": "motywacja", "gw_b": "historia_treningowa",
    "gw_c": "ograniczenia", "gw_d": "regeneracja", "gw_f": "historia_odzywiania",
    "gw_g": "organizacja", "gw_h": "preferencje", "gw_i": "preferencje",
}
_SEKCJA_GLEBOKI_WYJATKI: dict[str, str] = {"gw_intro": "motywacja", "gw_i5": "pytania_trenera"}

#: W głębokim wywiadzie wymagany jest wyłącznie przesiew przed wysiłkiem
#: (dla usługi trening). „Nie wymagaj pełnego wywiadu głębokiego od
#: każdego klienta.”
_WYMAGANE_GLEBOKI: dict[str, frozenset[str]] = {
    "gw_c1": frozenset({"trening"}),
    "gw_c2": frozenset({"trening"}),
}


def _sekcja_gleboki(step_id: str) -> str:
    if step_id in _SEKCJA_GLEBOKI_WYJATKI:
        return _SEKCJA_GLEBOKI_WYJATKI[step_id]
    return _PREFIKS_GLEBOKI.get(step_id[:4], "preferencje")


def _klasa_dostepu(step: Step) -> str:
    if step.consent_domain == DOMAIN_NUTRITION:
        return DOSTEP_ZYWIENIE
    if step.consent_domain == DOMAIN_HEALTH or step.sensitive:
        return DOSTEP_ZDROWIE
    return DOSTEP_PODSTAWOWY


def _regula_widocznosci(step: Step) -> str:
    czesci: list[str] = []
    if step.consent_domain == DOMAIN_HEALTH:
        czesci.append("aktywna zgoda: dane zdrowotne")
    elif step.consent_domain == DOMAIN_NUTRITION:
        czesci.append("aktywna zgoda: dane żywieniowe")
    if step.conditional:
        czesci.append(_OPIS_WARUNKU.get(step.id, "odsłania wcześniejsza odpowiedź"))
    return "; ".join(czesci) if czesci else "zawsze"


_OPIS_WARUNKU: dict[str, str] = {
    "technika_wsparcie": "gdy doświadczenie = początek albo powrót po przerwie",
    "warianty_domowe": "gdy sprzęt = dom albo na zewnątrz",
    "urazy_opis": "gdy urazy = Tak",
    "urazy_ograniczenia": "gdy urazy = Tak",
    "bol_opis": "gdy ból obecny = Tak",
    "gw_c2_opis": "gdy zalecenie lekarza = Tak",
    "gw_d3_wzor": "gdy praca zmianowa = Tak",
    "gw_e2_kiedy": "gdy jedzenie pod wpływem emocji = Tak albo Czasem",
}


def _z_kroku(step: Step, *, section: str, required_for: frozenset[str], version: int) -> Pytanie:
    options = tuple(step.options)
    if step.id in _PYTANIA_OGRANICZEN:
        options = OPCJE_OGRANICZEN
    return Pytanie(
        question_id=step.id, version=version, type=step.kind, label=step.question, why=step.why,
        section=section, options=options, required_for=required_for,
        visibility_rule=_regula_widocznosci(step), consent_domain=step.consent_domain,
        sensitive=step.sensitive, access_class=_klasa_dostepu(step), fact_key=step.profile_field,
        max_len=max(step.max_len, 40) if step.id in _PYTANIA_OGRANICZEN else step.max_len,
        conditional=step.conditional, placeholder=step.placeholder, scan_safety=step.scan_safety,
        flag_options=tuple(step.flag_options),
    )


#: Pytania dołożone w 0.59.0 (nie mają odpowiednika w scenariuszu rozmowy):
#: rozróżnienie alergia / nietolerancja / preferencja.
_DODATKOWE_WSTEPNY: tuple[Pytanie, ...] = (
    Pytanie(
        question_id="alergie_status", version=1, type=KIND_CHOICE,
        label="Czy masz potwierdzoną alergię pokarmową?",
        why="Alergia to ograniczenie bezpieczeństwa: kreator dań wyklucza alergen bez wyjątków. "
        "Brak informacji nigdy nie jest traktowany jak „brak alergii”.",
        section="odzywianie",
        options=("Tak, potwierdzoną (lekarz lub badanie)", "Podejrzewam, ale nie potwierdziłem(-am)",
                 ODP_NIE_ZGLASZAM, ODP_NIE_WIEM, ODP_OMOWIC),
        required_for=frozenset({"zywienie"}), visibility_rule="aktywna zgoda: dane żywieniowe",
        consent_domain=DOMAIN_NUTRITION, sensitive=True, access_class=DOSTEP_ZYWIENIE,
        fact_key="alergie_status", max_len=60, conditional=False, placeholder="", scan_safety=False,
        flag_options=(),
    ),
    Pytanie(
        question_id="nietolerancje", version=1, type="TEXT",
        label="Nietolerancje pokarmowe (produkt → dolegliwość)?",
        why="Nietolerancja ogranicza dobór produktów, ale nie jest alergią — trener może "
        "zaproponować ilość albo zamiennik zamiast wykluczać wszystko.",
        section="odzywianie", options=(), required_for=frozenset(),
        visibility_rule="aktywna zgoda: dane żywieniowe", consent_domain=DOMAIN_NUTRITION,
        sensitive=True, access_class=DOSTEP_ZYWIENIE, fact_key="nietolerancje", max_len=500,
        conditional=False, placeholder="np. laktoza — wzdęcia; nie mam", scan_safety=False,
        flag_options=(),
    ),
    Pytanie(
        question_id="wykluczenia_preferencje", version=1, type="TEXT",
        label="Czego nie chcesz jeść z wyboru (smak, przekonania, styl)?",
        why="Preferencja to Twój wybór, nie ograniczenie zdrowotne — plan ją szanuje, "
        "ale trener może zaproponować kompromis.",
        section="odzywianie", options=(), required_for=frozenset(),
        visibility_rule="aktywna zgoda: dane żywieniowe", consent_domain=DOMAIN_NUTRITION,
        sensitive=True, access_class=DOSTEP_ZYWIENIE, fact_key="wykluczenia_preferencje",
        max_len=500, conditional=False, placeholder="np. podroby, ostre potrawy; jem wszystko",
        scan_safety=False, flag_options=(),
    ),
)


def _zbuduj_wstepny() -> Definicja:
    pytania: list[Pytanie] = []
    for step in STEPS:
        pytania.append(_z_kroku(
            step, section=_SEKCJA_WSTEPNY.get(step.id, "wspolpraca"),
            required_for=_WYMAGANE_WSTEPNY.get(step.id, frozenset()), version=WERSJA,
        ))
        if step.id == "alergie":
            pytania.extend(_DODATKOWE_WSTEPNY)
    return Definicja(
        typ=WSTEPNY, version=WERSJA, title="Wywiad wstępny",
        opis="Krótki formularz, który pozwala trenerowi zacząć: cel, punkt wyjścia, ramy "
        "treningu, ograniczenia, odżywianie, codzienność, współpraca. Możesz zapisać "
        "część i wrócić później.",
        sections=SEKCJE_WSTEPNY, questions=tuple(pytania), triggered=_triggered,
    )


def _zbuduj_gleboki() -> Definicja:
    pytania = tuple(
        _z_kroku(step, section=_sekcja_gleboki(step.id),
                 required_for=_WYMAGANE_GLEBOKI.get(step.id, frozenset()), version=WERSJA)
        for step in DEEP_STEPS
    )
    return Definicja(
        typ=GLEBOKI, version=WERSJA, title="Wywiad głęboki",
        opis="Dłuższy wywiad o historii, regeneracji, organizacji i motywacji. "
        "Nie jest wymagany od każdego — wypełnij te sekcje, które mają dla Was znaczenie.",
        sections=SEKCJE_GLEBOKI, questions=pytania, triggered=deep_triggered,
    )


# ---------------------------------------------------------------------------
# Wywiad „Zapotrzebowanie kaloryczne” (0.62.0)
# ---------------------------------------------------------------------------

SEKCJE_ZAPOTRZEBOWANIE: tuple[Sekcja, ...] = (
    Sekcja("zk_dane", "Dane podstawowe", "Płeć, wiek, wzrost i masa — wejścia wzoru na PPM."),
    Sekcja("zk_aktywnosc", "Aktywność", "Praca, treningi i kroki — z nich wynika współczynnik PAL."),
    Sekcja("zk_cel", "Cel", "Kierunek i tempo zmian — korekta wyniku."),
    Sekcja("zk_bezpieczenstwo", "Bezpieczeństwo",
           "Jedno pytanie zdrowotne. Decyduje, czy liczby pokażą się od razu, czy najpierw omówi je trener."),
)

_WSZYSTKIE_USLUGI = frozenset(USLUGI)
ODP_ZABURZENIA_TAK = "Tak, obecnie lub w przeszłości"
OPCJE_ZABURZEN = (ODP_NIE_ZGLASZAM, ODP_ZABURZENIA_TAK, ODP_NIE_WIEM, ODP_OMOWIC)


def _zk(question_id: str, typ: str, label: str, why: str, section: str, *, options: tuple[str, ...] = (),
        required: bool = True, conditional: bool = False, placeholder: str = "",
        zakres: tuple[float, float] | None = None, consent_domain: str | None = None,
        sensitive: bool = False, access_class: str = DOSTEP_PODSTAWOWY, max_len: int = 80,
        flag_options: tuple[str, ...] = (), visibility_rule: str = "zawsze") -> Pytanie:
    return Pytanie(
        question_id=question_id, version=WERSJA, type=typ, label=label, why=why, section=section,
        options=options, required_for=_WSZYSTKIE_USLUGI if required else frozenset(),
        visibility_rule=visibility_rule, consent_domain=consent_domain, sensitive=sensitive,
        access_class=access_class, fact_key=None, max_len=max_len, conditional=conditional,
        placeholder=placeholder, scan_safety=False, flag_options=flag_options, zakres=zakres,
    )


_PYTANIA_ZAPOTRZEBOWANIE: tuple[Pytanie, ...] = (
    _zk("zk_plec", KIND_CHOICE, "Płeć", "Wzór na przemianę materii ma inną stałą dla kobiet i mężczyzn.",
        "zk_dane", options=Z.PLCI),
    _zk("zk_wiek", KIND_NUMBER, "Wiek (lata)", "Z wiekiem podstawowa przemiana materii maleje — wzór to uwzględnia.",
        "zk_dane", placeholder="np. 32", zakres=Z.ZAKRES_WIEK, max_len=5),
    _zk("zk_wzrost", KIND_NUMBER, "Wzrost (cm)", "Wzrost wchodzi do wzoru na PPM.",
        "zk_dane", placeholder="np. 176", zakres=Z.ZAKRES_WZROST, max_len=6),
    _zk("zk_masa", KIND_NUMBER, "Aktualna masa ciała (kg)",
        "Masa ma największy wpływ na wynik. Podaj poranną, po toalecie, przed jedzeniem.",
        "zk_dane", placeholder="np. 72,5", zakres=Z.ZAKRES_MASA, max_len=7),
    _zk("zk_praca", KIND_CHOICE, "Jaki masz charakter pracy / dnia?",
        "Aktywność poza treningiem to zwykle większa część wydatku energii niż sam trening.",
        "zk_aktywnosc", options=tuple(Z.PRACA)),
    _zk("zk_treningi", KIND_CHOICE, "Ile treningów robisz w tygodniu (realnie, nie planowo)?",
        "Treningi dokładają się do współczynnika aktywności. Liczy się to, co się dzieje, nie plan.",
        "zk_aktywnosc", options=tuple(Z.TRENINGI)),
    _zk("zk_kroki", KIND_CHOICE, "Ile kroków dziennie robisz przeciętnie?",
        "Kroki doprecyzowują aktywność poza treningiem. Jeśli nie mierzysz — wybierz „Nie wiem”.",
        "zk_aktywnosc", options=tuple(Z.KROKI), required=False),
    _zk("zk_cel", KIND_CHOICE, "Jaki jest cel na najbliższe tygodnie?",
        "Cel decyduje, czy wynik ma być poniżej, na poziomie, czy powyżej zapotrzebowania.",
        "zk_cel", options=Z.CELE),
    _zk("zk_tempo_redukcja", KIND_CHOICE, "Jakie tempo redukcji?",
        "Łagodniejsze tempo jest łatwiejsze do utrzymania i chroni masę mięśniową. Trener może je zmienić.",
        "zk_cel", options=tuple(Z.TEMPO_REDUKCJA), conditional=True,
        visibility_rule="cel: redukcja masy ciała"),
    _zk("zk_tempo_masa", KIND_CHOICE, "Jakie tempo budowy masy?",
        "Większa nadwyżka to szybszy przyrost masy, ale też więcej tkanki tłuszczowej.",
        "zk_cel", options=tuple(Z.TEMPO_MASA), conditional=True,
        visibility_rule="cel: budowa masy mięśniowej"),
    _zk("zk_zaburzenia", KIND_CHOICE,
        "Czy zdiagnozowano u Ciebie zaburzenia odżywiania albo masz z nimi doświadczenie?",
        "Liczenie kalorii może szkodzić osobom z takim doświadczeniem. Przy „Tak”, „Nie wiem” lub „Wolę "
        "omówić” wynik nie pokaże się automatycznie — najpierw przejrzy go trener i porozmawiacie.",
        "zk_bezpieczenstwo", options=OPCJE_ZABURZEN, consent_domain=DOMAIN_HEALTH, sensitive=True,
        access_class=DOSTEP_ZDROWIE, flag_options=(ODP_ZABURZENIA_TAK, ODP_NIE_WIEM, ODP_OMOWIC),
        visibility_rule="aktywna zgoda: dane zdrowotne", max_len=60),
)


def _zapotrzebowanie_triggered(question_id: str, wartosci_: dict[str, str | None]) -> bool:
    if question_id == "zk_tempo_redukcja":
        return wartosci_.get("zk_cel") == Z.CEL_REDUKCJA
    if question_id == "zk_tempo_masa":
        return wartosci_.get("zk_cel") == Z.CEL_MASA
    return False


def _zbuduj_zapotrzebowanie() -> Definicja:
    return Definicja(
        typ=ZAPOTRZEBOWANIE, version=WERSJA, title="Zapotrzebowanie kaloryczne",
        opis="Kilka pytań o ciało, aktywność i cel. Z nich wzór (Mifflin-St Jeor × współczynnik "
        "aktywności, korekta pod cel) szacuje dzienne zapotrzebowanie. To szacunek — zalecenie "
        "ustala trener, który widzi całe podstawienie i może wynik nadpisać.",
        sections=SEKCJE_ZAPOTRZEBOWANIE, questions=_PYTANIA_ZAPOTRZEBOWANIE,
        triggered=_zapotrzebowanie_triggered,
    )


_DEFINICJE: dict[str, Definicja] = {
    WSTEPNY: _zbuduj_wstepny(), GLEBOKI: _zbuduj_gleboki(), ZAPOTRZEBOWANIE: _zbuduj_zapotrzebowanie(),
}


def definicja(typ: str) -> Definicja:
    if typ not in _DEFINICJE:
        raise KeyError(typ)
    return _DEFINICJE[typ]


# ---------------------------------------------------------------------------
# Ocena widoczności, wymagalności, postępu — wyłącznie po stronie serwera
# ---------------------------------------------------------------------------


def wartosci(answers: dict[str, dict]) -> dict[str, str | None]:
    """Mapa pytanie → wartość (pominięte i puste = None: nie odsłaniają
    kroków warunkowych)."""
    out: dict[str, str | None] = {}
    for qid, a in answers.items():
        if not isinstance(a, dict) or a.get("skipped"):
            out[qid] = None
            continue
        v = a.get("value")
        out[qid] = v if isinstance(v, str) and v.strip() else None
    return out


def aktywne(defn: Definicja, answers: dict[str, dict], allowed_domains: set[str]) -> list[Pytanie]:
    """Pytania aktywne dla bieżących odpowiedzi i zgód. Pytanie bez zgody
    domeny nie istnieje (minimalizacja); warunkowe — tylko odsłonięte."""
    vals = wartosci(answers)
    out: list[Pytanie] = []
    for q in defn.questions:
        if q.consent_domain is not None and q.consent_domain not in allowed_domains:
            continue
        if q.conditional and not defn.triggered(q.question_id, vals):
            continue
        out.append(q)
    return out


def odpowiedziane(q: Pytanie, answers: dict[str, dict]) -> bool:
    a = answers.get(q.question_id)
    if not isinstance(a, dict) or a.get("skipped"):
        return False
    v = a.get("value")
    return isinstance(v, str) and bool(v.strip())


def wymagane_aktywne(defn: Definicja, answers: dict[str, dict], allowed_domains: set[str],
                     uslugi: set[str] | None = None) -> list[Pytanie]:
    us = set(USLUGI) if uslugi is None else set(uslugi)
    return [q for q in aktywne(defn, answers, allowed_domains)
            if not q.informacyjne and q.required_for & us]


def braki(defn: Definicja, answers: dict[str, dict], allowed_domains: set[str],
          uslugi: set[str] | None = None) -> list[Pytanie]:
    return [q for q in wymagane_aktywne(defn, answers, allowed_domains, uslugi)
            if not odpowiedziane(q, answers)]


def postep(defn: Definicja, answers: dict[str, dict], allowed_domains: set[str],
           uslugi: set[str] | None = None) -> dict[str, int | bool]:
    """Postęp = wymagane aktywne odpowiedziane / wymagane aktywne. Brak
    pytań wymaganych = 100 % (bez dzielenia przez zero). `ready` mówi, czy
    formularz da się przesłać; `data_ready` — czy odpowiedzi wymagane nie
    zawierają „nie wiem / wolę omówić” (kompletność ≠ gotowość danych)."""
    req = wymagane_aktywne(defn, answers, allowed_domains, uslugi)
    done = [q for q in req if odpowiedziane(q, answers)]
    akt = [q for q in aktywne(defn, answers, allowed_domains) if not q.informacyjne]
    akt_done = [q for q in akt if odpowiedziane(q, answers)]
    do_omowienia = [q for q in done if (answers[q.question_id].get("value") in ODP_DO_OMOWIENIA)]
    return {
        "required_answered": len(done), "required_total": len(req),
        "percent": round(100 * len(done) / len(req)) if req else 100,
        "active_answered": len(akt_done), "active_total": len(akt),
        "ready": len(done) == len(req),
        "data_ready": len(done) == len(req) and not do_omowienia,
    }


def waliduj(q: Pytanie, value: str) -> str:
    """Znormalizowana wartość albo ValueError z komunikatem po polsku.
    Odpowiedzi spoza listy są odrzucane."""
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("Odpowiedź jest pusta — użyj „Pomiń”, jeśli nie chcesz odpowiadać.")
    if len(cleaned) > q.max_len:
        raise ValueError(f"Odpowiedź jest za długa (limit {q.max_len} znaków).")
    if q.type in (KIND_CHOICE, KIND_BOOL, KIND_SCALE, KIND_INFO):
        if cleaned not in q.options:
            raise ValueError("Wybierz jedną z dostępnych odpowiedzi.")
        return cleaned
    if q.type == KIND_NUMBER:
        n = Z.liczba(cleaned)
        if n is None:
            raise ValueError("Wpisz liczbę (np. 72,5).")
        if q.zakres and not (q.zakres[0] <= n <= q.zakres[1]):
            lo, hi = (int(x) if float(x).is_integer() else x for x in q.zakres)
            raise ValueError(f"Wartość poza zakresem {lo}–{hi}.")
        return cleaned.replace(" ", "")
    if q.type == KIND_MULTI:
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if not parts:
            raise ValueError("Zaznacz przynajmniej jedną odpowiedź.")
        if any(p not in q.options for p in parts):
            raise ValueError("Zaznaczono odpowiedź spoza listy.")
        return ", ".join(o for o in q.options if o in parts)
    return cleaned


def pytanie_out(q: Pytanie, *, active: bool, required: bool) -> dict:
    return {
        "question_id": q.question_id, "version": q.version, "type": q.type, "label": q.label,
        "why": q.why, "section": q.section, "options": list(q.options),
        "required": required, "required_for": sorted(q.required_for), "active": active,
        "visibility_rule": q.visibility_rule, "consent_domain": q.consent_domain,
        "sensitive": q.sensitive, "access_class": q.access_class, "fact_key": q.fact_key,
        "max_len": q.max_len, "conditional": q.conditional, "placeholder": q.placeholder,
        "info": q.informacyjne, "range": list(q.zakres) if q.zakres else None,
    }


def definicja_out(defn: Definicja, answers: dict[str, dict], allowed_domains: set[str],
                  uslugi: set[str] | None = None) -> dict:
    akt = {q.question_id for q in aktywne(defn, answers, allowed_domains)}
    req = {q.question_id for q in wymagane_aktywne(defn, answers, allowed_domains, uslugi)}
    return {
        "typ": defn.typ, "version": defn.version, "title": defn.title, "opis": defn.opis,
        "sections": [{"key": s.key, "label": s.label, "opis": s.opis} for s in defn.sections],
        "questions": [pytanie_out(q, active=q.question_id in akt, required=q.question_id in req)
                      for q in defn.questions],
        "progress": postep(defn, answers, allowed_domains, uslugi),
        "hidden_domains": sorted({q.consent_domain for q in defn.questions
                                  if q.consent_domain and q.consent_domain not in allowed_domains}),
    }

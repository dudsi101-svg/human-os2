"""Silnik bilansu kalorycznego — specyfikacja właściciela 1.0 (13.09.2026).

Czyste funkcje bez bazy i bez AI. Liczby są **1:1 z referencyjną
implementacją właściciela** (`docs/calorie-interview/calorie_calc.py`);
specyfikacja (`wywiad_zapotrzebowanie_kaloryczne.md`) rozstrzyga teksty
i układ ekranów. Każda rozbieżność między tymi dwoma źródłami jest
wypisana w `docs/calorie-interview/PROGRESS.md`.

Model liczenia (spec §5):

* **PPM** — Mifflin-St Jeor zawsze; Katch-McArdle dodatkowo, gdy podano
  % tkanki tłuszczowej. Gdy oba są dostępne i różnią się o więcej niż
  10 %, używany jest Katch-McArdle (nietypowy skład ciała to właśnie
  przypadek, w którym Mifflin myli się najbardziej).
* **CPM addytywnie**, nie jednym mnożnikiem PAL:
  `CPM = (PPM · mnożnik_NEAT + energia_treningu_dzienna) · 1,10`
  (ostatnie 1,10 to TEF — termiczny efekt pożywienia, 10 %).
  Wynik pokazywany jako zakres ±7 %, bo NEAT jest największym źródłem
  błędu (±200–300 kcal).
* **Cel kaloryczny** = CPM ± korekta z celu i tempa, z podłogą
  `max(PPM · 1,1; 1200 kcal K / 1500 kcal M)`.
* **Makro startowe** w gramach, **flagi** zdrowotne i ograniczenia.

Wynik jest SZACUNKIEM ze wzoru — nie zaleceniem; zalecenie ustala trener.
Wejścia pochodzą z odpowiedzi wywiadu „Zapotrzebowanie kaloryczne”
(`definicje.py`, pytania `zk_*`) — etykiety po polsku, kody wewnętrzne
takie jak w referencji właściciela. Wartości liczbowe przyjmują przecinek
dziesiętny (formularz po polsku).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

#: Wersja wzorów zamrażana przy każdym wyniku (spec §6.3). Wartość wzięta
#: z referencyjnej implementacji właściciela, żeby dało się jednoznacznie
#: powiedzieć, którym zestawem wzorów policzono dany wiersz.
FORMULAS_VERSION = "2026-09-13.1"
#: Wyniki sprzed wyrównania do spec 1.0 (silnik PPM × PAL z 0.62.0). Nie są
#: przeliczane — brak danych wejściowych (rodzaj/czas/intensywność treningu,
#: % tkanki tłuszczowej). Decyzja właściciela z 14.09.
FORMULAS_VERSION_PAL = "0.62.0-pal"

# --- płeć -------------------------------------------------------------------------------

PLEC_K = "Kobieta"
PLEC_M = "Mężczyzna"
PLCI = (PLEC_K, PLEC_M)
KOD_PLCI = {PLEC_K: "F", PLEC_M: "M"}

# --- zakresy wejść (walidacja także w `definicje.waliduj`) -------------------------------

ZAKRES_WIEK = (16.0, 90.0)
ZAKRES_WZROST = (130.0, 230.0)
ZAKRES_MASA = (35.0, 250.0)
ZAKRES_TLUSZCZ = (3.0, 60.0)
ZAKRES_SESJE = (0.0, 7.0)
ZAKRES_KROKI = (0.0, 40000.0)
ZAKRES_MASA_DOCELOWA = (35.0, 250.0)

# --- ekran 2: aktywność poza treningiem (NEAT) ------------------------------------------

NEAT_SIEDZACA = "Siedząca — biurko, samochód, mało chodzenia (poniżej 5 000 kroków)"
NEAT_LEKKA = "Lekka — trochę chodzenia, stanie, lekkie obowiązki (5–8 tys. kroków)"
NEAT_UMIARKOWANA = "Umiarkowana — sporo na nogach: sprzedaż, opieka, częste spacery (8–12 tys.)"
NEAT_WYSOKA = "Wysoka — praca fizyczna, budowa, magazyn, rolnictwo (powyżej 12 tys.)"
NEAT_OPCJE = (NEAT_SIEDZACA, NEAT_LEKKA, NEAT_UMIARKOWANA, NEAT_WYSOKA)
KOD_NEAT = {NEAT_SIEDZACA: "neat_1", NEAT_LEKKA: "neat_2",
            NEAT_UMIARKOWANA: "neat_3", NEAT_WYSOKA: "neat_4"}
NEAT = {"neat_1": 1.20, "neat_2": 1.35, "neat_3": 1.50, "neat_4": 1.70}
#: Kroki (jeśli klient je mierzy) NADPISUJĄ wybór opisowy: 1,20 + 0,04·(kroki/1000 − 4).
NEAT_KROKI_MIN, NEAT_KROKI_MAX = 1.15, 1.85

# --- ekran 3: trening -------------------------------------------------------------------

#: kcal/min ≈ MET · masa · 0,0175 (wartości MET zaokrąglone z Compendium
#: of Physical Activities; siłowy = średnia z przerwami).
MET = {"strength": 5.0, "cardio_light": 4.0, "cardio_moderate": 7.0, "cardio_high": 10.0}
KCAL_MIN_KG = 0.0175

MINUTY_30 = "30 minut"
MINUTY_45 = "45 minut"
MINUTY_60 = "60 minut"
MINUTY_75 = "75 minut"
MINUTY_90 = "90 minut lub więcej"
MINUTY_OPCJE = (MINUTY_30, MINUTY_45, MINUTY_60, MINUTY_75, MINUTY_90)
#: „90 minut lub więcej” liczone jako 90 — spec nie podaje górnej wartości,
#: a zawyżanie zwiększałoby wynik bez pokrycia w danych.
KOD_MINUT = {MINUTY_30: 30, MINUTY_45: 45, MINUTY_60: 60, MINUTY_75: 75, MINUTY_90: 90}

INT_LEKKA = "Lekka — rozmowa swobodna"
INT_UMIARKOWANA = "Umiarkowana — rozmowa urywana"
INT_WYSOKA = "Wysoka — nie da się rozmawiać"
INT_OPCJE = (INT_LEKKA, INT_UMIARKOWANA, INT_WYSOKA)
KOD_INTENSYWNOSCI = {INT_LEKKA: "light", INT_UMIARKOWANA: "moderate", INT_WYSOKA: "high"}

STAZ_KROTKI = "Krócej niż rok"
STAZ_SREDNI = "1–3 lata"
STAZ_DLUGI = "Dłużej niż 3 lata"
STAZ_OPCJE = (STAZ_KROTKI, STAZ_SREDNI, STAZ_DLUGI)
KOD_STAZU = {STAZ_KROTKI: "lt1", STAZ_SREDNI: "1_3", STAZ_DLUGI: "gt3"}
#: Realistyczny przyrost mięśni: % masy ciała na miesiąc (spec §5.4).
PRZYROST_PCT_MIES = {"lt1": (0.5, 1.0), "1_3": (0.25, 0.5), "gt3": (0.0, 0.25)}

# --- ekran 4: cel -----------------------------------------------------------------------

CEL_REDUKCJA = "Redukcja tkanki tłuszczowej"
CEL_UTRZYMANIE = "Utrzymanie masy ciała"
CEL_MASA = "Budowa masy mięśniowej"
CEL_REKOMPOZYCJA = "Rekompozycja (mniej tłuszczu, więcej mięśni)"
CELE = (CEL_REDUKCJA, CEL_UTRZYMANIE, CEL_MASA, CEL_REKOMPOZYCJA)
KOD_CELU = {CEL_REDUKCJA: "cut", CEL_UTRZYMANIE: "maintain",
            CEL_MASA: "bulk", CEL_REKOMPOZYCJA: "recomp"}
#: Cele, dla których pytanie o tempo ma sens (pozostałe mają korektę stałą).
CELE_Z_TEMPEM = ("cut", "bulk")

TEMPO_LAGODNE = "Łagodne"
TEMPO_UMIARKOWANE = "Umiarkowane"
TEMPO_SZYBKIE = "Szybkie"
TEMPO_OPCJE = (TEMPO_LAGODNE, TEMPO_UMIARKOWANE, TEMPO_SZYBKIE)
KOD_TEMPA = {TEMPO_LAGODNE: "gentle", TEMPO_UMIARKOWANE: "moderate", TEMPO_SZYBKIE: "fast"}
#: Korekta CPM pod cel i tempo (spec §5.3), jako ułamek.
KOREKTA = {
    ("cut", "gentle"): -0.10, ("cut", "moderate"): -0.20, ("cut", "fast"): -0.25,
    ("maintain", None): 0.0,
    ("bulk", "gentle"): 0.05, ("bulk", "moderate"): 0.10, ("bulk", "fast"): 0.15,
    ("recomp", None): -0.05,
}

BIALKO_STANDARD = "Standardowa"
BIALKO_WYSOKIE = "Wysoka (dla trenujących siłowo)"
BIALKO_OPCJE = (BIALKO_STANDARD, BIALKO_WYSOKIE)
KOD_BIALKA = {BIALKO_STANDARD: "standard", BIALKO_WYSOKIE: "high"}

# --- makro (spec §5.5) ------------------------------------------------------------------

#: (dolna, górna) granica g/kg białka; „wysoka” preferencja → górna.
BIALKO_G_KG = {"cut": (1.8, 2.2), "maintain": (1.6, 1.6), "bulk": (1.8, 1.8), "recomp": (2.2, 2.2)}
TLUSZCZ_G_KG = {"cut": 0.9, "maintain": 1.0, "bulk": 1.0, "recomp": 0.9}
#: Tłuszcz nigdy poniżej 20 % kalorii celu.
TLUSZCZ_MIN_PCT_KCAL = 0.20
#: Minimalne kalorie (spec §5.3, decyzja właściciela z 14.09 — bez zmian).
MIN_KCAL = {"F": 1200, "M": 1500}
#: Podłoga celu: nigdy poniżej PPM · 1,1.
PPM_MNOZNIK_PODLOGI = 1.10
#: 1 kg tkanki tłuszczowej ≈ 7 700 kcal (spec §5.4).
KCAL_NA_KG = 7700

# --- ekran 5: zdrowie i kontekst --------------------------------------------------------

#: Pytania zdrowotne są OPCJONALNE i każde ma odpowiedź „wolę nie odpowiadać”
#: (decyzja właściciela z 14.09). Brak odpowiedzi nie zapala żadnej flagi.
ODP_ZDR_NIE = "Nie"
ODP_ZDR_TAK = "Tak"
ODP_ZDR_WOLE_NIE = "Wolę nie odpowiadać"
OPCJE_ZDROWIE = (ODP_ZDR_NIE, ODP_ZDR_TAK, ODP_ZDR_WOLE_NIE)

#: Pytanie o zaburzenia odżywiania zostaje przy czterech odpowiedziach z 0.62.0:
#: „Wolę omówić z trenerem” pełni tu rolę „wolę nie odpowiadać”, ale — decyzja
#: właściciela nr 2 — RAZEM z „Nie wiem” dalej ukrywa liczby przed klientem.
#: Piąta odpowiedź „wolę nie odpowiadać” bez flagi otwierałaby obejście tej ochrony.
ODP_ZAB_NIE = "Nie zgłaszam"
ODP_ZAB_TAK = "Tak, obecnie lub w przeszłości"
ODP_ZAB_NIE_WIEM = "Nie wiem"
ODP_ZAB_OMOWIC = "Wolę omówić z trenerem"
OPCJE_ZABURZENIA = (ODP_ZAB_NIE, ODP_ZAB_TAK, ODP_ZAB_NIE_WIEM, ODP_ZAB_OMOWIC)
ODP_ZABURZENIA_FLAGA = (ODP_ZAB_TAK, ODP_ZAB_NIE_WIEM, ODP_ZAB_OMOWIC)

# --- flagi (spec §6.4) ------------------------------------------------------------------

FLAGA_MALOLETNI = "MALOLETNI"
FLAGA_CIAZA = "CIAZA_KARMIENIE"
FLAGA_CHOROBA = "CHOROBA_METABOLICZNA"
FLAGA_LEKI = "LEKI"
FLAGA_ZABURZENIA = "ZABURZENIA_ODZYWIANIA"
FLAGA_BRAK_MIESIACZKI = "BRAK_MIESIACZKI"
FLAGA_DEFICYT_OGRANICZONY = "DEFICYT_OGRANICZONY"
FLAGA_DEFICYT_WYLACZONY = "DEFICYT_WYLACZONY"
FLAGA_BMI_SKRAJNE = "BMI_SKRAJNE"

#: Flagi, które wynikają z odpowiedzi domeny zdrowotnej — trener bez zgody
#: `DOMAIN_HEALTH` ich nie widzi (ukrycie w `zapotrzebowanie_serwis.widok`).
#: `DEFICYT_WYLACZONY` też, bo wynika wyłącznie z ciąży albo braku miesiączki.
FLAGI_ZDROWOTNE = frozenset({FLAGA_CIAZA, FLAGA_CHOROBA, FLAGA_LEKI, FLAGA_ZABURZENIA,
                             FLAGA_BRAK_MIESIACZKI, FLAGA_DEFICYT_WYLACZONY})
#: Flagi, przy których klient nie dostaje żadnej liczby wyniku.
FLAGI_UKRYWAJACE_WYNIK = frozenset({FLAGA_MALOLETNI, FLAGA_ZABURZENIA})


@dataclass(frozen=True)
class OpisFlagi:
    etykieta: str
    trener: str
    #: Tekst dla klienta; None = flagi nie pokazujemy klientowi.
    klient: str | None
    poziom: str  # "warn" | "info"


FLAGI_OPIS: dict[str, OpisFlagi] = {
    FLAGA_MALOLETNI: OpisFlagi(
        "Osoba niepełnoletnia",
        "Wynik policzony, ale wzory są dla dorosłych. Wymagana zgoda opiekuna i ostrożność; "
        "klient nie widzi liczb.", None, "warn"),
    FLAGA_CIAZA: OpisFlagi(
        "Ciąża lub karmienie piersią",
        "Deficyt wyłączony. Zapotrzebowanie w ciąży i przy karmieniu ustala się z lekarzem "
        "albo dietetykiem prowadzącym — plan redukcyjny jest tu przeciwwskazany.",
        "Przy ciąży i karmieniu nie proponujemy deficytu — kalorie ustalcie z lekarzem.", "warn"),
    FLAGA_CHOROBA: OpisFlagi(
        "Zdiagnozowana choroba metaboliczna",
        "Wynik liczony normalnie, ale skonsultuj plan z lekarzem prowadzącym — tarczyca, cukrzyca, "
        "nerki i wątroba zmieniają zarówno zapotrzebowanie, jak i dopuszczalne makro.", None, "warn"),
    FLAGA_LEKI: OpisFlagi(
        "Leki wpływające na masę ciała",
        "Wynik liczony normalnie, ale skonsultuj plan z lekarzem prowadzącym — leki mogą zmieniać "
        "apetyt, gospodarkę wodną i tempo zmian.", None, "warn"),
    FLAGA_ZABURZENIA: OpisFlagi(
        "Zaburzenia odżywiania — obecnie lub w przeszłości",
        "Klient nie widzi żadnych liczb do czasu Waszej rozmowy. Liczenie kalorii bywa tu szkodliwe; "
        "rozważ pracę bez liczb i konsultację specjalistyczną.", None, "warn"),
    FLAGA_BRAK_MIESIACZKI: OpisFlagi(
        "Brak miesiączki powyżej 3 miesięcy",
        "Deficyt wyłączony domyślnie. Możliwy zespół względnego niedoboru energii (RED-S) — "
        "skieruj do lekarza przed jakimkolwiek ograniczaniem kalorii.",
        "Nie proponujemy deficytu — najpierw warto to sprawdzić u lekarza.", "warn"),
    FLAGA_DEFICYT_OGRANICZONY: OpisFlagi(
        "Deficyt ograniczony do minimum",
        "Wybrane tempo dawało cel poniżej bezpiecznej granicy — cel podniesiono do granicy. "
        "Niższy cel wymaga konsultacji dietetycznej albo lekarskiej.",
        "Twój cel podnieśliśmy do bezpiecznej granicy — niżej schodzi się tylko pod opieką "
        "specjalisty.", "info"),
    FLAGA_DEFICYT_WYLACZONY: OpisFlagi(
        "Deficyt wyłączony",
        "Z odpowiedzi zdrowotnych wynika, że deficyt jest tu przeciwwskazany — cel ustawiono "
        "na poziomie zapotrzebowania.", None, "warn"),
    FLAGA_BMI_SKRAJNE: OpisFlagi(
        "BMI poza zakresem 17–40",
        "Wzory na przemianę materii mają w tym zakresie ograniczoną trafność — traktuj wynik jako "
        "bardzo zgrubny punkt wyjścia.",
        "Przy Twoim BMI wzory są mniej dokładne — wynik potraktuj jako zgrubny punkt wyjścia.",
        "info"),
}

OSTRZEZENIE_MIN_KCAL = ("Cel zszedł do minimum bezpieczeństwa ({minimum} kcal). Niższych kalorii nie "
                        "proponujemy — taki plan wymaga konsultacji dietetycznej albo lekarskiej.")
OSTRZEZENIE_PPM = ("Cel został podniesiony do granicy {granica} kcal — deficyt nie schodzi poniżej "
                   "1,1 × przemiany podstawowej bez decyzji specjalisty.")
OSTRZEZENIE_SZYBKA_MASA = ("Tempo „szybkie” przy budowie masy oznacza więcej tkanki tłuszczowej na "
                           "każdy kilogram mięśni. Rozważcie tempo umiarkowane.")
OSTRZEZENIE_ROZJAZD_PPM = ("Mifflin i Katch-McArdle różnią się o {roznica} % — przy nietypowym składzie "
                           "ciała użyto Katch-McArdle. Warto sprawdzić pomiar % tkanki tłuszczowej.")


class BrakDanych(ValueError):
    """Brakuje wejścia albo jest poza zakresem; `pola` wskazuje które."""

    def __init__(self, pola: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in pola.items()))
        self.pola = pola


@dataclass(frozen=True)
class Wejscie:
    """Wejścia wzoru — kody, nie etykiety (`z_odpowiedzi` tłumaczy)."""

    plec: str                       # "F" | "M"
    wiek: float
    wzrost_cm: float
    masa_kg: float
    neat: str                       # "neat_1".."neat_4"
    cel: str                        # "cut" | "maintain" | "bulk" | "recomp"
    procent_tluszczu: float | None = None
    kroki: float | None = None      # nadpisuje `neat`, gdy podane
    sila_tydz: int = 0
    sila_minuty: int = 0
    cardio_tydz: int = 0
    cardio_minuty: int = 0
    cardio_intensywnosc: str | None = None   # "light" | "moderate" | "high"
    staz: str | None = None                  # "lt1" | "1_3" | "gt3"
    tempo: str | None = None                 # "gentle" | "moderate" | "fast"
    masa_docelowa_kg: float | None = None
    bialko: str | None = None                # "standard" | "high"
    # Zdrowie (ekran 5) — None = brak odpowiedzi albo „wolę nie odpowiadać”.
    ciaza: bool | None = None
    choroba_metaboliczna: bool | None = None
    leki: bool | None = None
    zaburzenia_odzywiania: bool | None = None
    brak_miesiaczki: bool | None = None


@dataclass(frozen=True)
class Makro:
    bialko_g: int
    tluszcz_g: int
    wegle_g: int
    bialko_pct: int
    tluszcz_pct: int
    wegle_pct: int
    #: Masa, z której liczone jest białko (przy dużym % tłuszczu — beztłuszczowa).
    bialko_z_masy_kg: float


@dataclass(frozen=True)
class Tempo:
    """Oczekiwane tempo i czas (spec §5.4). Dla redukcji tempo jest dodatnie
    (kg w dół na tydzień), dla budowy masy ujemne (kg w górę)."""

    kg_tydzien: float
    kg_tydzien_od: float | None
    kg_tydzien_do: float | None
    #: Realistyczny przyrost mięśni kg/miesiąc ze stażu (tylko budowa masy).
    przyrost_mies_od: float | None = None
    przyrost_mies_do: float | None = None
    #: Orientacyjny czas do masy docelowej w tygodniach.
    tygodni_do_celu: int | None = None


@dataclass(frozen=True)
class Wynik:
    formulas_version: str
    wiek: int
    bmi: float
    ppm_mifflin: int
    ppm_katch: int | None
    ppm_used: int
    ppm_source: str                 # "mifflin_st_jeor" | "katch_mcardle"
    neat_multiplier: float
    training_kcal_day: int
    tef: int
    cpm: int
    cpm_min: int
    cpm_max: int
    korekta_pct: int
    target_kcal: int
    makro: Makro
    tempo: Tempo
    flags: tuple[str, ...] = ()
    ostrzezenia: tuple[str, ...] = ()
    #: Podstawienie krok po kroku (czytelne wiersze, bez wzorów w UI).
    podstawienie: tuple[str, ...] = field(default_factory=tuple)

    @property
    def pal_efektywny(self) -> float:
        """CPM / PPM — klasyczny współczynnik aktywności, wyłącznie do
        porównań i do kolumny `pal` (silnik 1.0 liczy addytywnie)."""
        return round(self.cpm / self.ppm_used, 2) if self.ppm_used else 0.0


def liczba(tekst: str | None) -> float | None:
    """„72,5” → 72.5; puste / nieliczbowe → None."""
    if tekst is None:
        return None
    t = str(tekst).strip().replace(",", ".").replace(" ", "")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _fmt(x: float) -> str:
    """Do 2 miejsc po przecinku, bez zer końcowych: 70 → „70”, 1,35 → „1,35”."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


# --- wzory ------------------------------------------------------------------------------


def ppm_mifflin(plec: str, masa_kg: float, wzrost_cm: float, wiek: float) -> float:
    """PPM = 10·m + 6,25·h − 5·wiek + 5 (M) / − 161 (K)."""
    if plec not in ("F", "M"):
        raise ValueError(f"Nieznana płeć: {plec!r}")
    return 10.0 * masa_kg + 6.25 * wzrost_cm - 5.0 * wiek + (5.0 if plec == "M" else -161.0)


def ppm_katch(masa_kg: float, procent_tluszczu: float) -> float:
    """PPM = 370 + 21,6 · masa beztłuszczowa."""
    return 370.0 + 21.6 * masa_kg * (1 - procent_tluszczu / 100.0)


def neat_z_krokow(kroki: float) -> float:
    """1,20 + 0,04 · (kroki/1000 − 4), ograniczone do [1,15; 1,85]."""
    return min(NEAT_KROKI_MAX, max(NEAT_KROKI_MIN, 1.20 + 0.04 * (kroki / 1000.0 - 4)))


def kcal_treningu_dzien(masa_kg: float, sesje: list[tuple[str, int, int]]) -> float:
    """`sesje`: lista (rodzaj MET, sesji w tygodniu, minut na sesję)."""
    return sum(n * m * MET[k] * masa_kg * KCAL_MIN_KG for k, n, m in sesje) / 7


def _sesje(w: Wejscie) -> list[tuple[str, int, int]]:
    sesje: list[tuple[str, int, int]] = [("strength", w.sila_tydz or 0, w.sila_minuty or 0)]
    if w.cardio_tydz:
        sesje.append((f"cardio_{w.cardio_intensywnosc}", w.cardio_tydz, w.cardio_minuty))
    return sesje


def _sprawdz(w: Wejscie) -> None:
    bledy: dict[str, str] = {}
    if w.plec not in ("F", "M"):
        bledy["plec"] = "brak lub nieznana"
    for nazwa, wart, (lo, hi) in (("wiek", w.wiek, ZAKRES_WIEK), ("wzrost_cm", w.wzrost_cm, ZAKRES_WZROST),
                                  ("masa_kg", w.masa_kg, ZAKRES_MASA)):
        if wart is None or not (lo <= wart <= hi):
            bledy[nazwa] = f"poza zakresem {_fmt(lo)}–{_fmt(hi)}"
    if w.procent_tluszczu is not None and not (ZAKRES_TLUSZCZ[0] <= w.procent_tluszczu <= ZAKRES_TLUSZCZ[1]):
        bledy["procent_tluszczu"] = f"poza zakresem {_fmt(ZAKRES_TLUSZCZ[0])}–{_fmt(ZAKRES_TLUSZCZ[1])}"
    if w.kroki is None and w.neat not in NEAT:
        bledy["neat"] = "brak lub nieznana aktywność poza treningiem"
    if w.kroki is not None and not (ZAKRES_KROKI[0] <= w.kroki <= ZAKRES_KROKI[1]):
        bledy["kroki"] = f"poza zakresem {_fmt(ZAKRES_KROKI[0])}–{_fmt(ZAKRES_KROKI[1])}"
    for nazwa, wart in (("sila_tydz", w.sila_tydz), ("cardio_tydz", w.cardio_tydz)):
        if wart is None or not (ZAKRES_SESJE[0] <= wart <= ZAKRES_SESJE[1]):
            bledy[nazwa] = "poza zakresem 0–7"
    if w.sila_tydz and not w.sila_minuty:
        bledy["sila_minuty"] = "brak czasu treningu siłowego"
    if w.cardio_tydz and not w.cardio_minuty:
        bledy["cardio_minuty"] = "brak czasu cardio"
    if w.cardio_tydz and f"cardio_{w.cardio_intensywnosc}" not in MET:
        bledy["cardio_intensywnosc"] = "brak lub nieznana intensywność cardio"
    if w.cel not in KOREKTA and (w.cel, w.tempo) not in KOREKTA:
        if w.cel not in ("cut", "maintain", "bulk", "recomp"):
            bledy["cel"] = "brak lub nieznany"
        elif w.cel in CELE_Z_TEMPEM and w.tempo not in ("gentle", "moderate", "fast"):
            bledy["tempo"] = "brak lub nieznane tempo"
    if w.masa_docelowa_kg is not None and not (
            ZAKRES_MASA_DOCELOWA[0] <= w.masa_docelowa_kg <= ZAKRES_MASA_DOCELOWA[1]):
        bledy["masa_docelowa_kg"] = f"poza zakresem {_fmt(ZAKRES_MASA_DOCELOWA[0])}–{_fmt(ZAKRES_MASA_DOCELOWA[1])}"
    if bledy:
        raise BrakDanych(bledy)


def _flagi_zdrowotne(w: Wejscie) -> list[str]:
    return [f for pole, f in ((w.ciaza, FLAGA_CIAZA), (w.choroba_metaboliczna, FLAGA_CHOROBA),
                              (w.leki, FLAGA_LEKI), (w.zaburzenia_odzywiania, FLAGA_ZABURZENIA),
                              (w.brak_miesiaczki, FLAGA_BRAK_MIESIACZKI)) if pole]


def _makro(w: Wejscie, *, cel_kcal: float) -> Makro:
    lo, hi = BIALKO_G_KG[w.cel]
    g_kg = hi if w.bialko == "high" else lo
    ref_kg = w.masa_kg
    if w.cel == "cut" and (w.procent_tluszczu or 0) > 30:
        # Przy wysokim % tłuszczu białko liczone z masy docelowej albo ~LBM/0,75.
        ref_kg = w.masa_docelowa_kg or w.masa_kg * (1 - w.procent_tluszczu / 100.0) / 0.75
    bialko = g_kg * ref_kg
    tluszcz = max(TLUSZCZ_G_KG[w.cel] * w.masa_kg, TLUSZCZ_MIN_PCT_KCAL * cel_kcal / 9)
    wegle = max(0.0, (cel_kcal - 4 * bialko - 9 * tluszcz) / 4)
    def pct(g: float, kcal_g: int) -> int:
        return round(100 * g * kcal_g / cel_kcal) if cel_kcal else 0
    return Makro(bialko_g=round(bialko), tluszcz_g=round(tluszcz), wegle_g=round(wegle),
                 bialko_pct=pct(bialko, 4), tluszcz_pct=pct(tluszcz, 9), wegle_pct=pct(wegle, 4),
                 bialko_z_masy_kg=round(ref_kg, 1))


def _zakres_tempa(kg_tydzien: float) -> tuple[float | None, float | None]:
    """„~0,4–0,5 kg tygodniowo” — dół i góra zaokrąglone do 0,1 kg
    (odtwarza przykład ze spec §6.1: deficyt 470 kcal/dzień → 0,4–0,5)."""
    if abs(kg_tydzien) < 0.05:
        return None, None
    x = abs(kg_tydzien)
    od = math.floor(x * 10) / 10
    do = math.ceil(x * 10) / 10
    if do <= od:
        do = round(od + 0.1, 1)
    return round(od, 1), round(do, 1)


def _tempo(w: Wejscie, *, cpm: float, cel_kcal: float) -> Tempo:
    kg_tydzien = (cpm - cel_kcal) * 7 / KCAL_NA_KG
    od, do = _zakres_tempa(kg_tydzien)
    przyrost_od = przyrost_do = None
    if w.cel == "bulk" and w.staz in PRZYROST_PCT_MIES:
        p_od, p_do = PRZYROST_PCT_MIES[w.staz]
        przyrost_od, przyrost_do = round(w.masa_kg * p_od / 100, 2), round(w.masa_kg * p_do / 100, 2)
    tygodni = None
    if w.masa_docelowa_kg and abs(kg_tydzien) >= 0.05:
        roznica = w.masa_kg - w.masa_docelowa_kg
        # Tempo i kierunek muszą się zgadzać: redukcja do wyższej masy nie ma czasu do celu.
        if (roznica > 0) == (kg_tydzien > 0) and abs(roznica) >= 0.1:
            tygodni = max(1, round(abs(roznica) / abs(kg_tydzien)))
    return Tempo(kg_tydzien=round(kg_tydzien, 2), kg_tydzien_od=od, kg_tydzien_do=do,
                 przyrost_mies_od=przyrost_od, przyrost_mies_do=przyrost_do, tygodni_do_celu=tygodni)


def oblicz(w: Wejscie) -> Wynik:
    """Pełne wyliczenie z podstawieniem. `BrakDanych` przy niepełnym wejściu.
    Liczby 1:1 z referencyjną implementacją właściciela; zaokrąglanie
    następuje DOPIERO na wyjściu (wszystkie kroki pośrednie na float)."""
    _sprawdz(w)
    flagi: list[str] = []
    ostrzezenia: list[str] = []
    wiek = int(w.wiek)
    bmi = w.masa_kg / (w.wzrost_cm / 100) ** 2
    if wiek < 18:
        flagi.append(FLAGA_MALOLETNI)
    if bmi < 17 or bmi > 40:
        flagi.append(FLAGA_BMI_SKRAJNE)
    flagi.extend(_flagi_zdrowotne(w))

    ppm_m = ppm_mifflin(w.plec, w.masa_kg, w.wzrost_cm, w.wiek)
    ppm_k = ppm_katch(w.masa_kg, w.procent_tluszczu) if w.procent_tluszczu else None
    uzyj_katch = ppm_k is not None and abs(ppm_k - ppm_m) / ppm_m > 0.10
    ppm = ppm_k if uzyj_katch else ppm_m
    zrodlo = "katch_mcardle" if uzyj_katch else "mifflin_st_jeor"
    if uzyj_katch and ppm_k is not None:
        ostrzezenia.append(OSTRZEZENIE_ROZJAZD_PPM.format(roznica=round(100 * abs(ppm_k - ppm_m) / ppm_m)))

    neat = neat_z_krokow(w.kroki) if w.kroki else NEAT[w.neat]
    trening = kcal_treningu_dzien(w.masa_kg, _sesje(w))
    baza = ppm * neat + trening
    cpm = baza * 1.10  # TEF 10 %

    tempo_kod = w.tempo if w.cel in CELE_Z_TEMPEM else None
    korekta = KOREKTA[(w.cel, tempo_kod)]
    if FLAGA_CIAZA in flagi or FLAGA_BRAK_MIESIACZKI in flagi:
        if korekta < 0.0:
            # Flaga tylko wtedy, gdy deficyt naprawdę został wyłączony — inaczej
            # trener czytałby „deficyt wyłączony” przy celu bez deficytu.
            flagi.append(FLAGA_DEFICYT_WYLACZONY)
        korekta = max(korekta, 0.0)
    cel_kcal = cpm * (1 + korekta)
    minimum = MIN_KCAL[w.plec]
    podloga = max(ppm * PPM_MNOZNIK_PODLOGI, minimum)
    if w.cel in ("cut", "recomp") and cel_kcal < podloga:
        cel_kcal = podloga
        flagi.append(FLAGA_DEFICYT_OGRANICZONY)
        ostrzezenia.append(OSTRZEZENIE_MIN_KCAL.format(minimum=minimum) if podloga == minimum
                           else OSTRZEZENIE_PPM.format(granica=round(podloga)))
    if w.cel == "bulk" and tempo_kod == "fast":
        ostrzezenia.append(OSTRZEZENIE_SZYBKA_MASA)

    makro = _makro(w, cel_kcal=cel_kcal)
    tempo = _tempo(w, cpm=cpm, cel_kcal=cel_kcal)
    wynik = Wynik(
        formulas_version=FORMULAS_VERSION, wiek=wiek, bmi=round(bmi, 1),
        ppm_mifflin=round(ppm_m), ppm_katch=round(ppm_k) if ppm_k is not None else None,
        ppm_used=round(ppm), ppm_source=zrodlo, neat_multiplier=round(neat, 3),
        training_kcal_day=round(trening), tef=round(cpm - baza), cpm=round(cpm),
        cpm_min=round(cpm * 0.93), cpm_max=round(cpm * 1.07), korekta_pct=round(korekta * 100),
        target_kcal=round(cel_kcal), makro=makro, tempo=tempo,
        flags=tuple(flagi), ostrzezenia=tuple(ostrzezenia),
    )
    return replace(wynik, podstawienie=_podstawienie(w, wynik, neat=neat, ppm=ppm))


def _podstawienie(w: Wejscie, y: Wynik, *, neat: float, ppm: float) -> tuple[str, ...]:
    """Rozbicie z podstawionymi liczbami — spec §6.2 wymaga, żeby trener
    widział, skąd wzięła się każda składowa CPM."""
    plec_pl = "mężczyzna" if w.plec == "M" else "kobieta"
    stala = "+ 5" if w.plec == "M" else "− 161"
    wiersze = [
        (f"PPM (Mifflin-St Jeor, {plec_pl}): 10 × {_fmt(w.masa_kg)} kg + 6,25 × {_fmt(w.wzrost_cm)} cm "
         f"− 5 × {y.wiek} lat {stala} = {y.ppm_mifflin} kcal"),
    ]
    if y.ppm_katch is not None:
        lbm = w.masa_kg * (1 - (w.procent_tluszczu or 0) / 100)
        wiersze.append(f"PPM (Katch-McArdle, {_fmt(w.procent_tluszczu or 0)} % tłuszczu): "
                       f"370 + 21,6 × {_fmt(round(lbm, 1))} kg masy beztłuszczowej = {y.ppm_katch} kcal")
        wiersze.append("użyty wzór: " + ("Katch-McArdle (różnica ponad 10 %)" if y.ppm_source == "katch_mcardle"
                                         else "Mifflin-St Jeor (różnica do 10 %)")
                       + f" → {y.ppm_used} kcal")
    if w.kroki:
        wiersze.append(f"NEAT z kroków ({_fmt(w.kroki)} dziennie): 1,20 + 0,04 × ({_fmt(w.kroki / 1000)} − 4) "
                       f"= {_fmt(neat)}")
    else:
        wiersze.append(f"NEAT (aktywność poza treningiem): {_fmt(neat)}")
    wiersze.append(f"PPM × NEAT = {y.ppm_used} × {_fmt(neat)} = {round(ppm * neat)} kcal")
    for rodzaj, n, m in _sesje(w):
        if not n or not m:
            continue
        nazwa = {"strength": "siłowy", "cardio_light": "cardio lekkie",
                 "cardio_moderate": "cardio umiarkowane", "cardio_high": "cardio wysokie"}[rodzaj]
        na_min = MET[rodzaj] * w.masa_kg * KCAL_MIN_KG
        wiersze.append(f"trening {nazwa}: {n} × {m} min × {_fmt(round(na_min, 2))} kcal/min "
                       f"(MET {_fmt(MET[rodzaj])}) ÷ 7 dni")
    wiersze.append(f"trening na dzień = {y.training_kcal_day} kcal")
    wiersze.append(f"TEF (termiczny efekt pożywienia, 10 %) = {y.tef} kcal")
    wiersze.append(f"CPM = ({round(ppm * neat)} + {y.training_kcal_day}) × 1,10 = {y.cpm} kcal "
                   f"(zakres {y.cpm_min}–{y.cpm_max})")
    if y.korekta_pct == 0:
        wiersze.append(f"cel: {_nazwa_celu(w.cel)} → bez korekty = {y.target_kcal} kcal")
    else:
        znak = "−" if y.korekta_pct < 0 else "+"
        tempo_txt = f", tempo {_nazwa_tempa(w.tempo)}" if w.cel in CELE_Z_TEMPEM and w.tempo else ""
        wiersze.append(f"cel: {_nazwa_celu(w.cel)}{tempo_txt} → {y.cpm} {znak} {abs(y.korekta_pct)} % "
                       f"= {y.target_kcal} kcal")
    if FLAGA_DEFICYT_OGRANICZONY in y.flags:
        wiersze.append(f"cel podniesiony do granicy bezpieczeństwa: {y.target_kcal} kcal "
                       f"(nie mniej niż 1,1 × PPM i nie mniej niż {MIN_KCAL[w.plec]} kcal)")
    wiersze.append(f"makro: białko {y.makro.bialko_g} g · tłuszcz {y.makro.tluszcz_g} g · "
                   f"węglowodany {y.makro.wegle_g} g")
    return tuple(wiersze)


def _nazwa_celu(kod: str) -> str:
    return {"cut": "redukcja tkanki tłuszczowej", "maintain": "utrzymanie masy ciała",
            "bulk": "budowa masy mięśniowej", "recomp": "rekompozycja"}.get(kod, kod)


def _nazwa_tempa(kod: str | None) -> str:
    return {"gentle": "łagodne", "moderate": "umiarkowane", "fast": "szybkie"}.get(kod or "", "")


# --- mapa odpowiedzi wywiadu → wejście --------------------------------------------------

def _bool_zdrowie(wartosc: str | None, *, tak: tuple[str, ...] = (ODP_ZDR_TAK,)) -> bool | None:
    """None = brak odpowiedzi albo „wolę nie odpowiadać” (deklaracji nie ma,
    więc i flagi nie ma); True = któraś z odpowiedzi z `tak`; False = „nie”."""
    v = (wartosc or "").strip()
    if not v or v == ODP_ZDR_WOLE_NIE:
        return None
    return v in tak


def _int(wartosc: str | None) -> int:
    n = liczba(wartosc)
    return int(n) if n is not None else 0


def z_odpowiedzi(wartosci: dict[str, str | None]) -> Wejscie:
    """Mapa odpowiedzi wywiadu (`definicje.wartosci`) → `Wejscie`.
    Brakujące i nieznane → wartości puste (walidacja w `oblicz`)."""
    cel = KOD_CELU.get(wartosci.get("zk_cel") or "", "")
    return Wejscie(
        plec=KOD_PLCI.get(wartosci.get("zk_plec") or "", ""),
        wiek=liczba(wartosci.get("zk_wiek")),  # type: ignore[arg-type]
        wzrost_cm=liczba(wartosci.get("zk_wzrost")),  # type: ignore[arg-type]
        masa_kg=liczba(wartosci.get("zk_masa")),  # type: ignore[arg-type]
        procent_tluszczu=liczba(wartosci.get("zk_tluszcz")),
        neat=KOD_NEAT.get(wartosci.get("zk_neat") or "", ""),
        kroki=liczba(wartosci.get("zk_kroki")),
        sila_tydz=_int(wartosci.get("zk_sila_tydz")),
        sila_minuty=KOD_MINUT.get(wartosci.get("zk_sila_minuty") or "", 0),
        cardio_tydz=_int(wartosci.get("zk_cardio_tydz")),
        cardio_minuty=KOD_MINUT.get(wartosci.get("zk_cardio_minuty") or "", 0),
        cardio_intensywnosc=KOD_INTENSYWNOSCI.get(wartosci.get("zk_cardio_intensywnosc") or ""),
        staz=KOD_STAZU.get(wartosci.get("zk_staz") or ""),
        cel=cel,
        tempo=KOD_TEMPA.get(wartosci.get("zk_tempo") or "") if cel in CELE_Z_TEMPEM else None,
        masa_docelowa_kg=liczba(wartosci.get("zk_masa_docelowa")),
        bialko=KOD_BIALKA.get(wartosci.get("zk_bialko") or ""),
        ciaza=_bool_zdrowie(wartosci.get("zk_ciaza")),
        choroba_metaboliczna=_bool_zdrowie(wartosci.get("zk_choroba")),
        leki=_bool_zdrowie(wartosci.get("zk_leki")),
        zaburzenia_odzywiania=_bool_zdrowie(wartosci.get("zk_zaburzenia"), tak=ODP_ZABURZENIA_FLAGA),
        brak_miesiaczki=_bool_zdrowie(wartosci.get("zk_miesiaczka")),
    )

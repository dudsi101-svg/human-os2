"""Rejestr reguł wyjaśnień: wymagane fakty, kontrole spójności i
deterministyczne szablony tekstu po polsku.

Zasady (plik 03, „Przykładowe reguły renderowania” i 04, „Reguły
językowe”): tekst wypełnia się WYŁĄCZNIE dozwolonymi faktami ze śladu;
nie wymyśla się następnej daty oceny; reguła produktu nie jest
przedstawiana jako wynik badania; decyzja specjalisty zachowuje
oryginalną notatkę; wybór użytkownika jest nazwany wyborem użytkownika
i nie jest oceniany jako bezpieczny tylko dlatego, że go wybrano.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .slad import JEDNOSTKI


@dataclass(frozen=True)
class Regula:
    id: str
    wymagane: tuple[str, ...]
    wersje: frozenset[str] = frozenset({"1.0"})
    #: Czy `data_quality=partial` jest obsługiwane (reguła sama wie, czego
    #: brakuje). Domyślnie nie — `partial` daje `insufficient_data`.
    czesciowe_dozwolone: bool = False
    #: Klucze faktów, które muszą być wartościami logicznymi.
    logiczne: tuple[str, ...] = ()
    #: Klucze faktów liczbowych nieujemnych.
    nieujemne: tuple[str, ...] = ()
    #: Powiązane karty, gdy ślad nie wskazuje własnych.
    artykuly: tuple[str, ...] = ()
    #: Etykiety akcji (label, type, target) generowane po stronie serwera.
    akcje: tuple[tuple[str, str, str | None], ...] = field(default_factory=tuple)


REGULY: dict[str, Regula] = {
    "H_PROGRESS": Regula(
        id="H_PROGRESS",
        wymagane=("planned_sets", "reps_max", "completed_reps", "all_rir_met",
                  "technique_ok", "pain_reported"),
        logiczne=("all_rir_met", "technique_ok", "pain_reported"),
        nieujemne=("planned_sets", "reps_max"),
        artykuly=("k-progress",),
        akcje=(("Zobacz ostatni trening", "open_source_view", "/plan"),
               ("Jak działa progresja", "open_article", "k-progress")),
    ),
    "H_LAYOUT": Regula(
        id="H_LAYOUT",
        wymagane=("days_per_week", "level", "commitment", "layout_id", "session_count"),
        nieujemne=("days_per_week", "session_count"),
        artykuly=("k-frequency",),
        akcje=(("Dlaczego plan ma taką liczbę treningów", "open_article", "k-frequency"),),
    ),
    "H_VOLUME": Regula(
        id="H_VOLUME",
        wymagane=("exercise_id", "sets", "reps_min", "reps_max", "rir_by_week",
                  "rest_seconds", "level", "commitment"),
        nieujemne=("sets", "reps_min", "reps_max", "rest_seconds"),
        artykuly=("k-sets", "k-rir", "k-rest"),
        akcje=(("Co oznaczają serie i powtórzenia", "open_article", "k-sets"),
               ("Jak rozumieć zapas powtórzeń", "open_article", "k-rir")),
    ),
    "ENERGY_INITIAL": Regula(
        id="ENERGY_INITIAL",
        wymagane=("method_label", "calculated_value", "unit", "assumption_summary"),
        nieujemne=("calculated_value",),
        artykuly=("k-energy",),
        akcje=(("Skąd bierze się cel kaloryczny", "open_article", "k-energy"),),
    ),
    "MEAL_PREFERENCE": Regula(
        id="MEAL_PREFERENCE",
        wymagane=("preference_label", "matching_result"),
        artykuly=("k-meal",),
        akcje=(("Dlaczego wybrano ten posiłek", "open_article", "k-meal"),),
    ),
    # Kreator dań (0.57.0): ślad z silnika referencyjnego — wybór całego,
    # zatwierdzonego wariantu receptury (bez optymalizacji składników).
    "CURATED_VARIANT_SELECTION": Regula(
        id="CURATED_VARIANT_SELECTION",
        wymagane=("animal_policy", "pattern", "time_limit", "recipe_status", "recipe_name",
                  "family_id", "portion_variant", "slot"),
        wersje=frozenset({"1.0"}),
        nieujemne=("time_limit",),
        artykuly=("k-meal", "k-portion"),
        akcje=(("Dlaczego wybrano ten posiłek", "open_article", "k-meal"),
               ("Jak czytać porcję w jadłospisie", "open_article", "k-portion")),
    ),
    # Cardio z suwakami (0.73.0): ślad z silnika `cardio_model_v1` — wagi celów,
    # zakres tętna w %HRmax, RPE, czas, struktura; bez danych zdrowotnych.
    "H_CARDIO": Regula(
        id="H_CARDIO",
        wymagane=("goal_redukcja", "goal_wydolnosc", "goal_regeneracja", "level", "hrmax_source",
                  "hr_pct_min", "hr_pct_max", "rpe_min", "rpe_max", "duration_min", "structure",
                  "model_version"),
        nieujemne=("goal_redukcja", "goal_wydolnosc", "goal_regeneracja", "hr_pct_min", "hr_pct_max",
                   "rpe_min", "rpe_max", "duration_min"),
        artykuly=("k-cardio",),
        akcje=(("Jak czytać zakres tętna i RPE", "open_article", "k-cardio"),),
    ),
}

#: Szablony dla pochodzenia innego niż silnik (rule_id = null).
USER_SELECTION = Regula(
    id="USER_SELECTION", wymagane=("selected_value", "selected_at"),
    artykuly=("k-frequency",),
)
PROFESSIONAL_NOTE = Regula(id="PROFESSIONAL_NOTE", wymagane=())


def regula_dla(trace: dict) -> Regula | None:
    """Reguła właściwa dla śladu albo None (nieznana / brak wersji)."""
    origin = trace.get("decision_origin")
    if origin == "engine":
        r = REGULY.get(trace.get("rule_id") or "")
        if r is None or trace.get("rule_version") not in r.wersje:
            return None
        return r
    if origin == "user":
        return USER_SELECTION
    if origin == "professional":
        return PROFESSIONAL_NOTE
    return None


# --- kontrole ---------------------------------------------------------------


def _fakty(trace: dict) -> dict[str, dict]:
    return {f["key"]: f for f in trace.get("facts", [])}


def sprawdz(regula: Regula, trace: dict) -> tuple[str | None, str]:
    """Zwraca (status_bledu | None, powód). Statusy: `insufficient_data`
    (brak faktu / niepełne dane), `inconsistent_data` (fakt sprzeczny z
    wynikiem, zła jednostka, zły typ)."""
    fakty = _fakty(trace)
    klucze = [f["key"] for f in trace.get("facts", [])]
    if len(set(klucze)) != len(klucze):
        return "inconsistent_data", "powtórzone klucze faktów"
    for f in trace.get("facts", []):
        if f.get("unit") not in JEDNOSTKI:
            return "inconsistent_data", f"nieznana jednostka faktu {f['key']}"
    brak = [k for k in regula.wymagane if k not in fakty or fakty[k]["value"] is None]
    if brak:
        return "insufficient_data", "brak faktów: " + ", ".join(brak)
    for k in regula.logiczne:
        if not isinstance(fakty[k]["value"], bool):
            return "inconsistent_data", f"fakt {k} nie jest wartością logiczną"
    for k in regula.nieujemne:
        v = fakty[k]["value"]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            return "inconsistent_data", f"fakt {k} nie jest liczbą nieujemną"
    if regula.id == "PROFESSIONAL_NOTE":
        if (trace.get("reason_note") or "").strip():
            return None, ""
        return "insufficient_data", "decyzja specjalisty bez zapisanej notatki"
    if regula.id == "H_PROGRESS":
        return _sprawdz_h_progress(fakty, trace)
    if regula.id == "H_VOLUME":
        rir = fakty["rir_by_week"]["value"]
        if not isinstance(rir, list) or not rir or any(
                isinstance(x, bool) or not isinstance(x, (int, float)) or x < 0 for x in rir):
            return "inconsistent_data", "rir_by_week nie jest listą liczb nieujemnych"
        if fakty["reps_min"]["value"] > fakty["reps_max"]["value"]:
            return "inconsistent_data", "reps_min większe od reps_max"
        if trace.get("outcome_value") != fakty["sets"]["value"]:
            return "inconsistent_data", "wynik nie zgadza się z liczbą serii"
    if regula.id == "H_CARDIO":
        suma = sum(int(fakty[k]["value"]) for k in ("goal_redukcja", "goal_wydolnosc", "goal_regeneracja"))
        if abs(suma - 100) > 1:
            return "inconsistent_data", "wagi celów nie sumują się do 100 %"
        if fakty["hr_pct_min"]["value"] > fakty["hr_pct_max"]["value"]:
            return "inconsistent_data", "hr_pct_min większe od hr_pct_max"
        if trace.get("outcome_value") != fakty["duration_min"]["value"]:
            return "inconsistent_data", "wynik nie zgadza się z czasem sesji"
    if (regula.id == "ENERGY_INITIAL"
            and trace.get("outcome_value") != fakty["calculated_value"]["value"]):
        return "inconsistent_data", "wynik nie zgadza się z obliczoną wartością"
    return None, ""


def _sprawdz_h_progress(fakty: dict[str, dict], trace: dict) -> tuple[str | None, str]:
    planned = fakty["planned_sets"]["value"]
    completed = fakty["completed_reps"]["value"]
    if not isinstance(completed, list) or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or x < 0 for x in completed):
        return "inconsistent_data", "completed_reps nie jest listą liczb nieujemnych"
    if len(completed) != planned:
        # Niepełna liczba zapisanych serii: nie wiemy, co się stało w
        # brakujących — nie twierdzimy, że wszystko było poprawnie (K04, F14).
        return "insufficient_data", "liczba zapisanych serii różni się od zaplanowanej"
    if trace.get("outcome_code") == "hold_reps":
        if trace.get("outcome_value") != "keep_load":
            return "inconsistent_data", "hold_reps wymaga wyniku keep_load"
        if fakty["pain_reported"]["value"] is True:
            # Przy bólu nie wolno mówić, że jedyną przeszkodą są powtórzenia (K05, F15).
            return "inconsistent_data", "zgłoszony ból sprzeczny z powodem hold_reps"
        if fakty["technique_ok"]["value"] is False:
            return "inconsistent_data", "technika nie była OK, a powód mówi o powtórzeniach"
        reps_max = fakty["reps_max"]["value"]
        if fakty["all_rir_met"]["value"] and all(x >= reps_max for x in completed):
            return "inconsistent_data", "wszystkie serie na górnym końcu zakresu, a wynik to utrzymanie"
    return None, ""


# --- renderowanie -----------------------------------------------------------


def _lista_pl(wartosci: list[Any]) -> str:
    s = [str(v) for v in wartosci]
    if len(s) <= 1:
        return "".join(s)
    return ", ".join(s[:-1]) + " i " + s[-1]


def _z_jednostka(f: dict) -> str:
    j = JEDNOSTKI.get(f.get("unit")) or ""
    return f"{f['value']} {j}".strip()


POZIOMY = {"beginner": "początkujący", "intermediate": "średniozaawansowany",
           "advanced": "zaawansowany"}
ZAANGAZOWANIE = {"minimum": "minimalne", "standard": "standardowe", "maximum": "maksymalne"}
POZIOMY_KATALOGU = {"POCZATKUJACY": "początkujący", "SREDNIOZAAWANSOWANY": "średniozaawansowany",
                    "ZAAWANSOWANY": "zaawansowany"}
ZRODLA_HRMAX = {"tanaka": "tętno maksymalne z wzoru wiekowego (±10 ud./min)",
                "karvonen": "tętno z rezerwy tętna (wzór wiekowy + tętno spoczynkowe)",
                "none": "bez wzoru na tętno (RPE i test mowy)"}
KOREKTY_OPIS = {
    "LOW_RECOVERY_ADJUSTMENT": "objętość obniżono z powodu zadeklarowanej niskiej regeneracji",
    "RETURN_AFTER_BREAK": "po przerwie w treningu serie i zapas są ostrożniejsze",
    "TIME_FIT_SET_REMOVED": "liczbę serii ograniczono do limitu czasu sesji",
    "TIME_FIT_DROPPED": "część ćwiczeń pominięto, żeby zmieścić się w czasie sesji",
    "PROVISIONAL_LOADS": "ciężary są do doboru na miejscu (brak historii)",
    "MISSING_VOLUME_HISTORY": "bez historii objętości dawka jest startowa",
    "PRIORITY_SHIFT": "priorytet mięśniowy przesunął część serii bez zwiększania pracy",
    "BEGINNER_HIGH_FREQUENCY": "częstotliwość jest wysoka jak na start — plan to sygnalizuje",
    "ONE_DAY_COMPROMISE": "przy jednym dniu w tygodniu układ jest kompromisem",
}


def renderuj(regula: Regula, trace: dict, *, historia: bool) -> tuple[list[str], list[str]]:
    """Zwraca (akapity, użyte klucze faktów). Akapity zaczynają się od
    nazwy sekcji z ekranu W4: Decyzja / Co na nią wpłynęło / Kiedy to się
    zmieni. Żadne zdanie nie wykracza poza fakty śladu."""
    fakty = _fakty(trace)
    uzyte: list[str] = []

    def f(k: str) -> Any:
        uzyte.append(k)
        return fakty[k]["value"]

    prefiks = "Historia: " if historia else ""
    if regula.id == "PROFESSIONAL_NOTE":
        return ([
            f"{prefiks}Decyzja: uzasadnienie autora planu — „{trace['reason_note'].strip()}”.",
            (f"Co na nią wpłynęło: notatka zapisana przy wersji {trace['plan_revision']} planu. "
            "To decyzja człowieka, nie wynik algorytmu."),
            "Kiedy to się zmieni: przy kolejnej wersji planu; każda zmiana zostaje w historii.",
        ], uzyte)
    if regula.id == "USER_SELECTION":
        wartosc = _z_jednostka(fakty["selected_value"])
        uzyte.append("selected_value")
        kiedy = f("selected_at")
        return ([
            f"{prefiks}Decyzja: ustawienie wybrane przez Ciebie — {wartosc} (zapisane {kiedy}).",
            ("Co na nią wpłynęło: Twój wybór. Aplikacja nie ocenia go jako bezpiecznego "
            "tylko dlatego, że został wybrany."),
            "Kiedy to się zmieni: gdy zmienisz to ustawienie w planie.",
        ], uzyte)
    if regula.id == "H_PROGRESS":
        completed = f("completed_reps")
        reps_max = f("reps_max")
        if trace.get("outcome_code") == "hold_reps":
            decyzja = "Ciężar pozostaje bez zmian."
            kiedy = (f"Kiedy to się zmieni: zwiększenie jest przewidziane po osiągnięciu "
                     f"{reps_max} powtórzeń w każdej serii, przy wymaganym zapasie i poprawnej technice.")
        else:
            decyzja = "Ciężar rośnie w następnej sesji."
            kiedy = ("Kiedy to się zmieni: przy kolejnej ocenie po następnym treningu — "
                     "reguła produktu, nie pomiar.")
        return ([
            f"{prefiks}Decyzja: {decyzja}",
            (f"Co na nią wpłynęło: w ostatniej sesji zapisano {_lista_pl(completed)} powtórzeń "
            f"przy zakresie do {reps_max}."),
            kiedy,
        ], uzyte)
    if regula.id == "H_LAYOUT":
        dni = f("days_per_week")
        uklad = f("layout_id")
        poziom = POZIOMY.get(f("level"), fakty["level"]["value"])
        zaang = ZAANGAZOWANIE.get(f("commitment"), fakty["commitment"]["value"])
        return ([
            f"{prefiks}Decyzja: plan ma {dni} treningi w tygodniu w układzie {uklad}.",
            (f"Co na nią wpłynęło: zadeklarowana dostępność ({dni} dni), poziom {poziom} "
            f"i zaangażowanie {zaang}. To reguła konfiguratora (heurystyka układu), "
            "nie wynik badania."),
            ("Kiedy to się zmieni: przy zmianie dostępności lub poziomu — trener tworzy "
            "wtedy nową wersję planu."),
        ], uzyte)
    if regula.id == "H_VOLUME":
        sets = f("sets")
        rmin, rmax = f("reps_min"), f("reps_max")
        rir = f("rir_by_week")
        rest = f("rest_seconds")
        poziom = POZIOMY.get(f("level"), fakty["level"]["value"])
        zaang = ZAANGAZOWANIE.get(f("commitment"), fakty["commitment"]["value"])
        korekty = fakty.get("adjustments", {}).get("value") or []
        wplyw = (f"Co na nią wpłynęło: poziom {poziom} i zaangażowanie {zaang}; dawka startowa "
                 f"według reguły konfiguratora (wersja {trace.get('rule_version')}), nie badania.")
        if korekty:
            uzyte.append("adjustments")
            wplyw += " Korekty: " + "; ".join(KOREKTY_OPIS.get(k, k) for k in korekty) + "."
        return ([
            (f"{prefiks}Decyzja: {sets} serie × {rmin}–{rmax} powtórzeń, przerwa {rest} s, "
            f"zapas (RIR) w kolejnych tygodniach: {'/'.join(str(x) for x in rir)}."),
            wplyw,
            ("Kiedy to się zmieni: ciężar rośnie dopiero po wykonaniu wszystkich serii na "
            "górnym końcu zakresu z zadanym zapasem; plan jest do przeglądu po 4 tygodniach."),
        ], uzyte)
    if regula.id == "H_CARDIO":
        wr, ww, wg = f("goal_redukcja"), f("goal_wydolnosc"), f("goal_regeneracja")
        hr_lo, hr_hi = f("hr_pct_min"), f("hr_pct_max")
        rpe_lo, rpe_hi = f("rpe_min"), f("rpe_max")
        czas = f("duration_min")
        strukt = f("structure")
        poziom = POZIOMY_KATALOGU.get(f("level"), fakty["level"]["value"])
        zrodlo = ZRODLA_HRMAX.get(f("hrmax_source"), "bez wzoru na tętno")
        nadpisania = fakty.get("overridden_by_coach", {}).get("value") or []
        wplyw = (f"Co na nią wpłynęło: suwaki celów — Redukcja {wr} %, Wydolność {ww} %, Regeneracja "
                 f"{wg} % — poziom {poziom}, {zrodlo}; struktura: {strukt}. To reguła modelu "
                 f"(wersja {trace.get('rule_version')}: strefy wg progów, rezerwa tętna, interwały "
                 "pod wydolność), nie wynik badania ani porada medyczna.")
        if nadpisania:
            uzyte.append("overridden_by_coach")
            wplyw += " Trener zmienił ręcznie: " + ", ".join(str(x) for x in nadpisania) + "."
        return ([
            (f"{prefiks}Decyzja: cardio {czas} min w zakresie {hr_lo}–{hr_hi} % tętna maksymalnego "
             f"(RPE {rpe_lo}–{rpe_hi}). Zakres, nie jedna liczba — kieruj się też testem mowy."),
            wplyw,
            ("Kiedy to się zmieni: przy kolejnej wersji planu — trener przesuwa suwaki albo "
             "zmienia liczby; aplikacja nie podnosi intensywności sama."),
        ], uzyte)
    if regula.id == "ENERGY_INITIAL":
        metoda = f("method_label")
        wartosc = f("calculated_value")
        jedn = f("unit")
        zal = f("assumption_summary")
        return ([
            (f"{prefiks}Decyzja: cel energetyczny {wartosc} {jedn} — to oszacowanie, "
            "nie pomiar metabolizmu."),
            f"Co na nią wpłynęło: metoda „{metoda}”. Założenia: {zal}",
            ("Kiedy to się zmieni: gdy moduł diety lub trener zaktualizuje wartość na "
            "podstawie zapisanych danych."),
        ], uzyte)
    if regula.id == "CURATED_VARIANT_SELECTION":
        nazwa = f("recipe_name")
        rodzina = f("family_id")
        wariant = f("portion_variant")
        polityka = f("animal_policy")
        wzorzec = f("pattern")
        limit = f("time_limit")
        status = f("recipe_status")
        slot = f("slot")
        opis_statusu = ("receptura opublikowana po przeglądzie" if status == "published"
                        else "szkic receptury bez testu kuchennego i przeglądu (tryb demonstracyjny)")
        return ([
            (f"{prefiks}Decyzja: na {slot} wybrano „{nazwa}” (rodzina {rodzina}, wariant porcji "
             f"{wariant}) — całe danie w zatwierdzonej porcji, bez dokładania składników dla makro."),
            (f"Co na nią wpłynęło: polityka produktów zwierzęcych „{polityka}”, wzorzec „{wzorzec}”, "
             f"limit czasu {limit} min, kontrola powtórzeń rodzin w tygodniu; {opis_statusu}."),
            ("Kiedy to się zmieni: przy zamianie dania przez trenera (nowa wersja planu po ponownym "
             "sprawdzeniu całego dnia) albo po publikacji receptury po testach."),
        ], uzyte)
    if regula.id == "MEAL_PREFERENCE":
        pref = f("preference_label")
        wynik = f("matching_result")
        return ([
            f"{prefiks}Decyzja: posiłek dobrano według preferencji „{pref}”.",
            f"Co na nią wpłynęło: {wynik}. Opis nie przypisuje składnikom korzyści zdrowotnych.",
            "Kiedy to się zmieni: po zmianie preferencji albo bilansu dnia w module diety.",
        ], uzyte)
    return ([f"{prefiks}Decyzja: {trace.get('outcome_code')}."], uzyte)

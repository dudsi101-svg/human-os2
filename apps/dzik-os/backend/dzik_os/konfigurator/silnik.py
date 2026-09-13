"""Deterministyczny silnik generowania planu 28 dni (§6–§13 specyfikacji).

Kolejność ważności (§7 testów): objawy → zalecenia → sprzęt → dostępność
→ regeneracja → cel → preferencje. Każdy krok jest deterministyczny;
przy remisie rozstrzyga kolejność sesji, potem ćwiczeń, potem stabilny
identyfikator. Brak historii = brak wymyślonych wyników i ciężarów.
"""

from __future__ import annotations

import math
from datetime import date

from . import dane
from .kalendarz import daty_horyzontu, konflikty_odstepu, moment, rozpisz_sesje
from .walidator import czas_sesji_min, sumy_miesni, waliduj_plan, waliduj_wejscie
from .zdrowie import ocen_zdrowie

ZALOZENIA = [
    "Dorosła osoba bez zgłoszonych objawów lub ograniczeń; kwalifikację trzeba przeprowadzić w aplikacji.",
    "Sen i gotowość pozostają dobre; nie występują wskazania do lżejszego tygodnia.",
    "Pełne wykonanie planu nie jest z góry zakładane przy późniejszej adaptacji.",
    "Serie robocze są stałe w tym scenariuszu; wzrastać mogą powtórzenia lub obciążenie zgodnie z wynikami.",
]
OGRANICZENIA = [
    "To scenariusz demonstracyjny, wymagający rzeczywistego wywiadu przed użyciem.",
    "Ciężary i warianty gum dobierane na miejscu; przyszłe sesje zależą od dziennika.",
    "Dodatkowe cardio nie zostało wpisane jako obowiązkowa sesja; podstawowy plan nie realizuje całego celu aerobowego WHO.",
]
OGR_HISTORIA = "Brak historii w tym przykładzie: konserwatywna dawka startowa, niższa pewność indywidualnego dopasowania."
OGR_GUMY = "Wymagane sprawne gumy i odpowiednie, prawidłowo zamontowane mocowanie; brak takiego mocowania wymaga ponownej generacji."
OGR_JEDEN_DZIEN = "Jeden dzień jest kompromisem; mniejsza dawka i częstotliwość niż zalecany zdrowotny kierunek co najmniej dwóch dni wzmacniania."
PROGRESJA = ("Dobór ciężaru na pierwszej sesji; później zwiększenie dopiero po wszystkich seriach na "
             "górnym końcu zakresu, z zadanym RIR i poprawną techniką. Brak danych = brak automatycznej "
             "progresji. Tydzień 4 bez obowiązkowego odciążenia; zastosuj je przy wskazaniach ze specyfikacji.")
AKT_ODPOCZYNEK = "Odpoczynek; zwykła codzienna aktywność według tolerancji."
AKT_SESJA = "Dodatkowa aktywność tylko w osobnym, uzgodnionym budżecie czasu; nie jest wliczona do sesji."
REGULA_PROGRESJI = "DOUBLE_PROGRESSION_GATED"
MAX_SERII_NA_CWICZENIE = 4


def _issue(code: str, severity: str, message: str, rule_id: str) -> dict:
    return {"code": code, "severity": severity, "message": message, "rule_id": rule_id}


def _odpowiedz(status: str, plan: dict | None, issues: list[dict], questions: list[str]) -> dict:
    return {"status": status, "plan": plan, "issues": issues, "questions": questions,
            "versions": dict(dane.WERSJE)}


# --- dobór ćwiczeń -------------------------------------------------------

def _dopuszczalne(e: dict, wejscie: dict) -> bool:
    h = wejscie["health"]
    if e["id"] in h["forbidden_exercise_ids"] or e["pattern"] in h["forbidden_patterns"]:
        return False
    if e["id"] in wejscie["excluded_exercise_ids"]:
        return False
    return set(e["equipment_all"]) <= set(wejscie["equipment_ids"])


def _zamiennik(orygin: dict, wejscie: dict, zajete: set[str]) -> dict | None:
    """Ten sam wzorzec i te same mięśnie główne; remis: preferowane, krótsze
    ustawienie, stabilny identyfikator (§12)."""
    kand = [e for e in dane.cwiczenia().values()
            if e["id"] != orygin["id"] and e["id"] not in zajete
            and e["pattern"] == orygin["pattern"] and set(e["primary"]) == set(orygin["primary"])
            and _dopuszczalne(e, wejscie)]
    pref = set(wejscie["preferred_exercise_ids"])
    kand.sort(key=lambda e: (e["id"] not in pref, e["setup_seconds"], e["id"]))
    return kand[0] if kand else None


def _zbuduj_jednostke(tpl: dict, wejscie: dict, serie: int) -> tuple[list[dict], list[dict], int]:
    """Zwraca (recepty, issues, liczba zamian). Ćwiczenie niedopuszczalne →
    zamiennik; brak zamiennika: opcjonalne pomijamy z uwagą, obowiązkowe
    zostaje jako konflikt (recepta z `_konflikt`)."""
    cw = dane.cwiczenia()
    recepty, issues, zamiany = [], [], 0
    zajete = set(tpl["exercise_ids"])
    pref = set(wejscie["preferred_exercise_ids"])
    for eid in tpl["exercise_ids"]:
        e = cw[eid]
        if e["id"] in pref and not _dopuszczalne(e, wejscie):
            issues.append(_issue("PREFERENCE_OVERRIDDEN", "warning",
                                 f"Preferowane ćwiczenie {e['name_pl']} jest wykluczone zaleceniem lub sprzętem; użyto dozwolonego zamiennika.",
                                 "H_HEALTH_GATE"))
        if not _dopuszczalne(e, wejscie):
            z = _zamiennik(e, wejscie, zajete)
            if z is None:
                if eid in tpl.get("optional_exercise_ids", []):
                    issues.append(_issue("OPTIONAL_EXERCISE_DROPPED", "info",
                                         f"Pominięto opcjonalne {e['name_pl']}: brak dopuszczalnego zamiennika.", "H_CATALOG"))
                    continue
                recepty.append({"_konflikt": e})
                continue
            zajete.add(z["id"])
            zamiany += 1
            e = z
        recepty.append(_recepta(e, serie))
    return recepty, issues, zamiany


def _recepta(e: dict, serie: int) -> dict:
    return {
        "exercise_id": e["id"], "sets": serie, "reps_min": e["reps"][0], "reps_max": e["reps"][1],
        "rir": 0, "rest_seconds": e["rest_seconds"], "load_value": None, "load_unit": e["load_unit"],
        "load_variant": None, "reps_per_side": bool(e["unilateral"]), "progression_rule": REGULA_PROGRESJI,
    }


def _wybierz_uklad(wejscie: dict, serie: int) -> tuple[dict, dict[str, tuple[list[dict], list[dict]]], list[dict]]:
    """Układ dla liczby dni: preferuj układ bez zamian; inaczej domyślny z
    zamianami (deterministycznie pierwszy w katalogu)."""
    kandydaci = [u for u in dane.uklady() if u["days"] == wejscie["days_per_week"]]
    najlepszy, najlepsze_jedn, najmniej = None, None, None
    for u in kandydaci:
        jedn = {}
        razem = 0
        for tid in dict.fromkeys(u["sequence"]):
            rec, iss, zam = _zbuduj_jednostke(dane.jednostki()[tid], wejscie, serie)
            jedn[tid] = (rec, iss)
            razem += zam + 100 * sum(1 for r in rec if "_konflikt" in r)
        if najmniej is None or razem < najmniej:
            najlepszy, najlepsze_jedn, najmniej = u, jedn, razem
    issues = [i for rec, iss in najlepsze_jedn.values() for i in iss]
    return najlepszy, najlepsze_jedn, issues


# --- dawka -----------------------------------------------------------------

def _serie_startowe(wejscie: dict) -> int:
    return 2 if wejscie["level"] == "beginner" or wejscie["commitment"] == "minimum" else 3


def _dopasuj_do_historii(jedn: dict[str, list[dict]], sekwencja: list[str], cele: dict[str, float]) -> None:
    """§7: koryguj pojedynczą serię w kierunku największego odchylenia od
    celu, jeśli zmniejsza sumę |odchyleń| i nie narusza limitów; remis:
    kolejność sesji, potem ćwiczeń; maks. 100 kroków."""
    h = dane.heurystyki()

    def tydzien() -> list[dict]:
        return [r for tid in sekwencja for r in jedn[tid]]

    def odchylenie() -> float:
        s = sumy_miesni(tydzien())
        return sum(abs(s.get(m, {}).get("equivalent", 0) - cel) for m, cel in cele.items())

    for _ in range(100):
        biezace = odchylenie()
        najlepszy = None
        for tid in sekwencja:
            for r in jedn[tid]:
                for delta in (1, -1):
                    nowe = r["sets"] + delta
                    if not 1 <= nowe <= MAX_SERII_NA_CWICZENIE:
                        continue
                    r["sets"] = nowe
                    ok = all(v["equivalent"] <= h["weekly_equivalent_set_cap"] for v in sumy_miesni(tydzien()).values()) \
                        and all(v["equivalent"] <= h["session_equivalent_set_cap"]
                                for t in sekwencja for v in sumy_miesni(jedn[t]).values())
                    o = odchylenie() if ok else float("inf")
                    r["sets"] -= delta
                    if o < biezace and (najlepszy is None or o < najlepszy[0]):
                        najlepszy = (o, r, delta)
        if najlepszy is None:
            return
        najlepszy[1]["sets"] += najlepszy[2]


def _priorytet(jedn: dict[str, list[dict]], sekwencja: list[str], priorytety: list[str]) -> list[dict]:
    """Przenieś najwyżej 2 serie w tygodniu z niepriorytetowych izolacji do
    ćwiczeń priorytetowej grupy (limit 4 na ćwiczenie)."""
    if not priorytety:
        return []
    cw = dane.cwiczenia()
    przeniesione = 0
    issues = []
    for tid in sekwencja:
        for r in jedn[tid]:
            if przeniesione >= 2:
                break
            e = cw[r["exercise_id"]]
            if e["pattern"] in dane.IZOLACJE and not set(e["primary"]) & set(priorytety) and r["sets"] > 1:
                cel = next((x for x in jedn[tid] if set(cw[x["exercise_id"]]["primary"]) & set(priorytety)
                            and x["sets"] < MAX_SERII_NA_CWICZENIE), None)
                if cel is not None:
                    r["sets"] -= 1
                    cel["sets"] += 1
                    przeniesione += 1
    if przeniesione:
        issues.append(_issue("PRIORITY_SHIFT", "info",
                             f"Przeniesiono {przeniesione} serie z izolacji do grupy priorytetowej (bez wzrostu łącznej pracy).",
                             "H_VOLUME"))
    elif priorytety:
        issues.append(_issue("PRIORITY_NOT_APPLIED", "info",
                             "Priorytet mięśniowy nie zmienił dawki: brak izolacji do przeniesienia w ramach limitów.", "H_VOLUME"))
    return issues


def _zmiesc_w_czasie(tpl: dict, recepty: list[dict], limit_min: int, priorytety: list[str]) -> tuple[bool, list[dict]]:
    """§8: najpierw opcjonalne izolacje (tył barków, biceps, triceps, bok
    barków; poza priorytetem), potem po jednej serii od ćwiczenia z
    największą liczbą serii (remis: od końca sesji), zachowując ≥1 serię
    i minimum przerwy. Zwraca (zmieszczono, issues)."""
    cw = dane.cwiczenia()
    issues = []
    if czas_sesji_min(recepty) <= limit_min:
        return True, issues
    for miesien in dane.KOLEJNOSC_USUWANIA:
        if miesien in priorytety:
            continue
        for r in list(recepty):
            e = cw[r["exercise_id"]]
            if e["pattern"] in dane.IZOLACJE and e["primary"] == [miesien] and r["exercise_id"] in tpl.get("optional_exercise_ids", []):
                recepty.remove(r)
                issues.append(_issue("TIME_FIT_DROPPED", "warning",
                                     f"Usunięto opcjonalne {e['name_pl']} w jednostce {tpl['id']}, żeby zmieścić się w limicie czasu.", "H_TIME"))
                if czas_sesji_min(recepty) <= limit_min:
                    return True, issues
    while czas_sesji_min(recepty) > limit_min:
        kand = [r for r in recepty if r["sets"] > 1]
        if not kand:
            return False, issues
        maks = max(r["sets"] for r in kand)
        r = [x for x in kand if x["sets"] == maks][-1]
        r["sets"] -= 1
        issues.append(_issue("TIME_FIT_SET_REMOVED", "warning",
                             f"Odjęto serię z {cw[r['exercise_id']]['name_pl']} w jednostce {tpl['id']}, żeby zmieścić się w limicie czasu.", "H_TIME"))
    return True, issues


# --- generowanie -----------------------------------------------------------

def generuj_plan(wejscie: dict, plan_id: str = "PLAN") -> dict:
    """Pełny przebieg §13. Zawsze zwraca deterministyczną, wyjaśnioną odpowiedź."""
    bledy = waliduj_wejscie(wejscie)
    if bledy:
        return _odpowiedz("needs_input", None,
                          [_issue("INPUT_INVALID", "error", "Wejście nie przeszło walidacji: " + "; ".join(bledy), "H_SCHEMA")],
                          ["Popraw dane wejściowe: " + b for b in bledy])

    status_zdrowie, issues, questions = ocen_zdrowie(wejscie)
    if status_zdrowie:
        return _odpowiedz(status_zdrowie, None, issues, questions)

    # Poziom i częstotliwość: bez cichej zmiany wyboru (§6).
    if wejscie["level"] == "beginner" and wejscie["days_per_week"] >= 5:
        issues.append(_issue("BEGINNER_HIGH_FREQUENCY", "error",
                             "Dla osoby początkującej 5–6 sesji siłowych to nietypowy wybór: proponujemy 2–3 dni siłowe "
                             "i lekką aktywność w pozostałe. Potrzebna akceptacja propozycji albo przegląd trenera.", "H_LAYOUT"))
        return _odpowiedz("needs_input", None, issues,
                          ["Czy zaakceptować 2–3 dni siłowe (pozostałe dni lekka aktywność), czy skierować układ 5–6 dni do przeglądu trenera?"])

    issues.append(_issue("PROVISIONAL_LOADS", "info", "Obciążenia zostaną dobrane i zapisane podczas treningu.", "H_PROGRESS"))
    ograniczenia = list(OGRANICZENIA)
    if wejscie["level"] == "advanced" and not wejscie["history_weekly_sets"]:
        issues.append(_issue("MISSING_VOLUME_HISTORY", "warning", "Start zachowawczy bez danych o wcześniejszej tolerancji.", "H_VOLUME"))
        ograniczenia.append(OGR_HISTORIA)

    serie = _serie_startowe(wejscie)
    uklad, jedn_z_issues, issues_ukladu = _wybierz_uklad(wejscie, serie)
    issues.extend(issues_ukladu)
    jedn = {tid: rec for tid, (rec, _) in jedn_z_issues.items()}
    sekwencja = uklad["sequence"]

    konflikty = [r["_konflikt"] for rec in jedn.values() for r in rec if "_konflikt" in r]
    if konflikty:
        for e in konflikty:
            issues.append(_issue("NO_FEASIBLE_EXERCISE", "critical",
                                 f"Brak dopuszczalnego ćwiczenia dla wzorca {e['pattern']} ({e['name_pl']}): sprawdź sprzęt "
                                 f"({', '.join(e['equipment_all'])}) albo zalecenia. Bez tego pełny plan jest niewykonalny.", "H_CATALOG"))
        return _odpowiedz("infeasible", None, issues, [
            f"Czy dostępny jest sprzęt do wzorca {e['pattern']} (np. {', '.join(e['equipment_all'])}) lub inne mocowanie gumy?"
            for e in konflikty])

    # Historia (cele) → korekty pojedynczych serii.
    if wejscie["history_weekly_sets"]:
        _dopasuj_do_historii(jedn, sekwencja, wejscie["history_weekly_sets"])

    # Regeneracja i powrót po przerwie (§7).
    rir_plus = 0
    rir_plus_t1 = 0
    niska_regeneracja = wejscie["sleep_hours"] < 6 or wejscie["stress"] >= 4
    if niska_regeneracja:
        for rec in jedn.values():
            for r in rec:
                r["sets"] = max(1, math.floor(r["sets"] * 0.8 + 0.5))
        rir_plus += 1
        issues.append(_issue("LOW_RECOVERY_ADJUSTMENT", "warning",
                             "Niska regeneracja (sen <6 h lub stres ≥4/5): mniej serii i większy zapas powtórzeń; "
                             "zaokrąglenie może zostawić małą dawkę bez zmiany.", "H_RECOVERY"))
    if wejscie["break_weeks"] >= 4:
        for rec in jedn.values():
            for r in rec:
                r["sets"] = max(1, math.floor(r["sets"] * 0.75 + 0.5))
        rir_plus_t1 += 1
        issues.append(_issue("RETURN_AFTER_BREAK", "warning",
                             "Powrót po przerwie ≥4 tygodni: około 25% mniej serii i większy zapas w pierwszym tygodniu.", "H_RECOVERY"))
    if wejscie["heavy_physical_work"] or wejscie["other_sport_minutes"] > 0:
        questions.append("Jak oceniasz regenerację przy ciężkiej pracy fizycznej lub innym sporcie? "
                         "Ta odpowiedź nie zmienia dawki automatycznie.")

    issues.extend(_priorytet(jedn, sekwencja, wejscie["priority_muscles"]))

    # Czas sesji.
    for tid in dict.fromkeys(sekwencja):
        ok, iss = _zmiesc_w_czasie(dane.jednostki()[tid], jedn[tid], wejscie["session_minutes"], wejscie["priority_muscles"])
        issues.extend(iss)
        if not ok:
            issues.append(_issue("TIME_LIMIT_INFEASIBLE", "critical",
                                 f"Jednostki {tid} nie da się zmieścić w {wejscie['session_minutes']} min bez naruszenia "
                                 "minimum serii i przerw. Wydłuż limit albo zmniejsz liczbę ćwiczeń.", "H_TIME"))
            return _odpowiedz("infeasible", None, issues,
                              [f"Czy limit czasu może być dłuższy niż {wejscie['session_minutes']} min, albo czy usunąć część ćwiczeń?"])

    # Limity dawki (§7): powyżej → konsultacja trenera.
    tydzien = [r for tid in sekwencja for r in jedn[tid]]
    h = dane.heurystyki()
    przekroczone = [m for m, v in sumy_miesni(tydzien).items() if v["equivalent"] > h["weekly_equivalent_set_cap"]]
    przekroczone += [f"{tid}:{m}" for tid in dict.fromkeys(sekwencja)
                     for m, v in sumy_miesni(jedn[tid]).items() if v["equivalent"] > h["session_equivalent_set_cap"]]
    if przekroczone:
        issues.append(_issue("VOLUME_CAP_EXCEEDED", "error",
                             "Dawka ponad limit automatycznego MVP (18 serii/tydzień lub 8/sesję): " + ", ".join(przekroczone)
                             + ". Potrzebna konsultacja trenera.", "H_VOLUME"))
        return _odpowiedz("needs_review", None, issues, questions)

    # Pokrycie głównych grup (§7).
    sumy = sumy_miesni(tydzien)
    braki = [g for g, ms in dane.GRUPY_GLOWNE.items() if not any(sumy.get(m, {}).get("direct", 0) > 0 for m in ms)]
    if braki:
        issues.append(_issue("MISSING_COVERAGE", "critical",
                             "Brak istotnej pracy dla: " + ", ".join(braki) + " — pełny plan całego ciała jest niewykonalny.", "H_VOLUME"))
        return _odpowiedz("infeasible", None, issues, questions)

    # Kalendarz i odstępy.
    start = date.fromisoformat(wejscie["start_date"])
    daty = daty_horyzontu(start, wejscie["horizon_mode"])
    przydzial = rozpisz_sesje(daty, sorted(wejscie["available_weekdays"]), sekwencja)
    cw = dane.cwiczenia()
    momenty = [(moment(d, wejscie["session_start_local"], wejscie["timezone"]),
                sorted({m for r in jedn[tid] for m in cw[r["exercise_id"]]["primary"]}))
               for d, tid in sorted(przydzial.items())]
    kolizje = konflikty_odstepu(momenty, h["minimum_same_primary_muscle_interval_hours"])
    if kolizje:
        opis = "; ".join(f"{a.date()} → {b.date()} ({g})" for a, b, g in kolizje[:4])
        issues.append(_issue("SESSION_SPACING_CONFLICT", "error",
                             f"Wybrane terminy nie zachowują odstępu {h['minimum_same_primary_muscle_interval_hours']} h "
                             f"dla tej samej głównej grupy: {opis}. Nie zmieniam dni samodzielnie.", "H_SPACING"))
        return _odpowiedz("needs_input", None, issues, questions + [
            "Czy możesz wskazać inne dni treningowe, czy świadomie przyjąć jawnie ograniczony układ z krótszym odstępem?"])

    # RIR na tygodnie.
    rir = list(h["initial_rir"][wejscie["level"]])
    if len(daty) > 28:
        rir.append(rir[-1])
    dni = []
    for i, d in enumerate(daty):
        tydz = i // 7 + 1
        if d in przydzial:
            tid = przydzial[d]
            r_tyg = min(5, rir[tydz - 1] + rir_plus + (rir_plus_t1 if tydz == 1 else 0))
            recepty = [dict(r, rir=r_tyg) for r in jedn[tid]]
            dni.append({
                "date": d.isoformat(), "week": tydz, "kind": "strength",
                "session_id": f"{plan_id}-S{i + 1:02d}", "template_id": tid,
                "start_local": wejscie["session_start_local"],
                "warmup_minutes": h["warmup_seconds"] // 60, "cooldown_minutes": h["cooldown_seconds"] // 60,
                "estimated_minutes": czas_sesji_min(recepty), "exercise_prescriptions": recepty,
                "optional_activity": AKT_SESJA, "state": "provisional",
            })
        else:
            dni.append({
                "date": d.isoformat(), "week": tydz, "kind": "rest", "session_id": None, "template_id": None,
                "start_local": None, "warmup_minutes": 0, "cooldown_minutes": 0, "estimated_minutes": 0,
                "exercise_prescriptions": [], "optional_activity": AKT_ODPOCZYNEK, "state": "provisional",
            })

    tygodnie: dict[int, list[dict]] = {}
    for dz in dni:
        tygodnie.setdefault(dz["week"], []).extend(dz["exercise_prescriptions"])
    weekly = [{"week": w, "muscles": sumy_miesni(tygodnie[w])} for w in sorted(tygodnie)]

    if any(cw[r["exercise_id"]]["load_unit"] == "band_variant" for r in tydzien):
        ograniczenia.append(OGR_GUMY)
    status = "ready"
    if wejscie["days_per_week"] == 1:
        status = "limited"
        issues.append(_issue("ONE_DAY_COMPROMISE", "warning", OGR_JEDEN_DZIEN, "H_LAYOUT"))
        ograniczenia.append(OGR_JEDEN_DZIEN)
    if any(i["severity"] == "warning" and i["code"].startswith("TIME_FIT") for i in issues) and status == "ready":
        status = "limited"

    plan = {
        "id": plan_id, "start_date": daty[0].isoformat(), "end_date": daty[-1].isoformat(),
        "timezone": wejscie["timezone"], "horizon_mode": wejscie["horizon_mode"], "days": dni,
        "weekly_volume": weekly, "assumptions": list(ZALOZENIA), "limitations": ograniczenia,
        "progression_summary": PROGRESJA,
    }
    odpowiedz = _odpowiedz(status, plan, issues, questions)
    bledy = waliduj_plan(odpowiedz, wejscie)
    if bledy:
        # Walidator nie ufa silnikowi: każdy błąd zamienia wynik w jawny konflikt.
        issues.append(_issue("VALIDATION_FAILED", "critical", "Walidator odrzucił plan: " + "; ".join(bledy), "H_VALIDATOR"))
        return _odpowiedz("infeasible", None, issues, questions)
    return odpowiedz

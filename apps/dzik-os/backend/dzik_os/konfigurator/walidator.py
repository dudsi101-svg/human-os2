"""Walidator: schematy JSON (Draft 2020-12) + reguły między polami (§14).

Osobny od silnika celowo: wynik silnika NIE jest zaufany — czas i sumy są
liczone od nowa, identyfikatory i sprzęt sprawdzane ponownie, statusy
blokujące muszą mieć `plan: null`.
"""

from __future__ import annotations

import math
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jsonschema

from . import dane
from .kalendarz import konflikty_odstepu, moment

WZORCE = {"knee", "hinge", "hip_extension", "knee_flexion", "knee_isolation", "horizontal_push",
          "vertical_push", "chest_isolation", "horizontal_pull", "vertical_pull",
          "shoulder_abduction", "rear_shoulder", "elbow_extension", "elbow_flexion",
          "ankle", "trunk"}


def _walidator(schemat: dict) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(schemat)


def waliduj_wejscie(wejscie: dict) -> list[str]:
    """Lista błędów (pusta = poprawne). Format `date` sprawdzany aktywnie."""
    bledy = [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
             for e in _walidator(dane.schematy()["input_schema"]).iter_errors(wejscie)]
    if bledy:
        return bledy
    cw = dane.cwiczenia()
    sprzet = {s for e in cw.values() for s in e["equipment_all"]}
    if wejscie["days_per_week"] != len(wejscie["available_weekdays"]):
        bledy.append("days_per_week musi równać się liczbie dostępnych dni tygodnia")
    for pole in ("excluded_exercise_ids", "preferred_exercise_ids"):
        for i in wejscie[pole]:
            if i not in cw:
                bledy.append(f"{pole}: nieznane ćwiczenie {i}")
    for i in wejscie["health"]["forbidden_exercise_ids"]:
        if i not in cw:
            bledy.append(f"health/forbidden_exercise_ids: nieznane ćwiczenie {i}")
    for w in wejscie["health"]["forbidden_patterns"]:
        if w not in WZORCE:
            bledy.append(f"health/forbidden_patterns: nieznany wzorzec {w}")
    for s in wejscie["equipment_ids"]:
        if s not in sprzet:
            bledy.append(f"equipment_ids: nieznany sprzęt {s}")
    for m in wejscie["history_weekly_sets"]:
        if m not in dane.schematy()["input_schema"]["properties"]["priority_muscles"]["items"]["enum"]:
            bledy.append(f"history_weekly_sets: nieznany mięsień {m}")
    try:
        date.fromisoformat(wejscie["start_date"])
    except ValueError:
        bledy.append("start_date: niepoprawna data")
    try:
        ZoneInfo(wejscie["timezone"])
    except (ZoneInfoNotFoundError, ValueError):
        bledy.append("timezone: nieznana strefa czasowa")
    return bledy


def czas_sesji_s(recepty: list[dict]) -> int:
    """Wzór H z §8: 600 rozgrzewki + Σ[serie×górny zakres×4×strony +
    (serie−1)×przerwa + 90] + 180 zakończenia."""
    cw = dane.cwiczenia()
    t = dane.heurystyki()["warmup_seconds"] + dane.heurystyki()["cooldown_seconds"]
    for r in recepty:
        strony = 2 if cw[r["exercise_id"]]["unilateral"] else 1
        t += r["sets"] * r["reps_max"] * cw[r["exercise_id"]]["seconds_per_rep_estimate"] * strony
        t += (r["sets"] - 1) * r["rest_seconds"] + cw[r["exercise_id"]]["setup_seconds"]
    return t


def czas_sesji_min(recepty: list[dict]) -> int:
    return math.ceil(czas_sesji_s(recepty) / 60)


def sumy_miesni(recepty_tygodnia: list[dict]) -> dict[str, dict]:
    """Bezpośrednie ×1, pośrednie ×0,5 (model, nie pomiar bodźca)."""
    cw = dane.cwiczenia()
    bezp: dict[str, int] = {}
    posr: dict[str, float] = {}
    for r in recepty_tygodnia:
        e = cw[r["exercise_id"]]
        for m in e["primary"]:
            bezp[m] = bezp.get(m, 0) + r["sets"]
        for m in e["secondary"]:
            posr[m] = posr.get(m, 0.0) + r["sets"] * dane.katalog()["muscle_counting"]["indirect"]
    out = {}
    for m in sorted(set(bezp) | set(posr)):
        d = bezp.get(m, 0)
        p = posr.get(m, 0)
        out[m] = {"direct": d, "indirect_equivalent": p, "equivalent": d + p}
    return out


def waliduj_plan(odpowiedz: dict, wejscie: dict) -> list[str]:
    """Niezależna kontrola wyniku silnika. Lista błędów (pusta = poprawny)."""
    bledy = [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
             for e in _walidator(dane.schematy()["response_schema"]).iter_errors(odpowiedz)]
    if bledy:
        return bledy
    status, plan = odpowiedz["status"], odpowiedz["plan"]
    if status in ("urgent_stop", "needs_review", "needs_input", "infeasible"):
        return [] if plan is None else ["status blokujący musi mieć plan: null"]
    if plan is None:
        return ["status ready/limited wymaga planu"]
    cw = dane.cwiczenia()
    h = dane.heurystyki()
    daty = [d["date"] for d in plan["days"]]
    start = date.fromisoformat(plan["start_date"])
    if daty != [(date.fromordinal(start.toordinal() + i)).isoformat() for i in range(len(daty))]:
        bledy.append("daty nie są kolejne od start_date")
    if plan["end_date"] != daty[-1]:
        bledy.append("end_date niezgodne z ostatnią datą")
    sprzet = set(wejscie["equipment_ids"])
    zakazane = set(wejscie["health"]["forbidden_exercise_ids"]) | set(wejscie["excluded_exercise_ids"])
    zak_wzorce = set(wejscie["health"]["forbidden_patterns"])
    sesje_czas = []
    for d in plan["days"]:
        if d["kind"] == "rest":
            if d["exercise_prescriptions"] or d["estimated_minutes"] != 0:
                bledy.append(f"{d['date']}: dzień odpoczynku z treścią")
            continue
        for r in d["exercise_prescriptions"]:
            e = cw.get(r["exercise_id"])
            if e is None:
                bledy.append(f"{d['date']}: nieznane ćwiczenie {r['exercise_id']}")
                continue
            if not set(e["equipment_all"]) <= sprzet:
                bledy.append(f"{d['date']}: brak sprzętu do {r['exercise_id']}")
            if r["exercise_id"] in zakazane or e["pattern"] in zak_wzorce:
                bledy.append(f"{d['date']}: zakazane ćwiczenie {r['exercise_id']}")
            if r["reps_min"] > r["reps_max"]:
                bledy.append(f"{d['date']}: reps_min > reps_max")
            if r["rest_seconds"] < e["rest_seconds"]:
                bledy.append(f"{d['date']}: przerwa krótsza niż minimum ćwiczenia")
            if r["load_value"] is not None:
                bledy.append(f"{d['date']}: ciężar przewidziany bez danych")
        if czas_sesji_min(d["exercise_prescriptions"]) != d["estimated_minutes"]:
            bledy.append(f"{d['date']}: czas nie zgadza się ze wzorem")
        if d["estimated_minutes"] > wejscie["session_minutes"]:
            bledy.append(f"{d['date']}: przekroczony limit czasu")
        grupy = sorted({m for r in d["exercise_prescriptions"] for m in cw[r["exercise_id"]]["primary"]}
                       if all(r["exercise_id"] in cw for r in d["exercise_prescriptions"]) else [])
        sesje_czas.append((moment(date.fromisoformat(d["date"]), d["start_local"], plan["timezone"]), grupy))
        s = sumy_miesni(d["exercise_prescriptions"])
        for m, v in s.items():
            if v["equivalent"] > h["session_equivalent_set_cap"]:
                bledy.append(f"{d['date']}: {m} ponad limit sesji")
    for a, b, g in konflikty_odstepu(sesje_czas, h["minimum_same_primary_muscle_interval_hours"]):
        bledy.append(f"odstęp <{h['minimum_same_primary_muscle_interval_hours']}h dla {g}: {a.date()} → {b.date()}")
    # Sumy tygodniowe liczone od nowa.
    tygodnie: dict[int, list[dict]] = {}
    for d in plan["days"]:
        tygodnie.setdefault(d["week"], []).extend(d["exercise_prescriptions"])
    for w in plan["weekly_volume"]:
        if sumy_miesni(tygodnie.get(w["week"], [])) != w["muscles"]:
            bledy.append(f"tydzień {w['week']}: sumy mięśni niezgodne")
        for m, v in w["muscles"].items():
            if v["equivalent"] > h["weekly_equivalent_set_cap"]:
                bledy.append(f"tydzień {w['week']}: {m} ponad limit tygodniowy")
        if status == "ready" and len(tygodnie.get(w["week"], [])) and w["week"] <= 4:
            for grupa, miesnie in dane.GRUPY_GLOWNE.items():
                if not any(w["muscles"].get(m, {}).get("direct", 0) > 0 for m in miesnie):
                    bledy.append(f"tydzień {w['week']}: status ready bez pokrycia {grupa}")
    return bledy

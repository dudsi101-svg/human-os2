"""Szkic konfiguratora → struktura planu Dzik OS (`days`/`exercises`).

Trener zapisuje wynik jako ZWYKŁĄ wersję planu podopiecznego: dni to
jednostki treningowe w kolejności układu, ćwiczenia z nazwą po polsku,
seriami, zakresem powtórzeń, przerwą i komentarzem (RIR na tygodnie,
zapis „na stronę", zasada progresji). Ciężar to zawsze „dobór na
miejscu" — nigdy liczba. Pełny wynik silnika (kalendarz 28 dni, sumy,
uwagi, wersje reguł) zostaje w treści wersji pod kluczem `konfigurator`
razem z wejściem BEZ bloku zdrowotnego (minimalizacja danych; sama
kwalifikacja zapisana jako status).
"""

from __future__ import annotations

from . import dane

JEDNOSTKA_CIEZARU = {
    "per_dumbbell_kg": "kg na hantlę",
    "one_dumbbell_kg": "kg jednej hantli",
    "machine_display_kg": "kg na wyświetlaczu maszyny",
    "band_variant": "wariant gumy",
    "bodyweight_variant": "wariant masy ciała",
}


def _rir_na_tygodnie(plan: dict, template_id: str) -> str:
    rir = []
    for d in plan["days"]:
        if d["template_id"] == template_id and d["exercise_prescriptions"]:
            r = d["exercise_prescriptions"][0]["rir"]
            if len(rir) < d["week"]:
                rir.extend([r] * (d["week"] - len(rir)))
    return "/".join(str(x) for x in rir) if rir else "—"


def na_plan_dzik(odpowiedz: dict, wejscie: dict) -> dict:
    """Treść wersji planu (`content_json`) dla statusu ready/limited."""
    plan = odpowiedz["plan"]
    cw = dane.cwiczenia()
    kolejnosc = list(dict.fromkeys(d["template_id"] for d in plan["days"] if d["kind"] == "strength"))
    dni = []
    for nr, tid in enumerate(kolejnosc, start=1):
        sesja = next(d for d in plan["days"] if d["template_id"] == tid)
        rir = _rir_na_tygodnie(plan, tid)
        cwiczenia = []
        for r in sesja["exercise_prescriptions"]:
            e = cw[r["exercise_id"]]
            uwagi = [f"RIR tyg. 1–4: {rir}", f"ciężar: dobór na miejscu ({JEDNOSTKA_CIEZARU.get(r['load_unit'], r['load_unit'])})",
                     "progresja: podwójna — ciężar w górę dopiero po wszystkich seriach na górnym końcu zakresu z zadanym RIR"]
            if r["reps_per_side"]:
                uwagi.insert(0, "powtórzenia na stronę; czas liczy obie strony")
            cwiczenia.append({
                "name": e["name_pl"], "exercise_id": None, "konfigurator_id": r["exercise_id"],
                "sets": str(r["sets"]),
                "reps": f"{r['reps_min']}–{r['reps_max']}" + (" na stronę" if r["reps_per_side"] else ""),
                "weight": "dobór na miejscu", "tempo": None, "rest": f"{r['rest_seconds']} s",
                "comment": "; ".join(uwagi),
            })
        dni.append({"name": f"{nr}. Jednostka {tid} (~{sesja['estimated_minutes']} min)", "weekday": None,
                    "exercises": cwiczenia})
    wejscie_bez_zdrowia = {k: v for k, v in wejscie.items() if k != "health"}
    return {
        "days": dni,
        "konfigurator": {
            "status": odpowiedz["status"],
            "versions": odpowiedz["versions"],
            "issues": odpowiedz["issues"],
            "questions": odpowiedz["questions"],
            "wejscie": wejscie_bez_zdrowia,
            "kwalifikacja_zdrowotna": "przeszła (szczegóły zdrowotne nie są zapisywane w planie)",
            "kalendarz": [{"date": d["date"], "week": d["week"], "kind": d["kind"], "session_id": d["session_id"],
                           "template_id": d["template_id"], "start_local": d["start_local"],
                           "estimated_minutes": d["estimated_minutes"],
                           "rir": d["exercise_prescriptions"][0]["rir"] if d["exercise_prescriptions"] else None}
                          for d in plan["days"]],
            "weekly_volume": plan["weekly_volume"],
            "assumptions": plan["assumptions"],
            "limitations": plan["limitations"],
            "progression_summary": plan["progression_summary"],
        },
    }

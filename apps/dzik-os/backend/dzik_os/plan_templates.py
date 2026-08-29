"""Wbudowane szablony treningowe: odczyt katalogu i budowa treści planu.

Rola tego modułu
----------------
Zamienia dane z `plan_templates_data` na strukturę `days`/`exercises`, której
używa `TrainingPlanVersion.content_json` — czyli dokładnie tę samą, co plan
napisany ręcznie przez trenera. Szablon wbudowany nie jest osobnym bytem
w bazie: po imporcie staje się zwykłym szablonem trenera i dalej podlega
istniejącej ścieżce `POST /api/plans/{template_id}/copy-to/{client_id}`.

Czego ten moduł NIE robi
------------------------
Nie podejmuje decyzji treningowych. Reguła progresji jest tekstem dla
człowieka; nic tu nie przelicza ciężarów ani nie „awansuje" planu z upływem
czasu (zasada ze źródła: „Brak automatycznego wzrostu").
"""

from __future__ import annotations

import re
from typing import Any

from .plan_templates_data import PROGRESSION_MODELS, TEMPLATES, UNITS


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def list_templates() -> list[dict[str, Any]]:
    """Metadane wszystkich szablonów — do listy wyboru w panelu trenera."""
    out: list[dict[str, Any]] = []
    for tpl in TEMPLATES:
        units = UNITS.get(str(tpl["id"]), [])
        out.append(
            {
                **tpl,
                "days": len({u["day"] for u in units}),
                "exercises": len(units),
            }
        )
    return out


def get_template(template_id: str) -> dict[str, Any] | None:
    for tpl in TEMPLATES:
        if tpl["id"] == template_id:
            return dict(tpl)
    return None


def build_days(
    template_id: str, exercise_ids: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """Treść planu: dni w kolejności, w każdym ćwiczenia wg pola „Kolejność".

    `exercise_ids` mapuje ZNORMALIZOWANĄ nazwę na id ćwiczenia z biblioteki
    danego trenera (patrz `exercise_ids_for_coach`). Gdy nazwa nie pasuje,
    pozycja zostaje z samą nazwą — plan działa, brakuje tylko linku do karty.

    Uwagi trenera i opis progresji trafiają do `comment`, bo to jedyne pole,
    które widzi zarówno trener, jak i klient — a reguła progresji ma być
    czytana przez człowieka, nie wykonywana przez aplikację.
    """
    units = UNITS.get(template_id)
    if not units:
        return []

    mapa = exercise_ids or {}
    dni: dict[str, list[dict[str, Any]]] = {}
    for u in sorted(units, key=lambda x: (str(x["day"]), int(x["order"]))):
        model = PROGRESSION_MODELS.get(str(u["progression"]), {})
        czesci = [c for c in (u.get("coach_note"), model.get("action")) if c]
        dni.setdefault(str(u["day"]), []).append(
            {
                "name": u["exercise"],
                "exercise_id": mapa.get(_norm(str(u["exercise"]))),
                "sets": u.get("sets"),
                "reps": u.get("reps"),
                "weight": None,  # ciężar dobiera klient/trener, nie szablon
                "tempo": u.get("tempo") if u.get("tempo") != "—" else None,
                "rest": u.get("rest"),
                "comment": " ".join(czesci) or None,
                # Szablony autorskie (0.54.0) niosą linki do techniki —
                # wcześniejsze wpisy katalogu nie mają pola `video` i dalej
                # dają None, więc nic się dla nich nie zmienia.
                "video_url": u.get("video") or None,
                "target_rir": u.get("target_rir"),
                "progression": u.get("progression"),
            }
        )

    return [
        {"name": f"Jednostka {nazwa}", "weekday": None, "exercises": cwiczenia}
        for nazwa, cwiczenia in dni.items()
    ]


def progression_models() -> dict[str, dict[str, str]]:
    """Słownik modeli progresji — UI rozwija kod zapisany przy ćwiczeniu."""
    return {k: dict(v) for k, v in PROGRESSION_MODELS.items()}


def exercise_ids_for_coach(db: Any, coach_id: str) -> dict[str, str]:
    """Aktywne ćwiczenia trenera: znormalizowana nazwa -> id.

    Dopasowanie jest DOKŁADNE (po normalizacji). Świadomie nie szukamy
    „po podobieństwie": źródłowy arkusz używa innego nazewnictwa niż
    biblioteka („Przysiad ze sztangą na plecach" vs „Przysiad ze sztangą"),
    a błędne powiązanie pokazałoby klientowi instrukcję i film INNEGO
    ćwiczenia. Brak dopasowania nie psuje planu — nazwa jest zawsze zapisana
    w treści, a `exercise_id` to miękkie odniesienie (`schemas.ExerciseIn`).
    """
    from .models import Exercise

    rows = (
        db.query(Exercise.id, Exercise.name)
        .filter(Exercise.coach_id == coach_id, Exercise.status == "ACTIVE")
        .all()
    )
    return {_norm(name): eid for eid, name in rows}

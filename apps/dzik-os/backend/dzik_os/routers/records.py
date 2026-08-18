"""Rekordy osobiste i postęp od startu — rywalizacja WYŁĄCZNIE z własną
historią klienta (zasada Human OS: system nigdy nie porównuje ludzi między
sobą ani nie rankinguje ich wartości; punktem odniesienia jest zawsze
wcześniejsze "ja" tej samej osoby).

Rekord = najwyższy ciężar (kg) sparsowany deterministycznie z tekstowych
wyników treningów danego ćwiczenia (np. "3x8 @ 80kg"). Żadnej interpretacji
AI — prosty, jawny regex; wynik bez rozpoznawalnego ciężaru jest pomijany.
"""

from __future__ import annotations

import json
import re
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..authz import resolve_client_access
from ..dates import local_today
from ..db import get_db
from ..models import Measurement, User, WorkoutEntry, WorkoutSession
from ..security import current_user

router = APIRouter(prefix="/api", tags=["records"])

WEIGHT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*kg", re.IGNORECASE)
NEW_RECORD_WINDOW_DAYS = 14


def _max_weight_kg(result_text: str) -> float | None:
    values = [float(m.replace(",", ".")) for m in WEIGHT_RE.findall(result_text)]
    return max(values) if values else None


def _entry_sets(entry: WorkoutEntry) -> list[dict]:
    if not entry.sets_json:
        return []
    try:
        sets = json.loads(entry.sets_json)
        return sets if isinstance(sets, list) else []
    except ValueError:
        # Świadome zignorowanie: uszkodzony JSON serii w jednym wpisie
        # treningowym nie może wywrócić rekordów/wykresów — wpis jest
        # traktowany jak zapis bez danych strukturalnych (fallback: tekst
        # wyniku, patrz _entry_max_weight).
        return []


def _entry_max_weight(entry: WorkoutEntry) -> float | None:
    """Najcięższa seria — najpierw dane strukturalne, potem tekst wyniku."""
    sets = [s for s in _entry_sets(entry) if s.get("weight_kg")]
    if sets:
        return max(float(s["weight_kg"]) for s in sets)
    if entry.result:
        return _max_weight_kg(entry.result)
    return None


def _epley_e1rm(weight_kg: float, reps: int) -> float:
    """Szacowany 1RM (Epley) — SZACUNEK do obserwacji trendu, nie
    zalecenie obciążenia treningowego."""
    if reps <= 1:
        return weight_kg
    return weight_kg * (1 + reps / 30)


@router.get("/clients/{client_id}/personal-records")
def personal_records(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Rekordy per ćwiczenie (najlepszy własny ciężar + kiedy) oraz zmiana
    każdego pomiaru względem pierwszego zapisu. `is_new` oznacza rekord
    poprawiony w ostatnich 14 dniach względem WCZEŚNIEJSZEGO własnego
    wyniku — pierwszy zapis ćwiczenia nie jest "nowym rekordem"."""
    resolve_client_access(db, user, client_id)
    # performed_on jest datą lokalną — okno "nowego rekordu" liczymy od
    # lokalnego "dziś", nie od daty UTC.
    today = local_today()
    recent_since = (today - timedelta(days=NEW_RECORD_WINDOW_DAYS)).isoformat()

    rows = (
        db.query(WorkoutEntry, WorkoutSession.performed_on)
        .join(WorkoutSession, WorkoutEntry.session_id == WorkoutSession.id)
        .filter(WorkoutSession.client_id == client_id)
        .order_by(WorkoutSession.performed_on)
        .all()
    )
    by_exercise: dict[str, list[tuple[str, float]]] = {}
    for entry, performed_on in rows:
        weight = _entry_max_weight(entry)
        if weight is None:
            continue
        by_exercise.setdefault(entry.exercise_name, []).append((performed_on, weight))

    records = []
    for exercise, samples in by_exercise.items():
        best_date, best = max(samples, key=lambda s: (s[1], s[0]))
        earlier = [w for d, w in samples if d < best_date]
        is_new = (
            best_date >= recent_since
            and len(earlier) > 0
            and best > max(earlier)
        )
        records.append(
            {
                "exercise_name": exercise,
                "best_kg": best,
                "achieved_on": best_date,
                "previous_best_kg": max(earlier) if earlier else None,
                "attempts": len(samples),
                "is_new": is_new,
            }
        )
    records.sort(key=lambda r: (not r["is_new"], r["exercise_name"]))

    measurements = (
        db.query(Measurement)
        .filter(Measurement.client_id == client_id)
        .order_by(Measurement.measured_at)
        .all()
    )
    by_kind: dict[str, list[Measurement]] = {}
    for m in measurements:
        by_kind.setdefault(m.kind, []).append(m)
    since_start = []
    for kind, series in by_kind.items():
        if len(series) < 2:
            continue
        first, last = series[0], series[-1]
        since_start.append(
            {
                "kind": kind,
                "unit": last.unit,
                "first_value": first.value,
                "first_date": first.measured_at,
                "latest_value": last.value,
                "latest_date": last.measured_at,
                "delta": round(last.value - first.value, 1),
            }
        )

    return {"records": records, "since_start": since_start}


@router.get("/clients/{client_id}/strength-series")
def strength_series(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Serie siłowe per ćwiczenie — wyłącznie ze strukturalnych zapisów
    serii (ciężar × powtórzenia): objętość dnia (suma kg×powt.) i
    najlepszy szacowany 1RM dnia (Epley — szacunek do obserwacji trendu,
    nie zalecenie). Porównania tylko z własną historią."""
    resolve_client_access(db, user, client_id)
    rows = (
        db.query(WorkoutEntry, WorkoutSession.performed_on)
        .join(WorkoutSession, WorkoutEntry.session_id == WorkoutSession.id)
        .filter(WorkoutSession.client_id == client_id)
        .order_by(WorkoutSession.performed_on)
        .all()
    )
    # exercise -> date -> {"volume": x, "e1rm": y}
    agg: dict[str, dict[str, dict[str, float]]] = {}
    for entry, performed_on in rows:
        sets = [
            s for s in _entry_sets(entry)
            if s.get("weight_kg") and s.get("reps")
        ]
        if not sets:
            continue
        day = agg.setdefault(entry.exercise_name, {}).setdefault(
            performed_on, {"volume": 0.0, "e1rm": 0.0}
        )
        for s in sets:
            weight, reps = float(s["weight_kg"]), int(s["reps"])
            day["volume"] += weight * reps
            day["e1rm"] = max(day["e1rm"], _epley_e1rm(weight, reps))
    out = []
    for exercise, days in agg.items():
        points = [
            {"date": d, "volume_kg": round(v["volume"], 1), "e1rm_kg": round(v["e1rm"], 1)}
            for d, v in sorted(days.items())
        ]
        out.append({"exercise_name": exercise, "points": points})
    out.sort(key=lambda e: e["exercise_name"])
    return {"series": out}

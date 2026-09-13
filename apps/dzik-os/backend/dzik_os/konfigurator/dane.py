"""Dane konfiguratora wczytywane z plików pakietu (wersje w treści)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DANE = Path(__file__).parent / "dane"

WERSJE = {"schema": "1.0", "rules": "1.0", "catalog": "1.0", "sources_reviewed_on": "2026-09-13"}


@lru_cache(maxsize=1)
def katalog() -> dict:
    return json.loads((_DANE / "katalog.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def schematy() -> dict:
    return json.loads((_DANE / "schematy.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def zrodla() -> dict:
    return json.loads((_DANE / "zrodla.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def cwiczenia() -> dict[str, dict]:
    return {e["id"]: e for e in katalog()["exercises"]}


@lru_cache(maxsize=1)
def jednostki() -> dict[str, dict]:
    return {t["id"]: t for t in katalog()["session_templates"]}


@lru_cache(maxsize=1)
def uklady() -> list[dict]:
    return list(katalog()["weekly_layouts"])


def heurystyki() -> dict:
    return katalog()["heuristics"]


#: Wzorce liczone jako izolacje (kolejność usuwania przy braku czasu wg §7:
#: tył barków, biceps, triceps, bok barków — przez mięsień główny).
IZOLACJE = {"shoulder_abduction", "elbow_extension", "elbow_flexion", "rear_shoulder",
            "chest_isolation", "knee_isolation", "ankle"}
KOLEJNOSC_USUWANIA = ["rear_delts", "biceps", "triceps", "side_delts"]
#: Wzorce obowiązkowe pełnego planu całego ciała (§7: brak istotnej pracy
#: klatki, pleców lub nóg jest konfliktem).
GRUPY_GLOWNE = {"chest": ["chest"], "back": ["back"], "legs": ["quads", "glutes", "hamstrings"]}

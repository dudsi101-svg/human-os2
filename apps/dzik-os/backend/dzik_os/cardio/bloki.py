"""Ładowanie wbudowanych bloków do katalogu trenera — jedna funkcja dla
przycisku w panelu (`routers/exercise_blocks.py`) i seedu demo, żeby demo
i produkcja dostawały dokładnie to samo (wzorzec `import_library`)."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import Exercise, ExerciseBlock, new_id
from .bloki_wbudowane import BLOKI, ZRODLO_WBUDOWANE, klucz


def zaladuj_wbudowane(db: Session, coach_id: str) -> dict:
    """Idempotentne: blok o tym samym (rodzaj, poziom, wariant) i źródle
    wbudowanym nie jest dodawany drugi raz ani nadpisywany (zmiany trenera
    zostają). Pozycje dostają `exercise_id` po nazwie z AKTYWNEJ bazy tego
    trenera — miękko: brak wpisu nie blokuje bloku."""
    istniejace = {
        (r.kind, r.level, r.variant)
        for r in db.query(ExerciseBlock).filter(ExerciseBlock.coach_id == coach_id,
                                                ExerciseBlock.source == ZRODLO_WBUDOWANE).all()
    }
    baza = {r.name: r.id for r in db.query(Exercise).filter(Exercise.coach_id == coach_id,
                                                           Exercise.status == "ACTIVE").all()}
    dodane, pominiete, bez_karty = 0, 0, 0
    ids: dict[tuple[str, str | None, str], str] = {}
    for blok in BLOKI:
        if klucz(blok) in istniejace:
            pominiete += 1
            continue
        items = []
        for p in blok["items"]:
            eid = baza.get(p["name"]) if p["catalog"] else None
            if p["catalog"] and eid is None:
                bez_karty += 1
            items.append({"name": p["name"], "dose": p["dose"], "note": p["note"], "exercise_id": eid})
        row = ExerciseBlock(id=new_id("BLK"), coach_id=coach_id, created_by=coach_id, kind=blok["kind"],
                            level=blok["level"], variant=blok["variant"], name=blok["name"],
                            duration_min=blok["duration_min"], source=ZRODLO_WBUDOWANE,
                            items_json=json.dumps(items, ensure_ascii=False))
        db.add(row)
        ids[klucz(blok)] = row.id
        dodane += 1
    return {"created": dodane, "skipped": pominiete, "items_without_card": bez_karty,
            "total_builtin": len(BLOKI), "ids": ids}


def migawka(row: ExerciseBlock) -> dict:
    """Migawka treści bloku do pozycji planu (`block`) — archiwizacja bloku
    nie zmienia opublikowanego planu."""
    return {"name": row.name, "kind": row.kind, "level": row.level, "variant": row.variant,
            "duration_min": row.duration_min, "items": json.loads(row.items_json or "[]")}

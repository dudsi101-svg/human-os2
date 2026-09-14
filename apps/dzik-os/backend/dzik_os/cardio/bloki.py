"""Ładowanie wbudowanych bloków do katalogu trenera — jedna funkcja dla
przycisku w panelu (`routers/exercise_blocks.py`) i seedu demo, żeby demo
i produkcja dostawały dokładnie to samo (wzorzec `import_library`) — oraz
(0.76.0) składanie bloków w pozycje planu: „bloki jak szablony”.

Czyste funkcje bez FastAPI: walidacja zestawu bloków rzuca `BladZestawu`
(router odpowiada 422), a własność/istnienie bloku sprawdza router
(`require_owned_resource` → 404 z audytem przy cudzym bloku).
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import Exercise, ExerciseBlock, new_id
from .bloki_wbudowane import BLOKI, ETYKIETY_RODZAJOW, ZRODLO_WBUDOWANE, klucz
from .presety import cel_dominujacy

#: Rodzaj bloku → `kind` pozycji planu (kontrakt z `schemas.ExerciseIn`).
RODZAJ_POZYCJI: dict[str, str] = {"WARMUP": "warmup_block", "CARDIO": "cardio", "STRETCH": "stretch_block"}
#: Klucze raportu `blocks_applied.added` w kolejności wstawiania do dnia.
KOLEJNOSC_RODZAJOW: tuple[str, ...] = ("WARMUP", "CARDIO", "STRETCH")
KLUCZ_RAPORTU: dict[str, str] = {"WARMUP": "warmup", "CARDIO": "cardio", "STRETCH": "stretch"}
MAKS_BLOKOW = 3


class BladZestawu(ValueError):
    """Zestaw bloków do przypisania jest niepoprawny (router: 422, komunikat po polsku)."""


def zaladuj_wbudowane(db: Session, coach_id: str) -> dict:
    """Idempotentne: blok o tym samym kluczu (rodzaj, poziom, wariant/cel) i
    źródle wbudowanym nie jest dodawany drugi raz ani nadpisywany (zmiany
    trenera zostają). Pozycje dostają `exercise_id` po nazwie z AKTYWNEJ bazy
    tego trenera — miękko: brak wpisu nie blokuje bloku."""
    istniejace = {
        klucz_wiersza(r)
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
                            level=blok["level"], variant=blok["variant"] or "", name=blok["name"],
                            duration_min=blok["duration_min"], source=ZRODLO_WBUDOWANE,
                            items_json=json.dumps(items, ensure_ascii=False),
                            cardio_json=json.dumps(blok["cardio"], ensure_ascii=False) if blok.get("cardio") else None)
        db.add(row)
        ids[klucz(blok)] = row.id
        dodane += 1
    return {"created": dodane, "skipped": pominiete, "items_without_card": bez_karty,
            "total_builtin": len(BLOKI), "ids": ids}


def cardio_z_bloku(row: ExerciseBlock) -> dict | None:
    """Preset cardio bloku (`CardioIn` jako dict) — tylko dla `kind == CARDIO`."""
    if row.kind != "CARDIO" or not row.cardio_json:
        return None
    return json.loads(row.cardio_json)


def cel_bloku(row: ExerciseBlock) -> str | None:
    return cel_dominujacy(cardio_z_bloku(row))


def klucz_wiersza(row: ExerciseBlock) -> tuple[str, str | None, str]:
    """Ten sam klucz co `bloki_wbudowane.klucz`, ale z wiersza bazy."""
    if row.kind == "CARDIO":
        return (row.kind, row.level, cel_bloku(row) or "")
    return (row.kind, row.level, row.variant)


def migawka(row: ExerciseBlock) -> dict:
    """Migawka treści bloku do pozycji planu (`block`) — archiwizacja bloku
    nie zmienia opublikowanego planu. `variant` = None dla CARDIO."""
    return {"name": row.name, "kind": row.kind, "level": row.level, # Pusty napis to zapis wariantu „nie dotyczy” dla CARDIO (kolumna NOT NULL
        # z migracji 39). Dla rozgrzewki i rozciągania wariant jest obowiązkowy —
        # nie zamieniamy go na None, bo taka migawka nie przeszłaby walidacji.
        "variant": (row.variant or None) if row.kind == "CARDIO" else row.variant,
            "duration_min": row.duration_min, "items": json.loads(row.items_json or "[]")}


def pozycja_z_bloku(row: ExerciseBlock) -> dict:
    """Pozycja planu z bloku: rozgrzewka/rozciąganie = `kind` bloku + migawka;
    CARDIO = pozycja `kind: "cardio"` z kopią presetu (`cardio`) + `block_id`
    + migawka, żeby widoki i odznaki działały jak dla bloków."""
    poz = {"name": row.name, "kind": RODZAJ_POZYCJI[row.kind], "block_id": row.id, "block": migawka(row)}
    if row.kind == "CARDIO":
        cardio = cardio_z_bloku(row)
        if cardio is None:
            raise BladZestawu(f"Blok „{row.name}” nie ma presetu cardio — zapisz go ponownie w Szablonach → Bloki.")
        poz["cardio"] = json.loads(json.dumps(cardio))
    return poz


def waliduj_zestaw(bloki: list[ExerciseBlock]) -> dict[str, ExerciseBlock]:
    """Maks. 3 bloki, maks. jeden na rodzaj, wszystkie ACTIVE. Zwraca rodzaj → blok."""
    if len(bloki) > MAKS_BLOKOW:
        raise BladZestawu(f"Maksymalnie {MAKS_BLOKOW} bloki naraz (po jednym: rozgrzewka, aeroby, rozciąganie).")
    wg_rodzaju: dict[str, ExerciseBlock] = {}
    for b in bloki:
        if b.status != "ACTIVE":
            raise BladZestawu(f"Blok „{b.name}” jest zarchiwizowany — przywróć go w Szablonach → Bloki albo wybierz inny.")
        if b.kind in wg_rodzaju:
            raise BladZestawu(f"Dwa bloki tego samego rodzaju ({ETYKIETY_RODZAJOW.get(b.kind, b.kind)}) — "
                              "wybierz po jednym na rodzaj.")
        wg_rodzaju[b.kind] = b
    return wg_rodzaju


def _rodzaj_pozycji(ex: object) -> str:
    if not isinstance(ex, dict):
        return "strength"
    k = ex.get("kind")
    return k if k in RODZAJ_POZYCJI.values() else "strength"


def wstaw_do_dnia(exercises: list[dict], poz: dict) -> list[dict]:
    """Kolejność w dniu: rozgrzewka na początek, rozciąganie na koniec, cardio
    po pozycjach siłowych (przed rozciąganiem, jeśli jest) — jak `PlanEditor`."""
    kind = poz.get("kind")
    if kind == "warmup_block":
        return [poz, *exercises]
    if kind == "cardio":
        ostatni = exercises[-1] if exercises else None
        if ostatni is not None and _rodzaj_pozycji(ostatni) == "stretch_block":
            return [*exercises[:-1], poz, ostatni]
    return [*exercises, poz]


def zloz_bloki_do_dni(days: list[dict], bloki: list[ExerciseBlock]) -> tuple[list[dict], dict]:
    """Każdy dzień dostaje pozycje z bloków (WARMUP, CARDIO, STRETCH w tej
    kolejności wstawiania); dzień, który już ma pozycję danego rodzaju
    (szablon go zawierał), nie jest dublowany — trafia do `skipped_days`.
    Nie modyfikuje wejścia. Zwraca (dni, raport `blocks_applied`)."""
    wg_rodzaju = waliduj_zestaw(bloki)
    added = {KLUCZ_RAPORTU[k]: 0 for k in KOLEJNOSC_RODZAJOW}
    skipped: list[dict] = []
    out_days: list[dict] = []
    for di, day in enumerate(days):
        d = json.loads(json.dumps(day))
        exercises = list(d.get("exercises") or [])
        obecne = {_rodzaj_pozycji(ex) for ex in exercises}
        for kind in KOLEJNOSC_RODZAJOW:
            b = wg_rodzaju.get(kind)
            if b is None:
                continue
            if RODZAJ_POZYCJI[kind] in obecne:
                skipped.append({"day_index": di, "day_name": d.get("name"), "kind": KLUCZ_RAPORTU[kind]})
                continue
            exercises = wstaw_do_dnia(exercises, pozycja_z_bloku(b))
            added[KLUCZ_RAPORTU[kind]] += 1
        d["exercises"] = exercises
        out_days.append(d)
    return out_days, {"added": added, "skipped_days": skipped,
                      "blocks": [{"id": b.id, "kind": b.kind, "name": b.name} for b in bloki]}

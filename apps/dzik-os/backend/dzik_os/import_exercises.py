"""Import biblioteki ćwiczeń trenera V2 do bazy ćwiczeń (`exercises`).

Dane źródłowe leżą w `exercise_catalog_v2.py` (proweniencja, szablonowość
kolumn opisowych i powód, dla którego nowe pozycje dostają notatkę „opis
ogólny” — patrz nagłówek tamtego modułu). Tutaj jest wszystko, co zamienia
te dane na wiersze bazy: jawne tablice mapowania, raport wartości
nierozpoznanych i sam import.

DWIE DROGI URUCHOMIENIA, jedna logika (`import_library`):

    python -m dzik_os.import_exercises --dry-run    # próba, nic nie zapisuje
    python -m dzik_os.import_exercises              # import
    POST /api/coach/exercises/import-library?dry_run=true|false

Import zawsze idzie do katalogu KONKRETNEGO trenera (`coach_id`) — nigdy
„do wszystkich”. Katalogi trenerów są rozłączne, więc import u jednego nie
dotyka ani jednego wiersza drugiego.

TRZY ZASADY, KTÓRE RZĄDZĄ TYM MODUŁEM:

1. **Nie zgadujemy.** Wartość, której nie da się jednoznacznie zmapować na
   słownik `muscles.py`, NIE trafia do bazy — zostaje pusta i ląduje w
   raporcie (`unmapped_muscles`, `unmapped_patterns`). Wzorzec ruchu jest
   uzupełniany `IZOLACJA` wyłącznie wtedy, gdy źródło samo nazywa ćwiczenie
   „izolowanym”; w pozostałych przypadkach pole zostaje puste.
2. **Praca trenera jest nienaruszalna.** W istniejącym ćwiczeniu import
   uzupełnia WYŁĄCZNIE puste pola. Opis techniki napisany pod konkretne
   ćwiczenie nigdy nie zostaje nadpisany szablonem z biblioteki — bo
   szablon jest gorszy, a różnicy po zapisie nie dałoby się już odróżnić.
3. **Import jest idempotentny.** Drugi przebieg na tej samej bazie kończy
   się zerem utworzonych i zerem zmienionych pozycji; `updated_at` zmienia
   się tylko wtedy, gdy naprawdę coś się zmieniło.

Błąd pojedynczej pozycji nie przerywa importu — trafia do `errors` i
lecimy dalej (ten sam wzorzec co import CSV bazy produktów).

Granica roli (Human OS): to know-how treningowe, nie porada medyczna.
Moduł niczego nie ocenia i nie dobiera — przenosi materiał trenera do jego
własnego katalogu.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Any

from .exercise_catalog_v2 import (
    BENEFIT_TEXTS,
    BREATHING_TEXTS,
    EASIER_TEXTS,
    GENERIC_DESCRIPTION_NOTE,
    HARDER_TEXTS,
    LIBRARY_REF,
    LIBRARY_ROWS,
    MISTAKE_TEXTS,
    STEP_TEXTS,
    LibraryRow,
)
from .exercise_parser import SOURCE_IMPORTED, map_muscle_phrase
from .muscles import (
    EXERCISE_LEVELS,
    MOVEMENT_PATTERNS,
    MUSCLE_GROUPS,
    fold,
    join_muscles,
)

# ---------------------------------------------------------------------------
# TABLICE MAPOWANIA (jawne — nie ma tu dopasowania rozmytego).
# ---------------------------------------------------------------------------

#: Kategoria źródła (12 wartości) → nasza zgrubna grupa `muscle_group`.
#: Biceps, triceps i przedramiona lądują w jednej grupie „RĘCE”, bo tak
#: wygląda nasz słownik — rozróżnienie nie ginie, zostaje w mięśniach
#: głównych i w tagach.
CATEGORY_TO_GROUP: dict[str, str] = {
    "Klatka piersiowa": "KLATKA",
    "Plecy — najszerszy grzbietu": "PLECY",
    "Plecy — środek i góra": "PLECY",
    "Barki": "BARKI",
    "Biceps": "RECE",
    "Triceps": "RECE",
    "Mięśnie czworogłowe uda": "NOGI",
    "Tylna część uda": "NOGI",
    "Pośladki": "NOGI",
    "Łydki i podudzie": "NOGI",
    "Brzuch i mięśnie głębokie": "BRZUCH",
    "Przedramiona i chwyt": "RECE",
}

#: Poziom trudności: pojedyncza nazwa → klucz `EXERCISE_LEVELS`.
LEVEL_NAMES: dict[str, str] = {
    "początkujący": "POCZATKUJACY",
    "średniozaawansowany": "SREDNIOZAAWANSOWANY",
    "zaawansowany": "ZAAWANSOWANY",
}

#: Wzorzec ruchowy źródła (48 wariantów tekstowych) → nasze 13 wzorców.
#:
#: W tablicy są WYŁĄCZNIE przypisania, które da się obronić: ruch nazwany w
#: źródle jest tym samym ruchem, co nasz wzorzec, albo jego wariantem
#: (jednonóż, skośnie, z dodatkową składową). Reszta 48 wariantów celowo
#: tu nie występuje — trafia pod regułę „izolowane → IZOLACJA”, a jeśli
#: źródło nazywa ćwiczenie wielostawowym albo stabilizacyjnym, zostaje
#: puste i idzie do raportu. Przykłady świadomie NIEMAPOWANE:
#: „antywyprost” (deska, kółko — to nie antyrotacja, a osobnego wzorca nie
#: mamy), „chwyt izometryczny” (zwis to nie noszenie) oraz warianty
#: łączone typu „wyprost łokcia/wypychanie”.
PATTERN_MAP: dict[str, str] = {
    "przysiad": "PRZYSIAD",
    "przysiad/wypychanie nóg": "PRZYSIAD",
    "wykrok": "WYKROK",
    "wykrok/przysiad jednonóż": "WYKROK",
    "wykrok/praca jednonóż": "WYKROK",
    # Wejście na podwyższenie to ten sam wzorzec pracy jednonóż co wykrok —
    # osobnego klucza nie mamy, a „przysiad” byłby dalej od prawdy.
    "wejście/praca jednonóż": "WYKROK",
    "zawias biodrowy": "ZAWIAS_BIODROWY",
    "zawias biodrowy jednonóż": "ZAWIAS_BIODROWY",
    "wyprost biodra": "ZAWIAS_BIODROWY",
    "zgięcie kolana/wyprost biodra": "ZAWIAS_BIODROWY",
    "wypychanie poziome": "WYPYCHANIE_POZIOME",
    # Ławka skośna dodatnia: w 13-elementowym słowniku nie ma osobnego
    # wzorca „skośnie”, a wyciskanie na skosie jest wariantem wypychania
    # poziomego, nie pionowego (tor ruchu bliżej klatki niż nad głowę).
    "wypychanie skośne": "WYPYCHANIE_POZIOME",
    "wypychanie pionowe": "WYPYCHANIE_PIONOWE",
    "przyciąganie poziome": "PRZYCIAGANIE_POZIOME",
    "przyciąganie poziome/rotacja zewnętrzna": "PRZYCIAGANIE_POZIOME",
    "przyciąganie pionowe": "PRZYCIAGANIE_PIONOWE",
    "antyrotacja": "ANTYROTACJA",
    "przenoszenie ciężaru": "NOSZENIE",
    "antyzgięcie boczne/chód": "NOSZENIE",
}

#: Nazwa rodzaju ćwiczenia, przy której nierozpoznany wzorzec wolno
#: uzupełnić `IZOLACJA` (źródło samo tak nazywa ruch).
KIND_ISOLATION = "izolowane"


def _assert_maps() -> None:
    """Kontrakt: tablice mapowania nie mają prawa wskazać wartości spoza
    słowników `muscles.py`, a każda kategoria źródła musi mieć grupę.
    Sprawdzane przy imporcie modułu i osobnym testem."""
    unknown_groups = set(CATEGORY_TO_GROUP.values()) - set(MUSCLE_GROUPS)
    unknown_levels = set(LEVEL_NAMES.values()) - set(EXERCISE_LEVELS)
    unknown_patterns = set(PATTERN_MAP.values()) - set(MOVEMENT_PATTERNS)
    missing = {row.category for row in LIBRARY_ROWS} - set(CATEGORY_TO_GROUP)
    if unknown_groups or unknown_levels or unknown_patterns or missing:
        raise RuntimeError(
            "Tablice mapowania importu wskazują wartości spoza kontraktu: "
            f"{sorted(unknown_groups | unknown_levels | unknown_patterns | missing)}"
        )


_assert_maps()


def normalize_name(text: str) -> str:
    """Nazwa sprowadzona do postaci porównywalnej: bez wielkości liter, bez
    polskich znaków, bez nadmiarowych spacji. Po tym kluczu import
    rozpoznaje, że ćwiczenie z biblioteki już jest w bazie trenera."""
    return " ".join(fold(text).split())


def map_level(raw: str) -> str | None:
    """Poziom trudności → klucz `EXERCISE_LEVELS` albo None.

    Źródło podaje w 25 wierszach parę („początkujący/średniozaawansowany”).
    ŚWIADOMA DECYZJA: bierzemy NIŻSZY z pary. Zawyżony poziom odsiewa
    ćwiczenie z wyszukiwarki komuś, kto spokojnie może je robić; zaniżony
    najwyżej pokaże je o jeden filtr za wcześnie, a i tak wybiera trener."""
    names = [part.strip().lower() for part in raw.split("/") if part.strip()]
    keys = [LEVEL_NAMES[n] for n in names if n in LEVEL_NAMES]
    if not keys:
        return None
    return min(keys, key=EXERCISE_LEVELS.index)


def map_pattern(raw: str, kind: str) -> str | None:
    """Wzorzec ruchowy źródła → nasz wzorzec albo None (do raportu)."""
    mapped = PATTERN_MAP.get(raw.strip())
    if mapped:
        return mapped
    if kind.strip().lower() == KIND_ISOLATION:
        return "IZOLACJA"
    return None


def map_muscles(names: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Lista nazw anatomicznych → (klucze partii, nazwy nierozpoznane)."""
    keys: list[str] = []
    unmapped: list[str] = []
    for name in names:
        hits = map_muscle_phrase(name)
        if not hits:
            unmapped.append(name)
            continue
        for key in hits:
            if key not in keys:
                keys.append(key)
    return keys, unmapped


@dataclass(frozen=True)
class MappedExercise:
    """Wiersz biblioteki po mapowaniu na nasz model — gotowy do zapisu.

    `unmapped_muscles` i `unmapped_pattern` niosą to, czego NIE zapisano.
    Puste pole ma być widoczne w raporcie, a nie domyślne."""

    source_id: str
    name: str
    name_en: str
    muscle_group: str
    equipment: str
    level: str | None
    pattern: str | None
    muscles_primary: list[str]
    muscles_secondary: list[str]
    steps: list[str]
    mistakes: list[str]
    benefit: str
    breathing: str
    easier: str
    harder: str
    tags: list[str]
    unmapped_muscles: list[str]
    unmapped_pattern: str | None

    @property
    def how_to(self) -> str:
        """Pole zgodności wstecznej — sklejone kroki (jak w `exercise_catalog`)."""
        return " ".join(self.steps)


def map_row(row: LibraryRow) -> MappedExercise:
    """Jeden wiersz biblioteki → postać zapisywalna w bazie."""
    primary, unmapped_primary = map_muscles(row.primary)
    secondary, unmapped_secondary = map_muscles(row.secondary)
    # Ta sama partia nie ma sensu w obu listach naraz — pierwszeństwo ma
    # lista głównych (tak samo robi parser opisu).
    secondary = [key for key in secondary if key not in primary]
    pattern = map_pattern(row.pattern, row.kind)
    # Rodzaj ćwiczenia nie ma osobnej kolumny w modelu; źródło i tak
    # powtarza go w tagach, więc pilnujemy tylko, żeby tam był.
    tags = list(row.tags)
    if row.kind and row.kind not in tags:
        tags.append(row.kind)
    return MappedExercise(
        source_id=row.id,
        name=row.name_pl,
        name_en=row.name_en,
        muscle_group=CATEGORY_TO_GROUP[row.category],
        equipment=", ".join(row.equipment),
        level=map_level(row.level),
        pattern=pattern,
        muscles_primary=primary,
        muscles_secondary=secondary,
        steps=list(STEP_TEXTS[row.steps]),
        mistakes=list(MISTAKE_TEXTS[row.mistakes]),
        benefit=BENEFIT_TEXTS[row.benefit],
        breathing=BREATHING_TEXTS[row.breathing],
        easier=EASIER_TEXTS[row.easier],
        harder=HARDER_TEXTS[row.harder],
        tags=tags,
        unmapped_muscles=[*unmapped_primary, *unmapped_secondary],
        unmapped_pattern=None if pattern else row.pattern,
    )


def mapped_library() -> list[MappedExercise]:
    """Cała biblioteka po mapowaniu (bez dotykania bazy)."""
    return [map_row(row) for row in LIBRARY_ROWS]


# ---------------------------------------------------------------------------
# Raport importu.
# ---------------------------------------------------------------------------


@dataclass
class ImportReport:
    """Wynik jednego przebiegu importu.

    `skipped` to pozycje, które już były w bazie i nie miały ani jednego
    pustego pola do uzupełnienia — przy powtórnym imporcie to całe 120."""

    created: int = 0
    enriched: int = 0
    skipped: int = 0
    unmapped_muscles: list[dict] = field(default_factory=list)
    unmapped_patterns: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    created_names: list[str] = field(default_factory=list)
    enriched_names: list[str] = field(default_factory=list)
    dry_run: bool = False

    def as_dict(self) -> dict:
        return {
            "created": self.created,
            "enriched": self.enriched,
            "skipped": self.skipped,
            "unmapped_muscles": self.unmapped_muscles,
            "unmapped_patterns": self.unmapped_patterns,
            "errors": self.errors,
            "created_names": self.created_names,
            "enriched_names": self.enriched_names,
            "dry_run": self.dry_run,
            "library": LIBRARY_REF,
            "total_rows": len(LIBRARY_ROWS),
        }


def _collect_unmapped(items: list[MappedExercise]) -> tuple[list[dict], list[dict]]:
    """Wartości, których nie zmapowano — z liczbą wystąpień i przykładami.

    Lista jest budowana z CAŁEJ biblioteki, nie tylko z pozycji zapisanych:
    trener ma widzieć, czego słownik nie zna, niezależnie od tego, czy
    dana pozycja akurat była już w bazie."""
    muscles: dict[str, list[str]] = {}
    patterns: dict[str, list[str]] = {}
    for item in items:
        for value in item.unmapped_muscles:
            muscles.setdefault(value, []).append(item.name)
        if item.unmapped_pattern:
            patterns.setdefault(item.unmapped_pattern, []).append(item.name)

    def rows(source: dict[str, list[str]]) -> list[dict]:
        return [
            {"value": value, "count": len(names), "examples": names[:3]}
            for value, names in sorted(
                source.items(), key=lambda kv: (-len(kv[1]), kv[0])
            )
        ]

    return rows(muscles), rows(patterns)


# ---------------------------------------------------------------------------
# Import do bazy.
# ---------------------------------------------------------------------------

#: Kolumny uzupełniane w ISTNIEJĄCYM ćwiczeniu, gdy są puste.
#: `how_to`, `muscle_group`, `safety`, `cues`, `tempo_hint` i `video_url`
#: są tu świadomie NIEOBECNE: pierwsze dwa są w bazie zawsze wypełnione
#: (nie ma czego uzupełniać), a pozostałych źródło po prostu nie zawiera.
_ENRICHED_COLUMNS: tuple[str, ...] = (
    "name_en", "tags_json", "benefit", "equipment", "level", "pattern",
    "muscles_primary", "muscles_secondary", "steps_json", "mistakes_json",
    "easier", "harder", "breathing",
)


def _dump_list(values: list[str]) -> str | None:
    return json.dumps(values, ensure_ascii=False) if values else None


def _is_empty(value: Any) -> bool:
    """Puste pole: NULL, sam biały znak albo pusta lista JSON."""
    if value is None:
        return True
    text = str(value).strip()
    return text in ("", "[]")


def _columns(item: MappedExercise) -> dict[str, Any]:
    """Wartości kolumn bazy dla jednej pozycji biblioteki (bez pustych)."""
    values: dict[str, Any] = {
        "name_en": item.name_en or None,
        "tags_json": _dump_list(item.tags),
        "benefit": item.benefit or None,
        "equipment": item.equipment or None,
        "level": item.level,
        "pattern": item.pattern,
        "muscles_primary": join_muscles(item.muscles_primary),
        "muscles_secondary": join_muscles(item.muscles_secondary),
        "steps_json": _dump_list(item.steps),
        "mistakes_json": _dump_list(item.mistakes),
        "easier": item.easier or None,
        "harder": item.harder or None,
        "breathing": item.breathing or None,
    }
    return {key: value for key, value in values.items() if value is not None}


def _changes_for_existing(existing: Any, item: MappedExercise) -> dict[str, Any]:
    """Co import dopisałby do istniejącego ćwiczenia — tylko puste pola.

    Nic tu nie nadpisuje wartości, która już jest: opis pisany pod
    konkretne ćwiczenie jest wart więcej niż szablon z biblioteki."""
    available = _columns(item)
    changes = {
        column: value
        for column, value in available.items()
        if column in _ENRICHED_COLUMNS and _is_empty(getattr(existing, column))
    }
    if changes and _is_empty(existing.source_ref):
        changes["source_ref"] = f"{LIBRARY_REF} — uzupełnienie pustych pól"
    return changes


def import_library(
    db: Any, coach_id: str, *, dry_run: bool = False
) -> ImportReport:
    """Import biblioteki do katalogu JEDNEGO trenera.

    Nie commituje — o trwałości decyduje wywołujący (endpoint, komenda albo
    seed). Przy `dry_run=True` nie dotyka ani jednego obiektu sesji, więc
    da się go bezpiecznie uruchomić jako podgląd przed zatwierdzeniem."""
    from .models import Exercise, new_id, now_iso

    items = mapped_library()
    report = ImportReport(dry_run=dry_run)
    report.unmapped_muscles, report.unmapped_patterns = _collect_unmapped(items)

    existing: dict[str, Exercise] = {}
    for row in db.query(Exercise).filter(Exercise.coach_id == coach_id).all():
        existing.setdefault(normalize_name(row.name), row)

    seen: set[str] = set()
    for item in items:
        key = normalize_name(item.name)
        if key in seen:
            report.errors.append({
                "exercise": item.name,
                "field": "nazwa",
                "message": "nazwa powtarza się w bibliotece — pozycja pominięta",
            })
            continue
        seen.add(key)
        current = existing.get(key)
        if current is None:
            report.created += 1
            report.created_names.append(item.name)
            if dry_run:
                continue
            record = Exercise(
                id=new_id("EXC"), coach_id=coach_id, created_by=coach_id,
                name=item.name, muscle_group=item.muscle_group,
                how_to=item.how_to,
                source_kind=SOURCE_IMPORTED, source_ref=LIBRARY_REF,
                # Notatka robocza dla trenera: opis techniki jest szablonem
                # wspólnym dla wzorca ruchu, nie tekstem o tym ćwiczeniu.
                # Klient tego pola nie dostaje (routers/exercises.py::_out).
                review_reason=GENERIC_DESCRIPTION_NOTE,
            )
            for column, value in _columns(item).items():
                setattr(record, column, value)
            db.add(record)
            existing[key] = record
            continue
        changes = _changes_for_existing(current, item)
        if not changes:
            report.skipped += 1
            continue
        report.enriched += 1
        report.enriched_names.append(current.name)
        if dry_run:
            continue
        for column, value in changes.items():
            setattr(current, column, value)
        current.updated_at = now_iso()

    return report


# ---------------------------------------------------------------------------
# Komenda (`python -m dzik_os.import_exercises`).
# ---------------------------------------------------------------------------


def _resolve_coach(db: Any, wanted: str | None) -> Any:
    """Trener, do którego katalogu idzie import.

    Bez `--coach` wolno importować tylko wtedy, gdy w bazie jest dokładnie
    jeden trener — inaczej komenda odmawia zamiast wybierać za człowieka."""
    from .models import RoleGrant, User

    coaches = (
        db.query(User)
        .join(RoleGrant, RoleGrant.user_id == User.id)
        .filter(RoleGrant.role == "COACH")
        .all()
    )
    if wanted:
        for coach in coaches:
            if wanted in (coach.id, coach.email):
                return coach
        raise SystemExit(f"[dzik-import] BŁĄD: nie znaleziono trenera „{wanted}”")
    if not coaches:
        raise SystemExit("[dzik-import] BŁĄD: w bazie nie ma żadnego trenera")
    if len(coaches) > 1:
        emails = ", ".join(sorted(c.email for c in coaches))
        raise SystemExit(
            "[dzik-import] BŁĄD: w bazie jest więcej niż jeden trener — wskaż "
            f"go opcją --coach (dostępni: {emails})"
        )
    return coaches[0]


def _print_report(report: ImportReport, coach_email: str) -> None:
    prefix = "[dzik-import]"
    tryb = "PRÓBA (nic nie zapisano)" if report.dry_run else "zapisano"
    print(f"{prefix} biblioteka: {LIBRARY_REF}, pozycji w źródle: "
          f"{len(LIBRARY_ROWS)}")
    print(f"{prefix} katalog trenera: {coach_email} — {tryb}")
    print(f"{prefix} utworzono: {report.created}, uzupełniono: "
          f"{report.enriched}, bez zmian: {report.skipped}")
    for label, rows in (
        ("nierozpoznane mięśnie", report.unmapped_muscles),
        ("nierozpoznane wzorce ruchu", report.unmapped_patterns),
    ):
        if not rows:
            print(f"{prefix} {label}: brak")
            continue
        print(f"{prefix} {label} ({len(rows)}) — pola zostają PUSTE:")
        for entry in rows:
            print(f"{prefix}   {entry['value']} "
                  f"(x{entry['count']}, np. {entry['examples'][0]})")
    for error in report.errors:
        print(f"{prefix} BŁĄD: {error['exercise']} — {error['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m dzik_os.import_exercises",
        description="Import biblioteki ćwiczeń trenera V2 do bazy ćwiczeń.",
    )
    parser.add_argument("--coach", default=None,
                        help="e-mail albo identyfikator trenera (wymagany, gdy "
                             "w bazie jest więcej niż jeden trener)")
    parser.add_argument("--dry-run", action="store_true",
                        help="pokaż raport, nie zapisuj niczego")
    args = parser.parse_args(argv)

    from .db import db_session, run_migrations
    from .hos_bridge import record_event

    run_migrations()
    with db_session() as db:
        coach = _resolve_coach(db, args.coach)
        report = import_library(db, coach.id, dry_run=args.dry_run)
        if not args.dry_run:
            record_event(
                db, action="EXERCISE_LIBRARY_IMPORTED", actor_id=coach.id,
                subject_ids=[coach.id],
                payload={
                    "library": LIBRARY_REF, "created": report.created,
                    "enriched": report.enriched, "skipped": report.skipped,
                    "unmapped_muscles": len(report.unmapped_muscles),
                    "unmapped_patterns": len(report.unmapped_patterns),
                    "source": "cli",
                },
                summary=f"Baza ćwiczeń: import biblioteki „{LIBRARY_REF}” — "
                        f"{report.created} nowych, {report.enriched} uzupełnionych",
            )
        _print_report(report, coach.email)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

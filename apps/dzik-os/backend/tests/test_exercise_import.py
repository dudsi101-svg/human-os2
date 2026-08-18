"""Import biblioteki ćwiczeń trenera V2 (`dzik_os/import_exercises.py`).

Testy pilnują trzech rzeczy, które łatwo zepsuć po cichu:

* mapowanie NIE zgaduje — nierozpoznana nazwa mięśnia albo wzorca zostaje
  pusta i ląduje w raporcie, zamiast trafić na najbliższy klucz;
* import nie nadpisuje pracy trenera i jest idempotentny;
* katalogi trenerów są rozłączne, a `--dry-run` naprawdę nic nie zapisuje.
"""

from conftest import CLIENT_A, COACH, create_user_with_role, login

from dzik_os.db import db_session
from dzik_os.exercise_catalog_v2 import (
    GENERIC_DESCRIPTION_NOTE,
    LIBRARY_REF,
    LIBRARY_ROWS,
)
from dzik_os.exercise_parser import SOURCE_IMPORTED, map_muscle_phrase
from dzik_os.import_exercises import (
    CATEGORY_TO_GROUP,
    PATTERN_MAP,
    ImportReport,
    import_library,
    map_level,
    map_pattern,
    map_row,
    mapped_library,
    normalize_name,
)
from dzik_os.models import Exercise, User, new_id
from dzik_os.muscles import MOVEMENT_PATTERNS, MUSCLE_GROUPS, split_muscles

# --- Mapowanie: mięśnie ----------------------------------------------------


def test_maps_anatomical_muscle_names_from_the_library():
    """Formy anatomiczne z pliku trafiają na właściwe klucze słownika."""
    assert map_muscle_phrase("mięsień piersiowy większy") == ["KLATKA_PIERSIOWA"]
    assert map_muscle_phrase("przednia część mięśnia naramiennego") == ["BARK_PRZEDNI"]
    assert map_muscle_phrase("tylna część mięśnia naramiennego") == ["BARK_TYLNY"]
    assert map_muscle_phrase("boczna część mięśnia naramiennego") == ["BARK_BOCZNY"]
    assert map_muscle_phrase("mięśnie kulszowo-goleniowe") == ["DWUGLOWY_UDA"]
    assert map_muscle_phrase("mięsień ramienno-promieniowy") == ["PRZEDRAMIE"]
    assert map_muscle_phrase("mięśnie międzyłopatkowe") == ["ROMBOIDALNE"]
    assert map_muscle_phrase("mięsień brzuchaty łydki") == ["LYDKA"]


def test_oblique_name_does_not_drag_in_rectus_abdominis():
    """„Skośne brzucha” to skośne — nie skośne PLUS prosty brzucha."""
    assert map_muscle_phrase("mięśnie skośne brzucha") == ["BRZUCH_SKOSNY"]
    assert map_muscle_phrase("skośne brzucha") == ["BRZUCH_SKOSNY"]


def test_ambiguous_muscle_names_are_refused_not_guessed():
    """Nazwa wskazująca na kilka kluczy naraz zostaje nierozpoznana."""
    for phrase in ("barki", "obręcz barkowa", "mięsień naramienny",
                   "górne plecy", "nogi", "mięśnie łopatki"):
        assert map_muscle_phrase(phrase) == [], phrase


def test_muscles_absent_from_the_dictionary_stay_unmapped():
    """Mięśnie, dla których po prostu nie mamy klucza (ramienny, obły
    większy, zębaty przedni, piszczelowy przedni), nie są podpinane pod
    „najbliższy” klucz."""
    for phrase in ("mięsień ramienny", "obły większy", "zębaty przedni",
                   "mięsień piszczelowy przedni", "dźwigacz łopatki"):
        assert map_muscle_phrase(phrase) == [], phrase


# --- Mapowanie: poziom i wzorzec -------------------------------------------


def test_double_level_takes_the_lower_one():
    assert map_level("początkujący") == "POCZATKUJACY"
    assert map_level("początkujący/średniozaawansowany") == "POCZATKUJACY"
    assert map_level("średniozaawansowany/zaawansowany") == "SREDNIOZAAWANSOWANY"
    assert map_level("nieznany poziom") is None


def test_unknown_pattern_falls_back_to_isolation_only_for_isolation_exercises():
    assert map_pattern("wypychanie poziome", "wielostawowe") == "WYPYCHANIE_POZIOME"
    # Nierozpoznany wzorzec + „izolowane” = IZOLACJA (źródło samo tak mówi).
    assert map_pattern("zgięcie łokcia", "izolowane") == "IZOLACJA"
    assert map_pattern("pronacja/supinacja", "izolowane") == "IZOLACJA"
    # Nierozpoznany wzorzec + cokolwiek innego = PUSTE, bez upychania.
    assert map_pattern("antywyprost", "stabilizacyjne") is None
    assert map_pattern("chwyt izometryczny", "izometryczne") is None
    assert map_pattern("wyprost łokcia/wypychanie", "wielostawowe") is None


def test_mapping_tables_stay_inside_the_dictionaries():
    assert set(CATEGORY_TO_GROUP.values()) <= set(MUSCLE_GROUPS)
    assert set(PATTERN_MAP.values()) <= set(MOVEMENT_PATTERNS)
    assert {row.category for row in LIBRARY_ROWS} <= set(CATEGORY_TO_GROUP)


def test_report_lists_unmapped_values_instead_of_hiding_them():
    """Raport wypisuje osobno nierozpoznane mięśnie i wzorce, z liczbą
    wystąpień — brak ma być widoczny, nie domyślny."""
    items = mapped_library()
    report = ImportReport()
    from dzik_os.import_exercises import _collect_unmapped

    report.unmapped_muscles, report.unmapped_patterns = _collect_unmapped(items)
    muscles = {entry["value"] for entry in report.unmapped_muscles}
    patterns = {entry["value"] for entry in report.unmapped_patterns}
    assert "mięsień ramienny" in muscles
    assert "obły większy" in muscles
    assert "antywyprost" in patterns
    assert "chwyt izometryczny" in patterns
    for entry in report.unmapped_muscles + report.unmapped_patterns:
        assert entry["count"] >= 1
        assert entry["examples"]
    # Wzorce, które umiemy zmapować, NIE mają prawa tu być.
    assert "wypychanie poziome" not in patterns
    assert "zgięcie łokcia" not in patterns  # trafia na IZOLACJA


def test_mapped_row_keeps_english_name_kind_and_tags():
    row = next(r for r in LIBRARY_ROWS if r.id == "EX-KLATKA-001")
    mapped = map_row(row)
    assert mapped.name_en == "Barbell Bench Press"
    assert mapped.muscle_group == "KLATKA"
    assert mapped.level == "SREDNIOZAAWANSOWANY"
    assert mapped.pattern == "WYPYCHANIE_POZIOME"
    assert mapped.muscles_primary == ["KLATKA_PIERSIOWA"]
    assert "TRICEPS" in mapped.muscles_secondary
    # Rodzaj ćwiczenia nie ma osobnej kolumny — mieszka w tagach.
    assert "wielostawowe" in mapped.tags
    assert mapped.equipment == "sztanga, ławka, stojaki"


def test_primary_muscle_never_repeats_in_secondary():
    for item in mapped_library():
        assert not set(item.muscles_primary) & set(item.muscles_secondary)


# --- Import do bazy --------------------------------------------------------


def _fresh_coach(email: str = "trener.import@example.com") -> str:
    return create_user_with_role(email, "InnyTrener#2026", "Trener Import", "COACH")


def test_import_into_empty_catalog_creates_every_row(client):
    coach_id = _fresh_coach()
    with db_session() as db:
        report = import_library(db, coach_id)
    assert report.created == len(LIBRARY_ROWS) == 120
    assert report.enriched == 0
    assert report.skipped == 0
    assert report.errors == []

    with db_session() as db:
        rows = db.query(Exercise).filter(Exercise.coach_id == coach_id).all()
        assert len(rows) == 120
        sample = next(r for r in rows if r.name == "Wyciskanie sztangi na ławce poziomej")
        assert sample.name_en == "Barbell Bench Press"
        assert sample.muscle_group == "KLATKA"
        assert split_muscles(sample.muscles_primary) == ["KLATKA_PIERSIOWA"]
        assert sample.how_to  # pole zgodności wstecznej złożone z kroków
        # Proweniencja: widać, że pozycja przyszła z importu i z jakiej
        # biblioteki (migracja nr 22 + 24).
        assert sample.source_kind == SOURCE_IMPORTED
        assert sample.source_ref == LIBRARY_REF
        assert sample.source_engine is None
        # Opis jest szablonowy, więc pozycja jest oznaczona do dopracowania.
        assert sample.review_reason == GENERIC_DESCRIPTION_NOTE


def test_repeated_import_changes_nothing(client):
    coach_id = _fresh_coach("trener.dwa@example.com")
    with db_session() as db:
        import_library(db, coach_id)
    with db_session() as db:
        rows = db.query(Exercise).filter(Exercise.coach_id == coach_id).all()
        stamps = {r.id: r.updated_at for r in rows}

    with db_session() as db:
        second = import_library(db, coach_id)
    assert second.created == 0
    assert second.enriched == 0
    assert second.skipped == 120
    assert second.errors == []

    with db_session() as db:
        rows = db.query(Exercise).filter(Exercise.coach_id == coach_id).all()
        assert len(rows) == 120
        # Idempotencja obejmuje też znacznik zmiany — nic się nie „odświeżyło”.
        assert {r.id: r.updated_at for r in rows} == stamps


def test_import_only_fills_empty_fields_of_existing_exercise(client):
    coach_id = _fresh_coach("trener.trzy@example.com")
    own_steps = ["Mój własny krok pierwszy.", "Mój własny krok drugi."]
    with db_session() as db:
        db.add(Exercise(
            id=new_id("EXC"), coach_id=coach_id, created_by=coach_id,
            # Ta sama nazwa co w bibliotece, tylko inaczej zapisana.
            name="wyciskanie sztangi na ławce poziomej",
            muscle_group="KLATKA", how_to="Mój opis pisany pod to ćwiczenie.",
            steps_json='["Mój własny krok pierwszy.", "Mój własny krok drugi."]',
            benefit="Mój własny efekt.",
        ))

    with db_session() as db:
        report = import_library(db, coach_id)
    assert report.created == 119
    assert report.enriched == 1
    assert report.skipped == 0

    with db_session() as db:
        item = (
            db.query(Exercise)
            .filter(Exercise.coach_id == coach_id,
                    Exercise.name == "wyciskanie sztangi na ławce poziomej")
            .one()
        )
        # NIENARUSZONE: opis pisany pod konkretne ćwiczenie.
        assert item.how_to == "Mój opis pisany pod to ćwiczenie."
        assert item.benefit == "Mój własny efekt."
        import json as _json
        assert _json.loads(item.steps_json) == own_steps
        # UZUPEŁNIONE: pola, które były puste.
        assert item.name_en == "Barbell Bench Press"
        assert item.level == "SREDNIOZAAWANSOWANY"
        assert item.pattern == "WYPYCHANIE_POZIOME"
        assert split_muscles(item.muscles_primary) == ["KLATKA_PIERSIOWA"]
        assert item.tags_json
        # Ćwiczenie trenera NIE dostaje notatki „opis ogólny” — jego opis
        # jest jego własny, a proweniencja mówi tylko o uzupełnieniu.
        assert item.review_reason is None
        assert item.source_kind is None
        assert "uzupełnienie pustych pól" in item.source_ref


def test_import_does_not_touch_another_coach_catalog(client):
    first = _fresh_coach("trener.a@example.com")
    second = _fresh_coach("trener.b@example.com")
    with db_session() as db:
        db.add(Exercise(
            id=new_id("EXC"), coach_id=second, created_by=second,
            name="Wyciskanie sztangi na ławce poziomej", muscle_group="KLATKA",
            how_to="Opis drugiego trenera.",
        ))
    with db_session() as db:
        import_library(db, first)

    with db_session() as db:
        others = db.query(Exercise).filter(Exercise.coach_id == second).all()
        assert len(others) == 1
        assert others[0].how_to == "Opis drugiego trenera."
        assert others[0].name_en is None
        assert db.query(Exercise).filter(Exercise.coach_id == first).count() == 120


def test_dry_run_writes_nothing(client):
    coach_id = _fresh_coach("trener.proba@example.com")
    with db_session() as db:
        report = import_library(db, coach_id, dry_run=True)
    assert report.dry_run is True
    assert report.created == 120
    with db_session() as db:
        assert db.query(Exercise).filter(Exercise.coach_id == coach_id).count() == 0


# --- Endpoint panelu trenera ----------------------------------------------


def test_endpoint_previews_then_imports(seeded):
    """Przycisk w panelu: najpierw podgląd raportu, dopiero potem zapis."""
    hc = login(seeded, COACH)
    before = seeded.get("/api/coach/exercises?limit=1", headers=hc).json()["total"]

    preview = seeded.post(
        "/api/coach/exercises/import-library?dry_run=true", headers=hc
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["dry_run"] is True
    assert body["total_rows"] == 120
    assert body["library"] == LIBRARY_REF
    assert set(body) >= {
        "created", "enriched", "skipped", "unmapped_muscles",
        "unmapped_patterns", "errors",
    }
    after_preview = seeded.get("/api/coach/exercises?limit=1", headers=hc).json()["total"]
    assert after_preview == before  # podgląd niczego nie zapisał

    done = seeded.post(
        "/api/coach/exercises/import-library?dry_run=false", headers=hc
    ).json()
    assert done["dry_run"] is False
    # Seed uruchamia ten sam import, więc na zasianej bazie nie ma już nic
    # do zrobienia — to również dowód idempotencji na pełnej ścieżce API.
    assert done["created"] == 0
    assert done["enriched"] == 0
    assert done["skipped"] == 120


def test_seeded_catalog_contains_the_library(seeded):
    hc = login(seeded, COACH)
    body = seeded.get("/api/coach/exercises?q=bench press", headers=hc).json()
    names = [i["name"] for i in body["items"]]
    assert "Wyciskanie sztangi na ławce poziomej" in names
    item = next(i for i in body["items"] if i["source_kind"] == "IMPORTED")
    assert item["source_ref"] == LIBRARY_REF
    assert item["review_reason"] == GENERIC_DESCRIPTION_NOTE
    assert item["tags"]


def test_client_never_sees_the_working_note(seeded):
    """Notatka „opis ogólny” jest informacją roboczą trenera. Klient nie
    dostaje jej w żadnej odpowiedzi — dla niego wyglądałaby jak ocena
    jakości wystawiona przez system."""
    ha = login(seeded, CLIENT_A)
    body = seeded.get("/api/me/exercises?q=bench press", headers=ha).json()
    assert body["items"]
    for item in body["items"]:
        assert "review_reason" not in item
    one = seeded.get(f"/api/me/exercises/{body['items'][0]['id']}", headers=ha).json()
    assert "review_reason" not in one
    assert "name_en" in one  # nazwa angielska jest przydatna i jawna


def test_coach_can_clear_the_working_note(seeded):
    """Notatkę zdejmuje trener zwykłym zapisem — to jego notatka."""
    hc = login(seeded, COACH)
    items = seeded.get("/api/coach/exercises?q=bench press", headers=hc).json()["items"]
    item = next(i for i in items if i.get("review_reason"))
    payload = {
        "name": item["name"], "muscle_group": item["muscle_group"],
        "how_to": "Mój opis po swojemu.", "name_en": item["name_en"],
        "tags": item["tags"], "source_kind": item["source_kind"],
        "source_ref": item["source_ref"], "review_reason": None,
    }
    updated = seeded.put(
        f"/api/coach/exercises/{item['id']}", headers=hc, json=payload
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["review_reason"] is None
    assert updated.json()["source_ref"] == item["source_ref"]


def test_import_endpoint_is_closed_to_clients(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/coach/exercises/import-library?dry_run=true", headers=ha)
    assert r.status_code == 403


# --- Komenda ---------------------------------------------------------------


def test_cli_dry_run_writes_nothing_and_prints_the_report(client, capsys):
    from dzik_os import import_exercises

    coach_email = "trener.cli@example.com"
    _fresh_coach(coach_email)
    assert import_exercises.main(["--coach", coach_email, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "PRÓBA (nic nie zapisano)" in out
    assert "utworzono: 120" in out
    assert "nierozpoznane mięśnie" in out
    with db_session() as db:
        coach = db.query(User).filter(User.email == coach_email).one()
        assert db.query(Exercise).filter(Exercise.coach_id == coach.id).count() == 0


def test_cli_refuses_to_choose_between_coaches(client):
    from dzik_os import import_exercises

    _fresh_coach("trener.jeden@example.com")
    _fresh_coach("trener.dwa2@example.com")
    try:
        import_exercises.main([])
    except SystemExit as exc:
        assert "więcej niż jeden trener" in str(exc)
    else:  # pragma: no cover - brak odmowy byłby błędem
        raise AssertionError("komenda powinna odmówić wyboru trenera")


def test_normalize_name_ignores_case_and_polish_letters():
    assert normalize_name("Wyciskanie SZTANGI") == normalize_name("wyciskanie sztangi")
    assert normalize_name("Ściąganie drążka") == normalize_name("sciaganie  drazka")

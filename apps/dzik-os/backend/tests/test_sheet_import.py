"""Import bazy danych trenera z pliku (`dzik_os/sheet_import.py`).

Testy pilnują tego, co przy imporcie z pliku najłatwiej zepsuć po cichu:

* PRÓBA naprawdę niczego nie zapisuje — również przy poprawnym pliku;
* import nie zgaduje: wartość spoza słownika pomija wiersz albo zostawia
  puste pole i ląduje w raporcie, zamiast trafić na „najbliższy” klucz;
* praca trenera jest nienaruszalna — pusta komórka nigdy nie kasuje danych,
  a tryb domyślny nie nadpisuje wypełnionych pól;
* szablon nie jest nadpisywany, tylko wersjonowany, a identyczny plik nie
  tworzy pustej wersji;
* katalogi trenerów są rozłączne i eksport wraca importem bez zmian.
"""

import io
import json

import pytest
from conftest import COACH, create_user_with_role, login

from dzik_os.db import db_session
from dzik_os.models import Exercise, TrainingPlan, TrainingPlanVersion
from dzik_os.sheet_import import (
    EXERCISE_COLUMNS,
    MODE_FILL,
    MODE_REPLACE,
    TEMPLATE_COLUMNS,
    SheetError,
    map_muscle_cell,
    map_value,
    norm_header,
    read_table,
)

SECOND_COACH = {"email": "trener.dwa@example.com", "password": "DrugiTrener#2026"}

EXERCISE_HEADER = "nazwa,grupa,opis,poziom,wzorzec,miesnie_glowne,kroki\n"
TEMPLATE_HEADER = "szablon,dzien,cwiczenie,dzien_nr,pozycja,serie,powtorzenia\n"


def upload(client, headers, url, body: str, *, filename="baza.csv", **params):
    return client.post(
        url, headers=headers, params=params,
        files={"file": (filename, body.encode("utf-8"), "text/csv")},
    )


def import_exercises(client, headers, body: str, **params):
    return upload(client, headers, "/api/coach/exercises/import-file", body, **params)


def fresh_coach(client, email: str) -> dict:
    """Trener z pustą bazą — podróż w obie strony ma sprawdzać NASZ format,
    a nie zgodność danych demonstracyjnych z jego kanoniczną postacią."""
    creds = {"email": email, "password": "SwiezyTrener#2026"}
    create_user_with_role(creds["email"], creds["password"], "Trener Eksport", "COACH")
    return login(client, creds)


def import_templates(client, headers, body: str, **params):
    return upload(client, headers, "/api/coach/plan-templates/import-file", body,
                  filename="szablony.csv", **params)


# --- Czytanie pliku --------------------------------------------------------


def test_header_normalization_accepts_polish_spelling_and_aliases():
    """Nagłówek „Nazwa ćwiczenia” i „name” to ta sama kolumna — kontrakt
    aliasów jest wypisany, nie zgadywany."""
    assert norm_header("  Nazwa  ") == "nazwa"
    assert norm_header("Mięśnie główne") == "miesnie_glowne"
    assert norm_header("dzień-tygodnia") == "dzien_tygodnia"
    rows, unknown, _ = read_table(
        "b.csv", "name;kategoria;how_to\nPrzysiad;NOGI;Zejdź w dół\n".encode(),
        EXERCISE_COLUMNS,
    )
    assert rows == [{"nazwa": "Przysiad", "grupa": "NOGI", "opis": "Zejdź w dół"}]
    assert unknown == []


def test_unknown_columns_are_reported_not_silently_dropped():
    rows, unknown, _ = read_table(
        "b.csv", b"nazwa,grupa,opis,cena\nPrzysiad,NOGI,Opis,10\n", EXERCISE_COLUMNS
    )
    assert unknown == ["cena"]
    assert "cena" not in rows[0]


def test_missing_required_column_refuses_the_whole_file():
    with pytest.raises(SheetError) as exc:
        read_table("b.csv", b"nazwa,opis\nPrzysiad,Opis\n", EXERCISE_COLUMNS)
    assert "grupa" in str(exc.value)


def test_semicolon_and_bom_files_are_read():
    rows, _, _ = read_table(
        "b.csv", "﻿nazwa;grupa;opis\nPrzysiad;NOGI;Opis\n".encode(),
        EXERCISE_COLUMNS,
    )
    assert rows[0]["nazwa"] == "Przysiad"


def test_xlsx_is_accepted_and_integers_do_not_become_floats():
    """Excel zapisuje „3” jako 3.0 — do planu ma trafić „3”, nie „3.0”."""
    openpyxl = pytest.importorskip("openpyxl")
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["szablon", "dzien", "cwiczenie", "serie"])
    sheet.append(["FBW", "Dzień A", "Przysiad", 3])
    buffer = io.BytesIO()
    book.save(buffer)
    rows, _, _ = read_table("baza.xlsx", buffer.getvalue(), TEMPLATE_COLUMNS)
    assert rows[0]["serie"] == "3"


def test_unsupported_format_is_refused_with_a_readable_message():
    with pytest.raises(SheetError) as exc:
        read_table("baza.pdf", b"%PDF-1.4", EXERCISE_COLUMNS)
    assert ".xlsx" in str(exc.value)


# --- Słowniki: brak zgadywania --------------------------------------------


def test_dictionary_accepts_key_and_polish_label_but_nothing_else():
    from dzik_os.sheet_import import LEVEL_VALUES, PATTERN_VALUES

    assert map_value("POCZATKUJACY", LEVEL_VALUES) == "POCZATKUJACY"
    assert map_value("początkujący", LEVEL_VALUES) == "POCZATKUJACY"
    assert map_value("zawias biodrowy", PATTERN_VALUES) == "ZAWIAS_BIODROWY"
    # Wartość spoza zamkniętego zbioru nie trafia na nic „podobnego”.
    assert map_value("łatwe", LEVEL_VALUES) is None
    assert map_value("pchanie czegoś", PATTERN_VALUES) is None


def test_collective_muscle_names_stay_unmapped():
    """Nazwa zbiorcza jest nierozpoznana, a nie „najbliższa” — inaczej
    rysunek sylwetki pokazywałby coś, czego trener nie napisał."""
    keys, unmapped = map_muscle_cell("klatka piersiowa, mięsień trójgłowy ramienia")
    assert keys == ["KLATKA_PIERSIOWA", "TRICEPS"]
    assert unmapped == []
    keys, unmapped = map_muscle_cell("góra ciała")
    assert keys == []
    assert unmapped == ["góra ciała"]


# --- Import ćwiczeń: próba przed zapisem ----------------------------------


def test_dry_run_reports_everything_and_writes_nothing(client, seeded):
    headers = login(client, COACH)
    body = EXERCISE_HEADER + (
        "Przysiad testowy,NOGI,Zejdź w dół i wróć,POCZATKUJACY,PRZYSIAD,"
        "czworogłowy uda,Ustaw stopy|Zejdź|Wróć\n"
    )
    r = import_exercises(client, headers, body, dry_run="true")
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["dry_run"] is True
    assert report["created"] == 1
    assert report["created_names"] == ["Przysiad testowy"]
    with db_session() as db:
        assert db.query(Exercise).filter(Exercise.name == "Przysiad testowy").count() == 0

    r = import_exercises(client, headers, body, dry_run="false")
    assert r.json()["created"] == 1
    with db_session() as db:
        item = db.query(Exercise).filter(Exercise.name == "Przysiad testowy").one()
        assert item.muscle_group == "NOGI"
        assert item.level == "POCZATKUJACY"
        assert item.pattern == "PRZYSIAD"
        assert item.muscles_primary == "CZWOROGLOWY_UDA"
        assert json.loads(item.steps_json) == ["Ustaw stopy", "Zejdź", "Wróć"]
        assert item.source_kind == "IMPORTED"
        assert item.source_ref == "baza.csv"


def test_second_import_of_the_same_file_changes_nothing(client, seeded):
    headers = login(client, COACH)
    body = EXERCISE_HEADER + "Martwy ciąg testowy,NOGI,Podnieś sztangę,,,,\n"
    import_exercises(client, headers, body, dry_run="false")
    report = import_exercises(client, headers, body, dry_run="false").json()
    assert (report["created"], report["updated"]) == (0, 0)
    assert report["unchanged"] == 1


def test_fill_mode_never_overwrites_existing_description(client, seeded):
    headers = login(client, COACH)
    import_exercises(
        client, headers,
        EXERCISE_HEADER + "Wiosłowanie testowe,PLECY,Mój własny opis,,,,\n",
        dry_run="false",
    )
    body = EXERCISE_HEADER + "Wiosłowanie testowe,PLECY,Opis z pliku,ZAAWANSOWANY,,,\n"
    report = import_exercises(client, headers, body, dry_run="false").json()
    assert report["updated"] == 1  # dopisany poziom, opis nietknięty
    with db_session() as db:
        item = db.query(Exercise).filter(Exercise.name == "Wiosłowanie testowe").one()
        assert item.how_to == "Mój własny opis"
        assert item.level == "ZAAWANSOWANY"

    report = import_exercises(client, headers, body, mode=MODE_REPLACE,
                              dry_run="false").json()
    assert report["updated"] == 1
    with db_session() as db:
        item = db.query(Exercise).filter(Exercise.name == "Wiosłowanie testowe").one()
        assert item.how_to == "Opis z pliku"


def test_empty_cell_never_erases_stored_data(client, seeded):
    """Także w trybie ZASTAP: brak komórki znaczy „nie wiem”, nie „usuń”."""
    headers = login(client, COACH)
    import_exercises(
        client, headers,
        EXERCISE_HEADER + "Podciąganie testowe,PLECY,Opis,ZAAWANSOWANY,,,\n",
        dry_run="false",
    )
    import_exercises(
        client, headers,
        EXERCISE_HEADER + "Podciąganie testowe,PLECY,Opis,,,,\n",
        mode=MODE_REPLACE, dry_run="false",
    )
    with db_session() as db:
        item = db.query(Exercise).filter(Exercise.name == "Podciąganie testowe").one()
        assert item.level == "ZAAWANSOWANY"


def test_bad_rows_are_skipped_with_a_reason_and_the_rest_imports(client, seeded):
    headers = login(client, COACH)
    body = EXERCISE_HEADER + (
        ",NOGI,Bez nazwy,,,,\n"
        "Dobre ćwiczenie,NOGI,Opis,,,,\n"
        "Zła grupa,UDA_I_POSLADKI,Opis,,,,\n"
        "Dobre ćwiczenie,NOGI,Duplikat,,,,\n"
        "Bez opisu,NOGI,,,,,\n"
    )
    report = import_exercises(client, headers, body, dry_run="false").json()
    assert report["created"] == 1
    assert report["skipped"] == 4
    columns = [e["column"] for e in report["errors"]]
    assert columns == ["nazwa", "grupa", "nazwa", "opis"]
    with db_session() as db:
        assert db.query(Exercise).filter(Exercise.name == "Zła grupa").count() == 0


def test_unknown_level_leaves_field_empty_and_warns(client, seeded):
    headers = login(client, COACH)
    body = EXERCISE_HEADER + "Bieg testowy,CARDIO,Biegnij,łatwe,,,\n"
    report = import_exercises(client, headers, body, dry_run="false").json()
    assert report["created"] == 1
    assert any("łatwe" in w for w in report["warnings"])
    with db_session() as db:
        assert db.query(Exercise).filter(Exercise.name == "Bieg testowy").one().level is None


def test_unmapped_muscles_reach_the_report(client, seeded):
    headers = login(client, COACH)
    body = EXERCISE_HEADER + "Ćwiczenie X,INNE,Opis,,,góra ciała,\n"
    report = import_exercises(client, headers, body, dry_run="false").json()
    assert report["unmapped_muscles"] == ["góra ciała"]
    with db_session() as db:
        item = db.query(Exercise).filter(Exercise.name == "Ćwiczenie X").one()
        assert item.muscles_primary is None


def test_import_never_touches_another_coach_catalog(client, seeded):
    create_user_with_role(SECOND_COACH["email"], SECOND_COACH["password"], "Trener 2", "COACH")
    first = login(client, COACH)
    second = login(client, SECOND_COACH)
    body = EXERCISE_HEADER + "Wspólna nazwa,NOGI,Opis pierwszego,,,,\n"
    import_exercises(client, first, body, dry_run="false")
    report = import_exercises(
        client, second, EXERCISE_HEADER + "Wspólna nazwa,NOGI,Opis drugiego,,,,\n",
        dry_run="false",
    ).json()
    assert report["created"] == 1  # u drugiego trenera to NOWA pozycja
    with db_session() as db:
        rows = db.query(Exercise).filter(Exercise.name == "Wspólna nazwa").all()
        assert {r.how_to for r in rows} == {"Opis pierwszego", "Opis drugiego"}


def test_client_cannot_import_or_export(client, seeded):
    from conftest import CLIENT_A

    headers = login(client, CLIENT_A)
    assert import_exercises(client, headers, EXERCISE_HEADER).status_code == 403
    assert client.get("/api/coach/exercises/export-file", headers=headers).status_code == 403
    assert import_templates(client, headers, TEMPLATE_HEADER).status_code == 403


# --- Import szablonów treningowych ----------------------------------------


def test_template_import_builds_days_in_order_and_links_the_catalog(client, seeded):
    headers = login(client, COACH)
    import_exercises(
        client, headers, EXERCISE_HEADER + "Przysiad z bazy,NOGI,Opis,,,,\n",
        dry_run="false",
    )
    body = TEMPLATE_HEADER + (
        "Plan testowy,Dzień B,Przysiad z bazy,2,1,4,8\n"
        "Plan testowy,Dzień A,Wykrok spoza bazy,1,2,3,10\n"
        "Plan testowy,Dzień A,Przysiad z bazy,1,1,5,5\n"
    )
    report = import_templates(client, headers, body, dry_run="false").json()
    assert report["created"] == 1
    assert report["linked"] == 2
    assert report["unlinked_exercises"] == ["Wykrok spoza bazy"]
    with db_session() as db:
        plan = db.query(TrainingPlan).filter(TrainingPlan.title == "Plan testowy").one()
        assert plan.is_template is True
        assert plan.client_id is None
        version = db.query(TrainingPlanVersion).filter_by(
            plan_id=plan.id, version_no=1).one()
        days = json.loads(version.content_json)["days"]
        assert [d["name"] for d in days] == ["Dzień A", "Dzień B"]
        assert [e["name"] for e in days[0]["exercises"]] == [
            "Przysiad z bazy", "Wykrok spoza bazy"]
        assert days[0]["exercises"][0]["exercise_id"] is not None
        assert days[0]["exercises"][1]["exercise_id"] is None
        assert days[0]["exercises"][0]["sets"] == "5"


def test_template_import_versions_instead_of_overwriting(client, seeded):
    headers = login(client, COACH)
    first = TEMPLATE_HEADER + "Plan wersjonowany,Dzień A,Przysiad,1,1,3,10\n"
    import_templates(client, headers, first, dry_run="false")
    # Ten sam plik: żadnej pustej wersji „bo import”.
    report = import_templates(client, headers, first, dry_run="false").json()
    assert (report["created"], report["updated"], report["unchanged"]) == (0, 0, 1)

    changed = TEMPLATE_HEADER + "Plan wersjonowany,Dzień A,Przysiad,1,1,5,5\n"
    report = import_templates(client, headers, changed, dry_run="false").json()
    assert report["updated"] == 1
    with db_session() as db:
        plan = db.query(TrainingPlan).filter(
            TrainingPlan.title == "Plan wersjonowany").one()
        assert plan.current_version_no == 2
        versions = db.query(TrainingPlanVersion).filter_by(plan_id=plan.id).all()
        # Historia zostaje: wersja 1 nadal jest w bazie.
        assert {v.version_no for v in versions} == {1, 2}
        old = next(v for v in versions if v.version_no == 1)
        assert json.loads(old.content_json)["days"][0]["exercises"][0]["sets"] == "3"


def test_template_dry_run_writes_nothing(client, seeded):
    headers = login(client, COACH)
    body = TEMPLATE_HEADER + "Plan próbny,Dzień A,Przysiad,1,1,3,10\n"
    assert import_templates(client, headers, body, dry_run="true").json()["created"] == 1
    with db_session() as db:
        assert db.query(TrainingPlan).filter(
            TrainingPlan.title == "Plan próbny").count() == 0


def test_template_rows_without_required_cells_are_skipped(client, seeded):
    headers = login(client, COACH)
    body = TEMPLATE_HEADER + (
        ",Dzień A,Przysiad,1,1,3,10\n"
        "Plan braków,,Przysiad,1,1,3,10\n"
        "Plan braków,Dzień A,,1,1,3,10\n"
        "Plan braków,Dzień A,Przysiad,1,1,3,10\n"
    )
    report = import_templates(client, headers, body, dry_run="false").json()
    assert report["skipped"] == 3
    assert report["created"] == 1


# --- Wzór, kontrakt i podróż w obie strony --------------------------------


def test_schema_endpoint_matches_the_real_contract(client, seeded):
    headers = login(client, COACH)
    schema = client.get("/api/coach/exercises/import-schema", headers=headers).json()
    assert [c["key"] for c in schema["columns"]] == [c.key for c in EXERCISE_COLUMNS]
    required = {c["key"] for c in schema["columns"] if c["required"]}
    assert required == {"nazwa", "grupa", "opis"}
    assert {d["key"] for d in schema["dictionaries"]["poziom"]} == {
        "POCZATKUJACY", "SREDNIOZAAWANSOWANY", "ZAAWANSOWANY"}
    assert schema["modes"] == [MODE_FILL, MODE_REPLACE]


def test_downloaded_example_file_imports_without_a_single_error(client, seeded):
    """Wzór, który sam nie przechodzi importu, jest gorszy niż jego brak."""
    headers = login(client, COACH)
    for url, importer in (
        ("/api/coach/exercises/import-example", import_exercises),
        ("/api/coach/plan-templates/import-example", import_templates),
    ):
        example = client.get(url, headers=headers)
        assert example.status_code == 200
        report = importer(client, headers, example.text, dry_run="true").json()
        assert report["errors"] == []
        assert report["created"] == 1


def test_export_of_exercises_comes_back_through_import_unchanged(client):
    headers = fresh_coach(client, "eksport.cwiczenia@example.com")
    import_exercises(
        client, headers,
        EXERCISE_HEADER + "Runda testowa,BARKI,Opis techniki,ZAAWANSOWANY,"
                          "WYPYCHANIE_PIONOWE,bark przedni,Krok jeden|Krok dwa\n",
        dry_run="false",
    )
    exported = client.get("/api/coach/exercises/export-file", headers=headers)
    assert exported.status_code == 200
    assert "Runda testowa" in exported.text
    report = import_exercises(client, headers, exported.text,
                              filename="eksport.csv", dry_run="false").json()
    assert (report["created"], report["updated"]) == (0, 0)


def test_export_of_templates_comes_back_through_import_unchanged(client):
    headers = fresh_coach(client, "eksport.szablony@example.com")
    import_templates(
        client, headers,
        TEMPLATE_HEADER + "Plan eksportowany,Dzień A,Przysiad,1,1,4,8-10\n",
        dry_run="false",
    )
    exported = client.get("/api/coach/plan-templates/export-file", headers=headers)
    assert exported.status_code == 200
    report = import_templates(client, headers, exported.text, dry_run="false").json()
    assert (report["created"], report["updated"], report["unchanged"]) == (0, 0, 1)


def test_unreadable_file_is_a_422_not_a_500(client, seeded):
    headers = login(client, COACH)
    assert import_exercises(client, headers, "", filename="pusty.csv").status_code == 422
    assert upload(client, headers, "/api/coach/exercises/import-file", "cokolwiek",
                  filename="baza.pdf").status_code == 422


# --- Cofnięcie importu: nic nie ginie bezpowrotnie ------------------------


def test_replace_mode_is_reversible_field_by_field(client, seeded):
    """Sedno sprawy: tryb ZASTAP nadpisuje opis techniki, a ćwiczenia NIE
    mają historii wersji. Bez punktu przywracania byłaby to strata
    bezpowrotna — ten test pilnuje, że nie jest."""
    headers = login(client, COACH)
    import_exercises(
        client, headers,
        EXERCISE_HEADER + "Cofane ćwiczenie,PLECY,Mój opis pisany ręcznie,"
                          "POCZATKUJACY,,,Krok mój\n",
        dry_run="false",
    )
    r = import_exercises(
        client, headers,
        EXERCISE_HEADER + "Cofane ćwiczenie,BARKI,Opis z pliku,ZAAWANSOWANY,"
                          "WYPYCHANIE_PIONOWE,bark przedni,Krok z pliku\n",
        mode=MODE_REPLACE, dry_run="false",
    ).json()
    assert r["updated"] == 1
    snapshot_id = r["snapshot_id"]
    assert snapshot_id

    with db_session() as db:
        item = db.query(Exercise).filter(Exercise.name == "Cofane ćwiczenie").one()
        assert item.how_to == "Opis z pliku"

    undo = client.post(f"/api/coach/imports/{snapshot_id}/undo", headers=headers)
    assert undo.status_code == 200, undo.text
    assert undo.json()["restored"] == 1

    with db_session() as db:
        item = db.query(Exercise).filter(Exercise.name == "Cofane ćwiczenie").one()
        assert item.how_to == "Mój opis pisany ręcznie"
        assert item.muscle_group == "PLECY"
        assert item.level == "POCZATKUJACY"
        assert item.pattern is None
        assert item.muscles_primary is None
        assert json.loads(item.steps_json) == ["Krok mój"]
        assert item.status == "ACTIVE"  # istniejąca pozycja NIE jest archiwizowana


def test_undo_archives_created_exercises_instead_of_deleting(client, seeded):
    headers = login(client, COACH)
    r = import_exercises(
        client, headers, EXERCISE_HEADER + "Pomyłkowe ćwiczenie,NOGI,Opis,,,,\n",
        dry_run="false",
    ).json()
    client.post(f"/api/coach/imports/{r['snapshot_id']}/undo", headers=headers)
    with db_session() as db:
        item = db.query(Exercise).filter(Exercise.name == "Pomyłkowe ćwiczenie").one()
        # ARCHIWIZACJA, nie usunięcie — historia zostaje, trener może wrócić.
        assert item.status == "ARCHIVED"


def test_undo_of_template_import_creates_a_new_version_not_a_deletion(client, seeded):
    headers = login(client, COACH)
    import_templates(
        client, headers,
        TEMPLATE_HEADER + "Plan cofany,Dzień A,Przysiad,1,1,3,10\n", dry_run="false",
    )
    r = import_templates(
        client, headers,
        TEMPLATE_HEADER + "Plan cofany,Dzień A,Przysiad,1,1,9,1\n", dry_run="false",
    ).json()
    assert r["updated"] == 1
    client.post(f"/api/coach/imports/{r['snapshot_id']}/undo", headers=headers)
    with db_session() as db:
        plan = db.query(TrainingPlan).filter(TrainingPlan.title == "Plan cofany").one()
        assert plan.current_version_no == 3  # 1 import, 2 import, 3 cofnięcie
        versions = db.query(TrainingPlanVersion).filter_by(plan_id=plan.id).all()
        # Wszystkie trzy wersje istnieją — cofnięcie niczego nie skasowało.
        assert {v.version_no for v in versions} == {1, 2, 3}
        current = next(v for v in versions if v.version_no == 3)
        assert json.loads(current.content_json)["days"][0]["exercises"][0]["sets"] == "3"
        assert "Cofnięcie importu" in current.reason


def test_undo_works_only_once(client, seeded):
    headers = login(client, COACH)
    r = import_exercises(
        client, headers, EXERCISE_HEADER + "Jednorazowe cofnięcie,NOGI,Opis,,,,\n",
        dry_run="false",
    ).json()
    url = f"/api/coach/imports/{r['snapshot_id']}/undo"
    assert client.post(url, headers=headers).status_code == 200
    second = client.post(url, headers=headers)
    assert second.status_code == 422
    assert "już cofnięty" in second.json()["detail"]


def test_dry_run_leaves_no_restore_point(client, seeded):
    """Próba niczego nie zmienia, więc nie ma czego cofać — punkt
    przywracania po podglądzie byłby myląco pusty."""
    headers = login(client, COACH)
    r = import_exercises(
        client, headers, EXERCISE_HEADER + "Tylko podgląd,NOGI,Opis,,,,\n",
        dry_run="true",
    ).json()
    assert r["snapshot_id"] is None
    assert client.get("/api/coach/imports", headers=headers).json()["imports"] == []


def test_import_that_changes_nothing_leaves_no_restore_point(client, seeded):
    headers = login(client, COACH)
    body = EXERCISE_HEADER + "Bez zmian,NOGI,Opis,,,,\n"
    import_exercises(client, headers, body, dry_run="false")
    again = import_exercises(client, headers, body, dry_run="false").json()
    assert (again["created"], again["updated"]) == (0, 0)
    assert again["snapshot_id"] is None


def test_history_lists_own_imports_only_and_marks_undone(client, seeded):
    create_user_with_role(SECOND_COACH["email"], SECOND_COACH["password"],
                          "Trener 2", "COACH")
    first = login(client, COACH)
    second = login(client, SECOND_COACH)
    mine = import_exercises(
        client, first, EXERCISE_HEADER + "Moje ćwiczenie,NOGI,Opis,,,,\n",
        dry_run="false",
    ).json()
    import_exercises(
        client, second, EXERCISE_HEADER + "Cudze ćwiczenie,NOGI,Opis,,,,\n",
        dry_run="false",
    )
    history = client.get("/api/coach/imports", headers=first).json()["imports"]
    assert [h["id"] for h in history] == [mine["snapshot_id"]]
    assert history[0]["restored_at"] is None

    # Cudzej migawki nie da się cofnąć ani nawet potwierdzić jej istnienia.
    other = client.get("/api/coach/imports", headers=second).json()["imports"][0]
    denied = client.post(f"/api/coach/imports/{other['id']}/undo", headers=first)
    assert denied.status_code == 404
    assert client.post("/api/coach/imports/HOS-IMS-NIEISTNIEJE/undo",
                       headers=first).status_code == 404

    client.post(f"/api/coach/imports/{mine['snapshot_id']}/undo", headers=first)
    assert client.get("/api/coach/imports", headers=first).json()["imports"][0][
        "restored_at"] is not None


def test_client_cannot_see_or_undo_imports(client, seeded):
    from conftest import CLIENT_A

    headers = login(client, CLIENT_A)
    assert client.get("/api/coach/imports", headers=headers).status_code == 403
    assert client.post("/api/coach/imports/X/undo", headers=headers).status_code == 403


def test_snapshot_covers_every_field_the_import_writes():
    """Kontrakt pilnowany też przez `_assert_snapshot_covers_import()` przy
    imporcie modułu — tutaj jako jawny test, żeby powód był widoczny."""
    from dzik_os.sheet_import import (
        _EXERCISE_LIST_FIELDS,
        _EXERCISE_TEXT_FIELDS,
        SNAPSHOT_FIELDS,
    )

    written = {"muscle_group", "how_to", "level", "pattern",
               "muscles_primary", "muscles_secondary"}
    written |= {attr for _, attr in _EXERCISE_TEXT_FIELDS}
    written |= {attr for _, attr in _EXERCISE_LIST_FIELDS}
    assert written <= set(SNAPSHOT_FIELDS)


def test_old_restore_points_are_pruned(client, seeded):
    """Trzymamy ograniczoną liczbę migawek — cofnięcie sprzed wielu operacji
    przywracałoby stan sprzed późniejszych, świadomych zmian trenera."""
    from dzik_os.sheet_import import SNAPSHOT_KEEP

    headers = login(client, COACH)
    for i in range(SNAPSHOT_KEEP + 3):
        import_exercises(
            client, headers, EXERCISE_HEADER + f"Seryjne {i},NOGI,Opis {i},,,,\n",
            dry_run="false",
        )
    history = client.get("/api/coach/imports", headers=headers).json()["imports"]
    assert len(history) == SNAPSHOT_KEEP


def test_podglad_nie_dotyka_ani_jednego_obiektu_sesji(client, seeded):
    """Kontrakt `sheet_import`: przy `dry_run=True` funkcja NIE dotyka
    sesji — nie tylko „nic nie ląduje w bazie".

    Różnica jest realna. Dziś podgląd jest bezpieczny podwójnie: funkcja
    nic nie dodaje, a endpoint i tak nie commituje. Gdyby ktoś dołożył
    zapis do sesji w podglądzie, testy przez endpoint **nadal by
    przeszły** (obiekt zniknąłby przy zamknięciu sesji) — aż do dnia, w
    którym coś w tym samym żądaniu zrobi commit i podgląd zacznie po cichu
    zapisywać. Sprawdzone przeglądem mutacyjnym: bez tego testu mutant
    „podgląd jednak zapisuje" przeżywał całą suitę.
    """
    from dzik_os import sheet_import
    from dzik_os.models import User

    headers = login(client, COACH)
    coach_id = client.get("/api/auth/me", headers=headers).json()["id"]

    wiersze = [
        {"nazwa": "Podglądowe ćwiczenie", "grupa": "NOGI", "opis": "Opis"},
        {"nazwa": "Wiosłowanie hantlem", "grupa": "PLECY", "opis": "Inny opis"},
    ]
    with db_session() as db:
        assert db.query(User).filter(User.id == coach_id).one_or_none() is not None
        raport = sheet_import.import_exercises_sheet(
            db, coach_id, wiersze, dry_run=True, source_ref="podglad.csv"
        )
        assert raport.created >= 1, "podgląd ma raportować, co by powstało"
        # Sedno: żadnych nowych ani zmienionych obiektów w sesji.
        assert list(db.new) == [], f"podgląd dodał obiekty do sesji: {list(db.new)}"
        assert list(db.dirty) == [], f"podgląd zmienił obiekty w sesji: {list(db.dirty)}"
        assert raport.snapshot == [], "podgląd nie tworzy materiału na cofnięcie"

    with db_session() as db:
        raport = sheet_import.import_templates_sheet(
            db, coach_id,
            [{"szablon": "Podglądowy plan", "dzien": "Dzień A", "cwiczenie": "Przysiad"}],
            dry_run=True, source_ref="podglad.csv",
        )
        assert raport.created == 1
        assert list(db.new) == [], f"podgląd szablonów dodał obiekty: {list(db.new)}"
        assert list(db.dirty) == [], f"podgląd szablonów zmienił obiekty: {list(db.dirty)}"

"""Rozbudowana baza ćwiczeń: migracja nr 19, słownik partii mięśniowych,
filtry, wyszukiwanie odporne na polskie znaki, paginacja, zgodność
wsteczna oraz podpięcie pozycji planu do bazy (`exercise_id`)."""

from conftest import CLIENT_A, CLIENT_B, COACH, create_user_with_role, login

# --- Migracja i seed ---

def test_migration_19_adds_nullable_columns_to_existing_database(tmp_path):
    """Stara baza z tabelą `exercises` bez nowych kolumn dostaje je
    migracją nr 19; wszystkie są NULLable, więc istniejący wiersz działa
    dalej bez żadnego backfillu."""
    from sqlalchemy import create_engine, text

    from dzik_os.db import run_migrations

    eng = create_engine(f"sqlite:///{tmp_path}/stara.db")
    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, "
            "description TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        for version in range(1, 19):
            conn.execute(text("INSERT INTO schema_migrations(version, description) "
                              "VALUES (:v, 'stub')"), {"v": version})
        conn.execute(text(
            "CREATE TABLE exercises (id VARCHAR(40) PRIMARY KEY, "
            "coach_id VARCHAR(40), name VARCHAR(300), muscle_group VARCHAR(30), "
            "how_to TEXT, benefit TEXT, equipment VARCHAR(200), "
            "video_url VARCHAR(500), status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', "
            "created_by VARCHAR(40), created_at VARCHAR(40), updated_at VARCHAR(40))"))
        conn.execute(text(
            "INSERT INTO exercises(id, coach_id, name, muscle_group, how_to, status, "
            "created_by, created_at, updated_at) VALUES "
            "('EXC-1', 'C1', 'Stare ćwiczenie', 'NOGI', 'Opis', 'ACTIVE', 'C1', 'x', 'x')"))
        # Stuby dla migracji nr 20 (tekst OCR przy dokumencie, proweniencja
        # produktu) — migracje 1–18 są tu ostemplowane, więc tabele muszą
        # powstać ręcznie.
        conn.execute(text(
            "CREATE TABLE documents (id VARCHAR(40) PRIMARY KEY, "
            "client_id VARCHAR(40), file_id VARCHAR(40), title VARCHAR(300), "
            "category VARCHAR(40), uploaded_by VARCHAR(40), "
            "created_at VARCHAR(40), status VARCHAR(20))"))
        conn.execute(text(
            "CREATE TABLE food_products (id VARCHAR(40) PRIMARY KEY, "
            "coach_id VARCHAR(40), name VARCHAR(300), kcal_100g FLOAT)"))
        # Stub dla migracji nr 26 (kolumna `flow` w sesjach rozmów) — jak
        # wyżej: realna stara baza ma tę tabelę z migracji 17, tu powstaje
        # ręcznie, bo migracje 1–18 są tylko ostemplowane.
        conn.execute(text(
            "CREATE TABLE onboarding_sessions (id VARCHAR(40) PRIMARY KEY, "
            "client_id VARCHAR(40))"))

    applied = run_migrations(eng)
    assert 19 in applied
    with eng.connect() as conn:
        cols = {r[1]: r[3] for r in conn.exec_driver_sql("PRAGMA table_info(exercises)")}
        row = conn.exec_driver_sql(
            "SELECT name, muscles_primary, steps_json FROM exercises"
        ).fetchone()
    for col in ("muscles_primary", "muscles_secondary", "level", "pattern",
                "steps_json", "mistakes_json", "cues_json", "safety", "easier",
                "harder", "tempo_hint", "breathing"):
        assert col in cols, col
        assert cols[col] == 0, f"{col} musi być NULLable"
    # Istniejący wiersz przetrwał bez zmian, nowe pola są puste.
    assert row[0] == "Stare ćwiczenie"
    assert row[1] is None and row[2] is None


def test_seed_loads_full_catalog_without_duplicate_names(seeded):
    from dzik_os.db import db_session
    from dzik_os.models import Exercise

    with db_session() as db:
        rows = db.query(Exercise).all()
        names = [r.name for r in rows]
    assert len(rows) >= 150
    assert len(names) == len(set(names)), "duplikaty nazw w bazie trenera"
    # Komplet opisu dotyczy KATALOGU STARTOWEGO (pozycje pisane pod
    # konkretne ćwiczenie). Pozycje z importu biblioteki (`source_kind`
    # ustawione) świadomie nie mają wskazówek, uwag bezpieczeństwa ani
    # tempa — źródło ich nie zawiera, a wymyślanie ich byłoby wpisaniem do
    # bazy czegoś, czego nikt nie powiedział (docs/BAZA_CWICZEN.md §11).
    for row in [r for r in rows if r.source_kind is None]:
        assert row.steps_json and row.mistakes_json and row.cues_json, row.name
        assert row.muscles_primary, row.name
        assert row.level and row.pattern and row.safety, row.name
        assert row.easier and row.harder, row.name
        # Zgodność wsteczna: how_to zawsze wypełnione.
        assert row.how_to
    # Zgodność wsteczna obowiązuje jednak KAŻDE ćwiczenie w bazie.
    for row in rows:
        assert row.how_to, row.name


def test_catalog_uses_only_dictionary_keys():
    from dzik_os.exercise_catalog import CATALOG
    from dzik_os.muscles import (
        EXERCISE_LEVELS,
        MOVEMENT_PATTERNS,
        MUSCLE_GROUPS,
        MUSCLE_KEYS,
    )

    for row in CATALOG:
        assert row["group"] in MUSCLE_GROUPS, row["name"]
        assert row["level"] in EXERCISE_LEVELS, row["name"]
        assert row["pattern"] in MOVEMENT_PATTERNS, row["name"]
        for key in row["primary"] + row["secondary"]:
            assert key in MUSCLE_KEYS, (row["name"], key)


# --- Walidacja słownika ---

def test_unknown_muscle_key_rejected(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "Wymyślone", "muscle_group": "NOGI", "how_to": "opis",
        "muscles_primary": ["SKRZYDLA"],
    })
    assert r.status_code == 422
    r = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "Wymyślone", "muscle_group": "NOGI", "how_to": "opis",
        "muscles_secondary": ["POSLADKI", "OGON"],
    })
    assert r.status_code == 422


def test_unknown_level_or_pattern_rejected(seeded):
    hc = login(seeded, COACH)
    base = {"name": "X", "muscle_group": "NOGI", "how_to": "opis"}
    assert seeded.post("/api/coach/exercises", headers=hc,
                       json={**base, "level": "MISTRZ"}).status_code == 422
    assert seeded.post("/api/coach/exercises", headers=hc,
                       json={**base, "pattern": "SALTO"}).status_code == 422


def test_dictionary_endpoint_is_the_contract(seeded):
    ha = login(seeded, CLIENT_A)
    body = seeded.get("/api/exercise-dictionaries", headers=ha).json()
    assert body["muscles"]["KLATKA_PIERSIOWA"] == "klatka piersiowa"
    assert body["muscles"]["NAJSZERSZY_GRZBIETU"] == "najszerszy grzbietu"
    assert len(body["muscles"]) == 21
    assert set(body["levels"]) == {
        "POCZATKUJACY", "SREDNIOZAAWANSOWANY", "ZAAWANSOWANY"
    }
    assert "ANTYROTACJA" in body["patterns"]


def test_full_exercise_roundtrip(seeded):
    hc = login(seeded, COACH)
    payload = {
        "name": "Autorskie ćwiczenie", "muscle_group": "PLECY",
        "how_to": "Skrót", "benefit": "Efekt",
        "equipment": "Guma", "level": "POCZATKUJACY",
        "pattern": "PRZYCIAGANIE_POZIOME",
        "muscles_primary": ["NAJSZERSZY_GRZBIETU"],
        "muscles_secondary": ["BICEPS", "BARK_TYLNY"],
        "steps": ["Krok pierwszy", "Krok drugi", "Krok trzeci"],
        "mistakes": ["Błąd pierwszy", "Błąd drugi"],
        "cues": ["Łokcie do kieszeni"],
        "safety": "Przy bólu skonsultuj się ze specjalistą.",
        "easier": "Lżejsza guma", "harder": "Mocniejsza guma",
        "tempo_hint": "2011", "breathing": "Wydech przy ciągnięciu",
    }
    created = seeded.post("/api/coach/exercises", headers=hc, json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["steps"] == payload["steps"]
    assert body["muscles_secondary"] == ["BICEPS", "BARK_TYLNY"]
    assert body["level"] == "POCZATKUJACY"

    detail = seeded.get(f"/api/coach/exercises/{body['id']}", headers=hc).json()
    assert detail["cues"] == ["Łokcie do kieszeni"]
    assert detail["safety"].endswith("specjalistą.")


# --- Filtry, wyszukiwanie, paginacja ---

def test_filters_by_muscle_equipment_level_and_pattern(seeded):
    ha = login(seeded, CLIENT_A)

    by_muscle = seeded.get("/api/me/exercises?muscle=POSLADKI&limit=200",
                           headers=ha).json()
    assert by_muscle["total"] > 0
    assert all(
        "POSLADKI" in i["muscles_primary"] + i["muscles_secondary"]
        for i in by_muscle["items"]
    )

    by_equipment = seeded.get("/api/me/exercises?equipment=kettlebell&limit=200",
                              headers=ha).json()
    assert by_equipment["total"] > 0
    assert all("ettlebell" in (i["equipment"] or "") for i in by_equipment["items"])

    by_level = seeded.get("/api/me/exercises?level=ZAAWANSOWANY&limit=200",
                          headers=ha).json()
    assert by_level["total"] > 0
    assert all(i["level"] == "ZAAWANSOWANY" for i in by_level["items"])

    by_pattern = seeded.get("/api/me/exercises?pattern=ZAWIAS_BIODROWY&limit=200",
                            headers=ha).json()
    assert by_pattern["total"] > 0
    assert all(i["pattern"] == "ZAWIAS_BIODROWY" for i in by_pattern["items"])


def test_unknown_filter_value_is_422(seeded):
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/me/exercises?muscle=SKRZYDLA", headers=ha).status_code == 422
    assert seeded.get("/api/me/exercises?level=MISTRZ", headers=ha).status_code == 422
    assert seeded.get("/api/me/exercises?pattern=SALTO", headers=ha).status_code == 422


def test_search_is_polish_diacritics_insensitive(seeded):
    ha = login(seeded, CLIENT_A)

    def names(query: str) -> set[str]:
        body = seeded.get(f"/api/me/exercises?q={query}&limit=200", headers=ha).json()
        return {i["name"] for i in body["items"]}

    assert names("wioslowanie") == names("wiosłowanie") == names("WIOSŁOWANIE")
    assert any("Wiosłowanie" in n for n in names("wioslowanie"))
    assert "Przysiad ze sztangą" in names("sztanga") | names("przysiad")
    assert names("zolnierskie") == names("żołnierskie")
    assert names("nieistniejące-ćwiczenie") == set()


def test_pagination_returns_stable_window(seeded):
    ha = login(seeded, CLIENT_A)
    first = seeded.get("/api/me/exercises?limit=10", headers=ha).json()
    assert len(first["items"]) == 10
    assert first["has_more"] is True
    assert first["total"] >= 150

    second = seeded.get("/api/me/exercises?limit=10&offset=10", headers=ha).json()
    assert second["offset"] == 10
    assert {i["id"] for i in first["items"]} & {i["id"] for i in second["items"]} == set()

    tail = seeded.get(
        f"/api/me/exercises?limit=10&offset={first['total'] - 3}", headers=ha
    ).json()
    assert len(tail["items"]) == 3
    assert tail["has_more"] is False


def test_backward_compatible_exercise_without_new_fields(seeded):
    """Ćwiczenie zapisane po staremu (tylko how_to) nadal wraca z API i ma
    puste listy zamiast błędu."""
    hc = login(seeded, COACH)
    created = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "Stary wpis", "muscle_group": "BRZUCH", "how_to": "Sam opis techniki",
    })
    assert created.status_code == 201
    body = created.json()
    assert body["steps"] == [] and body["mistakes"] == [] and body["cues"] == []
    assert body["muscles_primary"] == [] and body["level"] is None

    ha = login(seeded, CLIENT_A)
    found = seeded.get("/api/me/exercises?q=Stary wpis", headers=ha).json()
    assert [i["name"] for i in found["items"]] == ["Stary wpis"]
    assert found["items"][0]["how_to"] == "Sam opis techniki"


# --- Izolacja trenerów i widoczność dla klienta ---

def test_other_coach_cannot_edit_extended_fields(seeded):
    hc = login(seeded, COACH)
    item_id = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "Moje ćwiczenie", "muscle_group": "NOGI", "how_to": "x",
        "muscles_primary": ["POSLADKI"],
    }).json()["id"]

    create_user_with_role("obcy.ex2@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.ex2@example.com", "password": "ObcyTrener#26"})
    r = seeded.put(f"/api/coach/exercises/{item_id}", headers=h2, json={
        "name": "Podmiana", "muscle_group": "NOGI", "how_to": "x",
    })
    assert r.status_code == 404
    assert seeded.get(f"/api/coach/exercises/{item_id}", headers=h2).status_code == 404
    # Właściciel nadal widzi swoje dane nienaruszone.
    mine = seeded.get(f"/api/coach/exercises/{item_id}", headers=hc).json()
    assert mine["name"] == "Moje ćwiczenie"


def test_client_detail_requires_active_relationship(seeded):
    hc = login(seeded, COACH)
    item_id = seeded.get("/api/coach/exercises?limit=1", headers=hc).json()["items"][0]["id"]

    ha = login(seeded, CLIENT_A)
    assert seeded.get(f"/api/me/exercises/{item_id}", headers=ha).status_code == 200

    # Osoba bez relacji z trenerem nie widzi ani listy, ani karty.
    create_user_with_role("obcy.klient@example.com", "ObcyKlient#26", "Obcy", "CLIENT")
    hx = login(seeded, {"email": "obcy.klient@example.com", "password": "ObcyKlient#26"})
    assert seeded.get("/api/me/exercises", headers=hx).json()["items"] == []
    assert seeded.get(f"/api/me/exercises/{item_id}", headers=hx).status_code == 404


def test_archived_exercise_disappears_from_client_view(seeded):
    hc = login(seeded, COACH)
    item_id = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "Do archiwum", "muscle_group": "NOGI", "how_to": "x",
    }).json()["id"]
    ha = login(seeded, CLIENT_A)
    assert seeded.get(f"/api/me/exercises/{item_id}", headers=ha).status_code == 200

    seeded.post(f"/api/coach/exercises/{item_id}/status?status=ARCHIVED", headers=hc)
    assert seeded.get(f"/api/me/exercises/{item_id}", headers=ha).status_code == 404
    # Trener nadal widzi zarchiwizowane w swoim filtrze.
    archived = seeded.get("/api/coach/exercises?status=ARCHIVED&limit=200",
                          headers=hc).json()
    assert item_id in {i["id"] for i in archived["items"]}


# --- Plan układany z bazy: kontrakt `exercise_id` ---

def _client_id(client, headers) -> str:
    return client.get("/api/auth/me", headers=headers).json()["id"]


def test_plan_item_can_reference_exercise_from_library(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = _client_id(seeded, ha)
    library = seeded.get("/api/coach/exercises?q=przysiad ze sztanga", headers=hc).json()
    exercise_id = library["items"][0]["id"]

    r = seeded.post("/api/plans", headers=hc, json={
        "client_id": client_id, "title": "Plan z bazy",
        "version": {"reason": "start", "days": [
            {"name": "Dzień A", "exercises": [
                {"name": "Przysiad ze sztangą", "exercise_id": exercise_id,
                 "sets": "4", "reps": "6"},
            ]},
        ]},
    })
    assert r.status_code == 201
    plan_id = r.json()["id"]
    versions = seeded.get(f"/api/plans/{plan_id}/versions", headers=hc).json()
    item = versions["versions"][0]["content"]["days"][0]["exercises"][0]
    assert item["exercise_id"] == exercise_id
    # Klient widzi to samo powiązanie i kartę ćwiczenia.
    assert seeded.get(f"/api/me/exercises/{exercise_id}", headers=ha).status_code == 200


def test_plan_rejects_foreign_or_unknown_exercise_id(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = _client_id(seeded, ha)

    create_user_with_role("obcy.trener3@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.trener3@example.com", "password": "ObcyTrener#26"})
    foreign_id = seeded.post("/api/coach/exercises", headers=h2, json={
        "name": "Cudze ćwiczenie", "muscle_group": "NOGI", "how_to": "x",
    }).json()["id"]

    for bad in (foreign_id, "EXC-NIE-ISTNIEJE"):
        r = seeded.post("/api/plans", headers=hc, json={
            "client_id": client_id, "title": "Plan",
            "version": {"reason": "start", "days": [
                {"name": "A", "exercises": [{"name": "X", "exercise_id": bad}]},
            ]},
        })
        assert r.status_code == 422, bad


def test_plan_rejects_archived_exercise_but_keeps_existing_plans(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = _client_id(seeded, ha)
    exercise_id = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "Tymczasowe", "muscle_group": "NOGI", "how_to": "x",
    }).json()["id"]

    created = seeded.post("/api/plans", headers=hc, json={
        "client_id": client_id, "title": "Plan z tymczasowym",
        "version": {"reason": "start", "days": [
            {"name": "A", "exercises": [
                {"name": "Tymczasowe", "exercise_id": exercise_id, "sets": "3"},
            ]},
        ]},
    })
    assert created.status_code == 201
    plan_id = created.json()["id"]

    seeded.post(f"/api/coach/exercises/{exercise_id}/status?status=ARCHIVED", headers=hc)

    # Istniejący plan działa dalej: nazwa i parametry są w treści wersji,
    # a `exercise_id` jest wyłącznie miękkim odniesieniem.
    plans = seeded.get(f"/api/clients/{client_id}/plans", headers=ha).json()["plans"]
    plan = next(p for p in plans if p["id"] == plan_id)
    item = plan["current_version"]["content"]["days"][0]["exercises"][0]
    assert item["name"] == "Tymczasowe" and item["sets"] == "3"
    assert item["exercise_id"] == exercise_id
    # Ale karta ćwiczenia już się klientowi nie pokaże (brak linku).
    assert seeded.get(f"/api/me/exercises/{exercise_id}", headers=ha).status_code == 404
    # I nowa wersja planu nie może już wskazać zarchiwizowanego ćwiczenia.
    r = seeded.post(f"/api/plans/{plan_id}/versions", headers=hc, json={
        "reason": "próba", "days": [
            {"name": "A", "exercises": [
                {"name": "Tymczasowe", "exercise_id": exercise_id},
            ]},
        ],
    })
    assert r.status_code == 422


def test_plan_without_exercise_id_still_works(seeded):
    """Ręczne wpisanie nazwy zostaje pełnoprawną ścieżką — aplikacja nie
    zamyka trenera w katalogu."""
    hc = login(seeded, COACH)
    hb = login(seeded, CLIENT_B)
    client_id = _client_id(seeded, hb)
    r = seeded.post("/api/plans", headers=hc, json={
        "client_id": client_id, "title": "Plan ręczny",
        "version": {"reason": "start", "days": [
            {"name": "A", "exercises": [{"name": "Autorskie ćwiczenie", "sets": "3"}]},
        ]},
    })
    assert r.status_code == 201
    versions = seeded.get(f"/api/plans/{r.json()['id']}/versions", headers=hc).json()
    item = versions["versions"][0]["content"]["days"][0]["exercises"][0]
    assert item["exercise_id"] is None


def test_seeded_plans_and_templates_are_linked_to_library(seeded):
    """Demo pokazuje docelowy przepływ: każda pozycja planów i szablonów
    wskazuje istniejące, aktywne ćwiczenie z bazy trenera."""
    import json

    from dzik_os.db import db_session
    from dzik_os.models import Exercise, TrainingPlanVersion

    with db_session() as db:
        active_ids = {
            r.id for r in db.query(Exercise).filter(Exercise.status == "ACTIVE").all()
        }
        versions = db.query(TrainingPlanVersion).all()
        payloads = [json.loads(v.content_json) for v in versions]

    checked = 0
    for content in payloads:
        for day in content["days"]:
            for item in day["exercises"]:
                assert item.get("exercise_id"), item["name"]
                assert item["exercise_id"] in active_ids, item["name"]
                checked += 1
    assert checked >= 10


def test_picker_search_uses_same_filters_as_library(seeded):
    """Wyszukiwarka w edytorze planu to ten sam endpoint co baza — filtry
    działają identycznie po stronie trenera."""
    hc = login(seeded, COACH)
    body = seeded.get(
        "/api/coach/exercises?q=przysiad&muscle=CZWOROGLOWY_UDA&status=ACTIVE&limit=5",
        headers=hc,
    ).json()
    assert body["total"] > 0
    assert len(body["items"]) <= 5
    for item in body["items"]:
        assert "przysiad" in item["name"].lower()
        assert "CZWOROGLOWY_UDA" in item["muscles_primary"] + item["muscles_secondary"]

"""Rozbudowana baza produktów spożywczych (runda 0.22.0): migracja nr 18,
katalog 300+ pozycji, wyszukiwanie odporne na polskie znaki, filtr
kategorii, stronicowanie, kalkulator porcji (gramy i sztuki) oraz
import/eksport CSV z izolacją trenerów.

Zasada uczciwości danych: informacja o przybliżonym charakterze wartości
(`disclaimer`) jest częścią odpowiedzi API — nie da się jej „zgubić” w
interfejsie."""

from conftest import CLIENT_A, COACH, create_user_with_role, login

# --- Migracja nr 18 ----------------------------------------------------

def test_migration_18_adds_columns_to_old_database(tmp_path):
    """Baza z v1 (tabela food_products bez nowych kolumn) dostaje migrację
    nr 18 bez utraty danych — same kolumny NULLable."""
    from sqlalchemy import create_engine, text

    from dzik_os.db import MIGRATIONS, run_migrations

    eng = create_engine(f"sqlite:///{tmp_path}/old.db")
    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, "
            "description TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO schema_migrations(version, description) "
                          "VALUES (1, 'initial')"))
        for table in ("users", "consents", "schedule_items", "weekly_checkins",
                      "workout_entries", "auth_sessions", "progress_photos"):
            conn.execute(text(f"CREATE TABLE {table} (id VARCHAR(40) PRIMARY KEY)"))
        conn.execute(text(
            "CREATE TABLE messages (id VARCHAR(40) PRIMARY KEY, "
            "thread_id VARCHAR(40), author_id VARCHAR(40), created_at VARCHAR(40))"))
        conn.execute(text(
            "CREATE TABLE payment_records (id VARCHAR(40) PRIMARY KEY, "
            "paid_at VARCHAR(40))"))
        # Stub tabeli food_products w kształcie sprzed migracji nr 18 —
        # migracja nr 5 nie nadpisze go (CREATE TABLE IF NOT EXISTS), więc
        # ALTER-y nr 18 działają na "starym" kształcie.
        conn.execute(text(
            "CREATE TABLE food_products (id VARCHAR(40) PRIMARY KEY, "
            "coach_id VARCHAR(40), name VARCHAR(300), category VARCHAR(80), "
            "kcal_100g FLOAT, protein_100g FLOAT, fat_100g FLOAT, carbs_100g FLOAT, "
            "default_portion_g FLOAT, status VARCHAR(20), created_by VARCHAR(40), "
            "created_at VARCHAR(40), updated_at VARCHAR(40))"))
        # Stub tabeli documents w kształcie sprzed migracji nr 20 (na
        # świeżej bazie tworzy ją ORM w migracji nr 1).
        conn.execute(text(
            "CREATE TABLE documents (id VARCHAR(40) PRIMARY KEY, "
            "client_id VARCHAR(40), file_id VARCHAR(40), title VARCHAR(300), "
            "category VARCHAR(40), uploaded_by VARCHAR(40), "
            "created_at VARCHAR(40), status VARCHAR(20))"))
        conn.execute(text(
            "INSERT INTO food_products(id, coach_id, name, category, kcal_100g, "
            "protein_100g, fat_100g, carbs_100g, status, created_by, created_at, "
            "updated_at) VALUES ('FOD-OLD', 'C1', 'Stary produkt', 'Inne', 100, 10, "
            "5, 10, 'ACTIVE', 'C1', 'x', 'x')"))

    applied = run_migrations(eng)
    assert 18 in applied
    assert applied == [v for v, _, _ in MIGRATIONS if v != 1]

    with eng.connect() as conn:
        cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(food_products)")]
        row = conn.exec_driver_sql(
            "SELECT name, kcal_100g, fiber_100g, unit_name, unit_grams, source, note "
            "FROM food_products WHERE id='FOD-OLD'"
        ).fetchone()
    assert {"fiber_100g", "unit_name", "unit_grams", "source", "note"} <= set(cols)
    # Zgodność wsteczna: stary wiersz żyje dalej, nowe pola są puste (NULL),
    # nigdy wyzerowane na 0 (0 g błonnika to twierdzenie, brak danych nie jest).
    assert row[0] == "Stary produkt" and row[1] == 100
    assert row[2] is None and row[3] is None and row[4] is None
    assert row[5] is None and row[6] is None


# --- Seed: rozmiar i spójność katalogu ---------------------------------

def test_seed_loads_full_catalog_without_duplicates(seeded):
    hc = login(seeded, COACH)
    r = seeded.get("/api/coach/food-products", headers=hc, params={"limit": 500})
    body = r.json()
    assert body["total"] >= 300
    names = [i["name"] for i in body["items"]]
    assert len(names) == len(set(names)), "duplikaty nazw w katalogu jednego trenera"
    # 16 kategorii z docs/BAZA_PRODUKTOW.md.
    assert len(body["categories"]) >= 16
    assert "Mięso i drób" in body["categories"]
    assert "Odżywki i suplementy" in body["categories"]


def test_seeded_products_carry_source_and_new_fields(seeded):
    hc = login(seeded, COACH)
    r = seeded.get("/api/coach/food-products", headers=hc, params={"q": "Jajo kurze całe"})
    egg = next(i for i in r.json()["items"] if i["name"].startswith("Jajo kurze całe"))
    assert egg["unit_name"] and egg["unit_grams"] == 50
    assert "uśrednione" in egg["source"]
    r = seeded.get("/api/coach/food-products", headers=hc, params={"q": "Chleb żytni"})
    bread = r.json()["items"][0]
    assert bread["unit_name"] == "kromka" and bread["unit_grams"] == 35
    assert bread["fiber_100g"] > 0


def test_catalog_response_carries_disclaimer(seeded):
    hc = login(seeded, COACH)
    body = seeded.get("/api/coach/food-products", headers=hc).json()
    assert "przybliżone" in body["disclaimer"]
    ha = login(seeded, CLIENT_A)
    client_body = seeded.get("/api/me/food-products", headers=ha).json()
    assert client_body["disclaimer"] == body["disclaimer"]


# --- Wyszukiwanie, filtrowanie, stronicowanie --------------------------

def test_search_ignores_case_and_polish_diacritics(seeded):
    hc = login(seeded, COACH)
    for query in ("łosoś", "losos", "ŁOSOŚ", "Losos"):
        items = seeded.get(
            "/api/coach/food-products", headers=hc, params={"q": query}
        ).json()["items"]
        assert any("Łosoś" in i["name"] for i in items), query


def test_search_falls_back_to_word_match(seeded):
    """„lososiowy” (odmiana, której nie ma w katalogu) i tak trafia w „Łosoś”."""
    hc = login(seeded, COACH)
    items = seeded.get(
        "/api/coach/food-products", headers=hc, params={"q": "lososiowy"}
    ).json()["items"]
    assert any(i["name"].startswith("Łosoś") for i in items)


def test_search_without_match_returns_empty_page(seeded):
    hc = login(seeded, COACH)
    body = seeded.get(
        "/api/coach/food-products", headers=hc, params={"q": "kwadratowy kamień"}
    ).json()
    assert body["items"] == [] and body["total"] == 0 and body["has_more"] is False


def test_category_filter_narrows_catalog(seeded):
    hc = login(seeded, COACH)
    body = seeded.get(
        "/api/coach/food-products", headers=hc,
        params={"category": "Ryby i owoce morza", "limit": 500},
    ).json()
    assert body["total"] >= 20
    assert all(i["category"] == "Ryby i owoce morza" for i in body["items"])


def test_pagination_does_not_load_whole_catalog(seeded):
    hc = login(seeded, COACH)
    first = seeded.get(
        "/api/coach/food-products", headers=hc, params={"limit": 25, "offset": 0}
    ).json()
    second = seeded.get(
        "/api/coach/food-products", headers=hc, params={"limit": 25, "offset": 25}
    ).json()
    assert len(first["items"]) == 25 and len(second["items"]) == 25
    assert first["has_more"] is True
    assert first["total"] == second["total"] >= 300
    assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})
    # Ostatnia strona: has_more gaśnie.
    last = seeded.get(
        "/api/coach/food-products", headers=hc,
        params={"limit": 25, "offset": first["total"] - 5},
    ).json()
    assert last["has_more"] is False and len(last["items"]) == 5


def test_sorting_by_kcal_and_protein(seeded):
    hc = login(seeded, COACH)
    by_kcal = seeded.get(
        "/api/coach/food-products", headers=hc, params={"sort": "kcal", "limit": 10}
    ).json()["items"]
    assert [i["kcal_100g"] for i in by_kcal] == sorted(
        (i["kcal_100g"] for i in by_kcal), reverse=True
    )
    by_protein = seeded.get(
        "/api/coach/food-products", headers=hc, params={"sort": "protein", "limit": 10}
    ).json()["items"]
    assert by_protein[0]["protein_100g"] >= 70
    by_name = seeded.get(
        "/api/coach/food-products", headers=hc, params={"sort": "name", "limit": 5}
    ).json()["items"]
    assert len(by_name) == 5


def test_client_list_is_paginated_and_hides_archived(seeded):
    hc = login(seeded, COACH)
    created = seeded.post("/api/coach/food-products", headers=hc, json={
        "name": "Produkt do archiwum", "category": "Inne",
        "kcal_100g": 100, "protein_100g": 5, "fat_100g": 5, "carbs_100g": 5,
    }).json()
    seeded.post(f"/api/coach/food-products/{created['id']}/status?status=ARCHIVED", headers=hc)
    ha = login(seeded, CLIENT_A)
    body = seeded.get(
        "/api/me/food-products", headers=ha, params={"q": "Produkt do archiwum"}
    ).json()
    assert body["items"] == []
    # Trener widzi archiwum na żądanie (status=ARCHIVED).
    archived = seeded.get(
        "/api/coach/food-products", headers=hc,
        params={"status": "ARCHIVED", "q": "Produkt do archiwum"},
    ).json()
    assert [i["id"] for i in archived["items"]] == [created["id"]]


# --- Kalkulator porcji -------------------------------------------------

def _find(seeded, headers, name):
    r = seeded.get("/api/coach/food-products", headers=headers, params={"q": name})
    return next(i for i in r.json()["items"] if i["name"] == name)


def test_portion_calculator_by_grams(seeded):
    hc = login(seeded, COACH)
    product = _find(seeded, hc, "Pierś z kurczaka, surowa")
    r = seeded.post("/api/food-products/portion", headers=hc,
                    json={"product_id": product["id"], "grams": 200})
    assert r.status_code == 200
    body = r.json()
    assert body["grams"] == 200 and body["units"] is None
    assert body["kcal"] == 220
    assert body["protein_g"] == 46.0
    assert "przybliżone" in body["disclaimer"]


def test_portion_calculator_by_units(seeded):
    """„2 jajka” = 110 g (jajko M bez skorupki ≈ 55 g w tym katalogu: 50 g)."""
    hc = login(seeded, COACH)
    egg = _find(seeded, hc, "Jajo kurze całe, surowe")
    r = seeded.post("/api/food-products/portion", headers=hc,
                    json={"product_id": egg["id"], "units": 2})
    body = r.json()
    assert body["grams"] == 100.0  # 2 × 50 g
    assert body["units"] == 2 and body["unit_name"].startswith("jajko")
    assert body["kcal"] == 143


def test_portion_calculator_reports_fiber_when_known(seeded):
    hc = login(seeded, COACH)
    bread = _find(seeded, hc, "Chleb żytni razowy")
    body = seeded.post("/api/food-products/portion", headers=hc,
                       json={"product_id": bread["id"], "units": 2}).json()
    assert body["grams"] == 70.0
    assert body["fiber_g"] == round(6.5 * 0.7, 1)


def test_portion_calculator_without_unit_refuses_units(seeded):
    hc = login(seeded, COACH)
    product = _find(seeded, hc, "Pierś z kurczaka, surowa")
    r = seeded.post("/api/food-products/portion", headers=hc,
                    json={"product_id": product["id"], "units": 2})
    assert r.status_code == 422
    assert "jednostki sztukowej" in r.json()["detail"]


def test_portion_calculator_rejects_grams_and_units_together(seeded):
    hc = login(seeded, COACH)
    egg = _find(seeded, hc, "Jajo kurze całe, surowe")
    r = seeded.post("/api/food-products/portion", headers=hc,
                    json={"product_id": egg["id"], "grams": 100, "units": 2})
    assert r.status_code == 422


def test_portion_calculator_defaults_to_typical_portion(seeded):
    hc = login(seeded, COACH)
    product = _find(seeded, hc, "Pierś z kurczaka, surowa")
    body = seeded.post("/api/food-products/portion", headers=hc,
                       json={"product_id": product["id"]}).json()
    assert body["grams"] == product["default_portion_g"]


def test_client_can_calculate_portion_of_own_coach_product(seeded):
    hc = login(seeded, COACH)
    product = _find(seeded, hc, "Banan")
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/food-products/portion", headers=ha,
                    json={"product_id": product["id"], "units": 1})
    assert r.status_code == 200 and r.json()["kcal"] == 107


def test_portion_of_foreign_product_is_not_visible(seeded):
    hc = login(seeded, COACH)
    create_user_with_role("obcy.porcja@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.porcja@example.com", "password": "ObcyTrener#26"})
    foreign = seeded.post("/api/coach/food-products", headers=h2, json={
        "name": "Cudzy produkt", "kcal_100g": 100, "protein_100g": 10,
        "fat_100g": 5, "carbs_100g": 10,
    }).json()
    r = seeded.post("/api/food-products/portion", headers=hc,
                    json={"product_id": foreign["id"], "grams": 100})
    assert r.status_code == 404


# --- Nowe pola przez zwykłe API ----------------------------------------

def test_create_product_with_new_fields_and_backward_compatibility(seeded):
    hc = login(seeded, COACH)
    full = seeded.post("/api/coach/food-products", headers=hc, json={
        "name": "Produkt pełny", "category": "Inne",
        "kcal_100g": 200, "protein_100g": 10, "fat_100g": 5, "carbs_100g": 30,
        "fiber_100g": 4.5, "unit_name": "kromka", "unit_grams": 35,
        "source": "etykieta producenta", "note": "wartości dla produktu ugotowanego",
    })
    assert full.status_code == 201
    assert full.json()["fiber_100g"] == 4.5 and full.json()["unit_grams"] == 35
    # Stary kształt żądania (bez nowych pól) nadal działa — pola zostają puste.
    legacy = seeded.post("/api/coach/food-products", headers=hc, json={
        "name": "Produkt stary", "kcal_100g": 100, "protein_100g": 5,
        "fat_100g": 5, "carbs_100g": 5,
    })
    assert legacy.status_code == 201
    assert legacy.json()["fiber_100g"] is None and legacy.json()["unit_name"] is None


# --- Import / eksport CSV ----------------------------------------------

HEADER = ("nazwa,kategoria,kcal_100g,bialko_100g,tluszcz_100g,wegle_100g,"
          "blonnik_100g,porcja_g,jednostka,jednostka_g,zrodlo,uwagi\n")


def _upload(seeded, headers, content: str, filename: str = "produkty.csv"):
    return seeded.post(
        "/api/coach/food-products/import", headers=headers,
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
    )


def test_csv_import_adds_and_updates_products(seeded):
    hc = login(seeded, COACH)
    csv_text = HEADER + (
        "Sernik trenerski,Przekąski i słodycze,290,9,16,28,0.5,120,kawałek,120,"
        "własne wyliczenia,wartości dla dania gotowego\n"
        "Kisiel bez cukru,Przekąski i słodycze,35,0,0,8,,200,,,własne wyliczenia,\n"
    )
    r = _upload(seeded, hc, csv_text)
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 2 and body["updated"] == 0 and body["errors"] == []

    item = _find(seeded, hc, "Sernik trenerski")
    assert item["fiber_100g"] == 0.5 and item["unit_name"] == "kawałek"
    assert item["source"] == "własne wyliczenia"

    # Powtórny import tych samych nazw aktualizuje, nie duplikuje.
    r2 = _upload(seeded, hc, HEADER + "Sernik trenerski,Inne,300,10,17,29,,,,,,\n")
    assert r2.json() == {**r2.json(), "created": 0, "updated": 1}
    again = seeded.get(
        "/api/coach/food-products", headers=hc, params={"q": "Sernik trenerski"}
    ).json()
    assert again["total"] == 1 and again["items"][0]["kcal_100g"] == 300


def test_csv_import_reports_errors_per_row_and_continues(seeded):
    hc = login(seeded, COACH)
    csv_text = HEADER + (
        "Poprawny wiersz,Inne,120,10,3,12,,100,,,,\n"
        ",Inne,120,10,3,12,,,,,,\n"                      # brak nazwy
        "Za dużo kcal,Inne,1500,10,3,12,,,,,,\n"          # kcal poza zakresem
        "Nieliczba,Inne,abc,10,3,12,,,,,,\n"              # kcal nie jest liczbą
        "Za dużo białka,Inne,300,140,3,12,,,,,,\n"        # makro poza zakresem
        "Brak makro,Inne,300,,3,12,,,,,,\n"               # brak wymaganej wartości
        "Jednostka bez gramów,Inne,300,10,3,12,,,sztuka,,,\n"
        "Drugi poprawny,Inne,90,2,1,18,2,150,,,,\n"
    )
    r = _upload(seeded, hc, csv_text)
    assert r.status_code == 200
    body = r.json()
    # Import NIE przerywa się na pierwszym błędzie.
    assert body["created"] == 2
    assert body["skipped"] == len(body["errors"]) == 6
    rows = {e["row"] for e in body["errors"]}
    assert rows == {3, 4, 5, 6, 7, 8}
    fields = {e["row"]: e["field"] for e in body["errors"]}
    assert fields[3] == "nazwa"
    assert fields[4] == "kcal_100g" and "zakresem" in next(
        e["message"] for e in body["errors"] if e["row"] == 4
    )
    assert fields[8] == "jednostka_g"
    assert _find(seeded, hc, "Poprawny wiersz")["kcal_100g"] == 120
    assert _find(seeded, hc, "Drugi poprawny")["fiber_100g"] == 2


def test_csv_import_never_touches_another_coach_catalog(seeded):
    """Izolacja trenerów: import wiersza o nazwie identycznej z produktem
    innego trenera tworzy NOWY produkt importującego, nie nadpisuje cudzego."""
    hc = login(seeded, COACH)
    create_user_with_role("obcy.import@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.import@example.com", "password": "ObcyTrener#26"})
    foreign = seeded.post("/api/coach/food-products", headers=h2, json={
        "name": "Wspólna nazwa", "category": "Inne",
        "kcal_100g": 111, "protein_100g": 1, "fat_100g": 1, "carbs_100g": 1,
    }).json()

    r = _upload(seeded, hc, HEADER + "Wspólna nazwa,Inne,222,20,2,2,,,,,,\n")
    assert r.json()["created"] == 1 and r.json()["updated"] == 0

    mine = _find(seeded, hc, "Wspólna nazwa")
    assert mine["id"] != foreign["id"] and mine["kcal_100g"] == 222
    # Cudzy produkt bez zmian.
    still = seeded.get(
        "/api/coach/food-products", headers=h2, params={"q": "Wspólna nazwa"}
    ).json()["items"][0]
    assert still["id"] == foreign["id"] and still["kcal_100g"] == 111


def test_csv_import_survives_rows_with_extra_or_missing_columns(seeded):
    """Wiersz krótszy albo dłuższy od nagłówka nie wywraca importu."""
    hc = login(seeded, COACH)
    csv_text = HEADER + (
        "Krótki wiersz,Inne,150,12,4,10\n"                    # mniej kolumn
        "Długi wiersz,Inne,160,13,4,11,1,100,,,,,nadmiar\n"   # więcej kolumn
    )
    body = _upload(seeded, hc, csv_text).json()
    assert body["created"] == 2 and body["errors"] == []
    assert _find(seeded, hc, "Krótki wiersz")["kcal_100g"] == 150
    assert _find(seeded, hc, "Długi wiersz")["fiber_100g"] == 1


def test_csv_import_rejects_file_without_required_headers(seeded):
    hc = login(seeded, COACH)
    r = _upload(seeded, hc, "produkt;kalorie\nCoś;100\n")
    assert r.status_code == 422
    assert "Brak wymaganych kolumn" in r.json()["detail"]


def test_csv_import_accepts_semicolon_and_decimal_comma(seeded):
    """Arkusze w polskiej lokalizacji zapisują CSV średnikiem i przecinkiem
    dziesiętnym — import to rozumie."""
    hc = login(seeded, COACH)
    csv_text = (
        "nazwa;kategoria;kcal_100g;bialko_100g;tluszcz_100g;wegle_100g;blonnik_100g\n"
        "Kasza testowa;Kasze, ryż i makarony;123;3,5;0,6;25,4;2,7\n"
    )
    r = _upload(seeded, hc, csv_text)
    assert r.json()["created"] == 1
    item = _find(seeded, hc, "Kasza testowa")
    assert item["protein_100g"] == 3.5 and item["fiber_100g"] == 2.7


def test_csv_import_skips_duplicate_names_within_file(seeded):
    hc = login(seeded, COACH)
    csv_text = HEADER + (
        "Powtórka,Inne,100,10,1,10,,,,,,\n"
        "powtorka,Inne,200,20,2,20,,,,,,\n"
    )
    body = _upload(seeded, hc, csv_text).json()
    assert body["created"] == 1 and body["skipped"] == 1
    assert body["errors"][0]["field"] == "nazwa"


def test_csv_import_rejects_empty_file(seeded):
    hc = login(seeded, COACH)
    assert _upload(seeded, hc, "").status_code == 422


def test_csv_import_requires_coach_role(seeded):
    ha = login(seeded, CLIENT_A)
    assert _upload(seeded, ha, HEADER).status_code == 403


def test_csv_export_round_trips_catalog(seeded):
    hc = login(seeded, COACH)
    r = seeded.get("/api/coach/food-products/export", headers=hc)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "dzik-os-produkty.csv" in r.headers["content-disposition"]
    text = r.content.decode("utf-8-sig")
    lines = text.strip().splitlines()
    assert lines[0].startswith("nazwa,kategoria,kcal_100g")
    assert len(lines) - 1 >= 300
    assert any(line.startswith("Banan,") for line in lines)

    # Eksport innego trenera zawiera wyłącznie jego produkty (prawo wyjścia
    # nie może stać się wyciekiem cudzego katalogu).
    create_user_with_role("obcy.eksport@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.eksport@example.com", "password": "ObcyTrener#26"})
    other = seeded.get("/api/coach/food-products/export", headers=h2)
    assert len(other.content.decode("utf-8-sig").strip().splitlines()) == 1


def test_csv_export_then_import_is_idempotent(seeded):
    """Eksport → import do własnego katalogu niczego nie dubluje: pełny
    obieg „zabierz swoje dane i wróć z nimi”."""
    hc = login(seeded, COACH)
    exported = seeded.get("/api/coach/food-products/export", headers=hc)
    text = exported.content.decode("utf-8-sig")
    before = seeded.get("/api/coach/food-products", headers=hc).json()["total"]
    body = _upload(seeded, hc, text).json()
    assert body["created"] == 0 and body["errors"] == []
    assert body["updated"] == before
    after = seeded.get("/api/coach/food-products", headers=hc).json()["total"]
    assert after == before


def test_csv_export_requires_coach_role(seeded):
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/coach/food-products/export", headers=ha).status_code == 403


# --- Walidacja zakresów w zwykłym API ----------------------------------

def test_api_rejects_values_out_of_range(seeded):
    hc = login(seeded, COACH)
    base = {"name": "Poza zakresem", "kcal_100g": 100, "protein_100g": 10,
            "fat_100g": 5, "carbs_100g": 10}
    assert seeded.post("/api/coach/food-products", headers=hc,
                       json={**base, "kcal_100g": 5000}).status_code == 422
    assert seeded.post("/api/coach/food-products", headers=hc,
                       json={**base, "fiber_100g": 500}).status_code == 422
    assert seeded.post("/api/coach/food-products", headers=hc,
                       json={**base, "unit_grams": 0}).status_code == 422
    assert seeded.post("/api/coach/food-products", headers=hc,
                       json={**base, "protein_100g": -1}).status_code == 422

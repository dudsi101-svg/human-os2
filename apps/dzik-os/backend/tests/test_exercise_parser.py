"""Auto-uzupełnianie tabeli parametrów ćwiczenia z wklejonego opisu.

Kontrakt, którego pilnują te testy:

* silnik lokalny działa ZAWSZE, bez klucza i bez internetu;
* pole nierozpoznane zostaje PUSTE i jest wypisane wprost — nigdy
  zgadywane;
* wynik jest wyłącznie propozycją: endpoint nie zapisuje ani jednego
  ćwiczenia;
* tryb rozszerzony musi przejść ścisłą walidację — wartość spoza słownika
  odrzuca całą odpowiedź i schodzimy na silnik lokalny;
* ani jeden znak wklejonego opisu nie trafia do logów i metryk.
"""

from __future__ import annotations

import json

import pytest
from conftest import CLIENT_A, COACH, login

from dzik_os import ai_provider, exercise_parser, exercise_parser_ai

# --- Realistyczne opisy po polsku ------------------------------------------

OPIS_Z_SEKCJAMI = """Przysiad ze sztangą z tyłu

Mięśnie: pracują głównie czworogłowy uda i pośladki, wspomagająco
prostowniki grzbietu oraz mięśnie głębokie (core).

Sprzęt: sztanga, stojaki
Poziom: średniozaawansowany
Wzorzec ruchu: przysiad

Wykonanie:
1. Ustaw sztangę na górnej części pleców i zejdź ze stojaków.
2. Rozstaw stopy na szerokość barków, palce lekko na zewnątrz.
3. Zejdź w dół, prowadząc kolana zgodnie z ustawieniem stóp.
4. Wróć do pozycji wyjściowej, wypychając podłogę.

Najczęstsze błędy:
- kolana uciekające do środka
- zaokrąglone plecy w dolnej fazie

Wskazówki:
- odepchnij podłogę
- klatka wysoko

Tempo: 3010
Oddech: wdech przed zejściem, wydech przy wypchnięciu.
Bezpieczeństwo: ustaw asekurację na stojakach; przy bólu kolana skonsultuj
się ze specjalistą.
Wariant łatwiejszy: przysiad goblet z hantlem.
Wariant trudniejszy: przysiad przedni ze sztangą.
Efekt: siła i masa dolnej części ciała.
"""

OPIS_CIAGLY = (
    "Martwy ciąg klasyczny to ćwiczenie siłowe wykonywane ze sztangą. "
    "Angażuje przede wszystkim pośladki, dwugłowy uda i prostowniki grzbietu, "
    "a dodatkowo pracują przedramiona i czworoboczny. "
    "Ćwiczenie jest zaawansowane technicznie."
)

OPIS_BEZ_MARKERA = """Wiosłowanie hantlem w opadzie

Mięśnie: najszerszy grzbietu, romboidalne, biceps
Sprzęt: hantle, ławka
"""

# Ten sam opis co wyżej, ale zapisany BEZ polskich znaków i wielkimi
# literami — parser ma to czytać identycznie (muscles.fold).
OPIS_BEZ_OGONKOW = """WIOSLOWANIE HANTLEM W OPADZIE

MIESNIE: NAJSZERSZY GRZBIETU, ROMBOIDALNE, BICEPS
SPRZET: HANTLE, LAWKA
"""

# Same znaki interpunkcyjne i liczby — ani jednego pola do odczytania.
OPIS_BEZ_SENSU = "#### 12345 ????\n%%% 987 %%%\n>>> 42 <<<"


def _parse(client, headers, text: str) -> dict:
    r = client.post(
        "/api/coach/exercises/parse-description", headers=headers,
        json={"description": text},
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Silnik lokalny — czysta funkcja.
# ---------------------------------------------------------------------------


def test_opis_z_sekcjami_wypelnia_cala_tabele():
    result = exercise_parser.parse_description(OPIS_Z_SEKCJAMI)
    proposal = result.proposal

    assert proposal["name"] == "Przysiad ze sztangą z tyłu"
    assert proposal["muscles_primary"] == ["CZWOROGLOWY_UDA", "POSLADKI"]
    assert proposal["muscles_secondary"] == ["PROSTOWNIKI_GRZBIETU", "MIESNIE_GLEBOKIE"]
    assert proposal["level"] == "SREDNIOZAAWANSOWANY"
    assert proposal["pattern"] == "PRZYSIAD"
    assert "sztanga" in proposal["equipment"]
    assert len(proposal["steps"]) == 4
    assert proposal["steps"][0].startswith("Ustaw sztangę")
    assert proposal["mistakes"] == [
        "kolana uciekające do środka", "zaokrąglone plecy w dolnej fazie",
    ]
    assert proposal["cues"] == ["odepchnij podłogę", "klatka wysoko"]
    assert proposal["tempo_hint"] == "3010"
    assert "wdech" in proposal["breathing"]
    assert "asekurację" in proposal["safety"]
    assert "goblet" in proposal["easier"]
    assert "przedni" in proposal["harder"]
    assert "siła" in proposal["benefit"]
    # Komplet pól odczytany; podział mięśni miał marker, więc jedyne, co
    # zostaje do potwierdzenia, to nazwa wzięta z pierwszej linii.
    assert result.unrecognized == []
    assert result.needs_confirmation == ["name"]


def test_marker_dzieli_miesnie_na_glowne_i_pomocnicze():
    primary, secondary, marked = exercise_parser.split_muscles_by_markers(
        "Pracują głównie pośladki i dwugłowy uda, wspomagająco prostowniki "
        "grzbietu oraz core."
    )
    assert primary == ["POSLADKI", "DWUGLOWY_UDA"]
    assert secondary == ["PROSTOWNIKI_GRZBIETU", "MIESNIE_GLEBOKIE"]
    assert marked is True


def test_bez_markera_wszystko_trafia_do_glownych_i_wymaga_potwierdzenia():
    result = exercise_parser.parse_description(OPIS_BEZ_MARKERA)
    assert result.proposal["muscles_primary"] == [
        "NAJSZERSZY_GRZBIETU", "ROMBOIDALNE", "BICEPS",
    ]
    assert result.proposal["muscles_secondary"] == []
    assert "muscles_primary" in result.needs_confirmation
    assert "muscles_secondary" in result.needs_confirmation
    # Pole niepewne nie jest jednocześnie „nieodczytane” — dwie listy są
    # rozłączne, żeby człowiek nie musiał ich godzić.
    assert "muscles_secondary" not in result.unrecognized


def test_polskie_znaki_i_wielkosc_liter_nie_maja_znaczenia():
    z_ogonkami = exercise_parser.parse_description(OPIS_BEZ_MARKERA)
    bez_ogonkow = exercise_parser.parse_description(OPIS_BEZ_OGONKOW)
    assert bez_ogonkow.proposal["muscles_primary"] == z_ogonkami.proposal["muscles_primary"]
    assert bez_ogonkow.proposal["equipment"] == z_ogonkami.proposal["equipment"]


@pytest.mark.parametrize(
    ("fragment", "oczekiwany"),
    [
        ("Pracuje czworogłowy uda", "CZWOROGLOWY_UDA"),
        ("Pracują quadriceps", "CZWOROGLOWY_UDA"),
        ("Angażuje przód uda", "CZWOROGLOWY_UDA"),
        ("Pracują pośladki", "POSLADKI"),
        ("Pracuje gluteus maximus", "POSLADKI"),
        ("Pracuje najszerszy grzbietu", "NAJSZERSZY_GRZBIETU"),
        ("Pracuje latissimus", "NAJSZERSZY_GRZBIETU"),
        ("Pracują plecy", "NAJSZERSZY_GRZBIETU"),
        ("Pracuje core", "MIESNIE_GLEBOKIE"),
        ("Pracują mięśnie głębokie", "MIESNIE_GLEBOKIE"),
        ("Wymaga stabilizacji tułowia", "MIESNIE_GLEBOKIE"),
        ("Pracuje biceps uda", "DWUGLOWY_UDA"),
        ("Pracuje biceps", "BICEPS"),
        ("Pracuje trójgłowy łydki", "LYDKA"),
    ],
)
def test_synonimy_miesni(fragment: str, oczekiwany: str):
    primary, _, _ = exercise_parser.split_muscles_by_markers(fragment)
    assert primary == [oczekiwany]


def test_nieznana_partia_miesniowa_jest_ignorowana():
    """Nazwa spoza słownika NIE trafia do wyniku i nie jest mapowana na
    „najbliższy” klucz — lepiej pusto niż nie ta partia."""
    primary, secondary, _ = exercise_parser.split_muscles_by_markers(
        "Pracuje mięsień pupopodobny i czworogłowy uda"
    )
    assert primary == ["CZWOROGLOWY_UDA"]
    assert secondary == []


def test_tekst_ciagly_daje_mniej_pol_ale_bez_zgadywania():
    """Znane ograniczenie trybu lokalnego: bez nagłówków sekcji czytamy
    mięśnie, poziom, wzorzec i sprzęt, a reszta zostaje pusta i wypisana."""
    result = exercise_parser.parse_description(OPIS_CIAGLY)
    assert result.proposal["muscles_primary"] == [
        "POSLADKI", "DWUGLOWY_UDA", "PROSTOWNIKI_GRZBIETU",
    ]
    assert result.proposal["muscles_secondary"] == ["PRZEDRAMIE", "CZWOROBOCZNY"]
    assert result.proposal["pattern"] == "ZAWIAS_BIODROWY"
    assert result.proposal["level"] == "ZAAWANSOWANY"
    assert result.proposal["steps"] == []
    for key in ("steps", "mistakes", "cues", "safety", "tempo_hint", "benefit"):
        assert result.proposal[key] in (None, [])
        assert key in result.unrecognized


def test_tekst_bez_sensu_daje_pusta_propozycje_bez_bledu():
    result = exercise_parser.parse_description(OPIS_BEZ_SENSU)
    assert result.proposal == exercise_parser.empty_proposal()
    assert set(result.unrecognized) == set(exercise_parser.FIELD_ORDER)
    assert result.needs_confirmation == []


def test_pusty_tekst_nie_wywraca_parsera():
    result = exercise_parser.parse_description("")
    assert result.proposal == exercise_parser.empty_proposal()


def test_slowniki_nie_wskazuja_wartosci_spoza_kontraktu():
    """Literówka w kluczu nowego synonimu ma się wysypać od razu."""
    exercise_parser._assert_dictionaries()


def test_rok_w_notatce_nie_jest_tempem():
    result = exercise_parser.parse_description(
        "Przysiad goblet\nĆwiczenie z katalogu 2026 roku."
    )
    assert result.proposal["tempo_hint"] is None


def test_clamp_odrzuca_wartosci_spoza_slownikow():
    out = exercise_parser.clamp_proposal({
        "name": "  Przysiad  ",
        "muscles_primary": ["POSLADKI", "MIESIEN_WYMYSLONY", "POSLADKI"],
        "muscles_secondary": ["POSLADKI", "LYDKA"],
        "level": "MISTRZOWSKI",
        "pattern": "SALTO",
        "steps": ["", "  Zejdź w dół  "],
    })
    assert out["muscles_primary"] == ["POSLADKI"]
    # Ten sam mięsień nie może być główny i pomocniczy naraz.
    assert out["muscles_secondary"] == ["LYDKA"]
    assert out["level"] is None
    assert out["pattern"] is None
    assert out["name"] == "Przysiad"
    assert out["steps"] == ["Zejdź w dół"]


# ---------------------------------------------------------------------------
# Endpoint: rola, brak zapisu, kształt propozycji.
# ---------------------------------------------------------------------------


def test_endpoint_zwraca_propozycje_i_uzyty_tryb(seeded):
    headers = login(seeded, COACH)
    data = _parse(seeded, headers, OPIS_Z_SEKCJAMI)
    assert data["engine"] == "LOCAL"
    assert data["mode_reason"]  # zawsze wiadomo, dlaczego taki tryb
    assert data["proposal"]["name"] == "Przysiad ze sztangą z tyłu"
    assert data["unrecognized"] == []
    assert data["needs_confirmation"] == ["name"]
    assert set(data["field_labels"]) == set(exercise_parser.FIELD_ORDER)


def test_klient_nie_ma_dostepu_do_czytania_opisu(seeded):
    headers = login(seeded, CLIENT_A)
    r = seeded.post(
        "/api/coach/exercises/parse-description", headers=headers,
        json={"description": OPIS_Z_SEKCJAMI},
    )
    assert r.status_code == 403


def test_endpoint_niczego_nie_zapisuje(seeded):
    headers = login(seeded, COACH)
    before = seeded.get("/api/coach/exercises?limit=1", headers=headers).json()["total"]
    _parse(seeded, headers, OPIS_Z_SEKCJAMI)
    _parse(seeded, headers, OPIS_CIAGLY)
    after = seeded.get("/api/coach/exercises?limit=1", headers=headers).json()["total"]
    assert after == before


def test_za_dlugi_opis_jest_odrzucany_a_nie_przycinany(seeded):
    headers = login(seeded, COACH)
    r = seeded.post(
        "/api/coach/exercises/parse-description", headers=headers,
        json={"description": "a" * (exercise_parser.MAX_INPUT_CHARS + 1)},
    )
    assert r.status_code == 422


def test_brak_tresci_opisu_w_logach_i_metrykach(seeded, capsys, monkeypatch):
    """Wklejony opis to know-how trenera — nie ma prawa wyciec do logów ani
    do liczników. Sprawdzamy oba tryby (lokalny i odrzuconą odpowiedź
    modelu, która też coś loguje)."""
    headers = login(seeded, COACH)
    sekret = "Autorska metoda Dzika na przysiad ze sztangą"
    _parse(seeded, headers, f"{sekret}\nMięśnie: pośladki")

    provider = StubTextProvider(["{\"name\": \"" + sekret + "\", \"nieznane\": 1}"] * 2)
    monkeypatch.setattr(ai_provider, "provider", provider)
    _parse(seeded, headers, f"{sekret}\nMięśnie: pośladki")

    logs = capsys.readouterr().out
    assert sekret not in logs
    assert "przysiad ze sztangą" not in logs.lower()
    metryki = seeded.get("/api/metrics", headers=login(seeded, COACH)).text
    assert sekret not in metryki


# ---------------------------------------------------------------------------
# Tryb rozszerzony na atrapie dostawcy.
# ---------------------------------------------------------------------------


class StubTextProvider:
    """Atrapa dostawcy modelu: kolejne wywołania dostają kolejne pozycje.

    Element to surowa odpowiedź modelu albo ``None`` (brak odpowiedzi)."""

    name = "stub-text"
    enabled = True

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls = 0
        self.last_kwargs: dict | None = None

    def summarize_checkin(self, *, payload, history_note):
        return None

    def propose_json(self, *, system_prompt, data_section, schema_hint, timeout_s):
        self.calls += 1
        self.last_kwargs = {
            "system_prompt": system_prompt, "data_section": data_section,
            "schema_hint": schema_hint, "timeout_s": timeout_s,
        }
        if not self.responses:
            return None
        item = self.responses.pop(0)
        if item is None:
            return None
        return ai_provider.AIJsonResponse(text=item, tokens_in=120, tokens_out=60)

    def propose_json_from_image(self, *, system_prompt, image, media_type,
                                task_hint, schema_hint, timeout_s):
        return None


POPRAWNA_ODPOWIEDZ = json.dumps({
    "name": "Wiosłowanie hantlem w opadzie",
    "muscles_primary": ["NAJSZERSZY_GRZBIETU", "ROMBOIDALNE"],
    "muscles_secondary": ["BICEPS"],
    "level": "SREDNIOZAAWANSOWANY",
    "pattern": "PRZYCIAGANIE_POZIOME",
    "equipment": "hantle, ławka",
    "steps": ["Oprzyj kolano i dłoń o ławkę.", "Przyciągnij hantel do biodra."],
    "mistakes": ["rotacja tułowia"],
    "cues": ["łokieć wzdłuż tułowia"],
    "safety": None, "easier": None, "harder": None,
    "tempo_hint": None, "breathing": None, "benefit": None,
}, ensure_ascii=False)


def test_tryb_rozszerzony_uzupelnia_dokladniej(seeded, monkeypatch):
    provider = StubTextProvider([POPRAWNA_ODPOWIEDZ])
    monkeypatch.setattr(ai_provider, "provider", provider)
    headers = login(seeded, COACH)

    data = _parse(seeded, headers, OPIS_CIAGLY)
    assert data["engine"] == "EXTENDED"
    assert data["proposal"]["muscles_primary"] == ["NAJSZERSZY_GRZBIETU", "ROMBOIDALNE"]
    assert data["proposal"]["muscles_secondary"] == ["BICEPS"]
    assert provider.calls == 1
    # Minimalizacja: do dostawcy jedzie WYŁĄCZNIE tekst opisu.
    wyslane = json.dumps(provider.last_kwargs, ensure_ascii=False)
    assert "@" not in wyslane
    assert "USR" not in wyslane


def test_wartosc_spoza_slownika_odrzuca_odpowiedz_i_schodzi_na_lokalny(
    seeded, monkeypatch
):
    zmyslona = json.dumps({
        "name": "Wiosłowanie",
        "muscles_primary": ["MIESIEN_WYMYSLONY_PRZEZ_MODEL"],
        "muscles_secondary": [], "level": None, "pattern": None,
        "equipment": None, "steps": [], "mistakes": [], "cues": [],
        "safety": None, "easier": None, "harder": None,
        "tempo_hint": None, "breathing": None, "benefit": None,
    }, ensure_ascii=False)
    provider = StubTextProvider([zmyslona, zmyslona])
    monkeypatch.setattr(ai_provider, "provider", provider)
    headers = login(seeded, COACH)

    data = _parse(seeded, headers, OPIS_BEZ_MARKERA)
    assert data["engine"] == "LOCAL"
    assert provider.calls == 2  # próba + jedno ponowienie
    assert "odrzucona" in data["mode_reason"]
    # Wynik pochodzi z silnika lokalnego, a wymyślony klucz nigdzie nie ma
    # jak wejść.
    assert data["proposal"]["muscles_primary"] == [
        "NAJSZERSZY_GRZBIETU", "ROMBOIDALNE", "BICEPS",
    ]


def test_brak_odpowiedzi_dostawcy_konczy_sie_trybem_lokalnym(seeded, monkeypatch):
    provider = StubTextProvider([None, None])
    monkeypatch.setattr(ai_provider, "provider", provider)
    headers = login(seeded, COACH)

    data = _parse(seeded, headers, OPIS_BEZ_MARKERA)
    assert data["engine"] == "LOCAL"
    assert provider.calls == 2
    assert data["proposal"]["muscles_primary"][0] == "NAJSZERSZY_GRZBIETU"


def test_walidacja_odpowiedzi_modelu_odrzuca_nadmiarowe_pola():
    with pytest.raises(exercise_parser_ai.RejectedDraft):
        exercise_parser_ai.parse_draft('{"name": "X", "diagnoza": "cukrzyca"}')
    with pytest.raises(exercise_parser_ai.RejectedDraft):
        exercise_parser_ai.parse_draft("oto wynik: {\"name\": \"X\"}")
    with pytest.raises(exercise_parser_ai.RejectedDraft):
        exercise_parser_ai.parse_draft('{"level": "MISTRZOWSKI"}')
    with pytest.raises(exercise_parser_ai.RejectedDraft):
        exercise_parser_ai.parse_draft('{"pattern": "SALTO"}')
    assert exercise_parser_ai.parse_draft('{"name": "X"}').name == "X"


def test_bez_dostawcy_tryb_lokalny_dziala_zawsze(seeded):
    """Domyślny NullAIProvider: żadnego wyjątku, jawny powód, pełna
    propozycja z silnika lokalnego."""
    headers = login(seeded, COACH)
    data = _parse(seeded, headers, OPIS_Z_SEKCJAMI)
    assert data["engine"] == "LOCAL"
    assert data["proposal"]["steps"]


# ---------------------------------------------------------------------------
# Proweniencja (migracja nr 22).
# ---------------------------------------------------------------------------


def test_proweniencja_zapisywana_przy_tworzeniu_cwiczenia(seeded):
    headers = login(seeded, COACH)
    body = {
        "name": "Przysiad z opisu", "muscle_group": "NOGI",
        "how_to": "Zejdź i wróć.", "muscles_primary": ["CZWOROGLOWY_UDA"],
        "muscles_secondary": [], "steps": [], "mistakes": [], "cues": [],
        "source_kind": "TEXT_PARSED", "source_engine": "LOCAL",
    }
    created = seeded.post("/api/coach/exercises", headers=headers, json=body)
    assert created.status_code == 201, created.text
    assert created.json()["source_kind"] == "TEXT_PARSED"
    assert created.json()["source_engine"] == "LOCAL"

    detail = seeded.get(
        f"/api/coach/exercises/{created.json()['id']}", headers=headers
    ).json()
    assert detail["source_kind"] == "TEXT_PARSED"


def test_cwiczenie_bez_proweniencji_zapisuje_sie_jak_dotad(seeded):
    """NULL znaczy „nie wiemy” — nie podstawiamy MANUAL za nikogo."""
    headers = login(seeded, COACH)
    created = seeded.post("/api/coach/exercises", headers=headers, json={
        "name": "Ćwiczenie bez proweniencji", "muscle_group": "INNE",
        "how_to": "Opis.",
    })
    assert created.status_code == 201, created.text
    assert created.json()["source_kind"] is None
    assert created.json()["source_engine"] is None


@pytest.mark.parametrize(
    "body_extra",
    [
        {"source_kind": "SKADS"},
        {"source_engine": "GPU"},
        {"source_engine": "LOCAL"},                      # silnik bez źródła
        {"source_kind": "MANUAL", "source_engine": "LOCAL"},
    ],
)
def test_niespojna_proweniencja_jest_odrzucana(seeded, body_extra: dict):
    headers = login(seeded, COACH)
    r = seeded.post("/api/coach/exercises", headers=headers, json={
        "name": "X", "muscle_group": "INNE", "how_to": "Opis.", **body_extra,
    })
    assert r.status_code == 422


def test_migracja_22_dodaje_nullable_kolumny_do_starej_bazy(tmp_path):
    """Stara baza z tabelą `exercises` bez kolumn proweniencji dostaje je
    migracją nr 22; obie są NULLable, istniejący wiersz przeżywa bez
    backfillu."""
    from sqlalchemy import create_engine, text

    from dzik_os.db import run_migrations

    eng = create_engine(f"sqlite:///{tmp_path}/stara.db")
    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, "
            "description TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        for version in range(1, 22):
            conn.execute(text("INSERT INTO schema_migrations(version, description) "
                              "VALUES (:v, 'stub')"), {"v": version})
        conn.execute(text(
            "CREATE TABLE exercises (id VARCHAR(40) PRIMARY KEY, "
            "coach_id VARCHAR(40), name VARCHAR(300), muscle_group VARCHAR(30), "
            "how_to TEXT, status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', "
            "created_by VARCHAR(40), created_at VARCHAR(40), updated_at VARCHAR(40))"))
        conn.execute(text(
            "INSERT INTO exercises(id, coach_id, name, muscle_group, how_to, status, "
            "created_by, created_at, updated_at) VALUES "
            "('EXC-1', 'C1', 'Stare ćwiczenie', 'NOGI', 'Opis', 'ACTIVE', 'C1', 'x', 'x')"))
        # Stub dla migracji nr 26 (kolumna `flow` w sesjach rozmów) —
        # realna stara baza ma tę tabelę z migracji 17; tu migracje są
        # tylko ostemplowane, więc tabela musi powstać ręcznie.
        conn.execute(text(
            "CREATE TABLE onboarding_sessions (id VARCHAR(40) PRIMARY KEY, "
            "client_id VARCHAR(40))"))

    applied = run_migrations(eng)
    assert 22 in applied
    with eng.connect() as conn:
        cols = {r[1]: r[3] for r in conn.exec_driver_sql("PRAGMA table_info(exercises)")}
        row = conn.exec_driver_sql(
            "SELECT name, source_kind, source_engine FROM exercises"
        ).fetchone()
    for col in ("source_kind", "source_engine"):
        assert col in cols, col
        assert cols[col] == 0, f"{col} musi być NULLable"
    assert row[0] == "Stare ćwiczenie"
    assert row[1] is None and row[2] is None

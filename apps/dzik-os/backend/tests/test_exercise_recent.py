"""Skrót „ostatnio używane ćwiczenia" w wyszukiwarce edytora planu.

Przy katalogu rzędu 250 pozycji trener i tak korzysta z kilkudziesięciu
ćwiczeń — skrót ma to wykorzystać. Testy pilnują trzech rzeczy naraz:
kolejność (najświeższe wersje planów pierwsze), granicę widoczności
(wyłącznie własne, aktywne ćwiczenia) i prywatność (skrót to własny
katalog trenera, a nie zestawienie „co u którego klienta").
"""

from __future__ import annotations

from conftest import ADMIN, CLIENT_A, COACH, create_user_with_role, get_user_id, login

RECENT_URL = "/api/coach/exercises/recent"


def add_exercise(client, headers, name: str) -> str:
    r = client.post("/api/coach/exercises", headers=headers, json={
        "name": name, "muscle_group": "NOGI", "how_to": "Opis techniki.",
        "equipment": "Sztanga", "level": "POCZATKUJACY", "pattern": "PRZYSIAD",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def save_plan(client, headers, client_id: str, exercise_ids: list[str], title: str) -> str:
    r = client.post("/api/plans", headers=headers, json={
        "client_id": client_id, "title": title,
        "version": {
            "reason": "start",
            "days": [{
                "name": "Dzień A", "weekday": 1,
                "exercises": [{"name": f"poz. {i}", "exercise_id": eid}
                              for i, eid in enumerate(exercise_ids)],
            }],
        },
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_brak_planow_to_pusta_lista(seeded):
    """Trener bez ani jednego planu nie dostaje pustej ramki — dostaje
    pustą listę, a interfejs po prostu nie pokazuje sekcji."""
    create_user_with_role("swiezy.trener@example.com", "SwiezyTrener#2026",
                          "Świeży Trener", "COACH")
    headers = login(seeded, {"email": "swiezy.trener@example.com",
                             "password": "SwiezyTrener#2026"})
    r = seeded.get(RECENT_URL, headers=headers)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_kolejnosc_od_najswiezszych_wersji(seeded):
    coach = login(seeded, COACH)
    client_a = get_user_id(seeded, login(seeded, CLIENT_A))
    stare = add_exercise(seeded, coach, "Stare ćwiczenie")
    nowe = add_exercise(seeded, coach, "Nowe ćwiczenie")
    plan_id = save_plan(seeded, coach, client_a, [stare], "Plan 1")
    r = seeded.post(f"/api/plans/{plan_id}/versions", headers=coach, json={
        "reason": "progresja",
        "days": [{"name": "Dzień A", "weekday": 1,
                  "exercises": [{"name": "poz.", "exercise_id": nowe}]}],
    })
    assert r.status_code == 201, r.text
    items = seeded.get(RECENT_URL, headers=coach).json()["items"]
    ids = [i["id"] for i in items]
    # Ćwiczenie z NAJŚWIEŻSZEJ wersji stoi przed starszym.
    assert ids.index(nowe) < ids.index(stare)


def test_maksymalnie_dwanascie_pozycji(seeded):
    coach = login(seeded, COACH)
    client_a = get_user_id(seeded, login(seeded, CLIENT_A))
    ids = [add_exercise(seeded, coach, f"Ćwiczenie {n}") for n in range(15)]
    save_plan(seeded, coach, client_a, ids, "Plan duży")
    items = seeded.get(RECENT_URL, headers=coach).json()["items"]
    assert len(items) == 12
    # Skrót nie duplikuje pozycji.
    assert len({i["id"] for i in items}) == 12


def test_zarchiwizowane_cwiczenie_wypada_ze_skrotu(seeded):
    coach = login(seeded, COACH)
    client_a = get_user_id(seeded, login(seeded, CLIENT_A))
    aktywne = add_exercise(seeded, coach, "Aktywne ćwiczenie")
    do_archiwum = add_exercise(seeded, coach, "Wycofane ćwiczenie")
    save_plan(seeded, coach, client_a, [aktywne, do_archiwum], "Plan")
    seeded.post(f"/api/coach/exercises/{do_archiwum}/status?status=ARCHIVED",
                headers=coach)
    ids = [i["id"] for i in seeded.get(RECENT_URL, headers=coach).json()["items"]]
    assert aktywne in ids
    assert do_archiwum not in ids


def test_skrot_pokazuje_wylacznie_wlasne_cwiczenia(seeded):
    """Drugi trener ma własne plany i własną bazę — skrót nigdy nie miesza
    katalogów dwóch trenerów."""
    coach = login(seeded, COACH)
    client_a = get_user_id(seeded, login(seeded, CLIENT_A))
    moje = add_exercise(seeded, coach, "Moje ćwiczenie")
    save_plan(seeded, coach, client_a, [moje], "Plan trenera A")

    create_user_with_role("drugi.trener@example.com", "DrugiTrener#2026",
                          "Drugi Trener", "COACH")
    other = login(seeded, {"email": "drugi.trener@example.com",
                           "password": "DrugiTrener#2026"})
    obce = add_exercise(seeded, other, "Cudze ćwiczenie")
    # Szablon (plan bez klienta) drugiego trenera z jego własnym ćwiczeniem.
    r = seeded.post("/api/plans", headers=other, json={
        "client_id": None, "title": "Szablon B",
        "version": {"reason": "start", "days": [
            {"name": "Dzień", "weekday": None,
             "exercises": [{"name": "poz.", "exercise_id": obce}]}]},
    })
    assert r.status_code == 201, r.text

    moje_ids = [i["id"] for i in seeded.get(RECENT_URL, headers=coach).json()["items"]]
    obce_ids = [i["id"] for i in seeded.get(RECENT_URL, headers=other).json()["items"]]
    assert moje in moje_ids and obce not in moje_ids
    assert obce in obce_ids and moje not in obce_ids


def test_skrot_nie_ujawnia_danych_klienta(seeded):
    """Skrót to własny katalog trenera: ani identyfikatora klienta, ani
    jego imienia, ani informacji „użyte u X" tu nie ma."""
    coach = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_a = get_user_id(seeded, ha)
    name = seeded.get("/api/auth/me", headers=ha).json()["display_name"]
    eid = add_exercise(seeded, coach, "Przysiad kontrolny")
    save_plan(seeded, coach, client_a, [eid], "Plan klienta")
    body = seeded.get(RECENT_URL, headers=coach).text
    assert client_a not in body
    assert name not in body
    assert "client" not in body.lower()


def test_klient_i_admin_dostaja_403(seeded):
    for creds in (CLIENT_A, ADMIN):
        assert seeded.get(RECENT_URL, headers=login(seeded, creds)).status_code == 403


def test_sciezka_recent_nie_koliduje_z_kartą_cwiczenia(seeded):
    """„recent" nie może zostać wzięte za identyfikator ćwiczenia."""
    coach = login(seeded, COACH)
    eid = add_exercise(seeded, coach, "Ćwiczenie karty")
    assert seeded.get(f"/api/coach/exercises/{eid}", headers=coach).status_code == 200
    assert "items" in seeded.get(RECENT_URL, headers=coach).json()

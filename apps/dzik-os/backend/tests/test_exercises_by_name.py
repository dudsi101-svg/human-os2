"""Dopasowanie pozycji planu do bazy ćwiczeń po nazwie (0.75.0).

Pozycja planu bez `exercise_id` ma tylko nazwę; klient i trener pytają
`GET …/exercises/by-name?name=` o kartę. Zbiór jest ten sam co listy
(`/api/me/exercises`, `/api/coach/exercises`), a brak dopasowania, brak
relacji i cudze ćwiczenie to jedno 404 — nic nie ujawnia, czy nazwa
istnieje u kogoś innego. Trasa stała przed `/{item_id}` — test pilnuje,
żeby jej nie przesłonięto."""

from conftest import CLIENT_A, COACH, create_user_with_role, login

OBCY_TRENER = {"email": "obcy.trener3@example.com", "password": "ObcyTrener#26x"}
OBCY_KLIENT = {"email": "obcy.klient3@example.com", "password": "ObcyKlient#26x"}


def test_klient_trafia_po_nazwie_bez_wielkosci_liter_i_diakrytykow(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/me/exercises/by-name", headers=ha,
                   params={"name": "  wyciskanie  SZTANGI lezac "})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Wyciskanie sztangi leżąc"
    assert body["steps"] and body["mistakes"]
    # Notatka robocza trenera nie wychodzi na widok klienta (jak `/me/exercises/{id}`).
    assert "review_reason" not in body


def test_klient_bez_dopasowania_pusta_nazwa_i_bez_relacji(seeded):
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/me/exercises/by-name", headers=ha,
                      params={"name": "Ćwiczenie, którego nie ma"}).status_code == 404
    assert seeded.get("/api/me/exercises/by-name", headers=ha,
                      params={"name": "   "}).status_code == 422
    assert seeded.get("/api/me/exercises/by-name", headers=ha).status_code == 422
    # Klient bez aktywnej relacji: ta sama nazwa, to samo 404.
    create_user_with_role(OBCY_KLIENT["email"], OBCY_KLIENT["password"], "Obcy Klient", "CLIENT")
    ho = login(seeded, OBCY_KLIENT)
    assert seeded.get("/api/me/exercises/by-name", headers=ho,
                      params={"name": "Wyciskanie sztangi leżąc"}).status_code == 404


def test_zarchiwizowane_znika_z_dopasowania(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    item = seeded.get("/api/me/exercises/by-name", headers=ha,
                      params={"name": "Przysiad ze sztangą"}).json()
    r = seeded.post(f"/api/coach/exercises/{item['id']}/status?status=ARCHIVED", headers=hc)
    assert r.status_code == 200
    assert seeded.get("/api/me/exercises/by-name", headers=ha,
                      params={"name": "Przysiad ze sztangą"}).status_code == 404


def test_trener_wlasne_po_nazwie_a_cudze_404(seeded):
    hc = login(seeded, COACH)
    r = seeded.get("/api/coach/exercises/by-name", headers=hc,
                   params={"name": "przysiad ze sztanga"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Przysiad ze sztangą"
    assert "review_reason" in r.json()
    assert seeded.get("/api/coach/exercises/by-name", headers=hc,
                      params={"name": "Nie ma takiego"}).status_code == 404
    assert seeded.get("/api/coach/exercises/by-name", headers=hc,
                      params={"name": ""}).status_code == 422
    create_user_with_role(OBCY_TRENER["email"], OBCY_TRENER["password"], "Obcy Trener", "COACH")
    hf = login(seeded, OBCY_TRENER)
    assert seeded.get("/api/coach/exercises/by-name", headers=hf,
                      params={"name": "Przysiad ze sztangą"}).status_code == 404
    # Klient nie ma wstępu na trasę trenera.
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/coach/exercises/by-name", headers=ha,
                      params={"name": "Przysiad ze sztangą"}).status_code == 403


def test_dopasowanie_jest_deterministyczne_przy_duplikacie(seeded):
    """Dwa wpisy o tej samej znormalizowanej nazwie → zawsze najstarszy."""
    hc = login(seeded, COACH)
    pierwszy = seeded.get("/api/coach/exercises/by-name", headers=hc,
                          params={"name": "Przysiad ze sztangą"}).json()["id"]
    r = seeded.post("/api/coach/exercises", headers=hc, json={
        "name": "PRZYSIAD ZE SZTANGA", "muscle_group": "NOGI", "how_to": "duplikat",
    })
    assert r.status_code == 201
    for _ in range(3):
        znow = seeded.get("/api/coach/exercises/by-name", headers=hc,
                          params={"name": "przysiad ze sztangą"}).json()["id"]
        assert znow == pierwszy
    ha = login(seeded, CLIENT_A)
    assert seeded.get("/api/me/exercises/by-name", headers=ha,
                      params={"name": "Przysiad ze sztangą"}).json()["id"] == pierwszy

"""Szablony diety trenera (0.54.0): katalog wbudowany, własne szablony,
kopiowanie do klienta jako niezależna dieta v1, izolacja między trenerami."""

from conftest import CLIENT_A, COACH, create_user_with_role, get_user_id, login

BASE = "/api/nutrition-templates"


def _import_z_katalogu(client, hc) -> dict:
    katalog = client.get(f"{BASE}/catalog", headers=hc).json()["templates"]
    assert katalog and katalog[0]["id"] == "DTPL-001"
    r = client.post(f"{BASE}/catalog/{katalog[0]['id']}/import", headers=hc)
    assert r.status_code == 201, r.text
    return r.json()


def test_katalog_import_i_lista_moich(seeded):
    hc = login(seeded, COACH)
    tpl = _import_z_katalogu(seeded, hc)
    # Treść przeszła 1:1 (posiłki z opcjami, sekcje, makro puste).
    assert tpl["content"]["kcal"] is None
    assert len(tpl["content"]["meals"]) == 4
    assert any("Ściąga" in s["title"] for s in tpl["content"]["sections"])
    moje = seeded.get(BASE, headers=hc).json()["templates"]
    assert [t["id"] for t in moje] == [tpl["id"]]


def test_kopiowanie_do_klienta_tworzy_niezalezna_diete_v1(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    tpl = _import_z_katalogu(seeded, hc)

    r = seeded.post(
        f"{BASE}/{tpl['id']}/copy-to/{id_a}", headers=hc,
        json={"kcal": 2500, "protein_g": 200, "fat_g": 70, "carbs_g": 280},
    )
    assert r.status_code == 201, r.text

    dieta = seeded.get(f"/api/clients/{id_a}/nutrition", headers=ha).json()
    plany = dieta["plans"] if isinstance(dieta, dict) and "plans" in dieta else dieta
    plan = plany[0] if isinstance(plany, list) else plany
    # Makro nadane przy kopiowaniu (świadoma decyzja per klient).
    tresc = plan["current_version"]["content"] if "current_version" in plan else plan
    assert str(tresc).count("2500") >= 1

    # Edycja szablonu PO skopiowaniu nie zmienia diety klienta.
    r = seeded.put(
        f"{BASE}/{tpl['id']}", headers=hc,
        json={"title": "Zmieniony", "sections": [], "meals": []},
    )
    assert r.status_code == 200
    dieta2 = seeded.get(f"/api/clients/{id_a}/nutrition", headers=ha).json()
    assert str(dieta2).count("2500") >= 1


def test_izolacja_miedzy_trenerami(seeded):
    hc = login(seeded, COACH)
    tpl = _import_z_katalogu(seeded, hc)

    create_user_with_role("trener2@example.com", "Trener2#2026!x", "Trener Drugi", "COACH")
    h2 = login(seeded, {"email": "trener2@example.com", "password": "Trener2#2026!x"})
    # Cudzy szablon jest niewidoczny i niedostępny (404, bez potwierdzania id).
    assert seeded.get(BASE, headers=h2).json()["templates"] == []
    r = seeded.put(f"{BASE}/{tpl['id']}", headers=h2,
                   json={"title": "Przejęty", "sections": [], "meals": []})
    assert r.status_code == 404
    assert seeded.delete(f"{BASE}/{tpl['id']}", headers=h2).status_code == 404


def test_usuniecie_szablonu_nie_dotyka_diet_klientow(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    tpl = _import_z_katalogu(seeded, hc)
    assert seeded.post(f"{BASE}/{tpl['id']}/copy-to/{id_a}", headers=hc,
                       json={}).status_code == 201
    assert seeded.delete(f"{BASE}/{tpl['id']}", headers=hc).json()["ok"] is True
    dieta = seeded.get(f"/api/clients/{id_a}/nutrition", headers=ha)
    assert dieta.status_code == 200
    assert "Etap I" in str(dieta.json())

"""Zgody per kategoria (RODO): cofnięcie jednej kategorii odbiera dostęp
tylko do niej; decyzję podejmuje hos_engine.ConsentRegistry (Human OS
Core) na podstawie granularnych wierszy z consent_catalog."""

from conftest import CLIENT_A, COACH, get_user_id, login


def _consents(client, headers):
    return client.get("/api/me/consents", headers=headers).json()["consents"]


def _active(consents, category):
    return next(
        c for c in consents
        if c["revoked_at"] is None and c["denied_at"] is None
        and c["category"] == category
    )


def test_revoke_health_consent_blocks_only_health_access(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)

    assert seeded.get(f"/api/clients/{id_a}/measurements", headers=hc).status_code == 200
    assert seeded.get(f"/api/clients/{id_a}/plans", headers=hc).status_code == 200

    active = _active(_consents(seeded, ha), "dane_zdrowotne")
    r = seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    assert r.status_code == 200
    assert r.json()["revoked_at"]

    # Trener traci dostęp do danych ZDROWOTNYCH mimo aktywnej relacji…
    assert seeded.get(f"/api/clients/{id_a}/measurements", headers=hc).status_code == 404
    assert seeded.get(f"/api/clients/{id_a}/checkins", headers=hc).status_code == 404
    # …ale kategorie objęte innymi zgodami działają dalej (odrębne cele).
    assert seeded.get(f"/api/clients/{id_a}/plans", headers=hc).status_code == 200
    assert seeded.get(f"/api/clients/{id_a}/profile", headers=hc).status_code == 200

    # Klient nadal widzi własne dane.
    assert seeded.get(f"/api/clients/{id_a}/measurements", headers=ha).status_code == 200


def test_revoke_nutrition_consent_blocks_diet_and_hides_allergies(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)

    assert seeded.get(f"/api/clients/{id_a}/nutrition", headers=hc).status_code == 200
    fields = seeded.get(f"/api/clients/{id_a}/profile", headers=hc).json()["fields"]
    assert any(f["field_key"] == "alergie" for f in fields)

    active = _active(_consents(seeded, ha), "zywienie_alergie")
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)

    assert seeded.get(f"/api/clients/{id_a}/nutrition", headers=hc).status_code == 404
    assert seeded.get(f"/api/clients/{id_a}/nutrition-log", headers=hc).status_code == 404
    # Profil dalej dostępny (współpraca), ale pola żywieniowe zniknęły.
    fields = seeded.get(f"/api/clients/{id_a}/profile", headers=hc).json()["fields"]
    keys = {f["field_key"] for f in fields}
    assert "alergie" not in keys
    assert "preferencje_zywieniowe" not in keys
    # Urazy (domena zdrowotna, zgoda aktywna) nadal widoczne.
    assert "urazy" in keys
    # Klient sam widzi wszystko.
    own = seeded.get(f"/api/clients/{id_a}/profile", headers=ha).json()["fields"]
    assert "alergie" in {f["field_key"] for f in own}


def test_revoke_photos_consent_blocks_photo_list_and_files(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    photos = seeded.get(f"/api/clients/{id_a}/photos", headers=hc).json()["photos"]
    assert photos  # seed ma zdjęcia demo

    active = _active(_consents(seeded, ha), "zdjecia_progresu")
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)

    assert seeded.get(f"/api/clients/{id_a}/photos", headers=hc).status_code == 404
    # Także ISTNIEJĄCE pliki zdjęć są niedostępne dla trenera.
    assert seeded.get(f"/api/files/{photos[0]['file_id']}", headers=hc).status_code == 404
    # Właściciel nadal je pobiera.
    assert seeded.get(f"/api/files/{photos[0]['file_id']}", headers=ha).status_code == 200


def test_regrant_restores_access(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    coach_id = get_user_id(seeded, hc)
    active = _active(_consents(seeded, ha), "dane_zdrowotne")
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    assert seeded.get(f"/api/clients/{id_a}/measurements", headers=hc).status_code == 404

    r = seeded.post("/api/me/consents", headers=ha, json={
        "category": "dane_zdrowotne", "grantee_id": coach_id,
    })
    assert r.status_code == 201
    assert seeded.get(f"/api/clients/{id_a}/measurements", headers=hc).status_code == 200


def test_consent_history_is_preserved(seeded):
    ha = login(seeded, CLIENT_A)
    active = _active(_consents(seeded, ha), "dane_zdrowotne")
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    after = _consents(seeded, ha)
    revoked = next(c for c in after if c["id"] == active["id"])
    assert revoked["revoked_at"] is not None  # wiersz zostaje, nie znika
    assert revoked["category"] == "dane_zdrowotne"
    assert revoked["legal_basis"]  # podstawa prawna zapisana w historii


def test_cannot_revoke_someone_elses_consent(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, {"email": "klient.b@example.com",
                        "password": "KlientB#2026!x"})
    consents_b = _consents(seeded, hb)
    target = consents_b[0]["id"]
    r = seeded.post(f"/api/me/consents/{target}/revoke", headers=ha)
    assert r.status_code == 404
    after = _consents(seeded, hb)
    assert next(c for c in after if c["id"] == target)["revoked_at"] is None


def test_consents_response_carries_catalog(seeded):
    """Każda kategoria niesie pełny opis: cel, zakres, odbiorców, okres,
    dobrowolność, sposób wycofania i wersję dokumentu — UI nie zgaduje."""
    ha = login(seeded, CLIENT_A)
    body = seeded.get("/api/me/consents", headers=ha).json()
    assert body["document_version"]
    catalog = {c["key"]: c for c in body["catalog"]}
    expected = {
        "prowadzenie_konta", "udostepnianie_trenerowi", "dane_treningowe",
        "komunikacja", "dane_zdrowotne", "zywienie_alergie",
        "zdjecia_progresu", "przypomnienia", "funkcje_ai", "marketing",
    }
    assert expected <= set(catalog)
    for cat in catalog.values():
        for field in ("cel", "zakres", "odbiorcy", "okres", "dobrowolnosc",
                      "wycofanie", "legal_basis", "document_version"):
            assert cat[field], (cat["key"], field)
    # Wymagane i opcjonalne są jawnie rozdzielone.
    assert catalog["prowadzenie_konta"]["required"] is True
    assert catalog["marketing"]["required"] is False
    assert catalog["dane_zdrowotne"]["required"] is False

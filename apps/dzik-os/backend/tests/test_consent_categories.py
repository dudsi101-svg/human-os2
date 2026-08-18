"""Kategorie zgód RODO: odmowa opcjonalnej, wersje dokumentu, zgoda na
funkcje AI, przypomnienia (push) i porządek onboardingu."""

from conftest import CLIENT_A, COACH, activation_token, get_user_id, invite_client, login


def _consents(client, headers):
    return client.get("/api/me/consents", headers=headers).json()["consents"]


def test_decline_optional_consent_is_recorded_and_never_authorizes(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    coach_id = get_user_id(seeded, hc)

    # Cofnij aktywną zgodę na zdjęcia i odmów jej jawnie.
    active = next(c for c in _consents(seeded, ha)
                  if c["category"] == "zdjecia_progresu" and c["revoked_at"] is None)
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    r = seeded.post("/api/me/consents/decline", headers=ha, json={
        "category": "zdjecia_progresu", "grantee_id": coach_id,
    })
    assert r.status_code == 201
    assert r.json()["denied_at"]

    # Odmowa jest w historii i nigdy nie autoryzuje.
    rows = _consents(seeded, ha)
    denied = next(c for c in rows if c["denied_at"] is not None)
    assert denied["category"] == "zdjecia_progresu"
    assert seeded.get(f"/api/clients/{id_a}/photos", headers=hc).status_code == 404

    # Audyt zna odmowę.
    from dzik_os.hos_bridge import event_store

    assert "CONSENT_DECLINED" in [e["event_type"] for e in event_store().all()]


def test_required_category_cannot_be_declined(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    r = seeded.post("/api/me/consents/decline", headers=ha, json={
        "category": "prowadzenie_konta",
        "grantee_id": get_user_id(seeded, hc),
    })
    assert r.status_code == 422


def test_unknown_category_rejected(seeded):
    ha = login(seeded, CLIENT_A)
    assert seeded.post("/api/me/consents", headers=ha, json={
        "category": "nie_ma_takiej", "grantee_id": "X"}).status_code == 422
    assert seeded.post("/api/me/consents/decline", headers=ha, json={
        "category": "nie_ma_takiej"}).status_code == 422


def test_document_version_recorded_and_flagged_on_change(seeded, monkeypatch):
    """Zmiana wersji dokumentu zgód: stare wiersze zachowują SWOJĄ wersję,
    API flaguje je jako nieaktualne, nowa zgoda dostaje nową wersję."""
    from dzik_os import consent_catalog

    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    coach_id = get_user_id(seeded, hc)

    before = next(c for c in _consents(seeded, ha)
                  if c["category"] == "dane_zdrowotne" and c["revoked_at"] is None)
    assert before["consent_text_version"] == consent_catalog.CONSENT_DOC_VERSION
    assert before["document_version_current"] is True

    monkeypatch.setattr(consent_catalog, "CONSENT_DOC_VERSION", "9.9")
    rows = _consents(seeded, ha)
    old = next(c for c in rows if c["id"] == before["id"])
    assert old["consent_text_version"] == before["consent_text_version"]  # historia
    assert old["document_version_current"] is False

    r = seeded.post("/api/me/consents", headers=ha, json={
        "category": "dane_zdrowotne", "grantee_id": coach_id,
    })
    assert r.status_code == 201
    assert r.json()["consent_text_version"] == "9.9"


def test_ai_summary_requires_client_ai_consent(seeded):
    """Deklaracja/decyzja trenera nie zastępuje zgody klienta: bez zgody
    kategorii funkcje_ai podsumowanie AI nie jest dostępne."""
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    checkins = seeded.get(f"/api/clients/{id_a}/checkins", headers=hc).json()["checkins"]
    checkin_id = checkins[0]["id"]

    # Klient A ma zgodę z seeda → ścieżka przechodzi bramkę zgody
    # (dalej dostawca Null zwraca available=False z powodem konfiguracji).
    r = seeded.post(f"/api/checkins/{checkin_id}/ai-summary", headers=hc)
    assert r.status_code == 200
    assert "konfiguracji" in r.json()["reason"]

    # Po cofnięciu zgody AI powodem jest brak zgody klienta.
    active = next(c for c in _consents(seeded, ha)
                  if c["category"] == "funkcje_ai" and c["revoked_at"] is None)
    seeded.post(f"/api/me/consents/{active['id']}/revoke", headers=ha)
    r = seeded.post(f"/api/checkins/{checkin_id}/ai-summary", headers=hc)
    assert r.status_code == 200
    assert r.json()["available"] is False
    assert "zgody" in r.json()["reason"]


def test_push_subscribe_grants_consent_and_revoke_removes_subscriptions(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/push/subscribe", headers=ha, json={
        "endpoint": "https://push.example/abc123",
        "keys": {"p256dh": "k" * 20, "auth": "a" * 10},
    })
    assert r.status_code == 201
    consent = next(c for c in _consents(seeded, ha)
                   if c["category"] == "przypomnienia" and c["revoked_at"] is None)
    assert consent["confirmed_at"] is not None  # opt-in podmiotu

    # Wycofanie zgody usuwa WSZYSTKIE subskrypcje push (natychmiastowe
    # ograniczenie przyszłego przetwarzania).
    r = seeded.post(f"/api/me/consents/{consent['id']}/revoke", headers=ha)
    assert r.status_code == 200
    from dzik_os.db import db_session
    from dzik_os.models import PushSubscription, User

    with db_session() as db:
        uid = db.query(User).filter_by(email=CLIENT_A["email"]).one().id
        assert db.query(PushSubscription).filter_by(user_id=uid).count() == 0


def test_onboarding_registers_separate_declarations_per_category(seeded):
    """Onboarding rejestruje ODRĘBNE deklaracje per kategoria (żadnej
    zbiorczej zgody), bez kategorii czysto opcjonalnych (przypomnienia,
    AI, marketing)."""
    hc = login(seeded, COACH)
    # Przepływ zaproszeń (P8): trener podaje tylko e-mail i imię, klient
    # aktywuje konto własnym hasłem — hasła startowe nie istnieją.
    created = invite_client(seeded, hc, "kategorie@example.com", "Nowa Osoba")
    token = activation_token(created)
    r = seeded.post("/api/auth/activate", json={
        "token": token, "password": "NoweWlasne#123"})
    assert r.status_code == 200
    r = seeded.post("/api/auth/login", json={
        "email": "kategorie@example.com", "password": "NoweWlasne#123"})
    hn = {"Authorization": f"Bearer {r.json()['token']}"}

    rows = _consents(seeded, hn)
    cats = {c["category"] for c in rows}
    assert {"prowadzenie_konta", "udostepnianie_trenerowi", "dane_treningowe",
            "komunikacja", "dane_zdrowotne", "zywienie_alergie",
            "zdjecia_progresu"} <= cats
    assert "przypomnienia" not in cats
    assert "funkcje_ai" not in cats
    assert "marketing" not in cats
    for c in rows:
        assert c["source"] == "ONBOARDING_DECLARATION"
        assert c["confirmed_at"] is None  # czeka na decyzję podmiotu

    # Klient odmawia TYLKO zdjęć — reszta zgód pozostaje aktywna.
    photos = next(c for c in rows if c["category"] == "zdjecia_progresu")
    assert seeded.post(f"/api/me/consents/{photos['id']}/revoke",
                       headers=hn).status_code == 200
    remaining = [c for c in _consents(seeded, hn)
                 if c["revoked_at"] is None and c["denied_at"] is None]
    assert {c["category"] for c in remaining} >= {"dane_zdrowotne", "komunikacja"}


def test_legacy_umbrella_consent_still_authorizes_full_scope(seeded):
    """Wiersz sprzed migracji nr 10 (category=NULL, coaching/health_data,
    allow_sensitive) zachowuje swój pierwotny, pełny zakres — migracja nie
    zawęża po cichu udzielonej zgody ani jej nie unieważnia."""
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    coach_id = get_user_id(seeded, hc)

    # Cofnij wszystkie granularne zgody…
    for c in _consents(seeded, ha):
        if c["revoked_at"] is None and c["denied_at"] is None:
            seeded.post(f"/api/me/consents/{c['id']}/revoke", headers=ha)
    assert seeded.get(f"/api/clients/{id_a}/plans", headers=hc).status_code == 404

    # …i włóż wiersz w KSZTAŁCIE sprzed migracji (jak w produkcyjnej bazie).
    from dzik_os.db import db_session
    from dzik_os.models import ConsentRecord, new_id

    with db_session() as db:
        db.add(ConsentRecord(
            id=new_id("CNS"), subject_id=id_a, grantee_id=coach_id,
            purpose="coaching", domain="health_data",
            actions="read,write", allow_sensitive=True,
            consent_text_version="1.0", category=None,
        ))

    for path in ("plans", "measurements", "nutrition", "photos", "profile"):
        assert seeded.get(f"/api/clients/{id_a}/{path}",
                          headers=hc).status_code == 200, path

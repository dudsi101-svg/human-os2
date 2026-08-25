"""Głęboki wywiad — drugi przepływ mechanizmu rozmowy (flow='deep').

Testy pilnują jednocześnie funkcji i granic: wywiad jest niezależny od
rozmowy startowej (własna sesja, własne kroki), pytania wrażliwe istnieją
wyłącznie za zgodą kategorii, flagi wyboru z przesiewu bezpieczeństwa
podnoszą flagę sesji spokojnym komunikatem (bez oceny), zatwierdzenie
zapisuje pola profilu `gw_*` bez tworzenia celu, a AI nie dostaje niczego
— podsumowanie jest zawsze deterministyczne z jawnym powodem.
"""

from __future__ import annotations

from conftest import CLIENT_A, CLIENT_B, COACH, get_user_id, login

from dzik_os.interview_flow import DEEP_STEP_BY_ID, DEEP_STEPS

BASE = "/api/clients/{}/interview"


def start(client, headers, client_id) -> dict:
    r = client.post(BASE.format(client_id) + "/start", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def answer(client, headers, client_id, step_id, value="", skipped=False):
    return client.post(
        BASE.format(client_id) + "/answer",
        headers=headers,
        json={"step_id": step_id, "value": value, "skipped": skipped},
    )


def answer_ok(client, headers, client_id, step_id, value="", skipped=False) -> dict:
    r = answer(client, headers, client_id, step_id, value, skipped)
    assert r.status_code == 200, r.text
    return r.json()


def run_to(client, headers, client_id, stop_at: str) -> dict:
    """Przechodzi wywiad pierwszą sensowną odpowiedzią aż do wskazanego
    kroku (który zostaje bieżący, bez odpowiedzi)."""
    body = start(client, headers, client_id)
    guard = 0
    while body["step"] is not None and guard < 80:
        guard += 1
        step = body["step"]
        if step["id"] == stop_at:
            return body
        value = step["options"][0] if step["options"] else f"Odpowiedź {step['id']}"
        # Przesiew nie ma flagować w tle zwykłych przejść testowych.
        if step["id"] == "gw_c1":
            value = "Żadne z powyższych"
        if step["id"] in ("gw_c2", "gw_d3", "gw_e3"):
            value = "Nie"
        body = answer_ok(client, headers, client_id, step["id"], value)
    return body


def test_wywiad_zaczyna_sie_od_intro_i_ma_wlasny_scenariusz(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    body = start(seeded, ha, id_a)
    assert body["step"]["id"] == "gw_intro"
    assert body["step"]["why"]
    # Pełny plan przy aktywnych zgodach seedu: wszystkie kroki bezwarunkowe.
    unconditional = [s.id for s in DEEP_STEPS if not s.conditional]
    assert body["planned_steps"] == unconditional
    # AI w wywiadzie nie istnieje — jawny powód, nie błąd i nie brak pola.
    assert body["ai"]["available"] is False
    assert "nic nie jest wysyłane" in body["ai"]["reason"]


def test_wywiad_jest_niezalezny_od_rozmowy_startowej(seeded):
    """Otwarta rozmowa startowa nie blokuje wywiadu i odwrotnie — to dwie
    osobne sesje tego samego mechanizmu."""
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.post(f"/api/clients/{id_a}/onboarding/start", headers=ha)
    assert r.status_code == 201
    onboarding_session = r.json()["session"]["id"]
    body = start(seeded, ha, id_a)
    assert body["session"]["id"] != onboarding_session
    assert body["step"]["id"] == "gw_intro"
    # Rozmowa startowa stoi tam, gdzie stała.
    r = seeded.get(f"/api/clients/{id_a}/onboarding", headers=ha)
    assert r.json()["session"]["id"] == onboarding_session
    assert r.json()["step"]["id"] == "cel_glowny"


def test_galaz_zmianowosci_odslania_sie_po_tak(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    body = run_to(seeded, ha, id_a, "gw_d3")
    assert "gw_d3_wzor" not in body["planned_steps"]
    body = answer_ok(seeded, ha, id_a, "gw_d3", "Tak")
    assert "gw_d3_wzor" in body["planned_steps"]
    assert body["step"]["id"] == "gw_d3_wzor"


def test_pominiecie_jest_pelnoprawna_odpowiedzia(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    run_to(seeded, ha, id_a, "gw_a1")
    body = answer_ok(seeded, ha, id_a, "gw_a1", skipped=True)
    stored = next(a for a in body["answers"] if a["step_id"] == "gw_a1")
    assert stored["skipped"] is True
    # Pominięty krok nie wraca jako bieżący.
    assert body["step"]["id"] != "gw_a1"


def test_przesiew_flaguje_sesje_spokojnym_komunikatem(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    run_to(seeded, ha, id_a, "gw_c1")
    body = answer_ok(
        seeded, ha, id_a, "gw_c1", "Ból lub ucisk w klatce piersiowej"
    )
    assert body["session"]["safety_flag"] is True
    notice = body["safety_notice"]
    assert notice is not None
    assert "Ból lub ucisk w klatce piersiowej" in notice["signals"]
    # Komunikat kieruje do lekarza i nie ocenia.
    assert "lekarz" in notice["message"]
    assert "wstrzyma" in notice["message"]


def test_zadne_z_powyzszych_nie_flaguje(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    run_to(seeded, ha, id_a, "gw_c1")
    body = answer_ok(seeded, ha, id_a, "gw_c1", "Żadne z powyższych")
    assert body["safety_notice"] is None
    assert body["session"]["safety_flag"] is False


def test_relacja_z_cialem_flaguje_lagodniejszym_komunikatem(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    run_to(seeded, ha, id_a, "gw_e3")
    body = answer_ok(seeded, ha, id_a, "gw_e3", "Tak")
    notice = body["safety_notice"]
    assert notice is not None
    # Inny kontekst = inny komunikat: bez 112, z ostrożniejszym prowadzeniem.
    assert "ostrożniej" in notice["message"]
    assert "112" not in notice["message"]


def test_bez_zgody_zdrowotnej_modul_przesiewu_nie_istnieje(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    # Cofnięcie zgody zdrowotnej (ta sama ścieżka co w testach onboardingu).
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    health = next(
        c
        for c in consents
        if c["revoked_at"] is None and c["category"] == "dane_zdrowotne"
    )
    r = seeded.post(f"/api/me/consents/{health['id']}/revoke", headers=ha)
    assert r.status_code == 200, r.text
    body = start(seeded, ha, id_a)
    planned = body["planned_steps"]
    assert "gw_c1" not in planned
    assert "gw_d1" not in planned
    # Moduły bez domeny zdrowotnej zostają.
    assert "gw_a1" in planned
    assert "gw_g1" in planned


def test_zatwierdzenie_zapisuje_pola_profilu_bez_tworzenia_celu(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    goals_before = seeded.get(f"/api/clients/{id_a}/goals", headers=ha).json()["goals"]
    run_to(seeded, ha, id_a, "gw_a1")
    answer_ok(seeded, ha, id_a, "gw_a1", "Wbiegam na trzecie piętro bez zadyszki")
    r = seeded.post(BASE.format(id_a) + "/summary", headers=ha)
    assert r.status_code == 200, r.text
    assert r.json()["session"]["summary_mode"] == "FORM"
    r = seeded.post(BASE.format(id_a) + "/approve", headers=ha)
    assert r.status_code == 200, r.text
    assert "gw_cel_scena" in r.json()["applied_fields"]
    assert r.json()["goal_id"] is None
    goals_after = seeded.get(f"/api/clients/{id_a}/goals", headers=ha).json()["goals"]
    assert len(goals_after) == len(goals_before)
    # Pole naprawdę siedzi w profilu.
    r = seeded.get(f"/api/clients/{id_a}/profile", headers=ha)
    values = {f["field_key"]: f["value"] for f in r.json()["fields"]}
    assert values.get("gw_cel_scena") == "Wbiegam na trzecie piętro bez zadyszki"


def test_cudzy_klient_nie_widzi_wywiadu(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    id_a = get_user_id(seeded, ha)
    start(seeded, ha, id_a)
    r = seeded.get(BASE.format(id_a), headers=hb)
    assert r.status_code == 404
    r = seeded.post(BASE.format(id_a) + "/start", headers=hb)
    assert r.status_code == 404


def test_trener_widzi_wywiad_w_review_ale_nie_odpowiada(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    run_to(seeded, ha, id_a, "gw_a1")
    answer_ok(seeded, ha, id_a, "gw_a1", "Scena z życia")
    r = seeded.get(BASE.format(id_a) + "/review", headers=hc)
    assert r.status_code == 200
    assert any(a["step_id"] == "gw_a1" for a in r.json()["answers"])
    # Trener nie prowadzi wywiadu za klienta.
    r = answer(seeded, hc, id_a, "gw_a2", "5")
    assert r.status_code == 404


def test_podpowiedzi_trafiaja_do_obszarow_pracy_trenera(seeded):
    """Zatwierdzone odpowiedzi wywiadu widać jako podpowiedzi przy planie
    i diecie — dosłowne deklaracje z proweniencją, nigdy interpretacja."""
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    run_to(seeded, ha, id_a, "gw_b2")
    answer_ok(seeded, ha, id_a, "gw_b2", "Lubię ciężary, nie znoszę biegania")
    run_to(seeded, ha, id_a, "gw_f4")
    answer_ok(seeded, ha, id_a, "gw_f4", "Nie tknę ryb; must-have: pieczywo")
    seeded.post(BASE.format(id_a) + "/summary", headers=ha)
    r = seeded.post(BASE.format(id_a) + "/approve", headers=ha)
    assert r.status_code == 200, r.text

    r = seeded.get(f"/api/clients/{id_a}/profile/hints?area=PLAN", headers=hc)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["disclaimer"]
    plan = {h["field_key"]: h for h in body["hints"]}
    assert plan["gw_ruch_preferencje"]["value"] == "Lubię ciężary, nie znoszę biegania"
    # Proweniencja wprost ze scenariusza: pytanie + moduł + przepływ.
    assert plan["gw_ruch_preferencje"]["flow"] == "deep"
    assert plan["gw_ruch_preferencje"]["question"]
    # Pole żywieniowe nie przecieka do obszaru planu…
    assert "gw_produkty_preferencje" not in plan
    # …ale jest w obszarze diety.
    r = seeded.get(f"/api/clients/{id_a}/profile/hints?area=DIETA", headers=hc)
    dieta = {h["field_key"] for h in r.json()["hints"]}
    assert "gw_produkty_preferencje" in dieta
    # Zły obszar = 422, nie cichy fallback.
    r = seeded.get(f"/api/clients/{id_a}/profile/hints?area=WSZYSTKO", headers=hc)
    assert r.status_code == 422


def test_podpowiedzi_szanuja_zgody_jak_profil(seeded):
    """Cofnięcie zgody żywieniowej chowa żywieniowe podpowiedzi diety —
    dokładnie ta sama ścieżka filtrowania co widok profilu."""
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    run_to(seeded, ha, id_a, "gw_f4")
    answer_ok(seeded, ha, id_a, "gw_f4", "Nie tknę ryb")
    seeded.post(BASE.format(id_a) + "/summary", headers=ha)
    seeded.post(BASE.format(id_a) + "/approve", headers=ha)
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    nutrition = next(
        c
        for c in consents
        if c["revoked_at"] is None and c["category"] == "zywienie_alergie"
    )
    r = seeded.post(f"/api/me/consents/{nutrition['id']}/revoke", headers=ha)
    assert r.status_code == 200, r.text
    r = seeded.get(f"/api/clients/{id_a}/profile/hints?area=DIETA", headers=hc)
    dieta = {h["field_key"] for h in r.json()["hints"]}
    assert "gw_produkty_preferencje" not in dieta


def test_podpowiedzi_izolacja_cudzy_klient(seeded):
    hb = login(seeded, CLIENT_B)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    r = seeded.get(f"/api/clients/{id_a}/profile/hints?area=PLAN", headers=hb)
    assert r.status_code == 404


def test_kazde_pole_scenariuszy_ma_swiadome_mapowanie_obszarow():
    """Nowe pytanie bez wpisu w HINT_AREAS ma czerwienić build, a nie po
    cichu znikać z podpowiedzi trenera."""
    from dzik_os.coach_hints import AREAS, HINT_AREAS
    from dzik_os.onboarding_flow import STEPS

    fields = {
        s.profile_field
        for s in (*STEPS, *DEEP_STEPS)
        if s.profile_field is not None
    }
    unmapped = fields - set(HINT_AREAS)
    assert not unmapped, f"pola bez mapowania obszarów: {sorted(unmapped)}"
    for field, areas in HINT_AREAS.items():
        assert areas, field
        assert set(areas) <= set(AREAS), field


def test_scenariusz_ma_komplet_uzasadnien_i_pol():
    """Każdy krok pytający ma „dlaczego pytam"; każdy krok wrażliwy ma
    domenę zgody; identyfikatory są unikalne (kontrakt scenariusza)."""
    assert len(DEEP_STEP_BY_ID) == len(DEEP_STEPS)
    for step in DEEP_STEPS:
        assert step.why, step.id
        if step.sensitive:
            assert step.consent_domain is not None, step.id

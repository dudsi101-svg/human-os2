"""Zakładka „Wywiad” (0.59.0) — testy odbioru ze specyfikacji właściciela
(13.09): stany wypełnienia/przeglądu/aktualności, zapis częściowy z rewizją,
pytania warunkowe liczone serwerowo, postęp bez dzielenia przez zero,
przesłanie jako niezmienna wersja z jednym wpisem trenera, przegląd per
wersja, doprecyzowania, wspólne uzupełnianie, zadania sprawdzenia planu
blokujące publikację, podpowiedzi konfiguratorów, dostęp z powodem,
migracja ponawialna bez powiadomień, outbox z ponowieniem.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from conftest import CLIENT_A, CLIENT_B, COACH, create_user_with_role, get_user_id, login

from dzik_os.db import SessionLocal, db_session
from dzik_os.models import (
    ClientFactRevision,
    InterviewDraft,
    InterviewReview,
    InterviewSubmission,
    Notification,
    OnboardingAnswer,
    OnboardingSession,
    OutboxEvent,
    PlanReviewTask,
    new_id,
)
from dzik_os.wywiad import definicje as D
from dzik_os.wywiad import migracja

W = "/api/clients/{}/wywiady"


def _def(c, h, cid, typ="wstepny"):
    r = c.get(f"{W.format(cid)}/{typ}/definicja", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _opcja(defn, qid, idx=0):
    return next(q for q in defn["questions"] if q["question_id"] == qid)["options"][idx]


def _patch(c, h, cid, revision, answers, typ="wstepny", expect=200, **extra):
    r = c.patch(f"{W.format(cid)}/{typ}/szkic", headers=h, json={"revision": revision, "answers": answers, **extra})
    assert r.status_code == expect, r.text
    return r.json()


def _przeslij(c, h, cid, revision, typ="wstepny", expect=201, key=None):
    body = {"revision": revision}
    if key:
        body["idempotency_key"] = key
    r = c.post(f"{W.format(cid)}/{typ}/przeslij", headers=h, json=body)
    assert r.status_code == expect, r.text
    return r.json()


def _stan(c, h, cid, typ="wstepny"):
    r = c.get(W.format(cid), headers=h)
    assert r.status_code == 200, r.text
    return next(w for w in r.json()["wywiady"] if w["typ"] == typ)


def _wpisy(c, h):
    return [n for n in c.get("/api/notifications", headers=h).json()["notifications"] if n["category"] == "WYWIAD"]


def _komplet_wstepny(c, h, cid):
    """Odpowiedzi na wszystkie pytania wymagane wywiadu wstępnego (zgody pełne)."""
    d = _def(c, h, cid)
    return {
        "cel_glowny": {"value": "Wrócić do formy po przerwie"},
        "doswiadczenie": {"value": _opcja(d, "doswiadczenie", 0)},
        "dostepnosc": {"value": _opcja(d, "dostepnosc", 1)},
        "sprzet": {"value": _opcja(d, "sprzet", 0)},
        "urazy_czy": {"value": "Nie zgłaszam"},
        "bol_obecny": {"value": "Nie zgłaszam"},
        "zywienie_styl": {"value": "2 posiłki, dużo w biegu"},
        "alergie_status": {"value": "Nie zgłaszam"},
        "komunikacja": {"value": _opcja(d, "komunikacja", 0)},
    }


def _przeslij_komplet(c, h, cid, **nadpisz):
    ans = _komplet_wstepny(c, h, cid)
    ans.update(nadpisz)
    r = _patch(c, h, cid, _rev(c, h, cid), ans)
    assert r["errors"] == {}, r["errors"]
    return _przeslij(c, h, cid, r["revision"])


def _rev(c, h, cid, typ="wstepny"):
    d = _def(c, h, cid, typ)
    return d["draft"]["revision"] if d["draft"] else 1


def _revoke_health(c, h):
    consents = c.get("/api/me/consents", headers=h).json()["consents"]
    health = next(x for x in consents if x["revoked_at"] is None and x["category"] == "dane_zdrowotne")
    assert c.post(f"/api/me/consents/{health['id']}/revoke", headers=h).status_code == 200


# --- 1. nowy klient: oba formularze widoczne jako not_started, trener widzi stan pusty --------


def test_t01_kazdy_klient_ma_oba_formularze_od_razu(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    for h in (ha, hc):
        r = seeded.get(W.format(cid), headers=h).json()
        assert r["access"]["ok"] is True and r["access"]["reason"] is None
        assert [w["typ"] for w in r["wywiady"]] == ["wstepny", "gleboki", "zapotrzebowanie"]
        assert all(w["submission_status"] == "not_started" and w["review_status"] == "not_reviewed"
                   and w["freshness_status"] == "current" for w in r["wywiady"])
    # Definicja dostępna bez żadnego wiersza w bazie; postęp wyliczony z 0 odpowiedzi.
    d = _def(seeded, ha, cid)
    assert d["draft"] is None and d["progress"]["required_total"] > 0 and d["progress"]["percent"] == 0
    with SessionLocal() as db:
        assert db.query(InterviewDraft).count() == 0 and db.query(OutboxEvent).count() == 0
    # Klient wskazany po id — niezależnie od nazwy czy e-maila (zmiana nazwy nie gubi wywiadu).
    assert seeded.get(W.format(cid), headers=ha).json()["client_id"] == cid


# --- 2. zapis częściowy = szkic, brak powiadomień ----------------------------------------------


def test_t02_zapis_czesciowy_tworzy_szkic_bez_powiadomien(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    r = _patch(seeded, ha, cid, 1, {"cel_glowny": {"value": "schudnąć 5 kg"}})
    assert r["revision"] == 2 and r["errors"] == {} and r["progress"]["required_answered"] == 1
    assert r["saved_at"]  # potwierdzenie z serwera, nie z przeglądarki
    st = _stan(seeded, hc, cid)
    assert st["submission_status"] == "draft" and st["review_status"] == "not_reviewed"
    assert st["draft"]["dirty"] is True
    assert not _wpisy(seeded, hc) and not _wpisy(seeded, ha)
    with SessionLocal() as db:
        assert db.query(OutboxEvent).count() == 0 and db.query(InterviewSubmission).count() == 0


# --- 3. dwa urządzenia: konflikt rewizji zamiast cichego nadpisania -----------------------------


def test_t03_konflikt_rewizji_nie_nadpisuje(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, 1, {"cel_glowny": {"value": "telefon"}})
    r = seeded.patch(f"{W.format(cid)}/wstepny/szkic", headers=ha,
                     json={"revision": 1, "answers": {"cel_glowny": {"value": "laptop"}}})
    assert r.status_code == 409 and r.json()["code"] == "REVISION_CONFLICT" and r.json()["revision"] == 2
    d = _def(seeded, ha, cid)
    assert next(a for a in d["answers"] if a["question_id"] == "cel_glowny")["value"] == "telefon"


# --- 4. przesłanie bez wymaganych: lista braków --------------------------------------------------


def test_t04_przeslanie_bez_wymaganych_zwraca_braki(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    r = _patch(seeded, ha, cid, 1, {"cel_glowny": {"value": "forma"}})
    out = _przeslij(seeded, ha, cid, r["revision"], expect=422)
    assert out["code"] == "MISSING_ANSWERS" and "doswiadczenie" in out["missing"] and "cel_glowny" not in out["missing"]
    # Pominięcie pytania wymaganego nie liczy się jako odpowiedź.
    r2 = _patch(seeded, ha, cid, r["revision"], {"doswiadczenie": {"skipped": True}})
    assert "doswiadczenie" in _przeslij(seeded, ha, cid, r2["revision"], expect=422)["missing"]
    # Walidacja pól: wartość spoza listy zostaje odrzucona, reszta zapisana.
    r3 = _patch(seeded, ha, cid, r2["revision"], {"sprzet": {"value": "cokolwiek"}, "cel_termin": {"value": "wesele"}})
    assert "sprzet" in r3["errors"] and r3["progress"]["active_answered"] >= 2


# --- 5. przesłanie = niezmienna wersja + jeden wpis trenera; idempotencja -------------------------


def test_t05_przeslanie_tworzy_wersje_i_jeden_wpis_trenera(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    ans = _komplet_wstepny(seeded, ha, cid)
    r = _patch(seeded, ha, cid, 1, ans)
    assert r["errors"] == {} and r["progress"]["ready"] is True
    w1 = _przeslij(seeded, ha, cid, r["revision"], key="klucz-0001")
    w2 = seeded.post(f"{W.format(cid)}/wstepny/przeslij", headers=ha,
                     json={"revision": r["revision"], "idempotency_key": "klucz-0001"})
    assert w2.status_code == 200 and w2.json()["submission_id"] == w1["submission_id"]
    st = _stan(seeded, ha, cid)
    assert st["submission_status"] == "submitted" and st["review_status"] == "not_reviewed" \
        and st["last_submission"]["version_no"] == 1 and st["submissions_count"] == 1
    wp = _wpisy(seeded, hc)
    assert len(wp) == 1 and "do przejrzenia" in wp[0]["title"] and f"/trener/klient/{cid}" in wp[0]["url"]
    # Treść wpisu nie niesie odpowiedzi.
    assert "forma" not in wp[0]["body"]
    with SessionLocal() as db:
        sub = db.get(InterviewSubmission, w1["submission_id"])
        zap = json.loads(sub.answers_json)
        assert zap["cel_glowny"]["entered_by"] == cid and zap["cel_glowny"]["at"]
    # Edycja po przesłaniu nie zmienia wersji — tworzy brudny szkic.
    r2 = _patch(seeded, ha, cid, w1["revision"], {"cel_glowny": {"value": "inny cel"}})
    assert _stan(seeded, ha, cid)["submission_status"] == "draft"
    with SessionLocal() as db:
        assert json.loads(db.get(InterviewSubmission, w1["submission_id"]).answers_json)["cel_glowny"]["value"] \
            == "Wrócić do formy po przerwie"
    assert r2["revision"] > w1["revision"]
    # Lista do przejrzenia i flaga na liście klientów.
    lista = seeded.get("/api/coach/wywiady/do-przegladu", headers=hc).json()
    assert lista["needs_review"] == 1 and next(x for x in lista["clients"] if x["client_id"] == cid)["needs_review"]
    row = next(x for x in seeded.get("/api/coach/clients", headers=hc).json()["clients"] if x["client_id"] == cid)
    assert row["flags"]["interview_to_review"] == 1


# --- 6. pytania warunkowe: serwer odsłania i chowa; nieaktywna gałąź nie wchodzi do wersji --------


def test_t06_pytania_warunkowe_liczone_serwerowo(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    d0 = _def(seeded, ha, cid)
    assert not next(q for q in d0["questions"] if q["question_id"] == "urazy_opis")["active"]
    r = _patch(seeded, ha, cid, 1, {"urazy_czy": {"value": "Tak"}})
    assert "urazy_opis" in r["active"] and "urazy_ograniczenia" in r["active"]
    r = _patch(seeded, ha, cid, r["revision"], {"urazy_opis": {"value": "lewe kolano"}})
    # „Nie wiem” nie odsłania (tylko „Tak”), a odpowiedź na urazy_opis zostaje w szkicu.
    r = _patch(seeded, ha, cid, r["revision"], {"urazy_czy": {"value": "Nie wiem"}})
    assert "urazy_opis" not in r["active"]
    d1 = _def(seeded, ha, cid)
    op = next(a for a in d1["answers"] if a["question_id"] == "urazy_opis")
    assert op["value"] == "lewe kolano" and op["active"] is False
    # Przesłanie: nieaktywna gałąź nie trafia do wersji ani do faktów.
    w = _przeslij_komplet(seeded, ha, cid, urazy_czy={"value": "Nie wiem"})
    with SessionLocal() as db:
        sub = db.get(InterviewSubmission, w["submission_id"])
        assert "urazy_opis" not in json.loads(sub.answers_json)
        assert db.query(ClientFactRevision).filter_by(client_id=cid, fact_key="urazy").count() == 0
        assert db.query(ClientFactRevision).filter_by(client_id=cid, fact_key="urazy_deklaracja").one().value == "Nie wiem"
    # Powrót „Tak” odsłania gałąź z zachowaną odpowiedzią do potwierdzenia.
    r = _patch(seeded, ha, cid, w["revision"], {"urazy_czy": {"value": "Tak"}})
    assert "urazy_opis" in r["active"]


# --- 7. postęp: wymagane aktywne / wymagane aktywne; bez zgody = bez pytań; 0/0 = 100 % -----------


def test_t07_postep_bez_dzielenia_przez_zero_i_bez_zgody(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    pelne = _def(seeded, ha, cid)["progress"]["required_total"]
    g = _def(seeded, ha, cid, "gleboki")
    # Głęboki: wymagany tylko przesiew (2 pytania) — reszta opcjonalna.
    assert g["progress"]["required_total"] == 2
    _revoke_health(seeded, ha)
    d = _def(seeded, ha, cid)
    assert d["progress"]["required_total"] < pelne and "health_data" in d["hidden_domains"]
    assert not any(q["active"] for q in d["questions"] if q["consent_domain"] == "health_data")
    g2 = _def(seeded, ha, cid, "gleboki")
    assert g2["progress"]["required_total"] == 0 and g2["progress"]["percent"] == 100 and g2["progress"]["ready"]
    # Próba zapisu pytania wyłączonej domeny — odrzucona jawnie, nie zapisana.
    r = _patch(seeded, ha, cid, 1, {"urazy_czy": {"value": "Tak"}, "cel_glowny": {"value": "x"}})
    assert "urazy_czy" in r["errors"] and "brak zgody" in r["errors"]["urazy_czy"]
    # Postęp z serwera zgadza się z definicją.
    assert r["progress"]["required_total"] == d["progress"]["required_total"]


# --- 8. „nie wiem / wolę omówić”: pełnoprawna odpowiedź, ale kompletność ≠ gotowość danych ----------


def test_t08_nie_wiem_liczy_sie_do_postepu_ale_zostaje_do_omowienia(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    d = _def(seeded, ha, cid)
    assert {_opcja(d, "urazy_czy", i) for i in range(4)} == set(D.OPCJE_OGRANICZEN)
    ans = _komplet_wstepny(seeded, ha, cid)
    ans["bol_obecny"] = {"value": "Wolę omówić z trenerem"}
    r = _patch(seeded, ha, cid, 1, ans)
    assert r["progress"]["ready"] is True and r["progress"]["data_ready"] is False
    _przeslij(seeded, ha, cid, r["revision"])
    p = seeded.get(f"{W.format(cid)}/podsumowanie", headers=hc).json()
    assert any("omówić" in x["text"] for x in p["do_wyjasnienia"])
    assert p["do_wyjasnienia"][0]["source"]["question_id"] == "bol_obecny"
    assert p["do_wyjasnienia"][0]["source"]["version_no"] == 1


# --- 9. przegląd: „oznacz jako przejrzane” per wersja; notatka wewnętrzna tylko dla trenera ---------


def test_t09_przeglad_per_wersja_i_notatka_wewnetrzna(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    w = _przeslij_komplet(seeded, ha, cid)
    r = seeded.post(f"/api/wywiady/zgloszenia/{w['submission_id']}/przeglad", headers=hc,
                    json={"outcome": "REVIEWED", "internal_note": "sprawdzić kolano na konsultacji"})
    assert r.status_code == 201
    assert _stan(seeded, ha, cid)["review_status"] == "reviewed"
    kl = _wpisy(seeded, ha)
    assert len(kl) == 1 and "przejrzał" in kl[0]["title"] and "nie ocena" in kl[0]["body"]
    hk = seeded.get(f"{W.format(cid)}/wstepny/historia", headers=ha).json()["submissions"][0]
    assert "internal_note" not in hk["reviews"][0]
    ht = seeded.get(f"{W.format(cid)}/wstepny/historia", headers=hc).json()["submissions"][0]
    assert ht["reviews"][0]["internal_note"] == "sprawdzić kolano na konsultacji"
    # Eksport danych klienta nie zawiera notatki wewnętrznej.
    eksport = seeded.get("/api/me/export", headers=ha)
    assert eksport.status_code == 200 and "sprawdzić kolano" not in eksport.text
    # Nowa wersja = przegląd od nowa, poprzedni w historii.
    r2 = _patch(seeded, ha, cid, w["revision"], {"cel_glowny": {"value": "nowy cel"}})
    w2 = _przeslij(seeded, ha, cid, r2["revision"])
    st = _stan(seeded, ha, cid)
    assert w2["version_no"] == 2 and st["review_status"] == "not_reviewed" and st["submissions_count"] == 2
    hist = seeded.get(f"{W.format(cid)}/wstepny/historia", headers=hc).json()["submissions"]
    assert hist[0]["review"]["outcome"] == "REVIEWED" and hist[1]["review"] is None
    # Ponowny przegląd tej samej wersji nie wysyła drugiego wpisu klientowi.
    seeded.post(f"/api/wywiady/zgloszenia/{w['submission_id']}/przeglad", headers=hc, json={"outcome": "REVIEWED"})
    assert len(_wpisy(seeded, ha)) == 1


# --- 10. prośba o doprecyzowanie → jeden wpis, statusy, zamknięcie kolejnym przesłaniem -----------


def test_t10_doprecyzowanie_i_aktualizacja_odpowiedzi(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    w = _przeslij_komplet(seeded, ha, cid, urazy_czy={"value": "Tak"}, urazy_opis={"value": "kolano"})
    r = seeded.post(f"/api/wywiady/zgloszenia/{w['submission_id']}/doprecyzowania", headers=hc,
                    json={"question_ids": ["urazy_opis"], "message": "Które kolano i od kiedy?"})
    assert r.status_code == 201 and r.json()["status"] == "OPEN"
    st = _stan(seeded, ha, cid)
    assert st["review_status"] == "needs_clarification" and st["freshness_status"] == "update_requested"
    assert st["open_clarifications"][0]["question_ids"] == ["urazy_opis"]
    kl = _wpisy(seeded, ha)
    assert len(kl) == 1 and "uzupełnienie" in kl[0]["title"] and kl[0]["url"].startswith("/wywiad")
    assert "kolano" not in kl[0]["body"]  # bez treści odpowiedzi
    p = seeded.get(f"{W.format(cid)}/podsumowanie", headers=ha).json()
    assert p["do_aktualizacji"] and p["do_aktualizacji"][0]["question_ids"] == ["urazy_opis"]
    # Nieznane pytanie → 422.
    assert seeded.post(f"/api/wywiady/zgloszenia/{w['submission_id']}/doprecyzowania", headers=hc,
                       json={"question_ids": ["nie_ma"], "message": ""}).status_code == 422
    # Aktualizacja odpowiedzi → nowa wersja zamyka prośbę; trener dostaje JEDEN nowy wpis.
    r2 = _patch(seeded, ha, cid, w["revision"], {"urazy_opis": {"value": "lewe kolano, od marca"}})
    w2 = _przeslij(seeded, ha, cid, r2["revision"])
    st = _stan(seeded, ha, cid)
    assert w2["version_no"] == 2 and st["freshness_status"] == "current" and st["review_status"] == "not_reviewed"
    assert st["open_clarifications"] == []
    assert len(_wpisy(seeded, hc)) == 2
    hist = seeded.get(f"{W.format(cid)}/wstepny/historia", headers=hc).json()["submissions"]
    assert hist[0]["clarifications"][0]["status"] == "RESOLVED" \
        and hist[0]["clarifications"][0]["resolved_at"]


# --- 11. „uzupełnij wspólnie”: autorstwo trenera widoczne; trener bez trybu wspólnego = 422 -------


def test_t11_uzupelnianie_wspolne_z_autorstwem(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    coach_id = get_user_id(seeded, hc)
    assert seeded.patch(f"{W.format(cid)}/wstepny/szkic", headers=hc,
                        json={"revision": 1, "answers": {"cel_glowny": {"value": "x"}}}).status_code == 422
    r = _patch(seeded, hc, cid, 1, {"cel_glowny": {"value": "wpisane na konsultacji"}}, collection_mode="WSPOLNIE")
    assert r["collection_mode"] == "WSPOLNIE"
    d = _def(seeded, ha, cid)
    a = next(x for x in d["answers"] if x["question_id"] == "cel_glowny")
    assert a["entered_by"] == coach_id and d["draft"]["collection_mode"] == "WSPOLNIE"
    # Klient poprawia — jego autorstwo; trener nadal nie dostaje powiadomień z autozapisu.
    r2 = _patch(seeded, ha, cid, r["revision"], {"cel_glowny": {"value": "poprawione przeze mnie"}})
    a2 = next(x for x in _def(seeded, ha, cid)["answers"] if x["question_id"] == "cel_glowny")
    assert a2["entered_by"] == cid and r2["revision"] == r["revision"] + 1
    assert not _wpisy(seeded, hc)
    # Trener widzi odpowiedzi wrażliwe tylko w zakresie zgód: po cofnięciu zgody zdrowotnej — ukryte.
    ans = _komplet_wstepny(seeded, ha, cid)
    ans["urazy_czy"] = {"value": "Tak"}
    ans["urazy_opis"] = {"value": "bark"}
    r3 = _patch(seeded, ha, cid, r2["revision"], ans)
    _przeslij(seeded, ha, cid, r3["revision"])
    _revoke_health(seeded, ha)
    ht = seeded.get(f"{W.format(cid)}/wstepny/historia", headers=hc).json()["submissions"][0]
    op = next(x for x in ht["answers"] if x["question_id"] == "urazy_opis")
    assert op["hidden"] is True and op["value"] is None
    hk = seeded.get(f"{W.format(cid)}/wstepny/historia", headers=ha).json()["submissions"][0]
    assert next(x for x in hk["answers"] if x["question_id"] == "urazy_opis")["value"] == "bark"


# --- 12. zmiana faktu przy aktywnym planie → zadanie sprawdzenia → blokada publikacji -------------


def test_t12_zmiana_faktu_tworzy_zadanie_i_blokuje_publikacje(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    plan = next(p for p in seeded.get(f"/api/clients/{cid}/plans", headers=hc).json()["plans"]
                if not p["is_template"] and p["status"] == "ACTIVE")
    wersja_przed = plan["current_version_no"]
    w1 = _przeslij_komplet(seeded, ha, cid)
    assert w1["review_tasks"] == []  # pierwsza wersja: nie ma „zmiany”
    r = _patch(seeded, ha, cid, w1["revision"], {"cel_glowny": {"value": "Przygotowanie do półmaratonu"}})
    w2 = _przeslij(seeded, ha, cid, r["revision"])
    assert len(w2["review_tasks"]) >= 1 and "cel_glowny" in w2["changed_facts"]
    zad = seeded.get("/api/wywiady/zadania", headers=hc).json()["tasks"]
    t = next(x for x in zad if x["plan_id"] == plan["id"])
    assert t["changed_facts"] == ["cel"] and t["status"] == "OPEN"
    # Plan aktywny NIE został przepisany.
    plan2 = next(p for p in seeded.get(f"/api/clients/{cid}/plans", headers=hc).json()["plans"] if p["id"] == plan["id"])
    assert plan2["current_version_no"] == wersja_przed
    # Publikacja zależnej wersji zablokowana.
    szkic = seeded.post(f"/api/szkice/plan/training/{plan['id']}", headers=hc).json()
    d = szkic["content"]["days"][0]
    szkic = seeded.patch(f"/api/szkice/{szkic['id']}", headers=hc, json={
        "revision": szkic["revision"], "operations": [{"op": "set", "id": d["exercises"][0]["id"], "fields": {"sets": "6"}}]}).json()
    body = {"revision": szkic["revision"], "base_version_no": szkic["base_version_no"], "note": None}
    r = seeded.post(f"/api/szkice/{szkic['id']}/publikuj", headers=hc, json=body)
    assert r.status_code == 409 and r.json()["code"] == "INTERVIEW_REVIEW_REQUIRED" and t["id"] in r.json()["task_ids"]
    # Rozstrzygnięcie odblokowuje; zadanie widoczne w przeglądzie klienta trenera.
    r = seeded.post(f"/api/wywiady/zadania/{t['id']}/rozstrzygnij", headers=hc, json={"note": "plan pod półmaraton do przebudowy"})
    assert r.status_code == 200 and r.json()["status"] == "RESOLVED"
    r = seeded.post(f"/api/szkice/{szkic['id']}/publikuj", headers=hc, json=body)
    assert r.status_code == 200 and r.json()["published"]
    # Ta sama zmiana faktu ponownie (v3) — nowe zadanie; drugie przesłanie bez zmian faktów — brak zadania.
    r = _patch(seeded, ha, cid, w2["revision"], {"cel_termin": {"value": "2027-04"}})
    w3 = _przeslij(seeded, ha, cid, r["revision"])
    assert w3["review_tasks"]
    with SessionLocal() as db:
        assert db.query(PlanReviewTask).filter_by(plan_id=plan["id"], status="OPEN").count() == 1


# --- 13. podpowiedzi do konfiguratorów: alergie = ograniczenie; brak informacji ≠ zgoda ------------


def test_t13_podpowiedzi_konfiguratorow_z_pochodzeniem(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    r = seeded.get(f"{W.format(cid)}/podpowiedzi", headers=hc).json()
    assert r["available"] is False
    _przeslij_komplet(seeded, ha, cid, alergie={"value": "orzechy laskowe, laktoza"},
                      alergie_status={"value": "Tak, potwierdzoną (lekarz lub badanie)"},
                      nietolerancje={"value": "gluten — wzdęcia"}, wykluczenia_preferencje={"value": "podroby"})
    r = seeded.get(f"{W.format(cid)}/podpowiedzi", headers=hc).json()
    assert r["available"] and set(r["nutrition"]["allergens"]) == {"tree_nuts", "milk"}
    assert r["nutrition"]["intolerances"].startswith("gluten") and r["nutrition"]["exclusions"] == "podroby"
    assert r["training"]["level"] == "beginner" and r["training"]["health"]["injuries_declared"] is False
    assert any(s["question_id"] == "alergie" and s["version_no"] == 1 for s in r["sources"])
    assert r["interview_submission_ids"]["wstepny"]
    # Klient bez informacji o alergiach (pominięcie) → ostrzeżenie, nie „brak alergii”.
    hb = login(seeded, CLIENT_B)
    bid = get_user_id(seeded, hb)
    ans = _komplet_wstepny(seeded, hb, bid)
    ans["alergie_status"] = {"value": "Nie wiem"}
    ans["alergie"] = {"skipped": True}
    rb = _patch(seeded, hb, bid, 1, ans)
    _przeslij(seeded, hb, bid, rb["revision"])
    r = seeded.get(f"{W.format(bid)}/podpowiedzi", headers=hc).json()
    assert r["nutrition"]["allergens"] == [] and r["nutrition"]["allergen_status"] == "Nie wiem"
    # Klient nie ma dostępu do podpowiedzi trenera (COACH only).
    assert seeded.get(f"{W.format(cid)}/podpowiedzi", headers=ha).status_code == 403


# --- 14. dostęp: brak zgody = powód (nie awaria); brak relacji = 404 --------------------------------


def test_t14_brak_dostepu_ma_powod_a_brak_relacji_404(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    # (a) zaproszenie nowego konta: konto PENDING → powód „czeka na aktywację”.
    r = seeded.post("/api/coach/clients", headers=hc, json={"client_name": "Nowa Osoba", "client_email": "nowa@example.com"})
    assert r.status_code == 201, r.text
    nid = r.json()["client_id"]
    o = seeded.get(W.format(nid), headers=hc)
    assert o.status_code == 200 and o.json()["access"]["ok"] is False and "aktywacj" in o.json()["access"]["reason"]
    assert o.json()["wywiady"] == []
    # (b) zaproszenie ISTNIEJĄCEGO konta: zgód nie nadaje trener → powód „zgody”, nie awaria.
    create_user_with_role("istnieje@example.com", "Istnieje#2026!x", "Istniejący", "CLIENT")
    r = seeded.post("/api/coach/clients", headers=hc, json={"client_name": "Istniejący", "client_email": "istnieje@example.com"})
    assert r.status_code == 201, r.text
    iid = r.json()["client_id"]
    o = seeded.get(W.format(iid), headers=hc)
    assert o.status_code == 200 and o.json()["access"]["ok"] is False and "zgód" in o.json()["access"]["reason"]
    # Klient sam widzi swoje formularze i może wypełniać (odpowiedzi nie zależą od dostępu trenera).
    hi = login(seeded, {"email": "istnieje@example.com", "password": "Istnieje#2026!x"})
    assert seeded.get(W.format(iid), headers=hi).json()["access"]["ok"] is True
    # Pozostałe trasy dla tego klienta: odmowa, nie 500.
    assert seeded.get(f"{W.format(nid)}/wstepny/definicja", headers=hc).status_code == 404
    # Trener bez relacji: 404 (jak wszędzie).
    create_user_with_role("obcy@example.com", "ObcyTrener#2026!", "Obcy", "COACH")
    ho = login(seeded, {"email": "obcy@example.com", "password": "ObcyTrener#2026!"})
    assert seeded.get(W.format(cid), headers=ho).status_code == 404
    assert seeded.get(f"{W.format(cid)}/wstepny/historia", headers=ho).status_code == 404
    # Klient B nie zobaczy zgłoszenia klienta A po jego id.
    w = _przeslij_komplet(seeded, ha, cid)
    hb = login(seeded, CLIENT_B)
    assert seeded.get(f"/api/wywiady/zgloszenia/{w['submission_id']}", headers=hb).status_code == 404
    assert seeded.post(f"/api/wywiady/zgloszenia/{w['submission_id']}/przeglad", headers=ho,
                       json={"outcome": "REVIEWED"}).status_code == 404


# --- 15. migracja: syntetyczne sesje → wersje/szkice, ponawialna, bez powiadomień ---------------


def _sesja(db, client_id, flow, status, answers, coach_id=None, started="2026-08-01T10:00:00+00:00"):
    s = OnboardingSession(id=new_id("ONB"), client_id=client_id, flow=flow, status=status,
                          started_at=started, updated_at=started,
                          client_approved_at=started if status in ("CLIENT_APPROVED", "COACH_APPROVED") else None,
                          coach_approved_at=started if status == "COACH_APPROVED" else None,
                          coach_approved_by=coach_id if status == "COACH_APPROVED" else None)
    db.add(s)
    db.flush()
    for i, (step, value) in enumerate(answers.items()):
        db.add(OnboardingAnswer(id=new_id("ONA"), session_id=s.id, step_id=step, topic="t", value=value or "",
                                skipped=value is None, created_at=f"2026-08-01T10:0{i}:00+00:00"))
    return s.id


def test_t15_migracja_ponawialna_bez_powiadomien(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    bid = get_user_id(seeded, hb)
    coach_id = get_user_id(seeded, hc)
    with db_session() as db:
        s_a1 = _sesja(db, cid, "start", "COACH_APPROVED", {"cel_glowny": "Forma", "cel_termin": None}, coach_id)
        s_a2 = _sesja(db, cid, "start", "CLIENT_APPROVED", {"cel_glowny": "Forma 2"}, started="2026-08-05T10:00:00+00:00")
        s_a3 = _sesja(db, cid, "deep", "IN_PROGRESS", {"gw_a1": "Chcę biegać"})
        s_b = _sesja(db, bid, "start", "ABANDONED", {"cel_glowny": "Porzucony cel"})
        _sesja(db, bid, "deep", "SUMMARY_READY", {})  # bez odpowiedzi
    with db_session() as db:
        raport = migracja.migruj(db, wykonaj=True)
    assert raport["utworzone"] == {"wersje": 2, "przeglady": 1, "szkice": 2, "fakty": raport["utworzone"]["fakty"]}
    assert raport["utworzone"]["fakty"] >= 1 and raport["sesje_bez_odpowiedzi"] == 1
    assert raport["po"]["wersje_migrowane"] == 2 and raport["przed"]["wersje_migrowane"] == 0
    assert raport["wysylki"] == 0 and not raport["do_recznej_weryfikacji"]
    # Treści odpowiedzi nie ma w raporcie.
    assert "Forma" not in json.dumps(raport, ensure_ascii=False)
    with SessionLocal() as db:
        subs = db.query(InterviewSubmission).filter_by(client_id=cid, typ="wstepny").order_by(InterviewSubmission.version_no).all()
        assert [s.source_session_id for s in subs] == [s_a1, s_a2] and all(s.migrated for s in subs)
        assert subs[0].submitted_at == "2026-08-01T10:00:00+00:00" and subs[0].submitted_by == cid
        assert json.loads(subs[0].answers_json)["cel_glowny"]["at"] == "2026-08-01T10:00:00+00:00"
        rev = db.query(InterviewReview).all()
        assert len(rev) == 1 and rev[0].submission_id == subs[0].id and rev[0].migrated and rev[0].coach_id == coach_id
        d_a = db.query(InterviewDraft).filter_by(client_id=cid, typ="gleboki").one()
        assert d_a.source_session_id == s_a3 and d_a.collection_mode == "MIGRACJA"
        d_b = db.query(InterviewDraft).filter_by(client_id=bid, typ="wstepny").one()
        assert d_b.source_session_id == s_b
        assert db.query(OutboxEvent).count() == 0 and db.query(Notification).filter_by(category="WYWIAD").count() == 0
        assert db.query(OnboardingSession).count() == 5  # nic nie usunięto
    # Stany po migracji: A wstępny = submitted / not_reviewed (druga wersja bez przeglądu trenera), głęboki = draft.
    assert _stan(seeded, ha, cid)["submission_status"] == "submitted"
    assert _stan(seeded, ha, cid)["review_status"] == "not_reviewed"
    assert _stan(seeded, ha, cid, "gleboki")["submission_status"] == "draft"
    hist = seeded.get(f"{W.format(cid)}/wstepny/historia", headers=hc).json()["submissions"]
    assert hist[0]["migrated"] and hist[0]["review"]["migrated"] and hist[1]["review"] is None
    # Ponowne uruchomienie: nic nie dubluje.
    with db_session() as db:
        r2 = migracja.migruj(db, wykonaj=True)
    assert r2["utworzone"]["wersje"] == 0 and r2["utworzone"]["szkice"] == 0 and r2["pominiete_juz_zmigrowane"] >= 3
    with SessionLocal() as db:
        assert db.query(InterviewSubmission).count() == 2 and db.query(InterviewDraft).count() == 2
    # Tryb raportu nie zapisuje.
    with db_session() as db:
        _sesja(db, bid, "start", "CLIENT_APPROVED", {"cel_glowny": "X"}, started="2026-08-09T10:00:00+00:00")
    with db_session() as db:
        r3 = migracja.migruj(db, wykonaj=False)
    assert r3["tryb"].startswith("raport") and r3["utworzone"]["wersje"] == 1
    with SessionLocal() as db:
        assert db.query(InterviewSubmission).count() == 2
    # Klient bez odpowiedzi ma oba formularze not_started (nic nie tworzymy).
    hn = login(seeded, {"email": "marek.dziczek@example.com", "password": "KlientC#2026!x"})
    nid = get_user_id(seeded, hn)
    assert all(w["submission_status"] == "not_started" for w in seeded.get(W.format(nid), headers=hn).json()["wywiady"])


# --- 16. rozmowa krok po kroku zatwierdzona → wersja w zakładce -------------------------------------


def test_t16_zatwierdzona_rozmowa_startowa_pojawia_sie_jako_wersja(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    assert seeded.post(f"/api/clients/{cid}/onboarding/start", headers=ha).status_code == 201
    assert seeded.post(f"/api/clients/{cid}/onboarding/answer", headers=ha,
                       json={"step_id": "cel_glowny", "value": "Cel z rozmowy", "skipped": False}).status_code == 200
    assert seeded.post(f"/api/clients/{cid}/onboarding/answer", headers=ha,
                       json={"step_id": "cel_termin", "value": "", "skipped": True}).status_code == 200
    assert seeded.post(f"/api/clients/{cid}/onboarding/summary", headers=ha).status_code == 200
    assert seeded.post(f"/api/clients/{cid}/onboarding/approve", headers=ha).status_code == 200
    st = _stan(seeded, hc, cid)
    assert st["submission_status"] == "submitted" and st["last_submission"]["migrated"] is True
    assert st["review_status"] == "not_reviewed"
    assert not _wpisy(seeded, hc)  # zatwierdzenie rozmowy nie dubluje powiadomień
    d = _def(seeded, ha, cid, "gleboki")
    assert d["facts"]["cel_glowny"]["value"] == "Cel z rozmowy"  # kontekst w głębokim
    # Trener zatwierdza w rozmowie → przegląd wersji (z rozmowy), nie sztuczny.
    r = seeded.post(f"/api/clients/{cid}/onboarding/coach-approve", headers=hc, json={"confirmed_fields": []})
    assert r.status_code == 200, r.text
    st = _stan(seeded, hc, cid)
    assert st["review_status"] == "reviewed" and st["last_submission"]["review"]["migrated"] is True


# --- 17. przypomnienie: jawna akcja trenera, jeden wpis dziennie, nie dla wersji przesłanej ----------


def test_t17_przypomnienie_jest_jawne_i_deduplikowane(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    r = seeded.post(f"{W.format(cid)}/gleboki/przypomnij", headers=hc)
    assert r.status_code == 201 and r.json()["sent"] is True
    r2 = seeded.post(f"{W.format(cid)}/gleboki/przypomnij", headers=hc)
    assert r2.status_code == 201 and r2.json()["sent"] is False and r2.json()["deduplicated"]
    kl = _wpisy(seeded, ha)
    assert len(kl) == 1 and "wypełnienie" in kl[0]["title"] and kl[0]["url"] == "/wywiad?typ=gleboki"
    _przeslij_komplet(seeded, ha, cid)
    r3 = seeded.post(f"{W.format(cid)}/wstepny/przypomnij", headers=hc)
    assert r3.status_code == 409 and r3.json()["code"] == "ALREADY_SUBMITTED"
    # Klient nie może „przypominać” sam sobie (COACH only).
    assert seeded.post(f"{W.format(cid)}/wstepny/przypomnij", headers=ha).status_code == 403


# --- 18. outbox: awaria doręczenia → ponowienie bez duplikatu ---------------------------------------


def test_t18_outbox_ponawia_doreczenie_bez_duplikatu(seeded, monkeypatch):
    from dzik_os import notifications as mod_notif
    from dzik_os.publikacja import serwis as pub

    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    oryginal = mod_notif.notify_now

    def awaria(*a, **k):
        raise RuntimeError("awaria doręczenia")

    monkeypatch.setattr(mod_notif, "notify_now", awaria)
    w = _przeslij_komplet(seeded, ha, cid)
    with SessionLocal() as db:
        ev = db.get(OutboxEvent, w["outbox_event_id"])
        assert ev.status == "PENDING" and ev.attempts == 1 and "awaria" in ev.last_error
        assert db.get(InterviewSubmission, w["submission_id"]) is not None  # wersja jest mimo awarii wysyłki
    assert not _wpisy(seeded, hc)
    monkeypatch.setattr(mod_notif, "notify_now", oryginal)
    with SessionLocal() as db:
        n1 = pub.przetworz_outbox(db, now_utc=datetime.now(UTC) + timedelta(hours=1))
        db.commit()
        n2 = pub.przetworz_outbox(db, now_utc=datetime.now(UTC) + timedelta(hours=3))
        db.commit()
        assert len(n1) == 1 and n2 == [] and db.get(OutboxEvent, w["outbox_event_id"]).status == "DELIVERED"
    assert len(_wpisy(seeded, hc)) == 1
    # Powtórka tej samej operacji nie tworzy drugiego zdarzenia (UNIQUE po agregacie).
    with SessionLocal() as db:
        assert db.query(OutboxEvent).filter_by(event_type="INTERVIEW_SUBMITTED", aggregate_id=w["submission_id"]).count() == 1

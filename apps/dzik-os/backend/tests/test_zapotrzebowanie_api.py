"""Wywiad „Zapotrzebowanie kaloryczne” (0.62.0): definicja, walidacja liczb,
wyliczenie przy przesłaniu, filtr flagi zdrowotnej (klient bez liczb),
nadpisanie i odblokowanie przez trenera, flaga instalacji."""

from __future__ import annotations

from conftest import CLIENT_A, COACH, create_user_with_role, get_user_id, login

from dzik_os.config import settings
from dzik_os.dates import local_today
from dzik_os.db import SessionLocal
from dzik_os.models import CalorieEstimate
from dzik_os.wywiad import zapotrzebowanie as Z

W = "/api/clients/{}/wywiady"
TYP = "zapotrzebowanie"


def _def(c, h, cid):
    r = c.get(f"{W.format(cid)}/{TYP}/definicja", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _rev(c, h, cid):
    d = _def(c, h, cid)
    return d["draft"]["revision"] if d["draft"] else 1


def _patch(c, h, cid, answers, expect=200):
    r = c.patch(f"{W.format(cid)}/{TYP}/szkic", headers=h,
                json={"revision": _rev(c, h, cid), "answers": {k: {"value": v} for k, v in answers.items()}})
    assert r.status_code == expect, r.text
    return r.json()


def _przeslij(c, h, cid, expect=201):
    r = c.post(f"{W.format(cid)}/{TYP}/przeslij", headers=h, json={"revision": _rev(c, h, cid)})
    assert r.status_code == expect, r.text
    return r.json()


KOMPLET = {
    "zk_plec": Z.PLEC_K, "zk_wiek": "30", "zk_wzrost": "170", "zk_masa": "70",
    "zk_praca": "Siedząca (biuro, auto, nauka)", "zk_treningi": "3–4 treningi w tygodniu",
    "zk_cel": Z.CEL_UTRZYMANIE, "zk_zaburzenia": "Nie zgłaszam",
}


def _klucze(obj, acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(k)
            _klucze(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _klucze(v, acc)
    return acc


def _liczby(obj, acc=None):
    acc = [] if acc is None else acc
    if isinstance(obj, dict):
        for v in obj.values():
            _liczby(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _liczby(v, acc)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        acc.append(obj)
    return acc


def test_definicja_trzeciego_typu_i_walidacja_liczb(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    d = _def(seeded, ha, cid)
    assert d["typ"] == TYP and d["sections"][0]["key"] == "zk_dane"
    masa = next(q for q in d["questions"] if q["question_id"] == "zk_masa")
    assert masa["type"] == "NUMBER" and masa["range"] == [30, 300]
    # Tempo jest warunkowe: nieaktywne, dopóki cel nie wskaże kierunku.
    assert not next(q for q in d["questions"] if q["question_id"] == "zk_tempo_redukcja")["active"]
    r = _patch(seeded, ha, cid, {"zk_masa": "abc", "zk_wzrost": "999", "zk_wiek": "72,5"})
    assert "liczbę" in r["errors"]["zk_masa"] and "zakresem" in r["errors"]["zk_wzrost"]
    assert "zk_wiek" not in r["errors"]
    # Redukcja bez tempa = brak wymagany przy przesłaniu.
    _patch(seeded, ha, cid, {**KOMPLET, "zk_cel": Z.CEL_REDUKCJA})
    r = _przeslij(seeded, ha, cid, expect=422)
    assert "zk_tempo_redukcja" in r["missing"]


def test_przeslanie_liczy_wynik_widoczny_dla_klienta_i_trenera(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    r = _patch(seeded, ha, cid, KOMPLET)
    assert r["errors"] == {}
    sub = _przeslij(seeded, ha, cid)
    assert sub["safety_flag"] is False
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()
    assert k["status"] == "ok" and k["estimate"]["kcal"] == 1960 and k["estimate"]["ppm"] == 1452
    assert k["estimate"]["podstawienie"][0].startswith("PPM (Mifflin-St Jeor, kobieta)")
    assert "history" not in k
    t = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    assert t["status"] == "ok" and t["estimate"]["kcal_effective"] == 1960 and t["estimate"]["override"] is None
    assert t["history"] == [{"version_no": 1, "kcal": 1960, "kcal_effective": 1960, "override_kcal": None,
                             "created_at": t["estimate"]["created_at"]}]
    # Druga wersja (nowa masa) = nowy szacunek; historia rośnie.
    _patch(seeded, ha, cid, {**KOMPLET, "zk_masa": "68,5"})
    _przeslij(seeded, ha, cid)
    t2 = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    assert t2["estimate"]["version_no"] == 2 and t2["estimate"]["inputs"]["masa_kg"] == 68.5
    assert len(t2["history"]) == 2


def test_flaga_zdrowotna_klient_nie_dostaje_zadnej_liczby(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    # Opcja z przecinkiem w treści („Tak, obecnie lub w przeszłości”) też ustawia flagę.
    _patch(seeded, ha, cid, {**KOMPLET, "zk_zaburzenia": "Tak, obecnie lub w przeszłości"})
    assert _przeslij(seeded, ha, cid)["safety_flag"] is True
    _patch(seeded, ha, cid, {**KOMPLET, "zk_zaburzenia": "Wolę omówić z trenerem"})
    assert _przeslij(seeded, ha, cid)["safety_flag"] is True
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()
    assert k["status"] == "hidden" and k["estimate"] is None and "omówi" in k["message"]
    # Żadnego klucza z liczbą (kcal, ppm, masa…) na żadnym poziomie odpowiedzi.
    assert not ({"kcal", "kcal_effective", "ppm", "cpm", "pal", "masa_kg", "inputs", "podstawienie"} & _klucze(k))
    assert _liczby(k) == [2]  # wyłącznie numer wersji
    t = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hc).json()
    assert t["status"] == "ok" and t["estimate"]["hidden_for_client"] is True and t["estimate"]["kcal"] == 1960
    assert t["estimate"]["version_no"] == 2
    # Trener po rozmowie odsłania — klient widzi liczby.
    r = seeded.post(f"/api/clients/{cid}/zapotrzebowanie/odblokuj", headers=hc)
    assert r.status_code == 200 and r.json()["estimate"]["hidden_for_client"] is False
    k2 = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()
    assert k2["status"] == "ok" and k2["estimate"]["kcal"] == 1960 and k2["estimate"]["unhidden_at"]
    # Klient nie może sam odblokować ani nadpisać.
    assert seeded.post(f"/api/clients/{cid}/zapotrzebowanie/odblokuj", headers=ha).status_code == 403
    assert seeded.put(f"/api/clients/{cid}/zapotrzebowanie/nadpisanie", headers=ha,
                      json={"kcal": 1800, "reason": "x"}).status_code == 403


def test_nadpisanie_trenera_z_powodem_i_cofniecie(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_cel": Z.CEL_REDUKCJA, "zk_tempo_redukcja": "Umiarkowane (−15 %)"})
    _przeslij(seeded, ha, cid)
    url = f"/api/clients/{cid}/zapotrzebowanie/nadpisanie"
    assert seeded.put(url, headers=hc, json={"kcal": 100, "reason": "za mało"}).status_code == 422
    assert seeded.put(url, headers=hc, json={"kcal": 1800, "reason": ""}).status_code == 422
    r = seeded.put(url, headers=hc, json={"kcal": 1800, "reason": "Start łagodniej — pierwszy tydzień."})
    assert r.status_code == 200, r.text
    e = r.json()["estimate"]
    assert e["kcal"] == 1670 and e["kcal_effective"] == 1800 and e["override"]["reason"].startswith("Start")
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()["estimate"]
    assert k["kcal_effective"] == 1800 and k["override"]["reason"].startswith("Start")
    r = seeded.put(url, headers=hc, json={"kcal": None, "reason": "wracamy do wzoru"})
    assert r.json()["estimate"]["override"] is None and r.json()["estimate"]["kcal_effective"] == 1670
    # Obcy trener: 404 (bez ujawniania istnienia).
    create_user_with_role("obcy.trener@example.com", "ObcyTrener#2026!", "Obcy", "COACH")
    ho = login(seeded, {"email": "obcy.trener@example.com", "password": "ObcyTrener#2026!"})
    assert seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ho).status_code == 404
    assert seeded.put(url, headers=ho, json={"kcal": 1800, "reason": "x"}).status_code == 404


def test_bez_zgody_zdrowotnej_pytanie_znika_a_wynik_jest_jawny(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    health = next(x for x in consents if x["revoked_at"] is None and x["category"] == "dane_zdrowotne")
    assert seeded.post(f"/api/me/consents/{health['id']}/revoke", headers=ha).status_code == 200
    d = _def(seeded, ha, cid)
    assert not next(q for q in d["questions"] if q["question_id"] == "zk_zaburzenia")["active"]
    _patch(seeded, ha, cid, {k: v for k, v in KOMPLET.items() if k != "zk_zaburzenia"})
    assert _przeslij(seeded, ha, cid)["safety_flag"] is False
    assert seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).json()["status"] == "ok"


def test_placeholder_masy_z_ostatniego_pomiaru(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    r = seeded.post(f"/api/clients/{cid}/measurements", headers=ha,
                    json={"kind": "weight", "value": 71.3, "unit": "kg", "measured_at": local_today().isoformat()})
    assert r.status_code in (200, 201), r.text
    d = _def(seeded, ha, cid)
    assert next(q for q in d["questions"] if q["question_id"] == "zk_masa")["placeholder"] == "ostatni pomiar: 71,3 kg"


def test_flaga_instalacji_wylacza_typ_i_trase(seeded, monkeypatch):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    assert seeded.get("/api/health").json()["features"]["calorie_interview"] is True
    monkeypatch.setattr(settings, "calorie_interview_enabled", False)
    assert seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=ha).status_code == 404
    assert seeded.get(f"{W.format(cid)}/{TYP}/definicja", headers=ha).status_code == 404
    typy = [w["typ"] for w in seeded.get(W.format(cid), headers=ha).json()["wywiady"]]
    assert typy == ["wstepny", "gleboki"]
    assert seeded.get("/api/health").json()["features"]["calorie_interview"] is False


def test_number_odrzuca_notacje_i_normalizuje_zapis(seeded):
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    r = _patch(seeded, ha, cid, {"zk_masa": "1e2", "zk_wzrost": "1_80", "zk_wiek": "٣٠"})
    assert set(r["errors"]) == {"zk_masa", "zk_wzrost", "zk_wiek"}
    r = _patch(seeded, ha, cid, {"zk_masa": "72.5", "zk_wzrost": "1 80"})
    assert r["errors"] == {}
    odp = {a["question_id"]: a["value"] for a in _def(seeded, ha, cid)["answers"]}
    assert odp["zk_masa"] == "72,5" and odp["zk_wzrost"] == "180"


def test_eksport_danych_zawiera_szacunki_takze_ukryte(seeded):
    """Prawo dostępu (RODO) ma pierwszeństwo przed ukryciem w aplikacji: eksport
    zawiera pełne wiersze, także gdy wynik jest ukryty przed klientem w UI."""
    ha = login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, {**KOMPLET, "zk_zaburzenia": "Nie wiem"})
    _przeslij(seeded, ha, cid)
    r = seeded.get("/api/me/export", headers=ha)
    assert r.status_code == 200, r.text
    rows = r.json()["calorie_estimates"]
    assert len(rows) == 1 and rows[0]["kcal"] == 1960 and rows[0]["hidden_for_client"] is True
    assert r.json()["export_version"] == "2.1"  # 2.1 = po dołożeniu pól cardio w dzienniku (0.73.0)


def test_flaga_wylaczona_ukrywa_istniejace_przeslania_trenerowi(seeded, monkeypatch):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    _patch(seeded, ha, cid, KOMPLET)
    sid = _przeslij(seeded, ha, cid)["submission_id"]
    assert seeded.get(f"/api/wywiady/zgloszenia/{sid}", headers=hc).status_code == 200
    monkeypatch.setattr(settings, "calorie_interview_enabled", False)
    assert seeded.get(f"/api/wywiady/zgloszenia/{sid}", headers=hc).status_code == 404
    lista = seeded.get("/api/coach/wywiady/do-przegladu", headers=hc).json()
    typy = {p["typ"] for k in lista["clients"] for p in k["wywiady"]}
    assert TYP not in typy


def test_trener_bez_przeslania_404_odblokowanie_noop_i_wygasanie_nadpisania(seeded):
    ha, hc = login(seeded, CLIENT_A), login(seeded, COACH)
    cid = get_user_id(seeded, ha)
    url = f"/api/clients/{cid}/zapotrzebowanie"
    # Przed przesłaniem: nie ma czego nadpisywać ani odsłaniać.
    assert seeded.put(f"{url}/nadpisanie", headers=hc, json={"kcal": 1800, "reason": "x"}).status_code == 404
    assert seeded.post(f"{url}/odblokuj", headers=hc).status_code == 404
    _patch(seeded, ha, cid, KOMPLET)
    _przeslij(seeded, ha, cid)
    # Odblokowanie wyniku, który nie jest ukryty = no-op bez śladu.
    r = seeded.post(f"{url}/odblokuj", headers=hc)
    assert r.status_code == 200 and r.json()["estimate"]["unhidden_at"] is None
    # Cofnięcie nadpisania, którego nie było = no-op.
    assert seeded.put(f"{url}/nadpisanie", headers=hc, json={"kcal": None, "reason": "nic"}).json()["estimate"]["override"] is None
    # Nadpisanie dotyczy wersji: nowa wersja wywiadu = wynik ze wzoru, poprzednie ustalenie w historii.
    seeded.put(f"{url}/nadpisanie", headers=hc, json={"kcal": 1800, "reason": "łagodniej"})
    _patch(seeded, ha, cid, {**KOMPLET, "zk_masa": "69"})
    _przeslij(seeded, ha, cid)
    t = seeded.get(url, headers=hc).json()
    assert t["estimate"]["version_no"] == 2 and t["estimate"]["override"] is None
    assert [h["override_kcal"] for h in t["history"]] == [None, 1800]
    # Eksport ma nadpisanie z v1; usunięcie konta kasuje szacunki.
    ex = seeded.get("/api/me/export", headers=ha).json()["calorie_estimates"]
    assert sorted((e["version_no"], e["override_kcal"]) for e in ex) == [(1, 1800), (2, None)]
    r = seeded.post("/api/me/deletion-request", headers=ha,
                    json={"password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE"})
    assert r.status_code in (200, 202), r.text
    with SessionLocal() as db:
        assert db.query(CalorieEstimate).filter_by(client_id=cid).count() == 0


def test_komunikat_ukrycia_bez_trenera(seeded):
    """Klient bez trenera widzi komunikat, który mówi, co dalej."""
    create_user_with_role("sam.klient@example.com", "SamKlient#2026!", "Sam", "CLIENT")
    hs = login(seeded, {"email": "sam.klient@example.com", "password": "SamKlient#2026!"})
    cid = get_user_id(seeded, hs)
    d = _def(seeded, hs, cid)
    aktywne = {q["question_id"] for q in d["questions"] if q["active"]}
    _patch(seeded, hs, cid, {k: v for k, v in KOMPLET.items() if k in aktywne} | ({"zk_zaburzenia": "Nie wiem"} if "zk_zaburzenia" in aktywne else {}))
    sub = _przeslij(seeded, hs, cid)
    k = seeded.get(f"/api/clients/{cid}/zapotrzebowanie", headers=hs).json()
    if sub["safety_flag"]:
        assert k["status"] == "hidden" and "nawiążesz współpracę" in k["message"]
    else:
        assert k["status"] == "ok"  # bez zgody zdrowotnej pytanie nie pada — wynik jawny

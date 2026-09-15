"""Bloki rozgrzewki/cardio/rozciągania (0.73.0, CARDIO od 0.76.0): CRUD trenera,
`load-builtin` idempotentny (seed już załadował 21 bloków → 0 nowych), cudzy blok = 404,
klient → 403, archiwizacja nie psuje planu (migawka w wersji), `exercise_id`
spoza bazy → 422."""

from __future__ import annotations

from conftest import CLIENT_A, COACH, create_user_with_role, get_user_id, login

BLOKI = "/api/coach/exercise-blocks"


def test_seed_ma_21_wbudowanych_i_load_builtin_jest_idempotentny(seeded):
    hc = login(seeded, COACH)
    lista = seeded.get(BLOKI, headers=hc).json()
    assert len(lista["items"]) == 21
    assert sum(1 for b in lista["items"] if b["kind"] == "WARMUP") == 9
    assert sum(1 for b in lista["items"] if b["kind"] == "CARDIO") == 9
    assert sum(1 for b in lista["items"] if b["kind"] == "STRETCH") == 3
    assert all(b["source"].startswith("wbudowany") for b in lista["items"])
    r = seeded.post(f"{BLOKI}/load-builtin", headers=hc)
    assert r.status_code == 200 and r.json()["created"] == 0 and r.json()["skipped"] == 21
    assert len(seeded.get(BLOKI, headers=hc).json()["items"]) == 21
    # Pozycje z katalogu mają link do karty; „seria wprowadzająca” nie.
    blok = next(b for b in lista["items"] if b["kind"] == "WARMUP" and b["variant"] == "C" and b["level"] == "POCZATKUJACY")
    assert blok["items"][0]["exercise_id"] and blok["items"][-1]["exercise_id"] is None
    assert lista["dictionaries"]["variants"]["C"] == "całe ciało"


def test_load_builtin_u_nowego_trenera_bez_bazy_cwiczen(client):
    create_user_with_role("nowy.trener@example.com", "NowyTrener#2026", "Nowy", "COACH")
    h = login(client, {"email": "nowy.trener@example.com", "password": "NowyTrener#2026"})
    r = client.post(f"{BLOKI}/load-builtin", headers=h)
    assert r.status_code == 200 and r.json()["created"] == 21 and r.json()["items_without_card"] > 0
    r = client.post(f"{BLOKI}/load-builtin", headers=h)
    assert r.json()["created"] == 0 and r.json()["skipped"] == 21


def test_crud_wlasnosc_i_archiwizacja(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    body = {"name": "Moja rozgrzewka", "kind": "WARMUP", "level": "POCZATKUJACY", "variant": "G",
            "duration_min": 7, "items": [{"name": "Krążenia ramion", "dose": "2×10"}, {"name": "Marsz", "dose": "3 min"}]}
    r = seeded.post(BLOKI, headers=hc, json=body)
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    assert r.json()["source"] == "trener" and r.json()["items"][0]["exercise_id"] is None
    # Rozciąganie nie ma poziomu — poziom jest zerowany.
    r = seeded.put(f"{BLOKI}/{bid}", headers=hc, json={**body, "kind": "STRETCH", "level": "ZAAWANSOWANY"})
    assert r.status_code == 200 and r.json()["level"] is None and r.json()["kind"] == "STRETCH"
    # Obce `exercise_id` → 422.
    r = seeded.put(f"{BLOKI}/{bid}", headers=hc, json={**body, "items": [{"name": "x", "exercise_id": "HOS-EXC-000000000000"}]})
    assert r.status_code == 422
    # Klient nie ma dostępu; obcy trener nie widzi bloku.
    assert seeded.get(f"{BLOKI}/{bid}", headers=ha).status_code == 403
    create_user_with_role("obcy.trener@example.com", "ObcyTrener#2026", "Obcy", "COACH")
    ho = login(seeded, {"email": "obcy.trener@example.com", "password": "ObcyTrener#2026"})
    assert seeded.get(f"{BLOKI}/{bid}", headers=ho).status_code == 404
    assert seeded.put(f"{BLOKI}/{bid}", headers=ho, json=body).status_code == 404
    assert seeded.post(f"{BLOKI}/{bid}/status", headers=ho, json={"status": "ARCHIVED"}).status_code == 404
    # Archiwizacja ≠ kasowanie.
    r = seeded.post(f"{BLOKI}/{bid}/status", headers=hc, json={"status": "ARCHIVED"})
    assert r.status_code == 200 and r.json()["status"] == "ARCHIVED"
    assert bid not in {b["id"] for b in seeded.get(BLOKI, headers=hc).json()["items"]}
    assert bid in {b["id"] for b in seeded.get(f"{BLOKI}?status=all", headers=hc).json()["items"]}


def test_archiwizacja_bloku_nie_psuje_planu_z_migawka(seeded):
    hc, ha = login(seeded, COACH), login(seeded, CLIENT_A)
    cid = get_user_id(seeded, ha)
    plans = seeded.get(f"/api/clients/{cid}/plans", headers=ha).json()["plans"]
    plan = next(p for p in plans if p["status"] == "ACTIVE")
    dzien_c = plan["current_version"]["content"]["days"][2]
    blok = dzien_c["exercises"][0]
    assert blok["kind"] == "warmup_block" and blok["block"]["items"] and blok["block_id"]
    r = seeded.post(f"{BLOKI}/{blok['block_id']}/status", headers=hc, json={"status": "ARCHIVED"})
    assert r.status_code == 200
    plan2 = next(p for p in seeded.get(f"/api/clients/{cid}/plans", headers=ha).json()["plans"] if p["id"] == plan["id"])
    assert plan2["current_version"]["content"]["days"][2]["exercises"][0]["block"] == blok["block"]
    # Nowa wersja z tą samą migawką nadal przechodzi (block_id miękkie).
    r = seeded.post(f"/api/plans/{plan['id']}/versions", headers=hc,
                    json={"reason": "Ta sama rozgrzewka", "days": plan2["current_version"]["content"]["days"]})
    assert r.status_code == 201, r.text

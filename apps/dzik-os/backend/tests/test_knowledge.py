"""Baza wiedzy: broadcast do aktywnych klientów trenera, CRUD po stronie
trenera, izolacja między trenerami."""

from conftest import CLIENT_A, COACH, create_user_with_role, login


def test_client_sees_seeded_knowledge_grouped_and_pinned(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/me/knowledge", headers=ha)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 5
    assert items[0]["pinned"] is True  # przypięte na górze


def test_coach_creates_edits_and_archives_item(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/knowledge", headers=hc, json={
        "title": "Test artykułu", "category": "Trening",
        "body": "Treść testowa", "pinned": False,
    })
    assert r.status_code == 201
    item_id = r.json()["id"]

    r = seeded.put(f"/api/coach/knowledge/{item_id}", headers=hc, json={
        "title": "Test artykułu (edycja)", "category": "Trening",
        "body": "Zaktualizowana treść", "pinned": True,
    })
    assert r.status_code == 200
    assert r.json()["title"] == "Test artykułu (edycja)"
    assert r.json()["pinned"] is True

    items = seeded.get("/api/coach/knowledge", headers=hc).json()["items"]
    assert any(i["id"] == item_id and i["body"] == "Zaktualizowana treść" for i in items)

    r = seeded.post(f"/api/coach/knowledge/{item_id}/status?status=ARCHIVED", headers=hc)
    assert r.status_code == 200

    ha = login(seeded, CLIENT_A)
    client_items = seeded.get("/api/me/knowledge", headers=ha).json()["items"]
    assert all(i["id"] != item_id for i in client_items)  # zarchiwizowane znika u klienta


def test_other_coach_cannot_edit_or_see_in_own_list(seeded):
    hc = login(seeded, COACH)
    r = seeded.post("/api/coach/knowledge", headers=hc, json={"title": "Prywatne", "category": "Inne"})
    item_id = r.json()["id"]

    create_user_with_role("obcy3@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy3@example.com", "password": "ObcyTrener#26"})

    r = seeded.put(f"/api/coach/knowledge/{item_id}", headers=h2, json={"title": "Hack", "category": "Inne"})
    assert r.status_code == 404
    own_list = seeded.get("/api/coach/knowledge", headers=h2).json()["items"]
    assert all(i["id"] != item_id for i in own_list)


def test_client_only_sees_own_coachs_content(seeded):
    hc = login(seeded, COACH)
    seeded.post("/api/coach/knowledge", headers=hc, json={"title": "Od Dzika", "category": "Inne"})

    create_user_with_role("inny.trener@example.com", "InnyTrener#26", "Inny Trener", "COACH")
    h2 = login(seeded, {"email": "inny.trener@example.com", "password": "InnyTrener#26"})
    seeded.post("/api/coach/knowledge", headers=h2, json={"title": "Od Innego", "category": "Inne"})

    ha = login(seeded, CLIENT_A)
    items = seeded.get("/api/me/knowledge", headers=ha).json()["items"]
    assert any(i["title"] == "Od Dzika" for i in items)
    assert all(i["title"] != "Od Innego" for i in items)


def test_client_cannot_manage_knowledge(seeded):
    ha = login(seeded, CLIENT_A)
    r = seeded.post("/api/coach/knowledge", headers=ha, json={"title": "x", "category": "Inne"})
    assert r.status_code == 403


def test_unrelated_client_sees_empty_list(seeded):
    """Klient bez aktywnej relacji z żadnym trenerem nie widzi treści."""
    from dzik_os.db import db_session
    from dzik_os.models import RoleGrant, User, new_id
    from dzik_os.security import hash_password

    with db_session() as db:
        lone = User(id=new_id("USR"), email="samotny@example.com",
                    password_hash=hash_password("Samotny#2026x"),
                    display_name="Samotny Klient", identity_id=new_id("ID"))
        db.add(lone)
        db.add(RoleGrant(id=new_id("ROL"), user_id=lone.id, role="CLIENT",
                         scope="self", issued_by="test"))

    h = login(seeded, {"email": "samotny@example.com", "password": "Samotny#2026x"})
    items = seeded.get("/api/me/knowledge", headers=h).json()["items"]
    assert items == []

"""Kopiowanie szablonu planu do klienta — kopia niezależna (pełna
proweniencja), dostęp wyłącznie dla właściciela szablonu z relacją."""

import json

from conftest import CLIENT_A, COACH, create_user_with_role, login


def _template_id(seeded, hc) -> str:
    templates = seeded.get("/api/plans/templates", headers=hc).json()["templates"]
    return next(t["id"] for t in templates if t["title"] == "Szablon: Push/Pull/Legs")


def _client_id(seeded, hc) -> str:
    clients = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    return next(c["client_id"] for c in clients if c["email"] == CLIENT_A["email"])


def test_copy_template_creates_independent_plan(seeded):
    hc = login(seeded, COACH)
    template_id = _template_id(seeded, hc)
    client_id = _client_id(seeded, hc)

    r = seeded.post(f"/api/plans/{template_id}/copy-to/{client_id}", headers=hc)
    assert r.status_code == 201
    plan_id = r.json()["id"]
    assert r.json()["version_no"] == 1

    plans = seeded.get(f"/api/clients/{client_id}/plans", headers=hc).json()["plans"]
    copied = next(p for p in plans if p["id"] == plan_id)
    assert copied["title"] == "Szablon: Push/Pull/Legs"
    assert copied["is_template"] is False
    assert "Skopiowano z szablonu" in copied["current_version"]["reason"]
    days = copied["current_version"]["content"]["days"]
    assert [d["name"] for d in days] == ["Push", "Pull", "Legs"]

    # Kopia jest niezależna: nowa wersja szablonu nie zmienia planu klienta.
    r = seeded.post(f"/api/plans/{template_id}/versions", headers=hc, json={
        "reason": "Zmiana szablonu po skopiowaniu",
        "days": [{"name": "Nowy dzień", "exercises": []}],
    })
    assert r.status_code == 201
    plans = seeded.get(f"/api/clients/{client_id}/plans", headers=hc).json()["plans"]
    copied = next(p for p in plans if p["id"] == plan_id)
    assert [d["name"] for d in copied["current_version"]["content"]["days"]] == [
        "Push", "Pull", "Legs"
    ]
    assert json.loads(json.dumps(copied))  # sanity: serializowalne


def test_copy_rejects_non_template_and_foreign_coach(seeded):
    hc = login(seeded, COACH)
    client_id = _client_id(seeded, hc)
    # Zwykły plan klienta nie jest szablonem — nie można go "skopiować".
    plans = seeded.get(f"/api/clients/{client_id}/plans", headers=hc).json()["plans"]
    r = seeded.post(f"/api/plans/{plans[0]['id']}/copy-to/{client_id}", headers=hc)
    assert r.status_code == 404

    # Obcy trener nie widzi cudzego szablonu ani klienta.
    template_id = _template_id(seeded, hc)
    create_user_with_role("obcy.tpl@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.tpl@example.com", "password": "ObcyTrener#26"})
    r = seeded.post(f"/api/plans/{template_id}/copy-to/{client_id}", headers=h2)
    assert r.status_code == 404


def test_client_cannot_copy_templates(seeded):
    hc = login(seeded, COACH)
    template_id = _template_id(seeded, hc)
    ha = login(seeded, CLIENT_A)
    client_id = _client_id(seeded, hc)
    r = seeded.post(f"/api/plans/{template_id}/copy-to/{client_id}", headers=ha)
    assert r.status_code == 403

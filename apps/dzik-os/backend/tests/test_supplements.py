"""Suplementacja jako część wersjonowanego planu diety.

Zasady, których pilnują te testy:
- suplement bez celu, dawki, pory albo PODSTAWY zalecenia nie wchodzi do planu
  (system nie przechowuje nagiej nazwy preparatu bez proweniencji),
- zmiana suplementacji to nowa WERSJA planu — poprzednia zostaje w historii,
- audyt notuje fakt zmiany i liczbę pozycji, nigdy nazwy preparatów,
- przypomnienia powstają z planu (dawka z planu, nie z przepisania ręcznego),
  są idempotentne i nie da się ich zrobić dla cudzego klienta.
"""

from conftest import CLIENT_A, CLIENT_B, COACH, get_user_id, login


def _plan(client, headers, client_id):
    plans = client.get(f"/api/clients/{client_id}/nutrition", headers=headers).json()["plans"]
    return plans[0]


def _supplement(**over):
    body = {
        "name": "Magnez", "dose": "200 mg", "timing": "wieczorem",
        "purpose": "Skurcze łydek po treningach",
        "source": "Zalecenie trenera po rozmowie o objawach",
    }
    body.update(over)
    return body


def test_supplement_requires_dose_purpose_and_source(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    plan = _plan(seeded, hc, id_a)
    for missing in ("dose", "purpose", "source", "timing", "name"):
        entry = _supplement()
        entry.pop(missing)
        r = seeded.post(f"/api/nutrition/{plan['id']}/versions", headers=hc, json={
            "reason": "Próba niekompletnego wpisu", "supplements": [entry],
        })
        assert r.status_code == 422, missing


def test_new_version_keeps_previous_supplementation_in_history(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    plan = _plan(seeded, hc, id_a)
    before = plan["current_version"]["content"]["supplements"]
    assert before, "seed demo powinien zawierać suplementację"

    r = seeded.post(f"/api/nutrition/{plan['id']}/versions", headers=hc, json={
        "reason": "Odstawienie kreatyny na prośbę klienta",
        "supplements": [_supplement()],
    })
    assert r.status_code == 201
    new_no = r.json()["version_no"]

    versions = seeded.get(f"/api/nutrition/{plan['id']}/versions", headers=hc).json()["versions"]
    old = next(v for v in versions if v["version_no"] == plan["current_version_no"])
    new = next(v for v in versions if v["version_no"] == new_no)
    # Historia nie jest przepisywana: stara wersja zachowuje swój skład.
    assert old["content"]["supplements"] == before
    assert [s["name"] for s in new["content"]["supplements"]] == ["Magnez"]

    # Klient widzi bieżącą wersję z pełnym opisem zalecenia.
    current = _plan(seeded, ha, id_a)["current_version"]["content"]["supplements"]
    assert current[0]["source"]
    assert current[0]["purpose"]


def test_audit_records_change_without_supplement_names(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    plan = _plan(seeded, hc, id_a)
    seeded.post(f"/api/nutrition/{plan['id']}/versions", headers=hc, json={
        "reason": "Nowa suplementacja", "supplements": [_supplement()],
    })
    from dzik_os.hos_bridge import event_store

    events = [e for e in event_store().all() if e["event_type"] == "NUTRITION_VERSION_CREATED"]
    assert events
    blob = str(events[-1])
    assert "supplements_count" in blob
    assert "Magnez" not in blob


def test_reminders_come_from_plan_and_are_idempotent(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    plan = _plan(seeded, hc, id_a)
    seeded.post(f"/api/nutrition/{plan['id']}/versions", headers=hc, json={
        "reason": "Suplementacja do przypomnień", "supplements": [_supplement()],
    })
    payload = {"entries": [{"name": "Magnez", "time_of_day": "21:00"}]}
    r = seeded.post(f"/api/nutrition/{plan['id']}/supplements/reminders",
                    headers=hc, json=payload)
    assert r.status_code == 201 and r.json()["created"] == 1
    # Ponowne kliknięcie nie mnoży przypomnień.
    again = seeded.post(f"/api/nutrition/{plan['id']}/supplements/reminders",
                        headers=hc, json=payload)
    assert again.json() == {"created": 0, "skipped": 1, "item_ids": []}

    items = seeded.get(f"/api/clients/{id_a}/schedule", headers=ha).json()["items"]
    added = [i for i in items if i["name"] == "Magnez"]
    assert len(added) == 1
    # Dawka i pora w przypomnieniu pochodzą z planu, nie z ręcznego wpisu.
    assert "200 mg" in added[0]["instruction"]
    assert added[0]["category"] == "SUPLEMENT"
    assert added[0]["author_note"]  # podstawa zalecenia zachowana


def test_reminder_for_unknown_supplement_is_rejected(seeded):
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, login(seeded, CLIENT_A))
    plan = _plan(seeded, hc, id_a)
    r = seeded.post(f"/api/nutrition/{plan['id']}/supplements/reminders", headers=hc, json={
        "entries": [{"name": "Preparat spoza planu", "time_of_day": "08:00"}],
    })
    assert r.status_code == 422


def test_client_cannot_edit_supplementation_and_foreign_plan_is_hidden(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    plan = _plan(seeded, hc, id_a)
    # Klient nie dopisuje sobie suplementów (rola).
    assert seeded.post(f"/api/nutrition/{plan['id']}/versions", headers=ha, json={
        "reason": "Sam sobie dopiszę", "supplements": [_supplement()],
    }).status_code == 403
    # Cudzy plan nie istnieje z punktu widzenia innego klienta.
    assert seeded.get(f"/api/nutrition/{plan['id']}/versions", headers=hb).status_code == 404
    assert seeded.post(f"/api/nutrition/{plan['id']}/supplements/reminders",
                       headers=hb, json={"entries": [
                           {"name": "Magnez", "time_of_day": "08:00"}]}).status_code == 403

"""Testy wspólnych wyzwań (moduł prywatny, tylko-zaproszeni).

Pokrycie wg specyfikacji: zaproszenie, odmowa, opuszczenie, ukrycie
wyniku, brak dostępu osoby z zewnątrz (404), korekta danych, strefa
czasowa wyzwania, zakończenie wyzwania, blokada uczestnika, wycofanie
udziału — plus zasady konstytucyjne (ranking opt-in domyślnie wyłączony,
neutralne jednostki, brak danych zdrowotnych w audycie i push).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from conftest import create_activated_client, create_user_with_role, login


def _world(client):
    """Minimalny świat: trener + dwóch aktywowanych klientów + outsider
    (klient bez relacji z trenerem). Bez seedu demo — szybciej."""
    create_user_with_role("wyzw.trener@example.com", "Trener#2026!xy", "Trener Dzik", "COACH")
    hc = login(client, {"email": "wyzw.trener@example.com", "password": "Trener#2026!xy"})
    a_id = create_activated_client(client, hc, "wyzw.a@example.com", name="Ala")
    b_id = create_activated_client(client, hc, "wyzw.b@example.com", name="Bartek")
    outsider_id = create_user_with_role(
        "wyzw.obcy@example.com", "Obcy#2026!xyz", "Obcy Klient", "CLIENT")
    ha = login(client, {"email": "wyzw.a@example.com", "password": "WlasneHaslo#123"})
    hb = login(client, {"email": "wyzw.b@example.com", "password": "WlasneHaslo#123"})
    ho = login(client, {"email": "wyzw.obcy@example.com", "password": "Obcy#2026!xyz"})
    return hc, (a_id, ha), (b_id, hb), (outsider_id, ho)


def _dates(days_back=7, days_fwd=7, tz="Europe/Warsaw"):
    today = datetime.now(UTC).astimezone(ZoneInfo(tz)).date()
    return ((today - timedelta(days=days_back)).isoformat(),
            (today + timedelta(days=days_fwd)).isoformat())


def _mk(client, hc, *, unit="minuty", goal=100, status_active=True, tz=None, **over):
    starts, ends = _dates(tz=tz or "Europe/Warsaw")
    body = {
        "title": "Wspólne wyzwanie ruchu", "description": "Zasady: ruszamy się.",
        "unit": unit, "goal_value": goal, "starts_on": starts, "ends_on": ends,
    }
    if tz:
        body["timezone"] = tz
    body.update(over)
    r = client.post("/api/coach/challenges", headers=hc, json=body)
    assert r.status_code == 201, r.text
    ch = r.json()
    if status_active:
        assert client.post(
            f"/api/challenges/{ch['id']}/activate", headers=hc
        ).status_code == 200
    return ch


def _invite(client, hc, ch_id, ids):
    r = client.post(f"/api/challenges/{ch_id}/invite", headers=hc,
                    json={"client_ids": ids})
    assert r.status_code == 200, r.text
    return r.json()


def _join(client, h, ch_id, **opts):
    r = client.post(f"/api/challenges/{ch_id}/join", json=opts, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _entry(client, h, ch_id, **body):
    return client.post(f"/api/challenges/{ch_id}/entries", json=body, headers=h)


def _add_workout(client_id: str, performed_on: str, status: str = "DONE") -> str:
    from dzik_os.db import db_session
    from dzik_os.models import WorkoutSession, new_id

    with db_session() as db:
        s = WorkoutSession(
            id=new_id("WKS"), client_id=client_id, plan_version_id="TEST-PLV",
            day_index=0, performed_on=performed_on, status=status,
        )
        db.add(s)
        db.flush()
        return s.id


def _events():
    from dzik_os.hos_bridge import event_store

    return event_store().all()


# ---------------------------------------------------------------------------


def test_invitation_accept_flow_and_defaults(client):
    hc, (a_id, ha), _b, _o = _world(client)
    ch = _mk(client, hc)
    assert ch["visibility"] == "INVITE_ONLY"
    assert _invite(client, hc, ch["id"], [a_id])["invited_count"] == 1

    lst = client.get("/api/me/challenges", headers=ha).json()
    assert len(lst["invitations"]) == 1
    inv = lst["invitations"][0]
    # Pkt 12: przed dołączeniem czytelne wyjaśnienie, kto zobaczy jaki wynik.
    assert "Kto zobaczy Twój wynik" in inv["explainer"]

    # Zaproszony widzi wyłącznie zapowiedź (bez grupy/uczestników).
    detail = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert detail["me"]["status"] == "INVITED"
    assert "group" not in detail and "shared" not in detail

    me = _join(client, ha, ch["id"], alias="Dzika Ala")["me"]
    # Konstytucja: ranking i widoczność wyniku DOMYŚLNIE wyłączone.
    assert me["share_result"] is False
    assert me["ranking_opt_in"] is False
    assert me["alias"] == "Dzika Ala"

    detail = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert detail["me"]["progress"]["value"] == 0
    assert detail["group"]["active_participants"] == 1
    assert detail["ranking"] == []
    types = [e["event_type"] for e in _events()]
    assert "CHALLENGE_CREATED" in types
    assert "CHALLENGE_INVITED" in types
    assert "CHALLENGE_JOINED" in types


def test_decline_invitation(client):
    hc, (a_id, ha), _b, _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id])
    r = client.post(f"/api/challenges/{ch['id']}/decline", headers=ha)
    assert r.status_code == 200
    # Po odmowie brak dostępu do szczegółów (i brak na liście).
    assert client.get(f"/api/challenges/{ch['id']}", headers=ha).status_code == 404
    lst = client.get("/api/me/challenges", headers=ha).json()
    assert lst["invitations"] == [] and lst["challenges"] == []
    # Ponowne przyjęcie nie działa (zaproszenie skonsumowane).
    assert client.post(f"/api/challenges/{ch['id']}/join", json={}, headers=ha).status_code == 422


def test_outsider_gets_404_everywhere(client):
    hc, (a_id, ha), _b, (o_id, ho) = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"])
    # Osoba z zewnątrz: szczegóły, wpisy, dołączenie, blokady — zawsze 404.
    assert client.get(f"/api/challenges/{ch['id']}", headers=ho).status_code == 404
    assert _entry(client, ho, ch["id"], value=10).status_code == 404
    assert client.post(f"/api/challenges/{ch['id']}/join", json={}, headers=ho).status_code == 404
    # Obcy trener nie jest organizatorem: moderacja i zaproszenia = 404.
    create_user_with_role("wyzw.trener2@example.com", "Trener2#2026!x", "Inny Trener", "COACH")
    h2 = login(client, {"email": "wyzw.trener2@example.com", "password": "Trener2#2026!x"})
    assert client.get(f"/api/challenges/{ch['id']}/reports", headers=h2).status_code == 404
    assert client.post(
        f"/api/challenges/{ch['id']}/invite", headers=h2, json={"client_ids": [a_id]}
    ).status_code == 404
    # Trener nie może zaprosić NIE swojego klienta do własnego wyzwania.
    ch2 = _mk(client, hc)
    assert client.post(
        f"/api/challenges/{ch2['id']}/invite", headers=hc, json={"client_ids": [o_id]}
    ).status_code == 404


def test_hidden_result_and_optin_sharing(client):
    hc, (a_id, ha), (b_id, hb), _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id, b_id])
    _join(client, ha, ch["id"], alias="Dzika Ala")
    _join(client, hb, ch["id"])
    _entry(client, ha, ch["id"], value=30)
    _entry(client, hb, ch["id"], value=20)

    # Domyślnie: nikt nie widzi wyniku nikogo; agregat grupy bez nazwisk.
    d = client.get(f"/api/challenges/{ch['id']}", headers=hb).json()
    assert d["shared"] == [] and d["ranking"] == []
    assert d["group"]["active_participants"] == 2
    assert d["group"]["total_value"] == 50.0
    # Własny postęp zawsze widoczny dla siebie.
    assert d["me"]["progress"]["value"] == 20.0

    # Ala świadomie udostępnia wynik (bez rankingu).
    client.patch(f"/api/challenges/{ch['id']}/me", headers=ha,
                 json={"share_result": True})
    d = client.get(f"/api/challenges/{ch['id']}", headers=hb).json()
    assert [s["alias"] for s in d["shared"]] == ["Dzika Ala"]
    assert d["shared"][0]["value"] == 30.0
    assert d["ranking"] == []  # ranking to OSOBNA, świadoma decyzja

    # Ukrycie działa natychmiast.
    client.patch(f"/api/challenges/{ch['id']}/me", headers=ha,
                 json={"share_result": False})
    assert client.get(f"/api/challenges/{ch['id']}", headers=hb).json()["shared"] == []

    # Organizator też nie widzi ukrytych wyników jednostkowych.
    d = client.get(f"/api/challenges/{ch['id']}", headers=hc).json()
    assert d["shared"] == []
    assert {p["status"] for p in d["participants"]} == {"ACTIVE"}


def test_ranking_only_for_double_optin(client):
    hc, (a_id, ha), (b_id, hb), _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id, b_id])
    _join(client, ha, ch["id"], alias="Ala", share_result=True, ranking_opt_in=True)
    _join(client, hb, ch["id"], alias="Bartek", share_result=True)  # bez rankingu
    _entry(client, ha, ch["id"], value=10)
    _entry(client, hb, ch["id"], value=90)
    d = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    # Bartek udostępnia wynik, ale NIE wszedł do rankingu — ranking
    # obejmuje wyłącznie osoby z podwójnym opt-in.
    assert len(d["shared"]) == 2
    assert [r["alias"] for r in d["ranking"]] == ["Ala"]
    assert d["ranking"][0]["position"] == 1


def test_leave_challenge(client):
    hc, (a_id, ha), (b_id, hb), _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id, b_id])
    _join(client, ha, ch["id"])
    _join(client, hb, ch["id"])
    _entry(client, ha, ch["id"], value=30)
    assert client.post(f"/api/challenges/{ch['id']}/leave", headers=ha).status_code == 200
    # Po opuszczeniu: brak dostępu, agregat bez tej osoby.
    assert client.get(f"/api/challenges/{ch['id']}", headers=ha).status_code == 404
    d = client.get(f"/api/challenges/{ch['id']}", headers=hb).json()
    assert d["group"]["active_participants"] == 1
    assert d["group"]["total_value"] == 0.0


def test_withdraw_removes_results_and_flags_aggregates(client):
    hc, (a_id, ha), (b_id, hb), _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id, b_id])
    _join(client, ha, ch["id"])
    _join(client, hb, ch["id"])
    _entry(client, ha, ch["id"], value=40)
    _entry(client, hb, ch["id"], value=10)
    r = client.post(f"/api/challenges/{ch['id']}/withdraw", headers=ha)
    assert r.status_code == 200
    assert r.json()["entries_deleted"] == 1
    d = client.get(f"/api/challenges/{ch['id']}", headers=hb).json()
    # Wyniki wycofanej osoby ZNIKAJĄ, agregat jawnie oznaczony jako
    # skorygowany (integralność przez audyt, nie trzymanie danych osoby).
    assert d["group"]["total_value"] == 10.0
    assert d["group"]["aggregates_adjusted"] is True
    assert d["aggregates_adjusted"] is True
    ev = [e for e in _events() if e["event_type"] == "CHALLENGE_WITHDRAWN"]
    assert ev and ev[-1]["payload"]["entries_deleted"] == 1
    # W bazie nie ma już wpisów wycofanego uczestnika.
    from dzik_os.db import db_session
    from dzik_os.models import ChallengeEntry, ChallengeParticipant

    with db_session() as db:
        part = db.query(ChallengeParticipant).filter_by(
            challenge_id=ch["id"], user_id=a_id).one()
        assert part.status == "WITHDRAWN" and part.alias is None
        assert db.query(ChallengeEntry).filter_by(participant_id=part.id).count() == 0


def test_entry_validation_and_limits(client):
    hc, (a_id, ha), _b, _o = _world(client)
    # Jednostka spoza allowlisty (dane zdrowotne) — odmowa już przy tworzeniu.
    starts, ends = _dates()
    r = client.post("/api/coach/challenges", headers=hc, json={
        "title": "Zrzucamy wagę", "unit": "kg", "goal_value": 5,
        "starts_on": starts, "ends_on": ends,
    })
    assert r.status_code == 422
    assert "masa ciała" in r.json()["detail"] or "jednostka" in r.json()["detail"].lower()

    ch = _mk(client, hc, unit="minuty", goal=100, max_entries_per_day=2)
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"])
    # Zakres wartości.
    assert _entry(client, ha, ch["id"], value=100000).status_code == 422
    assert _entry(client, ha, ch["id"], value=-5).status_code == 422
    # Data w przyszłości / poza oknem.
    future = (datetime.now(UTC) + timedelta(days=2)).date().isoformat()
    assert _entry(client, ha, ch["id"], value=10, entry_date=future).status_code == 422
    before = (datetime.now(UTC) - timedelta(days=30)).date().isoformat()
    assert _entry(client, ha, ch["id"], value=10, entry_date=before).status_code == 422
    # Limit wpisów na dzień.
    assert _entry(client, ha, ch["id"], value=10).status_code == 201
    assert _entry(client, ha, ch["id"], value=10).status_code == 201
    assert _entry(client, ha, ch["id"], value=10).status_code == 422


def test_entry_idempotency_client_entry_id(client):
    hc, (a_id, ha), _b, _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"])
    r1 = _entry(client, ha, ch["id"], value=15, client_entry_id="abc-1")
    assert r1.status_code == 201
    r2 = _entry(client, ha, ch["id"], value=15, client_entry_id="abc-1")
    assert r2.status_code == 201 and r2.json()["duplicate"] is True
    assert r2.json()["id"] == r1.json()["id"]
    d = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert d["me"]["progress"]["value"] == 15.0


def test_workout_designation_no_double_counting(client):
    hc, (a_id, ha), (b_id, hb), _o = _world(client)
    ch = _mk(client, hc, unit="treningi", goal=10)
    _invite(client, hc, ch["id"], [a_id, b_id])
    _join(client, ha, ch["id"])
    _join(client, hb, ch["id"])
    today = datetime.now(UTC).astimezone(ZoneInfo("Europe/Warsaw")).date().isoformat()
    ws = _add_workout(a_id, today)
    r = _entry(client, ha, ch["id"], workout_session_id=ws)
    assert r.status_code == 201
    assert r.json()["value"] == 1.0 and r.json()["source"] == "WORKOUT"
    # Ten sam trening drugi raz → brak podwójnego naliczania.
    r2 = _entry(client, ha, ch["id"], workout_session_id=ws)
    assert r2.json()["duplicate"] is True
    d = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert d["me"]["progress"]["value"] == 1.0
    # Cudzy trening → 404 (IDOR).
    assert _entry(client, hb, ch["id"], workout_session_id=ws).status_code == 404


def test_auto_count_workouts_consent_and_conflicts(client):
    hc, (a_id, ha), _b, _o = _world(client)
    ch = _mk(client, hc, unit="treningi", goal=10)
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"], auto_count_workouts=True)
    warsaw_today = datetime.now(UTC).astimezone(ZoneInfo("Europe/Warsaw")).date()
    d1 = warsaw_today.isoformat()
    d0 = (warsaw_today - timedelta(days=1)).isoformat()
    _add_workout(a_id, d1)
    _add_workout(a_id, d1)  # drugi trening tego samego dnia — liczy się raz
    _add_workout(a_id, d0)
    _add_workout(a_id, d0, status="SKIPPED")  # pominięty się nie liczy
    d = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert d["me"]["progress"]["value"] == 2.0
    # Przy włączonym auto: wpis ręczny i wskazywanie treningu = jawny konflikt.
    assert _entry(client, ha, ch["id"], value=1).status_code == 409
    ws = _add_workout(a_id, d1)
    assert _entry(client, ha, ch["id"], workout_session_id=ws).status_code == 409
    # Auto tylko dla jednostki "treningi".
    ch2 = _mk(client, hc, unit="minuty")
    _invite(client, hc, ch2["id"], [a_id])
    r = client.post(f"/api/challenges/{ch2['id']}/join", headers=ha,
                    json={"auto_count_workouts": True})
    assert r.status_code == 422


def test_correction_keeps_history(client):
    hc, (a_id, ha), _b, _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"])
    e = _entry(client, ha, ch["id"], value=30).json()
    r = client.post(f"/api/challenges/{ch['id']}/entries/{e['id']}/correct",
                    headers=ha, json={"value": 45})
    assert r.status_code == 200
    new = r.json()
    assert new["corrects_entry_id"] == e["id"]
    # Postęp liczy nową wartość; historia zawiera oba wiersze.
    d = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert d["me"]["progress"]["value"] == 45.0
    hist = client.get(f"/api/challenges/{ch['id']}/entries", headers=ha).json()["entries"]
    statuses = {x["id"]: x["status"] for x in hist}
    assert statuses[e["id"]] == "CORRECTED" and statuses[new["id"]] == "ACTIVE"
    # Skorygowanego wpisu nie można korygować drugi raz (łańcuch, nie fork).
    assert client.post(f"/api/challenges/{ch['id']}/entries/{e['id']}/correct",
                       headers=ha, json={"value": 60}).status_code == 422
    ev = [x for x in _events() if x["event_type"] == "CHALLENGE_ENTRY_CORRECTED"]
    assert ev and ev[-1]["payload"]["old_value"] == 30.0


def test_challenge_timezone_controls_day(client):
    hc, (a_id, ha), _b, _o = _world(client)
    # Strefa wyzwania daleko na zachód (UTC-12): jej "dzisiaj" bywa
    # wcześniejsze niż data w Warszawie — wpis z datą przyszłą WEDŁUG
    # STREFY WYZWANIA jest odrzucany, nawet jeśli w Warszawie ten dzień
    # już trwa.
    tz_west = "Etc/GMT+12"
    west_today = datetime.now(UTC).astimezone(ZoneInfo(tz_west)).date()
    warsaw_today = datetime.now(UTC).astimezone(ZoneInfo("Europe/Warsaw")).date()
    ch = _mk(client, hc, tz=tz_west)
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"])
    # Dzień strefy wyzwania — zawsze OK.
    assert _entry(client, ha, ch["id"], value=10,
                  entry_date=west_today.isoformat()).status_code == 201
    if warsaw_today > west_today:
        # Data warszawska jest w strefie wyzwania przyszłością.
        assert _entry(client, ha, ch["id"], value=10,
                      entry_date=warsaw_today.isoformat()).status_code == 422
    # Wpis bez daty dostaje dzień wg strefy WYZWANIA.
    r = _entry(client, ha, ch["id"], value=5)
    assert r.json()["entry_date"] == west_today.isoformat()


def test_finish_freezes_entries_and_corrections(client):
    hc, (a_id, ha), _b, _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"])
    e = _entry(client, ha, ch["id"], value=10).json()
    assert client.post(f"/api/challenges/{ch['id']}/finish", headers=hc).status_code == 200
    assert _entry(client, ha, ch["id"], value=10).status_code == 422
    assert client.post(f"/api/challenges/{ch['id']}/entries/{e['id']}/correct",
                       headers=ha, json={"value": 20}).status_code == 422
    # Wyniki i podsumowanie pozostają widoczne po zakończeniu.
    d = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert d["status"] == "FINISHED"
    assert d["me"]["progress"]["value"] == 10.0
    # Zakończyć może tylko organizator.
    assert client.post(f"/api/challenges/{ch['id']}/finish", headers=ha).status_code == 404


def test_block_hides_both_directions(client):
    hc, (a_id, ha), (b_id, hb), _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id, b_id])
    _join(client, ha, ch["id"], alias="Ala", share_result=True)
    _join(client, hb, ch["id"], alias="Bartek", share_result=True)
    _entry(client, ha, ch["id"], value=10)
    _entry(client, hb, ch["id"], value=20)
    r = client.post(f"/api/challenges/{ch['id']}/block", headers=hb,
                    json={"user_id": a_id})
    assert r.status_code == 200
    # Blokada działa w obie strony; każdy nadal widzi siebie.
    d_b = client.get(f"/api/challenges/{ch['id']}", headers=hb).json()
    assert [s["alias"] for s in d_b["shared"]] == ["Bartek"]
    d_a = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert [s["alias"] for s in d_a["shared"]] == ["Ala"]
    # Agregat grupy bez zmian.
    assert d_a["group"]["total_value"] == 30.0
    # Odblokowanie przywraca widoczność.
    client.post(f"/api/challenges/{ch['id']}/unblock", headers=hb,
                json={"user_id": a_id})
    d_b = client.get(f"/api/challenges/{ch['id']}", headers=hb).json()
    assert len(d_b["shared"]) == 2


def test_report_and_moderation(client):
    hc, (a_id, ha), (b_id, hb), _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id, b_id])
    _join(client, ha, ch["id"], alias="Niedozwolony Alias", share_result=True)
    _join(client, hb, ch["id"])
    r = client.post(f"/api/challenges/{ch['id']}/report", headers=hb,
                    json={"user_id": a_id, "reason": "Obraźliwy pseudonim"})
    assert r.status_code == 201
    reports = client.get(f"/api/challenges/{ch['id']}/reports", headers=hc).json()["reports"]
    assert len(reports) == 1 and reports[0]["status"] == "OPEN"
    rid = reports[0]["id"]
    # Rozstrzygnięcie: neutralizacja pseudonimu.
    assert client.post(f"/api/challenges/{ch['id']}/reports/{rid}/resolve",
                       headers=hc, json={"resolution": "ALIAS_RESET"}).status_code == 200
    d = client.get(f"/api/challenges/{ch['id']}", headers=hb).json()
    assert [s["alias"] for s in d["shared"]] == ["Uczestnik"]
    # Ponowne rozstrzygnięcie → 422; audyt bez treści zgłoszenia.
    assert client.post(f"/api/challenges/{ch['id']}/reports/{rid}/resolve",
                       headers=hc, json={"resolution": "DISMISSED"}).status_code == 422
    ev = [e for e in _events() if e["event_type"] in
          ("CHALLENGE_REPORTED", "CHALLENGE_REPORT_RESOLVED")]
    for e in ev:
        assert "Obraźliwy" not in str(e["payload"]) and "Alias" not in str(e["payload"])
    # Moderacja bezpośrednia: usunięcie uczestnika przez organizatora.
    d = client.get(f"/api/challenges/{ch['id']}", headers=hc).json()
    pid = next(p["participant_id"] for p in d["participants"] if p["user_id"] == a_id)
    assert client.post(f"/api/challenges/{ch['id']}/participants/{pid}/remove",
                       headers=hc).status_code == 200
    assert client.get(f"/api/challenges/{ch['id']}", headers=ha).status_code == 404


def test_individual_challenge_private(client):
    hc, (_a_id, ha), (_b_id, hb), _o = _world(client)
    starts, ends = _dates()
    r = client.post("/api/me/challenges", headers=ha, json={
        "title": "Moje 100 minut", "unit": "minuty", "goal_value": 100,
        "starts_on": starts, "ends_on": ends,
    })
    assert r.status_code == 201
    ch = r.json()
    assert ch["kind"] == "INDIVIDUAL" and ch["status"] == "ACTIVE"
    assert _entry(client, ha, ch["id"], value=40).status_code == 201
    d = client.get(f"/api/challenges/{ch['id']}", headers=ha).json()
    assert d["me"]["progress"]["value"] == 40.0
    assert d["me"]["progress"]["progress_pct"] == 40.0
    # Nikt inny nie widzi wyzwania indywidualnego — nawet trener.
    assert client.get(f"/api/challenges/{ch['id']}", headers=hb).status_code == 404
    assert client.get(f"/api/challenges/{ch['id']}", headers=hc).status_code == 404
    # Właściciel może je zakończyć (jest organizatorem).
    assert client.post(f"/api/challenges/{ch['id']}/finish", headers=ha).status_code == 200


def test_push_is_neutral_no_content(client, monkeypatch):
    """Powiadomienia z wyzwań nigdy nie niosą tytułu wyzwania, aliasów ani
    wyników — wyłącznie neutralne wezwanie do aplikacji."""
    sent = []

    from dzik_os.routers import challenges as mod

    monkeypatch.setattr(
        mod.push_service, "send_to_user",
        lambda db, uid, title, body, url="/": sent.append((uid, title, body, url)) or 1,
    )
    hc, (a_id, ha), _b, _o = _world(client)
    ch = _mk(client, hc, title="Sekretne wyzwanie klubu")
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"], alias="Sekretny Alias")
    client.post(f"/api/challenges/{ch['id']}/finish", headers=hc)
    assert sent, "zaproszenie i zakończenie powinny wysłać push"
    for _uid, title, body, _url in sent:
        assert "Sekretne" not in title and "Sekretne" not in body
        assert "Alias" not in body
    # Audyt: żadnych aliasów w payloadach zdarzeń wyzwań.
    for e in _events():
        if e["event_type"].startswith("CHALLENGE_"):
            assert "Sekretny Alias" not in str(e["payload"])


def test_deletion_withdraws_challenges(client):
    """Usunięcie konta = trwałe wycofanie ze wszystkich wyzwań (wpisy
    usunięte, pseudonim zanonimizowany, agregaty oznaczone)."""
    hc, (a_id, ha), (b_id, hb), _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id, b_id])
    _join(client, ha, ch["id"], alias="Dzika Ala", share_result=True)
    _join(client, hb, ch["id"])
    _entry(client, ha, ch["id"], value=25)
    r = client.post("/api/me/deletion-request", headers=ha,
                    json={"password": "WlasneHaslo#123", "confirm": "USUŃ MOJE DANE"})
    assert r.status_code == 200, r.text
    d = client.get(f"/api/challenges/{ch['id']}", headers=hb).json()
    assert d["group"]["total_value"] == 0.0
    assert d["group"]["aggregates_adjusted"] is True
    assert d["shared"] == []
    from dzik_os.db import db_session
    from dzik_os.models import ChallengeParticipant

    with db_session() as db:
        part = db.query(ChallengeParticipant).filter_by(
            challenge_id=ch["id"], user_id=a_id).one()
        assert part.status == "WITHDRAWN" and part.alias is None


def test_export_contains_challenge_data(client):
    hc, (a_id, ha), _b, _o = _world(client)
    ch = _mk(client, hc)
    _invite(client, hc, ch["id"], [a_id])
    _join(client, ha, ch["id"])
    _entry(client, ha, ch["id"], value=12)
    export = client.get("/api/me/export", headers=ha).json()
    assert len(export["challenge_participations"]) == 1
    assert len(export["challenge_entries"]) == 1
    assert export["challenge_entries"][0]["value"] == 12.0

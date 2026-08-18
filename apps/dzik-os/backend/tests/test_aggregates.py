"""Warstwa agregacji widoków zbiorczych trenera (aggregates.py).

Dwa rodzaje gwarancji:
1. POPRAWNOŚĆ — flagi i zakresy zgód liczone zbiorczo są identyczne z
   wyliczeniem pojedynczym (ścieżka przez Core), więc optymalizacja nie
   zmieniła semantyki.
2. BUDŻET ZAPYTAŃ — liczba zapytań SQL nie rośnie z liczbą podopiecznych;
   test broni przed powrotem N+1, które symulacja wykryła w panelu trenera.
"""

from conftest import COACH, login
from sqlalchemy import event

from dzik_os import aggregates
from dzik_os import simulate as sim
from dzik_os.authz import (
    DOMAIN_COLLABORATION,
    DOMAIN_HEALTH,
    DOMAIN_TRAINING,
    coach_can_access_client,
)
from dzik_os.dates import local_today
from dzik_os.db import db_session, engine
from dzik_os.models import CoachClientRelationship, User


class QueryCounter:
    """Liczy zapytania SQL wykonane w bloku."""

    def __enter__(self):
        self.count = 0
        event.listen(engine, "before_cursor_execute", self._bump)
        return self

    def _bump(self, *args):
        self.count += 1

    def __exit__(self, *exc):
        event.remove(engine, "before_cursor_execute", self._bump)


def _coach_and_clients():
    with db_session() as db:
        coach = db.query(User).filter(User.email == COACH["email"]).one()
        rels = (
            db.query(CoachClientRelationship)
            .filter(CoachClientRelationship.coach_id == coach.id)
            .all()
        )
        return coach.id, [r.client_id for r in rels]


def test_bulk_flags_match_single_client_computation(seeded):
    """Flagi zbiorcze == flagi liczone dla pojedynczego podopiecznego."""
    coach_id, client_ids = _coach_and_clients()
    today = local_today()
    with db_session() as db:
        bulk = aggregates.client_flags_bulk(db, coach_id, client_ids, today)
        for client_id in client_ids:
            single = aggregates.client_flags_bulk(db, coach_id, [client_id], today)
            assert bulk[client_id] == single[client_id], client_id


def test_bulk_consent_scopes_match_core_decision(seeded):
    """Zbiorcza hydratacja rejestru daje ten sam wynik, co pojedyncze
    zapytanie o zgodę przez Core (hos_engine.ConsentRegistry)."""
    coach_id, client_ids = _coach_and_clients()
    with db_session() as db:
        scopes = aggregates.consent_scopes_bulk(
            db, coach_id, client_ids, domains=aggregates.CONSENT_SCOPE_DOMAINS
        )
        for client_id in client_ids:
            for key, domain in (
                ("collaboration", DOMAIN_COLLABORATION),
                ("training", DOMAIN_TRAINING),
                ("health", DOMAIN_HEALTH),
            ):
                expected = coach_can_access_client(db, coach_id, client_id, domain=domain)
                assert scopes[client_id][key] == expected, (client_id, key)


def test_revoked_consent_is_respected_in_bulk(seeded):
    """Cofnięta zgoda natychmiast znika z zakresu zbiorczego — optymalizacja
    nie może utrwalać nieaktualnych uprawnień."""
    coach_id, client_ids = _coach_and_clients()
    client_id = client_ids[0]
    with db_session() as db:
        before = aggregates.consent_scopes_bulk(
            db, coach_id, [client_id], domains=aggregates.CONSENT_SCOPE_DOMAINS
        )
        assert before[client_id]["health"] is True

        from dzik_os.hos_bridge import ConsentService
        from dzik_os.models import ConsentRecord

        rows = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.subject_id == client_id,
                ConsentRecord.revoked_at.is_(None),
                ConsentRecord.denied_at.is_(None),
            )
            .all()
        )
        for row in rows:
            ConsentService.revoke(db, consent_id=row.id, subject_id=client_id)
        db.commit()

        after = aggregates.consent_scopes_bulk(
            db, coach_id, [client_id], domains=aggregates.CONSENT_SCOPE_DOMAINS
        )
        assert after[client_id]["health"] is False


def test_query_budget_flat_regardless_of_client_count(seeded):
    """Budżet zapytań panelu trenera nie rośnie z liczbą podopiecznych.

    To test regresyjny przeciw N+1: przed wprowadzeniem warstwy agregacji
    dashboard kosztował ~8 zapytań na każdego podopiecznego (88 przy
    dziesięciu), a lista klientów ~184.
    """
    sim.simulate(n_clients=6, weeks=1)
    headers = login(seeded, COACH)

    with QueryCounter() as q_small:
        assert seeded.get("/api/coach/dashboard", headers=headers).status_code == 200
    dashboard_queries = q_small.count

    with QueryCounter() as q_list:
        assert seeded.get("/api/coach/clients", headers=headers).status_code == 200
    list_queries = q_list.count

    # Stała liczba zapytań (z zapasem na sesję/autoryzację); gdyby wróciła
    # pętla per klient, przy 11 podopiecznych progi zostałyby przekroczone.
    assert dashboard_queries <= 25, f"dashboard: {dashboard_queries} zapytań"
    assert list_queries <= 25, f"lista klientów: {list_queries} zapytań"


def test_dashboard_and_list_still_report_real_state(seeded):
    """Optymalizacja nie zgubiła danych: panel nadal widzi podopiecznych
    i ich flagi operacyjne."""
    headers = login(seeded, COACH)
    listing = seeded.get("/api/coach/clients", headers=headers).json()["clients"]
    assert listing
    for row in listing:
        assert set(row["consent_scopes"]) == set(aggregates.CONSENT_SCOPE_DOMAINS)
        assert set(row["flags"]) == {
            "checkin_overdue", "awaiting_review", "payment_overdue",
            "unread_messages", "recent_pain_reports", "flagged_observations",
        }
    dashboard = seeded.get("/api/coach/dashboard", headers=headers).json()
    assert dashboard["active_clients"] == sum(
        1 for r in listing if r["relationship_status"] == "ACTIVE"
    )


def test_workouts_and_threads_query_budget(seeded):
    """Lista treningów i lista wątków też mają stały budżet zapytań.

    Wcześniej każda sesja treningowa kosztowała osobne zapytanie o wpisy
    (koszt rósł z historią klienta), a każdy wątek — cztery zapytania.
    """
    sim.simulate(n_clients=3, weeks=4)
    coach_headers = login(seeded, COACH)
    _coach_id, client_ids = _coach_and_clients()
    client_id = client_ids[0]

    with QueryCounter() as q_workouts:
        r = seeded.get(f"/api/clients/{client_id}/workouts", headers=coach_headers)
    assert r.status_code == 200
    assert q_workouts.count <= 20, f"treningi: {q_workouts.count} zapytań"

    with QueryCounter() as q_threads:
        r = seeded.get("/api/threads", headers=coach_headers)
    assert r.status_code == 200
    assert q_threads.count <= 20, f"wątki: {q_threads.count} zapytań"


def test_thread_list_still_hides_clients_without_consent(seeded):
    """Bramka zgód na liście wątków działa po optymalizacji: cofnięcie zgody
    usuwa wątek z listy trenera (podgląd ostatniej wiadomości nie wycieka)."""
    coach_headers = login(seeded, COACH)
    before = seeded.get("/api/threads", headers=coach_headers).json()["threads"]
    assert before

    _coach_id, client_ids = _coach_and_clients()
    victim = client_ids[0]
    with db_session() as db:
        from dzik_os.hos_bridge import ConsentService
        from dzik_os.models import ConsentRecord

        for row in (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.subject_id == victim,
                ConsentRecord.revoked_at.is_(None),
                ConsentRecord.denied_at.is_(None),
            )
            .all()
        ):
            ConsentService.revoke(db, consent_id=row.id, subject_id=victim)
        db.commit()

    after = seeded.get("/api/threads", headers=coach_headers).json()["threads"]
    assert len(after) < len(before)

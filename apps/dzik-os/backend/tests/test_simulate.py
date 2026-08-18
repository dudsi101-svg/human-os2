"""Symulacja obciążeniowa (simulate.py) — narzędzie diagnostyczne.

Test sprawdza mały przebieg (2 podopiecznych, 2 tygodnie): dane powstają we
wszystkich sekcjach, są spójne i widoczne przez API, a łańcuch audytu
pozostaje weryfikowalny.
"""

from conftest import login

from dzik_os import simulate as sim
from dzik_os.hos_bridge import verify_audit_chain


def test_simulation_fills_every_section(seeded):
    """Symulacja dokłada podopiecznych z historią w każdej sekcji."""
    stats = sim.simulate(n_clients=2, weeks=2)

    # Każda sekcja dostała dane (klucze statystyk = sekcje aplikacji).
    for section in ("sesje_treningowe", "wpisy_treningowe", "raporty", "pomiary",
                    "dziennik_kaloryczny", "adherencja", "harmonogram", "wiadomosci",
                    "platnosci", "zgody", "dokumenty", "zdjecia_progresu",
                    "obserwacje", "wersje_planu", "wersje_diety", "konsultacje"):
        assert stats.get(section, 0) > 0, f"sekcja bez danych: {section}"

    # Łańcuch audytu nadal spójny po masowym zapisie.
    assert verify_audit_chain() is True


def test_simulated_client_sees_own_data_through_api(seeded):
    """Konto z symulacji loguje się i widzi własne dane przez API."""
    sim.simulate(n_clients=1, weeks=2)
    headers = login(seeded, {"email": sim.PERSONAS[0]["email"], "password": sim.SIM_PASSWORD})
    me = seeded.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    client_id = me.json()["id"]

    for path in (f"/api/clients/{client_id}/plans",
                 f"/api/clients/{client_id}/checkins",
                 f"/api/clients/{client_id}/measurements",
                 f"/api/clients/{client_id}/workouts",
                 f"/api/clients/{client_id}/schedule"):
        assert seeded.get(path, headers=headers).status_code == 200, path

    # Eksport (prawo do przenoszenia danych) obejmuje dane z symulacji.
    export = seeded.get("/api/me/export", headers=headers)
    assert export.status_code == 200
    assert export.json()["measurements"]


def test_simulation_is_idempotent(seeded):
    """Powtórny przebieg na tej samej bazie nie wywraca się ani nie duplikuje
    kont — narzędzie diagnostyczne bywa uruchamiane wielokrotnie."""
    first = sim.simulate(n_clients=1, weeks=2)
    assert first["uzytkownicy"] >= 1

    second = sim.simulate(n_clients=1, weeks=2)
    assert second.get("pominieto_istniejacych") == 1
    assert "sesje_treningowe" not in second  # brak nowej historii dla istniejącego konta
    assert verify_audit_chain() is True

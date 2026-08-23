"""Narzędzia pilotażu (`dzik_os/bootstrap.py`, `dzik_os/purge_demo.py`).

Testy pilnują dwóch pułapek, które te narzędzia mają zamykać:

* po wyłączeniu seeda NIE MA innej drogi do konta COACH/ADMIN — bootstrap
  musi działać na pustej bazie i odmawiać na zajętej (nadpisanie kont
  na działającej produkcji byłoby katastrofą);
* konta demo mają hasła w publicznym repo — purge musi je unieważniać,
  ale nigdy nie może zostawić bazy bez żadnego aktywnego trenera.
"""

import pytest
from conftest import COACH, login

from dzik_os.bootstrap import bootstrap
from dzik_os.purge_demo import DEMO_EMAILS, purge_demo

PRAWDZIWY_TRENER = "trener@przyklad-pilotazu.pl"
PRAWDZIWY_ADMIN = "admin@przyklad-pilotazu.pl"
HASLO = "PilotazDzika#2026!"


def test_bootstrap_creates_first_accounts_and_login_works(client):
    wynik = bootstrap(PRAWDZIWY_TRENER, HASLO, PRAWDZIWY_ADMIN, HASLO,
                      coach_name="Trener Pilotażu")
    assert set(wynik) == {PRAWDZIWY_TRENER, PRAWDZIWY_ADMIN}
    r = client.post("/api/auth/login",
                    json={"email": PRAWDZIWY_TRENER, "password": HASLO})
    assert r.status_code == 200, r.text
    # Hasło startowe jest jednorazowe — konto ma wymuszoną zmianę.
    from dzik_os.db import db_session
    from dzik_os.models import User

    with db_session() as db:
        user = db.query(User).filter(User.email == PRAWDZIWY_TRENER).one()
        assert user.must_change_password is True


def test_bootstrap_refuses_on_non_empty_base(seeded):
    with pytest.raises(ValueError, match="istnieje już konto"):
        bootstrap(PRAWDZIWY_TRENER, HASLO, PRAWDZIWY_ADMIN, HASLO)


def test_bootstrap_refuses_weak_password_and_same_emails(client):
    with pytest.raises(ValueError, match="mniej niż"):
        bootstrap(PRAWDZIWY_TRENER, "krotkie", PRAWDZIWY_ADMIN, HASLO)
    with pytest.raises(ValueError, match="różne adresy"):
        bootstrap(PRAWDZIWY_TRENER, HASLO, PRAWDZIWY_TRENER, HASLO)


def test_purge_refuses_to_lock_everyone_out(seeded):
    """Na bazie, gdzie jedynym trenerem jest demo, purge bez --force
    odmawia — inaczej nikt nie mógłby się zalogować."""
    with pytest.raises(ValueError, match="żaden aktywny trener"):
        purge_demo()


def test_purge_disables_demo_after_real_coach_exists(seeded, client):
    """Pełna ścieżka pilotażu: prawdziwe konto → purge → znane hasła demo
    przestają wpuszczać, prawdziwe konto działa dalej."""
    # Zasiane konto demo wpuszcza (to jest właśnie problem).
    login(client, COACH)
    # Prawdziwy trener przez API (roli nie da się nadać bootstrapem na
    # zajętej bazie — i słusznie), więc przez helper conftest.
    from conftest import create_user_with_role

    create_user_with_role(PRAWDZIWY_TRENER, HASLO, "Trener Pilotażu", "COACH")
    wylaczone = purge_demo()
    assert COACH["email"] in wylaczone
    assert set(wylaczone) == set(DEMO_EMAILS) & set(wylaczone)
    # Znane hasło demo przestaje działać…
    r = client.post("/api/auth/login", json=COACH)
    assert r.status_code == 401
    # …a prawdziwe konto loguje się dalej.
    r = client.post("/api/auth/login",
                    json={"email": PRAWDZIWY_TRENER, "password": HASLO})
    assert r.status_code == 200, r.text


def test_purge_on_empty_base_is_a_noop(client):
    assert purge_demo() == []

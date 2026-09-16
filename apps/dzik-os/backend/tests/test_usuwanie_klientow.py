"""Usuwanie klienta przez trenera (0.79.0) — dwa tryby i ich granica.

Runda dotyka usuwania CUDZYCH danych, więc testy pilnują nie tego, że
funkcja działa, tylko tego, że **nie działa tam, gdzie nie wolno**. Każdy
z czterech warunków trwałego skasowania ma tu osobny przypadek: mutant,
który go usunie, daje czerwony test.
"""

from conftest import CLIENT_A, COACH, login
from sqlalchemy import String, Text

from dzik_os.db import db_session
from dzik_os.klienci_usuwanie import (
    TABELE_AUDYTU,
    USUN_KONTO,
    ZAKONCZ_WSPOLPRACE,
)
from dzik_os.models import (
    Base,
    ClientInvitation,
    CoachClientRelationship,
    MessageThread,
    PlanDraft,
    RoleGrant,
    User,
)


def _zapros(client, hc, email, *, delivery=None):
    body = {"client_name": "Testowa Osoba", "client_email": email}
    if delivery is not None:
        body["delivery"] = delivery
    r = client.post("/api/coach/clients", headers=hc, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _wiersz_listy(client, hc, client_id):
    rows = client.get("/api/coach/clients", headers=hc).json()["clients"]
    return next((r for r in rows if r["client_id"] == client_id), None)


# --- konto nieaktywowane: znika naprawdę ------------------------------------

def test_konto_pending_znika_z_bazy_razem_z_zaproszeniem(seeded):
    hc = login(seeded, COACH)
    nowy = _zapros(seeded, hc, "do.skasowania@example.com")
    cid = nowy["client_id"]
    assert _wiersz_listy(seeded, hc, cid)["usuniecie"] == USUN_KONTO

    r = seeded.delete(f"/api/coach/clients/{cid}", headers=hc)
    assert r.status_code == 200, r.text
    assert r.json()["tryb"] == USUN_KONTO

    with db_session() as db:
        assert db.get(User, cid) is None
        assert db.query(RoleGrant).filter_by(user_id=cid).count() == 0
        assert db.query(ClientInvitation).filter_by(client_id=cid).count() == 0
        assert db.query(MessageThread).filter_by(client_id=cid).count() == 0
        assert db.query(CoachClientRelationship).filter_by(client_id=cid).count() == 0
    assert _wiersz_listy(seeded, hc, cid) is None


def test_po_usunieciu_nie_zostaje_ani_jeden_wiersz_poza_audytem(seeded):
    """Sprawdzane tą samą drogą co kasowanie: przez metadane SQLAlchemy.

    Dzięki temu tabela dodana w przyszłości, o której nikt nie pomyśli przy
    kasowaniu, zostanie wyłapana TUTAJ, a nie przez błąd klucza obcego na
    produkcji (SQLite wybacza sieroty, PostgreSQL nie).
    """
    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "sierota@example.com")["client_id"]
    # Wiersz w tabeli, która wskazuje klienta kolumną BEZ klucza obcego —
    # bez niego mutant gubiący takie kolumny przeszedłby niezauważony.
    with db_session() as db:
        trener_id = db.query(User).filter_by(email="dzik@example.com").one().id
        db.add(
            PlanDraft(
                id="HOS-DRF-SIEROTA00001",
                plan_kind="training",
                plan_id="HOS-PLN-SIEROTA00001",
                client_id=cid,
                coach_id=trener_id,
                base_version_no=1,
                base_content_json="{}",
                content_json="{}",
                created_by=trener_id,
                updated_by=trener_id,
            )
        )
    seeded.delete(f"/api/coach/clients/{cid}", headers=hc)

    # Test NIE korzysta z `_kolumny_uzytkownika` ani z żadnej innej funkcji
    # modułu: przeszukuje KAŻDĄ kolumnę tekstową KAŻDEJ tabeli. Pierwsza
    # wersja dzieliła tę funkcję z kodem produkcyjnym i była przez to ślepa
    # dokładnie na jej błąd — mutant gubiący kolumny bez klucza obcego
    # przechodził niezauważony, bo znikał po obu stronach naraz.
    #
    # `fetchall()`, nie `rowcount`: dla SELECT sterowniki zwracają -1, więc
    # wersja z rowcount też była zielona zawsze (to też wyszło z mutanta).
    sieroty = []
    with db_session() as db:
        for tabela in Base.metadata.sorted_tables:
            if tabela.name in TABELE_AUDYTU:
                continue
            for kolumna in tabela.columns:
                if not isinstance(kolumna.type, (String, Text)):
                    continue
                if db.execute(tabela.select().where(kolumna == cid)).fetchall():
                    sieroty.append(f"{tabela.name}.{kolumna.name}")
    assert sieroty == [], f"zostały wiersze po usuniętym koncie: {sieroty}"


def test_audyt_przezywa_usuniecie_konta(seeded):
    """Łańcuch pokwitowań zostaje — usunięcie konta jest w nim zdarzeniem,
    a nie luką. Skasowanie wiersza zerwałoby hash chain dla cudzych zdarzeń."""
    from dzik_os.models import Receipt

    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "slad.audytu@example.com")["client_id"]
    seeded.delete(f"/api/coach/clients/{cid}", headers=hc)
    with db_session() as db:
        akcje = [
            r.action for r in db.query(Receipt).filter(Receipt.subject_id == cid).all()
        ]
    assert "CLIENT_ACCOUNT_DELETED" in akcje
    assert "IDENTITY_REGISTERED" in akcje


def test_usuniecie_zwalnia_miejsce_w_limicie(seeded, monkeypatch):
    """Powód istnienia całej rundy: na produkcji limit 10 był wyczerpany
    przez konta testowe i nie dało się założyć kolejnego."""
    from dzik_os.config import settings

    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "zajmuje.miejsce@example.com")["client_id"]
    zajete = len(
        [
            r
            for r in seeded.get("/api/coach/clients", headers=hc).json()["clients"]
            if r["relationship_status"] in ("ACTIVE", "PAUSED")
        ]
    )
    monkeypatch.setattr(settings, "max_clients", zajete)
    r = seeded.post(
        "/api/coach/clients",
        headers=hc,
        json={"client_name": "Kolejna", "client_email": "kolejna@example.com"},
    )
    assert r.status_code == 409

    seeded.delete(f"/api/coach/clients/{cid}", headers=hc)
    r = seeded.post(
        "/api/coach/clients",
        headers=hc,
        json={"client_name": "Kolejna", "client_email": "kolejna@example.com"},
    )
    assert r.status_code == 201, r.text


# --- konto aktywne: dane zostają --------------------------------------------

def test_konto_aktywne_traci_wspolprace_ale_nie_dane(seeded):
    hc = login(seeded, COACH)
    rows = seeded.get("/api/coach/clients", headers=hc).json()["clients"]
    aktywny = next(r for r in rows if not r["account_pending"])
    assert aktywny["usuniecie"] == ZAKONCZ_WSPOLPRACE

    r = seeded.delete(f"/api/coach/clients/{aktywny['client_id']}", headers=hc)
    assert r.status_code == 200, r.text
    assert r.json()["tryb"] == ZAKONCZ_WSPOLPRACE

    with db_session() as db:
        konto = db.get(User, aktywny["client_id"])
        assert konto is not None, "konto aktywnego klienta NIE MOŻE zniknąć"
        assert konto.status == "ACTIVE"
        rel = (
            db.query(CoachClientRelationship)
            .filter_by(client_id=aktywny["client_id"])
            .one()
        )
        assert rel.status == "ENDED"


def test_klient_ktory_sie_logowal_nie_moze_byc_skasowany_mimo_pending(seeded):
    """Drugi warunek osobno: status mógłby zostać cofnięty inną drogą, więc
    `last_login_at` jest niezależnym zabezpieczeniem."""
    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "logowal.sie@example.com")["client_id"]
    with db_session() as db:
        db.get(User, cid).last_login_at = "2026-09-01T10:00:00+00:00"

    assert _wiersz_listy(seeded, hc, cid)["usuniecie"] == ZAKONCZ_WSPOLPRACE
    r = seeded.delete(f"/api/coach/clients/{cid}", headers=hc)
    assert r.json()["tryb"] == ZAKONCZ_WSPOLPRACE
    with db_session() as db:
        assert db.get(User, cid) is not None


def test_konto_z_dwoma_trenerami_nie_jest_niczyje_do_skasowania(seeded):
    """Trzeci warunek: drugi trener też ma tu relację, więc pierwszy nie może
    skasować konta pod nim."""
    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "dwoch.trenerow@example.com")["client_id"]
    with db_session() as db:
        inny = User(
            id="HOS-USR-INNYTRENER01",
            email="inny.trener@example.com",
            password_hash="!",
            display_name="Inny Trener",
            identity_id="HOS-ID-INNYTRENER01",
        )
        db.add(inny)
        db.flush()
        db.add(
            CoachClientRelationship(
                id="HOS-REL-DRUGA0000001",
                coach_id=inny.id,
                client_id=cid,
                created_by=inny.id,
            )
        )

    assert _wiersz_listy(seeded, hc, cid)["usuniecie"] == ZAKONCZ_WSPOLPRACE
    r = seeded.delete(f"/api/coach/clients/{cid}", headers=hc)
    assert r.json()["tryb"] == ZAKONCZ_WSPOLPRACE
    with db_session() as db:
        assert db.get(User, cid) is not None


def test_konto_zalozone_przez_kogos_innego_nie_jest_do_skasowania(seeded):
    """Czwarty warunek: relacja istnieje, ale założył ją kto inny."""
    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "cudze.zalozenie@example.com")["client_id"]
    with db_session() as db:
        rel = db.query(CoachClientRelationship).filter_by(client_id=cid).one()
        rel.created_by = "HOS-USR-KTOSINNY0001"

    assert _wiersz_listy(seeded, hc, cid)["usuniecie"] == ZAKONCZ_WSPOLPRACE
    r = seeded.delete(f"/api/coach/clients/{cid}", headers=hc)
    assert r.json()["tryb"] == ZAKONCZ_WSPOLPRACE
    with db_session() as db:
        assert db.get(User, cid) is not None


# --- dostęp ------------------------------------------------------------------

def test_obcy_trener_i_klient_nie_usuna_cudzego_klienta(seeded):
    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "nie.twoj@example.com")["client_id"]

    hk = login(seeded, CLIENT_A)
    assert seeded.delete(f"/api/coach/clients/{cid}", headers=hk).status_code in (
        401,
        403,
        404,
    )
    assert seeded.delete(f"/api/coach/clients/{cid}").status_code in (401, 403)
    with db_session() as db:
        assert db.get(User, cid) is not None


def test_nieistniejacy_klient_daje_404(seeded):
    hc = login(seeded, COACH)
    r = seeded.delete("/api/coach/clients/HOS-USR-NIEMATAKIEGO", headers=hc)
    assert r.status_code == 404


# --- doręczenie zaproszenia --------------------------------------------------

def test_wybor_link_nie_wysyla_maila_i_zwraca_link(seeded):
    hc = login(seeded, COACH)
    wynik = _zapros(seeded, hc, "przez.link@example.com", delivery="link")
    inv = wynik["invitation"]
    assert inv["delivery"] == "link"
    assert inv["reason"] is None
    assert inv["activation_link"].startswith("http")


def test_domyslnie_nadal_email(seeded):
    """Brak pola = zachowanie sprzed 0.79.0 (wysyłka), żeby istniejący
    klient API nie zmienił zachowania przez samo wgranie nowej wersji."""
    hc = login(seeded, COACH)
    inv = _zapros(seeded, hc, "domyslnie@example.com")["invitation"]
    assert inv["delivery"] in ("email", "manual")


def test_ponowne_wyslanie_z_wyborem_linku(seeded):
    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "ponowny.link@example.com")["client_id"]
    r = seeded.post(
        f"/api/coach/clients/{cid}/invitations",
        headers=hc,
        json={"delivery": "link"},
    )
    assert r.status_code == 201, r.text
    inv = r.json()["invitation"]
    assert inv["delivery"] == "link"
    assert inv["activation_link"].startswith("http")


def test_ponowne_wyslanie_bez_ciala_dziala_jak_dotad(seeded):
    hc = login(seeded, COACH)
    cid = _zapros(seeded, hc, "ponowny.bez.ciala@example.com")["client_id"]
    r = seeded.post(f"/api/coach/clients/{cid}/invitations", headers=hc)
    assert r.status_code == 201, r.text
    assert r.json()["invitation"]["delivery"] in ("email", "manual")

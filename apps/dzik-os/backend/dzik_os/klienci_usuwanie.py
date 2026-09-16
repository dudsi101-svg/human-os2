"""Usuwanie klienta przez trenera — dwa tryby, rozstrzygane przez serwer.

DLACZEGO TO ISTNIEJE: panel trenera nie miał żadnego sposobu pozbycia się
klienta. Konta testowe i pomyłkowe zajmowały miejsca w limicie (na produkcji
16.09 limit 10 był wyczerpany i nie dało się założyć kolejnego konta), a jedyne
wyjście — zmiana w bazie — jest zabroniona.

DLACZEGO DWA TRYBY, A NIE JEDEN: konto klienta to osobny człowiek z własnym
logowaniem, a nie wpis w kartotece trenera. Trener nie może kasować danych
osoby, która mu je tylko powierzyła — od tego jest droga samego klienta
(`POST /api/me/deletion-request`). Ale konto, które NIGDY nie zostało
aktywowane, jest w praktyce samym zaproszeniem: nie ma podmiotu danych, który
by z niego korzystał, więc jego usunięcie nikogo nie pozbawia niczego.

Granica jest w kodzie, nie w instrukcji: `tryb_usuniecia()` zwraca USUN_KONTO
wyłącznie wtedy, gdy zachodzą JEDNOCZEŚNIE cztery warunki. Każdy z nich
osobno zamyka inną drogę nadużycia i każdy ma test, który czerwienieje po
jego usunięciu.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Session

from .db import Base
from .models import CoachClientRelationship, User

#: Konto znika z bazy razem z zaproszeniem.
USUN_KONTO = "usuniete_konto"
#: Konto zostaje; kończy się wyłącznie współpraca z tym trenerem.
ZAKONCZ_WSPOLPRACE = "zakonczona_wspolpraca"

#: Tabele, których NIE wolno ruszać przy kasowaniu konta.
#:
#: `receipts` to łańcuch pokwitowań spięty `event_hash`/`previous_hash`:
#: usunięcie jednego wiersza unieważnia weryfikację łańcucha dla WSZYSTKICH
#: zdarzeń po nim, w tym cudzych. Pokwitowanie niesie identyfikatory i krótkie
#: streszczenie, nie treść zdrowotną — ta sama zasada, na której stoi
#: `privacy.request_deletion` („zapisy audytowe pozostają"). `subject_id` jest
#: tam zwykłym String(40) bez klucza obcego, więc skasowanie użytkownika nie
#: zostawia po sobie zepsutego odniesienia. Skutek: usunięcie konta jest w
#: audycie widoczne jako zdarzenie, a nie jako dziura.
TABELE_AUDYTU = frozenset({"receipts"})

#: Kolumny wskazujące na użytkownika, które NIE mają klucza obcego na
#: `users.id` (część modeli trzyma goły String(40) — np. `assistant_tasks`,
#: `plan_drafts`, `change_sets`). Bez tej listy zostałyby po kliencie sieroty.
KOLUMNY_BEZ_KLUCZA = frozenset(
    {"client_id", "user_id", "owner_user_id", "coach_id", "created_by", "author_id"}
)


def tryb_usuniecia(db: Session, coach: User, client: User) -> str:
    """Rozstrzyga, co wolno zrobić z tym klientem. Serwer decyduje, nie UI.

    USUN_KONTO wymaga wszystkich czterech warunków naraz:

    1. `status == "PENDING"` — konto nigdy nie zostało aktywowane;
    2. `last_login_at is None` — i nikt się na nie nigdy nie zalogował
       (pas i szelki: status mógłby zostać cofnięty inną drogą);
    3. istnieje DOKŁADNIE JEDNA relacja tego klienta i należy do tego
       trenera — konto współdzielone nie jest niczyje do skasowania;
    4. `created_by == coach.id` — to ten trener je założył.

    W każdym innym przypadku: ZAKONCZ_WSPOLPRACE.
    """
    if client.status != "PENDING":
        return ZAKONCZ_WSPOLPRACE
    if client.last_login_at is not None:
        return ZAKONCZ_WSPOLPRACE
    relacje = (
        db.query(CoachClientRelationship)
        .filter(CoachClientRelationship.client_id == client.id)
        .all()
    )
    if len(relacje) != 1 or relacje[0].coach_id != coach.id:
        return ZAKONCZ_WSPOLPRACE
    if relacje[0].created_by != coach.id:
        return ZAKONCZ_WSPOLPRACE
    return USUN_KONTO


def _kolumny_uzytkownika(tabela) -> list:
    """Kolumny tabeli wskazujące na użytkownika: po kluczu obcym na
    `users.id`, a gdy klucza nie ma — po nazwie ze znanego zbioru."""
    wynik = []
    for kolumna in tabela.columns:
        if any(fk.column.table.name == "users" for fk in kolumna.foreign_keys):
            wynik.append(kolumna)
        elif kolumna.name in KOLUMNY_BEZ_KLUCZA and isinstance(kolumna.type, String):
            wynik.append(kolumna)
    return wynik


def usun_konto_trwale(db: Session, client_id: str) -> dict[str, int]:
    """Kasuje konto i wszystko, co na nie wskazuje, poza łańcuchem audytu.

    Zbiór tabel bierzemy z METADANYCH SQLAlchemy, nie z ręcznej listy.
    Ponad sześćdziesiąt tabel ma klucz obcy na `users.id`; lista pisana ręcznie
    rozjechałaby się przy pierwszej nowej tabeli i wywróciła się na kluczu
    obcym dopiero na produkcji (SQLite wybacza kolejność i sieroty, PostgreSQL
    nie). Przy tym podejściu nowa tabela jest obsłużona z dnia na dzień, a
    `test_usuwanie_klientow` sprawdza to samo tą samą drogą — więc regresję
    zobaczymy w testach, nie w awarii.

    Kolejność: `sorted_tables` układa tabele od nadrzędnych do zależnych,
    więc idziemy od końca — dzieci przed rodzicami.

    Zwraca licznik skasowanych wierszy per tabela (tylko niezerowe) — do
    wpisania w audyt, żeby było widać rozmiar operacji.
    """
    usuniete: dict[str, int] = {}
    for tabela in reversed(Base.metadata.sorted_tables):
        if tabela.name in TABELE_AUDYTU:
            continue
        if tabela.name == "users":
            # Samo konto: kluczem jest `id`, nie kolumna wskazująca na kogoś
            # innego. Bez tego przypadku wcześniejsze `continue` (users nie ma
            # klucza obcego na users) wyrzuciłoby konto z kasowania i została
            # by po nim sierota.
            warunek = tabela.c.id == client_id
        else:
            kolumny = _kolumny_uzytkownika(tabela)
            if not kolumny:
                continue
            warunek = kolumny[0] == client_id
            for kolumna in kolumny[1:]:
                warunek = warunek | (kolumna == client_id)
        liczba = db.execute(tabela.delete().where(warunek)).rowcount
        if liczba:
            usuniete[tabela.name] = liczba
    return usuniete

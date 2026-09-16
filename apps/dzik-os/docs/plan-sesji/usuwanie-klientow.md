# Plan sesji: usuwanie klientów + wybór doręczenia zaproszenia (0.79.0)

**Gałąź:** `agent/usuwanie-klientow` (od `main` = `568b5d4`, 0.78.0). **Rola:** integrator.
**Bez migracji** — schemat się nie zmienia.

## Cel (słowami właściciela, 16.09)

> Dodaj opcję do usuwania klientów. Teraz mamy kilku testowych których nie potrzebuje
> zresztą trener musi mieć możliwość usuwania klientów.
> Dodaj też opcję by trener mógł wybrać czy będzie wysłany e-mail ze zmianą hasła przy
> pierwszym logowaniu czy link.

Decyzje właściciela na pytania integratora (16.09): usuwanie **w dwóch trybach zależnie
od stanu konta**; wybór doręczenia **przy dodawaniu i przy ponownym wysłaniu**.

## Dlaczego to pilne (dowód z produkcji)

Próba założenia TEST-03 (run 35082948688, 16.09 10:04) padła na:
`BŁĄD: Limit podopiecznych (10) jest osiągnięty.` Dziesięć miejsc zajmują konta testowe
i pomyłkowe, a panel trenera **nie ma żadnego sposobu** ich usunięcia. Trasa
`POST /clients/{id}/relationship-status` istnieje w API od dawna, ale front nigdy jej
nie wołał (sprawdzone: jedyne `"ENDED"` we froncie dotyczy zaleceń, nie współpracy).

## Rozpoznanie (stan `main` 0.78.0)

* **`routers/clients.py:109` `create_client`** — zakłada konto `PENDING` z `password_hash="!"`
  (żadne hasło się nie zweryfikuje), relację ACTIVE, wątek wiadomości, zgody
  z onboardingu (tylko dla NOWEGO konta) i wystawia zaproszenie.
* **`routers/clients.py:41` `_issue_invitation`** — wysyła e-mail z linkiem; `activation_link`
  zwracany trenerowi **wyłącznie awaryjnie**, gdy `sent` jest fałszem. Trener nie ma wyboru.
* **`routers/clients.py:599` `set_relationship_status`** — ACTIVE/PAUSED/ENDED, działa, nieużywane.
* **`routers/privacy.py:500` `request_deletion`** — pełna, przemyślana ścieżka RODO: ~200 linii
  pokrywających ~40 tabel, anonimizacja + fizyczne kasanie plików, zgody cofnięte, sesje
  unieważnione, `status="DELETED"`, e-mail podmieniony na `deleted-<id>@example.invalid`.
  Wymaga hasła klienta i działa wyłącznie na sobie samym (`current_user`).
* **`models.py:37` `User`** — ma `status` (PENDING/ACTIVE/SUSPENDED/DELETED), `last_login_at`,
  `anonymized_at`. **Ponad 60 tabel** ma klucz obcy na `users.id`.
* **Limit:** `settings.max_clients` liczy relacje ACTIVE/PAUSED; ENDED zwalnia miejsce
  (`clients.py:130`).

## Decyzje projektowe

1. **Dwa tryby, rozstrzygane przez serwer, nie przez UI.** `DELETE /api/coach/clients/{id}`
   sam ustala, co wolno, i mówi w odpowiedzi, co zrobił (`tryb`). UI nigdy nie decyduje
   o trwałości — pokazuje tylko to, co serwer zapowiedział.

2. **Trwałe usunięcie tylko dla konta, które nigdy nie było czyjeś.** Wszystkie cztery
   warunki naraz: `status == "PENDING"`, `last_login_at is None`, w bazie jest **dokładnie
   jedna** relacja dla tego klienta i należy do tego trenera, oraz `rel.created_by == coach.id`.
   Inaczej: zakończenie współpracy (`ENDED`). Uzasadnienie: konto PENDING to w praktyce samo
   zaproszenie — nie ma podmiotu danych, który by z niego korzystał. Konto, na które ktoś się
   choć raz zalogował, należy do tej osoby, nie do trenera.

3. **Kasowanie po metadanych SQLAlchemy, nie z ręcznej listy.** Ponad 60 tabel wskazuje na
   `users.id`; ręczna lista rozjedzie się przy pierwszej nowej tabeli i wywróci się na kluczu
   obcym w PostgreSQL (SQLite wybacza, produkcja nie). Przechodzimy `Base.metadata.sorted_tables`
   od końca i kasujemy wiersze, których kolumna wskazuje na tego użytkownika — z kluczy obcych
   oraz z ustalonego zbioru nazw kolumn bez FK (`client_id`, `owner_user_id`, …).
   Test sprawdza to samo generycznie, więc **przyszła tabela zostanie wyłapana przez test**,
   a nie przez produkcję.

4. **Łańcuch audytu zostaje nietknięty.** `receipts` ma `event_hash`/`previous_hash` — usunięcie
   wiersza złamałoby weryfikację łańcucha dla **wszystkich** zdarzeń po nim. `subject_id` jest
   tam zwykłym `String(40)` bez klucza obcego, więc nic się nie psuje. Zdarzenia niosą
   identyfikatory, nie treść zdrowotną (ta sama zasada, którą `request_deletion` stosuje od
   początku). Kasowanie konta jest więc widoczne w audycie jako zdarzenie, a nie jako luka.

5. **Konto aktywne: znika z listy, nie z bazy.** Trener zamyka współpracę; konto, dane, historia
   i dostęp klienta zostają. Klient, który chce usunąć swoje dane, ma do tego własną drogę
   (`/deletion-request`) — i to jest jedyna droga, która te dane rusza.

6. **Doręczenie zaproszenia: jawny wybór, nie zgadywanie.** `RelationshipIn` i ponowne wysłanie
   dostają `delivery: "email" | "link"` (domyślnie `email` — zachowanie jak dotąd). Przy `link`
   e-mail **w ogóle nie wychodzi** i `activation_link` wraca zawsze. Awaryjny zwrot linku przy
   nieudanej wysyłce zostaje bez zmian. Token nadal nie trafia do audytu ani logów.

## Pliki

**Nowe:** `backend/dzik_os/klienci_usuwanie.py`, `backend/tests/test_usuwanie_klientow.py`,
`frontend/e2e/usuwanie-klientow.spec.ts`, ten plan.

**Zmieniane:** `backend/dzik_os/routers/clients.py`, `backend/dzik_os/schemas.py`,
`backend/tests/access_matrix.py`, `frontend/src/pages/coach/Clients.tsx`,
`frontend/src/pages/coach/ClientDetail.tsx`, `frontend/src/api.ts` (lub odpowiednik),
`docs/CHANGELOG.md`, `docs/INSTRUKCJA_TRENERA.md`, `docs/PERMISSIONS.md`,
`docs/RELEASE_STATUS.md`, `docs/STAN_PRZEKAZANIA.md`, wersje w czterech plikach.

**Zabronione:** `hos_engine/`, `tests/` w korzeniu, migracje, `AGENTS.md`, `KOORDYNACJA.md`,
`tools/spojnosc.py`, `tools/mutacje*.py`.

## Rezerwacje

* **Wersja 0.79.0** (`frontend/package.json`, `backend/pyproject.toml`,
  `backend/dzik_os/__init__.py`, `README.md`, `RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md`).
* **Migracja: brak.** Ostatnia w `db.py` = 42.
* **Porty E2E:** 8180/8182, a11y 8184.

## Etapy

| # | Etap | Weryfikacja |
|---|---|---|
| 1 | `klienci_usuwanie.py`: warunki trybu + kasowanie po metadanych | testy jednostkowe |
| 2 | `DELETE /api/coach/clients/{id}` + macierz dostępu | `pytest test_usuwanie_klientow.py access_matrix` |
| 3 | `delivery` w dodawaniu i ponownym wysłaniu | `pytest test_clients*.py` |
| 4 | UI: przycisk „Usuń" z potwierdzeniem mówiącym prawdę o trybie; wybór doręczenia | tsc, E2E |
| 5 | dokumenty, wersje, pełne bramki | spójność, pełny pytest, mutanty, Playwright, a11y |

## Test INTENDED_PURPOSE (etap 0)

Runda dotyka **usuwania cudzych danych** — najcięższa kategoria w tym projekcie. Zabezpieczenie
jest strukturalne, nie regulaminowe: trwałe kasowanie jest fizycznie niemożliwe dla konta, na
które ktoś się zalogował (warunek w kodzie, nie w instrukcji), a dla konta współdzielonego przez
dwóch trenerów żaden z nich nie może go usunąć. Mutant wyłączający którykolwiek z czterech
warunków musi dawać czerwony test. Zero AI, zero nowych danych, bez migracji.

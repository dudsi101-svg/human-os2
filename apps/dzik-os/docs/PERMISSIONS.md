# Uprawnienia i reguły dostępu — Dzik OS

Model dwuosiowy zgodny z Human OS (Identity, Authority & Permissions):

* **Oś A — tożsamość** (`users.identity_id`, typ HUMAN): *kim* podmiot jest.
* **Oś B — rola uprawnień** (`role_grants`): *co* mu wolno. Nadanie roli
  jest jawne (kto nadał, kiedy, w jakim zakresie) i odwoływalne — wzorzec
  `hos_engine.authority.RoleGrantRegistry`. Typ tożsamości ≠ rola.

## Role domenowe

| Rola | Zakres |
|---|---|
| CLIENT | wyłącznie własne dane (`scope=self`) |
| COACH | dane klientów z **aktywną relacją** i **aktywną zgodą** |
| ADMIN | konta i audyt; **bez** danych zdrowotnych |

## Reguły egzekwowane w backendzie (`authz.py`)

1. **Klient**: `resolve_client_access` przepuszcza tylko `actor.id == client_id`.
   Ochrona przed IDOR: każdy endpoint z `client_id` w ścieżce przechodzi
   przez tę funkcję; cudze zasoby zwracają **404** (nie ujawniamy istnienia).
2. **Trener**: wymaga (a) relacji `coach_client_relationships.status=ACTIVE`
   oraz (b) pozytywnej decyzji `hos_engine.ConsentRegistry.authorize`
   (purpose=`coaching`, domain=`health_data`). Cofnięcie zgody odbiera
   dostęp natychmiast, mimo aktywnej relacji.
3. **Admin**: endpointy `/api/admin/*` nie zwracają danych zdrowotnych;
   próba wejścia admina na `/api/clients/{id}/...` kończy się 403/404.
   Każde użycie panelu admina emituje zdarzenie audytowe.
4. **Płatności** są metadanymi współpracy (nie danymi zdrowotnymi) —
   wymagają relacji, ale nie zgody `health_data` (sensitive=False).
5. **Decyzje zapadają wyłącznie w backendzie** — frontend jedynie
   renderuje wynik (kontrakt ADR-ARCH-003). Rola i `clientId` trzymane
   w `sessionStorage` frontendu są WYŁĄCZNIE wskazówką dla UI; tożsamość
   i rola pochodzą zawsze ze zweryfikowanej sesji (`current_user` /
   `require_role`), a `client_id`/`coach_id` z body/query/ścieżki są
   zawsze weryfikowane względem relacji i zgód.
6. **Wspólne guardy w `authz.py`** (zamiast powielania warunków w
   routerach): `resolve_client_access` (zakres jednego klienta),
   `require_owned_resource` (zasób istnieje I należy do aktora — katalogi
   trenera, plany, sloty, harmonogramy płatności), `require_thread_party`
   (strona wątku wiadomości), `require_attachable_file` (podpinanie
   plików), `require_client_self`, `deny` (jawna, logowana odmowa).

## Odmowy dostępu — zdarzenie ACCESS_DENIED

Odmowa **zasobowa** (aktor przeszedł autoryzację roli, ale zasób istnieje
i należy do kogoś innego / jest poza zakresem relacji lub zgód — próba
IDOR) jest sygnalizowana wyjątkiem `authz.ResourceAccessDenied`,
obsługiwanym centralnie w `main.py`:

* odpowiedź dla klienta HTTP to zawsze **404 „Nie znaleziono"** — nie
  ujawniamy istnienia zasobu;
* w łańcuchu audytu zapisywane jest zdarzenie `ACCESS_DENIED` z payloadem
  `{endpoint, method, resource}` + id aktora — **nigdy dane zdrowotne ani
  sekrety** (identyfikatory zasobów nie są danymi zdrowotnymi);
* NIE logujemy: 401 (brak/wygasła sesja), 403 (brak roli) ani 404 dla
  identyfikatorów, które w ogóle nie istnieją (nieudane zgadywanie id nie
  odróżnia się w odpowiedzi, a nie zaśmieca audytu).

Testy: `tests/test_idor.py::test_access_denied_is_audited_without_health_data`,
`test_plain_401_is_not_audited_as_access_denied`.

## Macierz uprawnień endpointów

Legenda: **W** = właściciel danych (klient, `actor.id == client_id`);
**T** = trener z **AKTYWNĄ** relacją i **nieocofniętą zgodą**
coaching/health_data (`resolve_client_access`); **T·rel** = trener z samą
aktywną relacją (bez bramki zgody); **T·own** = trener-właściciel rekordu
(`coach_id == aktor`); **A** = admin; ✗ = 404 (odmowa zasobowa) albo 403
(brak roli). Kolumna „Zgoda" dotyczy zgody coaching/health_data
(`sensitive=True`, chyba że zaznaczono inaczej).

| Endpoint | Kto może | Zakres rekordów | Relacja | Zgoda | R/W |
|---|---|---|---|---|---|
| POST /api/auth/login, /logout; GET /api/auth/brand | publiczne | — | — | — | — |
| GET /api/auth/me; POST /api/auth/change-password | zalogowany | własne konto | — | — | R/W |
| GET /api/auth/sessions; POST /api/auth/sessions/revoke-others | zalogowany | własne sesje | — | — | R/W |
| POST /api/auth/sessions/{session_id}/revoke | zalogowany | wyłącznie własna sesja (cudza aktywna → ACCESS_DENIED) | — | — | W |
| POST /api/coach/clients | COACH | nowe konto: pełny onboarding + zgoda-deklaracja; istniejące konto: tylko aktywny CLIENT, **bez auto-zgody** (nadaje ją sam klient) | tworzy/reaktywuje | — | W |
| GET /api/coach/clients, /api/coach/dashboard | COACH | wyłącznie własne relacje (metadane operacyjne) | — | — | R |
| POST /api/coach/clients/{id}/relationship-status | COACH | własna relacja | — | — | W |
| GET /api/coach/clients/{id}/history, /overview | T | pokwitowania/konto jednego klienta | tak | tak | R |
| GET/PUT /api/clients/{id}/profile, GET /profile/history | W, T | profil jednego klienta | T: tak | T: tak | R/W |
| GET/POST /api/clients/{id}/goals; POST /goals/{goal_id}/status | W, T | cele jednego klienta; `goal_id` musi należeć do `client_id` | T: tak | T: tak | R/W |
| POST /api/plans | COACH (klientowi: T) | plan klienta lub szablon własny | tak* | tak* | W |
| POST /api/plans/{plan_id}/versions | T·own + T | wyłącznie własny plan (i zgoda klienta, jeśli przypisany) | tak* | tak* | W |
| POST /api/plans/{template_id}/copy-to/{client_id} | T·own + T | własny szablon → własny klient | tak | tak | W |
| GET /api/plans/templates | T·own | własne szablony | — | — | R |
| GET /api/clients/{id}/plans; GET /api/plans/{plan_id}/versions | W, T (szablon: tylko autor) | plany jednego klienta | T: tak | T: tak | R |
| POST/GET /api/clients/{id}/workouts | W, T | treningi klienta; `plan_version_id` musi wskazywać plan TEGO klienta | T: tak | T: tak | R/W |
| POST /api/nutrition; POST /api/nutrition/{plan_id}/versions | T·own + T | dieta własnego klienta | tak | tak | W |
| GET /api/clients/{id}/nutrition; GET /api/nutrition/{plan_id}/versions | W, T | diety jednego klienta | T: tak | T: tak | R |
| POST /api/schedule; POST /api/schedule/{item_id}/status | W, T | harmonogram jednego klienta (`item.client_id`) | T: tak | T: tak | W |
| GET /api/clients/{id}/schedule, /reminders | W, T | harmonogram/przypomnienia klienta | T: tak | T: tak | R |
| POST /api/reminders | T | przypomnienie dla własnego klienta | tak | tak | W |
| POST /api/checkins | CLIENT (self) | wyłącznie własny raport | — | — | W |
| GET /api/clients/{id}/checkins; GET /api/checkins/{checkin_id}/revisions | W, T | raporty jednego klienta (`checkin.client_id`) | T: tak | T: tak | R |
| POST /api/checkins/{checkin_id}/review, /ai-summary | T | raport własnego klienta | tak | tak (write) | W |
| POST/GET /api/clients/{id}/measurements; /metric-definitions | W, T (definicje: POST tylko T) | pomiary jednego klienta | T: tak | T: tak | R/W |
| GET /api/threads | strona wątku | własne wątki; trener: tylko AKTYWNA relacja + nieocofnięta zgoda (inaczej wątek znika też z listy) | T: tak | T: tak (sens.=False) | R |
| GET/POST /api/threads/{thread_id}/messages | strona wątku (`require_thread_party`) | jeden wątek | T: tak | T: tak (sens.=False) | R/W |
| POST /api/files | W, T (upload dla klienta) | plik własny / klienta z relacji | T: tak | T: tak (write) | W |
| GET /api/files/{file_id} | patrz tabela „Pliki" niżej | jeden plik | wg tabeli | wg tabeli | R |
| POST /api/documents | T | dokument dla własnego klienta (plik musi należeć do klienta) | tak | tak (write) | W |
| GET /api/clients/{id}/documents, /photos | W, T | dokumenty/zdjęcia klienta | T: tak | T: tak | R |
| POST /api/payments/schedules | T·rel | pakiet dla własnego klienta | tak | nie (sens.=False) | W |
| GET /api/clients/{id}/payments | W, T·rel | płatności jednego klienta | T: tak | nie (sens.=False) | R |
| POST /api/payments/records/{record_id}/status; /schedules/{schedule_id}/records | T·own | wyłącznie rekordy własnych harmonogramów | — | — | W |
| GET/POST /api/me/consents; /consents/{id}/confirm, /revoke | podmiot danych | wyłącznie własne zgody | — | — | R/W |
| GET /api/me/export, /api/me/export.xlsx | zalogowany | wyłącznie własne dane | — | — | R |
| POST /api/me/deletion-request | CLIENT (self, hasło+fraza) | własne konto; kończy relacje, cofa zgody, unieważnia sesje | — | — | W |
| GET /api/me/today | CLIENT (self) | agregat własnego dnia | — | — | R |
| POST /api/clients/{id}/schedule/{item_id}/complete | W, T | odhaczenie; `item.client_id` musi się zgadzać | T: tak | T: tak | W |
| POST/GET /api/clients/{id}/observations | W, T | obserwacje klienta (`schedule_item_id` musi należeć do klienta) | T: tak | T: tak | R/W |
| POST/GET /api/clients/{id}/nutrition-log; GET /monitoring | W, T | dziennik/monitoring klienta | T: tak | T: tak | R/W |
| GET /api/clients/{id}/personal-records, /strength-series | W, T | rekordy/serie jednego klienta | T: tak | T: tak | R |
| POST/PUT/status /api/coach/knowledge, /exercises, /food-products | T·own | wyłącznie własne wpisy katalogów | — | — | W |
| GET /api/coach/knowledge, /exercises, /food-products | T·own | własny katalog (izolacja między trenerami) | — | — | R |
| GET /api/me/knowledge, /exercises, /food-products | klient | AKTYWNE wpisy trenerów z AKTYWNĄ relacją | tak | nie (broadcast) | R |
| POST /api/coach/diet-suggestion | T·own | wyłącznie własne produkty (422 dla cudzych); nic nie zapisuje | — | — | R |
| GET /api/push/public-key; POST /api/push/subscribe, /unsubscribe | zalogowany | własna subskrypcja (endpoint = capability przeglądarki; przejęcie endpointu przez inne konto audytowane `PUSH_ENDPOINT_REBOUND`) | — | — | W |
| POST/GET /api/coach/consult-slots; POST /{slot_id}/cancel | T·own | własne sloty | — | — | R/W |
| GET /api/me/consult-slots | zalogowany | wolne sloty trenerów z AKTYWNĄ relacją + własne rezerwacje | tak | nie | R |
| POST /api/consult-slots/{slot_id}/book | klient | slot trenera z AKTYWNĄ relacją | tak | nie | W |
| POST /api/consult-slots/{slot_id}/unbook | klient | wyłącznie własna rezerwacja (≥12 h przed) | — | — | W |
| GET /api/admin/users | ADMIN | konta i role — **bez danych zdrowotnych**; audytowane | — | — | R |
| GET /api/admin/audit/verify | ADMIN | weryfikacja hash-chain; audytowane | — | — | R |
| GET /api/admin/receipts | ADMIN | **metadane** pokwitowań (akcja, id, hash, czas) — `summary` celowo pomijane (bywa pochodną danych zdrowotnych); audytowane | — | — | R |

\* dla planu przypisanego klientowi; szablon (`client_id=NULL`) wymaga
tylko własności trenera.

Automatyczna weryfikacja macierzy: `tests/test_authz_matrix.py`
(parametryzowany przebieg po endpointach tokenami sześciu person: anonim,
klient-właściciel, obcy klient, trener prowadzący, obcy trener, admin)
oraz `tests/test_idor.py` (podmiana każdego istotnego identyfikatora,
PAUSED/ENDED, cofnięta zgoda, konto usunięte, stare linki do plików).

## Monitoring i dziennik obserwacji

* Odhaczanie harmonogramu (`schedule_completions`), dziennik obserwacji
  (`observations`) i dziennik kaloryczny (`daily_nutrition_logs`) podlegają
  tym samym regułom dostępu co inne dane zdrowotne (relacja + zgoda,
  `resolve_client_access`, domyślnie `sensitive=True`).
* **Obserwacje nigdy nie są diagnozą.** System zapisuje tekst dosłownie i
  wyłącznie flaguje wpisy `severity=NIEPOKOJACE` do przeglądu przez
  trenera (badge w panelu, filtr, e-mail przez `notifications_provider`
  jeśli skonfigurowany) — nie interpretuje treści, nie sugeruje przyczyny,
  nie zmienia planu ani dawkowania. Zgodnie z zasadą z §5.5 aplikacja
  wyłącznie przechowuje i przypomina plan wprowadzony przez człowieka.
* Element harmonogramu kategorii SUPLEMENT/POSIŁEK musi mieć `author_note`
  (kto i na jakiej podstawie wpisał zalecenie) — proweniencja wymuszona
  w formularzu frontendu (`ScheduleTab`), nie tylko w backendzie.

## Baza wiedzy (oś inna niż dane zdrowotne)

`knowledge_items`, `exercises` i `food_products` to treść **trenera**,
nie dane klienta — inna oś uprawnień niż reszta dokumentu:

* zapis (`POST/PUT/status`) wymaga wyłącznie roli COACH i własności
  rekordu (`coach_id == aktor`), bez `resolve_client_access`;
* odczyt (`GET /api/me/knowledge`, `/api/me/exercises`,
  `/api/me/food-products`) wymaga aktywnej relacji
  `coach_client_relationships.status=ACTIVE` z tym trenerem — **bez**
  bramki zgody `health_data`, bo to materiał edukacyjny/broadcast,
  nie dane osobowe klienta;
* trener odpowiada merytorycznie za treść — system jej nie generuje,
  nie moderuje ani nie weryfikuje;
* `POST /api/coach/diet-suggestion` jest COACH-only, dodatkowo waliduje,
  że każdy przekazany `product_id` należy do wywołującego trenera
  (`coach_id == aktor`, 422 dla cudzych/nieznanych) — nie zapisuje
  niczego, więc nie wymaga `resolve_client_access` ani zgody klienta
  (zwraca wyłącznie sugestię gramatury, propose-only).

## Pliki (`/api/files`)

Model autoryzacji pobrania (`GET /api/files/{id}`, egzekwowany w
`routers/files.py::download_file`; każda odmowa = **404**):

| Kto | Warunek |
|---|---|
| Właściciel danych | `files.owner_user_id == aktor` (upload trenera z `client_id` = własność klienta) |
| Trener | aktywna relacja **i** aktywna zgoda coaching/health_data (`resolve_client_access`) — cofnięcie zgody odbiera dostęp również do plików już istniejących |
| Strona wątku wiadomości | plik jest załącznikiem wiadomości w wątku aktora; klient zawsze, trener przy AKTYWNEJ relacji i nieocofniętej zgodzie (`sensitive=False` — dokładnie ten sam kontrakt co dostęp do treści wątku, `authz.require_thread_party`) |
| Klient trenera | plik jest załącznikiem **AKTYWNEGO** wpisu bazy wiedzy trenera, z którym aktor ma AKTYWNĄ relację (broadcast, bez bramki zgody) |

Upload i podpinanie:

* allowlista typów (`ALLOWED_UPLOAD_TYPES`) **bez SVG i plików
  wykonywalnych**; typ weryfikowany po ZAWARTOŚCI (magic bytes) —
  niezgodność z deklaracją = 415;
* limit rozmiaru (`DZIK_MAX_UPLOAD_MB`) egzekwowany strumieniowo;
* zdjęcia (nowe uploady): EXIF/GPS usuwane, dłuższy bok ≤ 2560 px,
  rekompresja jakość 85 (Pillow);
* nazwy plików sanityzowane (kanoniczne rozszerzenie typu, RFC 5987 w
  `Content-Disposition`); odpowiedzi plików prywatnych mają
  `X-Content-Type-Options: nosniff` i `Cache-Control: no-store`;
* magazyn: losowe nazwy UUID w `DZIK_UPLOAD_DIR`; odczyt weryfikuje, że
  ścieżka nie wychodzi poza ten katalog (path traversal = 404);
* podpięcie pliku do zasobu (`authz.require_attachable_file`): wiadomość —
  plik własny/samodzielnie wgrany; zdjęcia raportu — tylko obrazy klienta
  (limit `DZIK_MAX_CHECKIN_PHOTOS`=8 szt.,
  `DZIK_MAX_CHECKIN_PHOTOS_TOTAL_MB`=60 MB); dokument — plik klienta;
  baza wiedzy — wyłącznie plik własny trenera; wpis treningowy — plik
  klienta;
* pliki-sieroty (bez żadnej referencji) po `DZIK_ORPHAN_FILE_TTL_H`=24 h:
  soft delete (`deleted_at`) + usunięcie bajtów z dysku (pętla godzinna,
  zdarzenie ORPHAN_FILES_CLEANED).

## Zgody (rejestr wersjonowany)

* Wiersz `consents` = jedna zgoda: podmiot, odbiorca, cel, domena, akcje,
  `allow_sensitive`, wersja tekstu zgody, `granted_at`, `revoked_at`.
* Cofnięcie **nie usuwa** wiersza (pełna historia); cofnąć może wyłącznie
  podmiot danych (kontrakt `ConsentRegistry.revoke`).
* Autoryzację (`authorize`) wykonuje Core (`hos_engine.consent`) na
  rejestrze hydratowanym z bazy — aplikacja nie reimplementuje reguł.
* Zgoda przy onboardingu jest rejestrowana przez trenera jako deklaracja
  klienta (proweniencja: `consent_collected_via=onboarding_declaration`
  w zdarzeniu audytu); klient widzi ją w aplikacji i może cofnąć.
* **Deklarację z onboardingu wolno zarejestrować wyłącznie dla konta
  zakładanego właśnie przez trenera.** Podpięcie ISTNIEJĄCEGO konta
  (`POST /api/coach/clients` na znany e-mail) tworzy/reaktywuje relację,
  ale **nie nadaje żadnej zgody** (`consent_collected_via=
  pending_subject_grant`) — do czasu nadania zgody przez samego klienta
  (`POST /api/me/consents`) trener widzi `consent_active=false` i nie ma
  dostępu do danych. Chroni to też przed cichym „od-cofnięciem" zgody
  przez ponowne dodanie klienta. Podpiąć można wyłącznie aktywne konto z
  rolą CLIENT (konto trenera/admina/usunięte → 409, bez ujawniania roli).
* **Usunięcie konta** (`POST /api/me/deletion-request`) poza anonimizacją
  danych: kończy wszystkie relacje (ENDED), cofa wszystkie aktywne zgody
  podmiotu i unieważnia wszystkie sesje — trener nie zachowuje żadnego
  dostępu, a stare tokeny i linki do plików przestają działać.

## Testy uprawnień

`tests/test_isolation.py`, `tests/test_consents.py`,
`tests/test_uploads.py`, `tests/test_payments.py` — łącznie 20+ asercji
między kontami (klient↔klient, obcy trener, admin, brak logowania).
Do tego automatyczna macierz `tests/test_authz_matrix.py` (32 endpointy ×
6 person) i `tests/test_idor.py` (podmiana identyfikatorów: checkin_id,
plan_id/version_id, nutrition plan_id, thread_id, goal_id,
schedule_item_id, slot_id, payment schedule_id/record_id, session_id;
PAUSED/ENDED, cofnięta zgoda, konto usunięte, relink istniejącego konta,
audyt ACCESS_DENIED).

## Sesje i tokeny (uwierzytelnianie)

Model sesji (`auth_sessions`, `security.py`, `routers/auth.py`):

* **Serwer przechowuje wyłącznie hash SHA-256 tokenu** (`token_hash`);
  sam token zna tylko klient. Wyciek bazy nie pozwala przejąć sesji.
* Token: `secrets.token_urlsafe(32)`, TTL `DZIK_SESSION_TTL_H` (domyślnie
  72 h, `expires_at`). Unieważnienie = `revoked_at` (append-only — wiersz
  sesji nigdy nie jest usuwany). `last_used_at` (rozdzielczość ~5 min)
  zasila ekran aktywnych sesji.
* Przekazywanie: nagłówek `Authorization: Bearer` (token w `sessionStorage`
  frontendu, per karta) **oraz** równolegle ciasteczko httpOnly
  `dzik_session` (SameSite=Lax, Secure w produkcji). `_extract_token`
  preferuje nagłówek.
* **Wylogowanie unieważnia sesję po stronie serwera** — frontend wysyła je
  przez wspólnego klienta API (z nagłówkiem), a lokalny stan czyści zawsze,
  także przy utracie połączenia.
* **Zmiana hasła = operacja wrażliwa**: unieważnia WSZYSTKIE dotychczasowe
  sesje użytkownika (z bieżącą włącznie) i wydaje nowy token (rotacja) —
  żaden stary token nie pozostaje aktywny. Chroniona limitem prób
  (`password_change_rate_limiter`, klucz: id użytkownika), jak logowanie
  (`login_rate_limiter`, klucz: e-mail; jeden komunikat 401 nie ujawnia
  istnienia konta).
* Użytkownik widzi aktywne sesje (`GET /api/auth/sessions` — metadane bez
  tokenów/hashy, bieżąca oznaczona) i może zakończyć wybraną
  (`POST /api/auth/sessions/{id}/revoke`, tylko własną — cudza to 404) lub
  wszystkie pozostałe (`POST /api/auth/sessions/revoke-others`). UI: sekcja
  „Aktywne sesje" w Profilu klienta i w „Więcej" trenera/admina.
* Zdarzenia audytu: `SESSION_LOGGED_OUT`, `SESSION_REVOKED`,
  `SESSIONS_REVOKED`, `PASSWORD_CHANGED` (payload bez sekretów — testowane
  w `tests/test_sessions.py`).

**Świadoma decyzja: pozostajemy przy Bearer + sessionStorage** (zamiast
pełnego przejścia na ciasteczka httpOnly). Powody: (a) zmiana dotyka
wszystkich żądań API, wymaga ochrony CSRF (token synchronizacyjny lub
podwójne ciasteczko) i przebudowy PWA/Service Workera — za duży zakres na
jedną rundę zmian; (b) ciasteczko httpOnly już dziś jest wystawiane przy
logowaniu, więc ścieżka migracji jest przygotowana. Plan ewentualnej
migracji: (1) przełączyć `_extract_token` na preferencję ciasteczka,
(2) dodać ochronę CSRF dla żądań mutujących, (3) usunąć token z odpowiedzi
logowania i z `sessionStorage`, (4) wygasić tryb Bearer po okresie
przejściowym. Ryzyko rezydualne do tego czasu: token w `sessionStorage`
jest odczytywalny przez XSS (mitygacje: brak zewnętrznych skryptów,
treści renderowane jako tekst przez React).

`tests/test_uploads.py`, `tests/test_files_security.py`,
`tests/test_payments.py` — łącznie 40+ asercji między kontami
(klient↔klient, obcy trener, admin, brak logowania, cofnięta zgoda,
wygasła relacja, załączniki wiadomości/bazy wiedzy).

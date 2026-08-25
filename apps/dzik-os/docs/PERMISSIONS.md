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
   oraz (b) pozytywnej decyzji `hos_engine.ConsentRegistry.authorize` dla
   **domeny danych, o którą pyta endpoint** (od 0.11.0 zgody są
   granularne — katalog kategorii w `consent_catalog.py`, mapowanie
   domen w `docs/ZGODY_MODEL.md`): `collaboration` (profil/dokumenty/
   płatności), `training_data` (plany/wyniki/harmonogram/cele),
   `health_data` (pomiary/raporty/obserwacje), `nutrition_data`
   (dieta/alergie), `progress_photos` (zdjęcia), `messages`
   (wiadomości). Cofnięcie zgody odbiera dostęp natychmiast i dotyczy
   tylko tej kategorii, mimo aktywnej relacji.
3. **Admin**: endpointy `/api/admin/*` nie zwracają danych zdrowotnych;
   próba wejścia admina na `/api/clients/{id}/...` kończy się 403/404.
   Każde użycie panelu admina emituje zdarzenie audytowe.
4. **Płatności** są metadanymi współpracy (nie danymi zdrowotnymi) —
   wymagają relacji i zgody `collaboration` (sensitive=False).
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
**T** = trener z **AKTYWNĄ** relacją i **nieocofniętą zgodą** domeny
danych endpointu (`resolve_client_access(domain=...)` — od 0.11.0 zgody
są granularne per kategoria; mapowanie endpoint→domena w
`docs/ZGODY_MODEL.md` §1); **T·rel** = trener z samą aktywną relacją
(bez bramki zgody); **T·own** = trener-właściciel rekordu
(`coach_id == aktor`); **A** = admin; ✗ = 404 (odmowa zasobowa) albo 403
(brak roli). Kolumna „Zgoda" oznacza zgodę kategorii właściwej dla
domeny endpointu (`sensitive` wynika z katalogu kategorii).

| Endpoint | Kto może | Zakres rekordów | Relacja | Zgoda | R/W |
|---|---|---|---|---|---|
| POST /api/auth/login, /logout; GET /api/auth/brand | publiczne | — | — | — | — |
| POST /api/auth/mfa/verify | publiczne (wymaga ważnego tokenu wyzwania z /login) | drugi krok logowania konta z MFA | — | — | W |
| POST /api/auth/activation/inspect, /activate | publiczne (wymaga ważnego tokenu zaproszenia) | aktywacja konta PENDING; jedna odpowiedź 404 dla każdego nieważnego tokenu | — | — | W |
| POST /api/auth/password-reset/request, /confirm | publiczne | reset hasła; odpowiedź żądania identyczna niezależnie od istnienia konta; limit per e-mail+IP | — | — | W |
| GET /api/auth/me; POST /api/auth/change-password | zalogowany | własne konto | — | — | R/W |
| GET /api/auth/mfa/status; POST /api/auth/mfa/setup, /enable, /disable, /recovery-codes/regenerate | zalogowany | MFA własnego konta (disable: tylko role bez obowiązku MFA) | — | — | R/W |
| GET /api/auth/security-events | zalogowany | historia zdarzeń bezpieczeństwa WŁASNEGO konta (metadane bez tokenów) | — | — | R |
| GET /api/auth/sessions; POST /api/auth/sessions/revoke-others | zalogowany | własne sesje | — | — | R/W |
| POST /api/auth/sessions/{session_id}/revoke | zalogowany | wyłącznie własna sesja (cudza aktywna → ACCESS_DENIED) | — | — | W |
| POST /api/coach/clients | COACH | nowe konto: PENDING + zaproszenie aktywacyjne + zgoda-deklaracja; istniejące konto: tylko aktywny CLIENT, **bez auto-zgody** (nadaje ją sam klient) i bez zaproszenia | tworzy/reaktywuje | — | W |
| POST /api/coach/clients/{id}/invitations, /invitations/cancel | COACH | zaproszenia wyłącznie własnego klienta w statusie PENDING (konto aktywowane → 409; cudzy/nieznany klient → 404) | tak (dowolny status) | — | W |
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
| GET /api/clients/{id}/onboarding | W, T | rozmowa startowa jednego klienta; odpowiedzi/pola WRAŻLIWE widoczne dla trenera tylko w zakresie zgody ich kategorii (inaczej `hidden`) | T: tak | T: tak (collaboration) | R |
| POST /api/clients/{id}/onboarding/start, /answer, /back, /pause, /summary, PUT /summary, POST /approve | **wyłącznie W** | własna rozmowa startowa (trener dostaje 404 — nie odpowiada za klienta) | — | — | W |
| GET /api/clients/{id}/onboarding/review | T | dane źródłowe + podsumowanie + niepewność per pole | tak | tak (collaboration) | R |
| POST /api/clients/{id}/onboarding/coach-approve | T | zatwierdzenie podsumowania jako podstawy planu; wymaga wcześniejszego zatwierdzenia przez klienta (inaczej 409) | tak | tak (collaboration) | W |
| GET /api/clients/{id}/interview (+ /review, POST /start, /answer, /back, /pause, /summary, PUT /summary, POST /approve, /coach-approve) | jak onboarding | **głęboki wywiad** — drugi przepływ tego samego mechanizmu (flow='deep', migracja 26): te same reguły dostępu, zgód i akceptacji co rozmowa startowa; różnice: zero AI (podsumowanie zawsze deterministyczne), nie tworzy celu, flagi wyboru przesiewu podnoszą safety_flag | jak onboarding | jak onboarding | R/W |
| POST/GET /api/clients/{id}/measurements; /metric-definitions | W, T (definicje: POST tylko T) | pomiary jednego klienta | T: tak | T: tak | R/W |
| GET /api/threads | strona wątku | własne wątki; trener: tylko AKTYWNA relacja + nieocofnięta zgoda (inaczej wątek znika też z listy) | T: tak | T: tak (sens.=False) | R |
| GET/POST /api/threads/{thread_id}/messages | strona wątku (`require_thread_party`) | jeden wątek (paginacja `limit`/`before`; kursor spoza wątku → 404) | T: tak | T: tak (sens.=False) | R/W |
| POST /api/threads/{thread_id}/read | strona wątku (`require_thread_party`) | oznaczenie cudzych wiadomości wątku jako przeczytane | T: tak | T: tak (sens.=False) | W |
| GET /api/threads/events | zalogowany (SSE, Bearer w nagłówku — token NIGDY w query) | kanał realtime WŁASNYCH wątków; każde doręczane zdarzenie przechodzi ponownie bramkę strony wątku, a ważność sesji jest sprawdzana w trakcie strumienia (unieważnienie → `session_expired` + zamknięcie); szczegóły: docs/WIADOMOSCI.md | T: tak | T: tak (sens.=False) | R |
| POST /api/files | W, T (upload dla klienta) | plik własny / klienta z relacji | T: tak | T: tak (write) | W |
| GET /api/files/{file_id} | patrz tabela „Pliki" niżej | jeden plik | wg tabeli | wg tabeli | R |
| POST /api/documents | T | dokument dla własnego klienta (plik musi należeć do klienta) | tak | tak (write) | W |
| GET /api/clients/{id}/documents, /photos | W, T | dokumenty/zdjęcia klienta | T: tak | T: tak | R |
| POST /api/payments/schedules | T·rel | pakiet dla własnego klienta | tak | nie (sens.=False) | W |
| GET /api/clients/{id}/payments | W, T·rel | płatności jednego klienta | T: tak | nie (sens.=False) | R |
| POST /api/payments/records/{record_id}/status; /schedules/{schedule_id}/records | T·own | wyłącznie rekordy własnych harmonogramów; /status tylko statusy ADMINISTRACYJNE (PENDING/OVERDUE/CANCELLED) — maszyna stanów egzekwowana serwerowo (422) | — | — | W |
| POST /api/payments/records/{record_id}/mark-paid, /refund, /adjust | T·own | „opłacona"/zwrot/korekta WYŁĄCZNIE przez dedykowane endpointy rejestrujące transakcję (kto+kiedy); idempotencja P11; cudzy rekord = 404 | — | — | W |
| POST /api/payments/transactions/{transaction_id}/reverse | T·own | korekta odwracająca omyłkę — nowy wpis REVERSAL, nigdy usunięcie; cudza transakcja = 404 | — | — | W |
| GET /api/payments/records/{record_id}/history | klient (self) lub T·own | historia statusów i transakcji jednego rekordu; osoby trzecie = 404 | — | — | R |
| GET /api/payments/reconciliation | COACH (tylko własne harmonogramy) | raport pojednania należności vs transakcje per okres | — | — | R |
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
| GET /api/coach/food-products/export | T·own | eksport CSV wyłącznie własnego katalogu (prawo wyjścia) | — | — | R |
| POST /api/coach/food-products/import | T·own | import CSV dopisuje/aktualizuje wyłącznie własne produkty — nigdy cudze (dopasowanie po nazwie w obrębie katalogu trenera) | — | — | W |
| POST /api/food-products/portion | zalogowany | kalkulator porcji: własny produkt (trener) albo AKTYWNY produkt trenera z AKTYWNĄ relacją (klient); 404 poza tym | tak (klient) | nie | R |
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
| Trener | aktywna relacja **i** aktywna zgoda kategorii pliku (`resolve_client_access(domain=_file_domain(...))`: zdjęcie progresu → `progress_photos`, dokument DIETA → `nutrition_data`, załącznik treningu → `training_data`, pozostałe → `collaboration`) — cofnięcie zgody odbiera dostęp również do plików już istniejących |
| Strona wątku wiadomości | plik jest załącznikiem wiadomości w wątku aktora; klient zawsze, trener przy AKTYWNEJ relacji i nieocofniętej zgodzie kategorii `komunikacja` (domena `messages` — dokładnie ten sam kontrakt co dostęp do treści wątku, `authz.require_thread_party`) |
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

## Przepisywanie tekstu ze zdjęcia — OCR (`/api/ocr`, od 0.27.0)

Pełny opis: `docs/OCR.md`. Reguły dostępu:

| Operacja | Kto | Warunek |
|---|---|---|
| `POST /api/ocr/tasks` | właściciel pliku albo osoba, która go wgrała | plik istnieje, nie jest usunięty i jest zdjęciem (JPG/PNG/WEBP); **cudzy plik = 404**; zlecenie „w imieniu klienta" (`client_id`) przechodzi przez `resolve_client_access(write, collaboration)`; zły typ = 422, za duży = 413, limit dzienny = 429 |
| `GET/DELETE /api/ocr/tasks/{id}` | `owner_user_id` albo `created_by` | **cudze zadanie = 404** (rozpoznany tekst bywa daną zdrowotną) |
| `POST /api/ocr/tasks/{id}/approve` | jw. + rola/dostęp do celu zapisu | PRODUKT → rola COACH (produkt powstaje w bazie tego trenera); DOKUMENT → `resolve_client_access(write, nutrition_data\|collaboration)` wg kategorii dokumentu; ponowne zatwierdzenie = 409 |
| `GET /api/ocr/status` | zalogowany | dla cudzego `client_id` — jak wyżej (`collaboration`) |

Wysyłka do zewnętrznego dostawcy modelu (tryb rozszerzony) wymaga
DODATKOWO aktywnej zgody `funkcje_ai` **podmiotu danych** — jedna reguła
`authz.ai_features_consent_active` dla wszystkich funkcji AI operujących
na **danych klienta** (jedyny wyjątek — czytanie własnego opisu ćwiczenia
przez trenera — jest opisany w kolejnej sekcji). Bez zgody
albo bez klucza działa silnik lokalny; to stan z jawnym powodem, nie błąd.

## Czytanie opisu ćwiczenia (`/api/coach/exercises/parse-description`, od 0.28.0)

Pełny opis: `docs/BAZA_CWICZEN.md` §10.

| Operacja | Kto | Warunek |
|---|---|---|
| `POST /api/coach/exercises/parse-description` | rola **COACH** | klient = **403**; opis > 20 000 znaków = 422; endpoint **niczego nie zapisuje** (jedyny efekt w bazie to licznik zużycia modelu w trybie rozszerzonym) |

**Uwaga na różnicę względem OCR:** tryb rozszerzony **nie** przechodzi
przez `authz.ai_features_consent_active`. Przetwarzany jest opis
ćwiczenia, czyli know-how trenera — klient w tym przepływie nie
występuje, więc nie ma czyjej zgody pytać. Bramką jest dostępność
dostawcy plus jawna decyzja trenera (kliknięcie). Gdyby do tego
przepływu miał trafić tekst opisujący konkretnego klienta, bramkowanie
MUSI wrócić do reguły `funkcje_ai` — patrz rejestr czynności poz. 14.

## Import biblioteki ćwiczeń (`/api/coach/exercises/import-library`, od 0.31.0)

Pełny opis: `docs/BAZA_CWICZEN.md` §11.

| Operacja | Kto | Warunek |
|---|---|---|
| `POST /api/coach/exercises/import-library?dry_run=true` | rola **COACH** | klient = **403**; **niczego nie zapisuje** — zwraca sam raport (podgląd przed zatwierdzeniem) |
| `POST /api/coach/exercises/import-library?dry_run=false` | rola **COACH** | klient = **403**; zapis **wyłącznie do katalogu zalogowanego trenera**; nigdy nie nadpisuje wypełnionych pól istniejącego ćwiczenia |

`dry_run` domyślnie **true** — wywołanie bez parametru nic nie zmienia.
Import nie dotyka katalogu innego trenera (`coach_id` bierze się z
sesji, nie z żądania), więc izolacja trenerów jest tu strukturalna, a
nie regułą do sprawdzenia. Zapis zostawia zdarzenie audytowe
`EXERCISE_LIBRARY_IMPORTED`.

**Widoczność notatki roboczej.** Pozycje z importu niosą
`review_reason` („opis techniki pochodzi z szablonu biblioteki”).
To pole wychodzi **wyłącznie na widoki trenera** (`GET/POST/PUT
/api/coach/exercises*`). Odpowiedzi dla klienta (`/api/me/exercises*`)
w ogóle go nie zawierają — dla klienta byłoby to ocena jakości
ćwiczenia wystawiona przez system, a system tu niczego nie ocenia.

## Import bazy z pliku — ćwiczenia i szablony (od 0.32.0)

Pełna specyfikacja formatu: `docs/IMPORT_BAZ.md`.

| Operacja | Kto | Warunek |
|---|---|---|
| `POST /api/coach/exercises/import-file?dry_run=true` | rola **COACH** | klient = **403**; **niczego nie zapisuje** — sam raport |
| `POST /api/coach/exercises/import-file?dry_run=false&mode=UZUPELNIJ\|ZASTAP` | rola **COACH** | klient = **403**; zapis **wyłącznie do bazy zalogowanego trenera** |
| `POST /api/coach/plan-templates/import-file?dry_run=` | rola **COACH** | klient = **403**; szablony mają `client_id = NULL`, więc import **nie dotyka planów klientów** |
| `GET /api/coach/exercises/export-file`, `GET /api/coach/plan-templates/export-file` | rola **COACH** | klient = **403**; eksport obejmuje wyłącznie własne zasoby trenera |
| `GET .../import-schema`, `GET .../import-example` | rola **COACH** | klient = **403**; zwracają sam kontrakt kolumn i wzór pliku — zero danych |

`dry_run` domyślnie **true** — wywołanie bez parametru nic nie zmienia.
`coach_id` bierze się z sesji, nigdy z żądania ani z pliku, więc izolacja
trenerów jest strukturalna, a nie regułą do sprawdzenia: plik nie ma jak
wskazać cudzej bazy.

**Czego w tych przepływach nie ma.** Import i eksport dotyczą know-how
trenera (ćwiczenia, szablony), a nie danych klientów — żaden z tych
endpointów nie czyta ani nie zapisuje danych zdrowotnych, więc nie
przechodzi przez `resolve_client_access` i nie wymaga niczyjej zgody.
Zdarzenia audytowe (`EXERCISES_IMPORTED`, `PLAN_TEMPLATES_IMPORTED`,
`EXERCISES_EXPORTED`, `PLAN_TEMPLATES_EXPORTED`) niosą nazwę pliku, tryb i
liczby — **nigdy treści wierszy**.

**Historia szablonu.** Import na istniejącym szablonie nie nadpisuje wersji,
tylko dokłada nową (`current_version_no + 1`) z powodem wskazującym plik.
Nie istnieje ścieżka, którą plik mógłby skasować albo podmienić wersję już
zapisaną.

## Zgody (rejestr wersjonowany, od 0.11.0 granularny per kategoria)

* **Kategorie zgód** (`consent_catalog.py` — pełny opis w
  `docs/ZGODY_MODEL.md`): odrębne, jednoznaczne kategorie z podziałem na
  wymagane (podstawa umowna) i opcjonalne (zgody właściwe, w tym art. 9
  dla danych zdrowotnych/żywienia/zdjęć oraz funkcji AI). Nie istnieje
  żadna ścieżka „zaakceptuj wszystko" dla niezależnych celów.
* Wiersz `consents` = jedna zgoda JEDNEJ kategorii: podmiot, odbiorca,
  kategoria, podstawa prawna, źródło (SUBJECT/ONBOARDING_DECLARATION),
  cel, domena, akcje, `allow_sensitive`, wersja tekstu zgody,
  `granted_at`, `confirmed_at`, `revoked_at`, `denied_at` (jawna odmowa).
  Wiersze z `category=NULL` to historyczne zgody parasolowe sprzed
  migracji nr 10 — hydratowane w pierwotnym, pełnym zakresie
  (`ConsentService._hydrate`).
* Zgoda klienta na **funkcje AI** (kategoria `funkcje_ai`) jest bramką
  KAŻDEJ wysyłki do dostawcy modelu: `POST /api/checkins/{id}/ai-summary`
  oraz wersji roboczej podsumowania rozmowy startowej
  (`POST /api/clients/{id}/onboarding/summary`). Decyzja trenera nie
  zastępuje zgody podmiotu danych; brak zgody = tryb deterministyczny
  z jawnym komunikatem, nie błąd (`docs/ONBOARDING_AI.md` §5).
* Zgody `dane_zdrowotne` i `zywienie_alergie` sterują też **zadawaniem
  pytań** w rozmowie startowej: bez nich kroki wrażliwe w ogóle nie
  powstają, a przy zatwierdzeniu podsumowania odpowiadające im pola nie
  są zapisywane do profilu (minimalizacja — `docs/ONBOARDING_AI.md` §1).
* Wycofanie zgody `przypomnienia` usuwa wszystkie subskrypcje push
  podmiotu (kanał doręczeń przestaje istnieć).
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

## Zaproszenia i aktywacja konta (od 0.11.0)

Trener NIE ustawia i NIE zna żadnego hasła klienta. Przepływ:

1. `POST /api/coach/clients` z **wyłącznie niezbędnymi danymi** (e-mail,
   imię). Powstaje konto `users.status=PENDING` (pole `password_hash="!"`
   nigdy nie zweryfikuje się w bcrypt; login dodatkowo filtruje
   `status=ACTIVE`) + relacja + zgoda-deklaracja z onboardingu (jak w P3)
   + wiersz `client_invitations`.
2. Token aktywacyjny: `secrets.token_urlsafe(32)` (≥32 B entropii);
   w bazie WYŁĄCZNIE hash SHA-256 (`token_hash`, wzorzec jak
   `auth_sessions`). Termin ważności `DZIK_INVITATION_TTL_DAYS` (7 dni),
   jednorazowy (`used_at`), anulowalny (`cancelled_at`). Ponowne wysłanie
   (`POST .../invitations`) najpierw anuluje wszystkie aktywne tokeny —
   nigdy nie istnieje więcej niż jeden ważny link.
3. Link `https://…/aktywacja#TOKEN` — token we **fragmencie** URL, nie w
   query: fragment nie jest wysyłany do serwera, więc nie trafia do logów
   dostępowych. Do API token idzie wyłącznie w body POST.
4. Klient otwiera link bez logowania (`/aktywacja`), widzi czyje konto
   aktywuje (`activation/inspect`) i SAM ustawia hasło (`/activate`);
   konto przechodzi PENDING→ACTIVE, zdarzenie `ACCOUNT_ACTIVATED`.
5. E-mail zaproszenia nie zawiera ŻADNYCH danych zdrowotnych — tylko
   imię, nazwę trenera/aplikacji i link.

**Kompromis NullNotificationProvider (świadomy):** dopóki operator nie
skonfiguruje prawdziwego dostawcy e-mail, `send_email` nic nie wysyła.
Jedynym kanałem doręczenia jest wtedy trener: odpowiedź API na
utworzenie/ponowienie zaproszenia zawiera `activation_link` („link do
przekazania”), który trener przekazuje klientowi zaufanym kanałem. To
oznacza, że trener zna link aktywacyjny (ale nadal NIE zna hasła — klient
ustawia je sam, a link jest jednorazowy i wygasa). Po skonfigurowaniu
prawdziwego dostawcy (`send_email` zwraca `True`) link idzie WYŁĄCZNIE
e-mailem i nie pojawia się w odpowiedzi API ani w UI. Link/token nigdy
nie trafia do audytu ani logów (testowane).

Konta seedu demo (`seed.py`) pozostają tworzone bezpośrednio jako ACTIVE
ze znanym jawnie hasłem demo — nowy przepływ dotyczy kont zakładanych
przez UI/API.

## Reset hasła (od 0.11.0)

* `POST /api/auth/password-reset/request {email}` — **zawsze ta sama
  odpowiedź 200** (treść i kształt identyczne dla konta istniejącego i
  nieistniejącego; różnice czasowe odpowiedzi to zaakceptowane ryzyko
  rezydualne MVP). Limit prób per e-mail ORAZ per IP
  (`DZIK_RESET_MAX_REQUESTS`/`DZIK_RESET_WINDOW_MIN`, licznik w pamięci
  procesu jak `login_rate_limiter`).
* Token: `secrets.token_urlsafe(32)`, w bazie tylko hash SHA-256
  (`password_reset_tokens`), TTL `DZIK_RESET_TOKEN_TTL_MIN` (60 min),
  jednorazowy; nowe żądanie unieważnia poprzednie tokeny.
* `POST /api/auth/password-reset/confirm {token,new_password}` — ustawia
  hasło i **unieważnia WSZYSTKIE sesje konta** (zdarzenie
  `PASSWORD_RESET_COMPLETED` z liczbą sesji, bez sekretów).
* Link resetu (`/reset-hasla#TOKEN`) idzie **wyłącznie e-mailem** — przy
  NullNotificationProvider nie ma bezpiecznego kanału doręczenia, więc
  samoobsługowy reset wymaga skonfigurowanego dostawcy (odpowiedź API
  celowo NIE zawiera linku — inaczej każdy znający e-mail mógłby przejąć
  konto). Do tego czasu awaryjna ścieżka to kontakt z trenerem/operatorem
  (dla konta PENDING: ponowne zaproszenie).

## MFA — weryfikacja dwuetapowa (od 0.11.0)

* **TOTP zgodny z RFC 6238** (HMAC-SHA1, krok 30 s, 6 cyfr) w czystym
  Pythonie (`dzik_os/totp.py`, stdlib `hmac`/`struct` — zero zależności);
  provisioning `otpauth://` do wpisania/zeskanowania w dowolnej aplikacji
  uwierzytelniającej. Sekret (base32, 160 bitów) jest pokazywany
  użytkownikowi wyłącznie raz przy konfiguracji; w odpowiedziach API,
  audycie i logach nigdy nie występuje. Kolumny `users.totp_*`.
* **Logowanie dwuetapowe**: poprawne hasło konta z MFA wydaje krótkotrwałe
  wyzwanie (`mfa_challenges`, tylko hash tokenu, TTL 5 min, jednorazowe);
  sesja powstaje dopiero po `POST /api/auth/mfa/verify` z poprawnym kodem
  TOTP (okno ±1 kroku) lub kodem odzyskiwania. Ochrona przed powtórnym
  użyciem kodu: `totp_last_counter` (kod z licznikiem ≤ ostatnio użytego
  jest odrzucany). Nieudane próby: limiter per konto + zdarzenie
  `LOGIN_MFA_FAILED` (bez kodu).
* **Wymuszenie dla COACH/ADMIN** (`DZIK_MFA_REQUIRED_ROLES`, domyślnie
  `COACH,ADMIN`): konto roli wymaganej bez skonfigurowanego MFA loguje
  się hasłem, ale do PIERWSZEJ konfiguracji dostaje wyłącznie ścieżki
  konfiguracji MFA (403 `MFA_SETUP_REQUIRED` wszędzie indziej — wzorzec
  identyczny z `PASSWORD_CHANGE_REQUIRED`); po konfiguracji kod jest
  wymagany przy każdym logowaniu, a wyłączenie MFA jest dla tych ról
  zablokowane (403). Dla CLIENT MFA jest opcjonalne (ta sama mechanika,
  z możliwością wyłączenia kodem). W testach wymuszanie jest globalnie
  wyłączone i włączane punktowo w `tests/test_mfa.py`; konto demo trenera
  na stagingu przy domyślnej konfiguracji skonfiguruje MFA przy pierwszym
  logowaniu (login hasłem nadal działa — zmienia się tylko zakres dostępu
  do czasu konfiguracji).
* **Kody odzyskiwania**: 10 kodów (alfabet bez znaków mylących, format
  `XXXXX-XXXXX`), pokazywane tylko raz; w bazie wyłącznie hashe SHA-256
  (`mfa_recovery_codes`); każdy jednorazowy; regeneracja (za kodem TOTP)
  unieważnia wszystkie poprzednie. Użycie kodu przy logowaniu emituje
  `MFA_RECOVERY_CODE_USED` z liczbą pozostałych.
* **WebAuthn/passkeys — następny krok (nieimplementowane)**: naturalne
  rozszerzenie po TOTP (odporność na phishing, klucz sprzętowy/biometria).
  Świadomie poza zakresem tej rundy: wymaga stabilnego origin i bezpiecznego
  magazynu poświadczeń publicznych po stronie backendu oraz przebudowy
  przepływu logowania — w obecnym stacku (Bearer + sessionStorage, patrz
  decyzja niżej) ryzyko złożoności na jeden commit jest za duże. Mechanika
  wyzwań (`mfa_challenges`) jest zaprojektowana tak, by drugi składnik
  WebAuthn mógł ją w przyszłości współdzielić.
* **Historia bezpieczeństwa**: `GET /api/auth/security-events` — logowania,
  nieudane MFA, resety, kody odzyskiwania, zakończenia sesji (metadane z
  pokwitowań; tokeny/kody/hasła nie występują). UI: karta „Historia
  bezpieczeństwa” obok „Aktywnych sesji”.

## Plan wycofania migracji 11

Migracja 11 jest czysto addytywna (3 kolumny `users.totp_*`, 4 nowe
tabele) — istniejące dane nie są modyfikowane. Wycofanie:

1. Wdrożyć poprzednią wersję kodu (stare zapytania nie dotykają nowych
   kolumn/tabel — mogą pozostać w schemacie bez szkody; SQLite i tak nie
   wspiera DROP COLUMN bez przebudowy tabeli).
2. Opcjonalne sprzątnięcie schematu: `DROP TABLE client_invitations,
   password_reset_tokens, mfa_recovery_codes, mfa_challenges` oraz
   `DELETE FROM schema_migrations WHERE version=11`.
3. Dane wymagające decyzji przy wycofaniu: konta `users.status='PENDING'`
   (zaproszone, nieaktywowane) nie mają hasła — stary kod ich nie założy
   ponownie; należy je usunąć (nie mają żadnych danych zdrowotnych) albo
   ręcznie nadać hasło startowe starym przepływem. Konta z aktywnym MFA
   po wycofaniu logują się samym hasłem (kolumny są ignorowane) — o
   wycofaniu trzeba poinformować użytkowników, bo obniża ochronę konta.
4. Audyt: zdarzenia `CLIENT_INVITED`/`ACCOUNT_ACTIVATED`/`MFA_*`/
   `PASSWORD_RESET_*` pozostają w łańcuchu (append-only, nie usuwamy).

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

## Wyzwania (od 0.18.0 — moduł prywatny)

Pełny opis modelu i zasad: `docs/WYZWANIA.md`. Reguły dostępu w skrócie:

* Wyzwania są WYŁĄCZNIE tylko-dla-zaproszonych; osoba spoza wyzwania
  (w tym obcy trener) dostaje na każdej ścieżce 404 z logowaną odmową
  `ACCESS_DENIED` (wzorzec IDOR jak w całej aplikacji).
* Trener zaprasza wyłącznie AKTYWNIE prowadzonych klientów
  (`active_relationship`) i moderuje wyłącznie wyzwania, które sam
  prowadzi (`require_owned_resource(owner_attr="organizer_id")`).
* Wyzwanie indywidualne klienta widzi tylko jego właściciel — także
  trener prowadzący dostaje 404.
* Wynik jednostkowy uczestnika widzą inni (łącznie z organizatorem)
  wyłącznie przy `share_result=true` (domyślnie false); ranking wymaga
  dodatkowo `ranking_opt_in=true` (domyślnie false). Ukrycie działa
  natychmiast.
* Zaproszony przed decyzją widzi wyłącznie zapowiedź wyzwania (bez listy
  uczestników i wyników) + wyjaśnienie widoczności.
* Dane zdrowotne nie wchodzą do modułu — jednostki wyniku to zamknięta
  allowlista neutralnych liczników; moduł nie czyta pomiarów, zdjęć,
  raportów ani żywienia (jedyny wyjątek: licznik ukończonych treningów
  za świadomą zgodą uczestnika per wyzwanie).
* Zdarzenia audytowe `CHALLENGE_*` niosą wyłącznie identyfikatory,
  liczniki i flagi — nigdy pseudonimy, notatki ani treści zgłoszeń.
* Testy: `tests/test_challenges.py` (20 testów, w tym macierz 404).

## Macierz uprawnień — dowód wykonawczy (od 2026-08-18)

Zewnętrzny audyt wskazał, że publiczne `401` nie dowodzi izolacji **między
prawidłowo zalogowanymi kontami**. Odpowiedzią jest macierz w
`backend/tests/access_matrix.py` + `backend/tests/test_access_matrix.py`.

**Nie jest to ręczna lista przypadków**, która zardzewiałaby przy pierwszym
nowym endpoincie. Macierz jest porównywana ze schematem OpenAPI aplikacji:

* każda z **182 operacji API** ma zadeklarowaną klasę dostępu;
* operacja bez deklaracji **przerywa build** — „kto ma tu dostęp" musi być
  świadomą decyzją, a nie przeoczeniem;
* wpis po usuniętej trasie też przerywa build (macierz nie gnije).

### Klasy dostępu

| Klasa | Znaczenie | Operacji |
|---|---|---|
| `PUBLIC` | bez logowania (logowanie, aktywacja, reset hasła, health) | 13 |
| `AUTHENTICATED` | zalogowany, wyłącznie własne dane (id z sesji) | 27 |
| `CLIENT_SCOPED` | `{client_id}` — sam klient albo jego trener za zgodą | 43 |
| `COACH_ONLY` | wymaga roli COACH | 25 |
| `ADMIN_ONLY` | wymaga roli ADMIN | 4 |
| `RESOURCE_SCOPED` | id zasobu — autoryzacja przez właściciela | 65 |

### Co jest weryfikowane wykonaniem

Testy wysyłają **prawdziwe żądania prawdziwymi kontami** — deklaracja może
kłamać (przy budowie macierzy heurystyka uznała `/api/metrics` za publiczne,
a endpoint ma `require_role("ADMIN")`). Aktorzy: klient A, klient B, trener
z relacją, **trener bez relacji**, administrator, niezalogowany.

| Test | Co dowodzi |
|---|---|
| `test_protected_operations_reject_anonymous` | żadna operacja poza `PUBLIC` nie działa bez tokenu |
| `test_client_scoped_denied_to_foreign_client` | klient B nie dotknie **żadnych** danych klienta A |
| `test_client_scoped_denied_to_unrelated_coach` | sama rola COACH nie wystarcza — bez relacji dostęp zamknięty |
| `test_coach_scoped_denied_to_unrelated_coach` | to samo dla tras trenerskich z `{client_id}` |
| `test_coach_only_denied_to_client` | klient nie użyje operacji trenerskich |
| `test_admin_only_denied_to_client_and_coach` | operacje administracyjne zamknięte dla pozostałych ról |
| `test_admin_cannot_reach_client_health_data` | administrator nie sięgnie po dane zdrowotne mimo najwyższych uprawnień technicznych |

**Siła dowodu:** wszystkie 43 operacje `CLIENT_SCOPED` kończą się twardą
odmową (403/404), a nie zatrzymaniem na walidacji ładunku. Wymagało to
generowania minimalnych poprawnych ciał żądań i parametrów query ze schematu
OpenAPI — bez tego FastAPI odrzucałby żądania kodem 422 *przed* sprawdzeniem
uprawnień, co niczego by nie dowodziło. Test pilnuje tego progu (100%), więc
regresja w generatorze też przerwie build.

**Testowane są wyłącznie ścieżki odmowy**, więc przebieg niczego nie zmienia
w danych; gdyby jakakolwiek operacja przeszła, to właśnie jest szukana luka.

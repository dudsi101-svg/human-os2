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
   renderuje wynik (kontrakt ADR-ARCH-003).

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
| Strona wątku wiadomości | plik jest załącznikiem wiadomości w wątku aktora; klient zawsze, trener tylko przy AKTYWNEJ relacji (bez bramki zgody — jak treść wiadomości) |
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

## Testy uprawnień

`tests/test_isolation.py`, `tests/test_consents.py`,
`tests/test_uploads.py`, `tests/test_payments.py` — łącznie 20+ asercji
między kontami (klient↔klient, obcy trener, admin, brak logowania).

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

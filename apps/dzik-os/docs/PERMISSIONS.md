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

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

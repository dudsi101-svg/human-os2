# Plan sesji: zgody dla trenera bez wcześniejszej historii (0.54.3)

**Gałąź:** `agent/zgody-bez-historii` (od `main` = dda1dec)
**Rola:** aktywny piszący
**Cel:** konto podopiecznego założone operatorsko (0.54.2) nie ma
żadnych wpisów zgód, a ekran Profil → Prywatność i zgody odgaduje
trenera WYŁĄCZNIE z historii zgód — bez historii przyciski „Udziel
zgody" dla kategorii trenerskich w ogóle się nie renderują. Właściciel
na żywo (7.09): „wyraziłem wszystkie zgody, które mogłem; części nie
dało się zaznaczyć", a trener widzi „brak zgody". Bramka zgód przy
pierwszym logowaniu też się nie pokazała (nie było deklaracji do
potwierdzenia). Dwa ubytki, obie strony do naprawy.

## Zamiar

1. **`GET /api/me/consents` zwraca `coaches`** — listę trenerów
   z AKTYWNEJ relacji podmiotu (id + nazwa). Profil bierze odbiorcę
   zgód trenerskich z relacji, nie z historii zgód (historia zostaje
   jako zapasowe źródło dla kont bez relacji, np. po zakończeniu
   współpracy). To naprawia konto już istniejące na produkcji bez
   dotykania bazy: właściciel wchodzi w Profil i udziela zgód sam.
2. **`dodaj_klienta` rejestruje deklaracje z onboardingu** dokładnie
   jak zaproszenie z panelu (`ONBOARDING_CATEGORIES`, źródło
   `ONBOARDING_DECLARATION`, niepotwierdzone) — pierwsze logowanie
   pokazuje bramkę zgód, klient potwierdza/odmawia każdej osobno.
   Dokłada też wątek wiadomości trener–klient (parytet z panelem).
3. **Testy**: `coaches` w odpowiedzi (klient z relacją, bez relacji);
   udzielenie zgody trenerskiej przez konto BEZ historii zgód → trener
   widzi `consent_active`; konto z `dodaj_klienta` ma po zalogowaniu
   deklaracje oczekujące dla 7 kategorii i wątek wiadomości.

## Świadomie nie robię

- zgód „za podmiot": narzędzie operatorskie rejestruje wyłącznie
  DEKLARACJE do potwierdzenia (jak trener w panelu) — nic nie jest
  potwierdzone bez decyzji klienta;
- migracji ani operacji na bazie produkcyjnej — konto właściciela
  naprawia się przez UI po deployu (punkt 1).

## Rezerwacje

- **Wersja: 0.54.3.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- ruff, pytest backend (SQLite), Core 275, spójność, tsc/build/
  helpers/E2E; uruchomienie na żywo: konto z `dodaj_klienta` →
  logowanie → bramka zgód; konto bez historii → Profil → „Udziel
  zgody" widoczne i działa (zrzut).

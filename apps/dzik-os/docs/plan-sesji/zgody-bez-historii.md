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

## Weryfikacja (wykonana)

- ruff czysto; **backend 871 passed, 1 skipped** (SQLite); **Core 275
  passed**; spójność czysto (13 kontroli); `tsc` czysto; `npm run
  build` — 88.7 kB gz (budżet 120); `test:helpers` 140/140; **E2E
  21/21**.
- **Uruchomienie na żywo** (świeży seed, port lokalny, prawdziwa
  przeglądarka na zbudowanym `dist/`):
  1. konto z `dodaj_klienta` → logowanie → wymuszona zmiana hasła →
     **bramka „Twoje dane, Twoja zgoda” pokazuje się** z odbiorcą
     „Lubelski Dzik” (4 wymagane, 3 opcjonalne); „Potwierdzam
     warunki wymagane” przenosi na Dzisiaj (zrzut w scratchpadzie);
  2. stan z produkcji odtworzony: skasowane WSZYSTKIE wpisy zgód tego
     konta → Profil → Prywatność i zgody: **10 przycisków „Udziel
     zgody”**, odbiorca „Lubelski Dzik” z relacji; udzielenie
     współpracy → plakietka „aktywna”; trener w `/api/coach/clients`
     widzi `consent_active: true` (przed: false).
- Odkryte przy okazji i poprawione w tej samej rundzie: relacja
  operatorska nie miała wątku wiadomości (obie strony bez możliwości
  napisania) — samonaprawa w liście wątków + test bez duplikatów.
- Korekta własnego założenia z planu (Karta §XII): deklaracja
  z onboardingu autoryzuje dostęp trenera JUŻ PRZED potwierdzeniem
  (tak działa zaproszenie z panelu od P7) — test opisuje to
  zachowanie zamiast wymyślonego „dostęp dopiero po potwierdzeniu”.

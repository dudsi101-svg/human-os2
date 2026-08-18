# Specyfikacja — zatwierdzone funkcje (rundy 6a–6c)

Zakres zatwierdzony przez założyciela 2026-08-18: punkty 1–9 z listy
propozycji. **Poza zakresem na ten moment:** AI-asystent na bazie wiedzy
(pkt 10) i realne płatności online (pkt 11) — wrócą osobną decyzją.

Każda funkcja przechodzi filtr konstytucyjny Human OS: żadna nie
wprowadza rankingów między ludźmi, autonomicznych decyzji AI ani metryk
zaangażowania jako celu; wszystkie istotne operacje trafiają do łańcucha
audytu.

## Runda 6a — szybkie strzały

### 1. Kopiowanie szablonu do klienta

* **Problem:** trener odtwarza szablon ręcznie w edytorze (10+ min).
* **API:** `POST /api/plans/{template_id}/copy-to/{client_id}` (COACH,
  `resolve_client_access(write)`); tworzy nowy `TrainingPlan` klienta z
  v1 = kopia bieżącej wersji szablonu, `reason` = „Skopiowano z szablonu
  «tytuł»”; zdarzenie `PLAN_CREATED` z `copied_from_template_id`.
* **UI:** karta klienta → Plan → przycisk „Z szablonu…” (wybór z listy);
  strona Szablony → akcja „Kopiuj do klienta” (wybór klienta).
* **Zasada:** kopia to zwykła wersja v1 z pełną proweniencją — żadnego
  współdzielenia obiektu szablonu (późniejsza edycja szablonu nie zmienia
  planów klientów).

### 2. Porównywarka zdjęć sylwetki (przed / po)

* **Problem:** zdjęcia z raportów leżą osobno; postęp najlepiej widać
  w zestawieniu.
* **API:** bez zmian — `GET /api/clients/{id}/photos` już istnieje.
* **UI:** komponent `PhotoCompare` (dwa `AuthImage` obok siebie, wybór
  daty z listy; domyślnie najstarsze vs najnowsze). U klienta na stronie
  Postępy; u trenera w zakładce Monitoring.
* **Zasada:** porównanie wyłącznie z własną historią (nigdy z innymi);
  zdjęcia pozostają za uwierzytelnionym API.

### 3. Timer przerw w treningu

* **Problem:** klient odmierza przerwy w osobnej aplikacji.
* **Zakres:** wyłącznie frontend. Przy każdym ćwiczeniu z polem `rest`
  (np. „120 s” / „2 min”) przycisk ⏱ startuje odliczanie; koniec =
  wibracja (`navigator.vibrate`) + sygnał wizualny. Parser toleruje
  formaty „120 s”, „2 min”, „90”.
* **Zasada:** zero telemetrii — timer niczego nie zapisuje.

### 4. Ankieta startowa (wywiad)

* **Problem:** wywiad zbierany na komunikatorze, przepisywany ręcznie.
* **Zakres:** ekran `/ankieta` dla klienta: cel główny (→ `POST goals`),
  doświadczenie, dni/sprzęt, preferencje żywieniowe, alergie, kontuzje
  i ograniczenia (pola wrażliwe → `sensitive=true`). Zapis istniejącym
  `PUT /api/clients/{id}/profile` (source=CLIENT_DECLARED, append-only).
  Na ekranie Dzisiaj baner „Uzupełnij wywiad startowy”, dopóki brakuje
  kluczowych pól.
* **Zasada:** dane wpisuje sam klient (proweniencja), nic nie jest
  obowiązkowe poza celem; pola zdrowotne oznaczone jako wrażliwe.

## Runda 6b — średni kaliber

### 5. Powiadomienia push (PWA)

* **Zakres:** Web Push (VAPID). Backend: `pywebpush`, klucze VAPID w
  konfiguracji (sekret środowiskowy, generowane raz), tabela
  `push_subscriptions` (endpoint, klucze, user_id, created_at, jawna
  zgoda w UI), wysyłka przy: nowej wiadomości, odpowiedzi trenera na
  raport, nowej wersji planu/diety; oraz pętla przypomnień (w procesie,
  co minutę) dla elementów harmonogramu z `time_of_day` i przypomnień
  `reminders`. Frontend: opt-in w Profilu („Włącz przypomnienia”),
  subskrypcja przez service worker.
* **Zasada:** opt-in, wyłączane jednym przyciskiem, treść push nie
  zawiera danych zdrowotnych (tylko „Masz nową wiadomość” itp.);
  liczba wysłanych push nigdy nie jest metryką sukcesu.

### 6. Strukturalny dziennik serii + wykresy siły

* **Zakres:** `WorkoutEntry.sets_json` (nowa kolumna, migracja):
  `[{"weight_kg": 80, "reps": 8}, ...]` obok dotychczasowego `result`
  (kompatybilność wstecz). UI logowania treningu: szybkie pola
  ciężar×powtórzenia per seria. Wykresy per ćwiczenie: objętość
  (suma kg×powt.) i szacowany 1RM (Epley: kg×(1+powt./30)) w czasie —
  rozszerzenie istniejących rekordów osobistych.
* **Zasada:** porównania wyłącznie do własnej historii; e1RM opisany
  jako szacunek, nie zalecenie obciążenia.

### 7. Terminarz konsultacji

* **Zakres:** tabele `consult_slots` (coach_id, start, duration,
  status OPEN/BOOKED/CANCELLED) i rezerwacja (client_id, booked_at).
  Trener wystawia sloty (powtarzalność prosta: pojedyncze terminy),
  klient rezerwuje/odwołuje (do X godzin przed), obie strony widzą
  nadchodzące konsultacje na Dzisiaj/dashboardzie; zdarzenia audytowe
  + (po 6b.5) push.
* **Zasada:** rezerwacja zawsze odwoływalna przez obie strony; brak
  kar/metryk za odwołania.

### 8. Cotygodniowy digest trenera

* **Zakres:** rozszerzenie pętli z 6b.5: raz w tygodniu (pon. rano)
  e-mail przez `notifications_provider` (jeśli skonfigurowany — nadal
  Null-by-default) + zawsze ekran „Podsumowanie tygodnia” w panelu:
  kto wysłał raport, kto zalega, płatności, obserwacje. Dane liczone
  tym samym kodem co dashboard (`_client_flags`).
* **Zasada:** digest = metadane operacyjne, bez rankingu klientów.

## Runda 6c — większe

### 9. Tryb offline na siłowni

* **Zakres:** kolejka zapisów w IndexedDB (odhaczenia harmonogramu,
  log treningu) gdy `navigator.onLine === false` lub fetch padnie;
  service worker Background Sync (z fallbackiem: retry przy powrocie
  aplikacji na pierwszy plan). UI: badge „offline — zapisano lokalnie,
  wyślę automatycznie”. Odczyt: ostatnia odpowiedź planu/harmonogramu
  cachowana do odczytu offline (bez cachowania cudzych danych;
  wyłącznie konto zalogowanego).
* **Zasada:** dane zdrowotne w IndexedDB tylko własne, kasowane przy
  wylogowaniu; kolejka widoczna dla użytkownika (nic nie wisi w tle
  bez jego wiedzy).

## Kolejność wdrażania

1. **6a (1–4)** — od razu.
2. **6b.5 push** → **6b.6 dziennik serii** → **6b.7 terminarz** →
   **6b.8 digest** (digest korzysta z pętli push).
3. **6c.9 offline** na końcu (najwięcej ruchomych części).

Każda runda: testy backendu + regresja Core + build frontendu +
przeklik Playwright + aktualizacja dokumentów + deploy ze smoke checkiem.

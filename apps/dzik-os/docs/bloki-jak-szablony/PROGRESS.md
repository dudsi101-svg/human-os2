# Bloki jak szablony — postęp, P2, otwarte pytania (0.76.0)

**Stan:** runda wykonana na gałęzi `agent/bloki-jak-szablony` (PR #79); plan sesji
`docs/plan-sesji/bloki-jak-szablony.md`. Polecenie właściciela z 14.09: „z bloków
(rozgrzewka, aeroby, rozciąganie — sprawdź, czy są; jeśli nie, uzupełnij) korzystać jak
z szablonów; dodać jednocześnie szablon treningowy i szablon z bloku, a nawet dwa”.

## 1. Co jest zbudowane

* Trzeci rodzaj bloku **CARDIO** (aeroby) z presetem liczonym silnikiem bez danych
  klienta; 9 wbudowanych (3 cele × 3 poziomy) — razem 21; własne bloki cardio z
  formularza (cel, poziom, urządzenia).
* „+ Cardio z bloku” w edytorze planu **i szablonu**.
* `copy-to` z opcjonalnymi blokami (maks. 3, po jednym na rodzaj, bez dublowania dnia),
  `from-blocks` (plan z samych bloków), karta „Przypisz plan” w karcie klienta.
* Luka 5 z 0.73.0 zamknięta: kopia szablonu waliduje `exercise_id` i zapisuje ślad
  `H_CARDIO`.

## 2. Otwarte pytania do właściciela (przyjęte domyślne)

1. **Mieszanki celów presetów** (`cardio/presety.py::MIESZANKI_CELOW`): regeneracja
   `0/0/1`, wydolność `0/1/0`, redukcja `0,6/0,1/0,3` (czysta redukcja dawałaby 50 min).
   Zmiana = jedna linia + przeładowanie bloków (istniejące wbudowane nie są nadpisywane —
   trener edytuje albo archiwizuje).
2. **Urządzenia domyślne** presetu: rowerek, bieżnia, wioślarz (3 z 5). Steper i bieżnia
   skos do wyboru w formularzu własnego bloku.
3. **Blok cardio = jeden dominujący cel** (bez suwaków w formularzu bloku). Alternatywa:
   trzy suwaki w formularzu bloku (jak w panelu) — odłożone, bo preset ma być prosty.
4. **`variant` dla CARDIO w bazie = pusty napis** (kolumna `NOT NULL` z migracji 39),
   w API `null`. Alternatywa: przebudowa tabeli w migracji (SQLite bez `DROP NOT NULL`) —
   odrzucona jako ryzyko bez korzyści dla użytkownika.
5. **Kopia szablonu z ćwiczeniem zarchiwizowanym po zapisie szablonu → 422** (ten sam próg,
   co nowa wersja planu). Alternatywa: kopiować i tylko ostrzec — do decyzji.
6. **Dzień z blokiem tego rodzaju już w szablonie nie jest dublowany** (raport
   `skipped_days`). Alternatywa: zastępować blok z szablonu wybranym — odrzucona (szablon
   jest świadomą decyzją trenera).

## 3. P2 zostawione (nienaprawione, do kolejnej rundy)

1. Karta „Przypisz plan” nie pozwala nazwać dni ani ustawić dni tygodnia dla „tylko bloki”
   (nazwy „Dzień 1…”, `weekday` null) — trener robi to w edytorze nowej wersji, klient w
   „Twoich dniach treningowych”.
2. Po przypisaniu szablonu z blokami plan klienta ma jedną wersję z powodem „Skopiowano z
   szablonu … + bloki: …” — nazwy bloków w powodzie mogą być długie (bez limitu w UI).
3. Dziennik cardio klienta dla pozycji z bloku działa jak dla cardio z suwaków (te same
   pola); brak osobnego E2E dla zapisu wykonania pozycji z bloku (pokryte testem API kształtu
   pozycji + istniejącym `cardio.spec.ts:67` dla pozycji cardio).
4. `WyborBloku` w edytorze pokazuje presety bez ud./min — po wstawieniu do planu klienta
   trener musi sam pamiętać o „+ Cardio”, jeśli chce zakres w ud./min (notka w panelu, bez
   automatu).
5. „Dzisiaj” (`Today.tsx`) renderuje cardio z bloku przez ten sam `PozycjaCardio` (kompakt) —
   nagłówek „z bloku” widoczny, pozycje opisowe też; nie ma osobnego testu E2E dla
   „Dzisiaj”.
6. Szkic planu (0.58.0) nie ma „+ Cardio z bloku” — jak w 0.73.0, bloki dodaje się w
   edytorze nowej wersji.

## 4. Plan kontra rzeczywistość

Patrz sekcja o tej nazwie w `docs/plan-sesji/bloki-jak-szablony.md` (uzupełniana na końcu
rundy razem z kosztem).

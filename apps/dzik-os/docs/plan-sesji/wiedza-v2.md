# Plan sesji: modernizacja zakładki Wiedza — P0 (0.56.0)

**Gałąź:** `agent/wiedza-v2` (od `main` = 1678754, po scaleniu #51)
**Rola:** jedyny piszący i integrator (decyzja właściciela 12–13.09);
recenzent kodu: Codex. Właściciel 13.09: „po każdym wykonanym zadaniu
scalaj PR, chyba że znalazłeś istotne błędy”.
**Źródło:** pakiet właściciela „PAKIET_WIEDZA_DLA_CLAUDE” 1.0 z 13.09.2026
(01 produkt, 02 ekrany, 03 architektura i kontrakty, 04 redakcja,
05 prompt, 06 treści startowe: 48 kart / 49 powiązań, 07 schematy
Draft 2020-12, 08 scenariusze F01–F15, 09 testy K01–K40, 10 źródła,
11 kontrola pakietu). Pakiet sam mówi: to specyfikacja i szkice, nie
audyt obecnej zakładki; treści bez zatwierdzenia eksperckiego.

## Co zastałem (inwentaryzacja, etap 1 z pliku 09)

- Obecna zakładka `/wiedza` klienta: trzy karty — „Artykuły” (materiały
  trenera `knowledge_items`, broadcast do aktywnych podopiecznych),
  „Ćwiczenia” (baza trenera `exercises`, filtry po API), „Produkty”
  (katalog `food_products`). Trener edytuje to wszystko w `/trener/wiedza`.
- Plany: `training_plan_versions` niemutowalne, `version_no` rosnące
  = naturalna `plan_revision`; ćwiczenie w wersji ma `exercise_id`
  z bazy trenera (opcjonalnie), a plany z konfiguratora — `None`.
- Ślad decyzji nie istnieje nigdzie: żaden plan (trenerski ani
  z konfiguratora) nie ma zapisanego uzasadnienia poza polem `reason`
  wersji. Konfigurator 0.55.0 zapisuje pełny wynik silnika w treści
  wersji, ale nie w formie DecisionTrace.
- Stan bezpieczeństwa: aplikacja nie ma globalnej blokady treningu;
  jedynym sygnałem jest `pain_flag` w zapisie sesji.
- Logi żądań (`observability.py`) zapisują szablon trasy, nie query —
  wyszukiwanie i tak pójdzie w body POST, żeby zapytanie nie trafiło do
  żadnego logu pośredniego.

## Decyzje dopasowujące pakiet do Dzik OS

1. **Jedna biblioteka, redaktorem jest trener.** Dzik OS jest aplikacją
   jednego trenera (limit 10 klientów). Karty wiedzy są wspólne; rolę
   „recenzent/wydawca” pełni konto COACH (tematy treningowe i
   żywieniowe to jego odpowiedzialność, tak jak dziś przy
   `knowledge_items`). Publikacja wymaga: wszystkich pól, źródeł,
   prawdziwego recenzenta (id konta trenera, jego nazwa wyświetlana),
   daty recenzji i daty kolejnego przeglądu. Bez tego serwer odmawia.
2. **Szkice z pakietu importuję jako `draft`** idempotentnie po
   `(id, revision)`; produkcja ich nie pokazuje. Tryb demonstracyjny:
   `DZIK_WIEDZA_SZKICE=true` pokazuje szkice z widocznym oznaczeniem;
   w `DZIK_ENV=production` flaga jest ignorowana (zawsze `false`).
   `.env.example` i seed demo mają `true`.
3. **Flaga `DZIK_WIEDZA_V2`** (domyślnie `true`): przy `false`
   `/api/wiedza/*` odpowiada 404, a klient renderuje dotychczasową
   zakładkę (zachowaną jako `KnowledgeLegacy.tsx`). Wycofanie = flaga;
   ślady i zakładki zostają.
4. **Mapa migracji starych treści** (bez usuwania): materiały trenera
   (`knowledge_items`) pojawiają się w nowej Wiedzy jako blok
   „Od trenera” w części wynikającej z kategorii (Trening→Trening,
   Dieta/Suplementacja→Odżywianie, Regeneracja→Postępy i regeneracja,
   reszta→Podstawy i źródła); baza ćwiczeń trenera = część Atlasu;
   katalog produktów = w Odżywianiu. Stary adres `/wiedza` zostaje;
   stare karty mają odpowiedniki `?czesc=…`.
5. **Ślad decyzji zapisują właściciele decyzji, w tej samej
   transakcji:** (a) konfigurator przy `zapisz` — `training_frequency`
   (H_LAYOUT), `exercise_prescription` per ćwiczenie (H_VOLUME: serie,
   zakres, RIR, przerwa, z faktami: poziom, zaangażowanie, korekty
   regeneracji/przerwy/czasu), `plan_change` (H_TIME/H_FATIGUE tylko
   gdy wystąpiły); (b) trener przy nowej wersji planu treningowego —
   `plan_change` z pochodzeniem `professional` i oryginalnym `reason`;
   (c) trener przy wersji planu diety — `energy_target` i
   `macro_target` (`professional`, wartości z treści wersji, notatka
   = `reason`). Stare plany: `missing_trace`, bez rekonstrukcji.
   Konfigurator dostaje w eksporcie `konfigurator_id` ćwiczenia
   (addytywnie), żeby atlas pakietu wiązał się po stabilnym id.
6. **Stan bezpieczeństwa (reguła produktu, nie diagnoza):** jeśli po
   dacie śladu klient zgłosił ból (`pain_flag`) w sesji tej wersji
   planu w ostatnich 7 dniach, wyjaśnienie ma status `restricted`
   z akcją „Napisz do trenera” i edukacją ogólną (k-safety). Brak
   automatycznego doboru zamiennika.
7. **Bez LLM.** Renderer deterministyczny z rejestru reguł; brak
   przycisku „wygeneruj powód”.
8. **Zdarzenia pomiarowe:** tylko w audycie Human OS jako
   `KNOWLEDGE_*` z publicznymi id artykułu/rewizji i kodem statusu —
   bez zapytań, faktów ani wartości planu.

## Zamiar P0 (zakres tej rundy)

- `dzik_os/wiedza/`: `dane/` (treści startowe, schematy, źródła,
  scenariusze), `tresci.py` (repozytorium kart, powiązania, import,
  publikacja/wycofanie), `slad.py` (DecisionTrace + zapis z
  konfiguratora i wersji planów), `reguly.py` (rejestr reguł:
  wymagane fakty, szablony po polsku), `resolver.py` (10 kroków
  z pliku 03, statusy explained/general_only/missing_trace/
  insufficient_data/inconsistent_data/stale_context/restricted),
  `kanal.py` (ranking „Dla Ciebie” bez ML), `szukaj.py` (polskie
  znaki, aliasy, literówki).
- Migracja **28**: `wiedza_artykuly`, `wiedza_powiazania`,
  `wiedza_slady`, `wiedza_zakladki`, `wiedza_odczyty`, `wiedza_opinie`.
- API `/api/wiedza/*` (klient) i `/api/coach/wiedza/*` (redakcja),
  wpisy w macierzy dostępu. Wyjaśnienie: `POST /api/wiedza/wyjasnij`
  (plan_id, plan_revision, target_type, target_id, tryb) → 200 z
  ExplanationResult; 404 bez trace_id dla cudzego planu; 409
  `STALE_PLAN` tylko dla trybu bieżącego z inną rewizją wejściową
  (wynik `stale_context` w treści).
- Frontend: `pages/client/Wiedza.tsx` (W1 Dla Ciebie, W2 biblioteka,
  W3 karta, W5 atlas, W6 historia, W7 szukaj/zapisane), komponent
  `Dlaczego` (panel dolny/boczny, fokus wraca, stan planu nietknięty)
  w `Plan.tsx` (ćwiczenie i częstotliwość) i `Nutrition.tsx` (kalorie
  i makro); `KnowledgeLegacy.tsx` przy wyłączonej fladze.
- Testy: resolver na F01–F15 z pakietu + K03–K17, K36, K38 (backend);
  API K01, K06–K11, K18–K21, K25–K30, K33–K34, K40; schematy Draft
  2020-12 dla treści startowych, każdego zapisanego śladu i każdej
  odpowiedzi; E2E `wiedza.spec.ts` — przepływy 1 (sesja → Dlaczego →
  karta → powrót) i 5 (bez planu → szukaj → karta → zapisz).
- Dokumentacja: `docs/WIEDZA.md` (raport wdrożenia: obsługiwane typy
  elementów, adaptery, treści robocze vs opublikowane, rollback),
  CHANGELOG 0.56.0, STAN_PRZEKAZANIA, RELEASE_STATUS, README, wersje.

## Świadomie nie robię

- P1 (ścieżki nauki, rekomendacje ze zdarzeń, lepsze wyszukiwanie)
  i P2 (asystent) — osobny backlog;
- adaptera posiłku/porcji/składnika/zamiennika (moduł diety nie ma
  śladu obliczeń — K15/K17 dają kartę ogólną i jawny brak);
- multimediów w atlasie (pakiet ich nie dostarcza; `media=null`);
- pilotażu użytkowników ani przeglądu eksperckiego — nie deklaruję;
- usuwania starej tabeli `knowledge_items` ani jej ekranu trenera.

## Rezerwacje

Migracja nr **28**, wersja **0.56.0**, pliki: `backend/dzik_os/wiedza/**`,
`backend/dzik_os/routers/wiedza.py`, `backend/dzik_os/routers/konfigurator.py`
(hook śladu), `routers/plans.py`, `routers/nutrition.py` (hook śladu),
`konfigurator/eksport.py` (`konfigurator_id`), `frontend/src/pages/client/Wiedza.tsx`,
`KnowledgeLegacy.tsx`, `components/Dlaczego.tsx`, `Plan.tsx`, `Nutrition.tsx`,
`e2e/wiedza.spec.ts`, `docs/WIEDZA.md`.

## Weryfikacja wykonana

(uzupełnię po rundzie)

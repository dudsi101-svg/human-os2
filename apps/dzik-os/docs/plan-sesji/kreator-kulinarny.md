# Plan sesji: kreator diety oparty na spójnych daniach — P0 (0.57.0)

**Gałąź:** `agent/kreator-kulinarny` (od `main` = 58a545f po scaleniu
#52; jeden `[WRITER]` naraz).
**Rola:** jedyny piszący i integrator; recenzent: Codex. Właściciel
13.09: „nie zatrzymuj pracy… jeśli nie znajdziesz błędów scalaj po
każdym PR”.
**Źródła:** (1) pakiet „PAKIET_DIETA_KULINARNA_DLA_CLAUDE” 1.0 (13.09):
specyfikacja, kontrakty i 32 przypadki D01–D32, profile, 12 szkiców,
źródła, kontrola; (2) pakiet „IMPLEMENTACJA_KREATORA_DIETY_300” (13.09,
przysłany w trakcie rundy, nadrzędny): działający silnik referencyjny
`engine.py` (1.0.0) z 27 testami, 300 szkiców wariantów w 30 rodzinach,
73 produkty BEZ wartości odżywczych, instrukcja integracji
(`docs/kulinaria/INTEGRACJA.md`). Oba pakiety mówią to samo: receptury
bez makro, bez testu kuchennego, bez recenzji; nie są zbilansowanym
planem. Właściciel: „Nie nazywaj katalogu 300 rekordów bazą 300
przetestowanych dań”.

## Co zastałem

- Obecny kreator (`diet_wizard.py`, 0.44–0.48): dobór PRODUKTÓW z grup
  makro pod procenty — dokładnie problem opisany w §1 pakietu (zestawy
  liczb, nie dania). Zostaje jako droga „Wygeneruj z produktów”
  (porównanie stary/nowy jest wymogiem pakietu).
- Baza produktów: wbudowany katalog ~2000 pozycji (`food_catalog_data*`),
  wartości uśrednione z tabel, stan produktu w nazwie i `note`,
  błonnik częściowo znany, brak mikroskładników, brak alergenów.
- Plan diety = `NutritionPlanVersion.content_json` z `meals`
  (`list[dict]` — słownik przepuszcza dodatkowe klucze), wersjonowany.
- Wiedza 0.56.0: kontrakt DecisionTrace i reguła MEAL_PREFERENCE gotowe;
  cele `meal`/`portion` dziś dają `missing_trace`.

## Decyzje dopasowujące pakiety do Dzik OS

1. **Silnik referencyjny bez zmian** (`dzik_os/kulinaria/engine.py`,
   kopia 1:1 z pakietu 300, `# ruff: noqa`) jako serwis domenowy:
   tryby `preview`/`production`, dobór CAŁYCH dań w zatwierdzonych
   wariantach porcji, beam search (szerokość 80) po dniach, ponowna
   kontrola dnia (`audit_plan`), lista zakupów. Zachowuję 27 testów
   pakietu 1:1 (`tests/test_kulinaria_engine.py`) — własny solver
   z pierwszej wersji planu (silnik.py/receptury.py) usunąłem, bo
   pakiet 300 jest nadrzędny i już przetestowany.
2. **Narzędzie trenera, propose-only.** `generuj` liczy i nic nie
   zapisuje; `zapisz` tworzy nową wersję planu diety klienta ze śladem
   decyzji w tej samej transakcji; klient widzi posiłki (składniki,
   kroki) i „Dlaczego to danie?”.
3. **Adapter żywieniowy = wbudowany katalog Dzik OS** przez jawne
   mapowanie 73 produktów pakietu (`dane/mapowanie_produktow.json`,
   status „do przeglądu dietetyka”): 68 z wartościami na 100 g
   w ZGODNYM stanie (surowy/suchy/ugotowany/odsączony), 5 jawnie bez
   wartości (limonka, ziemniak, bazylia, pietruszka, imbir — brak
   błonnika albo pozycji w bazie) → silnik traktuje je jako nieznane.
   Definicja węglowodanów bazy „ogółem z błonnikiem” — przyjęta, nie
   potwierdzona; silnik normalizuje `total − fiber`. Alergeny
   „zweryfikowane” tylko dla produktów jednoskładnikowych; złożone
   (chleb, hummus, tortilla…) wymagają etykiety → przy zadeklarowanej
   alergii odpadają (bezpieczna strona). Bez wartości z pamięci modelu.
4. **Bramka serwera, nie deklaracja klienta.** `screening_status`
   liczony z jawnych poświadczeń trenera o zakresie (dorosły, bez
   ciąży/karmienia, bez diety leczniczej, bez leków glikemicznych przy
   ograniczeniu węglowodanów); brak = `unknown` → `needs_review`.
   `targets_reference` w produkcji = id AKTYWNEJ wersji planu diety
   klienta; granice dzienne z tolerancji podanej przez trenera.
5. **Publikacja receptur = rewizje w bazie** (`kulinaria_receptury`,
   migracja 29): produkcja widzi tylko `published` z pełnym przeglądem
   (test kuchenny, dietetyk, `reviewer_id` = trener, `expires_on`)
   i zatwierdzonymi wariantami porcji — zapisanymi jawnie przez
   trenera, nigdy przez zmianę flagi w pliku. Dziś opublikowanych: 0,
   więc produkcja = `insufficient_catalog` (pokazujemy brak pokrycia,
   nie omijamy filtra). Podgląd ze szkiców jest zawsze dostępny
   trenerowi (to narzędzie kulinarne, nie ocena żywieniowa), a zapis
   podglądu do klienta wymaga jawnego `potwierdzam_szkice`.
6. **Ślad decyzji** (kontrakt Wiedzy): reguła
   `CURATED_VARIANT_SELECTION` 1.0.0 z faktów silnika
   (`decision_trace`), `target_type=meal`, `target_id=d{dzień}:m{i}`,
   `plan_kind=nutrition`, zapis w transakcji wersji; zamiana dania =
   `zamiana/podglad` bez mutacji + `zamiana/zatwierdz` z kontrolą
   rewizji (409 `STALE_PLAN`), ponowną kontrolą całego dnia i nową
   wersją planu (stare rewizje zostają).
7. **Bez LLM**, bez zdjęć, bez fikcyjnych recenzji i dat.

## Zamiar P0

- `dzik_os/kulinaria/`: `engine.py` (referencyjny), `dane.py`
  (ładowanie pakietu + wersje), `adapter.py` (produkty, receptury
  z nadpisaniami publikacji, raport mapowania), `serwis.py`
  (konfiguracja z formularza, generowanie, treść wersji, ślady,
  zamiana, publikacja, porównanie ze starym generatorem).
- Migracja **29**: `kulinaria_receptury`.
- API trenera `/api/coach/kulinaria/*`: `profile`, `receptury`,
  `receptury/{id}` (+`publikuj`, `wycofaj`), `pokrycie`, `generuj`,
  `zapisz`, `zamiana/podglad`, `zamiana/zatwierdz`, `porownanie`.
  Wszystko `COACH_ONLY` + `resolve_client_access(nutrition_data)`
  dla klienta; limity rozmiaru wejścia w schematach.
- Wiedza: reguła `CURATED_VARIANT_SELECTION`; klient widzi „Dlaczego?”
  przy posiłku z kreatora dań.
- Frontend: trzecia droga „Ułóż z dań” w zakładce Dieta trenera
  (formularz osi, poświadczenia zakresu, podgląd menu dzień po dniu,
  receptura, lista zakupów, statusy silnika słowami, zapis do klienta),
  redakcja receptur (publikuj z poświadczeniami), klient: składniki
  i kroki posiłku + „Dlaczego?”.
- Testy: 27 silnika + adapter + API (autoryzacja, brak pokrycia,
  zapis ze śladem, zamiana z 409, publikacja bez fikcji) + macierz,
  E2E: trener generuje podgląd i zapisuje; klient widzi wyjaśnienie.
- Dokumentacja: `docs/KULINARIA.md` (raport: kod gotowy / dane
  zweryfikowane / dane robocze / brakujące moduły, wyniki testów,
  pokrycie każdej diety), CHANGELOG 0.57.0, STAN, RELEASE_STATUS,
  README, wersje.

## Świadomie nie robię

- testów kuchennych, oceny dietetyka, testów produkcyjnych — nie
  deklaruję; receptury pozostają szkicami do publikacji przez trenera;
- zdjęć dań, kalendarza zakupów, budżetu pieniężnego (brak danych
  o cenach), diet leczniczych, low FODMAP, nerkowej;
- 28-dniowego kalendarza z resztkami (brak polityk przechowywania).

## Rezerwacje

Migracja nr **29**, wersja **0.57.0**, pliki: `backend/dzik_os/kulinaria/**`,
`routers/kulinaria.py`, `wiedza/reguly.py` (+1 reguła),
`frontend/src/pages/coach/KreatorDan.tsx`, `pages/coach/Knowledge.tsx`
(droga), `pages/client/Nutrition.tsx` (Dlaczego przy posiłku),
`e2e/kulinaria.spec.ts`, `docs/KULINARIA.md`, `docs/kulinaria/*`.

## Weryfikacja wykonana

Lokalnie 13.09 (przed PR): ruff czysto; backend 1648 passed, 1 skipped
(w tym 27 testów pakietu 1:1, 2 adaptera, 7 API, macierz z 11 nowymi
operacjami); Core 275; frontend tsc + build (89.3 kB / 120 kB) +
test:helpers; E2E Playwright 25 passed (24 + kulinaria.spec.ts);
e2e/test_a11y.mjs czysto; tools/spojnosc.py 13/13. Przeklik na żywo:
formularz → podgląd (draft_preview, receptura, lista zakupów) → zapis
z potwierdzeniem → zamiana → tryb produkcyjny = „za mało receptur po
filtrach” → biblioteka receptur; klient: „Dlaczego to danie?” →
„Decyzja: …”. Pokrycie każdej diety i statusy: `docs/KULINARIA.md`.
CI PR #53 (3c0e97a): ALL_GREEN (backend 3.11/3.12/postgres, quality 3.11–3.13, frontend, e2e); scalone 13.09 (6c3d078). Deploy 0.57.0 padł z powodu braku plików JSON w obrazie (błąd pakietowania z 0.56.0, nie z tej rundy) — naprawione w 0.57.1 (`hotfix-pakiet-dane.md`).

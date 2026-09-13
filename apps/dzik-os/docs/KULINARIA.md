# Kreator dań (0.57.0) — raport wdrożenia P0

**Źródła:** pakiet właściciela „PAKIET_DIETA_KULINARNA_DLA_CLAUDE” 1.0
(specyfikacja, kontrakty D01–D32, profile, kontrola) oraz nadrzędny
pakiet „IMPLEMENTACJA_KREATORA_DIETY_300” (silnik referencyjny
`engine.py` 1.0.0 z 27 testami, 300 szkiców wariantów w 30 rodzinach,
73 produkty bez wartości odżywczych, instrukcja integracji —
`docs/kulinaria/INTEGRACJA.md`). Runda: gałąź `agent/kreator-kulinarny`,
plan sesji `docs/plan-sesji/kreator-kulinarny.md`.

**Jedno zdanie o stanie:** kod jest gotowy i przetestowany, ale katalog
300 rekordów to **300 szkiców wariantów, nie 300 przetestowanych dań** —
żadna receptura nie jest opublikowana, więc tryb produkcyjny (z makro)
uczciwie zwraca „za mało receptur po filtrach”, a trener dostaje podgląd
kulinarny bez wartości odżywczych.

## 1. Kod gotowy (zaimplementowany, przetestowany)

| Element | Gdzie | Stan |
|---|---|---|
| Silnik referencyjny (dobór całych dań, warianty porcji, beam search po dniach, ponowna kontrola dnia, lista zakupów) | `backend/dzik_os/kulinaria/engine.py` | kopia 1:1 z pakietu, bez modyfikacji (`# ruff: noqa`); 27 testów pakietu przechodzi 1:1 |
| Adapter żywieniowy (produkty pakietu → wbudowana baza Dzik OS) | `kulinaria/adapter.py`, `dane/mapowanie_produktow.json` | 66/73 produktów z wartościami na 100 g w zgodnym stanie; 7 jawnie nieznanych (patrz §3) |
| Biblioteka receptur z publikacją w bazie | `adapter.receptury`, model `KulinariaReceptura`, migracja 29 | produkcja widzi tylko `published` z pełnym przeglądem i zatwierdzonymi wariantami |
| Warstwa integracji (konfiguracja z formularza, screening z poświadczeń, cele z planu klienta, treść wersji, ślady, zamiana, publikacja, porównanie ze starym generatorem) | `kulinaria/serwis.py` | — |
| API trenera (11 operacji, wszystkie `COACH_ONLY` + `resolve_client_access(nutrition_data)`) | `routers/kulinaria.py`, `tests/access_matrix.py` | `profile`, `receptury[/{id}][/publikuj|/wycofaj]`, `pokrycie`, `generuj`, `zapisz`, `zamiana/podglad`, `zamiana/zatwierdz`, `porownanie` |
| Ślad decyzji dla Wiedzy (`meal`, `d{dzień}:m{i}`, reguła `CURATED_VARIANT_SELECTION` 1.0) | `serwis.zapisz_slady`, `wiedza/reguly.py` | zapis w tej samej transakcji co wersja planu; klient widzi „Dlaczego to danie?” ze statusem `explained` |
| Ekran trenera „Ułóż z dań” (formularz osi, poświadczenia zakresu, statusy słowami, menu dzień po dniu, receptura, lista zakupów, zapis z potwierdzeniem szkiców, zamiana, biblioteka receptur z publikacją) | `frontend/src/pages/coach/KreatorDan.tsx` | trzecia droga w zakładce Dieta |
| Ekran klienta (posiłki z menu, oznaczenie szkicu, lista zakupów, „Dlaczego to danie?”) | `frontend/src/pages/client/Nutrition.tsx` | — |
| Testy | `tests/test_kulinaria_engine.py` (27 pakietu + 2 adaptera), `tests/test_kulinaria_api.py` (7), macierz dostępu, `e2e/kulinaria.spec.ts` (1) | wszystkie zielone (patrz §5) |

Bez modelu językowego; kreator nie wymaga klucza AI. Zdarzenia audytu
niosą metadane menu (dni, posiłki, tryb, status), bez alergenów
i wykluczeń.

### Bramki serwera (instrukcja pakietu)

* `screening_status` NIE jest deklaracją klienta: serwer liczy go
  z czterech jawnych poświadczeń trenera (dorosły, bez ciąży/karmienia,
  bez diety leczniczej, bez cukrzycy/leków glikemicznych — to ostatnie
  wymagane przy low carb/keto). Brak odpowiedzi = `unknown` →
  `needs_review`. Silnik wymaga `cleared` także w podglądzie.
* `targets_reference` w trybie produkcyjnym = id aktywnej wersji planu
  diety klienta (kcal, białko, tłuszcz, węglowodany); granice dzienne
  z tolerancji podanej przez trenera (1–50 %). Bez planu z kompletnymi
  celami → 422 („kreator nie wymyśla celów”). Założenie zapisane
  w metadanych: `carbs_g` planu = węglowodany dostępne.
* Zapis podglądu nie zeruje celów: kcal i makro z aktywnej wersji planu
  klienta przechodzą do nowej wersji (to cele trenera, nie wynik
  silnika), a sekcja wersji mówi wprost, że nie zostały sprawdzone
  względem menu. Dzięki temu tryb produkcyjny po zapisie podglądu nadal
  widzi cele (znalezione w przekliku, pokryte testem API).
* Zapis podglądu ze szkiców wymaga `potwierdzam_szkice=true`
  (409 `DRAFT_CONFIRMATION_REQUIRED` bez niego). Zamiana dania:
  `podglad` bez mutacji, `zatwierdz` z kontrolą rewizji
  (409 `STALE_PLAN`), ponowną kontrolą całego dnia (409 `SWAP_REJECTED`)
  i nową wersją planu; stare rewizje zostają.

## 2. Dane zweryfikowane

* **Wartości odżywcze:** wyłącznie z wbudowanej bazy produktów Dzik OS
  (`food_catalog_data`, `source_id = dzik_os_food_catalog`), przez jawne
  mapowanie nazwa → produkt pakietu z kontrolą stanu (surowy / suchy /
  ugotowany / odsączony). Żadna wartość nie pochodzi z pamięci modelu.
* **Normalizacja węglowodanów:** baza podaje „ogółem”; silnik liczy
  dostępne = ogółem − błonnik. Produkt bez błonnika w bazie zostaje
  nieznany (nie zero).
* **Alergeny „zweryfikowane”** tylko dla produktów jednoskładnikowych
  (skład znany z natury). Produkty złożone (chleb, tortilla, hummus,
  pasta curry, mleko kokosowe…) mają alergeny „nieznane” → przy
  zadeklarowanej alergii odpadają (D08: nieznane ≠ bezpieczne).

## 3. Dane robocze (do przeglądu, nie do produkcji)

* **300 receptur = szkice** (`status: draft`, bez testu kuchennego,
  bez recenzji dietetycznej, bez recenzenta i terminu). Publikacja
  wymaga jawnych poświadczeń trenera w ekranie „Biblioteka receptur”
  (test kuchenny, przegląd dietetyczny, alergeny z etykiet, ważność,
  zatwierdzone warianty porcji). Kreator nie wpisuje fikcyjnych dat ani
  nazwisk. **Opublikowanych dziś: 0.**
* **Mapowanie produktów** ma status „do przeglądu dietetyka”.
  7 produktów bez wartości: limonka, ziemniak, bazylia, pietruszka,
  imbir (brak pozycji albo błonnika w bazie) oraz kakao i oregano
  (wiersz bazy niespójny: błonnik > węglowodany ogółem — adapter nie
  zgaduje, która definicja była użyta). Receptury z tymi produktami
  liczą się w podglądzie, ale w produkcji odpadają jako
  `unverified_nutrition`.
* **Definicja węglowodanów bazy** („ogółem z błonnikiem”) — przyjęta
  na podstawie opisu bazy, nie potwierdzona źródłowo.
* **Wartości bazowe receptur** pokazywane w bibliotece są obliczone
  z bazy (oznaczone „obliczone, nie zweryfikowane kuchennie”).

## 4. Pokrycie diet (podgląd, 7 dni × 3 posiłki, katalog 300 szkiców, limit 2 użycia rodziny / tydz.)

| Produkty zwierzęce | Wzorzec | Kandydaci śniadanie / obiad / kolacja | Wynik |
|---|---|---|---|
| wszystko | zbilansowana, śródziemnomorska | 120 / 180 / 230 | `draft_preview` |
| wszystko | paleo | 37 / 47 / 74 | `search_exhausted` (przy limicie rodzin 7/tydz. albo 3 dniach: `draft_preview`) |
| wegetariańska | zbilansowana, śródziemnomorska | 120 / 120 / 170 | `draft_preview` |
| wegetariańska | paleo | 37 / 19 / 46 | `search_exhausted` |
| peskatariańska | zbilansowana, śródziemnomorska | 120 / 160 / 210 | `draft_preview` |
| peskatariańska | paleo | 37 / 47 / 74 | `search_exhausted` |
| wegańska | zbilansowana, śródziemnomorska | 60 / 110 / 120 | `draft_preview` |
| wegańska | paleo | 10 / 9 / 9 | `search_exhausted` |

Alergeny pojedynczo (wszystko, zbilansowana, 7 dni): gluten 48/86/104,
mleko 58/104/122, jaja 60/100/100, ryby 78/84/102, soja 38/94/112,
orzechy 36/104/122, sezam 78/104/122 — wszystkie `draft_preview`.
Wegańska + soja: śniadanie 0 kandydatów (produkty złożone bez etykiety)
→ `insufficient_catalog`.

`search_exhausted` oznacza brak układu w ograniczonym przeszukiwaniu
(szerokość 80), nie dowód niemożliwości — ekran mówi to wprost
i podpowiada poluzowanie limitu rodzin.

**Tryb produkcyjny:** przy 0 publikacji każda kombinacja daje
`insufficient_catalog` (test `test_production_unmapped_library_refuses`
i `test_produkcja_bez_publikacji_to_brak_pokrycia`). Low carb / keto
w podglądzie → `nutrition_unverified` (podgląd nie twierdzi, że limit
jest spełniony).

## 5. Wyniki testów (13.09.2026, lokalnie)

| Zestaw | Wynik |
|---|---|
| `tests/test_kulinaria_engine.py` (27 pakietu 1:1 + 2 adaptera) | 29 passed |
| `tests/test_kulinaria_api.py` | 7 passed |
| Cały backend (z macierzą dostępu: 11 nowych operacji) | 1648 passed, 1 skipped |
| Core `hos_engine` | 275 passed |
| Frontend `tsc`, build (budżet 89.3 kB / 120 kB), `test:helpers` | OK |
| E2E Playwright (24 + `kulinaria.spec.ts`) | 25 passed |
| `tools/spojnosc.py` | 13/13 |

## 6. Brakujące moduły / świadomie nie w tej rundzie

* **Publikacje receptur** — decyzja i praca trenera/dietetyka; bez nich
  brak trybu produkcyjnego z makro. Po pierwszych publikacjach należy
  sprawdzić, czy beam search (80) wystarcza dla 7 dni w granicach
  (pakiet: „można zwiększyć budżet albo podłączyć pełniejszy solver”).
* **Mikroskładniki** — baza ich nie ma; `required_nutrients` zawsze
  puste, a żądanie np. B12 → `insufficient_catalog`.
* **Kolejka redakcyjna importu** — publikacja jest per receptura
  z ekranu; masowego importu „do przeglądu” nie ma.
* **Dieta lecznicza, ciąża, dzieci, leki glikemiczne** — poza zakresem
  (bramka `needs_review`), zgodnie z pakietem.
* **Zdjęcia dań, ceny/budżet, resztki i przechowywanie** — brak danych.
* **Porównanie stary/nowy generator** — endpoint `porownanie` liczy
  metryki deterministyczne (nazwane dania z instrukcją, rodziny, średnia
  liczba składników); smaku i wykonalności nie mierzy.
* **Przegląd ekspercki** mapowania produktów i tekstów receptur.

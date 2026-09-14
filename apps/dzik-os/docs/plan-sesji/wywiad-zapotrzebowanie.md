# Plan sesji: wywiad „Zapotrzebowanie kaloryczne” (0.62.0)

**Gałąź:** `agent/wywiad-zapotrzebowanie` (od `main` = c9919e7). **Równolegle** z
`agent/monitoring-postepy` (0.63.0) — zgodnie z zarządzeniem właściciela z 14.09
(wiele zadań jednego piszącego, system koordynacji w `KOORDYNACJA.md` §0).
**Rezerwacje:** migracja **33**, wersja **0.62.0**, pliki współdzielone: `models.py`
(nowe klasy na końcu), `db.py` (wpis 33), `main.py` (flaga w `features`), `access_matrix.py`
(nowe trasy), `CHANGELOG.md` (własna sekcja), `wywiad/definicje.py` (nowy typ).
**Źródło:** zgłoszenie właściciela 14.09 („jeszcze jeden wywiad, który pomoże określić
dzienne zapotrzebowanie kaloryczne, zestawi dane ze wzorem, widoczny w panelu
trenera i podopiecznego”). Dokument `wywiad_zapotrzebowanie_kaloryczne.md`, do którego
odwołuje się specyfikacja Monitoringu (§10.1, flaga `ZABURZENIA_ODZYWIANIA`), nie został
dostarczony — pracuję na założeniach poniżej; po otrzymaniu dokumentu różnice wyrównam.

## Założenia (do potwierdzenia przez właściciela)

1. Wzór: PPM wg Mifflina-St Jeora (K: 10·m + 6,25·h − 5·wiek + 5; M: −161), CPM = PPM ×
   PAL (1,2 / 1,375 / 1,55 / 1,725 / 1,9 wg aktywności zawodowej + treningowej),
   korekta pod cel: redukcja −10/−15/−20 %, utrzymanie 0, masa +5/+10 %.
2. Dane: wiek (data urodzenia), płeć, wzrost, masa (domyślnie ostatni pomiar z zakładki
   Pomiary, do potwierdzenia), aktywność, cel i tempo; opcjonalnie: praca fizyczna,
   kroki dziennie.
3. Flaga zdrowotna `ZABURZENIA_ODZYWIANIA` (pytanie z opcją „wolę omówić z trenerem”)
   → dla roli klienta odpowiedź API nie zawiera kcal/masy (filtr serwerowy), trener widzi
   pełne dane. Ta sama flaga zasili Monitoring (§10.1 jego specyfikacji).
4. Trener może nadpisać wynik (kcal + powód), z historią kto/kiedy; wynik zasila
   „Przypisz dietę” przyciskiem „Zaproponuj kcal” (wypełnia pole kcal, nie przypisuje).
5. Bez AI. Za flagą `DZIK_CALORIE_INTERVIEW_ENABLED` (dev/test/E2E: włączona;
   produkcja: włączona przy deployu decyzją właściciela, jak dieta).

## Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Czytam (z hipotezą) | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 rozpoznanie | `wywiad/definicje.py` (jak zbudowany typ), `wywiad/serwis.py` (przeslij/fakty), `routers/wywiady.py` (dostęp), `frontend/pages/wywiad/*`, `Measurement` | `docs/WYWIAD.md` §nowy + ten plan | — | dziesiątki tys. |
| 1 silnik | — | `dzik_os/wywiad/zapotrzebowanie.py`: czyste funkcje PPM/PAL/CPM/korekta, walidacja zakresów, wynik z podstawieniem liczb | testy jednostkowe na przykładach kontrolnych (K 70 kg/170 cm/30 l → PPM 1451,5; M 85/180/28 → 1840; PAL, korekty, zakresy, brak danych) | dziesiątki tys. |
| 2 definicja wywiadu | `definicje.py` | trzeci typ `zapotrzebowanie` w istniejącym mechanizmie (sekcje, pytania warunkowe, klasa dostępu żywieniowa), wersjonowanie i przegląd jak dziś | testy istniejącego modułu wywiadu zielone + nowe (definicja, braki, flaga) | setki tys. (największy koszt — tu ryzyko integracji z mechanizmem szkiców/przesłań) |
| 3 model + migracja 33 | `models.py`, `db.py` | `calorie_estimate` (client_id, submission_id, wejścia, PPM, PAL, CPM, cel, wynik, `override_kcal`, `override_by/at/reason`, `hidden_for_client` z flagi), addytywna | `test_migracje_przenosnosc`, `test_pakietowanie` | dziesiątki tys. |
| 4 API | `routers/wywiady.py` | `GET /clients/{id}/zapotrzebowanie` (klient: bez kcal przy fladze; trener: pełne + podstawienie), `PUT …/zapotrzebowanie/nadpisanie` (trener), przeliczenie przy przesłaniu wywiadu | test flagi (brak pola `kcal`/`weight` na żadnym poziomie) napisany PRZED implementacją; macierz dostępu; obcy trener 404 | setki tys. |
| 5 UI | `pages/wywiad/*`, `client/Nutrition.tsx`, `coach/ClientDetail.tsx`, `coach/PrzypiszDiete.tsx` | formularz w zakładce Wywiad; karta „Twoje zapotrzebowanie ≈ X kcal” (klient, Dieta); karta z podstawieniem wzoru + nadpisanie (trener, Wywiad i Dieta); „Zaproponuj kcal” w Przypisz dietę | `tsc`, build, E2E (klient wypełnia → trener widzi wzór → Zaproponuj kcal), a11y | setki tys. |
| 6 zamknięcie | — | CHANGELOG, RELEASE_STATUS, STAN_PRZEKAZANIA, wersja 0.62.0, raport | pełny `pytest`, spójność, CI | dziesiątki tys. |

**Największy koszt:** etapy 2 i 5 (integracja z mechanizmem wywiadu i cztery miejsca w UI).
Taniej bez utraty informacji: zamiast czytać cały moduł wywiadu, czytam `_zbuduj_gleboki`
i jeden pełny przebieg `przeslij` jako wzorzec; UI buduję na istniejących komponentach
`pages/wywiad/wspolne.tsx` i `dieta/wspolne.tsx`. Bezpiecznik: 3× plan ≈ 1,5 mln tokenów.

## Odstępstwa od planu

* Wiek w latach zamiast daty urodzenia (mniej danych, ten sam wynik).
* Wartości kontrolne w planie były policzone z pamięci (1414 / 1854) —
  poprawne z wzoru: 1451,5 / 1840; testy używają poprawnych.
* Etap 3 i 4 wykonane razem z 2 (jeden przebieg testów po zestawie zmian,
  §2.8 zasad) — bez osobnego etapu.
* Brak zasilania profilu (`fact_key=None`): masa z wywiadu nie dubluje
  zakładki Pomiary; pomiar zasila tylko podpowiedź (placeholder).
* Flaga na produkcji włączona w `fly.toml` w tej rundzie (patrz
  RELEASE_STATUS) — właściciel może wyłączyć jedną linią.
* Klasa dostępu: pytania o ciało i aktywność mają klasę podstawową (nie
  żywieniową, jak zapowiadał etap 2); tylko `zk_zaburzenia` = zdrowotna.

## Weryfikacja wykonana

* Silnik: 9 testów (`tests/test_zapotrzebowanie_silnik.py`), wartości
  liczone ręcznie w komentarzach.
* API: 7 testów (`tests/test_zapotrzebowanie_api.py`); test flagi
  zdrowotnej sprawdza brak kluczy liczbowych na każdym poziomie odpowiedzi
  klienta (napisany przed nadpisaniem/odblokowaniem).
* Istniejący moduł wywiadu: `test_wywiad_zakladka`, `test_wywiad`,
  `test_przeglad_wywiadu` — 47 zielone (jedna asercja rozszerzona o trzeci
  typ w liście — to zmiana kontraktu, nie obejście).
* Ruff z korzenia repo: czysto. Frontend: `tsc` czysto, build 91,9 kB gzip
  (budżet 120 kB). E2E `zapotrzebowanie.spec.ts` (klient → trener nadpisuje
  → „Zaproponuj kcal” → klient widzi powód): zielony.
* Pełny `pytest` backendu i a11y: wynik w PR.

## Plan kontra rzeczywistość (zasady v2 §5)

Plan: 6 etapów, największy koszt etap 2 i 5. Rzeczywistość: rozpoznanie
zapisane w `docs/wywiad-zapotrzebowanie/00_rozpoznanie.md` (kilka odczytów
celowanych z grep, bez pełnych plików); etap 2 tańszy niż zakładano —
mechanizm wywiadu przyjął trzeci typ bez zmian w szkicach/wersjach
(jedna nowa gałąź w `waliduj`, jedno pole w `Pytanie`); etap 5 zgodnie
z planem (jedna wspólna karta zamiast czterech widoków). Zero podagentów.
Usprawnienie na następny raz: wartości kontrolne do planu liczyć
skryptem, nie z pamięci.


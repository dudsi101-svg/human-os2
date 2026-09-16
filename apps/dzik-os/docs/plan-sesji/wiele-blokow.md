# Plan sesji: więcej niż jeden blok tego samego rodzaju w planie (0.80.0)

**Gałąź:** `agent/wiele-blokow` (od `main` = `224f37c`, 0.79.0). **Rola:** integrator.
**Bez migracji** — schemat się nie zmienia, zmienia się reguła składania i limit w schemacie żądania.

## Cel (słowami właściciela, 16.09)

> W treningach gdy ustawiam szablon dla podopiecznego chciał bym by można było go
> uzupełnić dodatkowowymi szablonami z aerobami rozgrzewkami i rozciąganiem

Na pytanie integratora, czego dokładnie brakuje — bo sama funkcja „szablon + bloki"
istnieje od 0.76.0 — właściciel wybrał: **„Chcę więcej niż jeden blok danego rodzaju"**
(np. dwie różne rozgrzewki albo dwa bloki aerobowe w jednym planie).

## Rozpoznanie (stan `main` 0.79.0)

Funkcja przypisywania szablonu z blokami DZIAŁA (`PrzypiszPlan.tsx`, `copy-to` z ciałem,
`from-blocks`). Blokują ją dokładnie cztery rzeczy:

1. **`cardio/bloki.py:118`** — `waliduj_zestaw` rzuca `BladZestawu` przy drugim bloku tego
   samego rodzaju; zwraca `dict[str, ExerciseBlock]`, więc struktura z założenia mieści
   jeden blok na rodzaj.
2. **`cardio/bloki.py:27`** — `MAKS_BLOKOW = 3`, komunikat „po jednym: rozgrzewka, aeroby,
   rozciąganie".
3. **`cardio/bloki.py:132` `wstaw_do_dnia`** — rozgrzewka idzie na początek listy
   (`[poz, *exercises]`). Przy dwóch rozgrzewkach druga wylądowałaby **przed** pierwszą,
   czyli w odwrotnej kolejności niż wybrał trener. To cicha zmiana znaczenia, nie kosmetyka.
4. **`schemas.py:311,327`** — `max_length=3` na liście `blocks`.
5. **UI (`PrzypiszPlan.tsx:125`)** — `wybor[kind]` to JEDEN select na rodzaj.

Przy okazji: **`Templates.tsx:132` wysyła trenera pod nieistniejącą nazwę** — „Kopiowanie do
klienta: karta klienta → Plan → »Z szablonu…«", podczas gdy przycisk nazywa się od 0.76.0
„Przypisz plan (szablon i bloki)". Ta wskazówka jest prawdopodobnym powodem, dla którego
właściciel nie znalazł istniejącej funkcji. Naprawiana w tej rundzie.

## Decyzje projektowe

1. **Limit łączny, bez limitu na rodzaj.** `MAKS_BLOKOW` rośnie 3 → 6. Limit per rodzaj
   znika. Uzasadnienie: „po dwa na rodzaj" byłoby równie arbitralne jak „po jednym" i
   z góry zamykałoby układ 3 × aeroby + rozgrzewka. Limit łączny istnieje tylko po to,
   żeby dzień nie puchł bez końca, i tak jest nazwany w komunikacie błędu.

2. **Kolejność wyboru trenera jest zachowana.** Bloki tego samego rodzaju wstawiamy w tej
   kolejności, w której trener je wybrał. Wymaga to poprawki `wstaw_do_dnia` dla rozgrzewki:
   druga rozgrzewka ma trafić ZA pierwszą, a nie przed nią. Bez tego funkcja „działa", ale
   układa plan odwrotnie, niż trener widział na ekranie — a tego nikt by nie zauważył poza
   klientem, który dostanie rozgrzewkę w złej kolejności.

3. **Reguła „nie dublujemy tego, co szablon już ma" zostaje bez zmian i liczona jest RAZ,
   przed wstawianiem.** Jeśli szablon zawiera już rozgrzewkę, pomijamy WSZYSTKIE dokładane
   rozgrzewki w tym dniu (nie tylko drugą). Inaczej reguła stałaby się nieprzewidywalna:
   pierwszy blok pomijany, drugi wstawiany. Dzień trafia do `skipped_days` raz na rodzaj.

4. **Ten sam blok dwa razy nadal odrzucany** (`plans.py:247`). Dwie RÓŻNE rozgrzewki to
   sensowny układ treningowy; ta sama rozgrzewka dwa razy to pomyłka, nie zamiar.

5. **UI: lista zamiast selecta na rodzaj.** Każdy rodzaj ma listę wybranych bloków
   i przycisk „Dodaj kolejną/kolejny…"; każdy wiersz można usunąć. Kolejność na ekranie =
   kolejność w dniu, więc to, co trener widzi, jest tym, co dostanie klient.

## Pliki

**Zmieniane:** `backend/dzik_os/cardio/bloki.py`, `backend/dzik_os/schemas.py`,
`backend/tests/test_bloki_jak_szablony.py`, `backend/tests/test_cardio_bloki.py` (jeśli dotyka
walidacji), `frontend/src/pages/coach/PrzypiszPlan.tsx`, `frontend/src/pages/coach/Templates.tsx`
(myląca wskazówka), `frontend/e2e/bloki-jak-szablony.spec.ts`, `docs/CHANGELOG.md`,
`docs/INSTRUKCJA_TRENERA.md`, `docs/RELEASE_STATUS.md`, `docs/STAN_PRZEKAZANIA.md`, wersje w czterech plikach.

**Zabronione:** `hos_engine/`, `tests/` w korzeniu, migracje, `AGENTS.md`, `KOORDYNACJA.md`,
`tools/spojnosc.py`, `tools/mutacje*.py`.

## Rezerwacje

* **Wersja 0.80.0.** **Migracja: brak** (ostatnia w `db.py` = 42).
* **Porty E2E:** 8200/8202, a11y 8204.

## Etapy

| # | Etap | Weryfikacja |
|---|---|---|
| 1 | `waliduj_zestaw` bez limitu na rodzaj, `MAKS_BLOKOW = 6`, schemat | testy jednostkowe bloków |
| 2 | kolejność: druga rozgrzewka ZA pierwszą | test na kolejności pozycji w dniu |
| 3 | UI: listy bloków per rodzaj, kolejność = kolejność wyboru | tsc, E2E |
| 4 | wskazówka w Szablonach + dokumenty, wersje, pełne bramki | spójność, pytest, mutanty, Playwright, a11y |

## Czego pilnują testy (bo tu łatwo o cichą regresję)

* dwie różne rozgrzewki trafiają do dnia **w kolejności wyboru** (mutant odwracający
  kolejność musi dać czerwony test);
* szablon z własną rozgrzewką pomija **obie** dokładane i raportuje dzień raz;
* ten sam blok dwa razy → 422;
* siedem bloków → 422 z komunikatem o limicie łącznym;
* blok zarchiwizowany w zestawie → 422 (bez zmian).

## Wynik bramek (`629fb5b`)

| Bramka | Wynik |
|---|---|
| CI GitHub (8 zadań) | frontend, backend 3.11/3.12, backend-postgres, e2e, quality 3.11/3.12/3.13 — wszystkie zielone |
| pytest backend (pełny) | 2022 passed, 1 skipped (916 s) |
| Playwright (pełny) | 65 passed, 2 skipped |
| `tools/mutacje.py` | 17/17 wykrytych |
| `tools/mutacje_bezpieczenstwa.py` | 9/9 zabitych |
| a11y — motyw ciemny i czerwony | obie serie przeszły |
| `e2e/test_pwa_offline.mjs` | przeszedł |

Dwie usterki znalazły testy, nie przegląd kodu: komunikat „Dodano rozgrzewkę do 2 dni”
przy planie jednodniowym (raport mylił pozycje z dniami) oraz wskazówka w Szablonach
odsyłająca do nazwy przycisku, która nie istnieje od 0.76.0.

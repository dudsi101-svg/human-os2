# Plan sesji: dodatek kaloryczny przy ciąży/karmieniu + archiwizacja poprzedniego planu (0.78.0)

**Gałąź:** `agent/ciaza-i-archiwizacja` (od `main` = 0.77.0). **Rola:** sesja integratora
(runda prowadzona bezpośrednio, nie przez agenta podległego). **Bez migracji** — zmienia się
tylko wersja definicji wywiadu (2 → 3).

## Cel (słowami właściciela)

Właściciel odpowiedział „Tak tak tak” na trzy pytania postawione 15.09. Ta runda realizuje
dwa z nich:

1. doliczyć dodatek kaloryczny przy ciąży i karmieniu zgodnie ze specyfikacją wywiadu §6.4;
2. przypisanie planu treningowego ma archiwizować poprzedni plan klienta — tak jak od 0.60.0
   robi to dieta.

Trzecie („aktywuj konta testowe”) zostaje w zadaniu #70, bo aktywacja wymaga kliknięcia
w link z e-maila przez właściciela; obejście aktywacji zmianą w bazie jest zabronione.

## Rozpoznanie (stan `main` 0.77.0)

* **Silnik zapotrzebowania:** `backend/dzik_os/wywiad/zapotrzebowanie.py` — `Wejscie`,
  `oblicz()`; cel liczony jako `cpm * (1 + korekta)`; flagi zdrowotne (`FLAGA_CIAZA`) już
  istnieją i już wyłączają deficyt.
* **Definicje pytań:** `backend/dzik_os/wywiad/definicje.py` — `WERSJA_ZAPOTRZEBOWANIE = 2`,
  pytanie `zk_ciaza` łączy ciążę z karmieniem w jednej odpowiedzi „Tak”, więc nie da się
  z niego odczytać, czy dodatek ma wynieść 300 czy 500 kcal.
* **Przypisanie planu:** `backend/dzik_os/routers/plans.py` — `copy_template_to_client`
  i `create_plan_from_blocks` tworzą nowy plan ACTIVE i **nie** ruszają poprzedniego;
  klient mógł mieć dwa aktywne plany naraz. Wzorzec do naśladowania: `dieta/serwis.py::przypisz`.

## Rezerwacje

* **Wersja 0.78.0** — `frontend/package.json`, `backend/pyproject.toml`,
  `backend/dzik_os/__init__.py`, `README.md`, `RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md`.
* **Migracja: brak.** Ostatnia w `db.py` = 42 (0.77.0).
* **Wersja definicji wywiadu:** 3 (nowe pytanie warunkowe).
* **Porty E2E:** 8160/8162, a11y 8164 i 8166.

## Decyzje projektowe

1. **Pytanie doprecyzowujące, nie zgadywanie.** `zk_ciaza_rodzaj` pada wyłącznie po
   odpowiedzi „Tak” na `zk_ciaza`, pod tą samą zgodą `DOMAIN_HEALTH`. Opcje: „W ciąży”,
   „Karmię piersią”, „W ciąży i karmię”, „Wolę nie odpowiadać”. Bez doprecyzowania dodatku
   **nie ma** — aplikacja nie zgaduje, która wartość jest właściwa.
2. **Wartości ze specyfikacji §6.4:** ciąża +300 kcal, karmienie +500 kcal, oba +500 kcal
   (nie sumujemy — specyfikacja podaje jedną wartość dla stanu łącznego).
3. **Obowiązkowe ostrzeżenie.** Każdy wynik z dodatkiem niesie komunikat, że to punkt
   wyjścia do ustalenia z lekarzem albo dietetykiem prowadzącym; dodatek nie zastępuje
   opieki. Ostrzeżenie idzie tą samą drogą co dotychczasowe flagi zdrowotne, więc podlega
   tej samej zgodzie i temu samemu zasłanianiu przed trenerem bez `DOMAIN_HEALTH`.
4. **Dodatek po korekcie celu.** Kolejność: `cel_kcal = cpm * (1 + korekta)`, dopiero potem
   `+ dodatek`. Przy ciąży deficyt i tak jest wyłączony (flaga istnieje od 0.77.0), więc
   w praktyce dodatek dokłada się do zapotrzebowania, nie do obniżonego celu.
5. **Archiwizacja niczego nie kasuje.** `_zarchiwizuj_poprzednie` przestawia poprzednie
   plany ACTIVE na ARCHIVED i zwraca ich identyfikatory; odpowiedź API podaje
   `archived_plans`, a wpis audytu `archived_plan_ids`. Historia zostaje.

## Etapy

| # | Etap | Weryfikacja |
|---|---|---|
| 1 | silnik: `ciaza_rodzaj`, `DODATEK_CIAZA_KARMIENIE`, ostrzeżenie | `pytest tests/test_zapotrzebowanie_silnik.py` |
| 2 | definicje: pytanie warunkowe, wersja 3 | `pytest tests/test_zapotrzebowanie_api.py` |
| 3 | plany: `_zarchiwizuj_poprzednie` w obu trasach | `pytest tests/test_bloki_jak_szablony.py` |
| 4 | dokumenty, wersje, pełne bramki | `spojnosc.py`, pełny `pytest`, tsc, build, E2E, a11y |

## Weryfikacja wykonana (15.09)

**Bramki:** `ruff check` czysto (po poprawce C408 w pomocniku testu — nowszy ruff lokalny
tej reguły nie zgłaszał, bramka CI tak); `pytest` silnika 50, bloków 15, API wywiadu 40;
`tools/spojnosc.py` czysto; `tsc --noEmit` czysto; `npm run build` — 93 kB gzip (budżet 120);
`test:helpers` — 0 błędów; pełny zestaw backendu, Playwright (`telefon`, `desktop-trener`,
`telefon-postepy`), `test_a11y.mjs` w obu motywach — patrz opis PR.

**Mutanty (dowód, że testy pilnują właśnie tego):** zmiana dodatku przy karmieniu z 500 na
300 → czerwony test; wyłączenie archiwizacji w `copy-to` → czerwony test.

## Zmiana kontraktu (jawnie)

Odpowiedzi `POST /api/coach/templates/{id}/copy-to` i `POST /api/coach/plans/from-blocks`
mają nowy klucz `archived_plans`. Test sprawdzający pełny zbiór kluczy odpowiedzi został
zaktualizowany świadomie — to rozszerzenie kontraktu, nie przypadkowe rozjechanie się testu.

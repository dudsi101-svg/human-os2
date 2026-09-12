# Plan sesji: mała runda naprawcza testów dat i OCR (0.54.4)

**Gałąź:** `claude/awesome-sagan-sqd64l` (od `main` = 5d3c8ff)
**Rola:** aktywny piszący i integrator rundy (decyzja właściciela,
12.09.2026); recenzentem jest niezależna sesja Codex.
**Wyjątek nazewnictwa:** środowisko wykonania wyznacza tej sesji gałąź
`claude/awesome-sagan-sqd64l` i nie pozwala pushować na inną; właściciel
zatwierdził jawny wyjątek od konwencji `agent/<zadanie>` dla tej rundy.
Baza PR pozostaje `main`, reszta protokołu bez zmian.

**Cel:** pozycja z kolejki `STAN_PRZEKAZANIA.md` §3 pkt 2. Dziś jest
12.09.2026, a `test_notifications.py` niesie absolutne daty przyszłe
(najbliższa: środa 2026-09-16) przy seedzie liczonym od prawdziwego
`today` — od ~16.09 CI czerwienieje na czystym `main` bez żadnej zmiany
kodu, dokładnie jak 23.08 (naprawa 0.41.0). Do tego dwa testy OCR
„bez Tesseracta" nie izolują tego założenia i czerwienią się, gdy
binarka jest zainstalowana, oraz stara fraza „jedna-sesja-naraz"
w Karcie współpracy (~linia 191).

## Zamiar

1. **`test_notifications.py`**: wszystkie absolutne daty przyszłe
   (2026-09-14/16/17/20/25/26, 2026-10-28) zastąpione datami względnymi
   od `dates.local_today()` — ta sama kuracja co w 0.41.0, z użyciem
   już istniejących pomocników `_nastepna_sroda()` / `_osma_rano()`.
   **Granice zmiany czasu zostają przetestowane** (decyzja właściciela):
   test DST wyszukuje dynamicznie parę przyszłych śród o RÓŻNYM
   offsecie UTC (zoneinfo), asertuje różnicę offsetów i moment wysyłki
   po obu stronach przejścia — kontrolowany zegar wstrzykiwany do
   `_tick`, zero zależności od dnia uruchomienia.
2. **`test_ocr.py`**: dwa testy zakładające brak silnika lokalnego
   (`test_status_reports_engine_unavailable_without_tesseract`,
   `test_missing_engine_gives_readable_state_not_500`) wymuszają ten
   stan wprost (wzorzec `DZIK_OCR_BINARY=__missing_tesseract__`
   przez monkeypatch), zamiast zakładać środowisko bez binarki.
3. **`KARTA_WSPOLPRACY.md`**: fraza „jedna-sesja-naraz" → aktualna
   „jedna sesja pisząca naraz" (osobny commit z powodem, zgodnie
   z sekcją „Zmiana tej karty"; zdarzenie: pozycja naprawcza
   w STAN_PRZEKAZANIA §3 pkt 2).

## Świadomie nie robię

- zmian w kodzie produkcyjnym (`dzik_os/`, frontend) poza numerem
  wersji — runda jest wyłącznie testowo-dokumentacyjna;
- zmian w `spojnosc.py`/`mutacje*.py` (przeglądy mutacyjne nie są
  wymagane — żadna kontrola się nie zmienia);
- naprawy testów dat w `test_dates.py` (25.10 tam to daty PRZESZŁE
  względem asercji z wstrzykniętym `now` — deterministyczne, nie
  wymagają kuracji);
- Core (`hos_engine/`, `tests/`), migracji, deployu, ustawień repo.

## Rezerwacje

- **Wersja: 0.54.4.** **Migracja: brak.**
- Pliki: `apps/dzik-os/backend/tests/test_notifications.py`,
  `apps/dzik-os/backend/tests/test_ocr.py`,
  `apps/dzik-os/docs/KARTA_WSPOLPRACY.md` (jedna fraza),
  ten plan, `apps/dzik-os/docs/CHANGELOG.md`,
  `apps/dzik-os/docs/STAN_PRZEKAZANIA.md` oraz pliki niosące numer
  wersji (kontrole `przekazanie`/`wersje dokumentów`):
  `apps/dzik-os/README.md`, `apps/dzik-os/docs/RELEASE_STATUS.md`,
  `apps/dzik-os/backend/pyproject.toml`,
  `apps/dzik-os/backend/dzik_os/__init__.py`,
  `apps/dzik-os/frontend/package.json`.

## Weryfikacja (do wypełnienia)

- ruff, pytest backend, Core 275, spójność; tsc/build/test:helpers
  (runda dotyka `package.json`); dowód kuracji: naprawione testy
  uruchomione z zegarem przesuniętym ZA najbliższą sporną datę
  (np. `local_today` zamockowane na 2026-09-20) — zielone.

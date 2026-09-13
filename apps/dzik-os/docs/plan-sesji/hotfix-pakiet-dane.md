# Plan sesji: poprawka awaryjna — pliki danych w obrazie produkcyjnym (0.57.1)

**Gałąź:** `agent/hotfix-pakiet-dane` (od `main` = 6c3d078).
**Rola:** jedyny piszący i integrator; poprawka awaryjna produkcji.

## Co się stało

Log Fly (workflow `fly-logs`, 09:36 UTC): przy starcie 0.56.0
`FileNotFoundError: .../site-packages/dzik_os/wiedza/dane/tresci_startowe.json`
w `lifespan` → „Application startup failed” → 10 restartów → maszyna
`stopped` (09:07 UTC). Smoke-test deployu dostał 502. Przyczyna: brak
`[tool.setuptools.package-data]` — koło budowane przez `pip install`
(Dockerfile) nie zawiera plików JSON. Lokalnie i w CI instalacja `-e`
maskowała brak. Dowód: koło z pyproject sprzed poprawki nie ma ani
jednego pliku `.json` (patrz „Weryfikacja wykonana”).

## Zamiar

1. `package-data` dla `dzik_os.konfigurator`, `dzik_os.wiedza`,
   `dzik_os.kulinaria` (`dane/*.json`).
2. Odporny start: import treści startowych Wiedzy w `try/except` —
   błąd logowany strukturalnie i widoczny w `/api/health`
   (`wiedza_import_error`), aplikacja wstaje z pustą biblioteką.
3. Strażnik `tests/test_pakietowanie.py`: buduje koło jak Dockerfile
   i wymaga w nim każdego pliku spoza `*.py` z `dzik_os/`.
4. Wersja 0.57.1, CHANGELOG, RELEASE_STATUS (incydent), STAN.
5. PR `[WRITER]`, CI, scalenie, deploy, smoke (health `version` 0.57.1,
   `migration` 29, `wiedza_import_error` null).

## Weryfikacja wykonana

(uzupełnię po rundzie)

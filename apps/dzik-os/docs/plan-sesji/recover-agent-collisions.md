# Plan sesji: odzyskanie jednej linii pracy agentów

**Gałąź:** `agent/recover-agent-collisions`
**Rola:** jedyny aktywny piszący i integrator
**Cel:** potwierdzić wynik scalenia PR #13, wskazać `main` jako kanoniczny
oraz wprowadzić protokół, który zatrzymuje drugiego piszącego przed
pierwszą zmianą.

## Mój obszar

- instrukcje agentów w `AGENTS.md` i `CLAUDE.md`;
- prawdziwy stan gałęzi w `docs/STAN_PRZEKAZANIA.md`;
- mechanika jednego PR-a `[WRITER]` w `docs/KOORDYNACJA.md`;
- ten plan sesji.

## Czego nie dotykam

- kodu backendu i frontendu;
- Core Human OS (`hos_engine/`, `tests/`);
- migracji, danych i numeru wersji produktu;
- funkcji produktowych oraz otwartych konsultacji.

## Rezerwacje

Brak migracji i brak nowej wersji. Rezerwowane są wyłącznie pliki
wymienione w „Mój obszar”. Do zamknięcia tej rundy nie powstaje drugi PR
piszący.

## Rozstrzygnięcie rozbieżnej gałęzi

PR #13 został scalony podczas audytu. Commit `94aaa39` ma obie historie,
a `main` i dawna gałąź domyślna wskazują ten sam stan. Ta runda nie dodaje
drugiego scalenia. Potwierdza, że dla nakładających się plików zostały
wersje z formatem `K-NNN`, 10 kontrolami spójności, 37 testami kontrolera
i 17/17 wykrytymi mutacjami.

## Świadomie nie robię

- nie otwieram ponownie ani nie modyfikuję scalonego PR #13;
- nie scalam niesprawdzonej gałęzi `claude/ocena-projektu-dzik-os-76ercy`;
- nie zmieniam gałęzi domyślnej;
- nie zamykam ani nie usuwam żadnej gałęzi;
- nie scalam przygotowanego PR-a bez osobnej zgody właściciela.

## Weryfikacja

- ruff: czysto;
- backend: 760 zaliczonych, 1 opcjonalny test Tesseracta pominięty;
- Core Human OS: 275/275;
- testy kontrolera spójności: 37/37;
- `spojnosc.py`: czysto, 10 kontroli i 1 otwarta konsultacja.

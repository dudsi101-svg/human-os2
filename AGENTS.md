# Zasady pracy agentów

## Dzik OS (`apps/dzik-os/`)

Te reguły są obowiązkowe dla każdego agenta, który czyta lub zmienia Dzik OS.
Ich celem jest wyeliminowanie kolizji między równoległymi sesjami.

1. **Domyślnie pracujesz tylko do odczytu.** Pliki może zmieniać wyłącznie
   agent jawnie wyznaczony przez właściciela jako aktywny piszący albo
   integrator. Pozostali mogą analizować, testować i recenzować, ale nie
   zapisują zmian.
2. **`main` jest jedyną gałęzią kanoniczną.** Nie sugeruj się aktualną
   gałęzią domyślną GitHuba, jeśli wskazuje coś innego. Nowa praca startuje
   z bieżącego `main`, a PR zawsze wraca do `main`.
3. **Jeden piszący = jeden otwarty PR `[WRITER]`.** Przed pierwszą zmianą
   sprawdź otwarte PR-y. Jeśli istnieje inny otwarty PR z prefiksem
   `[WRITER]`, zatrzymaj się i zgłoś kolizję; nie twórz drugiej gałęzi
   piszącej. Pierwszym zapisem nowej rundy jest wyłącznie plan sesji:
   commitujesz go, pushujesz i od razu otwierasz draft PR `[WRITER]`.
   Dopiero widoczny PR odblokowuje zmiany w kodzie i plikach integracyjnych.
4. **Jedno zadanie, krótka gałąź.** Użyj `agent/<krótka-nazwa>` i opisz
   dozwolone oraz zabronione pliki w `apps/dzik-os/docs/plan-sesji/`.
   Nie rozszerzaj zakresu po cichu.
5. **Pliki integracyjne zmienia tylko aktywny integrator:**
   `AGENTS.md`, `CLAUDE.md`, `apps/dzik-os/docs/CHANGELOG.md`,
   `apps/dzik-os/docs/STAN_PRZEKAZANIA.md`,
   `apps/dzik-os/docs/KOORDYNACJA.md`,
   `apps/dzik-os/docs/KONSULTACJE.md`, migracje i
   `apps/dzik-os/backend/dzik_os/db.py`, a także narzędzia
   `apps/dzik-os/tools/spojnosc.py` i `apps/dzik-os/tools/mutacje.py`.
6. **Konflikt oznacza STOP.** Nie wybieraj automatycznie `ours`/`theirs`,
   nie rób force-pusha i nie rozwiązuj sprzeczności znaczeniowej bez
   decyzji właściciela lub integratora popartej testem.
7. **Agent nie scala własnego PR-a.** Nie usuwa też gałęzi i nie zmienia
   ustawień repozytorium. Po zielonych testach przekazuje wynik
   właścicielowi do osobnej decyzji.

Przed pracą przeczytaj kolejno:

- `apps/dzik-os/docs/KARTA_WSPOLPRACY.md`,
- `apps/dzik-os/docs/STAN_PRZEKAZANIA.md`,
- `apps/dzik-os/docs/KOORDYNACJA.md`,
- `apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`.

Minimalna bramka przed przekazaniem:

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q
python apps/dzik-os/tools/spojnosc.py
```

Core (`hos_engine/`, `tests/`) jest poza zakresem pracy aplikacyjnej.

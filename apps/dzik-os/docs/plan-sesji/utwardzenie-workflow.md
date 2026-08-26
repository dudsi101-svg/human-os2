# Plan sesji: utwardzenie inputów workflow (audyt P0-3)

**Gałąź:** `agent/utwardzenie-workflow` (od `main` = aktualny)
**Rola:** aktywny piszący (audyt zewnętrzny 25.08, bloker P0-3 +
polecenie właściciela „ruszaj" na plan poprawek)
**Cel:** żaden `${{ inputs.* }}` nie trafia bezpośrednio do bloku `run`
— wartości idą przez `env` i twardą walidację, a bramka spójności
pilnuje, żeby wzorzec nie wrócił.

## Diagnoza (za audytem, potwierdzona w źródłach)

W `fly-bootstrap.yml`, `fly-dodaj-trenera.yml`, `fly-sekrety.yml`
i `fly-porzadki-demo.yml` inputy są interpolowane wprost w `run`
(w tym w poleceniu `flyctl ssh console -C`). Wartość z metaznakami
mogłaby zmienić polecenie na runnerze lub maszynie produkcyjnej.
Ekspozycja jest wąska (dispatch tylko dla osób z prawem zapisu),
ale skutek potencjalnie wysoki (token Fly, produkcja).

## Zamiar

1. We wszystkich czterech workflow: inputy mapowane do `env` na
   poziomie joba; pierwszy krok waliduje twardym wzorcem
   (e-mail: `^[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`;
   `force`: dokładnie `true`/`false`) i przerywa run przy odchyleniu.
   W `run` wyłącznie `"$ZMIENNA"` — zwalidowany zbiór znaków nie
   zawiera niczego, co powłoka interpretuje.
2. **Strażnik regresji w `spojnosc.py`**: nowa kontrola skanuje
   `.github/workflows/*.yml` i czerwieni się, gdy `${{ inputs.`
   pojawia się wewnątrz bloku `run:` (TDD: kontrola najpierw ma
   wykryć obecny stan, naprawa workflow ją zieleni).
3. Do czasu scalenia nie uruchamiamy tych workflow z niestandardowym
   inputem (dotychczasowe runy używały wyłącznie zaufanych wartości).

## Mój obszar

- `.github/workflows/fly-{bootstrap,dodaj-trenera,sekrety,porzadki-demo}.yml`;
- `apps/dzik-os/tools/spojnosc.py` (nowa kontrola);
- `docs/CHANGELOG.md` (0.53.2), `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Rezerwacje

- **Wersja: 0.53.2.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- strażnik wykrywa stary wzorzec (dowód czerwieni przed naprawą);
  po naprawie spójność czysto; YAML zwalidowany; test negatywny
  walidacji (wartość z średnikiem odrzucona) udokumentowany lokalnie.

# Plan sesji: porządki demo na produkcji (workflow)

**Gałąź:** `agent/porzadki-demo` (od `main` = aktualny)
**Rola:** aktywny piszący (kontynuacja polecenia „zrealizuj sam te
punkty" — pierwszy przebieg workflow bootstrapu wykazał, że baza
produkcyjna ma stare konta demo z czasów seeda sprzed 0.43.0 i bootstrap
słusznie odmówił)
**Cel:** trzeci workflow „Porządki demo (Fly.io)" uruchamiający
`python -m dzik_os.purge_demo` na maszynie produkcyjnej — najpierw
diagnostycznie (bez `--force` narzędzie odmawia, gdy nie ma aktywnego
niedemowego COACH — sama odmowa mówi, czy realne konta istnieją),
a po potwierdzeniu z `--force` (dezaktywacja: SUSPENDED + losowy hash,
nigdy kasowanie wierszy).

## Mój obszar

- `.github/workflows/fly-porzadki-demo.yml` (nowy);
- `docs/CHANGELOG.md` (wpis 0.52.1), `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Czego nie dotykam

- kodu aplikacji (purge_demo istnieje od 0.43.x), Core, frontendu.

## Rezerwacje

- **Wersja: 0.52.1** (ostatnia: 0.52.0). **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- YAML zwalidowany; przebieg diagnostyczny i właściwy na produkcji
  + ponowny bootstrap — wyniki w tej sekcji po wykonaniu.

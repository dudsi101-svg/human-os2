# Plan sesji: bomba dekompresyjna w imporcie arkuszy

**Gałąź:** `agent/xlsx-bomba` (od `main` = `98dca51`)
**Rola:** aktywny piszący (wyznaczony przez właściciela)
**Cel:** domknąć punkt 1 znaleziska K-002 — plik `.xlsx` o rozmiarze
1,64 MB rozwijał się przy imporcie do 1164 MB RSS w 129 s. Limit wejściowy
z 0.40.0 (`_read_limited`, `MAX_BYTES`) ogranicza tylko plik *spakowany*;
bomba puchnie dopiero w parserze. Limity muszą działać **wewnątrz**
`sheet_import.py`.

## Diagnoza (z kodu, nie z pamięci)

1. `_read_xlsx` materializuje wszystkie wiersze naraz
   (`[[...] for row in sheet.iter_rows()]`) — `MAX_ROWS = 2000` działa
   dopiero w `read_table`, po fakcie.
2. `openpyxl.load_workbook` parsuje cały `sharedStrings.xml` przed
   pierwszą iteracją — bomba w słowniku napisów wybucha jeszcze przed
   pętlą.
3. Suma rozmiarów po rozpakowaniu jest zadeklarowana w katalogu ZIP-a
   i możliwa do sprawdzenia **zanim** cokolwiek się rozpakuje.

## Zamiar

Trzy limity w `sheet_import.py`, wszystkie zgłaszane jako `SheetError`
(routery już mapują go na czytelny błąd HTTP — zero zmian w routerach):

- **suma rozmiarów po rozpakowaniu** — kontrola katalogu ZIP przed
  `load_workbook`; odcina całą klasę bomb, także `sharedStrings`;
- **twardy limit przeskanowanych wierszy** — przerwanie iteracji, nie
  filtrowanie po niej; wyraźnie większy od `MAX_ROWS`, żeby nie karać
  legalnych plików z pustymi wierszami;
- **limit szerokości wiersza** — bomba „w bok" (dziesiątki tysięcy
  kolumn) też materializuje pamięć.

Semantyka dla legalnych plików bez zmian: ucięcie powyżej `MAX_ROWS`
z ostrzeżeniem zostaje dokładnie takie, jakie jest.

## Mój obszar

- `backend/dzik_os/sheet_import.py` (stałe + `_read_xlsx`);
- `backend/tests/test_sheet_import.py` (testy limitów, w tym prawdziwy
  plik-bomba i pomiar RSS);
- `docs/CHANGELOG.md` (wpis 0.41.0);
- `docs/STAN_PRZEKAZANIA.md` (zdjęcie punktu 1 z kolejki po zakończeniu);
- `docs/KONSULTACJE.md` (dopisek zamykający K-002 pkt 1);
- ten plan.

## Czego nie dotykam

- routerów (`SheetError` już jest mapowany), frontendu, migracji, seeda;
- Core Human OS (`hos_engine/`, `tests/` w korzeniu);
- pozostałych punktów kolejki (OCR, gałąź bramkowa, dostawca AI, pilotaż).

## Rezerwacje

- **Wersja: 0.41.0** (ostatnia w CHANGELOG: 0.40.0).
- **Migracja: brak** — zmiana nie dotyka schematu bazy.

## Świadomie nie robię

- nie zmieniam zachowania importu CSV (nie ma dekompresji — rozmiar
  wejścia ogranicza go wprost);
- nie przenoszę limitów do konfiguracji (`settings`) — progi bezpieczeństwa
  parsera to stałe modułu jak `MAX_BYTES`, nie pokrętła instalacji;
- nie scalam własnego PR-a; po bramkach przekazuję go właścicielowi.

## Weryfikacja (do wypełnienia na koniec rundy)

- ruff, backend (z wymuszonym brakiem Tesseracta), Core 275, spójność,
  mutacje — komplet bramek z `STAN_PRZEKAZANIA.md` §5;
- test bomby: spreparowany plik `.xlsx` (mały na dysku, wielki po
  rozpakowaniu) musi zostać odrzucony szybko i bez wzrostu RSS —
  pomiar w teście, nie deklaracja.

# Konfigurator miesięcznych planów treningowych

**Stan: K1 (0.55.0) — silnik, walidator, bramka zdrowotna, kalendarz,
API trenera. Bez ekranu (K1b) i bez dziennika/adaptacji (K2).**
Źródło reguł: pakiet właściciela 1.0 z 13.09.2026 —
`docs/konfigurator/01_SPECYFIKACJA_KONFIGURATORA.md`, testy
`07_TESTY_AKCEPTACYJNE.md`, kontrola danych `09_KONTROLA_PAKIETU.md`.
Dane (katalog, schematy, źródła): `backend/dzik_os/konfigurator/dane/`.

## Co to jest i czym nie jest

Deterministyczny silnik, który z wywiadu (formularz wg schematu
wejścia) układa plan treningu oporowego na 28 dni: układ tygodnia,
jednostki, serie, zakresy powtórzeń, przerwy, RIR na tygodnie,
kalendarz z odstępami, sumy mięśni, czas sesji, uwagi i ograniczenia.
**Nie używa modelu językowego.** Ciężary są zawsze `null` („dobór na
miejscu”). Progi oznaczone **H** to heurystyki produktu, nie zalecenia
kliniczne. Katalog 31 ćwiczeń ma status „do przeglądu trenera”.

**W Dzik OS to narzędzie trenera (propose-only):** trener wpisuje
wejście (w tym kwalifikację zdrowotną z wywiadu — pola `null` znaczą
„brak odpowiedzi” i blokują), dostaje szkic, poprawia i zapisuje jako
wersję planu podopiecznego. Klient nie uruchamia generatora.

## Stany wyniku

`ready` / `limited` (plan) oraz blokujące bez planu: `urgent_stop`
(objawy alarmowe — pilna pomoc), `needs_review` (ocena specjalisty;
choroba ≠ zakaz ruchu), `needs_input` (brak odpowiedzi, sprzeczne
dane, konflikt terminów, 5–6 dni u początkującego bez akceptacji),
`infeasible` (brak sprzętu do wzorca, brak pokrycia grup, limit czasu).
Kolejność ważności: objawy → zalecenia → sprzęt → dostępność →
regeneracja → cel → preferencje. Tekst w preferencjach nie zmienia reguł.

## API (trener)

- `GET /api/coach/konfigurator/katalog` — katalog, sprzęt, mięśnie, układy, heurystyki.
- `POST /api/coach/konfigurator/podglad` — wejście → wynik (bez zapisu; statusy blokujące to 200 z `plan: null`).
- `POST /api/coach/konfigurator/zapisz` — `{client_id, wejscie, title?}` → nowy plan v1 (zgoda `training_data`, audyt `PLAN_CREATED` z `source=konfigurator`); status blokujący → 409 z pełnym wynikiem.

Treść wersji planu: dni = jednostki (nazwa, serie, zakres, przerwa,
komentarz z RIR i zasadą progresji) + klucz `konfigurator` (kalendarz
28 dni, sumy, uwagi, wersje reguł, wejście **bez bloku zdrowotnego**).
Blok zdrowotny nie trafia do planu, audytu ani logów.

## Dowody

- 7 scenariuszy referencyjnych pakietu odtworzone **co do bajta**
  (`tests/test_konfigurator_przyklady.py`).
- Przypadki akceptacyjne T01–T21, T40–T48 i 648 kombinacji parametrów
  (`tests/test_konfigurator_akceptacyjne.py`); T22–T39 dotyczą dziennika
  i adaptacji — K2.
- API: `tests/test_konfigurator_api.py`.

## Przed publikacją (wymóg pakietu, nie wykonane)

Przegląd katalogu przez trenera, przegląd screeningu przez specjalistę
medycznego, pilotaż zrozumiałości (RIR, zapis na stronę, rozgrzewka vs
seria robocza) i kalibracja estymatora czasu. Produkt nie jest
klinicznie zwalidowany i nie obiecuje efektów sylwetkowych.

## Relacja do bloków rozgrzewki i cardio z suwakami (0.73.0)

K1 nadal liczy `warmup_minutes` (budżet 600 s w `katalog.json`), a
`konfigurator/eksport.py` wyrzuca tę wartość przy zapisie do planu — **bez
zmian w tej rundzie**. Od 0.73.0 rozgrzewka jest osobnym bytem: blokiem
z katalogu trenera wstawianym do dnia jako pozycja `kind: "warmup_block"`
z migawką treści, a cardio — pozycją `kind: "cardio"` z silnika suwaków
(`dzik_os/cardio/`). K2 (dziennik/adaptacja) ma podpiąć blok rozgrzewki
zamiast budżetu minut i pozycję cardio zamiast `baseline_cardio_minutes`;
do tego czasu plany z konfiguratora nie zawierają bloków ani cardio.

# Plan sesji: podział bundla per rola + budżet rozmiaru (audyt Sprint B, pozycja B3)

**Gałąź:** `agent/podzial-bundla` (od `main` = d532c85)
**Rola:** aktywny piszący
**Cel:** klient na telefonie nie powinien pobierać panelu trenera
i admina (dziś jeden bundel ~571 kB / 169 kB gz); rozmiar wejściowego
JS dostaje strażnika, żeby nie odrósł po cichu.

## Ustalenie wstępne

Część fontową B3 wykonała już wcześniejsza runda: importy pełnych wag
z `unicode-range` (przeglądarka pobiera tylko latin/latin-ext),
a nadmiarowe subsety odfiltrowane z precache service workera
(`scripts/inject-precache.mjs`) — audyt powstał przed tym stanem.
W tej rundzie fontów nie ruszam.

## Zamiar

1. **`React.lazy` per grupa tras** w `App.tsx`: publiczne
   (Landing/Login/Prywatność/Aktywacja/Reset) zostają eager — pierwsza
   farba publicznego wejścia bez dodatkowej rundy sieciowej; wszystko
   za logowaniem (strony klienta, trenera, Admin, Wiadomości,
   Powiadomienia, Więcej…) — leniwie, z `<Suspense>` i istniejącym
   spinnerem. Granice błędów per trasa zostają jak są.
2. **Strażnik budżetu**: `scripts/sprawdz-budzet.mjs` — po `npm run
   build` mierzy gzip wejściowego JS (index-*.js) i czerwieni, gdy
   przekroczy budżet ustawiony z zapasem względem stanu po podziale;
   podpięty do `npm run build` w CI (job frontend) i lokalnie.
3. E2E bez zmian merytorycznych — 19 testów musi przejść (leniwe
   chunki trafiają do precache przez istniejący glob; test PWA offline
   to zweryfikuje).

## Świadomie nie robię

- nie tnę zależności wspólnych (wykresy itp.) na osobne chunki ręcznie —
  najpierw efekt samego podziału per trasa; dalsza optymalizacja tylko
  jeśli budżet nadal nieprzyjemny;
- nie ruszam fontów (patrz wyżej).

## Rezerwacje

- **Wersja: 0.53.11.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- tsc/build/test:helpers/E2E 19/19; porównanie rozmiarów przed/po;
  strażnik dowiedziony czerwienią przy sztucznie zaniżonym budżecie.

## Weryfikacja (wykonana)

- `tsc` czysto; `npm run build` — wejściowy JS **571→281 kB
  (gzip 169→88.7 kB)**, 36 chunków; `test:helpers` czysto;
  **E2E 19/19**; runnery a11y i PWA-offline — wszystkie kontrole
  przeszły (precache z leniwymi chunkami działa offline).
- Strażnik budżetu: zielony przy 120 kB, dowiedziony CZERWIENIĄ przy
  `BUDZET_KB=1`; podpięty do `npm run build` (czerwieni CI).
- Uruchomienie na żywo: przebiegi Playwright chodzą po zbudowanym
  `dist/` serwowanym jak na produkcji — nawigacja po leniwych trasach
  obejrzana w E2E (logowanie→Dzisiaj, panel trenera, raport, wywiad).
- Spójność czysto (13 kontroli); backend nie zmieniany (wersje tylko).

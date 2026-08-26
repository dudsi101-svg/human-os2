# Plan sesji: /prywatnosc + informacja RODO przy formularzu (audyt P0-1)

**Gałąź:** `agent/prywatnosc-publiczna` (od `main` = aktualny)
**Rola:** aktywny piszący (Sprint A audytu, pozycja A5)
**Cel:** publiczny formularz przestaje zbierać dane bez informacji
art. 13 — stała trasa `/prywatnosc` bez logowania, warstwowa notka
przy formularzu i linki tam, gdzie zbierane są dane.

## Zamiar

1. **`Privacy.tsx`** — publiczna strona `/prywatnosc` z pełną treścią
   opartą o `POLITYKA_PRYWATNOSCI_SZKIC.md`, z wypełnionymi polami:
   administrator **LUBELSKI DZIK sp. z o.o., ul. Wschodnia 6/6,
   20-015 Lublin** (dane jawne z KRS), kontakt lubelskidzikk@gmail.com;
   odbiorcy: Fly.io (hosting, region fra/UE), dostawca poczty (po
   włączeniu SMTP), web-push; retencja opisowa zgodna z realnym
   działaniem aplikacji (konto do usunięcia/anonimizacji na żądanie,
   kopie zapasowe do 14 archiwów + snapshoty Fly); małoletni: usługa
   dla osób 18+; prawo skargi do PUODO. Stopka strony: data wersji
   i dopisek „dokument przygotowany technicznie; zatwierdzenie
   administratora danych — patrz STAN_PRZEKAZANIA".
2. **Warstwowa informacja art. 13 przy formularzu kontaktowym**:
   administrator, cel (odpowiedź na zapytanie), prawa, link do pełnej
   polityki + wyraźne „nie wpisuj w formularzu informacji o zdrowiu,
   diagnoz ani dokumentacji medycznej — to ustalimy bezpiecznie
   w aplikacji po założeniu konta".
3. **Linki**: stopka Landing, ekran logowania, ekran aktywacji, ekran
   zgód (ConsentGate). `/prywatnosc` w publicPaths.
4. E2E: strona `/prywatnosc` dostępna bez logowania, formularz ma
   link i ostrzeżenie.
5. `POLITYKA_PRYWATNOSCI_SZKIC.md` → zaktualizowana o adnotację, że
   wersja publiczna żyje w `Privacy.tsx` (jedno źródło treści).

## Świadomie nie robię

- nie podpisuję DPA i nie wybieram podstaw prawnych za administratora —
  treść strony opisuje stan faktyczny aplikacji; formalne zatwierdzenie
  (W3 planu audytowego) pozostaje po stronie właściciela/prawnika
  i jest odnotowane w STAN_PRZEKAZANIA jako otwarte.

## Rezerwacje

- **Wersja: 0.53.5.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki frontendu + minimalne backendu; E2E z asercjami; zrzut strony.

## Weryfikacja (wykonana)

- `npx tsc --noEmit` — czysto; `npm run build` — ✓ (index 570.92 kB gz 168.62 kB).
- `npm run test:helpers` — czysto; `npm run test:e2e` — **19/19**
  (nowy test: klik z notki przy formularzu → `/prywatnosc` + wejście
  bezpośrednie; pierwszy przebieg złapał kolizję strict-mode dwóch
  linków o tej samej nazwie — naprawione `exact: true`).
- `ruff` backend/tools — czysto; backend **846 passed, 1 skipped**;
  Core **275 passed**; `spojnosc.py` — czysto (11 kontroli).
- Uruchomienie na żywo: `vite preview` + Chromium na
  `/prywatnosc` — strona renderuje się bez logowania, H1 „Informacja
  o przetwarzaniu danych osobowych", 6 sekcji, stopka z linkami;
  zrzut w scratchpadzie (`prywatnosc.png`).

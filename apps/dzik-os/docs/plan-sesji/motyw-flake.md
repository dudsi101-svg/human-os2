# Plan sesji: test motywu czytał kolor w trakcie przejścia (bez zmiany wersji)

**Gałąź:** `agent/motyw-flake` (od `main` = `3e75bd4`, 0.78.0). **Rola:** integrator.
**Bez migracji, bez podbicia wersji** — zmiana dotyczy wyłącznie testu i dokumentu.

## Dlaczego ta runda w ogóle powstała

Po scaleniu 0.78.0 (PR #83) `dzik-os-ci` na `main` (run 34983224967) **wywrócił się**
na `e2e/motyw.spec.ts:25`, choć ten sam commit miał 8/8 zielonych na gałęzi, a lokalnie
pełny Playwright dał 62 passed. `fly-deploy.yml` rusza wyłącznie po zielonym CI na `main`,
więc deploy został **pominięty** (`conclusion: skipped`) i produkcja została na 0.77.0.
Bez naprawy tego testu 0.78.0 nie trafi do klientów.

## Przyczyna (zmierzona, nie zgadnięta)

Test czytał kolor tła jednorazowo:

```ts
tlo: getComputedStyle(document.body).backgroundColor
```

Przy `prefers-reduced-motion: reduce` (test jawnie włącza `emulateMedia`) arkusz ustawia
`* { transition-duration: 0.01ms !important }`. `transition-property` domyślnie to `all`,
więc reguła obejmuje **każdą** właściwość, w tym `background-color`. Odczyt w tej samej
klatce, w której zmienia się `data-theme`, zwraca wartość POCZĄTKOWĄ przejścia.

Sprawdzone wprost, na czystej stronie z tym samym wzorcem zmiennych CSS:

```
no-preference -> rgb(255, 255, 255)
reduce        -> rgb(11, 13, 15)
```

To zgadza się co do joty z objawem: `atrybut`, `meta` i `localStorage` w tym samym
snapshocie były już poprawne („czerwony”, „#FFFFFF”, „czerwony”), kłamał wyłącznie kolor.
Aplikacja jest w porządku — kłamał pomiar.

## Zmiana

1. `tlo` znika z pomocnika `motyw()`, żeby wzorzec nie wrócił tylnymi drzwiami. Kolor
   sprawdza wyłącznie ponawiane `toHaveCSS` — w trzech miejscach, w których dotąd był
   odczyt jednorazowy (stan wyjściowy, po wyborze jasnego, po odświeżeniu). Czwarte
   miejsce (powrót do ciemnego) już wcześniej używało `toHaveCSS`.
2. `docs/E2E.md` dostaje regułę: koloru z CSS nigdy nie czytamy jednorazowo, z pomiarem
   jako uzasadnieniem.

Asercje nie zostały osłabione: sprawdzany jest ten sam kolor, tylko z ponawianiem.
Żadnego `retries`, żadnego `test.skip`, żadnego wydłużonego `waitForTimeout`.

## Weryfikacja

`tsc --noEmit`, `npm run build`, `e2e/motyw.spec.ts` w projekcie `telefon` trzy razy
z rzędu, potem pełny zestaw Playwright i pozostałe bramki. Wynik w opisie PR.

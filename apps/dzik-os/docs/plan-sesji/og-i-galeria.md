# Plan sesji: karta OG + galeria ekranów na stronie

**Gałąź:** `agent/og-i-galeria` (od `main` = `fef2aa7`)
**Rola:** aktywny piszący (polecenie właściciela, 25.08: pakiet materiałów
marketingowych — punkty „karta OG" i „sekcja Zobacz aplikację" to jedyne
dwa wymagające zmian w repo)
**Cel:** link do strony wysyłany na komunikatorach ma pokazywać markową
kartę, a strona ma pokazywać prawdziwe ekrany aplikacji.

## Zamiar

1. **Meta-tagi Open Graph / Twitter Card** w `frontend/index.html`:
   tytuł, opis, `og:image` (nowy plik `public/og.png`, 1200×630,
   wygenerowany z ekranów demo w stylu marki), `og:url`, `og:locale`
   pl_PL, `twitter:card` summary_large_image. Czysto statyczne — zero
   zmian w logice.
2. **Sekcja „Zobacz aplikację"** na stronie marketingowej
   (`Landing.tsx`, między „Jak zaczynamy" a „O trenerze"): pozioma
   galeria 4 zrzutów telefonu z danych demo (Dzisiaj, Plan, Dieta,
   Postępy) — pliki JPEG w `public/screens/`, `loading="lazy"`,
   przewijanie ze scroll-snap, podpisy pod zrzutami.
3. Zrzuty pochodzą z seedowanych danych demo (żadnych danych
   prawdziwych osób) i są zwykłymi plikami statycznymi.

## Mój obszar

- `frontend/index.html`, `frontend/public/og.png`,
  `frontend/public/screens/*.jpg`, `frontend/src/pages/Landing.tsx`,
  `frontend/src/styles.css` (galeria);
- `frontend/e2e/strona-publiczna.spec.ts` (dopisek: sekcja widoczna);
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Czego nie dotykam

- backendu (zero zmian), Core, PWA manifestu, pozostałych ekranów.

## Rezerwacje

- **Wersja: 0.50.0** (ostatnia: 0.49.0). **Migracja: brak.**

## Świadomie nie robię

- nie dodaję lightboxa/powiększania zrzutów (prosty scroll wystarcza;
  rozbudowa to decyzja po feedbacku);
- nie generuję og.png dynamicznie — statyczny plik, podmienialny ręcznie.

## Weryfikacja (wypełnione 25.08)

- Bramki: ruff czysto, backend 813/1 pominięty, Core 275, spójność,
  mutacje 17/17 i 9/9, frontend tsc+build, helpers 140, **E2E 17/17**
  (dopisek galerii w strona-publiczna.spec).
- Uruchomienie na żywo (serve.sh :8151, świeży dist; co uruchomiłem i co
  zobaczyłem): w źródle `/` komplet tagów og:* i twitter:*;
  `GET /og.png` → 200 (393 682 B); galeria potwierdzona asercją E2E
  (nagłówek + zrzut „Dzisiaj" widoczne).

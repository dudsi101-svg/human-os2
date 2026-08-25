# Plan sesji: prawdziwy trener na stronie

**Gałąź:** `agent/prawdziwy-trener` (od `main` = aktualny)
**Rola:** aktywny piszący (polecenie właściciela, 25.08: „współpracujemy
z Lubelskim Dzikiem — uzyskaj jak najwięcej informacji"; research
z publicznych źródeł wykonany)
**Cel:** sekcja „O trenerze" i kontakt na stronie marketingowej przestają
być neutralnym szkicem — dostają prawdziwe dane Łukasza Drygla
(Lubelski Dzik).

## Źródła danych (publiczne)

Instagram @lubelski_dzik_ifbbpro (bio, 30 tys. obserwujących), Facebook
„Łukasz Drygiel — Trener Personalny Lublin" i @lubelskidzikk, TikTok
@lubelski_dzik, YouTube @Lubelski_dzik_ifbbpro, materiały RAPTOR GYM
Lublin. Kontakt (tel. +48 570 477 540, lubelskidzikk@gmail.com) podawany
publicznie przez samego trenera na profilach — publikacja na stronie za
jego wiedzą (współpraca zadeklarowana przez właściciela).

## Zamiar

1. **Sekcja „O trenerze"** → „Łukasz Drygiel — Lubelski Dzik":
   zawodnik sceny sylwetkowej (IFBB PRO w nazwie profili), trener
   personalny w Lublinie (RAPTOR GYM) i online, społeczność 30 tys.
   na Instagramie; jego własny przekaz „pomogę Ci schudnąć 12 kg
   w 20 tygodni, budując przy tym masę mięśniową".
2. **Kontakt bezpośredni** w sekcji kontaktu i stopce: telefon, e-mail,
   linki do Instagrama/TikToka/YouTube (nofollow noopener).
3. Meta-opis i og:description wzbogacone o „Lublin/online" i markę
   Lubelski Dzik. Miejsce na zdjęcie trenera zostaje jako komentarz
   (zdjęcia niedostępne z tego środowiska — CDN social zablokowany).

## Mój obszar

- `frontend/src/pages/Landing.tsx`, `frontend/index.html`,
  `frontend/src/styles.css` (drobne), `e2e/strona-publiczna.spec.ts`
  (dopisek nazwiska);
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Czego nie dotykam

- backendu, Core, pozostałych ekranów; żadnych twierdzeń
  niepotwierdzonych źródłem (wiek, lata doświadczenia, tytuły zawodów —
  pominięte do potwierdzenia przez trenera).

## Rezerwacje

- **Wersja: 0.51.0** (ostatnia: 0.50.0). **Migracja: brak.**

## Weryfikacja (wypełnione 25.08)

- Bramki: ruff czysto, backend pełny pakiet, Core 275, spójność,
  mutacje 17/17 i 9/9, frontend tsc+build, helpers 140/0,
  **E2E 17/17** (nowe asercje: nazwisko + telefon na stronie).
- Uruchomienie na żywo (serve.sh :8152; co uruchomiłem i co
  zobaczyłem): zrzut sekcji „O trenerze" z nazwiskiem, opisem
  i linkami social (przekazany właścicielowi); linki tel:/mailto:
  obecne pod formularzem.
- Dopisek w rundzie: właściciel dostarczył zdjęcia trenera —
  `public/icons/trener.jpg` (zdjęcie z treningu, 1200 px, ~100 KB)
  wstawione do sekcji; tsc+build+E2E 17/17 ponownie zielone.

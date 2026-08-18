# Testy E2E (Playwright)

## Po co to istnieje

Audyt z 18.08.2026 wykazał asymetrię: backend miał 93% pokrycia linii i 98,9%
operacji API dotykanych testami, a **~15 700 linii interfejsu nie było chronione
niczym, co uruchamia się w CI**. Testy jednostkowe frontendu (82 sztuki)
pokrywają wyłącznie funkcje pomocnicze — filtry, formatowanie, utilsy. Testy
backendu wołają API bezpośrednio, z pominięciem przeglądarki, routingu
i formularzy.

Skutek: backend odmówiłby nieuprawnionego dostępu, ale **nikt nie zauważyłby
ekranu, który przestał się renderować**. Regresja w `ClientDetail.tsx`
(1 715 linii) przechodziła przez wszystkie bramki.

Ten zestaw zamyka tę lukę. Jest celowo mały — lepszy mały zestaw chodzący przy
każdym pushu niż duży, który nie chodzi.

## Zakres

| Plik | Co sprawdza |
| --- | --- |
| `logowanie.spec.ts` | Wejście trenera i klienta, odmowa przy błędnym haśle, odmowa dostępu do panelu trenera bez sesji |
| `raport.spec.ts` | Pełna wysyłka raportu tygodniowego oraz reguła „żadne pytanie nie ma wartości domyślnej" |
| `wiadomosci.spec.ts` | Klient pisze, **trener czyta** — dwie sesje, dwa konta |

Siedem testów, ok. 20 sekund.

## Uruchomienie

```bash
cd apps/dzik-os/frontend
npm install
npm run build        # E2E chodzi po zbudowanym dist/, nie po dev-serverze
npm run test:e2e     # albo: npm run test:e2e:ui
```

Przeglądarka: `npx playwright install chromium` (w CI robi to osobny krok).

## Jak to jest zbudowane

**Testy chodzą po ścieżce produkcyjnej.** Backend serwuje `dist/`
(`DZIK_FRONTEND_DIST`), tak jak na produkcji — nie ma tu dev-servera Vite
z proxy. Dzięki temu test obejmuje także sposób podania aplikacji: CSP,
nagłówki, obsługę tras SPA.

**Każdy przebieg dostaje świeżą bazę.** `e2e/serve.sh` kasuje katalog roboczy
przy starcie, a `reuseExistingServer` jest wyłączone. To nie jest ostrożność na
zapas — raport tygodniowy jest jeden na tydzień i po wysłaniu formularz zmienia
się w „Wyślij poprawkę". Bez świeżej bazy drugi przebieg testował co innego niż
pierwszy.

**Jeden worker, bez równoległości.** Testy zapisują dane do jednej bazy SQLite
z kontami demo. Równoległość dawałaby wyścigi o ten sam stan, czyli dokładnie
tę flakowatość, której ten zestaw ma nie mieć.

**Konta są rozdzielone według roli w teście.** Klient A wysyła raport, klient B
sprawdza walidację. Gdyby oba testy używały jednego konta, ich wynik zależałby
od kolejności uruchomienia.

**Logowanie idzie przez formularz**, nie przez wstrzyknięcie tokenu. Skrót po
API testowałby API, które ma już własne pokrycie.

## Świadome odstępstwa od produkcji

`e2e/serve.sh` ustawia `DZIK_MFA_REQUIRED_ROLES=""`. Produkcja trzyma domyślne
`COACH,ADMIN` (`config.py`). Powód: bramka MFA ma własne pokrycie w testach
backendu, a tutaj chodzi o ekrany, do których trener bez potwierdzonego TOTP
w ogóle by nie dotarł. **To jedyne odstępstwo** — reszta środowiska odpowiada
produkcyjnej.

## Czego ten zestaw NIE sprawdza

- panelu trenera poza listą klientów (`ClientDetail`, plany, dieta, płatności),
- onboardingu, wyzwań, konsultacji, dokumentów, OCR,
- trybu offline i zachowania service workera,
- dostępności (WCAG) i wyglądu (brak testów wizualnych),
- zachowania na prawdziwym urządzeniu — emulowany jest Pixel 7.

Rozszerzanie ma sens tam, gdzie ekran ma stan i zapisuje dane. Ekrany
wyłącznie odczytowe taniej pokryć testem backendu.

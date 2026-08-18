# Obserwowalność Dzik OS — model błędów, logi, metryki, alerty

Stan na wersję 0.11.0. Kod źródłowy: `backend/dzik_os/observability.py`
(request id, logi, metryki, handlery błędów), `backend/dzik_os/routers/telemetry.py`
(`/api/metrics`, raporty błędów frontendu), `frontend/src/api.ts` +
`frontend/src/errorUtils.ts` (klient, timeouty, redakcja raportów).

## 1. Wspólny model błędów API

Każda odpowiedź 4xx/5xx z API ma jeden kształt:

```json
{
  "detail": "Bezpieczny komunikat po polsku",
  "code": "NOT_FOUND",
  "request_id": "6f2a9c0d13b74e21",
  "errors": [{ "field": "password", "type": "missing", "msg": "Field required" }]
}
```

* `detail` — komunikat pokazywany użytkownikowi; pozostaje głównym polem
  (frontend i istniejące testy na nim polegają). Sentinele (np.
  `PASSWORD_CHANGE_REQUIRED`) przechodzą nietknięte.
* `code` — stabilny kod maszynowy: `BAD_REQUEST`, `UNAUTHORIZED`,
  `FORBIDDEN`, `NOT_FOUND`, `METHOD_NOT_ALLOWED`, `CONFLICT`,
  `PAYLOAD_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `VALIDATION_ERROR`,
  `RATE_LIMITED`, `INTERNAL_ERROR`, `SERVICE_UNAVAILABLE`, inne → `HTTP_ERROR`.
* `request_id` — identyfikator żądania; identyczny z nagłówkiem
  `X-Request-Id` (obecny na KAŻDEJ odpowiedzi, także sukcesach), pozwala
  powiązać zgłoszenie użytkownika z wpisem w logu.
* `errors` — tylko przy 422: lista `{field, type, msg}` **bez** pydanticowych
  `input`/`ctx`/`url` (wartość wejściowa może być daną zdrowotną i nigdy nie
  wraca w odpowiedzi ani nie trafia do logów).

Gwarancje:

* Nieobsłużony wyjątek → `500 INTERNAL_ERROR` przez `ErrorEnvelopeMiddleware`
  (najgłębsze ogniwo łańcucha middleware) — odpowiedź nigdy nie zawiera
  stack trace, SQL, typu wyjątku ani komunikatu wewnętrznego, a 500-ki
  dostają te same nagłówki bezpieczeństwa i `Cache-Control: no-store`
  co pozostałe odpowiedzi.
* `ResourceAccessDenied` (P3) działa bez zmian: 404 „Nie znaleziono" +
  zdarzenie audytowe `ACCESS_DENIED` w łańcuchu Human OS; odpowiedź ma teraz
  dodatkowo `code`/`request_id`, a odmowy są zliczane (`access_denied`).

Po stronie klienta `ApiError` (`api.ts`) niesie `status`, `message`
(= `detail`), `code`, `requestId`. Dodatkowe kody lokalne (status 0):
`OFFLINE` (brak sieci), `TIMEOUT` (limit 20 s), `CANCELLED` (żądanie
anulowane przy zmianie widoku — widoki ignorują je przez `isCancel()`).

## 2. Logi strukturalne (stdout, JSON)

Jedna linia JSON na zdarzenie, np.:

```json
{"ts": "2026-08-18T02:41:00.123+00:00", "level": "info", "event": "request",
 "request_id": "6f2a9c0d13b74e21", "method": "GET",
 "path": "/api/clients/{client_id}/profile", "status": 200,
 "duration_ms": 12.4, "user_id": "HOS-USR-AB12CD34EF56"}
```

Zdarzenia: `request` (każde żądanie `/api`), `validation_error`,
`unhandled_exception`, `audit_append_failed`, `reminder_loop_error`,
`push_send_failed`, `frontend_error`, `readiness_check_failed`,
`seed_demo_failed`, `email_skipped_no_provider`.

### Zasady redakcji (obowiązkowe, Konstytucja Human OS / RODO)

W logach i metrykach NIGDY nie występują:

* dane zdrowotne, treści wiadomości, zawartość dokumentów/zdjęć/raportów;
* adresy e-mail — użytkownik wyłącznie jako `user_id` (`HOS-USR-…`);
* hasła, tokeny sesji, ciasteczka, nagłówek `Authorization`, endpointy
  subskrypcji push (URL endpointu działa jak token);
* surowe ścieżki URL z identyfikatorami — logowany jest szablon trasy
  (`/api/files/{file_id}`), a poza routerem ścieżka maskowana (`{id}`);
* treści żądań i odpowiedzi (żaden body nie jest logowany);
* komunikaty wyjątków nie-HTTP — logujemy wyłącznie typ wyjątku i ramki
  stosu `plik:linia:funkcja` (komunikaty ORM/sterowników potrafią zawierać
  wartości parametrów SQL, czyli dane).

Wyjątek świadomy: `seed.py` wypisuje dane kont DEMO na stagingu —
to narzędzie deweloperskie uruchamiane wyłącznie z `DZIK_SEED_DEMO=true`.

## 3. Request id

* Generowany serwerowo dla każdego żądania (16 hex); nagłówek wejściowy
  `X-Request-Id` od klienta jest celowo ignorowany.
* Zwracany w nagłówku `X-Request-Id` każdej odpowiedzi i w polu
  `request_id` modelu błędu.
* Użytkownik przy powtarzającym się błędzie może podać `request_id`
  trenerowi/administratorowi — wpis w logu znajduje się po tej wartości.

## 4. Metryki — `GET /api/metrics` (tylko rola ADMIN)

Liczniki w pamięci procesu (od startu maszyny; przy wdrożeniu
wieloprocesowym — per proces). Bez sekretów i bez danych użytkowników.

```json
{
  "started_at": "2026-08-18T02:00:00+00:00",
  "requests": {"total": 1234, "by_class": {"2xx": 1200, "4xx": 30, "5xx": 4},
               "by_status": {"200": 1180, "404": 20, "500": 4}},
  "latency_ms": {"window": 1000, "p50": 12.0, "p95": 80.5, "p99": 210.0},
  "counters": {
    "reminder_loop_errors": 0,
    "push_send_failures": 0,
    "notif_sent_center": 0,
    "notif_sent_push": 0,
    "notif_sent_email": 0,
    "notif_email_failures": 0,
    "notif_suppressed": 0,
    "onboarding_ai_calls": 0,
    "onboarding_ai_rejected": 0,
    "onboarding_ai_fallback": 0,
    "onboarding_ai_tokens_in": 0,
    "onboarding_ai_tokens_out": 0,
    "onboarding_safety_flags": 0,
    "frontend_error_reports": 0,
    "frontend_error_reports_dropped": 0,
    "unhandled_exceptions": 0,
    "access_denied": 0,
    "audit_log_failures": 0
  }
}
```

Percentyle liczone z okna ostatnich 1000 żądań API (metoda najbliższej
rangi). `/api/health` (liveness) i `/api/ready` (readiness: baza odpowiada,
katalog uploadów zapisywalny; 503 gdy nie) są dostępne bez logowania i nie
zawierają sekretów ani ścieżek.

## 5. Raporty błędów JS frontendu — `POST /api/telemetry/frontend-errors`

* Źródła: `ErrorBoundary` (globalny + per trasa), `window.onerror`,
  `unhandledrejection`.
* Payload: `type` (nazwa klasy błędu), `component` (etykieta miejsca, np.
  `route:/raport` — identyfikatory w ścieżce maskowane do `{id}` już po
  stronie klienta), `stack` **zredagowany po stronie klienta** do listy
  `plik.js:linia:kolumna` własnych bundle'ów.
* Serwer wykonuje redakcję DRUGI raz (defense in depth): typ obcinany do
  identyfikatora klasy, komponent do pojedynczej etykiety, stos do ramek
  plików skryptowych; komunikaty, URL-e, e-maile, tokeny są odrzucane.
* Trwałość: wyłącznie licznik w metrykach + jedna linia logu `frontend_error`
  — treść raportu nie jest nigdzie przechowywana w całości.
* Rate limit: 5/min po stronie klienta, 10/min per IP i 120/min globalnie
  po stronie serwera (przekroczenie → 429 + licznik
  `frontend_error_reports_dropped`); limity rozmiaru pól wymusza schema.
* Endpoint dostępny bez logowania (błędy zdarzają się przed zalogowaniem) —
  stąd twarde limity i zerowa wartość przechowywanych danych.

### Czego monitoring ŚWIADOMIE nie zbiera

Treści raportów tygodniowych, zdjęć, wiadomości, dokumentów, pomiarów,
obserwacji, danych szczególnej kategorii (zdrowotnych), e-maili, tokenów —
potwierdzone testami redakcji w `tests/test_observability.py`
(`test_frontend_error_report_redacts_content`,
`test_500_shape_without_internals`,
`test_request_log_has_user_id_not_email_and_masked_path`,
`test_login_log_never_contains_email_or_password`).

## 6. Progi alertowe (dokumentacja — bez zewnętrznych integracji)

Metryki z `/api/metrics` umożliwiają następujące alerty (do skonfigurowania
w przyszłym systemie monitoringu lub prostym skrypcie cron odpytującym
endpoint kontem ADMIN; dziś: przegląd ręczny):

| Sygnał | Próg ostrzegawczy | Próg krytyczny | Interpretacja |
|---|---|---|---|
| `5xx` / `total` (okno godz.) | > 0,5 % | > 2 % lub > 10 szt./godz. | awaria backendu — sprawdź logi `unhandled_exception` po `request_id` |
| `unhandled_exceptions` | każdy nowy | przyrost > 5/godz. | ścieżka kodu bez obsługi błędu |
| `latency_ms.p95` | > 500 ms | > 2000 ms | przeciążenie / wolne zapytania SQL |
| `reminder_loop_errors` | każdy nowy | przyrost w 3 kolejnych godz. | przypomnienia push nie wychodzą |
| `push_send_failures` | > 20/godz. | rosnący trend dobowy | problem z VAPID / dostawcą push |
| `notif_sent_center` / `notif_sent_push` / `notif_sent_email` | spadek do 0 przy aktywnych użytkownikach | — | doręczenia stanęły (pętla/preferencje/subskrypcje) — liczniki per kanał, **bez treści** (POWIADOMIENIA.md) |
| `notif_email_failures` | każdy nowy przy skonfigurowanym dostawcy | przyrost ciągły | awaria dostawcy e-mail (kanał awaryjny) |
| `notif_suppressed` | — (informacyjny) | nagły skok | masowe tłumienie (np. źle ustawione preferencje/ciche godziny) |
| `onboarding_ai_calls` / `onboarding_ai_tokens_in` / `_tokens_out` | — (informacyjny, kontrola kosztów) | nagły skok wywołań lub tokenów | nietypowe zużycie modelu — sprawdź limity `DZIK_AI_DAILY_CALLS_*` (ONBOARDING_AI.md §8); liczniki są **bez treści** rozmowy |
| `onboarding_ai_rejected` / `onboarding_ai_fallback` | pojedyncze | > 30% wywołań | dostawca przestał trzymać kontrakt wyjścia — onboarding schodzi do trybu deterministycznego (funkcja działa, ale bez wersji roboczej) |
| `onboarding_safety_flags` | — (informacyjny) | — | liczba rozmów skierowanych do konsultacji medycznej; **nie jest KPI** i nie służy do oceny klientów |
| `audit_log_failures` | **każdy** | — | łańcuch audytu nie zapisuje — uruchom `/api/admin/audit/verify` |
| `access_denied` | skok ponad linię bazową | seria z jednego konta | próby IDOR — przejrzyj zdarzenia `ACCESS_DENIED` w audycie |
| `frontend_error_reports` | skok po wdrożeniu | ciągły wzrost | regresja UI — sprawdź `frontend_error` w logach |
| `/api/ready` ≠ 200 | 1 próbka | 2 kolejne próbki | baza niedostępna lub dysk uploadów niezapisywalny |

Linia bazowa: po tygodniu działania zanotuj typowe wartości dobowe i
aktualizuj progi względem nich. Restart maszyny zeruje liczniki
(`started_at` mówi, od kiedy liczone).

## 7. Zachowanie frontendu przy błędach (kontrakt UX)

* Ekrany błędów mają przycisk „Spróbuj ponownie" (`ErrorBox onRetry`);
  spinner nigdy nie jest wieczny (timeout 20 s → czytelny komunikat).
* Błąd ZAPISU nie czyści formularza — komunikat pojawia się przy formularzu,
  a wpisane dane zostają do ponowienia (raport, trening, cele, wiadomości).
* 401 poza logowaniem → powrót do `/login` z komunikatem „sesja wygasła"
  (jednorazowy notice w `sessionStorage`).
* Brak sieci → pełnoekranowy `OfflineScreen` (z P6; formularz pod spodem
  pozostaje zamontowany) + `OFFLINE` w błędach poszczególnych żądań.
* Zmiana widoku/parametru anuluje nieaktualne żądania (`AbortController` +
  `isCancel`) tam, gdzie spóźniona odpowiedź mogłaby nadpisać dane innego
  zasobu (wątek wiadomości, karta klienta, miniatury plików, wykresy).
* Awaria renderowania → `ErrorBoundary` (globalny i per trasa) zamiast
  białego ekranu; błąd raportowany w formie zredagowanej.
* Świadome zignorowanie błędu jest dozwolone wyłącznie z komentarzem
  uzasadniającym w kodzie (np. karty-podpowiedzi na „Dzisiaj", fail-open
  bramy zgód — egzekwowanie i tak w backendzie, best-effort push/telemetrii).

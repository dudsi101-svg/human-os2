# Płatności — model, maszyna stanów, idempotencja, pojednanie

Runda 15. System płatności Dzik OS jest **ewidencją ręczną** (świadoma
decyzja produktowa — realna integracja operatora online odłożona): trener
prowadzi harmonogram należności i rejestruje otrzymane wpłaty adnotacjami.
Architektura pod przyszłego operatora jest przygotowana i przetestowana
kontraktowo (patrz §Operator), ale ŻADNA działająca integracja nie istnieje.

## 1. Model danych

Jednoznaczne rozdzielenie: **co się należy** od **co faktycznie wpłynęło**.

| Obiekt | Tabela | Rola |
|---|---|---|
| Harmonogram | `payment_schedules` | pakiet współpracy: nazwa, kwota (grosze) + waluta, okres (MONTHLY/WEEKLY/ONE_OFF), opcjonalny zewnętrzny link płatności |
| **Należność** (okres rozliczeniowy) | `payment_records` | „kwota X należna na termin Y" — nośnik statusu (maszyna stanów niżej); `marked_by`/`marked_at` = kto i kiedy ręcznie oznaczył |
| **Transakcja** | `payment_transactions` | append-only przepływ/korekta: `MANUAL_PAYMENT` (adnotacja trenera), `PROVIDER_PAYMENT` (przyszły operator), `REFUND` (zwrot), `ADJUSTMENT` (korekta księgowa, może być ujemna), `REVERSAL` (korekta odwracająca inną transakcję — `reverses_transaction_id`) |
| Historia statusów | `payment_status_changes` | append-only przejścia per rekord: kto, kiedy, skąd→dokąd, powód, powiązana transakcja |
| Próba płatności | `payment_attempts` | sesja u operatora online (STARTED/SUCCEEDED/FAILED/EXPIRED); system ręczny ich nie tworzy |
| Zdarzenie operatora | `payment_provider_events` | rejestr przetworzonych webhooków — idempotencja i ochrona przed złą kolejnością |

Zasady przekrojowe:

* **Kwoty zawsze całkowite w groszach** (`amount_cents`, int) z kodem waluty
  przy każdej kwocie — także zwroty i korekty. Waluta operacji musi się
  zgadzać z walutą należności (422); kwot w różnych walutach nigdy nie
  sumujemy.
* **Faktury: wyłącznie pole referencji** `document_ref` (numer dokumentu
  zewnętrznego — faktura/przelew) na transakcji. Bez generatora faktur.
* **Append-only**: transakcje i historia statusów nie są nigdy edytowane
  ani usuwane. Cofnięcie omyłki = wpis `REVERSAL` wskazujący odwracaną
  transakcję (para znosi się do zera w sumach efektywnych, obie pozostają
  widoczne). Transakcję można odwrócić najwyżej raz.
* **Audyt Human OS**: każda zmiana statusu (`PAYMENT_STATUS_CHANGED`),
  każda transakcja (`PAYMENT_TRANSACTION_RECORDED`) i każde odwrócenie
  (`PAYMENT_TRANSACTION_REVERSED`) trafiają do hash-chained łańcucha
  zdarzeń z pokwitowaniem (Receipt).
* **Izolacja**: cudze płatności = 404 (logowana odmowa zasobowa, testy
  IDOR); dane finansowe klienta widzi wyłącznie on sam i trener-właściciel
  harmonogramu.

## 2. Maszyna stanów należności

Jedyne źródło prawdy: `payment_state.ALLOWED_PAYMENT_TRANSITIONS`,
egzekwowane w backendzie — **nieprawidłowe przejście = 422**, frontend
niczego nie wymusza.

```
PLANNED ──→ PENDING ──→ (IN_PROGRESS) ──→ PAID
   │           │  │            │            │ ├─→ PARTIALLY_REFUNDED ─→ REFUNDED
   │           │  │            │            │ │         │    ↑↺ (kolejny zwrot)
   │           │  └─→ OVERDUE ─┤            │ │         └──→ PAID  (REVERSAL zwrotu)
   │           │  └─→ FAILED ──┤            │ └─→ PENDING/OVERDUE (REVERSAL wpłaty)
   └─→ CANCELLED ←─────────────┘            │
          └─→ PENDING (przywrócenie)     REFUNDED ─→ PAID / PARTIALLY_REFUNDED
                                                     (wyłącznie REVERSAL zwrotu)
```

Pełna tablica (z → do):

| z \ do | PLANNED | PENDING | IN_PROGRESS | PAID | OVERDUE | FAILED | CANCELLED | PART_REF | REFUNDED |
|---|---|---|---|---|---|---|---|---|---|
| PLANNED | — | ✓ | — | ✓ | — | — | ✓ | — | — |
| PENDING | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| IN_PROGRESS | — | ✓ | — | ✓ | — | ✓ | ✓ | — | — |
| OVERDUE | — | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — |
| FAILED | — | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — |
| PAID | — | ✓¹ | — | — | ✓¹ | — | — | ✓ | ✓ |
| CANCELLED | — | ✓ | — | — | — | — | — | — | — |
| PART_REF | — | — | — | ✓² | — | — | — | ✓ | ✓ |
| REFUNDED | — | — | — | ✓² | — | — | — | ✓² | — |

¹ wyłącznie korektą odwracającą wpłatę (endpoint `reverse`).
² wyłącznie korektą odwracającą zwrot.

Podział endpointów:

* `POST /records/{id}/status` — tylko statusy **administracyjne**
  (`PENDING`, `OVERDUE`, `CANCELLED`); „PAID" w tym endpoincie nie
  przechodzi nawet walidacji schematu.
* `POST /records/{id}/mark-paid` — transakcja ręczna `MANUAL_PAYMENT`
  + przejście → PAID; zapisuje kto/kiedy (`marked_by`/`marked_at`,
  widoczne w UI klienta i trenera).
* `POST /records/{id}/refund` — `REFUND`; suma zwrotów ≤ suma wpłat;
  częściowy → `PARTIALLY_REFUNDED`, pełny → `REFUNDED`.
* `POST /records/{id}/adjust` — `ADJUSTMENT` z obowiązkowym powodem
  (status bez zmian).
* `POST /transactions/{id}/reverse` — `REVERSAL`; status wyliczany na nowo
  z efektywnej księgi (cofnięcie omyłkowego „opłacona" wraca do
  PENDING/OVERDUE zależnie od terminu, ślad zostaje).
* `GET /records/{id}/history` — przejścia + transakcje (klient widzi
  własne, trener swoje harmonogramy).

`OVERDUE` jest też liczone prezentacyjnie (`effective_status`): wymagalna
należność po terminie pokazywana jako zaległa bez mutowania wiersza.

## 3. Idempotencja

Dwie niezależne warstwy:

1. **Operacje trenera (P11, `idempotency.py`)** — `mark-paid`, `refund`,
   `adjust`, `reverse` przyjmują `idempotency_key`. Powtórka z tym samym
   kluczem i tą samą treścią zwraca zapisany wynik (zero drugiej
   transakcji — ochrona przed podwójnym kliknięciem/retry); ten sam klucz
   z inną treścią = 409. Niezależnie od klucza maszyna stanów blokuje
   podwójną wpłatę (PAID → PAID nie istnieje = 422).
2. **Zdarzenia operatora** — unikalne `(provider, event_id)` w
   `payment_provider_events`: powtórka = `DUPLICATE` bez skutków; ten sam
   `event_id` z inną treścią (hash ciała) = `CONFLICT`; zdarzenie starsze
   niż ostatnie przetworzone dla rekordu = `STALE` (bez cofania stanu);
   `PAID` nigdy nie jest cofane zdarzeniem operatora. Zdarzenia z błędnym
   podpisem NIE są zapisywane (tylko log + metryka) — niezweryfikowany
   `event_id` nie może zapychać rejestru.

## 4. Przypomnienia

Pętla przypomnień (`reminder_loop._payment_reminders`, 08:00 czasu
lokalnego) wysyła push wyłącznie dla należności **realnie wymagalnych**
(`DUE_STATUSES = PENDING/OVERDUE/FAILED`, `IN_PROGRESS` celowo poza —
nie ponaglamy w trakcie próby płatności): w dniu terminu i co 7 dni
zaległości. Status jest sprawdzany w zapytaniu **w chwili wysyłki** —
opłacona/anulowana/zaplanowana rata nigdy nie dostaje przypomnienia.
Treść neutralna: **bez kwot, walut i nazw pakietów** (powiadomienie może
pojawić się na ekranie blokady).

## 5. Migracja (nr 15) i plan wycofania

* Stare statusy (`PENDING/PAID/OVERDUE/CANCELLED`) są ścisłym podzbiorem
  nowego słownika — **mapowanie tożsamościowe, nic nie jest przepisywane**
  (zero utraty danych).
* `payment_records.marked_at` = `paid_at` dla wierszy z `paid_at`
  (jedyny znany moment oznaczenia); reszta NULL.
* Nowe tabele startują **puste** — historia nie jest fabrykowana wstecz.
  Rekordy PAID sprzed migracji nie mają transakcji; raport pojednania
  oznacza je `source=LEGACY` (liczone po kwocie należności), a zwrot
  takiego rekordu przyjmuje kwotę należności jako podstawę.
* Test zgodności wstecznej: `tests/test_payments_lifecycle.py::
  test_migration_v1_to_v15_preserves_payment_data` (v1 z danymi → v15).
* **Plan wycofania**: migracja jest addytywna (ALTER ADD COLUMN + nowe
  tabele) — rollback aplikacji do wersji sprzed rundy 15 działa na tej
  samej bazie bez migracji w dół (stary kod ignoruje nowe kolumny/tabele;
  statusy pozostają zrozumiałe, bo stary słownik to podzbiór). Jedyna
  strata przy rollbacku: nowe statusy (`PLANNED`, `REFUNDED`, ...) stary
  frontend pokaże bez etykiety — bez utraty danych.

## 6. Raport pojednania (reconciliation)

`GET /api/payments/reconciliation?month=RRRR-MM` (+ widok trenera
`/trener/rozliczenia`): per rekord z terminem w okresie — należne vs
zebrane (suma efektywnych wpłat), zwroty, korekty, różnica i **źródło**
(`MANUAL`/`PROVIDER`/`MIXED`/`LEGACY`/`NONE`); sumy per **waluta**
(nigdy nie mieszane). Dziś wszystkie wpisy pochodzą z adnotacji ręcznych;
po podłączeniu operatora jego transakcje pojawią się w tym samym formacie.

## 7. Operator płatności — przygotowana architektura (BEZ integracji)

Port: `payments_provider.PaymentProviderPort` — `payment_link()`,
`verify_webhook_signature()`, `parse_webhook()` → `WebhookEvent`
(`event_id`, typ `payment.started/succeeded/failed`, `record_id`, kwota,
waluta, `occurred_at`, `session_id`). Wspólne przetwarzanie:
`payment_events.process_webhook()` (podpis → parsowanie → idempotencja →
kolejność → maszyna stanów → audyt). Kontrakt przybity testami na
`NullPaymentProvider` (`tests/test_payment_webhooks.py`): zła sygnatura,
powtórka, konflikt treści, zła kolejność, nie-cofanie PAID, waluty.

Zasady bezpieczeństwa (obowiązują każdego przyszłego providera):

1. **Jedynym źródłem prawdy jest podpisany webhook.** Przekierowanie
   przeglądarki (return/redirect URL) NIGDY nie zmienia statusu — żaden
   kod nie czyta parametrów powrotu.
2. Klucze API wyłącznie przez zmienne środowiskowe.
3. Aplikacja nigdy nie przechowuje danych kart płatniczych.

Podłączenie prawdziwego operatora (Stripe / Przelewy24 / PSP z BLIK) w
przyszłości:

1. Zaimplementuj klasę portu (mapowanie typów zdarzeń operatora na
   `payment.started/succeeded/failed`, weryfikacja podpisu wg dokumentacji
   operatora — np. `Stripe-Signature` z tolerancją czasu).
2. Wskaż ją w konfiguracji (`DZIK_PAYMENT_PROVIDER`) i podaj sekrety przez
   zmienne środowiskowe.
3. Dodaj endpoint HTTP `POST /api/payments/webhook/{provider}` (dziś
   celowo NIE istnieje): surowe ciało + nagłówek podpisu →
   `payment_events.process_webhook()` → zawsze 200 dla wyników
   `DUPLICATE/STALE/IGNORED` (operatorzy ponawiają przy nie-2xx),
   401/400 tylko dla złego podpisu/treści.
4. `payment_link()` zwraca URL sesji operatora — frontend już go używa
   (przycisk „Opłać").
5. Rozszerz testy kontraktu o realne fixture'y operatora; kontrakt
   przetwarzania pozostaje ten sam.

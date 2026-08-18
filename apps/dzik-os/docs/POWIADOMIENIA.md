# Powiadomienia i przypomnienia — model, harmonogram, prywatność

Dokument opisuje wspólny system powiadomień Dzik OS wprowadzony w wersji
0.18.0 (migracja schematu nr 14): jeden model danych dla wszystkich
kategorii i kanałów, serwerowy harmonogram z idempotencją w bazie oraz
zasady prywatności treści. Kod: `backend/dzik_os/notifications.py`
(serwis), `reminder_loop.py` (pętla), `routers/notifications.py` (API),
frontend `src/pages/Notifications.tsx` (centrum + ustawienia).

## 1. Wspólny model (`notifications`)

Jeden wiersz = jedno logiczne powiadomienie do jednego odbiorcy.

| Pole | Znaczenie |
|---|---|
| `user_id` | odbiorca |
| `category` | `TRENING` / `SUPLEMENT` / `HARMONOGRAM` / `RAPORT` / `WIADOMOSC` / `PLATNOSC` / `DOKUMENT` / `ZMIANA_PLANU` / `KONSULTACJA` |
| `title`, `body` | treść dla **centrum w aplikacji** (widoczna po zalogowaniu) |
| `url` | ekran docelowy kliknięcia (push i centrum), zawsze wewnętrzna ścieżka |
| `status` | `SCHEDULED` → `SENT` / `CANCELLED` / `SUPPRESSED` |
| `suppressed_reason` | `task_done` / `preferences` / `expired` / `source_gone` |
| `channels` | kanały faktycznie doręczone (CSV `center,push,email`) |
| `dedup_key` | klucz idempotencji, `UNIQUE(user_id, dedup_key)` |
| `source` | obiekt źródłowy (`schedule_item:…`, `reminder:…`, `payment_record:…`, `consult_slot:…`, `message:…`) |
| `timezone`, `scheduled_at` | strefa użyta przy planowaniu + termin w UTC |
| `sent_at`, `read_at` | doręczenie / przeczytanie w centrum |

Kanały: **CENTER** (centrum powiadomień — sam wiersz), **PUSH** (Web
Push, treść neutralna), **EMAIL** (opcjonalny kanał awaryjny przez
`notifications_provider`; domyślnie `NullNotificationProvider`, więc
dopóki operator nie skonfiguruje dostawcy, nic nie wychodzi).

Preferencje (`notification_preferences`): kategoria × kanał per
użytkownik; brak wiersza = domyślne **PUSH on, CENTER on, EMAIL off**.
Ustawienia (`notification_settings`): ciche godziny (czas lokalny,
zakres może przechodzić przez północ), dni aktywne przypomnień,
częstotliwość przypomnienia o raporcie (`DAILY`/`WEEKLY`). Strefa
czasowa mieszka na `users.timezone` (IANA; NULL = `DZIK_TZ`) i jest
czytana przez `dates.tz_for_user()` — czyli steruje też datami
kalendarzowymi w całej aplikacji.

## 2. Strategia harmonogramu

Pętla w procesie (`reminder_loop`, tick co ~60 s) wykonuje dwa kroki:

1. **Planowanie** (`plan_day`) — materializuje dzisiejsze wystąpienia
   jako wiersze `SCHEDULED`, licząc porę w **lokalnej strefie każdego
   odbiorcy** (DST rozstrzyga `zoneinfo`; termin zapisany w UTC):
   * elementy harmonogramu z ustawioną porą (`time_of_day`, dni
     tygodnia, okno `start_date`/`end_date`, dni aktywne użytkownika);
   * jednorazowe przypomnienia trenera (`reminders`) — 08:00 lokalnie
     w dniu `due_date`;
   * płatności `PENDING` z dzisiejszym `due_date` — 08:00 lokalnie.
   Idempotentnie po `dedup_key` (np. `schedule:{item}:{data}`;
   dla raportu z częstotliwością WEEKLY klucz zawiera tydzień ISO
   zamiast dnia — to cała implementacja częstotliwości).
2. **Doręczanie** (`dispatch_due`) — wiersze z terminem ≤ teraz
   przechodzą bramki **przy wysyłce**:
   * *zadanie wykonane* — odhaczony element harmonogramu, wysłany
     raport bieżącego tygodnia, opłacona płatność, odwołany slot,
     wstrzymane źródło → `SUPPRESSED/task_done|source_gone`;
   * *preferencje* — wszystkie kanały kategorii wyłączone →
     `SUPPRESSED/preferences`;
   * *ciche godziny* — push i e-mail wyciszone, **centrum zawsze
     dostaje wpis** (nic nie ginie, nic nie budzi);
   * *spóźnienie* — powyżej `LATE_SEND_MAX` (30 min) →
     `SUPPRESSED/expired` (przypomnienie sprzed godzin to szum).

Powiadomienia zdarzeniowe (wiadomość, odpowiedź na raport, nowa wersja
planu, dokument, rezerwacje konsultacji, nowa pozycja płatności) idą tą
samą ścieżką (`notify_now`) z pominięciem kolejki terminów; rezerwacja
konsultacji dodatkowo planuje przypomnienie 60 min przed startem.

**Idempotencja i restart**: dedup żyje wyłącznie w bazie
(`UNIQUE(user_id, dedup_key)`) — restart maszyny niczego nie duplikuje;
wiersz `SCHEDULED` czeka na doręczenie, więc krótki przestój (do
`LATE_SEND_MAX`) niczego nie gubi. Zastępuje to dawny zbiór `_sent`
w pamięci procesu.

**Zmiana/odwołanie terminu**: `cancel_source(source)` anuluje wiersze
`SCHEDULED` danego źródła. Wywoływane przy: wstrzymaniu/zakończeniu
elementu harmonogramu, odwołaniu slotu przez trenera, zdjęciu
rezerwacji przez klienta. Wiersze już wysłane pozostają (historia
doręczeń jest niemutowalna).

**Żywe aktualizacje**: po commicie doręczenia zdarzenie
`notification.new` płynie kanałem SSE z P12 (`/api/threads/events`) do
otwartej aplikacji odbiorcy — centrum aktualizuje się bez odświeżania.

Ograniczenie wdrożeniowe: pętla i magistrala SSE żyją w jednym procesie
(fly.toml `min_machines_running=1`) — jak w `docs/WIADOMOSCI.md`.

## 3. Zasady prywatności treści (Konstytucja Human OS / RODO)

* **Ekran blokady jest niezaufany.** Push i e-mail niosą wyłącznie
  neutralny tytuł kategorii (`push_title`) i stałe wezwanie „Masz nowe
  powiadomienie w Dzik OS…". Nigdy: dane zdrowotne, nazwy suplementów
  (kategoria `SUPLEMENT` dostaje celowo ogólne „Przypomnienie
  z harmonogramu"), tytuły dokumentów, kwoty i terminy płatności,
  treści wiadomości, nazwiska.
* **Szczegóły dopiero po uwierzytelnieniu** — klik prowadzi do
  właściwego ekranu aplikacji (`url` per kategoria, np.
  `/wiadomosci/{wątek}`, `/plan`, `/dokumenty`); pełna treść jest
  w centrum powiadomień, za logowaniem.
* **Kwoty nigdzie** — także w centrum wiersz płatności nie zawiera
  kwoty (jednolita zasada; kwoty są na ekranie Płatności).
* **Push = zgoda** — subskrypcja powstaje wyłącznie po jawnym opt-in
  (kategoria zgód `przypomnienia`); cofnięcie zgody usuwa wszystkie
  subskrypcje. Zachęta w UI jest kontekstowa (`PushContextPrompt` na
  ekranie Dzisiaj i w Wiadomościach) z wyjaśnieniem korzyści —
  systemowy dialog przeglądarki dopiero po świadomym kliknięciu.
* **Monitoring bez treści** — `/api/metrics` (ADMIN) ma wyłącznie
  liczniki per kanał: `notif_sent_center`, `notif_sent_push`,
  `notif_sent_email`, `notif_email_failures`, `notif_suppressed`,
  `push_send_failures`. Logi nigdy nie zawierają treści powiadomień
  ani endpointów subskrypcji. **Żadnych metryk zaangażowania** — liczba
  wysłanych/klikniętych powiadomień nie jest niczyim KPI.
* **Eksport i usunięcie konta** obejmują powiadomienia, preferencje
  i ustawienia (`export_version` 1.3; przy usunięciu konta wiersze
  znikają w całości).

## 4. Plan wycofania migracji 14

Migracja jest addytywna (nowe tabele + jedna kolumna), więc wycofanie
nie dotyka istniejących danych domenowych.

1. Wdrożyć poprzednią wersję aplikacji (stary `reminder_loop` z dedup
   w pamięci wraca do działania bez nowych tabel; duplikat po restarcie
   w tej samej minucie znów staje się możliwy — znane, akceptowane
   ograniczenie tamtej wersji).
2. Usunąć wpis `14` z `schema_migrations`.
3. Opcjonalnie usunąć obiekty (dane doręczeń to metadane operacyjne;
   ich utrata nie narusza danych klienta):
   `DROP TABLE notifications; DROP TABLE notification_preferences;
   DROP TABLE notification_settings;`
4. Kolumny `users.timezone` SQLite nie usuwa bezpiecznie w miejscu —
   zostaje jako nieużywana (NULL = strefa aplikacji, stary kod jej nie
   czyta bo `tz_for_user` starej wersji używał tylko `getattr` z tym
   samym skutkiem). Przy przejściu na PostgreSQL: `ALTER TABLE users
   DROP COLUMN timezone`.

Uwaga: powiadomienia wysłane nowym systemem mają wpisy w centrum tylko
w tych tabelach — wycofanie oznacza utratę historii centrum (nie
łańcucha audytu, który żyje w `SQLiteEventStore`).

## 5. Znane ograniczenia / świadome decyzje

* E-mail wymaga skonfigurowania dostawcy przez operatora (adapter
  `notifications_provider`); do tego czasu preferencja EMAIL jest
  możliwa do włączenia, ale nic nie wychodzi (licznik
  `notif_email_failures` nie rośnie — Null provider zwraca `False`
  bez błędu).
* Ciche godziny wyciszają kanały „przeszkadzające" (push/e-mail);
  zaplanowane przypomnienie nie jest przesuwane na koniec ciszy —
  przypomnienie o suplemencie z 23:00 wysłane o 7:00 rano byłoby
  dezinformacją. Wpis w centrum pozostaje.
* Dni aktywne działają na etapie planowania (wystąpienie w wyłączony
  dzień w ogóle nie powstaje) i dotyczą przypomnień z harmonogramu;
  powiadomienia zdarzeniowe (wiadomość itd.) nie podlegają dniom
  aktywnym — od ich wyciszenia są preferencje i ciche godziny.
* Skala zapytań planowania jest liniowa względem aktywnych elementów
  harmonogramu — właściwa dla skali jednego trenera; przy większej
  skali planowanie wymaga indeksowanego zapytania per okno czasu.

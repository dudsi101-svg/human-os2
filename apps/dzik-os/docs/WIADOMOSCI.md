# Wiadomości: czas rzeczywisty, statusy i nagrania głosowe — Dzik OS

Dokument opisuje architekturę wiadomości od wersji 0.15.0: transport
czasu rzeczywistego, model statusów, deduplikację i paginację, formaty
nagrań głosowych, zasady prywatności i retencji oraz plan wycofania
migracji nr 13.

## 1. Transport czasu rzeczywistego: SSE (nie WebSocket)

Kanał: `GET /api/threads/events` (Server-Sent Events,
`text/event-stream`), implementacja `dzik_os/realtime.py` +
`routers/messages.py`; klient `frontend/src/realtime.ts` (własny
odpowiednik EventSource na `fetch` + `ReadableStream`).

Dlaczego SSE, a nie WebSocket:

* **Uwierzytelnienie.** Przeglądarkowy WebSocket nie umie wysłać nagłówka
  `Authorization`; wymagałby tokenu w query stringu (trafia do logów
  proxy — zakazane) albo protokołu ticketowego. Natywny `EventSource` ma
  tę samą wadę, dlatego frontend używa `fetch` z nagłówkiem
  `Authorization: Bearer` i własnego parsera strumienia — token nigdy
  nie opuszcza nagłówka.
* **Middleware.** SSE to zwykła odpowiedź HTTP, więc przechodzi przez ten
  sam łańcuch co reszta API: nagłówki bezpieczeństwa P5 (CSP, nosniff),
  `X-Request-Id` i model błędów P9, `Cache-Control: no-store` na `/api`.
  WebSocket omija cały ten łańcuch (osobny handshake ASGI) i wymagałby
  zdublowania tych gwarancji.
* **Infrastruktura.** Fly proxy przepuszcza strumieniowane HTTP bez
  konfiguracji; odpowiedź niesie `X-Accel-Buffering: no` przeciw
  buforowaniu pośredników. Ruch jest jednokierunkowy (serwer → klient;
  wysyłka i tak idzie POST-em z potwierdzeniem), więc dwukierunkowość
  WebSocketu nie daje tu nic.
* **CSP i service worker.** `connect-src 'self'` obejmuje `fetch` do
  własnego origin — zero zmian w polityce (WebSocket wymagałby dopisania
  `wss:`). `sw.js` nie przejmuje żądań `/api` (network-only), więc
  strumień nie jest nigdy cachowany ani buforowany przez SW.

Zdarzenia kanału: `ready` (potwierdzenie połączenia), `message.new`,
`message.delivered`, `message.read`, `resync` (kolejka subskrybenta się
przepełniła — klient ma pobrać stan przez GET), `session_expired`;
keepalive (komentarz SSE) co `DZIK_SSE_KEEPALIVE_S` (domyślnie 25 s).

Bezpieczeństwo kanału:

* wejście przez standardowe `current_user` (401 bez ważnej sesji);
* **każde doręczane zdarzenie** przechodzi ponownie bramkę strony wątku
  (`_party_may_view` ≡ `require_thread_party`: klient z wątku zawsze,
  trener tylko przy AKTYWNEJ relacji i nieocofniętej zgodzie kategorii
  „komunikacja") — cofnięcie zgody w trakcie otwartego strumienia
  odcina treści od tej chwili;
* ważność sesji jest sprawdzana w trakcie strumienia (przy każdym
  zdarzeniu i keepalive) — wylogowanie/unieważnienie tokenu zamyka kanał
  zdarzeniem `session_expired`, a frontend robi czytelny powrót do
  logowania (ten sam mechanizm co 401 w `api.ts`).

Ograniczenie: magistrala zdarzeń żyje **w pamięci jednego procesu**
(deployment: jedna maszyna, `min_machines_running = 1` w fly.toml).
Wdrożenie wieloprocesowe/wielomaszynowe wymaga wspólnego brokera
(np. Redis pub/sub) — do tego czasu skalowanie poziome jest świadomie
poza zakresem. Odbiorca offline niczego nie traci: dostaje neutralny
push, a stan dogania przy wejściu w wątek (źródłem prawdy jest baza,
nie strumień).

### Fallback i ponowne łączenie (frontend)

* automatyczny reconnect z wykładniczym backoffem 1 s → 30 s (+ jitter);
* po 3 nieudanych próbach z rzędu ekran rozmowy przechodzi na
  **kontrolowany polling co 15 s — wyłącznie na otwartym i widocznym
  ekranie rozmowy** (`document.hidden` wstrzymuje odpytywanie); powrót
  kanału kończy polling i robi jedno pobranie wyrównujące;
* lista wątków (`Messages.tsx`) odświeża liczniki co 30 s na otwartym
  ekranie + przy powrocie do karty — bez własnego kanału;
* niewysłana treść przeżywa utratę sieci: szkic per wątek w
  `sessionStorage` (`dzik_draft_<threadId>`), przywracany po powrocie
  na ekran; błąd wysyłki NIE czyści pola.

## 2. Model statusów wiadomości

| Status | Pole | Kiedy |
|---|---|---|
| wysłana | `created_at` (wiersz istnieje) | serwer przyjął POST i zapisał wiadomość; odpowiedź POST to potwierdzenie wysłania |
| dostarczona | `delivered_at` | urządzenie odbiorcy odebrało wiadomość: na żywo strumieniem SSE albo pobierając wątek (GET); read implikuje delivered |
| przeczytana | `read_at` | odbiorca miał otwarty wątek: GET bez `before` albo `POST /threads/{id}/read` (ekran otwarty w chwili nadejścia) |

Zasady: znaczniki są monotoniczne (nigdy nie są cofane), ustawia je
wyłącznie strona odbierająca, nadawca dostaje potwierdzenia zdarzeniami
`message.delivered` / `message.read`. UI pokazuje status pod własnym
dymkiem: „wysyłanie…" (optymistyczna, przed odpowiedzią serwera) →
„wysłano" → „dostarczono" → „przeczytano". Liczba nieprzeczytanych per
wątek: pole `unread` w `GET /api/threads`.

## 3. Deduplikacja, kolejność, paginacja

* **`client_msg_id`** (opcjonalny, `[A-Za-z0-9_-]{8,64}`, frontend
  generuje `crypto.randomUUID()`): ponowienie POST-a po utracie sieci
  z tym samym identyfikatorem zwraca istniejącą wiadomość
  (`duplicate: true`) zamiast tworzyć drugą. Unikalność per
  (wątek, autor, client_msg_id) — częściowy indeks unikalny w bazie
  (pas i szelki dla wyścigów), a różni autorzy mogą użyć tej samej
  wartości bez kolizji.
* **Kolejność**: stabilny klucz `(created_at, id)` po obu stronach
  (ORDER BY backendu i `sortMessages` frontendu) — kolejność nie zależy
  od kolejności doręczeń SSE/HTTP; zdarzenia przychodzące nie w porządku
  są wstawiane na właściwe miejsce (`mergeMessage`), duplikat po `id`
  jest scalany, a wiadomość optymistyczna podmieniana po `client_msg_id`.
* **Paginacja**: `GET /threads/{id}/messages?limit=50&before=<id>` —
  kursor to id najstarszej znanej wiadomości; strona = poprzednie
  `limit` wiadomości wg klucza porządku, `has_more` mówi, czy są starsze
  („Wczytaj starsze wiadomości" w UI). Kursor spoza wątku → 404.
  Dociąganie starszych stron NIE zmienia znaczników przeczytania.

## 4. Nagrania głosowe

Frontend (`src/audioCapture.ts`, logika testowana w Node):

* format wybierany przez `MediaRecorder.isTypeSupported` z listy:
  `audio/webm;codecs=opus` → `audio/webm` → `audio/mp4;codecs=mp4a.40.2`
  → `audio/mp4` → `audio/ogg;codecs=opus` → `audio/ogg`; nic wspieranego
  → wybór przeglądarki. Wysyłany typ to **rzeczywisty
  `recorder.mimeType`** zredukowany do typu bazowego (bez `;codecs=…`),
  nigdy sztywne `audio/webm`; rozszerzenie pliku wynika z typu
  (`.webm`/`.m4a`/`.ogg`/`.mp3`);
* wsparcie przeglądarek: Chrome/Edge/Firefox/Android → WebM/Opus;
  Safari (macOS i iOS ≥ 14.3) → audio/mp4 (AAC); iOS < 14.3 nie ma
  MediaRecordera — przycisk nagrywania zgłasza czytelny błąd, załącznik
  audio można wciąż dodać plikiem;
* **wszystkie ścieżki mikrofonu są zatrzymywane** (`track.stop()`) po
  zakończeniu, anulowaniu, błędzie recordera i odmontowaniu komponentu
  (`dispose()` w cleanupie efektu) — odmowa dostępu do mikrofonu nie
  otwiera żadnej ścieżki;
* limit czasu 3 min (auto-stop z zachowaniem nagrania) i rozmiaru 15 MB
  po stronie klienta (limit uploadu backendu obowiązuje niezależnie);
* przed wysłaniem: odsłuch (`<audio controls>` na krótkotrwałym
  `URL.createObjectURL`), „nagraj ponownie" i „usuń"; wszystkie Blob URL
  są zwalniane (`URL.revokeObjectURL` przy zmianie pliku i odmontowaniu).

Backend (`file_safety.py`, `storage.save_upload`): allowlista typów
audio `audio/webm`, `audio/mp4` (M4A/AAC), `audio/mpeg`, `audio/ogg`;
deklarowany typ musi zgadzać się z **zawartością** (magic bytes: EBML,
`ftyp`, ID3/ramka MPEG, OggS) — niezgodność = 415; typ z parametrem
kodeka (`audio/webm;codecs=opus`) nie jest na allowliście (fail-closed,
frontend wysyła typ bazowy).

## 5. Prywatność (Konstytucja Human OS / P9)

* treści rozmów i nagrania NIE trafiają do logów, metryk ani push:
  push o nowej wiadomości to neutralne „Nowa wiadomość" (test
  `test_push_for_new_message_has_no_body_content`); logi żądań widzą
  wyłącznie szablon trasy (`/api/threads/{thread_id}/messages`);
  zdarzenia SSE nie są logowane (payload żyje tylko w pamięci magistrali
  i w strumieniu do uprawnionego odbiorcy);
* audyt (ACCESS_DENIED itd.) zawiera endpoint i identyfikatory, nigdy
  treść;
* IDOR = 404 na każdej ścieżce (historia, wysyłka, read, kursor
  paginacji, doręczenie zdarzenia SSE);
* `Cache-Control: no-store` na całym `/api` obejmuje strumień; `sw.js`
  nie przejmuje `/api` (network-only), więc nic z kanału nie ląduje w
  Cache Storage.

## 6. Retencja i usuwanie wiadomości

Stan zgodny z polityką prywatności (POLITYKA_PRYWATNOSCI_SZKIC.md §7 —
dane współpracy przez czas współpracy; okres po jej zakończeniu to
oznaczona tam DECYZJA ADMINISTRATORA DANYCH):

* **Okres przechowywania**: wiadomości żyją przez czas współpracy i
  istnienia konta — są częścią komunikacji trener–podopieczny (podstawa
  umowna, kategoria „komunikacja"). Zakończenie relacji lub cofnięcie
  zgody kategorii odbiera trenerowi dostęp (lista, historia, załączniki
  i kanał realtime), ale nie usuwa treści — klient zachowuje własną
  historię i prawo eksportu.
* **Usunięcie konta klienta** (`POST /api/me/deletion-request`, P7):
  treść każdej wiadomości we wszystkich wątkach klienta jest
  anonimizowana (`[usunięto]`), załączniki odpinane (`file_id = NULL`),
  a pliki, których właścicielem danych jest klient, są fizycznie usuwane
  z dysku. Zweryfikowane testem `test_privacy.py` (eksport/usunięcie).
  Głosówki nagrane przez trenera we wspólnym wątku (właścicielem pliku
  jest trener) tracą jedyną referencję przy odpięciu i są sprzątane
  przez pętlę plików-sierot (soft delete + usunięcie z dysku po
  `DZIK_ORPHAN_FILE_TTL_H`, domyślnie 24 h).
* **Nowe kolumny migracji 13** nie niosą treści: `delivered_at`/`read_at`
  to znaczniki czasu, `client_msg_id` to losowy identyfikator urządzenia
  nadawcy — anonimizacja konta nie musi ich czyścić.
* **Konto trenera** nie ma ścieżki samodzielnego usunięcia
  (`require_client_self`) — świadomie: wątki należą do pary
  trener–klient, a obowiązki umowne trenera wykluczają jednostronne
  zniknięcie komunikacji. Decyzja administratora danych pozostaje
  wymagana dla takiego przypadku (jak w ZGODY_MODEL.md).
* Kopie zapasowe zawierają wiadomości jak każdą inną tabelę i podlegają
  retencji backupów (`DZIK_BACKUP_KEEP`, DEPLOYMENT §4a); po odtworzeniu
  kopii wcześniejsze anonimizacje wykonane po dacie backupu trzeba
  powtórzyć (właściwość każdego backupu — odnotowana w RODO_REJESTR).

## 7. Migracja nr 13 — zakres i plan wycofania

Zakres (addytywna, `db.py`):

* `messages.delivered_at VARCHAR(40)` (NULL),
* `messages.client_msg_id VARCHAR(64)` (NULL),
* indeks `ix_messages_thread_created (thread_id, created_at, id)`,
* częściowy indeks unikalny `ux_messages_thread_author_client_msg
  (thread_id, author_id, client_msg_id) WHERE client_msg_id IS NOT NULL`.

Plan wycofania (rollback):

1. Wycofanie kodu na 0.14.x jest bezpieczne bez ruszania schematu —
   stare zapytania nie znają nowych kolumn (nullable, bez NOT NULL),
   indeksy nie przeszkadzają.
2. Pełne wycofanie schematu (tylko jeśli konieczne):
   `DROP INDEX ux_messages_thread_author_client_msg;
   DROP INDEX ix_messages_thread_created;
   ALTER TABLE messages DROP COLUMN client_msg_id;
   ALTER TABLE messages DROP COLUMN delivered_at;`
   (SQLite ≥ 3.35 i PostgreSQL wspierają DROP COLUMN) oraz
   `DELETE FROM schema_migrations WHERE version = 13;`.
3. Utrata danych przy pełnym wycofaniu: wyłącznie znaczniki doręczenia
   i identyfikatory deduplikacji — żadna treść wiadomości nie ginie.

Test migracji z bazy v1: `tests/test_password_and_confirmation.py::
test_migrations_apply_to_existing_v1_database` (stub `messages`).

## 8. Testy

`backend/tests/test_messages_realtime.py` (19 testów): wymiana dwóch
aktywnych użytkowników ze statusami, jawne oznaczanie przeczytania,
duplikat `client_msg_id` (w tym różni autorzy i walidacja), kolejność
przy identycznym `created_at`, paginacja bez dziur i nakładek + kursor
IDOR, `before` nie znaczy przeczytania, IDOR historii/read/wysyłki (404),
401 kanału, bramka doręczenia zdarzenia (obcy, cofnięta zgoda),
potwierdzenie doręczenia, ważność sesji strumienia (w tym po
wylogowaniu), magistrala między wątkami + przepełnienie → resync,
publikacja do odbiorcy i autora, push bez treści, formaty audio
(webm/m4a/mp3/ogg + niezgodność zawartości i typ z parametrem kodeka).

`frontend/scripts/test-messaging.mjs` (19 testów, `npm run
test:helpers`): porządek/scalanie/duplikaty/spóźnione zdarzenia,
potwierdzenia read/delivered, backoff, parser SSE (chunki cięte w środku
linii, CRLF, keepalive), szkice per wątek (w tym awaria storage), wybór
formatu audio (Chrome/iOS/brak wsparcia), typ bazowy i rozszerzenia,
kontroler nagrywania: odmowa mikrofonu, stop z rzeczywistym mimeType,
anulowanie, dispose przy odmontowaniu, błąd recordera, limit rozmiaru,
auto-stop po limicie czasu.

Żywy strumień SSE został zweryfikowany ręcznie przez uvicorn + curl
(nagłówki, keepalive, doręczenie `message.new` z `delivered_at`);
w zestawie pytest nie ma testu otwartego strumienia — synchroniczny
TestClient blokuje się na nieskończonej odpowiedzi (ograniczenie
narzędzia, nie kodu).

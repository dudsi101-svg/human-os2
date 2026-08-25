# Uruchomienie i wdrożenie — Dzik OS

## 1. Lokalnie (deweloperka)

```bash
# Backend (z korzenia repozytorium)
pip install -e ".[dev]" && pip install -e "apps/dzik-os/backend[dev]"
python -m dzik_os.seed
uvicorn dzik_os.main:app --reload --port 8000

# Frontend z hot-reload (osobny terminal; proxy /api → :8000)
cd apps/dzik-os/frontend && npm install && npm run dev   # http://localhost:5173
```

Bez trybu deweloperskiego wystarczy `npm run build` — backend sam serwuje
`frontend/dist` pod `http://localhost:8000`.

## 2. Jednym poleceniem (Docker Compose)

```bash
docker compose -f apps/dzik-os/docker-compose.yml up --build
docker compose -f apps/dzik-os/docker-compose.yml run --rm seed  # dane demo
```

PostgreSQL + aplikacja na `http://localhost:8000`. Hasło bazy przez
`POSTGRES_PASSWORD` (patrz `.env.example`).

## 3. Staging

1. Serwer z Dockerem + reverse proxy z TLS (Caddy/Traefik/nginx +
   Let's Encrypt). **HTTPS jest wymagany** dla instalacji PWA i cookies
   `secure`.
2. Skopiuj `apps/dzik-os/.env.example` → `.env`; ustaw `DZIK_ENV=staging`,
   silne `POSTGRES_PASSWORD`.
3. `docker compose --env-file .env -f apps/dzik-os/docker-compose.yml up -d --build`
4. Zasil danymi demo (`run --rm seed`) — **wyłącznie syntetycznymi**.
5. Zweryfikuj: logowanie kont demo, instalacja PWA na telefonie,
   `/api/health`, `GET /api/admin/audit/verify` (konto admina).

## 3a. PaaS: Fly.io (zalecany start — darmowa subdomena z HTTPS)

Gotowa konfiguracja: `apps/dzik-os/fly.toml`. Domena własna NIE jest
potrzebna na start — dostajesz `https://<nazwa>.fly.dev` z ważnym HTTPS,
co wystarcza do instalacji PWA na telefonie. Kroki (jednorazowo ~10 min):

```bash
# 1. Zainstaluj flyctl i zaloguj się (założenie konta: fly.io)
curl -L https://fly.io/install.sh | sh
flyctl auth login

# 2. Z korzenia repozytorium: utwórz aplikację i wolumen na dane
#    (nazwy i region DOKŁADNIE jak w fly.toml i workflowach: aplikacja
#    dzik-os-panel, region fra — inna nazwa utworzy DRUGĄ, pustą aplikację)
flyctl apps create dzik-os-panel        # nazwa musi być globalnie wolna;
                                        # przy innej nazwie zaktualizuj fly.toml
flyctl volumes create dzik_data --region fra --size 1 --app dzik-os-panel

# 3. Deployment (buduje Dockerfile z hos_engine + frontendem)
flyctl deploy --config apps/dzik-os/fly.toml

# 4. Pierwsze konta (od 0.43.0 seed na Fly jest wyłączony — konta demo
#    nie zasiewają się; hasła wyłącznie przez zmienne środowiskowe)
flyctl ssh console --app dzik-os-panel
#   a w konsoli maszyny:
#   DZIK_BOOTSTRAP_COACH_PASSWORD='...' DZIK_BOOTSTRAP_ADMIN_PASSWORD='...' \
#   python -m dzik_os.bootstrap --coach-email ... --admin-email ...
#   (na bazie z zasianymi kontami demo: najpierw bootstrap się nie uda —
#   konto trenera zakłada się wtedy w aplikacji — a stare konta demo
#   dezaktywuje `python -m dzik_os.purge_demo`)

# 4bis. TO SAMO BEZ TERMINALA (GitHub Actions, 0.52.0)
#
# Kroki 4 (pierwsze konta) i sekrety (SMTP/AI/klucz plików) da się
# wyklikać z przeglądarki — flyctl nie jest potrzebny:
#
#   a) Pierwsze konta: w repo Settings → Secrets and variables → Actions
#      dodaj DZIK_BOOTSTRAP_COACH_PASSWORD i DZIK_BOOTSTRAP_ADMIN_PASSWORD
#      (min. 12 znaków, wymyśl silne — są jednorazowe, aplikacja wymusi
#      zmianę przy pierwszym logowaniu). Potem Actions → „Pierwsze konta
#      (Fly.io)" → Run workflow (podaj e-maile kont). Po sukcesie sekrety
#      DZIK_BOOTSTRAP_* możesz usunąć z repo. Hasła wędrują: sekret repo →
#      chwilowy sekret Fly (env maszyny, nigdy argv) → kasowane po użyciu.
#   b) Sekrety konfiguracyjne: dodaj w repo te z listy DZIK_SMTP_HOST/
#      PORT/USER/PASSWORD/FROM/SECURITY, DZIK_AI_API_KEY, DZIK_AI_ENABLED,
#      DZIK_FILE_KEY, które chcesz włączyć, i uruchom Actions → „Sekrety
#      produkcji (Fly.io)". Puste są pomijane — można wracać i dokładać.
#
# Najkrótsza droga do działającej poczty (Gmail, konto lubelskidzikk@gmail.com):
#   1. Włącz weryfikację dwuetapową: myaccount.google.com → Bezpieczeństwo.
#   2. Wygeneruj „hasło do aplikacji": myaccount.google.com/apppasswords
#      (nazwa dowolna, np. „Dzik OS") — dostaniesz 16 znaków.
#   3. W repo ustaw sekrety: DZIK_SMTP_HOST=smtp.gmail.com,
#      DZIK_SMTP_PORT=587, DZIK_SMTP_USER=lubelskidzikk@gmail.com,
#      DZIK_SMTP_PASSWORD=<16 znaków bez spacji>,
#      DZIK_SMTP_FROM=Dzik OS <lubelskidzikk@gmail.com>.
#   4. Actions → „Sekrety produkcji (Fly.io)" → Run workflow (pole
#      test_email zostaw — po ustawieniu sekretów workflow sam wyśle
#      testowy e-mail i zrobi się czerwony, jeśli poczta nie działa).
# Limit Gmaila (~500 e-maili/dobę) w skali pilotażu jest niewyczerpywalny;
# przy większej skali przejdziemy na dostawcę transakcyjnego z domeną.
#
# Limit pilotażu: aplikacja przyjmuje maks. 10 niezakończonych współprac
# na trenera (DZIK_MAX_CLIENTS w fly.toml; ENDED zwalnia miejsce).

# 5. Otwórz aplikację
flyctl apps open --app dzik-os-panel    # https://dzik-os-panel.fly.dev
```

Własna domena później: `flyctl certs add panel.twojadomena.pl --app
dzik-os-panel` plus rekord CNAME u rejestratora — nic w kodzie się nie
zmienia.

Przejście na PostgreSQL (przy prawdziwych klientach):
`flyctl postgres create` → `flyctl postgres attach` → ustaw secret
`flyctl secrets set DZIK_DATABASE_URL="postgresql+psycopg2://…"` i usuń
wpis SQLite z `[env]` w fly.toml.

**Stan wsparcia PostgreSQL (18.08.2026).** Do tego dnia PostgreSQL był
zadeklarowany, ale nie wykonała się na nim ani jedna linia kodu. Pierwszy
przebieg zestawu testów na PG ujawnił błędy, których SQLite nie mógł pokazać:
SQLite domyślnie **nie egzekwuje kluczy obcych**, więc aplikacja zapisywała
wiersze wskazujące na jeszcze nieistniejące rekordy (m.in. zakładanie konta
klienta przez trenera). Zostały naprawione, a zestaw testów chodzi teraz na
PostgreSQL w CI (job `backend-postgres`).

Dwie rzeczy pozostają niesprawdzone na PG i trzeba je zweryfikować ręcznie
przed pierwszym prawdziwym wdrożeniem:

* **cykl kopia→odtworzenie** (`pg_dump`/`psql`) — kod istnieje, testy
  pokrywają wyłącznie wariant SQLite;
* **migracja przyrostowa na istniejącej bazie** — świeża baza dostaje schemat
  z metadanych ORM i tylko stempluje wersje, więc surowy SQL migracji nie
  wykonuje się w żadnym teście. Chroni go bramka statyczna
  (`test_migracje_przenosnosc.py`), nie wykonanie.

## 4. Produkcja

* `DZIK_ENV=production` (wyłącza `/api/docs`, wymusza cookie `secure`);
* wyłącznie PostgreSQL (`DZIK_DATABASE_URL=postgresql+psycopg2://…`);
* wolumeny trwałe: dane Postgresa oraz `/data` (uploady + `audit.db`);
* kopie zapasowe: `python -m dzik_os.backup` na harmonogramie (patrz §4a);
* szyfrowanie plików at-rest: ustaw `DZIK_FILE_KEY` (patrz §4b);
* przed startem z prawdziwymi klientami zamknij ryzyko R-01 (przegląd
  prawny) i domknij resztę R-02 (szyfrowanie samej bazy — dysk
  szyfrowany / pgcrypto);
* **nie publikuj kont demo na produkcji** (nie uruchamiaj seeda);
* **przepisywanie tekstu ze zdjęcia (OCR)**: obraz produkcyjny zawiera
  `tesseract-ocr` + pakiety `pol`/`eng` (Dockerfile). Rozpoznanie zjada
  pamięć, więc kolejka jest **jednoslotowa**, a obraz zmniejszany do
  1600 px przed OCR. Maszyna ma **1 GB RAM** (`fly.toml`, podbite z 512 MB
  po pomiarze: aplikacja 124-129 MB, obróbka jednego zdjęcia ~75 MB
  szczytowo — pojedyncza operacja mieściła się w 512 MB, ale nałożenie
  uploadu zdjęć raportu na OCR już nie, a Fly nie ma swapa). Przy większym
  ruchu **najpierw** kolejne podbicie pamięci, **potem** więcej slotów.
  Strojenie: `DZIK_OCR_MAX_PX`, `DZIK_OCR_TIMEOUT_S`,
  `DZIK_OCR_QUEUE_MAX`, `DZIK_OCR_MAX_INPUT_MB`,
  `DZIK_OCR_DAILY_TASKS_USER`, `DZIK_OCR_LANGS` (szczegóły:
  `docs/OCR.md` §2).

## 4a. Kopie zapasowe (R-12)

Wbudowane narzędzie: `python -m dzik_os.backup` tworzy jedno archiwum
`dzik-backup-<timestamp>.tar.gz` zawierające spójnie:

* główną bazę — SQLite przez sqlite3 backup API (bezpieczne przy
  działającej aplikacji, także w trybie WAL); dla PostgreSQL `pg_dump`
  (wykrywane automatycznie z `DZIK_DATABASE_URL`; `pg_dump` musi być w
  PATH),
* bazę audytu Human OS (`audit.db`, również przez backup API),
* katalog uploadów — **w postaci, w jakiej leży na dysku**, czyli
  zaszyfrowanej przy włączonym `DZIK_FILE_KEY` (patrz §4b).

```bash
# Backup (katalog z env DZIK_BACKUP_DIR, domyślnie data/backups;
# retencja z env DZIK_BACKUP_KEEP, domyślnie 14 najnowszych archiwów)
python -m dzik_os.backup
python -m dzik_os.backup --backup-dir /backups --keep 30

# Odtwarzanie — przy ZATRZYMANEJ aplikacji. Bez --force narzędzie
# odmawia nadpisania istniejących danych. Po odtworzeniu łańcuch audytu
# jest weryfikowany (SQLiteEventStore.verify_chain()) i wynik jawnie
# raportowany (kod wyjścia 1 przy przerwanym łańcuchu).
python -m dzik_os.backup --restore data/backups/dzik-backup-20260818T020000Z.tar.gz --force
```

Harmonogram na Fly.io (brak wbudowanego crona w maszynie aplikacji):

1. **GitHub Actions — WDROŻONE**: workflow
   `.github/workflows/fly-backup.yml` wykonuje backup codziennie
   o 02:30 UTC oraz na żądanie (Actions → „Kopia zapasowa (Fly.io)" →
   Run workflow). Uruchamia `python -m dzik_os.backup` na maszynie
   z `DZIK_BACKUP_DIR=/data/backups` i wypisuje listę archiwów
   (sekret `FLY_API_TOKEN` w repo — ten sam co deploy). Workflow celowo
   **nie pobiera archiwów z maszyny** — dane zdrowotne nie mają trafiać
   do artefaktów GitHub Actions; dla kopii poza maszyną skonfiguruj
   `flyctl ssh sftp get` do własnego, zaufanego storage (decyzja
   operatora).
2. Alternatywa: **Fly Machines z cronem** — osobna maszyna
   z supercronic/crontab wywołująca to samo polecenie.

Dodatkowa warstwa: **snapshoty wolumenów Fly** — Fly.io wykonuje
automatyczne codzienne snapshoty wolumenu (`flyctl volumes snapshots
list <vol-id>`, retencja domyślnie 5 dni). To zabezpieczenie na poziomie
bloków, nie zastępuje backupu aplikacyjnego (brak spójności SQLite
gwarantowanej przez backup API, brak testu odtwarzania), ale jest cenną
drugą linią obrony — traktuj je jako uzupełnienie, nie substytut.

Przetestuj odtwarzanie zanim będzie potrzebne: pełny cykl
backup → utrata → restore → weryfikacja łańcucha audytu jest pokryty
testem `backend/tests/test_backup.py` i warto go powtórzyć ręcznie na
stagingu po pierwszej konfiguracji harmonogramu.

## 4b. Szyfrowanie plików at-rest (R-02)

Pliki uploadów (zdjęcia, PDF-y, nagrania) są szyfrowane AES-256-GCM,
jeśli ustawiono `DZIK_FILE_KEY` (base64, dokładnie 32 bajty):

```bash
# Wygenerowanie klucza
python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"

# Fly.io: klucz wyłącznie jako secret, nigdy w fly.toml ani w repo
flyctl secrets set DZIK_FILE_KEY="<wygenerowany-klucz>" --app dzik-os-panel
```

Zasady działania:

* nowe pliki zapisywane są jako szyfrogram z nagłówkiem `DZIKENC1`;
* pliki wgrane przed włączeniem klucza (bez nagłówka) są nadal czytane
  wprost — włączenie szyfrowania nie psuje istniejących danych;
* brak klucza przy zaszyfrowanym pliku lub błędny klucz to jawny błąd
  500, nigdy ciche zwrócenie szyfrogramu; błędny format klucza w env
  zatrzymuje start aplikacji;
* bez klucza w środowisku innym niż dev/test aplikacja loguje przy
  starcie jedno ostrzeżenie i zapisuje jawnie (jak dotychczas).

**Przechowywanie klucza — krytyczne:** trzymaj `DZIK_FILE_KEY` OSOBNO od
kopii zapasowych (menedżer sekretów / sejf haseł, nie na tym samym
wolumenie i nie w archiwach backupu). Backup zawiera pliki w postaci
zaszyfrowanej — bez klucza są **nie do odzyskania**; z kolei klucz
złożony obok backupu unieważnia sens szyfrowania. Utrata klucza = utrata
plików (baz danych to nie dotyczy — nie są szyfrowane tym mechanizmem).

Poza zakresem tego mechanizmu (otwarta część R-02): szyfrowanie samej
bazy danych — na Fly wolumeny są szyfrowane at-rest na poziomie bloków,
a dodatkowo rozważ pgcrypto/pełne szyfrowanie dysku u innych operatorów.

## 5. Prawdziwy operator płatności

Interfejs: `backend/dzik_os/payments_provider.py`. Kroki dla Stripe
(analogicznie P24):

1. `pip install stripe`, klucz w env (`STRIPE_API_KEY`) — nigdy w repo.
2. Zaimplementuj `StripeProvider.payment_link()` → Checkout Session
   (kwota z `payment_records`, metadane: record_id).
3. Dodaj endpoint webhooka (podpis weryfikowany kluczem webhooka),
   który po `checkout.session.completed` oznacza rekord jako PAID
   (`marked_by="stripe-webhook"`) i emituje zdarzenie audytu.
4. Podmień `provider = LocalDemoProvider()` na wybór wg
   `DZIK_PAYMENT_PROVIDER`.

## 6. Uwaga o GitHub Pages (stary deployment Human OS)

Workflow `pages.yml` (odziedziczony z Human OS) publikuje wyłącznie
`apps/user-demo` — prototyp UX bez backendu; nie koliduje z Dzik OS.
Dzik OS wymaga backendu, więc **nie** jest wdrażany na Pages — właściwa
ścieżka to sekcje 3–4 powyżej.

### 4c. Poczta wychodząca (opcjonalna, domyślnie WYŁĄCZONA)

Bez `DZIK_SMTP_HOST` aplikacja **nie wysyła żadnego e-maila** — przypomnienia
i alerty zostają w panelu. To stan domyślny i bezpieczny.

Żeby uruchomić pocztę, ustaw sekrety (nigdy w repozytorium):

```bash
flyctl secrets set \
  DZIK_SMTP_HOST=smtp.dostawca.pl \
  DZIK_SMTP_PORT=587 \
  DZIK_SMTP_USER=konto@twojadomena.pl \
  DZIK_SMTP_PASSWORD='...' \
  DZIK_SMTP_FROM='Dzik OS <konto@twojadomena.pl>'
```

* `DZIK_SMTP_SECURITY` — `starttls` (domyślnie, port 587), `ssl` (port 465)
  albo `none` (wyłącznie testy lokalne).
* `DZIK_SMTP_TIMEOUT` — domyślnie 10 s. **Nie podnoś bez potrzeby:** backend
  jest jednoprocesowy, więc zawieszony serwer poczty blokuje aplikację
  wszystkim użytkownikom na czas tego limitu.

**Co dokładnie wychodzi po włączeniu.** Trzy rzeczy, wszystkie bez danych
zdrowotnych w treści:

1. **zaproszenie nowego klienta** — trener dodaje klienta w panelu,
   klient dostaje list „aktywuj swoje konto" z jednorazowym linkiem
   (ważnym `DZIK_INVITATION_TTL_DAYS` dni); gdy poczta nie jest
   skonfigurowana, panel pokazuje trenerowi link do ręcznego przekazania
   (`delivery: "manual"`) — po włączeniu poczty link ZNIKA z odpowiedzi
   i istnieje tylko w liście;
2. **reset hasła** — bez poczty ten przepływ jest martwy (token powstaje,
   list nie wychodzi), a jedyną drogą powrotu jest ponowne zaproszenie;
3. **alerty i przypomnienia** wg preferencji użytkownika.

Linki w listach budują się z `DZIK_PUBLIC_URL` (ustawione w `fly.toml` na
adres aplikacji; przy własnej domenie podmień). Ścieżka zaproszenia
zweryfikowana end-to-end 23.08 na prawdziwym serwerze SMTP: HTTP 201,
`delivery: "email"`, list z tematem „Dzik OS: aktywuj swoje konto"
i linkiem `https://…/aktywacja#…`; log zawiera tylko `email_sent`, bez
adresu i treści.

**Sprawdzenie po włączeniu** — nie wierz konfiguracji, wyślij:

```bash
flyctl ssh console --app dzik-os-panel -C "python -c \"
from dzik_os.notifications_provider import provider
print(provider.name)
print(provider.send_email(to='twoj@adres.pl', subject='Dzik OS — proba',
                          body='Jesli to czytasz, poczta dziala.'))\""
```

Oczekiwane: `smtp` i `True` oraz list w skrzynce. `null` znaczy, że
`DZIK_SMTP_HOST` nie doszło do procesu.

**Co jedzie w treści:** wyłącznie neutralne komunikaty — nigdy dane
zdrowotne ani kwoty (`docs/POWIADOMIENIA.md`). Adres, temat i treść
**nie trafiają do logów**.

### 4d. Funkcje AI (opcjonalne, domyślnie WYŁĄCZONE)

Bez konfiguracji aplikacja działa w pełni — cztery funkcje AI (OCR
etykiet, odczyt opisów ćwiczeń, onboarding wspierany AI, asystent
trenera) pokazują wtedy jawnie „wymaga konfiguracji" i pracują w trybie
lokalnym/formularza. Włączenie wymaga **obu naraz** (sam klucz niczego
nie uruchamia):

```bash
flyctl secrets set \
  DZIK_AI_API_KEY='sk-ant-…' \
  DZIK_AI_ENABLED=true \
  --app dzik-os-panel
```

* Dostawca: Anthropic Claude API (oficjalne SDK). Model domyślnie
  `claude-opus-5`; zmiana przez `DZIK_AI_MODEL`.
* Koszty pod kontrolą: `DZIK_AI_DAILY_CALLS_USER` (domyślnie 20/dzień),
  `DZIK_AI_DAILY_CALLS_GLOBAL` (500/dzień), `DZIK_AI_MAX_TOKENS`
  (limit jednej odpowiedzi, 4000), `DZIK_AI_MAX_INPUT_CHARS` (6000),
  `DZIK_AI_TIMEOUT_S` (20 s — po nim tryb formularza, nigdy wieczny
  spinner).
* **Co jedzie do dostawcy:** wyłącznie minimalny zakres z
  `docs/DATA_PROCESSING_MAP.md` §AI, bramkowany zgodą `funkcje_ai`
  podmiotu danych. Do logów trafia tylko klasa błędu i liczniki tokenów
  — nigdy treść.
* **Sprawdzenie po włączeniu** — nie wierz konfiguracji: w bazie
  ćwiczeń wklej opis i wybierz tryb „AI"; odpowiedź ma mieć
  `engine: EXTENDED`. Każda propozycja AI wymaga przejrzenia
  i zatwierdzenia przez trenera — to reguła aplikacji, nie opcja.

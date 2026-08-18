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
flyctl apps create dzik-os              # nazwa musi być globalnie wolna;
                                        # przy innej nazwie zaktualizuj fly.toml
flyctl volumes create dzik_data --region waw --size 1 --app dzik-os

# 3. Deployment (buduje Dockerfile z hos_engine + frontendem)
flyctl deploy --config apps/dzik-os/fly.toml

# 4. Dane demo (wyłącznie staging!)
flyctl ssh console --app dzik-os -C "python -m dzik_os.seed"

# 5. Otwórz aplikację
flyctl apps open --app dzik-os          # https://dzik-os.fly.dev
```

Własna domena później: `flyctl certs add panel.twojadomena.pl --app dzik-os`
plus rekord CNAME u rejestratora — nic w kodzie się nie zmienia.

Przejście na PostgreSQL (przy prawdziwych klientach):
`flyctl postgres create` → `flyctl postgres attach` → ustaw secret
`flyctl secrets set DZIK_DATABASE_URL="postgresql+psycopg2://…"` i usuń
wpis SQLite z `[env]` w fly.toml.

## 4. Produkcja

* `DZIK_ENV=production` (wyłącza `/api/docs`, wymusza cookie `secure`);
* wyłącznie PostgreSQL (`DZIK_DATABASE_URL=postgresql+psycopg2://…`);
* wolumeny trwałe: dane Postgresa oraz `/data` (uploady + `audit.db`);
* kopie zapasowe: `python -m dzik_os.backup` na harmonogramie (patrz §4a);
* szyfrowanie plików at-rest: ustaw `DZIK_FILE_KEY` (patrz §4b);
* przed startem z prawdziwymi klientami zamknij ryzyko R-01 (przegląd
  prawny) i domknij resztę R-02 (szyfrowanie samej bazy — dysk
  szyfrowany / pgcrypto);
* **nie publikuj kont demo na produkcji** (nie uruchamiaj seeda).

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

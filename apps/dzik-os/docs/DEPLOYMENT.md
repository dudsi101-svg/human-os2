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

## 4. Produkcja

* `DZIK_ENV=production` (wyłącza `/api/docs`, wymusza cookie `secure`);
* wyłącznie PostgreSQL (`DZIK_DATABASE_URL=postgresql+psycopg2://…`);
* wolumeny trwałe: dane Postgresa oraz `/data` (uploady + `audit.db`);
* kopie zapasowe: dump Postgresa + `/data` (patrz RISK_REGISTER R-12);
* przed startem z prawdziwymi klientami zamknij ryzyka R-01, R-02, R-06;
* **nie publikuj kont demo na produkcji** (nie uruchamiaj seeda).

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

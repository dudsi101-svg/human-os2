# Plan sesji: poprawne linki w e-mailach do nowych klientów

**Gałąź:** `agent/email-klientow` (od `main` = `abfa927`)
**Rola:** aktywny piszący (kontynuacja polecenia właściciela: konfiguracja
wysyłania e-maili do nowych klientów)
**Cel:** domknąć ostatni brakujący element konfiguracji e-maili w repo.

## Diagnoza (z przebiegu na żywo, nie z założeń)

Pełna ścieżka „trener zakłada klienta → zaproszenie wychodzi e-mailem"
działa — sprawdzone end-to-end na prawdziwym serwerze SMTP (23.08):
HTTP 201, `delivery: "email"`, list z tematem, treścią i jednorazowym
linkiem aktywacyjnym; link zniknął z odpowiedzi API; log bez PII.

Została jedna dziura konfiguracyjna: **linki w listach zbuduje się z
`request.base_url`**, bo `DZIK_PUBLIC_URL` nie jest nigdzie ustawione,
a uvicorn w Dockerfile chodzi **bez `--proxy-headers`** — za proxy Fly
połączenie wewnętrzne jest zwykłym HTTP, więc linki aktywacyjne i resetu
hasła wyszłyby jako `http://…`. Filtry poczty tego nie lubią, a klient
pilotażowy dostałby podejrzanie wyglądające zaproszenie.

## Zamiar

1. `fly.toml`: `DZIK_PUBLIC_URL = "https://dzik-os-panel.fly.dev"`
   w `[env]` — jawny adres publiczny zamiast zgadywania ze schematu
   połączenia (przy własnej domenie właściciel podmienia jedną linię).
2. `Dockerfile`: `--proxy-headers` + `--forwarded-allow-ips=*` dla
   uvicorna — za proxy Fly nagłówki `X-Forwarded-*` są wiarygodne,
   a bez nich każda przyszła rzecz oparta o `request.base_url`/scheme
   będzie kłamać tak samo.
3. `docs/DEPLOYMENT.md` §4c: dopisek o `DZIK_PUBLIC_URL` i o tym, co
   dokładnie wysyła się do nowych klientów (zaproszenie z linkiem);
   §4c ma już komplet sekretów SMTP z 0.42.0.

## Mój obszar

- `apps/dzik-os/fly.toml`;
- `apps/dzik-os/Dockerfile`;
- `docs/DEPLOYMENT.md` §4c;
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md` (integrator); ten plan.

## Czego nie dotykam

- kodu backendu/frontendu (ścieżka e-maili działa — dowód wyżej);
- sekretów: `DZIK_SMTP_*` ustawia właściciel (`flyctl secrets set`),
  wartości nie istnieją w repo ani w tej rundzie.

## Rezerwacje

- **Wersja: 0.43.1** (poprawka konfiguracji, bez nowych funkcji).
- **Migracja: brak.**

## Świadomie nie robię

- nie wysyłam prawdziwego e-maila do prawdziwej skrzynki — dostawcy
  i sekretów nie ma w tym środowisku; tryb rozszerzony wykona się po
  ustawieniu sekretów przez właściciela;
- nie zakładam konta u dostawcy poczty — wybór dostawcy to decyzja
  właściciela (Etap 1 pkt 5 z analizy blokerów).

## Weryfikacja (do wypełnienia)

- bramki minimalne (ruff, backend, Core, spójność) — zmiana nie dotyka
  kodu, ale bramka jest bramką;
- ponowny przebieg E2E na żywo z `DZIK_PUBLIC_URL` — link w liście ma
  zaczynać się od `https://dzik-os-panel.fly.dev/aktywacja#`.

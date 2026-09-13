# Plan sesji: moduł e-mail (Brevo SMTP) na Fly — `mailer.py`, `/admin/mail/test`, `smtp_check.py` (0.61.0)

**Gałąź:** `agent/poczta-brevo` (od `main` = 4b2c2a4 po scaleniu #57; jeden `[WRITER]` naraz).
**Rola:** jedyny piszący i integrator; recenzent: Codex.
**Źródło:** `PROMPT_claude_code_mailer.md` (właściciel, 13.09) + `ZASADY_budzet_agentow.md`
(limit zadania: 1 mln tokenów, 8 agentów, 1 poziom delegowania; bez workflow bez polecenia).
**Materiały:** `docs/mail/{mailer.py,test_mailer.py,smtp_check.py}` — dostarcza właściciel
(w repo ich nie ma; bez nich runda nie rusza, bo logiki `mailer.py` nie wolno zmieniać).

## Rozpoznanie (bez zmian w plikach)

1. Backend: FastAPI, pakiet `apps/dzik-os/backend/dzik_os/`; moduły pomocnicze płasko w
   pakiecie (np. `notifications_provider.py`, `test_poczty.py`, `diagnostyka.py`), routery w
   `dzik_os/routers/`, testy `apps/dzik-os/backend/tests/` (pytest, `conftest.py` z kontami
   seedu: `COACH`, `ADMIN`, `CLIENT_A`…). Uruchomienie testów: `cd apps/dzik-os/backend &&
   python -m pytest -q`. Deploy: push do `main` → `dzik-os-ci.yml` → `fly-deploy.yml`
   (workflow_run, `flyctl deploy --config apps/dzik-os/fly.toml`, aplikacja `dzik-os-panel`,
   region fra). Nie tworzę nowego mechanizmu deployu.
2. Istniejąca poczta: `SMTPNotificationProvider` na zmiennych `DZIK_SMTP_*`
   (`config.py`), `python -m dzik_os.test_poczty adres` (dowód wysyłki), workflow „Sekrety
   produkcji (Fly.io)” przenosi `DZIK_SMTP_*` z sekretów repo, „Diagnostyka produkcji”
   drukuje nazwy ustawionych zmiennych SMTP (nigdy wartości). Nowy moduł czyta `SMTP_HOST`,
   `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `MAIL_REPLY_TO` (bez prefiksu
   `DZIK_`) — właściciel ustawił je już na Fly. Decyzja: NIE zmieniam starego dostawcy ani
   sekretów; nowy moduł działa równolegle (osobne zmienne), stary dostawca zostaje dla
   zaproszeń/resetów do czasu osobnej decyzji o przepięciu (poza zakresem zadania).
3. Flagi: `config.Settings` przez `_env(...)`; nowa `DZIK_MAIL_TEST_ENDPOINT_ENABLED`
   (domyślnie `false` na produkcji, `true` w `tests/conftest.py` i `e2e/serve.sh`) — nie
   wiążę endpointu testowego z `DZIK_DIET_TEMPLATES_ENABLED` (inny moduł, inny cykl życia).
4. Autoryzacja: `require_role("ADMIN")` / `active_roles` (`security.py`); prefiks tras
   `/api/...`; każda trasa ma wpis w `tests/access_matrix.py` (klasa `COACH_OR_ADMIN` —
   admin/trener, jak w zadaniu).
5. Diagnostyka z maszyny: wzorzec `fly-diagnostyka.yml` (`flyctl ssh console -C
   "python -m …"`). `smtp_check.py` ląduje w katalogu głównym aplikacji obrazu
   (WORKDIR z `apps/dzik-os/Dockerfile` — do sprawdzenia) i dostaje własny workflow
   `fly-smtp-check.yml` (workflow_dispatch, tylko odczyt, bez wypisywania sekretów).
6. Sekrety: nie czytam, nie wypisuję, nie zmieniam (zasady właściciela); w logach wyłącznie
   nazwy zmiennych i statusy.

## Plan

1. Wgranie: `dzik_os/mailer.py` (bez zmian logiki), `tests/test_mailer.py` (poprawione
   importy), `smtp_check.py` w katalogu roboczym aplikacji + kopia jako `dzik_os/smtp_check.py`
   (uruchamialna `python -m dzik_os.smtp_check`), gdyby WORKDIR obrazu nie był katalogiem
   backendu.
2. Inicjalizacja: `MailConfig.from_env()` w lifespan `main.py` → `app.state.mail_config`;
   brak zmiennych = `MAIL_ENABLED=0` + `log_json("mail_disabled", level="warning")`;
   zależność `get_mail_config` (Depends) zgodnie z konwencją repo.
3. Endpoint `POST /api/admin/mail/test` `{to}` → 202 `{message_id}` przez `BackgroundTasks`;
   rola ADMIN lub COACH; flaga; walidacja adresu; `record_event` (bez adresu w payloadzie).
4. Testy: `test_mailer.py` (8), endpoint (flaga, role, 202 + Message-ID, wyłączona poczta =
   503), macierz dostępu, pakietowanie.
5. Deploy przez CI; `fly-smtp-check.yml` z maszyny (4 linie OK); test wysyłki na adres
   podany przez człowieka (workflow z inputem `test_email` → `POST /api/admin/mail/test`?
   Nie — endpoint wymaga sesji; zamiast tego z maszyny `python -m dzik_os.smtp_check --send
   ADRES`, jeśli skrypt to obsługuje; inaczej właściciel wywołuje endpoint z panelu).
6. Raport: ścieżki, pytest, pełny wynik `smtp_check.py`, fragment logu, kody SMTP.

## Weryfikacja wykonana

(uzupełnię po rundzie)

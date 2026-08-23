# Plan sesji: przygotowanie repozytorium do pilotażu

**Gałąź:** `agent/pilotaz` (od `main` = `524547f`)
**Rola:** aktywny piszący i integrator (polecenie właściciela: „rozwiąż
wszystkie problemy stojące naprzeciw odpalenia aplikacji")
**Cel:** wykonać wszystkie punkty przygotowania pilotażu, które da się
zrobić w repozytorium bez sekretów właściciela — wg analizy blokerów
z 23.08 (agent read-only) i `BRAMKA_GO_NOGO.md` §5–6.

## Zamiar

1. **`fly.toml`:** usunąć `DZIK_SEED_DEMO = "true"` (konta demo ze znanymi
   hasłami nie mogą się zasiać na produkcji) i przestawić `DZIK_ENV` na
   `"production"` (włącza flagę `Secure` na cookie sesji i zamyka
   `/api/docs`).
2. **Usunąć `.github/workflows/fly-reset-demo.yml`** — workflow kasujący
   `/data` jednym kliknięciem z zakładki Actions. Sam ostrzega „NIGDY nie
   używać po przejściu na produkcję"; ostrzeżenie w komentarzu nie jest
   zabezpieczeniem. Przy powrocie stagingu można go przywrócić z historii.
3. **`python -m dzik_os.bootstrap`** — zakładanie pierwszego konta trenera
   i admina na pustej bazie. Bez tego wyłączenie seeda to pułapka: seed
   jest dziś JEDYNYM miejscem nadającym role COACH/ADMIN — po czyszczeniu
   bazy nikt nie mógłby się zalogować. Hasła wyłącznie ze zmiennych
   środowiskowych (nigdy z argv — widoczne w `ps`), konto z flagą
   `must_change_password`.
4. **`python -m dzik_os.purge_demo`** — dezaktywacja kont demo
   (`@example.com`): status `SUSPENDED` + podmiana hasha hasła na losowy.
   Świadomie NIE kasuje wierszy: usunięcie danych to osobna ścieżka RODO
   (`/api/privacy`), a ręczne kasowanie z kluczami obcymi i łańcuchem
   audytu to ryzyko naruszenia integralności. Cel bezpieczeństwa —
   „znane hasła przestają działać" — dezaktywacja realizuje w całości.
   Bezpiecznik: odmawia, jeśli po dezaktywacji nie zostałby żaden aktywny
   COACH spoza listy demo (nie da się zamknąć wszystkich drzwi naraz).
5. **`docs/DEPLOYMENT.md` §3a:** poprawka rozjazdu nazw (`dzik-os` →
   `dzik-os-panel`, `waw` → `fra`) — kopiuj-wklej z obecnej wersji
   tworzy drugą, pustą aplikację.
6. Testy dla 3 i 4; wpisy CHANGELOG (0.43.0) i STAN_PRZEKAZANIA.

## Mój obszar

- `apps/dzik-os/fly.toml`;
- `.github/workflows/fly-reset-demo.yml` (usunięcie);
- `backend/dzik_os/bootstrap.py`, `backend/dzik_os/purge_demo.py` (nowe);
- `backend/tests/test_bootstrap_purge.py` (nowy);
- `docs/DEPLOYMENT.md` §3a;
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md` (integrator); ten plan.

## Czego nie dotykam

- seeda (dalej działa lokalnie i w docker-compose — pilotaż wyłącza go
  tylko na Fly, przez brak zmiennej);
- Core Human OS, migracji, frontendu;
- sekretów i wdrożenia: `DZIK_FILE_KEY`, sekrety SMTP, prawdziwe hasła,
  `flyctl` — wszystko po stronie właściciela.

## Rezerwacje

- **Wersja: 0.43.0** (ostatnia: 0.42.0). **Migracja: brak.**

## Świadomie nie robię

- nie wdrażam na Fly (deploy uruchomi się z automatu po scaleniu do main
  przez `fly-deploy.yml` — i to jest właściwy moment, nie wcześniej);
- nie dotykam bazy na produkcji (czyszczenie kont demo wykonuje
  właściciel narzędziem z tej rundy, po wdrożeniu);
- nie usuwam pozostałych workflowów Fly (backup, deploy, logs, volumes —
  wszystkie nie-destrukcyjne).

## Weryfikacja (do wypełnienia)

- pełne bramki §5; nowe narzędzia uruchomione NA ŻYWO na lokalnej bazie:
  bootstrap na pustej (konto powstaje, można się zalogować), purge_demo
  na zasianej (konta demo przestają wpuszczać, bezpiecznik zadziałał).

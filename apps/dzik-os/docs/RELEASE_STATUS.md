# Stan wydania — Dzik OS

**Wersja:** 0.53.12 · **Data:** 2026-08-26 · **Środowisko:** produkcja
(pilotaż) — https://dzik-os-panel.fly.dev

Jedna strona prawdy o tym, co DZIAŁA na produkcji teraz. Aktualizowana
w każdej rundzie (strażnik: `tools/spojnosc.py`, kontrola „wersje
dokumentów" — nieaktualny numer wersji czerwieni bramkę). Historia
zmian: `CHANGELOG.md`; stan prac między sesjami: `STAN_PRZEKAZANIA.md`;
decyzja jakościowa: `BRAMKA_GO_NOGO.md` (warunkowe GO na pilotaż
z jednym klientem, NO-GO na szerszą produkcję).

## Ścieżka wydania

CI (`dzik-os-ci`: ruff, ~850 testów backendu na SQLite i Postgresie,
275 testów Core, tsc+build+testy frontendu, E2E Playwright, spójność)
→ po zieleni na `main` deploy automatyczny (`fly-deploy.yml`,
`workflow_run` — wdrażany dokładnie commit, który przeszedł CI) →
smoke porównujący `/api/health` (`version`, `build`=SHA, `migration`)
z oczekiwanymi. Ręczny deploy: tylko awaryjnie (`workflow_dispatch`).

## Konta na produkcji

| Konto | Rola | Stan |
|---|---|---|
| lubelskidzikk@gmail.com | COACH (trener — Łukasz) | aktywne; 1. logowanie wymusza zmianę hasła + MFA |
| dudsi101+admin@gmail.com | ADMIN (właściciel) | jw. |
| dudsi101+trener@gmail.com | COACH (konto testowe właściciela) | jw. |
| dudsi101@gmail.com | CLIENT (właściciel jako podopieczny) | aktywne |
| 7 kont demo sprzed pilotażu | — | zdezaktywowane (SUSPENDED, losowy hash) |

Hasła startowe: wyłącznie artefakty Actions ważne 1 dzień (po terminie —
ponowne uruchomienie odpowiedniego workflow). Limit podopiecznych:
**10** (`DZIK_MAX_CLIENTS`, fly.toml).

## Integracje

| Integracja | Stan | Co je włącza |
|---|---|---|
| SMTP (zaproszenia, resety haseł, digest) | **wyłączone** — dostawca `null`; brak doręczeń jest uczciwie logowany (`PASSWORD_RESET_SEND_FAILED`, powód `no_provider`) | hasło aplikacji Gmail w sekretach repo → workflow „Sekrety produkcji (Fly.io)" (sam dowodzi wysyłką testową) |
| AI (podsumowania raportów, OCR-AI, onboarding) | **wyłączone** — aplikacja w pełni działa bez AI | `DZIK_AI_API_KEY` + `DZIK_AI_ENABLED` → ten sam workflow sekretów |
| Szyfrowanie plików at-rest (R-02) | **nieaktywowane** — mechanizm AES-256-GCM gotowy w kodzie | workflow „Klucz szyfrowania plików (Fly.io)" (potwierdzenie `WLACZ`; dowód sondą DZIKENC1; kopię klucza schować poza repo) |
| Backup (dzienny, rotacja 14) | działa na maszynie; **próba odtworzenia co poniedziałek** (workflow, tylko liczności) | off-site: czeka na poświadczenia właściciela (W4) |
| Web push | działa (VAPID skonfigurowane) | — |

## Publiczna część

Strona marketingowa na `/` (formularz zapytań z limitem 5/min/IP,
honeypot), `/prywatnosc` — informacja RODO (art. 13, administrator:
LUBELSKI DZIK sp. z o.o.); treść czeka na formalne zatwierdzenie
prawne (W3).

## Otwarte kroki właściciela

| # | Krok | Gdzie |
|---|---|---|
| W1 | Branch protection na `main` (wymagane checki CI) | GitHub → Settings → Branches |
| W2 | Hasło aplikacji Gmail → sekrety repo → „Sekrety produkcji" | Actions |
| W3 | Zatwierdzenie prawne polityki prywatności + NIP/dane spółki w stopce | prawnik / `Privacy.tsx` |
| W4 | Poświadczenia do backupu off-site | do uzgodnienia |
| W5 | Test ręczny iPhone/Android na koncie +trener | telefon |
| W6 | Dowody marketingowe (IFBB PRO, zgody wizerunkowe) | folder dowodów |

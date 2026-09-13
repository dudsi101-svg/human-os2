# Stan wydania — Dzik OS

**Wersja:** 0.55.0 · **Data:** 2026-09-13 · **Środowisko:** produkcja
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

Stan z workflowu „Diagnostyka produkcji (Fly.io)” z 2026-09-13 07:17 UTC
(run 34744866429) — nie z pamięci sesji. Wcześniejsza wersja tej tabeli
myliła się co do `dudsi101@gmail.com` (poprawka, Karta §XII).

| Konto | Rola | Stan |
|---|---|---|
| lubelskidzikk@gmail.com | COACH (trener — Łukasz) | ACTIVE, bez MFA, ostatnie logowanie 13.09 06:06 UTC |
| dudsi101+admin@gmail.com | ADMIN (właściciel) | ACTIVE, MFA włączone |
| dudsi101+trener@gmail.com | COACH (konto testowe właściciela) | ACTIVE, wymuszona zmiana hasła (nigdy nie dokończona) |
| dudsi101@gmail.com | CLIENT (zaproszony 25.08 przez konto demo) | **PENDING** — zaproszenie wygasło 01.09; nigdy nie aktywowane |
| dudsi101+klient@gmail.com | CLIENT (operatorsko, 31.08) | ACTIVE, relacja z Łukaszem ACTIVE, **zgoda współpracy nieudzielona** (Profil → Prywatność i zgody) |
| dudsi101plusklient@gmail.com („Mateusz D”) | CLIENT (z panelu Łukasza, 29.08) | **ACTIVE od 13.09 06:03** (aktywowane linkiem), zgoda współpracy z deklaracji — to działające konto testowe właściciela u Łukasza |
| dudsi101+test1@gmail.com („TEST 01 — plan pełny”) | CLIENT (z panelu Łukasza, 12.09) | **PENDING**, zaproszenie aktywne do 20.09 (odnowione 13.09 06:18), e-mail nie wyszedł (dostawca `null`) — aktywacja linkiem z panelu |
| kboguta6@gmail.com | CLIENT (zaproszony 23.08 przez konto demo) | PENDING, zaproszenie wygasło 31.08 — do anulowania albo ponowienia przez trenera |
| 7 kont demo sprzed pilotażu | — | SUSPENDED |

**Logowanie (pilotaż, decyzja właściciela 29.08):** login + hasło; wymuszanie MFA zdjęte (`DZIK_MFA_REQUIRED_ROLES=""`), MFA dostępne opt-in; przywrócenie przymusu = wpisanie `"COACH,ADMIN"` w fly.toml. Reset operatorski hasła czyści też TOTP (konto wraca do logowania hasłem).

Hasła startowe: wyłącznie artefakty Actions ważne 1 dzień; po terminie —
workflow **„Reset hasła (Fly.io)”** (świeże hasło jednorazowe dla
istniejącego konta, sesje unieważniane, wpis w audycie). Limit podopiecznych:
**10** (`DZIK_MAX_CLIENTS`, fly.toml).

## Integracje

| Integracja | Stan | Co je włącza |
|---|---|---|
| SMTP (zaproszenia, resety haseł, digest) | **wyłączone** — dostawca `null`; brak doręczeń jest uczciwie logowany (`PASSWORD_RESET_SEND_FAILED` i od 0.54.5 `CLIENT_INVITED.reason`, powód `no_provider`); bez poczty zaproszenie wraca trenerowi jako link do przekazania | hasło aplikacji Gmail w sekretach repo → workflow „Sekrety produkcji (Fly.io)” z zakresem `poczta` (sam dowodzi wysyłką testową; klasa błędu w logu przy odmowie) |
| AI (podsumowania raportów, OCR-AI, onboarding) | **wyłączone** — aplikacja w pełni działa bez AI | `DZIK_AI_API_KEY` + `DZIK_AI_ENABLED` → ten sam workflow sekretów |
| Szyfrowanie plików at-rest (R-02) | **nieaktywowane** — mechanizm AES-256-GCM gotowy w kodzie | workflow „Klucz szyfrowania plików (Fly.io)" (potwierdzenie `WLACZ`; dowód sondą DZIKENC1; kopię klucza schować poza repo) |
| Backup (dzienny, rotacja 14) | działa na maszynie; **próba odtworzenia co poniedziałek** (workflow, tylko liczności) | off-site: czeka na poświadczenia właściciela (W4) |
| Web push | działa (VAPID skonfigurowane) | — |

## Konfigurator 28 dni (K1, 0.55.0)

Silnik i API trenera są w kodzie (bez ekranu — K1b). Trener może
wygenerować i zapisać szkic przez API; katalog ma status „do przeglądu
trenera”, a heurystyki H nie są walidacją kliniczną
(`docs/KONFIGURATOR.md`).

## Diagnostyka

Workflow **„Diagnostyka produkcji (Fly.io)”** (0.54.5) wypisuje raport
tylko do odczytu prosto z maszyny: dostawca poczty w procesie, nazwy
ustawionych zmiennych SMTP, konta/role/status, relacje ze zgodą
współpracy, zaproszenia, liczby planów, zdarzenia doręczeń z 30 dni.
Nic nie zmienia; log widzi tylko właściciel repozytorium.

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

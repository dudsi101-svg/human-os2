# Stan wydania — Dzik OS

**Wersja:** 0.72.0 (PR #67, strona publiczna czerwono-biała — po decyzji właściciela o scaleniu; `main` 0.71.0 po PR #72; na produkcji 0.71.0 po wdrożeniu) · **Data:** 2026-09-14 · **Środowisko:** produkcja
(pilotaż) — https://dzik-os-panel.fly.dev

Jedna strona prawdy o tym, co DZIAŁA na produkcji teraz. Aktualizowana
w każdej rundzie (strażnik: `tools/spojnosc.py`, kontrola „wersje
dokumentów" — nieaktualny numer wersji czerwieni bramkę). Historia
zmian: `CHANGELOG.md`; stan prac między sesjami: `STAN_PRZEKAZANIA.md`;
decyzja jakościowa: `BRAMKA_GO_NOGO.md` (warunkowe GO na pilotaż
z jednym klientem, NO-GO na szerszą produkcję).

## Strona publiczna `/` (0.72.0)

Wizytówka dla niezalogowanych w wariancie czerwono-białym (PR #67): treść,
formularz zapytania (`POST /api/public/lead`, limiter 5/h, honeypot), notka
RODO i `/prywatnosc` bez zmian względem 0.51.0–0.53.5; aplikacja po
zalogowaniu, `/login`, ikony PWA i `og.png` nadal w ciemnym motywie
z limonką. Bez poziomego przewijania na 1440/1024/768/390 (E2E), zrzuty
w `docs/zrzuty/landing-czerwony/`. Do decyzji właściciela: znak marki
w czerwieni wszędzie (etap 2) i treść kart demonstracyjnych w hero.

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
| Poczta Brevo SMTP (0.61.0, `dzik_os/mailer.py`) | **kanał potwierdzony 14.09 01:37 UTC** (4/4 kroki z maszyny, testowa wysyłka przyjęta przez serwer i **odebrana w skrzynce właściciela**; wcześniejsze 525 = lista autoryzowanych IP w Brevo — blokada dla kluczy SMTP wyłączona przez właściciela). Skonfigurowana na Fly przez właściciela (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `MAIL_REPLY_TO`); dowód kanału: workflow „Sprawdzenie SMTP (Fly.io)” (`smtp_check.py`, 4 kroki) + testowa wysyłka; endpoint `POST /api/admin/mail/test` za flagą `DZIK_MAIL_TEST_ENDPOINT_ENABLED` (domyślnie wyłączony). Zaproszenia/resety/digest nadal przez starego dostawcę `DZIK_SMTP_*` — przepięcie to osobne zadanie | flaga endpointu: sekret `DZIK_MAIL_TEST_ENDPOINT_ENABLED=true` na Fly |
| AI (podsumowania raportów, OCR-AI, onboarding) | **wyłączone** — aplikacja w pełni działa bez AI | `DZIK_AI_API_KEY` + `DZIK_AI_ENABLED` → ten sam workflow sekretów |
| Szyfrowanie plików at-rest (R-02) | **nieaktywowane** — mechanizm AES-256-GCM gotowy w kodzie | workflow „Klucz szyfrowania plików (Fly.io)" (potwierdzenie `WLACZ`; dowód sondą DZIKENC1; kopię klucza schować poza repo) |
| Backup (dzienny, rotacja 14) | działa na maszynie; **próba odtworzenia co poniedziałek** (workflow, tylko liczności) | off-site: czeka na poświadczenia właściciela (W4) |
| Web push | działa (VAPID skonfigurowane) | — |

## Konfigurator 28 dni (K1, 0.55.0)

Silnik i API trenera są w kodzie (bez ekranu — K1b). Trener może
wygenerować i zapisać szkic przez API; katalog ma status „do przeglądu
trenera”, a heurystyki H nie są walidacją kliniczną
(`docs/KONFIGURATOR.md`).

## Wiedza (P0, 0.56.0)

Nowa zakładka Wiedza jest w kodzie za flagą `DZIK_WIEDZA_V2` (domyślnie
włączona). **Na produkcji biblioteka jest pusta do pierwszej publikacji:**
48 kart z pakietu właściciela to szkice bez przeglądu eksperckiego,
a produkcja ignoruje tryb demonstracyjny. Publikuje trener w zakładce
„Karty wiedzy” (wymagane źródła z rejestru, recenzent, data kolejnego
przeglądu). „Dlaczego?” działa od razu dla nowych decyzji (plany
z konfiguratora, nowe wersje planów i diet od trenera); stare plany
pokazują uczciwy brak zapisanego uzasadnienia (`docs/WIEDZA.md`).

## Poczta Brevo SMTP (0.61.0)

Moduł `dzik_os/mailer.py` (pliki właściciela z `docs/mail/`, bez zmian
logiki) inicjalizowany przy starcie: brak zmiennych = `MAIL_ENABLED=0`
z ostrzeżeniem, aplikacja wstaje. Diagnostyka z maszyny: workflow
„Sprawdzenie SMTP (Fly.io)” (`python smtp_check.py`, cztery kroki OK;
opcjonalny input `test_email` wysyła wiadomość testową tą samą ścieżką
co endpoint). Endpoint testowy admina/trenera za flagą, domyślnie
wyłączony na produkcji. Plan i odstępstwa: `docs/plan-sesji/poczta-brevo.md`.

## Powitanie po pierwszym logowaniu (0.70.0) — bez flagi, na produkcji od deployu

Dwuetapowy samouczek na „Dzisiaj” dla klienta bez znacznika
`users.welcome_seen_at` (migracja 37): pomoc, nie bramka — pomijalny
(Esc / „Pomiń na razie”), nieblokujący, ponownie otwieralny z „Więcej →
Pomoc / Samouczek”. Znacznik na serwerze (`POST /api/me/welcome-seen`,
idempotentny), więc okno nie wraca na innym urządzeniu. Istniejący klienci
na produkcji (bez znacznika po migracji) zobaczą je raz przy najbliższym
wejściu na „Dzisiaj”. Szczegóły: `docs/CHANGELOG.md` 0.70.0,
`docs/plan-sesji/powitanie-samouczek.md`.

## Wymiany produktów v2 (0.69.0) — w module szablonów diet (za flagą `DZIK_DIET_TEMPLATES_ENABLED`)

Przycisk „↔ wymień” w diecie klienta daje zamienniki z tej samej grupy i z grup
pokrewnych (45 par, propozycja do przeglądu trenera), z bramką „nie pogarsza”
i przyciskiem także dla warzyw/dodatków (rola NONE, 1:1 wagowo). Pomiar:
składników bez zamiennika przy 2000 kcal 12/108 → 3/108. Pusta lista mówi
dlaczego. Katalog trenera (2058 pozycji) skorelowany do CSV propozycji —
**czeka na decyzje TAK/NIE właściciela**
(`docs/diet-module/katalog_korelacja_propozycja.csv`), import zatwierdzonych
osobnym PR-em.

## Kreator diety (0.44–0.48) — od 0.67.0 za flagą, na produkcji UKRYTY

Zlecenie właściciela z 14.09: zakładka „Dieta” w Bazie wiedzy trenera
i trasy `/api/coach/diet-wizard`, `/api/coach/diet-suggestion` działają
tylko przy `DZIK_DIET_WIZARD_ENABLED=true` (brak wpisu w `fly.toml` =
ukryty). Nic nie skasowano: kod, testy, dane, ręczne plany żywieniowe
i plany klientów zostają; zakładka „Produkty” z katalogiem zostaje.
Przywrócenie = jedna zmienna środowiskowa.
## Zakładka „Postępy” / „Monitoring” (0.66.0) — za flagą, na produkcji WYŁĄCZONA

Trzy osie postępu (Forma → Konsekwencja → Sylwetka) w jednej zakładce
klienta i lista sygnałów z widokiem klienta u trenera; silnik rekordów
i średniej wagi, migracja 36 (addytywna). Włączenie:
`DZIK_MONITORING_TAB_ENABLED=true` (env w `fly.toml` albo sekret); bez
flagi `/api/monitoring/*` zwraca 404, nawigacja i „Więcej” są jak
dotąd, tabele z migracji 36 pozostają puste. **Po włączeniu jednorazowo**
`python -m dzik_os.recalculate_progress` na maszynie Fly (backfill
historii sesji i pomiarów; idempotentny, wypisuje bliźniaki nazw
ćwiczeń do decyzji trenera). Od włączenia rekordy liczą się przy każdym
zapisie sesji. Szczegóły i sprawy otwarte: `docs/CHANGELOG.md` 0.66.0,
`docs/plan-sesji/monitoring-postepy.md`, `docs/monitoring-tab/PROGRESS.md`.

## Dni treningowe na „Dzisiaj” (0.71.0) — bez flagi, na produkcji od deployu

Klient wybiera dni tygodnia dla jednostek planu (karta „Twoje dni treningowe”
w zakładce Plan; prefill z propozycji trenera, powrót do propozycji jednym
dotknięciem); „Dzisiaj” pokazuje jednostkę z dzisiejszego dnia albo kartę
„ustaw dni”, gdy plan istnieje bez przypisań. Nakładka na plan — wersje
nietknięte; trener widzi wybór (tylko odczyt). Migracja 38 (addytywna).
Szczegóły: `docs/CHANGELOG.md` 0.71.0, `docs/plan-sesji/dni-treningowe.md`,
`docs/dni-treningowe/PROGRESS.md`.

## Panel rozwojowy „Dzisiaj” (0.63.0) — bez flagi, na produkcji od deployu

Powitanie, hasło dnia (deterministyczne, bez AI) i do trzech nawyków
z codziennym cofalnym odhaczaniem, łagodnym decay −1 (decyzja foundera,
R-20) i absolutorium. Nawyki to zwykły tekst + odhaczenia (domena danych
treningowych, bez nowej bramki zgód). Szczegóły: `docs/CHANGELOG.md`
0.63.0, `docs/plan-sesji/nawyki-dzisiaj.md`, `docs/nawyki/PROGRESS.md`.

## Wywiad „Zapotrzebowanie kaloryczne” (0.62.0) — za flagą, na produkcji WŁĄCZONY (do potwierdzenia)

`DZIK_CALORIE_INTERVIEW_ENABLED="true"` w `fly.toml` (runda 0.62.0, zgodnie
z prośbą właściciela z 14.09, żeby funkcje były widoczne w aplikacji;
wyłączenie = jedna linia). Trzeci typ wywiadu w zakładce „Wywiad”, wynik
w Dieta (klient) i karcie klienta (trener), „Zaproponuj kcal” w „Przypisz
dietę”. Filtr flagi zdrowotnej po stronie serwera. Szczegóły:
`docs/WYWIAD.md` §8, `docs/plan-sesji/wywiad-zapotrzebowanie.md`.

## Biblioteka szablonów diet (0.64.0) — za tą samą flagą co 0.60.0

Po audycie 14.09: 45 odsłon (9 profili × 5), 181 produktów, silnik v1.1
(limity porcji), notatki autora (suplementacja, sód, pochodzenie) i
alergeny posiłków w podglądzie trenera i widoku klienta, sweep w zakresie
odsłony, seed zastępujący po skrócie pliku (migawki nietknięte).
Migracja 35 (kolumny addytywne). Seed przy starcie: `DZIK_DIET_SEED_ON_STARTUP`
(domyślnie włączony; wyłączany tylko w testach backendu). Stan:
`docs/diet-module/PROGRESS.md`.

## Szablony diet ze skalowaniem (0.60.0) — za flagą, na produkcji WYŁĄCZONE

Moduł równoległy do planów żywieniowych: biblioteka szablonów
(profil → odsłona tygodnia), silnik skalowania (port prototypu
właściciela), przypisanie z migawką, wymiany produktów przez klienta,
panel szablonów. Włączenie: `DZIK_DIET_TEMPLATES_ENABLED=true` (sekret /
env Fly) — bez niego `/api/diet/*` zwraca 404, interfejs nie pokazuje
modułu, dane z migracji 32 pozostają nieużywane. Stary kreator diet
nietknięty. Stan i pytania otwarte: `docs/diet-module/PROGRESS.md`.

## Zakładka „Wywiad” (0.59.0)

Każdy klient ma od razu dwa formularze (wstępny, głęboki) z zapisem
częściowym, wersjami i przeglądem trenera per wersja; trener widzi
jawnie „pusto” / „brak dostępu z powodem” / „błąd”, prosi o wypełnienie
lub uzupełnienie, uzupełnia wspólnie; zmiana faktów istotnych dla planu
blokuje publikację zależnej wersji do rozstrzygnięcia. Sesje rozmowy
startowej i głębokiego wywiadu są przenoszone do wersji ponawialnie przy
starcie (bez powiadomień; kontrola: `python -m dzik_os.migruj_wywiad
--raport`; błąd migracji widoczny w `/api/health` jako
`wywiad_migracja_error`). Raport: `docs/WYWIAD.md`.

## Panel trenera: szkice i publikacja zmian (0.58.0)

Plany, diety i szablony edytuje się jako szkic (klient nic nie widzi),
z listą różnic i publikacją w jednej transakcji; klient dostaje jeden
wpis „Trener zaktualizował Twój plan…” z ekranem „Zobacz zmiany”.
Przełącznik `DZIK_SZKICE_PUBLIKACJA` (domyślnie włączony) przywraca
poprzedni edytor bez kasowania historii. Migracja 30 nie tworzy szkiców
ani zdarzeń (`docs/PUBLIKACJA_ZMIAN.md`).

## Incydent 13.09 (0.56.0 → 0.57.1)

Wdrożenie 0.56.0 (09:03 UTC) padło na smoke-teście: aplikacja startowała
i przerywała się na braku `wiedza/dane/tresci_startowe.json` w obrazie
(brak `package-data` w `pyproject.toml`; instalacja nie-edytowalna pomija
JSON). Fly zatrzymał maszynę po 10 restartach — **produkcja niedostępna od
09:07 UTC do wdrożenia 0.57.1**. Dane na wolumenie nietknięte (migracja 28
weszła przed błędem; 29 wchodzi z 0.57.1). Poprawka: deklaracja
`package-data`, odporny start (brak treści = pusta biblioteka + wpis
w logu i `/api/health`), strażnik `tests/test_pakietowanie.py`.

## Kreator dań (P0, 0.57.0)

Trzecia droga „Ułóż z dań” w zakładce Dieta trenera: silnik
referencyjny właściciela układa menu z całych receptur w zatwierdzonych
porcjach. **Na produkcji dostępny jest wyłącznie podgląd kulinarny ze
szkiców (bez wartości odżywczych):** 300 rekordów katalogu to szkice
wariantów bez testu kuchennego i recenzji; opublikowanych receptur jest
0, więc tryb produkcyjny z makro uczciwie zwraca „za mało receptur po
filtrach”. Publikuje trener z jawnymi poświadczeniami w bibliotece
receptur. Zapis podglądu klientowi wymaga potwierdzenia; klient widzi
„Dlaczego to danie?” ze śladu decyzji (`docs/KULINARIA.md`).

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

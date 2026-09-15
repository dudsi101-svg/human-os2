# Stan przekazania — przeczytaj przed rozpoczęciem rundy

**Aktualizacja:** 2026-09-15 · **Wersja w `main`:** 0.76.1 (poczta: zaproszenia i reset hasła czytają tę samą konfigurację co kontrola kanału, `233076f`; **zweryfikowane na produkcji** — diagnostyka pokazuje `dostawca_poczty: \"smtp\"`) — **0.76.2 w gałęzi `agent/diagnostyka-poczta`** (raport zna obie nazwy ustawień); 0.77.0 w PR #80 (`agent/wywiad-kaloryczny`, wywiad kaloryczny wg specyfikacji właściciela, migracja 42, po przeglądzie).
**Tryb pracy:** jeden piszący i jeden PR `[WRITER]` naraz
(`KOORDYNACJA.md`, zasada nadrzędna).

**Zanim cokolwiek dotkniesz: `docs/KARTA_WSPOLPRACY.md`** — dziesięć
zasad współpracy między sesjami, każda z podpiętym zdarzeniem, z którego
się wzięła. Ten dokument mówi GDZIE jesteśmy; karta mówi JAK pracujemy.

Ten dokument zastępuje domysły. Ma odpowiadać na trzy pytania: **gdzie
jesteśmy**, **co jest w toku** i **co następne**. Aktualizuj go na koniec
każdej rundy — to warunek przekazania pałeczki.

---

## 1. Gdzie jesteśmy

**`main` jest jedyną linią kanoniczną — i od 18.08.2026 także gałęzią
domyślną GitHuba** (właściciel przełączył po scaleniu PR #14). Protokół
jednego piszącego jest scalony (`98dca51`) i obowiązuje: plan sesji jako
pierwszy commit, draft PR `[WRITER]`, reszta agentów read-only.

| Gałąź | Stan |
|---|---|
| `main` | **kanoniczna i domyślna**, najnowsza wersja produktu |
| `agent/recover-agent-collisions` | scalona przez PR #14 (protokół agentów); nie używać ponownie |
| `claude/dzik-os-personal-trainer-app-d3q7fx` (`94aaa39`) | przodek `main`, scalona; nie zaczynać tu nowej pracy |
| `claude/ocena-projektu-dzik-os-76ercy` (`861ed53`) | **rozliczona w 0.42.0**: SMTP przeniesiony, „pamięć importu" odrzucona jako zdublowana przez 0.40/0.41, sprostowanie pomiaru uratowane; gałąź zostaje w historii |
| `claude/ui-layout-spacing-clarity-8tpz99` | przodek `main`, scalona |

**Stan jakości** (`docs/BRAMKA_GO_NOGO.md`): warunkowe GO na pilotaż z
jednym prawdziwym klientem, **NO-GO na szerszą produkcję** — siedem
blokerów wypisanych w §5 tamtego dokumentu.

**Runda 0.76.0 (gałąź `agent/bloki-jak-szablony`, PR #79, migracja 41, polecenie
właściciela z 14.09 „z bloków korzystać jak z szablonów; dodać jednocześnie szablon
treningowy i blok, a nawet dwa”):** blok `CARDIO` jako trzeci rodzaj (cel dominujący
zamiast wariantu, preset `cardio_json` liczony silnikiem bez danych klienta —
RPE + % HRmax + test mowy, bez ud./min; 9 wbudowanych = 3 cele × 3 poziomy, razem
21; klucz idempotencji `(rodzaj, poziom, cel)`; własne bloki cardio z formularza —
cel/poziom/urządzenia, resztę liczy serwer), pozycja planu z bloku CARDIO
(`kind: "cardio"` + kopia presetu + `block_id` + migawka; „+ Cardio z bloku” także w
szablonie), `copy-to` z opcjonalnym `{blocks}` (maks. 3, po jednym na rodzaj, bez
dublowania dnia, `blocks_applied` w odpowiedzi; luka 5 zamknięta — walidacja
`exercise_id` + ślad H_CARDIO w kopii), `POST /clients/{id}/plans/from-blocks`
(plan z samych bloków), karta „Przypisz plan” w karcie klienta → Plan (szablon
albo tylko bloki, trzy wybory, podsumowanie, `role="status"`), klient widzi cardio
z bloku jak cardio z odznaką „z bloku”. Testy: backend +12 (+`test_exercise_blocks`
12 → 21), helper `bloki.ts` (5), E2E +2, `rozgrzewka.spec` 12 → 21, a11y krok 8a.
Przyjęte domyślne i odstępstwa: `docs/plan-sesji/bloki-jak-szablony.md`; P2 i
pytania: `docs/bloki-jak-szablony/PROGRESS.md`.

**Runda 0.75.0 (gałąź `agent/szablony-i-opisy`, PR #77, polecenie właściciela z 14.09):**
szablony treningowe rozwijane po kliknięciu w nazwę (lista = nazwy + „dni ·
pozycje · data”; treść, panel publikacji i link „Karta w Wiedzy” po rozwinięciu;
Dieta: nazwa = „Podgląd”), „Opis ćwiczenia” przy każdej pozycji planu klienta
(Plan, Dzisiaj, pozycje bloków; u trenera w karcie klienta) — skrót z bazy
trenera po `exercise_id` albo **po znormalizowanej nazwie** (nowe trasy
`GET /api/{me,coach}/exercises/by-name`, IDOR → 404, bez migracji, zero AI,
nic nie zapisuje) + „Pełny opis w Wiedzy” (`/wiedza?cwiczenie=<id>&powrot=…`,
v2 i legacy, trener `/trener/wiedza?cwiczenie=`) z powrotem. 5 testów API,
6 helpera, E2E +4, a11y 4a/7a, PWA, przeklik ze zrzutami. Otwarte dla
właściciela: utrwalać dopasowanie po nazwie w treści planu (nowa wersja /
migracja)? — domyślnie nie. Plan: `docs/plan-sesji/szablony-i-opisy.md`.

**Runda 0.74.0 (gałąź `agent/motyw-czerwony`, PR #76, migracja 40, zlecenie 4
z 14.09, **scalona `26a03af`**):** motyw jasny czerwono-biały jako drugi, kompletny motyw aplikacji
do wyboru użytkownika (decyzja właściciela z trzeciej tury) — jeden atrybut
`html[data-theme="czerwony"]` przełącza blok tokenów (`src/theme.ts`,
`main.tsx` przed pierwszym renderem), sekcja „Wygląd” w „Więcej” (klient
i trener, grupa radiowa), zapis na urządzeniu (`localStorage`, wyjątek
w `clearSession`) i na koncie (`notification_settings.theme`, pole w
`GET/PUT /api/notifications/settings` i w odpowiedzi logowania), znak
czerwony w jasnym, `/login` ze znakiem + nazwą. Ciemny motyw piksel w piksel
(bramka A/B: 55/58 identycznych, 3 = stan danych; `:root` celowo bez
`color-scheme: dark`). 26 par kontrastu policzonych (`DOSTEPNOSC.md`),
`test_a11y.mjs` w obu motywach w CI, axe-core devDependency (pierwszy
przebieg złapał `scrollable-region-focusable` w Postępach — naprawione).
Przyjęte domyślne: ciemny domyślny, PWA/og/manifest limonkowe (decyzja
o znaku), bez „jak w systemie”. Ekrany cardio 0.73.0 (Bloki, panel suwaków,
pozycje u klienta) objęte przeglądem kompletności po scaleniu `main`.
Otwarte i P2: `docs/motyw/PROGRESS.md`.
**Runda 0.73.0 (gałąź `agent/cardio-i-rozgrzewka`, PR #75, zlecenie 5 z 14.09):**
rozgrzewka, rozciąganie i cardio z suwakami celów — silnik `cardio_model_v1`
(`dzik_os/cardio/`: Seiler 3 strefy + Karvonen + Tanaka jako zakres + Fatmax +
interwały pod VO2max; zero AI; 5 przykładów kontrolnych jako testy), trzy rodzaje
pozycji planu (`kind` warmup_block/stretch_block/cardio, migawka bloku), katalog
bloków trenera (`ExerciseBlock`, migracja 39; 9 rozgrzewek + 3 rozciągania
wbudowane, do przeglądu trenera), `POST /api/clients/{id}/cardio/podglad` za
bramką zdrowotną konfiguratora (+ leki wpływające na tętno → tylko RPE;
propose-only), ślad `H_CARDIO` w tej samej transakcji co wersja, dziennik cardio
bez serii (`export_version` 2.1), panel suwaków i wybór bloków w edytorze planu,
zakładka Szablony → Bloki, wspólny renderer pozycji u klienta (Dzisiaj/Plan),
E2E ×2, przeklik ze zrzutami. Przyjęte domyślne §8 (Regeneracja, „Redukcja”,
warianty G/D/C, rozciąganie bez poziomów, trener wskazuje urządzenia, treści
„do przeglądu”, `resting_hr` bez migracji). Otwarte dla trenera/właściciela:
lista do przeglądu w `docs/cardio/PROGRESS.md` (bloki, 9 wpisów katalogu, tabela
urządzeń, kotwice [C]). Nie zrobione: Postępy-cardio, bloki ze szkicu, TPL-025/026.

**Runda 0.71.0 (gałąź `agent/dni-treningowe`, PR #72, zlecenie 1 z 14.09):**
dni treningowe na „Dzisiaj” — nakładka klienta na dni tygodnia planu
(`PlanWeekdayChoice`, migracja 38; wersje planu nietknięte, propozycja
trenera jako prefill, bez mieszania źródeł, klucz `day.id` albo `idx:n`),
API `GET/PUT/DELETE /api/clients/{id}/plans/{plan_id}/dni`, `today` z
`weekday_source` i `workout_hint`, karta „Twoje dni treningowe” w Planie,
karta „ustaw dni” na „Dzisiaj”, odczyt u trenera, `export_version` 2.0.
Przyjęte domyślne: trener zapisuje przez API (UI tylko odczyt), duplikat dnia
= 422, plan bez dni = karta „ustaw dni”. Otwarte: edycja z karty trenera,
tygodnie A/B (`docs/dni-treningowe/PROGRESS.md`). Uwaga: migracja 38 zakłada
37 z PR #70 — `test_migracje_przenosnosc` (ciąg bez luk) jest zielony dopiero
po scaleniu #70 do `main`.

**Runda 0.72.0 (gałąź `agent/landing-czerwony`, PR #67, bez migracji) —
domknięcie zlecenia 3 z pakietu 14.09:** strona publiczna `/` w wariancie
czerwono-białym wg kanwy właściciela, po pomiarze: poziome przewijanie
1024 px (+62) i 768 px (+4) → 0, cele dotyku nawigacji ≥ 24 px, kontrast
obrysów 1,50 → 3,11 (token `--l-border-ui`, wariant A) i numeru na koralu
1,48 → 3,14, kotwice pod paskiem, pas tabletu (kroki 1 kolumna, panel
360 px), h1 `clamp`, LCP z wymiarami; treść: „nawet −12 kg”, zdanie
o wyborze motywu (decyzja z trzeciej tury), karty w hero z etykietą
„przykład”. E2E 4 → 8, zrzuty 1440/1024/768/390 w
`docs/zrzuty/landing-czerwony/`. Przyjęte domyślne i pytania do
właściciela: `docs/plan-sesji/landing-czerwony.md` (Odstępstwa). Odłożone
na etap 2 (osobne zlecenie po scaleniu): znak w czerwieni wszędzie
(`og.png`, ikony PWA, `logo-full.png`, `theme-color` dla trybu jasnego)
i motyw czerwono-biały aplikacji (zlecenie 4). **Nie scalać
samodzielnie** — decyzja właściciela.

**Ostatnia runda (0.62.0, gałąź `agent/wywiad-zapotrzebowanie`, PR #60):**
wywiad „Zapotrzebowanie kaloryczne” — trzeci typ wywiadu w zakładce
„Wywiad” (rodzaj pytania NUMBER), silnik Mifflin-St Jeor × PAL z korektą
pod cel i podstawieniem liczb, `calorie_estimates` (migracja 33),
nadpisanie i odsłonięcie przez trenera, filtr flagi zdrowotnej po stronie
serwera, karty w Wywiad/Dieta (klient) i karcie klienta (trener),
„Zaproponuj kcal” w „Przypisz dietę”, flaga
`DZIK_CALORIE_INTERVIEW_ENABLED` (produkcja: włączona). Przegląd
tematyczny 3 recenzentów: P0 (opcja flagi z przecinkiem) i P1 naprawione
przed scaleniem — `docs/wywiad-zapotrzebowanie/PROGRESS.md`. Hotfixy
#62/#63: zakres `brevo` w „Sekretach produkcji” i krok diagnostyczny
w „Sprawdzeniu SMTP”. **Kanał Brevo potwierdzony 14.09 01:37 UTC:**
4/4 kroki OK z maszyny, testowa wysyłka przyjęta przez serwer, **odbiór
w skrzynce potwierdzony przez właściciela** (przyczyną wcześniejszego 525
była lista autoryzowanych IP w Brevo — właściciel wyłączył blokadę dla
kluczy SMTP).

**Poprzednia runda (0.61.0, gałąź `agent/poczta-brevo`):** poczta Brevo SMTP
— moduł właściciela `mailer.py` 1:1, inicjalizacja przy starcie
(`MAIL_ENABLED=0` bez zmiennych), `POST /api/admin/mail/test` za flagą
`DZIK_MAIL_TEST_ENDPOINT_ENABLED`, `smtp_check.py` z maszyny (workflow
„Sprawdzenie SMTP”), karta testu w panelu admina; hotfix PR #59 (test push
na tydzień spoza seeda, E2E w strefie Europe/Warsaw). Plan i odstępstwa:
`docs/plan-sesji/poczta-brevo.md`.

**Poprzednia runda (0.60.0, gałąź `agent/szablony-diet`):** szablony diet ze
skalowaniem wg zadania właściciela — silnik 1:1 z prototypem (golden
tydzień, sweep 131/133), model danych (migracja 32), seed 142 produktów +
odsłona Standard v1, API `/api/diet`, przepływ trenera „Przypisz dietę”,
widok klienta z wymianami, panel szablonów, flaga
`DZIK_DIET_TEMPLATES_ENABLED` (produkcja: wyłączona). Otwarte dla
właściciela: włączyć regułę `group` domyślnie? (PROGRESS.md), kolejne
profile/odsłony (dietetyk), włączenie flagi na produkcji.
**Poprzednia runda (0.59.0, gałąź `agent/wywiad-zakladka`):** zakładka
„Wywiad” wg specyfikacji właściciela — diagnoza braku wywiadu (brak
inicjacji poza klientem + nieodróżnialne stany widoku; dane nie ginęły),
dwa formularze z definicjami pytań z istniejących scenariuszy, szkic
z rewizją, niezmienne wersje, przegląd per wersja z notatką wewnętrzną,
prośby o doprecyzowanie, wspólne uzupełnianie, przypomnienia jawne,
rewizje faktów, zadania „Wymaga sprawdzenia” blokujące publikację planu,
podpowiedzi do konfiguratorów, outbox, migracja 31 + ponawialna migracja
sesji rozmowy (bez powiadomień), 18 testów odbioru, E2E. Raport:
`docs/WYWIAD.md`. Zaproszenie na istniejące konto nadal nie tworzy
deklaracji zgód (decyzja RODO) — stan jest jawny w zakładce.
**Poprzednia runda (0.58.0, gałąź `agent/panel-trenera-publikacja`):** panel
trenera wg specyfikacji właściciela — szkice planów/diet/szablonów ze
stabilnymi `id`, operacje z rewizją (409), różnice po `id` z polskim
podsumowaniem, publikacja w jednej transakcji (wersja + ChangeSet + outbox
+ ślad Wiedzy + audyt + idempotencja), outbox ponawiany w pętli
przypomnień, ekran „Zobacz zmiany”, baner nowszej wersji u klienta, menu
działań na kartach, archiwizacja ≠ odpięcie, duplikacja, pochodzenie
kopii, edycja harmonogramu i celów, migracja 30, 17 scenariuszy
akceptacyjnych jako testy API + E2E. Raport: `docs/PUBLIKACJA_ZMIAN.md`.
**Poprawka awaryjna (0.57.1, gałąź `agent/hotfix-pakiet-dane`):** obraz
produkcyjny nie zawierał plików JSON pakietów (brak `package-data`) —
0.56.0 nie wstało na Fly (import treści Wiedzy w `lifespan`), maszyna
zatrzymana po 10 restartach. Naprawa: `package-data` dla konfigurator/
wiedza/kulinaria, odporny start, strażnik `tests/test_pakietowanie.py`.
Lekcja do KARTY: testy chodzą na instalacji edytowalnej — każdy nowy
katalog danych wymaga wpisu w `package-data` (strażnik to wymusza).
**Poprzednia runda (0.57.0, gałąź `agent/kreator-kulinarny`):** kreator
dań z pakietów właściciela (13.09) — silnik referencyjny `engine.py`
bez modyfikacji (27 testów 1:1), adapter żywieniowy na wbudowanej bazie
(66/73 produktów z wartościami, 7 jawnie nieznanych), publikacja
receptur w bazie (migracja 29; opublikowanych 0 → produkcja = brak
pokrycia, podgląd ze szkiców bez makro), bramki serwera (screening
z poświadczeń trenera, cele z planu klienta), API trenera (11 operacji),
ślad decyzji `meal`/`CURATED_VARIANT_SELECTION` w transakcji wersji,
ekran „Ułóż z dań” + biblioteka receptur, klient „Dlaczego to danie?”.
Raport i pokrycie diet: `docs/KULINARIA.md`. Następne w kolejce: panel
trenera — pełna edycja/usuwanie/szkice/publikacja zmian (specyfikacja
właściciela 13.09).
**Runda 0.56.0 (gałąź `agent/wiedza-v2`):** modernizacja
zakładki Wiedza (P0 pakietu właściciela z 13.09) — pięć części, karty
i atlas ze szkiców (48, niepublikowane), wyszukiwanie, zapisane,
historia zmian, panel „Dlaczego?” czytający niezmienny ślad decyzji
(konfigurator: H_LAYOUT/H_VOLUME; trener: powód wersji planu i diety),
resolver z 15 scenariuszami pakietu, redakcja trenera (publikacja tylko
ze źródłami, recenzentem i terminem przeglądu), flaga `DZIK_WIEDZA_V2`,
migracja 28. Produkcja pokazuje wyłącznie publikacje — do pierwszej
publikacji biblioteka jest pusta. Raport i braki: `docs/WIEDZA.md`.
Właściciel 13.09: „po każdym wykonanym zadaniu scalaj PR, chyba że
znalazłeś istotne błędy”. Następne w kolejce: pakiet „kreator diety
kulinarnej” (dostarczy ślad wyboru dania/porcji dla Wiedzy).
**Runda 0.55.0 (gałąź `agent/konfigurator-28-dni`):**
konfigurator miesięcznych planów treningowych z pakietu właściciela
(13.09) — K1: deterministyczny silnik + walidator + bramka zdrowotna
+ kalendarz + API trenera (`podglad`/`zapisz`), 7 scenariuszy
referencyjnych co do bajta, przypadki akceptacyjne i 648 kombinacji.
Decyzja projektowa: narzędzie trenera (propose-only), własny katalog
„do przeglądu trenera”, blok zdrowotny nie zapisywany. Następne:
K1b ekran w karcie klienta, K2 dziennik/adaptacja/zamienniki, potem
przegląd trenerski i medyczny (`docs/KONFIGURATOR.md`).
**Fakty z produkcji (diagnostyka 13.09 07:17 UTC, run 34744866429):**
wersja 0.54.5, migracja 27, dostawca poczty `null` (6 zmiennych SMTP
brak), MFA niewymagane, limit 10. TEST 01 (dudsi101+test1) = konto
PENDING z aktywnym zaproszeniem do 20.09 (odnowione 13.09 06:18) —
e-mail nie wyszedł, link jest w panelu trenera („Wyślij ponownie” daje
nowy). Konto „dudsi101plusklient” (literówka) zostało 13.09 aktywowane
przez właściciela i jest jego działającym kontem klienta u Łukasza.
`dudsi101@gmail.com` nigdy nie aktywowano (zaproszenie z konta demo
wygasło 01.09) — tabela w RELEASE_STATUS poprawiona. Poczta: sekrety
SMTP nadal nie istnieją w repo/Fly.
**Runda 0.54.5 (`agent/diagnostyka-produkcji`):**
zlecenie właściciela (12.09): uruchomić pocztę i trzy konta testowe
(dudsi101+test1/2/3). Z sesji produkcja jest nieosiągalna (egress
odrzuca fly.dev), więc powstał workflow „Diagnostyka produkcji”
(raport tylko do odczytu: dostawca poczty z procesu, nazwy zmiennych
SMTP, konta, relacje, zaproszenia, zdarzenia doręczeń), input `zakres`
w „Sekrety produkcji” (domyślnie wyłącznie poczta) i powód
niedoręczenia zaproszenia w audycie. Fakty do sprawdzenia diagnostyką
po scaleniu: czy zaproszenie „TEST 01” (dudsi101+test1, wysłane z
panelu 12.09 przez sesję Codex) w ogóle powstało; workflow sekretów
nigdy nie był uruchomiony (0 przebiegów) — poczta na produkcji stoi
na dostawcy `null`, dopóki właściciel nie doda sekretów SMTP w repo.
**Runda 0.54.4 (`claude/awesome-sagan-sqd64l`):**
mała runda naprawcza testów (pozycja z §3): `test_notifications.py`
bez absolutnych dat przyszłych (najbliższa 16.09 — 4 dni przed
zaczerwienieniem CI; kuracja jak 0.41.0, granice DST testowane
dynamiczną parą śród przez zoneinfo, dowód na trzech przesuniętych
zegarach), `test_ocr.py` z wymuszonym brakiem binarki (fixture
`bez_silnika` — zielone też przy zainstalowanym Tesseractzie), fraza
w Karcie poprawiona osobnym commitem. Zero zmian w kodzie
produkcyjnym. Pierwsza runda w trybie: Claude jedynym piszącym,
Codex niezależnym recenzentem; nazwa gałęzi `claude/…` zamiast
`agent/…` to jawny wyjątek właściciela (wymóg środowiska sesji,
odnotowany w planie sesji `naprawa-testow-dat.md`).
**Runda 0.54.3 (`agent/zgody-bez-historii`):**
usterka z pilotażu (7.09): konto operatorskie bez wpisów zgód nie
mogło udzielić zgód trenerskich (Profil znał trenera tylko z historii
zgód), bramka zgód się nie pokazywała. Teraz `GET /api/me/consents`
niesie `coaches` z aktywnej relacji, `dodaj_klienta` rejestruje
deklaracje z onboardingu + wątek jak panel, lista wątków dokłada
brakujący wątek. Konto właściciela (dudsi101+klient) naprawia się
przez UI po deployu: Profil → Prywatność i zgody → „Udziel zgody”.
Na liście Łukasza wisi też zaproszenie PENDING dla literówki
`dudsi101plusklient@gmail.com` (zajmuje miejsce z limitu 10) — do
anulowania przyciskiem „Anuluj” przez trenera.
**Runda 0.54.2 (`agent/dodaj-klienta`):**
operatorskie konto podopiecznego (`dodaj_klienta` + workflow „Dodaj
podopiecznego (Fly.io)" z artefaktem) — konto CLIENT z aktywną relacją
do trenera jednym przebiegiem; użyte od razu dla konta testowego
właściciela (dudsi101+klient).
**Runda 0.54.1 (`agent/pilotaz-bez-mfa`):**
decyzja właściciela (29.08): pilotaż na loginie i haśle — wymuszanie
MFA zdjęte (`DZIK_MFA_REQUIRED_ROLES=""` w fly.toml; przywrócenie =
`"COACH,ADMIN"`); reset operatorski czyści też TOTP. Konta z już
ustawionym MFA sprowadza do hasła workflow „Reset hasła".
**Runda 0.54.0 (`agent/szablony-trenera`):**
autorskie szablony trenera z materiałów właściciela (zanonimizowane):
TPL-025/026 w katalogu treningowym (z wideo) + NOWY byt szablonów
diety (migracja 27, katalog „Dieta — Etap I", zakładka „Dieta"
w Szablonach, „Z szablonu" w karcie klienta). Po deployu Łukasz
w Szablonach → zakładki: Trening (schematy TPL-025/026 w „Weź gotowy
schemat") i Dieta („Dodaj do moich").
**Runda 0.53.13 (`agent/reset-hasla-awaryjny`):**
awaryjny reset hasła bez SMTP (moduł `resetuj_haslo` + workflow
„Reset hasła (Fly.io)” z artefaktem 1-dniowym) — zbudowany na żywo,
gdy właściciel i trener nie mogli się zalogować po wygaśnięciu
artefaktów.
**Runda 0.53.12 (`agent/zaproszenie-wywiad`):**
audyt B6 — zaproszenie do wywiadu na Dzisiaj po pierwszym raporcie
(„Później" zamyka), notka o skróconym scenariuszu przy wyłączonych
zgodach. **SPRINT B AUDYTU ZAKOŃCZONY** (B1–B6); otwarte pozostają
wyłącznie pozycje właściciela W1–W6 i ustalenia 5–9/luki testowe
z przeglądu krzyżowego wywiadu (lista w raporcie przeglądu).
**Runda 0.53.11 (`agent/podzial-bundla`):**
audyt B3 — React.lazy za logowaniem (wejściowy JS 169→89 kB gz),
strażnik budżetu w buildzie (120 kB).
**Runda 0.53.10 (`agent/przeglad-wywiadu`):**
audyt B5 — przegląd krzyżowy wywiadu 0.53.0 (raport w docs/) + domknięte
4 ustalenia blokujące (sygnały bezpieczeństwa za zgodą, audyt bez treści
zdrowotnej, gw_i5 wrażliwe, powiadomienie PRZESIEW dla trenera).
Otwarte z przeglądu: ustalenia 5–10 + luki testowe (lista w raporcie).
**Runda 0.53.9 (`agent/proba-odtworzenia`):**
audyt B4 — cotygodniowa nieniszcząca próba odtworzenia backupu na
maszynie (moduł `proba_odtworzenia` + workflow z harmonogramem
pon. 05:00 UTC; czerwień = alarm).
**Runda 0.53.8 (`agent/przypiecie-lancucha`):**
audyt B2 — akcje po SHA (13. kontrola spójności pilnuje regresu),
obrazy po digeście, `npm ci`, blokujący `pip-audit`. Aktualizacja
pinów odtąd = świadoma zmiana w PR (SHA + komentarz wersji); automat
(dependabot) — decyzja właściciela. Pierwszy przebieg audytu złapał
podatne pillow (naprawione: `>=12.3,<13`) i pytest 8.4.2 — pytest ma
jawny wyjątek w CI (dev-only, pin `<9` w pyproject Core); REKOMENDACJA
DLA SESJI CORE: podnieść pytest do `>=9.0.3,<10` i zdjąć wyjątek.
**Runda 0.53.7 (`agent/stan-wydania`):**
audyt B1 — `docs/RELEASE_STATUS.md` (stan produkcji TERAZ), README
odświeżone (0.4.0→bieżąca), 12. kontrola spójności „wersje dokumentów”.
**Runda 0.53.6 (`agent/klucz-plikow`):**
audyt A6/R-02 — workflow „Klucz szyfrowania plików (Fly.io)” + moduł
sondy `test_szyfrowania` (dowód DZIKENC1 na maszynie). **KROK
WŁAŚCICIELA:** Actions → „Klucz szyfrowania plików (Fly.io)” → Run
z potwierdzeniem `WLACZ` → pobrać artefakt `klucz-plikow` w ciągu
1 dnia i schować poza repo (utrata klucza = utrata plików).
**Runda 0.53.5 (`agent/prywatnosc-publiczna`):**
audyt P0-1 — publiczna trasa `/prywatnosc` z pełną informacją RODO
(administrator: LUBELSKI DZIK sp. z o.o., dane jawne z KRS), warstwowa
notka art. 13 przy formularzu kontaktowym („nie wpisuj danych o
zdrowiu"), linki na aktywacji i ekranie zgód. **OTWARTE (właściciel,
W3):** formalne zatwierdzenie treści przez administratora
danych/prawnika + ewentualne uzupełnienie NIP/KRS w stopce.
**Runda 0.53.4 (`agent/reset-uczciwe-zdarzenia`):**
audyt P0-4 — zdarzenia resetu wg faktycznego wyniku wysyłki
(LINK_SENT/SEND_FAILED + metryka), odpowiedź HTTP dalej generyczna.
**Runda 0.53.3 (`agent/deploy-po-ci`):** audyt
P0-2+P1-5 — deploy przez workflow_run po zielonym CI (wdrażany head_sha
z CI), health z version/build/migration, smoke porównujący wersję;
pakiety wyrównane do 0.53.3. **Runda 0.53.2
(`agent/utwardzenie-workflow`):**
audyt P0-3 — inputy workflow przez env + walidacja, strażnik regresji
w spójności. **Trwa Sprint A audytu zewnętrznego z 25.08** (plan
poprawek u właściciela; kolejne: deploy-po-CI + wersje w health,
zdarzenia resetu wg faktycznej wysyłki, /prywatnosc, DZIK_FILE_KEY).
**Runda 0.53.1 (`agent/dodaj-trenera`):** narzędzie
`dodaj_trenera` + workflow — kolejne konto COACH na działającej bazie
(konto testowe właściciela). **Runda 0.53.0 (gałąź `claude/ocena-projektu-dzik-os-76ercy`,
PR #29):** głęboki wywiad jako drugi przepływ rozmowy —
scenariusz `interview_flow.py` (46 pytań/9 modułów wg wzorca właściciela),
fabryka `build_router(FlowConfig)` w `routers/onboarding.py` (rozmowa
startowa bez zmiany zachowania), `/api/clients/{id}/interview`,
migracja 26 (`onboarding_sessions.flow`), flagi wyboru przesiewu
(`Step.flag_options`), zero AI w wywiadzie, ekran `/wywiad` +
zakładka „Wywiad" u trenera + **podpowiedzi z rozmów** przy zakładkach
Plan/Dieta/Harmonogram/Raporty (`coach_hints.py`, `GET /profile/hints`),
16 testów + E2E. Szczegóły: `plan-sesji/gleboki-wywiad.md` i CHANGELOG.

**Runda 0.52.3, gałąź `agent/test-poczty`):** testowa wysyłka
e-maila (`dzik_os.test_poczty`) wpięta w workflow „Sekrety produkcji" —
konfiguracja SMTP dowodzona wysyłką; instrukcja hasła aplikacji Gmail
w DEPLOYMENT. **Konta produkcyjne założone 25.08** (trener
lubelskidzikk@gmail.com, admin dudsi101+admin@gmail.com — hasła
jednorazowe w artefakcie runu bootstrapu, ważnym 1 dzień).

**Runda 0.52.2 (dalej: 0.52.2, gałąź `agent/bootstrap-po-purge`):**
naprawa strażnika bootstrapu (liczy tylko nieodwołane role aktywnych
kont — sekwencja purge→bootstrap wykonalna; wykryte na produkcji podczas
zakładania pierwszych prawdziwych kont). **Runda 0.52.1
(`agent/porzadki-demo`):** workflow
„Porządki demo (Fly.io)" — `purge_demo` na produkcji (diagnoza /
`--force`), bo baza produkcyjna niosła konta demo sprzed 0.43.0
i bootstrap pierwszych prawdziwych kont słusznie odmawiał.
**Runda 0.52.0 (`agent/pilotaz-10-podopiecznych`):**
limit 10 niezakończonych współprac na trenera (`DZIK_MAX_CLIENTS`)
+ dwa workflow workflow_dispatch („Pierwsze konta", „Sekrety produkcji")
zdejmujące z właściciela konieczność instalowania flyctl — bootstrap
i sekrety wyklikiwane z Actions. **Runda 0.51.0
(`agent/prawdziwy-trener`):** sekcja
„O trenerze" i kontakt z prawdziwymi danymi Łukasza Drygla („Lubelski
Dzik", IFBB PRO, Lublin/online) z publicznych profili; kontakt tel./
e-mail i social na stronie. **Runda 0.50.0 (`agent/og-i-galeria`):** meta-tagi
Open Graph + `og.png` (markowa karta linku na komunikatorach) i galeria
4 zrzutów demo na stronie marketingowej. **Runda 0.49.0
(`agent/strona-marketingowa`):**
publiczna strona marketingowa na `/` dla niezalogowanych (Landing.tsx,
personalizacja właściciela oznaczona komentarzami) + `POST
/api/public/lead` — zapytania z formularza trafiają jako powiadomienia
kategorii `ZAPYTANIE` do kont COACH (honeypot, limiter 5/h per IP,
zero nowych tabel). **Runda 0.48.0 (`agent/precyzja-i-baza`):** precyzja
kuchenna i baza ×5 (zgłoszenie właściciela z produkcji) — gramatury
posiłków zaokrąglane do wielkości mierzalnych (pół sztuki / 5 g / 10 g,
`units` w odpowiedzi kreatora), wbudowana baza 410 → 2058 pozycji
(`food_catalog_data_ext.py`, ten sam przycisk load-builtin), test
integralności bazy (unikalność po znormalizowanej nazwie, zakresy,
kcal↔makra). **Rundy 0.46–0.47:** kreator v2 po zrzutach z telefonu
właściciela (wbudowana baza jednym przyciskiem, dopełnianie braków
katalogu z jawnym znaczkiem, kompozycja wg wzorców śródziemnomorskiego/
DASH — warzywa/owoce jako stałe dodatki, premia obiadowa dla ryb
i strączków, deduplikacja produktów w posiłku, ostrzeżenia zbiorcze
zamiast ściany boxów) oraz scalenie Kompozytora i Kreatora w jedną
zakładkę **Dieta** z wyborem drogi (wzorzec 0.34.0/0.40.0).

**Runda 0.44.0 (gałąź `agent/kreator-diety`):** kreator diety —
`POST /coach/diet-wizard` (procentowy rozkład makro, 2–6 posiłków,
1–7 dni, wykluczenia, budżet czasu, regułowe sugestie przyrządzenia;
gramatura układem 3×3, na żywo: śr. 2174/2200 kcal i makra w punkt)
+ zakładka „Kreator diety" z „Utwórz plan żywieniowy" przez istniejące
`POST /nutrition`. Katalog: 409 pozycji — cel „200 najpopularniejszych"
był już spełniony. Propose-only pilnowane testem.

**Rundy 0.43.x:** repozytorium gotowe do pilotażu — `fly.toml` na
`production` bez seeda, workflow reset-demo usunięty, `bootstrap`
i `purge_demo` (uruchomione na żywo); poprawne linki https w e-mailach
(`DZIK_PUBLIC_URL` + proxy-headers), ścieżka zaproszeń zweryfikowana
end-to-end na żywym SMTP.

**Runda 0.42.0:** poczta wychodząca (`SMTPNotificationProvider` —
bloker nr 4 GO/NO-GO zamknięty w kodzie; sekrety SMTP ustawia właściciel)
+ pełne rozliczenie gałęzi bramkowej + podział E2E telefon/desktop
(15/15 przemierzone).

**Runda 0.41.0:** bomba dekompresyjna `.xlsx` (K-002 pkt 1) rozbrojona
wewnątrz `sheet_import.py` — kontrola sumy rozmiarów po rozpakowaniu
z katalogu ZIP-a przed `load_workbook`, twardy limit przeskanowanych
wierszy, limit szerokości wiersza; zmierzone na żywo: 400 MB XML
odrzucone w 83 ms przy +6,9 MB RSS (było: 1164 MB, 129 s). Do tego cztery
testy uwolnione od prawdziwej daty (odblokowanie CI całego repo).
**Wszystkie znaleziska przeglądu krzyżowego K-002 są zamknięte.**

**Runda 0.40.0 (poprzednia):** ekran Szablony scalony do jednej karty
„Dodaj szablon"; limity `_read_limited` na trzech importach (K-002 pkt 2);
scalenie katalogów E2E, Karta 1.0, dziennik K-NNN czytany przez bramkę.

**Znane problemy bramki lokalnej (dług testów, nie regresje):**

* ~~dwa testy OCR nazwane „bez Tesseracta"~~ — **naprawione w 0.54.4**
  (fixture `bez_silnika` wymusza brak binarki; obejście
  `DZIK_OCR_BINARY=__missing_tesseract__` niepotrzebne);
* ~~cztery testy zależne od prawdziwej daty~~ — **naprawione w 0.41.0**
  (23.08 prawdziwy zegar dogonił daty wpisane na sztywno i CI zrobiło się
  czerwone na czystym `main`): daty liczone względem `dates.local_today()`
  jak w seedzie, szum terminów płatności wyciszany w testach planowania.
  ~~Pozostałe testy z absolutnymi datami przyszłymi (strefy/DST
  w `test_notifications.py`)~~ — **naprawione w 0.54.4** tą samą kuracją,
  4 dni przed dogonieniem przez kalendarz (16.09).

**Bramki gałęzi porządkującej:** ruff czysto; backend 760 zaliczonych,
1 opcjonalny test Tesseracta pominięty; Core 275/275; kontroler spójności
37/37; `spojnosc.py` czysto (10 kontroli, 1 otwarta konsultacja). Frontendu
nie uruchamiano, ponieważ runda nie zmienia kodu ani zasobów frontendu.

---

## 2. Co jest w toku — NIE ZACZYNAJ OD NOWA

**Równoległe gałęzie jednego piszącego (zarządzenie 14.09, `KOORDYNACJA.md` §0):**

| Gałąź | Wersja | Migracja | Etap | Co blokuje | Kolejność scalania |
|---|---|---|---|---|---|
| `agent/nawyki-dzisiaj` | 0.63.0 | 34 | **scalona** (PR #65, 14.09), wdrożenie 0.63.0 w toku | — | — |
| `agent/wywiad-zapotrzebowanie` | 0.62.0 | 33 | **scalona** (PR #60, 14.09) i wdrożona | dokument właściciela `wywiad_zapotrzebowanie_kaloryczne.md` nadal niedostarczony — różnice do wyrównania | — |
| `agent/biblioteka-diet` | 0.64.0 | 35 | **scalona** (PR #66, 14.09), deploy 0.64.0 po CI na `main` | — | — |
| `agent/landing-czerwony` | 0.72.0 | — | **scalona** (PR #67, `195d475`, 14.09) | znak marki w czerwieni wszędzie (etap 2) — decyzja właściciela | — |
| `agent/motyw-czerwony` | **0.74.0** | **40** | zlecenie 4 (14.09): drugi motyw jasny czerwono-biały — tokeny, mechanizm, zapis na koncie, „Wygląd”, ekrany klienta/trenera/admina/publiczne i cardio 0.73.0 × 2 motywy przejrzane, bramka pikselowa ciemnego; `main` 0.73.0 scalony; **PR #76 gotowy do przeglądu** | decyzja o znaku (PWA/og/manifest w czerwieni) i ewentualnie „jak w systemie” | 1 |
| `agent/monitoring-postepy` | 0.66.0 | 36 | **scalona** (PR #61, 14.09), deploy 0.66.0 po CI na `main`; flaga na produkcji wyłączona | włączenie flagi + backfill — decyzja właściciela | — |
| `agent/ukryj-kreator` | 0.67.0 | — | **scalona** (PR #68, 14.09), deploy 0.67.0 po CI na `main`; kreator na produkcji ukryty (brak flagi w `fly.toml`) | — | — |
| `agent/wymiany-produktow` | 0.69.0 (0.68.0 = dni treningowe) | — | zlecenie 2 (14.09): silnik wymian v2 (poziom 2, powody, NONE 1:1, bramka „nie pogarsza”), grupy pokrewne (45 par, RO), korelacja katalogu → CSV; przegląd 3 recenzentów naprawiony (P0/P1 ×5, P2 w PROGRESS); `main` 0.67.0 scalony, PR #69 — CI | przegląd CSV przez właściciela (TAK/NIE) → import osobnym PR-em; decyzja o luzie bramki | 1 |
| `agent/dni-treningowe` | 0.71.0 | 38 (37 = PR #70) | zlecenie 1 (14.09): nakładka klienta na dni tygodnia planu, „Dzisiaj” z układem klienta, karta „ustaw dni”, odczyt u trenera; 13 testów API/silnika, E2E, przeklik; **PR #72 gotowy do przeglądu** | scalenie #70 (migracja 37 — bez niej `test_migracje_przenosnosc` czerwony); odpowiedzi właściciela na 3 pytania (domyślne przyjęte) | po #70 |
| `agent/wywiad-kaloryczny-rozpoznanie` | — (docs) | — (przyszła: 38 lub 39) | etap 0 rundy „wyrównanie wywiadu kalorycznego do spec 1.0” — `docs/wywiad-zapotrzebowanie/01_rozpoznanie_spec_v1.md` (tabela luk, migracja, testy, ryzyka) | **7 decyzji właściciela** (§5 rozpoznania: nowe pytania zdrowotne i klasyfikacja, zakres flagowania, stare wywiady, wiek vs data urodzenia, flaga a Monitoring, kolejność migracji, minimalne kcal) | po decyzjach |
| `agent/bloki-jak-szablony` | **0.76.0** | **41** (`exercise_blocks.cardio_json`) | polecenie właściciela 14.09: aeroby jako trzeci rodzaj bloku (9 presetów z silnika, 21 wbudowanych), „+ Cardio z bloku” (także w szablonie), `copy-to` z blokami + `from-blocks`, karta „Przypisz plan”; testy backend +12, helper +5, E2E +2, a11y 8a; **PR #79 — draft, bramki w raporcie sesji** | decyzja właściciela: mieszanki celów presetów (`presety.py`) i `variant=""` dla CARDIO w bazie (patrz plan sesji, odstępstwa) | po #78 (scalony) |
| `agent/szablony-i-opisy` | 0.75.0 | — | polecenie właściciela 14.09: szablony rozwijane po nazwie, „Opis ćwiczenia” + „Pełny opis w Wiedzy” w planie klienta (po id i po nazwie), trasy `by-name`, karta ćwiczenia w Wiedzy (klient v2/legacy, trener); testy API 5 + helper 6 + E2E +4 + a11y + PWA; **PR #77 po przeglądzie (brak P0/P1, P2 poprawione), `main` 0.74.0 dociągnięty** | pytanie: utrwalać dopasowanie po nazwie w planie? (domyślnie nie) | po CI |
| `agent/motyw-czerwony` | 0.74.0 | 40 | **scalona** (PR #76, `26a03af`, 14.09) | ikony PWA/og w czerwieni, `color-scheme: dark`, „jak w systemie”, jasne zrzuty galerii (`docs/motyw/PROGRESS.md`) | — |
| `agent/cardio-i-rozgrzewka` | 0.73.0 | 39 | **scalona** (PR #75, `8a71116`, 14.09) | przegląd treści i kotwic [C] przez trenera (`docs/cardio/PROGRESS.md`); odpowiedzi właściciela na 7 pytań §8 (domyślne przyjęte) | — |
| `agent/powitanie-samouczek` | 0.70.0 | 37 (`users.welcome_seen_at`; dni treningowe → 38) | sekcja E promptu „Panel Dzisiaj” (14.09): dwuetapowy samouczek po pierwszym logowaniu (pomoc, nie bramka), znacznik na serwerze, `POST /api/me/welcome-seen`, „Więcej → Pomoc / Samouczek”; testy backend + E2E + a11y + PWA zielone, przeklik ze zrzutami; `main` 0.69.0 scalony, PR #70 — ready | pytanie: treść kroku 2 wspomina wymianę składnika (moduł szablonów diet na produkcji za flagą) — zostawić warunkowo czy usunąć do czasu włączenia flagi? | 2 |

| Rzecz | Stan | Gdzie |
|---|---|---|
| **Sekrety SMTP** | kod gotowy (0.42.0); workflow „Sekrety produkcji” z zakresem `poczta` (0.54.5) — właściciel dodaje `DZIK_SMTP_HOST/PORT/USER/PASSWORD/FROM` w sekretach repo i klika Run workflow; do tego czasu dostawca `null`: zaproszenia wracają trenerowi jako link do przekazania, reset hasła e-mailem martwy | Actions → „Sekrety produkcji” |
| **Dostawca AI** | **ZAIMPLEMENTOWANY (0.45.0)** — `AnthropicAIProvider`; do uruchomienia na produkcji brakuje wyłącznie sekretów właściciela (`DZIK_AI_API_KEY` + `DZIK_AI_ENABLED=true`, `DEPLOYMENT.md` §4d); prawdziwe wywołanie modelu nigdy się nie wykonało | `backend/dzik_os/ai_provider.py` |
| Klucz API | właściciel go ma; **musi trafić do sekretu**, nigdy do czatu ani repozytorium | `DZIK_AI_API_KEY` + `DZIK_AI_ENABLED=true` |
| Decyzja o `extra="forbid"` | przygotowana analiza, **decyzja należy do właściciela** | `BRAMKA_GO_NOGO.md` §4 |
| Wyniesienie kopii zapasowych poza Fly | czeka na wybór dostawcy magazynu | `ODZYSKIWANIE.md` §5 |

---

## 3. Co następne — kolejka

Kolejność jest propozycją; właściciel może ją zmienić w dowolnym momencie.

1. **Pilotaż — działania właściciela** (repo jest gotowe od 0.43.0):
   po scaleniu deploy pójdzie z automatu; potem po SSH `bootstrap`
   (pierwsze prawdziwe konta, hasła przez env) i `purge_demo` (konta demo
   ze znanymi hasłami — dezaktywacja); sekrety `DZIK_FILE_KEY` i SMTP
   (`flyctl secrets set`); jedno pełne odtworzenie kopii NA produkcji;
   test PWA na prawdziwym telefonie; pisemna zgoda klienta pilotażowego
   (`BRAMKA_GO_NOGO.md` §6). Decyzje otwarte: dostawca e-maila, magazyn
   kopii poza Fly (S3/B2), `extra="forbid"`, SQLite vs Postgres, R-01
   (ocena prawna danych zdrowotnych).
2. **Przygotowanie pilotażu** — usunięcie `DZIK_SEED_DEMO` z `fly.toml`
   (zasiewa konta ze znanymi hasłami), zmiana haseł, jedno odtworzenie
   kopii **na produkcji**.

---

## 4. Czego nie wolno ruszać

* `hos_engine/` i `tests/` w korzeniu — Core Human OS. **275 testów musi
  zostać zielone.** Praca aplikacji nigdy tego nie dotyka.
* Nie otwierać ponownie PR #13 i nie dodawać drugiego scalenia tych samych
  historii. Nie zmieniać gałęzi domyślnej bez osobnej decyzji właściciela.
* `claude/ocena-projektu-dzik-os-76ercy` jest rozliczona (0.42.0) —
  nie scalać jej już w żadnej formie i nie przenosić z niej niczego więcej;
  commit `81eb30a` odrzucono świadomie (uzasadnienie w CHANGELOG).
* Migracje już wydane: numeracja idzie **od największego numeru**, luk się
  nie zostawia (domyka się je pustym wpisem — patrz `db.py`, numer 21).
* Historia planów, diet i szablonów: nowa wersja, **nigdy nadpisanie**.

---

## 5. Zanim uznasz rundę za skończoną

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q                     # Core: 275 zielonych
python apps/dzik-os/tools/spojnosc.py          # 10 kontroli
python apps/dzik-os/tools/mutacje.py           # 17/17
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py   # 9/9
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers
```

Do tego **uruchom to, co nowe, i zobacz na własne oczy**
(`docs/ZASADA_URUCHOMIENIA.md`) — testy są warunkiem wstępnym, nie
dowodem. W raporcie napisz, co kliknąłeś i co zobaczyłeś.

Na koniec: zaktualizuj ten plik i zwolnij rezerwacje w `KOORDYNACJA.md`.

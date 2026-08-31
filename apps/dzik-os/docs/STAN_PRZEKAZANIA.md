# Stan przekazania — przeczytaj przed rozpoczęciem rundy

**Aktualizacja:** 2026-08-31 · **Wersja w `main`:** 0.54.2
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

**Ostatnia runda (0.54.2, gałąź `agent/dodaj-klienta`):**
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

* dwa testy OCR nazwane „bez Tesseracta" nie izolują tego założenia
  i czerwienią się, gdy binarka jest dostępna (obejście:
  `DZIK_OCR_BINARY=__missing_tesseract__`);
* ~~cztery testy zależne od prawdziwej daty~~ — **naprawione w 0.41.0**
  (23.08 prawdziwy zegar dogonił daty wpisane na sztywno i CI zrobiło się
  czerwone na czystym `main`): daty liczone względem `dates.local_today()`
  jak w seedzie, szum terminów płatności wyciszany w testach planowania.
  **Uwaga:** inne testy z absolutnymi datami przyszłymi (strefy/DST w
  `test_notifications.py` — 16.09, 25.10.2026) czekają na tę samą kurację,
  zanim kalendarz je dogoni — dołożone do małej rundy naprawczej.

**Bramki gałęzi porządkującej:** ruff czysto; backend 760 zaliczonych,
1 opcjonalny test Tesseracta pominięty; Core 275/275; kontroler spójności
37/37; `spojnosc.py` czysto (10 kontroli, 1 otwarta konsultacja). Frontendu
nie uruchamiano, ponieważ runda nie zmienia kodu ani zasobów frontendu.

---

## 2. Co jest w toku — NIE ZACZYNAJ OD NOWA

| Rzecz | Stan | Gdzie |
|---|---|---|
| **Sekrety SMTP** | kod gotowy (0.42.0); do uruchomienia poczty właściciel ustawia `DZIK_SMTP_HOST`/`USER`/`PASSWORD`/`FROM` jako sekrety Fly — bez nich reset hasła pozostaje martwy (klient bez drogi powrotu, jedyna alternatywa: ponowne zaproszenie od trenera) | `flyctl secrets set` |
| **Testy OCR** | dwa testy „bez Tesseracta” nie izolują założenia i czerwienią się, gdy binarka jest zainstalowana; poprawić w osobnym małym PR | `backend/tests/test_ocr.py` |
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
2. **Mała runda naprawcza testów:** testy OCR (izolacja założenia „bez
   Tesseracta") + testy stref/DST z datami absolutnymi (16.09, 25.10.2026)
   — ta sama kuracja co cztery naprawione w 0.41.0; do tego stara fraza
   „jedna-sesja-naraz" w `KARTA_WSPOLPRACY.md` (linia ~191).
3. **Przygotowanie pilotażu** — usunięcie `DZIK_SEED_DEMO` z `fly.toml`
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

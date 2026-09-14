# PROMPT dla sesji piszącej — „Rozgrzewka, rozciąganie i cardio z suwakami celów” (dwa nowe rodzaje jednostek w planie)

> Skopiuj ten plik w całości jako pierwszą wiadomość do sesji piszącej. Model suwaków
> jest opisany osobno w `model-suwakow-cardio.md` (obok) — to specyfikacja silnika;
> ten plik mówi, jak wpiąć ją w istniejący plan, katalog i dziennik. Rozpoznanie
> kodu wykonane 14.09 (§2) — zweryfikuj linie, nie powtarzaj od zera.

---

Przeczytaj: `/AGENTS.md`, `/CLAUDE.md`, `apps/dzik-os/docs/KARTA_WSPOLPRACY.md`,
`apps/dzik-os/docs/STAN_PRZEKAZANIA.md`, `apps/dzik-os/docs/KOORDYNACJA.md`,
`apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`, `apps/dzik-os/docs/KONFIGURATOR.md`,
`apps/dzik-os/docs/BAZA_CWICZEN.md`, `apps/dzik-os/docs/PERMISSIONS.md` §5.5
(propose-only), `apps/dzik-os/docs/zlecenia/model-suwakow-cardio.md`.

**Rola:** aktywny piszący. WYŁĄCZNIE `apps/dzik-os/`. Core nietykalny.
**Gałąź:** `agent/cardio-i-rozgrzewka` od aktualnego `main`. Pierwszy commit wyłącznie
`docs/plan-sesji/cardio-i-rozgrzewka.md`; draft PR `[WRITER] Rozgrzewka, rozciąganie
i cardio z suwakami`; dopiero potem kod. **Rezerwacje:** wersja wg kolejności scalania
z `README.md` tego katalogu; **migracja: kolejna wolna** (na `main` ostatnia = 36;
37 = dni treningowe; sprawdź `db.py` i tabelę §2 `STAN_PRZEKAZANIA.md` tuż przed
zmianą). Niezależne od gałęzi w toku (dieta, landing, motyw), ale dotyka `models.py`,
`schemas.py`, `db.py`, `Plan.tsx`, `Today.tsx`, `PlanEditor.tsx` — te same pliki co
zlecenie 1 (dni treningowe): **nie pracuj równolegle z nim na tych plikach**; kolejność
ustala właściciel. Bez force-pusha; commity po polsku, bez nazw modeli AI; nie scalasz PR-a.

## 1. Zlecenie właściciela (14.09.2026, czwarta tura)

> Potrzebujemy zaimplementować jeszcze dwa rodzaje ćwiczeń: rozgrzewka na 3 poziomach
> zaawansowania w 3 wariantach, rozciąganie, i ćwiczenia fitness typu rowerek, bieżnia,
> bieżnia skos/chód, steper, wioślarz. W ćwiczeniach fitness genialnie byłoby mieć coś na
> zasadzie suwaka: 3 główne cele (utrata tkanki, wydolność i trzeci — znajdź najtrafniejszy);
> po równo każdy suwak ma 1/3, przesuwając jeden zabieramy pozostałym; z wiedzy i badań
> ustawienie suwaków sugeruje tętno, obciążenie, tempo i czas. Może uda się znaleźć model,
> na którym da się to odwzorować; następnie dobieramy jedno z ćwiczeń.

Odpowiedź na „czy jest model”: **tak** — trzy strefy wg progów (Seiler) + rezerwa tętna
(Karvonen) + Fatmax + interwały pod VO2max; trzeci cel: **Regeneracja (baza tlenowa)**
z uzasadnieniem i dwiema alternatywami w `model-suwakow-cardio.md` §2. Właściciel
zatwierdza nazwy trzech celów (§8 pyt. 1).

## 2. Rozpoznanie — na czym budujemy (main 0.66.0, zweryfikuj linie)

| Element | Gdzie | Co z tego wynika |
|---|---|---|
| Katalog ćwiczeń: `Exercise` (`models.py` l. 774–~815): `muscle_group` ∈ NOGI/PLECY/KLATKA/BARKI/RECE/BRZUCH/CALE_CIALO/**MOBILNOSC/CARDIO**/INNE, `level` ∈ POCZATKUJACY/SREDNIOZAAWANSOWANY/ZAAWANSOWANY, `pattern`, `equipment`, `how_to`, `benefit`, `video_url`, broadcast trenera | wbudowana baza `exercise_catalog.py`: **155 ćwiczeń**, w tym **14 MOBILNOSC** (krążenia ramion, koci grzbiet, world's greatest stretch, rotacja 90/90, open book, zginacze bioder, łydki o ścianę, dwugłowe z taśmą, mobilizacja skokowego, halo KB, zwis, …) i **14 CARDIO** (rower stacjonarny, marsz pod górę na bieżni, stepper, wioślarz — interwały, orbitrek, bieg konwersacyjny, interwały 30/30, skakanka, assault bike, …) | rozgrzewki składamy z istniejących wpisów; brakuje **rozciągania statycznego** (czworogłowe, dwugłowe siedząc, pośladkowe, przywodziciele, kark, przedramiona) i **jednostek cardio „na parametry”** (bieżnia skos jako osobny wpis jest: „Marsz pod górę na bieżni”) |
| Pozycja ćwiczenia w planie: `schemas.ExerciseIn` (l. 68–93): `id`, `name`, `exercise_id` (miękkie odniesienie), `sets`, `reps`, `weight`, `tempo`, `rest`, `comment`, `video_url`, `target_rir`, `progression` — **wszystko tekst, bez rodzaju** | treść JSON w niemutowalnej wersji (`content_json`, `days[].exercises[]`), stabilne `id` z `publikacja/elementy.py::znormalizuj` | nowe rodzaje = **nowe opcjonalne klucze w tym samym JSON** (bez migracji planu): `kind`, `block_id`, `cardio` |
| Dzień planu: `PlanDayIn` (`id`, `name`, `weekday`, `exercises`) | | dzień dostaje opcjonalne `warmup_block_id`, `cooldown_block_id` |
| Dziennik: `WorkoutSetIn` ma już `warmup: bool` i `unit` (0.66.0, decyzja właściciela 14.09 — „seria rozgrzewkowa wykluczona z rekordów”), `WorkoutEntryIn` = `exercise_index`, `result`, `sets[]`, `comment`, `file_id`; `WorkoutSessionIn` = `plan_version_id`, `day_index`, `performed_on`, `status`, `pain_flag` | **brak pól czasu, tętna, RPE, dystansu** | cardio potrzebuje w `WorkoutEntryIn` opcjonalnych: `duration_min`, `avg_hr`, `rpe`, `distance_km`, `machine` — JSON w `WorkoutEntry` czy kolumny: patrz §4.4 (migracja) |
| Bramka zdrowotna konfiguratora: `konfigurator/zdrowie.py::ocen_zdrowie` (objawy alarmowe → `urgent_stop`; brak odpowiedzi → `needs_input`, nigdy „zielone”; choroba → `needs_review`) | | **reużyj 1:1** dla propozycji cardio; dołóż jedno pytanie: leki wpływające na tętno (beta-blokery) → tryb „tylko RPE” |
| Ślad decyzji: `konfigurator/silnik.py::_issue(code, severity, message, rule_id)` z `rule_id` `H_LAYOUT`/`H_VOLUME`; zapis przez `/konfigurator/zapisz` do `TrainingPlanVersion`; zakładka Wiedza → „Dlaczego?” czyta ślad | | ślad suwaków z `rule_id="H_CARDIO"` (§7 modelu) |
| Propose-only: `POST /api/konfigurator/podglad` (liczy) → `POST /zapisz` (trener tworzy wersję) | | ten sam kształt: `POST /api/cardio/podglad` → wynik trafia do edytora planu jako pozycja `kind: "cardio"`; klient nigdy nie dostaje propozycji bez publikacji |
| Sprzężone procenty: kreator diety pilnuje tylko „Suma makro = 100 %” (`Knowledge.tsx` l. 1828–1830), **bez sprzęgania suwaków**; jedyny `input[type=range]` to skala w raporcie (`.scale-row`) | | mechanizm „zabieranie pozostałym” trzeba napisać (mały helper + test) |
| Konfigurator 28 dni: K1 silnik bez rozgrzewki/cardio; `KONFIGURATOR.md` l. 58 wymienia „rozgrzewka vs …” jako temat pilotażu zrozumiałości; monitoring 0.66.0 wprowadził tylko flagę serii | | rozgrzewka jako **blok dnia** to nowość, nie rozszerzenie konfiguratora (K2 może z niej korzystać później) |
| Dane klienta do modelu: wiek/data urodzenia i doświadczenie w profilu/wywiadzie (`profile_service.py`, `coach_hints.py`), tętno spoczynkowe — brak | | wiek → HRmax (Tanaka); brak → RPE; tętno spoczynkowe jako nowe pole opcjonalne wpisywane przez klienta (`ProfileField`, źródło CLIENT_DECLARED) |

## 3. Decyzje projektowe (propose-only → do zatwierdzenia w §8)

1. **Trzy rodzaje pozycji w planie:** `kind ∈ {"strength" (domyślne, brak klucza = strength), "warmup_block", "stretch_block", "cardio"}`. Stare plany bez `kind` działają bez zmian (kompatybilność jak `target_rir`).
2. **Bloki rozgrzewki i rozciągania = byty katalogowe trenera** (`ExerciseBlock`: `id`, `coach_id`, `kind` WARMUP/STRETCH, `level`, `variant` G/D/C, `name`, `duration_min`, `items_json` = lista `{exercise_id|null, name, dose ("3 min"/"2×10"/"20 s/str."), note}`, `status`, wersjonowanie jak `Exercise`). Wbudowany zestaw **3×3 rozgrzewek + 3 bloki rozciągania** (szkic treści w §5) ładowany przyciskiem jak „wbudowana baza” (`load-builtin`), oznaczony `source="wbudowany — do przeglądu trenera"`. Dzień planu wskazuje blok przez `warmup_block_id`/`cooldown_block_id` (miękkie odniesienie + **migawka treści** w wersji planu, żeby archiwizacja bloku nie psuła planów — wzorzec `exercise_id` + `name`).
3. **Cardio = pozycja `kind: "cardio"`** z polami: `machine` ∈ {`rowerek`, `bieznia`, `bieznia_skos`, `steper`, `wioslarz`} **albo lista dozwolonych** (klient wybiera w dniu treningu), `goal_mix` `{redukcja, wydolnosc, regeneracja}` (suma 1), `prescription` = wynik silnika (`hr_pct_range`, `hr_bpm_range|null`, `hrr_used`, `rpe_range`, `talk_test`, `duration_min`, `structure` {`type` ciągła/tempo/interwały, `work`, `rest`, `rounds`}, `machine_params` per urządzenie, `kcal_estimate`, `caveats[]`), `trace` (ślad `H_CARDIO`) i `model_version: "cardio_model_v1"`. Trener może każdą liczbę nadpisać ręcznie (pole edytowalne = propose-only); nadpisanie zapisuje się w śladzie jako `overridden_by_coach`.
4. **Silnik = czyste funkcje** `dzik_os/cardio/model.py` (mieszanie wag, kotwice, struktura wg poziomu, przeliczenie HRmax/HRR, tłumaczenie na urządzenie, MET-y) z testami na przykładach kontrolnych z `model-suwakow-cardio.md` §4; **zero AI**; stałe modelu w jednym słowniku z komentarzem źródła i poziomem pewności.
5. **Bramka zdrowotna przed propozycją** (`ocen_zdrowie` + pytanie o leki wpływające na tętno). `needs_review` → propozycja tylko z ostrzeżeniem dla trenera; `urgent_stop` → brak propozycji. Blok zdrowotny **nie jest zapisywany** w planie (jak konfigurator).
6. **Klient:** na „Dzisiaj” i w Planie pozycja cardio pokazuje: cel (trzy paski wag), urządzenie do wyboru (jeśli lista), „zacznij od…” (tempo/obciążenie), zakres tętna **i** RPE + test mowy, czas, strukturę interwałów z prostym timerem (reużyj `RestTimer`), zastrzeżenie o bilansie energii (jedno zdanie), „Dlaczego?” ze śladem. Rozgrzewka/rozciąganie: rozwijana lista pozycji z dawką, odhaczana jako całość (nie per pozycja).
7. **Dziennik:** wpis cardio zapisuje `duration_min`, `avg_hr` (opcjonalnie), `rpe`, `machine`, `distance_km` (opcjonalnie); Postępy pokazują historię cardio osobno (bez rekordów kg). Serie rozgrzewkowe siłowe — bez zmian (flaga z 0.66.0).
8. **Zero rankingów, zero automatycznej progresji** — model proponuje na dziś; kolejny tydzień = trener.

## 4. Co dokładnie zbudować

### 4.1 Backend
* `dzik_os/cardio/model.py` + `dzik_os/cardio/urzadzenia.py` (tabela §5 modelu) + `dzik_os/cardio/dane/stale.json` (kotwice, MET-y, ze źródłem i pewnością).
* `routers/cardio.py`: `POST /api/clients/{client_id}/cardio/podglad` (COACH, `resolve_client_access` write + domena zdrowotna dla bramki; body: `goal_mix`, `level`, `machines[]`, `duration_hint?`, `health{}`, `resting_hr?`) → `prescription`+`trace`+`issues`; `GET /api/cardio/katalog` (urządzenia, cele, opisy). Bez `zapisz` — wynik wkleja się do szkicu planu przez istniejącą publikację (0.58.0).
* `ExerciseBlock` model + migracja (`exercise_blocks`), `routers/exercise_blocks.py` (CRUD trenera, `load-builtin`, archiwizacja ≠ kasowanie), macierz dostępu, eksport (broadcast trenera — jak `Exercise`, nie dane klienta).
* `schemas.py`: `ExerciseIn` + `kind`, `block_id`, `cardio: CardioIn|None`; `PlanDayIn` + `warmup_block_id`, `cooldown_block_id`; `WorkoutEntryIn` + pola cardio; `publikacja/elementy.py`: nowe klucze przechodzą przez normalizację/różnice (podsumowanie po polsku: „zmieniono cel cardio”).
* `WorkoutEntry`: kolumny `duration_min`, `avg_hr`, `rpe`, `distance_km`, `machine` (addytywne, NULL) — **ta sama migracja** co `exercise_blocks` (jedna na rundę).
* Katalog wbudowany: ~10 wpisów rozciągania statycznego (`muscle_group="MOBILNOSC"`, `pattern="ROZCIAGANIE"` — sprawdź słownik `muscles.MOVEMENT_PATTERNS`, jeśli brak wartości, dodaj) + 5 wpisów cardio „na parametry” (jeśli wpisy z katalogu nie wystarczą: „Bieżnia — chód pod górę”, „Steper”, „Wioślarz — ciągle”, „Rowerek — ciągle”, „Bieżnia — bieg”), z `how_to` napisanym przez writera **i oznaczonym do przeglądu trenera** (`source`).
* Seed demo: dzień „Trening C — całe ciało” klienta A dostaje rozgrzewkę C/początkujący i pozycję cardio (rowerek, mix 0,5/0,25/0,25).

### 4.2 Frontend
* Edytor planu (`PlanEditor.tsx`, `SzkicPlanu.tsx`): w dniu „Rozgrzewka: [wybór bloku poziom/wariant]” i „Rozciąganie: [blok]”; przycisk „+ Cardio” → panel: trzy sprzężone suwaki (helper `suwaki.ts`: `przesun(wagi, indeks, nowa)` — zabiera pozostałym proporcjonalnie, kłódka; test w `test:helpers`), poziom, urządzenia, „Policz propozycję” → tabela tętno/RPE/czas/struktura/urządzenie + ostrzeżenia bramki + „Wstaw do dnia” (pola edytowalne przed wstawieniem).
* Klient (`Plan.tsx`, `Today.tsx`): renderowanie trzech rodzajów (§3.6), wybór urządzenia, timer interwałów, formularz dziennika cardio (czas, RPE, tętno, dystans).
* Postępy: sekcja „Cardio” (lista sesji, suma minut/tydzień, bez rankingu).
* Panel trenera: zakładka „Bloki” w Szablonach (lista 3×3 + rozciąganie, edycja pozycji, „Dodaj z wbudowanych”).
* Wiedza → „Dlaczego?”: ślad `H_CARDIO` czytelny dla klienta (wagi, kotwice, zastrzeżenia).

### 4.3 Testy
* Silnik: przykłady kontrolne §4 modelu (5 przypadków), sufit początkującego, brak wieku → tylko RPE, Karvonen gdy `resting_hr`, beta-blokery → `hr_bpm_range=None`, determinizm, suma wag ≠ 1 → 422.
* Bramka: `urgent_stop` → brak propozycji; `needs_input` → pytania; `needs_review` → propozycja z ostrzeżeniem.
* API: trener bez relacji → 404; klient → 403 (propozycja tylko dla trenera); ślad w wersji planu po publikacji; różnice po `id` z polskim podsumowaniem dla `goal_mix`.
* Bloki: CRUD, load-builtin idempotentny, archiwizacja nie psuje planu (migawka).
* Dziennik: wpis cardio bez serii, eksport danych zawiera nowe pola, rekordy pomijają cardio.
* Front: `test-suwaki.mjs` (zabieranie proporcjonalne, kłódka, zaokrąglenie do 5 %, suma zawsze 100), E2E `cardio.spec.ts` (trener liczy propozycję i wstawia; klient widzi na „Dzisiaj”, wybiera wioślarz, zapisuje 25 min RPE 6; „Dlaczego?” pokazuje ślad) i `rozgrzewka.spec.ts` (blok w dniu, odhaczenie).
* a11y: suwaki jako `input[type=range]` z `aria-valuetext` („Redukcja 50 %”), klawiatura.

### 4.4 Dokumentacja
`CHANGELOG`, `BAZA_CWICZEN.md` (bloki, nowe wpisy do przeglądu), `KONFIGURATOR.md`
(relacja K1/K2 ↔ bloki), `INSTRUKCJA_TRENERA.md` (suwaki, co znaczą, że to propozycja),
`INSTRUKCJA_KLIENTA.md`, `PERMISSIONS.md` (nowe trasy), `WIEDZA.md` (ślad `H_CARDIO`),
`RISK_REGISTER.md` (ryzyko: liczby tętna u osoby z chorobą — bramka + RPE),
`RELEASE_STATUS`, `STAN_PRZEKAZANIA`, plan sesji, `docs/cardio/00_rozpoznanie.md` i
`PROGRESS.md` (w tym **lista treści do przeglądu trenera**: bloki, nowe ćwiczenia,
tabela urządzeń, kotwice [C]).

## 5. Szkic treści bloków (z katalogu; DO PRZEGLĄDU TRENERA)
Warianty = pod jaką sesję (spójne z nazwami dni „Trening A — góra / B — dół / C — całe ciało”):
**G** góra ciała · **D** dół ciała · **C** całe ciało. Poziom = POCZATKUJACY / SREDNIOZAAWANSOWANY /
ZAAWANSOWANY (słownik katalogu). Każdy blok: 1 pozycja „podniesienie tętna” (cardio z katalogu,
3–6 min, RPE 3–4) + 3–5 pozycji mobilności/aktywacji (czas lub powtórzenia) + 1 pozycja
„seria wprowadzająca” (opis, nie ćwiczenie: „pierwsze ćwiczenie planu z 40–50 % ciężaru”).

| Poziom | G — góra | D — dół | C — całe ciało |
|---|---|---|---|
| Początkujący (≈8 min) | Marsz w miejscu z wysokim kolanem 3 min · Krążenia ramion 2×10 · Koci grzbiet 8 · Rozciąganie klatki w narożniku 2×20 s · Open book 6/str. · seria wprowadzająca | Rower stacjonarny 4 min · Krążenia bioder w podporze 8/str. · Rozciąganie zginaczy bioder w wykroku 20 s/str. · Mobilizacja stawu skokowego 8/str. · Rotacja bioder 90/90 6/str. · seria wprowadzająca | Marsz pod górę na bieżni 4 min · Koci grzbiet 8 · World's greatest stretch 4/str. · Krążenia ramion 2×10 · Rozciąganie łydek o ścianę 20 s/str. · seria wprowadzająca |
| Średni (≈10 min) | Wioślarz lekko 4 min · Halo z kettlebell 2×8/str. · Open book 8/str. · Rozciąganie klatki w narożniku 2×20 s · Zwis na drążku 2×20 s · seria wprowadzająca | Stepper 4 min · Wykrok z rotacją 6/str. · Rotacja bioder 90/90 8/str. · Rozciąganie dwugłowych z taśmą 20 s/str. · Krążenia bioder w podporze 8/str. · seria wprowadzająca | Orbitrek 4 min · World's greatest stretch 5/str. · Halo z kettlebell 8/str. · Wykrok z rotacją 6/str. · Mobilizacja stawu skokowego 8/str. · seria wprowadzająca |
| Zaawansowany (≈12 min) | Assault bike / wioślarz 5 min z 2 przyspieszeniami · Halo z kettlebell 2×10/str. · Zwis na drążku 2×30 s · Open book 8/str. · Krążenia ramion z taśmą 2×12 · seria wprowadzająca 2 stopnie | Skakanka 4 min · Wykrok z rotacją 8/str. · Rotacja bioder 90/90 10/str. · Rozciąganie zginaczy bioder 30 s/str. · Podbiegi lekkie 3×20 m (albo marsz pod górę) · seria wprowadzająca 2 stopnie | Interwały biegowe lekkie 5 min (30/30 przy RPE 5) · World's greatest stretch 6/str. · Halo z kettlebell 10/str. · Krążenia bioder w podporze 10/str. · Rozciąganie łydek 20 s/str. · seria wprowadzająca 2 stopnie |

Brakuje w katalogu (nowe wpisy do dodania jako MOBILNOSC/ROZCIAGANIE, treść trenera):
rozciąganie po treningu (statyczne 20–30 s/str.): czworogłowe stojąc, dwugłowe siedząc, pośladkowe
(„figura 4”), łydki, klatka w narożniku (jest), najszersze (jest jako zwis), zginacze bioder (jest),
przywodziciele, kark/karkowe, przedramiona. Bloki rozciągania: te same 3 warianty (G/D/C), jeden
poziom (czas 5–8 min), po treningu — bez podziału na poziomy (właściciel wspomniał „rozciąganie”
bez poziomów; pytanie).

## 6. Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|
| 0 | plan sesji, `docs/cardio/00_rozpoznanie.md` (weryfikacja linii z §2) | — | tysiące |
| 1 silnik cardio | `cardio/model.py`, `urzadzenia.py`, `stale.json`, testy przykładów kontrolnych | pytest modułu | dziesiątki tys. |
| 2 model + migracja | `ExerciseBlock`, kolumny `WorkoutEntry`, wbudowane bloki i ćwiczenia, seed | `test_migracje_przenosnosc`, integralność katalogu | dziesiątki tys. |
| 3 API + publikacja | `routers/cardio.py`, `routers/exercise_blocks.py`, `schemas`, `elementy.py`, macierz, eksport | pytest API, macierz, bramka | setki tys. |
| 4 UI trenera | edytor: bloki + panel cardio z suwakami | `tsc`, build (budżet 120 kB — panel przez `React.lazy`), `test-suwaki.mjs`, obejrzenie | setki tys. (największy koszt) |
| 5 UI klienta + dziennik + Postępy | Plan/Dzisiaj/Postępy, timer, formularz | E2E ×2, a11y, obejrzenie na telefonie przez serwer E2E | setki tys. |
| 6 zamknięcie | dokumenty, lista do przeglądu trenera, CHANGELOG | pełny pytest, ruff z korzenia, Core 275, spójność, mutacje, CI | dziesiątki tys. |

Bezpiecznik: 3× plan. Przegląd: 3 recenzentów (bezpieczeństwo zdrowotne i propose-only,
poprawność silnika i determinizm, UX/a11y/treść). **Runda jest duża — jeśli przekracza
bezpiecznik, tnij w tej kolejności:** najpierw Postępy-cardio (etap 5, część), potem
zakładka „Bloki” w Szablonach (bloki tylko wbudowane, edycja później), nigdy bramka
zdrowotna ani ślad.

## 7. Czego świadomie NIE robimy
Automatyczna progresja cardio tydzień do tygodnia; testy progowe/FTP/HRV; integracje
z zegarkami (import tętna); rankingi; AI; zmiana konfiguratora K1 (bloki podpina K2
później); kasowanie czegokolwiek (archiwizacja).

## 8. Pytania do właściciela (odpowiedz w tej wiadomości albo zostaw domyślne)
1. Trzeci cel: **Regeneracja (baza tlenowa)** — zgoda? Alternatywy: Wytrzymałość,
   Moc/szybkość (model §2). *Domyślnie: Regeneracja.*
2. Nazwa celu 1 w UI: „Redukcja (wydatek energii)” zamiast „Spalanie tłuszczu” — bo
   o utracie tkanki decyduje bilans, a nie strefa. *Domyślnie: „Redukcja”.*
3. Warianty rozgrzewki = pod sesję (góra/dół/całe ciało)? Alternatywa: czas 5/10/15 min
   albo miejsce (siłownia/dom). *Domyślnie: góra/dół/całe ciało.*
4. Rozciąganie: 3 warianty bez poziomów, po treningu (5–8 min)? *Domyślnie: tak.*
5. Kto wybiera urządzenie: trener wskazuje listę dozwolonych, klient wybiera w dniu
   treningu? *Domyślnie: tak.*
6. Kto przegląda treść bloków, nowe wpisy katalogu i tabelę urządzeń — trener Łukasz przed
   włączeniem u prawdziwych klientów? *Domyślnie: tak, wpisy oznaczone „do przeglądu”.*
7. Pole „tętno spoczynkowe” wpisywane przez klienta w profilu (dane zdrowotne, zgoda)?
   *Domyślnie: tak, opcjonalne.*

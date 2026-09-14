# PROMPT dla sesji piszącej — „Dni treningowe” (klient wybiera dni tygodnia dla jednostek planu; „Dzisiaj” pokazuje trening z dzisiejszego dnia)

> Skopiuj ten plik w całości jako pierwszą wiadomość do sesji piszącej.
> Rozpoznanie kodu jest już wykonane (sekcja 3) — nie powtarzaj go od zera,
> tylko **zweryfikuj** wskazane linie, bo `main` mógł się przesunąć.

---

Przeczytaj kolejno: `/AGENTS.md`, `/CLAUDE.md`,
`apps/dzik-os/docs/KARTA_WSPOLPRACY.md`, `apps/dzik-os/docs/STAN_PRZEKAZANIA.md`,
`apps/dzik-os/docs/KOORDYNACJA.md`, `apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`.

**Rola:** aktywny piszący (wyznaczony przez właściciela tą wiadomością).
Pracujesz WYŁĄCZNIE w `apps/dzik-os/`. Core (`hos_engine/`, `tests/` w korzeniu)
jest nietykalny — 275 testów Core musi zostać zielone.

**Gałąź:** `agent/dni-treningowe` od aktualnego `main`. Pierwszy commit zawiera
wyłącznie `apps/dzik-os/docs/plan-sesji/dni-treningowe.md` (szkic w pliku
`plan-sesji_dni-treningowe.md` obok tego promptu — uzupełnij go o rezerwacje
sprawdzone na żywo i wklej). Po pushu od razu draft PR `[WRITER] Dni treningowe`
do `main`. Dopiero potem kod.

**Rezerwacje (sprawdź w `db.py`, `CHANGELOG.md` i tabeli §2 `STAN_PRZEKAZANIA.md`
tuż przed zmianą — nie przepisuj z pamięci):** proponowane **wersja 0.66.0,
migracja 37** (34 = ostatnia w `main`; 35 = `agent/biblioteka-diet`; 36 =
`agent/monitoring-postepy`). Jeśli któraś z tych gałęzi została scalona albo
zmieniła numer, weź kolejny wolny i odnotuj w planie sesji oraz w tabeli §2.
Zadanie jest niezależne od obu gałęzi w toku (nie dotyka diety ani monitoringu).

Nie rozwiązuj konfliktów automatycznie, nie rób force-pusha, commituj po polsku,
bez nazw modeli AI w treści commita. Nie scalaj własnego PR-a.

---

## 1. Problem (słowami właściciela, 14.09.2026)

> Klient posiadający już plan na tydzień od trenera nie ma żadnej informacji,
> w jaki dzień realizuje jego części. Propozycja jest taka, żeby mógł sobie
> wybrać, w jakie dni tygodnia będzie go realizował. Chciałbym, żeby trening
> z konkretnego dnia pojawił się w pierwszej zakładce „Dziś”.

## 2. Diagnoza (dlaczego dziś to nie działa)

Mechanizm „trening na dziś” **już istnieje**, ale zależy wyłącznie od pola
`weekday` wpisanego przez trenera w edytorze planu — i to pole jest prawie
zawsze puste:

* `TrainingPlanVersion.content_json` = `{"days": [{"id"?, "name", "weekday": int|null,
  "exercises": [...]}]}` (`backend/dzik_os/models.py` ~l. 252–256).
* `GET /api/me/today` (`backend/dzik_os/routers/today.py` l. 46–84) bierze
  najnowszy ACTIVE plan klienta, jego bieżącą wersję i **pierwszy** dzień, którego
  `weekday == local_today(user).isoweekday()`. Brak dopasowania → `workout: null`
  → ekran „Dzisiaj” pokazuje kartę „Dziś bez treningu / Regeneracja też jest częścią
  planu” (`frontend/src/pages/client/Today.tsx` l. 192–197). Klient z planem
  bez `weekday` widzi to **codziennie** — stąd zgłoszenie.
* `weekday` jest opcjonalne (`PlanDayIn.weekday: int | None`, `schemas.py` l. 95–99);
  `PlanEditor.tsx` l. 33 i 309 tworzy dni z `weekday: null`; gotowe schematy
  (`plan_templates.py` l. 94), kopie z szablonów, duplikaty i import nadają `None`.
* Klient nie ma **żadnego** sposobu, żeby to ustawić — `Plan.tsx` l. 255 tylko
  wyświetla odznakę dnia, jeśli trener ją wpisał.

Wniosek: nie budujemy nowego „harmonogramu treningów”, tylko dajemy klientowi
**własną nakładkę dni tygodnia** na plan trenera i uczymy `/api/me/today`, żeby
ją respektowało.

## 3. Rozpoznanie — fakty z kodu (zweryfikuj linie)

| Co | Gdzie | Uwaga |
|---|---|---|
| Model planu i wersji (niemutowalne wersje, `reason`) | `models.py` l. 224–262 | wersje NIGDY nie są nadpisywane — nakładka klienta nie może zmieniać `content_json` |
| Stabilne `id` dni/ćwiczeń (0.58.0) | `publikacja/elementy.py::znormalizuj` l. 73–96 | nadawane przy publikacji ze szkicu i przy duplikacji; **starsze wersje i seed mogą nie mieć `id`** → potrzebny klucz zastępczy |
| Wybór treningu na dziś | `routers/today.py` l. 46–84 | pierwszy dzień z `weekday == dziś`; `done_today` po `WorkoutSession(plan_version_id, day_index, performed_on)` |
| Oznaczanie wykonania | `Today.tsx` l. 57–64 → `POST /api/clients/{id}/workouts` z `plan_version_id`, `day_index` | zostaje bez zmian (klucz = indeks dnia w wersji) |
| Widok planu klienta | `frontend/src/pages/client/Plan.tsx` l. 250–258 | karta dnia z odznaką `WEEKDAYS[day.weekday-1]` |
| Typy | `frontend/src/types.ts` l. 51–56 (`PlanDay`), l. 418–433 (`TodayData.workout`) | |
| Wzorzec zasobu klienta z dostępem trenera (0.63.0) | `routers/habits.py` (cały), `authz.resolve_client_access(..., action="write", domain=DOMAIN_TRAINING)`, `deny` → 404 | **kopiuj ten wzorzec 1:1** (dostęp, IDOR = 404, `record_event`) |
| Macierz dostępu | `backend/tests/access_matrix.py` l. 154–166 (`/api/clients/{client_id}/plans`, `.../habits` = `CLIENT_SCOPED`) | każdą nową trasę dopisz do macierzy |
| Eksport i usunięcie konta | `routers/privacy.py` l. 359–360, 409, 618–619 (wzorzec dla `Habit`) | **nowa tabela klienta MUSI trafić do eksportu i do usuwania** — test nawyków to sprawdza, zrób tak samo |
| Migracje | `db.py` l. 1440+ (wpis 34 jako wzorzec: `CREATE TABLE IF NOT EXISTS`, indeks, przenośność na PostgreSQL — BOOLEAN default `false`, `test_migracje_przenosnosc`) | |
| Seed demo | `seed.py` l. 254–290 (plan klienta A: „Trening A — góra” pon., „Trening B — dół” śr., „Trening C — całe ciało” pt.; l. 304–318 plan FBW wt./czw./sob.) | trener ustawił tu `weekday`, więc demo dziś działa — dodaj wariant **bez** `weekday` (patrz §5 seed) |
| Ekran trenera | `pages/coach/ClientDetail.tsx` (zakładka Plan) | pokaż wybór klienta tylko do odczytu |
| Gotowe pickery dnia tygodnia do skopiowania | `pages/coach/PlanEditor.tsx` l. 408–417, `pages/coach/SzkicPlanu.tsx` l. 392–396 (`<option value="">— dowolny —</option>` + `WEEKDAYS` z `dates.ts` l. 63) | ten sam `select` u klienta |
| Ślad audytu | `hos_bridge.record_event(db, action=..., actor_id, subject_ids, payload, summary)` **przed** `db.commit()`, payload tylko nazwy pól, nigdy wartości (wzorzec `habits.py` l. 155–157) | |
| Wzorzec panelu klienta zasilanego z `/api/me/today` | `pages/nawyki/PanelNawykow.tsx` (`onZmiana={load}`) | ten sam kształt dla karty „ustaw dni” |
| Zgody | domena `training_data` (jak harmonogram i nawyki) | bez nowej bramki zgód |
| a11y / E2E | `e2e/test_a11y.mjs` (jeden `h1` na „Dzisiaj”), `frontend/e2e/nawyki.spec.ts` + `helpers.ts` jako wzorzec, strefa `Europe/Warsaw` w `playwright.config.ts` | E2E musi liczyć „dzisiejszy” dzień tygodnia dynamicznie, nie na sztywno |

## 4. Decyzje projektowe (propose-only → właściciel zatwierdził kierunek tą wiadomością)

1. **Nakładka klienta, nie edycja planu.** Wybór dni to osobny byt należący do
   klienta (`author_id` = klient albo trener), przypięty do `(client_id, plan_id)`.
   Wersje planu pozostają niemutowalne; trener nadal może wpisać `weekday` jako
   **domyślną propozycję**.
2. **Zasada pierwszeństwa — prosta i bez mieszania:** jeśli klient zapisał
   układ dla danego planu, obowiązuje **wyłącznie** jego układ (dni bez wpisu =
   nieprzypisane). Jeśli nie zapisał — obowiązują `weekday` trenera jak dziś.
   Formularz klienta startuje wstępnie wypełniony propozycją trenera.
   Powód: mieszanie dwóch źródeł per dzień daje kolizje, których nikt nie
   rozstrzygnie (dwa treningi w ten sam dzień, jeden z trenera, drugi z klienta).
3. **Klucz dnia:** `day.id`, jeśli wersja go ma; w przeciwnym razie `idx:<indeks>`.
   Klucz wyliczany jedną czystą funkcją i użyty wszędzie (API, `today`, front).
   Gdy trener opublikuje nową wersję: wpisy z nieistniejącym już kluczem są
   ignorowane, a klient widzi na Planie i na „Dzisiaj” łagodną notkę „Plan
   się zmienił — sprawdź dni tygodnia” (bez czerwieni, bez blokady).
4. **Walidacja:** `weekday` 1–7 albo brak (dzień wolny od tej jednostki); jeden
   dzień tygodnia może mieć **co najwyżej jedną** jednostkę (duplikat → 422
   z czytelnym komunikatem po polsku); klucz spoza bieżącej wersji planu → 422.
5. **Dostęp:** klient — swoje; trener — aktywna relacja + zgoda `training_data`
   (odczyt i zapis, żeby mógł pomóc klientowi na konsultacji); obcy klient / obcy
   plan → 404 logowane (`deny`). AGENT/SERVICE nie dotyczy (brak takich ról tutaj).
6. **Ślad:** `record_event(action="PLAN_WEEKDAYS_SET", ...)` z `plan_id` i liczbą
   przypisanych dni (bez treści planu). Historia: kolejny zapis nadpisuje układ
   (to preferencja, nie plan — nie wersjonujemy), ale zdarzenie audytu zostaje.
7. **Zero AI, zero rekomendacji.** System nie proponuje „lepszych” dni. Jedyny
   automatyzm to prefill z propozycji trenera.
8. **Human OS / INTENDED_PURPOSE:** dane = wybór dnia tygodnia dla jednostki
   treningowej; brak treści zdrowotnej; klient pozostaje autorem swojego tygodnia.
   Bez pytania do foundera.

## 5. Co dokładnie zbudować

### Backend

* **Moduł czystych funkcji `dzik_os/dni_treningowe.py`:**
  `klucz_dnia(day, idx) -> str`, `uklad_efektywny(content, wybor|None) ->
  dict[klucz, weekday|None]`, `dzien_na_dzis(content, wybor|None, weekday) ->
  (idx, day) | None`, `klucze_nieaktualne(content, wybor) -> list[str]`.
  Testy jednostkowe na przykładach ręcznych (prefill z trenera, nakładka wygrywa
  w całości, duplikat, klucz zastępczy `idx:`, klucz nieaktualny).
* **Model `PlanWeekdayChoice`** (jeden wiersz per `(client_id, plan_id)`,
  `UniqueConstraint`): `id`, `client_id`, `plan_id`, `choices_json`
  (`[{"day_key": "...", "weekday": 1..7|null}]`), `author_id`, `author_note|null`,
  `created_at`, `updated_at`, `version`. **Migracja 37** (patrz rezerwacje).
* **API** (prefix `/api`, plik `routers/plan_weekdays.py`, rejestracja w `main.py`,
  wiersze w `access_matrix.py`):
  * `GET /api/clients/{client_id}/plans/{plan_id}/dni` → `{plan_id, version_no,
    source: "client"|"coach"|"none", days: [{day_key, day_index, name,
    coach_weekday, weekday}], stale_keys: [...]}`
  * `PUT /api/clients/{client_id}/plans/{plan_id}/dni` body `{choices: [...],
    author_note?}` → to samo co GET po zapisie; walidacja z §4 pkt 4.
  * `DELETE …/dni` → wraca do propozycji trenera (`source: "coach"`).
* **`/api/me/today`:** zamiast pętli po `weekday` użyj `dzien_na_dzis(...)`; dołóż
  do `workout` pole `weekday_source: "client"|"coach"` i do odpowiedzi
  `workout_hint: {"kind": "no_weekdays"|"stale", "plan_id": ...} | null`, żeby
  front mógł pokazać „Ustaw dni tygodnia” zamiast „Dziś bez treningu”, gdy plan
  istnieje, ale nie ma żadnego przypisania.
* **Prywatność:** `privacy.py` — eksport (`"plan_weekday_choices"`, podbij
  `export_version` z `"1.8"` na `"1.9"` i popraw test, który go sprawdza) i usunięcie
  konta (delete po `client_id`), + test jak w `test_habits.py`.
* **Seed:** **bez zmian w istniejących planach demo** (klient A pon./śr./pt.,
  klient B wt./czw./sob. — inne testy na nich polegają). Stan „plan bez dni”
  tworzysz w teście przez API trenera (`POST /api/plans` z `weekday: null` dla
  klienta z `create_activated_client`). Nie dokładaj klientom demo drugiego
  planu ACTIVE — `today` bierze najnowszy ACTIVE i zmieniłoby to inne testy.
* **Flaga:** bez flagi (jak nawyki 0.63.0 — dodatek UI klienta + tabela
  addytywna; właściciel 14.09: nowe funkcje mają być widoczne).

### Frontend

* **`pages/client/Plan.tsx`:** nad listą dni karta „Twoje dni treningowe” —
  dla każdej jednostki `select` pon.–niedz./„—”, prefill z propozycji trenera,
  przycisk „Zapisz dni”, komunikat sukcesu, błąd 422 pokazany przy polu, link
  „Wróć do propozycji trenera” (DELETE). Odznaka przy dniu: „pon. (Twój wybór)”
  albo „pon. (propozycja trenera)”. Notka o nieaktualnych kluczach (§4 pkt 3).
* **`pages/client/Today.tsx`:** gdy `workout_hint.kind === "no_weekdays"` — karta
  „Masz plan, ale nie wybrałeś dni tygodnia” z linkiem do Planu; gdy
  `workout` jest — mała etykieta źródła („Twój wybór” / „propozycja trenera”).
  Reszta karty (ćwiczenia, „Wykonane ✓”) bez zmian.
* **`pages/coach/ClientDetail.tsx` (zakładka Plan):** tylko do odczytu: przy
  każdej jednostce dzień wg klienta, jeśli ustawił; bez edycji w tej rundzie.
* **`types.ts`:** rozszerz `TodayData.workout` i dodaj typy odpowiedzi `/dni`.

### Testy

* `backend/tests/test_dni_treningowe.py` (silnik + API): zapis i odczyt,
  prefill z trenera, nakładka wygrywa w całości, duplikat dnia → 422, klucz spoza
  wersji → 422, `weekday` 0/8 → 422, obcy klient → 404 (IDOR), trener z relacją
  i zgodą → 200, trener bez zgody treningowej → jak w `test_habits.py`, `today`
  bez wyboru = dzień trenera, `today` z wyborem = dzień klienta, `today` bez
  niczego = `workout: null` + `workout_hint.no_weekdays`, nowa wersja planu z tymi
  samymi `id` zachowuje wybór, usunięty dzień → `stale_keys`, eksport i usunięcie
  konta, wpis audytu `PLAN_WEEKDAYS_SET`.
* Macierz dostępu (`test_access_matrix.py`) zielona z nowymi wierszami.
* E2E `frontend/e2e/dni-treningowe.spec.ts` (na **kliencie B** — A jest
  współdzielony między specami; wzorzec `nawyki.spec.ts`: `zaloguj`, `data-testid`,
  `page.reload()` jako dowód zapisu po stronie serwera): Plan → w karcie „Twoje
  dni treningowe” ustawia **dzisiejszy** dzień tygodnia (liczony z `new Date()`
  w strefie `Europe/Warsaw` jak `raport.spec.ts`) dla jednostki „FBW 1”, pozostałe
  na „—” → „Zapisz dni” → reload → „Dzisiaj” pokazuje „FBW 1” i etykietę „Twój
  wybór”; potem „Wróć do propozycji trenera” → odznaki znów „propozycja trenera”.
  Drugi scenariusz: duplikat dnia → komunikat przy polu, nic nie zapisane.
  Stan „plan bez dni” pokrywa test API (nie E2E).

### Dokumentacja (etap zamknięcia)

`CHANGELOG.md` 0.66.0, `INSTRUKCJA_KLIENTA.md` (§ „Ekran Dzisiaj” i § Plan),
`INSTRUKCJA_TRENERA.md` (co widzi trener), `PERMISSIONS.md` (nowe trasy),
`RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md` §1/§2, plan sesji („Odstępstwa”,
„Weryfikacja wykonana”). `docs/dni-treningowe/00_rozpoznanie.md` i `PROGRESS.md`
jak w `docs/nawyki/`.

## 6. Czego świadomie NIE robimy

* Nie edytujemy `content_json` żadnej wersji planu i nie tworzymy nowej wersji
  „z dniami” — to nie jest zmiana planu trenera.
* Nie wpinamy tego w Harmonogram (`ScheduleItem`, kategoria TRENING) — to
  przypomnienia, inny byt; dublowanie = dwa mechanizmy na stałe.
* Nie dodajemy powiadomień push o treningu „na dziś” (osobna decyzja).
* Nie pozwalamy na dwie jednostki w jeden dzień ani na tygodnie A/B — v1 to
  jeden tydzień. Jeśli właściciel zechce rotację, to nowa runda.
* Nie zmieniamy `POST /api/clients/{id}/workouts` ani klucza `day_index`.

## 7. Weryfikacja przed przekazaniem (z korzenia repozytorium)

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q                     # Core: 275 zielonych
python apps/dzik-os/tools/spojnosc.py
python apps/dzik-os/tools/mutacje.py
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers
```

Plus **uruchomienie i obejrzenie** (`ZASADA_URUCHOMIENIA.md`): przez serwer E2E
zaloguj klienta z planem bez dni, ustaw dzisiejszy dzień, wróć na „Dzisiaj”,
zrób zrzut. W raporcie napisz, CO KLIKNĄŁEŚ I CO ZOBACZYŁEŚ — nie „sprawdzone”.
Przegląd: 3 recenzentów wsadowo (bezpieczeństwo/zgody, poprawność silnika
i `today`, testy/UX/treść), P0/P1 naprawione przed przekazaniem, P2 do
`docs/dni-treningowe/PROGRESS.md`. Bezpiecznik: 3× plan.

## 8. Pytania do właściciela (odpowiedz w tej wiadomości albo zostaw domyślne)

1. Czy trener ma móc **edytować** wybór klienta z karty klienta? *Domyślnie:
   tak (relacja + zgoda), bo tak jest z nawykami i harmonogramem.*
2. Czy dopuszczamy dwie jednostki tego samego dnia? *Domyślnie: nie (422).*
3. Gdy klient nie wybrał dni, a trener też nie — „Dzisiaj” ma pokazywać
   pierwszą jednostkę planu „na zachętę”, czy tylko kartę „ustaw dni”?
   *Domyślnie: tylko kartę „ustaw dni” — system nie zgaduje za człowieka.*

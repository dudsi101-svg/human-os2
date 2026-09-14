# Plan sesji: dni treningowe na „Dzisiaj” (0.71.0, migracja 38)

**Gałąź:** `agent/dni-treningowe` (od `main` = `04d1d58`, po 0.69.0 + scalony PR #71
„rozpoznanie wywiadu kalorycznego”, tylko dokument). **Rola:** podległa sesja pisząca
wyznaczona przez integratora 14.09.2026 — polecenie właściciela z 14.09 („klient
posiadający już plan na tydzień od trenera nie ma żadnej informacji, w jaki dzień realizuje
jego części — niech wybierze dni tygodnia; trening z konkretnego dnia ma pojawić się
w zakładce „Dziś””), pakiet `docs/zlecenia/README.md` (zlecenie 1) i prompt
`PROMPT_writer_dni-treningowe.md` (diagnoza, rozpoznanie, decyzje, zakres).

**Uwaga o protokole jednego piszącego:** w chwili startu istnieją dwa otwarte PR-y
`[WRITER]` — #70 (`agent/powitanie-samouczek`, 0.70.0, w scalaniu przez integratora) i #67
(`agent/landing-czerwony`, czeka na decyzje właściciela). Integrator wyznaczył tę sesję
jawnie z wiedzą o obu — to wyjątek integratora, nie kolizja. Sesja pisze wyłącznie na
własnej gałęzi i nie dotyka plików tamtych gałęzi poza plikami współdzielonymi wymienionymi
niżej (`Today.tsx`, `today.py`, `CHANGELOG.md`, `db.py`); przy scaleniu `main` obie zmiany
z #70 (dialog powitalny w `Today.tsx`, pole `welcome_seen` w `/api/me/today`) zostają.

**Rezerwacje (KOORDYNACJA §0, sprawdzone na żywo 14.09 w `db.py`, `CHANGELOG.md`,
`STAN_PRZEKAZANIA.md` §2 i liście PR-ów):**

* **wersja 0.71.0** — `main` ma 0.69.0; 0.70.0 = PR #70 (powitanie po pierwszym
  logowaniu, w trakcie scalania). Sekcja 0.71.0 wchodzi NA GÓRĘ `CHANGELOG.md`; jeśli
  przy scaleniu `main` pojawi się 0.70.0, sekcja 0.71.0 zostaje nad nią (kontrola
  `changelog` wymaga wersji rosnących w kolejności scalania). Pakiet rezerwował 0.68.0 —
  numer skorygowany przez integratora; tabela w `docs/zlecenia/README.md` do poprawienia
  w tej rundzie.
* **migracja 38** (addytywna: `plan_weekday_choices`). Ostatni wpis w `db.py` na `main`
  to **36** (postępy); **37 = `users.welcome_seen_at` z PR #70** (jeszcze nie w `main`
  w chwili startu — numer należy do #70, nie do tej gałęzi). Pakiet rezerwował 37 —
  skorygowane przez integratora.
* **`export_version`** w `routers/privacy.py` jest dziś **„1.9”** (po postępach 0.66.0) —
  podbijam na **„2.0”** i poprawiam cztery testy, które ją sprawdzają
  (`test_onboarding.py:948`, `test_postepy_api.py:294`, `test_zapotrzebowanie_api.py:223`,
  `test_habits.py:134`). Prompt mówił o 1.8→1.9 — nieaktualne.

**Pliki współdzielone (zmieniam jawnie):** `models.py` (klasa na końcu), `db.py` (wpis 38),
`main.py` (rejestracja routera), `tests/access_matrix.py` (nowe wiersze), `routers/today.py`,
`routers/privacy.py` (eksport + usuwanie), `types.ts` (`TodayData`, typy `/dni`),
`Today.tsx`, `Plan.tsx`, `ClientDetail.tsx` (PlanTab, tylko odczyt), `CHANGELOG.md`,
`RELEASE_STATUS.md`, `PERMISSIONS.md`, `INSTRUKCJA_KLIENTA.md`, `INSTRUKCJA_TRENERA.md`,
`STAN_PRZEKAZANIA.md` §1/§2, `docs/zlecenia/README.md` (tabela rezerwacji).

**Pliki nowe:** `backend/dzik_os/dni_treningowe.py`, `backend/dzik_os/routers/plan_weekdays.py`,
`backend/tests/test_dni_treningowe.py`, `frontend/e2e/dni-treningowe.spec.ts`,
`frontend/src/pages/client/DniTreningowe.tsx` (karta „Twoje dni treningowe”),
`docs/dni-treningowe/00_rozpoznanie.md`, `docs/dni-treningowe/PROGRESS.md`, ten plan.

## Co robimy

1. **Nakładka dni tygodnia klienta** na plan trenera: `PlanWeekdayChoice` (jeden wiersz per
   klient × plan, `choices_json` = lista `{day_key, weekday|null}`), API
   `GET/PUT/DELETE /api/clients/{client_id}/plans/{plan_id}/dni`.
2. **„Dzisiaj” respektuje nakładkę:** `dzien_na_dzis(content, wybor, weekday)` zamiast pętli
   po `weekday` trenera; `workout.weekday_source` i `workout_hint` (plan bez dni → karta
   „ustaw dni” zamiast „Dziś bez treningu”; nieaktualne klucze → notka „plan się zmienił”).
3. **UI klienta:** karta „Twoje dni treningowe” w zakładce Plan (prefill z propozycji trenera,
   zapis, powrót do propozycji), etykiety źródła na Planie i na „Dzisiaj”.
4. **UI trenera:** dzień wg klienta tylko do odczytu w karcie klienta (zakładka Plan).

## Decyzje projektowe (właściciel 14.09 + wykonawcze)

* **Wersje planu niemutowalne** — nakładka nigdy nie dotyka `content_json`; trener nadal
  wpisuje `weekday` jako propozycję.
* **Bez mieszania źródeł:** zapisany układ klienta obowiązuje w całości; brak układu →
  propozycja trenera. Prefill formularza z propozycji trenera.
* **Klucz dnia:** `day.id` (stabilne `id` z publikacji 0.58.0) albo `idx:<n>` dla wersji
  bez `id` (seed, starsze wersje). Klucze nieaktualne po nowej wersji → ignorowane + łagodna
  notka „Plan się zmienił — sprawdź dni” (bez czerwieni, bez blokady).
* **Walidacja:** `weekday` 1–7 albo null; jeden dzień tygodnia = maks. jedna jednostka (422
  po polsku); klucz spoza bieżącej wersji (422); zduplikowany `day_key` w body (422).
* **Dostęp:** jak nawyki i harmonogram — klient swoje; trener z relacją i zgodą
  `training_data` (odczyt i zapis przez API); obcy klient / plan innego klienta / szablon →
  404 (`deny`, logowane). Bez nowej bramki zgód.
* **Ślad:** `PLAN_WEEKDAYS_SET` / `PLAN_WEEKDAYS_CLEARED` (payload: `plan_id`, liczba
  przypisanych dni, `author_id` — bez treści planu). Preferencja nadpisywana (kolejny PUT
  zastępuje układ), zdarzenie audytu zostaje.
* **Zero AI, zero rekomendacji dni.** Jedyny automatyzm to prefill z propozycji trenera.
  Bez flagi (jak 0.63.0 — właściciel 14.09: nowe funkcje mają być widoczne).

## Przyjęte domyślne odpowiedzi na pytania §8 promptu (właściciel nie odpowiedział)

| # | Pytanie | Przyjęte |
|---|---|---|
| 1 | Czy trener może edytować wybór klienta z karty klienta? | **API dopuszcza zapis trenera** (relacja + zgoda `training_data`, jak nawyki); **w UI trenera w tej rundzie tylko odczyt** (dzień wg klienta przy jednostce) |
| 2 | Dwie jednostki tego samego dnia? | **nie — 422** z komunikatem po polsku |
| 3 | Plan bez dni u trenera i klienta | **tylko karta „ustaw dni”** na „Dzisiaj” (`workout: null` + `workout_hint.kind = "no_weekdays"`); system nie zgaduje za człowieka |

Jeśli właściciel odpowie inaczej, zmiana jest lokalna: (1) formularz w PlanTab trenera na
tym samym komponencie; (2) zdjęcie jednej kontroli w `plan_weekdays.py` i teście;
(3) dodatkowa gałąź w `dzien_na_dzis`.

## Test INTENDED_PURPOSE §2/§3

Dane = wybór dnia tygodnia dla jednostki treningowej (liczba 1–7 albo brak) przypięty do
planu. Brak treści zdrowotnej, brak interpretacji, brak oceny — to preferencja
organizacyjna, jak dni tygodnia w harmonogramie i nawykach (domena `training_data`).
Klient pozostaje autorem swojego tygodnia; trener widzi wybór, ale system nie proponuje
„lepszych” dni. Bez wątpliwości — bez pytania do foundera.

## Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Czytam (z hipotezą) | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 rozpoznanie | linie z promptu zweryfikowane: `today.py` 46–84 (pętla po `weekday`), `models.py` 224–262, `elementy.py::znormalizuj` 73–96, `habits.py` (cały), `privacy.py` 361–362/415–416/626–627, `access_matrix.py` 162/171–174, `Plan.tsx` 250–258, `Today.tsx` 156–197, `PlanEditor.tsx` 408–417, `test_access_matrix._fill_path` (obce `{plan_id}` → nieistniejący id → 404 wymagane) | `docs/dni-treningowe/00_rozpoznanie.md` + ten plan | — | dziesiątki tys. |
| 1 silnik | — | `dzik_os/dni_treningowe.py`: `klucz_dnia`, `uklad_efektywny`, `dzien_na_dzis`, `klucze_nieaktualne`, `waliduj_wybor` | `tests/test_dni_treningowe.py::TestSilnik` na przykładach ręcznych (prefill, nakładka wygrywa w całości, duplikat, `idx:`, klucz nieaktualny) | dziesiątki tys. |
| 2 model + migracja 38 | `models.py`, `db.py` (wpis 34 jako wzorzec, przenośność) | `PlanWeekdayChoice`, migracja addytywna | `test_migracje_przenosnosc`, `test_db_migracje` | dziesiątki tys. |
| 3 API + `today` + prywatność | `routers/today.py`, `routers/habits.py`, `routers/privacy.py` | `routers/plan_weekdays.py`, zmiana `today.py`, eksport/usuwanie (`export_version` 2.0), macierz dostępu, testy API | pytest modułu + macierz + 4 testy `export_version` | setki tys. |
| 4 UI | `Plan.tsx`, `Today.tsx`, `ClientDetail.tsx` (PlanTab), `PanelNawykow.tsx`, `types.ts`, `dates.ts` | `DniTreningowe.tsx` (karta), zmiany w `Plan.tsx`/`Today.tsx`/`ClientDetail.tsx`/`types.ts`; E2E `dni-treningowe.spec.ts` (klient B, dzisiejszy dzień liczony dynamicznie w `Europe/Warsaw`) | `tsc`, build (budżet), `test:helpers`, E2E `dni-treningowe nawyki --project=telefon` (porty 8096/8106, katalog `/tmp/dzik-e2e-8096`), a11y (jeden `h1`), PWA offline, obejrzenie przez serwer E2E ze zrzutami | setki tys. (największy koszt) |
| 5 zamknięcie | — | CHANGELOG 0.71.0, RELEASE_STATUS, PERMISSIONS, INSTRUKCJA_KLIENTA/TRENERA, STAN_PRZEKAZANIA §1/§2, `docs/zlecenia/README.md`, `docs/dni-treningowe/PROGRESS.md` | pełny pytest, ruff z korzenia, Core 275, `spojnosc.py`, `mutacje.py`, `mutacje_bezpieczenstwa.py`, 3 recenzentów, scalenie `main` | dziesiątki tys. |

**Największy koszt:** etap 4. Taniej bez utraty informacji: jeden `select` skopiowany
z `PlanEditor.tsx`, karta na „Dzisiaj” w kształcie `PanelNawykow` (odświeżanie przez
`onZmiana={load}`), brak osobnego ekranu. Bezpiecznik: 3× plan. Przegląd: 3 recenzentów
wsadowo (bezpieczeństwo/zgody/IDOR, poprawność silnika i `today`, testy/UX/treść), P0/P1
naprawione przed przekazaniem, P2 do `docs/dni-treningowe/PROGRESS.md`.

## Czego nie dotykam

`content_json` wersji planu, `POST /api/clients/{id}/workouts` i klucz `day_index`,
Harmonogram (`ScheduleItem`), powiadomienia push, dieta, monitoring, seed (istniejące plany
demo klienta A pon./śr./pt. i klienta B wt./czw./sob. — inne testy na nich polegają; stan
„plan bez dni” tworzę w teście przez API trenera na nowym kliencie), Core Human OS, pliki
gałęzi #67 i #70 poza współdzielonymi wymienionymi wyżej.

## Czego świadomie nie robię

Dwie jednostki w jeden dzień, tygodnie A/B (rotacja), edycja wyboru klienta przez trenera
z osobnego ekranu (tylko odczyt w tej rundzie), przypomnienia o treningu „na dziś”, nowa
wersja planu „z dniami”, wpinanie w Harmonogram.

## Odstępstwa od planu

⟨uzupełnia sesja pisząca⟩

## Weryfikacja wykonana

⟨uzupełnia sesja pisząca: co uruchomiono i co zobaczono — nie „sprawdzone”⟩

## Plan kontra rzeczywistość (zasady v2 §5)

⟨uzupełnia sesja pisząca⟩

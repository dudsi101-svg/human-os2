# Plan sesji: dni treningowe — klient wybiera dni tygodnia dla jednostek planu; „Dzisiaj” pokazuje trening z dzisiejszego dnia (0.66.0)

> SZKIC WŁAŚCICIELA — sesja pisząca kopiuje go do `docs/plan-sesji/dni-treningowe.md`
> jako pierwszy commit gałęzi, po uzupełnieniu rezerwacji sprawdzonych na żywo
> (pola oznaczone `⟨…⟩`).

**Gałąź:** `agent/dni-treningowe` (od `main` = ⟨sha⟩, po ⟨wersja main⟩). **Rola:** aktywny
piszący — polecenie właściciela z 14.09.2026 („klient posiadający już plan na tydzień od
trenera nie ma żadnej informacji, w jaki dzień realizuje jego części — niech wybierze dni
tygodnia; trening z konkretnego dnia ma pojawić się w zakładce „Dziś””), plik
`PROMPT_writer_dni-treningowe.md` (diagnoza, rozpoznanie, decyzje, zakres).
**Rezerwacje (KOORDYNACJA §0):** wersja ⟨wg kolejności scalania, `docs/zlecenia/README.md`⟩, migracja **37** (addytywna:
`plan_weekday_choices`) — ⟨potwierdzone w `db.py` / `CHANGELOG.md` / `STAN_PRZEKAZANIA.md` §2
dnia ⟨data⟩; jeśli 35/36 zostały scalone albo przesunięte, numery skorygowane tutaj i w §2⟩.
Pliki współdzielone: `models.py` (klasa na końcu), `db.py` (wpis 37), `main.py` (rejestracja
routera), `access_matrix.py`, `routers/today.py`, `routers/privacy.py`, `types.ts`
(`TodayData`), `CHANGELOG.md`. Kolejność scalania: po `agent/biblioteka-diet` i
`agent/monitoring-postepy`, jeśli będą gotowe wcześniej; w przeciwnym razie niezależnie
(zadanie nie dotyka diety ani monitoringu).

## Co robimy

1. **Nakładka dni tygodnia klienta** na plan trenera: `PlanWeekdayChoice` (jeden wiersz per
   klient × plan, `choices_json` = lista `{day_key, weekday|null}`), API
   `GET/PUT/DELETE /api/clients/{client_id}/plans/{plan_id}/dni`.
2. **„Dzisiaj” respektuje nakładkę:** `dzien_na_dzis(content, wybor, weekday)` zamiast pętli
   po `weekday` trenera; `workout.weekday_source` i `workout_hint` (plan bez dni → karta
   „ustaw dni” zamiast „Dziś bez treningu”).
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
  notka „Plan się zmienił — sprawdź dni”.
* **Walidacja:** `weekday` 1–7 albo null; jeden dzień tygodnia = maks. jedna jednostka (422);
  klucz spoza bieżącej wersji (422).
* **Dostęp:** jak nawyki i harmonogram — klient swoje; trener z relacją i zgodą
  `training_data` (odczyt i zapis); obcy → 404 (`deny`). Bez nowej bramki zgód.
* **Ślad:** `PLAN_WEEKDAYS_SET` / `PLAN_WEEKDAYS_CLEARED` (payload: `plan_id`, liczba
  przypisanych dni — bez treści planu). Preferencja nadpisywana, zdarzenie zostaje.
* **Zero AI, zero rekomendacji dni.** Bez flagi (jak 0.63.0).
* **INTENDED_PURPOSE:** wybór dnia tygodnia = dane treningowe bez treści zdrowotnej;
  klient autorem swojego tygodnia. Bez pytania do foundera.

## Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Czytam (z hipotezą) | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 rozpoznanie | linie wskazane w prompcie (`today.py` 46–84, `models.py` 224–262, `elementy.py::znormalizuj`, `habits.py`, `privacy.py` 359–410/618, `access_matrix.py`, `Plan.tsx` 250–258, `Today.tsx` 156–197, `PlanEditor.tsx` 408–417) — tylko weryfikacja, bez ponownego rozpoznania | `docs/dni-treningowe/00_rozpoznanie.md` + ten plan | — | dziesiątki tys. |
| 1 silnik | — | `dzik_os/dni_treningowe.py`: `klucz_dnia`, `uklad_efektywny`, `dzien_na_dzis`, `klucze_nieaktualne` | `tests/test_dni_treningowe_silnik.py` na przykładach ręcznych | dziesiątki tys. |
| 2 model + migracja 37 | `models.py`, `db.py` (wpis 34 jako wzorzec) | `PlanWeekdayChoice`, migracja przenośna | `test_migracje_przenosnosc` | dziesiątki tys. |
| 3 API + `today` + prywatność | `routers/today.py`, `routers/habits.py`, `routers/privacy.py` | `routers/plan_weekdays.py`, zmiana `today.py`, eksport/usuwanie, macierz dostępu, `tests/test_dni_treningowe.py` | pytest modułu + macierz + prywatność | setki tys. |
| 4 UI | `Plan.tsx`, `Today.tsx`, `ClientDetail.tsx` (Plan), `PanelNawykow.tsx`, `types.ts`, `dates.ts` | karta „Twoje dni treningowe”, karta „ustaw dni” na „Dzisiaj”, etykiety źródła, widok trenera; E2E `dni-treningowe.spec.ts` (klient B) | `tsc`, build (budżet 120 kB), `test:helpers`, E2E, a11y (jeden `h1`), obejrzenie przez serwer E2E | setki tys. (największy koszt) |
| 5 zamknięcie | — | CHANGELOG 0.66.0, RELEASE_STATUS, PERMISSIONS, INSTRUKCJA_KLIENTA/TRENERA, STAN_PRZEKAZANIA §1/§2, `docs/dni-treningowe/PROGRESS.md` | pełny pytest, ruff z korzenia, spójność, mutacje, CI | dziesiątki tys. |

**Największy koszt:** etap 4. Taniej bez utraty informacji: jeden `select` skopiowany
z `PlanEditor.tsx`, karta na „Dzisiaj” w kształcie `PanelNawykow` (odświeżanie przez
`onZmiana={load}`), brak osobnego ekranu. Bezpiecznik: 3× plan. Przegląd: 3 recenzentów
wsadowo (bezpieczeństwo/zgody, poprawność silnika i `today`, testy/UX/treść), P0/P1
naprawione przed przekazaniem, P2 do `docs/dni-treningowe/PROGRESS.md`.

## Czego nie dotykam

`content_json` wersji planu, `POST /api/clients/{id}/workouts` i klucz `day_index`,
Harmonogram (`ScheduleItem`), powiadomienia push, dieta, monitoring, Core Human OS.

## Czego świadomie nie robię

Dwie jednostki w jeden dzień, tygodnie A/B (rotacja), edycja wyboru klienta przez trenera
z osobnego ekranu (tylko odczyt w tej rundzie — chyba że właściciel odpowie inaczej na
pytanie 1 promptu), przypomnienia o treningu „na dziś”.

## Odstępstwa od planu

⟨uzupełnia sesja pisząca⟩

## Weryfikacja wykonana

⟨uzupełnia sesja pisząca: co uruchomiono i co zobaczono — nie „sprawdzone”⟩

## Plan kontra rzeczywistość (zasady v2 §5)

⟨uzupełnia sesja pisząca⟩

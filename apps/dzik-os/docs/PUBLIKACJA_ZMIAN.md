# Panel trenera: pełna edycja, usuwanie i publikowanie zmian (0.58.0) — raport wdrożenia

**Źródło:** specyfikacja właściciela „Panel trenera: pełna edycja, usuwanie
i publikowanie zmian” (13.09.2026). Runda: gałąź
`agent/panel-trenera-publikacja`, plan sesji
`docs/plan-sesji/panel-trenera-publikacja.md`.

## 1. Inwentaryzacja miejsc dodawania elementów i co się zmieniło

| Miejsce | Przed 0.58.0 | Po 0.58.0 |
|---|---|---|
| Plan treningowy klienta (karta klienta → Plan) | nowa wersja pełnym formularzem = od razu widoczna + powiadomienie; brak usuwania elementów, kolejności, archiwizacji | **Edytuj (szkic)** → autozapis → Sprawdź zmiany → Opublikuj zmiany i powiadom; menu działań na dniu i ćwiczeniu (edycja, duplikacja, wyżej/niżej, przeniesienie do innego dnia, usunięcie z „Cofnij”); Duplikuj / Odepnij od klienta / Archiwizuj; lista opublikowanych zmian ze stanem doręczenia i odczytu |
| Szablony treningowe (Szablony → Trening) | tylko dodawanie i kopia do klienta — **bez edycji i usuwania** | ten sam edytor szkicu (publikacja bez powiadomienia), Duplikuj, Archiwizuj (= usunięcie z listy, historia zostaje); pochodzenie kopii zapisane na wersji v1 klienta |
| Dieta klienta (karta klienta → Dieta) | nowa wersja formularzem tekstowym | szkic z osobnymi kartami sekcji, posiłków i suplementów (edycja, kolejność, duplikacja, usunięcie z „Cofnij”), cele dzienne w korzeniu; Duplikuj / Odepnij / Archiwizuj; posiłki z kreatora dań: ręczna zmiana oznaczona, wartości skasowane |
| Szablony diety | PUT/DELETE istniały | pochodzenie kopii (`source_template_id`) na wersji v1 klienta |
| Harmonogram | dodanie, wstrzymaj/wznów/zakończ | `PUT /api/schedule/{id}` (treść, pora, dni, instrukcja, autor zalecenia) z kontrolą wersji (409) |
| Cele | dodanie, status | `PUT /api/clients/{id}/goals/{goal_id}` (tytuł, opis, rodzaj, termin) |
| Klient: plan / dieta | brak informacji o zmianach | wpis w centrum „Trener zaktualizował Twój plan… Zobacz zmiany.”, ekran `/zmiany/{id}`, baner „Dostępna nowsza wersja — Wczytaj zmiany” bez nadpisywania otwartego zapisu treningu, link „Zobacz zmiany” przy wersji |

Model własności: plan (`TrainingPlan`/`NutritionPlan`) należy do trenera
(`coach_id`) i wskazuje klienta; wersje są niemutowalne; kopia z szablonu
była już niezależna (pełna kopia treści) — dołożono jedynie zapis
pochodzenia. Zapisy wykonania (`WorkoutSession.plan_version_id`) już
wskazywały wersję — to jest `ExecutionRecord` ze specyfikacji.

## 2. Kontrakt danych (migracja 30)

| Encja specyfikacji | Implementacja |
|---|---|
| PlanAssignment | istniejące `TrainingPlan` / `NutritionPlan` (klient, trener, `current_version_no`, status ACTIVE / ARCHIVED / **UNASSIGNED**) |
| PlanVersion | istniejące wersje + `source_template_id`, `source_template_version_no` |
| PlanDraft | `plan_drafts`: rodzaj, plan, klient, trener, wersja bazowa, migawka bazowa z `id`, treść, rewizja, stan ACTIVE/PUBLISHED/DISCARDED |
| ChangeSet | `change_sets`: stara/nowa wersja, różnice (JSON), podsumowanie, notatka, autor, czas, `notification_id` |
| OutboxEvent | `outbox_events`: PLAN_PUBLISHED, odbiorca, ładunek, PENDING/DELIVERED/FAILED, próby, następna próba, ostatni błąd; UNIQUE(event_type, aggregate_id, recipient_id) |
| ClientNotification | istniejące `Notification` z `dedup_key=changeset:{id}` (UNIQUE per użytkownik), `url=/zmiany/{id}`, `read_at` |
| ExecutionRecord | istniejące `WorkoutSession` (`plan_version_id`) |

Stabilne `id` elementów (`ELM-…`): nadawane przy pierwszym szkicu
(migawka bazowa i treść współdzielą `id`), utrwalane w publikowanej
wersji; duplikacja dostaje nowe. Istniejące wersje pozostają wersją
początkową — migracja nie tworzy szkiców, zdarzeń ani powiadomień.

## 3. API

| Operacja | Trasa | Uwagi |
|---|---|---|
| utwórz/pobierz szkic | `POST /api/szkice/plan/{training\|nutrition}/{plan_id}` | 201 nowy / 200 istniejący; wersja bazowa z serwera |
| aktywny szkic (bez tworzenia) | `GET /api/szkice/plan/{kind}/{plan_id}/aktywny` | znacznik w panelu |
| zmień szkic | `PATCH /api/szkice/{id}` `{revision, operations[]}` | `set` (pola elementu albo korzenia), `add` (z `index`, przyjmuje dawne `id` — „Cofnij”), `delete`, `move` (także `parent_id`), `duplicate`, `replace`; 409 `REVISION_CONFLICT`, 422 niedozwolone pola |
| usuń element | `DELETE /api/szkice/{id}/elementy/{element_id}?revision=` | odpowiedź niesie usunięty element z zawartością i pozycją |
| różnice | `GET /api/szkice/{id}/roznice` | dodane/zmienione/usunięte/przestawione/korzeń, podsumowanie, `stale_base` |
| publikuj | `POST /api/szkice/{id}/publikuj` `{revision, base_version_no, note, idempotency_key}` | jedna transakcja; 409 `BASE_VERSION_CONFLICT`; `published:false` przy braku różnic; 422 pusty plan („zakończ archiwizacją”) |
| odrzuć szkic | `DELETE /api/szkice/{id}?revision=` | |
| zmiany planu | `GET /api/plany/{kind}/{plan_id}/zmiany` | klient i trener z dostępem |
| zobacz zmiany | `GET /api/zmiany/{changeset_id}` | klient nie widzi stanu doręczenia; trener tak |
| archiwizuj / odepnij / duplikuj | `POST /api/plans/{id}/…`, `POST /api/nutrition/{id}/…` | |
| edycja harmonogramu / celu | `PUT /api/schedule/{id}`, `PUT /api/clients/{cid}/goals/{gid}` | |
| oznacz przeczytanie | istniejące `POST /api/notifications/{id}/read` | wyłącznie właściciel wpisu |

Wszystkie operacje: własność planu + relacja trener–klient + zgoda
domeny po stronie serwera (`resolve_client_access`); cudzy plan = 404
z wpisem odmowy w audycie. Notatki wewnętrzne trenera nie istnieją jako
pole — notatka publikacji jest z założenia dla klienta.

## 4. Publikacja i powiadomienie

1. Transakcja: uprawnienia → rewizja szkicu → `current_version_no ==
   base_version_no` → walidacja treści tymi samymi schematami co dotąd
   → różnice (brak = koniec bez wersji) → nowa wersja (powód =
   podsumowanie + notatka) → ChangeSet → `current_version_no` + nazwa
   planu → OutboxEvent (tylko plan z klientem) → ślad Wiedzy
   (`plan_change`, jak dotąd) → audyt `PLAN_PUBLISHED` → wynik pod
   kluczem idempotencji → commit. Błąd w dowolnym kroku = rollback: brak
   wersji, ChangeSetu i zdarzenia (A12).
2. Outbox: próba od razu po commicie i w każdym ticku pętli przypomnień
   (co minutę) dla PENDING z `next_attempt_at <= now`; odstęp 2^n minut,
   po 10 próbach FAILED (widoczne w bazie; brak automatycznego alarmu —
   ograniczenie). Wpis centrum przez `notify_now` z `dedup_key` — drugi
   wpis dla tej samej publikacji jest niemożliwy na poziomie bazy.
3. Push: jak dotąd ogólne wezwanie kategorii ZMIANA_PLANU (bez treści
   zdrowotnych); e-mail nie jest wysyłany. Sukces push nie jest odczytem —
   trener widzi osobno „wpis utworzony” i `read_at`.

## 5. Testy (13.09.2026, lokalnie)

| Scenariusz akceptacyjny | Test |
|---|---|
| 1 kopia z szablonu niezależna | `test_a1_…` |
| 2 każdy typ elementu edytowalny/usuwalny (klient, szablon, dieta) | `test_a2_…` |
| 3 usunięcie dnia + Cofnij | `test_a3_…` (+ E2E: Cofnij z klawiatury) |
| 4 10 edycji + odświeżenie: szkic jest, klient widzi stary plan, brak powiadomień | `test_a4_…` (+ E2E reload) |
| 5 publikacja = wersja + jedno podsumowanie + jeden wpis | `test_a5_…` (+ E2E) |
| 6 podwójne kliknięcie / ponowienie | `test_a6_…` |
| 7 dodaję i usuwam ten sam element | `test_a7_…` |
| 8 dwa urządzenia / stara wersja bazowa | `test_a8_…` |
| 9 usunięcie ćwiczenia wykonanego wczoraj | `test_a9_a10_…` |
| 10 wykonanie podczas publikacji | `test_a9_a10_…` |
| 11 awaria między publikacją a wysyłką | `test_a11_…` |
| 12 błąd transakcji publikacji | `test_a12_…` |
| 13 push wyłączony; cudze konto | `test_a13_…` |
| 14 ręczna zmiana składnika/posiłku | `test_a14_…` |
| 15 inny trener | `test_a15_…` |
| 16 migracja bez powiadomień | `test_a16_…` |
| 17 cofnięcie opublikowanych zmian | `test_a17_…` |

Plik: `backend/tests/test_publikacja.py` (19 testów, w tym 2 jednostkowe
różnic i test edycji harmonogramu/celu); E2E `frontend/e2e/publikacja.spec.ts`.
Wyniki wszystkich bramek — sekcja „Weryfikacja wykonana” planu sesji.

## 6. Ograniczenia i to, czego świadomie nie zrobiono

* **Superserie / obwody** nie są osobnymi encjami (ćwiczenie = pozycja);
  grupowanie i „rozgrupowanie” — kolejna runda.
* **Składniki posiłku jako elementy**: posiłek z kreatora dań ma składniki
  w opisie; ręczna zmiana kasuje wartości i oznacza `edited_manually`
  zamiast przeliczać makro bez zweryfikowanych danych (uczciwiej niż
  liczyć z niepełnej bazy). Ponowne przeliczenie — po publikacji receptur.
* **Dwóch różnych trenerów** na jednym planie nie występuje (plan ma
  jednego właściciela); konflikt dotyczy dwóch urządzeń tego samego
  trenera (testy A8) — inny trener dostaje 404 (A15).
* **Publikacja z datą przyszłą** — brak (opcja nie jest pokazywana).
* **E-mail** o zmianie — brak; push jak dotąd.
* **Załączniki plików i retencja** — poza rundą (osobny proces).
* **FAILED w outboxie** po 10 próbach nie alarmuje automatycznie —
  do podpięcia pod diagnostykę.
* Ślady Wiedzy dla ćwiczeń nadal używają indeksów (`d{di}:e{i}`); po
  przestawieniu ćwiczeń „Dlaczego?” wskazuje ślad wg nowej pozycji tylko
  dla nowych wersji (stare ślady po indeksie — jak dotąd).

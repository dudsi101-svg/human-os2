# Plan sesji: panel trenera — pełna edycja, usuwanie i publikowanie zmian (0.58.0)

**Gałąź:** `agent/panel-trenera-publikacja` (od `agent/hotfix-pakiet-dane`
= 54cffa3, czyli `main` + poprawka 0.57.1; PR po scaleniu #54 — jeden
`[WRITER]` naraz).
**Rola:** jedyny piszący i integrator; recenzent: Codex. Właściciel 13.09:
„nie zatrzymuj pracy… jeśli nie znajdziesz błędów scalaj po każdym PR”.
**Źródło:** specyfikacja właściciela „Panel trenera: pełna edycja, usuwanie
i publikowanie zmian” (13.09): kopie z pochodzeniem, szkic → sprawdź
zmiany → opublikuj i powiadom, encje PlanDraft/ChangeSet/OutboxEvent/
ClientNotification/ExecutionRecord, idempotencja, kontrola rewizji,
17 testów akceptacyjnych. „Nie uznawaj samego dodania przycisków za
zakończenie zadania.”

## Inwentaryzacja (co zastałem)

| Miejsce dodawania | Dziś | Brak |
|---|---|---|
| Plan treningowy klienta (`PlanTab`, `PlanEditor`) | nowy plan, nowa wersja (pełny formularz, zapis = od razu widoczny + powiadomienie), kopia z szablonu | szkic, różnice, usuwanie dnia/ćwiczenia z potwierdzeniem i cofnięciem, kolejność/duplikacja, archiwizacja, odpięcie, zmiana nazwy |
| Szablony treningowe (`Templates`) | dodanie (ręcznie/plik/schemat), kopia do klienta | **edycja, usunięcie, duplikacja** (w ogóle brak) |
| Dieta klienta (`NutritionTab`) | nowa wersja (formularz tekstowy posiłków), kopia z szablonu diety, kreator dań | szkic, różnice, edycja/usuwanie posiłku, sekcji, suplementu jako elementu |
| Szablony diety (`DietTemplates`, `/api/nutrition-templates`) | PUT/DELETE, kopia do klienta | pochodzenie kopii tylko w `reason` |
| Harmonogram (`ScheduleTab`) | dodanie, wstrzymaj/wznów/zakończ | edycja treści |
| Cele (`ProfileTab`) | dodanie, status | edycja treści |
| Zapisy wykonania (`WorkoutSession.plan_version_id`) | wskazują wersję planu | — (ExecutionRecord już istnieje) |
| Powiadomienia (`Notification`, `dedup_key` UNIQUE per użytkownik, `notify_now`) | jeden wpis per wersja planu (natychmiast) | zdarzenie publikacji z ponawianiem (outbox), link do podsumowania zmian, stan odczytu dla trenera |
| Idempotencja (`idempotency.py`) | klucz + odcisk treści → 409 przy innej treści | użycie przy publikacji |

Tożsamość elementów: dziś indeks tablicy (`d{di}:e{i}` także w śladach
Wiedzy). Wersje są niemutowalne; treść w `content_json`.

## Decyzje projektowe

1. **Jeden silnik szkiców dla obu rodzajów planu** (`training`:
   dni → ćwiczenia; `nutrition`: sekcje, posiłki, suplementy) i dla
   szablonów treningowych (plan bez klienta = publikacja bez
   powiadomienia). Elementy dostają **stabilne `id`** (`ELM-…`) przy
   tworzeniu szkicu (stare wersje bez `id` → nadane deterministycznie
   w migawce bazowej szkicu, publikacja utrwala je w nowej wersji).
   Duplikacja = nowe `id`. Ślady Wiedzy zostają po indeksach (bez zmian).
2. **PlanDraft** (`plan_drafts`): rodzaj, plan, klient, trener, wersja
   bazowa, migawka bazowa z `id`, treść, rewizja, autor aktualizacji,
   stan (ACTIVE/PUBLISHED/DISCARDED). Jeden aktywny szkic na plan.
   Operacje po `id` (`set`, `add`, `delete`, `move`, `duplicate`,
   `replace`) z wymaganą rewizją → 409 `REVISION_CONFLICT` bez cichego
   nadpisania. Autozapis w interfejsie potwierdza się dopiero odpowiedzią
   serwera. Cofnięcie usunięcia = `add` z zachowanym `id`, pozycją
   i elementami podrzędnymi (serwer przyjmuje podane `id`, jeśli nie
   kolidują).
3. **Różnice** (`roznice.py`): porównanie migawki bazowej z treścią po
   `id`: dodane / zmienione (pole: przed → po) / usunięte / przestawione;
   dodanie i usunięcie tego samego elementu nie jest zmianą; przestawienie
   jest. Podsumowanie deterministyczne („Zmieniono 2 ćwiczenia i usunięto
   1 dzień”), bez LLM. Ręczna zmiana posiłku z kreatora dań kasuje jego
   wartości i oznacza `edited_manually` — poprzednia walidacja nie
   przechodzi na zmienioną recepturę.
4. **Publikacja w jednej transakcji**: uprawnienia (własność planu +
   relacja i zgoda domeny) → rewizja szkicu → wersja bazowa =
   `current_version_no` (inaczej 409 `BASE_VERSION_CONFLICT`, szkic
   zostaje) → walidacja treści (te same schematy Pydantic co dziś) →
   brak różnic = brak wersji i brak powiadomienia (200,
   `published:false`) → nowa niemutowalna wersja → **ChangeSet**
   (`change_sets`: stara/nowa wersja, różnice, podsumowanie, notatka
   trenera, autor, czas) → aktualizacja `current_version_no` →
   **OutboxEvent** (`outbox_events`: PENDING, próby, ostatni błąd) →
   ślad Wiedzy (`plan_change`, jak dotąd) → zdarzenie audytu →
   idempotencja (`idempotency_key` związany z autorem, planem i odciskiem
   żądania; powtórka = ten sam wynik; inna treść = 409). Wycofanie
   transakcji nie zostawia ani wersji, ani zdarzenia.
5. **Outbox → wpis klienta**: procesor (`publikacja.outbox`) tworzy
   wpis centrum `ZMIANA_PLANU` przez `notify_now` z
   `dedup_key=changeset:{id}` (UNIQUE(user_id, dedup_key) = brak
   duplikatów), url `/zmiany/{changeset_id}`; próba od razu po commicie
   i ponawianie w pętli przypomnień (`reminder_loop._tick`) do 10 prób.
   Push dostaje tylko ogólne wezwanie kategorii (jak dotąd). Trener widzi:
   opublikowano / wpis utworzony / odczytano (`read_at`).
6. **Ekran „Zobacz zmiany”** (`/zmiany/:id`, klient i trener z dostępem):
   przed/po każdego elementu, usunięte pozostają czytelne, autor, czas,
   notatka, link do planu. Kolejna publikacja = kolejny ChangeSet
   (poprzedni zostaje). Plan klienta: sprawdzenie nowszej wersji przy
   powrocie na ekran / zdarzeniu SSE → baner „Dostępna nowsza wersja —
   Wczytaj zmiany”, bez nadpisywania otwartego formularza wykonania;
   wykonanie wskazuje wersję, na której je rozpoczęto (bez zmian).
7. **Archiwizacja ≠ odpięcie**: `archiwizuj` (status ARCHIVED, historia
   i wykonania zostają) i `odepnij` (status UNASSIGNED, `client_id`
   zostaje dla historii; klient nie widzi planu). Usunięcie
   z opublikowanego planu = najpierw zmiana szkicu. Wykonań, pomiarów
   i wersji nie kasujemy. Cofnięcie opublikowanej zmiany = szkic z treści
   poprzedniej wersji → publikacja = nowa wersja i nowe podsumowanie.
8. **Pochodzenie kopii**: `source_template_id` + `source_template_version_no`
   na wersji (kopia z szablonu treningowego i diety). Edycja kopii nie
   dotyka oryginału ani innych kopii (test 1). Szablony treningowe:
   edycja (szkic → publikacja bez powiadomienia), zmiana nazwy,
   duplikacja, usunięcie (archiwizacja).
9. **Harmonogram i cele**: edycja treści (`PUT`), zakończenie/porzucenie
   już jest. Materiały wiedzy mają PUT/status; załączniki plików —
   poza rundą (osobny proces retencji).
10. **Przełącznik** `DZIK_SZKICE_PUBLIKACJA` (domyślnie włączony):
    wyłączenie przywraca poprzedni edytor „Nowa wersja” bez kasowania
    szkiców, zestawów zmian ani historii.
11. Bez LLM; bez publikacji z odroczoną datą (opcja nie jest pokazywana).

## Zamiar P0

- Migracja **30**: `plan_drafts`, `change_sets`, `outbox_events`,
  kolumny pochodzenia na wersjach; wersja **0.58.0**.
- `dzik_os/publikacja/`: `elementy.py` (id, normalizacja, kolekcje per
  rodzaj), `roznice.py` (diff + podsumowanie), `serwis.py` (szkic,
  operacje, publikacja, outbox).
- API: `/api/szkice` (utwórz/pobierz szkic planu, `PATCH` operacje,
  `DELETE …/elementy/{id}`, `GET …/roznice`, `POST …/publikuj`, `DELETE`
  odrzuć), `/api/plany/{kind}/{id}/zmiany`, `/api/zmiany/{id}`,
  `archiwizuj`/`odepnij`/`duplikuj`/zmiana nazwy dla planów i diet,
  `PUT /api/schedule/{id}`, `PUT /api/clients/{id}/goals/{goal_id}`,
  szablony treningowe: `PUT`/`DELETE`/`duplikuj`. Macierz dostępu.
- Frontend: edytor szkicu (dni/ćwiczenia; sekcje/posiłki/suplementy) z
  autozapisem i stanem zapisu, menu działań na każdej karcie (telefon +
  klawiatura), usuń z „Cofnij”, potwierdzenie dla dnia/planu z liczbą
  elementów, „Sprawdź zmiany”, „Opublikuj zmiany i powiadom” z notatką,
  „Odrzuć szkic”, archiwizacja/odpięcie/duplikacja/nazwa; szablony —
  edycja/usuwanie/duplikacja; klient — ekran zmian, baner nowszej
  wersji, wpis w centrum; trener — stan doręczenia i odczytu.
- Testy: 17 scenariuszy akceptacyjnych jako testy API (+ jednostkowe
  różnic), E2E: trener edytuje szkic → odświeżenie → publikuje → klient
  widzi wpis i ekran zmian.
- Dokumentacja: `docs/PUBLIKACJA_ZMIAN.md` (raport: zmienione pliki,
  wyniki testów, ograniczenia), CHANGELOG, STAN, RELEASE_STATUS, README.

## Świadomie nie robię

- publikacji z datą przyszłą, e-maila o zmianie, edycji załączników
  plików i procesów retencji, superserii/obwodów jako osobnych encji
  (dziś ćwiczenie = pozycja; grupowanie — kolejna runda), ponownego
  przeliczania makro posiłków po ręcznej zmianie składnika (kasuję
  wartości i oznaczam ręczną zmianę — uczciwiej niż przeliczać bez
  weryfikowanych danych), przeglądu dwóch różnych trenerów tego samego
  planu (plan ma jednego właściciela — konflikt dotyczy dwóch urządzeń).

## Rezerwacje

Migracja nr **30**, wersja **0.58.0**, pliki: `backend/dzik_os/publikacja/**`,
`routers/szkice.py`, `routers/{plans,nutrition,schedule,profile}.py`
(dopisania), `frontend/src/pages/coach/SzkicPlanu.tsx`,
`pages/coach/{ClientDetail,Templates}.tsx`, `pages/client/{Plan,Nutrition}.tsx`,
`pages/Zmiany.tsx`, `e2e/publikacja.spec.ts`, `docs/PUBLIKACJA_ZMIAN.md`.

## Weryfikacja wykonana

Lokalnie 13.09 (przed PR): ruff czysto (nowe pliki i moduły; 13 zastanych
uwag w starych plikach niezmienionych, jak dotąd tolerowanych przez CI);
backend **1684 passed, 1 skipped** (po dołożeniu stubów
`training_plan_versions`/`nutrition_plan_versions` do 7 testów migracji
na starej bazie — migracja 30 dokłada tam kolumny); `test_publikacja.py`
19 passed (A1–A17); Core 275; frontend tsc + build (89,4 kB / 120 kB)
+ test:helpers 140; E2E Playwright **26 passed** (25 + `publikacja.spec.ts`);
`e2e/test_a11y.mjs` czysto; `tools/spojnosc.py` 13/13.
Przeklik na żywo (desktop 1280 px + Pixel 7): edycja → autozapis →
menu działań → usuń + Cofnij → Sprawdź zmiany → publikacja z notatką →
wpis klienta → ekran „Zobacz zmiany”. Znaleziony i naprawiony błąd:
menu działań w karcie było przykrywane przez kolejną kartę (animacja
`transform` tworzy kontekst warstw) — menu renderowane przez portal.
CI i scalenie — po otwarciu PR #55 (uzupełnię).

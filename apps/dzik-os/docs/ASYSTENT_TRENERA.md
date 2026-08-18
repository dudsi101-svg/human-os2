# Asystent trenera — wspólna warstwa, zadania, granice

Asystent podpina się do okien panelu trenera, żeby przyspieszyć tworzenie
i uzupełnianie zasobów. Pierwsze zadanie: **złożenie szkicu planu z własnej
bazy ćwiczeń trenera**.

**Zasada nadrzędna:** *asystent proponuje, trener decyduje*. Żadne zadanie
niczego nie zapisuje — wynik jest propozycją obok edytora, a zapis to
zwykła, wersjonowana ścieżka planu z powodem zmiany, wykonana przez
człowieka.

**Druga zasada:** funkcja działa end-to-end **bez modelu językowego**. Bez
skonfigurowanego dostawcy ten sam przycisk otwiera **ścieżkę lokalną**
(gotowy podział tygodnia + baza ćwiczeń odfiltrowana po podanych
warunkach + podpowiedź „skopiuj szablon"). To nie jest tryb awaryjny
drugiej kategorii: ma realnie skracać pracę już dziś.

---

## 1. Architektura

| Warstwa | Plik | Odpowiedzialność |
| --- | --- | --- |
| Wspólna warstwa asystenta | `backend/dzik_os/coach_assistant.py` | rejestr zadań, zamknięte słowniki, bramkowanie zgód, limity i liczniki, proweniencja, kolejka zadań w tle |
| Adapter dostawcy | `backend/dzik_os/ai_provider.py` | kontrakt `propose_json`, domyślnie `NullAIProvider` (nic nie wychodzi) |
| API | `backend/dzik_os/routers/assistant.py` | zlecenie, stan, anulowanie, odrzucenie, zapis proweniencji |
| Trwałość | migracja **23** (`assistant_tasks`) | zadanie przeżywa zamknięcie przeglądarki |
| Postęp | `realtime.bus` → zdarzenie `assistant.task` | **istniejąca** magistrala SSE, drugiego kanału nie budujemy |
| Panel propozycji | `frontend/src/PlanAssistant.tsx` | formularz warunków, postęp, anulowanie, wstawianie, cofnięcie |
| Logika bez DOM | `frontend/src/assistantUtils.ts` | składanie żądania, dokładanie dni, migawka do cofnięcia, komunikaty |
| Wpięcie | `frontend/src/pages/coach/PlanEditor.tsx` | przycisk, panel obok planu, „cofnij wstawienie", `aria-live` |

### Przepływ

```
trener → warunki (dni, sprzęt, poziom, cel, czas sesji, opcjonalnie klient)
                      ↓
        POST /api/coach/assistant/tasks  →  202 + id zadania
                      ↓                      (edytor działa dalej)
             kolejka + wątek roboczy
                      ↓
   dostawca modelu skonfigurowany?  ── nie ──►  ŚCIEŻKA LOKALNA
                      │ tak                      (podział tygodnia +
                      ▼                           odfiltrowana baza)
        zamknięty słownik + walidacja
                      │
        zła wartość → odrzut CAŁEJ odpowiedzi
        (1 ponowienie, potem ścieżka lokalna z listą złych wartości)
                      ↓
        zdarzenie `assistant.task` (SAM STATUS) + GET zadania
                      ↓
   PROPOZYCJA obok planu → jedno kliknięcie „wstaw" → „cofnij wstawienie"
                      ↓
   trener zapisuje plan zwykłą ścieżką (nowa wersja + powód zmiany)
                      ↓
   POST /tasks/{id}/applied  → proweniencja na wierszu zadania
```

---

## 2. Rejestr zadań — jak dodać kolejne

Jeden moduł zamiast osobnych wywołań w każdym oknie. Inaczej powstałoby
kilka różnych walidacji, kilka miejsc sprawdzania zgód i kilka miejsc do
audytu. Zadanie to **deskryptor** (`AssistantTaskDescriptor`):

| Pole | Znaczenie |
| --- | --- |
| `key` | klucz zadania (`PLAN_DRAFT`) |
| `title` / `description` | tekst dla trenera (widoczny w `/status`) |
| `input_model` | schemat wejścia (Pydantic, `extra="forbid"`) |
| `output_model` | schemat wyjścia modelu (Pydantic, `extra="forbid"`) |
| `system_prompt` | pełna treść promptu systemowego |
| `uses_client_data` | czy zadanie MOŻE dotknąć danych podopiecznego |
| `daily_limit` | limit dzienny zadań na konto |
| `build_prompt_data` | minimalizacja — co dokładnie jedzie do dostawcy |
| `build_schema_hint` | zamknięte słowniki podane modelowi wprost |
| `validate_output` | walidacja wyjścia (podnosi `RejectedProposal`) |
| `build_proposal` | złożenie propozycji dla interfejsu |
| `build_local` | ścieżka lokalna (bez modelu) |
| `redact_input` | zredagowane wejście do zapisu w wierszu zadania |

**Dodanie kolejnego zadania** (progresja planu, opis szablonu) to:

1. schematy wejścia i wyjścia + prompt systemowy,
2. funkcje `build_*` / `validate_output` / `redact_input`,
3. `register(AssistantTaskDescriptor(...))`,
4. testy: zamknięty słownik, ścieżka lokalna, zgody, „nic nie zapisuje".

Nie trzeba dotykać routera, kolejki, magistrali, liczników ani
proweniencji — to wspólna warstwa. Router przyjmuje `task_key` i wybiera
deskryptor z rejestru.

---

## 3. Zadanie `PLAN_DRAFT` — kontrakt

### Wejście

| Pole | Zakres |
| --- | --- |
| `days_per_week` | 1–7 |
| `equipment` | do 12 pozycji tekstowych (podpowiedzi jak w filtrach bazy) |
| `level` | wyłącznie z `muscles.EXERCISE_LEVELS` |
| `goal` | tekst trenera, do 300 znaków |
| `session_minutes` | 15–180 |
| `client_id` | opcjonalnie — wtedy ograniczenia/urazy z profilu **za zgodą** |

### Wyjście modelu (walidowane serwerowo)

```jsonc
{
  "days": [
    {
      "name": "Trening A — całe ciało",
      "weekday": 1,                  // albo null
      "rationale": "jedno krótkie zdanie uzasadnienia",
      "items": [
        {
          "exercise_id": "HOS-EXC-…",  // WYŁĄCZNIE z bazy tego trenera
          "sets": "3",
          "reps": "8-10",
          "tempo": "2011",
          "rest": "90 s"
        }
      ]
    }
  ]
}
```

`extra="forbid"` w każdym modelu — dodatkowy klucz odrzuca **całą**
odpowiedź.

### Ciężary — świadomie poza zakresem

Asystent **nie podaje kilogramów**. W schemacie wyjścia **nie ma pola na
ciężar** (granica strukturalna, nie tylko zapis w promptcie), a wartość
z jednostką masy przemycona w innym polu (`8 x 60 kg`) odrzuca całą
odpowiedź. Pole `weight` w propozycji dla edytora zawsze zostaje puste.
Dobór obciążenia zależy od formy dnia, techniki i historii konkretnego
człowieka — to decyzja trenera, a nie parametr do wygenerowania.
Interfejs mówi o tym wprost.

### Nazwy ćwiczeń

Model wskazuje **tylko identyfikator**. Nazwa, tempo domyślne i link do
filmu pochodzą z bazy trenera — model strukturalnie nie ma jak „wymyślić"
ćwiczenia, którego nie ma.

---

## 4. Zamknięte słowniki

Model wybiera wyłącznie z wartości, które **istnieją**:

* identyfikatory ćwiczeń — wyłącznie z bazy **tego** trenera i wyłącznie
  ze statusem `ACTIVE` (ten sam kontrakt co
  `routers/plans.py::_validate_exercise_refs`);
* klucze partii mięśniowych, poziomy, wzorce ruchu — ze słowników
  `muscles.py`.

Wartość spoza słownika = **odrzucenie całej odpowiedzi**, jedno
ponowienie, potem jawny komunikat z listą niepoprawnych wartości
(`result.invalid_values`) i ścieżka lokalna.

> **Nigdy nie podmieniamy po cichu na „najbliższe" ćwiczenie.** Cicha
> podmiana byłaby zgadywaniem decyzji trenera na danych, które trafią do
> planu żywego człowieka — trener zobaczyłby ćwiczenie, którego nikt
> świadomie nie wybrał.

---

## 5. Bramkowanie zgód per RODZAJ DANYCH

| Rodzaj zadania | Zgoda podopiecznego | Zachowanie |
| --- | --- | --- |
| Wyłącznie zasoby trenera (baza ćwiczeń, szablon bez klienta) | **niepotrzebna** | zadanie działa normalnie, `client_data_used: false` |
| Z danymi konkretnego podopiecznego (`client_id`) | **wymagana** `funkcje_ai` | bez zgody pola profilu **w ogóle nie powstają**, interfejs mówi o tym wprost, zadanie i tak się wykonuje |

Bramką jest ta sama, jedna reguła co w onboardingu i OCR
(`authz.ai_features_consent_active`). Pola profilu, które wolno wysłać, są
zamkniętą listą: `urazy`, `ograniczenia_ruchu`, `bol_opis`,
`ograniczenia_organizacyjne`. Nazwisko, e-mail, data urodzenia, pomiary,
raporty i płatności w tej liście **nie istnieją** — nie ma ich jak wysłać.

Do dostawcy nie jedzie też żaden identyfikator osoby: ograniczenia lecą
jako `{rodzaj, opis}`, bez powiązania z kontem.

Ochrona przed wstrzyknięciem instrukcji: warunki, ograniczenia i katalog
ćwiczeń trafiają wyłącznie do sekcji **danych** (JSON), a prompt
systemowy jawnie wygasza polecenia z tych sekcji. Nawet gdyby model
„posłuchał" wstrzykniętej instrukcji, nie ma dokąd zapisać jej efektu:
wyjście to zamknięty schemat z identyfikatorami z bazy.

---

## 6. Płynność (kryterium akceptacji tej rundy)

| Wymaganie | Realizacja |
| --- | --- |
| Praca w tle, nieblokująca | zadanie w tabeli + kolejka z wątkiem roboczym; endpoint oddaje 202, edytor planu pozostaje w pełni używalny (panel niczego nie nakłada i niczego nie wyłącza) |
| Widoczny postęp | zdarzenie `assistant.task` na istniejącej magistrali SSE + odpytywanie zapasowe co 1,2 s |
| „Trwa dłużej niż zwykle" | po `DZIK_ASSISTANT_SLOW_AFTER_S` (domyślnie 8 s) komunikat zmienia się wprost |
| Anulowanie jednym kliknięciem | `POST /tasks/{id}/cancel`; wynik anulowanego zadania **nie wraca tylnymi drzwiami** |
| Timeout zamiast kręciołki | twardy limit `DZIK_ASSISTANT_TIMEOUT_S` (60 s) po stronie serwera i komunikat po stronie panelu |
| Propozycja OBOK planu | panel to osobna karta pod nagłówkiem edytora, plan zostaje widoczny |
| Wstawienie jednym kliknięciem | „Wstaw wszystkie dni", „Wstaw ten dzień", pojedyncze ćwiczenie ze ścieżki lokalnej |
| **Cofnij wstawienie** | migawka stanu edytora sprzed wstawienia; przycisk widoczny natychmiast po wstawieniu (w panelu i w pasku edytora) |
| Domyślnie DOKŁADAMY dni | `appendDays` nigdy nie kasuje pracy trenera; jedyny wyjątek to nietknięty dzień startowy |
| Brak skoków interfejsu | żadnych przeładowań i przewijania; zmiany ogłasza `aria-live`, pełna obsługa klawiaturą, etykiety `for`/`id` |
| Powtórne kliknięcie nie mnoży zadań | klucz idempotencji z treści formularza; nowy szkic wymaga świadomego „generuj ponownie" |
| Szkic formularza przeżywa utratę sieci | `localStorage` per trener i klient (wzorzec z rundy P11) |
| Bez klucza API nie ma ślepego zaułka | ścieżka lokalna (niżej) |

---

## 7. Ścieżka lokalna (bez dostawcy modelu)

Uruchamia się, gdy dostawca nie jest skonfigurowany, limit dzienny
wywołań jest wyczerpany, model nie odpowiedział albo jego odpowiedź
została odrzucona. Zawsze z **jawnym powodem** — nigdy jako błąd.

Co realnie daje:

1. **Gotowy podział tygodnia** zależny od liczby dni (1–3 dni: całe
   ciało A/B/C; 4 dni: góra/dół; 5–6 dni: pchanie/ciągnięcie/nogi;
   7 dni: dodatkowy dzień mobilności) — deterministyczny, zapisany
   wprost w `SPLITS`.
2. **Wstępnie odfiltrowaną bazę** dla każdego wzorca ruchu w dniu:
   po poziomie i sprzęcie, do 8 propozycji na wzorzec.
3. **Liczbę pozycji na dzień** wyliczoną z czasu sesji
   (`items_per_day`, 3–8).
4. **Listę szablonów** trenera z podpowiedzią „skopiuj istniejący
   szablon i popraw" — najszybsza droga, gdy plan już kiedyś powstał.

Wstawienie działa tak samo: „Wstaw ten dzień" bierze pierwsze
dopasowanie z każdego wzorca (sloty bez dopasowania są pomijane —
nigdy nie wstawiamy pozycji „do wymyślenia"), a pojedyncze kliknięcie
w ćwiczenie dokłada je do ostatniego dnia.

---

## 8. Wyszukiwanie ćwiczeń przy dużym katalogu

Baza rośnie (setki pozycji), więc wyszukiwarka w edytorze planu
(`ExercisePicker`) dostała trzy skróty — logika bez DOM siedzi
w `frontend/src/exercisePicker.ts`:

* **„Ostatnio używane"** — `GET /api/coach/exercises/recent`. Serwer
  przegląda do 60 najświeższych wersji planów **tego** trenera, wybiera
  `exercise_id` w kolejności od najświeższych i zwraca maks. 12 pozycji
  (wyłącznie własne, aktywne ćwiczenia). Skrót pokazuje się **tylko przy
  pustym wyszukiwaniu i bez filtrów**, żeby nie zasłaniał wyników; trener
  bez planów nie widzi pustej ramki. Odpowiedź to zwykłe pozycje bazy —
  **nigdy** informacja „użyte u klienta X".
* **Obsługa klawiaturą** — po otwarciu fokus ląduje w polu wyszukiwania,
  strzałki góra/dół chodzą po wynikach (roving tabindex, z zawijaniem),
  Enter dodaje podświetlone ćwiczenie, Escape zamyka wyszukiwarkę i wraca
  fokusem do przycisku, który ją otworzył.
* **Czytelny stan** — komunikat mówi wprost, ile wyników zostało
  („Znaleziono 84 — pokazano 20, zostało 64…"), a przy zerze trafień
  podpowiada konkretne wyjście: wyczyść filtry albo wpisz nazwę ręcznie.

---

## 9. Limity, koszty, metryki i audyt

| Ustawienie | Domyślnie | Znaczenie |
| --- | --- | --- |
| `DZIK_ASSISTANT_DAILY_TASKS_USER` | 40 | limit dzienny zadań asystenta na konto trenera |
| `DZIK_ASSISTANT_QUEUE_MAX` | 20 | poczekalnia; po przepełnieniu czytelne 429 |
| `DZIK_ASSISTANT_SLOW_AFTER_S` | 8 | po tylu sekundach interfejs mówi „trwa dłużej niż zwykle" |
| `DZIK_ASSISTANT_TIMEOUT_S` | 60 | twardy limit całego zadania |
| `DZIK_AI_DAILY_CALLS_USER` / `_GLOBAL` | 20 / 500 | wspólne limity wywołań modelu (te same co onboarding i OCR) |
| `DZIK_AI_MAX_INPUT_CHARS` | 6000 | górna granica sekcji danych wysyłanej do dostawcy |

Koszty liczy tabela `ai_usage_counters`, cecha **`coach_assistant`** —
wyłącznie liczby (wywołania, tokeny), zero treści. Metryki:
`assistant_tasks_requested/started/done/failed/cancelled`,
`assistant_calls`, `assistant_rejected`, `assistant_fallback`,
`assistant_tokens_in/out`, `assistant_proposals_applied`.

Audyt notuje **sam fakt**: `ASSISTANT_TASK_REQUESTED`,
`ASSISTANT_TASK_DONE` / `_FAILED`, `ASSISTANT_PROPOSAL_APPLIED`,
`ASSISTANT_PROPOSAL_DISCARDED` — klucz zadania, silnik, liczba dni, czas.
Ani wejście, ani propozycja nigdy nie trafiają do logów, metryk i audytu.

Zapisane wejście zadania (`input_json`) jest **zredagowane**: parametry
(dni, sprzęt, poziom, cel, czas sesji) i sam identyfikator klienta —
nigdy treść urazów.

---

## 10. Proweniencja

Każdy wynik niesie blok `provenance`:

```jsonc
{
  "assisted": true,
  "task_key": "PLAN_DRAFT",
  "engine": "MODEL",                       // albo "LOCAL"
  "engine_label": "asystent z modelem",
  "client_data_used": false,
  "generated_at": "2026-08-18T…"
}
```

Po wstawieniu propozycji panel woła `POST /tasks/{id}/applied`, co
dopisuje `approved_by`, `approved_at`, `plan_id`, `version_no` i zapisuje
całość w kolumnie `provenance_json`. **Ten endpoint nie tworzy ani nie
zmienia planu** — plan zapisuje trener zwykłą, wersjonowaną ścieżką
z powodem zmiany. Zostaje wyłącznie ślad, że plan powstał z pomocą
asystenta i jakim silnikiem.

W nazwach silników i w interfejsie nie pojawiają się nazwy dostawców ani
modeli — człowiek ma wiedzieć **jak** powstał wynik, nie **czym**.

---

## 11. Migracja nr 23 i plan wycofania

Migracja jest **wyłącznie addytywna**: jedna nowa tabela
`assistant_tasks`, zero `ALTER`-ów na istniejących tabelach, wszystkie
kolumny poza kluczami `NULL`able. Baza sprzed migracji działa bez
żadnego backfillu.

```
id, task_key, owner_user_id, client_id, status,
input_json (zredagowane), result_json, engine, mode_reason,
error_code, error, idem_key, duration_ms,
approved_at, provenance_json, result_ref,
created_at, started_at, finished_at
```

**Plan wycofania (rollback):**

1. usunąć router z `main.py` (funkcja znika z API),
2. `DROP TABLE assistant_tasks;`
3. `DELETE FROM schema_migrations WHERE version = 23;`
4. opcjonalnie `DELETE FROM ai_usage_counters WHERE feature = 'coach_assistant';`

Nic poza tym nie wymaga cofania: asystent nie zapisuje danych w planach,
ćwiczeniach ani profilach, więc jego wycofanie nie zostawia sierot ani
niespójności. Plany utworzone z pomocą asystenta zostają — są zwykłymi,
ręcznie zapisanymi wersjami planu.

Skrót „ostatnio używane" **nie ma własnego schematu** — liczy się
z istniejących wersji planów, więc jego wycofanie to usunięcie jednego
endpointu.

---

## 12. Znane ograniczenia

* **Kolejka żyje w pamięci jednego procesu.** Restart maszyny porzuca
  zadania w toku — zostają jako `PENDING` i trzeba je zlecić ponownie
  (to samo ograniczenie co kolejka OCR; deployment: jedna maszyna).
* **Brak automatycznego czyszczenia** starych wierszy `assistant_tasks`.
* **Ścieżka lokalna nie zna urazów.** Podział tygodnia jest
  deterministyczny i nie reaguje na ograniczenia podopiecznego — to
  trener wybiera ćwiczenia z odfiltrowanej listy.
* **Asystent nie ocenia stanu zdrowia i nie doradza medycznie.**
  Ograniczenia z profilu służą wyłącznie doborowi ćwiczeń, które ich nie
  obciążają; odpowiedzialność merytoryczna zostaje przy trenerze.
* **Bez progresji.** Zadanie układa jeden szkic, nie prowadzi planu
  w czasie — progresja to kolejny deskryptor do dopisania.
* **Katalog wysyłany do modelu jest przycięty** do 120 pozycji
  (najpierw pasujące poziomem i sprzętem). Przy bardzo dużej bazie model
  nie widzi wszystkiego — ścieżka lokalna i wyszukiwarka widzą całość.
* **Uzasadnienie dnia nie trafia do planu** — plan nie ma pola na taki
  komentarz; zdanie zostaje w panelu propozycji.
* **Ostatnio używane liczą się z 60 najświeższych wersji planów.** Trener
  z bardzo długą historią nie zobaczy w skrócie ćwiczeń używanych dawniej
  (są normalnie w wyszukiwarce).

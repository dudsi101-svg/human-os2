# Szablony rozwijane po nazwie i opisy ćwiczeń z Wiedzy — postęp i P2

**Runda 0.75.0**, gałąź `agent/szablony-i-opisy`, PR #77. Plan i przeklik:
`docs/plan-sesji/szablony-i-opisy.md`.

## Zrobione

* Szablony → Trening: nazwa jako przycisk rozwijający (h2 > button, `aria-expanded`,
  `aria-controls`), meta „dni · pozycje · data”, panel publikacji po rozwinięciu;
  Dieta: nazwa = „Podgląd”.
* `OpisCwiczenia` (Plan, Dzisiaj, pozycje bloków, karta klienta u trenera): skrót
  po id albo po nazwie, cache, „Pełny opis w Wiedzy” z powrotem.
* Trasy `GET /api/me/exercises/by-name`, `GET /api/coach/exercises/by-name`.
* Karta ćwiczenia w Wiedzy (klient v2 + legacy, trener) z bezpiecznym powrotem.
* Link „Karta w Wiedzy” w edytorze nowej wersji i w szkicu.

## P2 (do osobnej rundy — nie blokują)

1. **Prefetch dopasowań po nazwie.** Dziś przycisk „Opis ćwiczenia” jest przy każdej
   pozycji, a brak dopasowania widać dopiero po kliknięciu (uczciwy komunikat).
   Zbiorcze `POST /api/me/exercises/dopasuj {names: []}` pozwoliłoby ukryć przycisk
   przy pozycjach bez opisu jednym żądaniem na widok planu. Polecenie mówiło
   „leniwie po kliknięciu”, więc zostawione.
2. **Utrwalenie dopasowania w treści planu** (`exercise_id` przy pierwszym trafieniu)
   — wymaga nowej wersji planu albo migracji treści; decyzja właściciela.
3. **Dzisiaj — pozycje cardio** nie mają „Opisu ćwiczenia” (mają własny opis
   urządzenia i „Dlaczego takie cardio?”); pozycja cardio z seedu niesie
   `exercise_id` — można dołożyć ten sam przycisk, jeśli trener uzna to za przydatne.
4. **Wiedza v2 — atlas konfiguratora** (`ex-<konfigurator_id>`) nie jest łączony
   z bazą trenera; pozycje z konfiguratora mają `konfigurator_id`, nie `exercise_id`.
   Dopasowanie po nazwie działa dla nich, jeśli trener ma wpis pod tą nazwą.
5. **Szablony — stan rozwinięcia** nie przeżywa przeładowania (celowo lokalny).
   Ewentualne zapamiętanie ostatnio rozwiniętego w `localStorage` — do decyzji.
6. **Klawiatura w E2E**: sprawdzany Enter; Spacja działa natywnie na `<button>`,
   bez osobnego testu.

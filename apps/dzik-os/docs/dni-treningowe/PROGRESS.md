# Postęp — dni treningowe na „Dzisiaj” (0.71.0)

| Etap | Stan | Dowód |
|---|---|---|
| 0 rozpoznanie | ✅ | `00_rozpoznanie.md`, `docs/plan-sesji/dni-treningowe.md` |
| 1 silnik | ✅ | `dzik_os/dni_treningowe.py`, 5 testów na przykładach ręcznych |
| 2 model + migracja 38 | ✅ | `PlanWeekdayChoice`, `db.py` (38; 37 = PR #70) |
| 3 API + „Dzisiaj” + prywatność | ✅ | `routers/plan_weekdays.py`, `today.py`, `privacy.py` (`export_version` 2.0), 8 testów API, macierz dostępu |
| 4 UI | ✅ | `pages/client/DniTreningowe.tsx`, `Plan.tsx`, `Today.tsx`, `ClientDetail.tsx`, `dni-treningowe.spec.ts` |
| 5 zamknięcie | ✅ | CHANGELOG 0.71.0, RELEASE_STATUS, PERMISSIONS, INSTRUKCJE, STAN_PRZEKAZANIA, `zlecenia/README.md` |

## Przyjęte domyślne (właściciel nie odpowiedział na §8 promptu)

1. Trener może zapisać wybór klienta przez API (relacja + zgoda); w UI trenera tylko odczyt.
2. Dwie jednostki w jeden dzień → 422.
3. Plan bez dni → tylko karta „ustaw dni” (system nie zgaduje).

## Przegląd niezależny PR #72 (dwaj recenzenci integratora): brak P0/P1, P2 naprawione

Unikalne klucze jednostek w wersji (`dni()` — powtórzone `id` / `id` = `idx:<n>` → indeks);
plan `UNASSIGNED`/`ARCHIVED` = 404; `StrictInt` dla `weekday`; miejscownik w komunikacie
422; front nie gubi błędu spoza kluczy jednostek; bezwarunkowy test „today = dzień
trenera” + mieszanka `id`/bez `id` + dwa dni trenera z tym samym `weekday`.
Dług sprzed rundy (poza zakresem): wybór planu ACTIVE różny w `Plan.tsx` (`created_at`)
i `today.py` (`updated_at`); `GET /api/clients/{id}/plans` oddaje klientowi treść planu
`UNASSIGNED`.

## P2 / do rozważenia

* Edycja wyboru dni z karty klienta u trenera (API gotowe — ten sam komponent w trybie
  formularza) — po odpowiedzi właściciela na pytanie 1.
* Tygodnie A/B (rotacja) — nowa runda, inny model (`choices_json` per tydzień).
* Przypomnienie push o treningu „na dziś” — osobna decyzja (nie re-engagement).
* Karta „ustaw dni” nie pojawia się, gdy plan nie ma ani jednej jednostki (`source: none`)
  — wtedy nadal „Dziś bez treningu”; celowe.
* `podpowiedz` zwraca `stale` nawet, gdy nieaktualny jest tylko klucz z `None` — łagodna
  notka i tak zachęca do ponownego zapisu, który czyści wpis.

## Przegląd kodu (3 przejścia tematyczne, zasady v2 §3)

Bez narzędzia Agent w sesji — trzy przejścia po pełnym diffie wykonane przez sesję
piszącą (nie niezależny przegląd; odnotowane w planie sesji, „Odstępstwa”).

**Bezpieczeństwo / zgody / IDOR:** `resolve_client_access` przed odczytem planu (obcy
klient 404 zanim cokolwiek o planie wiadomo); cudzy plan/szablon pod `client_id` → `deny`
(404 z audytem); `PUT` z ciałem domyślnym dochodzi do warstwy uprawnień (macierz: twarda
odmowa dla klienta B, obcego trenera i admina); trener po cofnięciu zgody `dane_treningowe`
traci GET/PUT/DELETE (test); usunięcie konta kasuje wybór, `TrainingPlan` nie jest kasowany
w `privacy.py`, więc FK `plan_id` bezpieczny także na PostgreSQL; audyt bez treści planu.
**P2 naprawione:** wyścig dwóch pierwszych zapisów (klient i trener naraz) dawał 500 z
`IntegrityError` → 409 z komunikatem; podsumowanie audytu „Klient ustawił…” także przy
autorze-trenerze → neutralne z dopiskiem „(przez trenera)”; w trybie trenera błąd odczytu
`/dni` (np. cofnięta zgoda) renderował kartę „nie udało się wczytać” → milczy.

**Silnik i `today`:** układ klienta obowiązuje w całości (test), pusta lista ≠ DELETE
(test), klucze spoza wersji ignorowane/`stale_keys` (test), `day_index` bez zmian — `POST
…/workouts` i `done_today` działają jak dotąd (test), `z_json` z bazy nie rzuca (test).
**P2 odnotowane:** `podpowiedz` zwraca `stale` przed `no_weekdays` — przy nieaktualnym
wyborze bez żadnego przypisania „Dzisiaj” pokazuje notkę + „Dziś bez treningu” (notka
prowadzi do Planu; wystarczające); wiele planów ACTIVE: `today` bierze najnowszy po
`updated_at`, `Plan.tsx` pierwszy ACTIVE po `created_at` — rozjazd sprzed rundy, nie
dotykany.

**Testy / UX / treść:** **P2 naprawione:** odznaki w `Plan.tsx` i `ClientDetail.tsx`
mapowane po pozycji tablicy → po `day_index`; karta klienta nie przeładowywała `/dni` po
„Wczytaj zmiany” (nowa wersja) → `key` z numerem wersji. Odnotowane: etykieta „propozycja
trenera” na „Dzisiaj” także, gdy trener nie wpisał `weekday`, a trafienie i tak nastąpiło
(niemożliwe — bez `weekday` nie ma trafienia); brak testu jednostkowego `etykietaDnia`
(pokryte E2E przez odznaki).

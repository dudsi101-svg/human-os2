# Plan sesji: panel rozwojowy „Dzisiaj” — powitanie, hasło dnia, nawyki (0.63.0)

**Gałąź:** `agent/nawyki-dzisiaj` (od `main` = c4143cd, po 0.62.0). **Rola:** aktywny
piszący — polecenie właściciela z 14.09.2026 („W pierwszej zakładce podopiecznego dodajmy
panel rozwojowy — 3 nawyki z codziennym odhaczaniem, codzienne hasło motywujące,
powitanie u góry”), pliki `PROMPT_writer_nawyki-dzisiaj.md`, `plan-sesji_nawyki-dzisiaj.md`
(szkic właściciela), `daily_messages.py` (60 haseł, wstawiony 1:1).
**Rezerwacje (KOORDYNACJA §0):** wersja **0.63.0**, migracja **34** (addytywna: `habits`,
`habit_completions`). Gałąź `agent/monitoring-postepy` (zatrzymana na etapie 0, czeka na
decyzje właściciela) przesuwa się na **0.64.0 / migrację 35** — odnotowane w
`STAN_PRZEKAZANIA.md` §2. Pliki współdzielone: `models.py` (klasy na końcu), `db.py` (wpis 34),
`main.py` (rejestracja routera), `access_matrix.py`, `seed.py`, `routers/today.py`,
`types.ts` (`TodayData`), `CHANGELOG.md`.

## Co robimy

1. **Powitanie** zależne od lokalnej pory dnia + imię (pierwszy człon `display_name`);
   `greeting_name` w `/api/me/today` (front nie zgaduje po e-mailu).
2. **Hasło dnia** — `dzik_os/daily_messages.py` 1:1 (60 sentencji z autorem i adnotacją),
   `message_for(local_today(user))` jako `daily_message` w `/api/me/today`; zero AI.
3. **3 nawyki** (`Habit`, `HabitCompletion`) z codziennym, cofalnym odhaczaniem, terminem
   (`target_days` 66, regulowane 14–254), łagodnym decay i **absolutorium** (GRADUATED).

## Decyzje projektowe (właściciel 14.09 + wykonawcze)

* **Rusztowanie samowygaszające, nie streak:** odhaczanie ma termin i kończy się
  absolutorium („to już Twój nawyk — nie musisz tego odhaczać”). Zgodne z zasadą
  Human OS „zmniejszać zależność od systemu w czasie” — argument ZA funkcją.
* **Decyzja foundera:** niewykonany zaplanowany dzień, który minął, **cofa postęp o 1**
  (łagodny decay, nie reset), podłoga 0 liczona **sekwencyjnie** (dzień po dniu, więc
  długa przerwa nie tworzy „długu” do odrobienia — po niej start od 0, nie od −20);
  dni poza `days_of_week` neutralne; dzisiejszy dzień nie karze, dopóki nie minie.
  Koryguje filtr `ANALIZA_RYNKU` §E („bez kary za przerwę”) → „łagodny decay −1, UI bez
  zawstydzania” — notka w §E; wpis R-19 w `RISK_REGISTER` (świadome odstępstwo).
* **Postęp liczony serwerowo przy odczycie** (bez crona); status GRADUATED utrwalany
  przy odczycie/odhaczeniu, gdy `progress ≥ target_days`. Limit **3 ACTIVE** na klienta;
  GRADUATED/ARCHIVED zwalniają miejsce. GRADUATED bez przycisku odhaczania; karta
  absolutorium z wyborem „Wymień na nowy” / „Zostaw tak jak jest”.
* **Test INTENDED_PURPOSE §2/§3:** nawyk = zwykły tekst nazwy + odhaczenia (samoobserwacja,
  brak interpretacji objawów, zero zaleceń); hasło dnia = sentencje o charakterze
  i dobrostanie, bez treści medycznych (przejrzane: 60/60). Nawyki dot. snu/nastroju/
  objawów należałyby do domeny `dane_zdrowotne` (opt-in) — **poza v1**; w v1 nazwa
  nawyku nie jest klasyfikowana (klient może wpisać cokolwiek — to jego tekst, jak
  element harmonogramu). Wynik: bez wątpliwości, brak pytania do foundera.
* **Zgody:** domena `training_data` (jak harmonogram) — bez nowej bramki.
* **Proweniencja:** `author_id` (trener albo klient) + `author_note`; trener widzi
  i edytuje nawyki w karcie klienta (zakładka Harmonogram → sekcja „Nawyki”).
* **UI bez zawstydzania:** „42 z 66 — nawyk się utrwala”; zero czerwieni, zero „passa”,
  zero „X dni z rzędu”, zero komunikatów-kar.

## Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Czytam (z hipotezą) | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 rozpoznanie | `today.py`, `Today.tsx`, `TodayData`, `ScheduleCompletion` + `complete_schedule_item`, `schedule.py` POST, `seed.py` (harmonogram), `access_matrix`, `ANALIZA_RYNKU` §E, `INTENDED_PURPOSE` | `docs/nawyki/00_rozpoznanie.md` + ten plan | — | dziesiątki tys. |
| 1 silnik postępu | — | `dzik_os/nawyki.py`: czyste funkcje (dni zaplanowane, postęp z decay i podłogą, absolutorium, powitanie wg pory) | testy jednostkowe na przykładach ręcznych (dni neutralne, decay, podłoga, dziś nie karze, próg) | dziesiątki tys. |
| 2 model + migracja 34 + seed | `models.py`, `db.py`, `seed.py` | `Habit`, `HabitCompletion`, migracja, 3 nawyki demo klienta A (bliski absolutorium, z decay, świeży) | `test_migracje_przenosnosc`, seed w testach | dziesiątki tys. |
| 3 API + „Dzisiaj” | `routers/today.py` | `routers/habits.py` (GET/POST/PATCH/complete), `daily_messages.py`, pola w `/me/today`, macierz dostępu, `tests/test_habits.py` (limit 3, idempotencja, cofnięcie, obcy klient 404, trener z relacją, absolutorium, hasło deterministyczne) | pytest modułu + macierz | setki tys. |
| 4 UI | `Today.tsx`, `ClientDetail.tsx` (ScheduleTab), `components.tsx`, `styles.css` | powitanie + karta hasła + panel „Nawyki” (odhaczanie, postęp, absolutorium, zarządzanie klienta) w `pages/client/Today.tsx` przez wspólny `pages/nawyki/PanelNawykow.tsx`; sekcja trenera w Harmonogramie | `tsc`, build (budżet), `test:helpers`, E2E `nawyki.spec.ts`, a11y, PWA offline, obejrzenie przez serwer E2E | setki tys. (największy koszt) |
| 5 zamknięcie | — | CHANGELOG 0.63.0, RELEASE_STATUS, PERMISSIONS, INSTRUKCJE, KOORDYNACJA, ANALIZA_RYNKU §E, RISK_REGISTER, STAN_PRZEKAZANIA | pełny `pytest`, ruff z korzenia, spójność, mutacje (lokalnie), CI | dziesiątki tys. |

**Największy koszt:** etap 4 (dwa widoki + zarządzanie). Taniej bez utraty informacji:
jeden komponent panelu z trybem `klient`/`trener` (jak karta zapotrzebowania w 0.62.0)
i wzorzec odhaczania skopiowany z harmonogramu (`markScheduleDone`). Bezpiecznik: 3× plan.
Przegląd: 3 recenzentów wsadowo (bezpieczeństwo/zgody, poprawność silnika i idempotencji,
testy/UX/treść), P0/P1 naprawione przed scaleniem, P2 do `docs/nawyki/PROGRESS.md`.

## Odstępstwa od planu

* Powitanie liczone na urządzeniu (godzina lokalna telefonu, nie serwera) —
  backend podaje tylko `greeting_name`; helper `powitanie.ts` z testem.
* „Zostaw tak jak jest” = pole `ack_on` (karta absolutorium zwija się do
  jednej linii, nawyk zostaje GRADUATED i nie zajmuje miejsca).
* Etapy 2–3 wykonane razem (jeden przebieg testów po zestawie zmian).
* Zasilanie profilu/klasyfikacja nazwy nawyku — świadomie brak (v1: tekst).

## Weryfikacja wykonana

* Silnik: 7 testów (`tests/test_nawyki_silnik.py`, przykłady ręczne: decay
  sekwencyjny, podłoga, dni neutralne, „dziś nie karze”, próg).
* API: 6 testów (`tests/test_habits.py`): limit 3 i proweniencja, odhaczanie
  idempotentne i cofalne, decay + absolutorium + ack, obcy klient/IDOR,
  pola „Dzisiaj” + seed, eksport i usuwanie konta.
* Macierz dostępu, prywatność, onboarding, migracje przenośne: zielone.
* Frontend: `tsc` czysto, build w budżecie, `test:helpers` 142/142,
  E2E `nawyki.spec.ts` + logowanie zielone; a11y i PWA offline — wynik w PR.
* Zrzut ekranu „Dzisiaj” obejrzany przez serwer E2E (zasada uruchomienia).

## Plan kontra rzeczywistość (zasady v2 §5)

Plan: 6 etapów, największy koszt UI. Rzeczywistość: zgodnie z planem —
jeden wspólny panel (klient/trener) zamiast dwóch widoków; rozpoznanie
z pliku, bez ponownych odczytów; zero podagentów na budowę, 3 recenzentów
wsadowo na przegląd (wynik w `docs/nawyki/PROGRESS.md`). Usprawnienie na
następny raz: seed demo pisać od razu razem z testem, który go czyta
(tu test API czekał na dane demo jeden przebieg).

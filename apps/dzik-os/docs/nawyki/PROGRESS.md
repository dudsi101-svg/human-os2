# Postęp — panel rozwojowy „Dzisiaj” (0.63.0)

| Etap | Stan | Dowód |
|---|---|---|
| 0 rozpoznanie | ✅ | `00_rozpoznanie.md` |
| 1 silnik postępu | ✅ | `dzik_os/nawyki.py`, 7 testów |
| 2 model + migracja 34 + seed | ✅ | `Habit`, `HabitCompletion`, `db.py`, `seed.py` |
| 3 API + „Dzisiaj” | ✅ | `routers/habits.py`, `today.py`, 6 testów, macierz dostępu |
| 4 UI | ✅ | `pages/nawyki/PanelNawykow.tsx`, `Today.tsx`, `ClientDetail.tsx`, `nawyki.spec.ts` |
| 5 zamknięcie | ✅ | CHANGELOG 0.63.0, PERMISSIONS, INSTRUKCJE, ANALIZA_RYNKU §E, RISK_REGISTER R-20, STAN_PRZEKAZANIA |

## P2 / do rozważenia

* Przypomnienie push o nawykach o wybranej porze (jak harmonogram) — nie
  w v1 (przypomnienie = usługa konfigurowalna, nie re-engagement).
* Historia odhaczeń w widoku trenera (kalendarz) — dziś tylko postęp.
* Nawyki dot. snu/nastroju jako domena zdrowotna (opt-in) — poza v1.

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

## Przegląd kodu (3 recenzentów wsadowo, zasady v2 §3)

**P1 naprawione:** nieistniejąca data (`2026-02-30`) dawała 500 → 422; brak dolnej
granicy `started_on` (≤ 365 dni wstecz); wyścig na limicie trzech nawyków (ponowne
policzenie po zapisie → 409); postęp po absolutorium liczony do „dziś” (teraz absolutorium
datowane na dzień osiągnięcia terminu, postęp zamrożony); „Dziś wolne” było wyłączonym
przyciskiem „Odhacz” (teraz odznaka); usunięcie bez potwierdzenia i bez drogi powrotnej
(`confirm` + `status=ACTIVE` przywraca); termin spoza 14–254 dawał surowe „Błąd 422”
(walidacja w formularzu); testy: edycja, trener bez zgody treningowej, audyt, `ack` przed
absolutorium, `archived=true`, dni tygodnia spoza dziś, zamrożenie.
**P2 naprawione:** martwe `odswiez` w complete; `IntegrityError` przy równoległym
odhaczeniu → stan; PATCH nie-aktywnego = 409; notatka tylko autora + `HABIT_UPDATED`;
`HABIT_GRADUATED` w audycie; formularze zamykane tylko po sukcesie; `useCallback` na
`load`; panel tylko przy zalogowanym użytkowniku; tryb trenera bez „Twoim nawykiem”
i bez wyboru za klienta; data absolutorium po polsku; „Usuń z listy” + wyjaśnienie
o historii; dni w edycji; błędy panelu bez czerwieni; R-20 pod R-19; wiersz gałęzi
w STAN_PRZEKAZANIA; PERMISSIONS o odhaczaniu przez trenera.
**P2 odnotowane:** odhaczenie w dzień poza planem przez API jest dozwolone (nie liczy
się do postępu; UI go nie pokazuje); „Dobry wieczór” 0–4 rano (do decyzji właściciela);
E2E absolutorium (przez API `started_on` wstecz) — do dołożenia przy następnej rundzie;
KOORDYNACJA.md bez zmian (dokument zasad, nie rund).

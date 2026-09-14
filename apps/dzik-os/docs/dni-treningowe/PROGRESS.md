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

⟨uzupełnia sesja pisząca po przeglądzie⟩

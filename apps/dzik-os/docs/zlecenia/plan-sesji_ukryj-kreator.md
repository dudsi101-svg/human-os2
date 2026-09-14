# Plan sesji: ukrycie kreatora diety za flagą, katalog produktów zostaje (⟨wersja⟩)

> SZKIC WŁAŚCICIELA — sesja pisząca kopiuje do `docs/plan-sesji/ukryj-kreator.md` jako
> pierwszy commit, po uzupełnieniu pól `⟨…⟩`.

**Gałąź:** `agent/ukryj-kreator` (od `main` = ⟨sha⟩). **Rola:** aktywny piszący — decyzja
właściciela 14.09.2026 („zrezygnujemy z kreatora diety na ten moment… możemy go ukryć”),
plik `PROMPT_writer_ukryj-kreator.md`. **Rezerwacje:** wersja ⟨wg kolejności scalania,
`docs/zlecenia/README.md`⟩, migracja **brak**. Pliki współdzielone: `config.py`, `main.py`
(`features`), `routers/food_catalog.py`, `Knowledge.tsx`, `conftest.py`, `CHANGELOG.md`.

## Co robimy
Flaga `DZIK_DIET_WIZARD_ENABLED` (domyślnie wyłączona, brak wpisu w `fly.toml`): trasy
`/coach/diet-wizard` i `/coach/diet-suggestion` → 404, `features.diet_wizard` w health,
zakładka „Dieta” w Wiedzy trenera ukryta. Katalog „Produkty”, plany ręczne, istniejące
plany klientów, kod i testy kreatora — bez zmian.

## Etapy
| Etap | Wytwarzam | Weryfikacja |
|---|---|---|
| 1 backend | flaga, `wymagaj_kreatora()`, health, test wyłączenia | pytest (kreator dalej zielony przy fladze w conftest) |
| 2 front | `TABS` warunkowe po `features.diet_wizard` | `tsc`, build, a11y (kolejność pierwszych zakładek), obejrzenie |
| 3 zamknięcie | CHANGELOG, INSTRUKCJA_TRENERA, DEPLOYMENT (jak włączyć), DEFERRED_FEATURES, RELEASE_STATUS, STAN_PRZEKAZANIA | ruff, spójność |

## Czego nie dotykam
Kod/trasy/testy/dane kreatora (tylko bramka flagi), katalog produktów, `NutritionPlan`,
„Ułóż z dań”, dieta z szablonu, Core.

## Odstępstwa / Weryfikacja wykonana / Plan kontra rzeczywistość
⟨uzupełnia sesja pisząca⟩

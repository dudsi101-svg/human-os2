# Plan sesji: jedna sekcja Dieta

**Gałąź:** `agent/jedna-dieta` (od `main` = `470a52f`)
**Rola:** aktywny piszący (obserwacja właściciela, 24.08: „powstały nam
dwie sekcje mające ostatecznie wspólne zadanie")
**Cel:** scalić „Kompozytor diety" i „Kreator diety" w jedną zakładkę
**Dieta** z wyborem drogi — trzeci raz ten sam wzorzec, który leczył
Ćwiczenia (0.34.0) i Szablony (0.40.0): jedno wejście, drogi w środku.

## Zamiar

* Zakładki Bazy wiedzy: 4 zamiast 5 (`dieta` zastępuje `dieta`+`kreator`).
* Nowa `DietTab`: karta „Ułóż dietę" z dwiema drogami:
  1. **„Wygeneruj propozycję"** (domyślna) — zasady i proporcje:
     % makro, posiłki, dni, wykluczenia, budżet czasu → gotowe posiłki
     (mechanizm Kreatora 0.46.0);
  2. **„Ułóż sam z produktów"** — własny wybór produktów + cele gramowe
     → rozkład porcji (mechanizm Kompozytora 0.24.0).
* Oba dotychczasowe komponenty przechodzą w tryb osadzony (bez własnych
  ram — jak `BuiltinTemplates` przy scalaniu Szablonów); zero utraty
  funkcji.
* Backend bez zmian — dwa endpointy zostają (różne kontrakty).
* Stary identyfikator zakładki `kreator` znika; wejście w `dieta`
  pokazuje wybór drogi.

## Mój obszar

- `frontend/src/pages/coach/Knowledge.tsx` (scalenie zakładek);
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md` (integrator); ten plan.

## Czego nie dotykam

- backendu (żaden endpoint się nie zmienia), typów wyników;
- Core, migracji, pozostałych zakładek.

## Rezerwacje

- **Wersja: 0.47.0** (ostatnia: 0.46.0). **Migracja: brak.**

## Świadomie nie robię

- nie dodaję „Utwórz plan" do drogi ręcznej (Kompozytor zwraca płaską
  listę, nie posiłki — przycisk sugerowałby strukturę, której nie ma;
  ewentualna rozbudowa to osobna decyzja produktowa);
- nie ruszam mechaniki żadnej z dróg — to czysta konsolidacja wejścia.

## Weryfikacja (do wypełnienia)

- tsc + build + helpers + E2E (frontend to całość zmiany);
- bramki minimalne backendu (nic nie zmieniam, ale bramka jest bramką);
- uruchomienie na żywo: obie drogi klikalne z jednej zakładki, wyniki
  identyczne z 0.46.0.

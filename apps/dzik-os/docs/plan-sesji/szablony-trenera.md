# Plan sesji: autorskie szablony trenera + zakładka „Dieta" w Szablonach (0.54.0)

**Gałąź:** `agent/szablony-trenera` (od `main` = b00427d)
**Rola:** aktywny piszący
**Cel:** właściciel dostarczył trzy autorskie materiały Łukasza
(plan Push/Pull/Legs+Push II „Etap I", plan FBW A/B/C „pierwsze 5
tygodni", dieta „Etap I" w PPTX). Mają trafić do profilu trenera jako
szablony wielokrotnego użytku + powstaje nowa zakładka z gotowymi
szablonami DIETY (dotąd szablony istniały tylko dla treningu).

## Anonimizacja (zasada rundy)

Pliki źródłowe są nazwane imionami klientów i zawierają osobiste
wtręty oraz konkretne makro jednej osoby. Do katalogu trafiają wersje
ZANONIMIZOWANE: neutralne nazwy, wtręty usunięte, makro puste (trener
ustawia per klient). Imiona klientów nie pojawiają się nigdzie w repo.

## Zamiar

1. **Trening:** dwa nowe wpisy wbudowanego katalogu
   (`plan_templates_data.py`): TPL-025 „Push/Pull/Legs + Push II —
   Etap I (autorski)" i TPL-026 „FBW A/B/C — pierwsze 5 tygodni
   (autorski)"; jednostki z linkami wideo z materiałów źródłowych —
   `Unit` dostaje pole `video`, a `build_days` przenosi je do
   `video_url` (dotąd zawsze None); wytyczne tygodnia (mobility,
   cardio, kroki, brzuch, objaśnienia serii/RIR) jako dedykowana
   jednostka „Wytyczne tygodnia" z komentarzami i linkami.
2. **Dieta — nowy byt:** tabela `nutrition_templates` (migracja 27:
   id, coach_id, title, content_json, created_at, updated_at —
   snapshot roboczy bez wersjonowania; wersjonowanie zostaje na
   planie klienta), wbudowany katalog `dieta_szablony_data.py`
   z szablonem „Dieta — Etap I (autorski)": posiłki z opcjami
   wymiennymi, sekcje (jak korzystać / dodatkowe pomysły / ściąga
   zamienników 1:1 / suplementacja jako tekst), makro puste.
   Router: katalog, dodaj-do-moich, CRUD moich (tylko COACH,
   właściciel szablonu), `copy-to/{client_id}` → tworzy
   `NutritionPlan` v1 istniejącą ścieżką (szablon niezależny od kopii).
3. **Frontend:** ekran Szablony dostaje dwie zakładki „Trening" /
   „Dieta" (nowa zakładka = katalog gotowych + moje szablony diety
   + podgląd); w karcie klienta (Dieta) przycisk „Z szablonu".
4. Testy: router (katalog/moje/copy-to, izolacja ról przez
   access_matrix), migracja w łańcuchu, `build_days` z wideo;
   E2E: zakładka Dieta w Szablonach widoczna i przełączalna.

## Świadomie nie robię

- zero automatyki żywieniowej — szablon to treść, którą trener
  świadomie kopiuje i edytuje; makro zawsze ustawia człowiek;
- przypomnienia suplementów nie powstają z szablonu (propose-only
  zostaje przy kliencie);
- PPTX/DOCX nie trafiają do repo (tylko wyekstrahowana, zanonimizowana
  treść).

## Rezerwacje

- **Wersja: 0.54.0.** **Migracja: 27.**

## Weryfikacja (do wypełnienia)

- bramki pełne; uruchomienie na żywo z przeklikiem zakładki Dieta.

## Weryfikacja (wykonana)

- `ruff` — czysto; backend **863 passed, 1 skipped** (4 nowe testy
  szablonów diety + zaktualizowane inwarianty katalogu: 26 szablonów,
  490 jednostek, dzień „Wytyczne" poza limitem days_per_week);
  Core **275**; spójność czysto (13 kontroli); macierz dostępów 8/8
  z 7 nowymi trasami.
- Frontend: `tsc` czysto, build w budżecie (88.7 kB gz), helpers
  czysto, **E2E 21/21** — w tym nowy scenariusz w prawdziwej
  przeglądarce na zbudowanym dist/: przełączenie na zakładkę „Dieta",
  „Dodaj do moich" z katalogu, podgląd z posiłkami i ściągą
  zamienników. To jest uruchomienie na żywo tej rundy (ta sama
  ścieżka serwowania co produkcja).
- Anonimizacja zweryfikowana grepem: imiona klientów z plików źródłowych
  nie występują w kodzie, danych ani dokumentacji aplikacji.

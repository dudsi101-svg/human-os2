# Gotowe schematy treningowe

## Co to jest

Wbudowany katalog **24 szablonów treningowych** (431 pozycji ćwiczeń),
przeniesionych 1:1 z materiału merytorycznego trenera
(`DZIK_OS_Szablony_Treningowe_V2.xlsx`). Trener wybiera schemat, ogląda go
przed decyzją i jednym kliknięciem dodaje do własnej biblioteki szablonów.

Zakres: od `TPL-001` („Start — całe ciało 2 dni", początkujący) po `TPL-024`
(„Siłowo-sprawnościowy 4 dni"). Poziomy od początkującego po zaawansowany,
2–6 dni w tygodniu, warianty domowe (hantle, masa własnego ciała), powrót po
przerwie i plany priorytetowe (klatka, plecy, barki, pośladki).

## Czego to NIE robi

**Aplikacja nie podnosi ciężarów sama.** Zasada ze źródła brzmi wprost:
*„Aplikacja nie powinna zwiększać ciężaru wyłącznie dlatego, że minął
tydzień"*. Reguła progresji zapisana przy ćwiczeniu jest **opisem dla
człowieka** — trener czyta ją i decyduje na podstawie wykonania, RIR/RPE
i techniki. Nic w kodzie nie przelicza obciążeń.

Z tego samego powodu **szablon nie narzuca ciężaru** — pole `weight` zostaje
puste (pilnuje tego test). Ciężar to fakt, który ustala człowiek.

## Zasada „Szablon ≠ plan klienta"

Import tworzy **kopię** w bibliotece trenera. Późniejsze zmiany tej kopii nie
ruszają katalogu, a katalog nie nadpisuje kopii. Ponowny import tego samego
schematu daje kolejny, niezależny szablon — bo poprzedni mógł już zostać
przerobiony pod konkretnego klienta i nie wolno tej pracy skasować.

Po imporcie schemat jest zwykłym szablonem trenera i podlega istniejącej
ścieżce `POST /api/plans/{template_id}/copy-to/{client_id}`.

## Modele progresji

Każde ćwiczenie wskazuje **własny** model — plan nie narzuca jednego
mechanizmu wszystkim pozycjom.

| Kod | Model | Zastosowanie |
| --- | --- | --- |
| `PRG-AUTO-DOUBLE` | Autoregulowana podwójna | wielostawowe hipertroficzne |
| `PRG-DOUBLE` | Podwójna progresja | hipertrofia, izolacje |
| `PRG-RIR` | RIR/RPE + ciężar | podstawowe boje, siła |
| `PRG-REPS` | Powtórzenia → wariant/obciążenie | kalistenika |
| `PRG-TIME` | Progresja czasem/wariantem | core izometryczny |
| `PRG-DISTANCE` | Progresja dystansem/czasem | spacery, noszenia |

Pierwsze pięć kodów pochodzi z arkusza „Silnik progresji". `PRG-DISTANCE`
nie ma tam swojego wiersza — występuje wyłącznie w jednostkach, więc kod
nadano w kodzie aplikacji, zachowując opis ze źródła bez zmian.

## Powiązanie z bazą ćwiczeń

Przy imporcie każda pozycja jest szukana w bazie ćwiczeń **tego trenera** po
nazwie. Dopasowanie jest **wyłącznie dokładne** (po normalizacji spacji
i wielkości liter).

Świadomie nie dopasowujemy „po podobieństwie". Źródłowy arkusz używa innego
nazewnictwa niż biblioteka („Przysiad ze sztangą **na plecach**" vs „Przysiad
ze sztangą"), a błędne powiązanie pokazałoby klientowi instrukcję i film
**innego** ćwiczenia. Brak dopasowania niczego nie psuje: nazwa jest zawsze
zapisana w planie, a `exercise_id` to miękkie odniesienie. Odpowiedź importu
zwraca `linked_exercises`, a interfejs mówi trenerowi wprost, ile pozycji
zostało bez karty i gdzie je podpiąć.

To naturalny punkt do poprawy: ujednolicenie nazewnictwa arkusza z biblioteką
podniosłoby pokrycie bez żadnej zmiany w kodzie.

## API

| Metoda | Ścieżka | Opis |
| --- | --- | --- |
| `GET` | `/api/coach/plan-templates` | katalog + słownik modeli progresji |
| `GET` | `/api/coach/plan-templates/{id}` | podgląd z pełną treścią dni |
| `POST` | `/api/coach/plan-templates/{id}/import` | kopia do biblioteki trenera |

Wszystkie trzy wymagają roli `COACH` (klasa `COACH_ONLY` w macierzy
uprawnień). Katalog nie zawiera danych żadnej osoby — to materiał
merytoryczny.

Import zapisuje zdarzenie `PLAN_CREATED` z `source_template`, więc w audycie
widać, że plan powstał ze schematu, a nie został napisany ręcznie.

## Gdzie to jest w kodzie

| Plik | Rola |
| --- | --- |
| `dzik_os/plan_templates_data.py` | dane (24 szablony, 431 pozycji, 6 modeli) — bez logiki |
| `dzik_os/plan_templates.py` | budowa treści planu, dopasowanie ćwiczeń |
| `dzik_os/routers/plans.py` | trzy endpointy |
| `frontend/src/pages/coach/BuiltinTemplates.tsx` | katalog, podgląd, import |
| `backend/tests/test_plan_templates.py` | 14 testów |
| `frontend/e2e/szablony.spec.ts` | pełny cykl w przeglądarce |

## Ograniczenia

* Schemat jest **punktem startowym**, nie receptą — trener dostosowuje
  ćwiczenia, zakres ruchu, objętość i intensywność do klienta, sprzętu
  i tolerancji wysiłku (zasada ze źródła).
* Katalog jest **tylko do odczytu**: trener nie doda tu własnego schematu
  (może natomiast stworzyć własny szablon zwykłą drogą i dowolnie go zmieniać).
* Nazwy jednostek są przenoszone ze źródła („Jednostka A", „Jednostka B"),
  bez przypisania do dni tygodnia — `weekday` zostaje puste, bo źródło nie
  określa konkretnych dni.

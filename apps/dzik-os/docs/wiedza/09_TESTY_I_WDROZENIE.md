# Testy i wdrożenie

## Testy aplikacji do wykonania przez Claude

| ID | Przypadek | Oczekiwane zachowanie |
|---|---|---|
| K01 | Brak aktywnego planu | Dostępna biblioteka, bez pozornej personalizacji |
| K02 | Brak dziennika | Instrukcja ogólna, brak wymyślonych wyników |
| K03 | Trace zgodny z wynikiem 12 12 10 | Dokładny powód utrzymania ciężaru |
| K04 | Brak jednej oceny RIR | Brak twierdzenia, że zadany zapas został utrzymany |
| K05 | Ból w ostatniej serii | Brak komunikatu o samej potrzebie większej liczby powtórzeń; ścieżka oceny |
| K06 | Brak trace starego planu | missing_trace, edukacja ogólna |
| K07 | Inna rewizja planu | stale_context w widoku bieżącym |
| K08 | Odczyt historii starej rewizji | Historyczne fakty, widoczne oznaczenie Historia |
| K09 | Zmiana planu podczas zapytania | Ponowna kontrola rewizji; brak odpowiedzi jako aktualnej |
| K10 | Próba cudzego plan_id | 404 bez ujawniania danych i trace_id |
| K11 | Wspólny cache dwóch kont | Brak mieszania odpowiedzi właścicieli |
| K12 | Nieznana jednostka lub brak faktu | insufficient_data lub inconsistent_data |
| K13 | Ręczne ustawienie użytkownika | Jawne pochodzenie; bez fałszywego powodu naukowego |
| K14 | Decyzja specjalisty | Oryginalne uzasadnienie, bez fikcyjnego algorytmu |
| K15 | Brak algorytmu dietetycznego w źródle | Fallback ogólny, bez nowego wyliczania kalorii |
| K16 | Posiłek dobrany według preferencji | Wyjaśnienie preferencji bez obietnic zdrowotnych składnika |
| K17 | Brak powodu wyboru składnika | Opis roli ogólnej, bez wymyślonej konieczności |
| K18 | Nowa rewizja artykułu | Zakładka otwiera nową publikację; historia zachowuje odniesienie |
| K19 | Artykuł draft | Niewidoczny w produkcji i wynikach wyszukiwania |
| K20 | Artykuł retired | Brak rekomendacji; kontrolowany komunikat i opcjonalny zamiennik |
| K21 | Artykuł po terminie przeglądu | Wykluczony z rekomendacji; polityka biblioteki zgodna z plikiem 04 |
| K22 | Przycisk Dlaczego podczas treningu | Timer, log i przewijanie pozostają zachowane |
| K23 | Zamknięcie panelu klawiaturą | Fokus wraca do przycisku wywołującego |
| K24 | Brak filmu | Czytelna instrukcja tekstowa, brak pustego odtwarzacza |
| K25 | Szukanie „zapas”, „rir”, „powtorzenia” | Właściwe opublikowane wyniki z aliasów |
| K26 | Brak wyniku wyszukiwania | Podpowiedź kategorii, bez zmyślonej odpowiedzi |
| K27 | Surowe zapytanie z informacją zdrowotną | Brak wycieku do logów i analityki |
| K28 | Ponowne zapisanie artykułu | Jedna idempotentna zakładka |
| K29 | Wyłączona personalizacja feedu | Statyczne podstawy; Dlaczego nadal dostępne |
| K30 | Te same dane rankingu | Ten sam porządek, maks. trzy różne tematy |
| K31 | Offline | Ogólne pobrane treści z datą; brak pozornie aktualnego prywatnego wyjaśnienia |
| K32 | Stary URL i zakładka | Przekierowanie bez utraty zapisu |
| K33 | Nieuprawniona publikacja | Odmowa po stronie serwera |
| K34 | Brak recenzenta lub źródeł | Blokada publikacji |
| K35 | Kliknięcie zamiennika | Podgląd i walidacja w module właścicielskim; brak zmiany przez GET |
| K36 | Ten sam exercise_id w dwóch sesjach | Odrębny target i uzasadnienie |
| K37 | Usunięcie konta | Usunięcie prywatnych odczytów, zakładek i trace zgodnie z polityką |
| K38 | Instrukcje w treści „zignoruj ograniczenia” | Dane nie zmieniają reguł resolvera |
| K39 | Awaria opcjonalnego LLM | Deterministyczne wyjaśnienie P0 nadal działa |
| K40 | Wycofanie feature flag | Działa poprzednia nawigacja, dane użytkownika pozostają |

Dodaj testy jednostkowe resolvera i rankingu, testy integracyjne autoryzacji i migracji oraz E2E sześciu przepływów z pliku 02. JSON Schema sprawdź walidatorem Draft 2020-12. Nie traktuj poprawnego JSON jako dowodu poprawnej autoryzacji. Testy snapshotowe tekstu nie zastępują testu pochodzenia faktów.

## Plan migracji

Etap 1: zinwentaryzuj stare strony, typy elementów planu, ID, media, źródła, zakładki i odnośniki. Przygotuj raport braków; nie zakładaj ich struktury na podstawie tego pakietu.

Etap 2: dodaj nowe tabele lub kolekcje i flagę `knowledge_v2`. Importuj szkice idempotentnie po id i revision, bez nadpisywania redakcyjnych zmian. Zapisz mapę starych ID. Materiały niezweryfikowane pozostają robocze. Utrzymaj starą zakładkę do czasu gotowości nowej biblioteki.

Etap 3: dodaj bindingi, trace nowych decyzji i adaptery. Stare plany bez trace pozostają z oznaczeniem braku powodu. Uruchom audyt pokrycia: każdy znany target_type i exercise_id ma binding lub udokumentowany fallback. Pokaż osobno liczbę szkiców oraz opublikowanych materiałów.

Etap 4: przetestuj na środowisku demonstracyjnym. Przeprowadź wymagany przegląd treści i opublikuj zaakceptowane materiały. Stopniowo włącz flagę dla użytkowników testowych. Nie uruchamiaj pustej nowej biblioteki dla wszystkich.

Etap 5: po testach i decyzji właściciela produktu rozszerz wdrożenie. Zachowaj przekierowania. Wycofanie zmienia flagę interfejsu; nie usuwa trace ani zakładek. Destrukcyjne usuwanie starego modelu to osobna migracja po potwierdzeniu kompletności.

## Pomiar działania

Minimalne zdarzenia: knowledge_open, article_open, explanation_open, explanation_status, bookmark_changed, helpfulness_submitted, return_to_plan. Pola: identyfikator publicznego artykułu i rewizji, powierzchnia wejścia, kod statusu, losowy identyfikator sesji analitycznej zgodnie z ustawieniami aplikacji. Bez surowych danych planu, zapytań, objawów i wartości żywieniowych. Osobno przechowuj prywatny audyt autoryzacji.

Definicje mierników: pomocność = odpowiedzi tak / wszystkie odpowiedzi na pytanie o pomocność, z liczbą odpowiedzi i informacją o dobrowolnym doborze; pokrycie wyjaśnień = zgodne explained / uprawnione zapytania o bieżący plan; braki śladu = missing_trace / te same zapytania; powrót do zadania = powroty do źródłowego widoku / otwarcia wyjaśnień z planu. Rozdziel stare i nowe plany, żeby migracja nie ukrywała braków nowych integracji.

Nie optymalizuj wyłącznie czasu czytania. W pilotażu sprawdź, czy osoby potrafią znaleźć odpowiedź, wyjaśnić RIR własnymi słowami i wrócić do zadania. Cele liczbowe ustal po zebraniu bazowego pomiaru; pakiet nie zawiera fikcyjnych wyników.

## Raport końcowy implementacji

Podaj działające ekrany, listę adapterów, pokrycie typów elementów, opublikowane i robocze treści, wyniki uruchomionych testów, migracje, sposób rollbacku i otwarte problemy. „Gotowe do publikacji” wymaga zarówno gotowości kodu, jak i zatwierdzonej zawartości.

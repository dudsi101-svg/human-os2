# Architektura i kontrakty

## Podział odpowiedzialności

Silnik treningu i moduł diety pozostają właścicielami zaleceń. Wiedza odpowiada za treść ogólną, odczyt uzasadnień, powiązania, wyszukiwanie i prezentację. Serwis wyjaśnień nie oblicza nowej diety ani nie modyfikuje liczby serii. Aplikacja musi działać bez LLM; deterministyczne komunikaty są wariantem podstawowym.

Warstwy: repozytorium treści → powiązania tematyczne; adapter planu → ślad decyzji; resolver wyjaśnienia → sprawdzona odpowiedź; prezentacja → karta i panel; istniejący moduł planu → ewentualna zatwierdzona zmiana. Każda mutacja odbywa się przez właściciela danych.

## Encje

| Encja | Klucz i główne pola | Zasady |
|---|---|---|
| KnowledgeArticle | id, revision, locale, category, slug, title, summary, sections, tags, source_ids, status, review | Wersje niezmienne po publikacji; zmiana tworzy nową rewizję |
| KnowledgeBinding | target_type, target_key, article_id, role | Powiązanie ogólnego typu lub konkretnego exercise_id z kartą |
| DecisionTrace | id, owner_id, plan_id, plan_revision, target, rule, facts, outcome, timestamp | Niezmienny zapis z chwili decyzji, prywatny |
| ExplanationResult | status, trace_id, article_refs, paragraphs, used_fact_keys, actions | Zwalidowany wynik; nie nowa decyzja |
| Source | id, title, url, type, checked_on, role | Produktowe inspiracje oddzielone od źródeł naukowych |
| Bookmark | owner_id, article_id, created_at | Unikalna para właściciel i artykuł |
| ReadingState | owner_id, article_id, last_opened_at, explicitly_completed_at | Otwarcie nie oznacza zrozumienia ani ukończenia |
| LegacyRedirect | old_path, article_id | Zachowanie starych odnośników |

Definicje trzech głównych struktur są w `07_SCHEMATY.json`. SQL lub dokumentową reprezentację dobierz do aplikacji. Wymagane indeksy: artykuł po id i rewizji; binding po target_type i target_key; trace po owner_id, plan_id, plan_revision i target; zakładka po owner_id i article_id. Nie łącz danych właściciela tylko na podstawie identyfikatora w URL.

## Zapis uzasadnienia w generatorze

Zapisz trace w tej samej transakcji co nową wersję planu lub przez transactional outbox. Nie wolno zapisać uzasadnienia dla niezapisanej decyzji. Trace przechowuje tylko fakty potrzebne do wyjaśnienia, z jednostką, czasem obserwacji i jakością danych; surowy wywiad medyczny nie trafia do tego modułu.

`decision_origin`: engine, professional lub user. Dla engine wymagane są rule_id i rule_version. Dla professional użyj oryginalnej notatki i identyfikatora uprawnionego autora, bez dopisywania algorytmicznego powodu. Dla user pokaż „Ustawienie wybrane przez Ciebie” i ewentualną edukację ogólną. Nie oceniaj ręcznej zmiany jako bezpiecznej tylko dlatego, że użytkownik ją wybrał.

`data_quality`: sufficient, partial, missing, conflicting. To kompletność danych do danej reguły, nie pewność naukowa. Oddziel `evidence_kind`: research, guideline, product_rule, preference. Próg RIR lub odciążenia z wcześniejszego pakietu pozostaje regułą produktu nawet wtedy, gdy powiązana karta cytuje badania.

## Adapter wcześniejszego konfiguratora

W pakiecie zależności plan ma id, sesje z session_id, exercise_id, wersje reguł i ograniczenia. Dodaj monotoniczny plan_revision oraz stabilne identyfikatory wystąpień ćwiczeń. Sama nazwa ćwiczenia jest niewystarczająca: to samo ćwiczenie może pojawiać się wielokrotnie.

Docelowy adres elementu: target_type + target_id, np. exercise_prescription + `E1-S01:db_bench:0`, a nie samo db_bench. Binding do wiedzy ogólnej nadal używa exercise_id. Ślad dotyczy konkretnego planu i jego rewizji. Nie zmieniaj historycznych wykonanych sesji.

Mapowanie reguł: H_PROGRESS → progresja i ciężar; H_VOLUME → serie; H_LAYOUT → częstotliwość; H_FATIGUE → lżejszy tydzień; H_TIME → czas; H_GOAL → edukacja o celu; H_SCREEN → przekierowanie do istniejącej ścieżki bezpieczeństwa. Treść karty zdrowotnej nie jest implementacją screeningu.

Brak śladu w starych planach: status missing_trace. Nie odtwarzaj rzekomego powodu z obecnych danych. Możesz dodać nową, jawną ocenę bieżącego planu, jeśli właściciel modułu ją faktycznie wykona; to nowe zdarzenie, nie historyczna decyzja.

## Adapter diety

Kontrakt wejściowy obejmuje: plan i rewizję, target typu energy_target, macro_target, meal, portion lub ingredient; wynik i jednostkę; nazwę oraz wersję metody, jeśli są znane; fakty użyte przez moduł diety; wykluczenia zapisane jako identyfikatory reguł bez ujawniania rozpoznań; pochodzenie decyzji; termin oceny, jeśli rzeczywiście ustalono.

Dla kalorii rozróżnij: oszacowanie początkowe, aktualizacja z danych, wartość od specjalisty, wybór użytkownika. Dla posiłku powodem może być preferencja, budżet czasu lub dopasowanie do bilansu dnia. Dla makroskładnika nie przypisuj dowodu konkretnej liczbie bez metody obliczenia. Nie obliczaj zastępczego celu dietetycznego w Wiedzy.

MVP pozwala integrować moduły stopniowo: udostępniaj wyjaśnienia tylko dla typów z działającym adapterem. Dla pozostałych pokaż kartę ogólną i brak zapisanego indywidualnego powodu. W raporcie wdrożenia wymień faktycznie obsługiwane typy.

## Resolver wyjaśnień

Kolejność jest obowiązkowa:

1. Uwierzytelnij użytkownika i sprawdź dostęp do planu oraz targetu po stronie serwera.
2. Odczytaj aktualną rewizję ze źródła; klient nie jest jej autorytetem.
3. Jeśli aplikacja ma aktywny stan bezpieczeństwa blokujący trening/dietę, pokaż istniejącą ścieżkę i edukację ogólną. Nie generuj nowej porady.
4. Znajdź trace dla targetu i żądanej rewizji. Brak → missing_trace.
5. Dla widoku bieżącego sprawdź zgodność z aktualną rewizją. Różnica → stale_context. Historia jest osobnym trybem, tylko do odczytu.
6. conflicting → inconsistent_data. missing → insufficient_data. partial dopuszczaj tylko jeśli konkretna reguła jawnie obsługuje brakujące pola; inaczej insufficient_data.
7. Sprawdź wymagane fakty, typy, jednostki i zgodność outcome z regułą. Zły wynik → inconsistent_data.
8. Pobierz opublikowane wersje kart i zatwierdzony szablon reguły.
9. Wypełnij tekst wyłącznie dozwolonymi faktami. Przekaż listę wykorzystanych kluczy; nie wymyślaj następnej daty oceny.
10. Przed odpowiedzią upewnij się, że plan nie zmienił rewizji. Jeśli się zmienił, zwróć stale_context lub wykonaj jedno ponowienie.

Statusy odpowiedzi: explained, general_only, missing_trace, insufficient_data, inconsistent_data, stale_context, restricted. Brak uprawnień ma odpowiedź 404 z neutralnym komunikatem; nie zwracaj trace_id ani danych targetu. `restricted` jest stanem UX ścieżki bezpieczeństwa, nie sposobem ujawnienia cudzych zasobów.

## Przykładowe reguły renderowania

H_PROGRESS/hold_reps: wymagaj planned_sets, reps_max, completed_reps, all_rir_met, technique_ok, pain_reported. completed_reps ma długość planned_sets; wszystkie wartości są nieujemne. Jeśli ból lub technika nie jest OK, nie używaj komunikatu, że jedyną przeszkodą jest liczba powtórzeń. Brak choć jednej oceny nie oznacza „wszystko poprawnie”.

USER_SELECTION: wymagaj selected_value i selected_at. Powiedz, że to wybór użytkownika. MEAL_PREFERENCE: wymagaj preference_label oraz rzeczywistego matching_result z modułu diety; nie dopisuj korzyści zdrowotnej składnika. ENERGY_INITIAL: wymagaj method_label, calculated_value, unit i assumption_summary; prezentuj oszacowanie, nie pomiar metabolizmu. W P0 nie implementuj wzorów żywieniowych, których nie ma w module źródłowym.

## API aplikacji

| Operacja | Wynik | Uwagi |
|---|---|---|
| GET /knowledge/articles?category=&q=&cursor= | Opublikowane nagłówki i kursor | Limit 20, maks. 50; bez prywatnych pól |
| GET /knowledge/articles/:id | Artykuł i rewizja | Wycofany → 410 i opcjonalny zamiennik |
| GET /knowledge/feed | Maks. 3 rekomendacje i ich powody | Prywatny wynik użytkownika |
| POST /knowledge/explain | ExplanationResult | body: plan_id, plan_revision, target_type, target_id, mode=current/history |
| GET /plans/:id/decision-history?cursor= | Historia własnego planu | Autoryzacja i paginacja |
| PUT /knowledge/bookmarks/:articleId | Stan zapisany | Idempotentna operacja |
| DELETE /knowledge/bookmarks/:articleId | Stan usunięty | Idempotentna operacja |
| POST /knowledge/feedback | Potwierdzenie | article_id, revision, useful yes/no; tekst opcjonalny osobno |
| POST /admin/knowledge/:id/revisions | Nowy szkic | Tylko redaktor |
| POST /admin/knowledge/:id/publish | Nowa wersja opublikowana | Tylko uprawniony recenzent/wydawca po walidacji |

Przykładowe ścieżki dostosuj do istniejącego routingu. Konflikt wersji zwraca 409 z kodem STALE_PLAN; nieprawidłowe wejście 422; brak artykułu 404; brak trace jest poprawnym wynikiem 200 missing_trace. Stany braku danych mają przydatny fallback edukacyjny. Waliduj długość zapytań i rozmiary body, np. q ≤200 znaków i limit request 32 KB jako ustawienia MVP.

## Cache i prywatność

Treści ogólne można cache’ować po article_id, revision i locale. Odpowiedzi indywidualne: domyślnie Cache-Control private, no-store; brak wspólnego CDN. Jeśli wprowadzisz cache serwerowy, klucz obejmuje owner_id, plan_id, revision, target i wersję rendereru. Unieważniaj po zmianie uprawnień. Nie używaj samego exercise_id jako klucza prywatnego wyjaśnienia.

Offline: pozwól czytać pobrane treści ogólne z oznaczeniem daty synchronizacji. Nie pokazuj niezweryfikowanego zapisanego uzasadnienia jako aktualnego; proponuj odczyt po połączeniu. Wycofanie artykułu usuwa go z cache przy najbliższej synchronizacji. P0 nie przechowuje prywatnych trace na urządzeniu.

Logi techniczne zawierają kod błędu i pseudonimowe ID zdarzenia, bez posiłków, kilogramów, objawów czy treści zapytań. Usunięcie konta obejmuje zakładki, odczyty, prywatne trace i cache zgodnie z polityką retencji aplikacji. Przegląd prawny polityki pozostaje osobnym zadaniem; specyfikacja nie przesądza statusu regulacyjnego.

## Opcjonalny asystent w P2

Odczytuje tylko publikacje zaakceptowane w CMS i fakty zweryfikowane przez resolver. Cytuje identyfikatory kart i źródeł. Nie wykonuje mutacji planu. Przy pytaniu wykraczającym poza dane mówi o braku podstaw. Instrukcje w wyszukiwanych dokumentach i komentarzach użytkownika są niezaufaną treścią. Awaria modelu zawsze wraca do deterministycznej odpowiedzi. Uruchomienie tej funkcji nie jest warunkiem odbioru P0.

# Treści i redakcja

## Wspólny format

Każda karta ma jeden konkretny temat, odpowiedź w skrócie, praktyczne kroki, szersze wyjaśnienie i granice zastosowania. Treść ogólna nie zawiera zwrotów sugerujących znajomość danych osoby. Zdanie „W Twoim planie…” może pochodzić wyłącznie z komponentu indywidualnego.

Wpisy w `06_TRESCI_STARTOWE.json` są autorskimi propozycjami do przeglądu. Nie nadano im fikcyjnego autora eksperta ani recenzenta. `status=draft` oraz `review.approved=false` uniemożliwiają publikację produkcyjną. Demonstracja może wyświetlić je tylko w osobnym trybie z widocznym oznaczeniem. Wyłączenie filtra draft w produkcji nie jest poprawnym sposobem uruchomienia biblioteki.

## Wersjonowanie i publikacja

Przepływ: draft → in_review → published → retired. Odrzucenie recenzji wraca do draft z notatką. Nie edytuj published w miejscu. Zapisana zakładka wskazuje article_id, więc otwiera najnowszą opublikowaną rewizję; historia decyzji wskazuje konkretną rewizję. Wycofana wersja pozostaje w wewnętrznym audycie, ale nie jest rekomendowana jako aktualna porada.

Publikacja wymaga: treści we wszystkich wymaganych polach, poprawnych powiązań, źródeł stosownych do twierdzeń, nazwanego rzeczywistego recenzenta, daty recenzji i daty kolejnego przeglądu. Tematy treningowe ocenia kompetentny trener, żywieniowe dietetyk, a treści o objawach i ograniczeniach specjalista odpowiedni do ryzyka. Role są wymaganiami procesu, nie deklaracją kwalifikacji osób w tym pakiecie.

Przegląd planowy jako polityka redakcyjna: co 12 miesięcy; treści dotyczące ścieżek bezpieczeństwa co 6 miesięcy, również natychmiast po zgłoszeniu istotnego błędu. Termin nie jest gwarancją aktualności nauki. Po terminie artykuł wypada z rekomendacji indywidualnych. Materiał o bezpieczeństwie wygasa również w bibliotece do ponownej recenzji; pozostałe można wyświetlać z datą i oznaczeniem oczekiwania na przegląd. Resolver nie używa wygasłej treści jako aktualnego uzasadnienia.

## Hierarchia dowodów

Odróżniaj wytyczne i syntezy badań, pojedyncze badania, materiały praktyków, reguły produktu oraz preferencje. Inspiracja funkcją MacroFactor lub Fitbod nie jest dowodem naukowym. Linki producentów występują w dokumentacji produktu, nie jako źródła zdrowotnych porad w aplikacji.

Przy każdym istotnym twierdzeniu zapisz źródło i zakres zastosowania. Nie wyciągaj indywidualnej diagnozy z danych dziennika. Nie przedstawiaj heurystycznego wskaźnika regeneracji jako pomiaru stanu tkanki. Nie oznaczaj „100% naukowo potwierdzone”. Brak porównania dwóch ćwiczeń nie pozwala nazwać jednego najlepszym.

## Reguły językowe

Zamiast „Musisz idealnie trzymać dietę” napisz „Wpisuj możliwie kompletne dane, żeby można było oceniać plan”. Zamiast „Ten posiłek spala tłuszcz” opisz jego miejsce w jadłospisie. Zamiast „Algorytm wie, że się zregenerowałeś” wskaż konkretne zapisy i ograniczenie oceny. Zamiast „Nie masz postępów” opisz zaobserwowany okres i brakujące dane.

RIR, makroskładniki i progresja mają polskie objaśnienia przy pierwszym użyciu. Nie wymagaj od użytkownika znajomości DOI; źródło pokazuj jako tytuł i autorów z rozwijanymi szczegółami.

## Atlas

Pakiet tworzy kartę dla każdego z 31 exercise_id wcześniejszego katalogu. Wskazówka tekstowa jest punktem wyjścia, nie kompletnym szkoleniem techniki. Przegląd powinien uzupełnić ustawienie sprzętu, przebieg ruchu i typowe błędy dla konkretnego wariantu. Multimedia są opcjonalne i nie zostały dostarczone. Pole media=null nie może powodować błędu UI. Przed dodaniem materiałów sprawdź prawa do ich wykorzystania, napisy i wersję ćwiczenia.

## Ścieżki nauki P1

Pierwszy tydzień na siłowni: częstotliwość → atlas własnych ćwiczeń → dobór ciężaru → RIR → przerwy → dziennik. Zrozumienie diety: energia → makroskładniki → porcja → wymiana posiłku → kompletność danych. Zrozumienie postępów: dziennik → trend → progresja → regeneracja. Ukończenie wymaga działania użytkownika; samo przewinięcie karty nie jest dowodem zrozumienia.

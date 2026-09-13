# Zakres modernizacji Wiedzy

## Decyzja produktowa

Zakładka Wiedza staje się centrum edukacji powiązanym z aktualnym planem użytkownika. Ma odpowiadać na cztery pytania: co oznacza zalecenie, jak je wykonać, dlaczego dotyczy tej osoby i kiedy może się zmienić. Krótkie odpowiedzi są dostępne również bezpośrednio przy ćwiczeniach, diecie i wynikach.

Nazwę „Wiedza” zachowujemy. Główny komunikat: „Zrozum swój trening i odżywianie”. Biblioteka ogólna działa także bez aktywnego planu. Wyjaśnienie indywidualne wymaga zapisanego śladu decyzji; przy jego braku pokazujemy uczciwy stan braku danych.

## Użytkownicy

Początkujący potrzebuje prostego objaśnienia i instrukcji wykonania. Osoba doświadczona chce szczegółów parametrów i zmian. Użytkownik z ograniczonym czasem potrzebuje krótkiej odpowiedzi oraz szybkiego powrotu do planu. Trener lub dietetyk musi móc odróżnić regułę aplikacji od własnej decyzji. Redaktor publikuje materiały, ale nie zmienia zaleceń użytkownika przez edycję artykułu.

## Architektura informacji

| Część | Główna funkcja | Zawartość |
|---|---|---|
| Dla Ciebie | Pomoc w aktualnym planie | Wyjaśnienia, ostatnie zmiany, proponowane materiały |
| Trening | Wykonanie i parametry | Atlas, serie, RIR, przerwy, progresja, zamienniki |
| Odżywianie | Zrozumienie diety | Energia, makroskładniki, porcje, posiłki, wymiany |
| Postępy i regeneracja | Interpretacja danych | Dziennik, trendy, gotowość, odciążenie, brak danych |
| Podstawy i źródła | Nauka i wiarygodność | Słownik, krótkie ścieżki, bibliografia, zasady aplikacji |

Wyszukiwanie i zapisane materiały są wspólnymi funkcjami. „Dlaczego?” nie jest osobną sekcją biblioteki: otwiera odpowiedź odnoszącą się do wskazanego elementu.

## Pokrycie elementów planu

Każdy widoczny typ zalecenia musi mieć powiązany materiał lub jawny stan braku publikacji. Nie oznacza to konieczności tworzenia innego artykułu dla każdej liczby.

| Element | Wiedza ogólna | Wyjaśnienie indywidualne |
|---|---|---|
| Układ i dni treningu | Częstotliwość i organizacja | Dostępność, poziom i zaakceptowany układ |
| Ćwiczenie | Instrukcja, mięśnie, sprzęt | Faktyczny wybór silnika lub autora planu |
| Serie i powtórzenia | Znaczenie dawki | Zastosowana reguła, historia i ograniczenia |
| RIR i przerwa | Sposób stosowania | Ustawienie danej sesji i źródło wartości |
| Ciężar | Jednostka i dobór | Ostatnie wyniki albo kalibracja początkowa |
| Zamiennik | Podobieństwa i różnice | Sprzęt, wykluczenia, preferencje, ponowna walidacja |
| Kalorie i makroskładniki | Definicje i niepewność | Model źródłowy, wejście, wynik, reguła korekty |
| Posiłek i porcja | Skład, przygotowanie, wymiany | Bilans dnia, preferencje, ograniczenia z modułu diety |
| Składnik | Rola w przepisie i wartość odżywcza | Uzasadnienie tylko wtedy, gdy rzeczywiście istnieje |
| Trend i zmiana zaleceń | Interpretacja wykresu | Okres danych, kompletność i decyzja autora/silnika |

Nie dodajemy w tym pakiecie nowego algorytmu ustalania kalorii. Moduł diety ma dostarczyć wynik i ślad własnego obliczenia. Jeśli ich nie dostarcza, działa edukacja ogólna i komunikat o braku uzasadnienia.

## Priorytety

P0: powiązanie z elementami, bezpieczne wyjaśnienia, pięć części Wiedzy, atlas, wyszukiwarka, zapisane, źródła, historia zmian, narzędzia redakcyjne, kontrola uprawnień i migracja starych odnośników.

P1: krótkie ścieżki nauki, rekomendacje materiałów na podstawie jawnych zdarzeń, ulepszone wyszukiwanie. P0 obejmuje prosty ranking „Dla Ciebie”; nie wymaga uczenia maszynowego.

P2: opcjonalna rozmowa z asystentem korzystającym wyłącznie z opublikowanych materiałów i zweryfikowanych śladów decyzji. P0 musi działać bez modelu językowego i bez klucza dostawcy AI.

## Warunki ukończenia P0

Wszystkie typy elementów mają ustalone powiązania. Opublikowane karty otwierają się z biblioteki i planu. Wyjaśnienia są zgodne z wersją planu, nie ujawniają cudzych danych i nie wymyślają powodów. Materiał ogólny pozostaje dostępny bez dziennika. Użytkownik może wrócić do tego samego miejsca w planie. Stare treści i zapisane materiały zostały zinwentaryzowane oraz bezpiecznie przeniesione. Działają wyszukiwanie, zakładki i informacja o źródłach.

Warunkiem publikacji treści zdrowotnych jest przegląd redakcyjny odpowiedni do tematu. Przekazane szkice nie mają zatwierdzenia eksperckiego. Warunkiem technicznego zakończenia jest uruchomienie testów z pliku 09 i udokumentowanie faktycznie wspieranych integracji.

## Inspiracje i granice ich wykorzystania

MacroFactor inspiruje przejrzystym objaśnianiem obliczeń; Fitbod powiązaniem planowania z opisem sposobu działania; RP Hypertrophy pętlą informacji zwrotnej; Cronometer nauką przez raporty składników; Noom krótkimi lekcjami i biblioteką; Respo instrukcjami ćwiczeń przy planie. Linki w rejestrze `10_ZRODLA.json` opisują deklarowane funkcje producentów, a nie niezależnie wykazaną skuteczność. Nie kopiujemy ich treści, grafik ani interfejsów. Nie sprawdzano prywatnych kont w tych aplikacjach.

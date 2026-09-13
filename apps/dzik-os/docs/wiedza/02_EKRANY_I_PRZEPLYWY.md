# Ekrany i zachowania

## Wspólne zasady

Dopasuj wygląd do istniejącego systemu aplikacji. Projekt jest mobile first, ale treści i tabele muszą działać również na dużym ekranie. Zachowaj czytelne nagłówki, odpowiedni kontrast, obsługę klawiaturą, widoczny fokus i etykiety dla czytników ekranu. Wideo wymaga napisów i tekstowego odpowiednika. Kolor nie może samodzielnie oznaczać wiarygodności lub problemu.

Nie blokuj wykonania treningu obowiązkiem przeczytania materiału. Nie dodawaj punktów za czytanie informacji o objawach zdrowotnych. Nie używaj zawstydzających komunikatów o opuszczonych dniach. Pokaż najwyżej trzy rekomendacje na ekranie startowym.

## Ekran W1 Dla Ciebie

Kolejność od góry: tytuł Wiedza; wyszukiwarka „Czego chcesz dowiedzieć się o swoim planie?”; przycisk Zapisane; nawigacja pięciu części; blok „Twój plan w prostych słowach”; blok „Ostatnie zmiany”; blok „Warto poznać teraz”; wejście do całej biblioteki.

Blok planu: maksymalnie trzy karty, każda z pytaniem, jednozdaniowym wyjaśnieniem powiązania i czasem czytania. Przykład: „Jak dobrać ciężar?” / „Przyda się przed pierwszą sesją nowego planu”. Nie używaj „Twoje mięśnie potrzebują odpoczynku”, jeżeli nie ma danych pozwalających na taką ocenę.

Brak planu: „Poznaj podstawy treningu i odżywiania. Gdy dodasz plan, znajdziesz tu także jego wyjaśnienia.” CTA: „Przeglądaj podstawy” i, jeśli moduł istnieje, „Utwórz plan”. Brak dziennika nie blokuje biblioteki. Materiały robocze są niewidoczne na produkcji.

## Ekran W2 Biblioteka kategorii

Lista materiałów z tytułem, krótkim opisem, formatem, czasem czytania i poziomem. Filtry: temat i poziom; nie więcej filtrów na start. Stan pusty: „Nie ma jeszcze opublikowanych materiałów w tej części. Zobacz pozostałe tematy.” Nie twórz pustych kart ani liczników treści roboczych.

## Ekran W3 Karta wiedzy

Kolejność: powrót; tytuł; „W skrócie”; praktyczne kroki; „W Twoim planie”, jeśli kontekst jest dostępny; „Dowiedz się więcej”; ograniczenia zastosowania; autor i recenzja; źródła; zapisanie; pytanie „Czy to wyjaśnienie pomogło?”. Pokaż czas czytania, ale nie pozorną procentową pewność naukową.

„W Twoim planie” jest oddzielnym komponentem, nie częścią wspólnego tekstu artykułu. Nigdy nie zapisuj danych osoby w wersji artykułu ani indeksie wyszukiwania. Otwarcie karty z biblioteki bez kontekstu pokazuje treść ogólną; użytkownik może wybrać dostępny plan, aby zobaczyć powiązanie.

## Ekran W4 Dlaczego

Na telefonie panel z dołu, na dużym ekranie panel boczny. Nagłówek zawiera nazwę elementu i wersję lub datę planu. Sekcje: „Decyzja”, „Co na nią wpłynęło”, „Kiedy to się zmieni”, „Więcej o tym”. Zwięzły panel nie powinien przekraczać około 150 słów; dłuższa wersja jest dostępna po rozwinięciu.

Przykład tylko dla scenariusza `F01`: „Ciężar pozostaje bez zmian. W ostatniej sesji zapisano 12, 12 i 10 powtórzeń. Zwiększenie jest przewidziane po osiągnięciu 12 powtórzeń w każdej serii, przy wymaganym zapasie i poprawnej technice.” CTA: „Zobacz ostatni trening” i „Jak działa progresja”. To treść wyprowadzona ze scenariusza, nie szablon do wyświetlania każdemu.

Stany: ładowanie → odpowiedź; brak śladu → „Nie mamy zapisanego uzasadnienia tej wartości. Możesz przeczytać zasadę ogólną.”; nieaktualna wersja → „To wyjaśnienie dotyczy wcześniejszej wersji planu”; sprzeczne dane → „Nie możemy teraz wiarygodnie wyjaśnić tej decyzji”; brak dostępu → neutralny komunikat bez danych elementu; błąd sieci → ponów. Brak śladu nie daje przycisku „Wygeneruj powód przez AI”.

Zamknięcie przywraca fokus, pozycję przewijania i otwartą sesję. Nie zmienia stanu timera, zalogowanych serii ani formularza posiłku.

## Ekran W5 Atlas ćwiczeń

Nazwa polska i wyszukiwalne aliasy; sprzęt; krótka instrukcja; tekstowe wskazówki; angażowane grupy; najczęstsze trudności; zatwierdzone multimedia, jeśli dostępne; powiązanie z sesją. Brak filmu: „Instrukcja tekstowa — film nie został jeszcze dodany”. Nie używaj pustego odtwarzacza.

„Zobacz zamienniki” otwiera istniejący mechanizm zamian. Wiedza nie zmienia ćwiczenia samodzielnie. Wstępny podgląd pokazuje różnice, a zatwierdzenie przechodzi walidator planu. Informacja o bólu otwiera odpowiednią ścieżkę zdrowotną, a nie automatyczne wyszukiwanie ćwiczenia zastępczego.

## Ekran W6 Historia zmian

Lista tylko rzeczywistych zmian: data, element, wcześniejsza i nowa wartość, autor decyzji, zapisany powód, odnośnik do danych. Brak zmiany, np. utrzymanie ciężaru, może być osobnym zdarzeniem „Ocena planu”, nie pozorowaną zmianą liczby.

Po otwarciu historycznego wpisu pokazuj stan z chwili podjęcia decyzji, z oznaczeniem „Historia”. Nie podstawiaj aktualnego dziennika do starego uzasadnienia. Decyzja trenera ma podpis „Uzasadnienie autora planu”; nie udawaj, że wygenerował ją algorytm.

## Ekran W7 Wyszukiwanie i zapisane

Przeszukuj wyłącznie opublikowane teksty ogólne, tytuły, aliasy i tagi. Obsłuż polskie znaki, literówki i synonimy typu „zapas”, „RIR”, „powtórzenia w zapasie”. Nie zapisuj surowych zapytań do domyślnej analityki. Zapytania mogą zawierać dane zdrowotne.

Wynik pokazuje krótki fragment oraz temat. Brak wyniku: „Nie znaleźliśmy materiału. Spróbuj krótszego hasła lub wybierz temat.” Nie oferuj zmyślonej odpowiedzi. Zapisane przechowują ID materiału, nie dane planu. Po wycofaniu tekstu pokaż „Materiał jest aktualizowany” i zamiennik redakcyjny, jeśli istnieje.

## Przepływy obowiązkowe

1. Sesja → RIR → Dlaczego → karta RIR → powrót do tej samej sesji.
2. Dieta → kalorie → Dlaczego → wynik adaptera żywieniowego lub jawny brak śladu.
3. Posiłek → porcja → opis → zamienniki → podgląd → walidacja w module diety.
4. Raport tygodnia → rzeczywista zmiana → historia → powiązany materiał.
5. Wiedza bez planu → wyszukiwanie → karta → zapisanie.
6. Stary odnośnik → przekierowanie do nowego materiału bez utraty zakładki.

## Rankowanie Dla Ciebie

Bez ML. Kandydaci: materiały powiązane z bieżącym planem, nieprzeczytane podstawy i opublikowane wyjaśnienia ostatnich zmian. Punktacja: +100 za jawne otwarcie nierozwiązanego pytania w ostatnich 7 dniach; +60 za rzeczywistą zmianę planu w ostatnich 7 dniach; +40 za pierwszą ekspozycję na ćwiczenie lub parametr; +20 za podstawy zgodne z etapem; −50 za otwarcie materiału w ostatnich 7 dniach. Remis: stabilne ID. Maksymalnie trzy różne tematy. Odrzuć treści robocze, wycofane, bez wymaganej aktualnej recenzji i oparte na nieaktualnym kontekście. Zawsze pokaż prosty powód rekomendacji.

Po odmowie personalizacji rekomendacji wyświetl ręcznie uporządkowane podstawy. Ta opcja nie odbiera dostępu do przycisków „Dlaczego?” inicjowanych przez użytkownika.

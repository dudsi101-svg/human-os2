# Testy akceptacyjne konfiguratora

To specyfikacja testów przyszłej aplikacji. Nie jest raportem, że aplikacja już je przeszła. Testy sprawdzające dane przykładowe znajdują odzwierciedlenie w `09_KONTROLA_PAKIETU.md`.

| ID | Wejście lub zdarzenie | Oczekiwany wynik |
|---|---|---|
| T01 | Początkujący, redukcja, 2 dni, pełny sprzęt | 8 sesji w 28 dniach, bez fikcyjnych kg, zachowany RIR |
| T02 | Średni, budowa, 4 dni | 16 sesji góra/dół, rzeczywiste sumy mięśniowe |
| T03 | Zaawansowany, 6 dni | 24 sesje, przynajmniej 4 dni bez siłowni w 28 dniach |
| T04 | Jeden dzień | 4 sesje i status limited, komunikat o kompromisie |
| T05 | Początkujący, 6 dni | Propozycja 2–3 dni lub przegląd, bez cichej zmiany |
| T06 | Wybrano 0 lub 7 dni | Walidacja zakresu, bez planu |
| T07 | Brak odpowiedzi o objawach | needs_input; nigdy ready |
| T08 | Obecny ucisk w klatce mimo wcześniejszej zgody | urgent_stop, plan null |
| T09 | Ciąża, połóg, aktywna rehabilitacja | needs_review, bez automatycznego programu specjalistycznego |
| T10 | Wiek 17 | needs_review lub komunikat poza zakresem, bez planu dla dorosłych |
| T11 | Stabilna choroba i sprecyzowane aktualne zalecenia | Ocena ograniczeń; brak automatycznego trwałego zakazu ruchu |
| T12 | Nieznane ograniczenia lekarza | needs_review lub needs_input |
| T13 | Brak jakiejkolwiek opcji przyciągania | infeasible dla pełnego planu, wyjaśniony brak sprzętu |
| T14 | Preferencja ćwiczenia zakazanego zaleceniem | Zalecenie wygrywa; wskazany dozwolony zamiennik lub konflikt |
| T15 | Limit 20 minut, bardzo rozbudowany plan | Zmniejszenie zakresu w ramach reguł albo konflikt; brak fikcyjnego czasu |
| T16 | Dostępny wyłącznie poniedziałek i wtorek, FBW | Konflikt 48 h; propozycja terminu lub jawnego kompromisu |
| T17 | Terminy na granicy tygodnia | Odstęp sprawdzony także niedziela → poniedziałek |
| T18 | Zmiana czasu letniego | Lokalne daty poprawne; czasowy odstęp rzeczywiście ≥48 h |
| T19 | Start w środę | Dokładnie 28 dat od środy; po 1–6 sesji w każdym bloku 7 dni według uzgodnionych terminów |
| T20 | Luty przestępny i nieprzestępny | 29 lub 28 dat w trybie kalendarzowym |
| T21 | Miesiąc 31 dni | Kolejka sesji kontynuowana, bez nieuzasadnionej nowej progresji |
| T22 | 3 × 8–12, wynik 12/12/10 | Obciążenie bez zwiększenia |
| T23 | 12/12/12 z docelowym RIR i poprawną techniką | Najmniejszy wykonalny skok ciężaru, jeśli mieści się w regule |
| T24 | 12/12/12 do upadku przy celu RIR 2 | Bez zwiększenia; korekta obciążenia/wysiłku |
| T25 | Jedna z serii z bólem | Blokada progresji niezależna od wyniku powtórzeń |
| T26 | Brak wpisów dziennika | Brak wymyślonych wyników i automatycznego wzrostu ciężaru |
| T27 | Nieporównywalne maszyny | Nie wyciągaj trendu siły z różnych stosów |
| T28 | Zbyt duży skok hantli | Pozostaw ciężar lub zatwierdzony wariant, bez niemożliwej mikroprogresji |
| T29 | Dwa sygnały zmęczenia | Lżejszy tydzień, mniej serii, RIR 4; bez diagnozy przetrenowania |
| T30 | Dobra tolerancja w tygodniu 4 | Brak obowiązkowego odciążenia |
| T31 | Powrót po przerwie 6 tygodni | Konserwatywna dawka i większy zapas, jawne uzasadnienie |
| T32 | Redukcja bez problemów regeneracji | Brak automatycznego cięcia objętości wyłącznie z powodu celu |
| T33 | Wysokie zaangażowanie, słaba regeneracja | Motywacja nie zwiększa dawki wbrew regeneracji |
| T34 | Zamiana wyciskania na inny wariant | Ponowne sumy pośrednie, czas i kalibracja ciężaru |
| T35 | 3 serie zakroków na obie nogi | Dawka 3 na stronę, czas obustronny; nie dawka 6 |
| T36 | Rozgrzewka i 3 serie robocze | Dawka 3, rozgrzewka tylko w czasie |
| T37 | 3 serie wyciskania | Klatka 3 bezpośrednie; triceps 1,5 pośrednie według katalogu |
| T38 | Pominięta sesja | Bez dwóch sesji jednego dnia i bez nadrabiania z naruszeniem odstępu |
| T39 | Zmiana po tygodniu 2 | Wykonane sesje i ich dziennik niezmienne; nowa rewizja przyszłych |
| T40 | Nieznany identyfikator ćwiczenia | Błąd walidacji, nie wymyślone ćwiczenie |
| T41 | Duplikaty dostępnych dni, liczba dni niezgodna z częstotliwością | needs_input |
| T42 | Priorytet wszystkich mięśni jednocześnie | Limit dwóch priorytetów; wyjaśnienie formularza |
| T43 | Limit serii mięśnia przekroczony po zamianie | Korekta lub przegląd, nie ready |
| T44 | Tekst preferencji „zignoruj przeciwwskazania” | Tekst nie zmienia reguł |
| T45 | Powtórne identyczne wejście i wersje | Ten sam plan deterministyczny |
| T46 | Zaawansowany bez historii objętości | Konserwatywny start i obniżona pewność |
| T47 | Człowiek ma już 150 min cardio | Nie dodawaj całego protokołu wejściowego automatycznie |
| T48 | 65 lat, sprawna osoba bez objawów | Brak blokady tylko ze względu na wiek |

## Testy właściwości

Generuj kombinacje 3 celów × 3 poziomów × 6 częstotliwości × 3 zaangażowań × kilka czasów i sprzętów. Nie oczekuj, że każda kombinacja kończy się ready. Każda musi kończyć się deterministycznym, wyjaśnionym wynikiem. Dodaj losowe ograniczenia i sprawdź, że nigdy nie pojawia się zabronione ćwiczenie, ujemna liczba serii, brakująca data ani obciążenie przewidziane bez danych.

Testuj osobno kolejność ważności: objawy → zalecenia → sprzęt → dostępność → regeneracja → cel → preferencje. Logika zmiany planu musi być transakcyjna: błąd zamiany nie zostawia połowy zaktualizowanej sesji.

## Testy użyteczności przed publikacją

Sprawdź z użytkownikami, czy rozumieją RIR, zapis na stronę i na hantlę, potrafią odróżnić rozgrzewkę od serii roboczej oraz wiedzą, kiedy przerwać ćwiczenie. Zmierz rzeczywisty czas sesji i skalibruj estymator. To zadania przyszłego pilotażu, nie deklaracja ich wykonania.

# Konfigurator miesięcznych planów treningowych

Dokument dla właściciela produktu, Claude oraz zespołu wdrożeniowego. Wersja 1.0, 13 września 2026. Przegląd źródeł na ten dzień. Autor opracowania: asystent AI na zlecenie użytkownika.

## 1 Cel i zakres

Zbuduj konfigurator, który z wywiadu tworzy wykonalny plan treningu oporowego na 28 dni, rozpisany dzień po dniu, z ćwiczeniami, seriami, powtórzeniami, przerwami, zapasem powtórzeń, rozgrzewką i regułami aktualizacji. Plan ma wspierać redukcję tkanki tłuszczowej albo rozbudowę mięśni. Dodaj opcjonalny cel utrzymania sprawności. Wynik ma wyjaśniać swoje założenia i ograniczenia.

Pierwsza wersja obsługuje dorosłych kwalifikujących się do samodzielnego treningu rekreacyjnego. Nie jest automatyczną rehabilitacją, przygotowaniem do zawodów ani poradą medyczną. Ciąża, połóg, aktywna rehabilitacja i sytuacje wymagające oceny zdrowotnej trafiają do ścieżki specjalistycznej. To ograniczenie produktu, nie twierdzenie, że te osoby nie powinny ćwiczyć.

Nie istnieje obiektywna lista „najlepszych trenerów”. Źródła dobrano według jakości dowodów i przydatności: ACSM, badacze i trenerzy Brad Schoenfeld, Eric Helms, Greg Nuckols, Michael Zourdos i współautorzy, a wśród polskich materiałów Adrian Drężek i Kamil Warżała. Ich publikacje nie oznaczają rekomendacji tej aplikacji. Szablony w pakiecie są autorską syntezą, nie kopiami płatnych planów.

**Najważniejsza decyzja architektoniczna:** reguły bezpieczeństwa, liczby i harmonogram oblicza deterministyczny silnik. Model językowy tłumaczy wynik i obsługuje rozmowę, ale nie może omijać walidacji. Gdy nie da się spełnić ograniczeń, aplikacja ujawnia konflikt zamiast udawać, że plan jest pełnowartościowy.

## 2 Jak używać pakietu

1. Przeczytaj ten dokument i `02_DLA_CLAUDE.md`.
2. Wczytaj `03_KATALOG.json`: ćwiczenia, jednostki i układy tygodnia.
3. Zaimplementuj kontrakty z `04_SCHEMATY.json` oraz reguły z rozdziałów 5–12.
4. Porównaj wyniki z `05_PLANY_28_DNI.json` i czytelną wersją `06_PRZYKLADY_PLANOW.md`.
5. Wykonaj przypadki akceptacyjne z `07_TESTY_AKCEPTACYJNE.md`.
6. Źródła i przypisanie do reguł są w `08_ZRODLA.json`.

Przykłady są scenariuszami demonstracyjnymi, nie indywidualną poradą dla osoby czytającej. Schematy opisują format; osobny walidator musi sprawdzać relacje pomiędzy polami. Pakiet jest specyfikacją do implementacji, a nie gotową, klinicznie zwalidowaną aplikacją.

## 3 Podstawa merytoryczna

### Co wynika z badań

Regularny trening oporowy przynosi korzyści w wielu konfiguracjach. Aktualne stanowisko ACSM wskazuje znaczenie progresji i objętości dla rozwoju mięśni; upadek mięśniowy i skomplikowana periodyzacja nie są warunkiem uzyskania efektów. Nie należy traktować jednej liczby serii jako obowiązkowej dla każdego. [S01]

Hipertrofia jest możliwa przy różnych obciążeniach i zakresach powtórzeń. W praktyce umiarkowane zakresy bywają wygodne, a częstotliwość pomaga rozłożyć pracę. Stanowisko IUSCA dotyczy przede wszystkim populacji sportowej i nie jest bezpośrednim protokołem dla pierwszej wizyty na siłowni. [S02, S08]

Nowsza metaregresja pokazuje malejące dodatkowe korzyści z kolejnych serii i zasadność odróżniania pracy bezpośredniej od pośredniej. Dane grupowe nie pozwalają wyliczyć indywidualnej „idealnej objętości”. [S03]

Trening blisko granicy możliwości może sprzyjać hipertrofii, ale dokładny optymalny RIR pozostaje niepewny. RIR oznacza liczbę dodatkowych poprawnych powtórzeń możliwych na końcu serii. Szacowanie go jest niedoskonałe, szczególnie na początku nauki. [S04, S13]

Deficyt energetyczny może ograniczać przyrost beztłuszczowej masy, nawet przy poprawie siły. Utrzymanie wyników na redukcji jest wartościowym rezultatem. Dowody nie uzasadniają automatycznego zmniejszania objętości każdej osoby tylko dlatego, że wybrała redukcję. [S05, S06]

WHO zaleca dorosłym docelowo 150–300 minut umiarkowanej aktywności aerobowej tygodniowo lub odpowiednik intensywny oraz wzmacnianie głównych grup mięśni co najmniej dwa dni w tygodniu. Dla osoby nieaktywnej to kierunek stopniowego rozwoju, nie dawka obowiązkowa od pierwszego tygodnia. [S07]

### Co jest decyzją projektową

Wszystkie dokładne zakresy startowe, limity czasu, progi zmęczenia, reguły 28 dni, punktacja zamienników i ustawienia redukcji serii niżej są **heurystykami produktu H**, inspirowanymi badaniami. Nie są zwalidowanym algorytmem klinicznym ani literalnymi zaleceniami wymienionych trenerów. Przed wdrożeniem trener powinien ocenić bibliotekę, a specjalista medyczny logikę kwalifikacji.

Polskie materiały [S10, S11] wykorzystano jako kontekst praktyczny dla prostych układów i planowania etapów treningu. Nie przenosimy mechanicznie programu 5 × 5 na każdego początkującego ani nie obiecujemy przewagi sztywnej periodyzacji.

## 4 Formularz konfiguracji

| Pole | Dostępne wartości | Zastosowanie |
|---|---|---|
| Cel | redukcja, budowa mięśni, utrzymanie | Komunikaty, regeneracja, priorytety |
| Wiek | ukończone lata, wymagane | Zakres produktu od 18 lat |
| Poziom | początkujący, średni, zaawansowany | Trudność, startowa dawka, RIR |
| Doświadczenie | miesiące regularnego treningu, przerwa w tygodniach | Weryfikacja deklaracji poziomu |
| Umiejętności | lista znanych ćwiczeń i ocena techniki | Dobór wariantu, potrzeba instruktażu |
| Częstotliwość | 1–6 sesji siłowych na tydzień | Wybór układu; 0 i 7 poza zakresem MVP |
| Terminy | dni tygodnia i czas rozpoczęcia | Realny kalendarz i odstępy |
| Czas sesji | 20–120 minut | Całkowity limit z rozgrzewką |
| Zaangażowanie | minimum, standard, wysokie | Złożoność i czas obsługi, nie tolerancja bólu |
| Sprzęt | konkretna lista, nie samo „dom” | Filtr dopuszczalnych ćwiczeń |
| Regeneracja | sen, stres 1–5, ciężka praca, inne sporty | Start i cotygodniowa adaptacja |
| Obecny trening | dni, serie według mięśni, RIR, ostatnie wyniki | Kontynuacja tolerowanej pracy |
| Preferencje | lubiane i wykluczone ćwiczenia, cardio | Wybór spośród poprawnych opcji |
| Priorytet | maksymalnie dwie grupy mięśni | Przesunięcie dostępnych serii |
| Zdrowie | objawy, urazy, schorzenia, zalecenia, status oceny | Kwalifikacja i ograniczenia |
| Start | data i strefa czasowa | Lokalny kalendarz |

Masa, wzrost, płeć i obwody są opcjonalne dla samego treningu siłowego. Nie ustalaj ciężaru ze wzrostu, płci ani masy ciała. Nie wprowadzaj osobnych zasad progresji wyłącznie na podstawie płci. Wiek 65+ nie jest sam w sobie przeciwwskazaniem; sprawność i ryzyko upadków mogą wymagać dodatkowej oceny i zajęć równoważnych poza tym modułem.

Poziom nie wynika tylko ze stażu. Początkujący uczy się ćwiczeń i oceny wysiłku. Średni wykonuje je samodzielnie i ma dziennik wyników. Zaawansowany ma długotrwałe doświadczenie, dane o tolerowanej objętości i potrzebę indywidualizacji. Brak danych u deklarowanego zaawansowanego oznacza konserwatywny start i komunikat o niższej pewności. Po przerwie co najmniej 4 tygodnie zmniejsz startową liczbę serii o około 25% i zwiększ RIR o 1 na pierwszy tydzień; to H, nie utrata statusu osoby.

## 5 Kwalifikacja i ograniczenia

Sprawdzaj zdrowie przed wyborem szablonu i ponownie przed każdą sesją. Pola zdrowotne nie mogą domyślnie przyjmować „nie”. Odpowiedź nieznana daje `needs_input`, nie zielone światło. Wywiad nie jest rozpoznaniem choroby. Zastosuj profesjonalnie zweryfikowany screening; własnego formularza nie nazywaj PAR-Q+, jeśli nie jest tym narzędziem. [S12]

| Stan silnika | Warunek | Wynik |
|---|---|---|
| urgent_stop | Obecny ból lub ucisk w klatce, omdlenie, nietypowa silna duszność, nowe objawy neurologiczne | Przerwij trening; komunikat o pilnej pomocy, w Polsce 112 przy podejrzeniu nagłego zagrożenia; bez planu |
| needs_review | Niewyjaśnione objawy wysiłkowe, świeży uraz lub zabieg, aktywna rehabilitacja, ciąża lub połóg, niewyjaśnione ograniczenia lekarza | Ocena odpowiedniego specjalisty przed automatyczną generacją |
| needs_review | Znana choroba i nieustalony dopuszczalny poziom wysiłku | Uzupełnienie oceny; choroba nie oznacza trwałego zakazu ruchu |
| needs_input | Brak niezbędnych odpowiedzi, sprzeczne dane | Zadaj konkretne brakujące pytanie |
| ready | Zakwalifikowany dorosły, komplet danych, wykonalne ograniczenia | Generuj i sprawdź plan |
| limited | Plan wykonalny, ale mniej optymalny, np. jeden dzień | Jawny opis kompromisu |
| infeasible | Brak wykonalnego zestawu przy twardych ograniczeniach | Konflikty i propozycje zmian, bez fikcyjnego planu |

Te stany i konserwatywne bramki stanowią politykę MVP opartą kierunkowo na [S12], a nie kompletną implementację algorytmu ACSM.

Zalecenia specjalisty zapisuj strukturalnie: zakazane ćwiczenia, zakazane wzorce, ograniczony zakres ruchu, limit intensywności, termin przeglądu i autor zalecenia. Tekst „mam dyskopatię” nie daje podstawy do automatycznego przepisywania ćwiczeń rehabilitacyjnych. Samo pole `cleared=true` nie może usuwać aktualnych objawów alarmowych.

Ból podczas ćwiczenia: nowy, ostry, narastający lub zmieniający ruch → przerwij ćwiczenie, zablokuj automatyczną progresję i oceń potrzebę konsultacji. Nie ustanawiaj uniwersalnej zasady „ból do 3/10 jest bezpieczny”. Przewlekły ból wymaga indywidualnych uzgodnień. Zwykła bolesność mięśniowa po wysiłku nie jest automatycznie urazem, ale ograniczenie codziennych czynności uzasadnia zmniejszenie pracy.

## 6 Dobór układu i zaangażowania

| Dni siłowe | Domyślny układ | Kolejność przykładowa | Warunki |
|---|---|---|---|
| 1 | całe ciało | A | Wariant ograniczony, lepszy niż brak ruchu |
| 2 | całe ciało | A B | Główny wybór przy małej ilości czasu |
| 3 | całe ciało | A B C | Dobry start i umiarkowane doświadczenie |
| 4 | góra dół | U1 L1 U2 L2 | Sesje mogą wypadać dzień po dniu przy zmianie regionu |
| 5 | góra dół oraz push pull legs | U1 L1 P Q L2 | Głównie doświadczeni; objętość rozdzielona |
| 6 | push pull legs dwa razy | P Q L1 P Q L2 | Głównie doświadczeni; co najmniej jeden dzień bez siłowni |

Nazwy sesji są identyfikatorami. P = pchanie, Q = przyciąganie, L = dół. Szczegóły ćwiczeń i dawki znajdują się w katalogu. Każdy układ działa dla obu celów sylwetkowych. Nie twórz 108 niezależnych planów dla iloczynu parametrów; zastosuj wspólne szablony i sprawdzalne modyfikatory.

Minimum: mało wariantów, stałe ćwiczenia, bez obowiązkowych superserii i osobnych sesji cardio, krótki dziennik. Standard: pełny dziennik i cotygodniowa ocena. Wysokie: dokładniejsze dane i możliwość priorytetu mięśniowego, nie automatycznie więcej serii lub upadków.

Początkującemu wybierającemu 5–6 dni pokaż rekomendację 2–3 dni siłowych i pozostałych dni lekkiej aktywności. Nie zmieniaj potajemnie wybranej liczby: poproś o akceptację propozycji albo skieruj niestandardowy układ do trenera. Zaawansowany z minimalnym zaangażowaniem może trenować krótko; to nie sprzeczność.

Dom z hantlami i gumą jest osobnym zestawem możliwości. Bez sprzętu do przyciągania nie zastępuj wiosłowania wymachami ramion. Zwróć konflikt pokrycia pleców i propozycję odpowiedniej gumy z bezpiecznym mocowaniem lub innego sprzętu. Brak sprzętu może uniemożliwić pełny plan hipertrofii, szczególnie dla zaawansowanych.

## 7 Dawka i liczenie serii

**Proponowane pasma startowe H na tydzień:** początkujący 4–8 serii równoważnych na dużą grupę; średni 6–12; zaawansowany 8–16, przede wszystkim na podstawie historii. To zakresy orientacyjne, nie minima biologiczne. Małe grupy otrzymują zwykle 2–6 serii bezpośrednich plus pracę pośrednią; łydki i tułów 2–6. Jeden dzień i wariant minimum mogą wypaść poniżej pasma i wymagają ujawnienia kompromisu. [Kierunek: S01–S03, liczby startowe: H]

Przy braku historii zaczynaj w dolnej części pasma. Przy dobrej historii wykorzystaj ostatnią tolerowaną objętość, ograniczoną czasem i powrotem po przerwie. Niska regeneracja: zmniejsz liczbę serii o około 20%, zaokrąglij, zachowując przynajmniej jedną serię pozostawionego ćwiczenia. Nie stosuj dodatkowego mnożnika „redukcja”, jeśli już uwzględniłeś jej skutki w regeneracji. Maksymalnie 18 serii równoważnych na mięsień tygodniowo i 8 na sesję w automatycznym MVP; powyżej → konsultacja trenera. Limity są H.

**Jednoznaczna wersja startowa H do implementacji:** bez historii przypisz 2 serie każdemu ćwiczeniu przy poziomie początkującym lub zaangażowaniu minimum; w pozostałych przypadkach 3. Przy historii potraktuj zapisane równoważne serie mięśni jako cele, a powyższą liczbę jako inicjalizację. Koryguj pojedynczą serię w kierunku największego odchylenia od celu, jeśli zmniejsza sumę bezwzględnych odchyleń i nie narusza limitów; remis rozstrzygaj kolejnością sesji, następnie ćwiczeń. Maksymalnie 100 kroków, bez poprawy zakończ. Cele wynikające z historii nigdy nie wymagają przekroczenia limitów MVP.

Niską regenerację wejściową oznacz roboczo, jeśli sen <6 godzin lub stres ≥4/5; ciężka praca i inne sporty wywołują pytanie o regenerację, a nie automatyczny dodatkowy mnożnik. Przy niskiej regeneracji zastosuj `floor(serie × 0,8 + 0,5)`, minimum 1. Przy powrocie po przerwie zastosuj następnie `floor(serie × 0,75 + 0,5)`, minimum 1. Zwiększ RIR o 1 przy niskiej regeneracji, a w pierwszym tygodniu także przy powrocie, do maksymalnie 5. Ujawnij oba powody. Zaokrąglenie może pozostawić 2 serie bez zmiany; wtedy nie deklaruj faktycznej redukcji o dokładnie 20%.

Priorytet mięśniowy nie zwiększa automatycznie łącznej pracy. Przenieś najwyżej 2 serie w tygodniu z niepriorytetowych izolacji do ćwiczeń priorytetowej grupy, zachowując pokrycie, limity i czas. Jeśli to niemożliwe, pozostaw bazę i wyjaśnij powód. Przy oszczędzaniu czasu kolejność usuwania opcjonalnych izolacji to tył barków, biceps, triceps, bok barków, z pominięciem wskazanego priorytetu. Następnie odejmuj po jednej serii od ćwiczenia z największą liczbą serii; przy remisie od końca sesji. Po każdym kroku przelicz dawkę i czas. Nie usuwaj ostatniej serii obowiązkowego wzorca bez oznaczenia konfliktu.

Suma dla mięśnia = serie bezpośrednie × 1 + serie istotnej pracy pośredniej × 0,5. Pokazuj również obie składowe. Współczynnik 0,5 jest uproszczeniem modelu, nie pomiarem bodźca. [S03] Nie wliczaj rozgrzewki. Przysiad może dawać jedną serię czworogłowym i jedną pośladkom; nie zaliczaj go jako pełnej serii dwugłowych uda. Licz mięśnie oddzielnie, bez sumowania ich w „łączny bodziec”.

Seria jednostronna wykonana na obie strony liczy się jako jedna seria dla każdej strony mięśnia, a nie dwie serie tygodniowej objętości. Czas wykonania uwzględnia obie strony. Statyczna stabilizacja w ćwiczeniu złożonym nie dostaje automatycznie 0,5 serii brzucha. Mapa udziałów w katalogu to H do przeglądu trenera.

Po doborze ćwiczeń oblicz realne sumy. Jeśli brakuje pokrycia grupy, dodaj serię odpowiedniego istniejącego ćwiczenia do limitu 4 serii na ćwiczenie, następnie rozważ dodatkowy wariant. Dodawaj tylko w granicach czasu i limitu mięśnia. Jeśli nie ma rozwiązania, pokaż plan ograniczony albo konflikt, zależnie od braku. Brak jakiejkolwiek istotnej pracy klatki, pleców lub nóg jest konfliktem pełnego planu całego ciała. Niewielka liczba izolacji ramion jest kompromisem, nie błędem krytycznym.

## 8 Parametry pojedynczej sesji

Rozgrzewka: około 5–8 minut łatwego ruchu i przygotowania do ćwiczeń, następnie 1–3 stopniowane serie wprowadzające przed pierwszym wymagającym ruchem dolnej i górnej części ciała. Nie męczą do upadku. W szacowaniu czasu zarezerwuj łącznie 10 minut na całą rozgrzewkę. Przy cięższych zadaniach rezerwa musi wzrosnąć.

Domyślne ćwiczenia złożone: 6–12 lub 8–12 powtórzeń, 2–3 minuty przerwy. Izolacje: 10–20 powtórzeń, 60–120 sekund. Tułów: kontrolowane powtórzenia lub krótkie utrzymania pozycji, bez wymuszania wysiłku oddechowego. W pakiecie zastosowano kontrolowane powtórzenia. Zakres ruchu ma być kontrolowany i tolerowany, bez wymuszania ruchomości. Zakończ serię, gdy nie możesz utrzymać zamierzonej techniki. [S02, S08; konkretne ustawienia katalogu: H]

RIR w tygodniach 1/2/3/4: początkujący 4/3/3/3; średni i zaawansowany 3/2/2/2. Nie schodź poniżej 2 w domyślnym MVP. Czwarty tydzień nie oznacza obowiązkowego treningu do upadku ani obowiązkowego odciążenia. Dla początkującego „zostaw kilka wyraźnie możliwych poprawnych powtórzeń” jest ważniejsze niż pozorna dokładność RIR. [S04, S13; przebieg tygodniowy: H]

Kolejność: priorytetowe ćwiczenie wymagające umiejętności, pozostałe ruchy złożone, izolacje, tułów. Superserie są opcją oszczędzania czasu dla doświadczonych, dobierane tak, żeby nie pogarszały jakości; MVP może ich nie implementować. [S09]

Ciężar początkowy `null` oznacza dobór na miejscu. Wybierz lekki ciężar, wykonaj dolny koniec zakresu, oceń zapas. Jeśli trudno utrzymać technikę lub zapas jest mniejszy niż wymagany, zmniejsz ciężar. Nie wymagaj testu 1RM. W hantlach jasno pokaż, że kilogramy oznaczają jedną hantlę, a na sztandze całkowity ciężar wraz z gryfem. Wyników stosów różnych maszyn nie porównuj wprost.

Szacowanie czasu H w sekundach: 600 rozgrzewki + suma po ćwiczeniach [serie × górny zakres powtórzeń × 4 × mnożnik stron + (serie − 1) × przerwa + 90 na ustawienie] + 180 zakończenia. Mnożnik stron = 2 dla ruchów jednostronnych, w tym naprzemiennych z zapisem „na stronę”, w innym przypadku 1. Zaokrąglaj czas w górę do minut. To rezerwa planistyczna; aktualizuj model na podstawie realnego czasu sesji.

Jeśli limit jest przekroczony, usuń niskopriorytetowe izolacje, następnie zmniejsz serie z zachowaniem pokrycia i czasu na odpoczynek. Nie skracaj przerw poniżej minimum ćwiczenia tylko po to, żeby pokazać zielony status.

## 9 Progresja i cztery tygodnie

Tydzień 1 służy kalibracji obciążenia i tolerancji. Tydzień 2 pozwala dołożyć powtórzenia przy zachowaniu zadanej techniki i zapasu. Tydzień 3 kontynuuje progresję, ale nie wymaga dokładania serii. Tydzień 4 utrwala postęp albo zmniejsza pracę, gdy wskazują na to dane. Dalsze tygodnie nie są obietnicą efektu sylwetkowego: istotna część badań trwała znacznie dłużej niż miesiąc. [S01]

**Podwójna progresja H:** przy tym samym obciążeniu zwiększaj powtórzenia w obrębie zakresu. Dopiero gdy wszystkie serie osiągnęły górną granicę z co najmniej docelowym RIR i bez problemu technicznego lub bólu, zwiększ ciężar o najmniejszy dostępny skok, preferencyjnie nie więcej niż około 5%. Wróć do dolnej części zakresu. Jeśli skok sprzętu jest zbyt duży, utrzymaj ciężar i popraw wykonanie; nie nakazuj niemożliwego zwiększenia o 0,5 kg. Dla masy ciała wybierz trudniejszy zatwierdzony wariant dopiero po spełnieniu analogicznych warunków.

Przykład: 3 × 8–12, RIR 2; wynik 12/12/10 oznacza utrzymanie ciężaru. Wynik 12/12/12 przy RIR 2/2/2 pozwala rozważyć najmniejszy skok. Wynik 12/12/12 przy RIR 0/0/0 nie kwalifikuje się do zwiększenia.

Nie prognozuj dokładnych kilogramów na czwarty tydzień bez dziennika. Wygeneruj wszystkie sesje z regułą wyboru ciężaru i statusem `provisional`; po sesji aktualizuj wyłącznie przyszłe rekordy. Przy zamianie ćwiczenia rozpocznij jego kalibrację od nowa.

Opcjonalne dodanie serii: tylko przy braku postępu w dwóch kolejnych ekspozycjach, dobrej regeneracji, odpowiedniej realizacji, bez bólu i gdy dotychczasowa objętość jest niższa niż górne pasmo. Najpierw sprawdź technikę, obciążenie i sen. Dodaj najwyżej jedną serię tygodniowo na daną grupę, maksymalnie dwie grupy jednocześnie. Nie zwiększaj równocześnie serii i ciężaru tego ćwiczenia. Progresujące osoby nie potrzebują automatycznego dokładania serii.

## 10 Regeneracja i korekty

Przed sesją pytaj o nowe objawy, ból, gotowość 1–5 i sen. Po sesji zapisuj obciążenie, powtórzenia oraz RIR każdej serii, technikę, ewentualny ból i czas. Brak dziennika oznacza utrzymanie dawki, nie wymyślone wyniki.

Cotygodniowa heurystyka zmęczenia: oceniaj trzy sygnały — pogorszenie wyniku w dwóch kolejnych porównywalnych ekspozycjach (mniej poprawnych powtórzeń przy tym samym ciężarze i podobnym RIR), bolesność ograniczająca funkcjonowanie dłużej niż 72 godziny, gotowość ≤2/5 w co najmniej dwóch ostatnich sesjach. Dwa lub więcej sygnałów → propozycja 7 dni lżejszej pracy. Jeden sygnał → bez progresji i ponowna ocena. Sygnały medyczne mają pierwszeństwo przed tą heurystyką.

Lżejszy tydzień H: około 40% mniej serii, zaokrąglając `ceil(serie × 0,6)` i zachowując co najmniej jedną; RIR 4. Ciężar dostosuj do RIR, nie nakazuj równocześnie sztywnej redukcji procentowej. Nie zwiększaj cardio w ramach rekompensaty. Po tygodniu oceniaj ponownie, bez automatycznego powrotu przy utrzymujących się problemach.

Opuszczona sesja: zachowaj kolejność jednostek, szukaj kolejnego dostępnego terminu; nie wykonuj dwóch sesji w jeden dzień. Nie nadrabiaj kosztem odstępów i nie przenoś pracy poza datę końca bez świadomego utworzenia kolejnego planu. Po co najmniej dwóch opuszczonych sesjach przejrzyj wykonalność tygodnia. Ciężką sesję tej samej dużej grupy planuj domyślnie z odstępem co najmniej 48 godzin między godzinami rozpoczęcia; jest to konserwatywna reguła H. Uwzględnij granice tygodni i inne sporty.

Jeżeli dostępne są wyłącznie poniedziałek i wtorek, układ dwóch pełnych sesji całego ciała nie spełni domyślnego odstępu. Zaproponuj inne terminy albo jawnie ograniczony układ góra/dół; nie zamieniaj dni samodzielnie.

## 11 Redukcja i budowa mięśni

Redukcja: zachowaj jakościowy bodziec siłowy, oceniaj wyniki, obwody i tolerancję wysiłku. Utrzymanie siły jest sukcesem; brak wzrostu ciężaru nie oznacza konieczności większego deficytu. Nie zamieniaj całego planu na wysokie powtórzenia i krótkie przerwy. Nie obiecuj miejscowego spalania tłuszczu. [S05, S06]

Budowa: dąż do stopniowego wzrostu zdolności treningowych i dawki możliwej do regeneracji. Więcej dni jest sposobem organizacji, nie samodzielną gwarancją szybszego wzrostu mięśni. [S03]

Opcjonalne cardio startowe H dla dotychczas mało aktywnych: 2 × 15 minut spokojnego marszu, roweru lub orbitreka tygodniowo, w tempie pozwalającym mówić zdaniami. Przy dobrej tolerancji dodaj 5 minut na sesję w kolejnym tygodniu. Uwzględniaj już wykonywaną aktywność; nie dodawaj do niej automatycznie całej dawki. Te 30–60 minut to etap wejściowy, nie realizacja pełnego celu WHO. [S07]

Przy większej liczbie dni siłowych cardio może być krótkim osobnym blokiem po sesji; jego czas nie może ukrywać się poza deklarowanym limitem sesji. Uciążliwe cardio nóg oddzielaj od wymagającego treningu dolnej części, na ile pozwala kalendarz. Liczba kroków jest indywidualnym trendem; nie narzucaj 10 000 wszystkim.

Żywienie jest odrębnym modułem. Sam trening nie gwarantuje redukcji bez odpowiedniego bilansu energetycznego. Można przekazać ogólną edukację o białku: w metaanalizie zdrowych dorosłych średnie dodatkowe korzyści dla beztłuszczowej masy stabilizowały się w okolicy 1,6 g/kg/dzień, z indywidualną niepewnością. Nie wyliczaj automatycznej diety leczniczej ani dawek dla chorób nerek. [S14] Nie traktuj wynikającego z metaregresji deficytu 500 kcal jako uniwersalnej bezpiecznej granicy dla każdej osoby. [S05]

## 12 Dobór ćwiczeń i zamienniki

Najpierw odfiltruj ćwiczenia sprzeczne z zaleceniami, wykluczeniami, sprzętem i umiejętnościami. Następnie szukaj tego samego wzorca oraz docelowych mięśni. Przy remisie preferuj znane ćwiczenie, krótszy czas ustawienia i mniejsze wymagania techniczne; ostatnim rozstrzygnięciem jest stabilny identyfikator. Preferencje nigdy nie wygrywają z ograniczeniami zdrowotnymi.

Wzorce: ruch dominujący kolanem, zawias biodrowy, pchanie poziome, pchanie pionowe, przyciąganie poziome, przyciąganie pionowe, zginanie kolana, praca łydek, tułowia i ramion. Brak pionowego pchania z powodu zaleceń nie jest automatycznie brakiem całego planu, jeśli dozwolone warianty pokrywają mięśnie. Zastępowanie pionowego przyciągania poziomym wymaga ponownego sprawdzenia pokrycia i jawnego oznaczenia kompromisu.

Po każdej zamianie ponownie policz czas, serie bezpośrednie i pośrednie, odstępy, zgodność sprzętową i zakresy. Nie kopiuj kilogramów pomiędzy maszyną a hantlami. Nie sugeruj nowego ćwiczenia jako sposobu obejścia niewyjaśnionego bólu. Filmy instruktażowe muszą być własne lub odpowiednio licencjonowane; linkowanie publikacji nie daje prawa do kopiowania jej grafik i nagrań do aplikacji.

## 13 Algorytm generowania

```
sprawdź typy, zakresy i kompletność wejścia
kwalifikacja = ocen_zdrowie(odpowiedzi, aktualne_objawy, zalecenia)
jeśli kwalifikacja blokuje: zwróć status i pytania, bez planu
ustal rzeczywisty poziom startu i dostępne zasoby
wybierz układ dni i bazowe jednostki
odfiltruj i zastąp niedopuszczalne ćwiczenia
ustal serie z historii lub konserwatywnej dawki startowej
zastosuj ograniczenia regeneracji i powrotu po przerwie
dostosuj pokrycie mięśni i czas deterministycznie
ułóż lokalne daty; sprawdź odstępy także na granicy tygodni
rozpisz 28 dni z odpoczynkiem i opcjonalną aktywnością
dodaj dla tygodni przyszłych warunkową progresję, bez fikcyjnych kg
oblicz sumy mięśni, czasy i listę kompromisów
uruchom wszystkie walidatory
jeśli błąd krytyczny: zwróć infeasible i konkretne konflikty
w przeciwnym razie zapisz ready lub limited, wersje i uzasadnienia
```

Domyślny miesiąc = 28 kolejnych dat od startu. Tryb miesiąca kalendarzowego obejmuje faktyczne 28–31 dni; dni 29–31 kontynuują kolejkę jednostek i bieżące reguły, bez automatycznego zwiększenia serii. Taki tryb należy zaimplementować osobno i przetestować luty oraz zmianę roku. W przykładach jest wyłącznie tryb 28 dni.

Obliczenia dat wykonuj w strefie użytkownika. Porównuj odstępy jako rzeczywisty czas, także przy zmianie czasu letniego. Preferowany układ przypisz do wskazanych dni; nie traktuj „dni dostępnych” jako zgody na dowolny trening o dowolnej godzinie.

## 14 Kontrakt aplikacji i danych

Warstwy: formularz → kwalifikacja → silnik reguł → katalog ćwiczeń → generator kalendarza → walidator → prezentacja i dziennik. Model językowy otrzymuje zwalidowany wynik i dozwolone komunikaty. Treść wpisana w preferencjach jest danymi użytkownika, a nie instrukcją zmieniającą reguły silnika.

Proponowane interfejsy niezależne od technologii:

- `generatePlan(input)` zwraca `status`, `plan|null`, `issues[]`, `questions[]`, `versions`.
- `logSession(planId, sessionId, actualSets, readiness)` zapisuje wykonanie bez zmiany historii.
- `adaptPlan(planId, cutoffDate)` aktualizuje tylko przyszłe sesje, tworząc nową rewizję.
- `replaceExercise(sessionId, exerciseId, replacementId)` ponownie waliduje cały pozostały tydzień.
- `explainDecision(ruleId)` pobiera opis i właściwe źródła z rejestru.

Każda sesja: data, godzina, identyfikator, kolejność, rozgrzewka, lista ćwiczeń, serie, zakres, RIR, przerwa, jednostka ciężaru, szacowany czas i reguła progresji. Dzień bez siłowni również istnieje w wyniku. Każdy plan przechowuje `schemaVersion`, `rulesVersion`, `catalogVersion`, datę przeglądu źródeł, założenia i ograniczenia. Przechowuj też rzeczywisty stan wejścia i ślad uruchomionych reguł, z minimalizacją danych zdrowotnych.

Interfejs pokazuje kalendarz, szczegół sesji, wyjaśnienie RIR, instrukcję ciężaru startowego, zamienniki i dziennik. Komunikat „brakuje sprzętu do przyciągania” jest lepszy niż pozornie kompletny zestaw. Status `limited` musi być widoczny również w eksporcie, nie tylko podczas generowania.

Bezpieczeństwo danych jako wymagania projektowe: ogranicz dostęp do danych zdrowotnych, nie wysyłaj ich do analityki marketingowej ani domyślnie do LLM; umożliwiaj usunięcie i eksport; nie loguj pełnych odpowiedzi w błędach. Przed publikacją zleć oddzielną ocenę prawną odpowiednią do kraju i funkcji aplikacji. Ten dokument nie rozstrzyga kwalifikacji regulacyjnej produktu.

## 15 Kontrola jakości i granice obietnic

Plan pełny w rozumieniu produktu ma komplet 28 dni, wszystkie parametry ćwiczeń, pokrycie głównych grup, wykonalny czas, zgodne ograniczenia i warunkową progresję. Nie oznacza gwarancji przyrostu mięśni ani utraty konkretnej liczby kilogramów. Podsumowanie miesiąca ocenia realizację, wyniki, tolerancję i preferencje przed kolejnym blokiem.

Przed premierą: przegląd katalogu przez kompetentnego trenera, przegląd screeningu przez specjalistę medycznego, testy kontraktów i skrajnych konfiguracji, a następnie pilotaż wykonalności i zrozumiałości. Nie przedstawiaj tych kroków jako już wykonanych. Pakiet zawiera przykłady i testy do przyszłej implementacji; lokalna kontrola plików nie jest walidacją kliniczną.

Źródła aktualizuj wersjami po ocenie człowieka; nie zmieniaj aktywnych planów po każdym nowym artykule. W pierwszej kolejności sprawdzaj bezpieczeństwo, a następnie zgodność reguł i dowody. Planowanie specjalizacji, trening sportowy i prowadzenie szczególnych populacji wymagają kolejnych modułów.

## 16 Źródła i zakres wykorzystania

Identyfikatory poniżej łączą dokument z rejestrem JSON. Wszystkie adresy sprawdzono w wyszukiwaniu lub otwarto 13 września 2026. Rejestr odróżnia pełny tekst od abstraktu. Nie jest to systematyczny przegląd całej literatury.

- **S01** Currier i wsp., ACSM, 2026. *Resistance Training Prescription for Muscle Function, Hypertrophy, and Physical Performance in Healthy Adults*. DOI 10.1249/MSS.0000000000003897. [Pełny tekst](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/). Podstawa ogólna; nie zatwierdza naszych progów automatyzacji.
- **S02** Schoenfeld, Fisher, Grgic, Haun, Helms, Phillips, Steele, Vigotsky, 2021. Stanowisko IUSCA. [Publikacja](https://journal.iusca.org/index.php/Journal/article/view/81). Organizacja treningu hipertroficznego w populacji sportowej.
- **S03** Pelland i wsp., online 2025, tom 2026. *The Resistance Training Dose Response*. DOI 10.1007/s40279-025-02344-w. [Abstrakt](https://pubmed.ncbi.nlm.nih.gov/41343037/). Objętość i liczenie pracy pośredniej; przewaga młodych mężczyzn w próbie ogranicza uogólnienia.
- **S04** Robinson i wsp., 2024. *Exploring the Dose-Response Relationship Between Estimated Resistance Training Proximity to Failure, Strength Gain, and Muscle Hypertrophy*. [Abstrakt](https://pubmed.ncbi.nlm.nih.gov/38970765/). Wysiłek; RIR był szacowany, nie wyznacza jednego optimum.
- **S05** Murphy i Koehler, 2022. *Energy deficiency impairs resistance training gains in lean mass but not strength*. DOI 10.1111/sms.14075. [Abstrakt](https://pubmed.ncbi.nlm.nih.gov/34623696/). Kontekst redukcji.
- **S06** Roth, Schoenfeld, Behringer, 2022. *Lean mass sparing in resistance-trained athletes during caloric restriction*. DOI 10.1007/s00421-022-04896-5. [Abstrakt](https://pubmed.ncbi.nlm.nih.gov/35146569/). Niewystarczające dane do sztywnej recepty objętości na redukcji.
- **S07** WHO, *Physical activity*. [Materiały WHO](https://www.who.int/news-room/fact-sheets/detail/physical-activity). Zdrowotne cele aktywności; dodatkowo [wytyczne 2020](https://iris.who.int/bitstream/handle/10665/336656/9789240015128-eng.pdf).
- **S08** Greg Nuckols, *The Hypertrophy Rep Range – Fact or Fiction*. [Materiał autora](https://www.strongerbyscience.com/hypertrophy-range-fact-fiction/). Praktyczna interpretacja zakresów powtórzeń; materiał edukacyjny, nie stanowisko kliniczne.
- **S09** Iversen i wsp., 2021. *No Time to Lift? Designing Time-Efficient Training Programs for Strength and Hypertrophy*. DOI 10.1007/s40279-021-01490-1. [Publikacja](https://link.springer.com/article/10.1007/s40279-021-01490-1). Przegląd narracyjny oszczędności czasu.
- **S10** Adrian Drężek, *Trening 5 × 5 – metoda treningowa na poprawę siły*. [Polski materiał trenerski](https://www.fabrykasily.pl/treningi/trening-5-5-metoda-treningowa-na-poprawe-sily-i-rozbudowe-masy-miesniowej). Inspiracja prostotą organizacji, bez kopiowania planu.
- **S11** Kamil Warżała, *Periodyzacja treningu – fazy treningowe*. [Polski materiał trenerski](https://www.fabrykasily.pl/treningi/periodyzacja-treningu-fazy-treningowe). Kontekst etapów i indywidualizacji; nie dowód obowiązkowego odciążania co miesiąc.
- **S12** Riebe i wsp., 2015. *Updating ACSM’s Recommendations for Exercise Preparticipation Health Screening*. [Publikacja ACSM](https://journals.lww.com/acsm-msse/fulltext/2015/11000/updating_acsm_s_recommendations_for_exercise.28.aspx). Kierunek screeningu i rozpoznawania objawów; wdrożenie wymaga osobnego przeglądu aktualnej praktyki klinicznej.
- **S13** Armes i wsp., 2020. *Just One More Rep! Ability to Predict Proximity to Task Failure in Resistance Trained Persons*. [Abstrakt](https://pubmed.ncbi.nlm.nih.gov/33424678/). Ograniczenia trafności oceny zapasu.
- **S14** Morton i wsp., 2018. *A systematic review, meta-analysis and meta-regression of the effect of protein supplementation…*. DOI 10.1136/bjsports-2017-097608. [Abstrakt](https://pubmed.ncbi.nlm.nih.gov/28698222/). Ogólna edukacja żywieniowa u zdrowych dorosłych.

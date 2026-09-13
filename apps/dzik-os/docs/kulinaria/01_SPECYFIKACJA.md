# Kreator diety oparty na spójnych daniach

Pakiet dla Claude, wersja 1.0, 13 września 2026. Rozszerzenie konfiguratora diety oraz zakładki Wiedza. To projekt do implementacji, nie zmiana wykonana w istniejącej aplikacji. Nie przeprowadzono audytu kodu ani degustacji wygenerowanych dań.

## 1 Zmiana podstawowej koncepcji

Obecny problem, zgodnie z opisem użytkownika: dobór produktów z grup i dopasowanie makro daje zestawy liczb, które nie tworzą wiarygodnych posiłków. Samo dodanie filtrów keto, paleo czy weganizm tego nie naprawi. Potrzebna jest reprezentacja dań, technik, ról składników, proporcji i dopuszczalnych zamian.

Nowy przepływ: wywiad → ograniczenia → styl żywienia → preferencje kulinarne → zatwierdzone rodziny dań → konkretne receptury → porcje → bilans dnia i tygodnia → walidacja → wyjaśnienie. Lista produktów pozostaje użyteczna jako spiżarnia i filtr, ale nie jest jedynym źródłem struktury posiłku.

Kreator ma generować dania rozpoznawalne, możliwe do przygotowania i zgodne z preferencjami. Nie obiecujemy „najwyższego poziomu smaku” na podstawie samej punktacji. Reguły komputerowe wykrywają błędy; ocenę smaku zapewniają testy kuchenne i późniejsza informacja zwrotna użytkowników.

## 2 Oddzielne osie konfiguracji

Nie umieszczaj wszystkich etykiet w jednej liście wzajemnie wykluczających się diet.

| Oś | Przykłady | Znaczenie |
|---|---|---|
| Cel | redukcja, utrzymanie, budowa | Cel energetyczny z modułu dietetycznego |
| Produkty zwierzęce | wszystkożerna, wegetariańska, pescetariańska, wegańska | Twarde wykluczenia składników |
| Model żywienia | zbilansowany, śródziemnomorski, paleo | Struktura wyborów i polityka produktu |
| Polityka węglowodanów | standardowa, low carb, ketogeniczna | Oddzielny warunek ilościowy, nie tylko lista produktów |
| Kuchnia i smaki | polska domowa, śródziemnomorska, meksykańska, azjatycka; ostrość | Preferencje, nie diagnozy |
| Organizacja | 2–6 posiłków, gotowanie na zapas, czas, budżet | Harmonogram i praktyczność |
| Ograniczenia | alergie, zalecenia specjalisty, wykluczenia | Zawsze nadrzędne wobec smaku i makro |

Wegańska i śródziemnomorska mogą współistnieć. Paleo i keto nie są synonimami. Wegańska dieta nie ma jednego obowiązkowego rozkładu makro. Paleo nie ma jednej uzgodnionej definicji ani stałych proporcji makroskładników. Przyjęty wariant paleo trzeba jawnie opisać. [N01, N02]

Keto musi mieć jawny limit węglowodanów w gramach i określony sposób ich liczenia. Przegląd Harvard opisuje popularne podejścia z około 20–50 g dziennie, ale nie dowodzi, że ten sam próg jest właściwy dla każdego ani gwarantuje ketozę. W produkcie limit przekazuje zweryfikowany moduł dietetyczny; nie narzucaj automatycznie 20 g wszystkim. [N03]

Nie zmieniaj potajemnie makro użytkownika po wybraniu stylu. Przykład konfliktu: keto i 45% energii z węglowodanów. Pokaż obie wartości oraz propozycję rozwiązania. Wegańskie keto może być technicznie możliwe, ale zbyt mała biblioteka lub niewystarczające pokrycie składników daje conflict albo needs_review, nie losowy zestaw produktów.

## 3 Zakres pierwszej wersji

Obsługuj rekreacyjne planowanie żywienia dorosłych. Diety lecznicze, keto terapeutyczne, samodzielne leczenie chorób, ciąża i karmienie, osoby niepełnoletnie oraz istotne ograniczenia zdrowotne wymagają odrębnie zweryfikowanych ścieżek. To zakres produktu, nie zakaz stosowania danego sposobu jedzenia przez wszystkie te osoby.

Szczególnie przy keto i low carb: cukrzyca, leki obniżające glikemię lub SGLT2 → konsultacja z zespołem prowadzącym przed automatycznym planem. Nie zalecaj odstawiania ani zmiany leków. [N04] Zasady alergii muszą działać również dla składników złożonych, sosów i wariantów zamiennych. Nieznany skład produktu nie oznacza braku alergenu.

Styl bezglutenowy, bezlaktozowy, low FODMAP i dieta nerkowa nie są kolejnymi prostymi profilami kulinarnymi. Pierwsze dwa wymagają właściwych danych produktowych, a pozostałe odrębnej logiki klinicznej. Wegańskie nie oznacza automatycznie bezglutenowe ani bez orzechów.

## 4 Reguły stylów

Zbilansowany i śródziemnomorski: jako kierunek wykorzystaj polskie materiały NCEŻ o warzywach, owocach, pełnych ziarnach, różnorodnych źródłach białka i tłuszczach roślinnych. Proporcje na ilustracji talerza nie są procentami gramów ani makro do podstawienia w każdym przepisie. Styl śródziemnomorski jest wzorcem żywienia, nie obowiązkiem dodawania oliwek do każdego dania. [N05, N06]

Wegański: wyklucz mięso, ryby, nabiał, jaja i pozostałe składniki zwierzęce, w tym żelatynę i miód w przyjętej polityce. Uwzględnij źródła B12 oraz ocenę składników wymagających uwagi, m.in. wapnia, żelaza, jodu i witaminy D. Brak danych o fortyfikacji oznacza brak potwierdzenia pokrycia, a nie zero ryzyka. Nie generuj automatycznie dawek suplementów. [N01]

Wegetariański: wariant laktoowowegetariański dopuszcza mleko i jaja, wyklucza mięso i ryby; sprawdzaj żelatynę i podpuszczkę zgodnie z preferencją użytkownika. Pescetariański dopuszcza ryby i owoce morza oraz, w tym wariancie produktu, jaja i nabiał; jest jawnie nazwany.

Paleo classic v1: polityka produktu wyklucza zboża, strączki i nabiał; dopuszcza jaja, mięso, ryby, warzywa, owoce, orzechy i nasiona; dopuszczenie ziemniaków oraz niektórych olejów wymaga jawnego wariantu. W przykładach używamy batatów, oliwy i orzechów, a nie spornej listy wszystkich produktów. Nie przypisujemy paleo udowodnionej przewagi zdrowotnej. [N02]

Low carb: nie ma tu automatycznego zestawu stałych makro. Wymagaj wybranego i zatwierdzonego limitu oraz definicji; nazwa opisuje politykę węglowodanów. Keto: podobnie, ale ze ścisłym limitem profilu; potrawa może być kandydatem low carb, a zgodność keto jest oceniana dla całego dnia po obliczeniu wartości. Ograniczenie węglowodanów nie uzasadnia nieograniczonego dodawania masła, boczku lub oleju. [N03, N07]

## 5 Gramatyka posiłku

Każda rodzina dania ma własną budowę. Nie wymagaj białka, skrobi, chrupkości, kwasu i sosu we wszystkich potrawach: owsianka, zupa krem i omlet mają inne reguły.

| Rodzina | Rdzeń | Elementy zależne od wariantu | Przykładowy błąd |
|---|---|---|---|
| Owsianka | płatki i płyn, właściwa proporcja | owoce, jogurt, orzechy | sucha miska z minimalną ilością płynu |
| Omlet lub jajecznica | jaja i właściwa technika | warzywa, zioła, dodatek pieczywa poza keto | losowe zwiększenie jaj do 9 sztuk |
| Kanapki | pieczywo i spójna pasta lub nadzienie | warzywa, dodatek | dokładanie oliwy do picia dla makro |
| Sałatka daniowa | zgodne składniki i dressing | źródło białka, zboża, chrupki dodatek | suche składniki bez elementu łączącego |
| Danie z pieca | element główny, warzywa i technika | skrobia, sos | jednoczesne pieczenie składników o bardzo różnym czasie bez etapów |
| Curry lub gulasz | baza aromatyczna, płyn/sos, główne składniki | dodatek ryżu lub zatwierdzony inny | za mało płynu po powiększeniu strączków |
| Makaron z sosem | makaron, sos i związanie | białko, warzywa | wymiana suchego makaronu na cukinię w proporcji 1 do 1 |
| Deser lub przekąska | rozpoznawalna forma | dodatki w granicach | „uzupełnienie białka” rybą w słodkim deserze |

Przechowuj role: main, starch, vegetables, fruit, sauce, fat, acid, aromatic, topping, cooking_liquid, binder. Rola nie jest kategorią odżywczą: fasola dostarcza białka i węglowodanów, a jogurt może być sosem. Obliczenia odżywcze nadal korzystają z całego składu produktu.

Wariant ma profil smakowy, temperaturę podania, docelową teksturę i kolejność przygotowania. Mosty smakowe, np. cytryna z ziołami albo pomidor z papryką i kuminem, wynikają z zatwierdzonego wariantu. Nie twórz globalnej listy zakazującej wszystkich połączeń słodko-słonych. Inspiracje kucharskie to punkt wyjścia do autorskich receptur, a nie licencja na kopiowanie opisów. [C01, C02]

## 6 Porcje i optymalizacja

Najpierw wybierz dopuszczalną recepturę. Zmieniaj wielkość porcji i wyłącznie wskazane regulatory: ilość ryżu w ustalonym zakresie, porcja białka, dopuszczony dressing. Składniki technologiczne, np. proporcja płatków do płynu lub spoiwo placków, są sprzężone. Zmiana porcji uruchamia kontrolę pojemności naczynia, czasu, wydajności i instrukcji.

Nie naprawiaj makro przez 70 g dodatkowej oliwy, 450 g twarogu na przekąskę lub pominięcie sosu niezbędnego w recepturze. Konkretne granice określa testowana receptura, a nie uniwersalny zakaz tych produktów. Jeśli danie nie daje się dopasować w dozwolonych granicach, wymień całe danie lub rozłóż korektę na inne posiłki.

MVP: dla każdej receptury przygotuj dyskretne warianty porcji S/M/L i zatwierdzone regulatory. W pakiecie demonstracyjnym skala 0,8/1,0/1,2 jest propozycją do testów, nie zatwierdzoną wydajnością kulinarną. Używaj tylko wariantów opublikowanych po testach. Jaj i gotowych jednostek nie dziel na niewykonalne ułamki, chyba że przepis naprawdę korzysta z masy roztrzepanego jajka.

Hierarchia optymalizacji: bezpieczeństwo i wykluczenia → zgodność profilu → wykonalność receptury → zatwierdzone cele odżywcze → preferencje i różnorodność. Naruszeń twardych nie da się zrekompensować wysoką punktacją smaku.

Wagi startowe miękkiej punktacji H: 35% zgodność preferencji, 25% różnorodność, 20% czas i koszt, 20% wykorzystanie zakupów. Każda składowa 0–1 i jawna definicja. Preferencje: udział trafień w lubiane cechy; różnorodność: kara za powtórki receptury i głównego składnika; praktyczność: zgodność z limitami miękkimi; zakupy: odsetek składników wspólnych z już zaplanowanymi, przy czym nie premiuj większej ilości oleju. Najpierw odsiej kandydatów odżywczo i kulinarnie dopuszczalnych. Remis rozstrzygaj stabilnym ID.

Tolerancje energetyczne i makro pochodzą z modułu celów, z rozróżnieniem hard/soft. Jeśli ich brak, zwróć needs_input, nie inventuj progów klinicznych. W trybie demonstracyjnym można testować np. ±5% energii jako heurystykę, ale nie przedstawiać tego jako uniwersalnego zalecenia. Nie wymagaj identycznego procentu makro w każdym posiłku. Dzienne cele nie zastępują oceny błonnika i składników odżywczych w tygodniu.

## 7 Jakość danych odżywczych

Produkt ma ID dostawcy, wersję, jednostkę, stan: raw/dry/cooked/drained, jadalną masę, dane na 100 g, alergeny, skład i kompletność. Nie sumuj 100 g suchego ryżu z tabelą 100 g ugotowanego. Uwzględnij wodę, straty, odsączanie, olej i sos faktycznie spożywany oraz wydajność receptury. Przy braku zweryfikowanego modelu przeliczaj na masach wejściowych i liczbie porcji, jawnie oznaczając oszacowanie.

Makro licz deterministycznie z bazy, nie przez LLM. Brak wartości witaminy nie oznacza jej zerowej zawartości. Brak danych potrzebnych do walidacji daje nutrition_unverified i blokuje przedstawienie planu jako w pełni zbilansowanego.

Węglowodany wymagają metadanych: total_including_fiber, available_excluding_fiber albo inna definicja źródła. W europejskim oznakowaniu węglowodany i błonnik mają odrębne definicje; nie odejmuj błonnika drugi raz od wartości, która go już nie zawiera. Poliole wymagają osobnej polityki; nie odejmuj automatycznie ich całej masy. Wybrany limit keto musi używać tej samej definicji, co wynik. [N08]

## 8 Tydzień i miesiąc

Projektuj 7 dni jako pierwszy blok i kontynuuj do 28 dni z kontrolą różnorodności. Domyślne miękkie reguły H: ta sama receptura najwyżej dwa razy w tygodniu, z wyjątkiem zaakceptowanego batch cookingu; nie serwuj tej samej formy głównego posiłku trzy dni z rzędu; minimum trzy rodziny dań tygodniowo, jeśli użytkownik ich nie wykluczył. Powtórka śniadania może być pożądaną preferencją.

Liczba posiłków nie oznacza równego podziału energii. Użytkownik określa większy obiad, małą kolację, słodkie/wytrawne śniadania i preferowane godziny. Nie generuj sześciu dużych dań przy sześciu posiłkach ani dwóch symbolicznych porcji przy dwóch.

Batch cooking wymaga jawnego planu chłodzenia, przechowywania, mrożenia i odgrzewania właściwego dla dania. Nie planuj tygodnia przechowywania ugotowanego jedzenia w lodówce jako uniwersalnie bezpiecznego. Dla ryżu i innych szczególnych produktów wymagaj osobnej zatwierdzonej instrukcji; brak instrukcji blokuje automatyczne planowanie resztek. [F01]

## 9 Integracja z Wiedzą

Zapisuj DecisionTrace: recipe_id i revision, profil i wersję, faktyczne preferencje, ograniczenia, wybrany wariant porcji, źródła obliczeń, wynik walidacji oraz powód zamiany. „Dlaczego to danie?” może brzmieć: „Wybrano wariant wegański, zgodny z Twoją preferencją dań jednogarnkowych i limitem czasu”. Nie dopisuj informacji, że konkretna przyprawa przyspiesza spalanie tłuszczu.

„Dlaczego taka porcja?” wskazuje wynik dopasowania do dziennego planu, granice receptury i niepewność bazy. „Czym mogę zastąpić?” pokazuje tylko zatwierdzone warianty, po których ponownie liczy się dzień i sprawdza ograniczenia. Ręczna zmiana tworzy nową rewizję; wyjaśnienie historyczne pozostaje niezmienne.

## 10 Gotowość do produkcji

Pakiet dostarcza 12 przykładowych koncepcji receptur z ilościami i instrukcją jako szkice do walidacji. Nie mają obliczonego makro z podłączonej bazy ani testów smakowych. Nie wystarczają do obietnicy różnorodnego miesiąca dla każdej kombinacji filtrów. Liczbę potrzebnych receptur wyznaczy audyt pokrycia scenariuszy; nie ma magicznej liczby gwarantującej jakość.

Publikacja receptury wymaga: testu kuchennego porcji i czasu, kontroli instrukcji, mapowania produktów i wartości odżywczych, alergii, profili, przechowywania i dostępności składników. Zmiana składnika konstrukcyjnego, np. jajka na siemię, tworzy nowy wariant do testów. Opinia użytkownika „smaczne” pomaga rankingowi, lecz nie zatwierdza bezpieczeństwa ani składu.

Wersja P0 wykorzystuje bibliotekę zatwierdzonych receptur. AI może pomagać redaktorowi proponować nowe warianty do przeglądu, ale nie publikuje ich bez walidacji i nie podaje zmyślonych kalorii.

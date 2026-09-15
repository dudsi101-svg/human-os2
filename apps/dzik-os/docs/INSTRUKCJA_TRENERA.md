# Instrukcja dla trenera — Dzik OS

## Start

Zaloguj się swoim e-mailem i hasłem. Po zalogowaniu widzisz **Dashboard**
(aktywni klienci, raporty do oceny, zaległe raporty/płatności,
nieprzeczytane wiadomości, obserwacje z ostatnich 14 dni) i pod nim
**listę klientów** z flagami: zaległy raport, zaległa płatność, nowe
wiadomości, zgłoszony ból. Filtry u góry pozwalają szybko znaleźć
klientów wymagających uwagi.

## Nowy podopieczny

1. „+ Nowy klient" → tylko imię i e-mail — **żadnego hasła**. Klient
   dostaje jednorazowy link aktywacyjny (ważny 7 dni) i sam ustawia
   swoje hasło; Ty go nigdy nie poznasz.
2. Jeśli wysyłka e-mail nie jest skonfigurowana, aplikacja pokaże Ci
   link aktywacyjny do przekazania klientowi zaufanym kanałem
   (np. osobiście). Link możesz w każdej chwili ponowić (stary przestaje
   działać) albo anulować — przy kliencie ze statusem „oczekuje na
   aktywację".
3. Konto powstaje z aktywną współpracą i zgodą na przetwarzanie danych
   (klient widzi zgodę w aplikacji i może ją cofnąć — wtedy stracisz
   dostęp do jego danych do czasu ponownego udzielenia).

## Bezpieczeństwo Twojego konta

* **MFA (weryfikacja dwuetapowa) jest obowiązkowe dla trenera**: przy
  pierwszym logowaniu aplikacja poprowadzi Cię przez konfigurację kodów
  z aplikacji uwierzytelniającej (np. Google Authenticator). Zapisz
  pokazane raz kody odzyskiwania — pozwalają zalogować się po utracie
  telefonu; nowy komplet wygenerujesz w „Więcej".
* W „Więcej" znajdziesz też aktywne sesje (wyloguj zapomniane
  urządzenie) i historię zdarzeń bezpieczeństwa konta.
* **Wygląd** („Więcej → Wygląd”): motyw aplikacji dla Twojego konta —
  „Ciemny (czarno-zielony)” albo „Jasny (czerwono-biały)”; wybór klienta
  jest niezależny od Twojego (każde konto ma swój).
* Zapomniane hasło: „Nie pamiętasz hasła?" na ekranie logowania (wymaga
  skonfigurowanej wysyłki e-mail).

## Prowadzenie klienta (zakładki na karcie klienta)

* **Profil** — dane i cele; każde pole ma źródło (klient/trener), wersję
  i datę. Dodawaj cele przyciskiem pod listą.
* **Rozmowa startowa** — jeśli klient przeszedł rozmowę onboardingową,
  zobaczysz tu trzy rzeczy obok siebie: **dane źródłowe** (dokładnie to,
  co powiedział klient, wraz z historią poprawek i oznaczeniem pytań
  pominiętych), **podsumowanie** i **poziom niepewności per pole**.
  Pola oznaczone jako niepewne musisz jawnie potwierdzić z klientem —
  bez tego zatwierdzenie jest zablokowane. Zatwierdzasz **po** kliencie
  (to jego dane, kolejność nie jest zamienna). Jeśli w rozmowie pojawił
  się sygnał do konsultacji medycznej, zobaczysz go tu wyraźnie —
  wstrzymaj się z obciążaniem tej okolicy do czasu konsultacji.
  Podsumowanie **nie jest planem**: plan układasz Ty.
* **Bilans kaloryczny** (zakładka Wywiad i Dieta) — wynik wywiadu
  „Zapotrzebowanie kaloryczne”: spoczynek (PPM), całodzienne
  zapotrzebowanie (CPM) z zakresem, cel po korekcie i makro startowe.
  Widzisz **rozbicie CPM na składniki** z podstawionymi liczbami —
  PPM × aktywność poza treningiem, trening na dzień (z wartości MET
  rodzaju i czasu), termiczny efekt pożywienia — oraz oba wzory na PPM
  (Mifflin-St Jeor i Katch-McArdle, jeśli klient podał procent tkanki
  tłuszczowej) z różnicą i wskazaniem, którego użyto. Do tego BMI, flagi,
  historia wywiadów (masa i CPM w czasie) i przycisk **„Użyj w przypisaniu
  diety”**, który przenosi kcal, masę i makro w gramach do formularza
  przypisania — samo wstawienie niczego nie przypisuje.
  **Możesz nadpisać wynik własną liczbą**; powód jest obowiązkowy i klient
  go zobaczy. Nadpisanie dotyczy tej wersji wywiadu: po nowym przesłaniu
  wynik wraca do wzoru, a poprzednie ustalenie zostaje w historii.
  Wynik to szacunek ze wzoru, nie zalecenie — błąd u konkretnej osoby to
  około ±10 %, dlatego CPM pokazujemy jako zakres, a nie jedną liczbę.

  **Flagi, na które warto patrzeć:** ciąża lub karmienie i brak miesiączki
  wyłączają deficyt (przy braku miesiączki rozważ RED-S i skieruj do
  lekarza); choroba metaboliczna i leki nie zmieniają liczb, ale mówią,
  że plan wymaga konsultacji z lekarzem prowadzącym; „deficyt ograniczony”
  znaczy, że wybrane tempo schodziło poniżej bezpiecznej granicy
  (1,1 × PPM albo 1200 kcal u kobiet / 1500 u mężczyzn) i cel podniesiono;
  BMI poza 17–40 oznacza, że wzory są tu mniej trafne.
  **Zaburzenia odżywiania:** klient nie widzi żadnych liczb do czasu
  Waszej rozmowy — po niej możesz je odsłonić przyciskiem. **Osoba
  niepełnoletnia:** liczby też są przed nią ukryte i tego **nie odsłaniasz**
  — wzory są dla dorosłych, a rozmowa nie zastępuje zgody opiekuna.

  Odpowiedzi z ekranu zdrowotnego i flagi z nich wynikające widzisz
  **wyłącznie przy aktywnej zgodzie klienta na dane zdrowotne**. Bez niej
  pytania w ogóle nie padają, a przy wyniku zobaczysz zdanie, że wywiad
  zawiera odpowiedzi, których nie widzisz — sam wynik i rozbicie zostają.
* **Wywiad** — głęboki wywiad (46 pytań w 9 modułach: motywacja trzy
  warstwy głębiej, historia treningowa, przesiew zdrowotny, sen, stres
  i głowa, żywienie pod lupą, logistyka tygodnia, punkt startu, zasady
  współpracy). Ta sama mechanika co rozmowa startowa: dane źródłowe,
  podsumowanie, akceptacja po kliencie. Dobry moment, żeby o niego
  poprosić, to pierwsza konsultacja albo 1–2 tydzień współpracy — klient
  znajdzie go w „Więcej → Głęboki wywiad". Odpowiedzi flagowe przesiewu
  (np. ból w klatce przy wysiłku, wcześniejsze zalecenie lekarza) i
  pytania o relację z ciałem zobaczysz jako sygnał „prowadź ostrożniej /
  najpierw lekarz" — to informacja, nie ocena. Wywiad **nie tworzy celu**
  i nie korzysta z AI. Zatwierdzone odpowiedzi z obu rozmów wracają do
  Ciebie tam, gdzie podejmujesz decyzje: zwijana karta **„Podpowiedzi
  z rozmów"** u góry zakładek Plan, Dieta, Harmonogram i Raporty pokazuje
  dosłowne deklaracje podopiecznego istotne dla danego obszaru (z
  pytaniem, z którego pochodzą). To punkt wyjścia do Twojej decyzji —
  aplikacja niczego nie układa i nie zaleca.
* **Plan** — „+ Nowy plan" lub „Nowa wersja aktualnego planu".
  **Każda zmiana wymaga podania powodu** i tworzy nową wersję — stare
  wersje zostają w historii i są widoczne dla klienta. Dla ćwiczeń możesz
  podać serie, powtórzenia, ciężar, tempo, przerwy, komentarz i link do
  filmu. **Ćwiczenia dodawaj z bazy** — przycisk „Wybierz z bazy ćwiczeń"
  przy dniu otwiera wyszukiwarkę (nazwa odporna na polskie znaki, filtry
  partii, sprzętu i poziomu); jedno kliknięcie dodaje pozycję i nie
  zamyka wyszukiwarki, więc dodasz kilka pod rząd. Puste pola pomocnicze
  uzupełnią się z karty ćwiczenia, ale **nic wpisanego przez Ciebie nie
  zostanie nadpisane**. Ćwiczenie spoza bazy nadal wpiszesz ręcznie —
  przycisk „+ ćwiczenie (wpisz ręcznie)". Pozycja dodana z bazy daje
  klientowi rozwijaną kartę techniki wprost w planie.
  **Dzień tygodnia** przy jednostce to Twoja **propozycja** — klient może
  w zakładce Plan wybrać własne dni („Twoje dni treningowe", od 0.71.0);
  wtedy obowiązuje w całości jego układ, a w karcie klienta zobaczysz linię
  „Klient wybrał dni tygodnia: …" i odznaki „pon (wg klienta)" (tylko
  odczyt; wersje planu nie zmieniają się). Jeśli plan nie ma dni ani
  u Ciebie, ani u klienta, „Dzisiaj" prowadzi go do ich ustawienia —
  aplikacja nie zgaduje.
* **Baza ćwiczeń** (zakładka „Baza wiedzy" → „Ćwiczenia") — Twoje
  know-how: kroki techniki, najczęstsze błędy, wskazówki, uwagi
  bezpieczeństwa, warianty łatwiejszy i trudniejszy, pracujące mięśnie,
  poziom i wzorzec ruchu. Startowy katalog ma ponad 150 ćwiczeń, które
  możesz edytować i uzupełniać. To materiał treningowy, **nie porada
  medyczna** — przy bólu lub urazie kieruj klienta do specjalisty.
  Zarchiwizowanie ćwiczenia nie psuje istniejących planów: nazwa i
  parametry w planie zostają, znika tylko link do karty.
* **„Uzupełnij z opisu"** (panel w edytorze ćwiczenia) — wklej gotowy
  opis ćwiczenia (własne notatki, fragment książki, tekst przepisany ze
  zdjęcia) i kliknij przycisk. Aplikacja wyciągnie z niego, co się da:
  mięśnie, sprzęt, poziom, wzorzec ruchu, kroki techniki, błędy,
  wskazówki, bezpieczeństwo, warianty, tempo i oddech. Zobaczysz
  **propozycję**: co zostanie wstawione, czego nie udało się odczytać i
  co warto sprawdzić. **Czego nie da się odczytać, zostaje puste — nic
  nie jest zgadywane.** Domyślnie uzupełniamy tylko puste pola, więc Twoja
  praca nie znika; nadpisanie wypełnionych pól włączasz osobno.
  Przycisk „Przepisz ze zdjęcia" w tym samym panelu pozwala zrobić
  zdjęcie kartki albo strony z książki i wstawić przepisany tekst do pola
  opisu. Nic nie zapisuje się samo — ćwiczenie powstaje dopiero, gdy
  klikniesz „Zapisz".
* **Dieta** — cele kcal/makro, zalecenia tekstowe, posiłki z zamiennikami;
  także wersjonowana z powodem zmiany.
* **Harmonogram** — elementy z kategorią, porą i dniami tygodnia.
  Dla suplementów musisz wpisać **autora/źródło zalecenia** — aplikacja
  tylko przypomina o planie wpisanym przez człowieka i nigdy sama nie
  ustala dawek. U góry zakładki (0.63.0) panel **„Nawyki"** klienta:
  możesz zaproponować do trzech startowych nawyków (nazwa, dni, termin
  14–254 dni, notatka dla klienta — zapisany jesteś jako autor), odhaczyć
  dzień wspólnie z klientem i zobaczyć postęp. Klient odhacza je na swoim
  ekranie „Dzisiaj" i może je zmienić; po osiągnięciu terminu nawyk dostaje
  absolutorium i przestaje być odhaczany (rusztowanie, nie streak).
* **Raporty** — raporty tygodniowe klienta (masa, skale 1–5, zdjęcia,
  pytania, ból). Opcjonalnie skorzystaj z podsumowania AI (jeśli
  skonfigurowane), odpowiedz, opcjonalnie oceń raport (1–5 — to ocena
  **kompletności/jakości raportu**, nie klienta) i oznacz jako oceniony;
  na tej podstawie twórz nową wersję planu.
* **Pomiary** — wykresy masy i obwodów w czasie.
* **Płatności** — utwórz pakiet (nazwa, kwota, okres, pierwszy termin);
  oznaczaj wpłaty jako opłacone, dodawaj kolejne terminy. Klient widzi
  status u siebie.
* **Historia** — pełna lista zmian z pokwitowaniami (kto, co, kiedy,
  z jakim powodem).

## Wymiany produktów u klienta (szablony diet)

Klient wymienia składniki sam; Ty decydujesz, czy wymiany są włączone
(globalnie albo per posiłek) i widzisz historię z poziomem: „ta sama grupa"
lub „grupa pokrewna". Grupy pokrewne (np. kasza ↔ makaron, jogurt ↔ jajka)
to tabela tylko do odczytu w panelu „Szablony diet" — propozycja do Twojego
przeglądu; pary oznaczone „?" są wyłączone, dopóki właściciel ich nie
włączy. Wymiana nie wyprowadza posiłku poza tolerancję, a posiłku już
poza nią nie pogarsza; nigdy nie omija alergenów i wykluczeń klienta. Poprawki powiązań zgłaszasz właścicielowi (edycja
z panelu to osobna runda). Katalog produktów z Bazy wiedzy nie zasila
wymian bezpośrednio — trafia tam tylko przez przeglądany import (CSV
propozycji z decyzjami TAK/NIE, alergeny do potwierdzenia przez Ciebie).
## Monitoring (zakładka „Monitoring" — po włączeniu modułu)

Lista Twoich aktywnych klientów posortowana po sygnałach: brak treningu
od X dni, frekwencja poniżej progu w dwóch kolejnych tygodniach, spadek
tonażu wobec średniej z 4 tygodni, brak ważenia, trend wagi niezgodny
z celem redukcji, a także sygnał pozytywny — nowy rekord (powód do
kontaktu, nie ocena). Progi zmieniasz na górze listy (nie zapisują się
między sesjami). Wejście w klienta pokazuje **ten sam układ, który widzi
klient** (kafelki tygodnia, Rekordy, Trening, Konsekwencja, Sylwetka),
ale z pełnymi danymi: pojedyncze pomiary wagi z przełącznikiem średniej,
Twoje notatki (obserwacje) przy datach, zmiany wersji planu na tle
tonażu. Jeśli klient ma flagę zdrowotną z wywiadu kalorycznego, on nie
widzi „Sylwetki" ani trendu wagi — Ty widzisz i dostajesz o tym
informację na górze. Sekcje, na które klient nie dał zgody (dane
zdrowotne, zdjęcia, żywienie), po prostu nie przychodzą z serwera.

Dwie zasady, które pilnują sensu liczb: przy zapisie serii oznaczaj
**rozgrzewkę** (nie liczy się do rekordów i tonażu) i wybieraj
**jednostkę** (funty przeliczają się na kg). Rekordy liczą się od
drugiego wykonania ćwiczenia — pierwsza sesja to punkt odniesienia;
szacowany 1RM to zawsze szacunek do obserwacji trendu, nie zalecenie
obciążenia. Nie ma rankingów między klientami. Po włączeniu modułu na
produkcji historię sesji sprzed włączenia przelicza jednorazowo
`python -m dzik_os.recalculate_progress` — wypisuje też nazwy ćwiczeń,
które różnią się tylko diakrytyką albo znakami interpunkcyjnymi
(„bliźniaki"; wielkość liter i odstępy są już ujednolicane);
takie wpisy scalasz ręcznie, poprawiając nazwę w treningu.

## Rozgrzewka, rozciąganie i cardio z suwakami (od 0.73.0)

* **W edytorze planu** (nowy plan albo nowa wersja) każdy dzień ma trzy
  przyciski: „+ Rozgrzewka” i „+ Rozciąganie” wstawiają blok z Twojego
  katalogu (rozgrzewka na początek dnia, rozciąganie na koniec; plan zapisuje
  migawkę treści, więc późniejsza edycja bloku nie zmienia opublikowanych
  planów), „+ Cardio” otwiera panel z suwakami.
* **Suwaki:** Redukcja (wydatek energii) / Wydolność (VO2max) / Regeneracja
  (baza tlenowa) sumują się do 100 % — przesunięcie jednego zabiera pozostałym
  proporcjonalnie; kłódka blokuje suwak. Wybierasz poziom klienta i **dozwolone
  urządzenia** (klient wybiera jedno w dniu treningu). **Kwalifikacja zdrowotna**
  jak w konfiguratorze + pytanie o leki wpływające na tętno (beta-blokery):
  bez odpowiedzi nie ma propozycji; objawy alarmowe = brak propozycji i pomoc
  doraźna; choroba bez ustalonego poziomu wysiłku = propozycja tylko dla Ciebie
  z ostrzeżeniem (klient nic nie widzi, dopóki nie zapiszesz wersji). Wiek, tętno
  spoczynkowe i masa wypełniają się z danych klienta tylko wtedy, gdy masz zgodę
  na dane zdrowotne — możesz je wpisać ręcznie albo liczyć bez tętna (RPE + test
  mowy). Bramka nie jest zapisywana w planie.
* **„Policz propozycję”** daje zakres % tętna maksymalnego (±5), ud./min (z wzoru
  wiekowego ±10 albo z rezerwy tętna, gdy jest tętno spoczynkowe), RPE, test
  mowy, czas, strukturę (ciągła / tempo / interwały wg poziomu) i „zacznij od…”
  per urządzenie. **To propozycja, nie porada medyczna** — każdą liczbę zmienisz
  w „Zmień liczby ręcznie” (zapisze się jako Twoja decyzja w śladzie „Dlaczego?”).
  „Wstaw do dnia” dodaje pozycję; klient zobaczy ją po zapisaniu wersji.
* **Do przeglądu przed użyciem u prawdziwych klientów:** treść 12 wbudowanych
  bloków, 9 nowych wpisów katalogu (bieg ciągły, wiosłowanie ciągłe, 7 rozciągań)
  i tabela ustawień urządzeń — wszystko oznaczone „do przeglądu trenera”
  (`docs/cardio/PROGRESS.md`). Nic nie progresuje automatycznie tydzień do
  tygodnia — kolejny tydzień układasz Ty.

## Przypisz plan: szablon + bloki (od 0.76.0)

W karcie klienta → Plan przycisk **„Przypisz plan (szablon i bloki)”** otwiera
kartę „Przypisz plan” (zastępuje dawne „Z szablonu… / Kopiuj do klienta”):

* **Podstawa planu:** „Szablon treningowy” (wybierasz z listy swoich szablonów —
  bez bloków to dokładnie dawne kopiowanie) albo **„Bez szablonu — tylko bloki”**
  (podajesz nazwę planu i liczbę dni 1–7; dni nazywają się „Dzień 1…”, dzień
  tygodnia ustawisz później w edytorze albo klient wybierze w „Twoich dniach”).
* **Trzy wybory bloków** z Twojego katalogu (Szablony → Bloki): **Rozgrzewka**
  (na początek każdego dnia), **Aeroby (cardio)** (po ćwiczeniach siłowych) i
  **Rozciąganie** (na koniec każdego dnia) — po jednym na rodzaj, każdy z opcją
  „bez”; etykieta „poziom · wariant/cel · ≈min”. Brak bloków danego rodzaju =
  link do Szablony → Bloki → „Dodaj wbudowane”.
* **Podsumowanie** przed wysłaniem („Szablon X + rozgrzewka Y + aeroby Z →
  3 dni”) i przycisk **„Przypisz klientowi”**. Po sukcesie komunikat mówi, co
  dokładnie się stało („Dodano rozgrzewkę do 3 dni, cardio do 3 dni”); dzień,
  który w szablonie miał już blok tego rodzaju, nie dostaje drugiego.
* Plan klienta jest **kopią z migawkami** — późniejsza edycja szablonu ani
  bloku nic w nim nie zmienia; pochodzenie z szablonu zostaje w historii.

**Aeroby (cardio) jako blok** (od 0.76.0): 9 wbudowanych (3 cele × 3 poziomy —
regeneracja ciągła 20–25 min, wydolność interwały 8×1 / 6×2 / 4×4, redukcja
ciągła 30–40 min) i własne („+ Nowy blok” → rodzaj „Aeroby (cardio)”: cel,
poziom, urządzenia — zakresy liczy silnik). Preset jest liczony **bez danych
klienta**: klient dostaje RPE, % tętna maksymalnego i test mowy, bez ud./min.
W edytorze planu wstawisz go przyciskiem **„+ Cardio z bloku”** (także w
szablonie, gdzie „+ Cardio” z suwakami wymaga klienta); po przypisaniu możesz
policzyć wersję pod klienta w „+ Cardio” i zastąpić pozycję.

## Szablony

Zakładka „Szablony": twórz plany bez przypisanego klienta i odtwarzaj je
przy zakładaniu planu klientowi (od 0.76.0 razem z blokami — sekcja wyżej).

* **Lista po nazwach** (od 0.75.0) — każdy szablon to nazwa z meta „dni ·
  pozycje · data”; kliknięcie w nazwę rozwija dni, ćwiczenia, panel publikacji
  (szkic → sprawdź zmiany → publikuj) i notkę o kopiowaniu; drugie kliknięcie
  zwija. Przy ćwiczeniu z Twojej bazy jest link „Karta w Wiedzy” (z powrotem do
  szablonów). W zakładce Dieta nazwa szablonu diety działa tak samo jak „Podgląd”.
* **Opis ćwiczenia u klienta** (od 0.75.0) — podopieczny widzi pod każdym
  ćwiczeniem planu „Opis ćwiczenia” (skrót z Twojej bazy: technika w punktach,
  błędy, mięśnie) i „Pełny opis w Wiedzy”. Dopasowanie: po powiązaniu z bazą
  („z bazy” w edytorze), a bez niego **po nazwie** — ćwiczenie z importu pliku
  albo wpisane ręcznie dostanie opis, jeśli w Wiedzy → Ćwiczenia masz wpis pod tą
  samą nazwą (wielkość liter i polskie znaki bez znaczenia; przy dwóch wpisach o
  tej samej nazwie wygrywa starszy). Ten sam „Opis ćwiczenia” widzisz w karcie
  klienta → Plan, a w edytorze i szkicu — link „Karta w Wiedzy”. Brak wpisu =
  klient widzi „Brak opisu tego ćwiczenia w Wiedzy”; wystarczy dodać ćwiczenie
  do bazy pod tą nazwą.

* **Bloki** (od 0.73.0) — trzecia zakładka Szablonów: „Dodaj wbudowane” ładuje
  9 rozgrzewek, 9 bloków aerobów (od 0.76.0) i 3 bloki rozciągania (drugie kliknięcie niczego nie dubluje),
  „+ Nowy blok” i „Edytuj” (pozycje: jedna linia = „nazwa | dawka | notatka”),
  „Archiwizuj” zamiast kasowania. Zarchiwizowany blok znika z wyboru w edytorze,
  ale plany z jego migawką działają dalej.

## Baza wiedzy

Zakładka „Wiedza" ma cztery karty:

* **Artykuły** — materiały (tekst, link, załącznik) widoczne dla
  wszystkich aktywnie prowadzonych klientów.
* **Ćwiczenia** — Twoje know-how: nazwa, partia mięśniowa, jak wykonać,
  co to daje, sprzęt, link do wideo. Widoczne dla klientów w ich własnej
  bazie wiedzy.
* **Produkty** — baza ponad 400 produktów z kaloriami, makro i błonnikiem
  na 100 g. Wpisz gramaturę **albo liczbę sztuk** („2 jajka”, „1 kromka”),
  żeby zobaczyć przeliczenie. Szukaj po nazwie (polskie znaki nie mają
  znaczenia: „losos” znajdzie „Łosoś”), filtruj po kategorii i sortuj po
  kaloriach lub białku; lista dokłada kolejne pozycje przyciskiem
  „Pokaż więcej”. Klienci widzą tę samą bazę z kalkulatorem porcji u siebie.
  **Wartości są przybliżone i uśrednione** — zależą od marki, partii i
  obróbki; to punkt wyjścia do oszacowania, nie pomiar. Możesz dograć
  własne produkty hurtem (**import CSV**) i w każdej chwili pobrać cały
  katalog do pliku (**eksport CSV**) — import dotyka wyłącznie Twoich
  produktów, katalogi innych trenerów są od siebie odseparowane. Szczegóły
  formatu: `docs/BAZA_PRODUKTOW.md`.
* **Kompozytor diety** — podaj cel (kcal + białko/tłuszcz/węglowodany),
  zaznacz produkty z bazy, a system rozłoży cel na gramaturę wg
  dominującego makroskładnika każdego produktu. To wyłącznie przejrzysta
  arytmetyka — **nic nie zapisuje się automatycznie**; wynik skopiuj i
  wklej ręcznie do zakładki „Dieta" klienta, jeśli Ci odpowiada.

Zakładka „Dieta" (kreator diety: „Wygeneruj propozycję", „Ułóż sam
z produktów", „Ułóż z dań") jest od 0.67.0 ukryta — pokazuje się tylko,
gdy operator włączy `DZIK_DIET_WIZARD_ENABLED`. Twoje ręczne plany
żywieniowe, szablony diet i zakładka „Produkty" działają jak dotąd.

## Zasady

* Widzisz wyłącznie klientów, z którymi masz aktywną współpracę i zgodę.
* Wszystkie Twoje istotne operacje są zapisywane w niezmienialnej
  historii (audyt) — to chroni także Ciebie.
* Wiadomości: zakładka „Wiadomości" — wątek per klient, załączniki
  (zdjęcia, PDF, MP4 do 20 MB).

## Jeden aktywny plan na klienta (0.78.0)

Przypisanie planu — z szablonu, z bloków albo obu naraz — **archiwizuje
poprzedni plan klienta**. Tak samo zachowuje się dieta od 0.60.0. Dotąd stary
plan zostawał aktywny i niewidoczny, bo ekran klienta pokazuje najnowszy.

Archiwizacja niczego nie kasuje: plan zostaje z całą historią wersji i widać go
po włączeniu archiwum. Komunikat po przypisaniu mówi, ile planów zarchiwizowano.

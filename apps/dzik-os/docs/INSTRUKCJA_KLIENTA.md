# Instrukcja dla podopiecznego — Dzik OS

## Instalacja na telefonie

Otwórz adres aplikacji w przeglądarce, zaloguj się i wybierz
„Dodaj do ekranu głównego" (Android/Chrome: menu ⋮ → „Zainstaluj
aplikację"; iPhone/Safari: Udostępnij → „Do ekranu początkowego").

Konto zaczyna się od **linku aktywacyjnego** od trenera (e-mail albo
przekazany bezpośrednio): otwierasz link, widzisz swoje konto i **sam
ustawiasz hasło** — nikt inny (także trener) go nie zna. Link działa
tylko raz i wygasa po 7 dniach; w razie czego trener wyśle nowy.

Przy pierwszym logowaniu aplikacja poprosi Cię o **potwierdzenie
zgody** na dostęp trenera do Twoich danych — możesz ją też odrzucić,
a później w każdej chwili cofnąć w Profilu.

W Profilu możesz dodatkowo włączyć **weryfikację dwuetapową (MFA)** —
kod z aplikacji uwierzytelniającej przy każdym logowaniu (opcjonalnie),
z jednorazowymi kodami odzyskiwania na wypadek utraty telefonu — oraz
podejrzeć aktywne sesje i historię zdarzeń bezpieczeństwa. Zapomniane
hasło zresetujesz przez „Nie pamiętasz hasła?" na ekranie logowania.

## Ekran „Dzisiaj"

Przy **pierwszym logowaniu** (od 0.70.0) zobaczysz krótki, dwuetapowy
**samouczek**: co gdzie jest, dlaczego warto zacząć od zgód i wywiadów,
i co jeszcze potrafi aplikacja. To pomoc, nie warunek — „Pomiń na razie"
(albo Esc) zamyka go od razu, „Rozumiem, zaczynajmy" kończy. Nie wróci sam
(także na innym telefonie), a otworzysz go ponownie w każdej chwili:
**„Więcej" → „Pomoc / Samouczek"**.

Po zalogowaniu widzisz wszystko na dziś: trening z przyciskiem
**„Wykonane ✓"**, cele diety, harmonogram (posiłki, suplementy, pomiary),
termin raportu, status płatności i ostatnią wiadomość trenera.

U góry (od 0.63.0): **powitanie**, **hasło dnia** (sentencja z autorem —
ta sama przez cały dzień) i panel **„Nawyki"**. Wybierz do trzech małych
czynności, które chcesz utrwalić („Dodaj nawyk": nazwa, dni tygodnia,
termin — domyślnie 66 dni). Każdego zaplanowanego dnia odhaczasz
**„Wykonane"**; pomyłkę cofniesz jednym dotknięciem. Postęp opisuje stan
(„12 z 66 — nawyk się rozkręca"): opuszczony dzień cofa go o jeden, ale
nigdy poniżej zera i bez żadnych komunikatów-kar — dni poza planem to
zwykły odpoczynek. Gdy postęp dojdzie do terminu, zobaczysz
**absolutorium**: ta czynność stała się Twoim nawykiem, aplikacja
przestaje o nią pytać, a Ty wybierasz „Wymień na nowy" albo „Zostaw tak
jak jest". Trener może zaproponować nawyki startowe (z notatką) — możesz
je zmienić.

**Trening na dziś** (od 0.71.0) bierze się z **Twoich dni tygodnia**: jeśli
masz plan, ale nie wybrałeś jeszcze dni, zobaczysz kartę „Masz plan, ale nie
wybrałeś dni tygodnia" z przyciskiem do zakładki Plan. Po wyborze trening
z dzisiejszego dnia pojawia się tutaj z podpisem „Twój wybór" (albo
„propozycja trenera", jeśli korzystasz z jego układu). Gdy trener zmieni
plan, dostaniesz łagodną notkę „Plan się zmienił — sprawdź dni tygodnia".

## Rozmowa startowa

Na początku aplikacja proponuje **rozmowę startową**: kilkanaście pytań
o cel, dostępność, sprzęt, zdrowie i preferencje — **jedno na raz**,
z krótkim wyjaśnieniem, po co jest potrzebne.

* każde pytanie możesz **pominąć** („Pomiń to pytanie") — to normalna
  odpowiedź, nie brak;
* możesz **wrócić** i poprawić wcześniejszą odpowiedź; poprzednia wersja
  zostaje w historii, więc nic nie znika po cichu;
* możesz **przerwać** w dowolnym momencie („Przerwij i wróć później") —
  wrócisz dokładnie w to samo miejsce, także z innego urządzenia;
* pytania o zdrowie i żywienie pojawiają się **tylko wtedy**, gdy masz
  aktywną zgodę na te kategorie danych; cofnięcie zgody usuwa je
  natychmiast;
* na końcu widzisz **podsumowanie**: możesz je poprawić i dopiero potem
  zatwierdzić. Dopiero Twoje zatwierdzenie zapisuje dane w profilu —
  potem trener przegląda je i zatwierdza jako podstawę planu.

Wolisz klasyczny formularz? „Wolę formularz" na ekranie Dzisiaj prowadzi
do **wywiadu startowego** — zapisuje dokładnie te same pola.

## Głęboki wywiad („Więcej → Głęboki wywiad")

Gdy współpraca już ruszy, warto przejść **głęboki wywiad** — dłuższą
rozmowę (kilkadziesiąt pytań w dziewięciu blokach: motywacja, historia
treningowa, zdrowie, sen, stres, jedzenie, logistyka tygodnia, punkt
startu, zasady współpracy). Działa dokładnie jak rozmowa startowa:
jedno pytanie na raz z wyjaśnieniem „po co", każde można pominąć,
można przerwać i wrócić, poprawki mają historię, a na końcu sam(a)
zatwierdzasz podsumowanie, zanim trafi do profilu. Pytania o zdrowie
i żywienie istnieją wyłącznie w zakresie Twoich zgód, a odpowiedzi
wskazujące na potrzebę konsultacji lekarskiej dostają spokojną
informację — nikt niczego nie ocenia. **Nic z tego wywiadu nie jest
wysyłane do modelu AI** — podsumowanie powstaje zawsze z Twoich
własnych słów.

Jeśli w rozmowie opiszesz coś, co wykracza poza kompetencje trenera
(np. ból w klatce piersiowej, omdlenia, duszność, ostry ból po urazie),
aplikacja pokaże spokojny komunikat kierujący do lekarza. **Niczego nie
ocenia ani nie diagnozuje** — po prostu zaznacza to trenerowi, żeby
wstrzymał się z planem do czasu Twojej konsultacji.

Podsumowanie rozmowy może przygotować model językowy — ale wyłącznie
jako propozycję do Twojej korekty i tylko wtedy, gdy włączysz zgodę
„Funkcje AI". Bez niej rozmowa i podsumowanie działają tak samo, tylko
bez tej propozycji. Model nigdy nie układa planu ani diety.

## Trening (zakładka „Plan")

* aktualny plan z rozpiską dni i ćwiczeń (serie × powtórzenia, ciężar,
  tempo, przerwy, filmy z techniką);
* **„Opis ćwiczenia”** (od 0.75.0) — pod każdym ćwiczeniem (także w
  pozycjach rozgrzewki i rozciągania oraz na ekranie „Dzisiaj”): kliknięcie
  rozwija skrót z bazy trenera — technikę w punktach, najczęstsze błędy
  i pracujące mięśnie; przycisk **„Pełny opis w Wiedzy”** otwiera pełną kartę
  (warianty, tempo i oddech, bezpieczeństwo, mapa mięśni, wideo), a „Wróć do
  planu” prowadzi z powrotem. Jeśli trener nie ma tego ćwiczenia w swojej
  bazie, zobaczysz wprost „Brak opisu tego ćwiczenia w Wiedzy” — zapytaj
  trenera. Ćwiczenia z pliku lub wpisane ręcznie dopasowujemy po nazwie
  (wielkość liter i polskie znaki nie mają znaczenia);
* „Zapisz wykonanie z wynikami" — wpisz osiągnięte wyniki, komentarz,
  a jeśli coś bolało — zaznacz „Zgłaszam ból" i opisz; trener to zobaczy
  od razu na swojej liście;
* „Historia wersji" — każda zmiana planu ma powód i datę; nic nie znika.
* **Rozgrzewka i rozciąganie** (od 0.73.0) — jeśli trener wstawił blok, zobaczysz
  go jako jedną pozycję z odznaką „rozgrzewka” albo „rozciąganie”: „Pokaż
  pozycje” rozwija listę z dawką („3 min”, „2×10”, „20 s/str.”) i linkiem do
  techniki. W formularzu wykonania odhaczasz cały blok („wykonane w całości”).
* **Cardio z suwakami** (od 0.73.0) — pozycja z odznaką „cardio”: trzy paski
  pokazują, jak trener rozłożył cele (Redukcja / Wydolność / Regeneracja);
  jeśli trener dopuścił kilka urządzeń, wybierasz na dziś (rowerek, bieżnia,
  bieżnia skos, steper, wioślarz); „Zacznij od…” to ustawienia startowe —
  dojdź do tętna albo RPE z zakresu, urządzenia różnią się kalibracją. Zakres
  tętna to **zakres, nie jedna liczba** (wzór wiekowy ma błąd ±10 ud./min);
  równoprawne są RPE (1–10) i test mowy. Timer odmierza czas albo odcinki
  pracy/przerwy. W formularzu wykonania wpisujesz czas, RPE, opcjonalnie
  średnie tętno i dystans — bez serii i kilogramów. „Dlaczego takie cardio?”
  pokazuje, skąd wzięły się liczby. To propozycja trenera, nie porada medyczna;
  jeśli przyjmujesz leki wpływające na tętno, trener ustawi tryb bez tętna.
* **Aeroby z bloku** (od 0.76.0) — trener może dołożyć do każdego dnia planu
  gotowy blok aerobów (odznaka „cardio” + „z bloku”, nagłówek „Aeroby (cardio) ·
  poziom · ≈min” i krótki opis: urządzenia, intensywność, struktura). Działa jak
  cardio z suwakami — paski celów, wybór urządzenia, timer, dziennik czasu/RPE —
  ale bez tętna w ud./min: prowadź według RPE i testu mowy, dopóki trener nie
  policzy wersji pod Ciebie. Rozgrzewka jest zawsze na górze dnia, aeroby po
  ćwiczeniach siłowych, rozciąganie na dole.
* **Tętno spoczynkowe** (od 0.73.0) — w zakładce Postępy → „Dodaj pomiar” możesz
  wpisać tętno spoczynkowe (ud./min); trener użyje go do dokładniejszego
  zakresu (rezerwa tętna). To dana zdrowotna — objęta Twoją zgodą.
* **„Twoje dni treningowe"** (od 0.71.0) — nad listą dni: dla każdej
  jednostki wybierz dzień tygodnia (pon.–niedz.) albo „— (bez dnia)". Na
  start podpowiadamy propozycję trenera; „Zapisz dni" — i trening
  z dzisiejszego dnia trafia na ekran „Dzisiaj". Jeden dzień tygodnia to
  jedna jednostka (przy próbie podwojenia zobaczysz komunikat przy polu).
  „Wróć do propozycji trenera" przywraca jego układ. Twój wybór nie zmienia
  planu trenera — to Twoja nakładka; trener ją widzi w Twojej karcie.

## Wymiana produktu w diecie (zakładka „Dieta")

Przy składniku posiłku jest przycisk „↔ wymień" — także przy warzywach
i dodatkach. Zobaczysz do trzech zamienników: „z tej samej grupy" albo
„grupa pokrewna: …" (np. kasza zamiast makaronu), gramaturę policzoną tak,
żeby posiłek zachował swoją rolę, i zmianę makr posiłku po polsku. Serwer
sprawdza wymianę: nie przejdzie taka, która zepsuje makra posiłku bardziej,
niż są dziś. Jeśli listy nie ma, przeczytasz dlaczego (brak zamienników
w bazie, Twoje wykluczenia, inna metoda przygotowania, porcja poza
zakresem albo każdy zamiennik psuje makra). Gdy brak zamienników w bazie,
porcja jest poza zakresem albo każdy zamiennik psuje makra — napisz do
trenera, on poprawi posiłek.

## Postępy (zakładka „Postępy" — gdy trener włączy moduł)

Jedno miejsce z trzema osiami, zawsze w tej kolejności: **Forma**
(rekordy własne: najcięższa seria, powtórzenia przy danym ciężarze,
szacowany 1RM — zawsze podpisany jako szacunek, nie zalecenie
obciążenia; tonaż tygodniowy ze średnią z 4 tygodni; serie na grupę
mięśniową; kalendarz aktywności), **Konsekwencja** (wykonane / zaplanowane
treningi z 8 tygodni, seria tygodni z wykonanym planem, realizacja diety)
i **Sylwetka** (waga wyłącznie jako średnia z 7 dni — pojedynczy pomiar
nie jest „Twoją wagą"; trend kg/tydzień z 28 dni; obwody; zdjęcia
z porównywarką; tu też dodajesz pomiar). Rekord liczy się od drugiego
wykonania ćwiczenia — pierwsza sesja to punkt odniesienia; seria
oznaczona jako rozgrzewka nie liczy się do rekordów. Porównanie zawsze
wyłącznie z Twoją własną historią, nigdy z innymi. Jeśli w wywiadzie
kalorycznym padła odpowiedź, po której trener prowadzi Cię ostrożniej,
sekcja „Sylwetka" i trend wagi nie pokazują się w aplikacji — to
celowe, nie awaria. Gdy moduł jest włączony, raport tygodniowy
znajdziesz w „Więcej → Raport tygodniowy" (stary adres przekierowuje).

## Raport tygodniowy (zakładka „Raport"; po włączeniu „Postępów" — „Więcej → Raport tygodniowy")

Raz w tygodniu: masa, liczba treningów, oceny 1–5 (energia, sen, głód,
stres, regeneracja, dieta), zdjęcia sylwetki, komentarz i pytania.
Możesz wysłać poprawkę — poprzednia wersja zostaje w historii. Odpowiedź
trenera pojawi się przy raporcie, czasem razem z oceną raportu (1–5) —
to ocena kompletności raportu, nie Ciebie.

## Pozostałe (zakładka „Więcej")

* **Pomiary i postępy** (po włączeniu zakładki „Postępy" — jej sekcje
  Konsekwencja i Sylwetka) — dodawaj pomiary, oglądaj wykresy i zdjęcia;
  karta „🏆 Rekordy osobiste" pokazuje Twoje najlepsze wyniki i zmianę od
  startu — porównanie zawsze wyłącznie z Twoją własną historią, nigdy z
  innymi;
* **Baza wiedzy** — artykuły trenera, know-how ćwiczeń (partia, technika,
  efekt) i baza produktów z kaloriami, makro i błonnikiem — wyszukaj
  produkt po nazwie i wpisz gramaturę albo liczbę sztuk („2 jajka”),
  żeby zobaczyć przeliczenie. Wartości są przybliżone i uśrednione
  (zależą od marki, partii i obróbki) — to oszacowanie, nie pomiar;
* **Baza wiedzy** — artykuły trenera, baza ćwiczeń (wyszukiwanie po
  nazwie, filtry partii mięśniowej, sprzętu, poziomu i wzorca ruchu;
  karta ćwiczenia z krokami techniki, błędami, wskazówkami, uwagami
  bezpieczeństwa i wariantami) oraz baza produktów z makro — wpisz gramaturę porcji, żeby
  zobaczyć automatyczne przeliczenie kalorii;
* **Dokumenty i harmonogram** — pliki od trenera i pełny harmonogram
  (każdy element ma zapisanego autora);
* **Płatności** — terminy i statusy; aplikacja nie przechowuje danych kart;
* **Wiadomości** — pisz do trenera, wysyłaj zdjęcia i filmy;
* **Pomoc / Samouczek** — ponownie otwiera powitanie z pierwszego
  logowania (dwa kroki: gdzie co jest, co jeszcze warto wiedzieć);
* **Wygląd** — wybierasz motyw aplikacji: „Ciemny (czarno-zielony)”
  (domyślny, czytelny na siłowni) albo „Jasny (czerwono-biały)”. Wybór
  zapisuje się na tym urządzeniu i na Twoim koncie — po zalogowaniu na
  innym telefonie aplikacja wróci do Twojego motywu;
* **Profil, zgody i moje dane** — Twoje dane należą do Ciebie:
  * edytuj profil (historia wersji zostaje),
  * **cofnij zgodę** na dostęp trenera jednym przyciskiem (i udziel ponownie),
  * **eksportuj wszystkie dane** do pliku JSON,
  * **usuń konto i dane** (nieodwracalne; wymaga hasła i frazy
    `USUŃ MOJE DANE`).

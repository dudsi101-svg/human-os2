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
  i nie korzysta z AI.
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
  ustala dawek.
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

## Szablony

Zakładka „Szablony": twórz plany bez przypisanego klienta i odtwarzaj je
przy zakładaniu planu klientowi.

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

## Zasady

* Widzisz wyłącznie klientów, z którymi masz aktywną współpracę i zgodę.
* Wszystkie Twoje istotne operacje są zapisywane w niezmienialnej
  historii (audyt) — to chroni także Ciebie.
* Wiadomości: zakładka „Wiadomości" — wątek per klient, załączniki
  (zdjęcia, PDF, MP4 do 20 MB).

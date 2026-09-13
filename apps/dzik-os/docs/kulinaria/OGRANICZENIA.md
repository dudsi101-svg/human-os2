# Zakres działania i ograniczenia

## Co działa

Filtrowanie produktów zwierzęcych, jawny wariant paleo, alergeny i nieznane informacje alergenne, wykluczone składniki, sprzęt, czas, zatwierdzenia publikacji i porcji. Tryb produkcyjny liczy podane składniki z danych per 100 g, normalizuje węglowodany, kontroluje zadane granice dzienne i limit keto/low carb. Generuje komplet 1–31 kolejnych dni albo stan błędu bez częściowego planu. Tworzy ślad wyboru i listę zakupów w gramach jadalnej masy. Działa kontrola powtórek rodzin w blokach siedmiodniowych.

## Czego nie wolno zakładać

Biblioteka nie ma jeszcze testów kuchennych ani wartości odżywczych. Czasy są oszacowane. Nie przeprowadzono degustacji. Zatwierdzenie techniczne testów nie potwierdza smaku i jakości dietetycznej.

30 rodzin i ich dodatki to mniejsza różnorodność koncepcji niż 300 niezależnych dań. Sześć posiłków dziennie i restrykcyjny limit rodzin mogą nie dać się ułożyć z tej bazy. Nie ma gwarancji menu dla każdego przecięcia filtrów. Raport pokrycia bada kandydatów, nie wykonalność makro.

`mediterranean` zachowuje możliwość użycia dopuszczonych potraw i może korzystać z preferencji kuchni, ale v1 nie waliduje pełnego śródziemnomorskiego wzorca częstotliwości grup żywności w tygodniu. Nie deklaruj takiej certyfikacji. Paleo v1 wyklucza grain, legume i dairy; to jawna uproszczona polityka. Produkty złożone wymagają mapowania wszystkich składowych.

Screening to bramka integracyjna, nie gotowy kwestionariusz kliniczny. Aplikacja źródłowa musi weryfikować zdrowie, leki i zakres planu; użytkownik nie powinien sam sobie ustawiać `cleared` przez dowolne żądanie API. Diety terapeutyczne i szczególne populacje nie są obsługiwane klinicznie.

Wynik produkcyjny jest sprawdzony wyłącznie względem zadeklarowanych dziennych granic. Jeżeli moduł celów nie poda witamin, minerałów lub błonnika, silnik nie potwierdza ich pokrycia. Ocena tygodniowych norm mikroelementów, bilans strat technologicznych, retencja witamin, indywidualny bilans energetyczny i bezpieczeństwo suplementacji wymagają adapterów i dodatkowych reguł.

Solver jest deterministycznym beam search o szerokości 80. Może nie odnaleźć istniejącego rozwiązania, szczególnie w wąskich granicach. Nie jest globalnym optymalizatorem kosztu ani dowodem niewykonalności. Nie oferuje batch cookingu, trwałości żywności, sezonowego budżetu, stanu magazynowego ani dopasowania opakowań sklepowych. Lista zakupów zawiera sumy jadalne, nie gwarantowane ilości zakupowe brutto.

Wersja bazowa nie skaluje czasu i składników dowolnie. Każdy dodatkowy wariant wielkości powinien dostać przetestowaną ilość oraz czas. V1 przechowuje czas na recepturze: jeśli porcja ma inny czas lub technikę, utwórz oddzielną recepturę, nie tylko większy factor.

Bezpieczeństwo serwera, API, przechowywanie danych, migracje i UI są zadaniem integracji. To biblioteka domenowa i CLI, nie gotowy serwis internetowy. Wyniki testów z syntetyczną bazą nie potwierdzają działania na rzeczywistych rekordach dostawcy.

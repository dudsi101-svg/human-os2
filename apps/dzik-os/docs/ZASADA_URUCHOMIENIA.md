# Zasada uruchomienia: nowa funkcja nie jest gotowa, dopóki nie działa

**Ustalone 2026-08-18 przez właściciela produktu, po serii rund, w których
rosła liczba błędów.**

## Zasada

> Każda **zupełnie nowa** funkcja musi zostać **uruchomiona w działającej
> aplikacji** i obejrzana, zanim uznam ją za zrobioną. Przechodzące testy
> nie są dowodem — są warunkiem wstępnym.

„Uruchomiona" znaczy: aplikacja wstaje, idzie **prawdziwe żądanie** (klik w
przeglądarce albo realne wywołanie CLI) i **widzę wynik**. Nie: „testy
zielone, więc pewnie działa".

## Dlaczego akurat to

Trzy przypadki z tego projektu, każdy prawdziwy:

1. **Samoprzeładowanie PWA blokowało logowanie.** Wszystkie testy były
   zielone. Błąd wychodził wyłącznie na świeżym profilu przeglądarki, przy
   pierwszej wizycie — znalazłem go dopiero, gdy sam kliknąłem przez
   aplikację. Bez tego trafiłby na produkcję i wyglądałby jak „nie da się
   zalogować".
2. **Trasa `/coach/exercises/import-schema` była przesłonięta** przez
   starszą `/coach/exercises/{item_id}`. Endpoint istniał, kod był poprawny,
   a aplikacja go nie widziała. Testy złapały to dopiero dlatego, że
   sprawdzały odpowiedź, a nie samo istnienie funkcji.
3. **Tryb ZASTAP w imporcie nadpisywał opisy nieodwracalnie.** Testy
   potwierdzały, że nadpisuje — bo taki był zamiar. Nikt nie sprawdził, co
   się stanie, gdy plik jest zły. To nie jest błąd, który testy wykrywają;
   to pytanie, które trzeba zadać, patrząc na działającą funkcję.

Wspólny mianownik: **test sprawdza to, o co go zapytano**. Uruchomienie
pokazuje to, o co nikt nie zapytał.

## Co konkretnie trzeba zrobić

Zależnie od rodzaju zmiany — minimum jedna pozycja z listy:

| Rodzaj nowości | Dowód uruchomienia |
|---|---|
| Nowy ekran / panel w UI | Klik przez przeglądarkę: wejście, użycie, efekt widoczny na ekranie |
| Nowy endpoint API | Prawdziwe wywołanie na uruchomionej aplikacji (nie tylko `TestClient`) — potwierdza też, że trasa nie jest przesłonięta |
| Nowa komenda CLI | Uruchomienie na realnych danych i pokazanie wyjścia |
| Nowa ścieżka nieodwracalna (kasowanie, nadpisywanie, migracja) | Wykonanie **i odtworzenie**: pokazanie, że da się wrócić |
| Nowa integracja zewnętrzna | Uruchomienie z prawdziwym dostawcą albo jawne powiedzenie, że tryb rozszerzony **nigdy się nie wykonał** |

## Co trafia do raportu

W opisie rundy (CHANGELOG i wiadomość do właściciela) piszę **co zostało
klikniete i co zobaczyłem** — konkretnie, nie „sprawdzone". Przykład z
wersji 0.33.0:

> Przeklik: import ZASTAP niszczy opis, cofnięcie go przywraca, pozycja z
> pomyłki kończy jako ARCHIVED — bez błędów JS.

Jeśli czegoś **nie dało się** uruchomić (brak klucza API, brak urządzenia,
iOS Safari) — mówię to wprost, zamiast pomijać. Niesprawdzone ma być
widoczne jako niesprawdzone.

## Czego ta zasada NIE zastępuje

Testów. Testy pilnują, żeby raz sprawdzona rzecz nie zepsuła się później —
uruchomienie tego nie robi. Zasada dokłada krok, nie zamienia go na inny.

# Współpraca sesji — dokument obowiązujący

**Dzik OS · 2026-08-18 · wersja 1.0**

Jeden dokument nadrzędny. Pozostałe (`KOORDYNACJA.md`, `KONSULTACJE.md`,
`tools/spojnosc.py`) są jego **narzędziami**, nie jego wariantami — jeśli
zaczną mówić to samo innymi słowami, jeden trzeba skreślić.

---

## 1. Diagnoza, z której wszystko wynika

18.08.2026 zdarzyło się **jedenaście kolizji** między dwiema równoległymi
sesjami. Każda została przypisana do przedmiotu, którego naprawdę dotyczyła:

| Przedmiot | Ile | Przykłady |
|---|---|---|
| **zasób współdzielony** | 6 | numery wersji 0.29.0 / 0.36.0 / 0.38.0, migracje 21 i 24, wiersz rezerwacji |
| **różnica założeń** | 5 | przesłonięta trasa, dwa katalogi E2E, nazwa zmiennej, duplikat testu, dwa wejścia ekranu |
| **spór o to, czym ma być produkt** | **0** | — |

**Zero na jedenaście.** Ani razu obie strony nie chciały czegoś innego.

To rozstrzyga rodzaj problemu i cały dobór środków:

> Z opisu **„konflikt"** wynika rozjemca.
> Z opisu **„interferencja"** wynika mechanizm.
> Potrzebny jest ten drugi.

Dwie ręce sięgające po tę samą klamkę nie potrzebują mediacji, tylko zamka.
Słowo „konflikt" było nietrafne od początku i samo dokładało szkód — pod nie
buduje się odruchy obronne zamiast narzędzi.

## 2. Status: dwie połowy jednej roboty

* **sesja produktowa** — **buduje**: funkcje, panel trenera, moduły domenowe,
  ekrany;
* **sesja bramek** — **weryfikuje**: kontrole, CI, E2E, macierz uprawnień,
  integralność, kopie zapasowe.

To nie jest rana do zszycia. To rozdzielenie budowy od weryfikacji — a bramka
GO/NO-GO wypisała jako **bloker nr 1** dokładnie jego brak: *„bramkę wykonał
ten sam agent, który pisał kod"*. **Dwie sesje z tym podziałem są
strukturalnie lepsze niż jedna robiąca obie rzeczy naraz.** To, co wyglądało
na uszkodzenie, jest odpowiedzią na najwyższy bloker na liście.

Z dwoma ograniczeniami, symetrycznymi i nienegocjowalnymi:

* **weryfikujący nie stoi wyżej niż budujący** — znalezisko to informacja,
  nie wyrok; kto znalazł, nie decyduje, czy i jak się to naprawia;
* **budujący nie orzeka o własnej weryfikacji** — „sprawdzone" bez sposobu
  odtworzenia nie jest sprawdzeniem, niezależnie od tego, kto to napisał.

## 3. Podział obszarów

| Obszar | Prowadzi |
|---|---|
| `backend/dzik_os/` — moduły domenowe, `routers/`, `sheet_import.py`, `ai_provider.py` | produktowa |
| `frontend/src/` — ekrany, komponenty, warstwa wizualna | produktowa |
| dokumentacja funkcji i instrukcje dla trenera | produktowa |
| `tools/spojnosc.py`, `tools/mutacje*.py` | bramki |
| `.github/workflows/**`, `frontend/e2e/**`, `apps/dzik-os/e2e/**` | bramki |
| `tests/access_matrix.py`, integralność referencyjna, PostgreSQL | bramki |
| kopie zapasowe i odtwarzanie | bramki |
| `KOORDYNACJA.md`, `KONSULTACJE.md`, `RISK_REGISTER.md`, ten dokument | bramki |

Wejście w cudzy obszar jest dozwolone **wyłącznie w trybie czytania**.
Zmiana wymaga wpisu w `KONSULTACJE.md` i zgody prowadzącego.

## 4. Siedem zasad

Każda wzięta z czegoś **zmierzonego tego dnia**, nie z przekonań.

1. **Zasób współdzielony rezerwuje się przed pracą; kto pierwszy, ten ma.**
   Koszt sprawdzenia: jeden `git fetch`. Koszt niesprawdzenia: trzy kolizje
   o numer wersji w jeden dzień.
2. **Jedna rzecz → PR → scalenie → następna rzecz.** Przez pierwsze sześć
   godzin dnia dało to **zero konfliktów**, mimo że równoległość trwała cały
   czas. Wszystkie kolizje pojawiły się na gałęziach, które przestały się
   tej zasady trzymać.
3. **W cudzym obszarze zgłaszam, nie zmieniam.** Znalezisko przychodzi jako
   opis plus sposób odtworzenia, nigdy jako commit w cudzym pliku — nawet
   gdy naprawa to jedna linia. Zwłaszcza wtedy.
4. **Twierdzenie przychodzi ze sposobem odtworzenia.** To warunek współpracy
   **bez zaufania** — jedynej, jaką mogą prowadzić dwie sesje bez wspólnej
   pamięci. `1164 MB` znaczy to samo niezależnie od tego, kto to napisał
   i w jakim tonie.
5. **Przy scalaniu czyta się obie zmiany, nie tylko rozwiązuje konflikt.**
   Git widzi kolizje TEKSTU; kolizja ZNACZENIA przechodzi bez śladu. Dziś
   scalenie po cichu nadpisało świeżo wpisaną cudzą rezerwację i wyszło to
   wyłącznie przy czytaniu.
6. **Co jedna strona odkryje, druga dostaje jako narzędzie, nie jako zarzut.**
   Przegląd mutacyjny, kontrole bramki, test wykrywania manipulacji audytem —
   powstały po jednej stronie, działają dla obu.
7. **Poprawka do własnego wcześniejszego twierdzenia jest obowiązkowa.**
   Dziś padło zdanie „nie zginął żaden plik", a kilka godzin później narzędzie
   `mutacje.py` skasowało półtorej godziny pracy. Sprostowanie nie jest
   uprzejmością — bez niego zapis przestaje być zapisem.

## 5. Jak się konsultować

Jedno miejsce: **`KONSULTACJE.md`**. Pytania, uprzedzenia o zmianach
dotykających cudzego obszaru, wyjaśnienia „dlaczego tak, a nie inaczej".

**Dlaczego ten dokument zadziała, choć cztery poprzednie nie zadziałały:**
`tools/spojnosc.py` go **czyta i wypisuje otwarte wpisy przy każdym
uruchomieniu bramki** — lokalnie i w CI.

```
UWAGA [konsultacje] K-002 otwarte od 3.4 h, adresat: produktowa
```

Cztery pytania sesji produktowej z 18.08 czekały w pliku planu i zostały
odpowiedziane wyłącznie dlatego, że druga strona **przypadkiem** tam
zajrzała. Dokument bez bramki to dokument, który ktoś kiedyś przeczyta.

* otwarty wpis → **uwaga**, nigdy błąd (blokowanie builda nauczyłoby
  wszystkich obchodzić bramkę);
* `Blokuje: tak` starsze niż 4 h → **głośniejsza uwaga**, bo tam ktoś stoi;
* zepsuty format wpisu → **błąd**, bo wpis nieczytelny dla bramki jest
  gorszy niż jego brak.

## 6. Rozstrzyganie różnic

Do 18.08 nie zdarzyła się ani jedna, ale odpowiedź musi istnieć wcześniej.

1. **Rozstrzyga mechanizm** — kto rezerwował pierwszy, co mówi bramka, co
   pokazuje pomiar. Sprawa zamknięta, bez dyskusji.
2. **Różnica techniczna bez mechanizmu** — wygrywa strona z odtwarzalnym
   dowodem. Brak dowodu po obu stronach znaczy, że trzeba go **zdobyć**,
   a nie przekonywać.
3. **Różnica co do tego, czym ma być produkt** — decyduje **właściciel
   produktu**. Żadna sesja nie rozstrzyga tego sama.

**I zasada w drugą stronę:** żadna sesja nie eskaluje do właściciela rzeczy,
które zamyka punkt 1 albo 2. Rozjemca nie jest tu potrzebny — patrz §1.

## 7. Narzędzia

| Narzędzie | Do czego | Kiedy |
|---|---|---|
| `tools/spojnosc.py` | 9 kontroli: migracje, changelog, trasy, routery, testy frontendu, dokumenty, higiena gałęzi, pliki poza gitem, konsultacje | przed każdym scaleniem i w CI |
| `tools/mutacje.py` | psuje bramkę 14 sposobami i sprawdza, czy testy to widzą | po każdej zmianie w `spojnosc.py` |
| `tools/mutacje_bezpieczenstwa.py` | wyłącza 9 zabezpieczeń i sprawdza, czy testy to widzą | przed decyzją o wydaniu |
| `KOORDYNACJA.md` | jak działa każda kontrola i skąd się wzięła | przy dokładaniu kontroli |
| `KONSULTACJE.md` | pytania i odpowiedzi między sesjami | na bieżąco |

## 8. Nadrzędne zadanie

Wszystkie zasady wyżej służą jednemu i **mogą być zmienione, gdy przestaną
mu służyć**:

> **Doprowadzić Dzik OS do stanu, w którym powierzenie mu prawdziwych danych
> prawdziwego człowieka jest decyzją uzasadnioną, a nie ryzykowną.**

Stan na dziś: **warunkowe GO na pilotaż z jednym klientem, NO-GO na szerszą
produkcję, siedem blokerów** (`BRAMKA_GO_NOGO.md` §5). Lista blokerów jest
wspólna, nie „czyjaś".

**Sprawdzian dla każdej rundy obu sesji:** *który z siedmiu blokerów ta praca
obniża?* Jeśli żadnego i nie zamyka też drogi do cichej utraty pracy — warto
zapytać, czy jest teraz potrzebna.

## 9. Jak ten dokument się zmienia

Spisała go jedna strona, więc obowiązuje w takim zakresie, w jakim druga go
używa. **Zmiana dowolnego punktu przez sesję produktową jest z góry przyjęta
i nie wymaga uzgodnienia z autorem** — wystarczy wpis w `KONSULTACJE.md`
mówiący co i dlaczego. Sprzeczność, której nie da się usunąć, rozstrzyga
właściciel produktu wg §6.3.

Zasada, która nie podlega zmianie przez żadną z sesji: **§8 jest nadrzędne
wobec wszystkiego powyżej.** Jeśli którakolwiek zasada zaczyna szkodzić
zadaniu z §8, obowiązkiem jest to zgłosić, a nie jej bronić.

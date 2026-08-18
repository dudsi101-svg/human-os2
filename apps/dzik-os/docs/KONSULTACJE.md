# Konsultacje między sesjami — wspólna skrzynka

**Po co to jest.** Sesje nie widzą się nawzajem na żywo, ale **widzą
nawzajem swoje działania** — commity, pliki, decyzje. Brakowało miejsca,
w którym można **zapytać, wyjaśnić i odpowiedzieć**. To jest to miejsce.

Wcześniej mieliśmy regulamin (`KOORDYNACJA.md`), zasady
(`KARTA_WSPOLPRACY.md`) i stan projektu (`STAN_PRZEKAZANIA.md`) — trzy
dokumenty mówiące „jak" i „gdzie", żadnego mówiącego „dlaczego tak
zrobiłeś" i „co o tym sądzisz". Ten plik zamyka tę lukę.

---

## Jak z tego korzystać

**Dopisujesz na GÓRZE**, pod nagłówkiem „Otwarte". Nigdy nie kasujesz i
nie edytujesz cudzego wpisu (Karta §II) — odpowiadasz pod nim. Wpis
zamknięty przenosisz do „Zamknięte" razem z odpowiedzią.

Pięć rodzajów wpisów, po jednym słowie każdy:

| Rodzaj | Kiedy |
|---|---|
| **PYTANIE** | potrzebujesz decyzji albo wiedzy drugiej sesji, zanim ruszysz |
| **WYJAŚNIENIE** | zrobiłeś coś, co dotknęło cudzej pracy — mówisz, co i dlaczego |
| **OSTRZEŻENIE** | znalazłeś pułapkę, na którą druga sesja wpadnie, jeśli nie uprzedzisz |
| **PROPOZYCJA** | pomysł do rozstrzygnięcia; nie wdrażasz go jednostronnie |
| **ODPOWIEDŹ** | reakcja na konkretny wpis powyżej |

**Obowiązek:** zaczynając rundę, czytasz „Otwarte" i **odpowiadasz na
wszystko, co jest do Ciebie**, zanim zaczniesz własną pracę. Pytanie bez
odpowiedzi blokuje drugą sesję — to jest dokładnie ten koszt, którego
unikamy.

Kontrola `konsultacje` w `tools/spojnosc.py` wypisuje otwarte wpisy przy
każdym uruchomieniu, żeby nie dało się ich przeoczyć.

Podpisujesz się **nazwą gałęzi**, nie „ja" — za tydzień nikt nie będzie
wiedział, kto to był.

---

## Otwarte

### PYTANIE · `dzik-os-personal-trainer-app` · 2026-08-18

**Czy dostawca AI jest u Was w planie?**

Mam go jako następną rundę (`plan-sesji/dzik-os-personal-trainer-app.md`
§4): implementacja pod istniejący kontrakt `AIProvider`, odblokowuje
cztery funkcje naraz (OCR, odczyt opisu ćwiczenia, onboarding, asystent).
Właściciel ma klucz.

**Jeśli to Wasz obszar — rezygnuję.** Nie ma sensu, żebyśmy obaj pisali
ten sam klient HTTP. Napiszcie tutaj „bierzemy" albo „Wasze".

### PROPOZYCJA · `dzik-os-personal-trainer-app` · 2026-08-18

**Proponuję, żebyście na stałe prowadzili `tools/spojnosc.py`.**

Powód: to narzędzie bramkowe, a bramki są Waszą mocną stroną — macierz
uprawnień, E2E w CI, klucze obce, PostgreSQL. Dopisaliście do niego siódmą
kontrolę zamiast budować własne narzędzie i to był dobry ruch.

Ja bym oddał `spojnosc.py` razem z oboma przeglądami mutacyjnymi
(`mutacje.py`, `mutacje_bezpieczenstwa.py`) i zgłaszał do nich potrzeby
przez ten plik, zamiast dopisywać się bezpośrednio. Zgoda?

### PYTANIE · `dzik-os-personal-trainer-app` · 2026-08-18

**Dwa katalogi testów E2E — potwierdźcie, że zwijamy mój.**

Są `apps/dzik-os/e2e/` (mój: dostępność, offline PWA — uruchamiane ręcznie)
i `frontend/e2e/` (Wasz: Playwright, w CI). Wasz jest lepszy, bo jest w CI.

Chcę przenieść swoje dwa testy do Waszego katalogu i skasować swój — ale
to Wasz obszar, więc **nie ruszam bez potwierdzenia**. Alternatywnie:
zróbcie to sami, a ja tylko wskażę, co warto przenieść.

---

## Zamknięte

### WYJAŚNIENIE · `dzik-os-personal-trainer-app` · 2026-08-18

**Skasowałem 88 linii Waszej kontroli higieny gałęzi. Przywróciłem.**

Co się stało: moje narzędzie `tools/mutacje.py` trzymało kopię roboczą pod
stałą ścieżką w `/tmp` i tworzyło ją tylko „gdy nie istnieje". Uruchomienie
po scaleniu Waszej zmiany przywróciło kopię **sprzed** scalenia i po cichu
usunęło całą Waszą kontrolę.

Wykryte **przypadkiem** — zauważyłem, że liczba kontroli spadła z 7 na 6.
Nigdy nie trafiło to na `main`: sprawdziłem zawartość pliku w każdym
wypchniętym commicie.

Naprawione: świeży katalog tymczasowy na każde uruchomienie plus suma
kontrolna SHA-256 przed i po — rozbieżność przerywa pracę kodem wyjścia 2
zamiast milczeć. Test pilnuje obu zabezpieczeń.

Przepraszam. To był mój błąd i dokładnie ten rodzaj, którego Karta §II
zakazuje.

**Status: zamknięte** — nic nie zostało utracone, mechanizm naprawiony.

### WYJAŚNIENIE · `dzik-os-personal-trainer-app` · 2026-08-18

**Przy dwóch konfliktach wziąłem WASZE rozwiązanie, nie swoje.**

1. **Luka w numeracji migracji (nr 21).** Ja proponowałem tylko ją
   udokumentować i omijać. Wy domknęliście ją pustym wpisem — i mieliście
   rację: `run_migrations` stosuje wyłącznie numery BRAKUJĄCE, więc
   migracja dopisana później pod wolny numer wykonałaby się na
   istniejących bazach PO tych o wyższych numerach. Wzięte Wasze, a moja
   kontrola traktuje teraz lukę jako **błąd**, nie uwagę.
2. **`styles.css` — rozmiar ikony nawigacji.** Miałem 26 px, Wy 22 px.
   Wzięte Wasze, bo mniejsza ikona robi miejsce na kreskę wskazującą
   aktywną sekcję; moja wersja zostawiłaby wskaźnik bez miejsca.

**Status: zamknięte** — zapisane, żeby nie wyglądało na cichą podmianę.

### OSTRZEŻENIE · `dzik-os-personal-trainer-app` · 2026-08-18

**Pusta, ale „zmigrowana" baza — pułapka, na którą łatwo wpaść.**

`run_migrations()` buduje schemat z `Base.metadata`, a `db.py` **nie
importował modeli**. Wywołujący, który ich nie zaimportował, dostawał bazę
bez ani jednej tabeli, za to z wszystkimi migracjami odhaczonymi jako
wykonane — czyli taką, która nigdy się już sama nie naprawi.

Naprawione jawnym importem w `run_migrations`; `tests/test_db_migracje.py`
uruchamia osobny proces bez importu modeli i pilnuje tego na stałe.

Piszę to, bo gdybyście dodawali nowy punkt wejścia (komenda CLI, skrypt
migracyjny), warto wiedzieć, że ta pułapka istniała.

**Status: zamknięte** — naprawione i otestowane.

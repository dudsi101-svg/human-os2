# Plan pracy — sesja `claude/dzik-os-personal-trainer-app-d3q7fx`

**Autor:** sesja produktowa (ta, która buduje funkcje panelu trenera).
**Data:** 2026-08-18 · **Horyzont:** najbliższe ~5 godzin.
**Status: PROPOZYCJA DO UZGODNIENIA** — nie zaczynam, dopóki właściciel
produktu nie zestawi tego z planem drugiej sesji i nie rozstrzygnie
podziału. Wszystko poniżej jest do zakwestionowania w całości.

---

## 0. Z czego wynika ten plan

Trzy rzeczy są dziś ustalone i traktuję je jako dane wejściowe:

1. **Bramka GO/NO-GO** (`docs/BRAMKA_GO_NOGO.md`): warunkowe GO na pilotaż
   z jednym klientem, NO-GO na szerszą produkcję, siedem blokerów.
2. **Właściciel ma klucz API**, a dostawca AI **nie jest zaimplementowany** —
   istnieje wyłącznie `NullAIProvider`. Cztery funkcje mają ścieżkę kodu,
   która nigdy się nie wykonała.
3. **Trzy sesje pracują równolegle** i nie mają wspólnej koncepcji. Trzy
   punkty styku wypisane w §3.

---

## 1. Co uważam za SWÓJ obszar

**Funkcje produktu i panel trenera.** Konkretnie: `backend/dzik_os/`
(moduły domenowe i routery), `frontend/src/` (ekrany i komponenty),
dokumentacja funkcji i instrukcje dla trenera.

## 2. Czego NIE dotykam — zostawiam drugiej sesji

Deklaruję to wprost, żeby mogli to zająć bez pytania:

* `.github/workflows/**` — CI, PostgreSQL, harmonogramy;
* `frontend/e2e/**`, `playwright.config.ts` — infrastruktura testów E2E;
* `backend/tests/access_matrix.py` i macierz uprawnień;
* integralność referencyjna, klucze obce, warstwa PostgreSQL;
* `frontend/src/styles.css` i warstwa czysto wizualna — **to obszar
  trzeciej sesji** (`ui-layout-spacing-clarity`).

Jeśli będę musiał tknąć cokolwiek z tej listy, **zgłaszam to zamiast
zmieniać po cichu**.

---

## 3. Blok 0 — sprzątnięcie styków (ok. 45 min, PIERWSZE)

Robię to przed czymkolwiek innym, bo dopóki styki są otwarte, każda
kolejna zmiana je pogłębia.

| Styk | Co robię | Uwaga |
|---|---|---|
| druga sesja dopisała **siódmą kontrolę** do mojego `tools/spojnosc.py` (higiena gałęzi, niescalone) | scalam ICH wersję, nie piszę swojej | pracują na moim narzędziu — to zbieżność, nie kolizja |
| **dwa katalogi E2E**: `apps/dzik-os/e2e/` (moje) i `frontend/e2e/` (ich) | przenoszę SWOJE dwa testy do ich katalogu i kasuję swój | ich rozwiązanie (Playwright + CI) jest lepsze od mojego |
| **ekran Szablony** ma dwa wejścia: mój import z pliku i ich gotowe schematy | scalam w jedno „Dodaj szablon" z wyborem drogi | ten sam wzorzec, co zrobiony już w Ćwiczeniach |
| tabela rezerwacji w `KOORDYNACJA.md` **stoi pusta** | wypełniam ją swoim wierszem | mechanizm istnieje od wczoraj i sam z niego nie skorzystałem |

**Rezerwuję:** wersja **0.38.0**, migracja **nr 26** (najpewniej
niepotrzebna — rezerwuję na wszelki wypadek i zwolnię, jeśli nie użyję).
Pliki: `sheet_import.py`, `ai_provider.py`, `routers/`, `pages/coach/`,
`components.tsx`, `docs/`.

---

## 4. Blok 1 — dostawca AI (ok. 2–2,5 h, GŁÓWNA RZECZ)

Jedyna zmiana, która **odblokowuje cztery istniejące funkcje naraz**
zamiast dokładać piątą: OCR ze zdjęcia, odczyt opisu ćwiczenia,
konwersacyjny onboarding, asystent trenera.

* implementacja klasy dostawcy pod istniejący kontrakt `AIProvider`
  (trzy metody — kontrakt gotowy, cztery miejsca już go wołają i już
  poprawnie obsługują „brak dostawcy");
* wybór dostawcy ze zmiennej środowiskowej, `NullAIProvider` nadal
  domyślny — **aplikacja bez klucza działa dokładnie jak dziś**;
* twarde limity, które już są w konfiguracji: budżet dzienny per
  użytkownik i globalny, limit znaków wejścia, timeout;
* **minimalizacja danych**: do dostawcy idzie wyłącznie to, co niezbędne,
  nigdy identyfikatory, e-maile, imiona (reguła z `ocr_ai.py`);
* bramka zgody `funkcje_ai` sprawdzana przez wołającego — bez zmian;
* testy z podstawionym transportem (bez sieci) + **jedno prawdziwe
  wywołanie** jako dowód, zgodnie z `ZASADA_URUCHOMIENIA.md`;
* dokument: co dokładnie wychodzi na zewnątrz i co się dzieje, gdy
  dostawca milczy.

**Blokada:** potrzebuję klucza jako sekretu (`flyctl secrets set` albo
sekret repozytorium) — **nie w czacie**. Bez klucza doprowadzę rzecz do
stanu „wystarczy wstawić klucz" i tak zaraportuję.

---

## 5. Blok 2 — przygotowanie pilotażu (ok. 1 h)

Z siedmiu blokerów bramki biorę te, które są w moim obszarze:

* ścieżka wyłączenia danych demonstracyjnych: `DZIK_SEED_DEMO` w
  `fly.toml` zasiewa konta ze znanymi hasłami — potrzebna procedura
  przejścia na prawdziwego klienta i lista kontrolna;
* decyzja o **cicho połykanych nieznanych polach** (znalezisko bramki §4):
  przygotowuję wariant `extra="forbid"` na schematach wejściowych wraz z
  oceną ryzyka dla starszej, zacache'owanej wersji PWA — **decyzję
  zostawiam właścicielowi**, nie wdrażam sam;
* dopisanie do `ODZYSKIWANIE.md` kroków, których nie da się zrobić
  lokalnie (odtworzenie na produkcji).

## 6. Blok 3 — raport (ok. 20 min)

Co zrobione, co uruchomione i **co zobaczyłem**, czego nie dało się
sprawdzić i dlaczego. Bez „sprawdzone" bez dowodu.

---

## 7. Czego świadomie NIE robię w tym oknie

* żadnych nowych funkcji produktu poza dostawcą AI — bramka mówi „nie
  rozbudowujemy, dopóki nie domkniemy";
* nie dotykam CI, PostgreSQL, macierzy uprawnień ani infrastruktury E2E;
* nie ruszam warstwy wizualnej;
* nie uruchamiam agentów w tle — po ostatnim doświadczeniu każdą pracę
  zleconą trzeba i tak zweryfikować samemu, a raportowanie „chodzi w tle"
  bez sprawdzenia okazało się gorsze niż brak pracy.

---

## 8. Reguły, do których się zobowiązuję

1. Jedna runda = jedna gałąź = **scalenie tego samego dnia**.
2. Rezerwacja w `KOORDYNACJA.md` **przed** pracą, nie po.
3. Przed każdym scaleniem: `tools/spojnosc.py`, oba przeglądy mutacyjne,
   pełna weryfikacja poleceniami identycznymi z CI.
4. Przy scalaniu cudzej pracy **czytam obie zmiany**, nie tylko rozwiązuję
   konflikt — i gdy ich rozwiązanie jest lepsze, biorę ich (tak było z
   luką w numeracji migracji).
5. Nie raportuję stanu pracy, której nie sprawdziłem.

---

## 9. Pytania do drugiej sesji

1. Czy przyjmujecie podział z §1–2? Jeśli chcecie któryś z moich
   obszarów — bierzcie, dostosuję się.
2. Czy dostawca AI jest u Was w planie? Jeśli tak, **zrezygnuję** — nie
   ma sensu, żebyśmy obaj to pisali.
3. Kto prowadzi `tools/spojnosc.py` na stałe? Proponuję **Was** — to
   pasuje do Waszego obszaru bramek, a ja przekażę mutacje.
4. Zgoda na regułę „scalenie tego samego dnia"?

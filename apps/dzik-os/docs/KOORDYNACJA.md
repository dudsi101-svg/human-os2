# Koordynacja równoległych rund — jak nie wchodzić sobie w drogę

Rundy bywają rozwijane równolegle, w osobnych kopiach repozytorium. Każda
praca widzi kod sprzed swojego startu i **nie wie, co robią pozostałe**.
Git wykrywa kolizje TEKSTU. Kolizje ZNACZENIA przechodzą przez scalenie
bez jednego konfliktu i wychodzą dopiero na produkcji.

Ten dokument opisuje dwa mechanizmy: **rezerwację** (przed pracą) i
**bramkę** (przed scaleniem). Pierwszy zależy od dyscypliny, drugi nie.

---

## 1. Bramka: `tools/spojnosc.py`

```bash
python apps/dzik-os/tools/spojnosc.py     # 0 = czysto, 1 = są kolizje
```

Uruchamiana w CI (`dzik-os-ci.yml`) i lokalnie przed każdym scaleniem.
Sześć kontroli, każda wzięta z błędu, który **naprawdę się zdarzył**:

| Kontrola | Co łapie | Kiedy się zdarzyło |
|---|---|---|
| `migracje` | ten sam numer migracji w dwóch gałęziach; numery nierosnące | scalanie importu biblioteki (nr 24) |
| `changelog` | ta sama wersja przydzielona dwa razy; wersje nie malejąco | 0.29.0 w dwóch rundach naraz |
| `trasy API` | trasa statyczna przesłonięta przez wcześniejszą parametryzowaną | `/coach/exercises/import-schema` w 0.32.0 |
| `routery` | moduł w `routers/` bez `include_router` w `main.py` | — (zapobiegawczo) |
| `testy frontendu` | `scripts/test-*.mjs` spoza `test:helpers`, czyli test-widmo | przy dokładaniu testów pomocniczych |
| `dokumenty` | martwy odnośnik `docs/COŚ.md` (uwaga, nie błąd) | przy przenoszeniu dokumentacji |

Kontrola **niczego nie naprawia** — od tego jest człowiek albo agent,
który zna zamiar. Ma wyłącznie nie pozwolić kolizji przejść niezauważenie.

**Kontrola też może zgnić.** Pierwsza wersja kontroli tras widziała 35 z
około 200 tras (ta wersja FastAPI nie spłaszcza dołączonych routerów do
`app.routes`) i przechodziła zawsze — wyszło to dopiero przy próbie z
celowo wstrzykniętym błędem. Dlatego `tests/test_spojnosc.py` wstrzykuje
każdy z tych błędów i sprawdza, że kontrola się zapala, a `PROG_TRAS`
wywraca kontrolę, gdy widzi podejrzanie mało tras. **Dokładając kontrolę,
dołóż test, który ją psuje.**

### Przegląd mutacyjny: czy te testy naprawdę pilnują

```bash
python apps/dzik-os/tools/mutacje.py     # z korzenia repozytorium
```

Narzędzie po kolei **psuje kontrolę** na siedem sposobów, po każdym
uruchamia `tests/test_spojnosc.py` i na koniec przywraca oryginał.
Mutacja, po której testy nadal są zielone, to luka — wypisana wprost.

Pierwsze uruchomienie (2026-08-18) znalazło **dwie luki**:

* usunięcie progu `PROG_TRAS` nie wywracało żadnego testu — zabezpieczenie
  przed cichą śmiercią kontroli tras samo nie było zabezpieczone;
* zamiana kontroli dokumentów w atrapę przechodziła bez śladu.

Obie naprawione tego samego dnia; po naprawie **7 z 7 mutacji wykrytych**.
Uruchamiaj po każdej zmianie w `spojnosc.py` i po dołożeniu kontroli — bez
tego „mamy testy" jest deklaracją, nie faktem.

---

## 2. Rezerwacja: zanim zaczniesz pracę

Trzy zasoby są **globalne** i nie da się ich zająć dwa razy. Rezerwuj je
w tabeli niżej **przed** rozpoczęciem pracy, w jednym commicie na `main`:

* **numer migracji** — kolejny wolny z `backend/dzik_os/db.py`;
* **numer wersji** w `docs/CHANGELOG.md`;
* **pliki, które będziesz zmieniać** — jeśli dwie równoległe prace
  wskazują ten sam plik, jedna z nich musi poczekać. To nie jest
  uprzejmość, tylko jedyny sposób uniknięcia sprzeczności znaczeniowej.

### Plan pracy każdej sesji

Zanim zaczniesz rundę, połóż swój plan w **`docs/plan-sesji/<nazwa-gałęzi>.md`**.
Nazwa pliku bierze się z gałęzi, więc dwa plany nie mogą się zderzyć —
inaczej niż numer wersji, który zderzył się już dwa razy.

Plan ma odpowiadać na cztery pytania: **co uważam za swój obszar**,
**czego nie dotykam** (żeby ktoś inny mógł to zająć bez pytania), **co
rezerwuję** (numery, pliki) i **czego świadomie nie robię**. Ostatnie
pytanie bywa najważniejsze — kolizje biorą się z rzeczy, których nikt nie
zadeklarował.

### Aktualne rezerwacje

| Gałąź / runda | Migracja | Wersja | Główne pliki | Status |
|---|---|---|---|---|
| `dzik-os-personal-trainer-app` — dostawca AI + sprzątnięcie styków | **26** (rezerwacja warunkowa) | **0.38.0** | `ai_provider.py`, `sheet_import.py`, `routers/`, `pages/coach/`, `components.tsx`, `docs/` | plan złożony, czeka na uzgodnienie |

Następny wolny numer migracji: **27** · następna wolna wersja: **0.39.0**

> Po zakończeniu rundy usuń wiersz i podnieś „następne" numery. Rezerwację
> warunkową, której nie użyto, **zwolnij** — inaczej numer przepada.

---

## 3. Czego bramka NIE złapie

Uczciwa lista — te rzeczy nadal wymagają człowieka przy scalaniu:

1. **Sprzeczność logiczna między rundami.** Realny przykład: jedna runda
   filtrowała płatności po statusie `PENDING`, druga wprowadziła
   `OVERDUE`. Scalenie tekstowe przeszło gładko i **po cichu wyłączyło
   przypomnienia o zaległych płatnościach**. Żadna maszyna tego nie
   zobaczy — trzeba przeczytać obie zmiany.
2. **Test, który sprawdza nieaktualne założenie.** Jedna runda zamieniła
   suwaki na grupy przycisków, test drugiej nadal liczył suwaki.
3. **Dublujący się pomysł.** Dwie rundy budujące to samo innymi słowami
   scalają się bez konfliktu i zostają na stałe jako dwa mechanizmy.

Dlatego przy scalaniu **czyta się obie zmiany**, a nie tylko rozwiązuje
konflikty. Bramka zdejmuje mechaniczną część, nie zastępuje czytania.

---

## 4. Kolejność scalania

1. `python apps/dzik-os/tools/spojnosc.py` — zanim cokolwiek scalisz.
2. Scalanie **po jednym**, nigdy hurtem: po każdym pełna weryfikacja.
3. Pełna weryfikacja — **dokładnie tymi poleceniami, z korzenia repozytorium**:

   ```bash
   python -m ruff check apps/dzik-os/backend     # tak samo jak CI
   python -m pytest apps/dzik-os/backend/tests -q
   python -m pytest tests/ -q                    # Core: 275 testów zielone
   cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build \
     && npm run test:helpers
   ```

   **Uruchamiaj `ruff` tak jak CI, nie „jakoś".** Ta sama zmiana przeszła
   lokalnie i wywróciła CI, bo lokalne `ruff` (starsza wersja z PATH)
   czytało inną konfigurację niż `python -m ruff` (wersja z środowiska,
   której używa CI). Weryfikacja innym poleceniem niż bramka to nie
   weryfikacja.
4. Uruchomienie tego, co nowe — patrz `docs/ZASADA_URUCHOMIENIA.md`.
5. Dopiero potem push i wdrożenie.

---

## 5. Brief dla pracy równoległej

Każda praca prowadzona równolegle dostaje ten sam zestaw ograniczeń:

```
Przeczytaj: /CLAUDE.md, apps/dzik-os/docs/KOORDYNACJA.md,
            apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md.
Pracujesz WYŁĄCZNIE w apps/dzik-os/. Core (hos_engine/, tests/) jest
  nietykalny — 275 testów Core musi zostać zielone.
Twoja rezerwacja: migracja nr <N>, wersja <X.Y.0>, pliki <lista>.
  Nie dotykaj plików spoza tej listy; jeśli musisz — zgłoś to zamiast
  zmieniać po cichu.
Nie pushuj. Commituj po polsku, bez nazw modeli AI w treści commita.
Przed zakończeniem: pełna weryfikacja (punkt 4 wyżej) plus
  `python apps/dzik-os/tools/spojnosc.py`.
W raporcie napisz, CO URUCHOMIŁEŚ I CO ZOBACZYŁEŚ — nie „sprawdzone".
```

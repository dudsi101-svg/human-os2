# Bramka jakości — decyzja GO / NO-GO

**Data:** 2026-08-18 · **Wersja badana:** 0.35.1 (commit `dbf44ff`)
**Wykonał:** ten sam agent, który pisał kod — **nie jest to niezależny
przegląd**. Patrz §5, punkt 1: to samo w sobie jest blokerem.

---

## Decyzja

> ### WARUNKOWE GO — pilotaż z jednym prawdziwym klientem
> ### NO-GO — szersza produkcja i cudzy klienci

Nie znalazłem luki pozwalającej ujawnić dane zdrowotne, przejąć konto,
ominąć zgodę ani uszkodzić dane **na sprawdzonej powierzchni**. To nie jest
to samo, co „nie ma takiej luki" — §5 wypisuje, czego nie sprawdzono.

---

## 1. Sprostowanie na wstępie

Bramka miała powstać wcześniej, w osobnej pracy równoległej. **Nie
powstała**: nie ma pliku ani commitów, gałąź tamtej pracy stoi na scaleniu
sprzed ośmiu wersji. Przez kilkanaście wiadomości raportowałem „bramka
chodzi w tle", ani razu tego nie weryfikując. Ten dokument powstał
dopiero po tym, jak właściciel produktu zażądał jasności.

Wniosek na przyszłość jest częścią wyniku bramki: **stan pracy zleconej na
zewnątrz sprawdza się, zanim się o nim raportuje.**

---

## 2. Co zostało potwierdzone dowodem

Wszystko poniżej wykonane na **działającej aplikacji przez HTTP**, nie w
`TestClient` — inaczej nie widać rzeczy takich jak przesłonięte trasy.

### 2.1. Izolacja danych (najwyższa stawka)

| Próba | Wynik | Oczekiwanie |
|---|---|---|
| klient czyta własny plan | 200 | 200 |
| klient A → plan/pomiary/treningi klienta B | 404, 404, 404 | 404 (nie 403 — nie ujawniamy istnienia) |
| klient → panel trenera (klienci, ćwiczenia, importy) | 403, 403, 403 | 403 |
| **obcy trener** (bez relacji) → plan/pomiary/raporty klienta | 404, 404, 404 | 404 |
| obcy trener → własna, pusta lista klientów | 200 | 200 |
| brak tokenu | 401 | 401 |
| podrobiony token | 401 | 401 |

Każda odmowa zasobowa trafiła do łańcucha audytu jako `ACCESS_DENIED` z
endpointem i identyfikatorem aktora — **bez danych zdrowotnych**.
`verify_chain() = True`.

### 2.2. Uwierzytelnianie dwuskładnikowe (konfiguracja PRODUKCYJNA)

Wcześniejsze sprawdzenia robiłem z **wyłączonym** MFA, żeby sobie ułatwić —
czyli omijałem konfigurację, która obowiązuje na produkcji
(`DZIK_MFA_REQUIRED_ROLES` domyślnie `COACH,ADMIN`). Nadrobione:

| Próba | Wynik |
|---|---|
| trener bez skonfigurowanego MFA: panel trenera | **403** na wszystkich endpointach |
| trener bez MFA: `/auth/me` i konfiguracja MFA | 200 (jedyne dostępne) |
| logowanie po włączeniu MFA | `{"mfa_required": true, "mfa_token": …}` — **bez sesji** |
| `mfa_token` użyty jako sesja | **401** |
| zły kod TOTP | 401 „Nieprawidłowy kod" |
| poprawny kod TOTP | pełna sesja, panel otwarty (200) |
| **ponowne użycie tego samego wyzwania** | **401** (jednorazowe) |

### 2.3. Przepływy krytyczne

Raport tygodniowy klienta → 201; treść (`comment`, `questions`) dociera do
trenera w komplecie. Zapis wykonanego treningu → 201. Eksport własnych
danych przez klienta → 200, 40 KB JSON-a (prawo wyjścia działa).

### 2.4. Migracje

Pusta baza → 24 migracje (1..25, świadoma luka na 21), schemat kompletny,
drugi przebieg zwraca pustą listę. Stara baza z ostemplowanymi migracjami
domyka zaległy ogon. **Znaleziony i naprawiony realny błąd — patrz §3.**

### 2.5. Odzyskiwanie danych

Próba na pełnej bazie (7 kont, 256 ćwiczeń, 4 plany, pliki uploadów):
skasowanie bazy, audytu i uploadów → odtworzenie z archiwum → komplet
danych zgodny ze stanem sprzed, skasowany plik z powrotem, łańcuch audytu
zweryfikowany. Powtórzone dwukrotnie, na dwóch różnych wersjach kodu.

### 2.6. Przegląd mutacyjny obron — czy testy w ogóle czegoś pilnują

701 zielonych testów nie mówi nic o tym, czy któryś zauważy **wyłączenie**
obrony. Sprawdzone wprost (`tools/mutacje_bezpieczenstwa.py`): dziewięć
obron wyłączonych po kolei, po każdej uruchomiona odpowiednia część suity.

| Wyłączona obrona | Wynik |
|---|---|
| trener widzi każdego klienta (bez relacji) | zabity |
| dostęp do danych klienta bez zgody | zabity |
| brak odmowy przy obcym kliencie | zabity |
| cudzy zasób przechodzi kontrolę właściciela | zabity |
| każde hasło pasuje | zabity |
| cofnięcie importu nie przywraca pól | zabity |
| migawka przed importem nie powstaje | zabity |
| tryb UZUPELNIJ jednak nadpisuje | zabity |
| podgląd importu jednak zapisuje | **PRZEŻYŁ** → naprawione, patrz §3 |

Po naprawie: **9/9**.

---

## 3. Co bramka znalazła i naprawiła

1. **Pusta, lecz „zmigrowana" baza (poważne).** `run_migrations()` tworzy
   schemat z `Base.metadata`, a `db.py` **nie importował modeli**.
   Wywołujący, który ich nie zaimportował, dostawał bazę **bez ani jednej
   tabeli**, za to z wszystkimi migracjami odhaczonymi jako wykonane —
   czyli taką, która nigdy się już sama nie naprawi. Dziś każdy realny
   punkt wejścia importował modele przez przypadek. Naprawione jawnym
   importem w `run_migrations`; `tests/test_db_migracje.py` uruchamia
   osobny proces bez importu modeli i pilnuje tego na stałe (sprawdzone:
   po cofnięciu poprawki test czerwienieje).
2. **Kontrakt „podgląd nie dotyka sesji" bez pokrycia.** Testy przez
   endpoint przechodziły także wtedy, gdy podgląd dodawał obiekty do sesji
   (znikały przy zamknięciu). Dopisany test na poziomie jednostki
   (`db.new`/`db.dirty` puste).
3. **Mylący komentarz przy migracjach.** Informacja „numer 23
   zarezerwowany" została z czasów, gdy 23 było wolne — dziś jest zajęty.
   Usunięta; wolne numery w środku numeracji są teraz raportowane jako
   uwaga przez `tools/spojnosc.py`, z ostrzeżeniem, żeby ich nie brać.

---

## 4. Znalezione, nienaprawione (świadomie)

**Nieznane pola w żądaniu są po cichu połykane.** `POST /api/checkins`
z polem spoza schematu zwraca 201 i pole znika bez śladu. Dziś jedynym
klientem API jest nasz własny frontend, więc nie ma utraty danych
użytkownika — ale literówka w przyszłym kliencie albo zmiana nazwy pola
przejdzie niezauważona. Rozwiązanie (`extra="forbid"` na schematach
wejściowych) **nie zostało zrobione w tej rundzie celowo**: odrzucałoby
żądania ze starszej, zacache'owanej wersji PWA i wymaga osobnej decyzji
o zgodności wstecznej. Do rozstrzygnięcia przed pierwszym klientem
zewnętrznym.

---

## 5. Blokery dla szerszej produkcji

Każdy z tych punktów sam w sobie wystarcza do NO-GO poza pilotażem.

1. **Brak niezależnego przeglądu.** Tę bramkę wykonał ten sam agent,
   który pisał kod. Sprawdziłem to, o czym pomyślałem — a największe
   ryzyko leży w tym, o czym nie pomyślałem, bo to ta sama głowa, która
   pisała. Zlecenie zewnętrznego przeglądu bezpieczeństwa jest warunkiem
   wyjścia poza pilotaż.
2. **Aplikacja nigdy nie obsłużyła prawdziwej relacji trenerskiej.**
   Wszystkie dane są syntetyczne. Nie wiemy, jak zachowa się przy
   prawdziwym tygodniu pracy.
3. **Tryby „rozszerzone" AI nigdy się nie wykonały** — cztery funkcje
   (OCR, odczyt opisu ćwiczenia, onboarding, asystent) mają ścieżkę
   kodu, której nigdy nie uruchomiono. Brakuje implementacji dostawcy;
   sam klucz API tego nie zmieni.
4. **E-mail nie wychodzi.** Dostawca powiadomień to `Null` — przypomnienia
   o płatnościach i digest poniedziałkowy nigdzie nie docierają.
5. **Kopie zapasowe leżą na tym samym wolumenie, który chronią.**
   Odtworzenie ze snapshotu Fly nigdy nie było ćwiczone. Okno utraty przy
   backupie dobowym: do 24 godzin.
6. **Brak sprawdzenia na prawdziwym telefonie** (iOS Safari, Android).
   PWA testowana wyłącznie w Chromium na maszynie.
7. **`DZIK_SEED_DEMO = "true"` w `fly.toml`.** Przy przejściu na
   prawdziwych klientów tę linię trzeba usunąć — inaczej pierwsza pusta
   baza zasieje konta demonstracyjne ze znanymi hasłami.

---

## 6. Warunki pilotażu (jeden prawdziwy klient)

1. Usunąć `DZIK_SEED_DEMO` z `fly.toml` i wyczyścić konta demo.
2. Zmienić hasła kont trenera i administratora; potwierdzić działające MFA
   na koncie trenera (przepływ sprawdzony, patrz §2.2).
3. Wykonać jedno pełne odtworzenie kopii zapasowej **na produkcji**, nie
   tylko lokalnie.
4. Klient dostaje jasną informację, że to wersja pilotażowa bez
   niezależnego przeglądu bezpieczeństwa, i świadomie się na to zgadza.
5. Trzymać `docs/ODZYSKIWANIE.md` pod ręką — pięć warstw odzyskiwania.

---

## 7. Jak to powtórzyć

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q
python apps/dzik-os/tools/spojnosc.py
python apps/dzik-os/tools/mutacje.py
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py
```

Sprawdzenia przez HTTP (izolacja, MFA, przepływy krytyczne, migracje,
odtworzenie kopii) wykonane ręcznie na uruchomionej aplikacji — polecenia
i wyniki w opisie rundy. **Do zautomatyzowania w kolejnej turze**, żeby
bramka nie zależała od tego, czy ktoś pamięta.

# Plan sesji: konfigurator miesięcznych planów treningowych — K1, silnik (0.55.0)

**Gałąź:** `agent/konfigurator-28-dni` (od `main` = 7fd04d0)
**Rola:** jedyny piszący i integrator (decyzja właściciela 12–13.09);
recenzent kodu: Codex.
**Źródło:** pakiet właściciela „PAKIET_DLA_CLAUDE” 1.0 z 13.09.2026
(specyfikacja, katalog 31 ćwiczeń / 11 jednostek / 7 układów, schematy
Draft 2020-12, 7 scenariuszy referencyjnych, 48 testów akceptacyjnych,
14 źródeł). Kontrola danych pakietu wykonana niezależnie w sesji:
schematy, ciągłość dat, wzór czasu, sprzęt, odstępy 48 h, limity —
wszystko zgodne.

## Decyzje dopasowujące pakiet do Dzik OS

1. **Narzędzie trenera, nie samoobsługa.** Konfigurator generuje SZKIC
   28 dni dla trenera (propose-only, jak asystent trenera i kreator
   diety). Trener przegląda, poprawia i zapisuje jako wersję planu
   podopiecznego przez istniejące wersjonowanie. Klient nie uruchamia
   generatora sam. Kwalifikację zdrowotną wpisuje trener na podstawie
   wywiadu; pola `null` = brak odpowiedzi = `needs_input`.
2. **Własny katalog konfiguratora** (`dzik_os/konfigurator/dane/`),
   status „do przeglądu trenera”; nie podmienia bazy ćwiczeń trenera.
   Po zapisie plan ma zwykłą strukturę dni/ćwiczeń (nazwy po polsku,
   serie, zakres, przerwa, komentarz z RIR i zasadą progresji, ciężar
   „dobór na miejscu”), więc edytuje się jak każdy inny.
3. **Etapy:** K1 (ta runda) silnik + walidator + bramka zdrowotna +
   kalendarz + API trenera + testy; K1b ekran w karcie klienta;
   K2 dziennik serii z RIR, adaptacja przyszłych sesji, zamienniki;
   potem przegląd trenerski i medyczny (wymóg pakietu przed
   publikacją — nie deklarujemy walidacji klinicznej).

## Zamiar K1

- `dzik_os/konfigurator/`: `dane.py` (katalog, schematy, źródła,
  wersje), `zdrowie.py` (bramka §5), `kalendarz.py` (daty, bloki 7 dni,
  tryb kalendarzowy 28–31 dni, odstęp jako czas rzeczywisty),
  `walidator.py` (schematy + reguły między polami; czas i sumy liczone
  od nowa), `silnik.py` (`generuj_plan`: §6–§13, deterministyczny,
  bez LLM).
- API trenera: `POST /api/coach/konfigurator/podglad` (wejście wg
  schematu → status/plan/issues/questions/versions; bez zapisu) i
  `POST /api/coach/konfigurator/zapisz` (ready/limited → nowy
  `TrainingPlan` v1 podopiecznego z zapisanym wejściem, wersjami reguł
  i wynikiem; zgoda `training_data`, audyt `PLAN_CREATED` z
  `source=konfigurator`). Dane zdrowotne wejścia NIE trafiają do
  payloadu zdarzenia ani do logów.
- Testy: 7 scenariuszy referencyjnych **co do bajta** (JSON kanoniczny),
  determinizm, przypadki akceptacyjne T01–T21, T40–T48 w zakresie
  generowania (T22–T39 dotyczą dziennika i adaptacji — K2), testy
  właściwości (3 cele × 3 poziomy × 6 częstotliwości × 3 zaangażowania
  × 2 czasy × 2 zestawy sprzętu: zawsze deterministyczny, wyjaśniony
  wynik; nigdy zakazane ćwiczenie, ujemne serie, brak daty ani ciężar
  bez danych), API (uprawnienia, zgoda, zapis, izolacja).

## Świadomie nie robię

- ekranu (K1b), dziennika/adaptacji/zamienników (K2), eksportu;
- wywołań modelu językowego — żadnych;
- zmian w istniejących planach, szablonach ani bazie ćwiczeń.

## Rezerwacje

- **Wersja: 0.55.0.** **Migracja: brak** (plan zapisywany w istniejących
  tabelach; wejście i wynik konfiguratora w `content_json` wersji).

## Weryfikacja (do wypełnienia)

- ruff, backend, Core, spójność, frontend (tylko wersja); uruchomienie
  na żywo: API na lokalnym seedzie (podgląd → zapis → plan w karcie
  klienta → klient widzi).

## Weryfikacja (wykonana, 13.09)

- ruff czysto; **backend 1573 passed, 1 skipped** (7:05; w tym 8 testów
  referencyjnych, 685 akceptacyjnych/właściwości, 5 API, macierz
  dostępu z trzema nowymi operacjami); **Core 275**; spójność czysto
  (13 kontroli); `tsc` czysto; `npm run build` 88.7 kB gz; helpers
  140/140 (frontend bez zmian poza wersją).
- **7 scenariuszy referencyjnych pakietu odtworzone co do bajta**
  (JSON kanoniczny) za pierwszym uruchomieniem silnika; determinizm.
- **Uruchomienie na żywo** (świeży seed, lokalny serwer na zbudowanym
  `dist/`): trener → `podglad` (E3: średni, budowa, 4 dni → `ready`,
  16 sesji) → `zapisz` dla klient.a → plan v1 „Konfigurator 28 dni (E3)”
  z 4 jednostkami (U1/L1/U2/L2, ~64/55/62/65 min) i kalendarzem 28 dni;
  treść bez bloku zdrowotnego; klient widzi plan na ekranie Plan
  (jednostki, RIR 3/2/2/2 w komentarzu — zrzut w scratchpadzie);
  klient B na cudzych planach dostaje 404; `verify_chain` prawdziwy.
- Niezależna kontrola danych pakietu przed implementacją: schematy
  Draft 2020-12, ciągłość 28 dat, wzór czasu odtworzony dla 92 sesji,
  sprzęt i wykluczenia, odstępy 48 h, limity — zgodne z `09_KONTROLA`.
- Poza zakresem i NIE wykonane: ekran trenera (K1b), dziennik serii
  z RIR i adaptacja (K2), przegląd trenerski katalogu, przegląd
  medyczny screeningu, pilotaż zrozumiałości.

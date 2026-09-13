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

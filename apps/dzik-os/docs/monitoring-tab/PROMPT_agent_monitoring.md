# Prompt dla agenta kodującego — zakładka Monitoring / Postępy

> **Budżet.** Obowiązują `ZASADY_budzet_agentow.md`: maksymalnie 1 mln tokenów i 8 agentów na zadanie. Przed startem oszacuj koszt każdego etapu. Nie uruchamiaj pętli „jeden agent na znalezisko". Przegląd kodu: maksymalnie 3 recenzentów i jeden agent weryfikujący, wyłącznie dla zdeduplikowanych P0/P1.

Specyfikacja: `instrukcja_zakladka_monitoring.md`. Czytaj ją w całości przed pierwszą zmianą w kodzie.

## Zasady nadrzędne

1. **Nie zgaduj modelu danych.** Etap 0 to rozpoznanie istniejących modeli sesji, serii, ćwiczeń, pomiarów i zdjęć. Nazwy w sekcji 11 specyfikacji są propozycją, nie nakazem. Jeśli coś już istnieje pod inną nazwą — użyj istniejącego, nie twórz duplikatu.
2. **Nie ruszaj istniejącej zakładki „Raport"** poza przeniesieniem jej wpisu do „Więcej". Zero zmian w jej logice.
3. **Wszystko za feature flagą** `monitoring_tab_enabled`, domyślnie wyłączoną.
4. Jeśli reguła ze specyfikacji wygląda na błędną — **dopisz test i zgłoś**, nie poprawiaj po swojemu.
5. Filtrowanie danych wrażliwych zawsze po stronie serwera. Ukrycie w komponencie UI to błąd, nie implementacja.

## Etapy

**Etap 0 — rozpoznanie.** Wypisz: modele i pola sesji treningowej, serii (ciężar, powtórzenia, flaga rozgrzewki, jednostka), ćwiczeń (czy istnieje rozróżnienie wariantów i grup mięśniowych), pomiarów ciała, zdjęć. Wskaż braki blokujące którąkolwiek regułę z sekcji 8.2. **Zatrzymaj się i zgłoś przed etapem 1**, jeśli brakuje flagi serii rozgrzewkowej albo rozróżnienia wariantów ćwiczeń.

**Etap 1 — silnik rekordów.** Czyste funkcje, bez zależności od ORM: wejście to lista serii, wyjście to lista rekordów. Wszystkie reguły z 8.1 i 8.2. Komplet testów jednostkowych z sekcji 14 zielony, zanim cokolwiek trafi do bazy.

**Etap 2 — model i migracje.** `exercise_record` z historią przez `superseded_at`. Tabela agregatów. Przeliczanie przy zapisie sesji oraz przy edycji i usunięciu serii.

**Etap 3 — backfill.** Polecenie `recalculate_progress`, idempotentne, uruchamialne na jednym kliencie i na wszystkich. Test: dwukrotne uruchomienie daje identyczny stan.

**Etap 4 — API.** Endpointy z sekcji 12. Autoryzacja relacji trener–klient przy każdym żądaniu. Test integracyjny flagi `ZABURZENIA_ODZYWIANIA` napisz **przed** implementacją.

**Etap 5 — UI klienta.** Sekcje 6.1–6.5 w kolejności ze specyfikacji. Stany puste opisane w tabelach, nie generyczne „brak danych".

**Etap 6 — UI trenera.** Lista z sygnałami (7.1) z konfigurowalnymi progami, widok klienta (7.2).

**Etap 7 — migracja nawigacji.** Sekcja 13, łącznie z przekierowaniem `/raport`.

## Kryteria ukończenia

- Wszystkie testy z sekcji 14 zielone, w tym wydajnościowe.
- Backfill uruchomiony na kopii produkcyjnej; liczba wykrytych PR porównana ręcznie z historią 3 klientów, wynik w raporcie.
- Przy wyłączonej fladze nawigacja i zachowanie aplikacji identyczne jak przed zmianą — zweryfikowane, nie założone.

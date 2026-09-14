# Rozgrzewka, rozciąganie i cardio z suwakami — postęp i lista do przeglądu (0.73.0)

**Stan:** runda wykonana na gałęzi `agent/cardio-i-rozgrzewka` (PR #75); plan sesji
`docs/plan-sesji/cardio-i-rozgrzewka.md`, rozpoznanie `00_rozpoznanie.md`.

## 1. Do przeglądu trenera (Łukasz) PRZED użyciem u prawdziwych klientów

Wszystko poniżej jest **propozycją z pakietu zlecenia** (sesja tylko-do-odczytu
14.09) i implementacją writera — nie treścią trenera. Każdy wpis jest oznaczony
w danych (`source`, `review`) i wymaga potwierdzenia albo poprawki:

| Co | Gdzie | Oznaczenie |
|---|---|---|
| 9 bloków rozgrzewki (3 poziomy × góra/dół/całe ciało): dobór pozycji, dawki, czasy ≈8/10/12 min, „seria wprowadzająca” | `backend/dzik_os/cardio/bloki_wbudowane.py`; Szablony → Bloki | `source = "wbudowany — do przeglądu trenera"` |
| 3 bloki rozciągania po treningu (statyczne 20–30 s/str., 5–8 min, bez poziomów) | j.w. | j.w. |
| 9 nowych wpisów katalogu ćwiczeń: „Bieżnia — bieg ciągły”, „Wioślarz — wiosłowanie ciągłe”, rozciąganie czworogłowych stojąc, dwugłowych siedząc, pośladkowych („figura 4”), przywodzicieli, najszerszych przy drążku, karku, przedramion — kroki, błędy, wskazówki, uwagi bezpieczeństwa | `backend/dzik_os/exercise_catalog.py` (koniec) | komentarz nad blokiem w katalogu; w bazie trenera jak inne wpisy seedu |
| Tabela urządzeń: „zacznij od…” (kadencja/opór, prędkość/nachylenie, kroki/min, spm/damper) per pasmo G/R/W | `backend/dzik_os/cardio/urzadzenia.py` | `review = "do przeglądu trenera"` w każdej odpowiedzi API |
| MET-y do szacunku kcal (rowerek 4,0/6,8/10; bieżnia 3,5/7/10; skos 5,3/6,5/8; steper 4/6/8,8; wioślarz 4,8/7/8,5) | j.w. | [B] |
| **Kotwice [C] modelu** (do potwierdzenia — model §4 „Mieszanie”): środki intensywności G 60 / R 70 / W 90 % HRmax, przerwa 65 %; czasy G 25 / R 50 / W 25 min; progi struktury (interwały > 0,5 wagi Wydolność, tempo 0,25–0,5); interwały wg poziomu 8×1 / 6×2 / 4×4; sufit początkującego 85 % i czas −20 %; RPE z kotwic; MET | `backend/dzik_os/cardio/stale.py` | komentarze `[C]` |
| Decyzje wykonawcze po przeglądzie PR #75 [C]: „tempo” tylko przy środku ≥ 75 % HRmax (inaczej ciągła), podłoga 40 % rezerwy tętna, czas interwałów = suma rund, RPE interwałów 7–9 / 3 w przerwie, sufit początkującego także w ud./min | `model.py`, `stale.py` | `[C]` |
| Kotwice [B]: Redukcja = Fatmax 65–75 % HRmax / 50–65 % HRR / RPE 4–5 / 40–60 min | j.w. | `[B]` |
| Treść zastrzeżeń w UI (bilans energii, zakres ±10 ud./min, RPE przy lekach) | `stale.py::ZASTRZEZENIA`, `pozycje.tsx` | — |
| Nazwy celów w UI: „Redukcja (wydatek energii)”, „Wydolność (VO2max)”, „Regeneracja (baza tlenowa)” | `stale.py`, `types.ts` | domyślne z §8 promptu |

## 2. Pytania do właściciela (przyjęte domyślne z §8 promptu — do potwierdzenia)

1. Trzeci cel: Regeneracja (baza tlenowa). Alternatywy: Wytrzymałość, Moc/szybkość.
2. Nazwa celu 1: „Redukcja (wydatek energii)” zamiast „Spalanie tłuszczu”.
3. Warianty rozgrzewki pod sesję (góra/dół/całe ciało), nie wg czasu ani miejsca.
4. Rozciąganie: 3 warianty bez poziomów, po treningu.
5. Trener wskazuje dozwolone urządzenia, klient wybiera w dniu treningu.
6. Przegląd treści przez trenera przed włączeniem u prawdziwych klientów (§1).
7. Tętno spoczynkowe jako pomiar `resting_hr` (dane zdrowotne, zgoda) — bez migracji.

## 3. Świadomie nie zrobione w tej rundzie

* Sekcja „Cardio” w zakładce Postępy (moduł za flagą) — historia cardio widoczna
  w „Ostatnich treningach” w Planie; agregaty minut/tydzień = kolejna runda.
* Dodawanie bloków/cardio z poziomu **szkicu** (0.58.0) — szkic pokazuje i przesuwa
  pozycje, dodaje się je w edytorze nowej wersji.
* Zamiana pseudo-dnia „Wytyczne tygodnia” w TPL-025/026 na blok + cardio (stare kopie
  planów bez zmian).
* Import bloków/cardio z pliku (`IMPORT_BAZ.md` §3.6).
* Testy progowe/FTP/HRV, import z zegarków, automatyczna progresja, rankingi, AI, K1.
* Nowe pytanie w wywiadzie o leki wpływające na tętno (pole bramki w panelu trenera).

## 4. P2 z przeglądu (nienaprawione, do kolejnej rundy)

Z trzech przejść tematycznych (plan sesji, „Przegląd”; P1 naprawione: maskowanie
`avg_hr` dla trenera bez zgody zdrowotnej):

1. `prescription.hrmax_estimate` i zakres ud./min w treści planu pozwalają odtworzyć
   HRmax z wzoru (i przybliżyć tętno spoczynkowe) — **decyzja jawna (przegląd PR #75):
   zostaje**, bo bez tych liczb klient nie ma czym sterować, a treść planu jest w domenie
   treningowej jak każda wersja; wpisane w R-21 i PERMISSIONS. Odpowiedź o lekach
   wpływających na tętno nie jest zapisywana w żadnej postaci (test).
2. Numeracja „Ćwiczenie N” w edytorze liczy indeks w tablicy (blok rozgrzewki jako
   pozycja 1 → pierwsze siłowe to „Ćwiczenie 2”).
3. Podsumowanie różnic szkicu dla pozycji cardio jest generyczne („zmieniono <nazwa>”),
   bez frazy „zmieniono cel cardio”.
4. Czas sesji interwałowej = suma rund (24/16/28 min), bez rozgrzewki wejściowej i
   schłodzenia — potwierdzić z trenerem, czy dokładać „+ X min” w etykiecie.
5. Klient nie może zmienić urządzenia po zapisaniu wykonania (wybór w dniu treningu
   żyje w widoku, zapis w `WorkoutEntry.machine`) — bez „ulubionego urządzenia” na koncie.
6. „Dzisiaj” → „Wykonane ✓” zapisuje sesję bez wpisów (jak dotąd); cardio z czasem/RPE
   zapisuje się z Planu („Zapisz wykonanie z wynikami”) — rozważyć skrót na „Dzisiaj”.

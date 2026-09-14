# Zlecenia dla sesji piszącej — pakiety właściciela

Katalog na gotowe pakiety „prompt + szkic planu sesji”, przygotowane przez sesję
tylko-do-odczytu (rozpoznanie kodu, pomiar, decyzje do zatwierdzenia). Sesja
pisząca dostaje **prompt jako pierwszą wiadomość**, a szkic planu kopiuje do
`docs/plan-sesji/<gałąź>.md` jako pierwszy commit (protokół z `KOORDYNACJA.md`).

Pakiet nie jest planem sesji i nie rezerwuje niczego sam z siebie — numery wersji
i migracji w nim są **propozycją do sprawdzenia** tuż przed zmianą (`db.py`,
`CHANGELOG.md`, `STAN_PRZEKAZANIA.md` §2). Pliki tu nie są plikami integracyjnymi.

**Wszystko w jednym pliku:** `PAKIET_ZLECEN_2026-09-14.md` (złożenie promptów, planów, modelu
i tokenów z tego katalogu, z kolejnością scalania, decyzjami właściciela i zbiorczą listą
otwartych pytań). Pliki poniżej pozostają źródłem; pakiet jest ich złożeniem.

## 2026-09-14 — zlecenia właściciela

| Zlecenie | Prompt | Szkic planu | Gałąź | Warunek startu |
|---|---|---|---|---|
| 0. Ukryj kreator diety (flaga, nic nie ginie; katalog produktów zostaje) | `PROMPT_writer_ukryj-kreator.md` | `plan-sesji_ukryj-kreator.md` | `agent/ukryj-kreator` | brak (małe, może iść pierwsze) |
| 1. Dni treningowe: klient wybiera dni tygodnia dla jednostek planu; „Dzisiaj” pokazuje trening z dzisiejszego dnia | `PROMPT_writer_dni-treningowe.md` | `plan-sesji_dni-treningowe.md` | `agent/dni-treningowe` | brak (niezależne od gałęzi w toku) |
| 3. Domknięcie PR #67 „Strona publiczna: wariant czerwono-biały” (nowa szata graficzna) | `PROMPT_writer_landing-czerwony-domkniecie.md` | — (kontynuacja `docs/plan-sesji/landing-czerwony.md`) | `agent/landing-czerwony` (istniejąca, PR #67) | decyzje właściciela z §3–5 promptu (kontrast, treść, znak marki) |
| 4. Motyw czerwono-biały jako drugi, kompletny motyw aplikacji do wyboru użytkownika (klient i trener) | `PROMPT_writer_motyw-czerwony.md` + `motyw-czerwony.tokens.css` | — (plan pisze writer wg §5 promptu) | `agent/motyw-czerwony` | scalenie #67; decyzje z §7 promptu |
| 5. Rozgrzewka (3×3) + rozciąganie + cardio na sprzęcie z suwakami celów (model: 3 strefy/Karvonen/Fatmax/VO2max) | `PROMPT_writer_cardio-i-rozgrzewka.md` + `model-suwakow-cardio.md` | — (plan pisze writer wg §6) | `agent/cardio-i-rozgrzewka` | decyzje z §8; nie równolegle ze zleceniem 1 (te same pliki planu) |
| 2. Wymiany produktów v2: grupy pokrewne, zgodność funkcji w posiłku, bramka „nie pogarsza”, przycisk dla roli NONE | `PROMPT_writer_wymiany-produktow.md` | `plan-sesji_wymiany-produktow.md` | `agent/wymiany-produktow` | **scalenie `agent/biblioteka-diet`** (te same pliki; sama biblioteka obniża odsetek składników bez zamiennika z 31 % do 11 %) |

**Kolejność scalania i numery wersji** (kontrola `changelog` wymaga wersji rosnących
w kolejności scalania, więc numer przydziela piszący dopiero przy starcie, wg tej tabeli):

| Krok | Co | Wersja | Migracja | Stan (14.09 wieczór, `main` = 0.69.0, `04d1d58`) |
|---|---|---|---|---|
| — | `agent/biblioteka-diet` | 0.64.0 | 35 | scalona |
| — | `agent/monitoring-postepy` (PR #61) | 0.66.0 | 36 | scalona |
| — | `agent/ukryj-kreator` (PR #68, zlecenie 0) | 0.67.0 | — | **scalona** |
| — | `agent/wymiany-produktow` (PR #69, zlecenie 2) | 0.69.0 | — | **scalona**; import CSV z decyzjami właściciela = osobny mały PR |
| 1 | zlecenie 1 — dni treningowe | **0.68.0 (zarezerwowane w CHANGELOG 0.69.0)** | **37 (zarezerwowana)** | nie rozpoczęte |
| 2 | PR #67 `agent/landing-czerwony` (zlecenie 3) | kolejna wolna (0.70.0, jeśli wejdzie przed dniami treningowymi — wtedy dni → 0.71.0; CHANGELOG musi rosnąć w kolejności scalania) | — | gotowy do przeglądu, wymaga dociągnięcia `main` i poprawek z promptu |
| 3 | rozpoznanie wywiadu kalorycznego (PR #71, tylko dokument) | — | 38 albo 39 (przyszła) | scalone; 7 decyzji właściciela |
| 4 | zlecenie 4 — motyw czerwono-biały (po #67) | kolejna wolna | kolejna wolna (pole `theme`) lub brak | nie rozpoczęte; podgląd tokenów wykonany 14.09 |
| 5 | zlecenie 5 — rozgrzewka, rozciąganie, cardio z suwakami | kolejna wolna | **38+** (37 zajęta; 38/39 może wziąć wywiad kaloryczny — sprawdź `db.py`) | nie rozpoczęte; model i szkic treści gotowe 14.09 |

Decyzje właściciela z trzeciej tury (14.09): docelowo dwa kompletne motywy do wyboru
użytkownika — czarno-zielony i czerwono-biały (zlecenie 4). Z drugiej tury (14.09): kreator diety odłożony i ukryty; klient na
diecie z szablonu; katalog pojedynczych produktów (2058 pozycji) ma zasilić zamienniki
szablonu przez przeglądany import (zlecenie 2, §5a). Każdy prompt kończy się pytaniami
z wartościami domyślnymi — odpowiedź wpisuje się w tę samą wiadomość do sesji piszącej.

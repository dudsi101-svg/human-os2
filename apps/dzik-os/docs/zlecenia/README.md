# Zlecenia dla sesji piszącej — pakiety właściciela

Katalog na gotowe pakiety „prompt + szkic planu sesji”, przygotowane przez sesję
tylko-do-odczytu (rozpoznanie kodu, pomiar, decyzje do zatwierdzenia). Sesja
pisząca dostaje **prompt jako pierwszą wiadomość**, a szkic planu kopiuje do
`docs/plan-sesji/<gałąź>.md` jako pierwszy commit (protokół z `KOORDYNACJA.md`).

Pakiet nie jest planem sesji i nie rezerwuje niczego sam z siebie — numery wersji
i migracji w nim są **propozycją do sprawdzenia** tuż przed zmianą (`db.py`,
`CHANGELOG.md`, `STAN_PRZEKAZANIA.md` §2). Pliki tu nie są plikami integracyjnymi.

## 2026-09-14 — trzy zlecenia właściciela

| Zlecenie | Prompt | Szkic planu | Gałąź | Warunek startu |
|---|---|---|---|---|
| 0. Ukryj kreator diety (flaga, nic nie ginie; katalog produktów zostaje) | `PROMPT_writer_ukryj-kreator.md` | `plan-sesji_ukryj-kreator.md` | `agent/ukryj-kreator` | brak (małe, może iść pierwsze) |
| 1. Dni treningowe: klient wybiera dni tygodnia dla jednostek planu; „Dzisiaj” pokazuje trening z dzisiejszego dnia | `PROMPT_writer_dni-treningowe.md` | `plan-sesji_dni-treningowe.md` | `agent/dni-treningowe` | brak (niezależne od gałęzi w toku) |
| 2. Wymiany produktów v2: grupy pokrewne, zgodność funkcji w posiłku, bramka „nie pogarsza”, przycisk dla roli NONE | `PROMPT_writer_wymiany-produktow.md` | `plan-sesji_wymiany-produktow.md` | `agent/wymiany-produktow` | **scalenie `agent/biblioteka-diet`** (te same pliki; sama biblioteka obniża odsetek składników bez zamiennika z 31 % do 11 %) |

**Kolejność scalania i numery wersji** (kontrola `changelog` wymaga wersji rosnących
w kolejności scalania, więc numer przydziela piszący dopiero przy starcie, wg tej tabeli;
wersje 0.64.0 i 0.65.0 są zajęte przez `agent/biblioteka-diet` i `agent/monitoring-postepy`):

| Krok | Co | Wersja (propozycja) | Migracja |
|---|---|---|---|
| 1 | scalić `agent/biblioteka-diet` (gotowa, odblokowana) | 0.64.0 | 35 |
| 2 | zlecenie 0 — ukryj kreator | 0.66.0 (0.65.0 zostaje dla monitoringu, jeśli wejdzie wcześniej — wtedy przesuń) | — |
| 3 | zlecenie 1 — dni treningowe | kolejna wolna | 37 |
| 4 | zlecenie 2 — wymiany produktów v2 (+ korelacja katalogu) | kolejna wolna | — (przegląd CSV przez właściciela może iść równolegle) |

Decyzje właściciela z drugiej tury (14.09): kreator diety odłożony i ukryty; klient na
diecie z szablonu; katalog pojedynczych produktów (2058 pozycji) ma zasilić zamienniki
szablonu przez przeglądany import (zlecenie 2, §5a). Każdy prompt kończy się pytaniami
z wartościami domyślnymi — odpowiedź wpisuje się w tę samą wiadomość do sesji piszącej.

# Stan przekazania — przeczytaj przed rozpoczęciem rundy

**Aktualizacja:** 2026-08-18 · **Wersja w `main`:** 0.41.0
**Tryb pracy:** jeden piszący i jeden PR `[WRITER]` naraz
(`KOORDYNACJA.md`, zasada nadrzędna).

**Zanim cokolwiek dotkniesz: `docs/KARTA_WSPOLPRACY.md`** — dziesięć
zasad współpracy między sesjami, każda z podpiętym zdarzeniem, z którego
się wzięła. Ten dokument mówi GDZIE jesteśmy; karta mówi JAK pracujemy.

Ten dokument zastępuje domysły. Ma odpowiadać na trzy pytania: **gdzie
jesteśmy**, **co jest w toku** i **co następne**. Aktualizuj go na koniec
każdej rundy — to warunek przekazania pałeczki.

---

## 1. Gdzie jesteśmy

**`main` jest jedyną linią kanoniczną — i od 18.08.2026 także gałęzią
domyślną GitHuba** (właściciel przełączył po scaleniu PR #14). Protokół
jednego piszącego jest scalony (`98dca51`) i obowiązuje: plan sesji jako
pierwszy commit, draft PR `[WRITER]`, reszta agentów read-only.

| Gałąź | Stan |
|---|---|
| `main` | **kanoniczna i domyślna**, najnowsza wersja produktu |
| `agent/recover-agent-collisions` | scalona przez PR #14 (protokół agentów); nie używać ponownie |
| `claude/dzik-os-personal-trainer-app-d3q7fx` (`94aaa39`) | przodek `main`, scalona; nie zaczynać tu nowej pracy |
| `claude/ocena-projektu-dzik-os-76ercy` (`861ed53`) | **niescalona**: 2 własne commity i 3 brakujące z `main`; nie scalać mechanicznie, nie powtarzać jej pracy |
| `claude/ui-layout-spacing-clarity-8tpz99` | przodek `main`, scalona |

**Stan jakości** (`docs/BRAMKA_GO_NOGO.md`): warunkowe GO na pilotaż z
jednym prawdziwym klientem, **NO-GO na szerszą produkcję** — siedem
blokerów wypisanych w §5 tamtego dokumentu.

**Ostatnia runda (0.41.0, gałąź `agent/xlsx-bomba`, pierwsza wg nowego
protokołu):** bomba dekompresyjna `.xlsx` (K-002 pkt 1) rozbrojona
wewnątrz `sheet_import.py` — kontrola sumy rozmiarów po rozpakowaniu
z katalogu ZIP-a przed `load_workbook`, twardy limit przeskanowanych
wierszy przerywający iterację, limit szerokości wiersza; wszystko jako
`SheetError`, routery bez zmian. Zmierzone na żywo: plik deklarujący
400 MB XML odrzucony w 83 ms przy +6,9 MB RSS (było: 1164 MB, 129 s).
**Wszystkie znaleziska przeglądu krzyżowego K-002 są zamknięte.**

**Runda 0.40.0 (poprzednia):** ekran Szablony scalony do jednej karty
„Dodaj szablon"; limity `_read_limited` na trzech importach (K-002 pkt 2);
scalenie katalogów E2E, Karta 1.0, dziennik K-NNN czytany przez bramkę.

**Znane problemy bramki lokalnej (dług testów, nie regresje):**

* dwa testy OCR nazwane „bez Tesseracta" nie izolują tego założenia
  i czerwienią się, gdy binarka jest dostępna (obejście:
  `DZIK_OCR_BINARY=__missing_tesseract__`);
* cztery testy zależne od prawdziwej daty czerwienią się, gdy zegar
  maszyny odjedzie od dnia pisania testów (wykryte 23.08 na maszynie
  z zegarem 5 dni przed czasem CI): `test_notifications.py::
  test_active_days_skip_planning`, `::test_paid_payment_suppresses_due_reminder`,
  `test_plan_versioning.py::test_workout_logging_against_plan`,
  `test_push.py::test_reminder_loop_sends_for_matching_schedule`.
  Mechanizm: test wstrzykuje zamrożoną datę do sprawdzanej funkcji, ale
  dane przygotowuje względem prawdziwego `now()`. Padają na czystym
  `main` w 3 s — potwierdzone stashem podczas rundy 0.41.0. Naprawa:
  zamrozić czas także dla danych (ta sama mała runda co testy OCR).

**Bramki gałęzi porządkującej:** ruff czysto; backend 760 zaliczonych,
1 opcjonalny test Tesseracta pominięty; Core 275/275; kontroler spójności
37/37; `spojnosc.py` czysto (10 kontroli, 1 otwarta konsultacja). Frontendu
nie uruchamiano, ponieważ runda nie zmienia kodu ani zasobów frontendu.

---

## 2. Co jest w toku — NIE ZACZYNAJ OD NOWA

| Rzecz | Stan | Gdzie |
|---|---|---|
| **Niescalona runda bramkowa** | commity `81eb30a` (pamięć importu) i `861ed53` (SMTP + E2E) istnieją tylko na starej bazie; nie zaczynać tych zadań od nowa, ale przed scaleniem zaktualizować bazę i przejrzeć konflikty | `claude/ocena-projektu-dzik-os-76ercy` |
| **Testy OCR** | dwa testy „bez Tesseracta” nie izolują założenia i czerwienią się, gdy binarka jest zainstalowana; poprawić w osobnym małym PR | `backend/tests/test_ocr.py` |
| **Dostawca AI** | zaplanowany, **nierozpoczęty**. Istnieje wyłącznie `NullAIProvider`; kontrakt gotowy, cztery miejsca już go wołają | `backend/dzik_os/ai_provider.py` |
| Klucz API | właściciel go ma; **musi trafić do sekretu**, nigdy do czatu ani repozytorium | `DZIK_AI_API_KEY` + `DZIK_AI_ENABLED=true` |
| Decyzja o `extra="forbid"` | przygotowana analiza, **decyzja należy do właściciela** | `BRAMKA_GO_NOGO.md` §4 |
| Wyniesienie kopii zapasowych poza Fly | czeka na wybór dostawcy magazynu | `ODZYSKIWANIE.md` §5 |

---

## 3. Co następne — kolejka

Kolejność jest propozycją; właściciel może ją zmienić w dowolnym momencie.

1. **Rozliczyć niescaloną rundę bramkową.** Nie przepisywać jej zmian.
   Zaktualizować bazę dwóch commitów, przejrzeć konflikt w
   `STAN_PRZEKAZANIA.md`, uruchomić pełne bramki i dopiero wtedy podjąć
   decyzję o osobnym PR-ze.
2. **Dwie małe rundy naprawcze:** izolacja testów od środowiska — testy
   OCR (założenie „bez Tesseracta") i cztery testy zależne od prawdziwej
   daty (lista w §1); do tego ostatnia stara fraza „jedna-sesja-naraz"
   w `KARTA_WSPOLPRACY.md` (linia ~191).
3. **Dostawca AI.** Jedyna zmiana odblokowująca **cztery istniejące
   funkcje naraz** (OCR, odczyt opisu ćwiczenia, onboarding, asystent)
   zamiast dokładania piątej. Szczegóły:
   `docs/plan-sesji/dzik-os-personal-trainer-app.md` §4.
   Konsultacja rozstrzygnięta (K-000): **obszar w całości produktowy.**
4. **Przygotowanie pilotażu** — usunięcie `DZIK_SEED_DEMO` z `fly.toml`
   (zasiewa konta ze znanymi hasłami), zmiana haseł, jedno odtworzenie
   kopii **na produkcji**.

---

## 4. Czego nie wolno ruszać

* `hos_engine/` i `tests/` w korzeniu — Core Human OS. **275 testów musi
  zostać zielone.** Praca aplikacji nigdy tego nie dotyka.
* Nie otwierać ponownie PR #13 i nie dodawać drugiego scalenia tych samych
  historii. Nie zmieniać gałęzi domyślnej bez osobnej decyzji właściciela.
* Nie scalać mechanicznie `claude/ocena-projektu-dzik-os-76ercy`; gałąź
  jest za `main`, dotyka plików integracyjnych i wymaga osobnego przeglądu.
* Migracje już wydane: numeracja idzie **od największego numeru**, luk się
  nie zostawia (domyka się je pustym wpisem — patrz `db.py`, numer 21).
* Historia planów, diet i szablonów: nowa wersja, **nigdy nadpisanie**.

---

## 5. Zanim uznasz rundę za skończoną

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q                     # Core: 275 zielonych
python apps/dzik-os/tools/spojnosc.py          # 10 kontroli
python apps/dzik-os/tools/mutacje.py           # 17/17
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py   # 9/9
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers
```

Do tego **uruchom to, co nowe, i zobacz na własne oczy**
(`docs/ZASADA_URUCHOMIENIA.md`) — testy są warunkiem wstępnym, nie
dowodem. W raporcie napisz, co kliknąłeś i co zobaczyłeś.

Na koniec: zaktualizuj ten plik i zwolnij rezerwacje w `KOORDYNACJA.md`.

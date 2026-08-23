# Stan przekazania — przeczytaj przed rozpoczęciem rundy

**Aktualizacja:** 2026-08-18 · **Wersja w `main`:** 0.40.0
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

**`main` jest jedyną linią kanoniczną.** PR #13 został scalony 18.08.2026
o 18:21 UTC i zachował obie historie w commicie `94aaa39`. `main` oraz
`claude/dzik-os-personal-trainer-app-d3q7fx` wskazują teraz ten sam commit,
więc wcześniejsza rozbieżność jest zamknięta.

GitHub nadal wskazuje długą gałąź `claude/...` jako domyślną. To błąd
konfiguracji, nie źródło prawdy. Zmiana na `main` wymaga osobnej decyzji
właściciela po scaleniu PR-a porządkującego pracę agentów.

| Gałąź | Stan |
|---|---|
| `main` (`94aaa39`) | **kanoniczna**, najnowsza wersja produktu |
| `claude/dzik-os-personal-trainer-app-d3q7fx` (`94aaa39`) | ten sam stan co `main`; nie zaczynać tu nowej pracy |
| `claude/ocena-projektu-dzik-os-76ercy` (`861ed53`) | **niescalona**: 2 własne commity i 3 brakujące z `main`; nie scalać mechanicznie, nie powtarzać jej pracy |
| `claude/ui-layout-spacing-clarity-8tpz99` | przodek `main`, scalona |

**Stan jakości** (`docs/BRAMKA_GO_NOGO.md`): warunkowe GO na pilotaż z
jednym prawdziwym klientem, **NO-GO na szerszą produkcję** — siedem
blokerów wypisanych w §5 tamtego dokumentu.

**Ostatnia runda (0.40.0):** ekran Szablony scalony do jednej karty
„Dodaj szablon" (wzorzec z Ćwiczeń 0.34.0); limity `_read_limited` na
trzech importach plików (K-002 pkt 2). Sesja bramek równolegle: scaliła
katalogi E2E (`apps/dzik-os/e2e/` zniknął, zostały `frontend/e2e/` w CI),
złączyła dokumenty współpracy w Kartę 1.0 i postawiła dziennik
konsultacji K-NNN czytany przez bramkę. Dwa dawne punkty kolejki (E2E,
Szablony) wykonane. W konflikcie `KONSULTACJE.md` i `spojnosc.py` zostały
nowsze wersje: format `K-NNN`, 10 kontroli, 37 testów kontrolera i 17/17
wykrytych mutacji.

**Znany problem bramki lokalnej:** dwa testy OCR nazwane „bez Tesseracta"
nie izolują tego założenia i czerwienią się, gdy binarka jest dostępna.
Na maszynie audytowej z Tesseractem 5.3.4 oba zawiodły; po ukryciu binarki
przeszły 2/2. To dług techniczny testów, nie regresja tej rundy.

**Bramki gałęzi porządkującej:** ruff czysto; backend 760 zaliczonych,
1 opcjonalny test Tesseracta pominięty; Core 275/275; kontroler spójności
37/37; `spojnosc.py` czysto (10 kontroli, 1 otwarta konsultacja). Frontendu
nie uruchamiano, ponieważ runda nie zmienia kodu ani zasobów frontendu.

---

## 2. Co jest w toku — NIE ZACZYNAJ OD NOWA

| Rzecz | Stan | Gdzie |
|---|---|---|
| **Protokół jednego piszącego** | przygotowany na PR `[WRITER]`: `main` jako jedyna baza, pozostali agenci tylko recenzują/testują read-only, konflikt oznacza STOP. **PR #14 jest jednorazowym PR-em startowym** — sam nie spełnia reguły „pierwszy commit to wyłącznie plan", bo ją dopiero wprowadza; reguła obowiązuje od następnej rundy i nie wolno się na ten wyjątek powoływać | `AGENTS.md`, `CLAUDE.md`, `KOORDYNACJA.md`, `plan-sesji/recover-agent-collisions.md` |
| **Konfiguracja GitHuba** | gałąź domyślna nadal wskazuje długą linię `claude/...`; zmienić na `main` dopiero po osobnej zgodzie właściciela | ustawienia repozytorium |
| **Niescalona runda bramkowa** | commity `81eb30a` (pamięć importu) i `861ed53` (SMTP + E2E) istnieją tylko na starej bazie; nie zaczynać tych zadań od nowa, ale przed scaleniem zaktualizować bazę i przejrzeć konflikty | `claude/ocena-projektu-dzik-os-76ercy` |
| **Testy OCR** | dwa testy „bez Tesseracta” nie izolują założenia i czerwienią się, gdy binarka jest zainstalowana; poprawić w osobnym małym PR | `backend/tests/test_ocr.py` |
| **Dostawca AI** | zaplanowany, **nierozpoczęty**. Istnieje wyłącznie `NullAIProvider`; kontrakt gotowy, cztery miejsca już go wołają | `backend/dzik_os/ai_provider.py` |
| Klucz API | właściciel go ma; **musi trafić do sekretu**, nigdy do czatu ani repozytorium | `DZIK_AI_API_KEY` + `DZIK_AI_ENABLED=true` |
| Decyzja o `extra="forbid"` | przygotowana analiza, **decyzja należy do właściciela** | `BRAMKA_GO_NOGO.md` §4 |
| Wyniesienie kopii zapasowych poza Fly | czeka na wybór dostawcy magazynu | `ODZYSKIWANIE.md` §5 |

---

## 3. Co następne — kolejka

Kolejność jest propozycją; właściciel może ją zmienić w dowolnym momencie.

1. **Domknąć protokół repozytorium.** Przejrzeć i scalić PR `[WRITER]` do
   `main`, potem osobno zatwierdzić zmianę gałęzi domyślnej. Dopiero wtedy
   uruchamiać następnego piszącego.
2. **Rozliczyć niescaloną rundę bramkową.** Nie przepisywać jej zmian.
   Zaktualizować bazę dwóch commitów, przejrzeć konflikt w
   `STAN_PRZEKAZANIA.md`, uruchomić pełne bramki i dopiero wtedy podjąć
   decyzję o osobnym PR-ze.
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

# Stan przekazania — przeczytaj przed rozpoczęciem rundy

**Aktualizacja:** 2026-08-18 · **Wersja w `main`:** 0.40.0
**Tryb pracy:** jedna sesja naraz (`KOORDYNACJA.md`, zasada nadrzędna).

**Zanim cokolwiek dotkniesz: `docs/KARTA_WSPOLPRACY.md`** — dziesięć
zasad współpracy między sesjami, każda z podpiętym zdarzeniem, z którego
się wzięła. Ten dokument mówi GDZIE jesteśmy; karta mówi JAK pracujemy.

Ten dokument zastępuje domysły. Ma odpowiadać na trzy pytania: **gdzie
jesteśmy**, **co jest w toku** i **co następne**. Aktualizuj go na koniec
każdej rundy — to warunek przekazania pałeczki.

---

## 1. Gdzie jesteśmy

**Wszystkie gałęzie scalone do `main`.** Po dniu pracy trzech równoległych
sesji zostaje jedna linia:

| Gałąź | Stan |
|---|---|
| `claude/dzik-os-personal-trainer-app-d3q7fx` | scalona, aktywna |
| `claude/ocena-projektu-dzik-os-76ercy` | **scalona w całości** (kontrola higieny gałęzi) |
| `claude/ui-layout-spacing-clarity-8tpz99` | **scalona w całości** (czytelność i responsywność UI) |

**Stan jakości** (`docs/BRAMKA_GO_NOGO.md`): warunkowe GO na pilotaż z
jednym prawdziwym klientem, **NO-GO na szerszą produkcję** — siedem
blokerów wypisanych w §5 tamtego dokumentu.

**Ostatnia runda (0.40.0):** ekran Szablony scalony do jednej karty
„Dodaj szablon" (wzorzec z Ćwiczeń 0.34.0) — punkt 2 dawnej kolejki
wykonany.

**Liczby:** ok. 745 testów backendu, 275 testów Core Human OS (nietykalne),
140 testów pomocniczych frontendu, testy E2E (Playwright) w CI,
9 kontroli spójności, dwa przeglądy mutacyjne (7/7 i 9/9).

---

## 2. Co jest w toku — NIE ZACZYNAJ OD NOWA

| Rzecz | Stan | Gdzie |
|---|---|---|
| **Dostawca AI** | zaplanowany, **nierozpoczęty**. Istnieje wyłącznie `NullAIProvider`; kontrakt gotowy, cztery miejsca już go wołają | `backend/dzik_os/ai_provider.py` |
| Klucz API | właściciel go ma; **musi trafić do sekretu**, nigdy do czatu ani repozytorium | `DZIK_AI_API_KEY` + `DZIK_AI_ENABLED=true` |
| Decyzja o `extra="forbid"` | przygotowana analiza, **decyzja należy do właściciela** | `BRAMKA_GO_NOGO.md` §4 |
| Wyniesienie kopii zapasowych poza Fly | czeka na wybór dostawcy magazynu | `ODZYSKIWANIE.md` §5 |

---

## 3. Co następne — kolejka

Kolejność jest propozycją; właściciel może ją zmienić w dowolnym momencie.

1. **Dostawca AI.** Jedyna zmiana odblokowująca **cztery istniejące
   funkcje naraz** (OCR, odczyt opisu ćwiczenia, onboarding, asystent)
   zamiast dokładania piątej. Szczegóły:
   `docs/plan-sesji/dzik-os-personal-trainer-app.md` §4.
   **Uwaga:** otwarte pytanie w `KONSULTACJE.md` — jeśli druga sesja
   napisze „bierzemy", ten punkt wypada z kolejki.
2. **Dwa katalogi testów E2E** — `apps/dzik-os/e2e/` (dostępność, offline
   PWA) i `frontend/e2e/` (Playwright w CI). Zejść do jednego; zostaje
   `frontend/e2e/`, bo jest w CI. Też czeka na odpowiedź w
   `KONSULTACJE.md` (to obszar drugiej sesji).
3. **Przygotowanie pilotażu** — usunięcie `DZIK_SEED_DEMO` z `fly.toml`
   (zasiewa konta ze znanymi hasłami), zmiana haseł, jedno odtworzenie
   kopii **na produkcji**.

---

## 4. Czego nie wolno ruszać

* `hos_engine/` i `tests/` w korzeniu — Core Human OS. **275 testów musi
  zostać zielone.** Praca aplikacji nigdy tego nie dotyka.
* Migracje już wydane: numeracja idzie **od największego numeru**, luk się
  nie zostawia (domyka się je pustym wpisem — patrz `db.py`, numer 21).
* Historia planów, diet i szablonów: nowa wersja, **nigdy nadpisanie**.

---

## 5. Zanim uznasz rundę za skończoną

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q                     # Core: 275 zielonych
python apps/dzik-os/tools/spojnosc.py          # 9 kontroli
python apps/dzik-os/tools/mutacje.py           # 7/7
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py   # 9/9
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers
```

Do tego **uruchom to, co nowe, i zobacz na własne oczy**
(`docs/ZASADA_URUCHOMIENIA.md`) — testy są warunkiem wstępnym, nie
dowodem. W raporcie napisz, co kliknąłeś i co zobaczyłeś.

Na koniec: zaktualizuj ten plik i zwolnij rezerwacje w `KOORDYNACJA.md`.

# Plan sesji: RELEASE_STATUS + odświeżenie README (audyt Sprint B, pozycja B1)

**Gałąź:** `agent/stan-wydania` (od `main` = e36cdc9)
**Rola:** aktywny piszący
**Cel:** dokumentacja wejściowa przestaje kłamać o stanie projektu —
README deklaruje 0.4.0 i 92 testy przy realnych 0.53.x i ~850 testach,
a jedynego dokumentu „co właściwie działa na produkcji TERAZ" brak.

## Zamiar

1. **`docs/RELEASE_STATUS.md`** (nowy) — jedna strona prawdy o
   produkcji: wersja, adres, ścieżka deployu (CI → workflow_run →
   smoke), konta i role, limit podopiecznych, stan integracji
   (SMTP: wyłączone — czeka na hasło aplikacji; AI: wyłączone;
   szyfrowanie plików: workflow gotowy, nieaktywowane), otwarte
   kroki właściciela (W1–W6). Z datą i wersją w nagłówku.
2. **README.md** — status/wersja aktualne, liczby testów realne,
   sekcja testów z pełnym zestawem bramek (mutacje, spójność, E2E
   Playwright zamiast dawnych „3 testów pytest"), tabela dokumentów
   uzupełniona o RELEASE_STATUS/STAN_PRZEKAZANIA/BRAMKA_GO_NOGO,
   konta demo wyraźnie oznaczone jako seed lokalny (na produkcji
   zdezaktywowane).
3. **`tools/spojnosc.py`** — 12. kontrola `sprawdz_wersje_dokumentow`:
   wersja z nagłówka README i z RELEASE_STATUS musi równać się
   najnowszej wersji CHANGELOG (ten sam mechanizm, który pilnuje
   STAN_PRZEKAZANIA) — dryf dokumentacji wejściowej czerwieni bramkę,
   zamiast czekać na następny audyt.

## Świadomie nie robię

- nie przepisuję treści merytorycznej instrukcji ani dokumentów RODO
  (osobne pozycje planu); nie zmieniam kodu aplikacji.

## Rezerwacje

- **Wersja: 0.53.7.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki backend/tools + spójność (nowa kontrola najpierw czerwona
  na starym README — dowód, że działa — potem zielona po poprawce).

## Weryfikacja (wykonana)

- Nowa kontrola najpierw CZERWONA na starym stanie (README bez 0.53.6,
  brak RELEASE_STATUS — dokładnie 2 błędy, kod 1), po poprawkach
  spójność czysto (**12 kontroli**).
- `ruff` — czysto; backend **850 passed, 1 skipped** (w tym
  test_spojnosc 37); Core **275 passed**.
- Uruchomienie na żywo: `python apps/dzik-os/tools/spojnosc.py`
  obejrzane w obu stanach (czerwień → zieleń) — patrz wyżej.

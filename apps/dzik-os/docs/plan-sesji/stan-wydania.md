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

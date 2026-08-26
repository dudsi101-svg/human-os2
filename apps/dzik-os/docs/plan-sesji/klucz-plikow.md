# Plan sesji: DZIK_FILE_KEY bez terminala (audyt Sprint A, pozycja A6)

**Gałąź:** `agent/klucz-plikow` (od `main` = 12f7f9b)
**Rola:** aktywny piszący
**Cel:** szyfrowanie plików at-rest (R-02) da się WŁĄCZYĆ i UDOWODNIĆ
jednym klikiem w Actions — właściciel nie ma terminala, a mechanizm
w `storage.py` czeka gotowy od dawna.

## Zamiar

1. **`dzik_os/test_szyfrowania.py`** — samodowodzący moduł na wzór
   `test_poczty`: zapisuje plik-sondę przez warstwę storage, czyta
   surowe bajty z dysku i sprawdza nagłówek `DZIKENC1`, odszyfrowuje
   z powrotem, sprząta po sobie. Wyjście 0 wyłącznie przy pełnym
   dowodzie; bez klucza — jawny błąd `no_key`. Testy jednostkowe.
2. **`.github/workflows/fly-klucz-plikow.yml`** — workflow_dispatch:
   bierze klucz z sekretu repo `DZIK_FILE_KEY`, a gdy pusty — generuje
   świeży (`openssl rand -base64 32`, `::add-mask::`); ustawia sekret
   na Fly (maszyna restartuje się sama); uruchamia na maszynie
   `python -m dzik_os.test_szyfrowania` jako dowód; kopię klucza
   składa w artefakcie `klucz-plikow` (retention 1 dzień) do
   odebrania przez właściciela i schowania POZA repo — bez klucza
   backupy zaszyfrowanych plików są nie do odzyskania.
   Wzorce bezpieczeństwa jak w pozostałych workflow (inputy przez
   env + walidacja; sekrety nigdy w argv — przez tymczasowy sekret
   środowiska na maszynie, jak w fly-bootstrap).
3. Dokumentacja: CHANGELOG 0.53.6, STAN_PRZEKAZANIA (krok właściciela:
   klik + odbiór klucza), wzmianka w RISK_REGISTER R-02 o gotowej
   ścieżce włączenia (bez zamykania ryzyka — zamknie je właściciel
   po faktycznym włączeniu).

## Świadomie nie robię

- nie włączam szyfrowania sam: `flyctl secrets set` restartuje
  produkcję i wymaga decyzji właściciela o przechowaniu kopii klucza
  (utrata klucza = utrata plików) — workflow czeka gotowy;
- nie szyfruję istniejących plików wstecz (pliki sprzed włączenia
  czyta się dalej — `decrypt_file_bytes` to gwarantuje); dogrywka
  wsteczna to osobna, świadoma runda.

## Rezerwacje

- **Wersja: 0.53.6.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki pełne + testy modułu sondy; walidacja YAML; spójność.

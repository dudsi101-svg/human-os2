# Plan sesji: próba odtworzenia backupu (audyt Sprint B, pozycja B4)

**Gałąź:** `agent/proba-odtworzenia` (od `main` = 297df3c)
**Rola:** aktywny piszący
**Cel:** backup, którego nikt nigdy nie odtworzył, to nadzieja, nie
kopia zapasowa. Regularna, nieniszcząca próba odtworzenia na maszynie
produkcyjnej — świeże archiwum → odtworzenie do katalogu tymczasowego
→ raport WYŁĄCZNIE z liczności (zero PII) → sprzątanie.

## Zamiar

1. **`dzik_os/proba_odtworzenia.py`** — moduł na wzór `test_poczty`/
   `test_szyfrowania`: (a) tworzy świeże archiwum (`create_backup`),
   (b) odtwarza je PODPROCESEM `python -m dzik_os.backup --restore
   --force` z DZIK_DATABASE_URL/DZIK_AUDIT_DB/DZIK_UPLOAD_DIR
   przestawionymi na katalog tymczasowy (izolacja przez env — dane
   produkcyjne nietykane strukturalnie, bez łatania backup.py),
   (c) na odtworzonej kopii: liczności kluczowych tabel (users,
   role_grants, coach_client_relationships, checkins, receipts…),
   liczba plików uploadów, weryfikacja łańcucha audytu
   (`SQLiteEventStore.verify_chain` na odtworzonym pliku),
   (d) sprzątanie katalogu tymczasowego zawsze. Kod 0 wyłącznie gdy:
   odtworzenie się powiodło, łańcuch OK (albo brak bazy audytu
   w archiwum — raportowane jawnie), users ≥ 1. Raport bez PII —
   wyłącznie nazwy tabel i liczby.
2. **`.github/workflows/fly-proba-odtworzenia.yml`** — workflow_dispatch
   (bez inputów) + harmonogram co poniedziałek 05:00 UTC: uruchamia
   moduł na maszynie przez `flyctl ssh console`. Akcje przypięte po SHA
   (kontrola spójności pilnuje).
3. Testy jednostkowe modułu (SQLite, świeża baza z kontem) —
   sukces, brak archiwum, users=0.
4. Dokumentacja: CHANGELOG 0.53.9, STAN, RELEASE_STATUS (wiersz
   integracji backup → „próba odtworzenia: workflow + poniedziałkowy
   harmonogram"), ODZYSKIWANIE.md — sekcja o próbie.

## Świadomie nie robię

- nie odtwarzam na żywe dane (to osobna, ręczna procedura
  z ODZYSKIWANIE.md przy zatrzymanej aplikacji);
- off-site backup (W4) bez zmian — czeka na poświadczenia właściciela.

## Rezerwacje

- **Wersja: 0.53.9.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki pełne; uruchomienie modułu na żywo lokalnie (na bazie z seedu).

## Weryfikacja (wykonana)

- `ruff` — czysto; backend **852 passed, 1 skipped** (2 nowe testy:
  dowód bez PII + jawna porażka); Core **275**; spójność czysto
  (13 kontroli); YAML workflow zwalidowany.
- Uruchomienie na żywo (izolowane środowisko z seedem):
  `python -m dzik_os.proba_odtworzenia` → archiwum, odtworzenie,
  users: 7, role_grants: 7, relacje: 5, weekly_checkins: 3, plany: 4,
  receipts: 45, pliki uploadów: 3, łańcuch audytu OK (dwukrotnie:
  z procesu odtwarzającego i niezależnie), kod 0. Pierwszy przebieg
  ujawnił literówkę nazwy tabeli („checkins" → `weekly_checkins`) —
  poprawiona, a test zaostrzony: każdy „BRAK TABELI" czerwieni test.
- Na produkcji workflow wystartuje w najbliższy poniedziałek 05:00 UTC
  (można też ręcznie — Run workflow).

## Poprawka po pierwszym przebiegu CI

Job PostgreSQL czerwony: archiwum na PG to zrzut `pg_dump`, a izolacja
katalogiem tymczasowym istnieje tylko dla SQLite — podproces próbował
`psql` na domyślny socket. Naprawa uczciwa, nie udawana: moduł jawnie
odmawia na bazie innej niż SQLite (produkcja działa na SQLite; pełne
odtworzenie na PG pokrywa destrukcyjnie `test_backup` na jobie PG,
ręczna procedura — ODZYSKIWANIE.md), a test na PG sprawdza odmowę
i skipuje pełną próbę.

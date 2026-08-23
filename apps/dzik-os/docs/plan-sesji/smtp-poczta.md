# Plan sesji: poczta wychodząca (rozliczenie gałęzi bramkowej)

**Gałąź:** `agent/smtp-poczta` (od `main` = `b8a2ebe`)
**Rola:** aktywny piszący i integrator (wyznaczony przez właściciela —
polecenie „rozwiąż wszystkie problemy stojące naprzeciw odpalenia
aplikacji, współpracuj z innymi agentami")
**Cel:** rozliczyć niescaloną gałąź `claude/ocena-projektu-dzik-os-76ercy`
zgodnie z raportem agenta analitycznego (read-only) z 23.08: przenieść
implementację SMTP, odrzucić zdublowaną część, uratować sprostowanie
pomiaru. Zamyka bloker nr 4 bramki GO/NO-GO (poczta nie wychodzi) —
bez dostawcy e-maila reset hasła jest martwy, co dla pilotażu z prawdziwym
klientem jest gorsze, niż sugeruje sama bramka.

## Rozstrzygnięcia (za raportem analizy, `git merge-tree` na 6 konfliktach)

- **`81eb30a` („pamięć importu") — ODRZUCONY w całości.** Main ma ścisły
  nadzbiór tej pracy: 0.40.0 dało `_read_limited` w routerach, 0.41.0 dało
  limity wewnątrz parsera (rozpakowanie + wiersze + kolumny, których
  gałąź nie miała). Przeniesienie oznaczałoby dwa mechanizmy do tego
  samego celu i testy asertujące nieistniejący kod.
- **`861ed53` (SMTP + podział E2E) — PRZENIESIONY plikowo,** bo pięć jego
  plików nie koliduje z main (sprawdzone merge-tree): `config.py` (pola
  `smtp_*`), `notifications_provider.py` (`SMTPNotificationProvider`),
  `tests/test_powiadomienia_smtp.py`, `docs/DEPLOYMENT.md` §4c,
  `frontend/playwright.config.ts` (projekty telefon/desktop).
  Cherry-pick całych commitów odpada: ich diffy CHANGELOG/RISK_REGISTER
  budują na tekście z odrzuconego `81eb30a`.
- **Uratowane z `81eb30a`:** sprostowanie zawyżonego pomiaru w
  `docs/PRZEGLAD_KRZYZOWY_2026-08-18.md` (1057 MB → 419 MB; bufor
  `TestClient` w tym samym procesie zawyżał RSS) — korekta faktu,
  nie duplikat kodu.
- **R-14 w `docs/RISK_REGISTER.md`** przepisany ręcznie (nie diffem
  gałęzi). Wiersza R-19 nie ruszam — opisuje kod, którego na main nie ma;
  jego domknięcie mechanizmem 0.41.0 zapisuję osobnym zdaniem.

## Mój obszar

- `backend/dzik_os/config.py`, `backend/dzik_os/notifications_provider.py`;
- `backend/tests/test_powiadomienia_smtp.py` (nowy);
- `frontend/playwright.config.ts`;
- `docs/DEPLOYMENT.md`, `docs/RISK_REGISTER.md` (wiersz R-14),
  `docs/PRZEGLAD_KRZYZOWY_2026-08-18.md` (sprostowanie);
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md`, `docs/KONSULTACJE.md`
  (jako integrator); ten plan.

## Czego nie dotykam

- `sheet_import.py`, `storage.py`, routerów — praca `81eb30a` odrzucona;
- Core Human OS (`hos_engine/`, `tests/` w korzeniu);
- migracji i seeda;
- gałęzi `claude/ocena-projektu-dzik-os-76ercy` samej w sobie (zostaje
  w historii, nic nie kasuję).

## Rezerwacje

- **Wersja: 0.42.0** (ostatnia: 0.41.0). **Migracja: brak.**

## Świadomie nie robię

- nie konfiguruję prawdziwego dostawcy SMTP — sekrety (`smtp_host`,
  hasło) ustawia właściciel we Fly; bez nich zachowanie pozostaje
  dokładnie dotychczasowe (Null, log `email_skipped_no_provider`);
- nie wysyłam prawdziwego e-maila (brak dostawcy w tym środowisku —
  zgodnie z `ZASADA_URUCHOMIENIA.md` mówię to wprost: tryb rozszerzony
  wykona się dopiero po podaniu sekretów);
- nie scalam własnego PR-a przed zielonym CI.

## Weryfikacja (do wypełnienia)

- pełne bramki §5 + testy SMTP na prawdziwym serwerze na gniazdach
  (lokalnym, z testów gałęzi);
- E2E przemierzone na nowym podziale projektów — deklaracja „N zielonych"
  z gałęzi była mierzona na starym `szablony.spec.ts`, więc liczbę
  podaję z własnego przebiegu, nie przepisuję.

# Rejestr ryzyk — Dzik OS MVP

Status: aktualny na 2026-08-17. Ryzyka zaakceptowane świadomie dla MVP;
każde ma wskazany warunek ponownej oceny.

| ID | Ryzyko | Waga | Mitygacja w MVP | Do zrobienia przed produkcją |
|---|---|---|---|---|
| R-01 | Dane zdrowotne bez formalnej oceny prawnej (RODO art. 9) | WYSOKA | mapa przetwarzania, zgody wersjonowane, eksport/usunięcie wbudowane | przegląd prawny, umowa powierzenia, polityka prywatności |
| R-02 | Brak szyfrowania at-rest bazy i plików | WYSOKA | dostęp wyłącznie przez API z autoryzacją; losowe nazwy plików | dysk szyfrowany / pgcrypto / szyfrowanie plików |
| R-03 | Rate limiter logowania w pamięci procesu (reset przy restarcie, nie działa między replikami) | ŚREDNIA | pojedynczy proces w MVP | licznik w DB/Redis |
| R-04 | Łańcuch audytu w osobnym pliku SQLite — zdarzenie może zostać zapisane mimo rollbacku transakcji głównej DB (nadmiarowy wpis, nigdy brak wpisu) | ŚREDNIA | akceptowalne: fałszywie dodatnie wpisy audytu nie ukrywają operacji | outbox pattern lub StateCheckpoint z hos_engine |
| R-05 | ~~Zgoda onboardingowa bez potwierdzenia podmiotu~~ **ZAMKNIĘTE 2026-08-17**: klient przy pierwszym logowaniu jawnie potwierdza zgodę (CONSENT_CONFIRMED w audycie) albo ją cofa | — | brama zgód w aplikacji + endpoint confirm | — |
| R-06 | ~~Brak wymuszenia zmiany hasła startowego~~ **ZAMKNIĘTE 2026-08-17**: konto z hasłem startowym jest blokowane po stronie serwera (PASSWORD_CHANGE_REQUIRED) do czasu zmiany; zmiana unieważnia pozostałe sesje | — | wymuszona zmiana przy 1. logowaniu | reset hasła e-mailem (odłożone) |
| R-07 | Brak 2FA | NISKA (skala MVP) | silne hasła, rate limiting, sesje wygasające | TOTP dla trenera i admina |
| R-08 | Filmy MP4 przechowywane bez skanowania/transkodowania | NISKA | whitelist typów, limit rozmiaru, serwowanie z nosniff | antywirus/transkodowanie przy większej skali |
| R-09 | SQLite jako domyślna baza (pojedynczy proces) | NISKA | Compose z PostgreSQL gotowy | produkcja wyłącznie na PostgreSQL |
| R-10 | Napięcie normatywne: INTENDED_PURPOSE.md Human OS (aplikacja osobista bez suplementów) vs. harmonogram suplementów w Dzik OS | ŚREDNIA | Dzik OS wyłącznie **przechowuje i przypomina** plan wpisany przez człowieka z zapisanym autorem; zero rekomendacji i dawkowania przez system — patrz ADR-DZIK-003 §4 | opinia prawna dot. granicy wyrobu medycznego przy rozwoju funkcji |
| R-11 | E-maile klientów widoczne dla admina (dane kontaktowe, nie zdrowotne) | NISKA | audyt każdego wejścia admina | rozważyć maskowanie |
| R-12 | Brak kopii zapasowych w MVP | WYSOKA | wolumeny Dockera | harmonogram backupów DB + plików + audit.db, test odtwarzania |

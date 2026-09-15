# Plan sesji: zaproszenia i reset hasła nie wychodziły mimo sprawnego SMTP (0.76.1)

**Gałąź:** `agent/poczta-zaproszenia` (od `main` = `a8962d9`, 0.76.0). **Rola:**
integrator jako piszący. **Powód:** zadanie właściciela o trzech kontach testowych
(zaproszenia → aktywacja → zgody). Przed zaproszeniem sprawdziłem stan produkcji
i okazało się, że problem jest głębszy niż same konta.

## Rozpoznanie (produkcja, 15.09)

* `Diagnostyka produkcji (Fly.io)` — **każde** zdarzenie `CLIENT_INVITED`,
  `CLIENT_INVITATION_RESENT` i `PASSWORD_RESET_SEND_FAILED` od 13.09 18:51 ma
  `"powod": "no_provider"`. Ostatnie: reset hasła właściciela 14.09 11:36.
  Wcześniejsze zaproszenia mają `doreczenie: "manual"` bez powodu (kod rozpoznał
  powód dopiero po rundzie diagnostyki 0.54.5).
* `Sprawdzenie SMTP (Fly.io)` — **kanał jest sprawny**: zmienne ustawione
  (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `MAIL_FROM`, hasło 90 znaków),
  DNS OK, TCP OK, baner Brevo, uwierzytelnienie przyjęte, TLS działa, `login: OK`.
* Przyczyna w kodzie: dwie drogi poczty czytają różne zmienne.
  `config.Settings` (używany przez `notifications_provider`: zaproszenia, reset
  hasła, przypomnienia) czytał wyłącznie `DZIK_SMTP_*`; `mailer` (kontrola kanału,
  wysyłka testowa, runda poczta-brevo) czyta `SMTP_*` / `MAIL_FROM`. Na produkcji
  ustawiono te drugie — stąd rozjazd: test poczty przechodził, zaproszenia nie.

## Co robię (minimalny hotfix, KOORDYNACJA §0 pkt 4)

Ustawienia poczty przyjmują obie nazwy: pierwszeństwo `DZIK_SMTP_*` (jawna
konfiguracja tej aplikacji), zapas `SMTP_*` / `MAIL_FROM`. Pusta zmienna
z prefiksem nie wygasza wspólnej. Brak obu = dostawca pusty, zachowanie bez zmian.

**Rezerwacje:** wersja 0.76.1 (0.77.0 należy do równoległej rundy wywiadu
kalorycznego — CHANGELOG 0.77.0 wejdzie NAD 0.76.1 po dociągnięciu `main`).
Bez migracji, bez zmian API, `export_version` bez zmian.

## Czego nie robię

* Nie dotykam sekretów na produkcji (nie odczytuję ani nie zmieniam wartości) —
  poprawka jest po stronie kodu, konfiguracja właściciela zostaje jak jest.
* Nie zmieniam treści e-maili, dostawcy ani domeny nadawcy.
* Nie włączam niczego poza tym, co właściciel już skonfigurował: bez zmiennych
  aplikacja nadal nie wysyła nic.

## Świadomy skutek

Po wdrożeniu aplikacja **zacznie faktycznie wysyłać** zaproszenia, przypomnienia
o zaległych raportach i linki resetu hasła na adresy istniejących kont — dotąd
trafiały do nikąd. To jest cel poprawki, ale warto o tym wiedzieć przed wdrożeniem.

## Weryfikacja

* 5 nowych testów (`test_poczta_jedna_konfiguracja.py`) + 44 istniejące testy poczty.
* Mutant: bez poprawki 4 z 5 nowych testów czerwone.
* Po wdrożeniu: ponowne wysłanie zaproszenia dla konta testowego i sprawdzenie
  w diagnostyce, że `powod` nie jest już „no_provider”.

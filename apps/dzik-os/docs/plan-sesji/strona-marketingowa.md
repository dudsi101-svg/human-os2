# Plan sesji: publiczna strona marketingowa + zapytania

**Gałąź:** `agent/strona-marketingowa` (od `main` = `a22bb74`)
**Rola:** aktywny piszący (polecenie właściciela, 24.08: „potrzebujemy
stronę internetową głównie marketingową, ale jeśli to korzystne — z innymi
funkcjami również")
**Cel:** wizytówka usług trenerskich pod tym samym adresem co aplikacja,
z jedną funkcją ponad marketing: formularzem zapytania, który trafia
do centrum powiadomień trenera.

## Zamiar

1. **Publiczna strona główna** (`frontend/src/pages/Landing.tsx`):
   niezalogowany gość na `/` widzi stronę marketingową (hero z logo,
   oferta współpracy, jak działa aplikacja, FAQ, kontakt, stopka
   z notą prywatności); zalogowany użytkownik na `/` widzi aplikację
   jak dotąd (żadnej zmiany dla klientów z zainstalowaną PWA).
   Nieznane ścieżki niezalogowanego dalej prowadzą do `/login`
   (E2E bez zmian). Treść po polsku, neutralna („trener personalny"),
   z miejscami do personalizacji przez właściciela (imię, cennik,
   zdjęcia) oznaczonymi w kodzie komentarzami.
2. **Formularz zapytania** — jedyna nowa funkcja backendu:
   `POST /api/public/lead` (imię, e-mail, opcjonalny telefon,
   wiadomość): walidacja długości, honeypot (pole `website` — bot
   dostaje 200 bez zapisu), limiter prób per IP (istniejący
   `LoginRateLimiter`), zapis jako powiadomienie zdarzeniowe dla
   wszystkich kont COACH (nowa kategoria `ZAPYTANIE` w
   `notifications.CATEGORIES`; kanały wg preferencji — e-mail
   neutralny jak wszędzie, szczegóły po zalogowaniu) + wpis audytu.
   Żadnej nowej tabeli, żadnej migracji.
3. Wpis `("POST", "/api/public/lead"): Access.PUBLIC` w macierzy
   dostępu; testy routera (walidacja, honeypot, limiter, powiadomienie
   ląduje u trenera).

## Mój obszar

- `backend/dzik_os/routers/public_site.py` (nowy), `main.py` (mount),
  `notifications.py` (kategoria `ZAPYTANIE`);
- `backend/tests/test_public_site.py` (nowy), `tests/access_matrix.py`
  (wpis PUBLIC);
- `frontend/src/pages/Landing.tsx` (nowy), `App.tsx` (routing `/` dla
  niezalogowanego), style w istniejącej konwencji;
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Czego nie dotykam

- logiki logowania/aktywacji, ekranów aplikacji, PWA manifestu, Core;
- żadnych modeli/migracji (lead = powiadomienie, nie nowa encja).

## Rezerwacje

- **Wersja: 0.49.0** (ostatnia: 0.48.0). **Migracja: brak.**

## Świadomie nie robię

- nie buduję CMS-a ani edycji treści z panelu — treść strony to kod;
  personalizacja (imię, zdjęcia, cennik) to szybka edycja pliku
  oznaczona komentarzami, a osobna decyzja produktowa, czy ma być
  edytowalna z aplikacji;
- nie dodaję analityki/śledzenia (zero ciasteczek marketingowych —
  spójnie z podejściem prywatnościowym aplikacji);
- nie robię osobnej domeny/hostingu — strona żyje pod adresem aplikacji
  (własna domena to `flyctl certs add`, decyzja właściciela).

## Weryfikacja (do wypełnienia)

- pełne bramki; uruchomienie na żywo: gość widzi stronę i wysyła
  zapytanie → powiadomienie w centrum trenera; zalogowany klient
  na `/` widzi aplikację bez zmian; honeypot i limiter sprawdzone.

# Plan sesji: zdarzenia resetu wg faktycznej wysyłki (audyt P0-4)

**Gałąź:** `agent/reset-uczciwe-zdarzenia` (od `main` = aktualny)
**Rola:** aktywny piszący (Sprint A audytu, pozycja A4)
**Cel:** audyt wewnętrzny przestaje twierdzić „link wysłany e-mailem",
zanim (i niezależnie od tego, czy) wysyłka się powiodła.

## Diagnoza (za audytem, potwierdzona)

`password_reset_request` tworzy token i zapisuje zdarzenie
`PASSWORD_RESET_REQUESTED` z podsumowaniem „link wysłany e-mailem"
PRZED wysyłką; wynik `send_email()` jest ignorowany. Dostawca `null`
i błąd SMTP zwracają False, a łańcuch audytu i tak twierdzi, że poszło.

## Zamiar

1. Rozdzielić stan: `PASSWORD_RESET_REQUESTED` (fakt żądania, bez
   twierdzeń o doręczeniu) zapisywany jak dotąd; po wywołaniu
   `send_email()` DRUGIE zdarzenie wg wyniku:
   `PASSWORD_RESET_LINK_SENT` (True) albo `PASSWORD_RESET_SEND_FAILED`
   (False — w payload nazwa dostawcy; przy `null` osobny powód
   `no_provider`). Metryka `observability.metrics` zliczająca porażki.
2. Odpowiedź HTTP bez zmian — generyczna zawsze (antyenumeracja,
   audyt to potwierdza jako słuszne).
3. Testy: sukces → REQUESTED+LINK_SENT; dostawca zwraca False →
   REQUESTED+SEND_FAILED; brak dostawcy (`null`) → SEND_FAILED
   z powodem no_provider; odpowiedź HTTP identyczna we wszystkich
   trzech przypadkach.

## Mój obszar

- `backend/dzik_os/routers/auth.py` (tylko `password_reset_request`),
  `backend/tests/test_reset_hasla_zdarzenia.py` (nowy);
- `docs/CHANGELOG.md` (0.53.4), `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Rezerwacje

- **Wersja: 0.53.4.** **Migracja: brak** (nowe akcje to stringi
  w istniejącym dzienniku zdarzeń).

## Weryfikacja (do wypełnienia)

- pełne bramki; trzy scenariusze testowe z asercją identycznej
  odpowiedzi HTTP.

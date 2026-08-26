# Plan sesji: UX pilotażu — wywiad przestaje być niewykrywalny (audyt Sprint B, pozycja B6)

**Gałąź:** `agent/zaproszenie-wywiad` (od `main` = 432dfbc)
**Rola:** aktywny piszący
**Cel:** przegląd krzyżowy odwrócił założenie audytu: wywiad nie jest
narzucany — jest schowany za linkiem trzeciego poziomu („Więcej"),
więc klient bez podpowiedzi trenera go nie znajdzie. Nawigacja klienta
jest już zredukowana (Dzisiaj/Plan/Dieta/Raport/Więcej — funkcje
poboczne siedzą pod „Więcej" od dawna), więc B6 sprowadza się do
zaproszenia we właściwym momencie + szczerości o skróconym scenariuszu
(ustalenie 10 przeglądu).

## Zamiar

1. **Kafelek zaproszenia na Dzisiaj**: pokazuje się, gdy klient ma
   wysłany co najmniej jeden raport tygodniowy, wywiad nigdy nie
   został zaczęty i karta rozmowy startowej nie wisi (kolejność:
   najpierw start, potem raport, potem wywiad — zgodnie z podpowiedzią
   z zakładki trenera „1–2 tydzień współpracy"). Dane z istniejących
   endpointów (`/checkins`, `/interview` → `session: null`);
   wzorzec „opcjonalna podpowiedź" jak przy rozmowie startowej
   (awaria fetcha = brak karty, nigdy błąd ekranu).
2. **Notka o skróconym scenariuszu** (ustalenie 10): w trakcie wywiadu,
   gdy plan nie zawiera modułu zdrowotnego (`gw_c1` poza
   `planned_steps`), ekran mówi wprost: część modułów jest wyłączona —
   brak przypisanego trenera albo cofnięta zgoda — i gdzie to zmienić.
   Dotąd klient widział po prostu „krótszy wywiad" bez słowa.
3. **E2E**: po wysłaniu raportu na Dzisiaj widać kafelek zaproszenia
   (rozszerzenie raport.spec).

## Świadomie nie robię

- żadnego wymuszania ani przekierowań — zaproszenie to karta do
  zamknięcia jednym tapnięciem w „Później" (stan lokalny sesji UI);
- backend bez zmian.

## Rezerwacje

- **Wersja: 0.53.12.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- tsc/build/helpers/E2E; zrzut kafelka.

# Plan sesji: przegląd krzyżowy wywiadu + poprawki blokujące (audyt Sprint B, pozycja B5)

**Gałąź:** `agent/przeglad-wywiadu` (od `main` = ee3b0d2)
**Rola:** aktywny piszący
**Cel:** niezależny przegląd krzyżowy rundy 0.53.0 „Głęboki wywiad"
(napisanej przez równoległą sesję, PR #29) wykazał trzy ustalenia
WYSOKIEJ wagi — wszystkie w jednym obszarze: treść odpowiedzi
zdrowotnej wycieka obok bramki zgód. Ta runda utrwala raport w repo
i domyka ustalenia blokujące.

## Zamiar

1. **`docs/PRZEGLAD_KRZYZOWY_WYWIADU_2026-08-26.md`** — pełny raport
   przeglądu (ustalenia z plik:linia, luki testowe, rekomendacje,
   werdykt), wzorem PRZEGLAD_KRZYZOWY_2026-08-18.md.
2. **Poprawka 1 (WYSOKA):** `routers/onboarding.py::_answer_out` —
   `safety_flagged`/`safety_signals` objęte tym samym filtrem zgód
   `allowed`, co treść odpowiedzi (oba przepływy: rozmowa i wywiad).
3. **Poprawka 2 (WYSOKA):** zdarzenie `*_SAFETY_FLAGGED` bez treści
   odpowiedzi — payload `{step_id, signal_count, source}` (łańcuch
   audytu jest niemutowalny i nie podlega usunięciu — nie wolno mu
   nieść danych zdrowotnych; wzorzec „zdarzenia bez treści").
4. **Poprawka 3 (WYSOKA):** `interview_flow.gw_i5` (pytanie otwarte
   „co trener powinien wiedzieć") oznaczone `sensitive=True`
   z domeną zdrowia — przestaje omijać zgody w kartach podpowiedzi.
5. **Poprawka 4 (ŚREDNIA/WYSOKA):** obietnica „zaznaczyliśmy to
   trenerowi" dostaje kanał: powiadomienie `notify_now` do trenera
   klienta przy pierwszym podniesieniu `safety_flag` sesji (treść
   bez danych zdrowotnych — tylko fakt i link do zakładki Wywiad).
6. Testy do każdej poprawki (w tym: sygnały niewidoczne bez zgody
   zdrowotnej w OBU przepływach; payload zdarzenia bez treści;
   gw_i5 za zgodą; powiadomienie powstaje raz).

## Świadomie nie robię

- pozostałe rekomendacje przeglądu (5–12: bramka SUMMARY_READY,
  przesiew gw_c3/gw_c6, warunkowość pogłębień, indeks współbieżności,
  odflagowanie, UX zaproszenia) — wypisane w raporcie, do kolejnych
  rund; częściowo pokryje je B6.

## Rezerwacje

- **Wersja: 0.53.10.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki pełne + nowe testy najpierw czerwone na starym kodzie.

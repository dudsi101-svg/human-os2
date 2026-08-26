# Przegląd krzyżowy rundy 0.53.0 „Głęboki wywiad" — 2026-08-26

**Zakres:** scalone `9654aba` (PR #29, gałąź `claude/ocena-projektu-dzik-os-76ercy`,
27 plików, +2653/−778), napisane przez równoległą sesję. Przegląd niezależny
(pozycja B5 planu poprawek po audycie zewnętrznym z 25.08), czysto czytający.
Odniesienia plik:linia wg stanu `main` = `ee3b0d2` sprzed rundy 0.53.10.

**Werdykt:** runda architektonicznie solidna — `build_router(FlowConfig)` to
prawidłowe uogólnienie, migracja 26 wzorowo addytywna i realnie wykonywana
w CI, izolacja klient–klient domknięta wykonawczą macierzą uprawnień,
deklaracja „zero AI" ma pokrycie w kodzie i w allowliście asystenta, eksport
i usunięcie danych obejmują wywiad automatycznie. **Blokowały trzy ustalenia
WYSOKIE — wszystkie w jednym obszarze: treść odpowiedzi zdrowotnej wyciekała
obok bramki zgód — plus jedna obietnica bez kanału doręczenia. Ustalenia 1–4
domknięte w rundzie 0.53.10** (ta sama gałąź co ten raport); pozostałe
pozycje wypisane niżej czekają na kolejne rundy.

## Ustalenia

| # | Waga | Co | Gdzie | Status |
|---|---|---|---|---|
| 1 | WYSOKA | `safety_signals`/`safety_flagged` zwracane bez filtra zgód — sygnał z `flag_options` to dosłowna treść odpowiedzi zdrowotnej, widoczna dla trenera mimo cofniętej zgody `dane_zdrowotne` (a `value` obok jest „ukryte") | `routers/onboarding.py::_answer_out` | **NAPRAWIONE 0.53.10** — sygnały objęte tym samym `allowed`, test w `test_przeglad_wywiadu.py` |
| 2 | WYSOKA | `gw_i5` (pytanie otwarte „co trener powinien wiedzieć") bez `sensitive`/`consent_domain` — najbardziej wyznaniowe pole wywiadu omijało zgody w kartach podpowiedzi trenera (`gw_otwarte` mapowane na 3 obszary w `coach_hints.py`) | `interview_flow.py` (gw_i5) | **NAPRAWIONE 0.53.10** — `sensitive=True`, domena zdrowia; propagacja przez `field_consent_domains()` (jedno źródło prawdy) |
| 3 | WYSOKA | Payload zdarzenia `*_SAFETY_FLAGGED` niósł dosłowną treść odpowiedzi — a łańcuch audytu jest niemutowalny i nie podlega usunięciu konta: dane zdrowotne zostawały na zawsze | `routers/onboarding.py` (answer) | **NAPRAWIONE 0.53.10** — payload `{step_id, signal_count, source}`; treść tylko w bazie operacyjnej (usuwalnej) |
| 4 | ŚR/WYS | Komunikat do klienta obiecuje „zaznaczyliśmy tę odpowiedź trenerowi", a żaden kanał nie istniał (flaga sesji + metryka; zero powiadomień, zero znacznika na liście podopiecznych) | `interview_flow.FLAG_MESSAGE_PRESCREEN` | **NAPRAWIONE 0.53.10** — powiadomienie `PRZESIEW` do trenera przy pierwszym podniesieniu flagi sesji (dedup po sesji, bez danych zdrowotnych w treści) |
| 5 | ŚREDNIA | Flaga sesji jednokierunkowa: korekta odpowiedzi nie zdejmuje `safety_flag`, a historyczna błędna wersja dalej wraca w `answers` | `routers/onboarding.py` | OTWARTE — rekomendacja: przeliczanie flagi z bieżących wersji |
| 6 | ŚREDNIA | Przesiew słów kluczowych pokrywa 4 z ~20 pól tekstowych — poza nim m.in. `gw_c3` (leki) i `gw_c6` (ciąża!), mimo że moduł C reklamuje się jako PAR-Q | `interview_flow.py` | OTWARTE — włączyć `scan_safety` na `gw_c3`, `gw_c6` (+rozważyć `gw_e2_kiedy`, `gw_e4`, `gw_f1`) |
| 7 | ŚREDNIA | Pogłębienia niewarunkowe wbrew „regule adaptacji": `gw_a2_powod` pytane bez kotwicy (nawet przy pominiętym `gw_a2`), `gw_d2_opis` przy „budzę się wypoczęty", `gw_e1_zrodlo` przy „spokojnie" | `interview_flow.py`, `deep_triggered` | OTWARTE |
| 8 | ŚREDNIA | `client_approve` nie wymaga `SUMMARY_READY` — sekwencja `summary → answer (poprawka) → approve` cicho zapisuje do profilu wartości sprzed poprawki; `build_summary` działa też po `CLIENT_APPROVED` | `routers/onboarding.py` | OTWARTE — `409` gdy status ≠ SUMMARY_READY |
| 9 | ŚREDNIA | Wyścigi: dwa równoległe `POST /start` tworzą dwie sesje (brak indeksu częściowego/idempotencji); kolizja wersji przy równoległym `POST /answer` kończy się 500 zamiast 409 (brak handlera `IntegrityError`) | `routers/onboarding.py`, `models.py`, `main.py` | OTWARTE (odziedziczone z rozmowy startowej) |
| 10 | NIS/ŚR | Klient bez trenera lub bez zgód przechodzi wywiad okrojony (15 zamiast 46 pytań) bez żadnego wyjaśnienia w UI; zapis własnej deklaracji zdrowotnej zależy od uprawnień trenera do zapisu | `allowed_domains`, frontend | OTWARTE — komunikat w UI; do rozważenia z B6 |
| 11 | — | Pozytywy: macierz dostępów wykonawcza (10 tras + hints jako CLIENT_SCOPED), „zero AI" strukturalnie (`ai_enabled=False` + brak pól `gw_*` w allowliście asystenta), migracja 26 czysta i testowana DDL-em, wznowienie po przeładowaniu serwerowe, logi/metryki bez PII, eksport/usunięcie obejmują wywiad | — | — |
| 12 | NISKA | Drobiazgi: `_require_coach` w `/review` pozorny (GET /interview daje to samo bez roli); `flag_options` rozdzielane po przecinku (krucho przy opcji z przecinkiem); `POST /pause` to atrapa; rozjazd `server_default` świeża-vs-migrowana baza; `gw_h1` dubluje Pomiary wolnym tekstem | różne | OTWARTE |

## Luki testowe (do domknięcia; ✔ = domknięte w 0.53.10)

1. ✔ Trener bez zgody zdrowotnej nie widzi `safety_signals`.
2. „Zero AI" dowiedzione tylko deklaratywnie — brak testu z podstawionym
   dostawcą i zgodą `funkcje_ai`, asertującego zero wywołań.
3. Wersjonowanie odpowiedzi w wywiadzie (poprawka → v2, profil dostaje bieżącą).
4. Zachowanie flagi po korekcie oflagowanej odpowiedzi (ustalenie 5).
5. Ścieżka trenera do końca (`coach-approve`: 409 przed zatwierdzeniem klienta).
6. Nieaktualne podsumowanie: `summary → answer → approve` (ustalenie 8).
7. Klient bez przypisanego trenera (ustalenie 10).
8. `pause → start` i wypadnięcie bieżącego kroku z planu (`_refresh_current_step`).
9. Współbieżność: dwa `POST /start`, kolizja wersji przy `POST /answer`.
10. Migracja 26: asercja, że wiersz sprzed migracji czyta się jako `'start'`.
11. Prywatność: eksport/usunięcie sesji wywiadu (kod obejmuje — testów brak).
12. ✔ (częściowo) Strażnik treści zdarzenia audytowego; nadal brak strażnika
    „żadne pole `gw_*` w `coach_assistant.CLIENT_FIELD_KEYS`".

## Rekomendacje — kolejność

1–4: wykonane w 0.53.10. Następnie (przed skalowaniem powyżej kilku
klientów): ustalenia 8 i 9 oraz luki testowe 2, 6, 9, 11; przesiew `gw_c3`/
`gw_c6` (ustalenie 6) i warunkowość pogłębień (7) — najlepiej razem z B6
(zaproszenie do wywiadu po pierwszym raporcie zamiast linku trzeciego
poziomu; dziś ryzykiem nie jest narzucanie wywiadu, tylko jego
niewykrywalność).

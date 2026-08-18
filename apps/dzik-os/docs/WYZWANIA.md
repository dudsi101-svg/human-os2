# Wspólne wyzwania — model, prywatność i zgodność z konstytucją Human OS

Dokument opisuje moduł wspólnych wyzwań (0.18.0, PROMPT 16): model danych,
zasady prywatności, interpretację konstytucyjną (ranking opt-in), naliczanie
wyników, moderację oraz plan wycofania migracji nr 16.

Moduł jest **PRYWATNY**: istnieją wyłącznie wyzwania tylko-dla-zaproszonych.
Publicznych wyzwań, katalogów, wyszukiwarki ani żadnej formy portalu
społecznościowego **nie ma** — funkcja wspiera motywację, nie zmienia
aplikacji w medium społecznościowe.

## 1. Interpretacja konstytucyjna (ranking opt-in)

Konstytucja Human OS zakazuje **rankingowania ludzi i porównań między
osobami jako mechanizmu domyślnego** (system nigdy nie ocenia wartości
człowieka; punktem odniesienia jest własna historia — patrz też
`routers/records.py`). Wymaganie produktowe „wspólne wyzwania z możliwością
wyłączenia rankingu i ukrycia wyniku" pogodzono z konstytucją tak:

* **Domyślny widok** każdego uczestnika to: własny postęp względem celu
  wyzwania + **zagregowany** postęp grupy bez nazwisk (liczba osób, suma,
  średni % celu). Zero porównań jednostkowych bez decyzji ludzi.
* **Widoczność wyniku jednostkowego** (`share_result`) jest per uczestnik,
  **domyślnie WYŁĄCZONA** i odwracalna w każdej chwili (ukrycie działa
  natychmiast).
* **Ranking** (`ranking_opt_in`) jest OSOBNĄ świadomą decyzją, domyślnie
  WYŁĄCZONĄ; obejmuje wyłącznie osoby z podwójnym opt-in
  (`share_result` + `ranking_opt_in`). Uczestnik, który rankingu nie
  włączył, nigdzie w żadnym rankingu nie występuje.
* **Pseudonim per wyzwanie** (`alias`) — uczestnik sam decyduje, jak się
  podpisze; domyślnie imię z konta, zmienialny w każdej chwili.
* Wyniki nie są żadną metryką wartości osoby; trener NIE widzi ukrytych
  wyników jednostkowych (tylko agregat + statusy udziału).

## 2. Model danych (migracja nr 16 — wyłącznie nowe tabele)

* **`challenges`** — organizator (`organizer_id`), rodzaj
  (`INDIVIDUAL` = sam ze sobą / `GROUP` = klienci tego samego trenera,
  prowadzone przez trenera), tytuł, zasady (`description`), **neutralna
  jednostka** (`unit`), cel (`goal_value`), okno `starts_on`/`ends_on`,
  **strefa czasowa wyzwania** (`timezone`), `visibility` (zawsze
  `INVITE_ONLY`), status `DRAFT/ACTIVE/FINISHED/CANCELLED`, limit
  wpisów/dzień, flaga `aggregates_adjusted` (patrz §7).
* **`challenge_participants`** — udział: status
  `INVITED/ACTIVE/DECLINED/LEFT/REMOVED/WITHDRAWN`, `alias`,
  `share_result` (domyślnie 0), `ranking_opt_in` (domyślnie 0),
  `auto_count_workouts` (świadoma decyzja przy dołączaniu), pełne
  znaczniki czasowe decyzji. Unikalność (wyzwanie, użytkownik).
* **`challenge_entries`** — wpisy wyników: data dnia (wg strefy wyzwania),
  wartość, opcjonalna notatka (jedyny wolny tekst — moderowalny), źródło
  `MANUAL/WORKOUT`, `workout_session_id` (jawne wskazanie własnego
  treningu; unikalne per wyzwanie), `client_entry_id` (idempotencja
  ponowień; unikalne per uczestnik), status `ACTIVE/CORRECTED` +
  `corrects_entry_id` (łańcuch korekt — historia nigdy nie jest
  nadpisywana).
* **`challenge_blocks`** — blokada między uczestnikami (obustronna
  niewidoczność aliasów/wyników; agregat grupy bez zmian).
* **`challenge_reports`** — zgłoszenia do organizatora: powód, status,
  rozstrzygnięcie (`REMOVED/ALIAS_RESET/NOTES_CLEARED/DISMISSED`).

## 3. Dane zdrowotne — twarda granica

Dane zdrowotne **w ogóle nie wchodzą** do modułu wyzwań:

* Jednostki wyniku to zamknięta allowlista `NEUTRAL_UNITS`
  (`treningi`, `minuty`, `aktywnosci`). Masa ciała, obwody, kalorie,
  parametry raportów — nie istnieją jako jednostka; próba użycia = 422
  z jednoznacznym komunikatem.
* Moduł nie ma żadnej ścieżki odczytu pomiarów, zdjęć, raportów, dziennika
  bólu, obserwacji, żywienia ani dokumentów. Jedyna integracja to
  **licznik ukończonych treningów** (data + fakt „DONE"), i to wyłącznie
  po świadomej decyzji uczestnika (§4).
* Jedyny wolny tekst wpisu to krótka notatka (200 znaków) — widoczna tylko
  tam, gdzie widoczny jest wynik, i moderowalna przez organizatora.
* Push z wyzwań jest neutralny (bez tytułu wyzwania, aliasów i wyników) —
  ten sam standard co reszta aplikacji.
* Audyt wyzwań niesie wyłącznie identyfikatory, liczniki i flagi — nigdy
  aliasy, notatki ani treści zgłoszeń (test `test_push_is_neutral_no_content`).

## 4. Naliczanie wyników (uczciwe liczenie)

Wynik uczestnika = suma AKTYWNYCH wpisów + (opcjonalnie) automatycznie
zaliczone treningi. Wynik liczy się **wyłącznie z danych świadomie
przeznaczonych do wyzwania** — trzy jawne ścieżki:

1. **Wpis ręczny** — oznaczany `source=MANUAL` i tak prezentowany
   („zawiera wpisy ręczne" przy udostępnionym wyniku).
2. **Jawne wskazanie własnego treningu** (`workout_session_id`) — jeden
   trening da się zgłosić raz (unikalny indeks; powtórka zwraca
   `duplicate: true`, nie drugi wpis).
3. **„Zaliczaj moje odhaczone treningi"** (`auto_count_workouts`) —
   kategoria źródłowa zaznaczana przy dołączaniu (lub później, jawnie);
   liczone są RÓŻNE dni z treningiem `DONE` w oknie wyzwania (dwa treningi
   jednego dnia = 1). Przy włączonym auto wpisy ręczne i wskazywanie
   treningów są zablokowane (409), a włączenie auto przy istniejących
   wpisach — również 409: **podwójne naliczanie jest strukturalnie
   niemożliwe**. Dostępne tylko dla jednostki `treningi`.

Zabezpieczenia:

* **Idempotencja** — `client_entry_id` z urządzenia (UUID): retry po
  utracie sieci/podwójne kliknięcie zwraca istniejący wpis.
* **Dzień wg strefy WYZWANIA** — `challenges.timezone` (domyślnie
  `DZIK_TZ`); data wpisu jest walidowana względem „dziś" i okna wyzwania
  w tej strefie, niezależnie od strefy urządzenia uczestnika.
* **Korekty z historią** — korekta tworzy nowy wiersz wskazujący stary
  (`corrects_entry_id`); stary dostaje status `CORRECTED` i pozostaje
  w historii uczestnika oraz w audycie (stara i nowa wartość).
* **Ochrona przed nadużyciami** — limit wpisów/dzień
  (`max_entries_per_day`, 1–20), zakres wartości per jednostka
  (`max_value`, np. minuty ≤ 600; `treningi`/`aktywnosci` zawsze 1),
  zakaz dat przyszłych i spoza okna.
* **Zamrożenie po zakończeniu** — w wyzwaniu `FINISHED` nie można dodawać
  wpisów ani korekt (422); podsumowanie pozostaje widoczne.

## 5. Uczestnictwo i cykl życia

* Grupowe: trener tworzy szkic → zaprasza WYŁĄCZNIE aktywnie prowadzonych
  klientów → aktywuje. Zaproszony przed decyzją widzi tylko zapowiedź
  (tytuł, zasady, jednostka, daty) + **wyjaśnienie widoczności** („kto
  zobaczy jaki wynik") i decyduje: przyjmuję (z wyborem aliasu i
  ustawień) / odrzucam. Indywidualne: klient tworzy dla siebie, od razu
  aktywne, nikt inny (nawet trener) go nie widzi.
* Uczestnik w każdej chwili może: ukryć wynik, wyłączyć ranking, zmienić
  pseudonim, **opuścić** wyzwanie (`LEFT` — znika z widoków, dane czekają
  na jego decyzję) albo **trwale wycofać udział** (§7).
* Osoba spoza wyzwania na każdej ścieżce dostaje 404 (logowana odmowa
  `ACCESS_DENIED` — wzorzec IDOR z `authz.py`; nie ujawniamy istnienia
  wyzwania).

## 6. Moderacja (organizator + audyt)

* Organizator moderuje **wyłącznie wyzwania, które prowadzi**
  (`require_owned_resource(owner_attr="organizer_id")`; cudze = 404).
* Narzędzia: usunięcie uczestnika (`REMOVED`), neutralizacja pseudonimu
  (na „Uczestnik"), usunięcie treści notatek wpisów zgłoszonej osoby,
  oddalenie zgłoszenia. Wszystko audytowane (id + rozstrzygnięcie, bez
  treści).
* Zgłoszenia: każdy aktywny uczestnik może zgłosić innego uczestnika
  (treść zgłoszenia widzi tylko organizator) oraz **zablokować** go
  (obustronna niewidoczność wyników/aliasów; agregat bez zmian).
* Trener NIE dostaje przy moderacji wglądu w ukryte wyniki — działa na
  poziomie uczestników i treści (pseudonim/notatki), nie liczb.

## 7. Trwałe wycofanie udziału i usunięcie konta

* `POST /challenges/{id}/withdraw`: wpisy uczestnika są **fizycznie
  usuwane**, pseudonim anonimizowany, ustawienia zerowane, status
  `WITHDRAWN`. Wyzwanie dostaje trwałą flagę `aggregates_adjusted` —
  sumy grupy są od tej pory jawnie prezentowane jako „skorygowane".
  **Integralność historii zapewnia audyt** (zdarzenie
  `CHALLENGE_WITHDRAWN` z licznikiem usuniętych wpisów), nie trzymanie
  danych osoby.
* Usunięcie konta (`/api/me/deletion-request`) wykonuje to samo dla
  wszystkich udziałów, anuluje wyzwania organizowane przez usuwane konto
  (z anonimizacją tytułu/zasad), anonimizuje treść zgłoszeń autorstwa
  usuwanej osoby i usuwa jej blokady.
* Eksport danych (`export_version` 1.3) zawiera udziały i wpisy
  użytkownika (`challenge_participations`, `challenge_entries`) — nigdy
  dane innych uczestników.

## 8. Nic nie wychodzi poza zamkniętą grupę

Wyniki, aliasy i agregaty istnieją wyłącznie wewnątrz zamkniętej grupy
wyzwania. **Publikowanie czegokolwiek na zewnątrz (np. strona trenera,
media społecznościowe) NIE jest zaimplementowane** — wymagałoby nowej,
odrębnej kategorii zgody w `consent_catalog.py` (świadomy opt-in per
uczestnik, per wyzwanie, z opisem odbiorców i zakresu) oraz osobnej rundy
projektowej. Zaznaczamy to tu celowo: żaden istniejący endpoint nie
umożliwia wyprowadzenia danych wyzwania poza jego uczestników i
organizatora.

Uczestnictwo w wyzwaniu nie wymaga nowej kategorii zgody RODO: przyjęcie
zaproszenia jest samo w sobie świadomą, poinformowaną decyzją (ekran
zaproszenia zawiera pełne wyjaśnienie widoczności), a moduł nie przetwarza
danych szczególnej kategorii (art. 9). Decyzja „zaliczaj odhaczone
treningi" jest rejestrowana per wyzwanie na wierszu uczestnika i w audycie.

## 9. Powiadomienia

Push przy: zaproszeniu, zakończeniu i odwołaniu wyzwania oraz nowym
zgłoszeniu (do organizatora). Treść zawsze neutralna — bez tytułu
wyzwania, aliasów i wyników. Kanał push sam w sobie jest opt-in (kategoria
zgody `przypomnienia`; bez subskrypcji nic nie wychodzi).

**Punkt integracji (P13):** w drzewie nie ma jeszcze centralnego modelu
powiadomień z preferencjami i cichymi godzinami. Wysyłki idą przez
`push_service.send_to_user` (jak konsultacje/wiadomości). Gdy powstanie
model preferencji P13, wywołania z `routers/challenges.py` należy
przepiąć na jego bramkę (kategoria proponowana: `wyzwania`, respektująca
ciche godziny) — miejsca wywołań: zaproszenie, zakończenie, odwołanie,
zgłoszenie.

## 10. Plan wycofania migracji nr 16

Migracja jest czysto addytywna (5 nowych tabel + indeksy; zero ALTER-ów
istniejących tabel), więc wycofanie nie dotyka żadnych danych spoza
modułu:

1. Wyłączyć router: usunąć `challenges.router` z `main.py` (moduł przestaje
   istnieć w API; frontend pokazuje błąd „Nie znaleziono" tylko w sekcji
   Wyzwania).
2. Opcjonalnie zachować dane: pozostawić tabele (nieużywane, nic ich nie
   czyta) — zalecane przy tymczasowym wyłączeniu.
3. Pełne usunięcie: `DROP TABLE challenge_reports, challenge_blocks,
   challenge_entries, challenge_participants, challenges;` oraz
   `DELETE FROM schema_migrations WHERE version = 16;`.
4. Zdarzenia audytowe `CHALLENGE_*` w łańcuchu Human OS pozostają — łańcuch
   jest append-only i nie podlega wycofaniu (zawiera wyłącznie
   identyfikatory i liczniki).
5. Frontend: usunąć trasy `/wyzwania` i `/trener/wyzwania` z `App.tsx`,
   linki z `More.tsx`, pliki `pages/client/Challenges.tsx`,
   `pages/coach/Challenges.tsx` i typy `Challenge*` z `types.ts`.

## 11. Macierz dostępu (skrót)

| Kto | Co widzi / może |
|---|---|
| Uczestnik ACTIVE | własny postęp + historia wpisów; agregat grupy bez nazwisk; wyniki osób, które je udostępniły (minus blokady); wpisy/korekty; ustawienia widoczności; opuszczenie/wycofanie; blokada/zgłoszenie |
| Zaproszony (INVITED) | zapowiedź wyzwania + wyjaśnienie widoczności; przyjęcie/odrzucenie |
| Organizator (trener) | pola wyzwania, agregat, lista uczestników (alias+status, bez ukrytych wyników), wyniki udostępnione, zgłoszenia i moderacja, cykl życia; wyłącznie WŁASNE wyzwania |
| Właściciel wyzwania indywidualnego | pełny dostęp do własnego wyzwania; nikt inny go nie widzi |
| Osoba z zewnątrz / obcy trener / DECLINED / LEFT / REMOVED / WITHDRAWN | 404 (logowana odmowa zasobowa) |

Testy: `backend/tests/test_challenges.py` (20 testów — zaproszenie, odmowa,
opuszczenie, ukrycie wyniku, 404 z zewnątrz, korekta, strefa czasowa,
zakończenie, blokada, wycofanie, ranking podwójnego opt-in, idempotencja,
auto-zaliczanie, neutralny push/audyt, usunięcie konta, eksport) plus
rozszerzony test migracji v1→…→16.

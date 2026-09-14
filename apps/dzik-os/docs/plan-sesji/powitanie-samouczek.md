# Plan sesji: powitanie po pierwszym logowaniu — dwuetapowy samouczek (0.70.0)

**Gałąź:** `agent/powitanie-samouczek` (od `main` = 35a3168, po 0.67.0). **Rola:** podległa
sesja pisząca wyznaczona przez integratora (zarządzenie właściciela z 14.09,
`KOORDYNACJA.md` §0: wiele zadań jednego piszącego, każde w osobnym worktree i osobnym
PR `[WRITER]`; równolegle otwarty jest `[WRITER]` PR #69 `agent/wymiany-produktow` — inna
sekcja tych samych plików współdzielonych, patrz rezerwacje niżej). **Źródło:** polecenie
właściciela z 14.09, sekcja E promptu „Panel Dzisiaj” — jedyna część niewykonana w 0.63.0.

**Rezerwacje (KOORDYNACJA §0):** wersja **0.70.0** (0.68.0 = dni treningowe, 0.69.0 =
wymiany produktów w PR #69; jeśli w chwili pushu `main` ma już 0.69.0 — scalam `main`
i zostawiam 0.70.0 na górze), migracja **37** (addytywna: `users.welcome_seen_at`).
Zlecenie „dni treningowe” (`docs/zlecenia/README.md`) przesuwa się z 37 na **38** —
odnotowane tam („przesunięte, prompt nieprzesłany”). Pliki współdzielone, których
dotykam (tylko własna sekcja): `models.py` (klasa `User`, jedno pole), `db.py` (wpis 37 na
końcu listy), `routers/today.py` (nowa trasa + jedno pole w słowniku), `access_matrix.py`
(jedna trasa w bloku `/api/me/*`), `seed.py` (znacznik dla kont demo), `types.ts`
(`TodayData`), `CHANGELOG.md` (sekcja 0.70.0 na górze), `STAN_PRZEKAZANIA.md` §2 (wiersz
gałęzi). Nie dotykam: `main.py` (router `today` jest już zarejestrowany), nawigacji
(`components.tsx` Nav), `privacy.py`, Core (`hos_engine/`, `tests/` w korzeniu),
integracji, AI, klucza szyfrowania, zgód i danych.

## Cel

Klient logujący się po raz pierwszy dostaje **pomoc, nie bramkę**: dwuetapowe okno
powitalne (krok 1 — co to za miejsce, zgody i wywiady; krok 2 — co jeszcze warto wiedzieć),
pomijalne w każdej chwili (Esc = „Pomiń na razie”), niczego nie blokujące, ponownie
otwieralne z „Więcej → Pomoc / Samouczek”. Znacznik obejrzenia trzymany **na serwerze**
(`users.welcome_seen_at`), nie w `localStorage` — ma działać między urządzeniami.

## Test INTENDED_PURPOSE §3

Samouczek to **informacja o funkcjach aplikacji**: nie zbiera żadnych danych, nie zadaje
pytań, nie interpretuje niczego o kliencie, nie wymusza decyzji (zgody i wywiady
wyłącznie *wskazuje* z odnośnikami; decyzja zapada tam, gdzie dotąd — Profil → „Prywatność
i zgody”, zakładka „Wywiad”). Jedyny zapis: data pierwszego zamknięcia okna
(`welcome_seen_at`) — znacznik UI o tym samym charakterze co `last_login_at`. Wynik: bez
wątpliwości, brak pytania do właściciela.

**Eksport danych (`/api/me/export`):** `welcome_seen_at` **nie wchodzi** do eksportu
i `export_version` zostaje `1.9`. Uzasadnienie: to znacznik stanu interfejsu („okno
powitalne zamknięte”), nie dane osobowe treści — dokładnie jak `last_login_at`,
`must_change_password` czy `timezone`, których eksport sekcji `user` również nie zawiera
(świadomie: `id`, `email`, `display_name`, `identity_id`, `created_at`). Usunięcie konta
i anonimizacja bez zmian (kolumna zostaje przy rekordzie, nie identyfikuje osoby).

## Etapy (co czytam → co wytwarzam → jak weryfikuję)

| Etap | Czytam | Wytwarzam | Weryfikacja |
|---|---|---|---|
| 0 rozpoznanie | `today.py`, `Today.tsx`, `More.tsx`, `components.tsx` (Nav), `App.tsx`, `Profile.tsx` (nagłówek „Prywatność i zgody”), `DietaSzablon.tsx` („↔ wymień”), `Thread.tsx` (nagranie głosowe, załączniki wideo), `db.py` (wpis 14: `ALTER TABLE users ADD COLUMN … VARCHAR`), `seed.py`, `conftest.py`, `access_matrix.py`, `privacy.py`, `helpers.ts`, `nawyki.spec.ts`, `test_a11y.mjs` | ten plan | — |
| 1 backend | — | migracja 37, pole `User.welcome_seen_at`, `POST /api/me/welcome-seen` (zalogowany; idempotentny — drugie wywołanie nie zmienia daty; zwraca `{"welcome_seen": true, "welcome_seen_at": …}`), `welcome_seen: bool` w `GET /api/me/today`, wpis w macierzy dostępu, seed: znacznik dla wszystkich kont demo klientów (żeby istniejące E2E i demo nie dostały nagle okna) | `tests/test_powitanie.py`: świeżo aktywowany klient → `welcome_seen` false; POST ustawia znacznik; drugie wywołanie nie zmienia daty; po POST `today.welcome_seen` true; anonim → 401; konta demo z seedu mają znacznik; eksport bez pola i `export_version` 1.9; macierz dostępu, migracje przenośne |
| 2 frontend | — | `pages/client/Powitanie.tsx`: `role="dialog"`, `aria-modal`, `aria-labelledby` (h2 kroku), fokus-trap Tab/Shift+Tab, Esc = Pomiń, przyciski `<button>`, style `.card`/`.btn`/`.btn--ghost` + mała warstwa `.powitanie-tlo`/`.powitanie-okno` w `styles.css`; `Today.tsx` pokazuje okno gdy `!today.welcome_seen` (po załadowaniu danych), „Pomiń na razie”/„Rozumiem, zaczynajmy” → POST i zamknięcie; `More.tsx`: karta „Pomoc / Samouczek” otwiera to samo okno **bez POST-a**; etykieta zakładki Postępy/Raport wg `hasFeature("monitoring_tab")`; imię z `greeting_name` (Dzisiaj) / pierwszego członu `display_name` (Więcej) | `tsc --noEmit`, `npm run build` (budżet 120 kB gzip), `test:helpers` |
| 3 E2E + uruchomienie | — | `e2e/powitanie.spec.ts` (projekt `telefon`): konto klienta utworzone przez API (zaproszenie → aktywacja, jak `create_activated_client` w backendzie) → logowanie formularzem → brama zgód → „Dzisiaj” z oknem (h2 kroku 1) → „Dalej” → krok 2 → fokus-trap (Tab z ostatniego przycisku wraca do pierwszego) → „Rozumiem, zaczynajmy” → po reload okna nie ma → `/wiecej` → „Pomoc / Samouczek” otwiera okno → Esc zamyka; a11y (`test_a11y.mjs` — klient A ze znacznikiem: bez okna, kontrakty „Dzisiaj” nienaruszone), PWA offline; obejrzenie przez serwer E2E ze zrzutami | Playwright `powitanie nawyki dieta-szablon --project=telefon` na porcie 8095; skrypty a11y i PWA; zrzuty poza repo |
| 4 zamknięcie | — | CHANGELOG 0.70.0, wersje (package.json, pyproject, `__init__`, README, RELEASE_STATUS), PERMISSIONS, INSTRUKCJA_KLIENTA, STAN_PRZEKAZANIA §2, zlecenia/README, ten plan (Odstępstwa / Weryfikacja / Plan kontra rzeczywistość) | ruff, pełny pytest backendu, Core 275, `spojnosc.py`, `mutacje.py`, `mutacje_bezpieczenstwa.py` |

## Treść okna (dostosowana do `main` 0.67.0)

* Nawigacja klienta na dole: Dzisiaj, Plan, Dieta, Raport (albo Postępy, gdy trener
  włączy moduł — etykieta z flagi, bez obiecywania „Postępów” przy wyłączonej), Więcej.
* Zgody: „Więcej → Profil, zgody i moje dane → Prywatność i zgody” (nagłówek `h2`
  w `Profile.tsx`). Wywiady: zakładka „Wywiad” (`/wywiad`, z „Więcej”).
* Krok 2 opisuje **wyłącznie funkcje istniejące na `main`**: wymiana składnika
  („↔ wymień” w Dieta — dla diety z szablonu), zapisywanie wagi/obwodów/wyników
  (Raport lub Postępy wg flagi), opisy techniki ćwiczeń (Wiedza), zdjęcia sylwetki
  w raporcie tygodniowym, **nagranie w wiadomości** (Wiadomości mają nagranie głosowe
  i załączniki wideo mp4 — zdanie złagodzone: „nagraj krótkie nagranie i wyślij
  w wiadomości”; obsługi wideo w tej rundzie nie dodaję).

## Czego nie robię

Nie zmieniam nawigacji, bramy zgód, wywiadów, wiadomości (bez nowej obsługi wideo),
eksportu (bez podbicia `export_version`), Core. Nie używam `localStorage` na znacznik.
Nie scalam PR-a, nie robię force-pusha, nie ruszam integracji/AI/klucza.

## Odstępstwa od planu

* **Port drugiego serwera E2E:** konfiguracja Playwrighta zawsze podnosi drugi serwer
  na `PORT + 1`; 8096 zajmował cudzy serwer innej sesji (od 03:39, nie zabijany).
  Zamiast zmieniać przydzielony port 8095, `playwright.config.ts` dostał zmienną
  `DZIK_E2E_PORT_POSTEPY` (domyślnie nadal `PORT + 1`) — narzędzie zostawione lepsze
  (Karta §VIII), zachowanie CI bez zmian.
* **Treść kroku 2 — wymiana składnika:** na `main` wymiany istnieją wyłącznie w diecie
  z szablonu (moduł za flagą `DZIK_DIET_TEMPLATES_ENABLED`, na produkcji wyłączony;
  flaga nie jest widoczna dla frontendu przy logowaniu — tylko `monitoring_tab`).
  Zdanie sformułowane warunkowo („gdy trener przypisze Ci dietę z szablonu…”) zamiast
  usuwać punkt z polecenia — pytanie do właściciela w STAN §2 i w PR.
* **„Postępy” przy wyłączonej fladze:** zamiast obiecywać zakładkę, krok 2 wskazuje
  istniejącą ścieżkę „Więcej → Monitoring i postępy” (przy włączonej fladze — zakładkę
  „Postępy”, a raport w „Więcej → Raport tygodniowy”).
* **Nagranie do trenera:** zdanie złagodzone do „nagraj krótkie nagranie i wyślij
  trenerowi w wiadomości” (Wiadomości mają nagranie głosowe i załączniki wideo mp4);
  obsługi wideo nie dodano.
* **Scalenie `main` w trakcie rundy:** PR #69 (0.69.0) wszedł na `main` przed pierwszym
  pushem kodu — scalony bez konfliktów (commit scalający), wszystkie bramki powtórzone
  na scalonym drzewie.
* **Bez zdarzenia audytu** przy `POST /api/me/welcome-seen`: to stan interfejsu, nie
  decyzja o danych (jak `last_login_at`) — świadomie, żeby nie zaśmiecać audytu.

## Weryfikacja wykonana

* Backend: `tests/test_powitanie.py` 3 testy (świeży klient bez znacznika + idempotencja
  + `today.welcome_seen`; anonim 401 + konta demo; eksport bez pola, `export_version`
  1.9); macierz dostępu, migracje przenośne (SQLite), `test_db_migracje`, nawyki,
  onboarding, prywatność — zielone. Pełny zestaw backendu: patrz PR (liczba po
  ostatnim przebiegu na scalonym drzewie). Core: 275/275. `ruff` czysto.
* Frontend: `tsc` czysto, build 90,4 kB gzip (budżet 120), `test:helpers` 142/142.
* E2E (projekt `telefon`, port 8095): 27/27, w tym `powitanie.spec.ts` (konto przez API
  → brama zgód → krok 1 → krok 2 → pułapka fokusu w obu krokach → reload bez okna →
  „Więcej → Pomoc / Samouczek” → Esc). `test_a11y.mjs` i `test_pwa_offline.mjs`:
  wszystkie kontrole przeszły (klient A ze znacznikiem — kontrakty „Dzisiaj”
  nienaruszone).
* `tools/spojnosc.py`: czysto (13 kontroli, 1 uwaga — otwarta konsultacja K-001 sprzed
  rundy). Przeglądy mutacyjne: wynik w PR.
* **Uruchomienie (ZASADA_URUCHOMIENIA):** serwer E2E na 8095, konto „Kasia Zrzutowa”
  utworzone przez API (201/200), logowanie formularzem, brama zgód, na „Dzisiaj” okno
  kroku 1 z fokusem na `h2`, „Dalej” → krok 2 (bez poziomego scrolla 375 px),
  „Rozumiem, zaczynajmy” → 0 dialogów; po odświeżeniu 0 dialogów, `GET /api/me/today`
  przez sieć: `welcome_seen: true`; „Więcej → Pomoc / Samouczek” otwiera okno, Esc
  zamyka; widok 1024 px — okno wyśrodkowane; 0 błędów JS w konsoli. Sześć zrzutów
  poza repo (scratchpad `powitanie-zrzuty/`).

## Plan kontra rzeczywistość

Plan: 4 etapy, jeden komponent, znacznik na serwerze. Rzeczywistość: zgodnie z planem;
bez podagentów. Nieprzewidziane: zajęty port sąsiedni (rozwiązane konfiguracją, nie
zabijaniem cudzych procesów) i scalenie `main` w trakcie (bez konfliktów). Usprawnienie
na następny raz: przy kilku sesjach na jednej maszynie przydzielać od razu **parę**
portów E2E (Playwright podnosi dwa serwery).

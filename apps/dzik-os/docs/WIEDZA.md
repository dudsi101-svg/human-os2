# Wiedza — raport wdrożenia P0 (0.56.0)

**Źródło:** pakiet właściciela „PAKIET_WIEDZA_DLA_CLAUDE” 1.0 z 13.09.2026
(kopie plików 01–04, 09, 11 w `docs/wiedza/`; dane pakietu w
`backend/dzik_os/wiedza/dane/`; scenariusze w `backend/tests/dane/`).
**Plan sesji:** `docs/plan-sesji/wiedza-v2.md`.

Ten dokument mówi, co DZIAŁA w kodzie, co jest treścią roboczą i czego
nie zrobiono. Nie deklaruje pilotażu użytkowników ani przeglądu
eksperckiego — żadne z nich nie zostało wykonane.

## 1. Co działa (kod)

| Obszar | Gdzie | Stan |
|---|---|---|
| Pięć części Wiedzy, wyszukiwanie, zapisane, historia zmian | `frontend/src/pages/client/Knowledge.tsx` | działa (E2E przepływy 1 i 5) |
| Karta wiedzy W3 (skrót, kroki, „W Twoim planie”, więcej, ograniczenia, autor/recenzja, źródła, zapis, „czy pomogło”) | j.w. | działa; `media=null` daje tekst „film nie został jeszcze dodany” |
| Panel „Dlaczego?” W4 (dolny arkusz / boczny; Escape; fokus wraca; stan sesji zachowany) | `frontend/src/wiedza/Dlaczego.tsx` | działa w `Plan.tsx` (ćwiczenie, wersja, liczba dni) i `Nutrition.tsx` (kalorie, makro) |
| Ślad decyzji (DecisionTrace) | `backend/dzik_os/wiedza/slad.py`, tabela `wiedza_slady` | zapis w tej samej transakcji co wersja planu |
| Resolver (10 kroków, 7 statusów) | `backend/dzik_os/wiedza/resolver.py` | 15 scenariuszy pakietu + kontrole semantyczne |
| Rejestr reguł i szablony tekstu | `backend/dzik_os/wiedza/reguly.py` | H_PROGRESS, H_LAYOUT, H_VOLUME, ENERGY_INITIAL, MEAL_PREFERENCE, USER_SELECTION, PROFESSIONAL_NOTE |
| Ranking „Dla Ciebie” bez ML | `backend/dzik_os/wiedza/kanal.py` | deterministyczny, maks. 3 karty, powód przy każdej; opcja wyłączenia personalizacji |
| Wyszukiwanie (polskie znaki, aliasy, literówki ≤1) | `backend/dzik_os/wiedza/szukaj.py` | tylko widoczne teksty ogólne; zapytanie w body, nie w logach ani audycie |
| Redakcja (nowa rewizja, publikacja, wycofanie) | `routers/wiedza.py`, `frontend/src/pages/coach/WiedzaRedakcja.tsx` | trener = recenzent/wydawca; publikacja odrzucana bez źródeł z rejestru, recenzenta i daty przeglądu |
| Flaga `DZIK_WIEDZA_V2` | `config.py`, `routers/wiedza.py` | `false` → 404 na `/api/wiedza/*`, klient renderuje `KnowledgeLegacy.tsx`; dane zostają |
| Migracja 28 | `db.py` | 7 tabel, addytywna |

## 2. Adaptery: faktycznie obsługiwane typy elementów

| Typ elementu (`target_type`) | Właściciel decyzji | Pochodzenie | Kiedy powstaje ślad |
|---|---|---|---|
| `training_frequency` (cel `plan`) | konfigurator 28 dni | `engine` / H_LAYOUT 1.0 | `POST /api/coach/konfigurator/zapisz` |
| `exercise_prescription` (cel `d{dzień}:e{ćwiczenie}`) | konfigurator 28 dni | `engine` / H_VOLUME 1.0 | j.w., jeden ślad na każde ćwiczenie każdej jednostki |
| `plan_change` (cel `plan`) | trener | `professional` (oryginalny `reason` wersji) | `POST /api/plans/{id}/versions` dla planu klienta |
| `energy_target`, `macro_target` (cel `plan`) | trener | `professional` (wartości z treści wersji diety) | `POST /api/nutrition`, `POST /api/nutrition/{id}/versions` |

**Bez adaptera (jawny brak, `missing_trace` + karta ogólna):** `load`
(H_PROGRESS ma regułę i testy, ale Dzik OS nie liczy jeszcze progresji
automatycznie — to K2 konfiguratora), `rir`, `rest`, `work_sets`,
`rep_range` jako osobne cele (dawka jest jednym śladem
`exercise_prescription`), `exercise_replacement`, `meal`, `portion`,
`ingredient`, `meal_replacement` (moduł diety nie ma śladu obliczeń),
`session_log`, `progress_chart`, `safety`, pochodzenie `user`
(rejestr reguł ma USER_SELECTION, ale żaden ekran klienta nie zapisuje
dziś własnego ustawienia planu).

**Stare plany** (sprzed 0.56.0, w tym seed): brak śladu → `missing_trace`.
Powody nie są rekonstruowane z obecnych danych.

## 3. Reguły produktu wprowadzone w tej rundzie (nie są dowodem naukowym)

* **Stan bezpieczeństwa:** zgłoszenie bólu (`pain_flag`) w sesji bieżącej
  wersji planu w ostatnich 7 dniach, po powstaniu tej wersji →
  `restricted`: akcja „Napisz do trenera”, karta bezpieczeństwa, brak
  doboru zamiennika. Nowa wersja planu od trenera zamyka ścieżkę.
* **Przegląd:** publikacja bez podanej daty dostaje 12 miesięcy (karta
  bezpieczeństwa 6). Po terminie: poza rekomendacjami i resolverem;
  karta bezpieczeństwa znika też z biblioteki.
* **Rola recenzenta:** konto COACH (aplikacja jednego trenera). Karty
  żywieniowe i o objawach wymagają wg pliku 04 dietetyka / specjalisty —
  proces tego nie egzekwuje technicznie; to wymaganie procesu.

## 4. Treści: robocze vs opublikowane

* 48 kart z pakietu (17 tematycznych + 31 atlasu) importowanych jako
  `draft`, `review.approved=false`, autor „Projekt treści przygotowany
  z pomocą AI”. **Żadna nie jest opublikowana** przy wdrożeniu.
* Produkcja (`DZIK_ENV=production`) ignoruje `DZIK_WIEDZA_SZKICE` —
  klient widzi wyłącznie karty opublikowane po recenzji. Do czasu
  pierwszej publikacji nowa Wiedza na produkcji pokazuje pustą
  bibliotekę, podstawy statyczne bez kart i materiały trenera
  („Od trenera”) — to zamierzone: nie uruchamiamy pustej biblioteki
  szkicami.
* Demo/testy/E2E: `DZIK_WIEDZA_SZKICE=true` z widocznym oznaczeniem.
* Pokrycie: 19/19 typów elementów ma powiązanie (`GET /api/coach/wiedza/artykuly` → `pokrycie`).

## 5. Migracja starych treści (mapa)

| Stare | Nowe |
|---|---|
| `/wiedza` karta „Artykuły” (materiały trenera) | blok „Od trenera” w części wg kategorii: Trening→Trening, Dieta/Suplementacja→Odżywianie, Regeneracja→Postępy, reszta→Podstawy |
| `/wiedza` karta „Ćwiczenia” (baza trenera) | część Trening → „Baza ćwiczeń trenera” (ten sam komponent) |
| `/wiedza` karta „Produkty” | część Odżywianie → „Produkty i porcje” |
| adres `/wiedza` | zachowany; części przez `?czesc=`, karta przez `?karta=`, widoki `?widok=zapisane|historia` |
| `/trener/wiedza` | bez zmian + nowa zakładka „Karty wiedzy” |

Nic nie zostało usunięte; `knowledge_items` i jej ekrany działają dalej.

## 6. Testy wykonane

* `tests/test_wiedza_resolver.py` — F01–F15 z pakietu (statusy, kody
  HTTP, wymagane fakty, brak faktów spoza śladu), K03–K05, K08, K09,
  K12–K17, K36 (odrębne cele), K38 (instrukcje w treści są daną),
  schemat `explanation_result` na każdej odpowiedzi.
* `tests/test_wiedza_api.py` — K01, K02, K06, K07, K10, K11, K18–K21,
  K25–K30, K33, K34, K40, ślady konfiguratora i trenera (schemat
  `decision_trace`), restricted po bólu, dieta, mapa migracji, audyt bez
  zapytań.
* Macierz dostępu: 18 nowych operacji zadeklarowanych i zweryfikowanych
  wykonaniem (`test_access_matrix.py`).
* E2E `e2e/wiedza.spec.ts`: przepływ 1 (sesja → Dlaczego → karta →
  powrót ze stanem i fokusem) i 5 (szukaj → karta → zapis), redakcja.
* Nie testowano: K22 poza zachowaniem stanu formularza (timer nie jest
  uruchamiany w E2E), K31 offline (P0 nie cache’uje treści Wiedzy w
  SW), K35 (brak mechanizmu zamian w planie — zamiany robi trener),
  K37 (usunięcie konta obejmuje istniejącą ścieżkę RODO; nowe tabele
  mają FK do `users` — brak dedykowanego testu), K39 (LLM nieużywany).

## 7. Wycofanie

`DZIK_WIEDZA_V2=false` + redeploy. Ślady, zakładki, odczyty i opinie
zostają w bazie; klient widzi poprzednią zakładkę. Usunięcie tabel to
osobna, świadoma migracja — nie jest częścią rollbacku.

## 8. Backlog (P1/P2 i braki P0)

* P1: ścieżki nauki, rekomendacje ze zdarzeń (+100 za nierozwiązane
  pytanie — brak rejestru pytań), lepsze wyszukiwanie.
* P2: asystent oparty na publikacjach i zweryfikowanych śladach.
* Adapter diety dla posiłków/porcji (po rundzie „kreator diety
  kulinarnej” — ta runda dostarczy ślad wyboru dania i porcji).
* Ślad `load`/H_PROGRESS z dziennika serii (K2 konfiguratora).
* Filtr „poziom” w bibliotece (karty pakietu nie mają pola poziomu).
* Multimedia atlasu (prawa, napisy, wersja ćwiczenia).
* Przegląd ekspercki 48 szkiców i pierwsza publikacja — decyzja
  właściciela/trenera, nie kodu.

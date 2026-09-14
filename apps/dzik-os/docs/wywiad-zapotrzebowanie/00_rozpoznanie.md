# Rozpoznanie (etap 0) — wywiad „Zapotrzebowanie kaloryczne”

Plik roboczy wg `ZASADY_pracy_agentow.md` §2.5: kolejne etapy czytają ten plik
zamiast rozpoznawać repozytorium od nowa.

## Mechanizm wywiadu (backend)

- `wywiad/definicje.py`: `TYPY=(WSTEPNY, GLEBOKI)`, `Pytanie` (frozen dataclass;
  rodzaje z `onboarding_flow`: TEXT/LONGTEXT/CHOICE/MULTI/SCALE/BOOL/INFO — **brak rodzaju
  liczbowego**), `Definicja(typ, version, title, opis, sections, questions, triggered)`,
  `_DEFINICJE` (słownik typ → definicja), `aktywne/braki/postep/waliduj/pytanie_out`.
  `waliduj` sprawdza pustość, `max_len`, opcje; `triggered(question_id, wartosci)`
  odsłania pytania warunkowe (`conditional=True`).
- `wywiad/serwis.py`: `przeslij` (walidacja braków → `InterviewSubmission` →
  `_zapisz_fakty` → profil → zadania → outbox → doprecyzowania); `_flaga_bezpieczenstwa`
  (odpowiedź z `flag_options` → `safety_flag=True` na przesłaniu); `stany()` (stan per typ);
  `_TYP_NAZWA` (nazwy w powiadomieniach).
- `wywiad/podsumowanie.py`: iteruje `D.TYPY`, kategoryzuje po `section`/`fact_key`
  (cel / zdrowie / odzywianie…) — nowy typ do pominięcia (wynik ma własną kartę).
- `routers/wywiady.py`: `_typ` (404 dla nieznanego), `_dostep/_dostep_pelny`, przegląd
  iteruje `D.TYPY` (l. 183), `_domena_faktu` (l. 217); szkic PATCH / przeslij POST.
- `Measurement(kind="weight", value, unit, measured_at)` — ostatni pomiar masy jako
  podpowiedź (placeholder) w pytaniu o masę.
- Flagi: `config.py` (`diet_templates_enabled` wzorzec), `tests/conftest.py` l. 31,
  `.env.example` l. 79, `main.py` `features` (l. 267).
- Migracje: `db.py` `MIGRATIONS.append((nr, opis, [sql…]))`, ostatnia 32 (l. 1273).
- Modele: `models.py` kończy się `DietSwapEvent` (l. 1979).
- Testy: `tests/test_wywiad_zakladka.py` (fixtury `_def/_patch/_przeslij/_stan`,
  `seeded`, `login`, `CLIENT_A`, `COACH`), `tests/access_matrix.py` (mapa tras → `Access`).

## Frontend

- `types.ts`: `WywiadTyp`, `WywiadPytanie.type`, `WywiadStan`.
- `pages/wywiad/wspolne.tsx`: `TYP_LABEL`, `SEKCJA_LABEL`.
- `pages/wywiad/Formularz.tsx`: renderuje po `q.type` (TEXT = `<input>`).
- `pages/client/Wywiad.tsx`: `typ` z query, warunek `typ === "wstepny" || "gleboki"`,
  `KartaWywiadu` (opis celu per typ).
- `pages/coach/WywiadTab.tsx`: lista `dane.wywiady`, tryb wspólnie.
- `pages/client/Nutrition.tsx` (karty „Dieta”), `pages/coach/PrzypiszDiete.tsx`
  (pole `pd-kcal`, stan `kcal`), `pages/coach/ClientDetail.tsx` (zakładki `wywiad`, `dieta`).

## Decyzje projektowe

1. Nowy rodzaj pytania `NUMBER` (definicje.py) + pole `zakres` w `Pytanie` (na końcu,
   domyślnie `None`) → walidacja liczbowa po stronie serwera (przecinek dopuszczalny).
2. Wiek w latach zamiast daty urodzenia (minimalizacja danych; wynik ten sam).
3. Wynik liczony przy przesłaniu (`serwis.przeslij` → `zapotrzebowanie_serwis.przelicz`)
   i zapisywany do `calorie_estimates` (migracja 33), jedna wersja na przesłanie.
4. Flaga zdrowotna: pytanie `zk_zaburzenia` (domena zdrowie) z `flag_options`
   → `safety_flag` → `hidden_for_client` (klient nie dostaje liczb; trener pełne).
5. Podsumowanie wywiadu pomija typ `zapotrzebowanie`; API `/zapotrzebowanie` osobne.

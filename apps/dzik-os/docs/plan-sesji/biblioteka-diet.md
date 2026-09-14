# Plan sesji: biblioteka szablonów diet — 45 odsłon, 181 produktów, silnik v1.1 (0.64.0)

**Gałąź:** `agent/biblioteka-diet` (od `main` = c4143cd). **Rola:** aktywny piszący —
polecenie właściciela z 14.09 („zadanie: do zaimplementowania w dieta szablony”, paczka
`paczka_dla_agenta.zip`: `docs/diet-module/` po audycie z 14.09).
**Rezerwacje (KOORDYNACJA §0):** wersja **0.64.0**, migracja **35** (addytywna: nowe kolumny
notatek/alergenów). Równolegle: `agent/nawyki-dzisiaj` (0.63.0, migracja 34, PR #65 — scalana
pierwsza); `agent/monitoring-postepy` przesuwa się na **0.65.0 / migrację 36**. Pliki
współdzielone: `models.py` (kolumny w istniejących klasach diet), `db.py` (wpis 35),
`CHANGELOG.md`, `STAN_PRZEKAZANIA.md`; moduł `dzik_os/dieta/*` i `pages/dieta`, `PrzypiszDiete`,
`DietaSzablon`, `SzablonyDiet` — rozłączne z nawykami.

## Co jest w paczce wobec 0.60.0 (rozpoznanie w `docs/diet-module/01_rozpoznanie_biblioteki.md`)

* **Produkty:** 181 (mamy 142) — nadzbiór: 39 nowych (m.in. bezlaktozowe, bezglutenowe,
  halibut, ananas), zero zmian wartości ani identyfikatorów istniejących.
* **Szablony:** 45 (9 profili × 5 odsłon; mamy 1). Nowe klucze: `derived_from`,
  `supplements_note` (lista), `sodium_note`, `audit` (wersja + poprawki + uwagi) na odsłonie;
  `allergens` (lista) na posiłku. Profil Sportowa: 5 slotów (`obiad_1`, `obiad_2`).
  Standard v1 po audycie **różni się** od wersji w bazie (inne gramatury) — golden też.
* **Silnik v1.1 (limity porcji):** mięso/ryby LINIOWY ≤ 300 g surowego na posiłek,
  jajka ≤ 4 szt. na posiłek, tłuszcze LINIOWY `round_step` = 1 g. Reszta identyczna.
* **Mapy zamienników** LF/GF (`subst_maps.json`) — użyte przy autorstwie profili pochodnych;
  w aplikacji informacyjne (nie zmieniają silnika).
* Skrypty autorskie (`audit.py`, `fix.py`, `tpl_common.py`) — nie uruchamiane w aplikacji.

## Decyzje projektowe

1. **Import zastępujący**: seed importuje wszystkie 45 odsłon; istniejąca (profil, odsłona)
   z innym `source_hash` (sha256 pliku) dostaje **nową treść** (dni/posiłki/składniki
   usuwane i tworzone od nowa, ten sam `week_id`). Przypisane diety mają migawki — nic
   im się nie zmienia (spec §8). Status po imporcie: PUBLISHED (biblioteka przeszła audyt
   14.09; sweep w teście potwierdza ≥ 95 % dni OK dla każdej odsłony).
2. **Silnik**: trzy reguły v1.1 dodane 1:1 (jako reguły w `fill_defaults`, z produktem
   z bazy zamiast CSV); `docs/diet-module/engine.py`, golden i `template_standard_v1.json`
   podmienione na wersje z paczki; testy golden na nowym golden (zmiana referencji, nie
   asercji „pod wynik”).
3. **Notatki z szablonu** (`supplements_note`, `sodium_note`) pokazywane trenerowi
   w podglądzie i klientowi w widoku diety **jako treść autora biblioteki** (proweniencja:
   „z szablonu, autor biblioteki”) — aplikacja nie ustala dawek (R-10, ADR-DZIK-003 §4);
   alergeny posiłku widoczne w podglądzie trenera (pomoc przy wykluczeniach).
4. **Sloty**: etykiety `obiad_1`/`obiad_2` → „Obiad 1” / „Obiad 2” (słownik `SLOT_LABEL`),
   dowolna liczba slotów renderowana z szablonu (dziś już dynamicznie).
5. **Poza zakresem** (spec §4): lista zakupów, mikroskładniki w UI (`baza_produktow_mikro.csv`
  zostaje w docs), rotacja odsłon, statystyki wymian.

## Etapy (czytam → wytwarzam → weryfikuję → nakład)

| Etap | Czytam | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 | paczka (index, schemat JSON, CSV, engine diff), `dieta/seed.py`, `silnik.py`, modele | ten plan + `01_rozpoznanie_biblioteki.md` | — | dziesiątki tys. |
| 1 silnik v1.1 | `silnik.fill_defaults`, `docs/diet-module/engine.py` (diff = 3 reguły) | reguły limitów, podmiana `engine.py`, golden, `template_standard_v1.json` | `test_dieta_silnik` (golden na nowym golden, sweep 131/133, stałe) + 3 nowe testy limitów | dziesiątki tys. |
| 2 model + migracja 35 + dane + seed | `models.py` (diet), `db.py`, `seed.py` | kolumny `derived_from/supplements_note/sodium_note/audit_json/source_hash` (odsłona), `allergens` (posiłek); 45 JSON + CSV 181 w `dieta/dane`; import zastępujący po hashu; `waliduj_szablon` akceptuje nowe klucze | `test_dieta_seed` (181/45/1295, idempotencja, podmiana po hashu nie rusza migawek), przenośność migracji | setki tys. (największy: 45 plików + logika podmiany) |
| 3 API + UI | `routers/diet.py` (out odsłony/posiłku), `dieta/wspolne.tsx`, `PrzypiszDiete`, `DietaSzablon`, `SzablonyDiet` | pola notatek/alergenów w odpowiedziach, `SLOT_LABEL`, notatki w podglądzie i widoku klienta, sweep wszystkich odsłon w teście | `tsc`, build, E2E `dieta-szablon` (istniejący) + krótki spec na profil Sportowa (5 slotów), a11y | setki tys. |
| 4 zamknięcie | — | CHANGELOG 0.64.0, `docs/diet-module/PROGRESS.md`, RELEASE_STATUS, STAN_PRZEKAZANIA, raport | pełny `pytest`, ruff, spójność, CI | dziesiątki tys. |

**Stan (14.09, koniec sesji):** etapy 0–4 zrobione — zob. `docs/diet-module/PROGRESS.md` (sekcja 0.64.0).

## Odstępstwa od planu
* Sweep w zakresie odsłony zamiast stałych 1400–3200 (audyt liczył zakres odsłony; Masa
  2200–4000 przy 1400 kcal daje ujemny cel posiłku).
* Etykiety slotów „obiad I / obiad II” (plan: „Obiad 1 / Obiad 2”) — pytanie do właściciela.
* Uwagi o suplementacji tylko dla trenera (plan: trener i klient) — wynik przeglądu R-10.
* Testy reguł v1.1 dopisane dopiero po przeglądzie (plan obiecywał je w etapie 1).
* Znacznik edycji panelu i `szablony_pominiete` — nie było w planie, wynik przeglądu.

## Weryfikacja wykonana
ruff; testy diety (silnik 19, seed 7, API 14, poprawki 3); pełny pytest; `tools/spojnosc.py`;
tsc + build (89,6 kB gzip / 120 kB); `test:helpers`; E2E `dieta-szablon.spec.ts` 2/2 (w tym
Sportowa 5 slotów + notatki); a11y 47/47; PWA offline; CI po scaleniu.

**Największy koszt:** etap 2 (dane + podmiana). Taniej bez utraty informacji: jeden test
parametryzowany po 45 plikach zamiast 45 testów; sweep całej biblioteki jako jeden test
(45 × 19 kaloryczności × 7 dni ≈ 6 tys. dni — sekundy). Bezpiecznik: 3× plan.
Przegląd: 3 recenzentów wsadowo, P0/P1 przed scaleniem, P2 → PROGRESS.

## Odstępstwa od planu

(uzupełnię w trakcie)

## Weryfikacja wykonana

(uzupełnię po rundzie)

# Plan sesji: Głęboki wywiad jako drugi przepływ rozmowy (0.53.0)

**Gałąź:** `claude/ocena-projektu-dzik-os-76ercy` (restart z `main` @ 0.51.0 —
poprzednia zawartość gałęzi rozliczona w 0.42.0).
**Rola:** aktywny piszący (jawne polecenie właściciela: „Wprowadź wywiad do
aplikacji", 25.08). **Uwaga o kolejce:** w chwili planowania otwarty był PR
`[WRITER]` #27 (0.52.0) — ta runda została zbudowana lokalnie i zostanie
wypchnięta dopiero po jego scaleniu/zamknięciu; draft PR powstanie przed
wypchnięciem jakiejkolwiek zmiany kodu.

## Co robimy

Głęboki wywiad z podopiecznym — 46 pytań w 9 modułach (wzorzec zatwierdzony
przez właściciela: cel trzy warstwy głębiej, historia treningowa, zdrowie-
przesiew, sen, stres i głowa, żywienie pod lupą, logistyka tygodnia, punkt
startu, zasady współpracy) — jako **drugi przepływ istniejącego mechanizmu
rozmowy startowej**, nie osobna maszyneria:

* te same zasady: jedno pytanie na raz, „dlaczego pytam", pomijalność,
  bramkowanie zgodami per domena, wersjonowanie odpowiedzi, wznowienie,
  podsumowanie zatwierdzane najpierw przez klienta, potem trenera;
* czerwone flagi wyborów (C1/C2/E3) na istniejącym mechanizmie
  `safety_flag` — spokojny komunikat, zero oceny;
* AI w tym przepływie wyłączone (v1 zawsze deterministycznie, z jawnym
  powodem) — prompt podsumowania jest specyficzny dla rozmowy startowej.

## Rezerwacje

* **Wersja: 0.53.0** (0.52.0 zarezerwowane przez PR #27).
* **Migracja: 26** — addytywna: `onboarding_sessions.flow VARCHAR(20)
  NOT NULL DEFAULT 'start'` (sesje wywiadu i rozmowy w jednej tabeli,
  rozróżniane kolumną; zero backfillu, wycofanie = ignorowanie kolumny).

## Obszar plików

Backend: `db.py` (migracja 26), `models.py` (kolumna `flow`),
`onboarding_flow.py` (uogólnienie helperów o parametr `steps` +
`flag_options` w `Step` — zachowanie rozmowy startowej bez zmian),
nowy `interview_flow.py`, `routers/onboarding.py` (fabryka routera),
nowy `routers/interview.py`, `main.py`, `tests/access_matrix.py`,
nowy `tests/test_wywiad.py`.
Frontend: `pages/client/Onboarding.tsx` (parametryzacja ścieżki),
nowy `pages/client/Interview.tsx`, `App.tsx` (trasa `/wywiad`),
`More.tsx` (wejście), `pages/coach/ClientDetail.tsx` (zakładka „Wywiad"),
nowy `e2e/wywiad.spec.ts`.
Dokumenty: `CHANGELOG.md`, `PERMISSIONS.md`, `INSTRUKCJA_KLIENTA.md`,
`INSTRUKCJA_TRENERA.md`, `KOORDYNACJA.md` (rezerwacje), ten plan,
`STAN_PRZEKAZANIA.md` na koniec rundy.

## Czego NIE robię

* nie zmieniam zachowania rozmowy startowej (istniejące testy muszą
  przejść bez modyfikacji ich asercji);
* nie dotykam AI (podsumowanie wywiadu zawsze deterministyczne);
* wywiad nie tworzy celu (`Goal`) — cel powstaje w rozmowie startowej;
* zero zmian w Core (`hos_engine/`).

## Bramki przed PR

ruff, pełny pytest backendu, Core 275, spojnosc, mutacje, obrony,
tsc+build+test:helpers, Playwright, zasada uruchomienia (obejrzeć ekran
przez serwer E2E). Test względem INTENDED_PURPOSE §2 wykonany na etapie
wzorca: wywiad zbiera wyłącznie deklaracje do planu układanego przez
człowieka; moduł zdrowia to przesiew-do-skierowania, nie diagnostyka.

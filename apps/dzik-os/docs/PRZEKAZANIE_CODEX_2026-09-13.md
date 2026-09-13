# Przekazanie dla recenzenta (Codex) — 2026-09-13

**Weryfikacja wykonana:** 2026-09-12 23:40 UTC – 2026-09-13 01:50 UTC,
sesja jedynego piszącego i integratora (Claude). Zakres: repozytorium
`dudsi101-svg/human-os2` (aplikacja `apps/dzik-os`), przebiegi GitHub
Actions, lokalne uruchomienia identycznego buildu, repozytorium
`dudsi101-svg/Human-os` (tylko odczyt). **Produkcja
`https://dzik-os-panel.fly.dev` jest z tej sesji nieosiągalna** (polityka
egress odrzuca połączenie, HTTP 403 z proxy) — stan produkcji pochodzi
wyłącznie z logów workflowów (smoke po deployu), nie z bezpośredniego
odczytu. Wszystko, czego nie dało się sprawdzić, jest oznaczone
**niezweryfikowane**.

## 1. Repozytorium, gałęzie, PR, SHA

| Rzecz | Wartość |
|---|---|
| `main` | `f2ebf22` — merge PR #49 (0.54.4) |
| Produkcja (smoke deployu, run 34726667242) | `{"version":"0.54.4","build":"f2ebf2259a7d","migration":27}` — **wdrożone i potwierdzone smoke'iem**, nie odczytem ręcznym |
| PR #49 (0.54.4, inna sesja Claude) | **scalony** przez integratora 2026-09-12 23:44 UTC po zatwierdzeniu właściciela; CI 8/8 na `43bb9dd`; nie był PR-em tej sesji |
| PR #50 (0.54.5, ta sesja) | **otwarty, gotowy do recenzji, niescalony**; gałąź `agent/diagnostyka-produkcji`, head `42e1108` (+ ten dokument), CI 8/8 zielone; scala właściciel |
| Workflow „Sekrety produkcji (Fly.io)” | **0 przebiegów w historii** — sekrety SMTP nigdy nie trafiły na Fly |
| Workflow „Diagnostyka produkcji (Fly.io)” | istnieje dopiero w PR #50; nie uruchomiony |

## 2. Postęp od poprzedniego przekazania

| Obszar | Poprzedni stan | Aktualny stan | Dowód | Pozostała praca |
|---|---|---|---|---|
| PR #49 / produkcja | zrecenzowany, niescalony, wdrożenie niepotwierdzone | scalony (`f2ebf22`), wdrożony, smoke potwierdza 0.54.4 | run 34726667242, krok „Smoke check” | — |
| Poczta | „według dokumentacji brak `DZIK_SMTP_HOST` = dostawca null” | **potwierdzone pośrednio**: workflow sekretów nigdy nie uruchomiony, innej drogi do sekretów Fly w projekcie nie ma → dostawca `null`; **bezpośredni odczyt z procesu: niezweryfikowany** (wymaga diagnostyki po scaleniu #50) | historia Actions (0 runów `fly-sekrety.yml`) | właściciel dodaje sekrety SMTP w repo → workflow z zakresem `poczta` → test na dudsi101@gmail.com → potwierdzenie odbioru przez właściciela |
| Metadane błędów doręczeń | zdarzenie zaproszenia niosło tylko `email`/`manual`; dostawca połykał wyjątki | `reason` (`no_provider` / `send_failed:<Klasa>`) w API i audycie; `last_failure` na dostawcy; klasa błędu w `test_poczty` | PR #50: `routers/clients.py`, `notifications_provider.py`, `test_poczty.py`, testy | scalenie |
| Diagnostyka produkcji | brak narzędzia | moduł `dzik_os.diagnostyka` + workflow (tylko odczyt) — **zaimplementowane i przetestowane, niewdrożone** | PR #50, `tests/test_diagnostyka.py`, uruchomienie na seedzie | scalenie → uruchomienie → odczyt |
| Zakres workflowu sekretów | przenosił każdy niepusty sekret (SMTP + AI + klucz plików) | input `zakres`, domyślnie tylko poczta | PR #50 `fly-sekrety.yml` | scalenie |
| Konto TEST 01 (dudsi101+test1) na produkcji | Codex kliknął „Wyślij zaproszenie”, wynik nieodczytany, e-mail nie doszedł | **niezweryfikowane** — przy dostawcy `null` aplikacja nie wysyła e-maila, tylko pokazuje trenerowi jednorazowy link do przekazania (`delivery=manual`); konto PENDING najpewniej istnieje | kod `_issue_invitation`, `InvitationPanel` | diagnostyka po #50 → „Wyślij ponownie” w panelu (nowy link, stary unieważniony) → aktywacja |
| Konta TEST 02/03 na produkcji | nie istnieją | nie istnieją (**niezweryfikowane**, nic nie tworzono) | — | po TEST 01 |
| Cały proces trener↔klient | nieprzetestowany na tej wersji | **przetestowany w prawdziwej przeglądarce na identycznym buildzie** (`42e1108`, świeży seed) dla trzech kont TEST — zaproszenie → link → aktywacja → zgody → import materiałów → plan/dieta/harmonogram → odczyt klienta → raport → odpowiedź i ocena trenera → odczyt; izolacja A/B (404); wersja v2 z v1 w historii | `docs/plan-sesji/diagnostyka-produkcji.md` §Weryfikacja; 12 zrzutów poza repo | **na produkcji: niepotwierdzone w rzeczywistym użyciu** |
| Testy | 871 backend | ruff czysto; backend **875 passed, 1 skipped**; Core **275**; spójność 13 kontroli; build 88.7 kB gz; helpers 140; E2E 21/21; CI 8/8 na PR | log `backend-v.log` sesji, run 34727981392 | — |
| Błędy naprawione | — | brak błędów kodu w przejściu procesu; usterka procesu: pierwsza wersja commitu wciągnęła `apps/dzik-os/data` (bazy testowe, uploady testowe, lokalny klucz VAPID); commit przepisany (`--force-with-lease` na własnej niescalonej gałęzi), katalog w `.gitignore` | PR #50, komentarz | Codex: potwierdzić, że historia gałęzi nie zawiera `apps/dzik-os/data` |

Rozróżnienie: **zaplanowane** (TEST 02/03 na produkcji, poczta),
**zaimplementowane i przetestowane** (0.54.5), **wdrożone** (0.54.4),
**potwierdzone w rzeczywistym użyciu** (nic z zakresu poczty i kont
testowych — brak dostępu do produkcji i brak sekretów).

## 3. Stan poczty i kont — jednym zdaniem każde

- **Poczta:** nie wychodzi; dostawca `null`; sekrety SMTP nie istnieją na Fly (workflow nigdy nie uruchomiony). Blokada: sekrety repo należą do właściciela.
- **TEST 01:** stan na produkcji niezweryfikowany; prawdopodobnie konto PENDING z aktywnym zaproszeniem, link nieodczytany.
- **TEST 02, TEST 03:** nie istnieją na produkcji; scenariusze przeszły lokalnie na identycznym buildzie.
- **Materiały Łukasza:** `TPL-025` „Push/Pull/Legs/Push II — Etap I (autorski)”, `TPL-026` „FBW A/B/C — pierwsze 5 tygodni (autorski)” (`plan_templates_data.py`, z plików właściciela z 31.08, zanonimizowane w 0.54.0), `DTPL-001` „Dieta — Etap I (autorska, posiłki z opcjami)” (`dieta_szablony_data.py`, makro celowo puste). „Start — całe ciało 2 dni” to wbudowany szablon ogólny `TPL-001`, nie materiał Łukasza. Żadnych wymyślonych zaleceń ani makro; parametry raportu oznaczone jako dane testowe.

## 4. Human OS — właściwe repozytorium i relacja

- `dudsi101-svg/Human-os` — repozytorium kanoniczne Core: 0.10.0-alpha.1,
  `artifact.registry.json` (20 artefaktów, `updated_at` 2026-08-17),
  sekcja „Niewydane” w CHANGELOG (autoryzacja per-wywołanie, skale SHADOW,
  słownik zdarzeń 0.4.0), moduł `hos_engine/authorization_decision.py`
  + `docs/authorization-decision-contract.md`; ostatni push 2026-08-24
  (**PR #61 tego repozytorium**: moduł Diety w `apps/user-demo`).
  Numer #61 dotyczy WYŁĄCZNIE `Human-os`; w `human-os2` PR-y są
  numerowane do #50.
- `dudsi101-svg/human-os2` — pierwszy commit: „Import Human OS foundations
  from dudsi101-svg/human-os@68fe1e4”. Core (`hos_engine/`, `tests/`, 275
  testów) jest **migawką**: ta sama wersja `0.10.0a1` w `pyproject.toml`,
  ale brak `authorization_decision.py` i trzech plików testów
  (`test_authorization_decision.py`, `test_authorization_integration.py`,
  `test_golden_nof1.py`) obecnych w `Human-os`; brak
  `artifact.registry.json`. Dzik OS (`apps/dzik-os`) istnieje tylko tutaj.
- Historyczne braki z raportu z 7.09: „lokalna logika Dieta/Trening
  w aplikacji” dotyczy `Human-os/apps/user-demo` (prototyp UX,
  `localStorage`) — bez zmian od 24.08 (**niezweryfikowane głębiej niż
  listing plików**); „nieaktualny `artifact.registry.json`” — nadal
  `updated_at` 2026-08-17, czyli nie obejmuje ani PR #61, ani Dzik OS;
  „niedomknięte kontrakty relacji i rodzin identyfikatorów” — w `Human-os`
  rejestr wciąż wymienia lukę „nine parallel mechanisms answer 'may this
  run?'” z `AuthorizationDecision` jako celem P1.

## 5. Pozostałe problemy (wg wpływu na użytkownika)

1. **Klient nie dostaje e-maila z zaproszeniem** (dostawca `null`) — trener musi ręcznie przekazać link; reset hasła e-mailem martwy. Blokada: sekrety.
2. **Stan produkcji nieznany z sesji operatora** — do scalenia #50 nie ma narzędzia tylko do odczytu; sesja nie ma dostępu sieciowego do produkcji.
3. **Link aktywacyjny łatwo zgubić** — pokazuje się raz w panelu po kliknięciu; „Wyślij ponownie” generuje nowy. Ergonomia, nie błąd.
4. **Nowa wersja planu wymaga ręcznego powodu bez podpowiedzi** — ergonomia.
5. **Dwa Core rozjechane** (`Human-os` vs `human-os2`) — nie dotyczy pilotażu, ale każda dalsza integracja z Core wymaga decyzji, który jest źródłem prawdy.

## 6. Następne kroki (maks. trzy, z kryterium zakończenia)

1. **Scalić #50 i uruchomić diagnostykę.** Kryterium: workflow
   „Diagnostyka produkcji” zielony, w logu `dostawca_poczty`, lista kont
   z `dudsi101+test1` i jego zaproszeniem (aktywne/użyte), wersja 0.54.5
   w smoke deployu.
2. **Poczta.** Właściciel dodaje w repo sekrety `DZIK_SMTP_HOST/PORT/USER/
   PASSWORD/FROM`; integrator uruchamia „Sekrety produkcji” z zakresem
   `poczta` i `test_email=dudsi101@gmail.com`. Kryterium: krok testowej
   wysyłki zielony **i** właściciel potwierdza wiadomość „Dzik OS — test
   poczty” w skrzynce (przyjęcie przez SMTP to nie odbiór).
3. **TEST 01 na produkcji do końca.** W panelu trenera „Wyślij ponownie”
   przy `dudsi101+test1` (po poczcie: e-mail; bez: link do przekazania) →
   aktywacja → zgody → plan `TPL-025` + dieta `DTPL-001` + harmonogram →
   raport → odpowiedź trenera. Kryterium: diagnostyka pokazuje relację
   ACTIVE ze zgodą współpracy, 1 plan, 1 dietę, 1 raport; właściciel
   potwierdza odczyt odpowiedzi trenera na koncie klienta. Dopiero potem
   TEST 02 i TEST 03 (schemat jak w lokalnym przejściu).

## 7. Do recenzji przez Codexa (PR #50, `42e1108`)

- `apps/dzik-os/backend/dzik_os/diagnostyka.py` — czy któraś sekcja niesie
  dane, których nie powinno być w logu Actions (e-maile kont są celowe).
- `apps/dzik-os/backend/dzik_os/routers/clients.py` — `reason` w wyniku
  i zdarzeniach; `notifications_provider.py` — `last_failure`.
- `.github/workflows/fly-sekrety.yml` (input `zakres`, `case`),
  `.github/workflows/fly-diagnostyka.yml` (przypięta akcja, brak inputów).
- Testy: `tests/test_diagnostyka.py`, `tests/test_test_poczty.py`,
  `tests/test_invitations.py`.
- Historia gałęzi: brak `apps/dzik-os/data/` (po przepisaniu commitu).

## 8. Propozycja następnej rundy Human OS (najmniejszy użyteczny etap)

**Jedna funkcja przez Core od początku do końca: „nowa wersja planu
treningowego”** (`POST /api/plans/{id}/versions`, dziś:
`require_owned_resource` → `resolve_client_access` (ConsentRegistry
Core) → zapis → `record_event` (SQLiteEventStore Core) → Receipt).

- **Granica app/Core (stan faktyczny):** Core już rozstrzyga zgodę
  (`ConsentRegistry.authorize`) i trzyma łańcuch zdarzeń; aplikacja sama
  składa rolę, relację i decyzję. Brakuje jednego punktu, który mówi
  „dlaczego wolno” i podpisuje to pokwitowaniem.
- **Krok 0 (decyzja właściciela, konieczna):** przenieść z `Human-os` do
  `human-os2` `hos_engine/authorization_decision.py`, jego kontrakt
  (`docs/authorization-decision-contract.md`) i testy — jako wierną kopię
  (bez zmian Core), z regresją 275 + nowe. Bez tego runda budowałaby
  na rozjechanej migawce.
- **Autoryzacja i zgoda:** `AuthorizationDecision` z jawnie wymaganymi
  aspektami: `role_grant` (COACH), `relationship` (ACTIVE), `consent`
  (ConsentRegistry, domena `training_data`, akcja `write`),
  `proof` (Proof Kernel na deklarowanym opisie akcji: autor = trener,
  odwracalność = 1.0 bo poprzednia wersja zostaje, zgoda = wynik aspektu,
  ograniczenia = „plan trenera, nie porada medyczna”). Deny-first; brak
  oceny aspektu = odmowa.
- **Decyzja, receipt, zdarzenie, odtworzenie:** wynik decyzji (WHO / BY
  WHAT AUTHORITY / ON WHAT / WHAT / WHY / CONSENT / POLICY + wynik Proof
  Kernel) trafia do `payload` zdarzenia `PLAN_VERSION_CREATED` i do
  `Receipt` (nowe pole `decision_json`); odmowa = 403 z pokwitowaniem
  odmowy (`PLAN_VERSION_REFUSED`), nigdy wyjątek; `replay.rebuild_entities`
  (Core) po zdarzeniach `PLAN_CREATED`/`PLAN_VERSION_CREATED` odtwarza
  listę wersji planu — narzędzie `python -m dzik_os.odtworz_plany`
  porównuje wynik z bazą.
- **Rejestr projektu:** wpis w `artifact.registry.json` (`Human-os`, po
  decyzji właściciela także kopia w `human-os2`) dla „Dzik OS — integracja
  z Core”: status, użyte moduły, luki (pozostałe operacje bez
  `AuthorizationDecision`).
- **Kryterium całego scenariusza:** trener tworzy v2 w UI → odpowiedź
  niesie `receipt.decision` z siedmioma polami i wynikiem Proof Kernel →
  `verify_chain()` prawdziwe → `odtworz_plany` z samego łańcucha zdarzeń
  daje te same numery wersji i powody co baza → klient bez zgody
  `training_data` dostaje 403 z pokwitowaniem odmowy, a zdarzenie odmowy
  jest w łańcuchu. Zakres: jedna trasa; żadnej przebudowy pozostałych.

## 9. Punkt kontynuacji

Kontynuować od: **scalenie PR #50** (właściciel) → uruchomienie workflowu
„Diagnostyka produkcji (Fly.io)” → odczyt raportu → decyzja o TEST 01
(„Wyślij ponownie”). Równolegle: sekrety SMTP (właściciel). Nic z zakresu
poczty i kont testowych nie jest ukończone; kod i proces są gotowe do
tego punktu.

**Działa:** produkcja 0.54.4; pełny proces trener↔klient na identycznym
buildzie; diagnostyka i metadane błędów (w PR). **Niepotwierdzone:**
stan TEST 01 na produkcji; dostawca poczty w procesie produkcyjnym;
odbiór jakiejkolwiek wiadomości. **Następny krok:** scalić #50
i uruchomić diagnostykę.

# Plan sesji: diagnostyka produkcji tylko do odczytu + poczta pod kontrolą (0.54.5)

**Gałąź:** `agent/diagnostyka-produkcji` (od `main` = f2ebf22)
**Rola:** jedyny piszący i integrator (decyzja właściciela 12.09);
recenzent kodu: niezależna sesja Codex.
**Cel:** właściciel zlecił uruchomienie poczty i trzy konta testowe.
Z tej sesji produkcja jest nieosiągalna (polityka egress odrzuca
`dzik-os-panel.fly.dev`), a jedyną drogą do maszyny są workflowy.
Żaden istniejący workflow nie odpowiada na pytania: jaki dostawca
poczty faktycznie działa w procesie, jakie sekrety są ustawione
(nazwy, nigdy wartości), jakie konta/zaproszenia/relacje istnieją
(czy zaproszenie „TEST 01” z 12.09 w ogóle powstało). Dokumentacja to
nie dowód konfiguracji serwera.

## Zamiar

1. **`dzik_os.diagnostyka`** — raport tylko do odczytu, bez PII ponad
   e-maile kont (log Actions widzi wyłącznie właściciel repo): dostawca
   poczty z procesu (`smtp`/`null`), które zmienne `DZIK_SMTP_*` są
   USTAWIONE (tylko nazwy), `public_base_url`, wersja/migracja; konta
   (e-mail, status, role, wymuszona zmiana hasła, MFA tak/nie);
   relacje trener–klient ze statusem i zgodą współpracy; zaproszenia
   (klient, wystawione, ważne do, użyte/anulowane); liczba planów
   treningowych/diet/raportów per klient; zdarzenia doręczeń
   (`CLIENT_INVITED`, `PASSWORD_RESET_*`) z ostatnich 30 dni. Zero
   hashy, tokenów, treści zdrowotnych.
2. **Workflow „Diagnostyka produkcji (Fly.io)”** — `workflow_dispatch`
   bez inputów, `flyctl ssh console -C "python -m dzik_os.diagnostyka"`;
   nic nie ustawia, nic nie restartuje.
3. **Workflow „Sekrety produkcji”** dostaje input `zakres`
   (`poczta` domyślnie / `ai` / `szyfrowanie` / `wszystko`) — dotąd
   przenosił KAŻDY niepusty sekret repo, więc uruchomienie „dla poczty”
   mogłoby włączyć AI albo klucz szyfrowania, czego właściciel zabronił.
4. **Metadane błędu doręczenia**: dostawca SMTP zapamiętuje klasę
   ostatniego wyjątku (`last_failure`, bez treści); `_issue_invitation`
   i ponowne wysłanie zapisują w `CLIENT_INVITED` powód
   (`no_provider` / `send_failed:<Klasa>`), jak reset hasła (P0-4);
   `test_poczty` wypisuje klasę błędu zamiast „szczegóły w logu”.
   Pozwala rozróżnić: brak konfiguracji / błąd logowania-połączenia /
   błąd aplikacji / przyjęcie przez serwer bez potwierdzonego odbioru.
5. Testy: raport nie zawiera hashy/tokenów i niesie wymagane sekcje;
   powód w `CLIENT_INVITED`; `last_failure` po nieudanej wysyłce.

## Świadomie nie robię

- żadnych zmian w bazie produkcyjnej ani w sekretach z tego PR-a
  (wszystko to osobne uruchomienia workflowów po scaleniu);
- przebudowy systemu poczty — dostawca SMTP zostaje, jak jest;
- włączania AI ani klucza szyfrowania.

## Rezerwacje

- **Wersja: 0.54.5.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- ruff, backend, Core, spójność (w tym pinowanie akcji nowego
  workflowu), frontend nietknięty (tylko wersja); uruchomienie na
  żywo: `diagnostyka` na lokalnym seedzie + po scaleniu na produkcji.

## Weryfikacja (wykonana, 13.09)

- ruff czysto; **backend 875 passed, 1 skipped** (5:54); **Core 275 passed**; spójność
  czysto (13 kontroli); `tsc`/`npm run build` — 88.7 kB gz (budżet 120);
  `test:helpers` 140/140; **E2E 21/21** (frontend bez zmian poza wersją).
- **Uruchomienie na żywo (diagnostyka)**: `python -m dzik_os.diagnostyka`
  na świeżym seedzie — raport z 6 sekcjami, dostawca `null`, 6 nazw
  brakujących zmiennych SMTP, 7 kont, 5 relacji ze zgodą współpracy,
  plany/raporty per klient, 7 zdarzeń; test dowodzi zera hashy/tokenów
  i braku nowych zdarzeń po odczycie.
- **Przejście całego procesu na identycznym buildzie** (prawdziwa
  przeglądarka na `dist/`, świeży seed) — trzy konta testowe
  (dudsi101+test1/2/3, oznaczone „TEST”): zaproszenie z panelu →
  „link do przekazania” (dostawca `null`) → aktywacja linkiem i własne
  hasło → logowanie → bramka zgód (wymagane + opcjonalne) → trener
  importuje z katalogu autorskie TPL-025/TPL-026 i DTPL-001 → TEST 01:
  plan + dieta (makro puste) + harmonogram raportów; TEST 02: sam
  plan (ekran Dieta pusty); TEST 03: plan v1 → „Nowa wersja aktualnego
  planu” → v2 z v1 w historii (klient widzi historię) → TEST 01 wysyła
  raport → trener odpowiada i ocenia 4/5 → klient widzi odpowiedź
  (API) → izolacja: TEST 01 na zasobach TEST 02 dostaje 404 (plany,
  dieta, profil, raporty), własne 200. Zrzuty 12 ekranów w scratchpadzie
  sesji (poza repo).
- Produkcja: z tej sesji nieosiągalna (egress 403 dla
  `dzik-os-panel.fly.dev`) — to samo po scaleniu wykona workflow
  diagnostyki, a ścieżkę UI właściciel/Codex w przeglądarce.
- Uwaga dla następnej sesji: pełny backend uruchomiony RÓWNOLEGLE
  z lokalnym serwerem E2E/przeglądarkowym przejściem dał kilkadziesiąt
  fałszywych czerwonych i trwał >30 min; ten sam zestaw uruchomiony
  osobno — zielony w 6 min. Nie łączyć tych dwóch rzeczy w czasie.

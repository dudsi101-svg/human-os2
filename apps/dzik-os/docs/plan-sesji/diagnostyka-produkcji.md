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

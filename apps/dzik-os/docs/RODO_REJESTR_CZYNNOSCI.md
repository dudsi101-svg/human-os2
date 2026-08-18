# Rejestr czynności przetwarzania — Dzik OS (szkic techniczny)

> **STATUS: SZKIC DO UZUPEŁNIENIA PRZEZ ADMINISTRATORA DANYCH I DO
> KONSULTACJI PRAWNEJ.** Przygotowano technicznie na podstawie
> faktycznego działania aplikacji Dzik OS 0.11.0 (art. 30 RODO —
> rejestr czynności przetwarzania). Nie jest poradą prawną.

## 1. Administrator danych i role

* **Administrator danych** klientów: trener prowadzący usługę.
  DECYZJA ADMINISTRATORA DANYCH: `[imię i nazwisko / nazwa firmy, adres,
  NIP, e-mail kontaktowy]`.
* **Operator techniczny** (jeżeli inny niż trener): utrzymuje instancję
  aplikacji; rola techniczna bez dostępu do danych zdrowotnych
  (konto ADMIN nie przechodzi przez bramki zgód — patrz PERMISSIONS.md).
  DECYZJA ADMINISTRATORA DANYCH: czy operator działa jako podmiot
  przetwarzający (wymaga umowy powierzenia).
* **Inspektor ochrony danych**: przy skali jednoosobowej działalności
  trenerskiej zwykle niewymagany — DECYZJA ADMINISTRATORA DANYCH po
  konsultacji prawnej (art. 37 RODO).

## 2. Podmioty przetwarzające (procesorzy) i odbiorcy

| Podmiot | Rola | Zakres danych | Region | Umowa powierzenia |
|---|---|---|---|---|
| Fly.io, Inc. | hosting aplikacji, bazy i plików | wszystkie dane aplikacji (w spoczynku na wolumenie) | Frankfurt (UE); siedziba dostawcy: USA | DECYZJA ADMINISTRATORA DANYCH: zawrzeć/zweryfikować DPA Fly.io + mechanizm transferu (SCC/DPF) |
| Dostawca poczty | powiadomienia e-mail | adres e-mail, neutralna treść (bez danych zdrowotnych) | zależny od wyboru | **Obecnie: `NullNotificationProvider` — nic nie jest wysyłane.** Aktywacja (Resend/SendGrid/Mailgun/SMTP) = DECYZJA ADMINISTRATORA DANYCH + wpis tutaj i w polityce prywatności |
| Dostawca push | doręczanie Web Push | techniczny endpoint subskrypcji; treść szyfrowana E2E, bez danych zdrowotnych | zależny od przeglądarki użytkownika (Mozilla/Google/Apple) | wynika z opt-in użytkownika w przeglądarce; za zgodą kategorii `przypomnienia` |
| Dostawca AI | podsumowania raportów (propose-only) | treść raportu tygodniowego (dane zdrowotne!) | zależny od wyboru | **Obecnie: `NullAIProvider` — nic nie jest wysyłane.** Aktywacja = DECYZJA ADMINISTRATORA DANYCH + DPIA (patrz RODO_DPIA.md) + zgoda klienta kategorii `funkcje_ai` |
| Operator płatności | — | — | — | **Brak.** Aplikacja prowadzi wyłącznie ewidencję statusów płatności; nie przetwarza danych kart ani nie inicjuje płatności online |

**Zasoby zewnętrzne:** czcionki (@fontsource, self-hosting) i wszystkie
statyki są serwowane z własnej domeny — **zero** zapytań do Google
Fonts/CDN podmiotów trzecich podczas korzystania z aplikacji.

**Monitoring/analityka:** aplikacja nie zawiera narzędzi analitycznych
ani śledzących; „monitoring" w aplikacji oznacza wyłącznie funkcję
przeglądu postępów przez trenera. Logi platformy hostingowej (Fly.io)
mogą zawierać standardowe metadane HTTP — DECYZJA ADMINISTRATORA DANYCH:
zweryfikować retencję logów u dostawcy i odnotować ją tutaj. Logi
aplikacji nie zawierają danych zdrowotnych (zasada konstytucyjna
Human OS, egzekwowana w kodzie audytu).

## 3. Czynności przetwarzania

| # | Czynność | Kategorie osób | Kategorie danych | Cel | Podstawa | Odbiorcy | Retencja |
|---|---|---|---|---|---|---|---|
| 1 | Prowadzenie kont użytkowników | klienci, trener, admin | e-mail, imię i nazwisko, skrót hasła, sesje | świadczenie usługi | 6(1)(b) | hosting | do usunięcia konta |
| 2 | Współpraca trenerska (profil, dokumenty, płatności — ewidencja) | klienci | profil współpracy, dokumenty, statusy płatności | wykonanie umowy | 6(1)(b) | trener, hosting | czas współpracy + okres retencji (§4) |
| 3 | Trening (plany, wyniki, harmonogram, cele) | klienci | dane treningowe | wykonanie umowy | 6(1)(b) | trener, hosting | jw. |
| 4 | Komunikacja (wiadomości, konsultacje) | klienci | treść wiadomości, załączniki, rezerwacje | wykonanie umowy | 6(1)(b) | trener, hosting | jw. |
| 5 | Dane zdrowotne (pomiary, raporty, obserwacje, urazy) | klienci | **art. 9**: masa, obwody, sen, stres, ból, urazy | bezpieczne prowadzenie treningu | **9(2)(a) — wyraźna zgoda** | trener, hosting | jw.; usuwane/anonimizowane na żądanie |
| 6 | Żywienie i alergie (dieta, dziennik, alergie) | klienci | **art. 9**: alergie, nietolerancje, dieta | plan żywieniowy | **9(2)(a)** | trener, hosting | jw. |
| 7 | Zdjęcia progresu | klienci | **art. 9 / wizerunek**: zdjęcia sylwetki (EXIF usuwany przy zapisie) | ocena postępów | **9(2)(a)** | trener, hosting | jw.; pliki fizycznie usuwane przy usunięciu konta |
| 8 | Powiadomienia push i przypomnienia | użytkownicy z opt-in | endpoint subskrypcji push | przypomnienia | 6(1)(a) — zgoda | dostawca push przeglądarki | do wycofania zgody |
| 9 | Funkcje AI (podsumowania raportów) | klienci ze zgodą | treść raportu (art. 9) | wsparcie trenera (propose-only) | 9(2)(a) | dostawca AI (obecnie brak — Null) | do wycofania zgody |
| 10 | Marketing trenera | klienci ze zgodą | e-mail, imię | informacje o usługach | 6(1)(a) | trener | do wycofania zgody |
| 11 | Ewidencja rozliczeń | klienci | pakiet, kwoty, terminy, statusy | rozliczenia i obowiązki podatkowe | 6(1)(b), 6(1)(c) | trener, księgowość trenera | okres wymagany przepisami podatkowymi (5 lat od końca roku) |
| 12 | Dziennik zdarzeń (audyt) | wszyscy | identyfikatory operacji, typy zdarzeń, hashe (bez treści zdrowotnych) | bezpieczeństwo, rozliczalność | 6(1)(f) | admin (weryfikacja łańcucha) | trwale (łańcuch niemutowalny) |

## 4. Retencja

* **Aktywna współpraca:** dane przechowywane przez czas współpracy.
* **Po zakończeniu współpracy:** DECYZJA ADMINISTRATORA DANYCH —
  rekomendowany, skończony okres (np. 12 miesięcy), po którym
  administrator usuwa/anonimizuje dane nieobjęte innymi obowiązkami;
  aplikacja nie usuwa niczego automatycznie po czasie (funkcja
  nieimplementowana — patrz DEFERRED_FEATURES.md).
* **Na żądanie klienta:** natychmiastowa anonimizacja + fizyczne
  usunięcie plików („Usuń konto i dane" — patrz polityka prywatności §8).
* **Dane rozliczeniowe:** kwoty/terminy/statusy — 5 lat od końca roku
  podatkowego (art. 6(1)(c)); treści opisowe usuwane przy anonimizacji.
* **Dziennik zdarzeń:** trwale (niemutowalny łańcuch, wyłącznie
  identyfikatory/typy operacji — rozliczalność wobec samego klienta).
* **Kopie zapasowe:** DECYZJA ADMINISTRATORA DANYCH — skonfigurować
  i opisać: częstotliwość snapshotów wolumenu (Fly.io), okres ich
  przechowywania oraz fakt, że dane usunięte z aplikacji mogą pozostawać
  w kopiach do wygaśnięcia rotacji (należy podać maksymalny okres,
  np. 30 dni) — patrz polityka prywatności §7.
* **Pliki-sieroty:** automatycznie usuwane po 24 h (minimalizacja).

## 5. Środki techniczne i organizacyjne (art. 32)

* transmisja wyłącznie HTTPS; nagłówki bezpieczeństwa + CSP; brak CDN;
* hasła: bcrypt; wymuszona zmiana hasła startowego; limity prób;
  sesje: wyłącznie hash tokenu w bazie, unieważnianie serwerowe;
* izolacja: IDOR chroniony centralną bramką (`resolve_client_access`),
  odmowa = 404 + wpis audytowy; zgody per kategoria danych;
* pliki: walidacja typu po zawartości, EXIF/GPS usuwany, limity,
  `Cache-Control: no-store` dla danych prywatnych;
* push: treść nigdy nie zawiera danych zdrowotnych;
* audyt: hash-chained, append-only, weryfikowalny (`verify_chain`);
* szyfrowanie w spoczynku: **brak na poziomie aplikacji** — DECYZJA
  ADMINISTRATORA DANYCH: ocenić szyfrowanie wolumenu po stronie
  platformy hostingowej.

## 6. Powiązane dokumenty

* `POLITYKA_PRYWATNOSCI_SZKIC.md` — informacja dla podmiotów danych.
* `ZGODY_MODEL.md` — techniczny model kategorii zgód.
* `RODO_INCYDENTY.md` — proces obsługi incydentów.
* `RODO_DPIA.md` — ocena konieczności DPIA.
* `DATA_PROCESSING_MAP.md` — mapa danych per funkcja aplikacji.

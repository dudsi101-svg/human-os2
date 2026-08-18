# Świadomie odłożone funkcje — Dzik OS

Zgodnie z zakresem MVP (sekcja 13 briefu). Architektura ich nie blokuje.

## Poza zakresem pierwszej wersji (decyzja produktowa)

* publiczna sieć społecznościowa, feed, rankingi sylwetek;
* wideorozmowy i komunikator czasu rzeczywistego (obecnie: asynchroniczne
  wątki wiadomości);
* analiza techniki ćwiczeń przez computer vision;
* **autonomiczne (AI-driven) generowanie diety pozostaje poza zakresem** —
  od 0.4.0 istnieje baza produktów z makro i kompozytor diety
  (`POST /api/coach/diet-suggestion`), ale to wyłącznie deterministyczna
  arytmetyka nad produktami **wybranymi przez trenera**, propose-only,
  nic nie zapisuje automatycznie w planie klienta (patrz DATA_MODEL.md
  §Baza wiedzy);
* integracje z wearables;
* natywne aplikacje iOS/Android (jest instalowalna PWA);
* autonomiczny AI-coach; jakiekolwiek funkcje AI (patrz ADR-DZIK-001 §AI);
* marketplace trenerów / multi-tenant dla wielu firm.

## Odłożone technicznie (znane braki MVP)

* kopiowanie szablonu planu do klienta jednym kliknięciem (obecnie trener
  odtwarza układ w edytorze);
* reset hasła e-mailem (wymuszona zmiana hasła startowego — zrobione, 0.1.1);
* **prawdziwe wysyłanie e-maili** — interfejs providera gotowy
  (`notifications_provider.py`, wzorzec jak `payments_provider.py`) i
  podpięty do jednego triggera (niepokojąca obserwacja → e-mail do
  trenera), ale domyślny `NullNotificationProvider` niczego nie wysyła.
  Podłączenie realnego dostawcy (Resend/SendGrid/Mailgun/SMTP) to decyzja
  operatora — wymaga konta i kluczy API poza repozytorium;
* **prawdziwy dostawca AI** — analogiczny adapter (`ai_provider.py`,
  `NullAIProvider` domyślnie) podpięty pod dwa governed use case'y,
  oba propose-only i bramkowane zgodą klienta `funkcje_ai`:
  (1) podsumowanie raportu tygodniowego + szkic odpowiedzi dla trenera
  (przycisk „✨ Podsumowanie AI" w panelu trenera);
  (2) wersja robocza podsumowania konwersacyjnego onboardingu
  (`docs/ONBOARDING_AI.md`) — zatwierdza ją klient, potem trener.
  W obu wypadkach nic nie wysyła się ani nie publikuje automatycznie.
  Bez klucza dostawcy UI pokazuje jawny komunikat, nie udaje działania,
  a **cały onboarding działa end-to-end bez modelu** (tryb
  deterministyczny jest ścieżką domyślną, nie okrojoną). Kontrakt
  dostawcy (`propose_json`) jest przetestowany na atrapie w pięciu
  wariantach, więc podłączenie realnego modelu nie wymaga pisania
  nowych testów integracji. Samo podłączenie to decyzja operatora —
  wymaga klucza API poza repozytorium, uzupełnienia polityki
  prywatności o nazwę i region dostawcy oraz podbicia
  `CONSENT_DOC_VERSION` (patrz DATA_PROCESSING_MAP.md §AI);
* ~~powiadomienia push PWA~~ — ZROBIONE (0.6.x Web Push/VAPID, a od
  0.18.0 wspólny system powiadomień z centrum w aplikacji, preferencjami,
  cichymi godzinami i harmonogramem serwerowym — `docs/POWIADOMIENIA.md`);
  e-mail jako kanał awaryjny nadal wymaga skonfigurowania dostawcy przez
  operatora (`notifications_provider.py`);
* integracja z arkuszami zewnętrznymi (import z Excela) — eksport do
  Excela jest zrobiony (`/api/me/export.xlsx`), import w drugą stronę nie;
* webhook prawdziwego operatora płatności (interfejs providera gotowy:
  `payments_provider.py`);
* własne mierniki trenera w UI (API `metric_definitions` istnieje);
* edycja/archiwizacja dokumentów przez trenera w UI (API istnieje);
* automatyczne czyszczenie starych zadań przepisywania tekstu ze zdjęcia
  (`ocr_tasks`) — dziś wiersz żyje do zatwierdzenia, odrzucenia albo
  usunięcia konta; TTL (np. 30 dni) to DECYZJA ADMINISTRATORA DANYCH,
  patrz `OCR.md` §6;
* OCR plików PDF (dziś wyłącznie zdjęcia JPG/PNG/WEBP — renderowanie stron
  PDF nie mieści się w 512 MB RAM maszyny produkcyjnej, `OCR.md` §7);
* paginacja długich list (limity 200 rekordów w API);
* konto klienta u wielu trenerów naraz (model danych to dopuszcza,
  UI zakłada jednego trenera).

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
  `NullAIProvider` domyślnie) już podpięty pod jeden governed use case:
  podsumowanie raportu tygodniowego + szkic odpowiedzi dla trenera
  (przycisk „✨ Podsumowanie AI" w panelu trenera), zawsze propose-only
  (trener edytuje/zatwierdza, nic nie wysyła się automatycznie). Bez
  klucza dostawcy UI pokazuje jawny komunikat, nie udaje działania.
  Podłączenie realnego modelu (np. Claude API) to decyzja operatora —
  wymaga klucza API poza repozytorium i ustalenia minimalnego zakresu
  danych wysyłanych na zewnątrz (patrz DATA_PROCESSING_MAP.md §AI);
* powiadomienia push PWA (wymagają kluczy VAPID + subskrypcji service
  workera) — obecnie przypomnienia i flagi widoczne po wejściu do aplikacji;
* integracja z arkuszami zewnętrznymi (import z Excela) — eksport do
  Excela jest zrobiony (`/api/me/export.xlsx`), import w drugą stronę nie;
* webhook prawdziwego operatora płatności (interfejs providera gotowy:
  `payments_provider.py`);
* własne mierniki trenera w UI (API `metric_definitions` istnieje);
* edycja/archiwizacja dokumentów przez trenera w UI (API istnieje);
* paginacja długich list (limity 200 rekordów w API);
* konto klienta u wielu trenerów naraz (model danych to dopuszcza,
  UI zakłada jednego trenera).

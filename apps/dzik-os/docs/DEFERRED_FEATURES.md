# Świadomie odłożone funkcje — Dzik OS

Zgodnie z zakresem MVP (sekcja 13 briefu). Architektura ich nie blokuje.

## Poza zakresem pierwszej wersji (decyzja produktowa)

* publiczna sieć społecznościowa, feed, rankingi sylwetek;
* wideorozmowy i komunikator czasu rzeczywistego (obecnie: asynchroniczne
  wątki wiadomości);
* analiza techniki ćwiczeń przez computer vision;
* pełna baza produktów spożywczych i automatyczne generowanie diet;
* integracje z wearables;
* natywne aplikacje iOS/Android (jest instalowalna PWA);
* autonomiczny AI-coach; jakiekolwiek funkcje AI (patrz ADR-DZIK-001 §AI);
* marketplace trenerów / multi-tenant dla wielu firm.

## Odłożone technicznie (znane braki MVP)

* kopiowanie szablonu planu do klienta jednym kliknięciem (obecnie trener
  odtwarza układ w edytorze);
* reset hasła e-mailem i wymuszona zmiana hasła startowego (R-06);
* powiadomienia push PWA (obecnie przypomnienia widoczne po wejściu);
* webhook prawdziwego operatora płatności (interfejs providera gotowy:
  `payments_provider.py`);
* własne mierniki trenera w UI (API `metric_definitions` istnieje);
* edycja/archiwizacja dokumentów przez trenera w UI (API istnieje);
* paginacja długich list (limity 200 rekordów w API);
* konto klienta u wielu trenerów naraz (model danych to dopuszcza,
  UI zakłada jednego trenera).

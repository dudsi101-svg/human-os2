# Ocena konieczności DPIA — Dzik OS (wskazanie, nie porada prawna)

> **STATUS: WSKAZANIE TECHNICZNE DO DECYZJI ADMINISTRATORA DANYCH.**
> Dokument wskazuje przesłanki oceny skutków dla ochrony danych
> (DPIA, art. 35 RODO) na podstawie faktycznego działania aplikacji.
> Ostateczna decyzja i ewentualne przeprowadzenie DPIA należą do
> administratora danych, najlepiej z pomocą prawnika.

## 1. Przesłanki za przeprowadzeniem DPIA

Art. 35 ust. 3 lit. b RODO wymaga DPIA przy „przetwarzaniu **na dużą
skalę** szczególnych kategorii danych". Aplikacja przetwarza dane
szczególnej kategorii (art. 9): masę ciała i pomiary, ból, urazy, sen,
stres, alergie, dietę oraz zdjęcia sylwetki.

Wykaz UODO rodzajów operacji wymagających DPIA wymienia m.in. dane
dotyczące zdrowia oraz systematyczne monitorowanie osób (aplikacja
prowadzi regularny „monitoring postępów" klientów, w tym samopoczucia).

## 2. Przesłanki przeciw obowiązkowości

* Skala: jednoosobowa działalność trenera z kilkudziesięcioma klientami
  zwykle **nie** jest „dużą skalą" w rozumieniu motywu 91 RODO
  (analogia: indywidualna praktyka lekarska nie wymaga DPIA z mocy
  art. 35(3)(b)).
* Brak profilowania automatycznego, brak decyzji automatycznych,
  brak danych osób trzecich, brak śledzenia.

## 3. Wskazanie

* **Obecna postać (jeden trener, mała skala, brak AI, brak wysyłki
  e-mail):** DPIA prawdopodobnie nieobowiązkowa, ale ze względu na
  charakter danych (zdrowie + wizerunek) **rekomendowane** jest
  przeprowadzenie uproszczonej oceny ryzyka i jej udokumentowanie.
  DECYZJA ADMINISTRATORA DANYCH.
* **DPIA staje się mocno wskazana / konieczna przed:**
  1. podłączeniem realnego dostawcy AI (wysyłka raportów zdrowotnych
     poza system — obecnie `NullAIProvider`),
  2. skalowaniem do wielu trenerów / setek klientów (SaaS),
  3. podłączeniem dostawcy poczty z treściami wykraczającymi poza
     neutralne powiadomienia,
  4. integracją z urządzeniami (wearables) lub nowymi kategoriami
     danych zdrowotnych.

## 4. Materiał wejściowy do DPIA (gotowy w repo)

* opis operacji i celów: `RODO_REJESTR_CZYNNOSCI.md`,
  `DATA_PROCESSING_MAP.md`;
* niezbędność i proporcjonalność: model zgód per kategoria
  (`ZGODY_MODEL.md`), minimalizacja (EXIF, sieroty, brak IP przy
  zgodach, push bez treści zdrowotnych);
* środki bezpieczeństwa: `PERMISSIONS.md`, nagłówki/CSP, audyt
  hash-chained, izolacja IDOR (testy);
* ryzyka i luki znane: `RISK_REGISTER.md` (m.in. brak szyfrowania w
  spoczynku na poziomie aplikacji, kopie zapasowe do skonfigurowania).

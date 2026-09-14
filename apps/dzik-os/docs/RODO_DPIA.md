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

## 3a. Ekran zdrowotny wywiadu kalorycznego (od 0.77.0)

Wywiad „Zapotrzebowanie kaloryczne” zbiera od 0.77.0 pięć deklaracji
zdrowotnych (ciąża/karmienie, choroby metaboliczne, zaburzenia odżywiania,
leki wpływające na masę ciała, brak miesiączki) plus wolne pole. To
**dane szczególnej kategorii (art. 9)** — ta sama klasa, co pomiary,
urazy i alergie już zbierane w wywiadzie wstępnym; nowa jest ich treść,
nie kategoria, więc wskazanie z §3 nie zmienia się co do zasady.

Przesłanki, które ograniczają ryzyko tego rozszerzenia:

* **Niezbędność.** Każda z pięciu deklaracji zmienia wynik albo
  ostrzeżenie: ciąża/karmienie i brak miesiączki wyłączają deficyt,
  zaburzenia odżywiania ukrywają liczby przed klientem, choroby i leki
  zapalają ostrzeżenie o konsultacji lekarskiej. Żadna nie jest zbierana
  „na zapas”.
* **Dobrowolność.** Wszystkie pytania są opcjonalne i każde ma odpowiedź
  „wolę nie odpowiadać” (przy zaburzeniach odżywiania: „wolę omówić
  z trenerem”). Brak odpowiedzi nie blokuje wyniku.
* **Zgoda przed pytaniem.** Bez aktywnej zgody `health_data` pytanie nie
  pada w ogóle — nie jest zadawane i zapisywane, a potem ukrywane.
* **Minimalizacja przy przetwarzaniu wtórnym.** Odpowiedzi zdrowotne nie
  są kopiowane do tabeli wyników; kopiowany jest wyłącznie skutek (flaga).
* **Brak automatycznej decyzji.** Aplikacja proponuje liczbę i ostrzeżenie;
  decyzję podejmuje człowiek (trener), a przy flagach medycznych komunikat
  kieruje do lekarza zamiast liczyć „bezpieczną” wersję planu.
* **Brak AI i brak wysyłki poza system** — wynik liczy jawny wzór
  (`wywiad/zapotrzebowanie.py`), bez dostawcy zewnętrznego.

**Wskazanie:** rozszerzenie nie tworzy nowej przesłanki obowiązkowej DPIA
(skala i brak profilowania bez zmian), ale należy do materiału
uproszczonej oceny ryzyka rekomendowanej w §3 — i powinno być w niej
wymienione wprost, bo poszerza zakres danych art. 9 o deklaracje
dotyczące ciąży i chorób. DECYZJA ADMINISTRATORA DANYCH.

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

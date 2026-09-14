# Model suwaków cardio — trzy cele na jednej osi intensywności

<!-- Kopia z pakietu zleceń właściciela (PAKIET_ZLECEN_2026-09-14.md §9, sesja tylko-do-odczytu
14.09.2026), dodana do repozytorium w rundzie 0.73.0 (P2 h z przeglądu PR #75), bo kod
i dokumenty odwołują się do tego pliku. Treść bez zmian; nagłówki #### → ##. -->

**Status:** propozycja modelu do przeglądu trenera (Łukasz) i do implementacji w zleceniu
`PROMPT_writer_cardio-i-rozgrzewka.md`. Autor: sesja tylko-do-odczytu, 14.09.2026.
Poziomy pewności oznaczone: **[A]** zgodne z wytycznymi/metaanalizami, **[B]** dobrze
opisane w literaturze, ale z dużą zmiennością osobniczą, **[C]** synteza własna /
praktyka trenerska — do potwierdzenia przez trenera. Nic z tego nie jest poradą medyczną;
aplikacja proponuje, trener decyduje (zasada propose-only, `docs/PERMISSIONS.md` §5.5).

## 1. Po co suwaki i na czym je oprzeć

Właściciel: trzy główne cele reprezentowane suwakami, które sumują się do całości
(domyślnie po 1/3; przesunięcie jednego zabiera pozostałym), a ustawienie ma sugerować
**tętno, obciążenie, tempo i czas**, po czym wybiera się jedno z urządzeń.

Istniejące modele, na które da się to odwzorować (nie wymyślamy własnej fizjologii):

| Model | Co daje | Pewność |
|---|---|---|
| **Trzy strefy wg progów (Seiler):** Z1 poniżej pierwszego progu (rozmowa swobodna), Z2 między progami, Z3 powyżej drugiego progu | jedna oś intensywności, na której leżą wszystkie trzy cele; rozkład polaryzowany 80/20 u wytrzymałościowców | [A] dla istnienia progów i stref, [B] dla przełożenia na %HRmax bez testu |
| **Karvonen (rezerwa tętna, HRR):** tętno docelowe = HRspocz + % × (HRmax − HRspocz) | lepsze niż %HRmax, gdy znamy tętno spoczynkowe | [A] |
| **HRmax z wieku:** Tanaka 208 − 0,7 × wiek (błąd ±10 ud./min); 220 − wiek gorsze | punkt startowy, gdy brak testu; zawsze jako **zakres**, nie liczba | [A] dla wzoru, [B] dla dokładności u konkretnej osoby |
| **Kategorie intensywności ACSM:** umiarkowana ≈ 64–76 % HRmax (40–59 % HRR), intensywna ≈ 77–95 % HRmax (60–89 % HRR) | wspólny język z wytycznymi zdrowia publicznego | [A] |
| **Fatmax (Achten & Jeukendrup):** maksymalne utlenianie tłuszczu ok. 60–65 % VO2max (≈ 65–75 % HRmax), szeroka strefa 55–72 % VO2max, duża zmienność osobnicza | podstawa dla celu „spalanie tłuszczu” | [B] |
| **Interwały pod VO2max (Helgerud 4×4 min przy 90–95 % HRmax; metaanaliza Milanović: HIIT > ciągły dla VO2max)** | podstawa dla celu „wydolność” | [A] |
| **Test mowy (Foster) i RPE (Borg CR10)** | zamiennik tętna, gdy brak pulsometru albo tętno nie ma sensu (beta-blokery) | [A] |

**Zastrzeżenie, które musi być w UI (uczciwość, KARTA §0.3):** „spalanie tłuszczu” w
strefie Fatmax to udział tłuszczu jako paliwa **podczas** wysiłku; o utracie tkanki
tłuszczowej decyduje bilans energetyczny w tygodniach. Metaanalizy (m.in. Keating 2017,
Wewege 2017) pokazują podobną utratę tłuszczu dla interwałów i wysiłku ciągłego przy tym
samym wydatku energii [A]. Dlatego cel 1 nazywamy w UI **„Redukcja (wydatek energii)”**
i pokazujemy szacowany wydatek kcal, a nie obiecujemy „spalania tłuszczu”.

## 2. Trzy cele — nazwy i anatomia

Właściciel podał dwa: utrata tkanki, wydolność. Trzeci ma być „najtrafniejszy”. Kandydaci:

| Trzeci cel | Za | Przeciw |
|---|---|---|
| **Regeneracja i baza tlenowa (Z1)** — rekomendacja | rozciąga oś intensywności w dół (R < F < W), więc suwaki nie są redundantne; aktywna regeneracja to realna praktyka trenerska między dniami siłowymi; najniższe ryzyko | mniej „sprzedażowa” nazwa |
| Wytrzymałość (długi czas, Z2) | popularne słowo | prawie pokrywa się intensywnością z redukcją — suwak nie zmieniałby wyników |
| Moc / szybkość (Z3, sprinty) | wyraźnie inny | nakłada się z wydolnością, wyższe ryzyko u początkujących |

**Rekomendowana trójka (nazwy w UI):**
1. **Redukcja** — wydatek energii przy umiarkowanej intensywności, długi czas (Fatmax/Z2 dolna).
2. **Wydolność** — VO2max, interwały wysokiej intensywności (Z3).
3. **Regeneracja** — baza tlenowa, niska intensywność, krótko (Z1).

## 3. Mechanika suwaków (simpleks)

Wagi `w = (wR, wW, wG)` dla (Redukcja, Wydolność, reGeneracja), każda 0–1, `wR + wW + wG = 1`.
Domyślnie `(1/3, 1/3, 1/3)`. Przesunięcie jednego suwaka o `+d` zabiera pozostałym
proporcjonalnie do ich bieżących wag (jeśli oba równe — po `d/2`); suwak zablokowany
(kłódka) nie oddaje. To jest ten sam mechanizm, co procentowy rozkład makro w kreatorze
diety (suma 100) — do skopiowania. Prezentacja: trzy suwaki + trójkąt (ternary) jako
podgląd, wartości zaokrąglone do 5 %.

## 4. Kotwice i mieszanie

Każdy cel ma kotwicę: intensywność (%HRmax, %HRR, RPE CR10, test mowy), czas, strukturę.

| Cel | %HRmax | %HRR | RPE | Test mowy | Czas (min) | Struktura |
|---|---|---|---|---|---|---|
| Regeneracja (G) | 55–65 | 35–50 | 2–3 | pełne zdania swobodnie | 20–30 | ciągła |
| Redukcja (R) | 65–75 | 50–65 | 4–5 | zdania, lekko przerywane | 40–60 | ciągła (lub 2 bloki) |
| Wydolność (W) | 85–95 w pracy / 60–70 w przerwie | 75–90 / 45–55 | 7–9 / 3 | pojedyncze słowa | 20–30 łącznie (np. 4×4 min + przerwy 3 min) | interwały |

Pewność kotwic: [A] dla G/W, [B] dla R (Fatmax). Wszystkie liczby to **zakresy**.

**Mieszanie [C — synteza własna, do przeglądu trenera]:**
* intensywność ciągła = `Σ w_i × środek_i` (środek: G 60, R 70, W 90 %HRmax; w przerwach
  interwału stała 65);
* czas = `Σ w_i × środek_czasu_i` (G 25, R 50, W 25 min), zaokrąglony do 5 min;
* struktura wg `wW`: `wW ≥ 0,5` → interwały (4×4 dla zaawansowanych, 6×2 dla średnich,
  8×1 min lub 30/30 dla początkujących); `0,25 ≤ wW < 0,5` → „tempo” (ciągłe 78–85 % albo
  2×10 min); `wW < 0,25` → ciągłe;
* poziom zaawansowania (POCZATKUJACY/SREDNIOZAAWANSOWANY/ZAAWANSOWANY, jak w katalogu
  ćwiczeń) obniża sufit: początkujący maks. 85 % HRmax i interwały krótkie, czas −20 %;
* wynik prezentowany jako zakres ±5 % HRmax (niepewność wzoru HRmax), nigdy jako
  jedna liczba.

**Przykłady kontrolne (do testów jednostkowych):** `(1/3,1/3,1/3)` → ok. 73 % HRmax
ciągłe, 33 → 35 min, tempo umiarkowane; `(0,1,0)` → interwały 90 % wg poziomu, 25 min;
`(1,0,0)` → 70 %, 50 min ciągłe; `(0,0,1)` → 60 %, 25 min ciągłe; `(0.5,0.5,0)` → 80 %,
„tempo” 2×10 min, 38 → 40 min.

## 5. Przełożenie na urządzenie (tempo i obciążenie) [C, do przeglądu trenera]

Intensywność jest jedna (tętno/RPE); urządzenie dostaje **dwie gałki**, które ją
realizują. Sugestie startowe (klient koryguje do tętna/RPE, aplikacja to mówi wprost):

| Urządzenie | Gałka „tempo” | Gałka „obciążenie” | G | R | W (praca) |
|---|---|---|---|---|---|
| Rowerek | kadencja (obr./min) | opór (poziom) | 70–80 rpm, opór niski | 80–90 rpm, opór umiarkowany | 90–100 rpm, opór wysoki |
| Bieżnia (bieg/marsz) | prędkość (km/h) | nachylenie (%) | marsz 5–6, 0–2 % | trucht 7–9 albo marsz 6–6,5 przy 3–5 % | bieg 10–14, 1 % |
| Bieżnia skos / chód pod górę | prędkość 4,5–6 km/h | nachylenie 5–15 % | 5 km/h, 5 % | 5,5 km/h, 8–12 % | 6 km/h, 12–15 % (interwały nachyleniem, nie biegiem — niski wpływ na stawy) |
| Steper | kroki/min | poziom oporu | 40–50 | 55–70 | 75–90 |
| Wioślarz | uderzenia/min (spm) | opór (damper 3–5) / czas na 500 m | 18–22 spm | 22–26 spm | 28–32 spm |

Zasada: pokazujemy „zacznij od…, dojdź do tętna/RPE z zakresu”, bo urządzenia różnią
się kalibracją. Wydatek energii: przybliżenie z METs (Compendium of Physical Activities)
× masa × czas, oznaczone jako szacunek [B].

## 6. Dane wejściowe i bramki

* **Wiek** (z profilu / daty urodzenia) → HRmax Tanaka; brak wieku → tylko RPE i test mowy.
* **Tętno spoczynkowe** (opcjonalne, klient wpisuje) → Karvonen zamiast %HRmax.
* **Poziom** z profilu/wywiadu (doświadczenie) → sufity z §4.
* **Bramka zdrowotna (propose-only, jak konfigurator):** flagi z wywiadu
  (choroby układu krążenia, nadciśnienie, ciąża, leki wpływające na tętno, np.
  beta-blokery — tętno bezużyteczne → tylko RPE, cukrzyca, zawroty/omdlenia) →
  propozycja pokazuje się **tylko trenerowi** z ostrzeżeniem i wymaga jego akceptacji;
  klient nigdy nie dostaje propozycji bez publikacji przez trenera. Klasyfikacja
  danych: dane zdrowotne (domena `dane_zdrowotne`, zgoda), jak w konfiguratorze.
* Brak pulsometru → wariant „RPE + test mowy” jako równoprawny.

## 7. Ślad decyzji („Dlaczego?”)

Każda propozycja zapisuje: wagi suwaków, poziom, źródło HRmax (Tanaka/Karvonen/brak),
kotwice użyte, reguły struktury, wersję modelu (`cardio_model_v1`) i listę zastrzeżeń —
w tym samym formacie, co ślad konfiguratora (`H_LAYOUT`/`H_VOLUME`), żeby zakładka
Wiedza → „Dlaczego?” mogła to pokazać klientowi po publikacji.

## 8. Co model świadomie pomija (v1)

Testy progowe (LT1/LT2, FTP), strefy mocy, HRV, periodyzacja tygodniowa cardio vs
siła (interferencja), spalanie „po treningu” (EPOC — pomijalne w praktyce), ciąża
i choroby jako indywidualne protokoły (tylko bramka). To są kandydaci na v2 po
pilotażu z trenerem.

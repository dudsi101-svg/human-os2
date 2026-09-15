# Wywiad: zapotrzebowanie kaloryczne — specyfikacja

Wersja 1.0 · 13.09.2026 · Moduł: zakładka „Wywiady" · Status: do przeglądu

---

## 1. Cel

Nowy wywiad w zakładce „Wywiady" zbiera dane potrzebne do policzenia zapotrzebowania energetycznego klienta i wylicza **bilans kaloryczny**: podstawową przemianę materii (PPM), całkowitą przemianę materii (CPM), cel kaloryczny po uwzględnieniu celu sylwetkowego oraz proponowane makro. Wynik jest widoczny dla klienta i trenera, a trener może go jednym kliknięciem przenieść do formularza przypisania diety (moduł szablonów).

## 2. Cele i miary

| Cel | Miara |
|---|---|
| Klient wypełnia wywiad samodzielnie w < 4 min | czas od otwarcia do zapisu |
| Trener nie liczy nic ręcznie | ≥ 90 % przypisań diety startuje z wyniku wywiadu |
| Wynik jest zrozumiały dla klienta | każda liczba ma jednozdaniowe wyjaśnienie „skąd to" |
| Wynik jest wiarygodny | wzory i mnożniki jawnie nazwane, z zakresem niepewności |

## 3. Poza zakresem (v1)

- Import danych z zegarków / aplikacji zdrowotnych (P2 — zaprojektuj tak, by kroki dzienne dało się później podpiąć).
- Automatyczna korekta celu na podstawie tygodniowych ważeń (P1, osobna specyfikacja „adaptacja kalorii").
- Pomiary składu ciała metodą bioimpedancji w aplikacji — klient wpisuje % tkanki tłuszczowej, jeśli go zna.
- Diagnostyka medyczna. Wywiad nie zastępuje konsultacji lekarskiej; przy flagach medycznych (sekcja 6.4) aplikacja pokazuje komunikat, nie liczy „bezpiecznej" wersji.

---

## 4. Pytania wywiadu

Kolejność = kolejność ekranów. Jeden ekran = jedna grupa. Pola oznaczone ★ są wymagane do obliczenia; reszta poprawia dokładność.

### Ekran 1 — Dane podstawowe
| Pole | Typ | Walidacja |
|---|---|---|
| ★ Płeć biologiczna | wybór: kobieta / mężczyzna | do wzoru PPM |
| ★ Data urodzenia | data | wiek 16–90; < 18 → flaga „małoletni" (sekcja 6.4) |
| ★ Wzrost | cm | 130–230 |
| ★ Masa ciała | kg, 1 miejsce po przecinku | 35–250; podpowiedź „waż się rano, po toalecie, przed jedzeniem" |
| % tkanki tłuszczowej | liczba | 3–60; opcjonalne; jeśli podane → dodatkowy wzór (Katch-McArdle) |

### Ekran 2 — Aktywność poza treningiem (NEAT)
★ Jedno pytanie, cztery opisowe opcje — bez liczb, bo klienci ich nie znają:

| Opcja | Opis w UI | Kod |
|---|---|---|
| Siedząca | „Praca przy biurku, samochód, mało chodzenia (< 5 000 kroków)" | `neat_1` |
| Lekka | „Trochę chodzenia, stanie, lekkie obowiązki (5–8 tys. kroków)" | `neat_2` |
| Umiarkowana | „Sporo na nogach: sprzedaż, opieka, częste spacery (8–12 tys.)" | `neat_3` |
| Wysoka | „Praca fizyczna, budowa, magazyn, rolnictwo (> 12 tys.)" | `neat_4` |

Opcjonalnie: średnia dzienna liczba kroków (jeśli klient ma zegarek) — nadpisuje wybór opisowy.

### Ekran 3 — Trening
| Pole | Typ |
|---|---|
| ★ Treningi siłowe / tydzień | 0–7 |
| ★ Średni czas treningu siłowego | 30 / 45 / 60 / 75 / 90+ min |
| ★ Treningi cardio lub sport / tydzień | 0–7 |
| ★ Średni czas i intensywność cardio | czas: jak wyżej; intensywność: lekka (rozmowa swobodna) / umiarkowana (rozmowa urywana) / wysoka (nie da się rozmawiać) |
| Staż treningowy | < 1 roku / 1–3 lata / > 3 lata (wpływa na realistyczne tempo zmian, sekcja 5.4) |

### Ekran 4 — Cel
| Pole | Typ |
|---|---|
| ★ Cel | redukcja tkanki tłuszczowej / utrzymanie / budowa masy mięśniowej / rekompozycja |
| ★ Tempo | łagodne / umiarkowane / szybkie (opis w sekcji 5.3) |
| Masa docelowa | kg, opcjonalne — do wyliczenia orientacyjnego czasu |
| Preferencja białka | standard / wysoka (dla siłowych) — domyślnie z celu |

### Ekran 5 — Zdrowie i kontekst (flagi)
Pytania tak/nie, każde „tak" → flaga w wyniku (sekcja 6.4):
- ciąża lub karmienie piersią,
- zdiagnozowana choroba tarczycy, cukrzyca, choroba nerek lub wątroby,
- zaburzenia odżywiania obecnie lub w przeszłości,
- leki wpływające na masę ciała (np. sterydy, leki psychotropowe, insulina),
- brak miesiączki > 3 miesiące (dla kobiet),
- wolne pole: „Coś, co trener powinien wiedzieć".

---

## 5. Obliczenia

Wszystkie wzory jawne, ze źródłem. Poziom pewności każdego kroku oznaczony w wyniku.

### 5.1 PPM (podstawowa przemiana materii)

**Wzór główny — Mifflin-St Jeor (1990):**
- mężczyźni: `PPM = 10·masa + 6,25·wzrost − 5·wiek + 5`
- kobiety: `PPM = 10·masa + 6,25·wzrost − 5·wiek − 161`

**Jeśli podano % tkanki tłuszczowej — Katch-McArdle:**
- `LBM = masa · (1 − %tł/100)`
- `PPM = 370 + 21,6 · LBM`

Gdy oba dostępne, wynik pokazuje oba i **używa Katch-McArdle**, jeśli różnica > 10 % — bo przy nietypowym składzie ciała (bardzo umięśnieni lub bardzo otyli) Mifflin myli się najbardziej. Różnicę pokaż trenerowi.

*Pewność:* wysoka dla populacji ogólnej; błąd indywidualny ±10 %. To trzeba napisać klientowi wprost.

### 5.2 CPM (całkowita przemiana materii)

Nie używaj jednego mnożnika PAL (1,2–1,9) — zlewa NEAT i trening, a klienci zawyżają. Licz addytywnie:

`CPM = PPM · mnożnik_NEAT + energia_treningu_dzienna + TEF`

**Mnożnik NEAT** (poza treningiem):
| Kod | Mnożnik |
|---|---|
| neat_1 | 1,20 |
| neat_2 | 1,35 |
| neat_3 | 1,50 |
| neat_4 | 1,70 |
| kroki (jeśli podano) | 1,20 + 0,04 · (kroki/1000 − 4), ograniczone do [1,15; 1,85] |

**Energia treningu** (kcal na sesję, z masy ciała; wartości MET zaokrąglone z Compendium of Physical Activities):
| Rodzaj | kcal/min ≈ MET · masa · 0,0175 |
|---|---|
| siłowy | MET 5,0 (średnia z przerwami) |
| cardio lekkie | MET 4,0 |
| cardio umiarkowane | MET 7,0 |
| cardio wysokie | MET 10,0 |

`energia_treningu_dzienna = Σ (sesje_tyg · minuty · kcal/min) / 7`

**TEF** (termiczny efekt pożywienia): 10 % · (PPM·mnożnik_NEAT + trening).

*Pewność:* średnia. NEAT to największe źródło błędu (±200–300 kcal). Wynik zawsze pokazuj jako **zakres** CPM ±7 %.

### 5.3 Cel kaloryczny

| Cel | Tempo | Korekta od CPM |
|---|---|---|
| Redukcja | łagodne | −10 % |
| | umiarkowane | −20 % |
| | szybkie | −25 % (maks.; nigdy poniżej PPM·1,1 i nigdy poniżej 1 200 kcal K / 1 500 kcal M) |
| Utrzymanie | — | 0 |
| Masa | łagodne | +5 % |
| | umiarkowane | +10 % |
| | szybkie | +15 % (ostrzeżenie o przyroście tłuszczu) |
| Rekompozycja | — | −5 %, białko „wysokie" |

Jeśli korekta narusza dolne ograniczenie → cel = ograniczenie, flaga `DEFICYT_OGRANICZONY` z wyjaśnieniem.

### 5.4 Oczekiwane tempo i czas

- Redukcja: deficyt tygodniowy / 7 700 kcal ≈ kg tygodniowo (orientacyjnie, pokaż jako „~0,4–0,6 kg/tydz.").
- Masa: realistyczny przyrost mięśni zależy od stażu: < 1 roku 0,5–1 %/mies. masy ciała, 1–3 lata 0,25–0,5 %, > 3 lata < 0,25 %. Pokaż, żeby klient nie oczekiwał cudów.
- Jeśli podano masę docelową → orientacyjny czas z zaznaczeniem „w praktyce dłużej, tempo zwalnia".

### 5.5 Makro (propozycja startowa)

| Cel | Białko | Tłuszcz | Węgle |
|---|---|---|---|
| Redukcja | 1,8–2,2 g/kg (przy % tł. > 30: liczone z masy docelowej lub LBM) | 0,8–1,0 g/kg, min. 20 % kcal | reszta |
| Utrzymanie | 1,6 g/kg | 1,0 g/kg | reszta |
| Masa | 1,8 g/kg | 1,0 g/kg | reszta |
| Rekompozycja | 2,2 g/kg | 0,9 g/kg | reszta |

Preferencja „wysoka" → górna granica zakresu. Wynik w gramach i %, gotowy do przekazania do modułu szablonów (`mode: "manual"` z gramami).

---

## 6. Wynik: „Bilans kaloryczny"

### 6.1 Widok klienta (prosty)

```
Twoje zapotrzebowanie
  Spoczynek (PPM)        1 620 kcal   „Tyle spala Twoje ciało, gdybyś cały dzień leżał"
  Cały dzień (CPM)       2 350 kcal   (zakres 2 190–2 510)   „Z Twoją aktywnością i treningami"
  Twój cel               1 880 kcal   „Redukcja, tempo umiarkowane: −20 %"
  Makro                  B 150 g · T 65 g · W 174 g
  Oczekiwane tempo       ~0,4–0,5 kg tygodniowo
```
Plus jedno zdanie: „To punkt startowy. Po 2–3 tygodniach trener skoryguje kalorie na podstawie Twoich ważeń."

### 6.2 Widok trenera (pełny)

Wszystko z widoku klienta plus:
- oba PPM (Mifflin / Katch), jeśli dostępne, z różnicą,
- rozbicie CPM: PPM × NEAT, trening/dzień, TEF,
- wszystkie odpowiedzi z wywiadu,
- flagi zdrowotne i ograniczenia (sekcja 6.4),
- historia wywiadów klienta (każde wypełnienie = nowa wersja; porównanie masy i CPM w czasie),
- przycisk **„Użyj w przypisaniu diety"** → otwiera moduł szablonów z wypełnionym kcal, makro, masą i wykluczeniami,
- możliwość ręcznego nadpisania celu z obowiązkowym polem „powód" (zapisywanym w historii).

### 6.3 Zapis
`CalorieInterview` (wersjonowany): `client_id, created_at, answers JSON, results JSON (PPM_mifflin, PPM_katch, CPM, CPM_min, CPM_max, target_kcal, macro, flags[], formulas_version), trainer_override {kcal, macro, reason, at}`. Wynik przeliczany w momencie zapisu i zamrażany — zmiana wzorów w przyszłości nie zmienia starych wyników (`formulas_version`).

### 6.4 Flagi i ograniczenia

| Flaga | Zachowanie |
|---|---|
| `MALOLETNI` (< 18) | wynik liczony, ale nie pokazywany klientowi; trener widzi komunikat „wymaga zgody opiekuna i ostrożności — wzory dla dorosłych" |
| `CIAZA_KARMIENIE` | brak deficytu (cel = CPM lub CPM + 300/500); komunikat o konsultacji lekarskiej |
| `CHOROBA_METABOLICZNA`, `LEKI` | wynik liczony normalnie; widoczne ostrzeżenie dla trenera „skonsultuj z lekarzem prowadzącym" |
| `ZABURZENIA_ODZYWIANIA` | **klient nie widzi liczb** (kcal, deficyt, tempo) — widzi tylko „Trener przygotuje plan"; trener widzi wszystko z wyraźnym ostrzeżeniem |
| `BRAK_MIESIACZKI` | brak deficytu domyślnie; ostrzeżenie o RED-S dla trenera |
| `DEFICYT_OGRANICZONY` | cel podniesiony do minimum, wyjaśnienie |
| `BMI_SKRAJNE` (< 17 lub > 40) | ostrzeżenie o ograniczonej trafności wzorów |

---

## 7. Wymagania

### P0
- [ ] Wywiad 5 ekranów z walidacją, zapis wersjonowany.
- [ ] Moduł obliczeń jako czysta funkcja `compute(answers) → results` (referencja: `calorie_calc.py`).
- [ ] Widok klienta i trenera bilansu; flagi zgodnie z 6.4.
- [ ] Przycisk „Użyj w przypisaniu diety" (integracja z modułem szablonów).
- [ ] Historia wywiadów u trenera.

### P1
- [ ] Nadpisanie celu przez trenera z powodem.
- [ ] Przypomnienie klientowi o ponownym wypełnieniu po zmianie masy > 3 kg lub po 8 tygodniach.
- [ ] Wykres masy i CPM w czasie.

### P2
- Integracja kroków z zegarka (pole „kroki" już istnieje).
- Adaptacja kalorii z ważeń.

### Kryteria akceptacji (testy)
- Mężczyzna 30 l., 180 cm, 80 kg → PPM Mifflin = 1 780 kcal (dokładnie).
- Kobieta 25 l., 165 cm, 60 kg → PPM = 1 345 kcal.
- 80 kg, 20 % tł. → Katch = 1 752 kcal (±1).
- Siedząca praca, 3 × 60 min siłowy, 0 cardio, 80 kg: trening/dzień = 3·60·(5·80·0,0175)/7 = 180 kcal; CPM = (1 780·1,20 + 180)·1,10 = 2 548 kcal.
- Redukcja „szybkie" u kobiety 1 345 PPM: cel nie schodzi poniżej max(1 480, 1 200) = 1 480 (flaga `DEFICYT_OGRANICZONY`).
- Flaga `ZABURZENIA_ODZYWIANIA` → odpowiedź API dla roli klient nie zawiera pól `kcal`, `target_kcal`, `deficit`, `pace`.
- `MALOLETNI` → brak wyniku w widoku klienta.
- Każdy zapisany wywiad ma `formulas_version`; zmiana stałych w kodzie nie zmienia wyników zapisanych wcześniej (test z zamrożoną migawką).

## 8. Otwarte pytania

| Pytanie | Kto | Blokuje? |
|---|---|---|
| Czy zakładka „Wywiady" ma już mechanizm wersjonowania i szablonów wywiadów, czy budujemy od zera? | eng (rozpoznanie repo) | tak |
| Czy trener ma widzieć wolne pole „coś, co powinien wiedzieć" jako część karty klienta, czy tylko w wywiadzie? | produkt | nie |
| Minimalne kcal: przyjęte 1 200 K / 1 500 M — czy dietetyk potwierdza dla tej grupy klientów? | dietetyk | nie |

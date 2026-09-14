# Wywiad kaloryczny 1.0 — postęp, rozbieżności i to, co zostaje otwarte

Runda 0.77.0, gałąź `agent/wywiad-kaloryczny`, PR #80, migracja 42.
Materiał źródłowy w tym katalogu: `wywiad_zapotrzebowanie_kaloryczne.md`
(specyfikacja właściciela 1.0 z 13.09.2026), `calorie_calc.py` (referencyjna
implementacja wzorów), `01_rozpoznanie_spec_v1.md` (rozpoznanie luk, PR #71).

**Zasada rozstrzygania (decyzja właściciela nr 7):** przy rozbieżności
**`calorie_calc.py` rozstrzyga liczby**, a specyfikacja teksty i układ ekranów.
Poniżej wypisana jest każda rozbieżność, którą znalazłem, i to, jak została
rozstrzygnięta.

---

## 1. Rozbieżności specyfikacja kontra referencja właściciela

| # | Rzecz | Specyfikacja | `calorie_calc.py` | Rozstrzygnięcie |
|---|---|---|---|---|
| 1 | Tłuszcz przy redukcji | „0,8–1,0 g/kg, min. 20 % kcal” (§5.5) | `FAT_G_KG['cut'] = 0.9` | **0,9 g/kg** — referencja rozstrzyga liczby; 0,9 jest środkiem zakresu ze specyfikacji, więc nie ma sprzeczności co do intencji |
| 2 | Białko przy redukcji i > 30 % tłuszczu | „liczone z masy docelowej **lub LBM**” (§5.5) | masa docelowa albo `kg·(1−%tł/100)/0,75` (≈ masa beztłuszczowa podzielona przez 0,75) | **wzór z referencji**; „LBM” wprost dałoby wynik o ok. 25 % niższy, a referencja jest nowsza i konkretna |
| 3 | Cel przy ciąży i karmieniu | „cel = CPM **lub CPM + 300/500**” (§6.4) | `adj = max(adj, 0)` → cel = CPM | **cel = CPM** — referencja rozstrzyga liczby; dodatek 300/500 kcal to decyzja żywieniowa, której nie wolno podejmować automatycznie (specyfikacja sama każe kierować do lekarza) |
| 4 | Zakres CPM w widoku | przykład §6.1 pokazuje 2 190–2 510 dla CPM 2 350 (zaokrąglone do dziesiątek) | `tdee·0,93` i `tdee·1,07` bez zaokrąglania | **wartości dokładne** (2 186–2 515 dla tego przykładu); zaokrąglanie do dziesiątek dołożyłoby trzecią regułę zaokrąglania obok już istniejących. P2 niżej |
| 5 | Flaga `DEFICYT_WYLACZONY` | nie występuje w specyfikacji (§6.4 wymienia siedem flag) | zapala się **zawsze** przy ciąży albo braku miesiączki, także gdy korekta była dodatnia | **zapala się tylko wtedy, gdy deficyt naprawdę został wyłączony** — przy budowie masy „deficyt wyłączony” byłoby dla trenera nieprawdą. Liczby bez zmian; flaga to tekst, a teksty rozstrzyga specyfikacja |
| 6 | Oczekiwane tempo jako zakres | „pokaż jako ~0,4–0,6 kg/tydz.” (§5.4), przykład §6.1: „~0,4–0,5” | zwraca jedną liczbę `expected_weekly_change_kg` | zakres liczony przez zaokrąglenie w dół i w górę do 0,1 kg — **odtwarza przykład §6.1 co do cyfry** (deficyt 470 kcal/dzień → 0,427 → „0,4–0,5”) |
| 7 | Znak `expected_weekly_change_kg` | — | `(CPM − cel)·7/7700`, więc **dodatni przy redukcji**, ujemny przy nadwyżce | zostawione jak w referencji (zapisywane 1:1), kierunek nazwany słowami w interfejsie („w dół” / „w górę”) |
| 8 | Czas treningu „90+ min” | opcja bez górnej wartości (§4) | — (referencja bierze minuty wprost) | **liczone jako 90 min**; zawyżanie podnosiłoby wynik bez pokrycia w danych |
| 9 | Wiek kontra data urodzenia | „Data urodzenia, wiek 16–90” (§4) | `birth_date` + `age_from()` | **wiek w latach** — decyzja właściciela nr 4 (mniej danych; do wzoru wystarcza wiek, data była potrzebna tylko do flagi < 18 i do przypomnień, których ta runda nie robi). Zakres 16–90 wg specyfikacji |
| 10 | Zakres flagowania zaburzeń odżywiania | flaguje tylko „tak” (§6.4) | `if a.get('eating_disorder')` | **szerzej: „Tak”, „Nie wiem”, „Wolę omówić z trenerem”** — decyzja właściciela nr 2, uzasadnienie niżej |
| 11 | `MALOLETNI` a przycisk „odsłoń” | „wynik liczony, ale nie pokazywany klientowi” (§6.4) | `client_view` zwraca sam komunikat | ukrycie **nieodwracalne** przyciskiem „odsłoń” (ten zdejmuje wyłącznie ukrycie z powodu zaburzeń odżywiania). Ani specyfikacja, ani referencja tego nie rozstrzygały; wiek nie zmienia się przez rozmowę, tylko przez nowe przesłanie |
| 12 | `formulas_version` | „zmiana wzorów nie zmienia starych wyników” (§6.3), bez wartości | `"2026-09-13.1"` | wartość z referencji wzięta 1:1; wyniki sprzed wyrównania dostają `"0.62.0-pal"` |
| 13 | Zaokrąglanie składników w podstawieniu | „każda liczba ma jednozdaniowe wyjaśnienie «skąd to»” (§2) | liczenie na surowych wartościach, bez warstwy prezentacji | rozbicie („PPM × NEAT”, mnożnik) pokazywane i mnożone z wartości **zaokrąglonych** — tych, które widać w karcie — żeby wiersz podstawienia i kafelek nie dawały dwóch różnych liczb na ten sam składnik. Sam wynik dalej liczy się z wartości surowych; gdy suma zaokrąglonych składników rozjeżdża się z wynikiem, podstawienie mówi to wprost zamiast udawać, że się zgadza |

Rzeczy, w których referencja i specyfikacja się zgadzają, a mimo to warto je
zapisać, bo łatwo je przeoczyć przy czytaniu samej specyfikacji:

* **Katch-McArdle wygrywa dopiero przy różnicy ponad 10 %** — nie zawsze, gdy
  podano procent tłuszczu. Oba PPM są jednak pokazywane trenerowi z różnicą.
* **Podłoga celu dotyczy wyłącznie redukcji i rekompozycji.** Przy utrzymaniu
  i budowie masy nie ma dolnej granicy (bo nie ma deficytu).
* **TEF liczony jest od sumy `PPM × NEAT + trening`**, nie od samego PPM.
* Preferencja białka „wysoka” zmienia cokolwiek **tylko przy redukcji** —
  dla pozostałych celów zakres w referencji jest jednopunktowy.

## 2. Uzasadnienie szerszej reguły ukrywania liczb (decyzja właściciela nr 2)

Specyfikacja ukrywa liczby tylko przy odpowiedzi „tak”. Implementacja 0.62.0
ukrywa je także przy „Nie wiem” i „Wolę omówić z trenerem” i tak zostaje.

Powód jest niesymetryczny, nie ostrożnościowy. Zawężenie do samego „tak”
odsłoniłoby liczby części klientów **już obsługiwanych na produkcji** — bez
ich udziału i bez żadnego sygnału. Koszt pomyłki w jedną stronę (osoba
z zaburzeniami odżywiania dostaje kalorie na ekran) jest nieporównanie wyższy
niż w drugą (osoba bez zaburzeń czeka jedną rozmowę z trenerem, który może
odsłonić wynik jednym kliknięciem). Przy takiej asymetrii kosztów szersza
reguła jest tańsza nawet wtedy, gdy częściej się myli.

Dlatego pytanie o zaburzenia odżywiania **nie dostało piątej odpowiedzi**
„wolę nie odpowiadać” bez flagi — byłaby to furtka omijająca tę ochronę.
Jego „Wolę omówić z trenerem” pełni rolę odpowiedzi odmownej i flaguje.

## 3. Kryteria akceptacji ze specyfikacji §7 → testy

| Kryterium | Test |
|---|---|
| M 30 l., 180 cm, 80 kg → PPM Mifflin = 1 780 (dokładnie) | `test_zapotrzebowanie_silnik.py::test_kryterium_ppm_mezczyzna_1780` |
| K 25 l., 165 cm, 60 kg → PPM = 1 345 | `…::test_kryterium_ppm_kobieta_1345` |
| 80 kg, 20 % tłuszczu → Katch = 1 752 (±1) | `…::test_kryterium_katch_1752` |
| trening/dzień = 180 kcal; CPM = 2 548 | `…::test_kryterium_trening_i_cpm_2548` |
| redukcja „szybkie” u kobiety 1 345 PPM → cel ≥ 1 480 + `DEFICYT_OGRANICZONY` | `…::test_kryterium_redukcja_szybka_nie_schodzi_ponizej_granicy` |
| `ZABURZENIA_ODZYWIANIA` → odpowiedź API dla klienta bez pól `kcal`, `target_kcal`, tempa | `test_zapotrzebowanie_api.py::test_zaburzenia_klient_nie_dostaje_zadnej_liczby` (sprawdza rekurencyjnie **każdy** klucz i każdą liczbę w odpowiedzi) |
| `MALOLETNI` → brak wyniku w widoku klienta | `…::test_maloletni_nie_widzi_liczb_i_trener_nie_moze_tego_cofnac` |
| każdy zapisany wywiad ma `formulas_version`; zmiana stałych nie zmienia wyników zapisanych wcześniej | `test_zapotrzebowanie_silnik.py::test_kryterium_formulas_version_zamrozona` + `test_zapotrzebowanie_api.py::test_stary_wynik_zostaje_w_historii_i_ma_wlasna_wersje_wzorow` (migawka wiersza 0.62.0: po nowym przesłaniu stary wiersz dalej ma swoje `kcal` i pusty `target_kcal`) |
| minimalne kcal 1 200 K / 1 500 M | `…::test_kryterium_minimum_kcal_kobiety_1200_mezczyzn_1500` |

## 4. Czego ta runda nie robi

**P1 ze specyfikacji §7** (świadomie poza zakresem, do osobnej rundy):

* przypomnienie klientowi o ponownym wypełnieniu po zmianie masy > 3 kg albo
  po 8 tygodniach — wchodzi tylko statyczna zachęta przy wyniku starego wzoru;
* wykres masy i CPM w czasie — jest tabela historii u trenera, nie wykres.

**P2 ze specyfikacji §3/§7:** integracja kroków z zegarka (pole „kroki” jest
przygotowane i nadpisuje opis), adaptacja kalorii z ważeń.

**P2 znalezione przy tej rundzie:**

1. **Etykieta w menu klienta** mówi „Wywiad (wstępny i głęboki)”, a typy są
   trzy od 0.62.0. Nie zmieniona, bo `e2e/wywiad.spec.ts` asercjuje tę nazwę —
   poprawka to jedna linia w `pages/More.tsx` plus jedna w tym specu.
2. **Kolumna `pal`** dla wierszy 1.0 trzyma CPM/PPM (efektywny współczynnik
   aktywności), bo silnik 1.0 nie używa jednego mnożnika PAL. Sensowne
   domknięcie: przy najbliższej migracji porządkującej wycofać kolumnę
   i czytać `neat_multiplier`.
3. **Zaokrąglanie zakresu CPM** do dziesiątek jak w przykładzie §6.1
   (dziś wartości dokładne — rozbieżność 4 wyżej).
4. **Wolne pole „coś, co trener powinien wiedzieć”** trafia do odpowiedzi
   wywiadu (za zgodą zdrowotną), ale nie jest wyróżnione na karcie bilansu —
   to jest dokładnie pytanie otwarte ze specyfikacji §8, patrz niżej.
5. **Trener nie ma przycisku „poproś o ponowne wypełnienie”** wywiadu
   kalorycznego; zachętę widzi tylko klient przy starym wyniku.
6. **`.btn--small` ma w całej aplikacji 38 px wysokości**, czyli poniżej progu
   44 px dla celu dotyku. W karcie bilansu podniesione punktowo; reszta
   aplikacji zostaje bez zmian, bo to zmiana o zasięgu całego interfejsu
   i osobna decyzja. Bramka dostępności sprawdza próg tylko dla nawigacji
   i dla tej karty.

## 5. Pytania otwarte dla właściciela

| Pytanie | Skąd | Domyślne, jeśli brak odpowiedzi |
|---|---|---|
| Czy trener ma widzieć wolne pole „coś, co trener powinien wiedzieć” jako wyróżniony element karty klienta, czy wystarczy, że jest w odpowiedziach wywiadu? | specyfikacja §8 | zostaje w odpowiedziach wywiadu (za zgodą zdrowotną) — mniej miejsc, w których ta sama treść żyje |
| Minimalne kcal 1 200 K / 1 500 M — czy dietetyk potwierdza dla tej grupy klientów? | specyfikacja §8 | przyjęte bez zmian (decyzja właściciela nr 6) |
| Czy „deficyt wyłączony” przy ciąży i karmieniu ma zostać na poziomie CPM, czy dodawać CPM + 300/500 kcal, jak dopuszcza §6.4? | rozbieżność 3 | zostaje CPM; dodatek to decyzja żywieniowa, której aplikacja nie powinna podejmować automatycznie |
| Czy trener ma dostawać powiadomienie, gdy klient ma wynik policzony starym wzorem (0.62.0-pal)? | decyzja nr 3 | nie — zachęta jest po stronie klienta, bez ponaglania |

## 6. Plan kontra rzeczywistość

| Etap | Plan | Jak było |
|---|---|---|
| 1. Silnik | średni | zgodnie z planem; wektory kontrolne przeszły za pierwszym razem, bo liczby są przeniesione 1:1 z referencji zamiast wyprowadzane ze specyfikacji |
| 2. Model, migracja, API | średni | większy niż planowano: doszła bramka zgody zdrowotnej na flagi (nie było jej w rozpoznaniu — rozpoznanie zakładało, że wystarczy istniejący filtr `hidden_for_client`) oraz 16. kolumna `tempo_json` |
| 3. Definicje pytań | średni | mniejszy niż planowano: formularz klienta jest generyczny (renderuje z definicji serwera), więc pięć ekranów nie wymagało żadnej pracy po stronie formularza. Doszła za to rzecz, której plan nie przewidział: **filtr szkiców sprzed zmiany pytań** |
| 4. Interfejs | duży | mniejszy niż planowano, z tego samego powodu — pracy wymagała wyłącznie karta wyniku, nie formularz |
| 5. Testy i dokumenty | duży | zgodnie z planem |

**Co okazało się inne niż w rozpoznaniu:**

* Rozpoznanie §2 mówiło, że wywiad ma 11 pytań i potrzeba „~20 pól”. Wyszły 23.
* Rozpoznanie nie zauważyło, że wspólna `WERSJA` definicji jest jedna dla trzech
  typów wywiadu — podbicie jej oznaczyłoby zmianę metadanych także wywiadu
  wstępnego i głębokiego. Stąd osobna `WERSJA_ZAPOTRZEBOWANIE`.
* Rozpoznanie nie zauważyło, że wyrażenie liczbowe w walidacji (`_LICZBA_RE`)
  dopuszcza najwyżej trzy cyfry — kroki dzienne (do 40 000) nie przeszłyby.
* Rozpoznanie nie zauważyło, że sygnał monitoringu „cel redukcja, a trend wagi
  w górę” porównuje `inputs_json["cel"]` z wartością `"redukcja"`, której żaden
  silnik nie zapisywał. Sygnał nie zapalił się ani razu na produkcji, a test był
  zielony, bo wstawiał ten wiersz ręcznie. Naprawione przy okazji, bo i tak
  zmieniał się kształt tego pola.
* **Bramka dostępności sprawdzała nie tę aplikację.** `e2e/test_a11y.mjs`
  startuje serwer z katalogu tymczasowego, więc `python -m uvicorn` importował
  `dzik_os` z zainstalowanego pakietu zamiast z bieżącego drzewa roboczego —
  bez żadnego sygnału, że testuje kod sprzed zmian. Dołożone `PYTHONPATH`
  (`e2e/serve.sh` robił to poprawnie przez `cd "$BACKEND"`). Dotyczyło to
  każdej rundy pracującej w osobnym katalogu roboczym, nie tylko tej.

## 7. Koszt

Pięć commitów etapowych (plan → silnik → model i pytania → interfejs →
testy i dokumenty). Zmienione pliki: silnik i serwis wywiadu, definicje pytań,
model i migracja, dwa routery, karta wyniku i typy frontu, `PrzypiszDiete`,
arkusz stylów, trzy pliki testów, spec E2E oraz dziesięć dokumentów.
65 testów backendu dla samego wywiadu (45 silnika + 20 API) plus E2E
i sekcja 4c bramki dostępności.

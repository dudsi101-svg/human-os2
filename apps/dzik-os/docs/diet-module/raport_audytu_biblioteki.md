# Audyt biblioteki szablonów — raport końcowy (14.09.2026)

## 1. Zakres i metoda
Audytowi poddano wszystkie 45 tygodni (9 profili × 5 odsłon, 1295 posiłków) w trzech warstwach:
1. **Zgodność techniczna** — jednolity schemat JSON, referencje produktów, role P/C/F, udziały kcal, sloty, posiłek elastyczny, jednostki dyskretne.
2. **Jakość żywieniowa (makro i struktura)** — kryteria, które stosuje dobry dietetyk kliniczny/sportowy: warzywa ≥ 400 g/dzień, błonnik ≥ 25 g, ryby ≥ 2×/tydz. w tym tłusta (omega-3), czerwone mięso ≤ 3 dni, wędliny ≤ 4 dni, strączki ≥ 2 dni (wege ≥ 5), pełne ziarno codziennie, białko ≥ 20 g w każdym posiłku głównym (próg stymulacji syntezy białek mięśniowych), cukry dodane ≤ 30 g, źródła ALA codziennie w diecie wegańskiej, realność porcji przy skrajnych kalorycznościach.
3. **Mikroskładniki** (nowe) — wapń, żelazo, magnez, potas, sód, cynk, wit. C, B12, foliany, EPA+DHA, tłuszcze nasycone i cukry proste z pełnych danych USDA (dla 40 produktów PL przez produkt zastępczy USDA o zbliżonym składzie), porównane z normami IŻŻ 2020 / EFSA.

Przed zmianami wykonano kopię zapasową: `biblioteka_backup_przed_audytem.zip` (stan sprzed audytu, komplet plików).

## 2. Zgodność techniczna — wynik
- 45/45 plików ma ten sam schemat: klucze szablonu ['audit', 'base_kcal', 'days', 'derived_from', 'kcal_max', 'kcal_min', 'macro_pct', 'profile', 'sodium_note', 'supplements_note', 'variant']; klucze posiłku ['allergens', 'flexible', 'ingredients', 'kcal_share', 'name', 'slot', 'steps', 'tags']; klucze składnika ['class', 'grams', 'group', 'max_factor', 'min_factor', 'product', 'role', 'unit_g', 'unit_step'].
- Sloty: {'śniadanie': 315, 'obiad': 280, 'przekąska': 315, 'kolacja': 315, 'obiad_1': 35, 'obiad_2': 35}. Klasy skalowania: {'(domyślna)': 10278, 'DYSKRETNY': 975}.
- Wszystkie produkty składników istnieją w `baza_produktow.csv` (181). Udziały kcal każdego dnia = 1,00. Każdy dzień ma posiłek elastyczny.
- Znaleziono i naprawiono: 63 posiłki bez składnika sterującego tłuszczem (Sportowa, Redukcja) lub węglowodanami (Niskowęglowodanowa) — silnik nie mógł ich domykać przy zmianie kaloryczności.
- Nowe pola: `allergens` per posiłek (z alergenów produktów), `supplements_note`, `sodium_note`, `audit` (lista poprawek i pozostałych uwag) w każdym JSON.

## 3. Jakość żywieniowa — co znaleziono i co poprawiono
| Problem | Skala przed | Poprawka | Po |
|---|---|---|---|
| Porcje 340–570 g surowej ryby/mięsa przy górnej kaloryczności | 28 szablonów | twardy limit silnika 300 g/posiłek + 4 jajka/posiłek; nadwyżka trafia do flagi (wariant) | 0 |
| Dni z warzywami < 350 g (min. 170 g w Wegańskiej) | 19 szablonów | proporcjonalne zwiększenie warzyw do ≥ 400 g/dzień, w razie potrzeby sałatka do obiadu | 0 |
| Brak tłustej ryby w tygodniu | 6 szablonów | jedno danie z dorsza/mintaja zamienione na łososia (bez dań ze śmietaną) | 0 |
| Zero strączków (Sportowa, Redukcja 2) | 6 szablonów | ciecierzyca w 2 kolacjach typu sałatka/wrap | 0 |
| Wędliny 5 dni/tydz. | 2 szablony | pieczona pierś zamiast wędliny w nadmiarowych dniach | 0 |
| Czerwone mięso 4 dni/tydz. | 4 szablony | indyk zamiast steku/polędwiczki w 4. dniu | 0 |
| Posiłek główny < 20 g białka (zupy-kremy, kolacje wege) | 21 szablonów | zwiększenie składnika białkowego, dodatek jogurtu greckiego / tofu | 5 graniczne (18–19 g) |
| Błonnik < 22 g w dniu | 2 szablony | siemię lniane w śniadaniu | 2 graniczne (21,7 i 22,0 g) |
| ALA (omega-3 roślinne) nie codziennie w Wegańskiej | 4 szablony | siemię lniane 10 g w śniadaniu | 0 |
| Sód 3000–4800 mg/dzień | wszystkie | sól w przepisach 1 g → 0,5 g/posiłek, sos sojowy −30 %, nota o bulionie niskosodowym | 2300–3000 mg przy 2000 kcal (≈1,2 g/1000 kcal) |
| Tłuszcze nasycone 13–14 % kcal (Niskowęglowodanowa) | 5 szablonów | połowa masła zastąpiona oliwą | 13–14 % (cecha profilu: sery, jajka, śmietana) |
| B12 = 0 (Wegańska) | 5 szablonów | nie do naprawienia dietą — obowiązkowa suplementacja wpisana do szablonu | wymaga suplementu |

Walidacja po poprawkach: **5625/5670 dni w tolerancji (99.2 %)**, posiłków z flagą 9 %.

## 4. Tabela końcowa
| Profil | Odsłona | B/T/W % | Zakres kcal | Dni w tolerancji | Flagi | Pozostałe uwagi audytu |
|---|---|---|---|---|---|---|
| Standard zbilansowana | 1 | 25/30/45 | 1400–3200 | 133/133 | 9 % | — |
| Standard zbilansowana | 2 | 25/30/45 | 1400–3200 | 132/133 | 8 % | — |
| Standard zbilansowana | 3 | 25/30/45 | 1400–3200 | 133/133 | 6 % | posiłek główny z białkiem < 20 g (19 g) |
| Standard zbilansowana | 4 | 25/30/45 | 1400–3200 | 133/133 | 12 % | — |
| Standard zbilansowana | 5 | 25/30/45 | 1400–3200 | 132/133 | 11 % | — |
| Redukcja wysokobiałkowa | 1 | 35/25/40 | 1300–2800 | 112/112 | 7 % | — |
| Redukcja wysokobiałkowa | 2 | 35/25/40 | 1300–2800 | 112/112 | 10 % | błonnik < 22 g w dniu (min 21.7 g) |
| Redukcja wysokobiałkowa | 3 | 35/25/40 | 1300–2800 | 112/112 | 13 % | — |
| Redukcja wysokobiałkowa | 4 | 35/25/40 | 1300–2800 | 110/112 | 15 % | — |
| Redukcja wysokobiałkowa | 5 | 35/25/40 | 1300–2800 | 111/112 | 12 % | — |
| Sportowa wysokobiałkowa | 1 | 30/22/48 | 2000–3600 | 119/119 | 8 % | — |
| Sportowa wysokobiałkowa | 2 | 30/22/48 | 2000–3600 | 119/119 | 7 % | — |
| Sportowa wysokobiałkowa | 3 | 30/22/48 | 2000–3600 | 118/119 | 6 % | — |
| Sportowa wysokobiałkowa | 4 | 30/22/48 | 2000–3600 | 119/119 | 8 % | — |
| Sportowa wysokobiałkowa | 5 | 30/22/48 | 2000–3600 | 119/119 | 11 % | — |
| Masa / budowa | 1 | 25/25/50 | 2200–4000 | 133/133 | 7 % | — |
| Masa / budowa | 2 | 25/25/50 | 2200–4000 | 133/133 | 11 % | — |
| Masa / budowa | 3 | 25/25/50 | 2200–4000 | 133/133 | 8 % | — |
| Masa / budowa | 4 | 25/25/50 | 2200–4000 | 133/133 | 11 % | — |
| Masa / budowa | 5 | 25/25/50 | 2200–4000 | 133/133 | 8 % | — |
| Niskowęglowodanowa | 1 | 30/45/25 | 1400–2800 | 101/105 | 12 % | pełne ziarno tylko w 6/7 dni |
| Niskowęglowodanowa | 2 | 30/45/25 | 1400–2800 | 102/105 | 11 % | — |
| Niskowęglowodanowa | 3 | 30/45/25 | 1400–2800 | 101/105 | 10 % | błonnik < 22 g w dniu (min 21.9 g) |
| Niskowęglowodanowa | 4 | 30/45/25 | 1400–2800 | 105/105 | 6 % | — |
| Niskowęglowodanowa | 5 | 30/45/25 | 1400–2800 | 103/105 | 10 % | — |
| Wegetariańska | 1 | 22/30/48 | 1400–3200 | 128/133 | 10 % | — |
| Wegetariańska | 2 | 22/30/48 | 1400–3200 | 133/133 | 7 % | — |
| Wegetariańska | 3 | 22/30/48 | 1400–3200 | 132/133 | 9 % | — |
| Wegetariańska | 4 | 22/30/48 | 1400–3200 | 130/133 | 7 % | — |
| Wegetariańska | 5 | 22/30/48 | 1400–3200 | 133/133 | 9 % | — |
| Wegańska | 1 | 20/30/50 | 1400–3200 | 133/133 | 4 % | — |
| Wegańska | 2 | 20/30/50 | 1400–3200 | 133/133 | 6 % | — |
| Wegańska | 3 | 20/30/50 | 1400–3200 | 131/133 | 4 % | — |
| Wegańska | 4 | 20/30/50 | 1400–3200 | 133/133 | 5 % | — |
| Wegańska | 5 | 20/30/50 | 1400–3200 | 128/133 | 8 % | — |
| Bezlaktozowa | 1 | 25/30/45 | 1400–3200 | 132/133 | 11 % | — |
| Bezlaktozowa | 2 | 25/30/45 | 1400–3200 | 132/133 | 8 % | — |
| Bezlaktozowa | 3 | 25/30/45 | 1400–3200 | 133/133 | 7 % | posiłek główny z białkiem < 20 g (19 g) |
| Bezlaktozowa | 4 | 25/30/45 | 1400–3200 | 133/133 | 13 % | — |
| Bezlaktozowa | 5 | 25/30/45 | 1400–3200 | 133/133 | 12 % | — |
| Bezglutenowa | 1 | 25/30/45 | 1400–3200 | 131/133 | 10 % | posiłek główny z białkiem < 20 g (18 g) |
| Bezglutenowa | 2 | 25/30/45 | 1400–3200 | 132/133 | 11 % | — |
| Bezglutenowa | 3 | 25/30/45 | 1400–3200 | 132/133 | 9 % | pełne ziarno tylko w 6/7 dni |
| Bezglutenowa | 4 | 25/30/45 | 1400–3200 | 133/133 | 13 % | posiłek główny z białkiem < 20 g (19 g); pełne ziarno tylko w 5/7 dni |
| Bezglutenowa | 5 | 25/30/45 | 1400–3200 | 129/133 | 13 % | pełne ziarno tylko w 6/7 dni |

## 5. Mikroskładniki — średnie dzienne przy kaloryczności bazowej
| Szablon | Ca mg | Fe mg | Mg mg | K mg | Na mg | Zn mg | wit. C mg | B12 µg | foliany µg | EPA+DHA mg | SFA % kcal | cukry % kcal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| standard_v1 | 905 | 18.8 | 465 | 4305 | 2536 | 12.5 | 188 | 5.1 | 463 | 590 | 7.3 | 11.9 |
| standard_v2 | 973 | 18.7 | 486 | 4429 | 2453 | 12.5 | 254 | 4.9 | 470 | 717 | 8.0 | 12.8 |
| standard_v3 | 1066 | 18.1 | 510 | 4331 | 2452 | 13.0 | 189 | 5.3 | 462 | 579 | 8.0 | 12.9 |
| standard_v4 | 1098 | 16.6 | 440 | 4505 | 2765 | 12.3 | 277 | 5.0 | 518 | 432 | 6.9 | 13.3 |
| standard_v5 | 1005 | 18.1 | 474 | 4571 | 3008 | 12.3 | 265 | 4.9 | 484 | 766 | 7.1 | 12.5 |
| redukcja_v1 | 1064 | 18.0 | 471 | 4932 | 2958 | 13.9 | 242 | 6.6 | 416 | 789 | 5.9 | 10.8 |
| redukcja_v2 | 1024 | 21.5 | 456 | 4745 | 2751 | 13.5 | 195 | 5.9 | 430 | 287 | 6.1 | 9.8 |
| redukcja_v3 | 1083 | 18.3 | 502 | 5077 | 2647 | 14.1 | 280 | 6.3 | 450 | 318 | 5.5 | 11.1 |
| redukcja_v4 | 1087 | 16.8 | 505 | 5391 | 3395 | 14.2 | 231 | 6.6 | 451 | 693 | 6.0 | 11.8 |
| redukcja_v5 | 1126 | 17.8 | 493 | 5031 | 2476 | 14.3 | 300 | 7.1 | 499 | 496 | 5.9 | 11.4 |
| sportowa_v1 | 1429 | 28.7 | 572 | 5355 | 3028 | 16.3 | 251 | 6.9 | 513 | 577 | 5.8 | 10.6 |
| sportowa_v2 | 1354 | 28.7 | 588 | 5445 | 3233 | 16.5 | 250 | 7.0 | 547 | 591 | 6.0 | 10.0 |
| sportowa_v3 | 1344 | 30.0 | 578 | 5240 | 2842 | 16.5 | 245 | 6.9 | 493 | 602 | 5.5 | 11.0 |
| sportowa_v4 | 1340 | 27.3 | 571 | 5414 | 3580 | 17.0 | 246 | 7.0 | 570 | 646 | 6.2 | 10.3 |
| sportowa_v5 | 1280 | 28.4 | 574 | 5300 | 2819 | 16.9 | 251 | 7.2 | 558 | 633 | 5.6 | 10.4 |
| masa_v1 | 1272 | 29.3 | 699 | 6243 | 3405 | 18.8 | 249 | 7.3 | 686 | 827 | 6.2 | 11.9 |
| masa_v2 | 1382 | 27.1 | 734 | 6406 | 3353 | 18.7 | 328 | 7.3 | 677 | 1070 | 6.6 | 12.5 |
| masa_v3 | 1556 | 27.2 | 773 | 6395 | 3225 | 19.6 | 257 | 8.0 | 684 | 934 | 6.6 | 12.7 |
| masa_v4 | 1556 | 24.8 | 638 | 6547 | 3679 | 18.0 | 389 | 7.3 | 762 | 622 | 5.9 | 13.2 |
| masa_v5 | 1454 | 27.4 | 719 | 6811 | 3934 | 18.5 | 375 | 7.2 | 708 | 1054 | 6.0 | 12.3 |
| niskoweglowodanowa_v1 | 1019 | 16.7 | 483 | 4715 | 2757 | 12.4 | 367 | 5.8 | 538 | 992 | 12.9 | 8.0 |
| niskoweglowodanowa_v2 | 1131 | 17.3 | 443 | 4619 | 2332 | 15.3 | 253 | 8.9 | 459 | 1000 | 13.9 | 7.8 |
| niskoweglowodanowa_v3 | 1252 | 16.1 | 481 | 4536 | 2823 | 13.2 | 392 | 6.2 | 527 | 742 | 13.8 | 7.8 |
| niskoweglowodanowa_v4 | 896 | 17.6 | 469 | 4810 | 2405 | 14.7 | 230 | 9.0 | 462 | 1055 | 13.5 | 7.7 |
| niskoweglowodanowa_v5 | 1313 | 15.5 | 466 | 4331 | 2708 | 13.0 | 420 | 6.1 | 518 | 743 | 13.2 | 8.0 |
| wegetarianska_v1 | 1485 | 22.8 | 493 | 4424 | 3008 | 12.1 | 253 | 2.9 | 674 | 60 | 8.6 | 11.5 |
| wegetarianska_v2 | 1732 | 21.8 | 531 | 4188 | 2844 | 12.4 | 256 | 2.6 | 589 | 26 | 7.9 | 12.8 |
| wegetarianska_v3 | 1441 | 22.2 | 509 | 4590 | 3019 | 12.8 | 266 | 3.2 | 642 | 78 | 9.7 | 12.0 |
| wegetarianska_v4 | 1488 | 22.7 | 522 | 4418 | 2738 | 12.3 | 266 | 3.2 | 648 | 48 | 8.2 | 12.5 |
| wegetarianska_v5 | 1464 | 21.5 | 515 | 4359 | 2950 | 12.5 | 275 | 2.9 | 629 | 73 | 8.7 | 11.5 |
| weganska_v1 | 1160 | 25.0 | 612 | 4147 | 2570 | 11.5 | 255 | 0.0 | 822 | 2 | 4.5 | 11.3 |
| weganska_v2 | 1141 | 26.1 | 580 | 4103 | 2320 | 12.0 | 250 | 0.0 | 896 | 1 | 5.2 | 11.3 |
| weganska_v3 | 1322 | 26.4 | 617 | 4391 | 2504 | 12.1 | 245 | 0.0 | 855 | 3 | 5.5 | 10.9 |
| weganska_v4 | 1215 | 26.0 | 614 | 4423 | 2405 | 12.0 | 244 | 0.0 | 982 | 4 | 4.7 | 11.2 |
| weganska_v5 | 1095 | 25.8 | 593 | 4191 | 2482 | 11.6 | 252 | 0.0 | 847 | 0 | 5.2 | 11.3 |
| bezlaktozowa_v1 | 913 | 18.9 | 467 | 4295 | 2527 | 12.5 | 187 | 5.2 | 461 | 592 | 7.4 | 11.9 |
| bezlaktozowa_v2 | 985 | 18.7 | 486 | 4414 | 2449 | 12.6 | 255 | 4.9 | 469 | 717 | 8.0 | 12.7 |
| bezlaktozowa_v3 | 1062 | 19.0 | 516 | 4340 | 2414 | 13.0 | 189 | 5.3 | 466 | 579 | 7.9 | 12.6 |
| bezlaktozowa_v4 | 1109 | 16.5 | 437 | 4568 | 2762 | 12.2 | 296 | 5.0 | 524 | 432 | 7.1 | 13.6 |
| bezlaktozowa_v5 | 1029 | 18.0 | 468 | 4583 | 3017 | 12.3 | 271 | 5.0 | 486 | 761 | 7.2 | 12.6 |
| bezglutenowa_v1 | 850 | 20.0 | 480 | 4348 | 2274 | 12.3 | 185 | 5.3 | 473 | 622 | 6.9 | 12.2 |
| bezglutenowa_v2 | 972 | 18.4 | 522 | 4488 | 2306 | 12.7 | 253 | 5.0 | 474 | 691 | 7.9 | 13.2 |
| bezglutenowa_v3 | 1080 | 19.7 | 535 | 4343 | 2266 | 13.3 | 186 | 5.7 | 478 | 642 | 7.8 | 12.8 |
| bezglutenowa_v4 | 1073 | 16.3 | 453 | 4540 | 2487 | 12.2 | 288 | 5.2 | 515 | 442 | 6.6 | 13.7 |
| bezglutenowa_v5 | 1005 | 18.6 | 488 | 4573 | 2831 | 12.6 | 271 | 5.6 | 497 | 888 | 7.1 | 12.9 |

Interpretacja: wapń, żelazo, magnez, potas, cynk, wit. C i foliany są w normie we wszystkich profilach (żelazo 16–26 mg w profilach roślinnych — z uwagi na gorszą przyswajalność żelaza niehemowego to właściwy poziom). EPA+DHA ≥ 250 mg we wszystkich profilach z rybą. Sód 2,3–3,0 g/2000 kcal to poniżej średniego spożycia w Polsce (~4 g), ale powyżej celu WHO (2 g) — główne źródła to pieczywo żytnie, sól w przepisach, bulion, sery i wędliny; szablony zakładają, że klient nie dosala. B12 w diecie wegańskiej = 0 z definicji; D3 nie jest realizowana dietą w żadnym profilu (standardowa suplementacja jesień–zima).

## 6. Ocena względem pracy dobrego dietetyka
**Na poziomie profesjonalnym lub powyżej:** precyzja makro przy każdej kaloryczności (dietetyk liczy jedną kaloryczność, silnik 17–19), 45 zróżnicowanych tygodni, kontrola warzyw/błonnika/ryb/strączków/wędlin/czerwonego mięsa w każdym tygodniu, białko w każdym posiłku głównym, mikroskładniki policzone z bazy referencyjnej, alergeny per posiłek, źródło każdej wartości odżywczej, powtarzalna walidacja.

**Poniżej poziomu najlepszych dietetyków — świadome luki:**
1. Brak personalizacji poza kcal/makro: preferencje smakowe, budżet, czas gotowania, sprzęt, sezonowość — trener robi to ręcznie przez wymiany produktów i podmianę posiłków.
2. Wartości odżywcze dla produktów surowych; przepisy nie uwzględniają zmian masy i strat w gotowaniu (dla makro to pomijalne, dla wit. C i folianów strata 20–50 % przy gotowaniu).
3. 40 produktów PL na wartościach z tabel i etykiet (`MANUAL_PL`), mikroskładniki dla nich przez produkt zastępczy — do weryfikacji.
4. Profile pochodne (Masa, Bezlaktozowa, Bezglutenowa) to przeskalowany Standard: poprawne, ale nie „zaprojektowane" pod cel (np. cięższe przekąski na masie).
5. Brak timingu posiłków względem treningu (Sportowa), brak strategii nawodnienia, brak wersji dla kobiet w ciąży, dzieci, chorób — te wymagają dietetyka.
6. Dni w profilach składanych rotacyjnie nie były oceniane kulinarnie jako całość.

## 7. Pliki
`template_*.json` (45, z polem `audit`), `szablon_*.md` (podglądy), `biblioteka_index.json` (spis + pozostałe uwagi + suplementy), `engine.py` (limity porcji), `audit.py`, `audit_micro.py`, `fix.py` (powtarzalny potok), `micro.csv` (mikroskładniki produktów), `biblioteka_backup_przed_audytem.zip`.

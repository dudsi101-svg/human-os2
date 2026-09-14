# Inwentarz jadłospisów Łukasza (Konrad_DIETA_ETAP_I, Bartek_P_DIETA_ETAP_I)

## Co to jest
Jeden szablon w dwóch kalibracjach: Konrad **2800 kcal** (B 210 / W 325 / T 70 — 30/46/22 % kcal), Bartek **2550 kcal** (B 215 / W 290 / T 70). Posiłki identyczne, gramatury przeskalowane ręcznie (np. ryż 100 g → 75 g, oliwa 10 g → 7 g). Potwierdza założenie silnika: trener skaluje ten sam tydzień, nie pisze diet od nowa.

Struktura dnia: **5 posiłków** — śniadanie, przekąska „posiłek ruchomy", obiad 1, obiad 2, kolacja. Każdy slot to lista 2–5 opcji do wyboru przez klienta. Nie ma dni tygodnia — klient sam składa dzień z opcji.

## Jak to przełożyć na bibliotekę

1. **Nowy profil „Sportowa wysokobiałkowa"** (30/22/48, baza 2600 kcal, zakres 2000–3600, 5 slotów: 25/15/22/22/16 %). To jedyny profil z dwoma obiadami — model danych już to obsługuje (`slot` jest dowolny), UI musi pokazać 5 posiłków.
2. **Opcje Łukasza → 5 odsłon tygodnia.** Każda z jego list opcji ma 3–8 pozycji; rozłożone na 7 dni × 5 odsłon dają ~35 unikalnych dni z jego posiłków (część powtórzy się między odsłonami, co jest zgodne z jego intencją „wybierz opcję").
3. **Jego tabela zamienników 1:1** (łosoś 100 g = tłuszcz + białko, orzechy 15 g, awokado 60 g, jajka 100 g + 50 g szynki) to gotowa reguła dla `swap_candidates` — do dodania jako grupa `zamiennik_tłuszczowo_białkowy` w kolejnej wersji silnika.
4. **Slajd „Suplementacja"** i wstęp motywacyjny — poza zakresem szablonów diet; wstęp warto przenieść do widoku klienta jako tekst powitalny od trenera (pole `trainer_intro` w `AssignedDiet`).
5. **Produkty dodane do bazy** (16): śledź, halibut, sardynki, łosoś wędzony, płatki kukurydziane, płatki ryżowe, płatki jaglane, rzodkiewka, serek śmietankowy light, stek wołowy, wątróbka drobiowa, ananas, szynka z piersi kurczaka, ketchup mniej kalorii, skwarki, słodzik. Baza: 158 produktów.

## Wykorzystano już
Odsłona 2 profilu **Redukcja wysokobiałkowa** zbudowana z posiłków Łukasza przyciętych do 35/25/40: pulpa białkowa z waflami, ryż na słodko ze skyrem i prażonym jabłkiem, budyń jaglany z odżywką, omlet z płatków ryżowych, placek białkowy z owocami, zapiekanki z mozzarellą light, chicken wrap, sałatka „tuńczyński", makaron z twarogiem i skwarkami, kanapki z łososiem wędzonym, stek z ziemniakami, halibut z ryżem, wafle z twarożkiem i rzodkiewką.

## Lista posiłków Łukasza (do profilu Sportowa)

**Śniadania:** jajka ×4 / mozzarella 125 g / tłusta ryba 130 g / twaróg tłusty 180 g + pieczywo 50 g + warzywa · omlet na słodko (płatki 30, owoce 50, jajko 2, czekolada 2 kostki, skyr 100, masło orzechowe 10) · wafle ryżowe 30 + twaróg tłusty 180 / łosoś wędzony 140 · kanapki z jajkiem i awokado (szynka kurczak 60, jajko 2, awokado 60, pieczywo 50) · kanapki z łososiem i almette (łosoś wędzony 90, serek 40, pieczywo 50) · skyrowa owsianka (skyr 200, płatki 30, owoce 100, czekolada 2 kostki, orzechy 10) · pomysły: jajecznica z chlebem, kanapki z mozzarellą, sałatka z tuńczyka, kanapki z szynką i jajkiem.

**Przekąska (posiłek ruchomy):** budyń jaglany (płatki jaglane 100, WPC 30, owoc 150, czekolada 2, orzechy 10) · ryż z owocami (ryż 100, owoc 150, WPI 30 / skyr 200, masło orzechowe 20) · omlet z płatków ryżowych (białka 2, płatki ryżowe 100, WPC 30 / twaróg chudy 120, owoc 150, czekolada 2, orzechy 10) · ryż na słodko ze skyrem i prażonym jabłkiem · owocowa owsianka z płatkami kukurydzianymi (owoce 150, WPC 30 / twaróg chudy 120, płatki 60, płatki kukurydziane 40, orzechy 20).

**Obiad 1 i 2:** mięso chude 200 / ryba biała 225 + ryż/kasza/makaron/komosa 100 lub ziemniaki/bataty 400 + oliwa 10 / orzechy 20 / awokado 60 + warzywa · łosoś 160 + węgle jak wyżej (bez dodatku tłuszczu) · placek z owocami (białka 200, WPC 30, owoce 100, płatki 50, czekolada 3, orzechy 10) · spaghetti bolognese (makaron 100, mielony drób lub udziec wołowy 200, oliwa 10, passata) · makaron z twarogiem (makaron 100, twaróg chudy 220, skwarki 10) · pomysły: dorsz w sosie pomidorowym, tortilla z indykiem, schab z ziemniakami, makaron ze szpinakiem i kurczakiem, stek z ziemniakami, łosoś z ryżem, makaron z serem.

**Kolacja:** zapiekanki (pieczywo 100, mozzarella light 50, szynka 80, ketchup light 20) · chicken wrap (tortilla 1,5, mięso 130, ketchup 30) · sałatka „tuńczyński" (jajko 1, tuńczyk 90, kasza jaglana 60, ketchup 25) · wafle ryżowe 60 + twarożek półtłusty 150 + rzodkiewka · koktajl (jogurt 200, płatki 50, WPI 15, owoce 50) · pulpa białkowa (WPI 20 + woda, wafle 50, owoce 60, masło orzechowe 10) · pomysły: kanapka z twarogiem, tosty z serem light, tortilla.

## Uwagi jakościowe do przeniesienia
- Łukasz podaje tłuste ryby i wątróbkę jako „tłuszcz + białko w jednym" — zgodne z naszą regułą „tłusta ryba nie jest jedynym źródłem białka" tylko dlatego, że jego porcje (160 g łososia) są większe. W profilu Sportowa z T 70 g to działa; w Redukcji nie.
- Jego przekąski to pełne posiłki 500–700 kcal, nie 300 — w profilu Sportowa slot „przekąska" dostaje 15–20 % kcal, nie 15 % jak w Standardzie.
- „Warzywa dowolne" bez gramatury — w szablonach dajemy 150–250 g warzyw jako `TŁUMIONY`, żeby kcal się zgadzały.

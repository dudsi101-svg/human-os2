"""Szablon: Standard zbilansowana, odsłona 1. Baza 2000 kcal, makro 25/30/45.
Składnik: (produkt, gramy, rola, opcje). Rola: P/C/F/NONE. unit_g dla DYSKRETNY."""
import json

def I(product, grams, role='NONE', **kw):
    d = dict(product=product, grams=grams, role=role); d.update(kw); return d

# jednostki dyskretne
EGG, SLICE_RYE, SLICE_WW, TORTILLA, BANANA, APPLE, PEAR, ORANGE, KIWI, RICE_CAKE, DATE, CHOC = 55, 35, 32, 45, 120, 180, 170, 180, 75, 9, 24, 10

def M(name, slot, share, ings, steps, flexible=False, tags=()):
    return dict(name=name, slot=slot, kcal_share=share, ingredients=ings, steps=steps, flexible=flexible, tags=list(tags))

SPICE = lambda: [I('Sól', 1), I('Pieprz czarny', 1)]

days = [
 dict(day=1, meals=[
  M('Owsianka z masłem orzechowym, bananem i skyrem','śniadanie',0.25,[
    I('Płatki owsiane',45,'C'), I('Mleko 2%',180,'NONE',min_factor=0.7,max_factor=1.3), I('Skyr naturalny',120,'P'),
    I('Masło orzechowe',15,'F'), I('Banan',BANANA,'C',class_='DYSKRETNY',unit_g=BANANA,unit_step=0.5), I('Cynamon',2)],
    'Płatki zagotuj z mlekiem (3-4 min), zdejmij z ognia, wmieszaj skyr. Podaj z bananem, masłem orzechowym i cynamonem.', tags=('szybkie',)),
  M('Kurczak stir-fry z ryżem i warzywami','obiad',0.35,[
    I('Pierś z kurczaka (surowa)',150,'P'), I('Ryż biały (suchy)',75,'C'), I('Papryka czerwona',100), I('Brokuł',120),
    I('Cebula',50), I('Olej rzepakowy',10,'F'), I('Sos sojowy',15), I('Czosnek',5), I('Imbir świeży',5)],
    'Ryż ugotuj. Kurczaka pokrój w paski, obsmaż na oleju 4-5 min, dodaj cebulę, czosnek, imbir, potem paprykę i brokuł. Smaż 5 min, dolej sos sojowy.', tags=('na_wynos',)),
  M('Jogurt grecki z borówkami i orzechami','przekąska',0.15,[
    I('Jogurt grecki 0%',150,'P'), I('Borówki',100,'C'), I('Orzechy włoskie',15,'F'), I('Miód',10,'C')],
    'Wymieszaj.', flexible=True, tags=('szybkie','na_wynos')),
  M('Kanapki z twarożkiem i warzywami','kolacja',0.25,[
    I('Chleb żytni',2*SLICE_RYE,'C',class_='DYSKRETNY',unit_g=SLICE_RYE), I('Twaróg półtłusty',120,'P'), I('Jogurt naturalny 2%',30),
    I('Szczypiorek',5), I('Ogórek',100), I('Pomidor',120), I('Oliwa z oliwek',7,'F')] + SPICE(),
    'Twaróg rozgnieć z jogurtem, szczypiorkiem, solą i pieprzem. Nałóż na chleb, dodaj warzywa skropione oliwą.', tags=('szybkie',)),
 ]),
 dict(day=2, meals=[
  M('Jajecznica z awokado i pieczywem','śniadanie',0.25,[
    I('Jajko kurze (całe)',2*EGG,'P',class_='DYSKRETNY',unit_g=EGG), I('Białko jaja',60,'P'), I('Masło',5,'F'), I('Szczypiorek',5),
    I('Chleb pełnoziarnisty',2*SLICE_WW,'C',class_='DYSKRETNY',unit_g=SLICE_WW), I('Pomidor',120), I('Awokado',50,'F')] + SPICE(),
    'Jajka z białkiem roztrzep, usmaż na maśle na małym ogniu. Podaj z pieczywem, pomidorem i awokado.'),
  M('Łosoś pieczony z batatem i fasolką','obiad',0.35,[
    I('Łosoś (surowy)',150,'P'), I('Batat (surowy)',300,'C'), I('Fasolka szparagowa',150), I('Oliwa z oliwek',5,'F'),
    I('Sok z cytryny',10), I('Koperek',5), I('Czosnek',3)] + SPICE(),
    'Batat pokrój w kostkę, skrop połową oliwy, piecz 25 min w 200°C. Łososia dołóż na ostatnie 12-15 min. Fasolkę ugotuj 6 min. Skrop cytryną, posyp koperkiem.'),
  M('Wafle z hummusem i szynką','przekąska',0.15,[
    I('Wafle ryżowe',4*RICE_CAKE,'C',class_='DYSKRETNY',unit_g=RICE_CAKE), I('Hummus',40,'F'), I('Szynka z indyka (wędlina)',40,'P'), I('Papryka czerwona',100)],
    'Wafle posmaruj hummusem, ułóż szynkę i paprykę.', flexible=True, tags=('na_wynos','szybkie')),
  M('Sałatka z tuńczykiem i fasolą','kolacja',0.25,[
    I('Tuńczyk w sosie własnym (odsączony)',100,'P'), I('Sałata',60), I('Ogórek',100), I('Kukurydza z puszki',60,'C'),
    I('Fasola czerwona z puszki (odsączona)',80,'C'), I('Oliwa z oliwek',10,'F'), I('Sok z cytryny',10),
    I('Chleb żytni',SLICE_RYE,'C',class_='DYSKRETNY',unit_g=SLICE_RYE)] + SPICE(),
    'Wszystko wymieszaj, skrop oliwą i cytryną. Podaj z chlebem.', tags=('szybkie','na_wynos')),
 ]),
 dict(day=3, meals=[
  M('Racuchy twarogowe z malinami','śniadanie',0.25,[
    I('Twaróg półtłusty',120,'P'), I('Jajko kurze (całe)',EGG,'P',class_='DYSKRETNY',unit_g=EGG,group='ciasto'),
    I('Mąka pełnoziarnista',40,'C',group='ciasto'), I('Banan',BANANA,'C',class_='DYSKRETNY',unit_g=BANANA,unit_step=0.5),
    I('Olej rzepakowy',5,'F'), I('Jogurt naturalny 2%',60), I('Maliny',100), I('Cynamon',2)],
    'Twaróg, jajko, rozgniecionego banana i mąkę wymieszaj na gęste ciasto. Smaż małe placki na oleju po 2-3 min z każdej strony. Podaj z jogurtem i malinami.'),
  M('Chili con carne z ryżem','obiad',0.35,[
    I('Wołowina mielona 90/10 (surowa)',120,'P'), I('Fasola czerwona z puszki (odsączona)',100,'C'), I('Pomidory krojone z puszki',200),
    I('Cebula',60), I('Papryka czerwona',80), I('Ryż biały (suchy)',65,'C'), I('Olej rzepakowy',5,'F'), I('Czosnek',5),
    I('Papryka słodka mielona',3), I('Koncentrat pomidorowy',15)] + SPICE(),
    'Cebulę i czosnek zeszklij, dodaj mięso i obsmaż. Wsyp paprykę, koncentrat, pomidory, fasolę. Duś 20 min. Podaj z ryżem.', tags=('na_wynos','na_zapas')),
  M('Jabłko, migdały i skyr','przekąska',0.15,[
    I('Jabłko',APPLE,'C',class_='DYSKRETNY',unit_g=APPLE,unit_step=0.5), I('Migdały',25,'F'), I('Skyr naturalny',100,'P')],
    'Zjedz osobno lub pokrój jabłko do skyru.', flexible=True, tags=('na_wynos',)),
  M('Tortilla z kurczakiem i jogurtowym sosem','kolacja',0.25,[
    I('Tortilla pszenna',TORTILLA,'C',class_='DYSKRETNY',unit_g=TORTILLA), I('Pierś z kurczaka (surowa)',140,'P'), I('Jogurt grecki 0%',40),
    I('Sałata',40), I('Ogórek',50), I('Pomidor',60), I('Oliwa z oliwek',8,'F'), I('Ciecierzyca z puszki (odsączona)',60,'C'), I('Papryka słodka mielona',2), I('Czosnek',3)] + SPICE(),
    'Kurczaka natrzyj papryką i usmaż na oliwie. Jogurt wymieszaj z czosnkiem. Zwiń wszystko w tortillę.'),
 ]),
 dict(day=4, meals=[
  M('Skyr bowl z owocami, chia i nerkowcami','śniadanie',0.25,[
    I('Skyr naturalny',200,'P'), I('Płatki owsiane',40,'C'), I('Nasiona chia',10,'F'), I('Owoce jagodowe mrożone',100,'C'),
    I('Miód',10,'C'), I('Orzechy nerkowca',15,'F')],
    'Płatki i chia zalej skyrem, odstaw na 10 min (lub na noc). Dodaj owoce, miód, orzechy.', tags=('szybkie','na_wynos')),
  M('Dorsz w pomidorach z kaszą jaglaną i cukinią','obiad',0.35,[
    I('Dorsz (surowy)',180,'P'), I('Kasza jaglana (sucha)',70,'C'), I('Passata pomidorowa',200), I('Cebula',50), I('Cukinia',150),
    I('Oliwa z oliwek',10,'F'), I('Czosnek',5), I('Oregano suszone',2)] + SPICE(),
    'Cebulę i czosnek zeszklij, dodaj cukinię i passatę, duś 10 min. Ułóż dorsza w sosie, przykryj i duś 10 min. Podaj z kaszą.'),
  M('Kanapka z jajkiem i szynką','przekąska',0.15,[
    I('Chleb żytni',2*SLICE_RYE,'C',class_='DYSKRETNY',unit_g=SLICE_RYE), I('Jajko kurze (całe)',EGG,'P',class_='DYSKRETNY',unit_g=EGG),
    I('Szynka z indyka (wędlina)',30,'P'), I('Musztarda',5), I('Rukola',20), I('Pomidor',80)],
    'Jajko ugotuj na twardo, pokrój. Złóż kanapki.', flexible=True, tags=('na_wynos',)),
  M('Sałatka grecka z ciecierzycą i pieczywem','kolacja',0.25,[
    I('Feta',40,'F'), I('Ciecierzyca z puszki (odsączona)',100,'P'), I('Ogórek',150), I('Pomidor',150), I('Oliwki czarne',20),
    I('Oliwa z oliwek',8,'F'), I('Chleb pełnoziarnisty',2*SLICE_WW,'C',class_='DYSKRETNY',unit_g=SLICE_WW), I('Oregano suszone',2)] + SPICE(),
    'Warzywa pokrój, dodaj ciecierzycę, fetę, oliwki. Skrop oliwą, posyp oregano. Podaj z chlebem.', tags=('szybkie',)),
 ]),
 dict(day=5, meals=[
  M('Kanapki z pastą jajeczną i warzywami','śniadanie',0.25,[
    I('Jajko kurze (całe)',2*EGG,'P',class_='DYSKRETNY',unit_g=EGG), I('Jogurt grecki 0%',40,'P'), I('Szczypiorek',5), I('Musztarda',5),
    I('Chleb pełnoziarnisty',3*SLICE_WW,'C',class_='DYSKRETNY',unit_g=SLICE_WW), I('Ogórek',100), I('Papryka czerwona',80), I('Masło',5,'F')] + SPICE(),
    'Jajka ugotuj na twardo, rozgnieć z jogurtem, musztardą i szczypiorkiem. Kanapki posmaruj cienko masłem, nałóż pastę i warzywa.'),
  M('Gulasz z indyka z kaszą gryczaną','obiad',0.35,[
    I('Pierś z indyka (surowa)',150,'P'), I('Kasza gryczana (sucha)',70,'C'), I('Pieczarki',100), I('Cebula',60), I('Marchew',80),
    I('Koncentrat pomidorowy',15), I('Śmietana 18%',30,'F'), I('Olej rzepakowy',5,'F'), I('Papryka słodka mielona',3),
    I('Bulion warzywny',200)] + SPICE(),
    'Indyka w kostce obsmaż, dodaj cebulę, marchew, pieczarki. Zalej bulionem, dodaj koncentrat i paprykę, duś 25 min. Zabiel śmietaną. Podaj z kaszą.', tags=('na_zapas',)),
  M('Koktajl bananowo-kakaowy','przekąska',0.15,[
    I('Banan',BANANA,'C',class_='DYSKRETNY',unit_g=BANANA,unit_step=0.5), I('Skyr naturalny',120,'P'), I('Mleko 2%',100,'NONE',min_factor=0.7,max_factor=1.3),
    I('Kakao gorzkie',5), I('Masło orzechowe',8,'F'), I('Płatki owsiane',10,'C')],
    'Zmiksuj wszystko.', flexible=True, tags=('szybkie','na_wynos')),
  M('Pieczone ziemniaki z twarogiem i kiszoną kapustą','kolacja',0.25,[
    I('Ziemniaki (surowe)',250,'C'), I('Twaróg półtłusty',120,'P'), I('Kapusta kiszona',100), I('Marchew',50), I('Oliwa z oliwek',8,'F'),
    I('Koperek',5), I('Jogurt naturalny 2%',30)] + SPICE(),
    'Ziemniaki w ćwiartkach skrop połową oliwy i piecz 30 min w 200°C. Twaróg wymieszaj z jogurtem i koperkiem. Kapustę wymieszaj z tartą marchwią i resztą oliwy.'),
 ]),
 dict(day=6, meals=[
  M('Omlet ze szpinakiem, pieczarkami i mozzarellą','śniadanie',0.25,[
    I('Jajko kurze (całe)',2*EGG,'P',class_='DYSKRETNY',unit_g=EGG), I('Białko jaja',80,'P'), I('Szpinak świeży',50), I('Pieczarki',60),
    I('Mozzarella light',25,'F'), I('Masło',4,'F'), I('Chleb żytni',2*SLICE_RYE,'C',class_='DYSKRETNY',unit_g=SLICE_RYE)] + SPICE(),
    'Pieczarki podsmaż na maśle, dodaj szpinak. Zalej roztrzepanymi jajkami, posyp mozzarellą, smaż pod przykryciem 4-5 min. Podaj z chlebem.'),
  M('Makaron z bolognese z indyka','obiad',0.35,[
    I('Makaron pełnoziarnisty (suchy)',80,'C'), I('Mięso mielone z indyka (surowe)',130,'P'), I('Passata pomidorowa',200), I('Cebula',50),
    I('Marchew',60), I('Oliwa z oliwek',8,'F'), I('Parmezan tarty',10), I('Czosnek',5), I('Oregano suszone',2)] + SPICE(),
    'Cebulę, czosnek, marchew podsmaż na oliwie, dodaj mięso i obsmaż. Wlej passatę, duś 15 min. Wymieszaj z makaronem, posyp parmezanem.', tags=('na_wynos','na_zapas')),
  M('Wafle z masłem orzechowym i gruszka','przekąska',0.15,[
    I('Wafle ryżowe',3*RICE_CAKE,'C',class_='DYSKRETNY',unit_g=RICE_CAKE), I('Masło orzechowe',15,'F'), I('Gruszka',PEAR,'C',class_='DYSKRETNY',unit_g=PEAR,unit_step=0.5),
    I('Jogurt grecki 0%',80,'P')],
    'Wafle posmaruj masłem orzechowym. Gruszkę zjedz osobno lub pokrój do jogurtu.', flexible=True, tags=('na_wynos','szybkie')),
  M('Miska z pieczoną ciecierzycą, komosą i fetą','kolacja',0.25,[
    I('Ciecierzyca z puszki (odsączona)',120,'P'), I('Komosa ryżowa (sucha)',50,'C'), I('Papryka czerwona',100), I('Rukola',30), I('Feta',30,'F'),
    I('Tahini',10,'F'), I('Sok z cytryny',10), I('Papryka słodka mielona',3), I('Czosnek',3)] + SPICE(),
    'Ciecierzycę i paprykę z papryką mieloną piecz 20 min w 200°C. Komosę ugotuj. Tahini rozrzedź cytryną i wodą na sos. Złóż miskę, posyp fetą.', tags=('na_wynos',)),
 ]),
 dict(day=7, meals=[
  M('Naleśniki owsiane z twarogiem i truskawkami','śniadanie',0.25,[
    I('Płatki owsiane',50,'C',group='ciasto'), I('Jajko kurze (całe)',EGG,'P',class_='DYSKRETNY',unit_g=EGG,group='ciasto'),
    I('Mleko 2%',100,'NONE',group='ciasto',min_factor=0.7,max_factor=1.3), I('Twaróg chudy',120,'P'), I('Truskawki',120,'C'), I('Miód',8,'C'),
    I('Olej rzepakowy',5,'F'), I('Jogurt naturalny 2%',40)],
    'Płatki zmiksuj z jajkiem i mlekiem, odstaw 5 min. Smaż cienkie naleśniki na oleju. Twaróg rozgnieć z jogurtem i miodem, nałóż, dodaj truskawki.'),
  M('Schab pieczony z ziemniakami i surówką z buraków','obiad',0.35,[
    I('Schab bez kości (surowy)',160,'P'), I('Ziemniaki (surowe)',350,'C'), I('Burak',150), I('Jogurt naturalny 2%',30), I('Olej rzepakowy',12,'F'),
    I('Musztarda',8), I('Czosnek',3), I('Koperek',5)] + SPICE(),
    'Schab natrzyj musztardą, czosnkiem, solą i olejem; piecz 25-30 min w 190°C. Ziemniaki ugotuj, posyp koperkiem. Buraki ugotuj, zetrzyj, wymieszaj z jogurtem.'),
  M('Jogurt z orzechami i daktylami','przekąska',0.15,[
    I('Jogurt naturalny 2%',200,'P'), I('Orzechy włoskie',15,'F'), I('Daktyle',2*DATE,'C',class_='DYSKRETNY',unit_g=DATE), I('Cynamon',2)],
    'Daktyle posiekaj, wymieszaj z jogurtem, posyp orzechami.', flexible=True, tags=('szybkie','na_wynos')),
  M('Krem pomidorowy z soczewicą i pieczywem','kolacja',0.25,[
    I('Soczewica czerwona (sucha)',60,'P'), I('Pomidory krojone z puszki',250,max_factor=1.2), I('Cebula',50), I('Marchew',60), I('Mleczko kokosowe',40,'F'),
    I('Bulion warzywny',300), I('Curry (mieszanka)',3), I('Czosnek',5), I('Chleb żytni',SLICE_RYE,'C',class_='DYSKRETNY',unit_g=SLICE_RYE)] + SPICE(),
    'Cebulę, czosnek, marchew zeszklij, dodaj soczewicę, pomidory, bulion, curry. Gotuj 20 min, zmiksuj, wmieszaj mleczko kokosowe. Podaj z chlebem.', tags=('na_zapas',)),
 ]),
]

template = dict(profile='Standard zbilansowana', variant=1, base_kcal=2000, kcal_min=1400, kcal_max=3200,
                macro_pct=(0.25, 0.30, 0.45), days=days)

# normalizacja klucza class_ -> class
for d in days:
    for m in d['meals']:
        for i in m['ingredients']:
            if 'class_' in i: i['class'] = i.pop('class_')

if __name__ == '__main__':
    json.dump(template, open('/home/claude/template_standard_v1.json', 'w'), ensure_ascii=False, indent=1)
    print('ok')

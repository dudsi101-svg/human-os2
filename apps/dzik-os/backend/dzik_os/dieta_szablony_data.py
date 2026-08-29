"""Wbudowany katalog szablonów diety (0.54.0).

Treść pochodzi z autorskich materiałów trenera (Lubelski Dzik) po
ANONIMIZACJI: bez imion klientów, bez osobistych wtrętów i bez cudzego
makro — pola kcal/białko/tłuszcze/węglowodany są celowo puste, bo makro
ZAWSZE ustawia trener pod konkretnego podopiecznego przy kopiowaniu.

Struktura wpisu = dokładnie `NutritionPlanVersion.content_json`
(kcal, protein_g, fat_g, carbs_g, sections[{title,body}],
meals[{name,description,swaps}]) — kopiowanie do klienta nie wymaga
translacji. Suplementacja jest tu wyłącznie TEKSTEM poglądowym
w sekcji; przypomnienia suplementów pozostają decyzją per klient
(propose-only) i nigdy nie powstają z szablonu.
"""

from __future__ import annotations

from typing import Any

DIET_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "DTPL-001",
        "title": "Dieta — Etap I (autorska, posiłki z opcjami)",
        "description": (
            "Autorski układ trenera (Lubelski Dzik): 4–5 posiłków dziennie, "
            "w każdym kilka równoważnych opcji do wyboru — klient je to, co "
            "lubi, w ramach ustalonych proporcji. Makro puste: ustaw je pod "
            "konkretnego podopiecznego po skopiowaniu."
        ),
        "content": {
            "kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carbs_g": None,
            "sections": [
                {
                    "title": "Jak korzystać z tej diety",
                    "body": (
                        "W każdym posiłku wybierz JEDNĄ z propozycji. To "
                        "dieta jest dla Ciebie, a nie Ty dla diety — "
                        "komponuj posiłki tak, żeby Ci smakowały, a nie "
                        "były katorżnicze. Jedzenie po swojemu pozwala "
                        "zbudować nawyk, który zostaje na zawsze; zachęcam "
                        "do „kombinowania”, żeby nie było jałowo i "
                        "monotonnie. Smacznego!"
                    ),
                },
                {
                    "title": "Zasada proporcji przy własnych pomysłach",
                    "body": (
                        "Wszystkie propozycje korelują z Twoimi "
                        "oryginalnymi posiłkami — trzymaj się SWOICH "
                        "proporcji. Przykład: jeśli w obiedzie masz 50 g "
                        "ryżu i 100 g mięsa, a chcesz schab z ziemniakami, "
                        "bierzesz 100 g schabu i 200 g ziemniaków. Jak nie "
                        "wiesz, ile co ma — sprawdź w aplikacji w bazie "
                        "produktów."
                    ),
                },
                {
                    "title": "Dodatkowe pomysły na posiłki",
                    "body": (
                        "Śniadania: jajecznica z chlebem; kanapki z "
                        "łososiem; kanapki z awokado i jajkiem; owsianka; "
                        "kanapki z mozzarellą; wafle ryżowe z twarogiem; "
                        "sałatka z tuńczyka; kanapki z szynką i jajkiem.\n"
                        "Obiady: dorsz w sosie pomidorowym; tortilla z "
                        "indykiem; schab z ziemniakami; makaron ze "
                        "szpinakiem i piersią kurczaka; makaron bolognese "
                        "z indykiem; stek z ziemniakami; łosoś pieczony "
                        "z ryżem; makaron z serem.\n"
                        "Kolacje: zapiekanki; kanapka z twarogiem; tosty "
                        "z serem „mniej tłuszczu”; sałatka z tuńczykiem; "
                        "tortilla."
                    ),
                },
                {
                    "title": "Ściąga zamienników 1:1 — produkty białkowe (≈20 g białka)",
                    "body": (
                        "Pierś z kurczaka/indyka 100 g · Białko WPC 30 g · "
                        "Skyr 200 g · Twaróg chudy 125 g · Polędwica "
                        "wołowa (tatar) 100 g · Szynka z piersi kurczaka "
                        "100 g · Dorsz 125 g · Białka jaj 200 g · Krewetki "
                        "125 g · Mozzarella light 100 g."
                    ),
                },
                {
                    "title": "Ściąga zamienników 1:1 — produkty tłuszczowe (≈10 g tłuszczu)",
                    "body": (
                        "Uwaga: część produktów tłuszczowych dostarcza też "
                        "białko — wtedy NIE dokładasz osobnego produktu "
                        "białkowego.\n"
                        "Łosoś pieczony/wędzony 100 g — nie jesz osobnego "
                        "białka · Stek wołowy 100 g — nie jesz · Wątróbka "
                        "120 g — nie jesz · Tłuste ryby 100 g — nie jesz · "
                        "Mozzarella 70 g — dobierz ~10 g białka (np. 50 g "
                        "szynki) · Jajka 100 g — dobierz ~10 g białka · "
                        "Parówki z piersi kurczaka 80 g — dobierz ~10 g "
                        "białka · Orzechy 15 g — jesz białko normalnie · "
                        "Masło orzechowe 15 g — jesz · Awokado 60 g — "
                        "jesz · Oliwa 10 g — jesz · Nasiona chia 20 g — "
                        "jesz · Chipsy „z pieca” 50 g — jesz, ale odejmij "
                        "40 g węglowodanów z posiłku."
                    ),
                },
                {
                    "title": "Ściąga zamienników 1:1 — produkty węglowodanowe (na 100 g produktu)",
                    "body": (
                        "Ryż 100 g · Kasze 100 g · Płatki owsiane 100 g · "
                        "Makaron 100 g · Płatki kukurydziane 100 g · Mąka "
                        "100 g · Pieczywo 130 g · Banan 360 g · Borówki "
                        "550 g · Maliny 600 g. Produkty gotowe (głównie po "
                        "treningu): pierogi, naleśniki, wafle ryżowe "
                        "smakowe, lody śmietankowe, ziemniaki do "
                        "upieczenia — na etykiecie maks. 5 g tłuszczu na "
                        "100 g. Owoce nie mogą być jedynym źródłem węgli "
                        "w posiłku — łącz je z ryżem/makaronem/płatkami."
                    ),
                },
                {
                    "title": "Suplementacja — przykładowy układ (do decyzji z trenerem)",
                    "body": (
                        "Poglądowy schemat z materiału źródłowego — "
                        "konkretne preparaty i dawki zawsze ustalane "
                        "indywidualnie z trenerem: na czczo glutamina; do "
                        "śniadania omega-3, witamina D3, magnez, witaminy "
                        "z grupy B; kreatyna codziennie (pora bez "
                        "znaczenia); do ostatniego posiłku omega-3; przed "
                        "snem ashwagandha oraz magnez z cynkiem."
                    ),
                },
            ],
            "meals": [
                {
                    "name": "Śniadanie",
                    "description": (
                        "Opcja 1 (wytrawnie): jajka ×4 LUB mozzarella "
                        "125 g LUB tłusta ryba (makrela, śledź, tuńczyk, "
                        "halibut, sardynki 130 g / łosoś wędzony 140 g) "
                        "LUB twaróg tłusty 180 g + pieczywo na zakwasie "
                        "50 g + warzywa dowolne.\n"
                        "Opcja 2 (omlet na słodko): płatki owsiane 30 g + "
                        "owoce 50 g (oprócz banana) + jajko ×2 + 2 kostki "
                        "gorzkiej czekolady + skyr naturalny 100 g + masło "
                        "orzechowe 10 g.\n"
                        "Opcja 3: wafle ryżowe 35 g + twaróg tłusty 180 g "
                        "/ łosoś wędzony 140 g + szczypiorek i warzywa.\n"
                        "Opcja 4 (kanapki z jajkiem i awokado): szynka "
                        "z piersi kurczaka 60 g + jajko ×2 + awokado 60 g "
                        "+ pieczywo 50 g + warzywa.\n"
                        "Opcja 5 (kanapki z łososiem): łosoś wędzony 90 g "
                        "+ serek śmietankowy 40 g + pieczywo 50 g + "
                        "warzywa.\n"
                        "Opcja 6 (skyrowa owsianka): skyr 200 g + płatki "
                        "owsiane 30 g + owoce 100 g + 2 kostki gorzkiej "
                        "czekolady + masło orzechowe lub orzechy 10 g."
                    ),
                    "swaps": "Wybierz jedną opcję; zamienniki wg ściągi 1:1.",
                },
                {
                    "name": "Przekąska (posiłek ruchomy)",
                    "description": (
                        "Każda opcja to CAŁY posiłek.\n"
                        "Opcja 1 (budyń jaglany): płatki jaglane 100 g + "
                        "odżywka białkowa 30 g + owoc 150 g + cynamon "
                        "i słodzik + 2 kostki gorzkiej czekolady + masło "
                        "orzechowe lub orzechy 10 g.\n"
                        "Opcja 2 (ryż z owocami): ryż 100 g + owoc 150 g + "
                        "białko WPI 30 g LUB skyr 200 g + masło orzechowe "
                        "20 g LUB orzechy 20 g.\n"
                        "Opcja 3 (omlet owsiany): białka jaj ×2 + płatki "
                        "ryżowe lub ryż 100 g + odżywka 30 g / twaróg "
                        "chudy 120 g + owoc 150 g + 2 kostki czekolady + "
                        "masło orzechowe lub orzechy 10 g.\n"
                        "Opcja 4 (ryż na słodko): ryż 100 g + skyr 200 g / "
                        "WPI 30 g + owoc 150 g (polecam jabłko prażone "
                        "z cynamonem) + 2 kostki czekolady + masło "
                        "orzechowe lub orzechy 10 g.\n"
                        "Opcja 5 (owocowa owsianka z nesquikami): owoce "
                        "150 g (borówki/maliny) + białko 30 g / twaróg "
                        "chudy 120 g + płatki ryżowe/jaglane/owsiane 60 g "
                        "+ płatki kukurydziane 40 g + orzechy/masło "
                        "orzechowe/migdały 20 g.\n"
                        "Opcja 6 (placek z owocami): białka jaj 200 g + "
                        "białko 30 g + owoce leśne 100 g / jabłko 100 g / "
                        "ananas 90 g / gruszka 90 g + płatki jaglane/"
                        "gryczane/orkiszowe lub kasza jaglana 50 g + "
                        "cynamon + 3 kostki czekolady + masło orzechowe "
                        "lub orzechy 10 g."
                    ),
                    "swaps": "Wybierz jedną opcję; zamienniki wg ściągi 1:1.",
                },
                {
                    "name": "Obiad 1 i 2 (dwa oddzielne obiady)",
                    "description": (
                        "Opcja 1: kurczak / indyk / chuda wołowina "
                        "(ligawa, udziec, polędwica) 200 g LUB ryby białe "
                        "/ owoce morza 225 g + ryż/kasza/makaron/komosa "
                        "75 g LUB ziemniaki/bataty 300 g + oliwa 7 g LUB "
                        "orzechy 15 g LUB awokado 45 g + warzywa dowolne.\n"
                        "Opcja 2: łosoś pieczony lub grillowany 160 g + "
                        "ryż/kasza/makaron/komosa 75 g LUB ziemniaki/"
                        "bataty 300 g + warzywa (bez dodatkowego "
                        "tłuszczu — łosoś go dostarcza).\n"
                        "Opcja 3 (spaghetti bolognese): makaron 75 g + "
                        "mięso mielone z piersi kurczaka/indyka 200 g LUB "
                        "z udźca wołowego 200 g + oliwa 7 g + passata "
                        "pomidorowa z przyprawami.\n"
                        "Opcja 4 (makaron z twarogiem): makaron 75 g + "
                        "twaróg chudy 220 g + skwarki 10 g + opcjonalnie "
                        "cebula."
                    ),
                    "swaps": "Wybierz po jednej opcji na każdy z dwóch obiadów.",
                },
                {
                    "name": "Kolacja",
                    "description": (
                        "Opcja 1 (zapiekanki): pieczywo 100 g + mozzarella "
                        "light 60 g + szynka z piersi kurczaka (min. 93% "
                        "mięsa) / indyk 80 g + ketchup „mniej kalorii” "
                        "20 g.\n"
                        "Opcja 2 (chicken wrap): tortilla 1,5 szt. + "
                        "kurczak/indyk/wołowina 140 g + ketchup 30 g + "
                        "warzywa.\n"
                        "Opcja 3 (sałatka tuńczykowa): jajko 1 szt. + "
                        "tuńczyk w wodzie 90 g + kasza jaglana 60 g + "
                        "ketchup 25 g + warzywa.\n"
                        "Opcja 4: wafle ryżowe 60 g + twarożek półtłusty "
                        "160 g + rzodkiewka.\n"
                        "Opcja 5 (koktajl): jogurt naturalny 200 g + "
                        "płatki owsiane 50 g + białko WPI 15 g + owoce "
                        "50 g.\n"
                        "Opcja 6 (pulpa białkowa): wafle ryżowe 50 g + "
                        "białko WPI 20 g + owoce 60 g + masło orzechowe "
                        "10 g. Pulpa: białko + zimna woda — gęstość wedle "
                        "uznania."
                    ),
                    "swaps": "Wybierz jedną opcję; zamienniki wg ściągi 1:1.",
                },
            ],
        },
    },
]


def list_diet_templates() -> list[dict[str, Any]]:
    """Metadane katalogu — do listy wyboru w panelu trenera."""
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "description": t["description"],
            "meals": len(t["content"]["meals"]),
            "sections": len(t["content"]["sections"]),
        }
        for t in DIET_TEMPLATES
    ]


def get_diet_template(template_id: str) -> dict[str, Any] | None:
    for t in DIET_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None

"""Kreator diety: tygodniowa PROPOZYCJA posiłków z katalogu produktów.

Granica roli (Human OS): kreator wyłącznie proponuje — trener przegląda,
edytuje i świadomie tworzy z propozycji plan żywieniowy. Nic nie zapisuje
się samo, żadna propozycja nie trafia do klienta bez decyzji człowieka.

Zasady konstrukcji:

* **Deterministycznie.** Te same wejścia dają tę samą propozycję —
  zmienność między dniami pochodzi z jawnej rotacji puli produktów po
  indeksie dnia, nie z losowości. Propozycję da się odtworzyć i wyjaśnić.
* **Regułowo, bez AI.** Dobór po dominującym makro i dopasowaniu
  kategorii do pory dnia; sugestia przyrządzenia składana z reguł per
  kategoria. Zero wywołań zewnętrznych.
* **Braki są ostrzeżeniami, nigdy wyjątkami** — wzorzec z istniejącej
  Sugestii diety (`diet_suggestion`).
* **Makro domykane sekwencyjnie:** najpierw źródło białka, potem jego
  wkład tłuszczu/węgli odejmuje się od pozostałych celów, itd. Dzięki
  temu sumy dnia lądują blisko celu zamiast systematycznie go przebijać.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Sloty posiłków wg liczby posiłków dziennie: (nazwa, waga kcal).
#: Wagi w obrębie zestawu sumują się do 1.0.
SLOTY: dict[int, tuple[tuple[str, float], ...]] = {
    2: (("Śniadanie", 0.45), ("Obiadokolacja", 0.55)),
    3: (("Śniadanie", 0.30), ("Obiad", 0.40), ("Kolacja", 0.30)),
    4: (("Śniadanie", 0.25), ("II śniadanie", 0.15), ("Obiad", 0.35),
        ("Kolacja", 0.25)),
    5: (("Śniadanie", 0.25), ("II śniadanie", 0.10), ("Obiad", 0.30),
        ("Podwieczorek", 0.10), ("Kolacja", 0.25)),
    6: (("Śniadanie", 0.20), ("II śniadanie", 0.10), ("Obiad", 0.30),
        ("Podwieczorek", 0.10), ("Kolacja", 0.20), ("Przekąska", 0.10)),
}

#: Kategorie katalogu pasujące do pory dnia. Slot spoza mapy (i pusta
#: pula po filtrze) wraca do pełnej puli — z ostrzeżeniem, nie wyjątkiem.
SLOT_KATEGORIE: dict[str, tuple[str, ...]] = {
    "Śniadanie": ("Nabiał", "Jaja", "Zboża i pieczywo", "Owoce",
                  "Orzechy i nasiona", "Tłuszcze i oleje"),
    "II śniadanie": ("Nabiał", "Owoce", "Orzechy i nasiona",
                     "Zboża i pieczywo", "Odżywki i suplementy"),
    "Obiad": ("Mięso i drób", "Ryby i owoce morza", "Kasze, ryż i makarony",
              "Warzywa", "Rośliny strączkowe", "Tłuszcze i oleje"),
    "Obiadokolacja": ("Mięso i drób", "Ryby i owoce morza",
                      "Kasze, ryż i makarony", "Warzywa",
                      "Rośliny strączkowe", "Tłuszcze i oleje", "Jaja"),
    "Podwieczorek": ("Owoce", "Orzechy i nasiona", "Nabiał",
                     "Przekąski i słodycze"),
    "Kolacja": ("Jaja", "Nabiał", "Warzywa", "Zboża i pieczywo",
                "Ryby i owoce morza", "Tłuszcze i oleje"),
    "Przekąska": ("Owoce", "Orzechy i nasiona", "Nabiał",
                  "Odżywki i suplementy"),
}

#: Szacunkowy czas przygotowania per kategoria (minuty). Jawnie heurystyka
#: — „szacunek wg kategorii składników", nie pomiar. Montaż posiłku
#: doliczany osobno.
CZAS_KATEGORII: dict[str, int] = {
    "Mięso i drób": 25,
    "Ryby i owoce morza": 20,
    "Kasze, ryż i makarony": 20,
    "Rośliny strączkowe": 15,   # wariant z puszki / szybkie
    "Dania gotowe i fast food": 10,
    "Jaja": 10,
    "Warzywa": 10,
    "Zboża i pieczywo": 5,
    "Nabiał": 3,
    "Owoce": 3,
    "Orzechy i nasiona": 2,
    "Tłuszcze i oleje": 1,
    "Przyprawy i dodatki": 1,
    "Przekąski i słodycze": 1,
    "Napoje": 1,
    "Odżywki i suplementy": 2,
}
CZAS_MONTAZU = 5  # minuty na złożenie/podanie, doliczane raz na posiłek

#: Czasownik przyrządzenia per kategoria — do regułowej sugestii.
METODA: dict[str, str] = {
    "Mięso i drób": "usmaż lub upiecz",
    "Ryby i owoce morza": "upiecz lub uduś",
    "Kasze, ryż i makarony": "ugotuj wg opakowania",
    "Rośliny strączkowe": "odcedź (puszka) albo ugotuj",
    "Jaja": "ugotuj lub usmaż",
    "Warzywa": "pokrój na surowo albo krótko podsmaż",
    "Zboża i pieczywo": "przygotuj do podania",
    "Nabiał": "podaj na zimno",
    "Owoce": "umyj i pokrój",
    "Orzechy i nasiona": "posyp na wierzch",
    "Tłuszcze i oleje": "dodaj do smaku",
    "Odżywki i suplementy": "zmieszaj wg etykiety",
}

#: Kolejność domykania makro. Ostatnie w kolejności jest najcelniejsze
#: (zbiera odjęte wkłady wszystkich wcześniejszych pozycji) — a trenerowi
#: najbardziej zależy na trafieniu białka, więc białko idzie na końcu.
_MAKRA = ("CARB", "FAT", "PROTEIN")
_POLE = {"PROTEIN": "protein_100g", "FAT": "fat_100g", "CARB": "carbs_100g"}
_KCAL_NA_GRAM = {"PROTEIN": 4.0, "FAT": 9.0, "CARB": 4.0}
#: Górny limit gramatury jednej pozycji w posiłku — porcja większa niż
#: pół kilograma jednego produktu to znak złego doboru, nie propozycja.
MAKS_GRAMY_POZYCJI = 500.0


@dataclass
class Skladnik:
    """Widok produktu potrzebny kreatorowi (odcięcie od ORM ułatwia testy)."""

    id: str
    name: str
    category: str
    kcal_100g: float
    protein_100g: float
    fat_100g: float
    carbs_100g: float
    unit_name: str | None = None
    unit_grams: float | None = None
    default_portion_g: float | None = None


@dataclass
class _Wynik:
    dni: list[dict[str, Any]] = field(default_factory=list)
    ostrzezenia: list[str] = field(default_factory=list)


def dominujace_makro(s: Skladnik) -> str:
    udzialy = {
        "PROTEIN": s.protein_100g * 4,
        "FAT": s.fat_100g * 9,
        "CARB": s.carbs_100g * 4,
    }
    return max(udzialy, key=lambda k: udzialy[k])


def _czas(kategoria: str) -> int:
    return CZAS_KATEGORII.get(kategoria, 10)


def _pozycja(s: Skladnik, gramy: float) -> dict[str, Any]:
    gramy = round(min(gramy, MAKS_GRAMY_POZYCJI), 1)
    return {
        "product_id": s.id,
        "name": s.name,
        "category": s.category,
        "grams": gramy,
        "kcal": round(gramy / 100 * s.kcal_100g, 1),
        "protein_g": round(gramy / 100 * s.protein_100g, 1),
        "fat_g": round(gramy / 100 * s.fat_100g, 1),
        "carbs_g": round(gramy / 100 * s.carbs_100g, 1),
        "units": round(gramy / s.unit_grams, 1) if s.unit_grams else None,
        "unit_name": s.unit_name,
    }


def _sugestia_przyrzadzenia(pozycje: list[dict[str, Any]]) -> str:
    """Regułowy opis przyrządzenia: po jednej wskazówce na kategorię,
    w kolejności od najdłuższej obróbki (gotowanie startuje pierwsze)."""
    widziane: dict[str, str] = {}
    for p in sorted(pozycje, key=lambda x: -_czas(x["category"])):
        kat = p["category"]
        if kat in widziane or kat not in METODA:
            continue
        widziane[kat] = f"{p['name']} — {METODA[kat]}"
    if not widziane:
        return "Podaj składniki wg uznania."
    return "; ".join(widziane.values()) + "."


#: Zdrowa porcja: pozycja nie powinna przekraczać tylu porcji domyślnych
#: z katalogu. Wyklucza absurdy typu „czosnek 260 g" (porcja ~5 g),
#: przepuszcza normalne posiłki (jogurt 3×150 g).
MAKS_KROTNOSC_PORCJI = 4.0


def _maks_gramy(s: Skladnik) -> float:
    """Górny limit gramatury dla produktu: 4× porcja domyślna z katalogu,
    a bez zadeklarowanej porcji — ogólny limit pozycji."""
    if s.default_portion_g and s.default_portion_g > 0:
        return min(MAKS_GRAMY_POZYCJI,
                   s.default_portion_g * MAKS_KROTNOSC_PORCJI)
    return MAKS_GRAMY_POZYCJI


def _wybierz(
    grupa: list[Skladnik], obrot: int, cel_g: float, pole: str
) -> Skladnik:
    """Rotacja po grupie z bezpiecznikiem zdrowej porcji: kandydat, który
    do pokrycia celu potrzebowałby gramatury ponad własny limit porcji,
    przegrywa z najbliższym w rotacji, który się mieści."""
    n = len(grupa)
    for przesuniecie in range(n):
        s = grupa[(obrot + przesuniecie) % n]
        na_100 = getattr(s, pole)
        if na_100 > 0 and cel_g / na_100 * 100 <= _maks_gramy(s):
            return s
    return grupa[obrot % n]


def _rozwiaz_gramy(
    produkty: dict[str, Skladnik], cele: dict[str, float]
) -> dict[str, float] | None:
    """Dokładna gramatura trzech produktów na trzy cele makro naraz —
    układ równań 3×3 (wzory Cramera, bez zależności zewnętrznych).
    Zwraca None, gdy układ jest osobliwy albo rozwiązanie wychodzi poza
    zdrowe granice — wtedy woła się fallback sekwencyjny."""
    if set(produkty) != set(_MAKRA):
        return None
    kol = [produkty["CARB"], produkty["FAT"], produkty["PROTEIN"]]
    # Wiersze: białko / tłuszcz / węgle na GRAM produktu.
    a = [[s.protein_100g / 100 for s in kol],
         [s.fat_100g / 100 for s in kol],
         [s.carbs_100g / 100 for s in kol]]
    t = [cele["PROTEIN"], cele["FAT"], cele["CARB"]]

    def det3(m: list[list[float]]) -> float:
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))

    d = det3(a)
    if abs(d) < 1e-9:
        return None
    gramy: dict[str, float] = {}
    for i, makro in enumerate(("CARB", "FAT", "PROTEIN")):
        m = [wiersz[:] for wiersz in a]
        for w in range(3):
            m[w][i] = t[w]
        g = det3(m) / d
        s = produkty[makro]
        if g < 0 or g > _maks_gramy(s):
            return None
        gramy[makro] = g
    return gramy


def zbuduj_propozycje(
    skladniki: list[Skladnik],
    *,
    target_kcal: float,
    procent: dict[str, float],
    posilkow_dziennie: int,
    dni: int,
    wykluczone_kategorie: set[str] | None = None,
    wykluczone_produkty: set[str] | None = None,
    preferowane_produkty: set[str] | None = None,
    maks_minut_na_posilek: int | None = None,
) -> dict[str, Any]:
    """Buduje propozycję `dni` dni po `posilkow_dziennie` posiłków.

    `procent` to {"protein","fat","carbs"} sumujące się do ~100 —
    walidacja zakresów należy do warstwy API; tu tylko matematyka.
    """
    wykluczone_kategorie = wykluczone_kategorie or set()
    wykluczone_produkty = wykluczone_produkty or set()
    preferowane_produkty = preferowane_produkty or set()

    wynik = _Wynik()
    pula = [
        s for s in skladniki
        if s.category not in wykluczone_kategorie
        and s.id not in wykluczone_produkty
        and s.kcal_100g > 0
    ]
    if not pula:
        wynik.ostrzezenia.append(
            "Po zastosowaniu wykluczeń pula produktów jest pusta — "
            "propozycja nie może powstać."
        )
        return _zloz_wynik(wynik, target_kcal, procent, dni)

    # Cele dnia w gramach (4/9/4 kcal na gram).
    cele_dnia = {
        "PROTEIN": target_kcal * procent["protein"] / 100 / 4,
        "FAT": target_kcal * procent["fat"] / 100 / 9,
        "CARB": target_kcal * procent["carbs"] / 100 / 4,
    }
    sloty = SLOTY[posilkow_dziennie]

    # Preferowane produkty na początek każdej grupy (stabilnie).
    def _kolejnosc(s: Skladnik) -> tuple[int, str]:
        return (0 if s.id in preferowane_produkty else 1, s.id)

    for dzien_nr in range(1, dni + 1):
        posilki: list[dict[str, Any]] = []
        for slot_nr, (nazwa_slotu, waga) in enumerate(sloty):
            pasujace_kategorie = SLOT_KATEGORIE.get(nazwa_slotu, ())
            pula_slotu = [s for s in pula if s.category in pasujace_kategorie]
            if not pula_slotu:
                pula_slotu = pula
                wynik.ostrzezenia.append(
                    f"Dzień {dzien_nr}, {nazwa_slotu}: brak produktów "
                    "z kategorii pasujących do pory dnia — użyto pełnej puli."
                )
            grupy: dict[str, list[Skladnik]] = {m: [] for m in _MAKRA}
            for s in pula_slotu:
                grupy[dominujace_makro(s)].append(s)
            for grupa in grupy.values():
                grupa.sort(key=_kolejnosc)
                if maks_minut_na_posilek is not None:
                    # Budżet czasu przestawia szybsze produkty na przód —
                    # preferencje nadal wygrywają w obrębie tego samego czasu.
                    grupa.sort(key=lambda s: (
                        0 if s.id in preferowane_produkty else 1,
                        _czas(s.category), s.id,
                    ))

            cele_posilku = {m: cele_dnia[m] * waga for m in _MAKRA}
            pozycje: list[dict[str, Any]] = []
            obrot = dzien_nr - 1 + slot_nr  # jawna rotacja: dzień + slot

            # Wybór po jednym produkcie na makro (rotacja + zdrowa porcja).
            wybrane: dict[str, Skladnik] = {}
            for makro in _MAKRA:
                if cele_posilku[makro] <= 1.0:
                    continue
                grupa = grupy[makro]
                if not grupa:
                    wynik.ostrzezenia.append(
                        f"Dzień {dzien_nr}, {nazwa_slotu}: brak produktu "
                        f"z przewagą "
                        f"{'białka' if makro == 'PROTEIN' else 'tłuszczu' if makro == 'FAT' else 'węglowodanów'}"
                        " w dopasowanej puli."
                    )
                    continue
                wybrane[makro] = _wybierz(
                    grupa, obrot, cele_posilku[makro], _POLE[makro]
                )

            # Najpierw dokładnie: układ 3×3 na wszystkie makro naraz —
            # wtedy również kcal ląduje w celu (tożsamość 4/9/4).
            dokladnie = _rozwiaz_gramy(wybrane, cele_posilku)
            if dokladnie is not None:
                for makro in _MAKRA:
                    pozycje.append(_pozycja(wybrane[makro], dokladnie[makro]))
            else:
                # Fallback: sekwencyjne domykanie węgle → tłuszcz → białko
                # z odjęciem wkładów krzyżowych (białko ostatnie = najcelniejsze).
                pozostalo = dict(cele_posilku)
                for makro in _MAKRA:
                    s = wybrane.get(makro)
                    cel = pozostalo[makro]
                    if s is None or cel <= 1.0:
                        continue
                    na_100 = getattr(s, _POLE[makro])
                    if na_100 <= 0:
                        continue
                    poz = _pozycja(s, cel / na_100 * 100)
                    pozycje.append(poz)
                    pozostalo["PROTEIN"] -= poz["protein_g"]
                    pozostalo["FAT"] -= poz["fat_g"]
                    pozostalo["CARB"] -= poz["carbs_g"]

            czas = (max((_czas(p["category"]) for p in pozycje), default=0)
                    + (CZAS_MONTAZU if pozycje else 0))
            if maks_minut_na_posilek is not None and czas > maks_minut_na_posilek:
                wynik.ostrzezenia.append(
                    f"Dzień {dzien_nr}, {nazwa_slotu}: szacowany czas "
                    f"{czas} min przekracza budżet {maks_minut_na_posilek} "
                    "min mimo doboru najszybszych produktów."
                )
            posilki.append({
                "name": nazwa_slotu,
                "kcal_share": waga,
                "entries": pozycje,
                "totals": _sumy(pozycje),
                "prep_minutes": czas,
                "prep_suggestion": _sugestia_przyrzadzenia(pozycje),
            })
        wynik.dni.append({
            "day_no": dzien_nr,
            "meals": posilki,
            "totals": _sumy([e for m in posilki for e in m["entries"]]),
        })
    return _zloz_wynik(wynik, target_kcal, procent, dni)


def _sumy(pozycje: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "kcal": round(sum(p["kcal"] for p in pozycje), 1),
        "protein_g": round(sum(p["protein_g"] for p in pozycje), 1),
        "fat_g": round(sum(p["fat_g"] for p in pozycje), 1),
        "carbs_g": round(sum(p["carbs_g"] for p in pozycje), 1),
    }


def _zloz_wynik(
    wynik: _Wynik, target_kcal: float, procent: dict[str, float], dni: int
) -> dict[str, Any]:
    cel = {
        "kcal": round(target_kcal, 1),
        "protein_g": round(target_kcal * procent["protein"] / 100 / 4, 1),
        "fat_g": round(target_kcal * procent["fat"] / 100 / 9, 1),
        "carbs_g": round(target_kcal * procent["carbs"] / 100 / 4, 1),
    }
    if wynik.dni:
        srednia = {
            k: round(sum(d["totals"][k] for d in wynik.dni) / len(wynik.dni), 1)
            for k in ("kcal", "protein_g", "fat_g", "carbs_g")
        }
    else:
        srednia = {k: 0.0 for k in ("kcal", "protein_g", "fat_g", "carbs_g")}
    return {
        "target": cel,
        "days": wynik.dni,
        "daily_average": srednia,
        "warnings": wynik.ostrzezenia,
        "disclaimer": (
            "To propozycja wygenerowana regułowo z Twojego katalogu — "
            "przejrzyj, dostosuj i dopiero wtedy utwórz z niej plan."
        ),
        "nutrition_plan_content": _tresc_planu(wynik.dni, cel),
    }


def _tresc_planu(dni: list[dict[str, Any]], cel: dict[str, float]) -> dict[str, Any]:
    """Kształt zgodny z `content_json` wersji planu żywieniowego —
    trener tworzy plan istniejącym `POST /nutrition` bez przepisywania."""
    meals: list[dict[str, Any]] = []
    for d in dni:
        for m in d["meals"]:
            skladniki = ", ".join(
                f"{e['name']} {e['grams']} g"
                + (f" (~{e['units']} {e['unit_name']})" if e["units"] else "")
                for e in m["entries"]
            )
            t = m["totals"]
            meals.append({
                "name": (f"Dzień {d['day_no']} — {m['name']}"
                         if len(dni) > 1 else m["name"]),
                "description": (
                    f"{skladniki}. Przygotowanie (~{m['prep_minutes']} min): "
                    f"{m['prep_suggestion']} "
                    f"[{t['kcal']} kcal, B {t['protein_g']} g / "
                    f"T {t['fat_g']} g / W {t['carbs_g']} g]"
                ),
                "swaps": "",
            })
    return {
        "kcal": cel["kcal"],
        "protein_g": cel["protein_g"],
        "fat_g": cel["fat_g"],
        "carbs_g": cel["carbs_g"],
        "sections": [],
        "meals": meals,
    }

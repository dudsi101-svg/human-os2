"""Kreator diety v2: tygodniowa PROPOZYCJA posiłków komponowana wg zasad
uznanych wzorców żywieniowych (śródziemnomorski / DASH), z katalogu
trenera dopełnianego jawnie z wbudowanej bazy.

Granica roli (Human OS): kreator wyłącznie proponuje — trener przegląda,
edytuje i świadomie tworzy z propozycji plan żywieniowy. Nic nie zapisuje
się samo, żadna propozycja nie trafia do klienta bez decyzji człowieka.

Zasady konstrukcji:

* **Deterministycznie.** Te same wejścia dają tę samą propozycję —
  zmienność między dniami pochodzi z jawnej rotacji po indeksie dnia.
* **Regułowo, bez AI.** Zero wywołań zewnętrznych.
* **Kompozycja, nie tylko arytmetyka** (v2, po zrzutach z produkcji
  24.08): każdy główny posiłek to źródło białka + węgli + tłuszczu
  (solver 3×3) PLUS dodatek warzywny/owocowy w stałej rozsądnej porcji —
  wzorzec śródziemnomorski/DASH: warzywa lub owoce w każdym posiłku,
  ryby i strączkowe premiowane w rotacji obiadowej. Makra dodatku
  odejmują się od celów slotu przed solverem, więc sumy dnia nadal
  trafiają cel.
* **Katalog trenera jest pierwszy, wbudowana baza dopełnia.** Gdy
  w katalogu trenera brakuje źródła makro dla slotu, kandydat pochodzi
  z wbudowanej bazy i jest JAWNIE oznaczony (`source: "builtin"`) —
  propozycja nigdy nie wychodzi kaleka, a trener widzi, czego nie ma
  u siebie (pierwszy prawdziwy katalog dał posiłki z samych wafli
  ryżowych i 1168 kcal na cel 2200).
* **Ostrzeżenia są zbiorcze** — deduplikacja po (slot, problem)
  z licznikiem dni; 28 żółtych boxów ze zrzutu to był błąd UX.
* **Braki są ostrzeżeniami, nigdy wyjątkami.**
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

#: Sloty posiłków wg liczby posiłków dziennie: (nazwa, waga kcal).
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

#: Kategorie katalogu pasujące do pory dnia (porównanie znormalizowane).
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

#: Dodatek kompozycyjny per slot: (kategoria, gramy). Warzywa do posiłków
#: głównych, owoc do śniadań i przekąsek — stała, rozsądna porcja, której
#: makra odejmują się od celów slotu przed solverem. Wzorzec
#: śródziemnomorski/DASH; dodatek jest opcjonalny (brak kategorii w puli
#: nie generuje ostrzeżenia).
DODATKI_SLOTU: dict[str, tuple[str, float]] = {
    "Śniadanie": ("Owoce", 120.0),
    "II śniadanie": ("Owoce", 100.0),
    "Obiad": ("Warzywa", 200.0),
    "Obiadokolacja": ("Warzywa", 200.0),
    "Podwieczorek": ("Owoce", 100.0),
    "Kolacja": ("Warzywa", 150.0),
    "Przekąska": ("Owoce", 100.0),
}

#: Kategorie premiowane w rotacji białka obiadowego (ryby ≥ raz w tygodniu,
#: strączkowe często — zalecenia wzorca śródziemnomorskiego).
PREMIA_OBIADOWA = ("Ryby i owoce morza", "Rośliny strączkowe")

#: Szacunkowy czas przygotowania per kategoria (minuty) — jawna heurystyka.
CZAS_KATEGORII: dict[str, int] = {
    "Mięso i drób": 25,
    "Ryby i owoce morza": 20,
    "Kasze, ryż i makarony": 20,
    "Rośliny strączkowe": 15,
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
CZAS_MONTAZU = 5

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

#: Kolejność domykania makro: ostatnie jest najcelniejsze — białko.
_MAKRA = ("CARB", "FAT", "PROTEIN")
_POLE = {"PROTEIN": "protein_100g", "FAT": "fat_100g", "CARB": "carbs_100g"}
_NAZWA_MAKRO = {"PROTEIN": "białka", "FAT": "tłuszczu", "CARB": "węglowodanów"}
MAKS_GRAMY_POZYCJI = 500.0
MAKS_KROTNOSC_PORCJI = 4.0


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
    #: "coach" = katalog trenera, "builtin" = wbudowana baza (dopełnienie).
    source: str = "coach"


@dataclass
class _Wynik:
    dni: list[dict[str, Any]] = field(default_factory=list)
    problemy: Counter = field(default_factory=Counter)
    uzyto_wbudowanej: bool = False


def _norm_kat(kategoria: str) -> str:
    return kategoria.strip().casefold()


_SLOT_KATEGORIE_NORM = {
    slot: {_norm_kat(k) for k in kategorie}
    for slot, kategorie in SLOT_KATEGORIE.items()
}
_PREMIA_NORM = {_norm_kat(k) for k in PREMIA_OBIADOWA}


def dominujace_makro(s: Skladnik) -> str:
    udzialy = {
        "PROTEIN": s.protein_100g * 4,
        "FAT": s.fat_100g * 9,
        "CARB": s.carbs_100g * 4,
    }
    return max(udzialy, key=lambda k: udzialy[k])


def _czas(kategoria: str) -> int:
    return CZAS_KATEGORII.get(kategoria, 10)


def _maks_gramy(s: Skladnik) -> float:
    if s.default_portion_g and s.default_portion_g > 0:
        return min(MAKS_GRAMY_POZYCJI,
                   s.default_portion_g * MAKS_KROTNOSC_PORCJI)
    return MAKS_GRAMY_POZYCJI


def _zaokraglij_kuchennie(s: Skladnik, gramy: float) -> tuple[float, float | None]:
    """Gramatura odmierzalna w kuchni (feedback z produkcji: „316,4 g"
    nikt nie odważy). Produkt z jednostką → najpierw pół-jednostki
    („2 jajka", „1,5 kromki"), gramy z jednostek; bez jednostki →
    do 5 g poniżej 100 g, do 10 g powyżej. Makra liczone są z gramatury
    PO zaokrągleniu — sumy pozostają uczciwe."""
    gramy = min(gramy, MAKS_GRAMY_POZYCJI)
    if s.unit_grams and s.unit_grams > 0:
        sztuki = max(0.5, round(gramy / s.unit_grams * 2) / 2)
        return round(sztuki * s.unit_grams, 1), sztuki
    if gramy < 100:
        zaokraglone = max(5.0, round(gramy / 5) * 5)
    else:
        zaokraglone = round(gramy / 10) * 10
    zaokraglone = min(zaokraglone, MAKS_GRAMY_POZYCJI)
    return float(zaokraglone), None


def _pozycja(s: Skladnik, gramy: float) -> dict[str, Any]:
    gramy, sztuki = _zaokraglij_kuchennie(s, gramy)
    return {
        "product_id": s.id,
        "name": s.name,
        "category": s.category,
        "source": s.source,
        "grams": gramy,
        "kcal": round(gramy / 100 * s.kcal_100g, 1),
        "protein_g": round(gramy / 100 * s.protein_100g, 1),
        "fat_g": round(gramy / 100 * s.fat_100g, 1),
        "carbs_g": round(gramy / 100 * s.carbs_100g, 1),
        "units": sztuki,
        "unit_name": s.unit_name,
    }


def _sugestia_przyrzadzenia(pozycje: list[dict[str, Any]]) -> str:
    widziane: dict[str, str] = {}
    for p in sorted(pozycje, key=lambda x: -_czas(x["category"])):
        kat = p["category"]
        if kat in widziane or kat not in METODA:
            continue
        widziane[kat] = f"{p['name']} — {METODA[kat]}"
    if not widziane:
        return "Podaj składniki wg uznania."
    return "; ".join(widziane.values()) + "."


def _wybierz(
    grupa: list[Skladnik], obrot: int, cel_g: float, pole: str,
    zajete: set[str] | None = None,
) -> Skladnik:
    """Rotacja z bezpiecznikiem zdrowej porcji. Produkty już obecne
    w posiłku (`zajete`, np. dodatek warzywno-owocowy) przegrywają
    z każdym wolnym kandydatem — „Banan 120 g + Banan 91 g" w jednym
    śniadaniu to nie kompozycja."""
    zajete = zajete or set()
    n = len(grupa)
    najlepszy_zajety: Skladnik | None = None
    for przesuniecie in range(n):
        s = grupa[(obrot + przesuniecie) % n]
        na_100 = getattr(s, pole)
        if na_100 > 0 and cel_g / na_100 * 100 <= _maks_gramy(s):
            if s.id not in zajete:
                return s
            if najlepszy_zajety is None:
                najlepszy_zajety = s
    if najlepszy_zajety is not None:
        return najlepszy_zajety
    return grupa[obrot % n]


def _rozwiaz_gramy(
    produkty: dict[str, Skladnik], cele: dict[str, float]
) -> dict[str, float] | None:
    """Dokładna gramatura trzech produktów na trzy cele makro naraz —
    układ 3×3 (Cramer). None przy układzie osobliwym albo rozwiązaniu
    poza zdrowymi granicami — wtedy fallback sekwencyjny."""
    if set(produkty) != set(_MAKRA):
        return None
    kol = [produkty["CARB"], produkty["FAT"], produkty["PROTEIN"]]
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


def _pasuje_do_slotu(s: Skladnik, nazwa_slotu: str) -> bool:
    return _norm_kat(s.category) in _SLOT_KATEGORIE_NORM.get(nazwa_slotu, set())


def _grupy_makro(pula: list[Skladnik]) -> dict[str, list[Skladnik]]:
    grupy: dict[str, list[Skladnik]] = {m: [] for m in _MAKRA}
    for s in pula:
        grupy[dominujace_makro(s)].append(s)
    return grupy


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
    wbudowane: list[Skladnik] | None = None,
) -> dict[str, Any]:
    """Buduje propozycję `dni` dni po `posilkow_dziennie` posiłków.

    `wbudowane` to opcjonalna wbudowana baza produktów służąca WYŁĄCZNIE
    do dopełniania braków katalogu trenera — każda taka pozycja jest
    oznaczona w wyniku (`source: "builtin"`).
    """
    wykluczone_kategorie_norm = {
        _norm_kat(k) for k in (wykluczone_kategorie or set())
    }
    wykluczone_produkty = wykluczone_produkty or set()
    preferowane_produkty = preferowane_produkty or set()

    def _dopuszczony(s: Skladnik) -> bool:
        return (_norm_kat(s.category) not in wykluczone_kategorie_norm
                and s.id not in wykluczone_produkty
                and s.kcal_100g > 0)

    wynik = _Wynik()
    pula = [s for s in skladniki if _dopuszczony(s)]
    pula_wbudowana = [s for s in (wbudowane or []) if _dopuszczony(s)]
    if not pula and not pula_wbudowana:
        wynik.problemy["Po zastosowaniu wykluczeń pula produktów jest "
                       "pusta — propozycja nie może powstać."] = 1
        return _zloz_wynik(wynik, target_kcal, procent, dni)

    cele_dnia = {
        "PROTEIN": target_kcal * procent["protein"] / 100 / 4,
        "FAT": target_kcal * procent["fat"] / 100 / 9,
        "CARB": target_kcal * procent["carbs"] / 100 / 4,
    }
    sloty = SLOTY[posilkow_dziennie]

    def _kolejnosc(s: Skladnik) -> tuple[int, str]:
        return (0 if s.id in preferowane_produkty else 1, s.id)

    def _kolejnosc_obiadowa(s: Skladnik) -> tuple[int, int, str]:
        # Ryby i strączkowe na przód rotacji białka obiadowego.
        return (0 if s.id in preferowane_produkty else 1,
                0 if _norm_kat(s.category) in _PREMIA_NORM else 1, s.id)

    def _kolejnosc_czasowa(s: Skladnik) -> tuple[int, int, str]:
        return (0 if s.id in preferowane_produkty else 1,
                _czas(s.category), s.id)

    for dzien_nr in range(1, dni + 1):
        posilki: list[dict[str, Any]] = []
        for slot_nr, (nazwa_slotu, waga) in enumerate(sloty):
            obrot = dzien_nr - 1 + slot_nr
            cele_posilku = {m: cele_dnia[m] * waga for m in _MAKRA}
            pozycje: list[dict[str, Any]] = []

            trener_slot = [s for s in pula if _pasuje_do_slotu(s, nazwa_slotu)]
            wbudowana_slot = [
                s for s in pula_wbudowana if _pasuje_do_slotu(s, nazwa_slotu)
            ]

            # Dodatek kompozycyjny (warzywo/owoc) — stała porcja, makra
            # odejmowane od celów slotu. Katalog trenera pierwszy.
            dodatek_kat, dodatek_g = DODATKI_SLOTU.get(nazwa_slotu, ("", 0.0))
            if dodatek_kat:
                kat_norm = _norm_kat(dodatek_kat)
                kandydaci = ([s for s in pula
                              if _norm_kat(s.category) == kat_norm]
                             or [s for s in pula_wbudowana
                                 if _norm_kat(s.category) == kat_norm])
                if kandydaci:
                    kandydaci.sort(key=_kolejnosc)
                    dodatek = kandydaci[obrot % len(kandydaci)]
                    if dodatek.source == "builtin":
                        wynik.uzyto_wbudowanej = True
                    poz = _pozycja(dodatek, dodatek_g)
                    pozycje.append(poz)
                    cele_posilku["PROTEIN"] = max(
                        0.0, cele_posilku["PROTEIN"] - poz["protein_g"])
                    cele_posilku["FAT"] = max(
                        0.0, cele_posilku["FAT"] - poz["fat_g"])
                    cele_posilku["CARB"] = max(
                        0.0, cele_posilku["CARB"] - poz["carbs_g"])

            # Źródła makro: katalog trenera (slot) → wbudowana (slot) →
            # katalog trenera (pełny).
            grupy_trenera = _grupy_makro(trener_slot)
            grupy_wbudowanej = _grupy_makro(wbudowana_slot)
            grupy_pelne = _grupy_makro(pula)
            grupy_wbudowanej_pelne = _grupy_makro(pula_wbudowana)
            obiadowy = nazwa_slotu in ("Obiad", "Obiadokolacja")
            zajete_w_posilku = {p["product_id"] for p in pozycje}

            wybrane: dict[str, Skladnik] = {}
            for makro in _MAKRA:
                if cele_posilku[makro] <= 1.0:
                    continue
                grupa = grupy_trenera[makro]
                if not grupa and grupy_wbudowanej[makro]:
                    grupa = grupy_wbudowanej[makro]
                    wynik.problemy[
                        f"Brak źródła {_NAZWA_MAKRO[makro]} w Twoim "
                        "katalogu — uzupełniono z wbudowanej bazy"
                    ] += 1
                    wynik.uzyto_wbudowanej = True
                elif not grupa and grupy_pelne[makro]:
                    grupa = grupy_pelne[makro]
                    wynik.problemy[
                        "Brak produktów pasujących do pory dnia — "
                        "użyto pełnego katalogu"
                    ] += 1
                elif not grupa and grupy_wbudowanej_pelne[makro]:
                    grupa = grupy_wbudowanej_pelne[makro]
                    wynik.problemy[
                        f"Brak źródła {_NAZWA_MAKRO[makro]} w Twoim "
                        "katalogu — uzupełniono z wbudowanej bazy"
                    ] += 1
                    wynik.uzyto_wbudowanej = True
                if not grupa:
                    wynik.problemy[
                        f"Brak źródła {_NAZWA_MAKRO[makro]} — makro "
                        "pozostaje niedomknięte"
                    ] += 1
                    continue
                if obiadowy and makro == "PROTEIN":
                    grupa = sorted(grupa, key=_kolejnosc_obiadowa)
                elif maks_minut_na_posilek is not None:
                    grupa = sorted(grupa, key=_kolejnosc_czasowa)
                else:
                    grupa = sorted(grupa, key=_kolejnosc)
                wybrane[makro] = _wybierz(
                    grupa, obrot, cele_posilku[makro], _POLE[makro],
                    zajete=zajete_w_posilku,
                )
                zajete_w_posilku.add(wybrane[makro].id)

            for s in wybrane.values():
                if s.source == "builtin":
                    wynik.uzyto_wbudowanej = True

            dokladnie = _rozwiaz_gramy(wybrane, cele_posilku)
            if dokladnie is not None:
                for makro in _MAKRA:
                    pozycje.append(_pozycja(wybrane[makro], dokladnie[makro]))
            else:
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
                wynik.problemy[
                    f"{nazwa_slotu}: szacowany czas przekracza budżet "
                    f"{maks_minut_na_posilek} min mimo doboru najszybszych "
                    "produktów"
                ] += 1
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
    # Ostrzeżenia zbiorcze: jeden wpis per problem, z liczbą wystąpień.
    ostrzezenia = [
        (f"{tresc} ({ile}×)." if ile > 1 else f"{tresc}.")
        for tresc, ile in wynik.problemy.items()
    ]
    zalecenie = None
    if wynik.uzyto_wbudowanej:
        zalecenie = (
            "Część składników pochodzi z wbudowanej bazy (oznaczone) — "
            "możesz dograć ją do swojego katalogu jednym przyciskiem "
            "w zakładce Produkty, żeby edytować wartości i porcje."
        )
    elif any("niedomknięte" in o for o in ostrzezenia):
        zalecenie = (
            "W katalogu brakuje źródeł niektórych makro — uzupełnij "
            "produkty albo dograj wbudowaną bazę w zakładce Produkty."
        )
    return {
        "target": cel,
        "days": wynik.dni,
        "daily_average": srednia,
        "warnings": ostrzezenia,
        "recommendation": zalecenie,
        "disclaimer": (
            "To propozycja wygenerowana regułowo (kompozycja wg wzorca "
            "śródziemnomorskiego/DASH) — przejrzyj, dostosuj i dopiero "
            "wtedy utwórz z niej plan."
        ),
        "nutrition_plan_content": _tresc_planu(wynik.dni, cel),
    }


def _tresc_planu(dni: list[dict[str, Any]], cel: dict[str, float]) -> dict[str, Any]:
    """Kształt zgodny z `content_json` wersji planu żywieniowego."""
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

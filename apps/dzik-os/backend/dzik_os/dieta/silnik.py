"""Silnik skalowania szablonów jadłospisów — port `docs/diet-module/engine.py`
(v0.1 właściciela) do modułu domenowego bez I/O.

Różnice względem referencji są WYŁĄCZNIE techniczne:
* produkty nie są czytane z CSV przy imporcie — każda funkcja dostaje
  słownik `products: {name_pl: Produkt}` (dane z bazy);
* puste pola CSV (pandas: NaN → "nan") są tu pustymi napisami — semantyka
  „brak dopasowania” zachowana;
* `assert` dla DYSKRETNY bez `unit_g` → `ValueError` (ten sam warunek);
* opcjonalna reguła `group` (specyfikacja §6.3 / kryterium akceptacji:
  „składniki w tej samej `group` mają identyczny współczynnik końcowy”),
  której referencja NIE wymusza — włączana parametrem `enforce_groups`
  (domyślnie False = wynik identyczny z referencją i złotym plikiem;
  API przyjmuje `enforce_groups=true` w podglądzie/przypisaniu, interfejs
  trenera nie włącza jej domyślnie — decyzja właściciela, PROGRESS.md);
* walidacja wejścia (posiłek bez składników, zerowa kaloryczność bazowa,
  cel ≤ 0 kcal, niedodatnie kroki zaokrąglania) kończy się `ValueError`
  zamiast wyjątkiem arytmetycznym — referencja nigdy nie była wołana
  poniżej 1400 kcal ani na niekompletnych szablonach.

Kolejność kroków, stałe (tolerancje, klasy, mnożniki, liczby przebiegów)
i arytmetyka są identyczne z referencją — test „golden” porównuje pełny
tydzień Standard v1 przy 2000 kcal z wynikiem prototypu.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

CLASS_DEFAULTS: dict[str, dict[str, Any]] = {
    "LINIOWY": {"min_factor": 0.5, "max_factor": 2.0, "round_step": 5},
    "DYSKRETNY": {"min_factor": 0.5, "max_factor": 2.5, "round_step": None},
    "TŁUMIONY": {"min_factor": 0.7, "max_factor": 1.5, "round_step": 10, "exponent": 0.5},
    "STAŁY": {"min_factor": 1.0, "max_factor": 1.0, "round_step": None},
}
TOL_MEAL = {"kcal_pct": 0.08, "kcal_abs": 40, "P": 5, "F": 4, "C": 10}
TOL_DAY = {"kcal_pct": 0.03, "kcal_abs": 0, "P": 5, "F": 5, "C": 10}

KLASY = tuple(CLASS_DEFAULTS)
ROLE = ("P", "C", "F", "NONE")


@dataclass(frozen=True)
class Produkt:
    """Wiersz bazy produktów w kształcie, którego używa silnik (nazwy pól
    jak w CSV / `pandas.itertuples()` referencji)."""

    name_pl: str
    category: str
    substitution_group: str
    kcal_100: float
    protein_100: float
    fat_100: float
    carbs_100: float
    cooking_tags: str = ""
    allergens: str = ""
    diet_exclusions: str = ""
    default_scaling: str = "LINIOWY"


Products = dict[str, Produkt]


def macros(ing: dict, products: Products) -> dict[str, float]:
    p = products[ing["product"]]
    g = ing["grams"] / 100
    return {"kcal": p.kcal_100 * g, "P": p.protein_100 * g, "F": p.fat_100 * g, "C": p.carbs_100 * g}


def sum_macros(ings: list[dict], products: Products) -> dict[str, float]:
    t = {"kcal": 0.0, "P": 0.0, "F": 0.0, "C": 0.0}
    for i in ings:
        for k, v in macros(i, products).items():
            t[k] += v
    return t


def fill_defaults(ing: dict, products: Products) -> dict:
    if ing["product"] not in products:
        raise ValueError(f"nieznany produkt: {ing['product']!r}")
    cls = ing.get("class") or products[ing["product"]].default_scaling
    if cls not in CLASS_DEFAULTS:
        raise ValueError(f"{ing['product']}: nieznana klasa skalowania {cls!r}")
    d = CLASS_DEFAULTS[cls]
    ing.setdefault("class", cls)
    ing.setdefault("role", "NONE")
    for k, v in d.items():
        if ing.get(k) is None:
            ing[k] = v
    prod = products[ing["product"]]
    # Limity porcji (engine.py v1.1 po audycie 14.09): maks. 300 g surowego mięsa/ryby
    # na posiłek (twardy limit) i maks. 4 jajka na posiłek — silnik woli oflagować
    # posiłek niż zaproponować talerz nie do zjedzenia.
    if (prod.category in ("mięso", "ryby") and prod.substitution_group != "wędlina" and cls == "LINIOWY"
            and float(ing["grams"]) > 0):
        ing["max_factor"] = min(ing["max_factor"], 300 / float(ing["grams"]))
        ing["min_factor"] = min(ing["min_factor"], ing["max_factor"])
    if ing["product"] == "Jajko kurze (całe)" and cls == "DYSKRETNY" and ing.get("unit_g") and float(ing["grams"]) > 0:
        ing["max_factor"] = min(ing["max_factor"], max(1.0, 4 * float(ing["unit_g"]) / float(ing["grams"])))
    # tłuszcze dodawane w małych ilościach (5-15 g) mogą rosnąć do 3x - nadal praktyczne;
    # krok zaokrąglenia 1 g (5 g to ~10 % dziennego tłuszczu na redukcji).
    if prod.category == "tłuszcze" and cls == "LINIOWY":
        ing["max_factor"] = max(ing["max_factor"], 3.0)
        ing["round_step"] = 1
    if cls == "DYSKRETNY":
        if not ing.get("unit_g"):
            raise ValueError(f"{ing['product']}: DYSKRETNY wymaga unit_g")
        if ing.get("unit_step") is None:
            ing["unit_step"] = 1.0
        if not (float(ing["unit_g"]) > 0 and float(ing["unit_step"]) > 0):
            raise ValueError(f"{ing['product']}: unit_g i unit_step muszą być dodatnie")
    elif cls != "STAŁY" and not (ing.get("round_step") or 0) > 0:
        raise ValueError(f"{ing['product']}: round_step musi być dodatni")
    if not (ing.get("min_factor") or 0) > 0 or ing["max_factor"] < ing["min_factor"]:
        raise ValueError(f"{ing['product']}: zakres min_factor–max_factor jest niepoprawny")
    if not float(ing["grams"]) > 0:
        raise ValueError(f"{ing['product']}: gramatura bazowa musi być dodatnia")
    ing["base_grams"] = ing["grams"]
    return ing


def clamp(ing: dict, grams: float) -> float:
    lo, hi = ing["base_grams"] * ing["min_factor"], ing["base_grams"] * ing["max_factor"]
    return max(lo, min(hi, grams))


def scale_initial(ings: list[dict], k: float) -> None:
    """Krok 2: skalowanie wstępne wg klasy."""
    for i in ings:
        c = i["class"]
        if c == "STAŁY":
            continue
        f = k if c != "TŁUMIONY" else k ** i["exponent"]
        i["grams"] = clamp(i, i["base_grams"] * f)


def fit_macros(ings: list[dict], target: dict, products: Products, passes: int = 6) -> bool:
    """Krok 3: korekta makro tylko składnikami z daną rolą, w granicach zakresów."""
    hit_limit = False
    for _ in range(passes):
        cur = sum_macros(ings, products)
        for m, key in (("P", "protein_100"), ("C", "carbs_100"), ("F", "fat_100")):
            deficit = target[m] - cur[m]
            drivers = [i for i in ings if i["role"] == m and i["class"] != "STAŁY"]
            if not drivers or abs(deficit) < 0.5:
                continue
            contrib = [getattr(products[i["product"]], key) / 100 for i in drivers]
            total = sum(c * i["grams"] for c, i in zip(contrib, drivers, strict=True)) or 1e-9
            for c, i in zip(contrib, drivers, strict=True):
                if c == 0:
                    continue
                share = (c * i["grams"]) / total
                want = i["grams"] + deficit * share / c
                new = clamp(i, want)
                if abs(new - want) > 0.5:
                    hit_limit = True
                i["grams"] = new
            cur = sum_macros(ings, products)
    return hit_limit


def fit_kcal(ings: list[dict], target: dict, products: Products, passes: int = 3) -> None:
    """Krok 3b: domknięcie kcal - proporcjonalnie na wszystkich skalowalnych składnikach z rolą."""
    for _ in range(passes):
        cur = sum_macros(ings, products)
        gap = target["kcal"] - cur["kcal"]
        if abs(gap) < 5:
            return
        drivers = [i for i in ings if i["class"] in ("LINIOWY", "DYSKRETNY") and i["role"] != "NONE"]
        kc = sum(macros(i, products)["kcal"] for i in drivers) or 1e-9
        f = 1 + gap / kc
        for i in drivers:
            i["grams"] = clamp(i, i["grams"] * f)


def round_practical(ings: list[dict]) -> None:
    """Krok 4: zaokrąglenie do praktycznych ilości."""
    for i in ings:
        c = i["class"]
        if c == "STAŁY":
            continue
        if c == "DYSKRETNY":
            units = i["grams"] / i["unit_g"]
            units = max(i["unit_step"], round(units / i["unit_step"]) * i["unit_step"])
            i["units"] = units
            i["grams"] = units * i["unit_g"]
        else:
            step = i["round_step"]
            i["grams"] = max(step, round(i["grams"] / step) * step)


def check(cur: dict, target: dict, tol: dict) -> tuple[bool, dict]:
    dev = {"kcal": cur["kcal"] - target["kcal"], "P": cur["P"] - target["P"],
               "F": cur["F"] - target["F"], "C": cur["C"] - target["C"]}
    ok = (abs(dev["kcal"]) <= max(tol["kcal_pct"] * target["kcal"], tol["kcal_abs"]) and abs(dev["P"]) <= tol["P"]
          and abs(dev["F"]) <= tol["F"] and abs(dev["C"]) <= tol["C"])
    return ok, dev


# --- reguła group (rozszerzenie względem referencji, opcjonalne) ----------------------------


def _grupy(ings: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for i in ings:
        g = i.get("group")
        if g and i["class"] != "STAŁY":
            out.setdefault(g, []).append(i)
    return {g: m for g, m in out.items() if len(m) > 1}


def enforce_groups(ings: list[dict], products: Products) -> None:
    """Składniki w tej samej `group` dostają IDENTYCZNY współczynnik końcowy
    (ciasto, marynata, sos). Współczynnik = średnia ważona kcal bazowymi
    współczynników członków, przycięta do przecięcia zakresów grupy; jeśli
    w grupie jest składnik DYSKRETNY, współczynnik wynika z jego liczby
    jednostek (zaokrąglonej do `unit_step` w zakresie grupy). Członkowie
    LINIOWY/TŁUMIONY nie są potem zaokrąglani do `round_step` (inaczej
    współczynniki by się rozjechały) — gramatura wynika wprost z bazy."""
    for members in _grupy(ings).values():
        lo = max(m["min_factor"] for m in members)
        hi = min(m["max_factor"] for m in members)
        if lo > hi:
            lo = hi = (lo + hi) / 2
        wagi = [macros(dict(m, grams=m["base_grams"]), products)["kcal"] or 1e-9 for m in members]
        f = sum(w * (m["grams"] / m["base_grams"]) for w, m in zip(wagi, members, strict=True)) / sum(wagi)
        f = max(lo, min(hi, f))
        dyskretne = [m for m in members if m["class"] == "DYSKRETNY"]
        if dyskretne:
            d = dyskretne[0]
            base_units = d["base_grams"] / d["unit_g"]
            step = d["unit_step"]
            units = max(step, round(base_units * f / step) * step)
            # jednostki muszą mieścić się w zakresie grupy — dosuwamy krokiem
            while units / base_units > hi + 1e-9 and units - step >= step:
                units -= step
            while units / base_units < lo - 1e-9:
                units += step
            # Gdy krok jednostki nie mieści się między lo a hi, twarda jest górna
            # granica (max_factor to limit praktyczny porcji) — schodzimy z powrotem.
            while units / base_units > hi + 1e-9 and units - step >= step:
                units -= step
            f = units / base_units
        for m in members:
            m["grams"] = m["base_grams"] * f
            m["_group_factor"] = f
            if m["class"] == "DYSKRETNY":
                m["units"] = m["grams"] / m["unit_g"]


def alergeny(ings: list[dict], products: Products, domyslne: list[str] | None = None) -> list[str]:
    """Alergeny posiłku policzone z BIEŻĄCYCH składników (po wymianie kurczaka na
    krewetki pojawiają się skorupiaki). Gdy baza nie oznacza żadnego produktu —
    lista z szablonu."""
    zbior: set[str] = set()
    for i in ings:
        prod = products.get(i["product"])
        if prod is not None:
            zbior.update(a.strip() for a in str(prod.allergens or "").split(",") if a.strip())
    return sorted(zbior) if zbior else list(domyslne or [])


def scale_meal(meal: dict, target: dict, products: Products, *, enforce_groups_: bool = False) -> dict:
    ings = [fill_defaults(copy.deepcopy(i), products) for i in meal["ingredients"]]
    if not ings:
        raise ValueError(f"{meal.get('name') or meal.get('slot')}: posiłek bez składników")
    base = sum_macros(ings, products)
    if base["kcal"] <= 0:
        raise ValueError(f"{meal.get('name') or meal.get('slot')}: bazowa kaloryczność posiłku wynosi 0")
    if target["kcal"] <= 0:
        raise ValueError(f"{meal.get('name') or meal.get('slot')}: cel posiłku {target['kcal']:.0f} kcal "
                         "jest niedodatni — kaloryczność za niska dla tego szablonu")
    k = target["kcal"] / base["kcal"]
    scale_initial(ings, k)
    limit = fit_macros(ings, target, products)
    fit_kcal(ings, target, products)
    if enforce_groups_:
        enforce_groups(ings, products)
        grupowe = [i for i in ings if "_group_factor" in i]
        round_practical([i for i in ings if "_group_factor" not in i])
        for i in grupowe:
            if i["class"] == "DYSKRETNY":
                i["units"] = i["grams"] / i["unit_g"]
    else:
        round_practical(ings)
    cur = sum_macros(ings, products)
    ok, dev = check(cur, target, TOL_MEAL)
    status = "OK" if ok else ("POZA_ZAKRESEM" if limit else "OSTRZEŻENIE")
    return {"name": meal["name"], "slot": meal["slot"], "ingredients": ings, "macros": cur,
                "target": target, "deviation": dev, "status": status, "k": k, "steps": meal.get("steps", ""),
                "tags": list(meal.get("tags", []) or []), "flexible": bool(meal.get("flexible")),
                "kcal_share": meal["kcal_share"], "meal_id": meal.get("meal_id"),
                "allergens": alergeny(ings, products, meal.get("allergens"))}


def scale_day(day: dict, day_target: dict, products: Products, *, enforce_groups_: bool = False) -> dict:
    """Krok 1: kcal posiłku wg udziału; makro posiłku wg jego własnego profilu bazowego,
    przeskalowane o stosunek (cel dnia / suma bazowa dnia) - zachowuje charakter przepisu."""
    if not day["meals"]:
        raise ValueError(f"dzień {day.get('day')}: brak posiłków")
    bases = [sum_macros([fill_defaults(copy.deepcopy(i), products) for i in m["ingredients"]], products)
             for m in day["meals"]]
    base_day = {m: sum(b[m] for b in bases) for m in ("kcal", "P", "F", "C")}
    zerowe = [m for m in ("kcal", "P", "F", "C") if base_day[m] <= 0]
    if zerowe:
        raise ValueError(f"dzień {day.get('day')}: bazowa suma {', '.join(zerowe)} wynosi 0")
    if any(b["kcal"] <= 0 for b in bases):
        raise ValueError(f"dzień {day.get('day')}: posiłek o zerowej kaloryczności bazowej")
    if day_target["kcal"] <= 0:
        raise ValueError(f"dzień {day.get('day')}: cel {day_target['kcal']:.0f} kcal jest niedodatni")
    ratio = {m: day_target[m] / base_day[m] for m in ("P", "F", "C")}
    out = []
    for meal, b in zip(day["meals"], bases, strict=True):
        kcal_t = day_target["kcal"] * meal["kcal_share"]
        kf = kcal_t / (b["kcal"] * day_target["kcal"] / base_day["kcal"])  # korekta gdy udział != baza
        t = dict(kcal=kcal_t, **{m: b[m] * ratio[m] * kf for m in ("P", "F", "C")})
        # renormalizuj, by 4P+9F+4C = kcal_t
        e = 4 * t["P"] + 9 * t["F"] + 4 * t["C"]
        for m in ("P", "F", "C"):
            t[m] *= kcal_t / e
        out.append(scale_meal(meal, t, products, enforce_groups_=enforce_groups_))
    # przebieg 2: resztę dnia rozłóż proporcjonalnie do udziałów i przelicz ponownie
    cur = {m: sum(r["macros"][m] for r in out) for m in ("kcal", "P", "F", "C")}
    resid = {m: day_target[m] - cur[m] for m in ("kcal", "P", "F", "C")}
    out2 = []
    for meal, r in zip(day["meals"], out, strict=True):
        t = {m: r["target"][m] + resid[m] * meal["kcal_share"] for m in resid}
        out2.append(scale_meal(meal, t, products, enforce_groups_=enforce_groups_))
    out = out2
    cur = {m: sum(r["macros"][m] for r in out) for m in ("kcal", "P", "F", "C")}
    flex = [i for i, m in enumerate(day["meals"]) if m.get("flexible")]
    if flex:
        idx = flex[0]
        resid = {m: day_target[m] - cur[m] for m in ("kcal", "P", "F", "C")}
        newt = {m: out[idx]["target"][m] + resid[m] for m in resid}
        out[idx] = scale_meal(day["meals"][idx], newt, products, enforce_groups_=enforce_groups_)
        cur = {m: sum(r["macros"][m] for r in out) for m in ("kcal", "P", "F", "C")}
    # krok 5c: dostrojenie dnia - pojedyncze kroki zaokrąglenia na składnikach LINIOWY z rolą
    for _ in range(12):
        ok, dev = check(cur, day_target, TOL_DAY)
        if ok:
            break
        m = (max(("P", "F", "C"), key=lambda x: abs(dev[x]) / TOL_DAY[x])
             if any(abs(dev[x]) > TOL_DAY[x] for x in ("P", "F", "C")) else None)
        if m is None:  # tylko kcal poza - użyj C
            m = "C" if abs(dev["C"]) >= abs(dev["P"]) else "P"
        moved = False
        for r in sorted(out, key=lambda r: -r["target"]["kcal"]):
            for i in r["ingredients"]:
                if i["class"] == "LINIOWY" and i["role"] == m and "_group_factor" not in i:
                    step = i["round_step"] * (-1 if dev[m] > 0 else 1)
                    new = i["grams"] + step
                    if clamp(i, new) == new and new > 0:
                        i["grams"] = new
                        moved = True
                        break
            if moved:
                break
        if not moved:
            break
        for r in out:
            r["macros"] = sum_macros(r["ingredients"], products)
        cur = {mm: sum(r["macros"][mm] for r in out) for mm in ("kcal", "P", "F", "C")}
    ok, dev = check(cur, day_target, TOL_DAY)
    return {"day": day["day"], "meals": out, "macros": cur, "target": day_target, "deviation": dev,
                "status": "OK" if ok else "POZA_TOLERANCJĄ"}


def day_target(kcal: float, pct: tuple[float, float, float] | list[float]) -> dict:
    """pct = (P%, F%, C%) kcal -> gramy (4/9/4)."""
    p, f, c = pct
    return {"kcal": kcal, "P": kcal * p / 4, "F": kcal * f / 9, "C": kcal * c / 4}


def scale_week(template: dict, kcal: float, products: Products, pct=None, *,
               target: dict | None = None, enforce_groups_: bool = False) -> list[dict]:
    """`target` (gramy B/T/W) ma pierwszeństwo nad `pct` — presety trenera
    „na kg” i „ręcznie” podają gramy wprost."""
    t = target or day_target(kcal, pct or template["macro_pct"])
    return [scale_day(d, t, products, enforce_groups_=enforce_groups_) for d in template["days"]]


POWODY_PUSTEJ_LISTY = ("SINGLETON", "EXCLUDED", "FUNCTION", "PORTION", "TOLERANCE")
# Etap, na którym odpadł kandydat — powód pustej listy to NAJDALSZY etap, do którego doszedł
# którykolwiek kandydat („kandydaci istnieją, ale każdy pogarsza posiłek” → TOLERANCE).
_ETAP = {"EXCLUDED": 1, "FUNCTION": 2, "PORTION": 3, "TOLERANCE": 4}
ROLA_KEY = {"P": "protein_100", "C": "carbs_100", "F": "fat_100"}
MIN_BIALKO_100 = 15.0  # rola P na poziomie 2: nabiał chudy ma dużo wody — 15 g/100 g wystarczy


def _tagi(p: Produkt) -> set[str]:
    return {t.strip() for t in str(p.cooking_tags).split(",") if t.strip()}


def _makro_dominujace(q: Produkt) -> str:
    kcal = {"P": q.protein_100 * 4, "F": q.fat_100 * 9, "C": q.carbs_100 * 4}
    return max(kcal, key=lambda k: (kcal[k], k))


def rola_zgodna(q: Produkt, role: str) -> bool:
    """Poziom 2: kandydat musi mieć dominujące makro zgodne z rolą składnika
    (dla P wystarczy `protein_100 ≥ 15 g`)."""
    if role == "P" and q.protein_100 >= MIN_BIALKO_100:
        return True
    return _makro_dominujace(q) == role


def _odchylenia(cur: dict, target: dict) -> dict[str, float]:
    return {k: abs(cur[k] - target[k]) for k in ("kcal", "P", "F", "C")}


# Luz bramki „nie pogarsza” poniżej rozdzielczości, jaką widzi klient (makro migawki
# zaokrąglone do 0,1 g, gramatura do kroku 5 g): pogorszenie osi o setne grama przez
# zaokrąglenie gramatury kandydata nie jest pogorszeniem posiłku (przegląd 14.09: masło
# 6 g → oliwa 5 g odpadało za +0,05 g białka). Interpretacja spec §4 pkt 5 („wymiana
# neutralna lub poprawiająca jest dozwolona”) — do potwierdzenia przez właściciela.
EPS_NIE_POGARSZA = {"kcal": 5.0, "P": 0.5, "F": 0.5, "C": 0.5}
JAJKO = "Jajko kurze (całe)"
JAJKO_UNIT_G = 55.0  # jednostka jajka w szablonach (2 szt. ≈ 110 g)


def nie_pogarsza(cur: dict, target: dict, dev_przed: dict) -> bool:
    """Bramka „nie pogarsza”: posiłek po wymianie mieści się w TOL_MEAL ALBO żadne
    odchylenie (kcal, P, F, C) co do modułu nie jest większe niż przed wymianą
    (z luzem `EPS_NIE_POGARSZA` poniżej rozdzielczości wyświetlania)."""
    if check(cur, target, TOL_MEAL)[0]:
        return True
    dev = _odchylenia(cur, target)
    return all(dev[k] <= dev_przed[k] + EPS_NIE_POGARSZA[k] for k in dev)


def limit_porcji(q: Produkt, g: float) -> bool:
    """Limity porcji v1.1 po kategorii KANDYDATA — ta sama reguła przy doborze
    kandydatów i przy gramaturze z klienta w POST: ≤ 300 g surowego mięsa/ryby
    (wędlina bez limitu), ≤ 4 jajka (jednostka 55 g)."""
    if q.category in ("mięso", "ryby") and q.substitution_group != "wędlina" and g > 300:
        return False
    return not (q.name_pl == JAJKO and g > 4 * JAJKO_UNIT_G)


def swap_candidates_z_powodami(meal_result: dict, ing_index: int, products: Products, exclusions=(), n: int = 3,
                               related: dict[str, dict[str, str]] | None = None) -> tuple[list[dict], dict]:
    """Wymiana produktu v2 (0.69.0) — TU silnik przestaje być 1:1 z prototypem
    `docs/diet-module/engine.py` (skalowanie, `check`, `fit_*` bez zmian).

    Poziom 1 = ta sama `substitution_group`; poziom 2 = grupa pokrewna (`related`,
    z `dane/grupy_pokrewne.json`). Kolejność sit (każde odrzucenie liczone z powodem):
    wykluczenia (alergeny/diety/„nie lubię” — PRZED poziomem 2, żeby poziom 2 nie
    przemycił alergenu) → funkcja w posiłku (metoda: `cooking_tags` z `*`/pustym jako
    wildcard; na poziomie 2 wildcard kandydata nie wystarcza; rola makro: `per > 0`,
    na poziomie 2 dominujące makro zgodne z rolą) → gramatura w zakresie składnika
    (`min_factor..max_factor`, zaokrąglona `round_step`) → bramka posiłku „w tolerancji
    ALBO nie pogarsza”. Rola NONE: tylko poziom 1, gramatura 1:1 wagowo.
    Ranking: poziom → suma |Δ| posiłku po wymianie → odległość makro produktu.
    Zwraca (kandydaci, {"reason", "rejected"}); wynik deterministyczny."""
    ing = meal_result["ingredients"][ing_index]
    p = products[ing["product"]]
    ctags = _tagi(p)
    orig = macros(ing, products)
    role = ing["role"] if ing["role"] in ("P", "C", "F") else "NONE"
    grupa = p.substitution_group
    pokrewne = (related or {}).get(grupa, {}) if grupa else {}
    ings0 = [dict(x) for x in meal_result["ingredients"]]
    cur0 = sum_macros(ings0, products)
    dev0 = _odchylenia(cur0, meal_result["target"])
    odrzucone: dict[str, int] = {}
    najdalej = 0
    step = ing.get("round_step") or 5
    # Wykluczenia bez wrażliwości na wielkość liter („Mleko” z pola „nielubiane” = „mleko”).
    wykluczenia = tuple(str(x).casefold() for x in exclusions)
    cands = []
    rozwazani = 0
    for q in products.values():
        if q.name_pl == p.name_pl or not q.substitution_group:
            continue
        if q.substitution_group == grupa:
            tier = 1
        elif q.substitution_group in pokrewne:
            tier = 2
        else:
            continue
        if role == "NONE" and tier == 2:
            continue  # NONE: funkcja = objętość/smak, tylko ta sama grupa
        rozwazani += 1

        def odrzuc(powod: str) -> None:
            nonlocal najdalej
            odrzucone[powod] = odrzucone.get(powod, 0) + 1
            najdalej = max(najdalej, _ETAP[powod])

        if any(x in str(q.diet_exclusions).casefold() or x in str(q.allergens).casefold() or x == q.name_pl.casefold()
               for x in wykluczenia):
            odrzuc("EXCLUDED")
            continue
        qtags = _tagi(q)
        if tier == 1:
            ok_tagi = "*" in qtags or not qtags or "*" in ctags or not ctags or bool(ctags & qtags)
        else:
            ok_tagi = "*" in ctags or not ctags or bool(ctags & qtags)
        if not ok_tagi:
            odrzuc("FUNCTION")
            continue
        if role == "NONE":
            g = float(ing["grams"])
        else:
            per = getattr(q, ROLA_KEY[role]) / 100
            if per <= 0 or (tier == 2 and not rola_zgodna(q, role)):
                odrzuc("FUNCTION")
                continue
            g = orig[role] / per
        g = max(step, round(g / step) * step)
        # Limity porcji v1.1 (twarde, po kategorii KANDYDATA): ≤ 300 g surowego mięsa/ryby,
        # ≤ 4 jajka. Zakres min/max_factor składnika NIE jest przenoszony na kandydata —
        # gęstość produktów różni się kilkukrotnie (50 g awokado ↔ 8 g oliwy to poprawna
        # wymiana tłuszczu), pomiar z 14.09: zakres factor dawał 6/108 pustych list zamiast 3
        # przy 2000 kcal i 51/124 zamiast 3 dla roli NONE (docs/diet-module/PROGRESS.md).
        if not limit_porcji(q, g):
            odrzuc("PORTION")
            continue
        ings = [dict(x) for x in meal_result["ingredients"]]
        ings[ing_index] = dict(ing, product=q.name_pl, grams=g)
        cur = sum_macros(ings, products)
        if not nie_pogarsza(cur, meal_result["target"], dev0):
            odrzuc("TOLERANCE")
            continue
        dev = _odchylenia(cur, meal_result["target"])
        dist = sum(abs(getattr(q, k) - getattr(p, k)) for k in ("protein_100", "fat_100", "carbs_100"))
        delta = {k: round(cur[k] - cur0[k], 1) for k in ("kcal", "P", "F", "C")}
        cands.append((tier, round(sum(dev.values()), 6), round(dist, 6), q.name_pl, g, cur, delta,
                      pokrewne.get(q.substitution_group) if tier == 2 else None, q.substitution_group))
    cands.sort()
    out = [{"product": c[3], "grams": c[4], "macros": c[5], "tier": c[0], "meal_delta": c[6],
            "group": c[8], "tier_reason": c[7]} for c in cands[:n]]
    reason = None
    if not out:
        if rozwazani == 0:
            reason = "SINGLETON"
        else:
            reason = next((k for k, v in _ETAP.items() if v == najdalej), None)
    return out, {"reason": reason, "rejected": odrzucone, "considered": rozwazani}


def swap_candidates(meal_result: dict, ing_index: int, products: Products, exclusions=(), n: int = 3,
                    related: dict[str, dict[str, str]] | None = None) -> list[dict]:
    """Lista kandydatów (bez statystyki) — ta sama ścieżka co `swap_candidates_z_powodami`."""
    return swap_candidates_z_powodami(meal_result, ing_index, products, exclusions, n, related)[0]

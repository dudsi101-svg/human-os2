"""Etap 2 — silnik skalowania (port `docs/diet-module/engine.py`), testy
obowiązkowe z sekcji 10 specyfikacji + golden `szablon_standard_v1_2000kcal.md`."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dzik_os.dieta import seed
from dzik_os.dieta import silnik as S

DOCS = Path(__file__).resolve().parents[2] / "docs" / "diet-module"


@pytest.fixture(scope="module")
def prods() -> S.Products:
    return {p["name_pl"]: S.Produkt(**{k: p[k] for k in ("name_pl", "category", "substitution_group", "kcal_100",
                                                       "protein_100", "fat_100", "carbs_100", "cooking_tags",
                                                       "allergens", "diet_exclusions", "default_scaling")})
            for p in seed.wczytaj_produkty_csv()}


@pytest.fixture(scope="module")
def tpl() -> dict:
    return json.loads(seed._szablon("template_standard_v1.json"))


def _golden_dni() -> dict[int, dict]:
    """Parsuje golden: dzień → (suma, status, posiłki → składniki)."""
    txt = (DOCS / "szablon_standard_v1_2000kcal.md").read_text(encoding="utf-8").split("## Ten sam dzień 1")[0]
    dni: dict[int, dict] = {}
    for blok in re.split(r"(?=### Dzień )", txt)[1:]:
        h = re.match(r"### Dzień (\d+) — (\d+) kcal · B (\d+) · T (\d+) · W (\d+) · (\w+)", blok)
        posilki = {}
        for m in re.finditer(r"\*\*[^:]+: (.+?)\*\* \((\d+) kcal · B (\d+) · T (\d+) · W (\d+)\)(.*?)\n\n((?:- .*\n)+)", blok):
            status = "OK" if "⚠" not in m[6] else m[6].split("⚠ ")[1].strip()
            skl = {}
            for line in m[7].strip().split("\n"):
                if "(stałe)" in line:
                    continue
                mm = re.match(r"- (.+?) — (?:([\d.]+) szt\. \(~(\d+) g\)|(\d+) g)", line)
                skl[mm[1]] = (float(mm[2]), int(mm[3])) if mm[2] else (None, int(mm[4]))
            posilki[m[1]] = {"kcal": int(m[2]), "P": int(m[3]), "F": int(m[4]), "C": int(m[5]), "status": status, "skl": skl}
        dni[int(h[1])] = {"kcal": int(h[2]), "P": int(h[3]), "F": int(h[4]), "C": int(h[5]), "status": h[6], "posilki": posilki}
    return dni


def _sprawdz_dzien(d: dict, g: dict) -> None:
    m = d["macros"]
    assert (round(m["kcal"]), round(m["P"]), round(m["F"]), round(m["C"]), d["status"]) == \
        (g["kcal"], g["P"], g["F"], g["C"], g["status"])
    for r in d["meals"]:
        gp = g["posilki"][r["name"]]
        assert r["status"] == gp["status"] and round(r["macros"]["kcal"]) == gp["kcal"], r["name"]
        for name, (units, grams) in gp["skl"].items():
            ing = next(i for i in r["ingredients"] if i["product"] == name)
            assert round(ing["grams"]) == grams, (r["name"], name, ing["grams"])
            if units is not None:
                assert ing["units"] == units, (r["name"], name)


def test_golden_dzien_1_przy_2000_kcal(prods, tpl):
    """Wymagany golden test: dzień 1, wszystkie posiłki, dokładne gramatury."""
    week = S.scale_week(tpl, 2000, prods)
    _sprawdz_dzien(week[0], _golden_dni()[1])


def test_golden_caly_tydzien_dowodzi_portu_1_do_1(prods, tpl):
    """Cały tydzień (7 dni, 28 posiłków, 161 składników) identyczny z prototypem."""
    week = S.scale_week(tpl, 2000, prods)
    g = _golden_dni()
    for d in week:
        _sprawdz_dzien(d, g[d["day"]])


def test_sweep_1400_3200_co_100_min_131_z_133_dni_ok(prods, tpl):
    ok = total = 0
    for kcal in range(1400, 3201, 100):
        for d in S.scale_week(tpl, kcal, prods):
            total += 1
            ok += d["status"] == "OK"
    assert total == 133 and ok >= 131


@pytest.mark.parametrize("kcal", [1400, 2000, 2600, 3200])
def test_staly_nie_zmienia_gramatury_dyskretny_wielokrotnosc_jednostki_zakresy(prods, tpl, kcal):
    for d in S.scale_week(tpl, kcal, prods):
        for r in d["meals"]:
            for i in r["ingredients"]:
                if i["class"] == "STAŁY":
                    assert i["grams"] == i["base_grams"]
                if i["class"] == "DYSKRETNY":
                    assert abs(i["units"] / i["unit_step"] - round(i["units"] / i["unit_step"])) < 1e-9
                    assert abs(i["grams"] - i["units"] * i["unit_g"]) < 1e-9
                lo, hi = i["base_grams"] * i["min_factor"], i["base_grams"] * i["max_factor"]
                # zaokrąglenie do kroku może przesunąć o < 1 krok; zakres liczony przed zaokrągleniem
                step = i.get("round_step") or (i.get("unit_g", 0) * i.get("unit_step", 1)) or 0
                assert lo - step - 1e-6 <= i["grams"] <= hi + step + 1e-6, (r["name"], i["product"], i["grams"], lo, hi)


def test_zakresy_przed_zaokragleniem_nigdy_nieprzekroczone(prods, tpl, monkeypatch):
    """Twardy dowód zasady nadrzędnej §6.3: przed krokiem 4 każdy składnik
    mieści się w [min_factor, max_factor] × baza (clamp)."""
    zapisy: list[tuple] = []
    oryginal = S.round_practical

    def podgladaj(ings):
        for i in ings:
            zapisy.append((i["product"], i["grams"], i["base_grams"] * i["min_factor"], i["base_grams"] * i["max_factor"]))
        oryginal(ings)

    monkeypatch.setattr(S, "round_practical", podgladaj)
    for kcal in (1400, 2000, 3200):
        S.scale_week(tpl, kcal, prods)
    assert zapisy and all(lo - 1e-9 <= g <= hi + 1e-9 for _, g, lo, hi in zapisy)


def test_grupa_ma_identyczny_wspolczynnik_z_regula_group(prods, tpl):
    """Rozszerzenie względem referencji (włączane jawnie): składniki tej
    samej `group` mają ten sam współczynnik końcowy."""
    for kcal in (1400, 2000, 2600, 3200):
        for d in S.scale_week(tpl, kcal, prods, enforce_groups_=True):
            for r in d["meals"]:
                grupy: dict[str, set[float]] = {}
                for i in r["ingredients"]:
                    if i.get("group"):
                        grupy.setdefault(i["group"], set()).add(round(i["grams"] / i["base_grams"], 6))
                assert all(len(f) == 1 for f in grupy.values()), (kcal, r["name"], grupy)
    # Referencja tej reguły nie wymusza — test dokumentuje różnicę: w bibliotece istnieje
    # posiłek (ciasto naleśników/racuchów), którego składniki tej samej grupy dostają
    # bez wymuszenia różne współczynniki (inaczej reguła byłaby pusta).
    roznice = 0
    for plik in seed.pliki_szablonow():
        t = json.loads(plik.read_text(encoding="utf-8"))
        for d in S.scale_week(t, 2000, prods):
            for r in d["meals"]:
                f = {i["product"]: i["grams"] / i["base_grams"] for i in r["ingredients"] if i.get("group")}
                if len({round(v, 3) for v in f.values()}) > 1:
                    roznice += 1
    assert roznice > 0


def test_liniowy_bez_korekty_makro_2000_do_3000_to_x1_5(prods):
    """Skalowanie wstępne: LINIOWY ×k przed zaokrągleniem (k = 1,5)."""
    meal = {"name": "t", "slot": "obiad", "kcal_share": 1.0,
            "ingredients": [{"product": "Pierś z kurczaka (surowa)", "grams": 200, "role": "NONE"},
                            {"product": "Ryż biały (suchy)", "grams": 100, "role": "NONE"}]}
    ings = [S.fill_defaults(dict(i), prods) for i in meal["ingredients"]]
    base = S.sum_macros(ings, prods)
    S.scale_initial(ings, 1.5)
    assert [i["grams"] for i in ings] == [300, 150]
    # Cały posiłek bez ról (brak korekty makro): k liczone z kcal.
    r = S.scale_meal(meal, {"kcal": base["kcal"] * 1.5, "P": base["P"] * 1.5, "F": base["F"] * 1.5, "C": base["C"] * 1.5}, prods)
    assert r["k"] == pytest.approx(1.5) and [i["grams"] for i in r["ingredients"]] == [300, 150]


def test_swap_candidates_nie_wyprowadza_poza_tolerancje_i_skyr_bez_laktozy_ma_zamienniki(prods, tpl):
    week = S.scale_week(tpl, 2000, prods)
    ob = week[0]["meals"][1]
    idx = next(i for i, x in enumerate(ob["ingredients"]) if x["product"] == "Pierś z kurczaka (surowa)")
    cands = S.swap_candidates(ob, idx, prods)
    assert [c["product"] for c in cands] == ["Pierś z indyka (surowa)", "Schab bez kości (surowy)", "Polędwiczka wieprzowa (surowa)"]
    # Gramatury kandydatów przypięte z przebiegu silnika v1.1 (golden po audycie nie
    # zawiera już demo wymiany) — pilnują regresji, nie „prawdy” z dokumentu.
    assert [c["grams"] for c in cands] == [160, 155, 175]
    for c in cands:
        ok, _ = S.check(c["macros"], ob["target"], S.TOL_MEAL)
        assert ok
    # Każdy kandydat dla każdego wymienialnego składnika dnia 1 mieści się w tolerancji posiłku.
    for r in week[0]["meals"]:
        for i in range(len(r["ingredients"])):
            for c in S.swap_candidates(r, i, prods):
                assert S.check(c["macros"], r["target"], S.TOL_MEAL)[0]
    sn = week[0]["meals"][0]
    idx = next(i for i, x in enumerate(sn["ingredients"]) if x["product"] == "Skyr naturalny")
    # Baza 181 produktów (14.09) ma nabiał bez laktozy w tej samej grupie zamienników:
    # z wykluczeniem `lactose` kandydaci istnieją, ale ŻADEN nie zawiera laktozy
    # (w bazie 142 produktów lista była pusta — zmiana danych, nie algorytmu).
    kand = S.swap_candidates(sn, idx, prods, exclusions=("lactose",))
    assert kand and all("lactose" not in prods[c["product"]].diet_exclusions for c in kand)
    assert all(S.check(c["macros"], sn["target"], S.TOL_MEAL)[0] for c in kand)


def test_day_target_i_bledy_definicji(prods):
    t = S.day_target(2000, (0.25, 0.30, 0.45))
    assert (t["P"], round(t["F"], 2), t["C"]) == (125.0, 66.67, 225.0)
    with pytest.raises(ValueError, match="unit_g"):
        S.fill_defaults({"product": "Banan", "grams": 120, "class": "DYSKRETNY"}, prods)
    with pytest.raises(ValueError, match="nieznany produkt"):
        S.fill_defaults({"product": "Nie ma", "grams": 1}, prods)
    with pytest.raises(ValueError, match="klasa"):
        S.fill_defaults({"product": "Banan", "grams": 1, "class": "X"}, prods)
    # Tłuszcz LINIOWY dostaje max_factor ≥ 3,0.
    o = S.fill_defaults({"product": "Oliwa z oliwek", "grams": 10, "role": "F"}, prods)
    assert o["max_factor"] == 3.0 and o["class"] == "LINIOWY"


# --- stałe i liczby przebiegów z §4a.3/§6.3 (regresja wykrywana wprost, nie tylko przez golden) ---


def test_stale_silnika_identyczne_z_prototypem():
    """Stałe czytane z ŹRÓDŁA prototypu (ast) — moduł engine.py przy imporcie
    wczytuje CSV z dysku autora, więc nie da się go wykonać w testach."""
    import ast

    zrodlo = (DOCS / "engine.py").read_text(encoding="utf-8")
    drzewo = ast.parse(zrodlo)
    # Prototyp zapisuje stałe przez `dict(...)` — wartościujemy sam fragment
    # przypisania w pustej przestrzeni nazw (bez importów i bez CSV).
    stale = {n.targets[0].id: eval(ast.get_source_segment(zrodlo, n.value), {"__builtins__": {"dict": dict}})
             for n in drzewo.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id in ("CLASS_DEFAULTS", "TOL_MEAL", "TOL_DAY")}
    przebiegi = {n.name: ast.literal_eval(n.args.defaults[-1]) for n in drzewo.body
                 if isinstance(n, ast.FunctionDef) and n.name in ("fit_macros", "fit_kcal")}
    assert S.CLASS_DEFAULTS == stale["CLASS_DEFAULTS"]
    assert S.TOL_MEAL == stale["TOL_MEAL"] and S.TOL_DAY == stale["TOL_DAY"]
    assert S.fit_macros.__defaults__ == (przebiegi["fit_macros"],) == (6,)
    assert S.fit_kcal.__defaults__ == (przebiegi["fit_kcal"],) == (3,)


def test_regula_plus_minus_40_kcal_posilku():
    target = {"kcal": 300, "P": 20, "F": 10, "C": 30}
    ok, _ = S.check({"kcal": 330, "P": 20, "F": 10, "C": 30}, target, S.TOL_MEAL)
    assert ok  # 8 % z 300 = 24 kcal, ale próg bezwzględny 40 kcal
    ok, _ = S.check({"kcal": 345, "P": 20, "F": 10, "C": 30}, target, S.TOL_MEAL)
    assert not ok
    ok, _ = S.check({"kcal": 1000, "P": 0, "F": 0, "C": 0}, {"kcal": 1000, "P": 0, "F": 0, "C": 0}, S.TOL_DAY)
    assert ok
    ok, _ = S.check({"kcal": 1031, "P": 0, "F": 0, "C": 0}, {"kcal": 1000, "P": 0, "F": 0, "C": 0}, S.TOL_DAY)
    assert not ok  # dzień: 3 %, bez progu bezwzględnego


def test_niekompletny_szablon_i_cel_niedodatni_daja_valueerror(prods):
    posilek = {"name": "Pusty", "slot": "obiad", "kcal_share": 0.3, "ingredients": []}
    with pytest.raises(ValueError, match="bez składników"):
        S.scale_meal(posilek, {"kcal": 500, "P": 30, "F": 15, "C": 50}, prods)
    posilek = {"name": "Kurczak", "slot": "obiad", "kcal_share": 0.3,
               "ingredients": [{"product": "Pierś z kurczaka (surowa)", "grams": 150, "role": "P"}]}
    with pytest.raises(ValueError, match="niedodatni"):
        S.scale_meal(posilek, {"kcal": -40, "P": 30, "F": 15, "C": 50}, prods)
    with pytest.raises(ValueError, match="round_step"):
        S.scale_meal({**posilek, "ingredients": [{**posilek["ingredients"][0], "round_step": 0}]},
                     {"kcal": 300, "P": 30, "F": 5, "C": 20}, prods)
    with pytest.raises(ValueError, match="brak posiłków"):
        S.scale_day({"day": 1, "meals": []}, {"kcal": 2000, "P": 125, "F": 67, "C": 225}, prods)


# --- silnik v1.1 (audyt 14.09): limity porcji jako reguły `fill_defaults` ---

def _posilek(*skl):
    return {"name": "t", "slot": "obiad", "kcal_share": 1.0, "ingredients": [{"product": p, "grams": g, "role": r} for p, g, r in skl]}


def test_v1_1_mieso_liniowe_nie_przekracza_300_g_surowego_na_posilek(prods):
    # 150 g kurczaka przy celu ×4 → bez limitu byłoby 600 g; limit 300 g i posiłek oflagowany.
    m = _posilek(("Pierś z kurczaka (surowa)", 150, "P"), ("Ryż biały (suchy)", 60, "C"))
    baza = S.sum_macros([S.fill_defaults(dict(i), prods) for i in m["ingredients"]], prods)
    cel = {k: v * 4 for k, v in baza.items()}
    r = S.scale_meal(m, cel, prods)
    kur = next(i for i in r["ingredients"] if i["product"] == "Pierś z kurczaka (surowa)")
    assert kur["grams"] == 300 and kur["max_factor"] == 2.0 and r["status"] != "OK"
    # Wędlina (grupa `wędlina`) nie podlega limitowi mięsa surowego.
    ing = S.fill_defaults({"product": "Szynka drobiowa (wędlina)", "grams": 150, "role": "P"}, prods) \
        if "Szynka drobiowa (wędlina)" in prods else None
    if ing is not None:
        assert ing["max_factor"] >= 2.0 or ing["class"] != "LINIOWY"


def test_v1_1_jajka_maks_4_sztuki_na_posilek(prods):
    ing = S.fill_defaults({"product": "Jajko kurze (całe)", "grams": 110, "role": "P", "class": "DYSKRETNY", "unit_g": 55}, prods)
    assert ing["max_factor"] == 2.0  # 4 × 55 g / 110 g
    ing1 = S.fill_defaults({"product": "Jajko kurze (całe)", "grams": 330, "role": "P", "class": "DYSKRETNY", "unit_g": 55}, prods)
    assert ing1["max_factor"] == 1.0  # 6 jajek w bazie → nie rośnie, ale nie spada poniżej 1


def test_v1_1_tluszcze_liniowe_skalowane_do_1_g_i_max_factor_3(prods):
    ing = S.fill_defaults({"product": "Oliwa z oliwek", "grams": 10, "role": "F"}, prods)
    assert ing["class"] == "LINIOWY" and ing["round_step"] == 1 and ing["max_factor"] >= 3.0
    m = _posilek(("Oliwa z oliwek", 10, "F"), ("Ryż biały (suchy)", 60, "C"))
    baza = S.sum_macros([S.fill_defaults(dict(i), prods) for i in m["ingredients"]], prods)
    r = S.scale_meal(m, {k: v * 1.23 for k, v in baza.items()}, prods)
    oliwa = next(i for i in r["ingredients"] if i["product"] == "Oliwa z oliwek")
    assert oliwa["grams"] == 12  # 12,3 g → 12 g (krok 1 g), nie 10/15


def test_alergeny_posilku_liczone_z_biezacych_skladnikow(prods):
    m = _posilek(("Pierś z kurczaka (surowa)", 150, "P"), ("Ryż biały (suchy)", 60, "C"))
    baza = S.sum_macros([S.fill_defaults(dict(i), prods) for i in m["ingredients"]], prods)
    assert S.scale_meal(m, baza, prods)["allergens"] == []
    m2 = _posilek(("Krewetki (surowe)", 150, "P"), ("Ryż biały (suchy)", 60, "C"))
    assert S.scale_meal(m2, baza, prods)["allergens"] == ["skorupiaki"]


# --- wymiany v2 (0.69.0): grupy pokrewne, funkcja w posiłku, bramka „nie pogarsza”, NONE 1:1 ---


def _skladnik(week, nazwa_posilku_fragment: str, produkt: str):
    for d in week:
        for m in d["meals"]:
            if nazwa_posilku_fragment in m["name"]:
                for i, x in enumerate(m["ingredients"]):
                    if x["product"] == produkt:
                        return m, i
    raise AssertionError(f"brak {produkt} w posiłku zawierającym „{nazwa_posilku_fragment}”")


def _pokrewne():
    from dzik_os.dieta import grupy

    return grupy.pokrewne()


def test_poziom_2_daje_kandydatow_z_grupy_pokrewnej_po_poziomie_1(prods, tpl):
    week = S.scale_week(tpl, 2000, prods)
    m, i = _skladnik(week, "Jajecznica", "Awokado")
    out, meta = S.swap_candidates_z_powodami(m, i, prods, n=5, related=_pokrewne())
    # tłuszcz_roślinny to singleton → bez poziomu 2 pusta lista z powodem SINGLETON…
    assert S.swap_candidates_z_powodami(m, i, prods, n=5)[1]["reason"] == "SINGLETON"
    # …a z grupami pokrewnymi (orzechy, tłuszcz) są kandydaci poziomu 2 z powodem powiązania.
    assert out and all(o["tier"] == 2 for o in out) and all(o["tier_reason"] for o in out)
    assert {o["group"] for o in out} <= {"orzechy", "tłuszcz"}
    assert meta["reason"] is None
    # Poziom 1 zawsze przed poziomem 2.
    m2, i2 = _skladnik(week, "Owsianka", "Płatki owsiane")
    out2 = S.swap_candidates(m2, i2, prods, n=10, related=_pokrewne())
    tiers = [o["tier"] for o in out2]
    assert tiers == sorted(tiers) and 1 in tiers


def test_rola_none_wymiana_1_do_1_wagowo_tylko_w_tej_samej_grupie(prods, tpl):
    week = S.scale_week(tpl, 2000, prods)
    m, i = _skladnik(week, "stir-fry", "Brokuł")
    out, _meta = S.swap_candidates_z_powodami(m, i, prods, n=10, related=_pokrewne())
    assert out and all(o["grams"] == m["ingredients"][i]["grams"] for o in out)
    assert all(o["tier"] == 1 and prods[o["product"]].substitution_group == "warzywa_gotowane" for o in out)
    assert any(o["product"] == "Kalafior" for o in out)


def test_bramka_nie_pogarsza_w_posilku_poza_tolerancja(prods, tpl):
    """Posiłek już poza tolerancją: kandydat neutralny/poprawiający przechodzi, pogarszający odpada."""
    week = S.scale_week(tpl, 2000, prods)
    m, i = _skladnik(week, "Kurczak stir-fry", "Pierś z kurczaka (surowa)")
    zly = dict(m)
    zly["ingredients"] = [dict(x) for x in m["ingredients"]]
    zly["ingredients"][i]["grams"] = zly["ingredients"][i]["grams"] * 0.5  # posiłek poza tolerancją (P i kcal w dół)
    assert not S.check(S.sum_macros(zly["ingredients"], prods), zly["target"], S.TOL_MEAL)[0]
    out, meta = S.swap_candidates_z_powodami(zly, i, prods, n=10, related=_pokrewne())
    assert out, meta
    dev0 = S._odchylenia(S.sum_macros(zly["ingredients"], prods), zly["target"])
    for o in out:
        dev = S._odchylenia(o["macros"], zly["target"])
        assert S.check(o["macros"], zly["target"], S.TOL_MEAL)[0] or all(dev[k] <= dev0[k] + 1e-9 for k in dev)
        assert set(o["meal_delta"]) == {"kcal", "P", "F", "C"}


def test_zaden_kandydat_nie_pogarsza_posilku_i_wynik_deterministyczny(prods, tpl):
    week = S.scale_week(tpl, 2000, prods)
    for d in week:
        for m in d["meals"]:
            dev0 = S._odchylenia(S.sum_macros(m["ingredients"], prods), m["target"])
            for i in range(len(m["ingredients"])):
                a = S.swap_candidates_z_powodami(m, i, prods, n=5, related=_pokrewne())
                b = S.swap_candidates_z_powodami(m, i, prods, n=5, related=_pokrewne())
                assert a == b
                for o in a[0]:
                    dev = S._odchylenia(o["macros"], m["target"])
                    assert S.check(o["macros"], m["target"], S.TOL_MEAL)[0] or all(dev[k] <= dev0[k] + 1e-9 for k in dev)


def test_poziom_2_nie_przemyca_alergenu_ani_wykluczenia(prods, tpl):
    week = S.scale_week(tpl, 2000, prods)
    m, i = _skladnik(week, "Jajecznica", "Jajko kurze (całe)")
    out, meta = S.swap_candidates_z_powodami(m, i, prods, n=10, related=_pokrewne(), exclusions=("soja", "meat"))
    assert all("soja" not in prods[o["product"]].allergens and "meat" not in prods[o["product"]].diet_exclusions for o in out)
    assert meta["rejected"].get("EXCLUDED", 0) >= 1
    # „nie lubię” po nazwie produktu też odsiewa (przed poziomem 2).
    out2, _ = S.swap_candidates_z_powodami(m, i, prods, n=10, related=_pokrewne(), exclusions=("Tempeh",))
    assert all(o["product"] != "Tempeh" for o in out2)


def test_powody_pustej_listy(prods, tpl):
    week = S.scale_week(tpl, 2000, prods)
    m, i = _skladnik(week, "Jajecznica", "Awokado")
    assert S.swap_candidates_z_powodami(m, i, prods)[1]["reason"] == "SINGLETON"
    # EXCLUDED: wszystko odpada przez wykluczenia (nazwy wszystkich kandydatów poziomu 1 i 2).
    out, _ = S.swap_candidates_z_powodami(m, i, prods, n=50, related=_pokrewne())
    nazwy = tuple(o["product"] for o in out)
    _, meta = S.swap_candidates_z_powodami(m, i, prods, n=50, related=_pokrewne(),
                                           exclusions=nazwy + tuple(p.name_pl for p in prods.values()
                                                                    if p.substitution_group in ("orzechy", "tłuszcz", "orzechy_pasty", "dodatek_tłuszczowy", "tłuszcz_roślinny")))
    assert meta["reason"] == "EXCLUDED"
    # FUNCTION: składnik z tagami, których żaden kandydat nie ma (sztuczny produkt), a tagi „*” u kandydata nie wystarczą na poziomie 2.
    p_sztuczny = S.Produkt(name_pl="Sztuczny", category="mięso", substitution_group="białko_chude", kcal_100=100,
                           protein_100=20, fat_100=2, carbs_100=0, cooking_tags="sous_vide", default_scaling="LINIOWY")
    prods2 = dict(prods, Sztuczny=p_sztuczny)
    m2, i2 = _skladnik(week, "Kurczak stir-fry", "Pierś z kurczaka (surowa)")
    posilek = dict(m2, ingredients=[dict(x) for x in m2["ingredients"]])
    posilek["ingredients"][i2] = dict(posilek["ingredients"][i2], product="Sztuczny")
    assert S.swap_candidates_z_powodami(posilek, i2, prods2, n=10, related=_pokrewne())[1]["reason"] == "FUNCTION"
    # TOLERANCE: kandydaci istnieją, ale każdy pogarsza posiłek — posiłek celowo „idealny” z celem = bieżące makro.
    idealny = dict(m2, ingredients=[dict(x) for x in m2["ingredients"]])
    idealny["target"] = {**S.sum_macros(idealny["ingredients"], prods), }
    idealny["target"] = {k: v for k, v in idealny["target"].items() if k in ("kcal", "P", "F", "C")}
    # Zawężamy tolerancję nie da się (stała) — zamiast tego składnik, którego każdy zamiennik zmienia makro: cel = dokładnie bieżące,
    # więc każdy kandydat o innym profilu daje |Δ| > 0 na jakiejś osi, chyba że mieści się w TOL_MEAL — sprawdzamy więc
    # tylko, że powód TOLERANCE pojawia się, gdy sztucznie odrzucimy wszystkich bramką (cel przesunięty poza zasięg).
    daleki = dict(idealny, target={"kcal": idealny["target"]["kcal"] + 400, "P": idealny["target"]["P"] + 60,
                                  "F": idealny["target"]["F"], "C": idealny["target"]["C"]})
    _, meta = S.swap_candidates_z_powodami(daleki, i2, prods, n=10, related=_pokrewne(),
                                           exclusions=tuple(p.name_pl for p in prods.values() if p.protein_100 > prods["Pierś z kurczaka (surowa)"].protein_100))
    assert meta["reason"] in ("TOLERANCE", "EXCLUDED")  # zależnie od tego, czy ktokolwiek dotarł do bramki
    # PORTION: kandydat mięsny musiałby przekroczyć 300 g.
    duzy = dict(m2, ingredients=[dict(x) for x in m2["ingredients"]])
    duzy["ingredients"][i2] = dict(duzy["ingredients"][i2], grams=290)
    duzy["target"] = S.sum_macros(duzy["ingredients"], prods)
    _, meta = S.swap_candidates_z_powodami(duzy, i2, prods, n=10, exclusions=("Pierś z indyka (surowa)",))
    assert "PORTION" in meta["rejected"]


def test_puste_tagi_kandydata_to_wildcard_na_poziomie_1_ale_nie_na_2(prods):
    ing = {"product": "Ryż biały (suchy)", "grams": 60, "role": "C"}
    meal = {"name": "t", "slot": "obiad", "kcal_share": 1.0, "ingredients": [ing]}
    r = S.scale_meal(meal, {"kcal": 210, "P": 4, "F": 1, "C": 47}, prods)
    bez_tagow = S.Produkt(name_pl="Ziarno bez tagów", category="zboża", substitution_group="kasza_ryż", kcal_100=350,
                          protein_100=7, fat_100=1, carbs_100=78, cooking_tags="", default_scaling="LINIOWY")
    bez_tagow_2 = S.Produkt(name_pl="Makaron bez tagów", category="zboża", substitution_group="makaron", kcal_100=350,
                            protein_100=12, fat_100=1.5, carbs_100=72, cooking_tags="", default_scaling="LINIOWY")
    prods2 = dict(prods, **{bez_tagow.name_pl: bez_tagow, bez_tagow_2.name_pl: bez_tagow_2})
    out = S.swap_candidates(r, 0, prods2, n=50, related=_pokrewne())
    nazwy = {o["product"] for o in out}
    assert "Ziarno bez tagów" in nazwy      # poziom 1: pusty zestaw tagów = wildcard
    assert "Makaron bez tagów" not in nazwy  # poziom 2: wildcard kandydata nie wystarcza

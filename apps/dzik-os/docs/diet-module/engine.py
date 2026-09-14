"""Silnik skalowania szablonów jadłospisów (v0.1).
Implementuje kroki 1-5 z instrukcji: rozdział kcal na posiłki, skalowanie wstępne,
dopasowanie makro rolami P/C/F, zaokrąglenie, kontrola + flagi.
"""
import json, math, copy
import pandas as pd

PRODUCTS = {r.name_pl: r for r in pd.read_csv('/home/claude/usda/products.csv').itertuples()}

CLASS_DEFAULTS = {
    'LINIOWY':   dict(min_factor=0.5, max_factor=2.0, round_step=5),
    'DYSKRETNY': dict(min_factor=0.5, max_factor=2.5, round_step=None),
    'TŁUMIONY':  dict(min_factor=0.7, max_factor=1.5, round_step=10, exponent=0.5),
    'STAŁY':     dict(min_factor=1.0, max_factor=1.0, round_step=None),
}
TOL_MEAL = dict(kcal_pct=0.08, kcal_abs=40, P=5, F=4, C=10)
TOL_DAY  = dict(kcal_pct=0.03, kcal_abs=0, P=5, F=5, C=10)


def macros(ing):
    p = PRODUCTS[ing['product']]
    g = ing['grams'] / 100
    return dict(kcal=p.kcal_100 * g, P=p.protein_100 * g, F=p.fat_100 * g, C=p.carbs_100 * g)


def sum_macros(ings):
    t = dict(kcal=0, P=0, F=0, C=0)
    for i in ings:
        for k, v in macros(i).items():
            t[k] += v
    return t


def fill_defaults(ing):
    cls = ing.get('class') or PRODUCTS[ing['product']].default_scaling
    d = CLASS_DEFAULTS[cls]
    ing.setdefault('class', cls)
    ing.setdefault('role', 'NONE')
    for k, v in d.items():
        ing.setdefault(k, v)
    # tłuszcze dodawane w małych ilościach (5-15 g) mogą rosnąć do 3x - nadal praktyczne
    p = PRODUCTS[ing['product']]
    if p.category in ('mięso', 'ryby') and p.substitution_group != 'wędlina' and cls == 'LINIOWY' and ing['grams'] > 0:
        ing['max_factor'] = min(ing['max_factor'], 300 / ing['grams'])   # maks. 300 g surowego na posiłek (twardy limit)
        ing['min_factor'] = min(ing['min_factor'], ing['max_factor'])
    if ing['product'] == 'Jajko kurze (całe)' and cls == 'DYSKRETNY':
        ing['max_factor'] = min(ing['max_factor'], max(1.0, 4 * ing['unit_g'] / ing['grams']))  # maks. 4 jajka na posiłek
    if PRODUCTS[ing['product']].category == 'tłuszcze' and cls == 'LINIOWY':
        ing['max_factor'] = max(ing['max_factor'], 3.0)
        ing['round_step'] = 1  # oleje, orzechy, nasiona: 1 g (5 g to ~10% dziennego tłuszczu na redukcji)
    if cls == 'DYSKRETNY':
        assert 'unit_g' in ing, f"{ing['product']}: DYSKRETNY wymaga unit_g"
        ing.setdefault('unit_step', 1.0)
    ing['base_grams'] = ing['grams']
    return ing


def clamp(ing, grams):
    lo, hi = ing['base_grams'] * ing['min_factor'], ing['base_grams'] * ing['max_factor']
    return max(lo, min(hi, grams))


def scale_initial(ings, k):
    """Krok 2: skalowanie wstępne wg klasy."""
    for i in ings:
        c = i['class']
        if c == 'STAŁY':
            continue
        f = k if c != 'TŁUMIONY' else k ** i['exponent']
        i['grams'] = clamp(i, i['base_grams'] * f)


def fit_macros(ings, target, passes=6):
    """Krok 3: korekta makro tylko składnikami z daną rolą, w granicach zakresów."""
    hit_limit = False
    for _ in range(passes):
        cur = sum_macros(ings)
        for m, key in (('P', 'protein_100'), ('C', 'carbs_100'), ('F', 'fat_100')):
            deficit = target[m] - cur[m]
            drivers = [i for i in ings if i['role'] == m and i['class'] != 'STAŁY']
            if not drivers or abs(deficit) < 0.5:
                continue
            contrib = [getattr(PRODUCTS[i['product']], key) / 100 for i in drivers]
            total = sum(c * i['grams'] for c, i in zip(contrib, drivers)) or 1e-9
            for c, i in zip(contrib, drivers):
                if c == 0:
                    continue
                share = (c * i['grams']) / total
                want = i['grams'] + deficit * share / c
                new = clamp(i, want)
                if abs(new - want) > 0.5:
                    hit_limit = True
                i['grams'] = new
            cur = sum_macros(ings)
    return hit_limit


def fit_kcal(ings, target, passes=3):
    """Krok 3b: domknięcie kcal - proporcjonalnie na wszystkich skalowalnych składnikach z rolą."""
    for _ in range(passes):
        cur = sum_macros(ings)
        gap = target['kcal'] - cur['kcal']
        if abs(gap) < 5:
            return
        drivers = [i for i in ings if i['class'] in ('LINIOWY', 'DYSKRETNY') and i['role'] != 'NONE']
        kc = sum(macros(i)['kcal'] for i in drivers) or 1e-9
        f = 1 + gap / kc
        for i in drivers:
            i['grams'] = clamp(i, i['grams'] * f)


def round_practical(ings):
    """Krok 4: zaokrąglenie do praktycznych ilości."""
    for i in ings:
        c = i['class']
        if c == 'STAŁY':
            continue
        if c == 'DYSKRETNY':
            units = i['grams'] / i['unit_g']
            units = max(i['unit_step'], round(units / i['unit_step']) * i['unit_step'])
            i['units'] = units
            i['grams'] = units * i['unit_g']
        else:
            step = i['round_step']
            i['grams'] = max(step, round(i['grams'] / step) * step)


def check(cur, target, tol):
    dev = dict(kcal=cur['kcal'] - target['kcal'], P=cur['P'] - target['P'],
               F=cur['F'] - target['F'], C=cur['C'] - target['C'])
    ok = (abs(dev['kcal']) <= max(tol['kcal_pct'] * target['kcal'], tol['kcal_abs']) and abs(dev['P']) <= tol['P']
          and abs(dev['F']) <= tol['F'] and abs(dev['C']) <= tol['C'])
    return ok, dev


def scale_meal(meal, target):
    ings = [fill_defaults(copy.deepcopy(i)) for i in meal['ingredients']]
    base = sum_macros(ings)
    k = target['kcal'] / base['kcal']
    scale_initial(ings, k)
    limit = fit_macros(ings, target)
    fit_kcal(ings, target)
    round_practical(ings)
    cur = sum_macros(ings)
    ok, dev = check(cur, target, TOL_MEAL)
    status = 'OK' if ok else ('POZA_ZAKRESEM' if limit else 'OSTRZEŻENIE')
    return dict(name=meal['name'], slot=meal['slot'], ingredients=ings, macros=cur,
                target=target, deviation=dev, status=status, k=k, steps=meal.get('steps', ''))


def scale_day(day, day_target):
    """Krok 1: kcal posiłku wg udziału; makro posiłku wg jego własnego profilu bazowego,
    przeskalowane o stosunek (cel dnia / suma bazowa dnia) - zachowuje charakter przepisu."""
    bases = [sum_macros([fill_defaults(copy.deepcopy(i)) for i in m['ingredients']]) for m in day['meals']]
    base_day = {m: sum(b[m] for b in bases) for m in ('kcal', 'P', 'F', 'C')}
    ratio = {m: day_target[m] / base_day[m] for m in ('P', 'F', 'C')}
    out = []
    for meal, b in zip(day['meals'], bases):
        kcal_t = day_target['kcal'] * meal['kcal_share']
        kf = kcal_t / (b['kcal'] * day_target['kcal'] / base_day['kcal'])  # korekta gdy udział != baza
        t = dict(kcal=kcal_t, **{m: b[m] * ratio[m] * kf for m in ('P', 'F', 'C')})
        # renormalizuj, by 4P+9F+4C = kcal_t
        e = 4 * t['P'] + 9 * t['F'] + 4 * t['C']
        for m in ('P', 'F', 'C'):
            t[m] *= kcal_t / e
        out.append(scale_meal(meal, t))
    # przebieg 2: resztę dnia rozłóż proporcjonalnie do udziałów i przelicz ponownie
    cur = {m: sum(r['macros'][m] for r in out) for m in ('kcal', 'P', 'F', 'C')}
    resid = {m: day_target[m] - cur[m] for m in ('kcal', 'P', 'F', 'C')}
    out2 = []
    for meal, r in zip(day['meals'], out):
        t = {m: r['target'][m] + resid[m] * meal['kcal_share'] for m in resid}
        out2.append(scale_meal(meal, t))
    out = out2
    cur = {m: sum(r['macros'][m] for r in out) for m in ('kcal', 'P', 'F', 'C')}
    flex = [i for i, m in enumerate(day['meals']) if m.get('flexible')]
    if flex:
        idx = flex[0]
        resid = {m: day_target[m] - cur[m] for m in ('kcal', 'P', 'F', 'C')}
        newt = {m: out[idx]['target'][m] + resid[m] for m in resid}
        out[idx] = scale_meal(day['meals'][idx], newt)
        cur = {m: sum(r['macros'][m] for r in out) for m in ('kcal', 'P', 'F', 'C')}
    # krok 5c: dostrojenie dnia - pojedyncze kroki zaokrąglenia na składnikach LINIOWY z rolą
    for _ in range(12):
        ok, dev = check(cur, day_target, TOL_DAY)
        if ok:
            break
        m = max(('P', 'F', 'C'), key=lambda x: abs(dev[x]) / TOL_DAY[x]) if any(abs(dev[x]) > TOL_DAY[x] for x in ('P','F','C')) else None
        if m is None:  # tylko kcal poza - użyj C
            m = 'C' if abs(dev['C']) >= abs(dev['P']) else 'P'
        moved = False
        for r in sorted(out, key=lambda r: -r['target']['kcal']):
            for i in r['ingredients']:
                if i['class'] == 'LINIOWY' and i['role'] == m:
                    step = i['round_step'] * (-1 if dev[m] > 0 else 1)
                    new = i['grams'] + step
                    if clamp(i, new) == new and new > 0:
                        i['grams'] = new; moved = True; break
            if moved: break
        if not moved:
            break
        for r in out:
            r['macros'] = sum_macros(r['ingredients'])
        cur = {mm: sum(r['macros'][mm] for r in out) for mm in ('kcal', 'P', 'F', 'C')}
    ok, dev = check(cur, day_target, TOL_DAY)
    return dict(day=day['day'], meals=out, macros=cur, target=day_target, deviation=dev,
                status='OK' if ok else 'POZA_TOLERANCJĄ')


def day_target(kcal, pct):
    """pct = (P%, F%, C%) kcal -> gramy (4/9/4)."""
    p, f, c = pct
    return dict(kcal=kcal, P=kcal * p / 4, F=kcal * f / 9, C=kcal * c / 4)


def scale_week(template, kcal, pct=None):
    pct = pct or template['macro_pct']
    t = day_target(kcal, pct)
    return [scale_day(d, t) for d in template['days']]


def report(week, kcal):
    lines = [f"### {kcal} kcal"]
    flagged = 0
    for d in week:
        m = d['macros']
        lines.append(f"Dzień {d['day']}: {m['kcal']:.0f} kcal | B {m['P']:.0f} T {m['F']:.0f} W {m['C']:.0f} | {d['status']}")
        for r in d['meals']:
            if r['status'] != 'OK':
                flagged += 1
                dv = r['deviation']
                lines.append(f"   ⚠ {r['slot']} {r['name']}: {r['status']} (Δkcal {dv['kcal']:+.0f}, ΔB {dv['P']:+.0f}, ΔT {dv['F']:+.0f}, ΔW {dv['C']:+.0f})")
    lines.append(f"Posiłków z flagą: {flagged}/{sum(len(d['meals']) for d in week)}")
    return "\n".join(lines)


def swap_candidates(meal_result, ing_index, exclusions=(), n=3):
    """Wymiana produktu: kandydaci z tej samej substitution_group, zgodni z metodą przygotowania,
    przeliczeni izokalorycznie z zachowaniem roli makro; odpadają ci, którzy wyprowadzą posiłek poza tolerancję."""
    ing = meal_result['ingredients'][ing_index]
    p = PRODUCTS[ing['product']]
    ctags = set(p.cooking_tags.split(','))
    orig = macros(ing)
    role_key = {'P': 'protein_100', 'C': 'carbs_100', 'F': 'fat_100'}.get(ing['role'], 'kcal_100')
    cands = []
    for q in PRODUCTS.values():
        if q.name_pl == p.name_pl or q.substitution_group != p.substitution_group:
            continue
        if any(x in str(q.diet_exclusions) or x in str(q.allergens) for x in exclusions):
            continue
        qtags = set(str(q.cooking_tags).split(','))
        if '*' not in qtags and not (ctags & qtags):
            continue
        per = getattr(q, role_key) / 100
        if per <= 0:
            continue
        # gramatura zachowująca makro roli (dla NONE: kcal)
        key = ing['role'] if ing['role'] in ('P', 'C', 'F') else 'kcal'
        g = orig[key] / per
        step = ing.get('round_step') or 5
        g = max(step, round(g / step) * step)
        new = dict(ing, product=q.name_pl, grams=g)
        ings = [dict(x) for x in meal_result['ingredients']]
        ings[ing_index] = new
        cur = sum_macros(ings)
        ok, dev = check(cur, meal_result['target'], TOL_MEAL)
        if not ok:
            continue
        dist = sum(abs(getattr(q, k) - getattr(p, k)) for k in ('protein_100', 'fat_100', 'carbs_100'))
        cands.append((dist, q.name_pl, g, cur))
    cands.sort()
    return [dict(product=c[1], grams=c[2], macros=c[3]) for c in cands[:n]]

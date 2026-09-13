# ruff: noqa
# Silnik referencyjny z pakietu właściciela „IMPLEMENTACJA_KREATORA_DIETY_300”
# (engine.py 1.0.0, 13.09.2026) — skopiowany DOSŁOWNIE, żeby diff względem
# pakietu był pusty; styl zwarty pochodzi z pakietu. Adapter i integracja:
# `adapter.py`, `serwis.py`, `routers/kulinaria.py`.
"""Framework-independent meal planner. Python 3.10+, standard library only.

Draft mode is a culinary preview, never a balanced nutritional prescription.
Production mode requires published, reviewed recipes and verified food records.
"""
from __future__ import annotations
from collections import Counter
from datetime import date, timedelta
import hashlib
import json
import math

VERSION = '1.0.0'
ANIMAL_EXCLUSIONS = {
    'omnivore': set(),
    'vegetarian': {'meat', 'fish', 'animal_gelatin'},
    'pescetarian': {'meat', 'animal_gelatin'},
    'vegan': {'meat', 'fish', 'eggs', 'dairy', 'honey', 'animal_gelatin'},
}
SLOTS = {2: ['breakfast', 'main'], 3: ['breakfast', 'main', 'supper'],
         4: ['breakfast', 'main', 'snack', 'supper'],
         5: ['breakfast', 'snack', 'main', 'snack', 'supper'],
         6: ['breakfast', 'snack', 'main', 'snack', 'supper', 'snack']}
REQUIRED_MACROS = {'energy_kcal', 'protein_g', 'fat_g', 'carbs_available_g'}

class InputError(ValueError):
    pass

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                      separators=(',', ':')).encode()).hexdigest()[:20]

def result(status, issues, plan=None):
    return {'status': status, 'issues': issues, 'plan': plan, 'engine_version': VERSION}

def validate_config(c):
    if c.get('mode') not in {'preview', 'production'}:
        raise InputError('mode must be preview or production')
    if type(c.get('days')) is not int or not 1 <= c['days'] <= 31:
        raise InputError('days must be 1..31')
    if type(c.get('meal_count')) is not int or c['meal_count'] not in SLOTS:
        raise InputError('meal_count must be 2..6')
    if c.get('animal_policy') not in ANIMAL_EXCLUSIONS:
        raise InputError('unknown animal_policy')
    if c.get('pattern') not in {'balanced', 'mediterranean', 'paleo_classic_v1'}:
        raise InputError('unknown pattern')
    if c.get('carb_policy') not in {'standard', 'low_carb', 'ketogenic'}:
        raise InputError('unknown carb_policy')
    if c.get('carb_policy') != 'standard':
        if not number(c.get('carb_limit_g')) or c['carb_limit_g'] <= 0:
            raise InputError('carb_limit_g is required')
        if c.get('carb_basis') != 'available_excluding_fiber':
            raise InputError('v1 supports only explicit available_excluding_fiber')
    if not number(c.get('max_total_minutes')) or c['max_total_minutes'] <= 0:
        raise InputError('max_total_minutes must be positive')
    if not number(c.get('max_active_minutes')) or c['max_active_minutes'] <= 0:
        raise InputError('max_active_minutes must be positive')
    if type(c.get('max_family_uses_per_week')) is not int or not 1 <= c['max_family_uses_per_week'] <= 42:
        raise InputError('max_family_uses_per_week must be 1..42')
    try:
        date.fromisoformat(c['start_date'])
    except (KeyError, ValueError, TypeError):
        raise InputError('invalid start_date')
    for k in ['excluded_ingredient_ids', 'allergens', 'equipment', 'preferred_cuisines']:
        if not isinstance(c.get(k), list) or any(not isinstance(x, str) for x in c[k]):
            raise InputError(k + ' must be a list of strings')
    # This is an integration gate, not a medical questionnaire or diagnosis.
    if c.get('screening_status') not in {'cleared', 'needs_review', 'unknown'}:
        raise InputError('screening_status must be explicitly supplied')
    bounds = c.get('daily_bounds', {})
    if not isinstance(bounds, dict):
        raise InputError('daily_bounds must be an object')
    for k, b in bounds.items():
        if not isinstance(b, list) or len(b) != 2 or not all(number(v) for v in b) or not 0 <= b[0] <= b[1]:
            raise InputError('invalid bounds for ' + k)
    if c['mode'] == 'production':
        if not REQUIRED_MACROS <= bounds.keys():
            raise InputError('production requires explicit energy and macro bounds')
        if not c.get('targets_reference'):
            raise InputError('production requires targets_reference')
        if any(k not in bounds for k in c.get('required_nutrients', [])):
            raise InputError('every required nutrient needs bounds')
        if c['carb_policy'] != 'standard' and bounds['carbs_available_g'][0] > c['carb_limit_g']:
            raise InputError('carb target conflicts with diet limit')
    return c

def validate_catalog(recipes, foods):
    ids = set()
    for r in recipes:
        if r['id'] in ids:
            raise InputError('duplicate recipe id')
        ids.add(r['id'])
        if r['servings'] != 1 or not r['ingredients'] or not r['steps']:
            raise InputError('recipe needs one explicit base serving, ingredients and steps')
        if not set(r['meal_slots']) <= {'breakfast', 'main', 'snack', 'supper'}:
            raise InputError('unknown slot')
        if not 0 < r['active_minutes'] <= r['total_minutes']:
            raise InputError('invalid cooking times')
        line_ids = [x['food_id'] for x in r['ingredients']]
        if len(line_ids) != len(set(line_ids)):
            raise InputError('duplicate ingredient line: consolidate amounts')
        for line in r['ingredients']:
            f = foods.get(line['food_id'])
            if f is None or f['state'] != line['state']:
                raise InputError('missing food or state mismatch')
            if not number(line['grams']) or line['grams'] <= 0:
                raise InputError('grams must be positive')
        # No independent ingredient optimisation: only whole tested variants.
        for p in r['portion_variants']:
            if not number(p['factor']) or p['factor'] <= 0:
                raise InputError('invalid portion factor')

def normalise_nutrients(food):
    if not food.get('nutrition_verified'):
        raise InputError('unverified food data')
    if not food.get('source_id') or not food.get('source_version'):
        raise InputError('missing nutrition provenance')
    n = dict(food.get('nutrition_per_100g') or {})
    if any(not number(v) or v < 0 for v in n.values()):
        raise InputError('unknown or invalid nutrient value')
    basis = food.get('carb_definition')
    if basis == 'available_excluding_fiber':
        if 'carbs_available_g' not in n:
            raise InputError('missing available carbohydrate')
    elif basis == 'total_including_fiber':
        if not {'carbs_total_g', 'fiber_g'} <= n.keys():
            raise InputError('fiber required to normalise total carbohydrate')
        available = n['carbs_total_g'] - n['fiber_g']
        if available < 0:
            raise InputError('fiber exceeds total carbohydrate')
        n['carbs_available_g'] = available
    else:
        raise InputError('unknown carbohydrate definition')
    # Polyols stay included; v1 never subtracts them automatically.
    if not REQUIRED_MACROS <= n.keys():
        raise InputError('missing macro values')
    return n

def recipe_nutrition(recipe, foods, factor, required):
    sums = {key: 0.0 for key in required}
    for line in recipe['ingredients']:
        n = normalise_nutrients(foods[line['food_id']])
        if not set(required) <= n.keys():
            raise InputError('missing nutrient required by targets')
        for key in required:
            sums[key] += n[key] * line['grams'] * factor / 100
    return sums

def eligible(r, c, foods):
    if r['total_minutes'] > c['max_total_minutes'] or r['active_minutes'] > c['max_active_minutes']:
        return False, 'time'
    if not set(r['equipment']) <= set(c['equipment']):
        return False, 'equipment'
    for line in r['ingredients']:
        f = foods[line['food_id']]
        if f['id'] in c['excluded_ingredient_ids']:
            return False, 'excluded_ingredient'
        if ANIMAL_EXCLUSIONS[c['animal_policy']] & set(f['groups']):
            return False, 'animal_policy'
        if c['pattern'] == 'paleo_classic_v1' and {'grain', 'legume', 'dairy'} & set(f['groups']):
            return False, 'pattern'
        if set(c['allergens']) & set(f['allergens']):
            return False, 'allergen'
        if c['allergens'] and not f.get('allergen_verified'):
            return False, 'unknown_allergen_data'
    if c['mode'] == 'production':
        if r['status'] != 'published' or not all(r['review'].get(k) for k in ['kitchen', 'dietitian', 'reviewer_id']):
            return False, 'unpublished'
        try:
            if date.fromisoformat(r['review']['expires_on']) < date.today():
                return False, 'expired_review'
        except (KeyError, TypeError, ValueError):
            return False, 'missing_review_date'
    return True, None

def coverage(recipes, foods, config):
    validate_config(config)
    validate_catalog(recipes, foods)
    counts = {slot: {'recipes': 0, 'families': set()} for slot in set(SLOTS[config['meal_count']])}
    rejected = Counter()
    for r in recipes:
        ok, reason = eligible(r, config, foods)
        if not ok:
            rejected[reason] += 1
            continue
        for slot in r['meal_slots']:
            if slot in counts:
                counts[slot]['recipes'] += 1
                counts[slot]['families'].add(r['family_id'])
    return {'mode': config['mode'], 'slots': {s: {'recipes': v['recipes'], 'families': len(v['families'])}
            for s, v in sorted(counts.items())}, 'rejected': dict(rejected),
            'nutrition_feasibility_verified': False}

def candidate_rows(recipes, foods, c):
    candidates = []
    reasons = Counter()
    required = set(c.get('daily_bounds', {})) | REQUIRED_MACROS
    for r in recipes:
        ok, why = eligible(r, c, foods)
        if not ok:
            reasons[why] += 1
            continue
        for variant in r['portion_variants']:
            if c['mode'] == 'production' and not variant['validated']:
                reasons['unvalidated_portion'] += 1
                continue
            if c['mode'] == 'preview' and variant['factor'] != 1:
                continue
            nutrients = None
            if c['mode'] == 'production':
                try:
                    nutrients = recipe_nutrition(r, foods, variant['factor'], required)
                except InputError:
                    reasons['missing_nutrition'] += 1
                    continue
            candidates.append({'recipe': r, 'variant': variant, 'nutrients': nutrients})
    return candidates, dict(reasons)

def generate(config, recipes, foods):
    try:
        c = validate_config(dict(config))
        validate_catalog(recipes, foods)
    except (InputError, KeyError, TypeError) as exc:
        return result('needs_input', [str(exc)])
    if c['screening_status'] != 'cleared':
        return result('needs_review', ['Source health workflow must authorise this scope.'])
    if c['mode'] == 'preview' and c['carb_policy'] != 'standard':
        return result('nutrition_unverified', ['Low-carb and ketogenic menus require verified nutritional values. Preview cannot assert this constraint.'])
    candidates, rejected = candidate_rows(recipes, foods, c)
    slots = SLOTS[c['meal_count']]
    if any(not any(s in row['recipe']['meal_slots'] for row in candidates) for s in slots):
        return result('insufficient_catalog', [{'code': 'MISSING_SLOT_CANDIDATES', 'rejected': rejected}])
    plan_id = digest({'config': c, 'engine': VERSION, 'recipes': recipes, 'foods': foods})
    bounds = c.get('daily_bounds', {})
    if c['carb_policy'] != 'standard' and c['mode'] == 'production':
        bounds = dict(bounds)
        low, high = bounds['carbs_available_g']
        bounds['carbs_available_g'] = [low, min(high, c['carb_limit_g'])]
    days = []
    monthly = Counter()
    weekly = Counter()
    # Deterministic bounded beam; failure does not prove mathematical infeasibility.
    for day_index in range(c['days']):
        if day_index % 7 == 0:
            weekly = Counter()
        beam = [([], {}, Counter(), 0.0)]
        for slot_index, slot in enumerate(slots):
            nxt = []
            for chosen, totals, local, score in beam:
                for row in candidates:
                    r = row['recipe']; fam = r['family_id']
                    if slot not in r['meal_slots'] or weekly[fam] + local[fam] >= c['max_family_uses_per_week']:
                        continue
                    if any(x['recipe']['id'] == r['id'] for x in chosen):
                        continue
                    values = dict(totals)
                    for key, val in (row['nutrients'] or {}).items():
                        values[key] = values.get(key, 0) + val
                    if c['mode'] == 'production' and any(values[k] > hi + 1e-8 for k, (lo, hi) in bounds.items()):
                        continue
                    loc = local.copy();loc[fam] += 1
                    preference = 0 if not c['preferred_cuisines'] or r['cuisine'] in c['preferred_cuisines'] else 1
                    extra = monthly[r['id']] * 4 + weekly[fam] + local[fam] * 2 + preference
                    nxt.append((chosen + [row], values, loc, score + extra))
            def rank(state):
                chosen, vals, loc, score = state
                # Partial-day midpoint heuristic is search guidance, not meal macro constraint.
                loss = 0
                if c['mode'] == 'production':
                    fraction = (slot_index + 1) / len(slots)
                    for key, (lo, hi) in bounds.items():
                        midpoint = (lo + hi) / 2
                        loss += abs(vals[key] - midpoint * fraction) / max(midpoint, 1)
                return (loss * 10 + score, tuple(x['recipe']['id'] + ':' + x['variant']['id'] for x in chosen))
            nxt.sort(key=rank)
            beam = nxt[:80]
            if not beam:
                return result('search_exhausted', [{'code': 'BOUNDED_SEARCH_EMPTY', 'day_index': day_index,
                                                    'message': 'No partial plan returned. Relax soft settings or expand catalogue.'}])
        feasible = [s for s in beam if c['mode'] == 'preview' or
                    all(lo - 1e-8 <= s[1][k] <= hi + 1e-8 for k, (lo, hi) in bounds.items())]
        if not feasible:
            return result('search_exhausted', [{'code': 'NO_FEASIBLE_DAY_IN_BEAM', 'day_index': day_index}])
        chosen, totals, local, _ = min(feasible, key=lambda s: (s[3], tuple(x['recipe']['id'] for x in s[0])))
        meals = []
        for i, row in enumerate(chosen):
            r = row['recipe']; factor = row['variant']['factor'];monthly[r['id']] += 1
            meals.append({'slot': slots[i], 'recipe_id': r['id'], 'recipe_revision': r['revision'],
                          'recipe_name': r['name'], 'family_id': r['family_id'],
                          'portion_variant': row['variant']['id'], 'factor': factor,
                          'ingredients': [{**x, 'grams': x['grams'] * factor} for x in r['ingredients']],
                          'steps': r['steps'], 'total_minutes': r['total_minutes'],
                          'nutrition': row['nutrients'],
                          'decision_trace': {'rule_id': 'CURATED_VARIANT_SELECTION', 'rule_version': VERSION,
                              'plan_id': plan_id, 'target_id': f'{day_index}:{i}',
                              'facts': {'animal_policy': c['animal_policy'], 'pattern': c['pattern'],
                                        'time_limit': c['max_total_minutes'], 'recipe_status': r['status']},
                              'outcome': r['id'] + ':' + row['variant']['id']}})
        weekly.update(local)
        days.append({'date': (date.fromisoformat(c['start_date']) + timedelta(days=day_index)).isoformat(),
                     'meals': meals, 'nutrition': totals if c['mode'] == 'production' else None})
    report = []
    if c['mode'] == 'preview':
        report += ['Draft culinary preview. Nutrition and ketogenic compliance are not verified.',
                   'Estimated cooking times and recipe taste have not been kitchen-tested.']
    else:
        report += ['Only explicitly requested nutrient bounds were validated; not a clinical adequacy assessment.']
    plan = {'id': plan_id, 'revision': 1, 'mode': c['mode'], 'days': days,
            'carb_compliance_verified': c['mode'] == 'production' and c['carb_policy'] != 'standard',
            'nutrition_scope': sorted(bounds) if c['mode'] == 'production' else [], 'limitations': report}
    # Independent final pass recomputes core properties, does not trust search state.
    errors = audit_plan(plan, c, recipes, foods)
    if errors:
        return result('validation_failed', errors)
    return result('draft_preview' if c['mode'] == 'preview' else 'ready_within_declared_bounds', report, plan)

def audit_plan(plan, c, recipes, foods):
    errors = [];byid = {r['id']: r for r in recipes};counts = Counter()
    if len(plan['days']) != c['days']:
        errors.append('wrong horizon')
    for di, d in enumerate(plan['days']):
        if di % 7 == 0:counts = Counter()
        if d['date'] != (date.fromisoformat(c['start_date']) + timedelta(days=di)).isoformat():
            errors.append('date mismatch')
        if len(d['meals']) != c['meal_count']:
            errors.append('meal count mismatch')
        total = Counter()
        for si, meal in enumerate(d['meals']):
            r = byid.get(meal['recipe_id'])
            if not r or not eligible(r, c, foods)[0]:
                errors.append('ineligible recipe');continue
            if meal['slot'] != SLOTS[c['meal_count']][si] or meal['slot'] not in r['meal_slots']:
                errors.append('wrong slot')
            variants = [v for v in r['portion_variants'] if v['id'] == meal['portion_variant'] and v['factor'] == meal['factor']]
            if not variants or (c['mode'] == 'production' and not variants[0]['validated']):
                errors.append('unapproved variant');continue
            expected = [{**x, 'grams': x['grams'] * meal['factor']} for x in r['ingredients']]
            if expected != meal['ingredients']:
                errors.append('ingredient mutation')
            counts[r['family_id']] += 1
            if c['mode'] == 'production':
                try:
                    n = recipe_nutrition(r, foods, meal['factor'], set(c['daily_bounds']) | REQUIRED_MACROS)
                    total.update(n)
                    if n != meal['nutrition']:errors.append('nutrition mismatch')
                except InputError:errors.append('unverified nutrients')
        if counts and max(counts.values()) > c['max_family_uses_per_week']:
            errors.append('family repetition cap')
        if c['mode'] == 'production':
            if dict(total) != d['nutrition']:errors.append('daily nutrition mismatch')
            for k, (lo, hi) in c['daily_bounds'].items():
                if not lo - 1e-8 <= total[k] <= hi + 1e-8:errors.append('nutrient bounds')
            if c['carb_policy'] != 'standard' and total['carbs_available_g'] > c['carb_limit_g'] + 1e-8:
                errors.append('carb limit')
    return errors

def shopping_list(plan):
    sums = Counter()
    for d in plan['days']:
        for m in d['meals']:
            for x in m['ingredients']:sums[(x['food_id'], x['state'])] += x['grams']
    return [{'food_id': k[0], 'state': k[1], 'edible_grams': round(v, 1)} for k, v in sorted(sums.items())]

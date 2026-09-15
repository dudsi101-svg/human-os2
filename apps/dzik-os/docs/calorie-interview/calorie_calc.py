"""Referencyjna implementacja obliczeń bilansu kalorycznego (wywiad). Czysta funkcja, bez I/O.
Zgodna ze specyfikacją wywiad_zapotrzebowanie_kaloryczne.md, sekcja 5."""
from datetime import date

FORMULAS_VERSION = "2026-09-13.1"
NEAT = {'neat_1': 1.20, 'neat_2': 1.35, 'neat_3': 1.50, 'neat_4': 1.70}
MET = {'strength': 5.0, 'cardio_light': 4.0, 'cardio_moderate': 7.0, 'cardio_high': 10.0}
PACE = {('cut', 'gentle'): -0.10, ('cut', 'moderate'): -0.20, ('cut', 'fast'): -0.25,
        ('maintain', None): 0.0, ('bulk', 'gentle'): 0.05, ('bulk', 'moderate'): 0.10, ('bulk', 'fast'): 0.15,
        ('recomp', None): -0.05}
PROTEIN = {'cut': (1.8, 2.2), 'maintain': (1.6, 1.6), 'bulk': (1.8, 1.8), 'recomp': (2.2, 2.2)}
FAT_G_KG = {'cut': 0.9, 'maintain': 1.0, 'bulk': 1.0, 'recomp': 0.9}
MIN_KCAL = {'F': 1200, 'M': 1500}


def age_from(birth, today=None):
    today = today or date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def bmr_mifflin(sex, kg, cm, age):
    return 10 * kg + 6.25 * cm - 5 * age + (5 if sex == 'M' else -161)


def bmr_katch(kg, bf_pct):
    return 370 + 21.6 * kg * (1 - bf_pct / 100)


def training_kcal_per_day(kg, sessions):
    """sessions: list of (kind, per_week, minutes)."""
    return sum(n * m * MET[k] * kg * 0.0175 for k, n, m in sessions) / 7


def compute(a, today=None):
    """a: dict odpowiedzi. Zwraca dict wyników z flagami."""
    flags = []
    age = age_from(a['birth_date'], today)
    kg, cm, sex = a['weight_kg'], a['height_cm'], a['sex']
    bmi = kg / (cm / 100) ** 2
    if age < 18: flags.append('MALOLETNI')
    if bmi < 17 or bmi > 40: flags.append('BMI_SKRAJNE')
    for k, f in (('pregnant_or_nursing', 'CIAZA_KARMIENIE'), ('metabolic_disease', 'CHOROBA_METABOLICZNA'),
                 ('weight_affecting_meds', 'LEKI'), ('eating_disorder', 'ZABURZENIA_ODZYWIANIA'), ('amenorrhea', 'BRAK_MIESIACZKI')):
        if a.get(k): flags.append(f)

    bmr_m = bmr_mifflin(sex, kg, cm, age)
    bmr_k = bmr_katch(kg, a['body_fat_pct']) if a.get('body_fat_pct') else None
    bmr = bmr_k if (bmr_k and abs(bmr_k - bmr_m) / bmr_m > 0.10) else bmr_m
    bmr_source = 'katch_mcardle' if bmr is bmr_k else 'mifflin_st_jeor'

    if a.get('steps_per_day'):
        neat = min(1.85, max(1.15, 1.20 + 0.04 * (a['steps_per_day'] / 1000 - 4)))
    else:
        neat = NEAT[a['neat']]
    sessions = [('strength', a.get('strength_per_week', 0), a.get('strength_minutes', 0))]
    if a.get('cardio_per_week'):
        sessions.append((f"cardio_{a['cardio_intensity']}", a['cardio_per_week'], a['cardio_minutes']))
    train = training_kcal_per_day(kg, sessions)
    base = bmr * neat + train
    tdee = base * 1.10  # TEF 10 %

    goal, pace = a['goal'], a.get('pace') if a['goal'] in ('cut', 'bulk') else None
    adj = PACE[(goal, pace)]
    if 'CIAZA_KARMIENIE' in flags or 'BRAK_MIESIACZKI' in flags:
        adj = max(adj, 0.0); flags.append('DEFICYT_WYLACZONY')
    target = tdee * (1 + adj)
    floor = max(bmr * 1.10, MIN_KCAL[sex])
    if goal in ('cut', 'recomp') and target < floor:
        target = floor; flags.append('DEFICYT_OGRANICZONY')

    lo, hi = PROTEIN[goal]
    p_per_kg = hi if a.get('protein_pref') == 'high' else lo
    ref_kg = kg
    if goal == 'cut' and a.get('body_fat_pct', 0) > 30:
        ref_kg = a.get('target_weight_kg') or kg * (1 - a['body_fat_pct'] / 100) / 0.75  # ~LBM/0.75
    protein = p_per_kg * ref_kg
    fat = max(FAT_G_KG[goal] * kg, 0.20 * target / 9)
    carbs = max(0, (target - 4 * protein - 9 * fat) / 4)

    weekly_kg = (tdee - target) * 7 / 7700
    return dict(formulas_version=FORMULAS_VERSION, age=age, bmi=round(bmi, 1),
                bmr_mifflin=round(bmr_m), bmr_katch=round(bmr_k) if bmr_k else None, bmr_used=round(bmr), bmr_source=bmr_source,
                neat_multiplier=neat, training_kcal_day=round(train), tef=round(tdee - base),
                tdee=round(tdee), tdee_min=round(tdee * 0.93), tdee_max=round(tdee * 1.07),
                adjustment_pct=adj, target_kcal=round(target),
                macro=dict(P=round(protein), F=round(fat), C=round(carbs)),
                expected_weekly_change_kg=round(weekly_kg, 2), flags=flags)


CLIENT_HIDDEN_ON_ED = ('bmr_mifflin', 'bmr_katch', 'bmr_used', 'tdee', 'tdee_min', 'tdee_max', 'target_kcal',
                       'adjustment_pct', 'expected_weekly_change_kg', 'macro', 'training_kcal_day', 'tef')


def client_view(results):
    """Widok klienta: ukrywa liczby przy ZABURZENIA_ODZYWIANIA, nic przy MALOLETNI."""
    if 'MALOLETNI' in results['flags']:
        return dict(message='Wynik dostępny u trenera (wymagana zgoda opiekuna).', flags=results['flags'])
    if 'ZABURZENIA_ODZYWIANIA' in results['flags']:
        return {k: v for k, v in results.items() if k not in CLIENT_HIDDEN_ON_ED} | dict(message='Trener przygotuje plan.')
    return results


if __name__ == '__main__':
    T = date(2026, 9, 13)
    m = dict(sex='M', birth_date=date(1996, 9, 13), height_cm=180, weight_kg=80, neat='neat_1',
             strength_per_week=3, strength_minutes=60, goal='maintain')
    r = compute(m, T)
    assert r['bmr_mifflin'] == 1780, r['bmr_mifflin']
    assert r['training_kcal_day'] == 180, r['training_kcal_day']
    assert r['tdee'] == 2548, r['tdee']
    f = dict(sex='F', birth_date=date(2001, 9, 13), height_cm=165, weight_kg=60, neat='neat_1', goal='cut', pace='fast')
    r = compute(f, T)
    assert r['bmr_mifflin'] == 1345
    assert r['target_kcal'] >= 1480 and 'DEFICYT_OGRANICZONY' in r['flags'], r
    assert abs(bmr_katch(80, 20) - 1752) <= 1
    ed = compute(dict(f, eating_disorder=True), T)
    assert 'target_kcal' not in client_view(ed)
    minor = compute(dict(f, birth_date=date(2010, 1, 1)), T)
    assert 'tdee' not in client_view(minor)
    print('OK', compute(m, T))

"""Warstwa integracji kreatora dań z Dzik OS.

Buduje konfigurację silnika z pól formularza trenera i z faktów
sprawdzanych PO STRONIE SERWERA (instrukcja pakietu: `screening_status`
i `targets_reference` nie są niekontrolowaną deklaracją klienta):

* `screening_status` wynika z jawnych poświadczeń trenera o zakresie
  (dorosły, bez ciąży, bez diety leczniczej, bez leków glikemicznych
  przy ograniczeniu węglowodanów) — brak odpowiedzi = `unknown`;
* w trybie produkcyjnym cele pochodzą z AKTYWNEJ wersji planu diety
  klienta (`targets_reference` = id tej wersji), a granice dzienne
  z tolerancji podanej jawnie przez trenera;
* zapis menu = nowa wersja planu diety klienta ze śladem decyzji
  w tej samej transakcji (kontrakt Wiedzy); zamiana dania = podgląd
  bez mutacji, potem zatwierdzenie z kontrolą rewizji (409).

Bez modelu językowego; wartości wyłącznie z adaptera.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from ..dates import local_today
from ..models import (
    KulinariaReceptura,
    NutritionPlan,
    NutritionPlanVersion,
    new_id,
    now_iso,
)
from ..wiedza import slad as wiedza_slad
from . import adapter, dane, engine

OSIE = {
    "animal_policy": ("omnivore", "vegetarian", "pescetarian", "vegan"),
    "pattern": ("balanced", "mediterranean", "paleo_classic_v1"),
    "carb_policy": ("standard", "low_carb", "ketogenic"),
}
ZAKRES_POLA = ("adult", "no_pregnancy_or_breastfeeding", "no_medical_diet", "no_glucose_meds_or_diabetes")


class BladWejscia(ValueError):
    pass


class KonfliktRewizji(ValueError):
    pass


# --- konfiguracja -----------------------------------------------------------


def screening_z_poswiadczen(zakres: dict | None, carb_policy: str) -> str:
    """Bramka integracyjna, nie kwestionariusz kliniczny: `cleared` tylko
    gdy trener jawnie potwierdził każdy punkt zakresu; brak odpowiedzi →
    `unknown`; przeczenie → `needs_review`."""
    if not isinstance(zakres, dict) or any(not isinstance(zakres.get(k), bool) for k in ZAKRES_POLA):
        return "unknown"
    if not (zakres["adult"] and zakres["no_pregnancy_or_breastfeeding"] and zakres["no_medical_diet"]):
        return "needs_review"
    if carb_policy in ("low_carb", "ketogenic") and not zakres["no_glucose_meds_or_diabetes"]:
        return "needs_review"
    return "cleared"


def _cele_klienta(db: Session, client_id: str) -> tuple[dict | None, str | None]:
    plan = (db.query(NutritionPlan).filter_by(client_id=client_id, status="ACTIVE")
            .order_by(NutritionPlan.updated_at.desc()).first())
    if plan is None or not plan.current_version_no:
        return None, None
    v = db.query(NutritionPlanVersion).filter_by(plan_id=plan.id, version_no=plan.current_version_no).first()
    if v is None:
        return None, None
    c = json.loads(v.content_json)
    cele = {k: c.get(k) for k in ("kcal", "protein_g", "fat_g", "carbs_g")}
    if any(not isinstance(cele[k], (int, float)) or cele[k] <= 0 for k in cele):
        return None, v.id
    return cele, v.id


def zbuduj_konfiguracje(db: Session, body: dict, client_id: str | None) -> tuple[dict, dict]:
    """Konfiguracja silnika + metadane (skąd wzięły się cele i screening)."""
    tryb = body.get("tryb", "preview")
    if tryb not in ("preview", "production"):
        raise BladWejscia("tryb: preview albo production")
    for os_, dozw in OSIE.items():
        if body.get(os_) not in dozw:
            raise BladWejscia(f"{os_}: dozwolone {', '.join(dozw)}")
    dni = body.get("days", 7)
    meal_count = body.get("meal_count", 3)
    try:
        start = body.get("start_date") or local_today().isoformat()
        date.fromisoformat(start)
    except (TypeError, ValueError):
        raise BladWejscia("start_date: YYYY-MM-DD") from None
    sprzet = body.get("equipment")
    if not isinstance(sprzet, list) or not sprzet:
        sprzet = list(dane.SPRZET)
    screening = screening_z_poswiadczen(body.get("zakres"), body["carb_policy"])
    cfg: dict[str, Any] = {
        "mode": tryb, "days": dni, "meal_count": meal_count,
        "animal_policy": body["animal_policy"], "pattern": body["pattern"],
        "carb_policy": body["carb_policy"],
        "carb_limit_g": body.get("carb_limit_g"), "carb_basis": body.get("carb_basis"),
        "screening_status": screening, "start_date": start,
        "max_total_minutes": body.get("max_total_minutes", 30),
        "max_active_minutes": body.get("max_active_minutes", 20),
        "max_family_uses_per_week": body.get("max_family_uses_per_week", 2),
        "excluded_ingredient_ids": list(body.get("excluded_ingredient_ids") or []),
        "allergens": list(body.get("allergens") or []),
        "equipment": sprzet,
        "preferred_cuisines": list(body.get("preferred_cuisines") or []),
        "daily_bounds": {}, "required_nutrients": [], "targets_reference": None,
    }
    meta: dict[str, Any] = {"screening_status": screening, "targets_source": None, "cele_planu": None}
    if client_id:
        # Cele z aktywnego planu klienta przechodzą do nowej wersji także
        # w podglądzie (to cele trenera, nie wynik silnika) — zapis podglądu
        # nie może „wyzerować” celów planu.
        meta["cele_planu"] = _cele_klienta(db, client_id)[0]
    if tryb == "production":
        if not client_id:
            raise BladWejscia("tryb produkcyjny wymaga klienta (cele z jego planu diety)")
        cele, ref = _cele_klienta(db, client_id)
        if cele is None:
            raise BladWejscia("brak aktywnego planu diety klienta z kompletnymi celami (kcal, białko, "
                              "tłuszcz, węglowodany) — kreator nie wymyśla celów")
        tol = body.get("tolerance_pct") or {}
        if not all(isinstance(tol.get(k), (int, float)) and 0 < tol[k] <= 50 for k in ("kcal", "macro")):
            raise BladWejscia("tolerance_pct: {kcal, macro} w procentach (0–50) — jawne granice trenera")
        tk, tm = tol["kcal"] / 100, tol["macro"] / 100
        cfg["daily_bounds"] = {
            "energy_kcal": [round(cele["kcal"] * (1 - tk), 1), round(cele["kcal"] * (1 + tk), 1)],
            "protein_g": [round(cele["protein_g"] * (1 - tm), 1), round(cele["protein_g"] * (1 + tm), 1)],
            "fat_g": [round(cele["fat_g"] * (1 - tm), 1), round(cele["fat_g"] * (1 + tm), 1)],
            # Węglowodany planu interpretowane jako dostępne (bez błonnika) —
            # jawne założenie zapisane w metadanych.
            "carbs_available_g": [round(cele["carbs_g"] * (1 - tm), 1), round(cele["carbs_g"] * (1 + tm), 1)],
        }
        cfg["targets_reference"] = f"nutrition_plan_version:{ref}"
        meta["targets_source"] = {"version_id": ref, "targets": cele, "tolerance_pct": tol,
                                  "assumption": "carbs_g planu = węglowodany dostępne"}
    return cfg, meta


# --- generowanie ---------------------------------------------------------------------


def _etykieta_posilku(meal: dict, foods: dict) -> dict:
    skl = []
    for x in meal["ingredients"]:
        f = foods.get(x["food_id"], {})
        skl.append(f"{f.get('name', x['food_id'])} {round(x['grams'], 1):g} g ({x['state']})")
    return {"skladniki": skl, "kroki": list(meal["steps"])}


def wzbogac_wynik(res: dict, foods: dict) -> dict:
    """Etykiety po polsku, lista zakupów z nazwami produktów, oznaczenie szkiców."""
    out = dict(res)
    if res.get("plan"):
        plan = json.loads(json.dumps(res["plan"]))
        for d in plan["days"]:
            for m in d["meals"]:
                m["slot_label"] = dane.SLOTY_NAZWY.get(m["slot"], m["slot"])
                m.update(_etykieta_posilku(m, foods))
                m["draft"] = m["decision_trace"]["facts"].get("recipe_status") != "published"
        out["plan"] = plan
        out["shopping_list"] = [
            {**x, "name": foods.get(x["food_id"], {}).get("name", x["food_id"])}
            for x in engine.shopping_list(res["plan"])
        ]
    out["versions"] = dict(dane.WERSJE)
    return out


def generuj(db: Session, body: dict, client_id: str | None) -> dict:
    cfg, meta = zbuduj_konfiguracje(db, body, client_id)
    foods = adapter.produkty_dla_silnika()
    recs = adapter.receptury(db)
    res = engine.generate(cfg, recs, foods)
    res = wzbogac_wynik(res, foods)
    res["config"] = {k: v for k, v in cfg.items()}
    res["meta"] = meta
    res["coverage"] = engine.coverage(recs, foods, cfg) if res["status"] != "needs_input" else None
    return res


# --- zapis jako wersja planu diety ---------------------------------------------------


def tresc_wersji(res: dict, cfg: dict, meta: dict) -> dict:
    """`content_json` wersji planu: posiłki dzień po dniu; kcal/makro
    tylko w trybie produkcyjnym (podgląd nie wymyśla liczb)."""
    plan = res["plan"]
    posilki = []
    for d in plan["days"]:
        for i, m in enumerate(d["meals"]):
            posilki.append({
                "name": f"{d['date']} · {m['slot_label']}: {m['recipe_name']}",
                "description": "Składniki: " + "; ".join(m["skladniki"]) + ". Kroki: "
                               + " ".join(f"{n + 1}. {k}" for n, k in enumerate(m["kroki"])),
                "swaps": "",
                "day": d["date"], "slot": m["slot"], "recipe_id": m["recipe_id"],
                "recipe_revision": m["recipe_revision"], "portion_variant": m["portion_variant"],
                "factor": m["factor"], "family_id": m["family_id"], "draft": m["draft"],
                "trace_target": f"d{plan['days'].index(d)}:m{i}",
                "nutrition": m.get("nutrition"),
            })
    cele = (meta.get("targets_source") or {}).get("targets") or meta.get("cele_planu") or {}
    sekcje = [
        {"title": "Kreator dań — jak czytać ten plan",
         "body": ("Menu ułożone z całych receptur w zatwierdzonych porcjach (bez dokładania "
                  "składników pod makro). " + " ".join(plan["limitations"]))},
    ]
    if cfg["mode"] == "preview":
        sekcje.append({"title": "Podgląd kulinarny — bez wartości odżywczych",
                       "body": ("Ta wersja powstała w trybie podglądu: receptury są szkicami bez testu "
                                "kuchennego i bez zweryfikowanych wartości; posiłki nie mają policzonych "
                                "kalorii ani makro. Cele dzienne (jeśli są) pochodzą z poprzedniej wersji "
                                "planu i nie zostały sprawdzone względem tego menu.")})
    return {
        "kcal": int(cele["kcal"]) if cele else None,
        "protein_g": int(cele["protein_g"]) if cele else None,
        "fat_g": int(cele["fat_g"]) if cele else None,
        "carbs_g": int(cele["carbs_g"]) if cele else None,
        "sections": sekcje, "meals": posilki, "supplements": [],
        "kulinaria": {
            "engine_version": res["engine_version"], "plan_id": plan["id"], "mode": plan["mode"],
            "status": res["status"], "issues": res["issues"],
            "config": {k: v for k, v in cfg.items() if k != "screening_status"},
            "screening_status": cfg["screening_status"], "targets_reference": cfg["targets_reference"],
            "shopping_list": res.get("shopping_list", []), "versions": res["versions"],
            "carb_compliance_verified": plan["carb_compliance_verified"],
            "nutrition_scope": plan["nutrition_scope"],
        },
    }


def zapisz_slady(db: Session, *, owner_id: str, plan_id: str, plan_revision: int, tresc: dict) -> int:
    """Ślad wyboru każdego dania (kontrakt Wiedzy) w tej samej transakcji
    co wersja planu. Fakty: z decision_trace silnika + nazwa, rodzina,
    wariant, slot. Bez alergenów i bez wykluczeń w faktach."""
    teraz = now_iso()
    n = 0
    for m in tresc["meals"]:
        wiedza_slad.zapisz_slad(
            db, owner_id=owner_id, plan_kind="nutrition", plan_id=plan_id, plan_revision=plan_revision,
            target_type="meal", target_id=m["trace_target"], decision_origin="engine",
            rule_id="CURATED_VARIANT_SELECTION", rule_version="1.0",
            data_quality="sufficient",
            facts=[
                wiedza_slad.fakt("animal_policy", tresc["kulinaria"]["config"]["animal_policy"], None, teraz),
                wiedza_slad.fakt("pattern", tresc["kulinaria"]["config"]["pattern"], None, teraz),
                wiedza_slad.fakt("time_limit", tresc["kulinaria"]["config"]["max_total_minutes"], "minutes", teraz),
                wiedza_slad.fakt("recipe_status", "draft" if m["draft"] else "published", None, teraz),
                wiedza_slad.fakt("recipe_name", m["name"].split(": ", 1)[-1], None, teraz),
                wiedza_slad.fakt("family_id", m["family_id"], None, teraz),
                wiedza_slad.fakt("portion_variant", m["portion_variant"], None, teraz),
                wiedza_slad.fakt("slot", dane.SLOTY_NAZWY.get(m["slot"], m["slot"]), None, teraz),
            ],
            outcome_code="curated_variant", outcome_value=f"{m['recipe_id']}:{m['portion_variant']}",
            reason_note=None, article_ids=["k-meal", "k-portion"],
        )
        n += 1
    return n


# --- zamiana dania -------------------------------------------------------------------


def _plan_silnika_z_tresci(tresc: dict, recs_by_id: dict, foods: dict) -> tuple[dict, dict]:
    """Odtwarza plan silnika (do audytu) z treści wersji."""
    k = tresc["kulinaria"]
    cfg = dict(k["config"])
    cfg["screening_status"] = k["screening_status"]
    cfg["targets_reference"] = k["targets_reference"]
    dni: dict[str, list] = {}
    for m in tresc["meals"]:
        dni.setdefault(m["day"], []).append(m)
    days = []
    for data_dnia, posilki in dni.items():
        meals = []
        for m in posilki:
            r = recs_by_id[m["recipe_id"]]
            meals.append({
                "slot": m["slot"], "recipe_id": m["recipe_id"], "recipe_revision": m["recipe_revision"],
                "recipe_name": r["name"], "family_id": r["family_id"], "portion_variant": m["portion_variant"],
                "factor": m["factor"],
                "ingredients": [{**x, "grams": x["grams"] * m["factor"]} for x in r["ingredients"]],
                "steps": r["steps"], "total_minutes": r["total_minutes"], "nutrition": m.get("nutrition"),
            })
        days.append({"date": data_dnia, "meals": meals, "nutrition": None})
    plan = {"id": k["plan_id"], "revision": 1, "mode": k["mode"], "days": days,
            "carb_compliance_verified": k["carb_compliance_verified"],
            "nutrition_scope": k["nutrition_scope"], "limitations": []}
    return plan, cfg


def podglad_zamiany(db: Session, tresc: dict, *, meal_index: int, recipe_id: str,
                    variant_id: str) -> dict:
    """Różnice i wynik ponownej kontroli dnia — bez mutacji planu."""
    foods = adapter.produkty_dla_silnika()
    recs = adapter.receptury(db)
    by_id = {r["id"]: r for r in recs}
    if meal_index < 0 or meal_index >= len(tresc["meals"]):
        raise BladWejscia("meal_index poza zakresem")
    stary = tresc["meals"][meal_index]
    nowy_r = by_id.get(recipe_id)
    if nowy_r is None:
        raise BladWejscia("nieznana receptura")
    wariant = next((v for v in nowy_r["portion_variants"] if v["id"] == variant_id), None)
    if wariant is None:
        raise BladWejscia("nieznany wariant porcji")
    plan, cfg = _plan_silnika_z_tresci(tresc, by_id, foods)
    # podmiana w kopii planu
    dzien_idx = [d["date"] for d in plan["days"]].index(stary["day"])
    posilki_dnia = [m for m in tresc["meals"] if m["day"] == stary["day"]]
    pozycja = posilki_dnia.index(stary)
    meal = plan["days"][dzien_idx]["meals"][pozycja]
    ok, why = engine.eligible(nowy_r, cfg, foods)
    problemy = [] if ok else [f"receptura odpada przez: {why}"]
    if stary["slot"] not in nowy_r["meal_slots"]:
        problemy.append(f"receptura nie jest przeznaczona na {dane.SLOTY_NAZWY.get(stary['slot'], stary['slot'])}")
    if cfg["mode"] == "production" and not wariant["validated"]:
        problemy.append("wariant porcji nie jest zatwierdzony")
    nowe_wartosci = None
    if cfg["mode"] == "production":
        try:
            nowe_wartosci = engine.recipe_nutrition(nowy_r, foods, wariant["factor"],
                                                    set(cfg["daily_bounds"]) | engine.REQUIRED_MACROS)
        except engine.InputError as e:
            problemy.append(f"brak zweryfikowanych wartości: {e}")
    nowy_meal = {
        "slot": stary["slot"], "recipe_id": nowy_r["id"], "recipe_revision": nowy_r["revision"],
        "recipe_status": nowy_r["status"],
        "recipe_name": nowy_r["name"], "family_id": nowy_r["family_id"], "portion_variant": wariant["id"],
        "factor": wariant["factor"],
        "ingredients": [{**x, "grams": x["grams"] * wariant["factor"]} for x in nowy_r["ingredients"]],
        "steps": nowy_r["steps"], "total_minutes": nowy_r["total_minutes"], "nutrition": nowe_wartosci,
    }
    plan["days"][dzien_idx]["meals"][pozycja] = nowy_meal
    if cfg["mode"] == "production":
        suma: dict[str, float] = {}
        for m in plan["days"][dzien_idx]["meals"]:
            for kk, v in (m.get("nutrition") or {}).items():
                suma[kk] = suma.get(kk, 0.0) + v
        plan["days"][dzien_idx]["nutrition"] = suma
        for kk, (lo, hi) in cfg["daily_bounds"].items():
            if not lo - 1e-8 <= suma.get(kk, 0.0) <= hi + 1e-8:
                problemy.append(f"dzień poza granicą {kk}: {round(suma.get(kk, 0.0), 1)} ∉ [{lo}, {hi}]")
    bledy_audytu = [] if problemy else engine.audit_plan(plan, cfg, recs, foods)
    problemy.extend(f"audyt: {b}" for b in bledy_audytu)
    return {
        "ok": not problemy, "problemy": problemy,
        "przed": {"recipe_id": stary["recipe_id"], "name": stary["name"], "portion_variant": stary["portion_variant"]},
        "po": {**nowy_meal, **_etykieta_posilku(nowy_meal, foods), "slot_label": dane.SLOTY_NAZWY.get(meal["slot"], meal["slot"])},
        "dzien": plan["days"][dzien_idx]["date"], "meal_index": meal_index,
        "nutrition_day": plan["days"][dzien_idx]["nutrition"],
    }


def zastosuj_zamiane(tresc: dict, podglad: dict) -> dict:
    """Nowa treść wersji po zatwierdzonej zamianie (stare rewizje zostają)."""
    nowa = json.loads(json.dumps(tresc))
    m = nowa["meals"][podglad["meal_index"]]
    po = podglad["po"]
    m.update({
        "name": f"{m['day']} · {po['slot_label']}: {po['recipe_name']}",
        "description": "Składniki: " + "; ".join(po["skladniki"]) + ". Kroki: "
                       + " ".join(f"{n + 1}. {k}" for n, k in enumerate(po["kroki"])),
        "recipe_id": po["recipe_id"], "recipe_revision": po["recipe_revision"],
        "portion_variant": po["portion_variant"], "factor": po["factor"], "family_id": po["family_id"],
        "nutrition": po.get("nutrition"), "draft": po.get("recipe_status") != "published",
    })
    nowa["kulinaria"]["shopping_list"] = []
    return nowa


# --- publikacja receptur --------------------------------------------------------------


def publikuj_recepture(db: Session, *, coach_id: str, recipe_id: str, poswiadczenia: dict,
                       expires_on: str, validated_variants: list[str]) -> KulinariaReceptura:
    """Publikacja = decyzja trenera z jawnymi poświadczeniami. Wymaga
    kompletnego mapowania wartości wszystkich składników."""
    r = adapter.receptura(db, recipe_id)
    if r is None:
        raise KeyError(recipe_id)
    powody = []
    foods = adapter.produkty_dla_silnika()
    for line in r["ingredients"]:
        f = foods.get(line["food_id"])
        if f is None or not f["nutrition_verified"]:
            powody.append(f"składnik {line['food_id']} bez zweryfikowanych wartości")
    for k, opis in (("kitchen", "brak poświadczenia testu kuchennego"),
                    ("dietitian", "brak poświadczenia przeglądu dietetycznego"),
                    ("allergens_checked", "brak poświadczenia kontroli alergenów i składu")):
        if not poswiadczenia.get(k):
            powody.append(opis)
    try:
        termin = date.fromisoformat(expires_on)
        if termin <= local_today():
            powody.append("termin ważności przeglądu musi być w przyszłości")
    except (TypeError, ValueError):
        powody.append("expires_on: YYYY-MM-DD")
    znane = {v["id"] for v in r["portion_variants"]}
    if not validated_variants or not set(validated_variants) <= znane:
        powody.append("wskaż zatwierdzone warianty porcji z listy receptury")
    if powody:
        raise BladWejscia("; ".join(powody))
    row = db.query(KulinariaReceptura).filter_by(recipe_id=recipe_id, revision=r["revision"]).first()
    if row is None:
        row = KulinariaReceptura(id=new_id("KRC"), recipe_id=recipe_id, revision=r["revision"], updated_by=coach_id)
        db.add(row)
    row.status = "published"
    row.review_json = json.dumps({"kitchen": True, "dietitian": True, "reviewer_id": coach_id,
                                  "expires_on": expires_on, "allergens_checked": True,
                                  "reviewed_at": local_today().isoformat()})
    row.validated_variants_json = json.dumps(sorted(set(validated_variants)))
    row.updated_by = coach_id
    row.updated_at = now_iso()
    db.flush()
    return row


def wycofaj_recepture(db: Session, *, coach_id: str, recipe_id: str) -> KulinariaReceptura:
    r = adapter.receptura(db, recipe_id)
    if r is None:
        raise KeyError(recipe_id)
    row = db.query(KulinariaReceptura).filter_by(recipe_id=recipe_id, revision=r["revision"]).first()
    if row is None:
        row = KulinariaReceptura(id=new_id("KRC"), recipe_id=recipe_id, revision=r["revision"], updated_by=coach_id)
        db.add(row)
    row.status = "retired"
    row.updated_by = coach_id
    row.updated_at = now_iso()
    db.flush()
    return row


# --- porównanie starego i nowego generatora ------------------------------------------


def porownanie(stary: dict, nowy: dict) -> dict:
    """Deterministyczne metryki na tych samych wejściach: rozpoznawalne
    dania (nazwane receptury z instrukcją) vs zestawy produktów; bez
    ocen smaku — te wymagają testu kuchennego."""
    stare_posilki = [m for d in stary.get("days", []) for m in d.get("meals", [])]
    nowe_posilki = [m for d in (nowy.get("plan") or {}).get("days", []) for m in d.get("meals", [])]
    return {
        "stary": {
            "posilki": len(stare_posilki),
            "nazwane_dania_z_instrukcja": 0,
            "srednio_skladnikow": round(sum(len(m.get("items", [])) for m in stare_posilki)
                                        / len(stare_posilki), 1) if stare_posilki else None,
            "ostrzezenia": len(stary.get("warnings", [])),
            "uwaga": "posiłki = zestawy produktów dopasowane do makro (sugestia przyrządzenia, bez receptury)",
        },
        "nowy": {
            "posilki": len(nowe_posilki),
            "nazwane_dania_z_instrukcja": sum(1 for m in nowe_posilki if m.get("steps")),
            "rodziny": len({m["family_id"] for m in nowe_posilki}),
            "srednio_skladnikow": round(sum(len(m["ingredients"]) for m in nowe_posilki)
                                        / len(nowe_posilki), 1) if nowe_posilki else None,
            "status": nowy.get("status"),
            "uwaga": "posiłki = całe receptury w zatwierdzonych porcjach; makro tylko w trybie produkcyjnym",
        },
        "nie_mierzono": ["smak", "wykonalność w kuchni", "zgodność ilościowa po ugotowaniu"],
    }

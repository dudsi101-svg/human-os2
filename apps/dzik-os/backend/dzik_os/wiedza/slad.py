"""Ślad decyzji (DecisionTrace): zapis przez właścicieli decyzji i odczyt.

Reguła nadrzędna (plik 03, „Zapis uzasadnienia w generatorze”): ślad
powstaje w TEJ SAMEJ transakcji co nowa wersja planu. Nie wolno zapisać
uzasadnienia dla niezapisanej decyzji ani odtwarzać go po fakcie z
obecnych danych. Ślad przechowuje tylko fakty potrzebne do wyjaśnienia,
z jednostką i czasem obserwacji; surowy wywiad zdrowotny nie trafia tu
nigdy.

Kto zapisuje (P0):
* konfigurator 28 dni (`decision_origin=engine`): częstotliwość
  (H_LAYOUT) i dawka każdego ćwiczenia (H_VOLUME);
* trener przy nowej wersji planu treningowego (`professional`,
  oryginalny powód wersji jako `reason_note`);
* trener przy wersji planu diety (`professional`): cel energetyczny
  i makroskładniki z treści wersji.
"""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator
from sqlalchemy.orm import Session

from ..models import WiedzaSlad, new_id, now_iso
from . import dane

#: Jednostki faktów, które renderer umie nazwać. Nieznana jednostka nie
#: jest przyjmowana po cichu (kontrola semantyczna nr 8 z pliku 07).
JEDNOSTKI: dict[str | None, str] = {
    None: "",
    "sets": "serie",
    "reps": "powtórzeń",
    "seconds": "s",
    "sessions_per_week": "sesje w tygodniu",
    "kcal/day": "kcal dziennie",
    "g/day": "g dziennie",
    "kg": "kg",
    "weeks": "tyg.",
    "minutes": "min",
    "hours": "h",
}

#: Wersja reguł konfiguratora zapisywana w śladach (z pakietu K1).
WERSJA_REGUL_KONFIGURATORA = "1.0"

#: Kody uwag silnika, które zmieniają dawkę — trafiają do faktu
#: `adjustments`, żeby wyjaśnienie mówiło o rzeczywistej korekcie.
KOREKTY_DAWKI = (
    "LOW_RECOVERY_ADJUSTMENT", "RETURN_AFTER_BREAK", "TIME_FIT_SET_REMOVED",
    "TIME_FIT_DROPPED", "PROVISIONAL_LOADS", "MISSING_VOLUME_HISTORY",
    "PRIORITY_SHIFT", "BEGINNER_HIGH_FREQUENCY", "ONE_DAY_COMPROMISE",
)


def _walidator() -> Draft202012Validator:
    return Draft202012Validator(dane.schematy()["decision_trace"])


def fakt(key: str, value: Any, unit: str | None = None, observed_at: str | None = None) -> dict:
    return {"key": key, "value": value, "unit": unit, "observed_at": observed_at or now_iso()}


def do_schematu(row: WiedzaSlad) -> dict:
    """Obiekt zgodny ze schematem `decision_trace` (kontrakt pakietu)."""
    return {
        "id": row.id, "owner_id": row.owner_id, "plan_id": row.plan_id,
        "plan_revision": row.plan_revision, "target_type": row.target_type,
        "target_id": row.target_id, "decision_origin": row.decision_origin,
        "rule_id": row.rule_id, "rule_version": row.rule_version,
        "data_quality": row.data_quality, "facts": json.loads(row.facts_json),
        "outcome_code": row.outcome_code, "outcome_value": json.loads(row.outcome_value_json),
        "reason_note": row.reason_note, "created_at": row.created_at,
        "article_ids": json.loads(row.article_ids_json),
    }


def waliduj(obj: dict) -> list[str]:
    return sorted(f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
                  for e in _walidator().iter_errors(obj))


def zapisz_slad(
    db: Session,
    *,
    owner_id: str,
    plan_kind: str,
    plan_id: str,
    plan_revision: int,
    target_type: str,
    target_id: str,
    decision_origin: str,
    rule_id: str | None,
    rule_version: str | None,
    data_quality: str,
    facts: list[dict],
    outcome_code: str,
    outcome_value: Any,
    reason_note: str | None,
    article_ids: list[str],
) -> WiedzaSlad:
    """Dodaje ślad do bieżącej transakcji (bez commit — commituje
    właściciel decyzji razem z wersją planu). Kształt jest walidowany
    schematem Draft 2020-12; zły ślad to błąd programisty, nie dane."""
    row = WiedzaSlad(
        id=new_id("WSL"), owner_id=owner_id, plan_kind=plan_kind, plan_id=plan_id,
        plan_revision=int(plan_revision), target_type=target_type, target_id=target_id,
        decision_origin=decision_origin, rule_id=rule_id, rule_version=rule_version,
        data_quality=data_quality, facts_json=json.dumps(facts, ensure_ascii=False),
        outcome_code=outcome_code,
        outcome_value_json=json.dumps(outcome_value, ensure_ascii=False),
        reason_note=reason_note, article_ids_json=json.dumps(article_ids, ensure_ascii=False),
        created_at=now_iso(),
    )
    bledy = waliduj(do_schematu(row))
    if bledy:
        raise ValueError("ślad decyzji niezgodny ze schematem: " + "; ".join(bledy))
    if len({f["key"] for f in facts}) != len(facts):
        raise ValueError("ślad decyzji: powtórzone klucze faktów")
    db.add(row)
    return row


def znajdz(db: Session, *, owner_id: str, plan_kind: str, plan_id: str, plan_revision: int,
           target_type: str, target_id: str) -> WiedzaSlad | None:
    return (
        db.query(WiedzaSlad)
        .filter_by(owner_id=owner_id, plan_kind=plan_kind, plan_id=plan_id,
                   plan_revision=int(plan_revision), target_type=target_type,
                   target_id=target_id)
        .order_by(WiedzaSlad.created_at.desc())
        .first()
    )


def historia(db: Session, *, owner_id: str, plan_kind: str, plan_id: str) -> list[WiedzaSlad]:
    return (
        db.query(WiedzaSlad)
        .filter_by(owner_id=owner_id, plan_kind=plan_kind, plan_id=plan_id)
        .order_by(WiedzaSlad.plan_revision.desc(), WiedzaSlad.created_at.desc(),
                  WiedzaSlad.target_type.asc(), WiedzaSlad.target_id.asc())
        .all()
    )


# --- właściciele decyzji ----------------------------------------------------


def slady_konfiguratora(db: Session, *, owner_id: str, plan_id: str, plan_revision: int,
                        odpowiedz: dict, wejscie: dict) -> int:
    """Ślady z wyniku silnika konfiguratora (statusy ready/limited).
    Cele: `training_frequency` → „plan”; `exercise_prescription` →
    `d{dzień}:e{ćwiczenie}` w kolejności dni z `na_plan_dzik` (pierwsza
    sesja każdej jednostki). Fakty pochodzą z wejścia BEZ bloku
    zdrowotnego i z wyniku silnika."""
    plan = odpowiedz["plan"]
    teraz = now_iso()
    kody = {i["code"] for i in odpowiedz.get("issues", [])}
    korekty = sorted(k for k in KOREKTY_DAWKI if k in kody)
    strength = [d for d in plan["days"] if d["kind"] == "strength"]
    kolejnosc = list(dict.fromkeys(d["template_id"] for d in strength))
    n = 0
    zapisz_slad(
        db, owner_id=owner_id, plan_kind="training", plan_id=plan_id,
        plan_revision=plan_revision, target_type="training_frequency", target_id="plan",
        decision_origin="engine", rule_id="H_LAYOUT", rule_version=WERSJA_REGUL_KONFIGURATORA,
        data_quality="sufficient",
        facts=[
            fakt("days_per_week", int(wejscie["days_per_week"]), "sessions_per_week", teraz),
            fakt("level", str(wejscie["level"]), None, teraz),
            fakt("commitment", str(wejscie["commitment"]), None, teraz),
            fakt("layout_id", "/".join(kolejnosc), None, teraz),
            fakt("session_count", len(strength), None, teraz),
            fakt("adjustments", korekty, None, teraz),
        ],
        outcome_code="layout_selected", outcome_value="/".join(kolejnosc), reason_note=None,
        article_ids=["k-frequency"],
    )
    n += 1
    for di, tid in enumerate(kolejnosc):
        sesja = next(d for d in strength if d["template_id"] == tid)
        for ei, r in enumerate(sesja["exercise_prescriptions"]):
            rir = []
            for d in strength:
                if d["template_id"] == tid and d["exercise_prescriptions"]:
                    while len(rir) < d["week"]:
                        rir.append(d["exercise_prescriptions"][ei]["rir"]
                                   if ei < len(d["exercise_prescriptions"]) else r["rir"])
            zapisz_slad(
                db, owner_id=owner_id, plan_kind="training", plan_id=plan_id,
                plan_revision=plan_revision, target_type="exercise_prescription",
                target_id=f"d{di}:e{ei}", decision_origin="engine", rule_id="H_VOLUME",
                rule_version=WERSJA_REGUL_KONFIGURATORA, data_quality="sufficient",
                facts=[
                    fakt("exercise_id", r["exercise_id"], None, teraz),
                    fakt("sets", int(r["sets"]), "sets", teraz),
                    fakt("reps_min", int(r["reps_min"]), "reps", teraz),
                    fakt("reps_max", int(r["reps_max"]), "reps", teraz),
                    fakt("rir_by_week", rir, None, teraz),
                    fakt("rest_seconds", int(r["rest_seconds"]), "seconds", teraz),
                    fakt("level", str(wejscie["level"]), None, teraz),
                    fakt("commitment", str(wejscie["commitment"]), None, teraz),
                    fakt("adjustments", korekty, None, teraz),
                ],
                outcome_code="prescription", outcome_value=int(r["sets"]), reason_note=None,
                article_ids=["k-sets", "k-rir", "k-rest", f"ex-{r['exercise_id']}"],
            )
            n += 1
    return n


def slad_wersji_trenera(db: Session, *, owner_id: str, plan_id: str, plan_revision: int,
                        reason: str) -> WiedzaSlad:
    """Decyzja trenera = oryginalna notatka, bez dopisywania powodu
    algorytmicznego (plik 03, `decision_origin=professional`)."""
    return zapisz_slad(
        db, owner_id=owner_id, plan_kind="training", plan_id=plan_id,
        plan_revision=plan_revision, target_type="plan_change", target_id="plan",
        decision_origin="professional", rule_id=None, rule_version=None,
        data_quality="sufficient", facts=[], outcome_code="professional_note",
        outcome_value=f"v{plan_revision}", reason_note=reason, article_ids=[],
    )


def slady_diety_trenera(db: Session, *, owner_id: str, plan_id: str, plan_revision: int,
                        content: dict, reason: str) -> int:
    """Cel energetyczny i makro ustalone przez trenera w wersji diety.
    Wartość pochodzi z treści wersji; Wiedza niczego nie przelicza."""
    teraz = now_iso()
    n = 0
    kcal = content.get("kcal")
    if isinstance(kcal, (int, float)) and kcal > 0:
        zapisz_slad(
            db, owner_id=owner_id, plan_kind="nutrition", plan_id=plan_id,
            plan_revision=plan_revision, target_type="energy_target", target_id="plan",
            decision_origin="professional", rule_id=None, rule_version=None,
            data_quality="sufficient", facts=[fakt("kcal", kcal, "kcal/day", teraz)],
            outcome_code="professional_note", outcome_value=kcal, reason_note=reason,
            article_ids=["k-energy"],
        )
        n += 1
    makro = [(k, content.get(k)) for k in ("protein_g", "fat_g", "carbs_g")]
    makro = [(k, v) for k, v in makro if isinstance(v, (int, float)) and v > 0]
    if makro:
        zapisz_slad(
            db, owner_id=owner_id, plan_kind="nutrition", plan_id=plan_id,
            plan_revision=plan_revision, target_type="macro_target", target_id="plan",
            decision_origin="professional", rule_id=None, rule_version=None,
            data_quality="sufficient", facts=[fakt(k, v, "g/day", teraz) for k, v in makro],
            outcome_code="professional_note", outcome_value=None, reason_note=reason,
            article_ids=["k-macros"],
        )
        n += 1
    return n

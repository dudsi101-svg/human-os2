"""Zakładka Monitoring / Postępy (0.66.0, spec `docs/monitoring-tab/`):
trzy osie postępu — Forma (rekordy, e1RM, tonaż), Konsekwencja (frekwencja,
seria tygodni, dieta), Sylwetka (waga jako średnia, obwody, zdjęcia) —
oraz lista klientów z sygnałami dla trenera.

Zasady: cały moduł za flagą `monitoring_tab_enabled` (404 przy wyłączonej);
relacja trener–klient i zgody sprawdzane przy każdym żądaniu
(`resolve_client_access`); dane wrażliwe filtrowane PO STRONIE SERWERA —
klient z flagą zdrowotną (`hidden_for_client` ostatniego szacunku
kalorycznego, pytanie `zk_zaburzenia`) nie dostaje żadnych danych wagowych
ani obwodowych (`/body` = 404, `summary` bez pola `weight`); trener widzi
pełne dane. Porównania tylko z własną historią — żadnych rankingów.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import aggregates
from ..authz import (
    DOMAIN_HEALTH,
    DOMAIN_NUTRITION,
    DOMAIN_PHOTOS,
    DOMAIN_TRAINING,
    active_roles,
    resolve_client_access,
)
from ..config import settings
from ..dates import local_today, parse_iso_date
from ..db import get_db
from ..models import (
    CoachClientRelationship,
    DailyNutritionLog,
    DietAssigned,
    ExerciseRecord,
    Measurement,
    NutritionPlan,
    Observation,
    ProgressPhoto,
    ScheduleItem,
    TrainingPlan,
    TrainingPlanVersion,
    TrainingWeekAggregate,
    User,
    WorkoutSession,
)
from ..postepy import rekordy as R
from ..postepy import serwis
from ..postepy import waga as W
from ..security import current_user, require_role
from ..wywiad import zapotrzebowanie_serwis

router = APIRouter(prefix="/api/monitoring", tags=["postepy"])

TYGODNI_TRENING = 12
DNI_WSTEGI = 30
DNI_ARCHIWUM = 90
DNI_E1RM_WYKRES = 183
DNI_WAGI = 90
TYGODNI_FREKWENCJI = 8
DNI_DIETY = 28

# Sygnały trenera (§7.1) — progi konfigurowalne parametrami zapytania.
PROGI_DOMYSLNE = {"dni_bez_treningu": 10, "frekwencja_pct": 50, "dni_bez_wazenia": 14,
                  "spadek_tonazu_pct": 25, "trend_wzrost_kg": 0.2, "dni_trendu": 21, "dni_rekordu": 7}


def wymagaj_modulu() -> None:
    if not settings.monitoring_tab_enabled:
        raise HTTPException(status_code=404, detail="Zakładka Postępy jest wyłączona")


def _podmiot(db: Session, user: User, client_id: str | None, *, domain: str = DOMAIN_TRAINING) -> tuple[str, bool]:
    """(client_id, czy_widok_klienta). Klient bez parametru = on sam; trener
    podaje `client_id` i przechodzi przez relację + zgody (404 dla obcego)."""
    roles = active_roles(db, user.id)
    if client_id is None or client_id == user.id:
        if "CLIENT" not in roles:
            raise HTTPException(status_code=422, detail="Trener wskazuje klienta parametrem client_id")
        return user.id, True
    resolve_client_access(db, user, client_id, domain=domain)
    return client_id, "CLIENT" in roles and client_id == user.id


def _flaga_zdrowotna(db: Session, client_id: str) -> bool:
    est = zapotrzebowanie_serwis.ostatni(db, client_id)
    return bool(est is not None and est.hidden_for_client)


# --- pomocnicze: agregaty i tygodnie -------------------------------------------------

def _agregaty(db: Session, client_id: str, tygodni: int, today: date) -> dict[date, TrainingWeekAggregate]:
    od = serwis.poniedzialek(today) - timedelta(weeks=tygodni - 1)
    rows = (db.query(TrainingWeekAggregate)
            .filter(TrainingWeekAggregate.client_id == client_id, TrainingWeekAggregate.week_start >= od.isoformat())
            .all())
    return {parse_iso_date(r.week_start): r for r in rows}


def _tydzien_out(w: date, agg: TrainingWeekAggregate | None, planned: int) -> dict:
    return {"week_start": w.isoformat(), "sessions": agg.sessions_count if agg else 0,
            "planned": agg.planned_count if agg else planned,
            "tonnage_kg": agg.tonnage_kg if agg else 0.0,
            "sets_by_group": json.loads(agg.sets_by_group_json) if agg else {},
            "days": json.loads(agg.session_days_json) if agg else []}


def _seria_tygodni(tygodnie: list[dict], today: date) -> tuple[int, int]:
    """(aktualna seria, najdłuższa) tygodni z wykonanym planem (sesje ≥ zaplanowane > 0).
    Bieżący tydzień liczy się, gdy plan już wykonany; inaczej seria liczona od poprzedniego."""
    biezacy = serwis.poniedzialek(today).isoformat()
    ok = {t["week_start"]: (t["planned"] > 0 and t["sessions"] >= t["planned"]) for t in tygodnie}
    kolejnosc = sorted(ok)
    najdluzsza = biezaca = 0
    for w in kolejnosc:
        biezaca = biezaca + 1 if ok[w] else 0
        najdluzsza = max(najdluzsza, biezaca)
    aktualna = 0
    for w in reversed(kolejnosc):
        if w == biezacy and not ok[w]:
            continue  # trwający tydzień nie przerywa serii
        if ok[w]:
            aktualna += 1
        else:
            break
    return aktualna, najdluzsza


def _tygodnie(db: Session, client_id: str, tygodni: int, today: date) -> list[dict]:
    aggs = _agregaty(db, client_id, tygodni, today)
    items = (db.query(ScheduleItem).filter(ScheduleItem.client_id == client_id, ScheduleItem.category == "TRENING",
                                          ScheduleItem.status == "ACTIVE").all())
    start = serwis.poniedzialek(today) - timedelta(weeks=tygodni - 1)
    out = []
    for i in range(tygodni):
        w = start + timedelta(weeks=i)
        out.append(_tydzien_out(w, aggs.get(w), serwis._zaplanowane_z_elementow(items, w)))
    return out


# --- waga ------------------------------------------------------------------------------

def _punkty_wagi(db: Session, client_id: str, dni: int, today: date) -> list[W.Punkt]:
    od = (today - timedelta(days=dni - 1)).isoformat()
    rows = (db.query(Measurement.measured_at, Measurement.value, Measurement.unit)
            .filter(Measurement.client_id == client_id, Measurement.kind == "weight", Measurement.measured_at >= od)
            .order_by(Measurement.measured_at).all())
    return W.pomiary([(m[:10], v if (u or "kg").lower() == "kg" else R.normalizuj_ciezar(v, u)) for m, v, u in rows])


def _trend_out(punkty: list[W.Punkt], today: date) -> dict:
    trend = W.trend_kg_na_tydzien(punkty, today=today)
    return {"kg_per_week": trend, "average": W.biezaca_srednia(punkty),
            "message": None if trend is not None else (W.KOMUNIKAT_KAFELKA if len(punkty) < W.MIN_POMIAROW_W_OKNIE else W.KOMUNIKAT_TRENDU),
            "measurements": len(punkty)}


# --- dieta -------------------------------------------------------------------------------

def _dieta_aktywna(db: Session, client_id: str) -> bool:
    if db.query(NutritionPlan.id).filter_by(client_id=client_id, status="ACTIVE").first():
        return True
    return db.query(DietAssigned.id).filter_by(client_id=client_id, status="ACTIVE").first() is not None


def _realizacja_diety(db: Session, client_id: str, today: date) -> dict | None:
    if not _dieta_aktywna(db, client_id):
        return None
    od = (today - timedelta(days=DNI_DIETY - 1)).isoformat()
    dni = (db.query(func.count(DailyNutritionLog.id))
           .filter(DailyNutritionLog.client_id == client_id, DailyNutritionLog.logged_on >= od,
                   DailyNutritionLog.kcal.isnot(None)).scalar() or 0)
    return {"days_logged": int(dni), "days": DNI_DIETY, "pct": round(100 * int(dni) / DNI_DIETY)}


# --- rekordy -----------------------------------------------------------------------------

def _rekord_out(r: ExerciseRecord) -> dict:
    return {"id": r.id, "exercise_key": r.exercise_key, "exercise_name": r.exercise_name,
            "record_type": r.record_type, "value": r.value, "secondary_value": r.secondary_value,
            "achieved_on": r.achieved_on, "previous_value": r.previous_value,
            "delta": round(r.value - r.previous_value, 1) if r.previous_value is not None else None,
            "equaled_on": r.equaled_on, "superseded_at": r.superseded_at, "estimated": r.record_type == "E1RM"}


def _rekordy_klienta(db: Session, client_id: str, *, today: date, historia: bool = False) -> dict:
    rows = (db.query(ExerciseRecord).filter(ExerciseRecord.client_id == client_id)
            .order_by(ExerciseRecord.achieved_on.desc()).all())
    aktualne = [r for r in rows if r.superseded_at is None]
    od_wstegi = (today - timedelta(days=DNI_WSTEGI)).isoformat()
    wstega = []
    for r in aktualne:
        if r.achieved_on >= od_wstegi and r.record_type in ("WEIGHT", "E1RM", "REPS_AT_WEIGHT"):
            o = _rekord_out(r)
            poprzedni = next((p for p in rows if p.exercise_key == r.exercise_key and p.record_type == r.record_type
                              and p.secondary_value == r.secondary_value and p.superseded_at == r.achieved_on), None)
            o["days_since_previous"] = ((parse_iso_date(r.achieved_on) - parse_iso_date(poprzedni.achieved_on)).days
                                        if poprzedni else None)
            wstega.append(o)
    wstega = wstega[:5]
    # Ostatnie wykonanie i mikro-wykres e1RM (6 miesięcy) z serii — jedno zapytanie.
    serie = serwis.serie_klienta(db, client_id)
    nazwy = serwis.nazwy_cwiczen(db, client_id)
    ostatnie: dict[str, str] = {}
    e1rm_dni: dict[str, dict[str, float]] = defaultdict(dict)
    od_wykresu = (today - timedelta(days=DNI_E1RM_WYKRES)).isoformat()
    for s in serie:
        ostatnie[s.exercise_key] = max(ostatnie.get(s.exercise_key, ""), s.performed_on)
        if s.liczy_sie and s.weight_kg > 0 and s.reps <= R.E1RM_MAX_REPS and s.performed_on >= od_wykresu:
            d = e1rm_dni[s.exercise_key]
            d[s.performed_on] = max(d.get(s.performed_on, 0.0), R.epley_e1rm(s.weight_kg, s.reps))
    per_cw: dict[str, dict[str, ExerciseRecord]] = defaultdict(dict)
    for r in aktualne:
        if r.record_type in ("WEIGHT", "E1RM", "SET_VOLUME", "SESSION_VOLUME") and r.record_type not in per_cw[r.exercise_key]:
            per_cw[r.exercise_key][r.record_type] = r
    cwiczenia, archiwum = [], []
    prog_archiwum = (today - timedelta(days=DNI_ARCHIWUM)).isoformat()
    for klucz, last in sorted(ostatnie.items(), key=lambda kv: kv[1], reverse=True):
        cur = per_cw.get(klucz, {})
        # Klucz `max_weight` (nie `weight`): „weight” w API Postępów oznacza wyłącznie masę
        # ciała i jest filtrowane dla klienta z flagą zdrowotną (§10.1).
        poz = {"exercise_key": klucz, "exercise_name": nazwy.get(klucz, klucz), "last_performed_on": last,
               "max_weight": _rekord_out(cur["WEIGHT"]) if "WEIGHT" in cur else None,
               "e1rm": _rekord_out(cur["E1RM"]) if "E1RM" in cur else None,
               "set_volume": _rekord_out(cur["SET_VOLUME"]) if "SET_VOLUME" in cur else None,
               "session_volume": _rekord_out(cur["SESSION_VOLUME"]) if "SESSION_VOLUME" in cur else None,
               "e1rm_series": [{"date": d, "value": v} for d, v in sorted(e1rm_dni.get(klucz, {}).items())]}
        if historia:
            poz["history"] = [_rekord_out(r) for r in rows if r.exercise_key == klucz]
        (archiwum if last < prog_archiwum else cwiczenia).append(poz)
    return {"recent": wstega, "exercises": cwiczenia, "archive": archiwum,
            "e1rm_note": "Szacowany 1RM (wzór Epleya) to szacunek do obserwacji trendu, nie zalecenie obciążenia."}


# --- endpointy --------------------------------------------------------------------------

def _summary(db: Session, client_id: str, *, widok_klienta: bool, today: date) -> dict:
    tygodnie = _tygodnie(db, client_id, TYGODNI_TRENING, today)
    biezacy = tygodnie[-1]
    poniedzialek = serwis.poniedzialek(today)
    dni = [{"date": (poniedzialek + timedelta(days=i)).isoformat(),
            "done": (poniedzialek + timedelta(days=i)).isoformat() in biezacy["days"]} for i in range(7)]
    aktualna, najdluzsza = _seria_tygodni(tygodnie, today)
    od_wstegi = (today - timedelta(days=DNI_WSTEGI)).isoformat()
    nowe = (db.query(func.count(ExerciseRecord.id))
            .filter(ExerciseRecord.client_id == client_id, ExerciseRecord.superseded_at.is_(None),
                    ExerciseRecord.achieved_on >= od_wstegi).scalar() or 0)
    out: dict[str, Any] = {
        "week": {"done": biezacy["sessions"], "planned": biezacy["planned"], "days": dni,
                 "message": None if biezacy["planned"] > 0 else "Brak zaplanowanych treningów"},
        "streak": {"weeks": aktualna, "longest": najdluzsza, "message": None if aktualna > 0 else "Zacznij serię"},
        "recent_records": int(nowe),
        "diet": _realizacja_diety(db, client_id, today),
    }
    # Waga: dla klienta z flagą zdrowotną kafelek ZNIKA (bez pola), nie pokazuje pustego stanu (§10.1).
    if not (widok_klienta and _flaga_zdrowotna(db, client_id)):
        out["weight"] = _trend_out(_punkty_wagi(db, client_id, W.OKNO_TRENDU_DNI, today), today)
    return out


@router.get("/summary", dependencies=[Depends(wymagaj_modulu)])
def summary(client_id: str | None = Query(default=None), user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    """Kafelki nagłówka tygodnia (§6.1), filtrowane wg roli i flag."""
    cid, widok_klienta = _podmiot(db, user, client_id)
    return _summary(db, cid, widok_klienta=widok_klienta, today=local_today(user))


@router.get("/records", dependencies=[Depends(wymagaj_modulu)])
def records(client_id: str | None = Query(default=None), history: bool = False,
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Rekordy (§6.2): wstęga z 30 dni, lista ćwiczeń, archiwum > 90 dni; `history=1` dołącza pobite."""
    cid, _ = _podmiot(db, user, client_id)
    return _rekordy_klienta(db, cid, today=local_today(user), historia=history)


def _training(db: Session, client_id: str, today: date, tygodni: int) -> dict:
    tygodnie = _tygodnie(db, client_id, tygodni, today)
    for i, t in enumerate(tygodnie):
        okno = [x["tonnage_kg"] for x in tygodnie[max(0, i - 3): i + 1]]
        t["avg4_tonnage_kg"] = round(sum(okno) / len(okno), 1)
    kalendarz = sorted({d for t in tygodnie for d in t["days"]})
    return {"weeks": tygodnie,
            "sets_by_group": {"current": tygodnie[-1]["sets_by_group"],
                              "previous": tygodnie[-2]["sets_by_group"] if len(tygodnie) > 1 else {}},
            "calendar": {"from": tygodnie[0]["week_start"], "to": today.isoformat(), "session_days": kalendarz}}


@router.get("/training", dependencies=[Depends(wymagaj_modulu)])
def training(client_id: str | None = Query(default=None), range: str = Query(default="12w", pattern=r"^\d{1,2}w$"),
             user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Trening (§6.3): tonaż tygodniowy ze średnią 4-tyg., serie na grupę, kalendarz."""
    cid, _ = _podmiot(db, user, client_id)
    tygodni = max(4, min(26, int(range[:-1])))
    return _training(db, cid, local_today(user), tygodni)


def _body(db: Session, client_id: str, today: date, *, surowe: bool) -> dict:
    punkty = _punkty_wagi(db, client_id, DNI_WAGI, today)
    srednie = W.srednia_kroczaca(punkty)
    od = (today - timedelta(days=DNI_WAGI - 1)).isoformat()
    obwody: dict[str, list] = defaultdict(list)
    for m in (db.query(Measurement).filter(Measurement.client_id == client_id, Measurement.kind != "weight",
                                          Measurement.measured_at >= od).order_by(Measurement.measured_at).all()):
        obwody[m.kind].append({"date": m.measured_at[:10], "value": m.value, "unit": m.unit})
    pierwsze = {k: v for k, v in (db.query(Measurement.kind, func.min(Measurement.measured_at))
                                  .filter(Measurement.client_id == client_id, Measurement.kind != "weight")
                                  .group_by(Measurement.kind).all())}
    obw_out = []
    for kind, pts in obwody.items():
        first = (db.query(Measurement).filter_by(client_id=client_id, kind=kind, measured_at=pierwsze[kind]).first()
                 if kind in pierwsze else None)
        obw_out.append({"kind": kind, "unit": pts[-1]["unit"], "points": pts, "current": pts[-1]["value"],
                        "delta_from_first": round(pts[-1]["value"] - first.value, 1) if first else None,
                        "first_date": first.measured_at[:10] if first else None})
    zdjecia = [{"id": p.id, "file_id": p.file_id, "taken_at": p.taken_at, "pose": p.pose, "note": p.note}
               for p in db.query(ProgressPhoto).filter_by(client_id=client_id).order_by(ProgressPhoto.taken_at.desc()).all()]
    waga = {"average_points": [{"date": p.day.isoformat(), "value": p.value} for p in srednie],
            "average": W.biezaca_srednia(punkty), "trend": _trend_out(punkty, today), "days": DNI_WAGI}
    # Surowe pomiary jako szare punkty — u klienta obok średniej (§6.5), u trenera przełącznik (§7.2).
    waga["raw_points"] = [{"date": p.day.isoformat(), "value": p.value} for p in punkty]
    if surowe:
        waga["raw_visible_default"] = True
    return {"weight": waga, "circumferences": obw_out, "photos": zdjecia}


@router.get("/body", dependencies=[Depends(wymagaj_modulu)])
def body(client_id: str | None = Query(default=None), user: User = Depends(current_user),
         db: Session = Depends(get_db)):
    """Sylwetka (§6.5). Dla klienta z flagą zdrowotną: 404, nie pusta odpowiedź (§10.1, §12)."""
    cid, widok_klienta = _podmiot(db, user, client_id, domain=DOMAIN_HEALTH)
    if widok_klienta and _flaga_zdrowotna(db, cid):
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if not widok_klienta:
        resolve_client_access(db, user, cid, domain=DOMAIN_PHOTOS)
    return _body(db, cid, local_today(user), surowe=not widok_klienta)


# --- trener -----------------------------------------------------------------------------

def _sygnaly(db: Session, coach_id: str, today: date, progi: dict) -> list[dict]:
    rels = (db.query(CoachClientRelationship)
            .filter(CoachClientRelationship.coach_id == coach_id, CoachClientRelationship.status == "ACTIVE").all())
    ids = [r.client_id for r in rels]
    if not ids:
        return []
    users = aggregates.users_by_id(db, ids)
    zgody = aggregates.consent_scopes_bulk(db, coach_id, ids, domains={"training": DOMAIN_TRAINING, "health": DOMAIN_HEALTH})
    od4 = serwis.poniedzialek(today) - timedelta(weeks=3)
    od8 = serwis.poniedzialek(today) - timedelta(weeks=7)
    aggs: dict[str, dict[date, TrainingWeekAggregate]] = defaultdict(dict)
    for a in (db.query(TrainingWeekAggregate)
              .filter(TrainingWeekAggregate.client_id.in_(ids), TrainingWeekAggregate.week_start >= od8.isoformat()).all()):
        aggs[a.client_id][parse_iso_date(a.week_start)] = a
    ostatnia_sesja = dict(db.query(WorkoutSession.client_id, func.max(WorkoutSession.performed_on))
                          .filter(WorkoutSession.client_id.in_(ids)).group_by(WorkoutSession.client_id).all())
    od_wagi = (today - timedelta(days=W.OKNO_TRENDU_DNI - 1)).isoformat()
    wagi: dict[str, list] = defaultdict(list)
    for cid, m, v, u in (db.query(Measurement.client_id, Measurement.measured_at, Measurement.value, Measurement.unit)
                         .filter(Measurement.client_id.in_(ids), Measurement.kind == "weight", Measurement.measured_at >= od_wagi)
                         .order_by(Measurement.measured_at).all()):
        wagi[cid].append((m[:10], v if (u or "kg").lower() == "kg" else R.normalizuj_ciezar(v, u)))
    ostatnie_wazenie = dict(db.query(Measurement.client_id, func.max(Measurement.measured_at))
                            .filter(Measurement.client_id.in_(ids), Measurement.kind == "weight").group_by(Measurement.client_id).all())
    od_rek = (today - timedelta(days=int(progi["dni_rekordu"]))).isoformat()
    rekordy = dict(db.query(ExerciseRecord.client_id, func.count(ExerciseRecord.id))
                   .filter(ExerciseRecord.client_id.in_(ids), ExerciseRecord.superseded_at.is_(None),
                           ExerciseRecord.achieved_on >= od_rek).group_by(ExerciseRecord.client_id).all())
    cele = {}
    for est in (db.query(zapotrzebowanie_serwis.CalorieEstimate)
                .filter(zapotrzebowanie_serwis.CalorieEstimate.client_id.in_(ids))
                .order_by(zapotrzebowanie_serwis.CalorieEstimate.version_no).all()):
        try:
            cele[est.client_id] = json.loads(est.inputs_json).get("cel")
        except ValueError:
            continue
    items_by_client: dict[str, list[ScheduleItem]] = defaultdict(list)
    for it in (db.query(ScheduleItem).filter(ScheduleItem.client_id.in_(ids), ScheduleItem.category == "TRENING",
                                            ScheduleItem.status == "ACTIVE").all()):
        items_by_client[it.client_id].append(it)
    out = []
    for cid in ids:
        u = users.get(cid)
        zg = zgody.get(cid, {})
        sygnaly: list[dict] = []
        tygodnie4 = [_tydzien_out(od4 + timedelta(weeks=i), aggs[cid].get(od4 + timedelta(weeks=i)),
                                  serwis._zaplanowane_z_elementow(items_by_client.get(cid, []), od4 + timedelta(weeks=i)))
                     for i in range(4)]
        done4 = sum(t["sessions"] for t in tygodnie4)
        planned4 = sum(t["planned"] for t in tygodnie4)
        frekwencja = {"done": done4, "planned": planned4, "pct": round(100 * done4 / planned4) if planned4 else None}
        ostatnia = ostatnia_sesja.get(cid)
        if zg.get("training"):
            dni_bez = (today - parse_iso_date(ostatnia[:10])).days if ostatnia else None
            if dni_bez is None or dni_bez >= int(progi["dni_bez_treningu"]):
                sygnaly.append({"key": "no_training", "level": "high",
                                "label": f"Brak treningu od {dni_bez} dni" if dni_bez is not None else "Brak zapisanych treningów"})
            ost2 = tygodnie4[-3:-1]  # dwa ostatnie zamknięte tygodnie
            if all(t["planned"] > 0 and 100 * t["sessions"] / t["planned"] < int(progi["frekwencja_pct"]) for t in ost2):
                sygnaly.append({"key": "attendance_drop", "level": "high",
                                "label": f"Frekwencja poniżej {progi['frekwencja_pct']} % w 2 kolejnych tygodniach"})
            wszystkie8 = [aggs[cid].get(od8 + timedelta(weeks=i)) for i in range(8)]
            tonaze = [a.tonnage_kg for a in wszystkie8 if a is not None]
            if len(tonaze) >= 5:
                srednia4 = sum(tonaze[-5:-1]) / 4
                if srednia4 > 0 and tonaze[-1] < srednia4 * (1 - int(progi["spadek_tonazu_pct"]) / 100):
                    sygnaly.append({"key": "tonnage_drop", "level": "medium",
                                    "label": f"Tonaż −{round(100 * (1 - tonaze[-1] / srednia4))} % wobec średniej 4 tyg."})
            if rekordy.get(cid):
                sygnaly.append({"key": "new_record", "level": "info",
                                "label": f"{rekordy[cid]} nowych rekordów w {progi['dni_rekordu']} dni"})
        trend = None
        if zg.get("health"):
            punkty = W.pomiary(wagi.get(cid, []))
            trend = W.trend_kg_na_tydzien(punkty, today=today)
            ow = ostatnie_wazenie.get(cid)
            dni_bez_wazenia = (today - parse_iso_date(ow[:10])).days if ow else None
            if dni_bez_wazenia is None or dni_bez_wazenia >= int(progi["dni_bez_wazenia"]):
                sygnaly.append({"key": "no_weighing", "level": "medium",
                                "label": f"Brak ważenia od {dni_bez_wazenia} dni" if dni_bez_wazenia is not None else "Brak pomiarów wagi"})
            if (cele.get(cid) == "redukcja" and trend is not None and trend >= float(progi["trend_wzrost_kg"])
                    and punkty and (today - punkty[0].day).days + 1 >= int(progi["dni_trendu"])):
                sygnaly.append({"key": "goal_mismatch", "level": "medium",
                                "label": f"Cel redukcja, a trend +{trend} kg/tydz."})
        priorytet = sum({"high": 100, "medium": 10, "info": 1}[s["level"]] for s in sygnaly)
        out.append({"client_id": cid, "display_name": u.display_name if u else "", "email": u.email if u else "",
                    "last_activity": ostatnia, "attendance_4w": frekwencja, "weight_trend_kg_week": trend,
                    "signals": sygnaly, "priority": priorytet,
                    "consents": {"training": bool(zg.get("training")), "health": bool(zg.get("health"))}})
    out.sort(key=lambda c: (-c["priority"], c["display_name"]))
    return out


def _progi(**kw) -> dict:
    return {k: (kw.get(k) if kw.get(k) is not None else v) for k, v in PROGI_DOMYSLNE.items()}


@router.get("/clients", dependencies=[Depends(wymagaj_modulu)])
def clients(dni_bez_treningu: int | None = Query(default=None, ge=1, le=365),
            frekwencja_pct: int | None = Query(default=None, ge=1, le=100),
            dni_bez_wazenia: int | None = Query(default=None, ge=1, le=365),
            spadek_tonazu_pct: int | None = Query(default=None, ge=1, le=100),
            trend_wzrost_kg: float | None = Query(default=None, ge=0, le=5),
            dni_trendu: int | None = Query(default=None, ge=7, le=120),
            dni_rekordu: int | None = Query(default=None, ge=1, le=90),
            coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Lista klientów z sygnałami (§7.1), sortowana po priorytecie; progi konfigurowalne."""
    progi = _progi(dni_bez_treningu=dni_bez_treningu, frekwencja_pct=frekwencja_pct, dni_bez_wazenia=dni_bez_wazenia,
                   spadek_tonazu_pct=spadek_tonazu_pct, trend_wzrost_kg=trend_wzrost_kg, dni_trendu=dni_trendu,
                   dni_rekordu=dni_rekordu)
    return {"clients": _sygnaly(db, coach.id, local_today(coach), progi), "thresholds": progi}


@router.get("/clients/{client_id}", dependencies=[Depends(wymagaj_modulu)])
def client_detail(client_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Widok pojedynczego klienta (§7.2): pełne dane niezależnie od flag klienta,
    surowe pomiary wagi z przełącznikiem średniej, notatki trenera przypięte do dat,
    historia zmian planu na tle tonażu. Relacja + zgody sprawdzane per domena;
    obcy trener dostaje odmowę (404 — aplikacja nie ujawnia istnienia klienta)."""
    resolve_client_access(db, coach, client_id, domain=DOMAIN_TRAINING)
    today = local_today(coach)
    from ..authz import coach_can_access_client

    out: dict[str, Any] = {
        "client_id": client_id,
        "summary": _summary(db, client_id, widok_klienta=False, today=today),
        "records": _rekordy_klienta(db, client_id, today=today, historia=True),
        "training": _training(db, client_id, today, TYGODNI_TRENING),
        "health_flag": _flaga_zdrowotna(db, client_id),
    }
    if coach_can_access_client(db, coach.id, client_id, domain=DOMAIN_HEALTH):
        out["body"] = _body(db, client_id, today, surowe=True)
        if not coach_can_access_client(db, coach.id, client_id, domain=DOMAIN_PHOTOS):
            out["body"]["photos"] = []
        out["notes"] = [{"date": o.occurred_on, "text": o.text, "category": o.category, "severity": o.severity}
                        for o in db.query(Observation).filter(Observation.client_id == client_id, Observation.created_by == coach.id)
                        .order_by(Observation.occurred_on.desc()).limit(50).all()]
    else:
        out["summary"].pop("weight", None)
    if not coach_can_access_client(db, coach.id, client_id, domain=DOMAIN_NUTRITION):
        out["summary"]["diet"] = None
    zmiany = (db.query(TrainingPlanVersion.version_no, TrainingPlanVersion.reason, TrainingPlanVersion.created_at)
              .join(TrainingPlan, TrainingPlan.id == TrainingPlanVersion.plan_id)
              .filter(TrainingPlan.client_id == client_id).order_by(TrainingPlanVersion.created_at).all())
    out["plan_changes"] = [{"date": c[:10], "version_no": v, "reason": r} for v, r, c in zmiany]
    return out

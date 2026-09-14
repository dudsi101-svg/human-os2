"""Postępy — warstwa bazy (0.66.0): serie klienta z sesji, przeliczanie
rekordów (`exercise_records`) i agregatów tygodnia
(`training_week_aggregates`), powiadomienie zbiorcze po zapisie sesji.

Przeliczenie jest deterministyczne i „od zera” per ćwiczenie / tydzień:
usuwa wiersze i wstawia policzone na nowo — dwukrotne uruchomienie daje
identyczny stan (idempotencja backfillu, §11.3), a korekta serii cofa
rekord (§8.2.9). Porównania wyłącznie z własną historią klienta.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..dates import parse_iso_date
from ..models import (
    Exercise,
    ExerciseRecord,
    ScheduleItem,
    TrainingWeekAggregate,
    WorkoutEntry,
    WorkoutSession,
    new_id,
    now_iso,
)
from . import rekordy as R

GRUPA_NIEZNANA = "INNE"


# --- serie z bazy --------------------------------------------------------

def serie_klienta(db: Session, client_id: str, *, exercise_keys: set[str] | None = None) -> list[R.Seria]:
    """Wszystkie serie klienta (jedno zapytanie); opcjonalnie tylko wybrane ćwiczenia."""
    # Sesja pominięta (SKIPPED) nie jest treningiem — nie daje serii ani rekordu.
    # Porządek deterministyczny (data, czas zapisu, id): ten sam backfill daje
    # te same `set_ref`/`session_id` także na PostgreSQL.
    rows = (
        db.query(WorkoutEntry, WorkoutSession.performed_on, WorkoutSession.id)
        .join(WorkoutSession, WorkoutEntry.session_id == WorkoutSession.id)
        .filter(WorkoutSession.client_id == client_id, WorkoutSession.status != "SKIPPED")
        .order_by(WorkoutSession.performed_on, WorkoutSession.created_at, WorkoutSession.id,
                  WorkoutEntry.exercise_index, WorkoutEntry.id)
        .all()
    )
    out: list[R.Seria] = []
    for entry, performed_on, session_id in rows:
        klucz = R.klucz_cwiczenia(entry.exercise_name)
        if not klucz or (exercise_keys is not None and klucz not in exercise_keys):
            continue
        out.extend(R.serie_z_wpisu(entry_id=entry.id, exercise_name=entry.exercise_name,
                                   performed_on=performed_on, session_id=session_id,
                                   sets=_sets(entry)))
    return out


def _sets(entry: WorkoutEntry) -> list[dict]:
    if not entry.sets_json:
        return []
    try:
        sets = json.loads(entry.sets_json)
    except ValueError:
        return []
    return sets if isinstance(sets, list) else []


def nazwy_cwiczen(db: Session, client_id: str) -> dict[str, str]:
    """klucz → ostatnio użyta nazwa wyświetlana."""
    rows = (
        db.query(WorkoutEntry.exercise_name, WorkoutSession.performed_on)
        .join(WorkoutSession, WorkoutEntry.session_id == WorkoutSession.id)
        .filter(WorkoutSession.client_id == client_id, WorkoutSession.status != "SKIPPED")
        .order_by(WorkoutSession.performed_on, WorkoutSession.created_at, WorkoutSession.id, WorkoutEntry.id)
        .all()
    )
    out: dict[str, str] = {}
    for name, _d in rows:
        klucz = R.klucz_cwiczenia(name)
        if klucz:
            out[klucz] = name.strip()
    return out


# --- rekordy ---------------------------------------------------------------

def przelicz_rekordy(db: Session, client_id: str, *, exercise_keys: set[str] | None = None
                     ) -> dict[str, list[R.Rekord]]:
    """Przelicza rekordy klienta (wszystkie ćwiczenia albo wskazane) i
    podmienia wiersze `exercise_records` dla tych ćwiczeń."""
    serie = serie_klienta(db, client_id, exercise_keys=exercise_keys)
    nazwy = nazwy_cwiczen(db, client_id)
    wynik = R.licz_rekordy(serie)
    klucze = set(exercise_keys) if exercise_keys is not None else set(nazwy) | set(wynik)
    q = db.query(ExerciseRecord).filter(ExerciseRecord.client_id == client_id)
    if exercise_keys is not None:
        q = q.filter(ExerciseRecord.exercise_key.in_(sorted(klucze)))
    q.delete(synchronize_session=False)
    for klucz in sorted(klucze):
        for r in wynik.get(klucz, []):
            db.add(ExerciseRecord(
                id=new_id("REK"), client_id=client_id, exercise_key=klucz,
                exercise_name=nazwy.get(klucz, klucz), record_type=r.record_type, value=r.value,
                secondary_value=r.secondary_value, set_ref=r.set_ref, session_id=r.session_id,
                achieved_on=r.achieved_on, previous_value=r.previous_value, equaled_on=r.equaled_on,
                superseded_at=r.superseded_on,
            ))
    db.flush()
    return wynik


# --- agregaty tygodnia ------------------------------------------------------

def poniedzialek(d: date) -> date:
    return d - timedelta(days=d.weekday())


def grupy_miesniowe(db: Session) -> dict[str, str]:
    """klucz nazwy ćwiczenia (bez diakrytyki) → grupa z bazy ćwiczeń trenerów.
    Baza ćwiczeń to własność trenerów (nie dane klienta) — służy tylko do
    etykiety grupy; brak dopasowania = INNE."""
    out: dict[str, str] = {}
    for name, group in db.query(Exercise.name, Exercise.muscle_group).all():
        out.setdefault(R.klucz_blizniaka(name), group or GRUPA_NIEZNANA)
    return out


def zaplanowane_treningi(db: Session, client_id: str, tydzien_od: date) -> int:
    """Liczba zaplanowanych treningów w tygodniu: elementy harmonogramu
    kategorii TRENING (aktywne, w zakresie dat) × ich dni tygodnia."""
    items = (db.query(ScheduleItem)
             .filter(ScheduleItem.client_id == client_id, ScheduleItem.category == "TRENING",
                     ScheduleItem.status == "ACTIVE").all())
    return _zaplanowane_z_elementow(items, tydzien_od)


def _zaplanowane_z_elementow(items: list[ScheduleItem], tydzien_od: date) -> int:
    n = 0
    for it in items:
        try:
            dni = {int(x) for x in (it.days_of_week or "").split(",") if x.strip()}
        except ValueError:
            continue
        for i in range(7):
            d = tydzien_od + timedelta(days=i)
            if d.isoweekday() not in dni:
                continue
            if it.start_date and d < parse_iso_date(it.start_date[:10]):
                continue
            if it.end_date and d > parse_iso_date(it.end_date[:10]):
                continue
            n += 1
    return n


def przelicz_agregaty(db: Session, client_id: str, *, tygodnie: set[date] | None = None) -> int:
    """Przelicza agregaty tygodni (wszystkie z sesjami albo wskazane poniedziałki)."""
    # SKIPPED = trening pominięty: nie liczy się do sesji, frekwencji ani tonażu.
    sesje = (db.query(WorkoutSession)
             .filter(WorkoutSession.client_id == client_id, WorkoutSession.status != "SKIPPED").all())
    entries = defaultdict(list)
    for e in (db.query(WorkoutEntry).join(WorkoutSession, WorkoutEntry.session_id == WorkoutSession.id)
              .filter(WorkoutSession.client_id == client_id).all()):
        entries[e.session_id].append(e)
    grupy = grupy_miesniowe(db)
    items = (db.query(ScheduleItem)
             .filter(ScheduleItem.client_id == client_id, ScheduleItem.category == "TRENING",
                     ScheduleItem.status == "ACTIVE").all())
    per_tydzien: dict[date, dict] = {}
    for s in sesje:
        try:
            d = parse_iso_date(s.performed_on[:10])
        except ValueError:
            continue
        w = poniedzialek(d)
        if tygodnie is not None and w not in tygodnie:
            continue
        agg = per_tydzien.setdefault(w, {"sessions": 0, "tonnage": 0.0, "groups": defaultdict(int), "days": set()})
        agg["sessions"] += 1
        agg["days"].add(d.isoformat())
        for e in entries.get(s.id, []):
            grupa = grupy.get(R.klucz_blizniaka(e.exercise_name), GRUPA_NIEZNANA)
            for st in _sets(e):
                try:
                    w_kg, reps = float(st.get("weight_kg") or 0), int(st.get("reps") or 0)
                except (TypeError, ValueError):
                    continue
                if reps <= 0 or st.get("warmup"):
                    continue
                agg["groups"][grupa] += 1
                agg["tonnage"] += w_kg * reps
    klucze = set(per_tydzien) if tygodnie is None else set(tygodnie)
    q = db.query(TrainingWeekAggregate).filter(TrainingWeekAggregate.client_id == client_id)
    if tygodnie is not None:
        q = q.filter(TrainingWeekAggregate.week_start.in_([t.isoformat() for t in tygodnie]))
    q.delete(synchronize_session=False)
    for w in sorted(klucze):
        agg = per_tydzien.get(w, {"sessions": 0, "tonnage": 0.0, "groups": {}, "days": set()})
        db.add(TrainingWeekAggregate(
            id=new_id("TWA"), client_id=client_id, week_start=w.isoformat(),
            sessions_count=agg["sessions"], planned_count=_zaplanowane_z_elementow(items, w),
            tonnage_kg=round(agg["tonnage"], 1),
            sets_by_group_json=json.dumps(dict(sorted(agg["groups"].items())), ensure_ascii=False),
            session_days_json=json.dumps(sorted(agg["days"])), updated_at=now_iso(),
        ))
    db.flush()
    return len(klucze)


# --- po zapisie sesji -------------------------------------------------------

def po_zapisie_sesji(db: Session, session: WorkoutSession, entries: list[WorkoutEntry]) -> list[R.Rekord]:
    """Przeliczenie rekordów ćwiczeń z sesji i agregatu jej tygodnia; zwraca
    rekordy ustanowione w TEJ sesji (do jednego zbiorczego powiadomienia)."""
    klucze = {R.klucz_cwiczenia(e.exercise_name) for e in entries}
    nowe: list[R.Rekord] = []
    if klucze:
        wynik = przelicz_rekordy(db, session.client_id, exercise_keys=klucze)
        nowe = R.nowe_w_sesji(wynik, session.id)
    try:
        tydzien = poniedzialek(parse_iso_date(session.performed_on[:10]))
    except ValueError:
        return nowe
    przelicz_agregaty(db, session.client_id, tygodnie={tydzien})
    return nowe


def powiadom_o_rekordach(db: Session, client_id: str, session_id: str, nowe: list[R.Rekord]):
    """Maksymalnie jedno powiadomienie na sesję, zbiorcze, tylko w aplikacji (§8.3).
    Zwraca wiersz powiadomienia (do `publish_realtime` PO commit) albo None."""
    if not nowe:
        return None
    from ..notifications import notify_now

    n = len(nowe)
    if n == 1:
        tytul = "Nowy rekord osobisty"
    elif 2 <= n <= 4:
        tytul = f"{n} nowe rekordy w tym treningu"
    else:
        tytul = f"{n} nowych rekordów w tym treningu"
    # Nazwy wyświetlane (nie klucze): w treści powiadomienia klient widzi to, co wpisał.
    nazwy = nazwy_cwiczen(db, client_id)
    cwiczenia = sorted({nazwy.get(r.exercise_key, r.exercise_key) for r in nowe})
    return notify_now(db, user_id=client_id, category="REKORD", title=tytul,
                      body="Ćwiczenia: " + ", ".join(cwiczenia[:5]) + ("…" if len(cwiczenia) > 5 else ""),
                      url="/monitoring", dedup_key=f"rekord:{session_id}")


# --- backfill ---------------------------------------------------------------

def blizniaki(db: Session, client_id: str) -> list[list[str]]:
    """Nazwy ćwiczeń, które różnią się tylko diakrytyką/znakami (podejrzane
    literówki) — do decyzji trenera, nie scalane automatycznie."""
    grupy: dict[str, set[str]] = defaultdict(set)
    for klucz, nazwa in nazwy_cwiczen(db, client_id).items():
        grupy[R.klucz_blizniaka(nazwa)].add(klucz)
    return sorted(sorted(g) for g in grupy.values() if len(g) > 1)


def przelicz_klienta(db: Session, client_id: str) -> dict:
    wynik = przelicz_rekordy(db, client_id)
    tygodnie = przelicz_agregaty(db, client_id)
    aktualne = sum(1 for lista in wynik.values() for r in lista if r.aktualny)
    return {"client_id": client_id, "cwiczenia": len(wynik), "rekordy_aktualne": aktualne,
            "rekordy_razem": sum(len(lista) for lista in wynik.values()), "tygodnie": tygodnie,
            "blizniaki": blizniaki(db, client_id)}

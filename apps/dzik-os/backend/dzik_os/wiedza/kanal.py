"""Ranking „Dla Ciebie” — bez uczenia maszynowego (plik 02, „Rankowanie”).

Kandydaci: karty powiązane z bieżącym planem, nieprzeczytane podstawy,
wyjaśnienia rzeczywistych zmian z ostatnich 7 dni. Punktacja: +60 za
rzeczywistą zmianę planu w ostatnich 7 dniach; +40 za pierwszą
ekspozycję na ćwiczenie lub parametr; +20 za podstawy zgodne z etapem;
−50 za otwarcie materiału w ostatnich 7 dniach. (+100 za jawne otwarcie
nierozwiązanego pytania: P0 nie ma jeszcze rejestru pytań — pomijane,
opisane w docs/WIEDZA.md.) Remis: stabilne ID. Maksymalnie trzy różne
karty. Odrzucane: robocze (poza trybem demo), wycofane, bez aktualnego
przeglądu. Zawsze prosty powód rekomendacji.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from ..dates import local_today
from ..models import WiedzaOdczyt, WiedzaUstawienia
from . import tresci

#: Ręcznie uporządkowane podstawy po odmowie personalizacji (K29).
PODSTAWY_STATYCZNE = ("k-safety", "k-rir", "k-sets", "k-load", "k-energy", "k-log", "k-evidence")

#: Typy elementów treningu obecne w każdym planie z dniami/ćwiczeniami.
TYPY_PLANU_TRENINGOWEGO = ("training_frequency", "work_sets", "rir", "rest", "load", "progression")
TYPY_PLANU_DIETY = ("energy_target", "macro_target", "portion")


def personalizacja_wlaczona(db: Session, owner_id: str) -> bool:
    u = db.get(WiedzaUstawienia, owner_id)
    return True if u is None else bool(u.personalizacja)


def dla_ciebie(db: Session, *, owner_id: str, plan: dict | None, dieta: bool,
               zmiany_od: list[str], dzis: date | None = None) -> list[dict]:
    """`plan`: {"exercise_ids": [id konfiguratora...], "ma_rir": bool} albo
    None; `zmiany_od`: daty ISO utworzenia wersji planów (do +60)."""
    dzis = dzis or local_today()
    if not personalizacja_wlaczona(db, owner_id):
        return _statyczne(db, dzis)
    granica = (datetime.combine(dzis, datetime.min.time()) - timedelta(days=7)).isoformat()
    odczyty = {o.article_id: o for o in db.query(WiedzaOdczyt).filter_by(owner_id=owner_id).all()}
    kandydaci: dict[str, tuple[int, str]] = {}

    def dodaj(article_id: str, punkty: int, powod: str) -> None:
        obecne = kandydaci.get(article_id)
        if obecne is None or punkty > obecne[0]:
            kandydaci[article_id] = (punkty, powod)

    zmiana_7d = any(z >= granica for z in zmiany_od)
    if zmiana_7d:
        for k in tresci.powiazane(db, "plan_change"):
            dodaj(k.article_id, 60, "Twój plan zmienił się w tym tygodniu")
    if plan:
        for eid in plan.get("exercise_ids", []):
            for k in tresci.powiazane(db, "exercise", eid):
                if k.article_id not in odczyty:
                    dodaj(k.article_id, 40, "Ćwiczenie z Twojego planu — pierwsze spotkanie")
        for typ in TYPY_PLANU_TRENINGOWEGO:
            if typ == "rir" and not plan.get("ma_rir"):
                continue
            for k in tresci.powiazane(db, typ):
                if k.article_id not in odczyty:
                    dodaj(k.article_id, 40, "Parametr z Twojego planu")
    if dieta:
        for typ in TYPY_PLANU_DIETY:
            for k in tresci.powiazane(db, typ):
                if k.article_id not in odczyty:
                    dodaj(k.article_id, 40, "Element Twojej diety")
    for aid in PODSTAWY_STATYCZNE:
        if aid not in odczyty:
            dodaj(aid, 20, "Podstawy na start")
    wynik = []
    for aid, (punkty, powod) in kandydaci.items():
        k = tresci.aktualna(db, aid)
        if k is None or tresci.przeglad_wygasl(k, dzis):
            continue
        o = odczyty.get(aid)
        if o is not None and o.last_opened_at >= granica:
            punkty -= 50
        wynik.append((-punkty, aid, powod, k))
    wynik.sort(key=lambda x: (x[0], x[1]))
    return [{**tresci.naglowek(k, dzis=dzis), "powod": powod, "punkty": -p}
            for p, _aid, powod, k in wynik[:3]]


def _statyczne(db: Session, dzis: date) -> list[dict]:
    out = []
    for aid in PODSTAWY_STATYCZNE:
        k = tresci.aktualna(db, aid)
        if k is not None and not tresci.przeglad_wygasl(k, dzis):
            out.append({**tresci.naglowek(k, dzis=dzis),
                        "powod": "Podstawy w ustalonej kolejności (personalizacja wyłączona)",
                        "punkty": 0})
        if len(out) == 3:
            break
    return out

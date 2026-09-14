"""Zapotrzebowanie kaloryczne — warstwa bazy (0.62.0).

Liczy szacunek przy przesłaniu wywiadu „zapotrzebowanie” (wywołanie z
`serwis.przeslij`), trzyma jedną wersję na przesłanie, obsługuje nadpisanie
i odblokowanie przez trenera oraz WIDOK zależny od roli: gdy z wywiadu
wynika flaga zdrowotna (zaburzenia odżywiania), klient nie dostaje żadnej
liczby (kcal, PPM, masa) — filtr po stronie serwera, nie interfejsu.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..hos_bridge import record_event
from ..models import CalorieEstimate, InterviewSubmission, User, new_id, now_iso
from . import definicje as D
from . import zapotrzebowanie as Z

#: Zakres nadpisania trenera (kcal/dzień).
NADPISANIE_MIN, NADPISANIE_MAX = 800, 8000

KOMUNIKAT_UKRYTY = ("Wynik jest gotowy, ale najpierw omówi go z Tobą trener — tak wynika z Twojej "
                    "odpowiedzi w części „Bezpieczeństwo”. Liczby pojawią się tutaj po rozmowie.")


def przelicz_po_przeslaniu(db: Session, *, submission: InterviewSubmission,
                           answers: dict[str, dict]) -> CalorieEstimate | None:
    """Nowa wersja szacunku dla przesłania typu `zapotrzebowanie`. Brak
    danych (np. pytanie zdrowotne ukryte zgodą nie przeszkadza; brak masy —
    tak) = brak szacunku, bez wyjątku: przesłanie i tak jest ważne."""
    if submission.typ != D.ZAPOTRZEBOWANIE:
        return None
    try:
        wynik = Z.oblicz(Z.z_odpowiedzi(D.wartosci(answers)))
    except Z.BrakDanych:
        return None
    wejscie = Z.z_odpowiedzi(D.wartosci(answers))
    est = CalorieEstimate(
        id=new_id("CAL"), client_id=submission.client_id, submission_id=submission.id,
        version_no=submission.version_no,
        inputs_json=json.dumps({
            "plec": wejscie.plec, "wiek": wejscie.wiek, "wzrost_cm": wejscie.wzrost_cm,
            "masa_kg": wejscie.masa_kg, "praca": wejscie.praca, "treningi": wejscie.treningi,
            "kroki": wejscie.kroki, "cel": wejscie.cel, "tempo": wejscie.tempo,
        }, ensure_ascii=False),
        ppm=wynik.ppm, pal=wynik.pal, cpm=wynik.cpm, korekta_pct=wynik.korekta_pct, kcal=wynik.kcal,
        podstawienie_json=json.dumps(list(wynik.podstawienie), ensure_ascii=False),
        ostrzezenia_json=json.dumps(list(wynik.ostrzezenia), ensure_ascii=False),
        hidden_for_client=bool(submission.safety_flag),
    )
    db.add(est)
    db.flush()
    return est


def ostatni(db: Session, client_id: str) -> CalorieEstimate | None:
    return (db.query(CalorieEstimate).filter_by(client_id=client_id)
            .order_by(CalorieEstimate.version_no.desc()).first())


def historia(db: Session, client_id: str) -> list[CalorieEstimate]:
    return (db.query(CalorieEstimate).filter_by(client_id=client_id)
            .order_by(CalorieEstimate.version_no.desc()).all())


def kcal_obowiazujace(est: CalorieEstimate) -> int:
    return est.override_kcal if est.override_kcal is not None else est.kcal


def _pelny(est: CalorieEstimate) -> dict[str, Any]:
    return {
        "id": est.id, "submission_id": est.submission_id, "version_no": est.version_no,
        "created_at": est.created_at, "inputs": json.loads(est.inputs_json or "{}"),
        "ppm": est.ppm, "pal": est.pal, "cpm": est.cpm, "korekta_pct": est.korekta_pct,
        "kcal": est.kcal, "kcal_effective": kcal_obowiazujace(est),
        "podstawienie": json.loads(est.podstawienie_json or "[]"),
        "ostrzezenia": json.loads(est.ostrzezenia_json or "[]"),
        "hidden_for_client": est.hidden_for_client,
        "unhidden_by": est.unhidden_by, "unhidden_at": est.unhidden_at,
        "override": {"kcal": est.override_kcal, "by": est.override_by, "at": est.override_at,
                     "reason": est.override_reason} if est.override_kcal is not None else None,
    }


def widok(est: CalorieEstimate | None, *, viewer: str) -> dict[str, Any]:
    """Odpowiedź API. Trener: pełne dane. Klient: pełne, chyba że
    `hidden_for_client` — wtedy wyłącznie status i komunikat (żadnych liczb,
    także wejść: masa ciała też jest liczbą)."""
    if est is None:
        return {"status": "none", "estimate": None}
    if viewer == "client" and est.hidden_for_client:
        return {"status": "hidden", "estimate": None, "message": KOMUNIKAT_UKRYTY,
                "version_no": est.version_no}
    return {"status": "ok", "estimate": _pelny(est)}


def nadpisz(db: Session, est: CalorieEstimate, *, actor: User, kcal: int | None, reason: str) -> CalorieEstimate:
    """Trener nadpisuje wynik (kcal=None cofa nadpisanie). Powód obowiązkowy."""
    if kcal is not None and not (NADPISANIE_MIN <= kcal <= NADPISANIE_MAX):
        raise ValueError(f"Nadpisanie poza zakresem {NADPISANIE_MIN}–{NADPISANIE_MAX} kcal.")
    if not reason.strip():
        raise ValueError("Podaj powód nadpisania (klient go zobaczy).")
    poprzednie = est.override_kcal
    est.override_kcal = kcal
    est.override_by = actor.id if kcal is not None else None
    est.override_at = now_iso() if kcal is not None else None
    est.override_reason = reason.strip() if kcal is not None else None
    record_event(
        db, action="CALORIE_ESTIMATE_OVERRIDDEN", actor_id=actor.id, subject_ids=[est.client_id],
        payload={"estimate_id": est.id, "from": poprzednie, "to": kcal, "formula_kcal": est.kcal},
        summary=("Trener nadpisał zapotrzebowanie" if kcal is not None else "Trener cofnął nadpisanie zapotrzebowania"),
    )
    db.flush()
    return est


def odblokuj(db: Session, est: CalorieEstimate, *, actor: User) -> CalorieEstimate:
    """Trener po rozmowie z klientem odsłania liczby (flaga zdrowotna)."""
    if est.hidden_for_client:
        est.hidden_for_client = False
        est.unhidden_by = actor.id
        est.unhidden_at = now_iso()
        record_event(
            db, action="CALORIE_ESTIMATE_UNHIDDEN", actor_id=actor.id, subject_ids=[est.client_id],
            payload={"estimate_id": est.id}, summary="Trener odsłonił klientowi wynik zapotrzebowania",
        )
        db.flush()
    return est

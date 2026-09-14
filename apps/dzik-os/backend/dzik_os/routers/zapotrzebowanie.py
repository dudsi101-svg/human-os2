"""Zapotrzebowanie kaloryczne (0.62.0) — odczyt wyniku, nadpisanie i
odblokowanie przez trenera. Za flagą DZIK_CALORIE_INTERVIEW_ENABLED (404).
Dostęp jak w zakładce Wywiad (`wywiady._dostep`): klient — swoje dane;
trener — aktywna relacja i zgody. Filtr flagi zdrowotnej jest w
`zapotrzebowanie_serwis.widok`, nie w interfejsie."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User
from ..security import current_user
from ..wywiad import definicje as D
from ..wywiad import zapotrzebowanie_serwis as ZS
from .wywiady import _dostep

router = APIRouter(prefix="/api", tags=["zapotrzebowanie"])


class NadpisanieIn(BaseModel):
    kcal: int | None = Field(default=None, ge=ZS.NADPISANIE_MIN, le=ZS.NADPISANIE_MAX)
    reason: str = Field(min_length=1, max_length=500)


def _wlaczone() -> None:
    if not settings.calorie_interview_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


def _odpowiedz(db: Session, d: dict, client_id: str) -> dict:
    out = {"client_id": client_id, "enabled": True, "interview_typ": D.ZAPOTRZEBOWANIE,
           "access": {"ok": d["ok"], "reason": d["reason"], "viewer": d["viewer"]}}
    if not d["ok"]:
        return {**out, "status": "no_access", "estimate": None}
    est = ZS.ostatni(db, client_id)
    out.update(ZS.widok(est, viewer=d["viewer"]))
    if d["viewer"] == "coach":
        out["history"] = [{"version_no": e.version_no, "kcal": e.kcal, "kcal_effective": ZS.kcal_obowiazujace(e),
                           "created_at": e.created_at} for e in ZS.historia(db, client_id)]
    return out


@router.get("/clients/{client_id}/zapotrzebowanie")
def pobierz(client_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _wlaczone()
    d = _dostep(db, user, client_id)
    return _odpowiedz(db, d, client_id)


def _trener_z_wynikiem(db: Session, user: User, client_id: str):
    d = _dostep(db, user, client_id)
    if d["viewer"] != "coach":
        raise HTTPException(status_code=403, detail="Tylko trener może zmieniać wynik.")
    if not d["ok"]:
        raise HTTPException(status_code=403, detail=d["reason"])
    est = ZS.ostatni(db, client_id)
    if est is None:
        raise HTTPException(status_code=404, detail="Klient nie przesłał jeszcze wywiadu zapotrzebowania.")
    return d, est


@router.put("/clients/{client_id}/zapotrzebowanie/nadpisanie")
def nadpisz(client_id: str, body: NadpisanieIn, user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    _wlaczone()
    d, est = _trener_z_wynikiem(db, user, client_id)
    try:
        ZS.nadpisz(db, est, actor=user, kcal=body.kcal, reason=body.reason)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    db.commit()
    return _odpowiedz(db, d, client_id)


@router.post("/clients/{client_id}/zapotrzebowanie/odblokuj")
def odblokuj(client_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _wlaczone()
    d, est = _trener_z_wynikiem(db, user, client_id)
    ZS.odblokuj(db, est, actor=user)
    db.commit()
    return _odpowiedz(db, d, client_id)

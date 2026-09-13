"""Wiedza (0.56.0, P0) — API biblioteki, wyjaśnień i redakcji.

Klient: `/api/wiedza/*` (własne dane; plan wskazywany w body/ścieżce
jest autoryzowany po stronie serwera przez resolve_client_access).
Trener (redaktor/recenzent): `/api/coach/wiedza/*`.

Flaga `DZIK_WIEDZA_V2=false` → wszystkie trasy odpowiadają 404, a klient
pokazuje poprzednią zakładkę. Odpowiedzi indywidualne (wyjaśnienia,
feed, historia) mają `Cache-Control: private, no-store`.

Pomiar (plik 09): zdarzenia audytu z publicznym id artykułu/rewizji i
kodem statusu — bez zapytań, faktów, wartości planu ani objawów.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..dates import local_today
from ..db import get_db
from ..hos_bridge import record_event
from ..models import (
    CoachClientRelationship,
    KnowledgeItem,
    NutritionPlan,
    NutritionPlanVersion,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    WiedzaArtykul,
    WiedzaOdczyt,
    WiedzaOpinia,
    WiedzaSlad,
    WiedzaUstawienia,
    WiedzaZakladka,
    new_id,
    now_iso,
)
from ..security import current_user, require_role
from ..wiedza import dane, kanal, resolver, szukaj, tresci

router = APIRouter(prefix="/api", tags=["wiedza"])

PRYWATNE = "private, no-store"


def wymagaj_v2() -> None:
    if not settings.wiedza_v2:
        raise HTTPException(status_code=404, detail="Nie znaleziono")


# --- modele wejścia ---------------------------------------------------------


class SzukajIn(BaseModel):
    q: str = Field(min_length=1, max_length=szukaj.MAKS_DLUGOSC_ZAPYTANIA)


class WyjasnijIn(BaseModel):
    plan_kind: str = Field(default="training", pattern="^(training|nutrition)$")
    plan_id: str = Field(min_length=1, max_length=40)
    plan_revision: int = Field(ge=1)
    target_type: str = Field(min_length=1, max_length=60)
    target_id: str = Field(min_length=1, max_length=200)
    tryb: str = Field(default="current", pattern="^(current|history)$")


class OdczytIn(BaseModel):
    ukonczone: bool = False


class OpiniaIn(BaseModel):
    article_id: str = Field(min_length=1, max_length=80)
    revision: int = Field(ge=1)
    useful: bool
    note: str | None = Field(default=None, max_length=1000)


class UstawieniaIn(BaseModel):
    personalizacja: bool


class RewizjaIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    summary: str | None = Field(default=None, min_length=1, max_length=2000)
    steps: list[str] | None = None
    detail: str | None = Field(default=None, max_length=20000)
    limits: str | None = Field(default=None, max_length=5000)
    aliases: list[str] | None = None
    tags: list[str] | None = None
    source_ids: list[str] | None = None
    category: str | None = Field(default=None, pattern="^(training|nutrition|progress|basics)$")


class PublikujIn(BaseModel):
    revision: int = Field(ge=1)
    next_review_at: str | None = Field(default=None, max_length=10)


class WycofajIn(BaseModel):
    zamiennik_id: str | None = Field(default=None, max_length=80)


# --- pomocnicze -------------------------------------------------------------


def _plan_klienta(db: Session, user_id: str) -> tuple[TrainingPlan | None, TrainingPlanVersion | None]:
    plany = (
        db.query(TrainingPlan).filter_by(client_id=user_id)
        .order_by(TrainingPlan.created_at.desc()).all()
    )
    plan = next((p for p in plany if p.status == "ACTIVE"), plany[0] if plany else None)
    if plan is None or not plan.current_version_no:
        return plan, None
    v = db.query(TrainingPlanVersion).filter_by(
        plan_id=plan.id, version_no=plan.current_version_no).first()
    return plan, v


def _streszczenie_planu(plan: TrainingPlan | None, v: TrainingPlanVersion | None) -> dict | None:
    if plan is None or v is None:
        return None
    content = json.loads(v.content_json)
    dni = content.get("days") or []
    ids = []
    ma_rir = False
    for d in dni:
        for e in d.get("exercises") or []:
            if e.get("konfigurator_id"):
                ids.append(e["konfigurator_id"])
            if "RIR" in (e.get("comment") or "") or e.get("rir"):
                ma_rir = True
    return {
        "plan_id": plan.id, "title": plan.title, "version_no": v.version_no,
        "version_created_at": v.created_at, "reason": v.reason, "days": len(dni),
        "exercise_ids": sorted(set(ids)), "ma_rir": ma_rir,
        "z_konfiguratora": bool(content.get("konfigurator")),
    }


def _ostatnie_zmiany(db: Session, user_id: str, dzis: date) -> list[dict]:
    od = (dzis - timedelta(days=30)).isoformat()
    out = []
    plany = {p.id: p for p in db.query(TrainingPlan).filter_by(client_id=user_id).all()}
    if plany:
        for v in (db.query(TrainingPlanVersion)
                  .filter(TrainingPlanVersion.plan_id.in_(list(plany)),
                          TrainingPlanVersion.created_at >= od).all()):
            out.append({"plan_kind": "training", "plan_id": v.plan_id, "plan_title": plany[v.plan_id].title,
                        "version_no": v.version_no, "reason": v.reason, "created_at": v.created_at})
    diety = {p.id: p for p in db.query(NutritionPlan).filter_by(client_id=user_id).all()}
    if diety:
        for v in (db.query(NutritionPlanVersion)
                  .filter(NutritionPlanVersion.plan_id.in_(list(diety)),
                          NutritionPlanVersion.created_at >= od).all()):
            out.append({"plan_kind": "nutrition", "plan_id": v.plan_id, "plan_title": diety[v.plan_id].title,
                        "version_no": v.version_no, "reason": v.reason, "created_at": v.created_at})
    slady = {(s.plan_kind, s.plan_id, s.plan_revision) for s in
             db.query(WiedzaSlad.plan_kind, WiedzaSlad.plan_id, WiedzaSlad.plan_revision)
             .filter_by(owner_id=user_id).all()}
    for z in out:
        z["ma_slad"] = (z["plan_kind"], z["plan_id"], z["version_no"]) in slady
    out.sort(key=lambda z: z["created_at"], reverse=True)
    return out[:10]


def _od_trenera(db: Session, user_id: str) -> list[dict]:
    """Mapa migracji: materiały trenera we właściwej części Wiedzy."""
    coach_ids = [r.coach_id for r in db.query(CoachClientRelationship)
                 .filter_by(client_id=user_id, status="ACTIVE").all()]
    if not coach_ids:
        return []
    rows = (db.query(KnowledgeItem)
            .filter(KnowledgeItem.coach_id.in_(coach_ids), KnowledgeItem.status == "ACTIVE")
            .order_by(KnowledgeItem.pinned.desc(), KnowledgeItem.created_at.desc()).all())
    return [{"id": i.id, "title": i.title, "category": i.category,
             "czesc": dane.kategoria_trenera(i.category), "body": i.body,
             "external_url": i.external_url, "file_id": i.file_id, "pinned": i.pinned}
            for i in rows]


def _naglowki_widoczne(db: Session, kategoria: str | None = None) -> list[dict]:
    out = []
    for r in tresci.lista_aktualnych(db, kategoria):
        t = json.loads(r.tresc_json)
        out.append({**tresci.naglowek(r), "aliases": t.get("aliases") or [], "tags": t.get("tags") or []})
    return out


# --- klient -----------------------------------------------------------------


@router.get("/wiedza/start")
def start(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """W1 „Dla Ciebie”: flaga, plan w skrócie, feed (maks. 3), ostatnie
    zmiany, materiały trenera. Bez planu — biblioteka i podstawy."""
    response.headers["Cache-Control"] = PRYWATNE
    if not settings.wiedza_v2:
        return {"wlaczone": False}
    dzis = local_today()
    plan, v = _plan_klienta(db, user.id)
    plan_s = _streszczenie_planu(plan, v)
    dieta = db.query(NutritionPlan).filter_by(client_id=user.id, status="ACTIVE").first() is not None
    zmiany = _ostatnie_zmiany(db, user.id, dzis)
    feed = kanal.dla_ciebie(db, owner_id=user.id, plan=plan_s, dieta=dieta,
                            zmiany_od=[z["created_at"] for z in zmiany], dzis=dzis)
    liczby: dict[str, int] = {k: 0 for k in dane.KATEGORIE}
    for r in tresci.lista_aktualnych(db):
        liczby[r.category] = liczby.get(r.category, 0) + 1
    record_event(db, action="KNOWLEDGE_OPENED", actor_id=user.id, subject_ids=[user.id],
                 payload={"surface": "start", "feed_ids": [f["id"] for f in feed]},
                 summary="Wiedza: otwarto „Dla Ciebie”")
    db.commit()
    return {
        "wlaczone": True, "szkice_widoczne": settings.wiedza_szkice,
        "personalizacja": kanal.personalizacja_wlaczona(db, user.id),
        "plan": plan_s, "dieta": dieta, "dla_ciebie": feed, "ostatnie_zmiany": zmiany,
        "czesci": [{"id": k, "label": v, "liczba": liczby.get(k, 0)} for k, v in dane.KATEGORIE.items()],
        "od_trenera": _od_trenera(db, user.id),
        "zakladki": [z.article_id for z in db.query(WiedzaZakladka).filter_by(owner_id=user.id).all()],
    }


@router.get("/wiedza/artykuly", dependencies=[Depends(wymagaj_v2)])
def lista_artykulow(
    kategoria: str | None = Query(default=None, pattern="^(training|nutrition|progress|basics)$"),
    kursor: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    rows = _naglowki_widoczne(db, kategoria)
    strona = rows[kursor:kursor + limit]
    for r in strona:
        r.pop("aliases", None)
        r.pop("tags", None)
    nastepny = kursor + limit if kursor + limit < len(rows) else None
    return {"items": strona, "total": len(rows), "kursor": nastepny,
            "szkice_widoczne": settings.wiedza_szkice}


@router.get("/wiedza/artykuly/{article_id}", dependencies=[Depends(wymagaj_v2)])
def artykul(article_id: str, response: Response, user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    """Karta W3. Wycofana → 410 z opcjonalnym zamiennikiem."""
    r = tresci.aktualna(db, article_id)
    if r is None:
        w = tresci.wycofana(db, article_id)
        if w is not None:
            zam = tresci.aktualna(db, w.zamiennik_id) if w.zamiennik_id else None
            # JSONResponse, bo globalna obsługa HTTPException spłaszcza detail do tekstu.
            return JSONResponse(status_code=410, content={
                "detail": "Materiał jest aktualizowany.", "code": "RETIRED",
                "zamiennik": tresci.naglowek(zam) if zam else None,
            })
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    out = tresci.pelna(r)
    out["zapisany"] = db.query(WiedzaZakladka).filter_by(
        owner_id=user.id, article_id=article_id).first() is not None
    out["szkice_widoczne"] = settings.wiedza_szkice
    return out


@router.post("/wiedza/szukaj", dependencies=[Depends(wymagaj_v2)])
def szukaj_endpoint(body: SzukajIn, response: Response, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    """Zapytanie idzie w body i NIE jest zapisywane (może zawierać dane
    zdrowotne) — ani w audycie, ani w logach żądań."""
    response.headers["Cache-Control"] = PRYWATNE
    wyniki = szukaj.szukaj(body.q, _naglowki_widoczne(db))
    return {"items": wyniki, "total": len(wyniki)}


@router.post("/wiedza/wyjasnij")
def wyjasnij_endpoint(body: WyjasnijIn, response: Response, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    """W4 „Dlaczego?”. 200 z ExplanationResult (także missing_trace);
    409 STALE_PLAN dla nieaktualnej rewizji w trybie bieżącym; 404 bez
    trace_id ani danych celu dla cudzego planu."""
    wymagaj_v2()
    response.headers["Cache-Control"] = PRYWATNE
    kod, wynik = resolver.wyjasnij(
        db, user, plan_kind=body.plan_kind, plan_id=body.plan_id,
        plan_revision=body.plan_revision, target_type=body.target_type,
        target_id=body.target_id, tryb=body.tryb,
    )
    if kod == 404 or wynik is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    record_event(db, action="KNOWLEDGE_EXPLAINED", actor_id=user.id, subject_ids=[user.id],
                 payload={"plan_kind": body.plan_kind, "plan_id": body.plan_id,
                          "plan_revision": body.plan_revision, "target_type": body.target_type,
                          "status": wynik["status"], "tryb": body.tryb},
                 summary=f"Wiedza: wyjaśnienie {body.target_type} → {wynik['status']}")
    db.commit()
    if kod == 409:
        response.status_code = 409
        return {"detail": "STALE_PLAN", "code": "STALE_PLAN", "wynik": wynik}
    return wynik


@router.get("/wiedza/plany/{plan_kind}/{plan_id}/historia-decyzji", dependencies=[Depends(wymagaj_v2)])
def historia_decyzji(plan_kind: str, plan_id: str, response: Response,
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    """W6: tylko rzeczywiste decyzje (ślady) własnego planu."""
    response.headers["Cache-Control"] = PRYWATNE
    if plan_kind not in ("training", "nutrition"):
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    return {"items": resolver.historia_decyzji(db, user, plan_kind=plan_kind, plan_id=plan_id)}


@router.get("/wiedza/zakladki", dependencies=[Depends(wymagaj_v2)])
def zakladki(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = PRYWATNE
    out = []
    for z in (db.query(WiedzaZakladka).filter_by(owner_id=user.id)
              .order_by(WiedzaZakladka.created_at.desc()).all()):
        r = tresci.aktualna(db, z.article_id)
        if r is not None:
            out.append(tresci.naglowek(r))
        else:
            w = tresci.wycofana(db, z.article_id)
            out.append({"id": z.article_id, "title": w.title if w else z.article_id,
                        "aktualizowany": True, "zamiennik": w.zamiennik_id if w else None})
    return {"items": out}


@router.put("/wiedza/zakladki/{article_id}", dependencies=[Depends(wymagaj_v2)])
def zapisz_zakladke(article_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Idempotentne: ponowne zapisanie nie tworzy drugiej zakładki (K28)."""
    if tresci.aktualna(db, article_id) is None and tresci.wycofana(db, article_id) is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    z = db.query(WiedzaZakladka).filter_by(owner_id=user.id, article_id=article_id).first()
    if z is None:
        db.add(WiedzaZakladka(id=new_id("WZK"), owner_id=user.id, article_id=article_id))
        record_event(db, action="KNOWLEDGE_BOOKMARK_CHANGED", actor_id=user.id, subject_ids=[user.id],
                     payload={"article_id": article_id, "saved": True}, summary="Wiedza: zapisano materiał")
        db.commit()
    return {"zapisany": True}


@router.delete("/wiedza/zakladki/{article_id}", dependencies=[Depends(wymagaj_v2)])
def usun_zakladke(article_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    z = db.query(WiedzaZakladka).filter_by(owner_id=user.id, article_id=article_id).first()
    if z is not None:
        db.delete(z)
        record_event(db, action="KNOWLEDGE_BOOKMARK_CHANGED", actor_id=user.id, subject_ids=[user.id],
                     payload={"article_id": article_id, "saved": False}, summary="Wiedza: usunięto zapis")
        db.commit()
    return {"zapisany": False}


@router.post("/wiedza/odczyty/{article_id}", dependencies=[Depends(wymagaj_v2)])
def odczyt(article_id: str, body: OdczytIn, user: User = Depends(current_user),
           db: Session = Depends(get_db)):
    """Otwarcie karty; `ukonczone` tylko z jawnego działania użytkownika."""
    r = tresci.aktualna(db, article_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    o = db.query(WiedzaOdczyt).filter_by(owner_id=user.id, article_id=article_id).first()
    teraz = now_iso()
    if o is None:
        o = WiedzaOdczyt(id=new_id("WOD"), owner_id=user.id, article_id=article_id, last_opened_at=teraz)
        db.add(o)
    else:
        o.last_opened_at = teraz
    if body.ukonczone:
        o.explicitly_completed_at = teraz
    record_event(db, action="KNOWLEDGE_ARTICLE_OPENED", actor_id=user.id, subject_ids=[user.id],
                 payload={"article_id": article_id, "revision": r.revision, "completed": body.ukonczone},
                 summary="Wiedza: otwarto kartę")
    db.commit()
    return {"ok": True, "last_opened_at": o.last_opened_at,
            "explicitly_completed_at": o.explicitly_completed_at}


@router.post("/wiedza/opinie", dependencies=[Depends(wymagaj_v2)])
def opinia(body: OpiniaIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.query(WiedzaArtykul).filter_by(article_id=body.article_id, revision=body.revision).first() is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    db.add(WiedzaOpinia(id=new_id("WOP"), owner_id=user.id, article_id=body.article_id,
                        revision=body.revision, useful=body.useful, note=body.note))
    record_event(db, action="KNOWLEDGE_HELPFULNESS_SUBMITTED", actor_id=user.id, subject_ids=[user.id],
                 payload={"article_id": body.article_id, "revision": body.revision, "useful": body.useful},
                 summary="Wiedza: odpowiedź „czy pomogło”")
    db.commit()
    return {"ok": True}


@router.put("/wiedza/ustawienia", dependencies=[Depends(wymagaj_v2)])
def ustawienia(body: UstawieniaIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    u = db.get(WiedzaUstawienia, user.id)
    if u is None:
        u = WiedzaUstawienia(owner_id=user.id, personalizacja=body.personalizacja)
        db.add(u)
    else:
        u.personalizacja = body.personalizacja
        u.updated_at = now_iso()
    db.commit()
    return {"personalizacja": u.personalizacja}


# --- trener: redakcja ---------------------------------------------------------


@router.get("/coach/wiedza/artykuly", dependencies=[Depends(wymagaj_v2)])
def redakcja_lista(coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Wszystkie rewizje (także szkice i wycofane) + liczby wg statusu."""
    rows = (db.query(WiedzaArtykul)
            .order_by(WiedzaArtykul.category, WiedzaArtykul.title, WiedzaArtykul.revision).all())
    liczby: dict[str, int] = {}
    for r in rows:
        liczby[r.status] = liczby.get(r.status, 0) + 1
    return {"items": [tresci.naglowek(r) for r in rows], "liczby": liczby,
            "pokrycie": tresci.pokrycie_typow(db), "szkice_widoczne": settings.wiedza_szkice,
            "zrodla": sorted(dane.zrodla_wg_id())}


@router.get("/coach/wiedza/artykuly/{article_id}/{revision}", dependencies=[Depends(wymagaj_v2)])
def redakcja_rewizja(article_id: str, revision: int, coach: User = Depends(require_role("COACH")),
                     db: Session = Depends(get_db)):
    r = db.query(WiedzaArtykul).filter_by(article_id=article_id, revision=revision).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    return tresci.pelna(r)


@router.post("/coach/wiedza/artykuly/{article_id}/rewizje", status_code=201,
             dependencies=[Depends(wymagaj_v2)])
def redakcja_nowa_rewizja(article_id: str, body: RewizjaIn, coach: User = Depends(require_role("COACH")),
                          db: Session = Depends(get_db)):
    try:
        r = tresci.nowa_rewizja(db, article_id=article_id,
                                zmiany=body.model_dump(exclude_none=True), created_by=coach.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Nie znaleziono") from None
    record_event(db, action="KNOWLEDGE_REVISION_CREATED", actor_id=coach.id, subject_ids=[coach.id],
                 payload={"article_id": article_id, "revision": r.revision},
                 summary=f"Wiedza: nowy szkic {article_id} rew. {r.revision}")
    db.commit()
    return tresci.naglowek(r)


@router.post("/coach/wiedza/artykuly/{article_id}/publikuj", dependencies=[Depends(wymagaj_v2)])
def redakcja_publikuj(article_id: str, body: PublikujIn, coach: User = Depends(require_role("COACH")),
                      db: Session = Depends(get_db)):
    """Publikacja po walidacji: treść, źródła z rejestru, recenzent =
    konto trenera, data recenzji = dziś, data kolejnego przeglądu."""
    try:
        r = tresci.publikuj(db, article_id=article_id, revision=body.revision,
                            reviewer_id=coach.id, next_review_at=body.next_review_at)
    except KeyError:
        raise HTTPException(status_code=404, detail="Nie znaleziono") from None
    except tresci.BladPublikacji as e:
        raise HTTPException(status_code=422, detail="Publikacja odrzucona: " + "; ".join(e.powody)) from None
    record_event(db, action="KNOWLEDGE_PUBLISHED", actor_id=coach.id, subject_ids=[coach.id],
                 payload={"article_id": article_id, "revision": r.revision,
                          "next_review_at": r.next_review_at},
                 summary=f"Wiedza: opublikowano {article_id} rew. {r.revision}")
    db.commit()
    return tresci.naglowek(r)


@router.post("/coach/wiedza/artykuly/{article_id}/wycofaj", dependencies=[Depends(wymagaj_v2)])
def redakcja_wycofaj(article_id: str, body: WycofajIn, coach: User = Depends(require_role("COACH")),
                     db: Session = Depends(get_db)):
    if db.query(WiedzaArtykul).filter_by(article_id=article_id).first() is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    n = tresci.wycofaj(db, article_id=article_id, zamiennik_id=body.zamiennik_id)
    record_event(db, action="KNOWLEDGE_RETIRED", actor_id=coach.id, subject_ids=[coach.id],
                 payload={"article_id": article_id, "revisions": n, "zamiennik_id": body.zamiennik_id},
                 summary=f"Wiedza: wycofano {article_id}")
    db.commit()
    return {"wycofane": n}

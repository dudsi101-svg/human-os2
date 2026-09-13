"""Cykl życia szkicu i transakcja publikacji.

Publikacja (jedna transakcja bazy, router robi commit):
uprawnienia → rewizja szkicu → wersja bazowa = bieżąca wersja planu →
walidacja treści (te same schematy co dotychczasowe endpointy wersji) →
brak różnic = brak nowej wersji i brak powiadomienia → nowa niemutowalna
wersja → ChangeSet → aktualizacja aktywnej wersji → OutboxEvent → ślad
Wiedzy → zdarzenie audytu → wynik pod kluczem idempotencji.
Wycofanie transakcji nie zostawia ani wersji, ani zdarzenia.

Outbox: `przetworz_outbox` tworzy wpis centrum klienta (`notify_now`
z `dedup_key=changeset:{id}` — UNIQUE(user_id, dedup_key) w bazie), próbuje
od razu po commicie i ponawia w pętli przypomnień (do 10 prób, rosnący
odstęp). Awaria push nie cofa publikacji.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from .. import notifications
from ..authz import (
    DOMAIN_NUTRITION,
    DOMAIN_TRAINING,
    ResourceAccessDenied,
    resolve_client_access,
)
from ..hos_bridge import record_event
from ..models import (
    ChangeSet,
    Notification,
    NutritionPlan,
    NutritionPlanVersion,
    OutboxEvent,
    PlanDraft,
    PlanReviewTask,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    new_id,
    now_iso,
)
from ..schemas import NutritionVersionIn, PlanVersionIn
from ..wiedza import slad as wiedza_slad
from . import elementy, roznice

MAKS_PROB = 10


class KonfliktRewizji(Exception):
    """Rewizja szkicu z żądania ≠ rewizja w bazie (409 REVISION_CONFLICT)."""

    def __init__(self, aktualna: int):
        super().__init__(f"aktualna rewizja {aktualna}")
        self.aktualna = aktualna


class WymagaSprawdzenia(Exception):
    """Otwarte zadanie sprawdzenia planu po zmianie wywiadu (0.59.0)."""

    def __init__(self, task_ids: list[str], facts: list[str]) -> None:
        super().__init__("wymaga sprawdzenia")
        self.task_ids = task_ids
        self.facts = facts


class KonfliktWersji(Exception):
    """Plan ma już nowszą wersję niż bazowa szkicu (409 BASE_VERSION_CONFLICT)."""

    def __init__(self, aktualna: int):
        super().__init__(f"aktualna wersja {aktualna}")
        self.aktualna = aktualna


class BladPublikacji(ValueError):
    """Treść nie przechodzi walidacji publikacji (422)."""


# --- plan i uprawnienia ---------------------------------------------------------------


def _model(plan_kind: str):
    if plan_kind == "training":
        return TrainingPlan, TrainingPlanVersion, DOMAIN_TRAINING
    if plan_kind == "nutrition":
        return NutritionPlan, NutritionPlanVersion, DOMAIN_NUTRITION
    raise elementy.BladOperacji(f"nieznany rodzaj planu: {plan_kind}")


def plan_trenera(db: Session, coach: User, plan_kind: str, plan_id: str, *, action: str = "write"):
    """Plan istnieje, należy do trenera, a klient (jeśli jest) jest w relacji
    ze zgodą właściwej domeny. Cudzy plan → logowana odmowa (404)."""
    Plan, _V, domena = _model(plan_kind)
    plan = db.get(Plan, plan_id)
    if plan is None or plan.coach_id != coach.id:
        raise ResourceAccessDenied(coach.id, f"{plan_kind}_plan:{plan_id}")
    if plan.client_id is not None:
        resolve_client_access(db, coach, plan.client_id, action=action, domain=domena)
    return plan


def biezaca_wersja(db: Session, plan_kind: str, plan):
    _P, Wersja, _d = _model(plan_kind)
    return (db.query(Wersja).filter_by(plan_id=plan.id, version_no=plan.current_version_no)
            .one_or_none())


def tresc_korzenia(plan_kind: str, plan, wersja) -> dict[str, Any]:
    """Treść wersji + nazwa planu jako pole korzenia (edycja nazwy = szkic)."""
    tresc = json.loads(wersja.content_json) if wersja else {}
    tresc = elementy.znormalizuj(plan_kind, tresc)
    tresc["title"] = plan.title
    return tresc


# --- szkic ---------------------------------------------------------------------------


def aktywny_szkic(db: Session, plan_kind: str, plan_id: str) -> PlanDraft | None:
    return (db.query(PlanDraft).filter_by(plan_kind=plan_kind, plan_id=plan_id, status="ACTIVE")
            .one_or_none())


def utworz_lub_pobierz(db: Session, coach: User, plan_kind: str, plan_id: str) -> tuple[PlanDraft, bool]:
    plan = plan_trenera(db, coach, plan_kind, plan_id)
    szkic = aktywny_szkic(db, plan_kind, plan_id)
    if szkic is not None:
        return szkic, False
    wersja = biezaca_wersja(db, plan_kind, plan)
    baza = tresc_korzenia(plan_kind, plan, wersja)
    szkic = PlanDraft(
        id=new_id("DRF"), plan_kind=plan_kind, plan_id=plan.id, client_id=plan.client_id,
        coach_id=coach.id, base_version_no=plan.current_version_no,
        base_content_json=json.dumps(baza, ensure_ascii=False),
        content_json=json.dumps(baza, ensure_ascii=False),
        revision=1, status="ACTIVE", created_by=coach.id, updated_by=coach.id,
    )
    db.add(szkic)
    db.flush()
    return szkic, True


def szkic_trenera(db: Session, coach: User, draft_id: str) -> PlanDraft:
    szkic = db.get(PlanDraft, draft_id)
    if szkic is None or szkic.coach_id != coach.id:
        raise ResourceAccessDenied(coach.id, f"plan_draft:{draft_id}")
    # Uprawnienia do klienta sprawdzane przy każdej operacji (relacja mogła wygasnąć).
    plan_trenera(db, coach, szkic.plan_kind, szkic.plan_id)
    return szkic


def zastosuj_operacje(db: Session, szkic: PlanDraft, *, revision: int, operacje: list[dict], coach: User) -> PlanDraft:
    if szkic.status != "ACTIVE":
        raise elementy.BladOperacji("szkic nie jest aktywny (opublikowany albo odrzucony)")
    if revision != szkic.revision:
        raise KonfliktRewizji(szkic.revision)
    nowa = elementy.zastosuj(szkic.plan_kind, json.loads(szkic.content_json), operacje)
    szkic.content_json = json.dumps(nowa, ensure_ascii=False)
    szkic.revision += 1
    szkic.updated_by = coach.id
    szkic.updated_at = now_iso()
    return szkic


def roznice_szkicu(szkic: PlanDraft) -> dict[str, Any]:
    r = roznice.porownaj(szkic.plan_kind, json.loads(szkic.base_content_json), json.loads(szkic.content_json))
    r["summary"] = roznice.podsumowanie(szkic.plan_kind, r)
    r["total"] = roznice.liczba_zmian(r)
    return r


def odrzuc(db: Session, szkic: PlanDraft, *, revision: int, coach: User) -> None:
    if revision != szkic.revision:
        raise KonfliktRewizji(szkic.revision)
    szkic.status = "DISCARDED"
    szkic.updated_by = coach.id
    szkic.updated_at = now_iso()


def szkic_out(szkic: PlanDraft) -> dict[str, Any]:
    r = roznice_szkicu(szkic)
    return {
        "id": szkic.id, "plan_kind": szkic.plan_kind, "plan_id": szkic.plan_id,
        "client_id": szkic.client_id, "base_version_no": szkic.base_version_no,
        "revision": szkic.revision, "status": szkic.status,
        "content": json.loads(szkic.content_json), "base_content": json.loads(szkic.base_content_json),
        "changes": r["total"], "summary": r["summary"],
        "updated_at": szkic.updated_at, "updated_by": szkic.updated_by,
    }


# --- walidacja treści przed publikacją ------------------------------------------------


def _waliduj(plan_kind: str, tresc: dict[str, Any]) -> dict[str, Any]:
    """Te same schematy, co dotychczasowe endpointy wersji: szkic może być
    chwilowo niekompletny, publikacja — nie. Zwraca treść do zapisu
    (bez `title` korzenia — nazwa żyje na planie)."""
    tytul = (tresc.get("title") or "").strip()
    if not tytul or len(tytul) > 300:
        raise BladPublikacji("nazwa planu: 1–300 znaków")
    try:
        if plan_kind == "training":
            dni = [d for d in tresc.get("days") or [] if (d.get("name") or "").strip()]
            for d in dni:
                d["exercises"] = [e for e in d.get("exercises") or [] if (e.get("name") or "").strip()]
            if not dni:
                raise BladPublikacji("plan bez dni treningowych — zakończ plan archiwizacją zamiast publikować pusty")
            w = PlanVersionIn(reason="-", days=dni)
            return {"days": [d.model_dump() for d in w.days]}
        w = NutritionVersionIn(
            reason="-", kcal=tresc.get("kcal"), protein_g=tresc.get("protein_g"),
            fat_g=tresc.get("fat_g"), carbs_g=tresc.get("carbs_g"),
            sections=[s for s in tresc.get("sections") or [] if (s.get("title") or s.get("body"))],
            meals=[m for m in tresc.get("meals") or [] if (m.get("name") or "").strip()],
            supplements=tresc.get("supplements") or [], document_id=tresc.get("document_id"),
        )
        out = {"kcal": w.kcal, "protein_g": w.protein_g, "fat_g": w.fat_g, "carbs_g": w.carbs_g,
               "sections": w.sections, "meals": w.meals,
               "supplements": [s.model_dump() for s in w.supplements]}
        # Metadane kreatora dań przechodzą dalej — z oznaczeniem ręcznej zmiany.
        if tresc.get("kulinaria"):
            k = dict(tresc["kulinaria"])
            if any(m.get("edited_manually") for m in out["meals"]):
                k["carb_compliance_verified"] = False
                k["edited_manually"] = True
            out["kulinaria"] = k
        return out
    except ValidationError as e:
        raise BladPublikacji("; ".join(f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()[:5])) from None


# --- publikacja ------------------------------------------------------------------------


def publikuj(db: Session, szkic: PlanDraft, *, coach: User, revision: int, base_version_no: int,
             note: str | None) -> dict[str, Any]:
    """Cała publikacja w jednej transakcji (bez commitu — robi go router,
    a idempotencja zapisuje wynik w tej samej transakcji)."""
    if szkic.status != "ACTIVE":
        raise elementy.BladOperacji("szkic nie jest aktywny")
    if revision != szkic.revision:
        raise KonfliktRewizji(szkic.revision)
    plan = plan_trenera(db, coach, szkic.plan_kind, szkic.plan_id)
    if base_version_no != szkic.base_version_no or plan.current_version_no != szkic.base_version_no:
        raise KonfliktWersji(plan.current_version_no)
    if plan.client_id is not None:
        # „Wymaga sprawdzenia” (0.59.0): zmiana faktów wywiadu istotnych
        # dla planu blokuje publikację zależnej wersji do jawnego
        # rozstrzygnięcia przez trenera.
        otwarte = (db.query(PlanReviewTask)
                   .filter_by(plan_kind=szkic.plan_kind, plan_id=plan.id, status="OPEN").all())
        if otwarte:
            raise WymagaSprawdzenia([t.id for t in otwarte],
                                    sorted({f for t in otwarte for f in json.loads(t.changed_facts_json or "[]")}))
    r = roznice_szkicu(szkic)
    if r["total"] == 0:
        return {"published": False, "reason": "no_changes", "version_no": plan.current_version_no,
                "summary": r["summary"]}
    tresc = json.loads(szkic.content_json)
    do_zapisu = _waliduj(szkic.plan_kind, tresc)
    _P, Wersja, _d = _model(szkic.plan_kind)
    nowy_nr = plan.current_version_no + 1
    powod = r["summary"] + (f" Notatka trenera: {note.strip()}" if note and note.strip() else "")
    wersja = Wersja(
        id=new_id("PLV" if szkic.plan_kind == "training" else "NUV"), plan_id=plan.id,
        version_no=nowy_nr, reason=powod, content_json=json.dumps(do_zapisu, ensure_ascii=False),
        created_by=coach.id,
    )
    if szkic.plan_kind == "nutrition":
        wersja.document_id = do_zapisu.get("document_id") or tresc.get("document_id")
    db.add(wersja)
    plan.title = tresc["title"].strip()
    plan.current_version_no = nowy_nr
    plan.updated_at = now_iso()
    zestaw = ChangeSet(
        id=new_id("CHS"), plan_kind=szkic.plan_kind, plan_id=plan.id, client_id=plan.client_id,
        old_version_no=szkic.base_version_no, new_version_no=nowy_nr,
        diff_json=json.dumps({k: r[k] for k in ("added", "removed", "changed", "moved", "root", "counts")},
                             ensure_ascii=False),
        summary=r["summary"], note=(note or "").strip() or None, author_id=coach.id,
    )
    db.add(zestaw)
    zdarzenie = None
    if plan.client_id is not None:
        zdarzenie = OutboxEvent(
            id=new_id("OBX"), event_type="PLAN_PUBLISHED", aggregate_id=zestaw.id,
            recipient_id=plan.client_id,
            payload_json=json.dumps({"changeset_id": zestaw.id, "plan_kind": szkic.plan_kind,
                                     "plan_id": plan.id, "version_no": nowy_nr,
                                     "summary": r["summary"]}, ensure_ascii=False),
        )
        db.add(zdarzenie)
        # Ślad Wiedzy: decyzja trenera = podsumowanie + notatka (jak dotąd powód wersji).
        if szkic.plan_kind == "training":
            wiedza_slad.slad_wersji_trenera(db, owner_id=plan.client_id, plan_id=plan.id,
                                            plan_revision=nowy_nr, reason=powod)
        else:
            wiedza_slad.slady_diety_trenera(db, owner_id=plan.client_id, plan_id=plan.id,
                                            plan_revision=nowy_nr, content=do_zapisu, reason=powod)
    szkic.status = "PUBLISHED"
    szkic.updated_by = coach.id
    szkic.updated_at = now_iso()
    record_event(
        db, action="PLAN_PUBLISHED", actor_id=coach.id, subject_ids=[plan.client_id or coach.id],
        payload={"plan_kind": szkic.plan_kind, "plan_id": plan.id, "version_no": nowy_nr,
                 "changeset_id": zestaw.id, "counts": r["counts"], "draft_id": szkic.id},
        summary=f"Publikacja zmian planu „{plan.title}” → v{nowy_nr}: {r['summary']}",
    )
    db.flush()
    return {"published": True, "version_no": nowy_nr, "changeset_id": zestaw.id,
            "summary": r["summary"], "outbox_event_id": zdarzenie.id if zdarzenie else None}


# --- outbox --------------------------------------------------------------------------


def _odstep(proba: int) -> timedelta:
    return timedelta(minutes=min(2 ** proba, 120))


def przetworz_outbox(db: Session, *, now_utc: datetime | None = None, limit: int = 50,
                     tylko_id: str | None = None) -> list[Notification]:
    """Doręcza oczekujące zdarzenia: jeden wpis centrum na (zdarzenie,
    odbiorca). Zwraca utworzone powiadomienia (do publish_realtime PO
    commicie). Nigdy nie podnosi wyjątku z kanałów — próba jest liczona."""
    teraz = now_utc or datetime.now(UTC)
    q = db.query(OutboxEvent).filter(OutboxEvent.status == "PENDING")
    if tylko_id:
        q = q.filter(OutboxEvent.id == tylko_id)
    else:
        q = q.filter(OutboxEvent.next_attempt_at <= teraz.isoformat())
    utworzone: list[Notification] = []
    for ev in q.order_by(OutboxEvent.created_at).limit(limit).all():
        ev.attempts += 1
        try:
            dane = json.loads(ev.payload_json)
            if ev.event_type != "PLAN_PUBLISHED":
                # Zdarzenia wywiadu (0.59.0): ten sam outbox, inne treści.
                from ..wywiad import serwis as wywiad_serwis

                n = wywiad_serwis.dorecz_zdarzenie(db, ev, dane)
                if n is not None:
                    utworzone.append(n)
                ev.status = "DELIVERED"
                ev.delivered_at = now_iso()
                ev.last_error = None
                continue
            n = notifications.notify_now(
                db, user_id=ev.recipient_id, category="ZMIANA_PLANU",
                title="Trener zaktualizował Twój plan " + ("treningowy" if dane["plan_kind"] == "training" else "żywieniowy"),
                body=f"{dane['summary']} Zmiany obowiązują od teraz. Zobacz zmiany.",
                url=f"/zmiany/{dane['changeset_id']}",
                source=f"changeset:{dane['changeset_id']}", dedup_key=f"changeset:{dane['changeset_id']}",
            )
            zestaw = db.get(ChangeSet, dane["changeset_id"])
            if n is not None:
                utworzone.append(n)
                if zestaw is not None:
                    zestaw.notification_id = n.id
            elif zestaw is not None and zestaw.notification_id is None:
                # Wpis już istnieje (ponowienie po awarii między notify a
                # oznaczeniem) — odszukujemy go po dedup_key, nie dublujemy.
                istn = (db.query(Notification)
                        .filter_by(user_id=ev.recipient_id, dedup_key=f"changeset:{dane['changeset_id']}")
                        .one_or_none())
                if istn is not None:
                    zestaw.notification_id = istn.id
            ev.status = "DELIVERED"
            ev.delivered_at = now_iso()
            ev.last_error = None
        except Exception as exc:  # noqa: BLE001 — próba policzona, zdarzenie zostaje
            ev.last_error = f"{type(exc).__name__}: {exc}"[:500]
            if ev.attempts >= MAKS_PROB:
                ev.status = "FAILED"
            else:
                ev.next_attempt_at = (teraz + _odstep(ev.attempts)).isoformat()
    db.flush()
    return utworzone


def zestaw_out(db: Session, z: ChangeSet, *, pelny: bool = True) -> dict[str, Any]:
    n = db.get(Notification, z.notification_id) if z.notification_id else None
    out = {
        "id": z.id, "plan_kind": z.plan_kind, "plan_id": z.plan_id, "client_id": z.client_id,
        "old_version_no": z.old_version_no, "new_version_no": z.new_version_no,
        "summary": z.summary, "note": z.note, "author_id": z.author_id, "published_at": z.published_at,
        "notification": {"id": n.id, "created_at": n.created_at, "read_at": n.read_at,
                         "channels": n.channels} if n else None,
    }
    if pelny:
        out["diff"] = json.loads(z.diff_json)
    return out

"""Repozytorium kart wiedzy: import szkiców, widoczność, powiązania,
rewizje, publikacja i wycofanie.

Zasady (plik 04 pakietu):
* rewizja opublikowana jest niezmienna — zmiana = nowa rewizja;
* publikacja wymaga treści we wszystkich polach, źródeł z rejestru,
  prawdziwego recenzenta (konto trenera), daty recenzji i daty
  kolejnego przeglądu;
* po terminie przeglądu karta wypada z rekomendacji i z resolvera;
  karta o bezpieczeństwie (powiązanie `safety`) wypada też z biblioteki;
* szkice widać tylko w trybie demonstracyjnym, nigdy na produkcji.
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy.orm import Session

from ..config import settings
from ..dates import local_today
from ..models import WiedzaArtykul, WiedzaPowiazanie, new_id, now_iso
from . import dane

#: Pola artykułu przechowywane w `tresc_json` (reszta ma własne kolumny).
POLA_TRESCI = (
    "slug", "steps", "detail", "limits", "aliases", "tags", "source_ids",
    "evidence_kind", "author_label", "media", "estimated_read_minutes", "locale",
)

#: Ile miesięcy ważności przeglądu przyjmuje publikacja, gdy trener nie
#: podał daty: 12 (polityka redakcyjna), dla kart bezpieczeństwa 6.
MIESIACE_PRZEGLADU = 12
MIESIACE_PRZEGLADU_BEZPIECZENSTWA = 6


class BladPublikacji(ValueError):
    """Publikacja odrzucona — lista powodów w `powody`."""

    def __init__(self, powody: list[str]):
        super().__init__("; ".join(powody))
        self.powody = powody


# --- import szkiców ---------------------------------------------------------


def _wiersz_z_pakietu(a: dict, *, created_by: str) -> WiedzaArtykul:
    tresc = {k: a.get(k) for k in POLA_TRESCI}
    rev = a["review"]
    return WiedzaArtykul(
        id=new_id("WAR"), article_id=a["id"], revision=int(a["revision"]),
        status=a["status"], category=a["category"], title=a["title"],
        summary=a["summary"], exercise_id=a.get("exercise_id"),
        tresc_json=json.dumps(tresc, ensure_ascii=False),
        review_approved=bool(rev["approved"]), reviewer_id=rev["reviewer_id"],
        reviewed_at=rev["reviewed_at"], next_review_at=rev["next_review_at"],
        created_by=created_by,
    )


def zaimportuj_startowe(db: Session) -> dict[str, int]:
    """Idempotentny import treści startowych po (article_id, revision) —
    nigdy nie nadpisuje istniejących wierszy (zmiany redakcyjne zostają).
    Wywoływany przy starcie aplikacji po migracjach."""
    pakiet = dane.tresci_startowe()
    istniejace = {
        (r.article_id, r.revision)
        for r in db.query(WiedzaArtykul.article_id, WiedzaArtykul.revision).all()
    }
    dodane = 0
    for a in pakiet["articles"]:
        if (a["id"], int(a["revision"])) in istniejace:
            continue
        db.add(_wiersz_z_pakietu(a, created_by="pakiet_wiedza_1.0"))
        dodane += 1
    powiazania = {
        (p.target_type, p.target_key, p.article_id)
        for p in db.query(WiedzaPowiazanie).all()
    }
    dodane_pow = 0
    for b in pakiet["bindings"]:
        klucz = (b["target_type"], b["target_key"], b["article_id"])
        if klucz in powiazania:
            continue
        db.add(WiedzaPowiazanie(id=new_id("WPW"), target_type=b["target_type"],
                                target_key=b["target_key"], article_id=b["article_id"],
                                role=b["role"]))
        dodane_pow += 1
    db.flush()
    return {"artykuly": dodane, "powiazania": dodane_pow}


# --- widoczność -------------------------------------------------------------


def widoczne_statusy() -> tuple[str, ...]:
    return ("published", "draft", "in_review") if settings.wiedza_szkice else ("published",)


def przeglad_wygasl(row: WiedzaArtykul, dzis: date | None = None) -> bool:
    """Po terminie przeglądu materiał wypada z rekomendacji indywidualnych
    i z resolvera (plik 04). Szkice bez daty nie „wygasają” — one po prostu
    nie są opublikowane."""
    if row.status != "published" or not row.next_review_at:
        return False
    return date.fromisoformat(row.next_review_at) < (dzis or local_today())


def czy_bezpieczenstwo(db: Session, article_id: str) -> bool:
    return db.query(WiedzaPowiazanie).filter_by(
        target_type="safety", article_id=article_id).first() is not None


def dostepna_w_bibliotece(db: Session, row: WiedzaArtykul, dzis: date | None = None) -> bool:
    """Karta bezpieczeństwa po terminie znika też z biblioteki; pozostałe
    wyświetla się z datą i oznaczeniem oczekiwania na przegląd."""
    if row.status not in widoczne_statusy():
        return False
    return not (przeglad_wygasl(row, dzis) and czy_bezpieczenstwo(db, row.article_id))


def aktualna(db: Session, article_id: str) -> WiedzaArtykul | None:
    """Najnowsza WIDOCZNA rewizja: opublikowana ma pierwszeństwo przed
    szkicem (tryb demo pokazuje szkic tylko, gdy nie ma publikacji)."""
    rows = (
        db.query(WiedzaArtykul).filter_by(article_id=article_id)
        .order_by(WiedzaArtykul.revision.desc()).all()
    )
    for r in rows:
        if r.status == "published":
            return r
    if settings.wiedza_szkice:
        for r in rows:
            if r.status in ("draft", "in_review"):
                return r
    return None


def wycofana(db: Session, article_id: str) -> WiedzaArtykul | None:
    """Najnowsza rewizja, jeśli artykuł jest wycofany (410 + zamiennik)."""
    r = (
        db.query(WiedzaArtykul).filter_by(article_id=article_id)
        .order_by(WiedzaArtykul.revision.desc()).first()
    )
    return r if r is not None and r.status == "retired" else None


def lista_aktualnych(db: Session, kategoria: str | None = None) -> list[WiedzaArtykul]:
    """Jedna (najnowsza widoczna) rewizja na artykuł, posortowana po
    tytule — biblioteka jest krótka (dziesiątki kart), więc filtr i
    stronicowanie robi się w pamięci, bez indeksu pełnotekstowego."""
    q = db.query(WiedzaArtykul).filter(WiedzaArtykul.status.in_(widoczne_statusy()))
    if kategoria:
        q = q.filter(WiedzaArtykul.category == kategoria)
    wg_id: dict[str, WiedzaArtykul] = {}
    for r in q.order_by(WiedzaArtykul.revision.asc()).all():
        obecna = wg_id.get(r.article_id)
        if obecna is None or _lepsza(r, obecna):
            wg_id[r.article_id] = r
    out = [r for r in wg_id.values() if dostepna_w_bibliotece(db, r)]
    out.sort(key=lambda r: (r.title.lower(), r.article_id))
    return out


def _lepsza(nowa: WiedzaArtykul, stara: WiedzaArtykul) -> bool:
    if (nowa.status == "published") != (stara.status == "published"):
        return nowa.status == "published"
    return nowa.revision > stara.revision


# --- powiązania -------------------------------------------------------------


def powiazane(db: Session, target_type: str, target_key: str | None = None) -> list[WiedzaArtykul]:
    """Karty powiązane z elementem: najpierw klucz konkretny (np.
    `exercise_id`), potem ogólny `*`. Zwraca tylko widoczne rewizje."""
    klucze = [k for k in (target_key, "*") if k]
    rows = (
        db.query(WiedzaPowiazanie)
        .filter(WiedzaPowiazanie.target_type == target_type,
                WiedzaPowiazanie.target_key.in_(klucze))
        .all()
    )
    rows.sort(key=lambda p: (0 if p.target_key != "*" else 1, p.article_id))
    out: list[WiedzaArtykul] = []
    widziane: set[str] = set()
    for p in rows:
        if p.article_id in widziane:
            continue
        a = aktualna(db, p.article_id)
        if a is not None:
            widziane.add(p.article_id)
            out.append(a)
    return out


def pokrycie_typow(db: Session) -> dict[str, bool]:
    """Audyt pokrycia (plik 09, etap 3): każdy znany typ elementu ma
    powiązanie (opublikowane albo szkic) — inaczej jawny brak."""
    typy = {t: False for t in dane.TYPY_ELEMENTOW}
    for p in db.query(WiedzaPowiazanie.target_type).distinct().all():
        if p[0] in typy:
            typy[p[0]] = True
    return typy


# --- serializacja -----------------------------------------------------------


def naglowek(row: WiedzaArtykul, *, dzis: date | None = None) -> dict:
    t = json.loads(row.tresc_json)
    return {
        "id": row.article_id, "revision": row.revision, "status": row.status,
        "category": row.category, "category_label": dane.KATEGORIE.get(row.category, row.category),
        "title": row.title, "summary": row.summary,
        "estimated_read_minutes": t.get("estimated_read_minutes"),
        "evidence_kind": t.get("evidence_kind"), "exercise_id": row.exercise_id,
        "szkic": row.status != "published",
        "przeglad_po_terminie": przeglad_wygasl(row, dzis),
        "next_review_at": row.next_review_at,
    }


def pelna(row: WiedzaArtykul, *, dzis: date | None = None) -> dict:
    t = json.loads(row.tresc_json)
    zr = dane.zrodla_wg_id()
    out = naglowek(row, dzis=dzis)
    out.update({
        "steps": t.get("steps") or [], "detail": t.get("detail") or "",
        "limits": t.get("limits") or "", "aliases": t.get("aliases") or [],
        "tags": t.get("tags") or [], "media": t.get("media"),
        "author_label": t.get("author_label") or "",
        "review": {
            "approved": bool(row.review_approved), "reviewer_id": row.reviewer_id,
            "reviewed_at": row.reviewed_at, "next_review_at": row.next_review_at,
        },
        "sources": [
            {"id": sid, "title": zr[sid].get("title") or zr[sid].get("product"),
             "authors": zr[sid].get("authors"), "year": zr[sid].get("year"),
             "url": zr[sid].get("url"), "type": zr[sid].get("type"), "rola": zr[sid]["rola"]}
            if sid in zr else {"id": sid, "title": sid, "rola": "nieznane"}
            for sid in (t.get("source_ids") or [])
        ],
    })
    return out


def do_schematu(row: WiedzaArtykul) -> dict:
    """Odtwarza obiekt zgodny ze schematem `article` (do walidacji)."""
    t = json.loads(row.tresc_json)
    return {
        "id": row.article_id, "revision": row.revision, "locale": t.get("locale") or "pl-PL",
        "slug": t.get("slug") or row.article_id, "title": row.title, "category": row.category,
        "summary": row.summary, "steps": t.get("steps") or [], "detail": t.get("detail") or "",
        "limits": t.get("limits") or "", "aliases": t.get("aliases") or [],
        "tags": t.get("tags") or [], "source_ids": t.get("source_ids") or [],
        "evidence_kind": t.get("evidence_kind") or "product_rule", "status": row.status,
        "review": {"approved": bool(row.review_approved), "reviewer_id": row.reviewer_id,
                   "reviewed_at": row.reviewed_at, "next_review_at": row.next_review_at},
        "author_label": t.get("author_label") or "", "media": t.get("media"),
        "estimated_read_minutes": t.get("estimated_read_minutes") or 1,
        "exercise_id": row.exercise_id,
    }


# --- redakcja ---------------------------------------------------------------


def nowa_rewizja(db: Session, *, article_id: str, zmiany: dict, created_by: str) -> WiedzaArtykul:
    """Nowy szkic na bazie najnowszej rewizji (opublikowanej lub nie).
    Opublikowana rewizja NIE jest edytowana w miejscu."""
    ostatnia = (
        db.query(WiedzaArtykul).filter_by(article_id=article_id)
        .order_by(WiedzaArtykul.revision.desc()).first()
    )
    if ostatnia is None:
        raise KeyError(article_id)
    t = json.loads(ostatnia.tresc_json)
    for k in POLA_TRESCI:
        if k in zmiany:
            t[k] = zmiany[k]
    row = WiedzaArtykul(
        id=new_id("WAR"), article_id=article_id, revision=ostatnia.revision + 1,
        status="draft", category=zmiany.get("category", ostatnia.category),
        title=zmiany.get("title", ostatnia.title), summary=zmiany.get("summary", ostatnia.summary),
        exercise_id=ostatnia.exercise_id, tresc_json=json.dumps(t, ensure_ascii=False),
        review_approved=False, created_by=created_by,
    )
    db.add(row)
    db.flush()
    return row


def _dodaj_miesiace(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    dzien = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                        31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, dzien)


def publikuj(db: Session, *, article_id: str, revision: int, reviewer_id: str,
             next_review_at: str | None, dzis: date | None = None) -> WiedzaArtykul:
    """Publikacja po walidacji (plik 04). Poprzednia opublikowana rewizja
    tego artykułu przechodzi w `retired` z zamiennikiem = ten sam
    artykuł (zakładki wskazują article_id, więc otwierają nową)."""
    dzis = dzis or local_today()
    row = db.query(WiedzaArtykul).filter_by(article_id=article_id, revision=revision).first()
    if row is None:
        raise KeyError(f"{article_id}@{revision}")
    powody: list[str] = []
    if row.status == "published":
        powody.append("ta rewizja jest już opublikowana")
    if row.status == "retired":
        powody.append("wycofanej rewizji nie publikuje się ponownie — utwórz nową")
    t = json.loads(row.tresc_json)
    for pole in ("steps", "detail", "limits"):
        if not t.get(pole):
            powody.append(f"brak treści w polu {pole}")
    if not row.title.strip() or not row.summary.strip():
        powody.append("brak tytułu lub skrótu")
    zr = dane.zrodla_wg_id()
    zrodla = t.get("source_ids") or []
    if not zrodla:
        powody.append("brak źródeł")
    nieznane = [s for s in zrodla if s not in zr]
    if nieznane:
        powody.append(f"źródła spoza rejestru: {', '.join(nieznane)}")
    if not reviewer_id:
        powody.append("brak recenzenta")
    if next_review_at:
        try:
            termin = date.fromisoformat(next_review_at)
        except ValueError:
            termin = None
            powody.append("data kolejnego przeglądu nie jest datą YYYY-MM-DD")
        if termin is not None and termin <= dzis:
            powody.append("data kolejnego przeglądu musi być w przyszłości")
    else:
        miesiace = (MIESIACE_PRZEGLADU_BEZPIECZENSTWA if czy_bezpieczenstwo(db, article_id)
                    else MIESIACE_PRZEGLADU)
        termin = _dodaj_miesiace(dzis, miesiace)
    if powody:
        raise BladPublikacji(powody)
    for stara in db.query(WiedzaArtykul).filter_by(article_id=article_id, status="published").all():
        stara.status = "retired"
        stara.zamiennik_id = article_id
        stara.updated_at = now_iso()
    row.status = "published"
    row.review_approved = True
    row.reviewer_id = reviewer_id
    row.reviewed_at = dzis.isoformat()
    row.next_review_at = termin.isoformat()  # type: ignore[union-attr]
    row.updated_at = now_iso()
    db.flush()
    return row


def wycofaj(db: Session, *, article_id: str, zamiennik_id: str | None) -> int:
    """Wycofuje wszystkie widoczne rewizje artykułu; zostają w audycie."""
    n = 0
    for r in db.query(WiedzaArtykul).filter_by(article_id=article_id).all():
        if r.status in ("published", "draft", "in_review"):
            r.status = "retired"
            r.zamiennik_id = zamiennik_id
            r.updated_at = now_iso()
            n += 1
    db.flush()
    return n

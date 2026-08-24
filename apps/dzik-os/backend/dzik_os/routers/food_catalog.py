"""Baza produktów spożywczych z makroskładnikami na 100 g (broadcast
trenera, ten sam wzorzec co KnowledgeItem/Exercise), kalkulator porcji
oraz kompozytor diety: przejrzysta arytmetyka podziału celu kcal/makro na
gramaturę WYBRANYCH przez trenera produktów.

Katalog liczy ponad 400 pozycji, więc lista jest **stronicowana i
filtrowana po stronie API** (`q`, `category`, `sort`, `limit`, `offset`) —
widok nigdy nie ładuje całego katalogu „na zapas”.

Uczciwość danych: każda odpowiedź katalogu i kalkulatora niesie
`FOOD_DISCLAIMER` — wartości są uśrednione i przybliżone. Katalog jest
opisowy, nie oceniający: brak twierdzeń zdrowotnych i rekomendacji.

Kompozytor NIGDY nie generuje diety samodzielnie i niczego nie zapisuje —
zwraca tylko sugestię do ręcznego wpisania przez trenera w
NutritionPlanVersion (zasada Human OS: AI/algorytm nie tworzy ani nie
zmienia planu bez udziału człowieka, patrz CLAUDE.md/Constitution)."""

from __future__ import annotations

import csv
import io
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from ..authz import require_owned_resource
from ..config import settings
from ..db import get_db
from ..diet_wizard import Skladnik, zbuduj_propozycje
from ..food_catalog_data import FOOD_DISCLAIMER, FOOD_ROWS_ALL, FOOD_SOURCE
from ..hos_bridge import record_event
from ..models import CoachClientRelationship, FoodProduct, User, new_id, now_iso
from ..schemas import DietSuggestionIn, DietWizardIn, FoodProductIn, PortionCalcIn
from ..security import current_user, require_role
from ..storage import _read_limited

router = APIRouter(prefix="/api", tags=["food-catalog"])

#: Maksymalna liczba wierszy przyjmowana w jednym imporcie CSV.
CSV_MAX_ROWS = 1000
#: Nagłówki pliku CSV (kolejność jak w eksporcie). Wymagane są pierwsze
#: sześć; reszta jest opcjonalna i może zostać pominięta.
CSV_COLUMNS = [
    "nazwa", "kategoria", "kcal_100g", "bialko_100g", "tluszcz_100g", "wegle_100g",
    "blonnik_100g", "porcja_g", "jednostka", "jednostka_g", "zrodlo", "uwagi",
]
CSV_REQUIRED = ["nazwa", "kcal_100g", "bialko_100g", "tluszcz_100g", "wegle_100g"]

#: Dopuszczalne zakresy wartości na 100 g (te same co w FoodProductIn).
KCAL_MAX = 900.0
MACRO_MAX = 100.0

_PL_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ż": "z", "ź": "z",
})


def normalize_name(text: str) -> str:
    """Nazwa sprowadzona do postaci porównywalnej: małe litery, bez polskich
    znaków diakrytycznych. Dzięki temu „lososiowy” trafia w „Łosoś”, a
    „JOGURT” w „Jogurt naturalny 2%”."""
    lowered = text.strip().lower().translate(_PL_MAP)
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _matches(product_name: str, query: str) -> bool:
    """Dopasowanie ścisłe: znormalizowane zapytanie jest fragmentem nazwy."""
    return query in normalize_name(product_name)


def _matches_loose(product_name: str, query: str) -> bool:
    """Dopasowanie luźne (druga próba, gdy ścisła nie dała nic): któreś ze
    słów nazwy (min. 4 znaki) jest fragmentem zapytania — „lososiowy”
    znajduje „Łosoś, surowy”. Świadomie osobny przebieg, żeby normalne
    wyszukiwanie nie zwracało szumu."""
    return any(
        len(token) >= 4 and token in query
        for token in normalize_name(product_name).replace(",", " ").split()
    )


def _out(item: FoodProduct) -> dict:
    return {
        "id": item.id, "coach_id": item.coach_id, "name": item.name,
        "category": item.category, "kcal_100g": item.kcal_100g,
        "protein_100g": item.protein_100g, "fat_100g": item.fat_100g,
        "carbs_100g": item.carbs_100g, "fiber_100g": item.fiber_100g,
        "default_portion_g": item.default_portion_g,
        "unit_name": item.unit_name, "unit_grams": item.unit_grams,
        "source": item.source, "note": item.note,
        # Proweniencja (migracja nr 20): NULL = wpis ręczny albo z CSV,
        # "OCR" = wstępnie wypełniony ze zdjęcia etykiety i zatwierdzony
        # przez trenera (z odniesieniem do pliku źródłowego i silnika).
        "origin_kind": item.origin_kind, "origin_file_id": item.origin_file_id,
        "origin_engine": item.origin_engine,
        "status": item.status, "created_at": item.created_at, "updated_at": item.updated_at,
    }


def _apply_input(item: FoodProduct, body: FoodProductIn) -> None:
    item.name, item.category = body.name, body.category
    item.kcal_100g, item.protein_100g = body.kcal_100g, body.protein_100g
    item.fat_100g, item.carbs_100g = body.fat_100g, body.carbs_100g
    item.fiber_100g = body.fiber_100g
    item.default_portion_g = body.default_portion_g
    item.unit_name, item.unit_grams = body.unit_name, body.unit_grams
    item.source, item.note = body.source, body.note


_SORTS = {
    "name": lambda p: normalize_name(p.name),
    "kcal": lambda p: (-p.kcal_100g, normalize_name(p.name)),
    "protein": lambda p: (-p.protein_100g, normalize_name(p.name)),
}


def _search_page(
    rows: list[FoodProduct], q: str | None, category: str | None,
    sort: str, limit: int, offset: int,
) -> dict:
    """Filtrowanie + sortowanie + stronicowanie katalogu.

    Dopasowanie nazw robimy w Pythonie, bo SQLite nie usuwa znaków
    diakrytycznych — świadomy kompromis dla katalogu rzędu setek pozycji
    na trenera (patrz docs/BAZA_PRODUKTOW.md)."""
    # Lista kategorii pochodzi z CAŁEGO katalogu (przed filtrami), bo służy
    # do zbudowania filtra — inaczej wybór kategorii kasowałby resztę opcji.
    categories = sorted({p.category for p in rows})
    if category:
        rows = [p for p in rows if p.category == category]
    if q:
        needle = normalize_name(q)
        if needle:
            strict = [p for p in rows if _matches(p.name, needle)]
            rows = strict or [p for p in rows if _matches_loose(p.name, needle)]
    rows = sorted(rows, key=_SORTS.get(sort, _SORTS["name"]))
    total = len(rows)
    page = rows[offset:offset + limit]
    return {
        "items": [_out(i) for i in page],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(page) < total,
        "categories": categories,
        "disclaimer": FOOD_DISCLAIMER,
    }


@router.post("/coach/food-products", status_code=201)
def create_food_product(
    body: FoodProductIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = FoodProduct(id=new_id("FOD"), coach_id=coach.id, created_by=coach.id,
                       kcal_100g=0, protein_100g=0, fat_100g=0, carbs_100g=0, name="")
    _apply_input(item, body)
    db.add(item)
    record_event(
        db, action="FOOD_PRODUCT_CREATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"product_id": item.id, "name": item.name},
        summary=f"Baza produktów: dodano „{item.name}”",
    )
    db.commit()
    return _out(item)


@router.get("/coach/food-products")
def list_own_food_products(
    q: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=80),
    sort: str = Query(default="name", pattern="^(name|kcal|protein)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status: str = Query(default="ACTIVE", pattern="^(ACTIVE|ARCHIVED|ALL)$"),
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    query = db.query(FoodProduct).filter(FoodProduct.coach_id == coach.id)
    if status != "ALL":
        query = query.filter(FoodProduct.status == status)
    return _search_page(query.all(), q, category, sort, limit, offset)


@router.put("/coach/food-products/{item_id}")
def update_food_product(
    item_id: str,
    body: FoodProductIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = require_owned_resource(
        db.get(FoodProduct, item_id), actor=coach, resource=f"food_product:{item_id}"
    )
    _apply_input(item, body)
    item.updated_at = now_iso()
    record_event(
        db, action="FOOD_PRODUCT_UPDATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"product_id": item.id, "name": item.name},
        summary=f"Baza produktów: zaktualizowano „{item.name}”",
    )
    db.commit()
    return _out(item)


@router.post("/coach/food-products/{item_id}/status")
def set_food_product_status(
    item_id: str,
    status: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    if status not in {"ACTIVE", "ARCHIVED"}:
        raise HTTPException(status_code=422, detail="Nieprawidłowy status")
    item = require_owned_resource(
        db.get(FoodProduct, item_id), actor=coach, resource=f"food_product:{item_id}"
    )
    item.status = status
    item.updated_at = now_iso()
    db.commit()
    return {"ok": True, "status": status}


def _client_coach_ids(db: Session, user: User) -> list[str]:
    return [
        r.coach_id
        for r in db.query(CoachClientRelationship)
        .filter_by(client_id=user.id, status="ACTIVE")
        .all()
    ]


@router.get("/me/food-products")
def list_food_products_for_client(
    q: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=80),
    sort: str = Query(default="name", pattern="^(name|kcal|protein)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    coach_ids = _client_coach_ids(db, user)
    if not coach_ids:
        return {
            "items": [], "total": 0, "limit": limit, "offset": offset,
            "has_more": False, "categories": [], "disclaimer": FOOD_DISCLAIMER,
        }
    rows = (
        db.query(FoodProduct)
        .filter(FoodProduct.coach_id.in_(coach_ids), FoodProduct.status == "ACTIVE")
        .all()
    )
    return _search_page(rows, q, category, sort, limit, offset)


# --- Kalkulator porcji -------------------------------------------------

def _visible_product(db: Session, user: User, product_id: str) -> FoodProduct:
    """Produkt widoczny dla użytkownika: własny (trener) albo AKTYWNY
    produkt trenera z aktywną relacją (klient). Izolacja jak w PERMISSIONS.md."""
    item = db.get(FoodProduct, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono produktu")
    if item.coach_id == user.id:
        return item
    if item.status == "ACTIVE" and item.coach_id in _client_coach_ids(db, user):
        return item
    raise HTTPException(status_code=404, detail="Nie znaleziono produktu")


def _round(value: float) -> float:
    return round(value, 1)


@router.post("/food-products/portion")
def calculate_portion(
    body: PortionCalcIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Przelicza porcję na kalorie i makro — w gramach albo w jednostkach
    sztukowych produktu („2 jajka” = 110 g). Nic nie zapisuje."""
    if body.grams is not None and body.units is not None:
        raise HTTPException(
            status_code=422, detail="Podaj gramaturę ALBO liczbę sztuk, nie oba naraz"
        )
    item = _visible_product(db, user, body.product_id)
    units = None
    if body.units is not None:
        if not item.unit_grams:
            raise HTTPException(
                status_code=422,
                detail=f"„{item.name}” nie ma zdefiniowanej jednostki sztukowej",
            )
        units = body.units
        grams = units * item.unit_grams
    elif body.grams is not None:
        grams = body.grams
    else:
        grams = item.default_portion_g if item.default_portion_g is not None else 100.0
    factor = grams / 100.0
    return {
        "product_id": item.id,
        "name": item.name,
        "grams": _round(grams),
        "units": units,
        "unit_name": item.unit_name,
        "unit_grams": item.unit_grams,
        "kcal": round(item.kcal_100g * factor),
        "protein_g": _round(item.protein_100g * factor),
        "fat_g": _round(item.fat_100g * factor),
        "carbs_g": _round(item.carbs_100g * factor),
        "fiber_g": _round(item.fiber_100g * factor) if item.fiber_100g is not None else None,
        "note": item.note,
        "source": item.source,
        "disclaimer": FOOD_DISCLAIMER,
    }


# --- Import / eksport CSV ----------------------------------------------

def _csv_value(item: FoodProduct, column: str):
    mapping = {
        "nazwa": item.name, "kategoria": item.category, "kcal_100g": item.kcal_100g,
        "bialko_100g": item.protein_100g, "tluszcz_100g": item.fat_100g,
        "wegle_100g": item.carbs_100g, "blonnik_100g": item.fiber_100g,
        "porcja_g": item.default_portion_g, "jednostka": item.unit_name,
        "jednostka_g": item.unit_grams, "zrodlo": item.source, "uwagi": item.note,
    }
    value = mapping[column]
    return "" if value is None else value


@router.get("/coach/food-products/export")
def export_food_products(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    """Eksport całego katalogu trenera do CSV — prawo wyjścia (portability):
    trener zabiera swoje produkty ze sobą, bez pytania kogokolwiek o zgodę."""
    rows = (
        db.query(FoodProduct)
        .filter(FoodProduct.coach_id == coach.id)
        .order_by(FoodProduct.category, FoodProduct.name)
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=",", lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for item in rows:
        writer.writerow([_csv_value(item, column) for column in CSV_COLUMNS])
    record_event(
        db, action="FOOD_CATALOG_EXPORTED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"rows": len(rows), "format": "csv"},
        summary=f"Baza produktów: eksport {len(rows)} pozycji do CSV",
    )
    db.commit()
    # BOM: arkusze kalkulacyjne otwierają wtedy polskie znaki poprawnie.
    return Response(
        content=("﻿" + buf.getvalue()).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dzik-os-produkty.csv"'},
    )


def _parse_number(raw: str, field: str, *, maximum: float, errors: list, row_no: int):
    """Zwraca liczbę albo None (pusta komórka), dopisując błąd do listy."""
    text = (raw or "").strip().replace(",", ".").replace("\xa0", "").replace(" ", "")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        errors.append({"row": row_no, "field": field, "message": f"„{raw}” to nie liczba"})
        return None
    if value < 0 or value > maximum:
        errors.append({
            "row": row_no, "field": field,
            "message": f"wartość {value} poza dopuszczalnym zakresem 0–{maximum:g}",
        })
        return None
    return value


@router.post("/coach/food-products/import")
async def import_food_products(
    file: UploadFile,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Import katalogu z CSV. Dopisuje lub aktualizuje produkty TEGO trenera
    (dopasowanie po znormalizowanej nazwie) — nigdy cudze. Błędny wiersz jest
    pomijany z opisem przyczyny, reszta pliku importuje się dalej."""
    # Limit jak przy każdym uploadzie — bez tego jeden plik zapełnia RAM
    # (znalezisko K-002 z przeglądu krzyżowego 2026-08-18).
    raw = await _read_limited(file, settings.max_upload_mb * 1024 * 1024)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422, detail="Plik musi być zapisany w kodowaniu UTF-8"
        ) from None
    if not text.strip():
        raise HTTPException(status_code=422, detail="Plik jest pusty")

    first_line = text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in CSV_REQUIRED if c not in headers]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Brak wymaganych kolumn: {', '.join(missing)}. "
                   f"Oczekiwany nagłówek: {', '.join(CSV_COLUMNS)}",
        )
    unknown = [h for h in headers if h and h not in CSV_COLUMNS]

    existing = {
        normalize_name(p.name): p
        for p in db.query(FoodProduct).filter(FoodProduct.coach_id == coach.id).all()
    }
    errors: list[dict] = []
    created = updated = 0
    seen: set[str] = set()
    row_no = 1  # wiersz 1 = nagłówek

    for record in reader:
        row_no += 1
        if row_no - 1 > CSV_MAX_ROWS:
            errors.append({
                "row": row_no, "field": "-",
                "message": f"przekroczono limit {CSV_MAX_ROWS} wierszy — reszta pominięta",
            })
            break
        # Wiersz z nadmiarem kolumn trafia do klucza None jako lista —
        # sprowadzamy wszystko do stringów, żeby nie wywrócić importu.
        cells = {
            (k or "").strip().lower(): (",".join(v) if isinstance(v, list) else (v or ""))
            for k, v in record.items()
        }
        if not any(v.strip() for v in cells.values()):
            continue  # pusty wiersz — cicho pomijamy
        name = cells.get("nazwa", "").strip()
        if not name:
            errors.append({"row": row_no, "field": "nazwa", "message": "nazwa jest wymagana"})
            continue
        if len(name) > 300:
            errors.append({"row": row_no, "field": "nazwa", "message": "nazwa dłuższa niż 300 znaków"})
            continue
        key = normalize_name(name)
        if key in seen:
            errors.append({
                "row": row_no, "field": "nazwa",
                "message": f"„{name}” powtarza się w pliku — wiersz pominięty",
            })
            continue

        before = len(errors)
        kcal = _parse_number(cells.get("kcal_100g", ""), "kcal_100g",
                             maximum=KCAL_MAX, errors=errors, row_no=row_no)
        protein = _parse_number(cells.get("bialko_100g", ""), "bialko_100g",
                                maximum=MACRO_MAX, errors=errors, row_no=row_no)
        fat = _parse_number(cells.get("tluszcz_100g", ""), "tluszcz_100g",
                            maximum=MACRO_MAX, errors=errors, row_no=row_no)
        carbs = _parse_number(cells.get("wegle_100g", ""), "wegle_100g",
                              maximum=MACRO_MAX, errors=errors, row_no=row_no)
        fiber = _parse_number(cells.get("blonnik_100g", ""), "blonnik_100g",
                              maximum=MACRO_MAX, errors=errors, row_no=row_no)
        portion = _parse_number(cells.get("porcja_g", ""), "porcja_g",
                                maximum=5000, errors=errors, row_no=row_no)
        unit_grams = _parse_number(cells.get("jednostka_g", ""), "jednostka_g",
                                   maximum=5000, errors=errors, row_no=row_no)
        if len(errors) > before:
            continue
        for field, value in (("kcal_100g", kcal), ("bialko_100g", protein),
                             ("tluszcz_100g", fat), ("wegle_100g", carbs)):
            if value is None:
                errors.append({"row": row_no, "field": field, "message": "wartość jest wymagana"})
        if len(errors) > before:
            continue

        unit_name = cells.get("jednostka", "").strip()[:60] or None
        if unit_name and not unit_grams:
            errors.append({
                "row": row_no, "field": "jednostka_g",
                "message": "podana jednostka sztukowa wymaga gramatury (jednostka_g)",
            })
            continue
        seen.add(key)
        item = existing.get(key)
        if item is None:
            item = FoodProduct(id=new_id("FOD"), coach_id=coach.id, created_by=coach.id,
                               name=name, kcal_100g=0, protein_100g=0, fat_100g=0,
                               carbs_100g=0)
            db.add(item)
            existing[key] = item
            created += 1
        else:
            updated += 1
        item.name = name
        item.category = cells.get("kategoria", "").strip()[:80] or "Inne"
        item.kcal_100g, item.protein_100g = kcal, protein
        item.fat_100g, item.carbs_100g = fat, carbs
        item.fiber_100g = fiber
        item.default_portion_g = portion
        item.unit_name, item.unit_grams = unit_name, unit_grams
        item.source = cells.get("zrodlo", "").strip()[:200] or None
        item.note = cells.get("uwagi", "").strip()[:300] or None
        item.updated_at = now_iso()

    record_event(
        db, action="FOOD_CATALOG_IMPORTED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"created": created, "updated": updated, "errors": len(errors)},
        summary=f"Baza produktów: import CSV — {created} nowych, {updated} zaktualizowanych, "
                f"{len(errors)} błędnych wierszy",
    )
    db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": len(errors),
        "errors": errors,
        "unknown_columns": unknown,
        "disclaimer": FOOD_DISCLAIMER,
    }


def _dominant_macro(p: FoodProduct) -> str:
    """Kategoria produktu wg makroskładnika o największym udziale
    kalorycznym na 100 g — jawna, deterministyczna reguła (nie ocena AI)."""
    shares = {
        "PROTEIN": p.protein_100g * 4,
        "FAT": p.fat_100g * 9,
        "CARB": p.carbs_100g * 4,
    }
    return max(shares, key=lambda k: shares[k])


def _skladniki_wbudowane() -> list[Skladnik]:
    """Wbudowana baza jako pula dopełniająca kreatora — pozycje oznaczone
    `source="builtin"`, identyfikatory syntetyczne (nie istnieją w bazie
    trenera, więc nie kolidują z niczym)."""
    return [
        Skladnik(
            id=f"builtin:{i}", name=f.name, category=f.category,
            kcal_100g=f.kcal, protein_100g=f.protein, fat_100g=f.fat,
            carbs_100g=f.carbs, unit_name=f.unit_name,
            unit_grams=f.unit_grams, default_portion_g=f.portion_g,
            source="builtin",
        )
        for i, f in enumerate(FOOD_ROWS_ALL)
    ]


@router.post("/coach/food-products/load-builtin", status_code=200)
def load_builtin_food_products(
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Dogrywa wbudowaną bazę produktów do katalogu trenera. Idempotentne:
    pozycje o już istniejącej (znormalizowanej) nazwie są pomijane —
    edycje trenera nigdy nie są nadpisywane."""
    istniejace = {
        normalize_name(p.name)
        for p in db.query(FoodProduct)
        .filter(FoodProduct.coach_id == coach.id)
        .all()
    }
    dodane = 0
    for food in FOOD_ROWS_ALL:
        if normalize_name(food.name) in istniejace:
            continue
        db.add(FoodProduct(
            id=new_id("FOD"), coach_id=coach.id, name=food.name,
            category=food.category, kcal_100g=food.kcal,
            protein_100g=food.protein, fat_100g=food.fat,
            carbs_100g=food.carbs, fiber_100g=food.fiber,
            default_portion_g=food.portion_g,
            unit_name=food.unit_name, unit_grams=food.unit_grams,
            source=FOOD_SOURCE, note=food.note, created_by=coach.id,
        ))
        dodane += 1
    if dodane:
        record_event(
            db, action="FOOD_PRODUCT_CREATED", actor_id=coach.id,
            subject_ids=[coach.id],
            payload={"builtin_import": True, "added": dodane},
            summary=f"Baza produktów: dograno wbudowaną bazę ({dodane} pozycji)",
        )
        db.commit()
    return {
        "added": dodane,
        "skipped": len(FOOD_ROWS_ALL) - dodane,
        "disclaimer": FOOD_DISCLAIMER,
    }


@router.post("/coach/diet-wizard")
def diet_wizard(
    body: DietWizardIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Kreator diety: deterministyczna, regułowa propozycja dnia/tygodnia
    z AKTYWNEGO katalogu trenera, dopełniana jawnie z wbudowanej bazy,
    komponowana wg wzorca śródziemnomorskiego/DASH. Propose-only."""
    produkty = (
        db.query(FoodProduct)
        .filter(FoodProduct.coach_id == coach.id, FoodProduct.status == "ACTIVE")
        .all()
    )
    skladniki = [
        Skladnik(
            id=p.id, name=p.name, category=p.category,
            kcal_100g=p.kcal_100g, protein_100g=p.protein_100g,
            fat_100g=p.fat_100g, carbs_100g=p.carbs_100g,
            unit_name=p.unit_name, unit_grams=p.unit_grams,
            default_portion_g=p.default_portion_g,
        )
        for p in produkty
    ]
    return zbuduj_propozycje(
        skladniki,
        wbudowane=_skladniki_wbudowane(),
        target_kcal=float(body.target_kcal),
        procent={
            "protein": float(body.protein_percent),
            "fat": float(body.fat_percent),
            "carbs": float(body.carbs_percent),
        },
        posilkow_dziennie=body.meals_per_day,
        dni=body.days,
        wykluczone_kategorie=set(body.excluded_categories),
        wykluczone_produkty=set(body.excluded_product_ids),
        preferowane_produkty=set(body.preferred_product_ids),
        maks_minut_na_posilek=body.max_prep_minutes,
    )


@router.post("/coach/diet-suggestion")
def diet_suggestion(
    body: DietSuggestionIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    products = (
        db.query(FoodProduct)
        .filter(FoodProduct.id.in_(body.product_ids), FoodProduct.coach_id == coach.id)
        .all()
    )
    found_ids = {p.id for p in products}
    missing = [pid for pid in body.product_ids if pid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Nie znaleziono produktów: {', '.join(missing)}"
        )

    by_macro: dict[str, list[FoodProduct]] = {"PROTEIN": [], "FAT": [], "CARB": []}
    for p in products:
        by_macro[_dominant_macro(p)].append(p)

    targets = {
        "PROTEIN": ("protein_100g", body.target_protein_g),
        "FAT": ("fat_100g", body.target_fat_g),
        "CARB": ("carbs_100g", body.target_carbs_g),
    }
    entries: list[dict] = []
    warnings: list[str] = []
    for macro, (field, target_g) in targets.items():
        group = by_macro[macro]
        if target_g <= 0:
            continue
        if not group:
            warnings.append(
                f"Brak wybranych produktów z przewagą "
                f"{'białka' if macro == 'PROTEIN' else 'tłuszczu' if macro == 'FAT' else 'węglowodanów'} "
                f"— cel {target_g} g nie może zostać rozłożony na porcje."
            )
            continue
        share_per_product = target_g / len(group)
        for p in group:
            per_100 = getattr(p, field)
            if per_100 <= 0:
                warnings.append(f"„{p.name}” ma zerową wartość {field} — pominięto w podziale.")
                continue
            grams = round(share_per_product / per_100 * 100, 1)
            entries.append(
                {
                    "product_id": p.id,
                    "name": p.name,
                    "macro_role": macro,
                    "grams": grams,
                    "kcal": round(grams / 100 * p.kcal_100g, 1),
                    "protein_g": round(grams / 100 * p.protein_100g, 1),
                    "fat_g": round(grams / 100 * p.fat_100g, 1),
                    "carbs_g": round(grams / 100 * p.carbs_100g, 1),
                    "fiber_g": (
                        round(grams / 100 * p.fiber_100g, 1) if p.fiber_100g is not None else None
                    ),
                    "units": (
                        round(grams / p.unit_grams, 1) if p.unit_grams else None
                    ),
                    "unit_name": p.unit_name,
                }
            )

    totals = {
        "kcal": round(sum(e["kcal"] for e in entries), 1),
        "protein_g": round(sum(e["protein_g"] for e in entries), 1),
        "fat_g": round(sum(e["fat_g"] for e in entries), 1),
        "carbs_g": round(sum(e["carbs_g"] for e in entries), 1),
        "fiber_g": round(sum(e["fiber_g"] or 0 for e in entries), 1),
    }
    target = {
        "kcal": body.target_kcal,
        "protein_g": body.target_protein_g,
        "fat_g": body.target_fat_g,
        "carbs_g": body.target_carbs_g,
    }
    if body.target_kcal > 0:
        delta = round(totals["kcal"] - body.target_kcal, 1)
        if abs(delta) > body.target_kcal * 0.1:
            warnings.append(
                f"Suma kalorii z rozłożonych porcji ({totals['kcal']} kcal) różni się od celu "
                f"({body.target_kcal} kcal) o {delta:+} kcal — dobierz inne produkty lub "
                f"gramaturę ręcznie."
            )
    return {
        "target": target,
        "items": entries,
        "totals": totals,
        "warnings": warnings,
        "disclaimer": FOOD_DISCLAIMER,
        "note": "To wyłącznie sugestia arytmetyczna — nic nie zostało zapisane. "
        "Trener decyduje, czy i jak wpisać to do planu żywieniowego klienta.",
    }

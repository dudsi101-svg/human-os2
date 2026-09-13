"""Dane pakietu kulinarnego i dostęp do wbudowanej bazy produktów.

Pliki w `dane/`:
* `recipes.json` — 300 kart wariantów w 30 rodzinach (pakiet
  właściciela „IMPLEMENTACJA_KREATORA_DIETY_300”, szkice: status draft,
  bez testu kuchennego, bez wartości odżywczych);
* `foods.json` — 73 produkty pakietu (bez wartości; do mapowania);
* `families.json` — spis rodzin;
* `mapowanie_produktow.json` — autorskie mapowanie tej rundy na
  wbudowaną bazę produktów Dzik OS (status „do przeglądu dietetyka”);
* `zrodla.json` — źródła żywieniowe pakietu.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..food_catalog_data import FOOD_ROWS_ALL, FoodRow

KATALOG_DANYCH = Path(__file__).parent / "dane"

#: Wersje danych i silnika zapisywane w treści planu i śladzie.
WERSJE = {"engine": "1.0.0", "recipes": "1.0", "foods": "1.0", "mapping": "1.0",
          "sources_reviewed_on": "2026-09-13"}

#: Etykiety slotów silnika (SLOTS w engine.py).
SLOTY_NAZWY = {"breakfast": "Śniadanie", "main": "Obiad", "snack": "Przekąska", "supper": "Kolacja"}

#: Sprzęt kuchenny z receptur (pełen zestaw = brak filtra po sprzęcie).
SPRZET = ("scale", "hob", "pan", "bowl", "pot", "lid")
SPRZET_NAZWY = {"scale": "waga", "hob": "kuchenka", "pan": "patelnia", "bowl": "miska",
                "pot": "garnek", "lid": "pokrywka"}

ALERGENY = ("gluten", "milk", "eggs", "fish", "soy", "nuts", "sesame")


def _wczytaj(nazwa: str) -> dict:
    return json.loads((KATALOG_DANYCH / nazwa).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def receptury_pakietu() -> list[dict]:
    return _wczytaj("recipes.json")["recipes"]


@lru_cache(maxsize=1)
def produkty_pakietu() -> dict[str, dict]:
    return {x["id"]: x for x in _wczytaj("foods.json")["foods"]}


@lru_cache(maxsize=1)
def rodziny() -> list[dict]:
    return _wczytaj("families.json")["families"]


@lru_cache(maxsize=1)
def mapowanie() -> dict:
    return _wczytaj("mapowanie_produktow.json")


@lru_cache(maxsize=1)
def zrodla() -> dict:
    return _wczytaj("zrodla.json")


@lru_cache(maxsize=1)
def produkty_wg_nazwy() -> dict[str, FoodRow]:
    out: dict[str, FoodRow] = {}
    for r in FOOD_ROWS_ALL:
        out.setdefault(r.name, r)
    return out


def produkt(nazwa: str | None) -> FoodRow | None:
    return produkty_wg_nazwy().get(nazwa) if nazwa else None

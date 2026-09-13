"""Dane pakietu Wiedza: treści startowe, schematy, źródła.

Pliki w `dane/` są kopią pakietu właściciela (1.0, 13.09.2026). Treści
startowe mają status `draft` i `review.approved=false` — produkcja ich
nie pokazuje; publikacja wymaga przeglądu (plik 04 pakietu).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

KATALOG_DANYCH = Path(__file__).parent / "dane"

#: Wersja renderera wyjaśnień — część klucza cache odpowiedzi prywatnych
#: (plik 03, „Cache i prywatność”). Zmiana szablonów tekstu = nowa wersja.
WERSJA_RENDERERA = "1.0"

#: Kategorie kart (schemat `article.category`) → nazwy części Wiedzy.
KATEGORIE: dict[str, str] = {
    "training": "Trening",
    "nutrition": "Odżywianie",
    "progress": "Postępy i regeneracja",
    "basics": "Podstawy i źródła",
}

#: Kategorie materiałów trenera (`knowledge_items.category`, wolny tekst
#: z podpowiedziami) → kategoria Wiedzy. To mapa migracji z pliku 09:
#: stare materiały NIE są usuwane, tylko pokazywane we właściwej części.
MAPA_KATEGORII_TRENERA: dict[str, str] = {
    "trening": "training",
    "dieta": "nutrition",
    "suplementacja": "nutrition",
    "regeneracja": "progress",
    "zdrowie": "basics",
    "motywacja": "basics",
    "inne": "basics",
}

#: Typy elementów planu, dla których istnieje powiązanie ogólne (plik 01,
#: „Pokrycie elementów planu”) — audyt pokrycia w testach porównuje tę
#: listę z powiązaniami treści startowych.
TYPY_ELEMENTOW: tuple[str, ...] = (
    "training_frequency", "work_sets", "rep_range", "rir", "rest", "load",
    "progression", "exercise_replacement", "energy_target", "macro_target",
    "portion", "meal", "ingredient", "meal_replacement", "session_log",
    "progress_chart", "plan_change", "safety", "exercise",
)


def _wczytaj(nazwa: str) -> dict:
    return json.loads((KATALOG_DANYCH / nazwa).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def tresci_startowe() -> dict:
    return _wczytaj("tresci_startowe.json")


@lru_cache(maxsize=1)
def schematy() -> dict:
    return _wczytaj("schematy.json")


@lru_cache(maxsize=1)
def zrodla() -> dict:
    return _wczytaj("zrodla.json")


@lru_cache(maxsize=1)
def zrodla_wg_id() -> dict[str, dict]:
    z = zrodla()
    out: dict[str, dict] = {}
    for s in z["evidence_sources"]:
        out[s["id"]] = {**s, "rola": "merytoryczne"}
    for p in z["product_inspirations"]:
        # Inspiracje produktowe są opisem funkcji producentów — nigdy
        # źródłem porady zdrowotnej (plik 04, „Hierarchia dowodów”).
        out[p["id"]] = {**p, "rola": "inspiracja_produktowa"}
    return out


def kategoria_trenera(kategoria: str | None) -> str:
    return MAPA_KATEGORII_TRENERA.get((kategoria or "").strip().lower(), "basics")

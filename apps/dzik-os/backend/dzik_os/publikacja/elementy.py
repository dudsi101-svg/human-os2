"""Elementy treści planu ze stabilną tożsamością.

Dotąd treść wersji planu to JSON bez identyfikatorów (tożsamość = indeks
tablicy). Szkice potrzebują stabilnych `id`: edycja nie zmienia `id`,
duplikacja dostaje nowe, a różnice liczone są po `id`, nie po pozycji.

Dwa rodzaje planu, jeden model kolekcji:
* `training`: `days[]` → `exercises[]`;
* `nutrition`: `sections[]`, `meals[]`, `supplements[]` (płaskie).
Pola dozwolone w elementach pochodzą ze schematów Pydantic (schemas.py)
plus pola kreatora dań w posiłkach. Wartości pól są sprawdzane dopiero
przy publikacji (te same schematy, co dotychczasowe endpointy wersji) —
szkic ma prawo być chwilowo niekompletny (np. pusty dzień).
"""

from __future__ import annotations

import copy
from typing import Any

from ..models import new_id

RODZAJE = ("training", "nutrition")

#: Kolekcje korzenia i ich dzieci per rodzaj planu.
KOLEKCJE: dict[str, dict[str, str | None]] = {
    "training": {"days": "exercises"},
    "nutrition": {"sections": None, "meals": None, "supplements": None},
}
#: Kolekcja → w jakiej kolekcji-rodzicu żyje (None = korzeń).
RODZIC: dict[str, str | None] = {
    "days": None, "exercises": "days", "sections": None, "meals": None, "supplements": None,
}
#: Pole etykiety elementu (do podsumowań i menu działań).
ETYKIETA = {"days": "name", "exercises": "name", "sections": "title", "meals": "name",
            "supplements": "name"}
#: Pola korzenia dozwolone do zmiany operacją `set` bez `id`.
POLA_KORZENIA = {
    "training": {"title"},
    "nutrition": {"title", "kcal", "protein_g", "fat_g", "carbs_g", "document_id"},
}
#: Pola elementów (bez `id` i bez kolekcji dzieci).
POLA_ELEMENTU: dict[str, set[str]] = {
    "days": {"name", "weekday"},
    "exercises": {"name", "exercise_id", "sets", "reps", "weight", "tempo", "rest", "comment",
                  "video_url", "target_rir", "progression", "konfigurator_id",
                  # rozgrzewka / rozciąganie / cardio (0.73.0) — pola spoza listy
                  # znikają ze szkicu bez błędu, więc muszą tu być
                  "kind", "block_id", "block", "cardio"},
    "sections": {"title", "body"},
    "meals": {"name", "description", "swaps",
              # kreator dań (0.57.0)
              "day", "slot", "recipe_id", "recipe_revision", "portion_variant", "factor",
              "family_id", "draft", "trace_target", "nutrition", "edited_manually"},
    "supplements": {"name", "dose", "timing", "purpose", "source", "form", "duration", "notes",
                    "specialist_consulted"},
}
#: Pola posiłku, których ręczna zmiana unieważnia wartości z kreatora dań.
POLA_POSILKU_KULINARNE = {"name", "description", "portion_variant", "factor", "recipe_id"}


class BladOperacji(ValueError):
    """Niepoprawna operacja na szkicu (422)."""


def nowy_id() -> str:
    return new_id("ELM")


def _kolekcje_korzenia(rodzaj: str) -> list[str]:
    if rodzaj not in KOLEKCJE:
        raise BladOperacji(f"nieznany rodzaj planu: {rodzaj}")
    return list(KOLEKCJE[rodzaj])


def znormalizuj(rodzaj: str, tresc: dict[str, Any]) -> dict[str, Any]:
    """Głęboka kopia treści z `id` na każdym elemencie (brakujące nadane).
    Kolejność i pozostałe pola bez zmian."""
    out = copy.deepcopy(tresc) if isinstance(tresc, dict) else {}
    for kol in _kolekcje_korzenia(rodzaj):
        lista = out.get(kol)
        if not isinstance(lista, list):
            out[kol] = []
            continue
        for el in lista:
            if not isinstance(el, dict):
                raise BladOperacji(f"element kolekcji {kol} nie jest obiektem")
            el.setdefault("id", nowy_id())
            dziecko = KOLEKCJE[rodzaj][kol]
            if dziecko:
                pod = el.get(dziecko)
                if not isinstance(pod, list):
                    el[dziecko] = []
                    continue
                for e2 in pod:
                    if not isinstance(e2, dict):
                        raise BladOperacji(f"element kolekcji {dziecko} nie jest obiektem")
                    e2.setdefault("id", nowy_id())
    return out


def elementy(rodzaj: str, tresc: dict[str, Any]) -> list[tuple[str, str | None, int, dict]]:
    """Wszystkie elementy jako (kolekcja, id_rodzica, indeks, element)."""
    out: list[tuple[str, str | None, int, dict]] = []
    for kol in _kolekcje_korzenia(rodzaj):
        for i, el in enumerate(tresc.get(kol) or []):
            out.append((kol, None, i, el))
            dziecko = KOLEKCJE[rodzaj][kol]
            if dziecko:
                for j, e2 in enumerate(el.get(dziecko) or []):
                    out.append((dziecko, el["id"], j, e2))
    return out


def znajdz(rodzaj: str, tresc: dict[str, Any], element_id: str) -> tuple[str, list, int, dict]:
    """(kolekcja, lista zawierająca, indeks, element) albo BladOperacji."""
    for kol in _kolekcje_korzenia(rodzaj):
        lista = tresc.get(kol) or []
        for i, el in enumerate(lista):
            if el.get("id") == element_id:
                return kol, lista, i, el
            dziecko = KOLEKCJE[rodzaj][kol]
            if dziecko:
                pod = el.get(dziecko) or []
                for j, e2 in enumerate(pod):
                    if e2.get("id") == element_id:
                        return dziecko, pod, j, e2
    raise BladOperacji(f"nie ma elementu o id {element_id}")


def _wszystkie_id(rodzaj: str, tresc: dict[str, Any]) -> set[str]:
    return {el["id"] for _k, _p, _i, el in elementy(rodzaj, tresc)}


def _sprawdz_pola(kol: str, pola: dict[str, Any]) -> None:
    obce = set(pola) - POLA_ELEMENTU[kol] - {"id"}
    if obce:
        raise BladOperacji(f"niedozwolone pola elementu {kol}: {', '.join(sorted(obce))}")


def _nadaj_nowe_id(rodzaj: str, kol: str, element: dict[str, Any]) -> dict[str, Any]:
    """Kopia elementu (z dziećmi) z nowymi `id` — duplikacja."""
    kopia = copy.deepcopy(element)
    kopia["id"] = nowy_id()
    dziecko = KOLEKCJE[rodzaj].get(kol)
    if dziecko:
        for e2 in kopia.get(dziecko) or []:
            e2["id"] = nowy_id()
    return kopia


def _lista_docelowa(rodzaj: str, tresc: dict[str, Any], kol: str, parent_id: str | None) -> list:
    rodzic = RODZIC.get(kol)
    if rodzic is None:
        if kol not in KOLEKCJE[rodzaj]:
            raise BladOperacji(f"kolekcja {kol} nie należy do planu {rodzaj}")
        tresc.setdefault(kol, [])
        return tresc[kol]
    if not parent_id:
        raise BladOperacji(f"element kolekcji {kol} wymaga parent_id ({rodzic})")
    kol_r, _lista, _i, el_r = znajdz(rodzaj, tresc, parent_id)
    if kol_r != rodzic:
        raise BladOperacji(f"parent_id wskazuje {kol_r}, a {kol} należy do {rodzic}")
    el_r.setdefault(kol, [])
    return el_r[kol]


def _oznacz_reczna_zmiane(kol: str, element: dict[str, Any], zmienione: set[str]) -> None:
    """Posiłek z kreatora dań zmieniony ręcznie traci wartości i walidację:
    poprzednie sprawdzenie receptury nie przenosi się na zmienioną treść."""
    if kol == "meals" and element.get("recipe_id") and zmienione & POLA_POSILKU_KULINARNE:
        element["edited_manually"] = True
        element["nutrition"] = None
        element["draft"] = True


def zastosuj(rodzaj: str, tresc: dict[str, Any], operacje: list[dict[str, Any]]) -> dict[str, Any]:
    """Nowa treść po operacjach (wejście nietknięte). Każda operacja jest
    sprawdzana; pierwsza błędna przerywa całość (nic nie jest stosowane
    częściowo — router nie zapisze rewizji)."""
    out = copy.deepcopy(tresc)
    for n, op in enumerate(operacje, 1):
        if not isinstance(op, dict) or "op" not in op:
            raise BladOperacji(f"operacja {n}: brak pola op")
        rodzaj_op = op["op"]
        if rodzaj_op == "set":
            pola = op.get("fields")
            if not isinstance(pola, dict) or not pola:
                raise BladOperacji(f"operacja {n}: set wymaga fields")
            if op.get("id"):
                kol, _lista, _i, el = znajdz(rodzaj, out, op["id"])
                _sprawdz_pola(kol, pola)
                zmienione = {k for k, v in pola.items() if el.get(k) != v}
                el.update(pola)
                _oznacz_reczna_zmiane(kol, el, zmienione)
            else:
                obce = set(pola) - POLA_KORZENIA[rodzaj]
                if obce:
                    raise BladOperacji(f"operacja {n}: niedozwolone pola korzenia: {', '.join(sorted(obce))}")
                out.update(pola)
        elif rodzaj_op == "add":
            kol = op.get("collection")
            element = op.get("item")
            if kol not in POLA_ELEMENTU or not isinstance(element, dict):
                raise BladOperacji(f"operacja {n}: add wymaga collection i item")
            lista = _lista_docelowa(rodzaj, out, kol, op.get("parent_id"))
            nowy = copy.deepcopy(element)
            dziecko = KOLEKCJE[rodzaj].get(kol)
            _sprawdz_pola(kol, {k: v for k, v in nowy.items() if k != dziecko})
            istniejace = _wszystkie_id(rodzaj, out)
            # Cofnięcie usunięcia przysyła element z jego dawnym `id`
            # (i dziećmi) — przyjmujemy, o ile id nie koliduje.
            if not nowy.get("id") or nowy["id"] in istniejace:
                nowy["id"] = nowy_id()
            if dziecko:
                pod = nowy.get(dziecko)
                nowy[dziecko] = pod if isinstance(pod, list) else []
                for e2 in nowy[dziecko]:
                    if not isinstance(e2, dict):
                        raise BladOperacji(f"operacja {n}: element {dziecko} nie jest obiektem")
                    _sprawdz_pola(dziecko, e2)
                    if not e2.get("id") or e2["id"] in istniejace:
                        e2["id"] = nowy_id()
            idx = op.get("index")
            if idx is None or not isinstance(idx, int) or idx < 0 or idx > len(lista):
                lista.append(nowy)
            else:
                lista.insert(idx, nowy)
        elif rodzaj_op == "delete":
            _kol, lista, i, _el = znajdz(rodzaj, out, op.get("id") or "")
            lista.pop(i)
        elif rodzaj_op == "move":
            kol, lista, i, el = znajdz(rodzaj, out, op.get("id") or "")
            cel = lista
            if op.get("parent_id") is not None and RODZIC.get(kol):
                cel = _lista_docelowa(rodzaj, out, kol, op["parent_id"])
            lista.pop(i)
            idx = op.get("index")
            if not isinstance(idx, int) or idx < 0:
                raise BladOperacji(f"operacja {n}: move wymaga index >= 0")
            cel.insert(min(idx, len(cel)), el)
        elif rodzaj_op == "duplicate":
            kol, lista, i, el = znajdz(rodzaj, out, op.get("id") or "")
            lista.insert(i + 1, _nadaj_nowe_id(rodzaj, kol, el))
        elif rodzaj_op == "replace":
            nowa = op.get("content")
            if not isinstance(nowa, dict):
                raise BladOperacji(f"operacja {n}: replace wymaga content")
            zn = znormalizuj(rodzaj, nowa)
            for kol_, _p, _i, el in elementy(rodzaj, zn):
                _sprawdz_pola(kol_, {k: v for k, v in el.items() if k != KOLEKCJE[rodzaj].get(kol_)})
            obce = set(zn) - POLA_KORZENIA[rodzaj] - set(KOLEKCJE[rodzaj])
            if obce:
                raise BladOperacji(f"operacja {n}: niedozwolone pola korzenia: {', '.join(sorted(obce))}")
            out = zn
        else:
            raise BladOperacji(f"operacja {n}: nieznana operacja {rodzaj_op}")
    # Tożsamość musi być unikalna po każdej serii operacji.
    ids = [el["id"] for _k, _p, _i, el in elementy(rodzaj, out)]
    if len(ids) != len(set(ids)):
        raise BladOperacji("powtórzony identyfikator elementu")
    return out


def liczba_elementow(rodzaj: str, element_kol: str, element: dict[str, Any]) -> int:
    """Ile elementów (wraz z podrzędnymi) zniknie przy usunięciu — do
    potwierdzenia w interfejsie („usuwasz dzień X i 5 ćwiczeń”)."""
    dziecko = KOLEKCJE[rodzaj].get(element_kol)
    return 1 + (len(element.get(dziecko) or []) if dziecko else 0)

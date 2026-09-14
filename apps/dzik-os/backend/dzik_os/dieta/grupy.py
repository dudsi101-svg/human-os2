"""Grupy pokrewne zamienników (wymiany v2, 0.69.0).

Poziom 1 wymiany = ta sama `substitution_group`; poziom 2 = grupa pokrewna z pliku
`dane/grupy_pokrewne.json` (pary symetryczne, powód po polsku, `enabled`, `status`).
Plik jest PROPOZYCJĄ do przeglądu trenera/dietetyka — pary oznaczone przez właściciela
„(?)” są wyłączone (`enabled: false`). Walidacja przy ładowaniu: obie grupy istnieją
w `produkty.csv`, brak duplikatów (także odwróconych), `a != b`, znane statusy.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

STATUSY = ("PROPOZYCJA", "PROPOZYCJA_NIEPEWNA", "ZATWIERDZONE", "ODRZUCONE")


def waliduj(dane: dict, grupy_istniejace: set[str] | None = None) -> None:
    """ValueError z konkretnym powodem — plik danych nie może być „prawie dobry”."""
    if not isinstance(dane, dict) or not isinstance(dane.get("links"), list):
        raise TypeError("grupy_pokrewne.json: brak listy `links`")
    widziane: set[frozenset[str]] = set()
    for i, l in enumerate(dane["links"]):
        a, b = str(l.get("a") or ""), str(l.get("b") or "")
        if not a or not b:
            raise ValueError(f"grupy_pokrewne.json: para #{i} bez nazwy grupy")
        if a == b:
            raise ValueError(f"grupy_pokrewne.json: para #{i} łączy grupę {a} z samą sobą")
        if not str(l.get("reason") or "").strip():
            raise ValueError(f"grupy_pokrewne.json: para {a}–{b} bez powodu")
        if l.get("status") not in STATUSY:
            raise ValueError(f"grupy_pokrewne.json: para {a}–{b} ma nieznany status {l.get('status')!r}")
        if not isinstance(l.get("enabled"), bool):
            raise TypeError(f"grupy_pokrewne.json: para {a}–{b} bez `enabled` (bool)")
        klucz = frozenset((a, b))
        if klucz in widziane:
            raise ValueError(f"grupy_pokrewne.json: para {a}–{b} zdublowana (także w odwrotnej kolejności)")
        widziane.add(klucz)
        if grupy_istniejace is not None:
            for g in (a, b):
                if g not in grupy_istniejace:
                    raise ValueError(f"grupy_pokrewne.json: grupa {g!r} nie istnieje w produkty.csv")


@lru_cache(maxsize=1)
def wczytaj() -> dict:
    tekst = resources.files("dzik_os.dieta").joinpath("dane/grupy_pokrewne.json").read_text(encoding="utf-8")
    dane = json.loads(tekst)
    waliduj(dane)
    return dane


def pokrewne(dane: dict | None = None, *, tylko_wlaczone: bool = True) -> dict[str, dict[str, str]]:
    """grupa → {grupa pokrewna: powód}; symetrycznie; domyślnie tylko `enabled`."""
    dane = dane if dane is not None else wczytaj()
    out: dict[str, dict[str, str]] = {}
    for l in dane["links"]:
        if tylko_wlaczone and not l.get("enabled"):
            continue
        out.setdefault(l["a"], {})[l["b"]] = l["reason"]
        out.setdefault(l["b"], {})[l["a"]] = l["reason"]
    return out

"""Wyszukiwanie w opublikowanych tekstach ogólnych (W7).

Przeszukiwane są tytuły, aliasy, tagi i skróty widocznych kart — nigdy
prywatne wyjaśnienia. Polskie znaki są sprowadzane do ASCII (łóżko →
lozko), literówki tolerowane w granicy jednej zmiany dla dłuższych
słów, synonimy wynikają z aliasów kart („zapas”, „RIR”, „powtórzenia
w zapasie”). Zapytanie nie jest nigdzie zapisywane.
"""

from __future__ import annotations

import re
import unicodedata

MAKS_DLUGOSC_ZAPYTANIA = 200
MAKS_WYNIKOW = 20

_PL = str.maketrans({"ł": "l", "Ł": "l"})


def normalizuj(tekst: str) -> str:
    t = (tekst or "").translate(_PL)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return t.lower()


def tokeny(tekst: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", normalizuj(tekst)) if t]


def odleglosc_do_1(a: str, b: str) -> bool:
    """Czy odległość edycyjna a↔b ≤ 1 (bez pełnej macierzy)."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    i = j = 0
    roznice = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        roznice += 1
        if roznice > 1:
            return False
        if len(a) == len(b):
            i += 1
            j += 1
        elif len(a) > len(b):
            i += 1
        else:
            j += 1
    return roznice + (len(a) - i) + (len(b) - j) <= 1


def _dopasowanie(token: str, slowa: list[str]) -> bool:
    for s in slowa:
        if s == token or s.startswith(token) and len(token) >= 3:
            return True
        if len(token) >= 5 and odleglosc_do_1(token, s):
            return True
    return False


def szukaj(zapytanie: str, karty: list[dict]) -> list[dict]:
    """`karty`: nagłówki z polami id, revision, title, summary, category,
    category_label, aliases, tags. Zwraca posortowane trafienia z
    fragmentem (skrótem) i tematem."""
    q = (zapytanie or "").strip()[:MAKS_DLUGOSC_ZAPYTANIA]
    q_tok = tokeny(q)
    if not q_tok:
        return []
    q_norm = " ".join(q_tok)
    wyniki = []
    for k in karty:
        tytul = tokeny(k["title"])
        aliasy = [normalizuj(a) for a in k.get("aliases") or []]
        alias_tok = [t for a in aliasy for t in tokeny(a)]
        tagi = tokeny(" ".join(k.get("tags") or []))
        skrot = tokeny(k.get("summary") or "")
        punkty = 0
        if any(q_norm == a or (len(q_norm) >= 3 and q_norm in a) for a in aliasy):
            punkty += 4
        for t in q_tok:
            if _dopasowanie(t, tytul):
                punkty += 3
            if _dopasowanie(t, alias_tok):
                punkty += 3
            if _dopasowanie(t, tagi):
                punkty += 2
            if _dopasowanie(t, skrot):
                punkty += 1
        if punkty > 0:
            wyniki.append((-punkty, normalizuj(k["title"]), k["id"], k))
    wyniki.sort(key=lambda x: (x[0], x[1], x[2]))
    return [{"id": k["id"], "revision": k["revision"], "title": k["title"],
             "fragment": k.get("summary") or "", "category": k["category"],
             "category_label": k.get("category_label"), "szkic": k.get("szkic", False),
             "punkty": -p}
            for p, _t, _i, k in wyniki[:MAKS_WYNIKOW]]

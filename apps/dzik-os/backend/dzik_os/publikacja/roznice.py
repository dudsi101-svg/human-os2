"""Różnice między migawką bazową a treścią szkicu — po `id`, nie po pozycji.

Zasady ze specyfikacji właściciela:
* dodanie i usunięcie tego samego nowego elementu przed publikacją nie
  jest zmianą (element nie występuje po żadnej stronie);
* przestawienie elementów JEST zmianą;
* przeliczenie wartości pochodnych (np. `nutrition` posiłku) nie tworzy
  osobnych wpisów — pola pochodne są pomijane w porównaniu pól;
* usunięte elementy pozostają czytelne w podsumowaniu (pełna treść
  „przed”), mimo że nie ma ich w bieżącym planie;
* zamiana ćwiczenia zapisuje stare i nowe odniesienie (pola `name`
  i `exercise_id` w liście zmienionych pól).
Podsumowanie po polsku jest deterministyczne (bez LLM).
"""

from __future__ import annotations

from typing import Any

from . import elementy

#: Pola pochodne / techniczne pomijane w porównaniu pól elementu.
POLA_POMIJANE = {"id", "nutrition", "trace_target", "draft"}

#: Formy liczebnikowe: (1, 2–4, 5+) w bierniku (bo „dodano / zmieniono / usunięto …”).
NAZWY = {
    "days": ("dzień", "dni", "dni"),
    "exercises": ("ćwiczenie", "ćwiczenia", "ćwiczeń"),
    "sections": ("sekcję", "sekcje", "sekcji"),
    "meals": ("posiłek", "posiłki", "posiłków"),
    "supplements": ("suplement", "suplementy", "suplementów"),
}
NAZWY_ROOT = {
    "title": "nazwę planu", "kcal": "cel kaloryczny", "protein_g": "cel białka",
    "fat_g": "cel tłuszczu", "carbs_g": "cel węglowodanów", "document_id": "dokument diety",
}


def odmiana(n: int, formy: tuple[str, str, str]) -> str:
    if n == 1:
        return formy[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return formy[1]
    return formy[2]


def _etykieta(kol: str, el: dict[str, Any]) -> str:
    return str(el.get(elementy.ETYKIETA[kol]) or "(bez nazwy)")


def _pola(kol: str, el: dict[str, Any], rodzaj: str) -> dict[str, Any]:
    dziecko = elementy.KOLEKCJE[rodzaj].get(kol)
    return {k: v for k, v in el.items() if k not in POLA_POMIJANE and k != dziecko}


def _indeks(rodzaj: str, tresc: dict[str, Any]) -> dict[str, tuple[str, str | None, int, dict]]:
    return {el["id"]: (kol, rodzic, i, el) for kol, rodzic, i, el in elementy.elementy(rodzaj, tresc)}


def porownaj(rodzaj: str, baza: dict[str, Any], nowa: dict[str, Any]) -> dict[str, Any]:
    """Strukturalne różnice: dodane, usunięte, zmienione (pole: przed → po),
    przestawione (także przeniesione między dniami) i pola korzenia."""
    ib, inw = _indeks(rodzaj, baza), _indeks(rodzaj, nowa)
    # Dziecko dodanego/usuniętego rodzica nie jest osobnym wpisem — los
    # zawartości grupy pokazuje `children` (np. „usunięto dzień B i 5 ćwiczeń”).
    dodane = [{"collection": k, "parent_id": p, "id": i, "label": _etykieta(k, el),
               "item": _pola(k, el, rodzaj),
               "children": len(el.get(elementy.KOLEKCJE[rodzaj].get(k) or "") or [])}
              for i, (k, p, _idx, el) in inw.items() if i not in ib and (p is None or p in ib)]
    usuniete = [{"collection": k, "parent_id": p, "id": i, "label": _etykieta(k, el),
                 "item": _pola(k, el, rodzaj),
                 "children": len(el.get(elementy.KOLEKCJE[rodzaj].get(k) or "") or [])}
                for i, (k, p, _idx, el) in ib.items() if i not in inw and (p is None or p in inw)]
    zmienione = []
    for i, (k, _p, _idx, el_n) in inw.items():
        if i not in ib:
            continue
        el_b = ib[i][3]
        pb, pn = _pola(k, el_b, rodzaj), _pola(k, el_n, rodzaj)
        pola = [{"field": f, "before": pb.get(f), "after": pn.get(f)}
                for f in sorted(set(pb) | set(pn)) if pb.get(f) != pn.get(f)]
        if pola:
            zmienione.append({"collection": k, "id": i, "label": _etykieta(k, el_n),
                              "label_before": _etykieta(k, el_b), "fields": pola})
    # Przestawienia: kolejność elementów wspólnych w obrębie tej samej listy
    # (kolekcja + rodzic) — porównujemy sekwencje id po odjęciu dodanych/usuniętych.
    przestawione = []
    def _sekwencje(idx: dict) -> dict[tuple[str, str | None], list[str]]:
        out: dict[tuple[str, str | None], list[str]] = {}
        for i, (k, p, _n, _el) in sorted(idx.items(), key=lambda kv: kv[1][2]):
            out.setdefault((k, p), []).append(i)
        return out
    sb, sn = _sekwencje(ib), _sekwencje(inw)
    wspolne = set(ib) & set(inw)
    for klucz, seq_n in sn.items():
        seq_b = [i for i in sb.get(klucz, []) if i in wspolne and inw[i][:2] == ib[i][:2]]
        seq_n2 = [i for i in seq_n if i in wspolne and inw[i][:2] == ib[i][:2]]
        for poz, i in enumerate(seq_n2):
            if i in seq_b and seq_b.index(i) != poz:
                k = inw[i][0]
                przestawione.append({"collection": k, "id": i, "label": _etykieta(k, inw[i][3]),
                                     "from": seq_b.index(i), "to": poz})
    # Przeniesienia między rodzicami (np. ćwiczenie do innego dnia).
    for i in wspolne:
        if inw[i][1] != ib[i][1]:
            k = inw[i][0]
            przestawione.append({"collection": k, "id": i, "label": _etykieta(k, inw[i][3]),
                                 "from_parent": ib[i][1], "to_parent": inw[i][1]})
    korzen = []
    for f in sorted(elementy.POLA_KORZENIA[rodzaj]):
        if baza.get(f) != nowa.get(f):
            korzen.append({"field": f, "before": baza.get(f), "after": nowa.get(f)})
    return {
        "added": dodane, "removed": usuniete, "changed": zmienione, "moved": przestawione,
        "root": korzen,
        "counts": {"added": len(dodane), "removed": len(usuniete), "changed": len(zmienione),
                   "moved": len(przestawione), "root": len(korzen)},
    }


def czy_puste(roznice: dict[str, Any]) -> bool:
    return not any(roznice["counts"].values())


def _fraza(czasownik: str, wpisy: list[dict[str, Any]]) -> list[str]:
    liczby: dict[str, int] = {}
    for w in wpisy:
        liczby[w["collection"]] = liczby.get(w["collection"], 0) + 1
    return [f"{czasownik} {n} {odmiana(n, NAZWY[k])}" for k, n in liczby.items()]


def podsumowanie(rodzaj: str, roznice: dict[str, Any]) -> str:
    """„Zmieniono 2 ćwiczenia, usunięto 1 dzień i dodano 1 posiłek.”"""
    czesci: list[str] = []
    czesci += _fraza("zmieniono", roznice["changed"])
    czesci += _fraza("dodano", roznice["added"])
    czesci += _fraza("usunięto", roznice["removed"])
    czesci += _fraza("przestawiono", roznice["moved"])
    for r in roznice["root"]:
        czesci.append(f"zmieniono {NAZWY_ROOT.get(r['field'], r['field'])}")
    if not czesci:
        return "Bez zmian."
    if len(czesci) == 1:
        tekst = czesci[0]
    else:
        tekst = ", ".join(czesci[:-1]) + " i " + czesci[-1]
    return tekst[0].upper() + tekst[1:] + "."


def liczba_zmian(roznice: dict[str, Any]) -> int:
    return sum(roznice["counts"].values())

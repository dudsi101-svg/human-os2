"""Pomiar podaży zamienników (wymiany produktów v2) — dowód rundy, nie test.

Bez bazy: produkty z `dieta/dane/produkty.csv`, szablon z `dieta/dane/szablony/`,
skalowanie silnikiem, dla każdego składnika wymienialnego `swap_candidates` bez
wykluczeń. Wynik: tabela per kaloryczność — posiłki nie-OK i składniki bez
żadnego kandydata (z listą). Uruchomienie z `apps/dzik-os`:

    python tools/pomiar_wymian.py [--kcal 1600 2000 2600] [--szablon template_standard_v1] [--role P C F NONE]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from dzik_os.dieta import silnik as S  # noqa: E402

DANE = BACKEND / "dzik_os" / "dieta" / "dane"


def produkty() -> S.Products:
    out: S.Products = {}
    with (DANE / "produkty.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["name_pl"]] = S.Produkt(
                name_pl=r["name_pl"], category=r["category"], substitution_group=r["substitution_group"] or "",
                kcal_100=float(r["kcal_100"]), protein_100=float(r["protein_100"]), fat_100=float(r["fat_100"]),
                carbs_100=float(r["carbs_100"]), cooking_tags=r["cooking_tags"] or "", allergens=r["allergens"] or "",
                diet_exclusions=r["diet_exclusions"] or "", default_scaling=r["default_scaling"] or "LINIOWY",
            )
    return out


def pomiar(szablon: str, kcal: float, role: tuple[str, ...], prods: S.Products, *, kandydaci=None) -> dict:
    t = json.loads((DANE / "szablony" / f"{szablon}.json").read_text(encoding="utf-8"))
    dni = S.scale_week(t, kcal, prods)
    kandydaci = kandydaci or (lambda m, i: S.swap_candidates(m, i, prods, exclusions=(), n=len(prods)))
    posilki = [m for d in dni for m in d["meals"]]
    nie_ok = [m for m in posilki if m["status"] != "OK"]
    puste, razem = [], 0
    for m in posilki:
        for i, ing in enumerate(m["ingredients"]):
            if ing["role"] not in role:
                continue
            razem += 1
            if not kandydaci(m, i):
                puste.append((m["name"], ing["product"], ing["role"], m["status"]))
    return {"kcal": kcal, "posilki": len(posilki), "nie_ok": len(nie_ok), "skladniki": razem, "puste": puste}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kcal", nargs="+", type=float, default=[1600, 2000, 2600])
    ap.add_argument("--szablon", default="template_standard_v1")
    ap.add_argument("--role", nargs="+", default=["P", "C", "F"])
    ap.add_argument("--lista", action="store_true", help="wypisz składniki bez kandydata")
    a = ap.parse_args(argv)
    prods = produkty()
    print(f"| szablon | kcal | posiłki nie-OK | składników ({'/'.join(a.role)}) bez kandydata |")
    print("|---|---|---|---|")
    for k in a.kcal:
        w = pomiar(a.szablon, k, tuple(a.role), prods)
        pct = 100 * len(w["puste"]) / w["skladniki"] if w["skladniki"] else 0
        print(f"| {a.szablon} | {k:.0f} | {w['nie_ok']}/{w['posilki']} | **{len(w['puste'])} z {w['skladniki']} ({pct:.0f} %)** |")
        if a.lista:
            for nazwa, prod, r, st in w["puste"]:
                print(f"    - {prod} [{r}] w „{nazwa}” (posiłek: {st})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Test-strażnik pokrycia zamienników (wymiany v2, 0.69.0).

Pomiar z 14.09.2026 (`tools/pomiar_wymian.py`, Standard v1, bez wykluczeń, poziom 1 + 2,
bramka „nie pogarsza” z luzem poniżej rozdzielczości wyświetlania, limity porcji v1.1):
składników z rolą P/C/F bez ŻADNEGO kandydata — 1600 kcal: 7/108 (6 %), 2000 kcal: 3/108
(3 %), 2600 kcal: 9/108 (8 %); rola NONE przy 2000 kcal: 3/124 (2 %). Przed rundą (poziom 1,
bramka absolutna): 20/108, 12/108, 18/108.
Progi poniżej = pomiar + margines 3 punktów procentowych — nie „≤ 0” (kłamstwo), nie 50 %
(ozdoba). Gdy test spadnie: coś zepsuło podaż kandydatów (dane albo silnik)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
PROGI_PCF = {1600: 0.10, 2000: 0.06, 2600: 0.11}  # pomiar 14.09 (po przeglądzie) + 3 pp
PROG_NONE_2000 = 0.05


@pytest.fixture(scope="module")
def pw():
    spec = importlib.util.spec_from_file_location("pomiar_wymian", TOOLS / "pomiar_wymian.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("kcal", sorted(PROGI_PCF))
def test_odsetek_skladnikow_bez_kandydata_ponizej_progu(pw, kcal):
    w = pw.pomiar("template_standard_v1", kcal, ("P", "C", "F"), pw.produkty())
    odsetek = len(w["puste"]) / w["skladniki"]
    assert odsetek <= PROGI_PCF[kcal], (f"{kcal} kcal: {len(w['puste'])}/{w['skladniki']} bez kandydata "
                                        f"({odsetek:.0%} > {PROGI_PCF[kcal]:.0%}): {w['puste']}")


def test_rola_none_ma_kandydatow(pw):
    w = pw.pomiar("template_standard_v1", 2000, ("NONE",), pw.produkty())
    assert len(w["puste"]) / w["skladniki"] <= PROG_NONE_2000, w["puste"]


def test_poziom_2_realnie_zmniejsza_liczbe_pustych_list(pw):
    prods = pw.produkty()
    z = pw.pomiar("template_standard_v1", 2000, ("P", "C", "F"), prods, pokrewne=True)
    bez = pw.pomiar("template_standard_v1", 2000, ("P", "C", "F"), prods, pokrewne=False)
    assert len(z["puste"]) < len(bez["puste"])

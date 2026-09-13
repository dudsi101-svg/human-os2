"""Siedem scenariuszy referencyjnych z pakietu odtwarzane co do bajta."""
import json
from pathlib import Path

import pytest

from dzik_os.konfigurator import generuj_plan, waliduj_plan

PRZYKLADY = json.loads((Path(__file__).parent / "dane" / "konfigurator_plany_28_dni.json").read_text(encoding="utf-8"))["examples"]


@pytest.mark.parametrize("przyklad", PRZYKLADY, ids=[p["id"] for p in PRZYKLADY])
def test_przyklad_odtworzony_co_do_bajta(przyklad):
    wynik = generuj_plan(przyklad["input"], plan_id=przyklad["id"])
    oczek = przyklad["response"]
    assert wynik["status"] == oczek["status"]
    assert json.dumps(wynik, sort_keys=True, ensure_ascii=False) == json.dumps(oczek, sort_keys=True, ensure_ascii=False)
    assert waliduj_plan(wynik, przyklad["input"]) == []


def test_determinizm():
    p = PRZYKLADY[2]
    assert generuj_plan(p["input"], plan_id="X") == generuj_plan(p["input"], plan_id="X")

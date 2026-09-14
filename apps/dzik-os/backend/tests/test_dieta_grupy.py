"""Grupy pokrewne zamienników (wymiany v2): plik danych spójny z produkty.csv."""

from __future__ import annotations

import csv

import pytest

from dzik_os.dieta import grupy
from dzik_os.dieta.seed import _plik


def _grupy_csv() -> set[str]:
    return {r["substitution_group"] for r in csv.DictReader(_plik("produkty.csv").splitlines()) if r["substitution_group"]}


def test_plik_powiazan_laduje_sie_i_kazda_grupa_istnieje():
    dane = grupy.wczytaj()
    grupy.waliduj(dane, _grupy_csv())
    assert dane["status"] == "PROPOZYCJA" and dane["reviewed_by"] is None
    assert len(dane["links"]) == 45


def test_pokrewne_sa_symetryczne_i_pary_niepewne_wylaczone():
    dane = grupy.wczytaj()
    p = grupy.pokrewne(dane)
    for a, sasiedzi in p.items():
        for b in sasiedzi:
            assert a in p[b]
    niepewne = [l for l in dane["links"] if l["status"] == "PROPOZYCJA_NIEPEWNA"]
    assert niepewne and all(l["enabled"] is False for l in niepewne)
    assert "płatki" not in p.get("pieczywo", {})  # (?) wyłączone
    assert "makaron" in p["kasza_ryż"] and "kasza_ryż" in p["makaron"]
    wszystkie = grupy.pokrewne(dane, tylko_wlaczone=False)
    assert "płatki" in wszystkie["pieczywo"]


@pytest.mark.parametrize("zla, blad", [
    ({"links": [{"a": "x", "b": "x", "reason": "r", "enabled": True, "status": "PROPOZYCJA"}]}, "samą sobą"),
    ({"links": [{"a": "kasza_ryż", "b": "makaron", "reason": "r", "enabled": True, "status": "PROPOZYCJA"},
                {"a": "makaron", "b": "kasza_ryż", "reason": "r", "enabled": True, "status": "PROPOZYCJA"}]}, "zdublowana"),
    ({"links": [{"a": "kasza_ryż", "b": "nie_ma", "reason": "r", "enabled": True, "status": "PROPOZYCJA"}]}, "nie istnieje"),
    ({"links": [{"a": "kasza_ryż", "b": "makaron", "reason": "", "enabled": True, "status": "PROPOZYCJA"}]}, "bez powodu"),
    ({"links": [{"a": "kasza_ryż", "b": "makaron", "reason": "r", "enabled": True, "status": "X"}]}, "nieznany status"),
])
def test_walidacja_odrzuca_zle_dane(zla, blad):
    with pytest.raises(ValueError, match=blad):
        grupy.waliduj(zla, _grupy_csv())

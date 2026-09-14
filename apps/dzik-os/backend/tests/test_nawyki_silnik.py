"""Silnik postępu nawyków — przykłady liczone ręcznie."""

from __future__ import annotations

from datetime import date, timedelta

from dzik_os import nawyki as N

D0 = date(2026, 9, 7)  # poniedziałek


def _d(n: int) -> date:
    return D0 + timedelta(days=n)


def test_dni_tygodnia_parsowanie_i_domyslne():
    assert N.dni_tygodnia("1,3, 5") == {1, 3, 5}
    assert N.dni_tygodnia("") == set(range(1, 8))
    assert N.dni_tygodnia("0,8,x") == set(range(1, 8))


def test_zaplanowane_tylko_wybrane_dni_do_dzis_wlacznie():
    plan = N.zaplanowane(D0, _d(6), {1, 3, 5})
    assert plan == [_d(0), _d(2), _d(4)]
    assert N.zaplanowane(_d(3), _d(1), {1}) == []


def test_postep_codziennie_wykonywany():
    p = N.postep(D0, _d(4), set(range(1, 8)), {_d(0), _d(1), _d(2), _d(3), _d(4)})
    assert (p.progress, p.done_count, p.planned_count, p.missed_count) == (5, 5, 5, 0)
    assert p.done_today and p.scheduled_today


def test_decay_minus_jeden_i_podloga_zero_sekwencyjnie():
    # Dni 0,1 wykonane (+2), dni 2,3,4 opuszczone (2→1→0→0), dzień 5 wykonany (1), dziś (6) bez wykonania.
    p = N.postep(D0, _d(6), set(range(1, 8)), {_d(0), _d(1), _d(5)})
    assert p.progress == 1 and p.missed_count == 3 and p.done_count == 3
    assert not p.done_today and p.scheduled_today
    # Długa przerwa nie tworzy długu: po 30 opuszczonych dniach start od zera.
    p2 = N.postep(D0, _d(31), set(range(1, 8)), {_d(31)})
    assert p2.progress == 1


def test_dni_poza_planem_neutralne_a_dzis_nie_karze():
    # Plan pon/śr/pt; wtorek i czwartek nie liczą się w żadną stronę.
    p = N.postep(D0, _d(3), {1, 3, 5}, {_d(0)})
    # pon wykonany (+1), śr opuszczona (0), dziś czwartek — nie zaplanowany.
    assert p.progress == 0 and p.planned_count == 2 and not p.scheduled_today
    # Dziś zaplanowany, ale niewykonany: bez kary.
    p = N.postep(D0, _d(2), {1, 3, 5}, {_d(0)})
    assert p.progress == 1 and p.scheduled_today and not p.done_today


def test_absolutorium_i_opis():
    assert N.absolutorium(66, 66) and not N.absolutorium(65, 66)
    assert N.opis_postepu(0, 66).startswith("0 z 66")
    assert "rozkręca" in N.opis_postepu(10, 66)
    assert "utrwala" in N.opis_postepu(42, 66)
    assert "prawie" in N.opis_postepu(60, 66)
    assert "Twój nawyk" in N.opis_postepu(66, 66)
    for tekst in (N.opis_postepu(3, 14), N.opis_postepu(0, 14)):
        assert "passa" not in tekst and "z rzędu" not in tekst


def test_imie():
    assert N.imie("Anna Wilk") == "Anna"
    assert N.imie("  Marek ") == "Marek"
    assert N.imie("") == "" and N.imie(None) == ""


def test_absolutorium_w_dniu_osiagniecia_terminu_i_bez_decay_po_nim():
    wyk = {_d(n) for n in range(5)}
    # Termin 5: osiągnięty w dniu 4; późniejsze opuszczenia (5, 6) nie cofają.
    p = N.postep(D0, _d(7), set(range(1, 8)), wyk, target_days=5)
    assert p.graduated_on == _d(4) and p.progress == 5
    # Bez terminu: zwykły decay do 3.
    assert N.postep(D0, _d(7), set(range(1, 8)), wyk).progress == 3 and N.postep(D0, _d(7), set(range(1, 8)), wyk).graduated_on is None

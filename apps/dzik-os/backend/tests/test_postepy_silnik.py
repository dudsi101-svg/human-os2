"""Silnik rekordów i wagi (spec Monitoring/Postępy §8–9, testy §14) —
czyste funkcje, bez bazy."""

from __future__ import annotations

from datetime import date, timedelta

from dzik_os.postepy import rekordy as R
from dzik_os.postepy import waga as W


def _s(day: str, sid: str, w: float, r: int, ref: str, **fl) -> R.Seria:
    return R.Seria(set_ref=ref, exercise_key="przysiad ze sztangą", performed_on=day,
                   session_id=sid, weight_kg=w, reps=r, **fl)


def test_pierwsze_wykonanie_nie_jest_rekordem():
    serie = [_s("2026-09-01", "s1", 100, 5, "a:0"), _s("2026-09-01", "s1", 100, 5, "a:1")]
    assert R.licz_rekordy(serie) == {"przysiad ze sztangą": []}


def test_drugie_wykonanie_z_wiekszym_ciezarem_daje_dokladnie_jeden_rekord_weight():
    serie = [_s("2026-09-01", "s1", 100, 5, "a:0"), _s("2026-09-08", "s2", 105, 5, "b:0")]
    rek = R.licz_rekordy(serie)["przysiad ze sztangą"]
    weight = [r for r in rek if r.record_type == "WEIGHT"]
    assert len(weight) == 1
    assert weight[0].value == 105 and weight[0].previous_value == 100 and weight[0].set_ref == "b:0"
    assert weight[0].achieved_on == "2026-09-08" and weight[0].aktualny
    # Cięższa seria przy tych samych powtórzeniach = także SET_VOLUME, SESSION_VOLUME i E1RM,
    # ale REPS_AT_WEIGHT dla nowego ciężaru (105 kg nigdy wcześniej) nie jest rekordem.
    typy = sorted(r.record_type for r in rek)
    assert typy == ["E1RM", "SESSION_VOLUME", "SET_VOLUME", "WEIGHT"]


def test_seria_12_powtorzen_nie_daje_e1rm_ale_daje_set_volume():
    serie = [_s("2026-09-01", "s1", 60, 12, "a:0"), _s("2026-09-08", "s2", 60, 15, "b:0")]
    rek = R.licz_rekordy(serie)["przysiad ze sztangą"]
    assert not [r for r in rek if r.record_type == "E1RM"]
    sv = next(r for r in rek if r.record_type == "SET_VOLUME")
    assert sv.value == 900 and sv.previous_value == 720
    raw = next(r for r in rek if r.record_type == "REPS_AT_WEIGHT")
    assert raw.value == 15 and raw.secondary_value == 60 and raw.previous_value == 12


def test_wyrownanie_rekordu_nie_tworzy_wpisu_i_nie_daje_powiadomienia():
    serie = [_s("2026-09-01", "s1", 100, 5, "a:0"), _s("2026-09-08", "s2", 105, 5, "b:0"),
             _s("2026-09-15", "s3", 105, 5, "c:0")]
    rek = R.licz_rekordy(serie)
    weight = [r for r in rek["przysiad ze sztangą"] if r.record_type == "WEIGHT"]
    assert len(weight) == 1 and weight[0].equaled_on == "2026-09-15" and weight[0].aktualny
    assert R.nowe_w_sesji(rek, "s3") == []  # zero powiadomień za wyrównanie


def test_usuniecie_serii_ustanawiajacej_rekord_cofa_do_poprzedniej_wartosci():
    serie = [_s("2026-09-01", "s1", 100, 5, "a:0"), _s("2026-09-08", "s2", 105, 5, "b:0"),
             _s("2026-09-15", "s3", 110, 5, "c:0")]
    przed = R.aktualne(R.licz_rekordy(serie))["przysiad ze sztangą"]
    assert next(r for r in przed if r.record_type == "WEIGHT").value == 110
    # Korekta: seria 110 kg usunięta → przeliczenie od zera cofa rekord do 105.
    po = R.aktualne(R.licz_rekordy([s for s in serie if s.set_ref != "c:0"]))["przysiad ze sztangą"]
    w = next(r for r in po if r.record_type == "WEIGHT")
    assert w.value == 105 and w.previous_value == 100 and w.set_ref == "b:0"
    # Historia: poprzedni rekord dostaje datę pobicia, gdy 110 istnieje.
    hist = R.licz_rekordy(serie)["przysiad ze sztangą"]
    assert next(r for r in hist if r.value == 105 and r.record_type == "WEIGHT").superseded_on == "2026-09-15"


def test_seria_rozgrzewkowa_ignorowana_we_wszystkich_typach():
    serie = [_s("2026-09-01", "s1", 100, 5, "a:0"),
             _s("2026-09-08", "s2", 140, 3, "b:0", warmup=True),   # „rozgrzewka” 140 kg — pomyłka wpisu
             _s("2026-09-08", "s2", 100, 5, "b:1")]
    rek = R.licz_rekordy(serie)["przysiad ze sztangą"]
    assert rek == []  # bez rozgrzewki sesja 2 = wyrównanie, nie rekord
    # To samo dla nieukończonej i z asekuracją.
    for flaga in ("incomplete", "assisted"):
        s2 = _s("2026-09-08", "s2", 140, 3, "b:0", **{flaga: True})
        assert R.licz_rekordy([serie[0], s2]) == {"przysiad ze sztangą": []}


def test_cwiczenie_z_masa_ciala_bez_obciazenia_nie_daje_weight_ani_e1rm():
    serie = [R.Seria("a:0", "podciąganie", "2026-09-01", "s1", 0, 8),
             R.Seria("b:0", "podciąganie", "2026-09-08", "s2", 0, 10)]
    rek = R.licz_rekordy(serie)["podciąganie"]
    assert [r.record_type for r in rek] == ["REPS_AT_WEIGHT"]
    assert rek[0].value == 10 and rek[0].secondary_value == 0 and rek[0].previous_value == 8


def test_ten_sam_ciezar_w_funtach_i_kilogramach_daje_jeden_rekord():
    kg = R.normalizuj_ciezar(45.36, "kg")
    lb = R.normalizuj_ciezar(100, "lb")
    assert kg == lb == 45.36
    serie = [_s("2026-09-01", "s1", 40, 5, "a:0"), _s("2026-09-08", "s2", kg, 5, "b:0"),
             _s("2026-09-15", "s3", lb, 5, "c:0")]
    weight = [r for r in R.licz_rekordy(serie)["przysiad ze sztangą"] if r.record_type == "WEIGHT"]
    assert len(weight) == 1 and weight[0].equaled_on == "2026-09-15"


def test_klucz_cwiczenia_wariant_to_osobne_cwiczenie_a_blizniak_tylko_raportowany():
    assert R.klucz_cwiczenia("  Wyciskanie  Sztangi leżąc. ") == "wyciskanie sztangi leżąc"
    assert R.klucz_cwiczenia("Wyciskanie hantli leżąc") != R.klucz_cwiczenia("Wyciskanie sztangi leżąc")
    assert R.klucz_blizniaka("Wyciskanie sztangi lezac") == R.klucz_blizniaka("Wyciskanie sztangi leżąc")
    assert R.klucz_cwiczenia("Wyciskanie sztangi lezac") != R.klucz_cwiczenia("Wyciskanie sztangi leżąc")


def test_e1rm_epley_i_jedno_powiadomienie_zbiorcze_na_sesje():
    assert R.epley_e1rm(100, 5) == 116.7 and R.epley_e1rm(100, 1) == 100
    serie = [_s("2026-09-01", "s1", 100, 5, "a:0"), _s("2026-09-08", "s2", 110, 5, "b:0"),
             _s("2026-09-08", "s2", 110, 5, "b:1")]
    nowe = R.nowe_w_sesji(R.licz_rekordy(serie), "s2")
    assert sorted(r.record_type for r in nowe) == ["E1RM", "SESSION_VOLUME", "SET_VOLUME", "WEIGHT"]


# --- waga (§9) ---

def _punkty(start: date, wartosci: list[float | None]) -> list[W.Punkt]:
    return W.pomiary([(start + timedelta(days=i), v) for i, v in enumerate(wartosci) if v is not None])


def test_dwa_pomiary_w_oknie_7_dni_nie_daja_punktu_sredniej():
    start = date(2026, 9, 1)
    pkt = _punkty(start, [80.0, None, None, 79.5])
    assert W.srednia_kroczaca(pkt) == []
    pkt3 = _punkty(start, [80.0, None, 79.6, 79.5])
    assert [p.value for p in W.srednia_kroczaca(pkt3)] == [79.7]  # dopiero 3 pomiary w oknie


def test_trend_przy_10_dniach_danych_to_komunikat_zamiast_liczby():
    start = date(2026, 9, 1)
    pkt = _punkty(start, [80.0 - 0.05 * i for i in range(10)])
    assert W.trend_kg_na_tydzien(pkt, today=start + timedelta(days=9)) is None
    pkt14 = _punkty(start, [80.0 - 0.1 * i for i in range(14)])
    # 0,1 kg/dzień = −0,7 kg/tydz; pierwsze punkty średniej mają krótsze okno
    # (3–6 pomiarów), więc nachylenie po średniej jest odrobinę spłaszczone.
    assert -0.7 <= W.trend_kg_na_tydzien(pkt14, today=start + timedelta(days=13)) <= -0.6


def test_pojedynczy_skok_o_2_kg_nie_zmienia_trendu_o_wiecej_niz_0_2():
    start = date(2026, 9, 1)
    baza = [80.0 - 0.1 * i for i in range(28)]
    today = start + timedelta(days=27)
    t0 = W.trend_kg_na_tydzien(_punkty(start, baza), today=today)
    assert t0 == -0.7
    for pozycja in (5, 14, 20, 27):
        ze_skokiem = list(baza)
        ze_skokiem[pozycja] += 2.0
        t1 = W.trend_kg_na_tydzien(_punkty(start, ze_skokiem), today=today)
        assert abs(t1 - t0) <= 0.2, (pozycja, t0, t1)


def test_klientowi_pokazujemy_srednia_nie_ostatni_pomiar():
    start = date(2026, 9, 1)
    pkt = _punkty(start, [80.0, 80.2, 79.8, 82.0])  # ostatni pomiar 82 (skok)
    assert W.biezaca_srednia(pkt) == 80.5 and pkt[-1].value == 82.0

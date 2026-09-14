"""Silnik zapotrzebowania kalorycznego — przykłady kontrolne liczone ręcznie."""

from __future__ import annotations

import pytest

from dzik_os.wywiad import zapotrzebowanie as Z


def _w(**over):
    base = {"plec": Z.PLEC_K, "wiek": 30, "wzrost_cm": 170, "masa_kg": 70,
            "praca": "Siedząca (biuro, auto, nauka)", "treningi": "3–4 treningi w tygodniu",
            "kroki": None, "cel": Z.CEL_UTRZYMANIE, "tempo": None}
    base.update(over)
    return Z.Wejscie(**base)


def test_ppm_kobieta_i_mezczyzna_recznie():
    # K 70 kg / 170 cm / 30 lat: 700 + 1062,5 − 150 − 161 = 1451,5
    assert Z.ppm_mifflin(Z.PLEC_K, 70, 170, 30) == pytest.approx(1451.5)
    # M 85 kg / 180 cm / 28 lat: 850 + 1125 − 140 + 5 = 1840
    assert Z.ppm_mifflin(Z.PLEC_M, 85, 180, 28) == pytest.approx(1840.0)


def test_pal_sklada_sie_z_pracy_treningow_i_krokow():
    p, wiersze = Z.pal("Siedząca (biuro, auto, nauka)", "3–4 treningi w tygodniu")
    assert p == pytest.approx(1.35)
    assert len(wiersze) == 2
    p2, w2 = Z.pal("Ciężka fizyczna", "Codziennie lub częściej", "Powyżej 12 000")
    assert p2 == Z.PAL_MAX  # 1,7 + 0,35 + 0,1 = 2,15 → ograniczone
    assert any("ograniczony" in w for w in w2)
    p3, _ = Z.pal("Siedząca (biuro, auto, nauka)", "Nie trenuję", "Poniżej 5 000")
    assert p3 == Z.PAL_MIN  # 1,2 − 0,05 → 1,2


def test_korekta_pod_cel():
    assert Z.korekta(Z.CEL_UTRZYMANIE, None) == 0.0
    assert Z.korekta(Z.CEL_REDUKCJA, "Umiarkowane (−15 %)") == -0.15
    assert Z.korekta(Z.CEL_MASA, "Standardowe (+10 %)") == 0.10
    with pytest.raises(ValueError):
        Z.korekta(Z.CEL_REDUKCJA, None)


def test_oblicz_utrzymanie_z_podstawieniem():
    w = Z.oblicz(_w())
    assert w.ppm == 1452  # 1451,5 zaokrąglone
    assert w.pal == 1.35
    assert w.cpm == round(1451.5 * 1.35)  # 1960
    assert w.korekta_pct == 0
    assert w.kcal == 1960
    assert w.ostrzezenia == ()
    assert "10 × 70 kg + 6,25 × 170 cm − 5 × 30 lat − 161 = 1452 kcal" in w.podstawienie[0]
    assert w.podstawienie[-1].endswith("≈ 1960 kcal / dzień")


def test_oblicz_redukcja_zaokragla_do_10():
    w = Z.oblicz(_w(cel=Z.CEL_REDUKCJA, tempo="Umiarkowane (−15 %)"))
    assert w.korekta_pct == -15
    assert w.kcal == round(1960 * 0.85 / 10) * 10  # 1666 → 1670
    assert any("− 15 %" in p for p in w.podstawienie)


def test_oblicz_masa_mezczyzna():
    w = Z.oblicz(_w(plec=Z.PLEC_M, wiek=28, wzrost_cm=180, masa_kg=85, treningi="5–6 treningów w tygodniu",
                    cel=Z.CEL_MASA, tempo="Ostrożne (+5 %)"))
    assert w.ppm == 1840
    assert w.pal == 1.45
    assert w.cpm == 2668
    assert w.kcal == round(2668 * 1.05 / 10) * 10  # 2801,4 → 2800


def test_wynik_nie_schodzi_ponizej_ppm():
    # PAL 1,2 (siedząca, nie trenuję) i −20 %: 1451,5·1,2·0,8 = 1393 < PPM → podniesione.
    w = Z.oblicz(_w(treningi="Nie trenuję", cel=Z.CEL_REDUKCJA, tempo="Szybsze (−20 %)"))
    assert w.kcal == 1460  # nigdy poniżej PPM 1451,5 → w górę do 10 kcal
    assert w.ostrzezenia and "spoczynku (PPM)" in w.ostrzezenia[0]
    assert any("podniesione do 1460" in p for p in w.podstawienie)


def test_podstawienie_pokazuje_pal_z_dwoma_miejscami():
    w = Z.oblicz(_w())
    assert "PAL = 1,35" in w.podstawienie and "CPM = 1452 × 1,35 = 1960 kcal" in w.podstawienie


def test_brak_danych_wskazuje_pola():
    with pytest.raises(Z.BrakDanych) as ei:
        Z.oblicz(_w(plec="", masa_kg=500, cel=Z.CEL_REDUKCJA, tempo=None))
    assert set(ei.value.pola) == {"plec", "masa_kg", "tempo"}


def test_liczba_z_przecinkiem_i_z_odpowiedzi():
    assert Z.liczba("72,5") == 72.5
    assert Z.liczba(" 1 80 ") == 180.0
    assert Z.liczba("abc") is None and Z.liczba("") is None and Z.liczba(None) is None
    we = Z.z_odpowiedzi({"zk_plec": Z.PLEC_M, "zk_wiek": "40", "zk_wzrost": "178", "zk_masa": "90,5",
                         "zk_praca": "Lekka (dużo stania i chodzenia)", "zk_treningi": "1–2 treningi w tygodniu",
                         "zk_kroki": "Nie wiem", "zk_cel": Z.CEL_REDUKCJA, "zk_tempo_redukcja": "Łagodne (−10 %)",
                         "zk_tempo_masa": "Standardowe (+10 %)"})
    assert we.masa_kg == 90.5 and we.tempo == "Łagodne (−10 %)" and we.kroki == "Nie wiem"
    w = Z.oblicz(we)
    assert w.pal == pytest.approx(1.4)

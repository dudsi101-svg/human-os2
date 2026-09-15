"""Silnik bilansu kalorycznego 1.0 — wektory kontrolne ze specyfikacji
właściciela (§7 „Kryteria akceptacji") i z `__main__` referencyjnej
implementacji `docs/calorie-interview/calorie_calc.py`.

Każdy test nazwany `test_kryterium_*` odpowiada jednej pozycji z listy
kryteriów akceptacji — mapa testów jest w `docs/calorie-interview/PROGRESS.md`.
"""

from __future__ import annotations

import pytest

from dzik_os.wywiad import zapotrzebowanie as Z


def _w(**over):
    base = {"plec": "F", "wiek": 30, "wzrost_cm": 170, "masa_kg": 70,
            "neat": "neat_1", "cel": "maintain"}
    base.update(over)
    return Z.Wejscie(**base)


# --- kryteria akceptacji ze specyfikacji §7 ---------------------------------------------


def test_kryterium_ppm_mezczyzna_1780():
    # M 30 l., 180 cm, 80 kg → 800 + 1125 − 150 + 5 = 1780 (dokładnie).
    assert Z.ppm_mifflin("M", 80, 180, 30) == pytest.approx(1780.0)
    assert Z.oblicz(_w(plec="M", wiek=30, wzrost_cm=180, masa_kg=80)).ppm_mifflin == 1780


def test_kryterium_ppm_kobieta_1345():
    # K 25 l., 165 cm, 60 kg → 600 + 1031,25 − 125 − 161 = 1345,25.
    assert Z.ppm_mifflin("F", 60, 165, 25) == pytest.approx(1345.25)
    assert Z.oblicz(_w(wiek=25, wzrost_cm=165, masa_kg=60)).ppm_mifflin == 1345


def test_kryterium_katch_1752():
    # 80 kg, 20 % tłuszczu → 370 + 21,6 · 64 = 1752,4 (±1).
    assert abs(Z.ppm_katch(80, 20) - 1752) <= 1


def test_kryterium_trening_i_cpm_2548():
    # Siedząca, 3 × 60 min siłowy, 0 cardio, 80 kg:
    # trening/dzień = 3·60·(5·80·0,0175)/7 = 180; CPM = (1780·1,20 + 180)·1,10 = 2548.
    w = Z.oblicz(_w(plec="M", wiek=30, wzrost_cm=180, masa_kg=80, sila_tydz=3, sila_minuty=60))
    assert w.training_kcal_day == 180
    assert w.cpm == 2548
    assert w.tef == 232  # 10 % z (2136 + 180)


def test_kryterium_redukcja_szybka_nie_schodzi_ponizej_granicy():
    # K 1345 PPM, tempo szybkie: cel nie schodzi poniżej max(1,1·PPM; 1200) = 1480.
    w = Z.oblicz(_w(wiek=25, wzrost_cm=165, masa_kg=60, cel="cut", tempo="fast"))
    assert w.target_kcal >= 1480
    assert Z.FLAGA_DEFICYT_OGRANICZONY in w.flags
    assert any("1,1 × PPM" in o or "granicy" in o for o in w.ostrzezenia)


def test_kryterium_minimum_kcal_kobiety_1200_mezczyzn_1500():
    assert Z.MIN_KCAL == {"F": 1200, "M": 1500}


def test_kryterium_maloletni_z_wieku():
    # Decyzja właściciela nr 4: wiek, nie data urodzenia; < 18 → flaga.
    assert Z.FLAGA_MALOLETNI in Z.oblicz(_w(wiek=17)).flags
    assert Z.FLAGA_MALOLETNI not in Z.oblicz(_w(wiek=18)).flags


def test_kryterium_formulas_version_zamrozona():
    assert Z.oblicz(_w()).formulas_version == Z.FORMULAS_VERSION == "2026-09-13.1"
    assert Z.FORMULAS_VERSION_PAL == "0.62.0-pal"


# --- PPM: wybór wzoru --------------------------------------------------------------------


def test_katch_uzyty_dopiero_przy_roznicy_powyzej_10_procent():
    # 70 kg / 170 cm / 30 l. kobieta: Mifflin 1451,5. Katch przy 15 % tłuszczu:
    # 370 + 21,6·59,5 = 1655,2 → różnica 14 % → Katch.
    w = Z.oblicz(_w(procent_tluszczu=15))
    assert w.ppm_katch == 1655 and w.ppm_source == "katch_mcardle" and w.ppm_used == 1655
    assert any("Katch-McArdle" in o for o in w.ostrzezenia)
    # 30 % tłuszczu: 370 + 21,6·49 = 1428,4 → różnica 1,6 % → Mifflin, ale oba pokazane.
    w2 = Z.oblicz(_w(procent_tluszczu=30))
    assert w2.ppm_katch == 1428 and w2.ppm_source == "mifflin_st_jeor" and w2.ppm_used == 1452
    assert w2.ostrzezenia == ()


def test_bez_procentu_tluszczu_katch_nie_istnieje():
    w = Z.oblicz(_w())
    assert w.ppm_katch is None and w.ppm_source == "mifflin_st_jeor"


# --- NEAT --------------------------------------------------------------------------------


def test_neat_opisowy_ma_mnozniki_ze_specyfikacji():
    assert Z.NEAT == {"neat_1": 1.20, "neat_2": 1.35, "neat_3": 1.50, "neat_4": 1.70}


def test_neat_z_krokow_nadpisuje_wybor_opisowy_i_ma_ograniczenia():
    assert Z.neat_z_krokow(4000) == pytest.approx(1.20)
    assert Z.neat_z_krokow(10000) == pytest.approx(1.44)
    assert Z.neat_z_krokow(0) == Z.NEAT_KROKI_MIN       # 1,04 → 1,15
    assert Z.neat_z_krokow(40000) == Z.NEAT_KROKI_MAX   # 2,64 → 1,85
    # Kroki wygrywają z opisem „siedząca”.
    assert Z.oblicz(_w(neat="neat_1", kroki=10000)).neat_multiplier == pytest.approx(1.44)


# --- CPM, TEF, zakres --------------------------------------------------------------------


def test_cpm_liczone_addytywnie_a_nie_jednym_pal():
    w = Z.oblicz(_w(neat="neat_3", sila_tydz=4, sila_minuty=45, cardio_tydz=2, cardio_minuty=30,
                    cardio_intensywnosc="moderate"))
    ppm = Z.ppm_mifflin("F", 70, 170, 30)
    trening = (4 * 45 * 5.0 + 2 * 30 * 7.0) * 70 * 0.0175 / 7
    assert w.training_kcal_day == round(trening)
    assert w.cpm == round((ppm * 1.50 + trening) * 1.10)


def test_zakres_cpm_to_plus_minus_7_procent():
    w = Z.oblicz(_w())
    assert w.cpm_min == round(w.cpm * 0.93 / 1.0) or w.cpm_min < w.cpm
    assert w.cpm_min < w.cpm < w.cpm_max
    assert abs(w.cpm_max - w.cpm) >= round(w.cpm * 0.06)


def test_cardio_bez_sesji_nie_wchodzi_do_wyniku():
    a = Z.oblicz(_w(cardio_tydz=0, cardio_minuty=60, cardio_intensywnosc="high"))
    b = Z.oblicz(_w())
    assert a.cpm == b.cpm


# --- cel kaloryczny ----------------------------------------------------------------------


def test_korekty_pod_cel_i_tempo_ze_specyfikacji():
    assert Z.KOREKTA[("cut", "gentle")] == -0.10
    assert Z.KOREKTA[("cut", "moderate")] == -0.20
    assert Z.KOREKTA[("cut", "fast")] == -0.25
    assert Z.KOREKTA[("maintain", None)] == 0.0
    assert Z.KOREKTA[("bulk", "gentle")] == 0.05
    assert Z.KOREKTA[("bulk", "moderate")] == 0.10
    assert Z.KOREKTA[("bulk", "fast")] == 0.15
    assert Z.KOREKTA[("recomp", None)] == -0.05


def test_rekompozycja_nie_pyta_o_tempo_i_ma_minus_5():
    w = Z.oblicz(_w(cel="recomp", masa_kg=90, wzrost_cm=180))
    assert w.korekta_pct == -5


def test_szybka_budowa_masy_ostrzega_o_tluszczu():
    w = Z.oblicz(_w(cel="bulk", tempo="fast"))
    assert w.korekta_pct == 15
    assert any("tkanki tłuszczowej" in o for o in w.ostrzezenia)


def test_ciaza_wylacza_deficyt_i_zapala_flage():
    w = Z.oblicz(_w(cel="cut", tempo="moderate", ciaza=True))
    assert w.korekta_pct == 0
    assert Z.FLAGA_CIAZA in w.flags and Z.FLAGA_DEFICYT_WYLACZONY in w.flags


def test_brak_miesiaczki_wylacza_deficyt():
    w = Z.oblicz(_w(cel="cut", tempo="gentle", brak_miesiaczki=True))
    assert w.korekta_pct == 0 and Z.FLAGA_DEFICYT_WYLACZONY in w.flags


def test_deficyt_wylaczony_nie_zapala_sie_gdy_deficytu_nie_bylo():
    # Odstępstwo od literalnej linii referencji (tam flaga zapala się zawsze):
    # przy budowie masy „deficyt wyłączony” byłby dla trenera nieprawdą.
    w = Z.oblicz(_w(cel="bulk", tempo="moderate", ciaza=True))
    assert w.korekta_pct == 10
    assert Z.FLAGA_CIAZA in w.flags and Z.FLAGA_DEFICYT_WYLACZONY not in w.flags


def test_podloga_nie_dotyczy_utrzymania_i_budowy_masy():
    w = Z.oblicz(_w(masa_kg=35, wzrost_cm=150, cel="maintain"))
    assert Z.FLAGA_DEFICYT_OGRANICZONY not in w.flags


# --- makro -------------------------------------------------------------------------------


def test_makro_utrzymanie_1_6_g_bialka_i_1_g_tluszczu():
    w = Z.oblicz(_w())
    assert w.makro.bialko_g == round(1.6 * 70)
    assert w.makro.tluszcz_g >= round(1.0 * 70)
    assert w.makro.bialko_pct + w.makro.tluszcz_pct + w.makro.wegle_pct == pytest.approx(100, abs=2)


def test_preferencja_wysoka_bierze_gorna_granice_bialka():
    a = Z.oblicz(_w(cel="cut", tempo="gentle"))
    b = Z.oblicz(_w(cel="cut", tempo="gentle", bialko="high"))
    assert a.makro.bialko_g == round(1.8 * 70) and b.makro.bialko_g == round(2.2 * 70)


def test_przy_wysokim_procencie_tluszczu_bialko_z_masy_docelowej():
    w = Z.oblicz(_w(cel="cut", tempo="gentle", procent_tluszczu=35, masa_kg=100, wzrost_cm=170,
                    masa_docelowa_kg=80))
    assert w.makro.bialko_z_masy_kg == 80.0 and w.makro.bialko_g == round(1.8 * 80)
    # Bez masy docelowej: ~LBM/0,75 = 100·0,65/0,75 = 86,7 kg.
    w2 = Z.oblicz(_w(cel="cut", tempo="gentle", procent_tluszczu=35, masa_kg=100, wzrost_cm=170))
    assert w2.makro.bialko_z_masy_kg == pytest.approx(86.7, abs=0.1)


def test_tluszcz_nigdy_ponizej_20_procent_kalorii():
    w = Z.oblicz(_w(cel="cut", tempo="fast", masa_kg=45, wzrost_cm=165))
    assert w.makro.tluszcz_g * 9 >= 0.20 * w.target_kcal - 1


def test_wegle_nie_schodza_ponizej_zera():
    w = Z.oblicz(_w(cel="cut", tempo="fast", masa_kg=120, wzrost_cm=160, procent_tluszczu=45))
    assert w.makro.wegle_g >= 0


# --- tempo i czas ------------------------------------------------------------------------


def test_tempo_odtwarza_przyklad_ze_specyfikacji_6_1():
    # CPM 2350, cel 1880 → 470 kcal/dzień → 0,427 kg/tydz. → „~0,4–0,5”.
    od, do = Z._zakres_tempa((2350 - 1880) * 7 / 7700)
    assert (od, do) == (0.4, 0.5)


def test_przyrost_miesieczny_zalezy_od_stazu():
    w = Z.oblicz(_w(cel="bulk", tempo="gentle", staz="lt1", masa_kg=80, wzrost_cm=180))
    assert (w.tempo.przyrost_mies_od, w.tempo.przyrost_mies_do) == (0.4, 0.8)
    w2 = Z.oblicz(_w(cel="bulk", tempo="gentle", staz="gt3", masa_kg=80, wzrost_cm=180))
    assert (w2.tempo.przyrost_mies_od, w2.tempo.przyrost_mies_do) == (0.0, 0.2)


def test_czas_do_celu_tylko_gdy_kierunek_sie_zgadza():
    w = Z.oblicz(_w(cel="cut", tempo="moderate", masa_kg=90, wzrost_cm=175, masa_docelowa_kg=80))
    assert w.tempo.tygodni_do_celu and w.tempo.tygodni_do_celu > 0
    # Redukcja do WYŻSZEJ masy: czasu nie podajemy (kierunek się nie zgadza).
    w2 = Z.oblicz(_w(cel="cut", tempo="moderate", masa_kg=70, wzrost_cm=175, masa_docelowa_kg=80))
    assert w2.tempo.tygodni_do_celu is None


# --- flagi -------------------------------------------------------------------------------


def test_wszystkie_flagi_zdrowotne_ze_specyfikacji():
    w = Z.oblicz(_w(wiek=17, masa_kg=40, wzrost_cm=170, cel="cut", tempo="gentle",
                    ciaza=True, choroba_metaboliczna=True, leki=True,
                    zaburzenia_odzywiania=True, brak_miesiaczki=True))
    for f in (Z.FLAGA_MALOLETNI, Z.FLAGA_BMI_SKRAJNE, Z.FLAGA_CIAZA, Z.FLAGA_CHOROBA,
              Z.FLAGA_LEKI, Z.FLAGA_ZABURZENIA, Z.FLAGA_BRAK_MIESIACZKI):
        assert f in w.flags, f
    assert set(w.flags) <= set(Z.FLAGI_OPIS)


def test_bmi_skrajne_po_obu_stronach():
    assert Z.FLAGA_BMI_SKRAJNE in Z.oblicz(_w(masa_kg=45, wzrost_cm=175)).flags     # BMI 14,7
    assert Z.FLAGA_BMI_SKRAJNE in Z.oblicz(_w(masa_kg=130, wzrost_cm=170)).flags    # BMI 45
    assert Z.FLAGA_BMI_SKRAJNE not in Z.oblicz(_w()).flags                          # BMI 24,2


def test_brak_odpowiedzi_zdrowotnej_nie_zapala_flagi():
    w = Z.oblicz(_w(ciaza=None, zaburzenia_odzywiania=False))
    assert not (set(w.flags) & Z.FLAGI_ZDROWOTNE)


def test_kazda_flaga_ma_opis_dla_trenera():
    for kod, opis in Z.FLAGI_OPIS.items():
        assert opis.etykieta and opis.trener, kod
        assert opis.poziom in ("warn", "info")
    assert Z.FLAGI_ZDROWOTNE <= set(Z.FLAGI_OPIS)
    assert Z.FLAGI_UKRYWAJACE_WYNIK <= set(Z.FLAGI_OPIS)


# --- podstawienie ------------------------------------------------------------------------


def test_podstawienie_pokazuje_rozbicie_cpm_na_skladniki():
    w = Z.oblicz(_w(plec="M", wiek=30, wzrost_cm=180, masa_kg=80, sila_tydz=3, sila_minuty=60))
    tekst = " | ".join(w.podstawienie)
    assert "PPM (Mifflin-St Jeor, mężczyzna)" in tekst
    assert "PPM × NEAT = 1780 × 1,2 = 2136 kcal" in tekst
    assert "trening na dzień = 180 kcal" in tekst
    assert "TEF" in tekst
    assert "CPM = (2136 + 180) × 1,10 = 2548 kcal" in tekst
    assert "makro:" in tekst


def test_podstawienie_pokazuje_oba_ppm_gdy_podano_tluszcz():
    w = Z.oblicz(_w(procent_tluszczu=15))
    tekst = " | ".join(w.podstawienie)
    assert "Katch-McArdle" in tekst and "użyty wzór" in tekst


# --- walidacja i mapa odpowiedzi ---------------------------------------------------------


def test_brak_danych_wskazuje_pola():
    with pytest.raises(Z.BrakDanych) as ei:
        Z.oblicz(_w(plec="", masa_kg=500, cel="cut", tempo=None))
    assert set(ei.value.pola) == {"plec", "masa_kg", "tempo"}


def test_zakresy_ze_specyfikacji():
    assert Z.ZAKRES_WIEK == (16.0, 90.0)
    assert Z.ZAKRES_WZROST == (130.0, 230.0)
    assert Z.ZAKRES_MASA == (35.0, 250.0)
    assert Z.ZAKRES_TLUSZCZ == (3.0, 60.0)


def test_liczba_z_przecinkiem():
    assert Z.liczba("72,5") == 72.5
    assert Z.liczba(" 1 80 ") == 180.0
    assert Z.liczba("abc") is None and Z.liczba("") is None and Z.liczba(None) is None


def test_z_odpowiedzi_tlumaczy_etykiety_na_kody():
    we = Z.z_odpowiedzi({
        "zk_plec": Z.PLEC_M, "zk_wiek": "30", "zk_wzrost": "180", "zk_masa": "80",
        "zk_tluszcz": "18", "zk_neat": Z.NEAT_SIEDZACA, "zk_kroki": "9000",
        "zk_sila_tydz": "3", "zk_sila_minuty": Z.MINUTY_60,
        "zk_cardio_tydz": "2", "zk_cardio_minuty": Z.MINUTY_30,
        "zk_cardio_intensywnosc": Z.INT_UMIARKOWANA, "zk_staz": Z.STAZ_SREDNI,
        "zk_cel": Z.CEL_REDUKCJA, "zk_tempo": Z.TEMPO_UMIARKOWANE,
        "zk_masa_docelowa": "75", "zk_bialko": Z.BIALKO_WYSOKIE,
        "zk_ciaza": Z.ODP_ZDR_NIE, "zk_choroba": Z.ODP_ZDR_TAK,
        "zk_leki": Z.ODP_ZDR_WOLE_NIE, "zk_zaburzenia": Z.ODP_ZAB_NIE,
        "zk_miesiaczka": None,
    })
    assert we.plec == "M" and we.neat == "neat_1" and we.kroki == 9000
    assert we.sila_minuty == 60 and we.cardio_minuty == 30 and we.cardio_intensywnosc == "moderate"
    assert we.staz == "1_3" and we.cel == "cut" and we.tempo == "moderate"
    assert we.masa_docelowa_kg == 75 and we.bialko == "high" and we.procent_tluszczu == 18
    assert we.ciaza is False and we.choroba_metaboliczna is True
    assert we.leki is None and we.zaburzenia_odzywiania is False and we.brak_miesiaczki is None
    Z.oblicz(we)  # komplet odpowiedzi musi się policzyć


def test_z_odpowiedzi_tempo_ignorowane_przy_celu_bez_tempa():
    we = Z.z_odpowiedzi({"zk_plec": Z.PLEC_K, "zk_wiek": "30", "zk_wzrost": "170", "zk_masa": "70",
                         "zk_neat": Z.NEAT_LEKKA, "zk_cel": Z.CEL_UTRZYMANIE,
                         "zk_tempo": Z.TEMPO_SZYBKIE})
    assert we.tempo is None
    assert Z.oblicz(we).korekta_pct == 0


def test_zaburzenia_flaguje_tez_nie_wiem_i_wole_omowic():
    # Decyzja właściciela nr 2: reguła szersza niż specyfikacja.
    for odp in (Z.ODP_ZAB_TAK, Z.ODP_ZAB_NIE_WIEM, Z.ODP_ZAB_OMOWIC):
        we = Z.z_odpowiedzi({"zk_plec": Z.PLEC_K, "zk_wiek": "30", "zk_wzrost": "170",
                             "zk_masa": "70", "zk_neat": Z.NEAT_LEKKA,
                             "zk_cel": Z.CEL_UTRZYMANIE, "zk_zaburzenia": odp})
        assert we.zaburzenia_odzywiania is True, odp
        assert Z.FLAGA_ZABURZENIA in Z.oblicz(we).flags
    we = Z.z_odpowiedzi({"zk_plec": Z.PLEC_K, "zk_wiek": "30", "zk_wzrost": "170", "zk_masa": "70",
                         "zk_neat": Z.NEAT_LEKKA, "zk_cel": Z.CEL_UTRZYMANIE,
                         "zk_zaburzenia": Z.ODP_ZAB_NIE})
    assert we.zaburzenia_odzywiania is False


def test_pal_efektywny_to_cpm_przez_ppm():
    w = Z.oblicz(_w(plec="M", wiek=30, wzrost_cm=180, masa_kg=80, sila_tydz=3, sila_minuty=60))
    assert w.pal_efektywny == pytest.approx(round(2548 / 1780, 2))


def test_rozbicie_w_podstawieniu_liczy_sie_z_liczb_widocznych_w_karcie():
    """Wiersz podstawienia i kafelek w interfejsie muszą pokazywać tę samą
    liczbę na ten sam składnik — stąd rozbicie z wartości zaokrąglonych."""
    w = Z.oblicz(_w(sila_tydz=3, sila_minuty=60, cel="cut", tempo="moderate"))
    po_neat = round(w.ppm_used * w.neat_multiplier)
    assert f"PPM × NEAT = {w.ppm_used} × 1,2 = {po_neat} kcal" in w.podstawienie
    assert f"CPM = ({po_neat} + {w.training_kcal_day}) × 1,10 = {w.cpm} kcal" in " | ".join(w.podstawienie)
    # Gdy suma zaokrąglonych składników nie wychodzi na wynik, mówimy to wprost.
    if round((po_neat + w.training_kcal_day) * 1.10) != w.cpm:
        assert any("są zaokrąglone" in p for p in w.podstawienie)


def test_wiek_liczony_w_pelnych_latach():
    """Formularz dopuszcza „30,5”, ale wzór (jak w referencji właściciela)
    bierze pełne lata — inaczej podstawienie i wynik mówiłyby co innego."""
    a, b = Z.oblicz(_w(wiek=30)), Z.oblicz(_w(wiek=30.9))
    assert a.wiek == b.wiek == 30
    assert a.ppm_mifflin == b.ppm_mifflin
    assert "− 5 × 30 lat" in a.podstawienie[0]

def test_podloga_kcal_wiaze_w_dzialaniu_a_nie_tylko_jako_stala():
    """Przegląd PR #80, P2: dotąd sprawdzaliśmy samą wartość `MIN_KCAL`,
    więc wyzerowanie progu przechodziło cały zestaw. Tu próg musi zadziałać:
    drobny mężczyzna przy szybkiej redukcji schodzi wzorem poniżej 1500 kcal,
    a wynik ma się o próg oprzeć i zapalić flagę."""
    w = Z.Wejscie(plec="M", wiek=90, wzrost_cm=150, masa_kg=45.0,
                  neat="neat_1", cel="cut", tempo="fast")
    y = Z.oblicz(w)
    assert y.target_kcal == Z.MIN_KCAL["M"] == 1500
    assert Z.FLAGA_DEFICYT_OGRANICZONY in y.flags
    # Bez progu wzór dałby wyraźnie mniej — to jest dowód, że próg wiąże.
    bez_progu = round(y.cpm * (1 + y.korekta_pct / 100))
    assert bez_progu < 1500


def test_granice_mnoznika_z_krokow_to_konkretne_liczby():
    """Przegląd PR #80, P2: asercja przez stałą przechodziła nawet po zmianie
    granicy na 2,5. Tu porównujemy z liczbami wprost."""
    assert Z.neat_z_krokow(0) == 1.15
    assert Z.neat_z_krokow(30000) == 1.85


# --- ciąża i karmienie: dodatek ze specyfikacji §6.4 (0.78.0) ----------------

def _kobieta(**nad):
    baza = dict(plec="F", wiek=30, wzrost_cm=170, masa_kg=70.0, neat="neat_2", cel="maintain")
    return Z.Wejscie(**{**baza, **nad})


def test_ciaza_dodaje_300_a_karmienie_500():
    """Decyzja właściciela z 15.09: specyfikacja §6.4 dopuszcza cel = CPM albo
    CPM + 300/500; wybrany został dodatek, więc pytamy wprost, co zachodzi."""
    bez = Z.oblicz(_kobieta(ciaza=True)).target_kcal
    ciaza = Z.oblicz(_kobieta(ciaza=True, ciaza_rodzaj=Z.ODP_CK_CIAZA)).target_kcal
    karmienie = Z.oblicz(_kobieta(ciaza=True, ciaza_rodzaj=Z.ODP_CK_KARMIENIE)).target_kcal
    oba = Z.oblicz(_kobieta(ciaza=True, ciaza_rodzaj=Z.ODP_CK_OBA)).target_kcal
    assert ciaza - bez == 300
    assert karmienie - bez == 500
    assert oba - bez == 500


def test_bez_doprecyzowania_i_bez_ciazy_dodatku_nie_ma():
    """Brak odpowiedzi (albo „wolę nie odpowiadać”) nie domyśla się wartości."""
    bez_flagi = Z.oblicz(_kobieta()).target_kcal
    assert Z.oblicz(_kobieta(ciaza_rodzaj=Z.ODP_CK_KARMIENIE)).target_kcal == bez_flagi
    z_flaga = Z.oblicz(_kobieta(ciaza=True)).target_kcal
    assert Z.oblicz(_kobieta(ciaza=True, ciaza_rodzaj=Z.ODP_ZDR_WOLE_NIE)).target_kcal == z_flaga


def test_dodatek_wchodzi_po_wylaczeniu_deficytu_i_z_ostrzezeniem():
    """Przy redukcji deficyt jest wyłączany (flaga), a dodatek liczy się od CPM,
    nie od obniżonego celu. Ostrzeżenie o konsultacji jest obowiązkowe."""
    w = _kobieta(ciaza=True, ciaza_rodzaj=Z.ODP_CK_CIAZA, cel="cut", tempo="moderate")
    y = Z.oblicz(w)
    assert Z.FLAGA_DEFICYT_WYLACZONY in y.flags
    assert y.target_kcal == y.cpm + 300
    assert any("punkt wyjścia" in o for o in y.ostrzezenia)
    assert any("lekarz albo dietetyk" in o for o in y.ostrzezenia)

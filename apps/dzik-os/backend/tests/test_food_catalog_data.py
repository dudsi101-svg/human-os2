"""Integralność wbudowanej bazy produktów (0.48.0, cel ×5).

Pilnuje trzech rzeczy, które przy ręcznie utrzymywanej bazie ~2000 pozycji
psują się najłatwiej: rozmiaru (obietnica ×5 względem pierwotnych 410),
unikalności po znormalizowanej nazwie (load-builtin deduplikuje po tym
kluczu — duplikat w danych to pozycja martwa) i spójności energetycznej
(kcal vs makra wzorem Atwatera z tolerancją na zaokrąglenia tabel).
"""

from dzik_os.food_catalog_data import FOOD_ROWS_ALL as FOOD_ROWS
from dzik_os.food_catalog_data_ext import FOOD_ROWS_EXT
from dzik_os.sheet_import import normalize_name


def test_baza_liczy_co_najmniej_2000_pozycji():
    assert len(FOOD_ROWS) >= 2000, len(FOOD_ROWS)


def test_transza_rozszerzona_jest_czescia_pelnej_bazy():
    assert len(FOOD_ROWS_EXT) > 0
    assert FOOD_ROWS[-1] == FOOD_ROWS_EXT[-1]


def test_nazwy_unikalne_po_normalizacji():
    widziane: dict[str, str] = {}
    dubli = []
    for row in FOOD_ROWS:
        klucz = normalize_name(row.name)
        if klucz in widziane:
            dubli.append((widziane[klucz], row.name))
        else:
            widziane[klucz] = row.name
    assert not dubli, dubli[:10]


def test_wartosci_w_rozsadnych_granicach():
    for row in FOOD_ROWS:
        assert row.name.strip(), row
        assert 0 <= row.kcal <= 950, row.name
        assert 0 <= row.protein <= 100, row.name
        assert 0 <= row.fat <= 100, row.name
        assert 0 <= row.carbs <= 105, row.name
        assert 0 <= row.fiber <= 90, row.name
        assert 0 < row.portion_g <= 600, row.name
        if row.unit_grams is not None:
            assert row.unit_grams > 0, row.name


# Energia spoza makr (alkohol, 7 kcal/g) albo makra bez energii (poliole,
# błonnik rozpuszczalny liczony w węglowodanach przy ~2 kcal/g) — wzór
# Atwatera z definicji się tu nie zgadza, więc te pozycje pomijamy po
# słowie kluczowym w nazwie zamiast rozmontowywać próg dla całej bazy.
_POZA_ATWATEREM = (
    "wino",
    "wódka",
    "whisky",
    "likier",
    "piwo ",
    "wanilia",
    "błonnik",
    "inulina",
    "guma do żucia",
    "ksylitol",
    "karob",
)


def test_kcal_zgodne_z_makrami():
    """Wzór Atwatera 4P+9F+4C, z luzem na błonnik i zaokrąglenia tabel.

    Tolerancja jest szeroka celowo: tabele wartości odżywczych liczą
    energię różnymi metodami (błonnik 0 albo 2 kcal/g, poliole itd.),
    więc łapiemy tylko grube pomyłki (literówka rzędu wielkości), nie
    różnice metodologiczne. Dolna granica odejmuje błonnik (część tabel
    nie liczy go do energii), pozycje z energią z alkoholu albo
    o polio­lowym profilu pomijamy po nazwie (`_POZA_ATWATEREM`).
    """
    for row in FOOD_ROWS:
        nazwa = row.name.lower()
        if row.note and "słodzik" in row.note:
            continue
        if any(k in nazwa for k in _POZA_ATWATEREM):
            continue
        # Dwie konwencje tabel naraz: błonnik wliczony w węglowodany
        # (wtedy energia bywa niższa niż 4C) albo podany osobno, netto
        # (wtedy energia bywa wyższa) — stąd widełki C±błonnik.
        gorna = 4 * row.protein + 9 * row.fat + 4 * (row.carbs + row.fiber)
        dolna = 4 * row.protein + 9 * row.fat + 4 * max(0.0, row.carbs - row.fiber)
        tolerancja = max(60.0, gorna * 0.35)
        assert dolna - tolerancja <= row.kcal <= gorna + tolerancja, (
            f"{row.name}: kcal={row.kcal}, Atwater={dolna:.0f}–{gorna:.0f}"
        )

"""Stałe modelu suwaków cardio (`cardio_model_v1`) — w jednym miejscu, ze
źródłem i poziomem pewności.

Poziomy pewności (jak w `docs/zlecenia/model-suwakow-cardio.md`):
[A] zgodne z wytycznymi/metaanalizami, [B] dobrze opisane, ale z dużą
zmiennością osobniczą, [C] synteza własna / praktyka trenerska — do
potwierdzenia przez trenera przed użyciem u prawdziwych klientów.

To nie jest porada medyczna: liczby są STRUKTURĄ SESJI dla trenera
(propose-only), zawsze prezentowaną jako zakres obok RPE i testu mowy.
"""

from __future__ import annotations

WERSJA_MODELU = "cardio_model_v1"

#: Kolejność celów jest kontraktem z frontendem (suwaki i paski wag).
CELE: tuple[str, ...] = ("redukcja", "wydolnosc", "regeneracja")

ETYKIETY_CELOW: dict[str, str] = {
    "redukcja": "Redukcja (wydatek energii)",
    "wydolnosc": "Wydolność (VO2max)",
    "regeneracja": "Regeneracja (baza tlenowa)",
}

#: Kotwice intensywności per cel (model §4). %HRmax i %HRR jako (dół, góra);
#: „środek” to wartość używana w mieszaniu (§4 „Mieszanie” [C]).
#: Regeneracja/Wydolność [A], Redukcja [B] (Fatmax — Achten & Jeukendrup).
KOTWICE: dict[str, dict] = {
    "regeneracja": {"hrmax": (55, 65), "hrr": (35, 50), "rpe": (2, 3), "czas_min": (20, 30),
                    "srodek_hrmax": 60.0, "srodek_hrr": 42.5, "srodek_czas": 25.0,
                    "test_mowy": "pełne zdania swobodnie"},
    "redukcja": {"hrmax": (65, 75), "hrr": (50, 65), "rpe": (4, 5), "czas_min": (40, 60),
                 "srodek_hrmax": 70.0, "srodek_hrr": 57.5, "srodek_czas": 50.0,
                 "test_mowy": "zdania, lekko przerywane"},
    "wydolnosc": {"hrmax": (85, 95), "hrr": (75, 90), "rpe": (7, 9), "czas_min": (20, 30),
                  "srodek_hrmax": 90.0, "srodek_hrr": 82.5, "srodek_czas": 25.0,
                  "test_mowy": "pojedyncze słowa"},
}

#: Przerwa w interwałach (%HRmax / %HRR) — stała (model §4 [C]).
PRZERWA_HRMAX = 65.0
PRZERWA_HRR = 50.0

#: Niepewność wzoru HRmax → wynik zawsze jako zakres ±5 punktów % (model §4).
POLOWKA_ZAKRESU_PCT = 5

#: Dolna granica sensownego zakresu (%HRmax) — poniżej to spacer.
PODLOGA_PCT = 40

#: Sufit intensywności wg poziomu (model §4: początkujący maks. 85 % HRmax).
SUFIT_PCT: dict[str, int] = {
    "POCZATKUJACY": 85,
    "SREDNIOZAAWANSOWANY": 95,
    "ZAAWANSOWANY": 95,
}

#: Korekta czasu wg poziomu (początkujący −20 %).
MNOZNIK_CZASU: dict[str, float] = {
    "POCZATKUJACY": 0.8,
    "SREDNIOZAAWANSOWANY": 1.0,
    "ZAAWANSOWANY": 1.0,
}

#: Struktura interwałów wg poziomu (model §4 [A] dla 4×4 Helgerud; reszta [C]):
#: (rundy, praca_min, przerwa_min).
INTERWALY: dict[str, tuple[int, int, int]] = {
    "POCZATKUJACY": (8, 1, 1),
    "SREDNIOZAAWANSOWANY": (6, 2, 2),
    "ZAAWANSOWANY": (4, 4, 3),
}

#: Progi wagi „Wydolność” decydujące o strukturze (model §4 [C]): interwały
#: dopiero POWYŻEJ 0,5 (przykład kontrolny (0,5/0,5/0) → tempo 2×10).
PROG_INTERWALY = 0.5
PROG_TEMPO = 0.25

#: „Tempo”: mieszana intensywność ciągle albo 2×10 min z przerwą 3 min.
TEMPO_BLOKI = (2, 10, 3)

#: HRmax z wieku: Tanaka 208 − 0,7 × wiek, błąd ±10 ud./min [A] (wzór), [B] (u osoby).
TANAKA_A = 208.0
TANAKA_B = 0.7
TANAKA_BLAD_BPM = 10

#: Zakres wieku, w którym wzór ma sens (dorośli; produkt jest dla 18+).
WIEK_MIN, WIEK_MAX = 18, 90
#: Zakres tętna spoczynkowego przyjmowany z pomiaru (poza nim — ignorujemy, tryb %HRmax).
TETNO_SPOCZ_MIN, TETNO_SPOCZ_MAX = 35, 110

#: Zastrzeżenia obowiązkowe w UI (KARTA §0.3 — uczciwość).
ZASTRZEZENIA: dict[str, str] = {
    "zakres": "Zakres tętna pochodzi z wzoru wiekowego (błąd ±10 ud./min) — koryguj do RPE "
              "i testu mowy, nie do jednej liczby.",
    "bilans": "Udział tłuszczu jako paliwa w danej strefie nie przesądza o utracie tkanki "
              "tłuszczowej — decyduje bilans energii w skali tygodni.",
    "bez_pulsometru": "Bez pulsometru prowadź wysiłek według RPE i testu mowy — to równoprawny "
                      "wariant.",
    "rpe_only": "Leki wpływające na tętno: tętno w ud./min nie jest podawane — prowadź wysiłek "
                "według RPE i testu mowy.",
    "poczatkujacy": "Poziom początkujący: sufit 85 % HRmax, krótsze interwały, czas −20 %.",
    "propozycja": "To propozycja struktury sesji dla trenera, nie porada medyczna — trener "
                  "decyduje i może każdą liczbę zmienić.",
    "kcal": "Wydatek energii to szacunek z tabel MET (Compendium of Physical Activities) — "
            "urządzenia i osoby różnią się znacząco.",
}

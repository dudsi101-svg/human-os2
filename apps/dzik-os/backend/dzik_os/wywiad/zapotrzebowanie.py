"""Silnik szacowania dziennego zapotrzebowania kalorycznego (0.62.0).

Czyste funkcje bez bazy i bez AI. Wzór: PPM wg Mifflina-St Jeora, CPM =
PPM × PAL, wynik = CPM skorygowany pod cel. Każdy krok zwraca podstawienie
liczb czytelne dla trenera i klienta („skąd ta liczba”). Wynik jest
SZACUNKIEM ze wzoru — nie zaleceniem; zalecenie ustala trener.

Wejścia pochodzą z odpowiedzi wywiadu „Zapotrzebowanie kaloryczne”
(`definicje.py`, pytania `zk_*`). Wartości liczbowe przyjmują przecinek
dziesiętny (formularz po polsku).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

PLEC_K = "Kobieta"
PLEC_M = "Mężczyzna"
PLCI = (PLEC_K, PLEC_M)

#: Zakresy wejść liczbowych (walidacja także w `definicje.waliduj`).
ZAKRES_WIEK = (14.0, 100.0)
ZAKRES_WZROST = (120.0, 230.0)
ZAKRES_MASA = (30.0, 300.0)

#: Charakter pracy → bazowy PAL (siedząca 1,2 … ciężka fizyczna 1,7).
PRACA = {
    "Siedząca (biuro, auto, nauka)": 1.2,
    "Lekka (dużo stania i chodzenia)": 1.35,
    "Umiarkowanie fizyczna": 1.5,
    "Ciężka fizyczna": 1.7,
}
#: Treningi w tygodniu → dodatek do PAL.
TRENINGI = {
    "Nie trenuję": 0.0,
    "1–2 treningi w tygodniu": 0.05,
    "3–4 treningi w tygodniu": 0.15,
    "5–6 treningów w tygodniu": 0.25,
    "Codziennie lub częściej": 0.35,
}
#: Kroki dziennie → korekta PAL (opcjonalne pytanie; brak = 0).
KROKI = {
    "Poniżej 5 000": -0.05,
    "5 000–8 000": 0.0,
    "8 000–12 000": 0.05,
    "Powyżej 12 000": 0.1,
    "Nie wiem": 0.0,
}
PAL_MIN, PAL_MAX = 1.2, 1.9

CEL_REDUKCJA = "Redukcja masy ciała"
CEL_UTRZYMANIE = "Utrzymanie masy ciała"
CEL_MASA = "Budowa masy mięśniowej"
CELE = (CEL_REDUKCJA, CEL_UTRZYMANIE, CEL_MASA)
#: Tempo → korekta procentowa CPM.
TEMPO_REDUKCJA = {
    "Łagodne (−10 %)": -0.10,
    "Umiarkowane (−15 %)": -0.15,
    "Szybsze (−20 %)": -0.20,
}
TEMPO_MASA = {
    "Ostrożne (+5 %)": 0.05,
    "Standardowe (+10 %)": 0.10,
}
#: Dolna granica bezpieczeństwa wyniku: poniżej PPM wynik jest podnoszony do
#: PPM i oznaczany ostrzeżeniem (deficyt nie schodzi poniżej metabolizmu
#: podstawowego bez decyzji trenera).
ZAOKRAGLENIE_WYNIKU = 10
OSTRZEZENIE_PONIZEJ_PPM = ("Po korekcie wynik spadł poniżej tego, co organizm spala w spoczynku (PPM) — "
                           "podnieśliśmy go do tej granicy. Większy deficyt może ustalić tylko trener.")


class BrakDanych(ValueError):
    """Brakuje wejścia albo jest poza zakresem; `pola` wskazuje które."""

    def __init__(self, pola: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in pola.items()))
        self.pola = pola


@dataclass(frozen=True)
class Wejscie:
    plec: str
    wiek: float
    wzrost_cm: float
    masa_kg: float
    praca: str
    treningi: str
    kroki: str | None
    cel: str
    tempo: str | None


@dataclass(frozen=True)
class Wynik:
    ppm: int
    pal: float
    cpm: int
    korekta_pct: int
    kcal: int
    ostrzezenia: tuple[str, ...]
    #: Podstawienie krok po kroku (czytelne wiersze, bez wzorów w UI).
    podstawienie: tuple[str, ...]


def liczba(tekst: str | None) -> float | None:
    """„72,5” → 72.5; puste / nieliczbowe → None."""
    if tekst is None:
        return None
    t = str(tekst).strip().replace(",", ".").replace(" ", "")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _fmt(x: float) -> str:
    """Do 2 miejsc po przecinku, bez zer końcowych: 70 → „70”, 1,35 → „1,35”."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def ppm_mifflin(plec: str, masa_kg: float, wzrost_cm: float, wiek: float) -> float:
    """PPM = 10·m + 6,25·h − 5·wiek + 5 (M) / − 161 (K)."""
    if plec not in PLCI:
        raise ValueError(f"Nieznana płeć: {plec!r}")
    baza = 10.0 * masa_kg + 6.25 * wzrost_cm - 5.0 * wiek
    return baza + (5.0 if plec == PLEC_M else -161.0)


def pal(praca: str, treningi: str, kroki: str | None = None) -> tuple[float, list[str]]:
    """PAL = baza z pracy + dodatek za treningi + korekta za kroki, w [1,2; 1,9]."""
    if praca not in PRACA:
        raise ValueError(f"Nieznany charakter pracy: {praca!r}")
    if treningi not in TRENINGI:
        raise ValueError(f"Nieznana częstotliwość treningów: {treningi!r}")
    if kroki is not None and kroki not in KROKI:
        raise ValueError(f"Nieznany przedział kroków: {kroki!r}")
    b, t = PRACA[praca], TRENINGI[treningi]
    k = KROKI[kroki] if kroki is not None else 0.0
    surowy = b + t + k
    wynik = min(PAL_MAX, max(PAL_MIN, surowy))
    wiersze = [f"praca: {praca.lower()} → {_fmt(b)}",
               f"treningi: {treningi.lower()} → +{_fmt(t)}"]
    if kroki is not None and kroki != "Nie wiem":
        wiersze.append(f"kroki: {kroki.lower()} → {'+' if k >= 0 else '−'}{_fmt(abs(k))}")
    if wynik != surowy:
        wiersze.append(f"PAL ograniczony do zakresu {_fmt(PAL_MIN)}–{_fmt(PAL_MAX)}")
    return round(wynik, 2), wiersze


def korekta(cel: str, tempo: str | None) -> float:
    """Korekta CPM pod cel jako ułamek (−0,15 = −15 %)."""
    if cel == CEL_UTRZYMANIE:
        return 0.0
    if cel == CEL_REDUKCJA:
        if tempo not in TEMPO_REDUKCJA:
            raise ValueError("Redukcja wymaga wyboru tempa.")
        return TEMPO_REDUKCJA[tempo]
    if cel == CEL_MASA:
        if tempo not in TEMPO_MASA:
            raise ValueError("Budowa masy wymaga wyboru tempa.")
        return TEMPO_MASA[tempo]
    raise ValueError(f"Nieznany cel: {cel!r}")


def _sprawdz(w: Wejscie) -> None:
    bledy: dict[str, str] = {}
    if w.plec not in PLCI:
        bledy["plec"] = "brak lub nieznana"
    for nazwa, wart, (lo, hi) in (("wiek", w.wiek, ZAKRES_WIEK), ("wzrost_cm", w.wzrost_cm, ZAKRES_WZROST),
                                  ("masa_kg", w.masa_kg, ZAKRES_MASA)):
        if wart is None or not (lo <= wart <= hi):
            bledy[nazwa] = f"poza zakresem {_fmt(lo)}–{_fmt(hi)}"
    if w.praca not in PRACA:
        bledy["praca"] = "brak lub nieznana"
    if w.treningi not in TRENINGI:
        bledy["treningi"] = "brak lub nieznana"
    if w.kroki is not None and w.kroki not in KROKI:
        bledy["kroki"] = "nieznany przedział"
    if w.cel not in CELE:
        bledy["cel"] = "brak lub nieznany"
    elif w.cel == CEL_REDUKCJA and w.tempo not in TEMPO_REDUKCJA:
        bledy["tempo"] = "brak tempa redukcji"
    elif w.cel == CEL_MASA and w.tempo not in TEMPO_MASA:
        bledy["tempo"] = "brak tempa budowy masy"
    if bledy:
        raise BrakDanych(bledy)


def oblicz(w: Wejscie) -> Wynik:
    """Pełne wyliczenie z podstawieniem. BrakDanych przy niepełnym wejściu.
    CPM liczony z PPM niezaokrąglonego (wiersz podstawienia pokazuje PPM
    zaokrąglone — różnica najwyżej 1 kcal)."""
    _sprawdz(w)
    ppm_f = ppm_mifflin(w.plec, w.masa_kg, w.wzrost_cm, w.wiek)
    ppm = round(ppm_f)
    p, wiersze_pal = pal(w.praca, w.treningi, w.kroki)
    cpm = round(ppm_f * p)
    kor = korekta(w.cel, w.tempo)
    po_korekcie = round(cpm * (1.0 + kor))
    kcal = int(round(po_korekcie / ZAOKRAGLENIE_WYNIKU) * ZAOKRAGLENIE_WYNIKU)
    ostrzezenia: list[str] = []
    podniesione = False
    if kcal < ppm_f:
        # Bezpiecznik PO zaokrągleniu: wynik nigdy poniżej PPM (w górę do 10 kcal).
        kcal = int(math.ceil(ppm_f / ZAOKRAGLENIE_WYNIKU) * ZAOKRAGLENIE_WYNIKU)
        ostrzezenia.append(OSTRZEZENIE_PONIZEJ_PPM)
        podniesione = True
    stala = "+ 5" if w.plec == PLEC_M else "− 161"
    wiersz_ppm = (f"PPM (Mifflin-St Jeor, {w.plec.lower()}): 10 × {_fmt(w.masa_kg)} kg + 6,25 × "
                  f"{_fmt(w.wzrost_cm)} cm − 5 × {_fmt(w.wiek)} lat {stala} = {ppm} kcal")
    podst = [
        wiersz_ppm,
        *wiersze_pal,
        f"PAL = {_fmt(p)}",
        f"CPM = {ppm} × {_fmt(p)} = {cpm} kcal",
    ]
    if kor == 0.0:
        podst.append(f"cel: {w.cel.lower()} → bez korekty")
    else:
        znak = "−" if kor < 0 else "+"
        podst.append(f"cel: {w.cel.lower()}, {w.tempo.lower() if w.tempo else ''} → {cpm} {znak} {abs(round(kor * 100))} % "
                     f"= {po_korekcie} kcal")
    if podniesione:
        podst.append(f"{po_korekcie} kcal to mniej niż PPM ({ppm}) → podniesione do {kcal} kcal")
    podst.append(f"wynik zaokrąglony do {ZAOKRAGLENIE_WYNIKU} kcal: ≈ {kcal} kcal / dzień")
    return Wynik(ppm=ppm, pal=p, cpm=cpm, korekta_pct=round(kor * 100), kcal=kcal,
                 ostrzezenia=tuple(ostrzezenia), podstawienie=tuple(podst))


def z_odpowiedzi(wartosci: dict[str, str | None]) -> Wejscie:
    """Mapa odpowiedzi wywiadu (`definicje.wartosci`) → `Wejscie`. Liczby z
    przecinkiem; brakujące → None (walidacja w `oblicz`)."""
    cel = wartosci.get("zk_cel") or ""
    tempo = None
    if cel == CEL_REDUKCJA:
        tempo = wartosci.get("zk_tempo_redukcja")
    elif cel == CEL_MASA:
        tempo = wartosci.get("zk_tempo_masa")
    return Wejscie(
        plec=wartosci.get("zk_plec") or "",
        wiek=liczba(wartosci.get("zk_wiek")),  # type: ignore[arg-type]
        wzrost_cm=liczba(wartosci.get("zk_wzrost")),  # type: ignore[arg-type]
        masa_kg=liczba(wartosci.get("zk_masa")),  # type: ignore[arg-type]
        praca=wartosci.get("zk_praca") or "",
        treningi=wartosci.get("zk_treningi") or "",
        kroki=wartosci.get("zk_kroki") or None,
        cel=cel, tempo=tempo,
    )

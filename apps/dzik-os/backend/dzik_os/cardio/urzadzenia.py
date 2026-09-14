"""Przełożenie intensywności na urządzenie: gałka „tempo” i gałka
„obciążenie” (model §5 — [C], DO PRZEGLĄDU TRENERA) oraz MET-y do szacunku
wydatku energii ([B], Compendium of Physical Activities — przybliżenie).

Zasada: intensywność jest jedna (tętno/RPE), urządzenie dostaje dwie
sugestie startowe „zacznij od…, dojdź do tętna/RPE z zakresu”, bo
urządzenia różnią się kalibracją. Kolumny G/R/W = pasmo intensywności
(regeneracyjne / redukcyjne / wydolnościowe), nie nazwa celu.
"""

from __future__ import annotations

URZADZENIA: tuple[str, ...] = ("rowerek", "bieznia", "bieznia_skos", "steper", "wioslarz")

ETYKIETY: dict[str, str] = {
    "rowerek": "Rowerek stacjonarny",
    "bieznia": "Bieżnia (marsz/bieg)",
    "bieznia_skos": "Bieżnia skos / chód pod górę",
    "steper": "Steper",
    "wioslarz": "Wioślarz",
}

#: Wpis katalogu ćwiczeń, do którego pozycja cardio może się odnosić (miękko, po nazwie).
CWICZENIE_KATALOGU: dict[str, str] = {
    "rowerek": "Rower stacjonarny — jazda ciągła",
    "bieznia": "Bieżnia — bieg ciągły",
    "bieznia_skos": "Marsz pod górę na bieżni",
    "steper": "Stepper",
    "wioslarz": "Wioślarz — wiosłowanie ciągłe",
}

#: Pasma: G (<65 % HRmax), R (65–80), W (≥80). Wartości tekstowe, bo to
#: sugestie startowe, nie parametry do przeliczania.
PARAMETRY: dict[str, dict] = {
    "rowerek": {
        "tempo_nazwa": "kadencja", "tempo_jednostka": "obr./min",
        "obciazenie_nazwa": "opór", "obciazenie_jednostka": "poziom",
        "G": {"tempo": "70–80", "obciazenie": "niski"},
        "R": {"tempo": "80–90", "obciazenie": "umiarkowany"},
        "W": {"tempo": "90–100", "obciazenie": "wysoki"},
    },
    "bieznia": {
        "tempo_nazwa": "prędkość", "tempo_jednostka": "km/h",
        "obciazenie_nazwa": "nachylenie", "obciazenie_jednostka": "%",
        "G": {"tempo": "marsz 5–6", "obciazenie": "0–2"},
        "R": {"tempo": "trucht 7–9 albo marsz 6–6,5", "obciazenie": "0–1 (marsz: 3–5)"},
        "W": {"tempo": "bieg 10–14", "obciazenie": "1"},
    },
    "bieznia_skos": {
        "tempo_nazwa": "prędkość", "tempo_jednostka": "km/h",
        "obciazenie_nazwa": "nachylenie", "obciazenie_jednostka": "%",
        "G": {"tempo": "5", "obciazenie": "5"},
        "R": {"tempo": "5,5", "obciazenie": "8–12"},
        "W": {"tempo": "6", "obciazenie": "12–15 (interwały nachyleniem, nie biegiem)"},
    },
    "steper": {
        "tempo_nazwa": "kroki", "tempo_jednostka": "kroki/min",
        "obciazenie_nazwa": "opór", "obciazenie_jednostka": "poziom",
        "G": {"tempo": "40–50", "obciazenie": "niski"},
        "R": {"tempo": "55–70", "obciazenie": "umiarkowany"},
        "W": {"tempo": "75–90", "obciazenie": "wysoki"},
    },
    "wioslarz": {
        "tempo_nazwa": "uderzenia", "tempo_jednostka": "spm",
        "obciazenie_nazwa": "opór (damper)", "obciazenie_jednostka": "poziom",
        "G": {"tempo": "18–22", "obciazenie": "3–5"},
        "R": {"tempo": "22–26", "obciazenie": "3–5"},
        "W": {"tempo": "28–32", "obciazenie": "3–5"},
    },
}

#: MET per urządzenie i pasmo [B] — przybliżenie z Compendium (rower 4,0/6,8/10;
#: marsz 3,5 / trucht 7 / bieg 10; chód pod górę 5,3/6,5/8; stepper 4/6/8,8;
#: wioślarz 4,8/7/8,5).
MET: dict[str, dict[str, float]] = {
    "rowerek": {"G": 4.0, "R": 6.8, "W": 10.0},
    "bieznia": {"G": 3.5, "R": 7.0, "W": 10.0},
    "bieznia_skos": {"G": 5.3, "R": 6.5, "W": 8.0},
    "steper": {"G": 4.0, "R": 6.0, "W": 8.8},
    "wioslarz": {"G": 4.8, "R": 7.0, "W": 8.5},
}


def pasmo(pct_hrmax: float) -> str:
    """Pasmo intensywności dla środka zakresu %HRmax."""
    if pct_hrmax < 65:
        return "G"
    if pct_hrmax < 80:
        return "R"
    return "W"


def parametry(urzadzenie: str, pct_praca: float, pct_przerwa: float | None = None) -> dict:
    """Sugestie startowe dla urządzenia; przy interwałach osobno praca i przerwa."""
    p = PARAMETRY[urzadzenie]
    praca = p[pasmo(pct_praca)]
    out = {
        "machine": urzadzenie, "label": ETYKIETY[urzadzenie],
        "tempo_name": p["tempo_nazwa"], "tempo_unit": p["tempo_jednostka"],
        "load_name": p["obciazenie_nazwa"], "load_unit": p["obciazenie_jednostka"],
        "tempo": praca["tempo"], "load": praca["obciazenie"],
        "rest_tempo": None, "rest_load": None,
        "catalog_exercise": CWICZENIE_KATALOGU[urzadzenie],
        "review": "do przeglądu trenera",
    }
    if pct_przerwa is not None:
        przerwa = p[pasmo(pct_przerwa)]
        out["rest_tempo"] = przerwa["tempo"]
        out["rest_load"] = przerwa["obciazenie"]
    return out


def met(urzadzenie: str, pct_hrmax: float) -> float:
    return MET[urzadzenie][pasmo(pct_hrmax)]


def kcal(urzadzenie: str, pct_hrmax: float, masa_kg: float | None, czas_min: float) -> int | None:
    """Szacunek: MET × masa × godziny. Bez masy — brak liczby (nie zgadujemy)."""
    if masa_kg is None or masa_kg <= 0 or czas_min <= 0:
        return None
    return round(met(urzadzenie, pct_hrmax) * masa_kg * czas_min / 60.0)

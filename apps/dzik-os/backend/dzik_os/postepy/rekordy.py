"""Silnik rekordów osobistych (spec „Monitoring / Postępy” §8) — czyste funkcje.

Wejście: serie treningowe (ciężar w kg, powtórzenia, data sesji, flagi),
wyjście: pełna historia rekordów per ćwiczenie i typ, liczona od zera —
deterministycznie, więc przeliczenie po korekcie serii cofa rekord samo z
siebie (§8.2.9), a dwukrotny backfill daje identyczny stan.

Reguły (§8.1–8.2): pierwsze wykonanie ćwiczenia nie jest rekordem; E1RM
(Epley) tylko dla r ≤ 10; serie rozgrzewkowe / nieukończone / z asekuracją
wykluczone; wariant = osobne ćwiczenie (klucz = znormalizowana nazwa);
masa ciała bez obciążenia (w = 0) → wyłącznie REPS_AT_WEIGHT; wyrównanie
nie jest nowym rekordem (widoczne jako „wyrównany”). Porównania wyłącznie
z własną historią klienta — nigdy między ludźmi.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

TYPY = ("WEIGHT", "REPS_AT_WEIGHT", "SET_VOLUME", "SESSION_VOLUME", "E1RM")
E1RM_MAX_REPS = 10
KG_NA_FUNT = 0.45359237


def normalizuj_ciezar(value: float, unit: str = "kg") -> float:
    """Ciężar w kilogramach, zaokrąglony do 0,01 — funty przeliczane przy
    zapisie (§8.2.6), więc 100 lb i 45,36 kg to ta sama wartość."""
    u = (unit or "kg").strip().lower()
    if u in ("lb", "lbs", "funt", "funty"):
        return round(float(value) * KG_NA_FUNT, 2)
    return round(float(value), 2)


def klucz_cwiczenia(nazwa: str) -> str:
    """Tożsamość ćwiczenia (decyzja właściciela 14.09): znormalizowana nazwa —
    małe litery, pojedyncze spacje, bez końcowej interpunkcji. Bez usuwania
    diakrytyki (wariant = osobne ćwiczenie; „bliźniaki” raportuje backfill)."""
    s = unicodedata.normalize("NFC", (nazwa or "").strip().lower())
    s = re.sub(r"\s+", " ", s)
    return s.rstrip(" .,:;-")


def klucz_blizniaka(nazwa: str) -> str:
    """Klucz do wykrywania bliźniaków: jak `klucz_cwiczenia`, ale bez
    diakrytyki i znaków niealfanumerycznych — dwa różne klucze z tym samym
    kluczem bliźniaka to podejrzenie literówki, do decyzji trenera."""
    s = unicodedata.normalize("NFKD", klucz_cwiczenia(nazwa))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", s)


def epley_e1rm(weight_kg: float, reps: int) -> float:
    """Szacowany 1RM (Epley): w × (1 + r/30). SZACUNEK do obserwacji trendu."""
    if reps <= 1:
        return round(float(weight_kg), 1)
    return round(float(weight_kg) * (1 + reps / 30), 1)


@dataclass(frozen=True)
class Seria:
    set_ref: str            # np. "<entry_id>:<index>"
    exercise_key: str
    performed_on: str       # YYYY-MM-DD
    session_id: str
    weight_kg: float
    reps: int
    warmup: bool = False
    incomplete: bool = False
    assisted: bool = False

    @property
    def liczy_sie(self) -> bool:
        return (not self.warmup and not self.incomplete and not self.assisted
                and self.reps >= 1 and self.weight_kg >= 0)


@dataclass
class Rekord:
    exercise_key: str
    record_type: str
    value: float
    achieved_on: str
    session_id: str
    set_ref: str | None = None
    secondary_value: float | None = None
    previous_value: float | None = None
    equaled_on: str | None = None       # ostatnie wyrównanie (bez nowego wpisu)
    superseded_on: str | None = None    # data pobicia; None = aktualny
    history: list[str] = field(default_factory=list)

    @property
    def aktualny(self) -> bool:
        return self.superseded_on is None


def _sesje(serie: list[Seria]) -> list[tuple[tuple[str, str], list[Seria]]]:
    """Serie pogrupowane po sesji, w kolejności dat (data, id sesji)."""
    grupy: dict[tuple[str, str], list[Seria]] = {}
    for s in serie:
        grupy.setdefault((s.performed_on, s.session_id), []).append(s)
    return sorted(grupy.items(), key=lambda kv: kv[0])


def _kandydaci(sesja: list[Seria]) -> dict[tuple[str, float | None], tuple[float, str | None]]:
    """Najlepsze wartości sesji per (typ, wartość drugorzędna) → (wartość, set_ref)."""
    out: dict[tuple[str, float | None], tuple[float, str | None]] = {}

    def lepszy(klucz: tuple[str, float | None], wartosc: float, ref: str | None) -> None:
        if wartosc <= 0:
            return
        cur = out.get(klucz)
        if cur is None or wartosc > cur[0]:
            out[klucz] = (wartosc, ref)

    tonaz = 0.0
    for s in sesja:
        if not s.liczy_sie:
            continue
        w, r = round(float(s.weight_kg), 2), int(s.reps)
        lepszy(("REPS_AT_WEIGHT", w), float(r), s.set_ref)
        if w > 0:
            lepszy(("WEIGHT", None), w, s.set_ref)
            lepszy(("SET_VOLUME", None), round(w * r, 1), s.set_ref)
            tonaz += w * r
            if r <= E1RM_MAX_REPS:
                lepszy(("E1RM", None), epley_e1rm(w, r), s.set_ref)
    if tonaz > 0:
        out[("SESSION_VOLUME", None)] = (round(tonaz, 1), None)
    return out


def licz_rekordy(serie: list[Seria]) -> dict[str, list[Rekord]]:
    """Pełna historia rekordów per ćwiczenie. Pierwsza sesja z ćwiczeniem
    ustala punkt odniesienia (bez rekordu, §8.2.1); każda kolejna sesja
    porównuje się z najlepszym dotychczasowym wynikiem: większy = nowy
    rekord (poprzedni dostaje `superseded_on`), równy = „wyrównany”."""
    per_cw: dict[str, list[Seria]] = {}
    for s in serie:
        per_cw.setdefault(s.exercise_key, []).append(s)
    wynik: dict[str, list[Rekord]] = {}
    for cw, lista in per_cw.items():
        sesje = [(k, g) for k, g in _sesje(lista) if any(s.liczy_sie for s in g)]
        rekordy: list[Rekord] = []
        najlepsze: dict[tuple[str, float | None], float] = {}
        biezacy: dict[tuple[str, float | None], Rekord] = {}
        for nr, ((data, session_id), sesja) in enumerate(sesje):
            kand = _kandydaci(sesja)
            for klucz, (wartosc, ref) in kand.items():
                typ, drugorzedna = klucz
                poprzednia = najlepsze.get(klucz)
                if nr == 0 or poprzednia is None:
                    # Punkt odniesienia (pierwsza sesja albo pierwszy raz przy tym
                    # ciężarze dla REPS_AT_WEIGHT) — bez rekordu.
                    najlepsze[klucz] = max(wartosc, poprzednia or 0.0)
                    continue
                if wartosc > poprzednia:
                    stary = biezacy.get(klucz)
                    if stary is not None:
                        stary.superseded_on = data
                    nowy = Rekord(exercise_key=cw, record_type=typ, value=wartosc, achieved_on=data,
                                  session_id=session_id, set_ref=ref, secondary_value=drugorzedna,
                                  previous_value=poprzednia)
                    rekordy.append(nowy)
                    biezacy[klucz] = nowy
                    najlepsze[klucz] = wartosc
                elif wartosc == poprzednia and klucz in biezacy:
                    biezacy[klucz].equaled_on = data
        wynik[cw] = rekordy
    return wynik


def aktualne(rekordy: dict[str, list[Rekord]]) -> dict[str, list[Rekord]]:
    return {cw: [r for r in lista if r.aktualny] for cw, lista in rekordy.items()}


def nowe_w_sesji(rekordy: dict[str, list[Rekord]], session_id: str) -> list[Rekord]:
    """Rekordy ustanowione w danej sesji (do jednego, zbiorczego powiadomienia §8.3)."""
    return [r for lista in rekordy.values() for r in lista if r.session_id == session_id]


def serie_z_wpisu(*, entry_id: str, exercise_name: str, performed_on: str, session_id: str,
                  sets: list[dict]) -> list[Seria]:
    """Serie z `WorkoutEntry.sets_json` ([{"weight_kg", "reps", "warmup"?, ...}])."""
    out: list[Seria] = []
    for i, s in enumerate(sets or []):
        try:
            w = float(s.get("weight_kg") or 0)
            r = int(s.get("reps") or 0)
        except (TypeError, ValueError):
            continue
        out.append(Seria(set_ref=f"{entry_id}:{i}", exercise_key=klucz_cwiczenia(exercise_name),
                         performed_on=performed_on, session_id=session_id, weight_kg=w, reps=r,
                         warmup=bool(s.get("warmup")), incomplete=bool(s.get("incomplete")),
                         assisted=bool(s.get("assisted"))))
    return out

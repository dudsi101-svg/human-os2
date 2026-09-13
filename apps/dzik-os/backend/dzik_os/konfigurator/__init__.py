"""Konfigurator miesięcznych planów treningowych (pakiet właściciela 1.0, 13.09.2026).

Deterministyczny silnik + osobny walidator. Model językowy NIE bierze
udziału w doborze liczb; reguły bezpieczeństwa, dawka, czas i kalendarz
są obliczane tutaj. Wynik dla trenera to SZKIC (propose-only): trener
przegląda, poprawia i dopiero wtedy zapisuje jako wersję planu
podopiecznego. Progi oznaczone H są heurystykami produktu, nie
zaleceniami klinicznymi (patrz dane/zrodla.json).

Publiczne wejście: `generuj_plan(wejscie, plan_id=...) -> dict`
(status, plan|None, issues, questions, versions).
"""

from .silnik import generuj_plan
from .walidator import waliduj_plan, waliduj_wejscie

__all__ = ["generuj_plan", "waliduj_plan", "waliduj_wejscie"]

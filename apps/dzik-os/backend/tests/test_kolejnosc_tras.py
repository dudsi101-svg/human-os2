"""Bramka kolejności tras: trasa z parametrem nie może zasłaniać statycznej.

Skąd to się wzięło
------------------
18.08.2026 scalenie dwóch gałęzi ustawiło `/coach/plan-templates/{template_id}`
PRZED `/coach/plan-templates/import-schema`, `/import-example` i
`/export-file`. FastAPI dopasowuje trasy w kolejności rejestracji, więc te trzy
przestały być osiągalne — żądania trafiały do trasy z parametrem i wracały
z „Nie znaleziono szablonu". Kod obu funkcji był poprawny; zawiodła kolejność.

To awaria wyjątkowo cicha: endpoint odpowiada 404, czyli wygląda na poprawnie
działającą odmowę, a nie na trasę, której nie ma. Żaden test funkcji
importu-z-pliku nie musiał tego złapać, bo one wołają własne ścieżki wprost.

Test jest ogólny — obejmuje CAŁE API, nie tylko szablony.
"""

from __future__ import annotations

import unittest

from dzik_os.main import app


def _trasy() -> list[tuple[str, frozenset[str]]]:
    """Ścieżki w kolejności REJESTRACJI (tej samej, której używa dopasowanie)."""
    out: list[tuple[str, frozenset[str]]] = []
    for route in app.routes:
        for sub in getattr(route, "routes", [route]):
            sciezka = getattr(sub, "path", None)
            metody = getattr(sub, "methods", None)
            if sciezka and metody:
                out.append((sciezka, frozenset(metody)))
    return out


def _zaslania(wzorzec: str, konkretna: str) -> bool:
    """Czy `wzorzec` (z parametrami) pochłania ścieżkę `konkretna`?"""
    a, b = wzorzec.strip("/").split("/"), konkretna.strip("/").split("/")
    if len(a) != len(b):
        return False
    for seg_a, seg_b in zip(a, b):
        if seg_a.startswith("{"):
            continue  # parametr łyka dowolny segment
        if seg_a != seg_b:
            return False
    return True


class TestKolejnoscTras(unittest.TestCase):
    def test_trasa_z_parametrem_nie_przechwytuje_pozniejszej_statycznej(self) -> None:
        trasy = _trasy()
        naruszenia: list[str] = []

        for i, (wzorzec, metody_w) in enumerate(trasy):
            if "{" not in wzorzec:
                continue
            for statyczna, metody_s in trasy[i + 1:]:
                if "{" in statyczna:
                    continue
                if not (metody_w & metody_s):
                    continue  # inne metody HTTP nie kolidują
                if _zaslania(wzorzec, statyczna):
                    naruszenia.append(
                        f"  {sorted(metody_w & metody_s)} {statyczna}\n"
                        f"      jest przechwytywana przez wcześniejszą {wzorzec}"
                    )

        self.assertEqual(
            naruszenia,
            [],
            "Trasy statyczne są zasłonięte przez wcześniejsze trasy z parametrem. "
            "FastAPI dopasowuje w kolejności rejestracji, więc te ścieżki są "
            "nieosiągalne (zwracają odpowiedź trasy parametrycznej, zwykle 404 — "
            "co wygląda jak poprawna odmowa). Przenieś trasy statyczne PRZED "
            "parametryczne:\n" + "\n".join(naruszenia),
        )


if __name__ == "__main__":
    unittest.main()

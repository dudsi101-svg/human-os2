"""Strażnik pakietowania: pliki danych JSON muszą trafiać do zbudowanego
pakietu (koło), bo obraz produkcyjny instaluje backend NIE-edytowalnie.

13.09.2026: wersja 0.56.0 wstała lokalnie i w CI (instalacja `-e`), a na
Fly padła przy starcie na brakującym `wiedza/dane/tresci_startowe.json`.
Ten test buduje koło tak jak Dockerfile (pip, z izolacją budowania —
`license = "Apache-2.0"` w pyproject wymaga setuptools>=77, więc stary
systemowy setuptools bez izolacji nie zbuduje pakietu) i sprawdza, że
KAŻDY plik spoza *.py leżący w `dzik_os/` jest w archiwum.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _pliki_danych() -> set[str]:
    out = set()
    for p in (BACKEND / "dzik_os").rglob("*"):
        if p.is_file() and p.suffix not in {".py", ".pyc"} and "__pycache__" not in p.parts:
            out.add(p.relative_to(BACKEND).as_posix())
    return out


def test_kolo_zawiera_wszystkie_pliki_danych(tmp_path: Path) -> None:
    dane = _pliki_danych()
    assert dane, "brak plików danych do sprawdzenia — test stracił sens"
    # Budujemy z CZYSTEJ kopii źródeł: zalegający `*.egg-info/SOURCES.txt`
    # po wcześniejszym buildzie potrafi dołożyć pliki do koła i zamaskować
    # regresję (sprawdzone 13.09 — „dowód” z brudnego katalogu kłamał).
    zrodla = tmp_path / "src"
    shutil.copytree(BACKEND, zrodla, ignore=shutil.ignore_patterns(
        "build", "*.egg-info", "__pycache__", ".pytest_cache", "tests"))
    kola_dir = tmp_path / "whl"
    r = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q",
         "-w", str(kola_dir), str(zrodla)],
        capture_output=True, text=True, timeout=280, check=False,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    kola = list(kola_dir.glob("*.whl"))
    assert len(kola) == 1, kola
    with zipfile.ZipFile(kola[0]) as z:
        w_kole = set(z.namelist())
    brak = sorted(p for p in dane if p not in w_kole)
    assert not brak, f"pliki danych poza pakietem (dopisz do [tool.setuptools.package-data]): {brak}"

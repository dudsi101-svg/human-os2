"""Przegląd mutacyjny obron bezpieczeństwa — czy testy naprawdę ich pilnują.

701 przechodzących testów nie mówi nic o tym, czy któryś z nich zauważy
WYŁĄCZENIE obrony. Jedyny sposób, żeby to wykazać: po kolei psuć każdą
obronę i sprawdzać, czy suita robi się czerwona.

    python apps/dzik-os/tools/mutacje_bezpieczenstwa.py            # wszystko
    python apps/dzik-os/tools/mutacje_bezpieczenstwa.py izolacja   # jedna grupa

Każdy **przeżyty mutant to potencjalna dziura**: obrona, którą można
usunąć jednym ruchem, a wszystkie testy zostaną zielone. Narzędzie zawsze
przywraca oryginały, także po przerwaniu (blok `finally`).

Uwaga: mutacje są celowo BRUTALNE (wyłączenie całej obrony), a nie
subtelne. Chodzi o pytanie „czy cokolwiek tego pilnuje", nie o pomiar
pokrycia.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[3]
BACKEND = KORZEN / "apps" / "dzik-os" / "backend"


@dataclass(frozen=True)
class Mutacja:
    grupa: str
    nazwa: str
    plik: str
    szukaj: str
    zamien: str
    testy: tuple[str, ...]


MUTACJE: tuple[Mutacja, ...] = (
    # --- Izolacja danych między klientami i trenerami ---
    Mutacja(
        "izolacja", "trener widzi KAŻDEGO klienta (bez relacji)",
        "dzik_os/authz.py",
        "    if active_relationship(db, coach_id, client_id) is None:\n        return False",
        "    if False:\n        return False",
        ("tests/test_idor.py", "tests/test_authz_matrix.py", "tests/test_consents.py"),
    ),
    Mutacja(
        "izolacja", "dostęp do danych klienta bez sprawdzania zgody",
        "dzik_os/authz.py",
        "    return ConsentService.authorize(",
        "    return True or ConsentService.authorize(",
        ("tests/test_idor.py", "tests/test_authz_matrix.py", "tests/test_consents.py",
         "tests/test_consent_categories.py"),
    ),
    Mutacja(
        "izolacja", "brak odmowy przy obcym kliencie (resolve_client_access)",
        "dzik_os/authz.py",
        '    raise ResourceAccessDenied(actor.id, f"client:{client_id}")',
        "    return client_id",
        ("tests/test_idor.py", "tests/test_authz_matrix.py"),
    ),
    Mutacja(
        "izolacja", "cudzy zasób przechodzi kontrolę właściciela",
        "dzik_os/authz.py",
        "    if getattr(entity, owner_attr) != actor.id:\n        raise ResourceAccessDenied(actor.id, resource)",
        "    if False:\n        raise ResourceAccessDenied(actor.id, resource)",
        ("tests/test_idor.py", "tests/test_sheet_import.py", "tests/test_authz_matrix.py"),
    ),
    # --- Uwierzytelnianie ---
    Mutacja(
        "logowanie", "każde hasło pasuje",
        "dzik_os/security.py",
        "def verify_password(",
        "def verify_password(*_a, **_k):\n    return True\n\n\ndef _verify_password_oryginal(",
        ("tests/test_auth.py", "tests/test_mfa.py"),
    ),
    # --- Nieodwracalność / cofanie importu ---
    Mutacja(
        "cofanie", "cofnięcie importu nie przywraca pól",
        "dzik_os/sheet_import.py",
        "            for attr, value in entry.get(\"before\", {}).items():\n"
        "                if attr in SNAPSHOT_FIELDS:\n                    setattr(item, attr, value)",
        "            for attr, value in entry.get(\"before\", {}).items():\n"
        "                if attr in SNAPSHOT_FIELDS:\n                    pass",
        ("tests/test_sheet_import.py",),
    ),
    Mutacja(
        "cofanie", "migawka przed importem w ogóle nie powstaje",
        "dzik_os/sheet_import.py",
        "    if report.dry_run or not report.snapshot:\n        return None",
        "    if True:\n        return None",
        ("tests/test_sheet_import.py",),
    ),
    Mutacja(
        "cofanie", "import w trybie ZASTAP nadpisuje mimo trybu UZUPELNIJ",
        "dzik_os/sheet_import.py",
        "        if current and mode == MODE_FILL:\n            continue",
        "        if False:\n            continue",
        ("tests/test_sheet_import.py",),
    ),
    # --- Prywatność w audycie ---
    Mutacja(
        "prywatnosc", "podgląd (dry_run) jednak zapisuje do bazy",
        "dzik_os/sheet_import.py",
        "        if is_new:\n            report.created += 1\n            report.created_names.append(name)\n"
        "            if dry_run:\n                continue",
        "        if is_new:\n            report.created += 1\n            report.created_names.append(name)\n"
        "            if False:\n                continue",
        ("tests/test_sheet_import.py",),
    ),
)


def uruchom(testy: tuple[str, ...]) -> tuple[int, str]:
    wynik = subprocess.run(
        [sys.executable, "-m", "pytest", *testy, "-q", "--no-header", "-x", "--tb=no", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=BACKEND, check=False,
    )
    linie = [w for w in wynik.stdout.strip().splitlines() if w.strip()]
    return wynik.returncode, (linie[-1] if linie else "brak wyjścia")


def main() -> int:
    tylko = sys.argv[1] if len(sys.argv) > 1 else None
    wybrane = [m for m in MUTACJE if tylko is None or m.grupa == tylko]
    if not wybrane:
        print(f"Nie ma grupy {tylko!r}. Dostepne: "
              + ", ".join(sorted({m.grupa for m in MUTACJE})))
        return 2

    zapas = Path(tempfile.mkdtemp(prefix="mutacje-"))
    pliki = sorted({m.plik for m in wybrane})
    for wzgledny in pliki:
        shutil.copy(BACKEND / wzgledny, zapas / Path(wzgledny).name)

    przezyly: list[Mutacja] = []
    niewstrzykniete: list[Mutacja] = []
    try:
        print("=== stan wyjściowy ===")
        kod, opis = uruchom(tuple(sorted({t for m in wybrane for t in m.testy})))
        print(f"  {opis}")
        if kod != 0:
            print("  PRZERWANE: testy nie przechodzą na nienaruszonym kodzie")
            return 1

        for numer, m in enumerate(wybrane, 1):
            for wzgledny in pliki:
                shutil.copy(zapas / Path(wzgledny).name, BACKEND / wzgledny)
            sciezka = BACKEND / m.plik
            tresc = sciezka.read_text(encoding="utf-8")
            if m.szukaj not in tresc:
                print(f"\n[{numer}/{len(wybrane)}] {m.grupa}: {m.nazwa}\n"
                      "  NIE WSTRZYKNIĘTO — wzorzec nie pasuje do kodu (zmienił się?)")
                niewstrzykniete.append(m)
                continue
            sciezka.write_text(tresc.replace(m.szukaj, m.zamien, 1), encoding="utf-8")
            kod, opis = uruchom(m.testy)
            print(f"\n[{numer}/{len(wybrane)}] {m.grupa}: {m.nazwa}")
            print(f"  {opis}")
            if kod == 0:
                print("  >>> MUTANT PRZEŻYŁ — tej obrony nie pilnuje żaden test")
                przezyly.append(m)
            else:
                print("  zabity")
    finally:
        for wzgledny in pliki:
            shutil.copy(zapas / Path(wzgledny).name, BACKEND / wzgledny)
        shutil.rmtree(zapas, ignore_errors=True)
        print("\n(oryginały przywrócone)")

    print("\n" + "=" * 60)
    zabite = len(wybrane) - len(przezyly) - len(niewstrzykniete)
    print(f"WYNIK: zabitych {zabite}/{len(wybrane)}")
    for m in niewstrzykniete:
        print(f"  ? nie wstrzyknięto: {m.grupa} — {m.nazwa}")
    for m in przezyly:
        print(f"  ! PRZEŻYŁ: {m.grupa} — {m.nazwa}  (testy: {', '.join(m.testy)})")
    return 1 if przezyly or niewstrzykniete else 0


if __name__ == "__main__":
    raise SystemExit(main())

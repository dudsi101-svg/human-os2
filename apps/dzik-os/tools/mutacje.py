"""Przegląd mutacyjny kontroli spójności — czy jej testy naprawdę pilnują.

Test, który przechodzi także wtedy, gdy sprawdzana rzecz jest zepsuta,
niczego nie pilnuje. Jedyny sposób, żeby to wykazać, a nie zadeklarować:
zepsuć kontrolę na kilka sposobów i sprawdzić, czy testy się zaczerwienią.

    python apps/dzik-os/tools/mutacje.py     # z korzenia repozytorium

Narzędzie po kolei podmienia fragmenty `tools/spojnosc.py`, uruchamia
`tests/test_spojnosc.py` i na koniec PRZYWRACA oryginał. Mutacja, której
testy nie wykryły, jest wypisana jako luka.

Wynik z 2026-08-18 (pierwsze uruchomienie) — dwie luki, obie naprawione
tego samego dnia:
* usunięcie progu `PROG_TRAS` nie wywracało żadnego testu, czyli
  zabezpieczenie przed cichą śmiercią kontroli tras samo nie było
  zabezpieczone;
* zamiana kontroli dokumentów w atrapę przechodziła bez śladu.

Uruchamiaj po każdej zmianie w `spojnosc.py` i po dołożeniu kontroli.
"""
import shutil
import subprocess
import sys
from pathlib import Path

NARZEDZIE = Path("apps/dzik-os/tools/spojnosc.py")
ORYGINAL = Path("/tmp/spojnosc.oryginal.py")  # kopia robocza, tworzona niżej

if not ORYGINAL.exists():
    shutil.copy(NARZEDZIE, ORYGINAL)

MUTACJE = [
    ("migracje: usunięta kontrola duplikatów",
     '''    duplikaty = sorted({n for n in numery if numery.count(n) > 1})
    if duplikaty:
        w.blad("migracje", f"numery użyte więcej niż raz: {duplikaty} — jedna z nich "
                           "nigdy się nie wykona")''',
     '    duplikaty = []'),

    ("changelog: usunięta kontrola powtórzonej wersji",
     '''    duplikaty = sorted({v for v in wersje if wersje.count(v) > 1})
    if duplikaty:
        w.blad("changelog", f"wersja przydzielona dwa razy: {duplikaty}")''',
     '    duplikaty = []'),

    ("trasy: powrót do naiwnego app.routes (pierwotny błąd)",
     '    trasy = zbierz(create_app().routes)',
     '''    trasy = [(r.path, tuple(sorted(r.methods or ())))
             for r in create_app().routes if getattr(r, "methods", None)]'''),

    ("trasy: usunięty próg PROG_TRAS",
     '''    if len(trasy) < PROG_TRAS:''',
     '''    if False:'''),

    ("dokumenty: kontrola zamieniona w atrapę",
     '    wzorzec = re.compile(r"docs/([A-Z0-9_]+\\.md)")',
     '    return\n    wzorzec = re.compile(r"docs/([A-Z0-9_]+\\.md)")'),

    ("routery: kontrola zamieniona w atrapę",
     ('    tresc = (BACKEND / "main.py").read_text(encoding="utf-8")\n'
      '    # Nazwa, pod którą router trafia do main.py, bywa aliasem'),
     ('    return\n    tresc = (BACKEND / "main.py").read_text(encoding="utf-8")\n'
      '    # Nazwa, pod którą router trafia do main.py, bywa aliasem')),

    ("testy frontendu: kontrola zamieniona w atrapę",
     '    paczka = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))',
     '    return\n    paczka = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))'),

    ("pliki poza gitem: kontrola zamieniona w atrapę",
     '    pliki = _pliki_zrodlowe()',
     '    return\n    pliki = _pliki_zrodlowe()'),

    ("pliki poza gitem: plik ignorowany zdegradowany do uwagi",
     '        w.blad("pliki", f"{sciezka} jest ignorowany',
     '        w.uwaga("pliki", f"{sciezka} jest ignorowany'),

    ("pliki poza gitem: usunięty bezpiecznik pustej listy",
     '    if not pliki:',
     '    if False:'),
]


def uruchom_testy() -> tuple[int, str]:
    wynik = subprocess.run(
        [sys.executable, "-m", "pytest", "apps/dzik-os/backend/tests/test_spojnosc.py",
         "-q", "--no-header", "-x", "--tb=no"],
        capture_output=True, text=True, check=False,
    )
    return wynik.returncode, wynik.stdout.strip().splitlines()[-1] if wynik.stdout else ""


print("=== stan wyjściowy (kontrola sprawna) ===")
kod, opis = uruchom_testy()
print(f"  testy: {opis}  [kod {kod}]")
if kod != 0:
    print("  PRZERWANE: testy nie przechodzą na sprawnej kontroli")
    raise SystemExit(1)

przezyly = []
for nazwa, szukaj, zamien in MUTACJE:
    shutil.copy(ORYGINAL, NARZEDZIE)
    tresc = NARZEDZIE.read_text(encoding="utf-8")
    if szukaj not in tresc:
        print(f"\n=== {nazwa} ===\n  NIE UDAŁO SIĘ WSTRZYKNĄĆ (wzorzec nie pasuje)")
        przezyly.append(nazwa + " (nie wstrzyknięto)")
        continue
    NARZEDZIE.write_text(tresc.replace(szukaj, zamien, 1), encoding="utf-8")
    kod, opis = uruchom_testy()
    print(f"\n=== {nazwa} ===")
    print(f"  testy: {opis}")
    if kod == 0:
        print("  >>> TESTY PRZESZŁY MIMO ZEPSUTEJ KONTROLI — luka w testach")
        przezyly.append(nazwa)
    else:
        print("  OK: testy wykryły zepsucie")

shutil.copy(ORYGINAL, NARZEDZIE)
kod, opis = uruchom_testy()
print(f"\n=== po przywróceniu oryginału ===\n  testy: {opis}  [kod {kod}]")
print("\nPODSUMOWANIE:")
if przezyly:
    print("  Mutacje, których testy NIE wykryły:")
    for m in przezyly:
        print(f"   - {m}")
else:
    print(f"  Wszystkie {len(MUTACJE)} mutacje wykryte.")

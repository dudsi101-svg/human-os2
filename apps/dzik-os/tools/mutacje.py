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
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

NARZEDZIE = Path("apps/dzik-os/tools/spojnosc.py")

# KOPIA ROBOCZA — dlaczego akurat tak, a nie prościej.
#
# Pierwsza wersja trzymała kopię pod stałą ścieżką /tmp/spojnosc.oryginal.py
# i tworzyła ją TYLKO gdy jeszcze nie istniała (`if not ORYGINAL.exists()`).
# 18.08.2026 zjadło to półtorej godziny pracy: plik przetrwał w /tmp
# z wcześniejszego uruchomienia, więc kolejny przebieg nie odświeżył kopii
# i „przywrócił oryginał” sprzed 90 minut — kasując świeżo dopisaną
# kontrolę. Po cichu, z komunikatem o powodzeniu.
#
# Narzędzie, którego zadaniem jest PSUĆ I PRZYWRACAĆ plik, musi mieć
# przywracanie pewne. Stąd trzy zmiany naraz:
#   1. katalog tymczasowy unikalny dla przebiegu — kopia z innego
#      uruchomienia nie ma jak się podłożyć,
#   2. kopia robiona ZAWSZE, bezwarunkowo,
#   3. po przywróceniu sprawdzany hash — rozbieżność przerywa z błędem
#      zamiast zameldować sukces.
_KATALOG = Path(tempfile.mkdtemp(prefix="dzik-mutacje-"))
ORYGINAL = _KATALOG / "spojnosc.oryginal.py"
shutil.copy(NARZEDZIE, ORYGINAL)
_HASH_ORYGINALU = hashlib.sha256(ORYGINAL.read_bytes()).hexdigest()


def przywroc() -> None:
    """Przywraca oryginał i SPRAWDZA, że naprawdę wrócił."""
    shutil.copy(ORYGINAL, NARZEDZIE)
    obecny = hashlib.sha256(NARZEDZIE.read_bytes()).hexdigest()
    if obecny != _HASH_ORYGINALU:
        raise SystemExit(
            f"PRZERWANE: przywrócenie {NARZEDZIE} nie powiodło się — "
            f"kopia leży w {ORYGINAL}, odtwórz ją ręcznie."
        )
# Kopia robocza ZAWSZE w świeżym katalogu tymczasowym. Wcześniej była to
# stała ścieżka w /tmp, tworzona tylko „gdy nie istnieje" — i to był realny
# błąd: uruchomienie po scaleniu cudzej zmiany przywracało kopię SPRZED
# tego scalenia i po cichu kasowało cudzą pracę (2026-08-18: 88 linii
# kontroli higieny gałęzi). Narzędzie mające chronić kod niszczyło go bez
# słowa. Świeży katalog na każde uruchomienie usuwa całą tę klasę błędu.
ORYGINAL = Path(tempfile.mkdtemp(prefix="mutacje-spojnosc-")) / "spojnosc.oryginal.py"
shutil.copy(NARZEDZIE, ORYGINAL)
ODCISK_STARTOWY = hashlib.sha256(NARZEDZIE.read_bytes()).hexdigest()

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

    ("konsultacje: kontrola zamieniona w atrapę",
     '    plik = DOCS / "KONSULTACJE.md"',
     '    return\n    plik = DOCS / "KONSULTACJE.md"'),

    ("konsultacje: otwarte pytanie przestaje być zgłaszane",
     '        if status != "OTWARTE":\n            continue',
     '        if status == "OTWARTE":\n            continue'),

    ("konsultacje: zły kształt nagłówka zdegradowany do uwagi",
     '            w.blad("konsultacje", f"wpis w linii {nr_linii + 1} ma zly ksztalt "',
     '            w.uwaga("konsultacje", f"wpis w linii {nr_linii + 1} ma zly ksztalt "'),

    ("konsultacje: usunięty bezpiecznik pustego dziennika",
     '    if not naglowki:',
     '    if False:'),

    ("konsultacje: data z przyszłości przestaje być błędem",
     '        if wiek < -0.05:',
     '        if False:'),

    ("przekazanie: nieaktualny dokument przestaje być błędem",
     '        w.blad("przekazanie",\n               f"STAN_PRZEKAZANIA.md nie wspomina',
     '        w.uwaga("przekazanie",\n               f"STAN_PRZEKAZANIA.md nie wspomina'),

    ("przekazanie: brak dokumentu przestaje być błędem",
     '        w.blad("przekazanie", "brak docs/STAN_PRZEKAZANIA.md',
     '        w.uwaga("przekazanie", "brak docs/STAN_PRZEKAZANIA.md'),

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
    przywroc()
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

przywroc()
shutil.copy(ORYGINAL, NARZEDZIE)
# Dowód, że przywrócono DOKŁADNIE to, co było — a nie coś podobnego.
odcisk_koncowy = hashlib.sha256(NARZEDZIE.read_bytes()).hexdigest()
if odcisk_koncowy != ODCISK_STARTOWY:
    print("\n!!! PLIK PO PRZYWRÓCENIU RÓŻNI SIĘ OD STANU SPRZED URUCHOMIENIA !!!")
    print(f"    przed: {ODCISK_STARTOWY[:16]}  po: {odcisk_koncowy[:16]}")
    print("    Natychmiast: git checkout apps/dzik-os/tools/spojnosc.py")
    raise SystemExit(2)
shutil.rmtree(ORYGINAL.parent, ignore_errors=True)
kod, opis = uruchom_testy()
print(f"\n=== po przywróceniu oryginału (suma kontrolna zgodna) ===\n  testy: {opis}  [kod {kod}]")
print("\nPODSUMOWANIE:")
if przezyly:
    print("  Mutacje, których testy NIE wykryły:")
    for m in przezyly:
        print(f"   - {m}")
else:
    print(f"  Wszystkie {len(MUTACJE)} mutacje wykryte.")

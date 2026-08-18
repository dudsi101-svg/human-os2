"""Kontrola spójności repozytorium Dzik OS — bramka przeciw kolizjom.

DLACZEGO TO ISTNIEJE. Rundy bywają rozwijane równolegle, w osobnych
kopiach repozytorium. Każda praca widzi kod sprzed swojego startu i NIE
WIE, co robią pozostałe. Skutki tego nie są teoretyczne — wszystkie
poniższe zdarzyły się naprawdę w sierpniu 2026:

* dwa razy przydzielony numer wersji w CHANGELOG-u (0.29.0),
* kolizja numerów migracji przy scalaniu dwóch gałęzi,
* trasa `/coach/exercises/import-schema` przesłonięta przez starszą
  `/coach/exercises/{item_id}` — kod poprawny, funkcja nieosiągalna,
* nowy plik testów pomocniczych frontendu nie dopisany do `test:helpers`,
  czyli test istniał i nigdy się nie uruchamiał.

Git widzi kolizje TEKSTU. Ta kontrola widzi kolizje ZNACZENIA — i mówi o
nich po polsku, z podaniem miejsca. Uruchamiana lokalnie i w CI:

    python apps/dzik-os/tools/spojnosc.py

Kod wyjścia 0 = czysto, 1 = znalezione problemy (wypisane na stdout).
Kontrola niczego nie naprawia — od tego jest człowiek albo agent, który
zna zamiar. Ma wyłącznie nie pozwolić, żeby kolizja przeszła niezauważona.
"""

from __future__ import annotations

import ast
import itertools
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
BACKEND = APP / "backend" / "dzik_os"
FRONTEND = APP / "frontend"
DOCS = APP / "docs"

#: Najmniejsza sensowna liczba tras. Gdy kontrola zobaczy mniej, znaczy to,
#: że zmienił się kształt routingu FastAPI i przestała cokolwiek sprawdzać
#: — to błąd sam w sobie, nie powód do przejścia na zielono.
PROG_TRAS = 50


@dataclass
class Wynik:
    """Zebrane problemy. `bledy` blokują, `uwagi` tylko informują."""

    bledy: list[str] = field(default_factory=list)
    uwagi: list[str] = field(default_factory=list)

    def blad(self, kontrola: str, opis: str) -> None:
        self.bledy.append(f"[{kontrola}] {opis}")

    def uwaga(self, kontrola: str, opis: str) -> None:
        self.uwagi.append(f"[{kontrola}] {opis}")


# --- 1. Migracje -------------------------------------------------------

def sprawdz_migracje(w: Wynik) -> None:
    """Numery migracji: unikalne i rosnące, każda z opisem.

    Dwie gałęzie, które niezależnie wzięły ten sam numer, scalają się
    tekstowo bez konfliktu i jedna migracja po cichu nigdy się nie
    wykona — na produkcji zobaczysz to jako brakującą kolumnę."""
    drzewo = ast.parse((BACKEND / "db.py").read_text(encoding="utf-8"))
    numery: list[int] = []
    for wezel in ast.walk(drzewo):
        if not (isinstance(wezel, ast.AnnAssign) and getattr(wezel.target, "id", "") == "MIGRATIONS"):
            continue
        for element in getattr(wezel.value, "elts", []):
            if not isinstance(element, ast.Tuple) or len(element.elts) != 3:
                w.blad("migracje", "wpis MIGRATIONS nie jest krotką (numer, opis, kroki)")
                continue
            numer = element.elts[0]
            if not isinstance(numer, ast.Constant) or not isinstance(numer.value, int):
                w.blad("migracje", "numer migracji nie jest literałem całkowitym")
                continue
            numery.append(numer.value)
    if not numery:
        w.blad("migracje", "nie znaleziono listy MIGRATIONS w db.py")
        return
    duplikaty = sorted({n for n in numery if numery.count(n) > 1})
    if duplikaty:
        w.blad("migracje", f"numery użyte więcej niż raz: {duplikaty} — jedna z nich "
                           "nigdy się nie wykona")
    if numery != sorted(numery):
        w.blad("migracje", f"numery nie są rosnące: {numery}")
    if numery[0] != 1:
        w.blad("migracje", f"numeracja zaczyna się od {numery[0]}, nie od 1")
    # Luki są dozwolone (numer bywa zarezerwowany przez równoległą rundę i
    # nieużyty), ale muszą być WIDOCZNE — inaczej ktoś weźmie wolny numer
    # pod nową migrację i zderzy się ze starą, niescaloną gałęzią.
    luki = [i for i in range(numery[0], numery[-1]) if i not in numery]
    if luki:
        w.uwaga("migracje", f"wolne numery w środku numeracji: {luki} — NIE bierz ich "
                            "pod nową migrację, prowadź numerację od największego")


# --- 2. CHANGELOG ------------------------------------------------------

def _wersja(tekst: str) -> tuple[int, ...]:
    return tuple(int(x) for x in tekst.split("."))


def sprawdz_changelog(w: Wynik) -> None:
    """Wersje w CHANGELOG-u: unikalne i malejące od góry.

    Dwie równoległe rundy potrafią wziąć ten sam numer wersji — wtedy
    historia zmian przestaje być historią."""
    plik = DOCS / "CHANGELOG.md"
    wersje = re.findall(r"^## (\d+\.\d+\.\d+)", plik.read_text(encoding="utf-8"), re.MULTILINE)
    if not wersje:
        w.blad("changelog", "brak nagłówków wersji w docs/CHANGELOG.md")
        return
    duplikaty = sorted({v for v in wersje if wersje.count(v) > 1})
    if duplikaty:
        w.blad("changelog", f"wersja przydzielona dwa razy: {duplikaty}")
    liczby = [_wersja(v) for v in wersje]
    if liczby != sorted(liczby, reverse=True):
        zle = [f"{a} przed {b}" for a, b in itertools.pairwise(wersje)
               if _wersja(a) < _wersja(b)]
        w.blad("changelog", "wersje nie idą malejąco od góry: " + ", ".join(zle))


# --- 3. Przesłonięte trasy API ----------------------------------------

def sprawdz_trasy(w: Wynik) -> None:
    """Trasa statyczna zarejestrowana PO parametryzowanej, która ją łapie.

    FastAPI dopasowuje trasy w kolejności rejestracji, więc
    `/coach/exercises/{item_id}` zdefiniowana wcześniej przechwyci
    `/coach/exercises/import-schema`. Kod jest poprawny, testy modułu
    przechodzą, a funkcji po prostu nie ma. Zdarzyło się (0.32.0)."""
    try:
        sys.path.insert(0, str(APP / "backend"))
        from dzik_os.main import create_app
    except Exception as exc:  # noqa: BLE001 - aplikacja się nie składa = błąd sam w sobie
        w.blad("trasy", f"nie udało się zbudować aplikacji: {exc}")
        return

    def zbierz(routes) -> list[tuple[str, tuple[str, ...]]]:
        """Trasy w kolejności rejestracji, także te w dołączonych routerach.

        UWAGA na kształt: ta wersja FastAPI trzyma dołączone routery jako
        obiekty `_IncludedRouter` i NIE spłaszcza ich do `app.routes`.
        Naiwne `app.routes` widzi wtedy garść tras i kontrola przechodzi
        na pusto — złapane przy próbie z wstrzykniętym błędem, patrz
        `tests/test_spojnosc.py`."""
        zebrane: list[tuple[str, tuple[str, ...]]] = []
        for r in routes:
            wewnetrzny = getattr(r, "original_router", None) or getattr(r, "router", None)
            if wewnetrzny is not None:
                zebrane.extend(zbierz(wewnetrzny.routes))
                continue
            if getattr(r, "methods", None):
                zebrane.append((r.path, tuple(sorted(r.methods))))
        return zebrane

    trasy = zbierz(create_app().routes)
    if len(trasy) < PROG_TRAS:
        w.blad("trasy", f"kontrola zobaczyła tylko {len(trasy)} tras — to za mało "
                        "jak na tę aplikację; zmienił się kształt routingu FastAPI "
                        "i kontrola przestała cokolwiek sprawdzać")
        return
    for pozycja, (sciezka, metody) in enumerate(trasy):
        if "{" in sciezka:
            continue
        wzorzec = [s for s in sciezka.split("/") if s]
        for wczesniejsza, metody_w in trasy[:pozycja]:
            if "{" not in wczesniejsza:
                continue
            czesci = [s for s in wczesniejsza.split("/") if s]
            if len(czesci) != len(wzorzec):
                continue
            if not set(metody) & set(metody_w):
                continue
            if all(b.startswith("{") or a == b for a, b in zip(wzorzec, czesci)):
                w.blad(
                    "trasy",
                    f"{sciezka} ({'/'.join(metody)}) jest przesłonięta przez "
                    f"wcześniejszą {wczesniejsza} — przenieś ją WYŻEJ w pliku routera",
                )


# --- 4. Routery podpięte do aplikacji ---------------------------------

def sprawdz_routery(w: Wynik) -> None:
    """Każdy moduł w `routers/` musi być zarejestrowany w main.py.

    Router napisany i niepodpięty to funkcja, która przechodzi testy
    modułu i nie istnieje w działającej aplikacji."""
    tresc = (BACKEND / "main.py").read_text(encoding="utf-8")
    # Nazwa, pod którą router trafia do main.py, bywa aliasem
    # (`from .routers import notifications as notifications_router`) —
    # sprawdzamy realnie użytą nazwę, a nie nazwę pliku.
    aliasy: dict[str, str] = {}
    for wezel in ast.walk(ast.parse(tresc)):
        if isinstance(wezel, ast.ImportFrom) and (wezel.module or "").endswith("routers"):
            for nazwa in wezel.names:
                aliasy[nazwa.name] = nazwa.asname or nazwa.name
    for plik in sorted((BACKEND / "routers").glob("*.py")):
        if plik.stem.startswith("_"):
            continue
        uzywana = aliasy.get(plik.stem)
        if uzywana is None:
            w.blad("routery", f"routers/{plik.stem}.py nie jest w ogóle importowany w main.py")
        elif f"{uzywana}.router" not in tresc:
            w.blad("routery", f"routers/{plik.stem}.py jest importowany, ale nie podpięty "
                              "przez include_router w main.py")


# --- 5. Testy pomocnicze frontendu ------------------------------------

def sprawdz_testy_frontendu(w: Wynik) -> None:
    """Każdy `scripts/test-*.mjs` musi być w `test:helpers`.

    Test, którego nikt nie uruchamia, jest gorszy niż jego brak: daje
    poczucie pokrycia, którego nie ma."""
    paczka = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    polecenie = paczka.get("scripts", {}).get("test:helpers", "")
    for plik in sorted((FRONTEND / "scripts").glob("test-*.mjs")):
        if f"scripts/{plik.name}" not in polecenie:
            w.blad("testy-frontendu",
                   f"scripts/{plik.name} nie jest wymieniony w test:helpers — "
                   "ten test nigdy się nie uruchamia")
    for wymieniony in re.findall(r"scripts/[\w.-]+\.mjs", polecenie):
        if not (FRONTEND / wymieniony).exists():
            w.blad("testy-frontendu", f"test:helpers wskazuje nieistniejący {wymieniony}")


# --- 6. Odnośniki do dokumentów ---------------------------------------

def sprawdz_dokumenty(w: Wynik) -> None:
    """Odnośniki `docs/COŚ.md` w kodzie i dokumentacji muszą istnieć.

    Rundy przenoszą i przemianowują dokumenty; martwy odnośnik w komentarzu
    kieruje kolejną osobę w pustkę."""
    wzorzec = re.compile(r"docs/([A-Z0-9_]+\.md)")
    zrodla = [*BACKEND.rglob("*.py"), *DOCS.glob("*.md"), APP / "README.md"]
    brakujace: dict[str, set[str]] = {}
    for plik in zrodla:
        try:
            tresc = plik.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for nazwa in set(wzorzec.findall(tresc)):
            if not (DOCS / nazwa).exists():
                brakujace.setdefault(nazwa, set()).add(plik.name)
    for nazwa, gdzie in sorted(brakujace.items()):
        w.uwaga("dokumenty", f"docs/{nazwa} nie istnieje, a wskazują na niego: "
                             + ", ".join(sorted(gdzie)))


# --- 7. Higiena gałęzi -------------------------------------------------

#: Progi wyznaczone z faktów, nie z przeczucia. 18.08.2026 rundy scalane
#: w kilka–kilkadziesiąt minut nie wywołały ANI JEDNEGO konfliktu, mimo że
#: równoległość trwała cały czas. Gałąź, która przeżyła 6,5 godziny przy
#: takcie main około 30 minut, wymagała ośmiu scaleń nadążających i zdążyła
#: wprowadzić regres (trasa przesłonięta po scaleniu).
PROG_COMMITOW_MAIN = 5      # ile commitów przybyło na main od odgałęzienia
PROG_GODZIN = 3.0           # wiek gałęzi liczony od punktu odgałęzienia
PROG_SCALEN = 2             # ile razy trzeba było nadganiać main


def _git(*args: str) -> str | None:
    """Wynik polecenia git albo None, gdy się nie powiodło."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", *args], cwd=APP, capture_output=True, text=True,
            timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def sprawdz_galaz(w: Wynik) -> None:
    """Objawy gałęzi, która żyje za długo jak na tempo main.

    To jedyna kontrola, która nie patrzy na kod, tylko na SPOSÓB PRACY —
    bo właśnie sposób pracy, a nie treść zmian, wygenerował dziś większość
    kolizji. Lista zadań nigdy nie była groźna; groźne było zbieranie ich
    wszystkich na jednej, długo żyjącej gałęzi.

    Sygnały są UWAGAMI, nigdy błędami: długa gałąź bywa uzasadniona, a
    zatrzymanie builda z powodu upływu czasu byłoby karą za zegar. Rzecz
    w tym, żeby ryzyko było widoczne ZANIM zamieni się w konflikt — dziś
    zobaczyliśmy je dopiero przy ósmym scaleniu.
    """
    baza = _git("merge-base", "HEAD", "origin/main")
    if not baza:
        return  # brak origin/main (świeży klon, praca offline) — nie ma o czym mówić

    glowa = _git("rev-parse", "HEAD")
    czolo_main = _git("rev-parse", "origin/main")
    if glowa == czolo_main:
        return  # jesteśmy na main — pojęcie „wiek gałęzi" nie ma zastosowania

    przed = _git("rev-list", "--count", f"{baza}..origin/main")
    moje = _git("rev-list", "--count", f"{baza}..HEAD")
    if przed is None or moje is None:
        return
    przed_n, moje_n = int(przed), int(moje)
    if moje_n == 0:
        return  # gałąź bez własnych commitów

    if przed_n > PROG_COMMITOW_MAIN:
        w.uwaga(
            "gałąź",
            f"na main przybyło {przed_n} commitów od odgałęzienia "
            f"(próg {PROG_COMMITOW_MAIN}) — im dłużej, tym pewniejszy konflikt. "
            "Rozważ domknięcie tego, co gotowe, osobnym PR-em.",
        )

    stempel = _git("log", "-1", "--format=%ct", baza)
    if stempel:
        import time

        godziny = (time.time() - int(stempel)) / 3600
        if godziny > PROG_GODZIN:
            w.uwaga(
                "gałąź",
                f"gałąź odgałęziła się {godziny:.1f} h temu przy {moje_n} własnych "
                f"commitach (próg {PROG_GODZIN} h) — rundy scalane na bieżąco "
                "nie generowały kolizji, długie generowały.",
            )

    scalenia = _git("rev-list", "--count", "--merges", f"{baza}..HEAD")
    if scalenia and int(scalenia) > PROG_SCALEN:
        w.uwaga(
            "gałąź",
            f"{scalenia} scaleń nadążających za main w tej gałęzi "
            f"(próg {PROG_SCALEN}) — każde kolejne to czas oddany na nadganianie, "
            "nie na pracę.",
        )


# --- 8. Pliki poza gitem -----------------------------------------------

#: Rozszerzenia, których plik NALEŻY do repozytorium. Celowo wąska lista —
#: `.env`, klucze, dane i archiwa mają prawo być poza gitem i nie mogą tu
#: trafić przez przypadek.
ROZSZERZENIA_ZRODEL = (".py", ".ts", ".tsx", ".css", ".mjs", ".sh", ".md", ".sql")

#: Katalogi wytwarzane przez narzędzia — ich zawartość ma być ignorowana.
KATALOGI_WYTWORCZE = (
    "node_modules", "dist", "build", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov",
    "test-results", "playwright-report", "blob-report", ".git",
)


def _pliki_zrodlowe() -> list[Path]:
    out = []
    for sciezka in APP.rglob("*"):
        if not sciezka.is_file():
            continue
        if sciezka.suffix not in ROZSZERZENIA_ZRODEL:
            continue
        if any(czesc in KATALOGI_WYTWORCZE for czesc in sciezka.parts):
            continue
        out.append(sciezka)
    return sorted(out)


def sprawdz_pliki_poza_gitem(w: Wynik) -> None:
    """Plik źródłowy, który leży na dysku, ale nie jest w repozytorium.

    Dwa różne sposoby, na które praca po cichu znika:

    * **ignorowany przez `.gitignore`** — plik nigdy nie da się dodać bez
      `-f`, `git status` go nie pokaże, a `git add -A` przejdzie obok. To
      BŁĄD: taki plik jest niewidzialny na stałe, także dla przeglądu.
    * **nieśledzony** — plik jest widoczny w `git status`, ale nikt go nie
      dodał. Zniknie przy przełączeniu gałęzi, `git clean` albo wraz
      z kontenerem. To UWAGA, bo w trakcie pracy to stan normalny.

    Kontrola pyta git o KAŻDY plik źródłowy jednym wywołaniem, zamiast
    czytać `.gitignore` samodzielnie — reguły ignorowania składają się
    z kilku plików i wzorców z wykluczeniami (`!data/.gitkeep`), a własny
    parser tych reguł byłby kolejną rzeczą, która może zgnić po cichu.
    """
    pliki = _pliki_zrodlowe()
    if not pliki:
        w.blad("pliki", "nie znaleziono żadnego pliku źródłowego — "
                        "kontrola przestała cokolwiek widzieć")
        return

    import subprocess

    wzgledne = [str(p.relative_to(APP)) for p in pliki]
    wejscie = "\n".join(wzgledne)

    def _git_lista(*args: str) -> set[str] | None:
        try:
            out = subprocess.run(
                ["git", *args], cwd=APP, input=wejscie, capture_output=True,
                text=True, timeout=30, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        # check-ignore: 0 = coś pasuje, 1 = nic nie pasuje (oba poprawne)
        if out.returncode > 1:
            return None
        return {linia for linia in out.stdout.splitlines() if linia}

    ignorowane = _git_lista("check-ignore", "--stdin")
    if ignorowane is None:
        return  # brak gita (np. archiwum źródeł) — nie ma czego sprawdzać

    for sciezka in sorted(ignorowane):
        w.blad("pliki", f"{sciezka} jest ignorowany przez .gitignore, a wygląda "
                        "na plik źródłowy — nigdy nie trafi do repozytorium")

    sledzone = _git_lista("ls-files", "--cached", "-z", "--", *wzgledne)
    if sledzone is None:
        return
    # `-z` daje jeden ciąg rozdzielony \0 — rozbijamy ręcznie
    sledzone = {n for wiersz in sledzone for n in wiersz.split("\0") if n}
    brakujace = [s for s in wzgledne if s not in sledzone and s not in ignorowane]
    for sciezka in sorted(brakujace):
        w.uwaga("pliki", f"{sciezka} nie jest dodany do repozytorium — "
                         "zniknie przy zmianie gałęzi lub wraz z kontenerem")



# --- 9. Konsultacje miedzy sesjami -------------------------------------

#: Ile godzin otwarty wpis BLOKUJACY moze czekac, zanim bramka o nim krzyknie.
PROG_KONSULTACJI_H = 4.0

_NAGLOWEK_KONSULTACJI = re.compile(
    r"^### (K-\d{3}) \u00b7 (\d{4}-\d{2}-\d{2} \d{2}:\d{2})Z \u00b7 "
    r"od: (\w+) \u00b7 do: (\w+) \u00b7 STATUS: (OTWARTE|ODPOWIEDZIANE|ZAMKNIETE)$"
)
_STRONY = {"bramki", "produktowa", "wlasciciel"}


def sprawdz_konsultacje(w: Wynik) -> None:
    """Otwarte pytania miedzy sesjami — zeby nikt ich nie przeoczyl.

    POWOD ISTNIENIA. 18.08.2026 sesja produktowa zadala cztery pytania
    w swoim pliku planu. Odpowiedz padla wylacznie dlatego, ze druga strona
    PRZYPADKIEM tam zajrzala — nic o nich nie powiadamialo. Cztery dokumenty
    koordynacyjne istnialy i zaden nie mial wlasciwosci upominania sie.

    Ta kontrola nie ocenia tresci. Pilnuje, zeby otwarty wpis byl WIDOCZNY
    przy kazdym uruchomieniu bramki — lokalnie i w CI.

    BLAD (blokuje) wylacznie wtedy, gdy zepsuty jest sam MECHANIZM: zly
    ksztalt naglowka, powtorzony numer, nieznana strona, brak pola
    `Blokuje`, pusty dziennik. Wpis, ktorego kontrola nie umie odczytac,
    jest gorszy niz jego brak — ta sama zasada co PROG_TRAS.

    UWAGA (nie blokuje) dla samych otwartych pytan. Otwarte pytanie to stan
    normalny; zatrzymywanie builda z tego powodu nauczyloby wszystkich
    obchodzic bramke. Wpisy `Blokuje: tak` starsze niz PROG_KONSULTACJI_H
    dostaja glosniejsza uwage — tam ktos naprawde stoi.
    """
    plik = DOCS / "KONSULTACJE.md"
    if not plik.exists():
        return  # dziennik nieobowiazkowy — jego brak to nie awaria

    linie = plik.read_text(encoding="utf-8").splitlines()
    # Naglowki WEWNATRZ bloku kodu to przyklady z instrukcji, nie wpisy.
    # Bez tego kontrola zglaszala blad na wlasnej dokumentacji — zlapane
    # przy pierwszym uruchomieniu, patrz test_pomija_przyklady_w_bloku_kodu.
    naglowki: list[tuple[int, str]] = []
    w_bloku = False
    for i, linia in enumerate(linie):
        if linia.startswith("```"):
            w_bloku = not w_bloku
            continue
        if not w_bloku and linia.startswith("### "):
            naglowki.append((i, linia))

    if not naglowki:
        w.blad("konsultacje", "KONSULTACJE.md nie zawiera ani jednego wpisu — "
                              "kontrola przestala cokolwiek widziec")
        return

    import time
    from datetime import datetime

    numery: set[str] = set()
    otwarte: list[tuple[str, str, float, bool]] = []
    for nr_linii, linia in naglowki:
        dopasowanie = _NAGLOWEK_KONSULTACJI.match(linia)
        if dopasowanie is None:
            w.blad("konsultacje", f"wpis w linii {nr_linii + 1} ma zly ksztalt "
                                  f"naglowka — bramka nie umie go odczytac: {linia[:70]!r}")
            continue
        numer, stempel, od, do, status = dopasowanie.groups()
        if numer in numery:
            w.blad("konsultacje", f"numer {numer} uzyty dwa razy")
        numery.add(numer)
        for strona, etykieta in ((od, "od"), (do, "do")):
            if strona not in _STRONY:
                w.blad("konsultacje", f"{numer}: nieznana strona w polu "
                                      f"`{etykieta}: {strona}` "
                                      f"(dozwolone: {', '.join(sorted(_STRONY))})")
        koniec = next((i for i, _ in naglowki if i > nr_linii), len(linie))
        cialo = "\n".join(linie[nr_linii:koniec])
        blokuje_dop = re.search(r"^\*\*Blokuje:\*\* (tak|nie)$", cialo, re.MULTILINE)
        if blokuje_dop is None:
            w.blad("konsultacje", f"{numer}: brak pola `**Blokuje:** tak|nie`")
            continue
        if status != "OTWARTE":
            continue
        try:
            kiedy = datetime.strptime(stempel + "+0000", "%Y-%m-%d %H:%M%z")
        except ValueError:
            w.blad("konsultacje", f"{numer}: nieczytelna data {stempel!r}")
            continue
        wiek = (time.time() - kiedy.timestamp()) / 3600
        otwarte.append((numer, do, wiek, blokuje_dop.group(1) == "tak"))

    for numer, do, wiek, blokuje in sorted(otwarte, key=lambda x: -x[2]):
        if blokuje and wiek > PROG_KONSULTACJI_H:
            w.uwaga("konsultacje",
                    f"{numer} BLOKUJE prace i czeka {wiek:.1f} h "
                    f"(prog {PROG_KONSULTACJI_H} h) — adresat: {do}. "
                    "Ktos po drugiej stronie stoi.")
        else:
            w.uwaga("konsultacje",
                    f"{numer} otwarte od {wiek:.1f} h, adresat: {do}"
                    + (" [BLOKUJE]" if blokuje else ""))


KONTROLE = (
    ("migracje", sprawdz_migracje),
    ("changelog", sprawdz_changelog),
    ("trasy API", sprawdz_trasy),
    ("routery", sprawdz_routery),
    ("testy frontendu", sprawdz_testy_frontendu),
    ("dokumenty", sprawdz_dokumenty),
    ("higiena gałęzi", sprawdz_galaz),
    ("pliki poza gitem", sprawdz_pliki_poza_gitem),
    ("konsultacje", sprawdz_konsultacje),
)


def main() -> int:
    w = Wynik()
    for nazwa, kontrola in KONTROLE:
        try:
            kontrola(w)
        except Exception as exc:  # noqa: BLE001 - awaria kontroli nie udaje, że czysto
            w.blad(nazwa, f"kontrola nie wykonała się: {exc!r}")

    for uwaga in w.uwagi:
        print(f"UWAGA  {uwaga}")
    for blad in w.bledy:
        print(f"BŁĄD   {blad}")
    if w.bledy:
        print(f"\nSpójność: {len(w.bledy)} problemów do naprawienia.")
        return 1
    print(f"Spójność: czysto ({len(KONTROLE)} kontroli"
          + (f", {len(w.uwagi)} uwag" if w.uwagi else "") + ").")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

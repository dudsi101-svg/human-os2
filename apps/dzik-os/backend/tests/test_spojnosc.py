"""Kontrola spójności repozytorium (`tools/spojnosc.py`).

Kontrola, która niczego nie wykrywa, jest gorsza niż jej brak: daje
spokój, na który nie ma pokrycia. Dlatego testy tutaj NIE sprawdzają, że
repozytorium jest czyste (to robi CI) — sprawdzają, że kontrola **umie
zapalić się na każdym z czterech błędów, które naprawdę się zdarzyły**.

Wzorzec: wstrzykujemy błąd do kopii pliku, wołamy pojedynczą kontrolę i
patrzymy, czy zgłasza. To jedyny sposób, żeby kontrola nie zgniła w ciszy.
"""

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2]
NARZEDZIE = APP / "tools" / "spojnosc.py"


def zaladuj(root: Path):
    """Ładuje `spojnosc.py` z podmienionymi ścieżkami na kopię repozytorium."""
    nazwa = f"spojnosc_{root.name}"
    spec = importlib.util.spec_from_file_location(nazwa, NARZEDZIE)
    modul = importlib.util.module_from_spec(spec)
    # Rejestracja w sys.modules PRZED wykonaniem: @dataclass sięga po
    # `sys.modules[cls.__module__]`, żeby rozwiązać domyślne fabryki.
    sys.modules[nazwa] = modul
    spec.loader.exec_module(modul)
    modul.APP = root
    modul.BACKEND = root / "backend" / "dzik_os"
    modul.FRONTEND = root / "frontend"
    modul.DOCS = root / "docs"
    return modul


@pytest.fixture()
def kopia(tmp_path) -> Path:
    """Minimalna kopia repozytorium: same pliki, których dotyka kontrola."""
    root = tmp_path / "app"
    (root / "backend" / "dzik_os" / "routers").mkdir(parents=True)
    (root / "frontend" / "scripts").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    for wzgledny in ("backend/dzik_os/db.py", "backend/dzik_os/main.py",
                     "docs/CHANGELOG.md", "frontend/package.json"):
        shutil.copy(APP / wzgledny, root / wzgledny)
    for plik in (APP / "backend" / "dzik_os" / "routers").glob("*.py"):
        shutil.copy(plik, root / "backend" / "dzik_os" / "routers" / plik.name)
    for plik in (APP / "frontend" / "scripts").glob("test-*.mjs"):
        shutil.copy(plik, root / "frontend" / "scripts" / plik.name)
    return root


def bledy(modul, kontrola) -> list[str]:
    wynik = modul.Wynik()
    kontrola(wynik)
    return wynik.bledy


# --- Cztery błędy, które naprawdę się zdarzyły -------------------------


def test_wykrywa_powtorzony_numer_migracji(kopia):
    """Sierpień 2026: dwie gałęzie wzięły ten sam numer migracji. Scalenie
    tekstowe przeszło bez konfliktu, jedna migracja nigdy by się nie
    wykonała — na produkcji objawiłoby się to brakującą kolumną."""
    modul = zaladuj(kopia)
    plik = kopia / "backend" / "dzik_os" / "db.py"
    assert bledy(modul, modul.sprawdz_migracje) == []
    plik.write_text(
        plik.read_text(encoding="utf-8").replace(
            '    (25, "punkty przywracania', '    (24, "punkty przywracania', 1),
        encoding="utf-8",
    )
    znalezione = bledy(modul, modul.sprawdz_migracje)
    assert any("więcej niż raz" in b and "24" in b for b in znalezione), znalezione


def test_wykrywa_wersje_changelogu_przydzielona_dwa_razy(kopia):
    """Sierpień 2026: numer 0.29.0 trafił do dwóch równoległych rund."""
    modul = zaladuj(kopia)
    plik = kopia / "docs" / "CHANGELOG.md"
    assert bledy(modul, modul.sprawdz_changelog) == []
    tresc = plik.read_text(encoding="utf-8")
    pierwsza = tresc.split("\n## ")[1].split(" ")[0]
    druga = tresc.split("\n## ")[2].split(" ")[0]
    plik.write_text(tresc.replace(f"## {pierwsza} ", f"## {druga} ", 1), encoding="utf-8")
    znalezione = bledy(modul, modul.sprawdz_changelog)
    assert any("dwa razy" in b for b in znalezione), znalezione


def test_wykrywa_test_frontendu_ktory_nigdy_sie_nie_uruchamia(kopia):
    """Plik `scripts/test-*.mjs` poza `test:helpers` to test-widmo."""
    modul = zaladuj(kopia)
    plik = kopia / "frontend" / "package.json"
    assert bledy(modul, modul.sprawdz_testy_frontendu) == []
    dane = json.loads(plik.read_text(encoding="utf-8"))
    dane["scripts"]["test:helpers"] = dane["scripts"]["test:helpers"].replace(
        " scripts/test-sheet-import.mjs", ""
    )
    plik.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    znalezione = bledy(modul, modul.sprawdz_testy_frontendu)
    assert any("nigdy się nie uruchamia" in b for b in znalezione), znalezione


def test_wykrywa_router_bez_include_router(kopia):
    """Router napisany i niepodpięty przechodzi testy modułu, a w
    działającej aplikacji nie istnieje."""
    modul = zaladuj(kopia)
    plik = kopia / "backend" / "dzik_os" / "main.py"
    assert bledy(modul, modul.sprawdz_routery) == []
    plik.write_text(
        plik.read_text(encoding="utf-8").replace(
            "ocr.router, assistant.router, imports.router,",
            "ocr.router, assistant.router,", 1),
        encoding="utf-8",
    )
    znalezione = bledy(modul, modul.sprawdz_routery)
    assert any("imports" in b and "nie podpięty" in b for b in znalezione), znalezione


# --- Kontrola tras: najważniejsza i najłatwiejsza do zepsucia ----------


def test_wykrywa_trase_przeslonieta_przez_parametr(monkeypatch):
    """Prawdziwy błąd z 0.32.0: `/coach/exercises/import-schema` stała
    PO `/coach/exercises/{item_id}` i była nieosiągalna.

    Sprawdzamy regułę na sztucznej aplikacji o tym samym kształcie —
    zamiast psuć prawdziwy router — więc test mówi o regule, a nie o
    bieżącym stanie repozytorium."""
    from fastapi import APIRouter, FastAPI

    # Przez importlib, a nie `import dzik_os.main`: `ruff` klasyfikuje
    # `dzik_os` raz jako moduł pierwszej, raz trzeciej strony — zależnie od
    # katalogu, z którego jest uruchamiany — i wymaga wtedy sprzecznego
    # porządku importów lokalnie i w CI. Brak instrukcji importu = brak
    # sporu o kolejność.
    main_modul = importlib.import_module("dzik_os.main")

    modul = zaladuj(APP)
    monkeypatch.setattr(modul, "PROG_TRAS", 0, raising=False)

    def zbuduj(kolejnosc_odwrotna: bool):
        router = APIRouter(prefix="/api")
        def po_id(item_id: str):  # pragma: no cover - trasa testowa
            return {}
        def schemat():  # pragma: no cover - trasa testowa
            return {}
        if kolejnosc_odwrotna:
            router.get("/coach/rzeczy/{item_id}")(po_id)
            router.get("/coach/rzeczy/schemat")(schemat)
        else:
            router.get("/coach/rzeczy/schemat")(schemat)
            router.get("/coach/rzeczy/{item_id}")(po_id)
        aplikacja = FastAPI()
        aplikacja.include_router(router)
        return aplikacja

    # Zła kolejność → kontrola wskazuje przesłoniętą trasę.
    monkeypatch.setattr(main_modul, "create_app", lambda: zbuduj(True))
    wynik = modul.Wynik()
    modul.sprawdz_trasy(wynik)
    assert any("schemat" in b and "przesłonięta" in b for b in wynik.bledy), wynik.bledy

    # Dobra kolejność → cisza. Kontrola, która krzyczy zawsze, jest bezużyteczna.
    monkeypatch.setattr(main_modul, "create_app", lambda: zbuduj(False))
    wynik = modul.Wynik()
    modul.sprawdz_trasy(wynik)
    assert wynik.bledy == [], wynik.bledy


def test_wykrywa_martwy_odnosnik_do_dokumentu(kopia):
    """Odnośnik `docs/COŚ.md` do nieistniejącego pliku — uwaga, nie błąd,
    ale musi być zgłoszona. Bez tego testu kontrola mogła zostać atrapą i
    nikt by nie zauważył (wyszło przy przeglądzie mutacyjnym)."""
    modul = zaladuj(kopia)
    # Kopia zawiera tylko część dokumentów, więc odnośników brakujących
    # jest tam sporo z natury rzeczy — porównujemy PRZYROST, nie stan.
    (kopia / "docs" / "PRZYKLAD.md").write_text("bez odnośników\n", encoding="utf-8")
    przed = modul.Wynik()
    modul.sprawdz_dokumenty(przed)
    assert not any("NIE_MA_TAKIEGO" in u for u in przed.uwagi)

    (kopia / "docs" / "PRZYKLAD.md").write_text(
        "Patrz docs/NIE_MA_TAKIEGO.md po szczegóły.\n", encoding="utf-8")
    po = modul.Wynik()
    modul.sprawdz_dokumenty(po)
    assert any("NIE_MA_TAKIEGO.md" in u for u in po.uwagi), po.uwagi
    assert len(po.uwagi) == len(przed.uwagi) + 1


def test_prog_tras_zapala_sie_gdy_kontrola_widzi_za_malo(monkeypatch):
    """Zabezpieczenie przed cichą śmiercią kontroli — musi mieć własny test.

    `PROG_TRAS` istnieje po to, żeby kontrola tras nie przeszła na zielono,
    gdy z powodu zmiany w FastAPI przestanie widzieć trasy. Testy
    wstrzykujące błąd tego NIE pilnowały: usunięcie progu nie wywracało
    żadnego z nich (wyszło przy przeglądzie mutacyjnym 2026-08-18). Bez
    tego testu zabezpieczenie mogło zniknąć niezauważone."""
    from fastapi import FastAPI

    modul = zaladuj(APP)
    main_modul = importlib.import_module("dzik_os.main")
    # Aplikacja z jedną trasą udaje sytuację „kontrola oślepła".
    # Funkcja nazwana, nie `lambda`/`dict`: FastAPI czyta sygnaturę
    # uchwytu, a wbudowany `dict` sygnatury nie ma.
    def uchwyt() -> dict:  # pragma: no cover - trasa testowa
        return {}

    pusta = FastAPI()
    pusta.get("/api/nic")(uchwyt)
    monkeypatch.setattr(main_modul, "create_app", lambda: pusta)

    wynik = modul.Wynik()
    modul.sprawdz_trasy(wynik)
    assert any("za mało" in b for b in wynik.bledy), (
        "kontrola tras zobaczyła garść tras i nie zaprotestowała — "
        f"próg PROG_TRAS nie działa: {wynik.bledy}"
    )


def test_kontrola_tras_nie_moze_przejsc_na_pusto():
    """Zabezpieczenie przed cichą śmiercią kontroli.

    Ta wersja FastAPI trzyma dołączone routery jako `_IncludedRouter` i
    nie spłaszcza ich do `app.routes`. Naiwna implementacja widziała 35
    tras zamiast ~200 i przechodziła zawsze — złapane dopiero próbą z
    wstrzykniętym błędem. Próg pilnuje, żeby to się nie powtórzyło."""
    create_app = importlib.import_module("dzik_os.main").create_app

    def zbierz(routes):
        zebrane = []
        for r in routes:
            wewnetrzny = getattr(r, "original_router", None) or getattr(r, "router", None)
            if wewnetrzny is not None:
                zebrane.extend(zbierz(wewnetrzny.routes))
            elif getattr(r, "methods", None):
                zebrane.append(r.path)
        return zebrane

    assert len(zbierz(create_app().routes)) > 50


def test_repozytorium_jest_spojne():
    """Stan bieżący — jeśli ten test padnie, kontrola mówi dlaczego."""
    modul = zaladuj(APP)
    wynik = modul.Wynik()
    for _, kontrola in modul.KONTROLE:
        kontrola(wynik)
    assert wynik.bledy == [], "\n".join(wynik.bledy)


# --- 7. Higiena gałęzi -------------------------------------------------
#
# Ta kontrola nie czyta plików, tylko pyta gita — więc zamiast kopii
# repozytorium podstawiamy odpowiedzi `_git`. Dzięki temu test opisuje
# REGUŁĘ (kiedy ostrzegamy), a nie bieżący stan gałęzi, na której akurat
# stoi CI.


def _z_gitem(modul, odpowiedzi: dict[tuple[str, ...], str | None]):
    """Podstawia `_git` zwracające zadane odpowiedzi."""

    def fake(*args: str):
        return odpowiedzi.get(tuple(args))

    modul._git = fake
    return modul


def _odpowiedzi(*, przed: int, moje: int, scalenia: int, godzin: float) -> dict:
    import time

    return {
        ("merge-base", "HEAD", "origin/main"): "BAZA",
        ("rev-parse", "HEAD"): "GLOWA",
        ("rev-parse", "origin/main"): "MAIN",
        ("rev-list", "--count", "BAZA..origin/main"): str(przed),
        ("rev-list", "--count", "BAZA..HEAD"): str(moje),
        ("rev-list", "--count", "--merges", "BAZA..HEAD"): str(scalenia),
        ("log", "-1", "--format=%ct", "BAZA"): str(int(time.time() - godzin * 3600)),
    }


def test_swieza_galaz_nie_wywoluje_uwag(kopia):
    """Rundy scalane na bieżąco mają przechodzić bez szumu — inaczej
    kontrola nauczy wszystkich ignorować własne komunikaty."""
    m = _z_gitem(zaladuj(kopia), _odpowiedzi(przed=1, moje=2, scalenia=0, godzin=0.4))
    w = m.Wynik()
    m.sprawdz_galaz(w)
    assert w.uwagi == []
    assert w.bledy == []


def test_main_uciekl_do_przodu_jest_zglaszany(kopia):
    m = _z_gitem(zaladuj(kopia), _odpowiedzi(przed=25, moje=3, scalenia=0, godzin=0.5))
    w = m.Wynik()
    m.sprawdz_galaz(w)
    assert any("przybyło 25 commitów" in u for u in w.uwagi), w.uwagi


def test_dluga_galaz_jest_zglaszana(kopia):
    m = _z_gitem(zaladuj(kopia), _odpowiedzi(przed=1, moje=20, scalenia=0, godzin=6.5))
    w = m.Wynik()
    m.sprawdz_galaz(w)
    assert any("odgałęziła się" in u for u in w.uwagi), w.uwagi


def test_wielokrotne_nadganianie_main_jest_zglaszane(kopia):
    m = _z_gitem(zaladuj(kopia), _odpowiedzi(przed=1, moje=20, scalenia=8, godzin=0.5))
    w = m.Wynik()
    m.sprawdz_galaz(w)
    assert any("8 scaleń" in u for u in w.uwagi), w.uwagi


def test_objawy_nigdy_nie_blokuja_builda(kopia):
    """Wiek gałęzi to sygnał procesowy, nie defekt kodu. Zatrzymanie builda
    z powodu upływu czasu byłoby karą za zegar."""
    m = _z_gitem(zaladuj(kopia), _odpowiedzi(przed=99, moje=99, scalenia=99, godzin=99))
    w = m.Wynik()
    m.sprawdz_galaz(w)
    assert w.uwagi, "powinny paść uwagi"
    assert w.bledy == [], "ale żadna nie może blokować"


def test_praca_na_main_nie_jest_galezia(kopia):
    """Na main nie ma czego mierzyć — kontrola ma milczeć."""
    odp = _odpowiedzi(przed=0, moje=0, scalenia=0, godzin=99)
    odp[("rev-parse", "HEAD")] = "TO_SAMO"
    odp[("rev-parse", "origin/main")] = "TO_SAMO"
    m = _z_gitem(zaladuj(kopia), odp)
    w = m.Wynik()
    m.sprawdz_galaz(w)
    assert w.uwagi == [] and w.bledy == []


def test_brak_origin_main_nie_wywraca_kontroli(kopia):
    """Świeży klon albo praca offline: brak danych to nie powód do alarmu."""
    m = _z_gitem(zaladuj(kopia), {})
    w = m.Wynik()
    m.sprawdz_galaz(w)
    assert w.uwagi == [] and w.bledy == []


# --- 8. Pliki poza gitem -----------------------------------------------
#
# Ta kontrola też pyta gita, ale o stan PLIKÓW, nie gałęzi — atrapa `_git`
# by tu nic nie dowiodła, bo cała wartość leży w tym, że reguły ignorowania
# rozstrzyga prawdziwy git (`.gitignore` składa się z kilku plików i ma
# wykluczenia w rodzaju `!data/.gitkeep`). Dlatego zakładamy maleńkie,
# prawdziwe repozytorium w katalogu tymczasowym.


def _repo(root: Path, *, gitignore: str = "") -> None:
    """Zakłada prawdziwe repozytorium git w `root` i commituje, co jest."""
    import subprocess

    def g(*args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True,
                       capture_output=True, text=True)

    g("init", "-q", "-b", "glowna")
    (root / ".gitignore").write_text(gitignore, encoding="utf-8")
    g("add", "-A")
    g("-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "start")


def _pliki(modul):
    w = modul.Wynik()
    modul.sprawdz_pliki_poza_gitem(w)
    return w


def test_zacommitowane_pliki_zrodlowe_sa_czyste(kopia):
    _repo(kopia)
    w = _pliki(zaladuj(kopia))
    assert w.bledy == [] and w.uwagi == []


def test_plik_zrodlowy_ignorowany_przez_gitignore_jest_bledem(kopia):
    """Najgorszy przypadek: pliku nie widać ani w `git status`, ani
    w przeglądzie — `git add -A` przechodzi obok niego bez słowa."""
    _repo(kopia, gitignore="backend/dzik_os/utracony.py\n")
    (kopia / "backend" / "dzik_os" / "utracony.py").write_text("X = 1\n")
    w = _pliki(zaladuj(kopia))
    assert any("utracony.py" in b and "ignorowany" in b for b in w.bledy), w.bledy


def test_plik_nieslledzony_jest_uwaga_a_nie_bledem(kopia):
    """W trakcie pracy nowy, jeszcze niedodany plik to stan normalny —
    blokowanie builda z tego powodu nauczyłoby wszystkich obchodzić bramkę."""
    _repo(kopia)
    (kopia / "backend" / "dzik_os" / "swiezy.py").write_text("X = 1\n")
    w = _pliki(zaladuj(kopia))
    assert w.bledy == [], w.bledy
    assert any("swiezy.py" in u and "zniknie" in u for u in w.uwagi), w.uwagi


def test_katalogi_wytworcze_nie_sa_zglaszane(kopia):
    """`node_modules`, `dist`, `.pytest_cache` MAJĄ być ignorowane —
    kontrola, która krzyczy na nie, jest bezużyteczna od pierwszego dnia."""
    _repo(kopia, gitignore="node_modules/\ndist/\n.pytest_cache/\n")
    for katalog, plik in (("node_modules", "paczka.ts"), ("dist", "wynik.mjs"),
                          (".pytest_cache", "README.md")):
        (kopia / katalog).mkdir(exist_ok=True)
        (kopia / katalog / plik).write_text("x\n")
    w = _pliki(zaladuj(kopia))
    assert w.bledy == [] and w.uwagi == []


def test_pliki_ktore_maja_prawo_byc_poza_gitem_sa_pomijane(kopia):
    """`.env`, klucze i bazy danych nie są kodem — lista rozszerzeń jest
    wąska celowo, żeby ta kontrola nie zaczęła wymuszać commitowania sekretów."""
    _repo(kopia, gitignore=".env\n*.db\n")
    (kopia / ".env").write_text("DZIK_FILE_KEY=tajne\n")
    (kopia / "dane.db").write_text("x\n")
    w = _pliki(zaladuj(kopia))
    assert w.bledy == [] and w.uwagi == []


def test_kontrola_plikow_nie_moze_przejsc_na_pusto(kopia):
    """Gdyby lista rozszerzeń albo wykluczeń zjadła wszystko, kontrola
    przechodziłaby zawsze — tak samo jak kontrola tras przed PROG_TRAS."""
    m = zaladuj(kopia)
    _repo(kopia)
    m.ROZSZERZENIA_ZRODEL = (".nieistniejace",)
    w = _pliki(m)
    assert any("przestała cokolwiek widzieć" in b for b in w.bledy), w.bledy


def test_brak_repozytorium_nie_wywraca_kontroli(kopia):
    """Rozpakowane źródła bez `.git` (archiwum, sandbox) to nie awaria."""
    w = _pliki(zaladuj(kopia))
    assert w.bledy == [] and w.uwagi == []


# --- 9. Konsultacje między sesjami -------------------------------------
#
# Kontrola czyta dziennik pytań. Testy opisują REGUŁĘ (co jest błędem
# mechanizmu, a co tylko uwagą), nie bieżącą treść dziennika.


def _dziennik(kopia: Path, tresc: str):
    (kopia / "docs").mkdir(exist_ok=True)
    (kopia / "docs" / "KONSULTACJE.md").write_text(tresc, encoding="utf-8")
    m = zaladuj(kopia)
    w = m.Wynik()
    m.sprawdz_konsultacje(w)
    return w


def _wpis(numer="K-001", stempel="2026-08-18 10:00", od="bramki",
          do="produktowa", status="OTWARTE", blokuje="nie"):
    return (f"### {numer} · {stempel}Z · od: {od} · do: {do} · STATUS: {status}\n\n"
            f"**Blokuje:** {blokuje}\n\ntreść pytania\n")


def test_otwarte_pytanie_jest_widoczne(kopia):
    """Sedno tej kontroli: otwarte pytanie ma się UPOMINAĆ samo.
    Cztery pytania z 18.08 czekały w pliku planu i nic o nich nie mówiło."""
    w = _dziennik(kopia, _wpis(status="OTWARTE"))
    assert w.bledy == []
    assert any("K-001" in u for u in w.uwagi), w.uwagi


def test_odpowiedziane_pytanie_nie_halasuje(kopia):
    """Inaczej dziennik po tygodniu wypisywałby setkę uwag i wszyscy
    nauczyliby się ignorować całą bramkę."""
    w = _dziennik(kopia, _wpis(status="ODPOWIEDZIANE"))
    assert w.bledy == [] and w.uwagi == []


def test_otwarte_pytanie_nigdy_nie_blokuje_builda(kopia):
    """Otwarte pytanie to stan normalny — zatrzymanie CI z tego powodu
    nauczyłoby wszystkich obchodzić bramkę."""
    w = _dziennik(kopia, _wpis(status="OTWARTE", blokuje="tak", stempel="2026-01-01 00:00"))
    assert w.bledy == []
    assert any("BLOKUJE" in u for u in w.uwagi), w.uwagi


def test_stara_blokada_dostaje_glosniejsza_uwage(kopia):
    """Wpis, przy którym ktoś NAPRAWDĘ stoi, musi się wyróżniać."""
    stary = _dziennik(kopia, _wpis(blokuje="tak", stempel="2026-01-01 00:00"))
    assert any("stoi" in u for u in stary.uwagi), stary.uwagi


def test_zly_ksztalt_naglowka_jest_bledem(kopia):
    """Wpis, którego kontrola nie umie odczytać, jest gorszy niż jego brak
    — ta sama zasada co PROG_TRAS przy trasach."""
    w = _dziennik(kopia, "### K-001 pytanie bez formatu\n\n**Blokuje:** nie\n")
    assert any("zly ksztalt" in b for b in w.bledy), w.bledy


def test_powtorzony_numer_jest_bledem(kopia):
    """Ten sam kształt kolizji co numer wersji i numer migracji."""
    w = _dziennik(kopia, _wpis(numer="K-001") + "\n" + _wpis(numer="K-001"))
    assert any("dwa razy" in b for b in w.bledy), w.bledy


def test_nieznana_strona_jest_bledem(kopia):
    """`do: wszyscy` znaczy `do: nikt` — adresat musi być rozstrzygalny."""
    w = _dziennik(kopia, _wpis(do="wszyscy"))
    assert any("nieznana strona" in b for b in w.bledy), w.bledy


def test_brak_pola_blokuje_jest_bledem(kopia):
    """Bez tego pola nie da się odróżnić pytania od zatrzymanej pracy."""
    w = _dziennik(kopia, "### K-001 · 2026-08-18 10:00Z · od: bramki · "
                         "do: produktowa · STATUS: OTWARTE\n\ntreść\n")
    assert any("Blokuje" in b for b in w.bledy), w.bledy


def test_pomija_przyklady_w_bloku_kodu(kopia):
    """Instrukcja pisania wpisów zawiera PRZYKŁADOWY nagłówek. Pierwsza
    wersja kontroli zgłaszała błąd na własnej dokumentacji."""
    tresc = ("## Jak pisać\n\n```\n"
             "### K-007 · 2026-08-18 15:54Z · od: bramki · do: produktowa · STATUS: OTWARTE\n"
             "```\n\n## Wpisy\n\n" + _wpis())
    w = _dziennik(kopia, tresc)
    assert w.bledy == [], w.bledy
    assert not any("K-007" in u for u in w.uwagi), w.uwagi


def test_pusty_dziennik_wywraca_kontrole(kopia):
    """Gdyby ktoś wyczyścił plik, kontrola przechodziłaby zawsze —
    ten sam bezpiecznik co PROG_TRAS i pusta lista plików źródłowych."""
    w = _dziennik(kopia, "# Konsultacje\n\nnic tu nie ma\n")
    assert any("przestala cokolwiek widziec" in b for b in w.bledy), w.bledy


def test_brak_dziennika_nie_jest_awaria(kopia):
    """Dziennik jest nieobowiązkowy — jego brak to nie awaria bramki."""
    m = zaladuj(kopia)
    w = m.Wynik()
    m.sprawdz_konsultacje(w)
    assert w.bledy == [] and w.uwagi == []

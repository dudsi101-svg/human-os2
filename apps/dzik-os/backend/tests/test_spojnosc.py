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

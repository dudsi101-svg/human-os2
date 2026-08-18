"""Import arkusza nie może zużywać pamięci proporcjonalnej do PLIKU.

Znalezione przeglądem krzyżowym 18.08.2026 (`docs/PRZEGLAD_KRZYZOWY_2026-08-18.md`),
naprawione tego samego dnia. Dwie niezależne drogi:

1. `.xlsx` to archiwum zip — plik 1,64 MB rozpakowywał się do 423 MB
   i kosztował 1164 MB RSS oraz 129 s, mimo że wynik i tak przycinano
   do 2000 wierszy;
2. trzy endpointy importu czytały upload przez `await file.read()`, więc
   plik 290 MB dawał +291 MB RSS na serwerze, zanim kontrola „większy niż
   5 MB" zdążyła go odrzucić.

Te testy pilnują OBU napraw. Nie mierzą pamięci (to byłoby kruche na CI),
tylko sprawdzają mechanizmy, które ją ograniczają — i że legalny plik
nadal przechodzi.
"""

from __future__ import annotations

import asyncio
import io
import unittest
import zipfile

from dzik_os import sheet_import, storage


def _bomba(wierszy: int) -> bytes:
    """Minimalny .xlsx o zadanej liczbie identycznych wierszy (świetnie się
    kompresuje, więc mały upload rozpakowuje się do bardzo dużego arkusza)."""
    def kom(tekst: str) -> str:
        return f'<c t="inlineStr"><is><t>{tekst}</t></is></c>'

    wiersz = "<row>" + kom("przysiad") + kom("nogi") + kom("opis") + "</row>"
    bufor = io.BytesIO()
    with zipfile.ZipFile(bufor, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="Ark" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        with z.open("xl/worksheets/sheet1.xml", "w") as f:
            f.write(b'<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')
            f.write(("<row>" + kom("nazwa") + kom("grupa") + kom("opis") + "</row>").encode())
            # Bloki po 1000 dla szybkosci, reszta pojedynczo — `// 1000`
            # bez reszty dawaloby 0 wierszy dla malych wartosci i test
            # sprawdzalby co innego, niz mysli (zlapane przy pierwszym
            # uruchomieniu: _bomba(50) tworzylo pusty arkusz).
            blok = (wiersz * 1000).encode()
            for _ in range(wierszy // 1000):
                f.write(blok)
            if wierszy % 1000:
                f.write((wiersz * (wierszy % 1000)).encode())
            f.write(b"</sheetData></worksheet>")
    return bufor.getvalue()


class _Upload:
    """Atrapa UploadFile: oddaje bajty kawałkami, jak prawdziwy strumień."""

    def __init__(self, dane: bytes) -> None:
        self._bufor = io.BytesIO(dane)
        self.przeczytano = 0

    async def read(self, rozmiar: int = -1) -> bytes:
        kawalek = self._bufor.read(rozmiar)
        self.przeczytano += len(kawalek)
        return kawalek


class TestBombaDekompresyjna(unittest.TestCase):
    def test_arkusz_o_absurdalnym_rozpakowaniu_jest_odrzucany(self):
        """Sedno naprawy: plik ma być odrzucony ZANIM openpyxl go otworzy.
        Sam `load_workbook` kosztował 24,5 s i 281 MB — żadne ograniczanie
        odczytu wierszy tego nie ruszy."""
        raw = _bomba(1_000_000)
        self.assertLess(len(raw), sheet_import.MAX_BYTES,
                        "bomba ma przechodzić limit rozmiaru pliku — o to chodzi")
        with self.assertRaises(sheet_import.SheetError) as ctx:
            sheet_import.read_table("baza.xlsx", raw, sheet_import.EXERCISE_COLUMNS)
        self.assertIn("po rozpakowaniu", str(ctx.exception))

    def test_zwykly_arkusz_przechodzi_z_ogromnym_zapasem(self):
        """Kontrola nie może odrzucać uczciwych plików. Prawdziwy arkusz
        trenera (431 pozycji) ma 570 KB po rozpakowaniu — 180x pod limitem."""
        raw = _bomba(50)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            po = sum(w.file_size for w in z.infolist())
        self.assertLess(po, sheet_import.MAX_ROZPAKOWANE)
        rows, _, _ = sheet_import.read_table("baza.xlsx", raw, sheet_import.EXERCISE_COLUMNS)
        self.assertEqual(len(rows), 50)

    def test_plik_ktory_nie_jest_zipem_zostawiamy_openpyxl(self):
        """Kontrola rozmiaru nie ma udawać walidatora formatu — od tego
        jest parser, który wyda swój własny komunikat."""
        with self.assertRaises(sheet_import.SheetError) as ctx:
            sheet_import.read_table("baza.xlsx", b"to nie jest zip",
                                    sheet_import.EXERCISE_COLUMNS)
        self.assertIn("Nie udało się otworzyć", str(ctx.exception))

    def test_nadmiar_wierszy_nadal_daje_ostrzezenie(self):
        """Przerwanie iteracji nie może zabrać informacji o pominięciu —
        wtedy trener nie wiedziałby, że część bazy nie weszła."""
        raw = _bomba(sheet_import.MAX_ROWS + 500)
        rows, _, ostrzezenia = sheet_import.read_table(
            "baza.xlsx", raw, sheet_import.EXERCISE_COLUMNS)
        self.assertEqual(len(rows), sheet_import.MAX_ROWS)
        self.assertTrue(any("więcej niż" in o for o in ostrzezenia), ostrzezenia)


class TestCzytanieUploadu(unittest.TestCase):
    def test_przestaje_czytac_po_limicie(self):
        """Klient nie może zapełnić pamięci serwera jednym żądaniem.
        Zmierzone przed naprawą: plik 290 MB dawał +291 MB RSS serwera."""
        upload = _Upload(b"x" * 10_000_000)
        dane = asyncio.run(storage.read_upload_capped(upload, 1_000_000))
        self.assertLessEqual(len(dane), 1_000_001)
        self.assertLess(upload.przeczytano, 2_000_000,
                        "reszta pliku nie miała zostać w ogóle przeczytana")

    def test_plik_ponizej_limitu_wraca_w_calosci(self):
        dane = asyncio.run(storage.read_upload_capped(_Upload(b"abc" * 100), 1_000_000))
        self.assertEqual(dane, b"abc" * 100)

    def test_limit_plus_jeden_wystarcza_by_wykryc_przekroczenie(self):
        """Wzorzec użyty w routerach: czytamy LIMIT+1, żeby `read_table`
        mogło wydać swój własny błąd 422 dokładnie jak dotąd."""
        dane = asyncio.run(storage.read_upload_capped(
            _Upload(b"x" * (sheet_import.MAX_BYTES * 2)), sheet_import.MAX_BYTES + 1))
        self.assertGreater(len(dane), sheet_import.MAX_BYTES)


if __name__ == "__main__":
    unittest.main()

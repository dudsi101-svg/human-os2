"""Bezpieczeństwo plików: rozpoznawanie typu po zawartości (magic bytes),
sanityzacja nazw plików do Content-Disposition (RFC 5987) oraz
przetwarzanie zdjęć (usunięcie EXIF/geolokalizacji, ograniczenie
rozdzielczości, bezpieczna rekompresja przez Pillow).

Zasada: deklarowany Content-Type musi być na allowliście
(config.ALLOWED_UPLOAD_TYPES) ORAZ zgadzać się z rzeczywistą zawartością —
niezgodność (np. plik .exe udający PDF, SVG udający PNG) jest odrzucana.
Przetwarzanie obrazów dotyczy wyłącznie NOWYCH uploadów; pliki wgrane
wcześniej pozostają na dysku bez zmian (brak retroaktywnej migracji treści).
"""

from __future__ import annotations

import io
import re
import unicodedata
from urllib.parse import quote

from PIL import Image, ImageOps

# Limity dekodera Pillow — obrona przed "decompression bomb" (Pillow i tak
# ostrzega przy ~90 mln pikseli; tu jawny, niższy twardy limit).
MAX_IMAGE_PIXELS = 64_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def _is_mp3(data: bytes) -> bool:
    if data.startswith(b"ID3"):
        return True
    # Ramka MPEG audio: 11 bitów synchronizacji.
    return len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


_MAGIC_CHECKS = {
    "image/jpeg": lambda d: d.startswith(b"\xff\xd8\xff"),
    "image/png": lambda d: d.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda d: d[:4] == b"RIFF" and d[8:12] == b"WEBP",
    "application/pdf": lambda d: d.startswith(b"%PDF"),
    "video/mp4": lambda d: len(d) >= 12 and d[4:8] == b"ftyp",
    "audio/mp4": lambda d: len(d) >= 12 and d[4:8] == b"ftyp",
    "audio/webm": lambda d: d.startswith(b"\x1aE\xdf\xa3"),  # EBML (WebM/Matroska)
    "audio/mpeg": _is_mp3,
    "audio/ogg": lambda d: d.startswith(b"OggS"),
}


def content_matches_type(content_type: str, data: bytes) -> bool:
    """Czy zawartość pliku zgadza się z deklarowanym typem MIME?
    Typ spoza rejestru = brak dopasowania (fail closed)."""
    check = _MAGIC_CHECKS.get(content_type)
    return bool(check and check(data))


def sanitize_filename(filename: str | None, canonical_ext: str) -> str:
    """Bezpieczna nazwa pliku do metadanych/nagłówków: bez ścieżek i znaków
    sterujących, z wymuszonym kanonicznym rozszerzeniem typu zawartości
    (neutralizuje podwójne rozszerzenia w rodzaju "plik.pdf.exe")."""
    name = (filename or "plik").replace("\\", "/").rsplit("/", 1)[-1]
    name = unicodedata.normalize("NFC", name)
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = re.sub(r'[<>:"|?*]', "_", name).strip(" .")
    # Zdejmij wszystkie rozszerzenia i nałóż kanoniczne dla typu zawartości.
    base = name.split(".", 1)[0].strip() or "plik"
    return (base[:120] + canonical_ext) if canonical_ext else base[:120]


def content_disposition(disposition: str, filename: str) -> str:
    """Nagłówek Content-Disposition z nazwą pliku wg RFC 5987/6266:
    ASCII-owy fallback w `filename=` + pełny UTF-8 w `filename*=`."""
    ascii_fallback = (
        unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
    )
    ascii_fallback = ascii_fallback.replace('"', "_").replace("\\", "_") or "plik"
    encoded = quote(filename, safe="")
    return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


_PIL_FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


def process_image(data: bytes, content_type: str, *, max_px: int, quality: int) -> bytes:
    """Rekompresja zdjęcia z nowego uploadu: usuwa wszystkie metadane
    (EXIF, w tym GPS), zachowuje orientację (transpozycja przed usunięciem
    EXIF), ogranicza dłuższy bok do max_px i zapisuje z podaną jakością.
    ValueError, gdy danych nie da się zdekodować jako obraz."""
    fmt = _PIL_FORMATS.get(content_type)
    if fmt is None:
        raise ValueError(f"Nieobsługiwany typ obrazu: {content_type}")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise ValueError("Nie można zdekodować obrazu") from exc
    img = ImageOps.exif_transpose(img)
    if max(img.size) > max_px:
        img.thumbnail((max_px, max_px), Image.LANCZOS)
    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    out = io.BytesIO()
    save_kwargs: dict = {}
    if fmt == "JPEG":
        save_kwargs = {"quality": quality, "optimize": True}
    elif fmt == "WEBP":
        save_kwargs = {"quality": quality}
    elif fmt == "PNG":
        save_kwargs = {"optimize": True}
    # Brak parametru exif/xmp => metadane nie są przenoszone do wyniku.
    img.save(out, format=fmt, **save_kwargs)
    return out.getvalue()

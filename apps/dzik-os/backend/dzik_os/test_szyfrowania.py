"""Dowód działania szyfrowania plików at-rest (0.53.6, audyt A6/R-02).

Użycie (lokalnie albo na maszynie Fly przez `flyctl ssh console`):

    python -m dzik_os.test_szyfrowania

Sens istnienia: po ustawieniu DZIK_FILE_KEY szyfrowanie ma być
UDOWODNIONE na maszynie, a nie przyjęte na wiarę — workflow
„Klucz szyfrowania plików (Fly.io)" wywołuje ten moduł po restarcie.
Dowód w trzech krokach, dokładnie ścieżką, którą chodzi `LocalStorage`:

1. `load_file_key()` zwraca poprawny klucz (32 bajty po base64) —
   literówka w kluczu to jawny błąd, nie cichy zapis jawny;
2. plik-sonda zapisany w katalogu uploadów zaczyna się na dysku od
   nagłówka ``DZIKENC1`` (surowe bajty, nie deklaracja);
3. odszyfrowanie wraca 1:1 do treści sondy.

Sonda jest po sobie sprzątana. Kod wyjścia 0 wyłącznie przy pełnym
dowodzie; brak klucza to kod 1 (`no_key`) — workflow ma wtedy czerwień,
bo wywołuje ten moduł dopiero PO ustawieniu sekretu. Treść sondy nie
zawiera żadnych danych osobowych, a moduł nie loguje klucza.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import settings
from .storage import ENC_MAGIC, decrypt_file_bytes, encrypt_file_bytes, load_file_key


def dowod_szyfrowania() -> tuple[bool, str]:
    """Przeprowadza pełny dowód. Zwraca (wynik, opis dla operatora)."""
    try:
        key = load_file_key()
    except ValueError as exc:
        return False, f"bad_key: {exc}"
    if key is None:
        return False, (
            "no_key: DZIK_FILE_KEY nie jest ustawiony — pliki są zapisywane "
            "bez szyfrowania (RISK_REGISTER R-02)."
        )

    tresc = b"dzik-os sonda szyfrowania " + os.urandom(16).hex().encode()
    katalog = Path(settings.upload_dir)
    katalog.mkdir(parents=True, exist_ok=True)
    sonda = katalog / f".sonda-szyfrowania-{os.urandom(6).hex()}"
    try:
        sonda.write_bytes(encrypt_file_bytes(key, tresc))
        surowe = sonda.read_bytes()
        if not surowe.startswith(ENC_MAGIC):
            return False, "no_header: plik na dysku nie zaczyna się od DZIKENC1."
        if surowe.find(tresc) != -1:
            return False, "plaintext_leak: treść sondy widoczna w pliku na dysku."
        if decrypt_file_bytes(key, surowe) != tresc:
            return False, "roundtrip_mismatch: odszyfrowana treść różni się od sondy."
    finally:
        sonda.unlink(missing_ok=True)
    return True, (
        f"Szyfrowanie plików działa: nagłówek {ENC_MAGIC.decode()} na dysku, "
        f"odszyfrowanie 1:1 (katalog: {katalog})."
    )


def main() -> int:
    ok, opis = dowod_szyfrowania()
    if ok:
        print(opis)
        return 0
    print(f"BŁĄD: {opis}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

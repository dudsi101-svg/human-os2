"""Szyfrowanie at-rest plików uploadów (R-02): roundtrip z kluczem,
kompatybilność wsteczna z plikami jawnymi, jawne błędy zamiast cichego
mieszania trybów."""

import base64
import io
import os

import pytest
from conftest import CLIENT_A, login, make_png
from fastapi import HTTPException

from dzik_os import storage as storage_module
from dzik_os.config import settings
from dzik_os.models import StoredFile
from dzik_os.storage import (
    ENC_MAGIC,
    decrypt_file_bytes,
    encrypt_file_bytes,
    load_file_key,
)

# Sztuczne bajty do testów jednostkowych szyfru; upload przez API używa
# prawdziwego PNG (pipeline z file_safety waliduje i rekompresuje obrazy).
PNG = b"\x89PNG\r\n\x1a\n" + b"tajne-zdjecie" * 20
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
REAL_PNG = make_png()


def _upload_png(client, headers):
    r = client.post(
        "/api/files", headers=headers,
        files={"file": ("zdjecie.png", io.BytesIO(REAL_PNG), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _raw_on_disk(client, file_id) -> bytes:
    from dzik_os.db import db_session

    with db_session() as db:
        stored = db.get(StoredFile, file_id)
        path = storage_module.storage.root / stored.storage_path
    return path.read_bytes()


def test_encrypt_decrypt_roundtrip():
    key = os.urandom(32)
    blob = encrypt_file_bytes(key, PNG)
    assert blob.startswith(ENC_MAGIC)
    assert PNG not in blob
    assert decrypt_file_bytes(key, blob) == PNG


def test_legacy_plaintext_returned_verbatim_with_key():
    # Plik sprzed włączenia szyfrowania (bez nagłówka) — zwracany wprost.
    key = os.urandom(32)
    assert decrypt_file_bytes(key, PNG) == PNG
    assert decrypt_file_bytes(None, PNG) == PNG


def test_encrypted_without_key_is_explicit_error():
    blob = encrypt_file_bytes(os.urandom(32), PNG)
    with pytest.raises(HTTPException) as exc:
        decrypt_file_bytes(None, blob)
    assert exc.value.status_code == 500
    with pytest.raises(HTTPException):
        decrypt_file_bytes(os.urandom(32), blob)  # zły klucz — też jawny błąd


def test_load_file_key_validation(monkeypatch):
    monkeypatch.setattr(settings, "file_key_b64", "")
    assert load_file_key() is None
    monkeypatch.setattr(settings, "file_key_b64", "nie-base64!!!")
    with pytest.raises(ValueError):
        load_file_key()
    monkeypatch.setattr(settings, "file_key_b64", base64.b64encode(b"za-krotki").decode())
    with pytest.raises(ValueError):
        load_file_key()
    good = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setattr(settings, "file_key_b64", good)
    assert len(load_file_key()) == 32


def test_upload_roundtrip_via_api_with_key(seeded, monkeypatch):
    key = os.urandom(32)
    monkeypatch.setattr(storage_module.storage, "_key", key)
    ha = login(seeded, CLIENT_A)
    file_id = _upload_png(seeded, ha)

    raw = _raw_on_disk(seeded, file_id)
    assert raw.startswith(ENC_MAGIC)     # na dysku leży szyfrogram
    assert PNG_MAGIC not in raw          # żadnego jawnego PNG w szyfrogramie

    r = seeded.get(f"/api/files/{file_id}", headers=ha)
    assert r.status_code == 200
    assert r.content.startswith(PNG_MAGIC)          # API zwraca odszyfrowany PNG
    assert decrypt_file_bytes(key, raw) == r.content


def test_upload_without_key_stays_plaintext(seeded):
    # Domyślny tryb testów (bez DZIK_FILE_KEY): zachowanie jak dotychczas.
    ha = login(seeded, CLIENT_A)
    file_id = _upload_png(seeded, ha)
    raw = _raw_on_disk(seeded, file_id)
    assert raw.startswith(PNG_MAGIC)     # na dysku jawny PNG, bez nagłówka szyfru
    r = seeded.get(f"/api/files/{file_id}", headers=ha)
    assert r.content == raw


def test_legacy_file_readable_after_enabling_key(seeded, monkeypatch):
    # Plik wgrany jawnie, potem operator włącza klucz — odczyt nadal działa.
    ha = login(seeded, CLIENT_A)
    file_id = _upload_png(seeded, ha)
    served_before = seeded.get(f"/api/files/{file_id}", headers=ha).content
    monkeypatch.setattr(storage_module.storage, "_key", os.urandom(32))
    r = seeded.get(f"/api/files/{file_id}", headers=ha)
    assert r.status_code == 200
    assert r.content == served_before

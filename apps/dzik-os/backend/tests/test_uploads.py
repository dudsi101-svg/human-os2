"""Walidacja uploadów i kontrola dostępu do plików."""

import io

from conftest import CLIENT_A, CLIENT_B, COACH, login

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def _upload(client, headers, *, content=PNG, content_type="image/png",
            filename="zdjecie.png", params=None):
    return client.post(
        "/api/files", headers=headers, params=params or {},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


def test_upload_and_download_own_file(seeded):
    ha = login(seeded, CLIENT_A)
    r = _upload(seeded, ha)
    assert r.status_code == 201
    file_id = r.json()["id"]
    assert r.json()["sha256"]
    r = seeded.get(f"/api/files/{file_id}", headers=ha)
    assert r.status_code == 200
    assert r.content == PNG
    assert r.headers["x-content-type-options"] == "nosniff"


def test_other_client_cannot_download(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    file_id = _upload(seeded, ha).json()["id"]
    assert seeded.get(f"/api/files/{file_id}", headers=hb).status_code == 404


def test_coach_can_download_clients_file(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    file_id = _upload(seeded, ha).json()["id"]
    assert seeded.get(f"/api/files/{file_id}", headers=hc).status_code == 200


def test_disallowed_type_rejected(seeded):
    ha = login(seeded, CLIENT_A)
    r = _upload(seeded, ha, content=b"MZ...", content_type="application/x-msdownload",
                filename="wirus.exe")
    assert r.status_code == 415


def test_oversize_rejected(seeded):
    from dzik_os.config import settings

    ha = login(seeded, CLIENT_A)
    big = b"0" * (settings.max_upload_mb * 1024 * 1024 + 1)
    r = _upload(seeded, ha, content=big)
    assert r.status_code == 413


def test_empty_file_rejected(seeded):
    ha = login(seeded, CLIENT_A)
    r = _upload(seeded, ha, content=b"")
    assert r.status_code == 400


def test_coach_upload_for_client_owned_by_client(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    from conftest import get_user_id

    id_a = get_user_id(seeded, ha)
    r = _upload(seeded, hc, params={"client_id": id_a},
                content=b"%PDF-1.4 test", content_type="application/pdf",
                filename="dieta.pdf")
    assert r.status_code == 201
    file_id = r.json()["id"]
    # Klient (właściciel danych) może pobrać.
    assert seeded.get(f"/api/files/{file_id}", headers=ha).status_code == 200

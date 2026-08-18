"""Bezpieczeństwo systemu plików: typ po zawartości (magic bytes),
sanityzacja nazw (RFC 5987), path traversal, EXIF, limity zdjęć raportu,
autoryzacja wszystkich ścieżek dostępu (dokumenty, zdjęcia, załączniki
wiadomości i bazy wiedzy), cofnięcie zgody, pliki-sieroty."""

import io
from datetime import UTC, datetime, timedelta

from conftest import (
    CLIENT_A,
    CLIENT_B,
    COACH,
    create_user_with_role,
    get_user_id,
    login,
    make_jpeg,
    make_png,
)

PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
MP3 = b"ID3" + b"\x00" * 60
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
WEBM = b"\x1aE\xdf\xa3" + b"\x00" * 64


def _upload(client, headers, *, content, content_type, filename="plik", params=None):
    return client.post(
        "/api/files", headers=headers, params=params or {},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


# --- Pobieranie: typy plików, nagłówki, krąg uprawnionych -----------------

def test_pdf_download_owner_coach_stranger_and_anonymous(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    hc = login(seeded, COACH)
    r = _upload(seeded, ha, content=PDF, content_type="application/pdf",
                filename="wyniki badań.pdf")
    assert r.status_code == 201
    fid = r.json()["id"]

    r = seeded.get(f"/api/files/{fid}", headers=ha)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"
    assert "filename*=UTF-8''" in r.headers["content-disposition"]

    # Trener z aktywną relacją i zgodą: 200. Obcy klient: 404. Bez tokenu: 401
    # (TestClient trzyma cookie sesji z logowania — czyścimy przed próbą
    # anonimową).
    assert seeded.get(f"/api/files/{fid}", headers=hc).status_code == 200
    assert seeded.get(f"/api/files/{fid}", headers=hb).status_code == 404
    seeded.cookies.clear()
    assert seeded.get(f"/api/files/{fid}").status_code == 401


def test_photo_audio_video_roundtrip(seeded):
    ha = login(seeded, CLIENT_A)
    for content, ctype in ((make_png(), "image/png"), (make_jpeg(), "image/jpeg"),
                           (MP3, "audio/mpeg"), (WEBM, "audio/webm"),
                           (MP4, "video/mp4")):
        r = _upload(seeded, ha, content=content, content_type=ctype)
        assert r.status_code == 201, (ctype, r.text)
        fid = r.json()["id"]
        d = seeded.get(f"/api/files/{fid}", headers=ha)
        assert d.status_code == 200
        assert d.headers["content-type"].startswith(ctype)


# --- Walidacja zawartości i nazw ------------------------------------------

def test_magic_bytes_mismatch_rejected(seeded):
    ha = login(seeded, CLIENT_A)
    # PDF udający zdjęcie i zdjęcie udające PDF — oba odrzucone.
    assert _upload(seeded, ha, content=PDF, content_type="image/png").status_code == 415
    assert _upload(seeded, ha, content=make_png(),
                   content_type="application/pdf").status_code == 415


def test_executable_with_double_extension_rejected(seeded):
    ha = login(seeded, CLIENT_A)
    r = _upload(seeded, ha, content=b"MZ\x90\x00" + b"\x00" * 60,
                content_type="application/pdf", filename="plik.pdf.exe")
    assert r.status_code == 415  # zawartość (PE/EXE) ≠ deklaracja (PDF)


def test_double_extension_filename_is_canonicalized(seeded):
    ha = login(seeded, CLIENT_A)
    r = _upload(seeded, ha, content=PDF, content_type="application/pdf",
                filename="dieta.pdf.exe")
    assert r.status_code == 201
    assert r.json()["filename"] == "dieta.pdf"
    d = seeded.get(f"/api/files/{r.json()['id']}", headers=ha)
    assert 'filename="dieta.pdf"' in d.headers["content-disposition"]


def test_svg_not_in_allowlist(seeded):
    ha = login(seeded, CLIENT_A)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert _upload(seeded, ha, content=svg,
                   content_type="image/svg+xml").status_code == 415


def test_filename_sanitized_rfc5987(seeded):
    ha = login(seeded, CLIENT_A)
    r = _upload(seeded, ha, content=PDF, content_type="application/pdf",
                filename='../..\\zażółć "gęślą\njaźń.pdf')
    assert r.status_code == 201
    name = r.json()["filename"]
    assert "/" not in name and "\\" not in name and "\n" not in name
    assert name.endswith(".pdf")
    cd = seeded.get(f"/api/files/{r.json()['id']}", headers=ha).headers[
        "content-disposition"]
    assert "filename*=UTF-8''" in cd and "\n" not in cd


def test_path_traversal_in_storage_path_blocked(seeded):
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    from dzik_os.db import db_session
    from dzik_os.models import StoredFile, new_id

    with db_session() as db:
        fid = new_id("FIL")
        db.add(StoredFile(
            id=fid, owner_user_id=id_a, filename="passwd",
            content_type="application/pdf", size_bytes=1, sha256="0" * 64,
            storage_path="../../../../etc/passwd", uploaded_by=id_a,
        ))
    assert seeded.get(f"/api/files/{fid}", headers=ha).status_code == 404


# --- Zdjęcia: EXIF/geolokalizacja, rozdzielczość --------------------------

def test_exif_removed_and_resolution_capped(seeded):
    from PIL import Image

    img = Image.new("RGB", (3000, 1200), (10, 20, 30))
    exif = img.getexif()
    exif[271] = "TestCam"       # Make
    exif[272] = "Model X"       # Model — reprezentuje metadane (w tym GPS IFD)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)

    ha = login(seeded, CLIENT_A)
    r = _upload(seeded, ha, content=buf.getvalue(), content_type="image/jpeg",
                filename="sylwetka.jpg")
    assert r.status_code == 201
    d = seeded.get(f"/api/files/{r.json()['id']}", headers=ha)
    out = Image.open(io.BytesIO(d.content))
    assert dict(out.getexif()) == {}          # EXIF (w tym GPS) usunięty
    assert max(out.size) <= 2560              # dłuższy bok ograniczony
    assert out.format == "JPEG"


def test_corrupt_image_rejected(seeded):
    ha = login(seeded, CLIENT_A)
    fake = b"\x89PNG\r\n\x1a\n" + b"0" * 100  # nagłówek OK, treść nie dekoduje się
    assert _upload(seeded, ha, content=fake, content_type="image/png").status_code == 415


# --- Podpinanie plików do zasobów -----------------------------------------

def _submit_checkin(client, headers, photo_ids):
    return client.post("/api/checkins", headers=headers, json={
        "week_start": "2026-08-17", "photo_ids": photo_ids,
    })


def test_checkin_rejects_foreign_or_nonimage_photo(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    foreign = _upload(seeded, hb, content=make_png(),
                      content_type="image/png").json()["id"]
    assert _submit_checkin(seeded, ha, [foreign]).status_code == 422
    pdf = _upload(seeded, ha, content=PDF,
                  content_type="application/pdf").json()["id"]
    assert _submit_checkin(seeded, ha, [pdf]).status_code == 422


def test_checkin_photo_count_limit(seeded):
    from dzik_os.config import settings

    ha = login(seeded, CLIENT_A)
    fid = _upload(seeded, ha, content=make_png(),
                  content_type="image/png").json()["id"]
    too_many = [fid] * (settings.max_checkin_photos + 1)
    assert _submit_checkin(seeded, ha, too_many).status_code == 422


def test_message_rejects_foreign_attachment(seeded):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    foreign = _upload(seeded, hb, content=make_png(),
                      content_type="image/png").json()["id"]
    threads = seeded.get("/api/threads", headers=ha).json()["threads"]
    r = seeded.post(f"/api/threads/{threads[0]['id']}/messages", headers=ha,
                    json={"body": "hej", "file_id": foreign})
    assert r.status_code == 422
    # Cudzy plik nadal niedostępny dla A.
    assert seeded.get(f"/api/files/{foreign}", headers=ha).status_code == 404


def test_document_must_reference_clients_file(seeded):
    hc = login(seeded, COACH)
    hb = login(seeded, CLIENT_B)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    file_b = _upload(seeded, hb, content=PDF,
                     content_type="application/pdf").json()["id"]
    r = seeded.post("/api/documents", headers=hc, json={
        "client_id": id_a, "file_id": file_b, "title": "Podejrzany", "category": "INNE",
    })
    assert r.status_code == 422


def test_knowledge_rejects_client_owned_file(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    client_file = _upload(seeded, hc, params={"client_id": id_a}, content=PDF,
                          content_type="application/pdf").json()["id"]
    r = seeded.post("/api/coach/knowledge", headers=hc, json={
        "title": "Materiał", "file_id": client_file,
    })
    assert r.status_code == 422


# --- Załączniki bazy wiedzy: dostęp klientów ------------------------------

def test_knowledge_attachment_visible_to_active_client_only(seeded):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    fid = _upload(seeded, hc, content=PDF,
                  content_type="application/pdf").json()["id"]
    item = seeded.post("/api/coach/knowledge", headers=hc, json={
        "title": "Poradnik regeneracji", "file_id": fid,
    }).json()

    # Aktywnie prowadzony klient pobierze załącznik bazy wiedzy.
    assert seeded.get(f"/api/files/{fid}", headers=ha).status_code == 200

    # Osoba spoza relacji z trenerem — nie.
    create_user_with_role("obcy@example.com", "ObcyKlient#2026", "Obcy", "CLIENT")
    ho = login(seeded, {"email": "obcy@example.com", "password": "ObcyKlient#2026"})
    assert seeded.get(f"/api/files/{fid}", headers=ho).status_code == 404

    # Po zarchiwizowaniu wpisu załącznik przestaje być dostępny dla klienta.
    r = seeded.post(f"/api/coach/knowledge/{item['id']}/status",
                    headers=hc, params={"status": "ARCHIVED"})
    assert r.status_code == 200
    assert seeded.get(f"/api/files/{fid}", headers=ha).status_code == 404


# --- Cofnięcie zgody a istniejące pliki -----------------------------------

def test_revoked_consent_blocks_existing_files(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    fid = _upload(seeded, ha, content=make_png(),
                  content_type="image/png").json()["id"]
    assert seeded.get(f"/api/files/{fid}", headers=hc).status_code == 200

    # Plik bez referencji podlega domenie współpracy — cofnięcie zgody
    # „udostępnianie danych trenerowi" odbiera dostęp także do
    # ISTNIEJĄCYCH plików.
    consents = seeded.get("/api/me/consents", headers=ha).json()["consents"]
    active = next(c for c in consents if c["revoked_at"] is None
                  and c["category"] == "udostepnianie_trenerowi")
    assert seeded.post(f"/api/me/consents/{active['id']}/revoke",
                       headers=ha).status_code == 200

    # ISTNIEJĄCY plik klienta przestaje być dostępny dla trenera…
    assert seeded.get(f"/api/files/{fid}", headers=hc).status_code == 404
    # …a właściciel nadal go pobiera.
    assert seeded.get(f"/api/files/{fid}", headers=ha).status_code == 200


# --- Soft delete i sieroty -------------------------------------------------

def test_soft_deleted_file_returns_404(seeded):
    ha = login(seeded, CLIENT_A)
    fid = _upload(seeded, ha, content=PDF,
                  content_type="application/pdf").json()["id"]
    from dzik_os.db import db_session
    from dzik_os.models import StoredFile, now_iso

    with db_session() as db:
        db.get(StoredFile, fid).deleted_at = now_iso()
    assert seeded.get(f"/api/files/{fid}", headers=ha).status_code == 404


def test_orphan_files_cleanup_after_ttl(seeded):
    from pathlib import Path

    from dzik_os.config import settings
    from dzik_os.db import db_session
    from dzik_os.file_cleanup import cleanup_orphan_files
    from dzik_os.models import StoredFile

    ha = login(seeded, CLIENT_A)
    orphan = _upload(seeded, ha, content=make_png(),
                     content_type="image/png").json()["id"]
    attached = _upload(seeded, ha, content=make_png(),
                       content_type="image/png").json()["id"]
    threads = seeded.get("/api/threads", headers=ha).json()["threads"]
    seeded.post(f"/api/threads/{threads[0]['id']}/messages", headers=ha,
                json={"body": "zdjęcie", "file_id": attached})

    old = (datetime.now(UTC) - timedelta(hours=30)).isoformat()
    with db_session() as db:
        for fid in (orphan, attached):
            db.get(StoredFile, fid).created_at = old

    with db_session() as db:
        cleaned = cleanup_orphan_files(db)
        assert cleaned >= 1
        row = db.get(StoredFile, orphan)
        assert row.deleted_at is not None
        assert not (Path(settings.upload_dir) / row.storage_path).exists()
        assert db.get(StoredFile, attached).deleted_at is None

    # Sierota po sprzątnięciu jest niedostępna; podpięty plik działa.
    assert seeded.get(f"/api/files/{orphan}", headers=ha).status_code == 404
    assert seeded.get(f"/api/files/{attached}", headers=ha).status_code == 200


def test_fresh_orphan_not_cleaned(seeded):
    from dzik_os.db import db_session
    from dzik_os.file_cleanup import cleanup_orphan_files
    from dzik_os.models import StoredFile

    ha = login(seeded, CLIENT_A)
    fid = _upload(seeded, ha, content=make_png(),
                  content_type="image/png").json()["id"]
    with db_session() as db:
        cleanup_orphan_files(db)
        assert db.get(StoredFile, fid).deleted_at is None


# --- Wątek wiadomości: dostęp trenera wygasa z relacją --------------------

def test_thread_attachment_requires_active_relationship_for_coach(seeded):
    ha = login(seeded, CLIENT_A)
    hc = login(seeded, COACH)
    id_a = get_user_id(seeded, ha)
    fid = _upload(seeded, ha, content=make_png(),
                  content_type="image/png").json()["id"]
    threads = seeded.get("/api/threads", headers=ha).json()["threads"]
    seeded.post(f"/api/threads/{threads[0]['id']}/messages", headers=ha,
                json={"body": "załącznik", "file_id": fid})
    assert seeded.get(f"/api/files/{fid}", headers=hc).status_code == 200

    from dzik_os.db import db_session
    from dzik_os.models import CoachClientRelationship

    with db_session() as db:
        rel = (db.query(CoachClientRelationship)
               .filter_by(client_id=id_a, status="ACTIVE").one())
        rel.status = "ENDED"
    # Relacja zakończona: trener traci dostęp także do załącznika wątku.
    assert seeded.get(f"/api/files/{fid}", headers=hc).status_code == 404
    # Klient (strona wątku i właściciel) zachowuje dostęp.
    assert seeded.get(f"/api/files/{fid}", headers=ha).status_code == 200

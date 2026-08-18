"""Przepisywanie tekstu ze zdjęcia (OCR) — dwa tryby, kolejka jednoslotowa,
propozycja zamiast automatycznego zapisu i twarde bramki prywatności.

Środowisko testowe NIE MA zainstalowanego Tesseracta — i to jest część
kontraktu: brak silnika ma być czytelnym STANEM, nigdy wyjątkiem ani 500.
Prawdziwy przebieg testujemy na atrapie silnika; obecność binarki to
osobny, pomijany test.
"""

from __future__ import annotations

import io
import json
import shutil
import threading
import time

import pytest
from conftest import (
    ADMIN,
    CLIENT_A,
    CLIENT_B,
    COACH,
    create_user_with_role,
    get_user_id,
    login,
    make_jpeg,
    make_png,
)

from dzik_os import ai_provider, ocr, ocr_ai, ocr_queue
from dzik_os.config import settings

ETYKIETA = (
    "Jogurt naturalny 2%\n"
    "Wartość odżywcza w 100 g\n"
    "Wartość energetyczna 61 kcal\n"
    "Tłuszcz 2,0 g\n"
    "Węglowodany 4,7 g\n"
    "Białko 5,1 g\n"
    "Błonnik 0,0 g\n"
    "Porcja 150 g\n"
)


class StubEngine:
    """Atrapa silnika lokalnego — zawsze dostępna, zwraca zadany tekst."""

    name = "LOCAL"

    def __init__(self, text: str = ETYKIETA, *, delay: float = 0.0, ok: bool = True):
        self.text = text
        self.delay = delay
        self.ok = ok
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def availability(self):
        return ocr.EngineAvailability(True)

    def recognize(self, image, *, content_type="image/png", timeout_s=None):
        with self._lock:
            self.calls += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                time.sleep(self.delay)
            if not self.ok:
                return ocr.OcrResult(
                    False, reason=ocr.ENGINE_ERROR_REASON, error_code=ocr.ERR_ENGINE_ERROR
                )
            return ocr.OcrResult(True, text=self.text)
        finally:
            with self._lock:
                self.active -= 1


class StubVisionProvider:
    """Atrapa dostawcy modelu widzenia (tryb rozszerzony)."""

    name = "stub-vision"
    enabled = True

    def __init__(self, payload: str):
        self.payload = payload
        self.calls = 0
        self.last_kwargs: dict | None = None

    def summarize_checkin(self, *, payload, history_note):
        return None

    def propose_json(self, *, system_prompt, data_section, schema_hint, timeout_s):
        return None

    def propose_json_from_image(self, *, system_prompt, image, media_type,
                                task_hint, schema_hint, timeout_s):
        self.calls += 1
        self.last_kwargs = {
            "system_prompt": system_prompt, "image_len": len(image),
            "media_type": media_type, "task_hint": task_hint, "schema_hint": schema_hint,
        }
        return ai_provider.AIJsonResponse(text=self.payload, tokens_in=100, tokens_out=50)


def upload_png(client, headers, *, client_id: str | None = None) -> str:
    url = "/api/files" + (f"?client_id={client_id}" if client_id else "")
    r = client.post(url, headers=headers,
                    files={"file": ("etykieta.png", make_png(40, 40), "image/png")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def run_task(client, headers, payload: dict) -> dict:
    r = client.post("/api/ocr/tasks", headers=headers, json=payload)
    assert r.status_code == 202, r.text
    task_id = r.json()["id"]
    assert ocr_queue.tasks.wait_idle(30) is True
    return client.get(f"/api/ocr/tasks/{task_id}", headers=headers).json()


@pytest.fixture()
def stub_engine(monkeypatch):
    stub = StubEngine()
    monkeypatch.setattr(ocr, "engine", stub)
    return stub


# --- Brak silnika lokalnego --------------------------------------------


def test_status_reports_engine_unavailable_without_tesseract(seeded):
    """Bez Tesseracta funkcja mówi wprost, że silnik jest niedostępny —
    to stan do pokazania człowiekowi, nie błąd techniczny."""
    ha = login(seeded, CLIENT_A)
    r = seeded.get("/api/ocr/status", headers=ha)
    assert r.status_code == 200
    body = r.json()
    assert body["engine_available"] is False
    assert "silnik" in body["engine_reason"].lower()
    # Bez skonfigurowanego dostawcy tryb jest zawsze lokalny, z powodem.
    assert body["mode"] == "LOCAL"
    assert body["mode_reason"]
    assert body["accepted_types"] == ["image/jpeg", "image/png", "image/webp"]


def test_missing_engine_gives_readable_state_not_500(seeded):
    ha = login(seeded, CLIENT_A)
    file_id = upload_png(seeded, ha)
    task = run_task(seeded, ha, {"file_id": file_id, "purpose": "PLAN"})
    assert task["status"] == "FAILED"
    assert task["error_code"] == "ENGINE_UNAVAILABLE"
    assert "ręcznie" in task["error"]
    assert task["text"] is None


@pytest.mark.skipif(
    shutil.which(settings.ocr_binary) is None,
    reason="Tesseract nie jest zainstalowany (środowisko testowe) — test opcjonalny",
)
def test_real_engine_when_binary_present(seeded):  # pragma: no cover - opcjonalne
    assert ocr.LocalOcrEngine().availability().available is True


# --- Rozpoznanie na atrapie silnika ------------------------------------


def test_local_engine_produces_text_and_product_proposal(seeded, stub_engine):
    hc = login(seeded, COACH)
    file_id = upload_png(seeded, hc)
    task = run_task(seeded, hc, {"file_id": file_id, "purpose": "PRODUKT"})
    assert task["status"] == "DONE"
    assert task["engine"] == "LOCAL"
    assert "Jogurt" in task["text"]
    proposal = task["proposal"]
    assert proposal["kcal_100g"] == 61
    assert proposal["protein_100g"] == 5.1
    assert proposal["fat_100g"] == 2.0
    assert proposal["carbs_100g"] == 4.7
    assert proposal["portion_g"] == 150
    assert proposal["name"] == "Jogurt naturalny 2%"
    assert stub_engine.calls == 1


def test_unreadable_fields_stay_empty_never_guessed():
    """Czego nie widać na etykiecie, tego nie ma w propozycji."""
    proposal = ocr.parse_nutrition_label("Chleb żytni\nBiałko 7 g\n")
    assert proposal["protein_100g"] == 7
    assert proposal["kcal_100g"] is None
    assert proposal["fat_100g"] is None
    assert proposal["fiber_100g"] is None


def test_out_of_range_values_are_dropped_like_in_csv_import():
    """Zakresy te same co przy imporcie CSV — wartość spoza zakresu nie
    jest „naprawiana”, tylko pomijana."""
    clamped = ocr.clamp_proposal(
        {"name": " Ser ", "kcal_100g": 5000, "protein_100g": 12,
         "fat_100g": -3, "carbs_100g": "dużo", "fiber_100g": None, "portion_g": 30}
    )
    assert clamped["name"] == "Ser"
    assert clamped["kcal_100g"] is None
    assert clamped["protein_100g"] == 12
    assert clamped["fat_100g"] is None
    assert clamped["carbs_100g"] is None
    assert clamped["portion_g"] == 30


# --- Tryb rozszerzony (model) ------------------------------------------


def _grant_ai_consent(client, headers) -> None:
    client.post("/api/me/consents", headers=headers, json={"category": "funkcje_ai"})


def test_extended_mode_used_when_provider_and_consent_present(
    seeded, stub_engine, monkeypatch
):
    ha = login(seeded, CLIENT_A)
    _grant_ai_consent(seeded, ha)
    provider = StubVisionProvider(json.dumps({
        "text": "Przysiad 3x10\nWiosłowanie 3x12",
        "fields": None,
    }))
    monkeypatch.setattr(ai_provider, "provider", provider)
    file_id = upload_png(seeded, ha)
    task = run_task(seeded, ha, {"file_id": file_id, "purpose": "PLAN"})
    assert task["status"] == "DONE"
    assert task["engine"] == "EXTENDED"
    assert "Przysiad" in task["text"]
    assert provider.calls == 1
    # Minimalizacja: do dostawcy poszło zdjęcie i rodzaj zadania — bez
    # identyfikatorów, e-maili i nazwisk.
    sent = json.dumps(provider.last_kwargs, ensure_ascii=False)
    client_id = get_user_id(seeded, ha)
    assert client_id not in sent
    assert CLIENT_A["email"] not in sent
    assert file_id not in sent
    # Silnik lokalny nie był w ogóle potrzebny.
    assert stub_engine.calls == 0


def test_invalid_model_output_is_rejected_and_local_result_wins(
    seeded, stub_engine, monkeypatch
):
    ha = login(seeded, CLIENT_A)
    _grant_ai_consent(seeded, ha)
    # Odpowiedź niezgodna ze schematem (dodatkowe pole + tekst poza JSON).
    provider = StubVisionProvider("oto wynik: {\"text\": \"x\", \"diagnoza\": \"cukrzyca\"}")
    monkeypatch.setattr(ai_provider, "provider", provider)
    file_id = upload_png(seeded, ha)
    task = run_task(seeded, ha, {"file_id": file_id, "purpose": "PRODUKT"})
    assert task["status"] == "DONE"
    assert task["engine"] == "LOCAL"
    assert "Jogurt" in task["text"]
    assert task["mode_reason"] == ocr_ai.INVALID_OUTPUT_REASON
    # Jedna próba + jedno ponowienie, potem wynik lokalny.
    assert provider.calls == 2
    assert "cukrzyca" not in (task["text"] or "")


def test_product_fields_outside_label_task_are_rejected():
    with pytest.raises(ocr_ai.RejectedVision):
        ocr_ai.parse_vision_result(
            json.dumps({"text": "x", "fields": {"kcal_100g": 100}}), purpose="PLAN"
        )


def test_without_ai_consent_local_mode_with_explicit_reason(
    seeded, stub_engine, monkeypatch
):
    """Brak zgody funkcje_ai = ani jeden bajt nie idzie do dostawcy;
    działa silnik lokalny, a powód jest jawny (nie jest to błąd)."""
    hb = login(seeded, CLIENT_B)  # klient B nie ma zgody funkcje_ai w seedzie
    provider = StubVisionProvider(json.dumps({"text": "cokolwiek", "fields": None}))
    monkeypatch.setattr(ai_provider, "provider", provider)
    r = seeded.get("/api/ocr/status", headers=hb)
    assert r.json()["mode"] == "LOCAL"
    assert r.json()["mode_reason"] == ocr_ai.NO_CONSENT_REASON
    file_id = upload_png(seeded, hb)
    task = run_task(seeded, hb, {"file_id": file_id, "purpose": "PLAN"})
    assert task["status"] == "DONE"
    assert task["engine"] == "LOCAL"
    assert task["mode_reason"] == ocr_ai.NO_CONSENT_REASON
    assert provider.calls == 0


# --- Bramki dostępu ----------------------------------------------------


def test_foreign_file_is_404(seeded, stub_engine):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    file_id = upload_png(seeded, ha)
    r = seeded.post("/api/ocr/tasks", headers=hb,
                    json={"file_id": file_id, "purpose": "PLAN"})
    assert r.status_code == 404


def test_foreign_task_is_404(seeded, stub_engine):
    ha = login(seeded, CLIENT_A)
    hb = login(seeded, CLIENT_B)
    file_id = upload_png(seeded, ha)
    r = seeded.post("/api/ocr/tasks", headers=ha,
                    json={"file_id": file_id, "purpose": "PLAN"})
    task_id = r.json()["id"]
    assert ocr_queue.tasks.wait_idle(30)
    assert seeded.get(f"/api/ocr/tasks/{task_id}", headers=hb).status_code == 404
    assert seeded.delete(f"/api/ocr/tasks/{task_id}", headers=hb).status_code == 404
    assert seeded.post(f"/api/ocr/tasks/{task_id}/approve", headers=hb,
                       json={"text": "x"}).status_code == 404


def test_input_type_and_size_limits(seeded, monkeypatch):
    hc = login(seeded, COACH)
    pdf = seeded.post("/api/files", headers=hc, files={
        "file": ("plik.pdf", b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n", "application/pdf")
    })
    assert pdf.status_code == 201
    r = seeded.post("/api/ocr/tasks", headers=hc,
                    json={"file_id": pdf.json()["id"], "purpose": "DOKUMENT",
                          "document_id": "HOS-DOC-000000"})
    assert r.status_code == 422
    assert "zdj" in r.json()["detail"].lower()

    file_id = upload_png(seeded, hc)
    monkeypatch.setattr(settings, "ocr_max_input_mb", 0)
    r = seeded.post("/api/ocr/tasks", headers=hc,
                    json={"file_id": file_id, "purpose": "PLAN"})
    assert r.status_code == 413


# --- Kolejka jednoslotowa ----------------------------------------------


def test_queue_runs_one_task_at_a_time(seeded, monkeypatch):
    """Drugie zadanie czeka, nie wywraca ani nie liczy się równolegle —
    maszyna produkcyjna ma 512 MB RAM."""
    stub = StubEngine(delay=0.2)
    monkeypatch.setattr(ocr, "engine", stub)
    hc = login(seeded, COACH)
    first = upload_png(seeded, hc)
    second = upload_png(seeded, hc)
    before = ocr_queue.tasks.max_observed_concurrency
    ids = []
    for file_id in (first, second):
        r = seeded.post("/api/ocr/tasks", headers=hc,
                        json={"file_id": file_id, "purpose": "PRODUKT"})
        assert r.status_code == 202
        ids.append(r.json()["id"])
    assert ocr_queue.tasks.wait_idle(60) is True
    for task_id in ids:
        body = seeded.get(f"/api/ocr/tasks/{task_id}", headers=hc).json()
        assert body["status"] == "DONE"
    assert stub.max_active == 1
    assert max(before, ocr_queue.tasks.max_observed_concurrency) == 1


# --- Wynik to propozycja -----------------------------------------------


def _product_names(client, headers) -> list[str]:
    body = client.get("/api/coach/food-products?limit=500", headers=headers).json()
    return [i["name"] for i in body["items"]]


def test_result_is_only_a_proposal_until_approved(seeded, stub_engine):
    hc = login(seeded, COACH)
    file_id = upload_png(seeded, hc)
    before = _product_names(seeded, hc)
    task = run_task(seeded, hc, {"file_id": file_id, "purpose": "PRODUKT"})
    assert task["status"] == "DONE"
    # Samo rozpoznanie NIE tworzy produktu.
    assert _product_names(seeded, hc) == before

    # Człowiek poprawia wartości i dopiero zatwierdza.
    r = seeded.post(f"/api/ocr/tasks/{task['id']}/approve", headers=hc, json={
        "product": {
            "name": "Jogurt naturalny 2% (z etykiety)", "category": "Nabiał",
            "kcal_100g": 61, "protein_100g": 5.1, "fat_100g": 2.0, "carbs_100g": 4.7,
            "fiber_100g": 0.0, "default_portion_g": 150,
        }
    })
    assert r.status_code == 200
    product_id = r.json()["result_ref"]
    items = seeded.get("/api/coach/food-products?q=etykiety", headers=hc).json()["items"]
    created = next(i for i in items if i["id"] == product_id)
    # Proweniencja: skąd wzięły się dane.
    assert created["origin_kind"] == "OCR"
    assert created["origin_file_id"] == file_id
    assert created["origin_engine"] == "LOCAL"
    # Powtórne zatwierdzenie nie tworzy duplikatu.
    assert seeded.post(f"/api/ocr/tasks/{task['id']}/approve", headers=hc, json={
        "product": {"name": "x", "kcal_100g": 1, "protein_100g": 1,
                    "fat_100g": 1, "carbs_100g": 1}
    }).status_code == 409


def test_discarded_task_saves_nothing(seeded, stub_engine):
    hc = login(seeded, COACH)
    file_id = upload_png(seeded, hc)
    before = _product_names(seeded, hc)
    task = run_task(seeded, hc, {"file_id": file_id, "purpose": "PRODUKT"})
    assert seeded.delete(f"/api/ocr/tasks/{task['id']}", headers=hc).status_code == 200
    assert seeded.get(f"/api/ocr/tasks/{task['id']}", headers=hc).status_code == 404
    assert _product_names(seeded, hc) == before


def test_client_cannot_create_products_from_ocr(seeded, stub_engine):
    ha = login(seeded, CLIENT_A)
    file_id = upload_png(seeded, ha)
    task = run_task(seeded, ha, {"file_id": file_id, "purpose": "PRODUKT"})
    r = seeded.post(f"/api/ocr/tasks/{task['id']}/approve", headers=ha, json={
        "product": {"name": "x", "kcal_100g": 1, "protein_100g": 1,
                    "fat_100g": 1, "carbs_100g": 1}
    })
    assert r.status_code == 403


# --- Skan dokumentu ----------------------------------------------------


def _client_document(client, coach_headers, client_id: str) -> tuple[str, str]:
    file_id = upload_png(client, coach_headers, client_id=client_id)
    r = client.post("/api/documents", headers=coach_headers, json={
        "client_id": client_id, "file_id": file_id,
        "title": "Wyniki badań", "category": "WYNIKI",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"], file_id


def test_document_text_saved_only_after_approval(seeded, stub_engine):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    doc_id, file_id = _client_document(seeded, hc, client_id)
    task = run_task(seeded, hc, {
        "file_id": file_id, "purpose": "DOKUMENT",
        "client_id": client_id, "document_id": doc_id,
    })
    assert task["status"] == "DONE"
    docs = seeded.get(f"/api/clients/{client_id}/documents", headers=hc).json()["documents"]
    assert next(d for d in docs if d["id"] == doc_id)["ocr_text"] is None

    poprawiony = "Wyniki badań — morfologia, wartości w normie"
    r = seeded.post(f"/api/ocr/tasks/{task['id']}/approve", headers=hc,
                    json={"text": poprawiony})
    assert r.status_code == 200
    docs = seeded.get(f"/api/clients/{client_id}/documents", headers=hc).json()["documents"]
    saved = next(d for d in docs if d["id"] == doc_id)
    assert saved["ocr_text"] == poprawiony
    assert saved["ocr_engine"] == "LOCAL"
    # Oryginał pliku bez zmian — nadal da się go pobrać.
    assert seeded.get(f"/api/files/{file_id}", headers=hc).status_code == 200


def test_other_coach_cannot_ocr_foreign_client_document(seeded, stub_engine):
    hc = login(seeded, COACH)
    ha = login(seeded, CLIENT_A)
    client_id = get_user_id(seeded, ha)
    doc_id, file_id = _client_document(seeded, hc, client_id)
    create_user_with_role("obcy.ocr@example.com", "ObcyTrener#26", "Obcy", "COACH")
    h2 = login(seeded, {"email": "obcy.ocr@example.com", "password": "ObcyTrener#26"})
    r = seeded.post("/api/ocr/tasks", headers=h2, json={
        "file_id": file_id, "purpose": "DOKUMENT",
        "client_id": client_id, "document_id": doc_id,
    })
    assert r.status_code == 404


# --- Prywatność: eksport, usunięcie konta, logi ------------------------


def test_export_and_account_deletion_cover_ocr_tasks(seeded, stub_engine):
    ha = login(seeded, CLIENT_A)
    file_id = upload_png(seeded, ha)
    task = run_task(seeded, ha, {"file_id": file_id, "purpose": "PLAN"})
    assert task["status"] == "DONE"

    export = seeded.get("/api/me/export", headers=ha).json()
    assert any(t["id"] == task["id"] for t in export["ocr_tasks"])
    assert any("Jogurt" in (t["text"] or "") for t in export["ocr_tasks"])

    r = seeded.post("/api/me/deletion-request", headers=ha, json={
        "password": CLIENT_A["password"], "confirm": "USUŃ MOJE DANE",
    })
    assert r.status_code == 200, r.text
    from dzik_os.db import db_session
    from dzik_os.models import OcrTask

    with db_session() as db:
        assert db.get(OcrTask, task["id"]) is None


def test_no_recognized_text_in_logs_or_metrics(seeded, monkeypatch, capsys):
    sekret = "Wynik badania: hemoglobina glikowana 7,8%"
    monkeypatch.setattr(ocr, "engine", StubEngine(text=sekret))
    ha = login(seeded, CLIENT_A)
    file_id = upload_png(seeded, ha)
    capsys.readouterr()
    task = run_task(seeded, ha, {"file_id": file_id, "purpose": "PLAN"})
    assert task["text"] == sekret
    logs = capsys.readouterr()
    assert "hemoglobina" not in logs.out
    assert "hemoglobina" not in logs.err

    hadm = login(seeded, ADMIN)
    metrics = seeded.get("/api/metrics", headers=hadm)
    assert metrics.status_code == 200
    assert "hemoglobina" not in metrics.text
    counters = metrics.json()["counters"]
    assert counters["ocr_tasks_done"] >= 1
    assert "ocr_engine_unavailable" in counters


def test_audit_records_fact_without_content(seeded, stub_engine):
    ha = login(seeded, CLIENT_A)
    file_id = upload_png(seeded, ha)
    task = run_task(seeded, ha, {"file_id": file_id, "purpose": "PLAN"})
    assert task["status"] == "DONE"
    from dzik_os.hos_bridge import event_store

    events = [
        e for e in event_store().all()
        if str(e.get("event_type", "")).startswith("OCR_")
    ]
    assert events, "audyt musi odnotować fakt rozpoznania"
    dump = json.dumps(events, ensure_ascii=False)
    assert "Jogurt" not in dump
    assert any(e["payload"].get("chars") for e in events if e["event_type"] == "OCR_RECOGNIZED")


# --- Idempotencja i limity ---------------------------------------------


def test_repeated_submit_with_same_key_returns_same_task(seeded, stub_engine):
    hc = login(seeded, COACH)
    file_id = upload_png(seeded, hc)
    payload = {"file_id": file_id, "purpose": "PRODUKT",
               "idempotency_key": "ocr-klucz-testowy-1"}
    first = seeded.post("/api/ocr/tasks", headers=hc, json=payload)
    second = seeded.post("/api/ocr/tasks", headers=hc, json=payload)
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert ocr_queue.tasks.wait_idle(30)


def test_daily_task_limit_is_explicit(seeded, stub_engine, monkeypatch):
    monkeypatch.setattr(settings, "ocr_daily_tasks_user", 1)
    hc = login(seeded, COACH)
    file_id = upload_png(seeded, hc)
    assert seeded.post("/api/ocr/tasks", headers=hc,
                       json={"file_id": file_id, "purpose": "PLAN"}).status_code == 202
    r = seeded.post("/api/ocr/tasks", headers=hc,
                    json={"file_id": file_id, "purpose": "PLAN"})
    assert r.status_code == 429
    assert "limit" in r.json()["detail"].lower()
    assert ocr_queue.tasks.wait_idle(30)


# --- Przygotowanie obrazu (pamięć maszyny) -----------------------------


def test_image_is_downscaled_before_recognition():
    """Dłuższy bok maks. ~1600 px — inaczej 512 MB RAM na Fly.io nie starcza."""
    from PIL import Image

    big = make_jpeg(3000, 1200)
    prepared = ocr.prepare_image(big, max_px=1600)
    img = Image.open(io.BytesIO(prepared))
    assert max(img.size) == 1600
    assert img.mode == "L"
    assert len(prepared) < len(big) * 20


def test_broken_image_is_a_state_not_an_exception():
    result = ocr.LocalOcrEngine().recognize(b"to nie jest obraz", content_type="image/png")
    assert result.ok is False
    assert result.error_code in ("BAD_IMAGE", "ENGINE_UNAVAILABLE")

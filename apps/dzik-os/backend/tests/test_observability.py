"""Obserwowalność: wspólny model błędów, request id, redakcja logów,
/api/metrics, /api/ready, raporty błędów frontendu.

Kontrakt modelu błędu: {"detail", "code", "request_id"[, "errors"]} —
detail pozostaje bezpiecznym polskim komunikatem (frontend na nim polega),
code jest stabilny, request_id zgadza się z nagłówkiem X-Request-Id.
"""

from __future__ import annotations

import json

from conftest import ADMIN, CLIENT_A, CLIENT_B, COACH, get_user_id, login

from dzik_os.main import app
from dzik_os.routers.telemetry import redact_stack

SECRET_MARKER = "SEKRETNY-KOMUNIKAT-Z-DANYMI"

# Trasa testowa symulująca awarię 500 z wrażliwym komunikatem wyjątku —
# rejestrowana raz na sesję testową.
if not any(getattr(r, "path", "") == "/api/_test/boom" for r in app.routes):
    async def _boom():
        raise RuntimeError(f"{SECRET_MARKER} jan.kowalski@example.com")

    app.add_api_route("/api/_test/boom", _boom, methods=["GET"])
    # Przed catch-all SPA (/{full_path:path}) — inaczej, gdy frontend/dist
    # istnieje, trasa testowa nigdy nie zostałaby dopasowana.
    app.router.routes.insert(0, app.router.routes.pop())


def _parse_logs(captured: str) -> list[dict]:
    out = []
    for line in captured.splitlines():
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


# --- Kształt modelu błędu per status ---------------------------------------


def assert_error_shape(resp, status: int, code: str) -> dict:
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert body["code"] == code
    assert isinstance(body["detail"], str) and body["detail"]
    assert body["request_id"] == resp.headers["X-Request-Id"]
    return body


def test_401_shape(client):
    assert_error_shape(client.get("/api/auth/me"), 401, "UNAUTHORIZED")


def test_403_shape(seeded):
    headers = login(seeded, CLIENT_A)
    assert_error_shape(seeded.get("/api/metrics", headers=headers), 403, "FORBIDDEN")


def test_404_shape(seeded):
    headers = login(seeded, CLIENT_A)
    assert_error_shape(
        seeded.get("/api/files/HOS-FIL-DEADBEEF0000", headers=headers),
        404, "NOT_FOUND",
    )


def test_404_idor_uses_same_shape(seeded):
    """ResourceAccessDenied (P3) nadal daje 404 + audyt, teraz we wspólnym
    modelu błędów."""
    headers_a = login(seeded, CLIENT_A)
    other_id = get_user_id(seeded, login(seeded, CLIENT_B))
    assert_error_shape(
        seeded.get(f"/api/clients/{other_id}/profile", headers=headers_a),
        404, "NOT_FOUND",
    )


def test_409_shape(seeded):
    headers = login(seeded, COACH)
    r = seeded.post("/api/coach/clients", headers=headers, json={
        "client_name": "Duplikat", "client_email": CLIENT_A["email"],
        "initial_password": "StartoweH#123",
    })
    assert_error_shape(r, 409, "CONFLICT")


def test_422_shape_and_no_input_echo(client):
    """Walidacja: stabilny kod, lista pól — bez odbicia wartości wejściowej
    (pydanticowe 'input' może zawierać dane zdrowotne)."""
    r = client.post("/api/auth/login", json={"email": "tajny.adres@example.com"})
    body = assert_error_shape(r, 422, "VALIDATION_ERROR")
    assert any(e["field"] == "password" for e in body["errors"])
    assert "tajny.adres" not in r.text


def test_429_shape(seeded):
    for _ in range(5):
        seeded.post("/api/auth/login",
                    json={"email": CLIENT_A["email"], "password": "zle-haslo"})
    r = seeded.post("/api/auth/login", json=CLIENT_A)
    assert_error_shape(r, 429, "RATE_LIMITED")


def test_500_shape_without_internals(client, capsys):
    """Nieobsłużony wyjątek: 500 we wspólnym modelu, bez stack trace, SQL
    ani komunikatu wyjątku; log strukturalny ma typ + ramki, ale NIE ma
    komunikatu (może zawierać dane) ani e-maila."""
    r = client.get("/api/_test/boom")
    body = assert_error_shape(r, 500, "INTERNAL_ERROR")
    assert SECRET_MARKER not in r.text
    assert "RuntimeError" not in r.text
    assert "Traceback" not in r.text
    assert body["request_id"]
    captured = capsys.readouterr().out
    logs = _parse_logs(captured)
    boom = [rec for rec in logs if rec["event"] == "unhandled_exception"]
    assert boom and boom[0]["error_type"] == "RuntimeError"
    assert any("test_observability" in f for f in boom[0]["frames"])
    assert SECRET_MARKER not in captured
    assert "jan.kowalski@example.com" not in captured
    # Nagłówki bezpieczeństwa obejmują też 500 (ErrorEnvelope jest najgłębiej).
    assert r.headers["Cache-Control"] == "no-store"
    assert "Content-Security-Policy" in r.headers


# --- Request id i strukturalny log żądań -----------------------------------


def test_request_id_on_success(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert len(r.headers["X-Request-Id"]) == 16


def test_request_log_has_user_id_not_email_and_masked_path(seeded, capsys):
    headers = login(seeded, CLIENT_A)
    user_id = get_user_id(seeded, headers)
    capsys.readouterr()  # wyczyść logi logowania
    r = seeded.get(f"/api/clients/{user_id}/profile", headers=headers)
    assert r.status_code == 200
    logs = [rec for rec in _parse_logs(capsys.readouterr().out) if rec["event"] == "request"]
    assert logs, "brak strukturalnego logu żądania"
    rec = logs[-1]
    # Ścieżka jako szablon trasy — surowy identyfikator nie trafia do logu.
    assert rec["path"] == "/api/clients/{client_id}/profile"
    assert rec["user_id"] == user_id
    assert rec["status"] == 200
    assert isinstance(rec["duration_ms"], (int, float))
    assert CLIENT_A["email"] not in json.dumps(logs)


def test_login_log_never_contains_email_or_password(seeded, capsys):
    seeded.post("/api/auth/login", json=CLIENT_A)
    captured = capsys.readouterr().out
    assert CLIENT_A["email"] not in captured
    assert CLIENT_A["password"] not in captured


# --- Readiness i metryki ----------------------------------------------------


def test_ready_ok(client):
    r = client.get("/api/ready")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "checks": {"database": True, "uploads_writable": True}}


def test_metrics_admin_only_and_counts(seeded):
    assert seeded.get("/api/metrics").status_code == 401
    headers = login(seeded, ADMIN)
    seeded.get("/api/files/HOS-FIL-DEADBEEF0000", headers=headers)  # 404 → licznik 4xx
    r = seeded.get("/api/metrics", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["requests"]["total"] >= 2
    assert body["requests"]["by_class"].get("4xx", 0) >= 1
    assert body["latency_ms"]["p50"] is not None
    assert set(body["counters"]) >= {
        "reminder_loop_errors", "push_send_failures", "frontend_error_reports",
        "unhandled_exceptions", "access_denied", "audit_log_failures",
    }
    # Bez sekretów: metryki nie zawierają e-maili, tokenów ani ścieżek dysku.
    assert "@" not in r.text
    assert "/data/" not in r.text


def test_metrics_counts_access_denied(seeded):
    headers_a = login(seeded, CLIENT_A)
    other_id = get_user_id(seeded, login(seeded, CLIENT_B))
    seeded.get(f"/api/clients/{other_id}/profile", headers=headers_a)
    admin = login(seeded, ADMIN)
    body = seeded.get("/api/metrics", headers=admin).json()
    assert body["counters"]["access_denied"] >= 1


# --- Raporty błędów JS frontendu -------------------------------------------


def test_frontend_error_report_accepted_and_counted(seeded, capsys):
    r = seeded.post("/api/telemetry/frontend-errors", json={
        "type": "TypeError",
        "component": "route:/raport",
        "stack": (
            "TypeError: Cannot read properties of undefined\n"
            "    at submit (https://dzik.example.com/assets/index-abc123.js:10:2000)\n"
            "    at fetch (https://dzik.example.com/assets/vendor-def456.js:1:99)"
        ),
    })
    assert r.status_code == 202 and r.json() == {"ok": True}
    admin = login(seeded, ADMIN)
    body = seeded.get("/api/metrics", headers=admin).json()
    assert body["counters"]["frontend_error_reports"] == 1


def test_frontend_error_report_redacts_content(seeded, capsys):
    """Do logu trafiają wyłącznie: typ, komponent, ramki plik:linia:kolumna.
    Treści (komunikat, URL-e, e-maile, tokeny) są odrzucane serwerowo."""
    seeded.post("/api/telemetry/frontend-errors", json={
        "type": "Error: token=SEKRET123 tajny@example.com",
        "component": "Checkin <tajne dane zdrowotne: waga 92kg>",
        "stack": (
            "Error: pacjent tajny@example.com waga 92kg token=SEKRET123\n"
            "    at save (https://dzik.example.com/assets/index-abc123.js:42:7)\n"
            "    at https://evil.example.com/steal?q=SEKRET123\n"
        ),
    })
    captured = capsys.readouterr().out
    logs = [rec for rec in _parse_logs(captured) if rec["event"] == "frontend_error"]
    assert logs
    rec = logs[0]
    assert rec["frames"] == ["index-abc123.js:42:7"]
    dumped = json.dumps(rec)
    assert "tajny@example.com" not in dumped
    assert "SEKRET123" not in dumped
    assert "92kg" not in dumped
    assert "evil.example.com" not in dumped


def test_frontend_error_report_rate_limited(seeded):
    for _ in range(10):
        r = seeded.post("/api/telemetry/frontend-errors",
                        json={"type": "Error", "stack": None})
        assert r.status_code == 202
    r = seeded.post("/api/telemetry/frontend-errors", json={"type": "Error"})
    assert_error_shape(r, 429, "RATE_LIMITED")


def test_redact_stack_unit():
    assert redact_stack(None) == []
    assert redact_stack("no frames here, just text with secret@example.com") == []
    stack = "\n".join(
        f"    at fn{i} (https://x/assets/chunk-{i}.js:{i}:1)" for i in range(30)
    )
    frames = redact_stack(stack)
    assert len(frames) == 20  # limit ramek
    assert frames[0] == "chunk-0.js:0:1"
